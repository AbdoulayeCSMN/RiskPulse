"""
RiskPulse API — Authentification par cle API.
Cle generee au premier lancement, persistee dans data/preferences.json.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException, status

try:
    from utils.paths import paths
    PREFS_PATH = paths.preferences
except Exception:
    PREFS_PATH = Path("data") / "preferences.json"


def _load_prefs() -> dict:
    if PREFS_PATH.exists():
        try:
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_prefs(d: dict):
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PREFS_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def get_or_create_api_key() -> str:
    """
    Retourne la cle API existante ou en cree une au premier appel.
    Format : 'rpk_' + 32 hex chars.
    """
    prefs = _load_prefs()
    key = prefs.get("api_key")
    if not key:
        key = "rpk_" + secrets.token_hex(16)
        prefs["api_key"] = key
        _save_prefs(prefs)
    return key


def regenerate_api_key() -> str:
    """Force une nouvelle cle (les anciens clients seront deconnectes)."""
    prefs = _load_prefs()
    key = "rpk_" + secrets.token_hex(16)
    prefs["api_key"] = key
    _save_prefs(prefs)
    return key


# ─────────────────────────────────────────────
#  Dependency FastAPI
# ─────────────────────────────────────────────

def require_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """
    Dependency injecte dans toutes les routes protegees.
    Verifie l'en-tete X-API-Key.
    """
    expected = get_or_create_api_key()
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
    return True
