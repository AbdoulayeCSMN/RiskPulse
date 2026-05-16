"""
Met a jour les fichiers .ts en extrayant les tr() de tous les sources.

Wrap autour de pyside6-lupdate. Sans dependance au format .pro deprecie.
"""

import subprocess
import sys
from pathlib import Path

LANGS = ["fr", "en", "ar", "it", "es"]

HERE = Path(__file__).parent
ROOT_UI = HERE.parent

# Tous les fichiers source qui contiennent des tr(...)
SOURCES = [
    "i18n.py",
    "main_window.py",
    "components/sidebar.py",
    "components/topbar.py",
    "components/statusbar.py",
    "components/card.py",
    "components/toast.py",
    "components/command_palette.py",
    "components/about_dialog.py",
    "components/splash.py",
    "components/login_dialog.py",
    "components/user_badge.py",
    "views/_base.py",
    "views/welcome_view.py",
    "views/analyse_view.py",
    "views/intelligence_view.py",
    "views/knowledge_view.py",
    "views/monitoring_view.py",
    "views/banking_view.py",
    "views/predictive_view.py",
    "views/insights_view.py",
    "views/api_view.py",
    "views/users_view.py",
    "views/propagation_view.py",
    "views/comparaison_view.py",
    "views/contrefactuel_view.py",
    "views/traduction_view.py",
    "views/dashboard_view.py",
    "views/parametres_view.py",
]

# Filtre les fichiers existants
existing = []
missing = []
for s in SOURCES:
    p = ROOT_UI / s
    if p.exists():
        existing.append(str(p))
    else:
        missing.append(s)

if missing:
    print(f"WARN missing source files: {missing}")

print(f"Source files          : {len(existing)}")

for lang in LANGS:
    ts = HERE / f"riskpulse_{lang}.ts"
    print(f"\n=== Updating riskpulse_{lang}.ts ===")
    cmd = ["pyside6-lupdate"] + existing + ["-ts", str(ts), "-no-obsolete"]
    r = subprocess.run(cmd, capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"  ERROR: {r.stderr[-400:]}")
        continue
    # Affiche les lignes informatives
    for line in (r.stdout + r.stderr).splitlines():
        if any(k in line.lower() for k in (
            "found", "kept", "removed", "updating", "obsolete", "new")):
            print(f"  {line}")

print("\nDone.")
