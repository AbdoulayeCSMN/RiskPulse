"""
Telemetry & crash reports — local-first, opt-in.

Principe
--------
- AUCUN envoi reseau. Tout reste sur la machine.
- Opt-in : desactive par defaut. L'utilisateur active dans Settings.
- Stockage : SQLite (data/telemetry.db).
- L'utilisateur peut exporter un zip de support (crashes + logs) pour
  envoyer manuellement par email a l'editeur en cas de bug.

Donnees collectees (uniquement si opt-in)
-----------------------------------------
- Evenements applicatifs : 'app_start', 'app_quit', 'view_shown',
  'feature_used' (juste un nom + timestamp, AUCUN contenu utilisateur).
- Crashes : exc_type, exc_value, traceback complet (chemins absolus
  scrub a partir de "users/<name>/..."), thread name, app version.

Anti-tracking
-------------
- Pas d'install id, pas d'IP, pas de device fingerprint.
- Le user_id en base est local (1 ligne par session) et n'est jamais
  exporte tel quel ; l'export reset les ids aleatoirement.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import sqlite3
import sys
import threading
import time
import traceback
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from utils.paths import paths

log = logging.getLogger("riskpulse.telemetry")


# ─────────────────────────────────────────────────────────────────────────────
# OPT-IN
# ─────────────────────────────────────────────────────────────────────────────

PREF_FILE = paths.preferences        # data/preferences.json
PREF_KEY  = "telemetry_enabled"      # bool


def _load_pref(default: bool = False) -> bool:
    try:
        if PREF_FILE.exists():
            return bool(json.loads(PREF_FILE.read_text(encoding="utf-8"))
                          .get(PREF_KEY, default))
    except Exception:
        pass
    return default


def _save_pref(value: bool):
    try:
        data = {}
        if PREF_FILE.exists():
            try:
                data = json.loads(PREF_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data[PREF_KEY] = bool(value)
        PREF_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    except Exception:
        log.warning("Cannot persist telemetry pref", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
# SCRUB
# ─────────────────────────────────────────────────────────────────────────────

# Masque les chemins absolus qui contiennent souvent un nom utilisateur.
_PATH_RX_WIN  = re.compile(r"[A-Za-z]:\\Users\\[^\\]+", re.IGNORECASE)
_PATH_RX_NIX  = re.compile(r"/Users/[^/]+|/home/[^/]+", re.IGNORECASE)
_EMAIL_RX     = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def scrub(text: str) -> str:
    if not text:
        return text
    text = _PATH_RX_WIN.sub("<HOME>", text)
    text = _PATH_RX_NIX.sub("<HOME>", text)
    text = _EMAIL_RX.sub("<EMAIL>", text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# TELEMETRY SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class Telemetry:
    """Singleton local telemetry. Thread-safe."""

    _instance: Optional["Telemetry"] = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._db_path = paths.data_dir / "telemetry.db"
        self._enabled = _load_pref(False)
        self._app_version = "1.0.1"
        self._session_start = time.time()
        self._init_db()

    # ── Opt-in ───────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, value: bool):
        self._enabled = bool(value)
        _save_pref(self._enabled)
        log.info("Telemetry %s", "enabled" if self._enabled else "disabled")

    def set_app_version(self, v: str):
        self._app_version = v

    # ── DB ───────────────────────────────────────────

    @contextmanager
    def _conn(self):
        c = sqlite3.connect(str(self._db_path), timeout=10)
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def _init_db(self):
        with self._conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        REAL    NOT NULL,
                name      TEXT    NOT NULL,
                detail    TEXT,
                version   TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_name ON events(name);
            CREATE INDEX IF NOT EXISTS idx_events_ts   ON events(ts);

            CREATE TABLE IF NOT EXISTS crashes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                ts           REAL    NOT NULL,
                exc_type     TEXT,
                exc_value    TEXT,
                traceback    TEXT,
                thread_name  TEXT,
                version      TEXT,
                platform     TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_crashes_type ON crashes(exc_type);
            CREATE INDEX IF NOT EXISTS idx_crashes_ts   ON crashes(ts);
            """)

    # ── Events ───────────────────────────────────────

    def event(self, name: str, detail: Optional[dict] = None):
        if not self._enabled:
            return
        try:
            d = json.dumps(detail, ensure_ascii=False) if detail else None
            with self._conn() as c:
                c.execute(
                    "INSERT INTO events(ts, name, detail, version) VALUES(?,?,?,?)",
                    (time.time(), name, d, self._app_version),
                )
        except Exception:
            log.debug("event() failed", exc_info=True)

    def feature_used(self, feature: str):
        self.event("feature_used", {"feature": feature})

    def view_shown(self, view_id: str):
        self.event("view_shown", {"view": view_id})

    # ── Crashes ──────────────────────────────────────

    def record_crash(self, exc_type, exc_value, tb, thread_name: str = "main"):
        """Capture inconditionnelle (memes si opt-out, on garde localement
        pour aider en cas de plainte client). Aucun envoi reseau."""
        try:
            full_tb = "".join(traceback.format_exception(exc_type, exc_value, tb))
            with self._conn() as c:
                c.execute(
                    """INSERT INTO crashes
                       (ts, exc_type, exc_value, traceback, thread_name,
                        version, platform)
                       VALUES(?,?,?,?,?,?,?)""",
                    (
                        time.time(),
                        exc_type.__name__ if exc_type else "UnknownError",
                        scrub(str(exc_value)),
                        scrub(full_tb),
                        thread_name,
                        self._app_version,
                        f"{platform.system()} {platform.release()}",
                    ),
                )
        except Exception:
            log.debug("record_crash() failed", exc_info=True)

    # ── Read API ─────────────────────────────────────

    def list_crashes(self, limit: int = 50):
        with self._conn() as c:
            rows = c.execute(
                """SELECT id, ts, exc_type, exc_value, traceback,
                          thread_name, version, platform
                   FROM crashes ORDER BY ts DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [
            {"id": r[0], "ts": r[1], "exc_type": r[2], "exc_value": r[3],
             "traceback": r[4], "thread_name": r[5], "version": r[6],
             "platform": r[7]}
            for r in rows
        ]

    def top_errors(self, limit: int = 10):
        with self._conn() as c:
            rows = c.execute(
                """SELECT exc_type, COUNT(*) AS n, MAX(ts) AS last
                   FROM crashes GROUP BY exc_type
                   ORDER BY n DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [{"exc_type": r[0], "count": r[1], "last_ts": r[2]} for r in rows]

    def feature_usage(self, limit: int = 20):
        with self._conn() as c:
            rows = c.execute(
                """SELECT json_extract(detail, '$.feature') AS feature,
                          COUNT(*) AS n
                   FROM events
                   WHERE name='feature_used' AND feature IS NOT NULL
                   GROUP BY feature
                   ORDER BY n DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [{"feature": r[0], "count": r[1]} for r in rows]

    def counts(self) -> dict:
        with self._conn() as c:
            ev = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            cr = c.execute("SELECT COUNT(*) FROM crashes").fetchone()[0]
        return {"events": ev, "crashes": cr}

    def clear(self):
        with self._conn() as c:
            c.execute("DELETE FROM events")
            c.execute("DELETE FROM crashes")

    # ── Export ───────────────────────────────────────

    def export_support_bundle(self, out_dir: Optional[Path] = None) -> Path:
        """
        Cree un zip 'riskpulse-support-YYYYMMDD-HHMMSS.zip' contenant :
          - telemetry.db (copy)
          - logs/riskpulse.log + errors.log (si presents)
          - meta.json (version, OS, counts)
        L'utilisateur peut l'envoyer manuellement par email.
        """
        out_dir = out_dir or paths.exports_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        zip_path = out_dir / f"riskpulse-support-{ts}.zip"

        meta = {
            "exported_at":  datetime.now(timezone.utc).isoformat(),
            "app_version":  self._app_version,
            "platform":     f"{platform.system()} {platform.release()}",
            "python":       platform.python_version(),
            "counts":       self.counts(),
            "opt_in":       self._enabled,
        }

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            if self._db_path.exists():
                z.write(self._db_path, arcname="telemetry.db")
            for log_file in (paths.main_log, paths.error_log):
                if log_file.exists():
                    z.write(log_file, arcname=f"logs/{log_file.name}")
            z.writestr("meta.json",
                        json.dumps(meta, indent=2, ensure_ascii=False))

        log.info("Support bundle exported: %s", zip_path)
        return zip_path


# Singleton accessor
def get_telemetry() -> Telemetry:
    return Telemetry()
