"""
Watch list & sources & alerts.
================================
S'appuie sur le meme SQLite que la KB (services/knowledge_base.py).
"""

from __future__ import annotations
import hashlib
import logging
from datetime import datetime
from typing import Optional

from .knowledge_base import get_kb

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  WATCH LIST
# ─────────────────────────────────────────────

class WatchlistManager:
    """CRUD pour les entites surveillees, les sources, et les alertes."""

    def __init__(self):
        self._kb = get_kb()

    # ── Watchlist ────────────────────────────

    def add_watch(self, name: str, threshold: float = 0.6,
                  entity_id: Optional[int] = None,
                  notes: str = "") -> int:
        ts = datetime.now().isoformat()
        with self._kb._conn() as c:
            # Si pas d'entity_id fourni, essaie de matcher avec une entite existante
            if entity_id is None:
                row = c.execute(
                    "SELECT id FROM entities WHERE canonical_name LIKE ? LIMIT 1",
                    (f"%{name.lower()}%",)
                ).fetchone()
                if row:
                    entity_id = row["id"]

            cur = c.execute("""
                INSERT INTO watchlist (entity_id, name, added_at, threshold, enabled, notes)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (entity_id, name, ts, threshold, notes))
            return cur.lastrowid

    def remove_watch(self, watch_id: int):
        with self._kb._conn() as c:
            c.execute("DELETE FROM watchlist WHERE id=?", (watch_id,))

    def toggle_watch(self, watch_id: int, enabled: bool):
        with self._kb._conn() as c:
            c.execute("UPDATE watchlist SET enabled=? WHERE id=?",
                      (1 if enabled else 0, watch_id))

    def list_watches(self, enabled_only: bool = False) -> list[dict]:
        with self._kb._conn() as c:
            q = ("SELECT w.*, e.avg_risk_score, e.trend "
                 "FROM watchlist w "
                 "LEFT JOIN entities e ON w.entity_id = e.id ")
            if enabled_only:
                q += "WHERE w.enabled=1 "
            q += "ORDER BY w.added_at DESC"
            rows = c.execute(q).fetchall()
        return [dict(r) for r in rows]

    def update_last_score(self, watch_id: int, score: float):
        with self._kb._conn() as c:
            c.execute(
                "UPDATE watchlist SET last_score=?, last_check=? WHERE id=?",
                (score, datetime.now().isoformat(), watch_id)
            )

    # ── Sources ──────────────────────────────

    def add_source(self, url: str, label: str = "", source_type: str = "url") -> int:
        ts = datetime.now().isoformat()
        with self._kb._conn() as c:
            try:
                cur = c.execute("""
                    INSERT INTO sources (url, label, type, enabled, added_at)
                    VALUES (?, ?, ?, 1, ?)
                """, (url, label or url, source_type, ts))
                return cur.lastrowid
            except Exception as e:
                logger.warning(f"Source deja existante : {url} ({e})")
                row = c.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
                return row["id"] if row else -1

    def remove_source(self, source_id: int):
        with self._kb._conn() as c:
            c.execute("DELETE FROM source_items WHERE source_id=?", (source_id,))
            c.execute("DELETE FROM sources WHERE id=?", (source_id,))

    def toggle_source(self, source_id: int, enabled: bool):
        with self._kb._conn() as c:
            c.execute("UPDATE sources SET enabled=? WHERE id=?",
                      (1 if enabled else 0, source_id))

    def list_sources(self, enabled_only: bool = False) -> list[dict]:
        with self._kb._conn() as c:
            q = "SELECT * FROM sources "
            if enabled_only:
                q += "WHERE enabled=1 "
            q += "ORDER BY added_at DESC"
            rows = c.execute(q).fetchall()
        return [dict(r) for r in rows]

    def update_source_status(self, source_id: int, status: str,
                              items_added: int = 0):
        with self._kb._conn() as c:
            c.execute("""
                UPDATE sources SET
                  last_check=?, last_status=?, items_seen=COALESCE(items_seen,0)+?
                WHERE id=?
            """, (datetime.now().isoformat(), status, items_added, source_id))

    # ── Source items (deduplication) ─────────

    def is_item_seen(self, source_id: int, item_hash: str) -> bool:
        with self._kb._conn() as c:
            row = c.execute(
                "SELECT id FROM source_items WHERE source_id=? AND item_hash=?",
                (source_id, item_hash)
            ).fetchone()
            return row is not None

    def record_item(self, source_id: int, item_hash: str, title: str,
                    url: str, published: str = "",
                    analysis_id: Optional[int] = None) -> int:
        with self._kb._conn() as c:
            try:
                cur = c.execute("""
                    INSERT INTO source_items
                      (source_id, item_hash, title, url, published, fetched_at,
                       analyzed, analysis_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source_id, item_hash, title, url, published,
                    datetime.now().isoformat(),
                    1 if analysis_id else 0, analysis_id,
                ))
                return cur.lastrowid
            except Exception as e:
                logger.debug(f"Item deja vu : {e}")
                return -1

    # ── Alertes ──────────────────────────────

    def record_alert(self, *,
                     watchlist_id: int,
                     entity_name: str,
                     score: float,
                     delta: float,
                     verdict: str,
                     analysis_id: Optional[int] = None,
                     source_url: str = "",
                     title: str = "",
                     message: str = "") -> int:
        ts = datetime.now().isoformat()
        with self._kb._conn() as c:
            cur = c.execute("""
                INSERT INTO alerts
                  (timestamp, watchlist_id, entity_name, score, delta,
                   verdict, analysis_id, source_url, title, message, seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                ts, watchlist_id, entity_name, score, delta,
                verdict, analysis_id, source_url, title, message,
            ))
            return cur.lastrowid

    def list_alerts(self, limit: int = 50, unread_only: bool = False) -> list[dict]:
        with self._kb._conn() as c:
            q = "SELECT * FROM alerts "
            if unread_only:
                q += "WHERE seen=0 "
            q += "ORDER BY timestamp DESC LIMIT ?"
            rows = c.execute(q, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def count_unread_alerts(self) -> int:
        with self._kb._conn() as c:
            row = c.execute("SELECT COUNT(*) FROM alerts WHERE seen=0").fetchone()
            return row[0] if row else 0

    def mark_alert_seen(self, alert_id: int):
        with self._kb._conn() as c:
            c.execute("UPDATE alerts SET seen=1 WHERE id=?", (alert_id,))

    def mark_all_seen(self):
        with self._kb._conn() as c:
            c.execute("UPDATE alerts SET seen=1 WHERE seen=0")


# Singleton
_wl_instance: Optional[WatchlistManager] = None

def get_watchlist() -> WatchlistManager:
    global _wl_instance
    if _wl_instance is None:
        _wl_instance = WatchlistManager()
    return _wl_instance


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def hash_item(*parts: str) -> str:
    """Hash deterministe d'un item pour la dedup."""
    s = "||".join(p or "" for p in parts)
    return hashlib.sha1(s.encode("utf-8", errors="replace")).hexdigest()[:16]
