"""
Auto-update service.

Verifie un manifest distant pour detecter une nouvelle version, la telecharge,
verifie son hash SHA-256, et installe via un script externe (puisque l'exe ne
peut pas se remplacer lui-meme pendant son execution).

Manifest format (publie a une URL stable) :
    {
        "latest":       "1.0.1",
        "released_at":  "2026-06-01T00:00:00Z",
        "channel":      "stable",
        "min_version":  "1.0.0",
        "url":          "https://riskpulse.io/releases/RiskPulse-1.0.1-portable.zip",
        "sha256":       "abc123...",
        "size":         512345678,
        "notes":        "Bug fixes and performance improvements.",
        "mandatory":    false
    }
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


# URL par defaut (a remplacer par celle du serveur de release)
DEFAULT_MANIFEST_URL = "https://riskpulse.io/releases/latest.json"
CURRENT_VERSION = "1.0.0"
USER_AGENT = f"RiskPulse-Updater/{CURRENT_VERSION}"


# ─────────────────────────────────────────────
#  STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class UpdateInfo:
    """Resultat d'un check : nouvelle version disponible ou pas."""
    available:      bool = False
    current:        str  = ""
    latest:         str  = ""
    url:            str  = ""
    sha256:         str  = ""
    size:           int  = 0
    notes:          str  = ""
    released_at:    str  = ""
    mandatory:      bool = False
    error:          str  = ""

    def to_dict(self) -> dict:
        return {
            "available":   self.available,
            "current":     self.current,
            "latest":      self.latest,
            "url":         self.url,
            "size":        self.size,
            "notes":       self.notes,
            "released_at": self.released_at,
            "mandatory":   self.mandatory,
            "error":       self.error,
        }


# ─────────────────────────────────────────────
#  VERSION COMPARISON (SemVer light)
# ─────────────────────────────────────────────

def _parse_version(v: str) -> tuple:
    """'1.2.3' -> (1, 2, 3). Ignore le pre-release suffix."""
    v = v.strip().lstrip("v")
    main = v.split("-")[0].split("+")[0]
    try:
        return tuple(int(p) for p in main.split("."))
    except ValueError:
        return (0,)


def version_gt(a: str, b: str) -> bool:
    """True si version a > version b."""
    return _parse_version(a) > _parse_version(b)


# ─────────────────────────────────────────────
#  UPDATER
# ─────────────────────────────────────────────

