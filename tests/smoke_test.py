"""
Smoke test production : valide que tout boot et que les modules cles repondent.

Sortie 0 = OK, 1 = au moins une erreur.

Usage :
    python -m tests.smoke_test
"""

import sys
import os
import traceback
from pathlib import Path

# Ajoute la racine au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RESULTS = []


def check(name: str, fn):
    """Execute une verification et enregistre OK/FAIL."""
    try:
        fn()
        RESULTS.append(("OK  ", name, ""))
        return True
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        RESULTS.append(("FAIL", name, msg))
        return False


# ── Tests ─────────────────────────────────

def _t_imports_core():
    import controller.risk_controller
    import engines.nlp_engine
    import engines.risk_intelligence
    import engines.predictive_engine
    import engines.banking_pack
    import services.knowledge_base
    import services.auth_service
    import services.permissions
    import services.watchlist
    import services.enrichment

def _t_imports_ui():
    import ui_qt.i18n
    import ui_qt.theme
    import ui_qt.main_window
    import ui_qt.views.welcome_view
    import ui_qt.views.analyse_view
    import ui_qt.views.intelligence_view
    import ui_qt.views.knowledge_view
    import ui_qt.views.monitoring_view
    import ui_qt.views.banking_view
    import ui_qt.views.predictive_view
    import ui_qt.views.api_view
    import ui_qt.views.users_view
    import ui_qt.views.parametres_view

def _t_imports_api():
    import api.server
    import api.auth
    import api.sdk.client
    import api.routes.health
    import api.routes.analyze
    import api.routes.knowledge
    import api.routes.monitoring
    import api.routes.predictive

def _t_utils():
    from utils import paths, setup_logging, get_logger
    setup_logging()
    log = get_logger("smoke")
    log.info("Logger OK")
    assert paths.data_dir.exists()
    assert paths.logs_dir.exists()

def _t_kb():
    from services.knowledge_base import get_kb
    kb = get_kb()
    stats = kb.stats()
    assert "n_entities" in stats
    assert "n_analyses" in stats

def _t_auth():
    from services.auth_service import get_auth
    auth = get_auth()
    users = auth.list_users()
    # Au minimum, l'admin bootstrap doit exister
    assert any(u.username == "admin" for u in users), "admin missing"

def _t_permissions():
    from services.permissions import PERM, ROLE_PERMS, role_has
    assert role_has("admin", PERM.MANAGE_USERS)
    assert not role_has("viewer", PERM.MANAGE_USERS)
    assert role_has("analyst", PERM.RUN_ANALYSIS)

def _t_i18n_files():
    from utils.paths import paths
    locales = paths.resource("ui_qt", "locales")
    qms = list(locales.glob("*.qm"))
    assert len(qms) >= 4, f"Expected 4+ .qm files, got {len(qms)}"

def _t_engines_pipeline():
    """Pipeline NLP complet sur un texte court : doit retourner des entites."""
    from controller.risk_controller import RiskController
    ctrl = RiskController(language="fr")
    result = ctrl.analyze_text(
        "WafaCash et CashPlus sont les leaders du transfert d'argent au Maroc. "
        "Bank Al-Maghrib regule l'ensemble des operateurs FinTech."
    )
    assert "error" not in result, result.get("error")
    assert result["stats"]["nb_entities"] >= 2

def _t_risk_intel():
    """Risk Intelligence doit produire des profils + crisis matches."""
    from controller.risk_controller import RiskController
    ctrl = RiskController(language="fr")
    result = ctrl.analyze_text(
        "La Banque Centrale a annonce une baisse des taux suite aux difficultes "
        "du Fonds Alpha Capital. InvestCorp Maroc collabore avec TechVentures SA."
    )
    ri = result.get("risk_intel", {})
    assert "profiles" in ri
    assert "crisis_matches" in ri
    assert len(ri["crisis_matches"]) > 0

def _t_pyvis():
    """PyVis genere un HTML inline complet."""
    from pyvis.network import Network
    import networkx as nx
    G = nx.Graph(); G.add_edge("A", "B"); G.add_edge("B", "C")
    net = Network(cdn_resources="in_line", bgcolor="#0a0a0c", font_color="#e4e4e7")
    net.from_nx(G)
    html = net.generate_html(notebook=False)
    assert "vis-network" in html and len(html) > 100_000

def _t_api_import():
    from api.server import create_app
    app = create_app()
    routes = [r.path for r in app.routes]
    assert "/v1/health" in routes
    assert "/v1/analyze" in routes


# ── Runner ─────────────────────────────────

CHECKS = [
    ("Core imports",        _t_imports_core),
    ("UI imports",          _t_imports_ui),
    ("API imports",         _t_imports_api),
    ("Utils (paths/log)",   _t_utils),
    ("Knowledge base",      _t_kb),
    ("Auth bootstrap",      _t_auth),
    ("Permissions",         _t_permissions),
    ("i18n .qm present",    _t_i18n_files),
    ("NLP pipeline",        _t_engines_pipeline),
    ("Risk intelligence",   _t_risk_intel),
    ("PyVis offline",       _t_pyvis),
    ("API factory",         _t_api_import),
]


def main():
    print("=" * 70)
    print("  RiskPulse smoke test")
    print("=" * 70)
    for name, fn in CHECKS:
        check(name, fn)

    print()
    n_ok = sum(1 for s, _, _ in RESULTS if s == "OK  ")
    n_fail = sum(1 for s, _, _ in RESULTS if s == "FAIL")
    for status, name, msg in RESULTS:
        line = f"  [{status}] {name}"
        if msg:
            line += f"  ->  {msg}"
        print(line)
    print()
    print(f"  Total : {n_ok}/{len(CHECKS)} passed")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
