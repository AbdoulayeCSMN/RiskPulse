"""
Gestionnaire de chemins production-ready.

En dev (mode source) : tous les chemins sont relatifs au repo.
En prod (exe) : les donnees utilisateur sont dans %APPDATA%/RiskPulse
                (ou ~/.config/RiskPulse sur Linux/Mac).

Cela permet :
  - Pas de write dans Program Files (Windows nous interdit l'access)
  - Plusieurs utilisateurs Windows ont chacun leur base
  - Backup/restore plus facile (1 seul dossier a copier)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


class _Paths:
    """Singleton pour resoudre tous les chemins de l'application."""

    APP_NAME = "RiskPulse"
    ENV_FORCE_DEV = "RISKPULSE_DEV"   # Force le mode dev si =1

    def __init__(self):
        self._is_frozen = getattr(sys, "frozen", False)
        # Override par env var pour les devs
        self._force_dev = os.environ.get(self.ENV_FORCE_DEV) == "1"

        if self._is_frozen and not self._force_dev:
            self._user_dir = self._compute_user_dir()
        else:
            # Mode dev : tout dans le repo
            self._user_dir = Path(__file__).resolve().parent.parent

        self._app_dir = self._compute_app_dir()

    # ── Resolution ────────────────────────────

    def _compute_app_dir(self) -> Path:
        """Dossier de l'app (binaires, locales, etc.). Read-only en prod."""
        if self._is_frozen:
            # PyInstaller : sys._MEIPASS pointe vers le bundle
            base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            return Path(base)
        return Path(__file__).resolve().parent.parent

    def _compute_user_dir(self) -> Path:
        """Dossier utilisateur (writable, persistant entre versions)."""
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
        elif sys.platform == "darwin":
            base = os.path.expanduser("~/Library/Application Support")
        else:
            base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return Path(base) / self.APP_NAME

    # ── Chemins exposes ──────────────────────

    @property
    def is_frozen(self) -> bool:
        return self._is_frozen

    @property
    def app_dir(self) -> Path:
        return self._app_dir

    @property
    def user_dir(self) -> Path:
        return self._user_dir

    @property
    def data_dir(self) -> Path:
        p = self._user_dir / "data"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def logs_dir(self) -> Path:
        p = self._user_dir / "data" / "logs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def exports_dir(self) -> Path:
        p = self._user_dir / "data" / "exports"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cache_dir(self) -> Path:
        p = self._user_dir / "data" / "cache"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def knowledge_db(self) -> Path:
        return self.data_dir / "knowledge.db"

    @property
    def preferences(self) -> Path:
        return self.data_dir / "preferences.json"

    @property
    def session(self) -> Path:
        return self.data_dir / "session.json"

    @property
    def main_log(self) -> Path:
        return self.logs_dir / "riskpulse.log"

    @property
    def error_log(self) -> Path:
        return self.logs_dir / "errors.log"

    # ── Resources packagees (locales, etc.) ──

    def resource(self, *parts: str) -> Path:
        """
        Resolve un chemin RELATIF au dossier d'app (locales, ui_qt, etc.).
        Utilise pour les .qm, icons et autres assets read-only.
        """
        return self._app_dir.joinpath(*parts)


paths = _Paths()