class Updater:
    """
    Gestionnaire d'updates. Singleton.
    """

    def __init__(self, current_version: str = CURRENT_VERSION,
                  manifest_url: str = DEFAULT_MANIFEST_URL):
        self.current_version = current_version
        self.manifest_url = manifest_url
        self._last_check: Optional[UpdateInfo] = None

    # ── Check ────────────────────────────────

    def check(self, timeout: int = 8) -> UpdateInfo:
        """
        Recupere le manifest distant et compare. Bloquant — appeler depuis un thread.
        """
        info = UpdateInfo(current=self.current_version)
        try:
            req = urllib.request.Request(self.manifest_url, headers={
                "User-Agent": USER_AGENT,
                "Accept":     "application/json",
                "Cache-Control": "no-cache",
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            info.error = f"HTTP {e.code} : {e.reason}"
            return info
        except urllib.error.URLError as e:
            info.error = f"Network error : {e.reason}"
            return info
        except Exception as e:
            info.error = f"Manifest error : {e}"
            return info

        info.latest      = data.get("latest", "")
        info.url         = data.get("url", "")
        info.sha256      = data.get("sha256", "").lower()
        info.size        = int(data.get("size", 0))
        info.notes       = data.get("notes", "")
        info.released_at = data.get("released_at", "")
        info.mandatory   = bool(data.get("mandatory", False))

        info.available = (
            info.latest
            and version_gt(info.latest, self.current_version)
            and info.url
            and info.sha256
        )
        self._last_check = info
        return info

    # ── Download ──────────────────────────────

    def download(self, info: UpdateInfo,
                  on_progress: Optional[Callable[[int, int], None]] = None,
                  ) -> Optional[Path]:
        """
        Telecharge l'archive. Verifie SHA-256. Retourne le chemin local.
        Retourne None en cas d'echec.
        """
        if not info.url:
            return None

        # Telechargement dans tempdir
        tmp_dir = Path(tempfile.gettempdir()) / "riskpulse_update"
        tmp_dir.mkdir(exist_ok=True)
        suffix = Path(info.url).suffix or ".zip"
        target = tmp_dir / f"update_{info.latest}{suffix}"

        try:
            req = urllib.request.Request(info.url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0)) or info.size
                downloaded = 0
                sha = hashlib.sha256()
                with open(target, "wb") as f:
                    while True:
                        chunk = resp.read(64 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        sha.update(chunk)
                        downloaded += len(chunk)
                        if on_progress and total:
                            on_progress(downloaded, total)
        except Exception as e:
            logger.exception("Download failed")
            if target.exists():
                target.unlink(missing_ok=True)
            return None

        # Verification du hash
        actual = sha.hexdigest()
        if actual.lower() != info.sha256.lower():
            logger.error(f"SHA-256 mismatch : expected {info.sha256}, got {actual}")
            target.unlink(missing_ok=True)
            return None

        return target

    # ── Apply ─────────────────────────────────

    def apply(self, archive_path: Path, restart: bool = True) -> bool:
        """
        Applique l'update : extrait l'archive, backup l'install courant, swap,
        relance l'app.

        Utilise un script externe `apply_update.bat` pour faire le swap car l'exe
        en cours d'execution ne peut pas se remplacer lui-meme.
        """
        if not getattr(sys, "frozen", False):
            logger.warning("Update apply : ne marche qu'en mode frozen")
            return False
        if not archive_path or not archive_path.exists():
            return False

        # Determine l'install dir (le dossier qui contient RiskPulse.exe)
        install_dir = Path(sys.executable).parent
        backup_dir  = install_dir.parent / f"{install_dir.name}.backup"

        # Extrait l'archive dans un staging dir
        staging = archive_path.parent / "staging"
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive_path) as z:
                z.extractall(staging)
        except Exception as e:
            logger.exception("Archive extraction failed")
            return False

        # Determine la racine du nouveau bundle dans staging (peut etre staging/RiskPulse/)
        new_root = staging
        children = [p for p in staging.iterdir() if p.is_dir()]
        if len(children) == 1 and (children[0] / "RiskPulse.exe").exists():
            new_root = children[0]

        if not (new_root / "RiskPulse.exe").exists():
            logger.error("New bundle missing RiskPulse.exe")
            shutil.rmtree(staging, ignore_errors=True)
            return False

        # Genere le batch script qui fait :
        #  1. wait that RiskPulse.exe is gone
        #  2. move install -> backup
        #  3. move staging -> install
        #  4. (optionnel) restart RiskPulse.exe
        bat_path = archive_path.parent / "apply_update.bat"
        restart_line = f'start "" "{install_dir}\\RiskPulse.exe"' if restart else ""
        bat_content = f"""@echo off
echo Applying RiskPulse update...
:wait
tasklist /FI "IMAGENAME eq RiskPulse.exe" 2>nul | find /I "RiskPulse.exe" >nul
if errorlevel 1 goto :doit
timeout /t 2 /nobreak >nul
goto :wait

:doit
if exist "{backup_dir}" rmdir /S /Q "{backup_dir}"
move "{install_dir}" "{backup_dir}"
move "{new_root}"   "{install_dir}"
{restart_line}
"""
        bat_path.write_text(bat_content, encoding="utf-8")

        # Lance le batch en detached
        try:
            import subprocess
            subprocess.Popen(
                ["cmd.exe", "/c", str(bat_path)],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008,  # DETACHED
                close_fds=True,
            )
            logger.info("Update apply script launched")
            return True
        except Exception:
            logger.exception("Failed to launch apply script")
            return False


# Singleton
_updater_instance: Optional[Updater] = None


def get_updater(current_version: str = CURRENT_VERSION,
                 manifest_url: Optional[str] = None) -> Updater:
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = Updater(
            current_version=current_version,
            manifest_url=manifest_url or DEFAULT_MANIFEST_URL,
        )
    return _updater_instance
