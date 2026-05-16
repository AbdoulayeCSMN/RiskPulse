"""
Permissions RBAC — qui a le droit de faire quoi.

Trois roles :
  - admin   : tout
  - analyst : analyser, exporter, gerer watchlist/sources, run monitoring
  - viewer  : lecture seule

Utilisation :
  from services.permissions import can, PERM
  if can(PERM.RUN_ANALYSIS):
      ...
  if can(PERM.MANAGE_USERS):
      # admin uniquement
"""

from __future__ import annotations
from typing import Optional


# ─────────────────────────────────────────────
#  PERMISSIONS DEFINITIONS
# ─────────────────────────────────────────────

class PERM:
    # Lecture
    VIEW_ANALYSES     = "view_analyses"
    VIEW_KB           = "view_kb"
    VIEW_ALERTS       = "view_alerts"
    VIEW_DASHBOARD    = "view_dashboard"
    VIEW_INTELLIGENCE = "view_intelligence"

    # Ecriture
    RUN_ANALYSIS      = "run_analysis"
    RUN_DEMO          = "run_demo"
    EXPORT_DATA       = "export_data"
    MANAGE_WATCHLIST  = "manage_watchlist"
    MANAGE_SOURCES    = "manage_sources"
    RUN_MONITORING    = "run_monitoring"
    RUN_PREDICTIVE    = "run_predictive"
    ENRICH_ENTITIES   = "enrich_entities"
    TRANSLATE         = "translate"

    # Admin
    MANAGE_USERS      = "manage_users"
    MANAGE_API        = "manage_api"
    VIEW_AUDIT        = "view_audit"
    CLEAR_KB          = "clear_kb"
    DELETE_ANALYSES   = "delete_analyses"


# ─────────────────────────────────────────────
#  MAPPING role -> permissions
# ─────────────────────────────────────────────

ROLE_PERMS = {
    "viewer": {
        PERM.VIEW_ANALYSES, PERM.VIEW_KB, PERM.VIEW_ALERTS,
        PERM.VIEW_DASHBOARD, PERM.VIEW_INTELLIGENCE,
    },
    "analyst": {
        # Hereditage des viewer
        PERM.VIEW_ANALYSES, PERM.VIEW_KB, PERM.VIEW_ALERTS,
        PERM.VIEW_DASHBOARD, PERM.VIEW_INTELLIGENCE,
        # Plus
        PERM.RUN_ANALYSIS, PERM.RUN_DEMO,
        PERM.EXPORT_DATA, PERM.MANAGE_WATCHLIST, PERM.MANAGE_SOURCES,
        PERM.RUN_MONITORING, PERM.RUN_PREDICTIVE,
        PERM.ENRICH_ENTITIES, PERM.TRANSLATE,
    },
    "admin": {
        # Tout
        PERM.VIEW_ANALYSES, PERM.VIEW_KB, PERM.VIEW_ALERTS,
        PERM.VIEW_DASHBOARD, PERM.VIEW_INTELLIGENCE,
        PERM.RUN_ANALYSIS, PERM.RUN_DEMO,
        PERM.EXPORT_DATA, PERM.MANAGE_WATCHLIST, PERM.MANAGE_SOURCES,
        PERM.RUN_MONITORING, PERM.RUN_PREDICTIVE,
        PERM.ENRICH_ENTITIES, PERM.TRANSLATE,
        PERM.MANAGE_USERS, PERM.MANAGE_API,
        PERM.VIEW_AUDIT, PERM.CLEAR_KB, PERM.DELETE_ANALYSES,
    },
}


# Lib readable des permissions pour l'UI
PERM_LABELS = {
    PERM.VIEW_ANALYSES:     "View analyses",
    PERM.VIEW_KB:           "Browse knowledge base",
    PERM.VIEW_ALERTS:       "View alerts",
    PERM.VIEW_DASHBOARD:    "View dashboard",
    PERM.VIEW_INTELLIGENCE: "View risk intelligence",
    PERM.RUN_ANALYSIS:      "Run new analysis",
    PERM.RUN_DEMO:          "Run demo scenarios",
    PERM.EXPORT_DATA:       "Export reports (PDF/CSV/JSON)",
    PERM.MANAGE_WATCHLIST:  "Manage watchlist",
    PERM.MANAGE_SOURCES:    "Manage monitoring sources",
    PERM.RUN_MONITORING:    "Trigger monitoring cycles",
    PERM.RUN_PREDICTIVE:    "Run forecasts & Monte Carlo",
    PERM.ENRICH_ENTITIES:   "Enrich entities (Wikidata)",
    PERM.TRANSLATE:         "Use translation module",
    PERM.MANAGE_USERS:      "Manage users",
    PERM.MANAGE_API:        "Manage API server & keys",
    PERM.VIEW_AUDIT:        "View audit log",
    PERM.CLEAR_KB:          "Clear knowledge base",
    PERM.DELETE_ANALYSES:   "Delete analyses",
}


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def role_has(role: str, perm: str) -> bool:
    return perm in ROLE_PERMS.get(role, set())


def can(perm: str, user=None) -> bool:
    """
    Verifie si l'utilisateur courant (ou celui passe) a la permission.
    Si pas de user connecte : False (par defaut securitaire).
    """
    if user is None:
        from services.auth_service import get_auth
        user = get_auth().current_user
    if not user or not user.active:
        return False
    return role_has(user.role, perm)


def require(perm: str):
    """
    Decorator pour functions UI. Si l'utilisateur n'a pas le droit,
    leve une PermissionError au lieu d'executer.
    """
    def deco(fn):
        def wrapper(*args, **kwargs):
            if not can(perm):
                raise PermissionError(
                    f"Permission denied: {PERM_LABELS.get(perm, perm)}"
                )
            return fn(*args, **kwargs)
        return wrapper
    return deco
