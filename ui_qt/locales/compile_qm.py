"""Compile tous les .ts en .qm via pyside6-lrelease."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
LANGS = ["fr", "en", "ar", "it", "es"]

for lang in LANGS:
    ts = HERE / f"riskpulse_{lang}.ts"
    qm = HERE / f"riskpulse_{lang}.qm"
    if not ts.exists():
        print(f"Skip: {ts.name} not found")
        continue
    print(f"Compiling {ts.name} -> {qm.name}")
    r = subprocess.run(
        ["pyside6-lrelease", str(ts), "-qm", str(qm)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"  ERROR: {r.stderr}")
    else:
        # Affiche la ligne 'Generated <N> translations'
        for line in r.stdout.splitlines():
            if "translation" in line.lower() or "generated" in line.lower():
                print(f"  {line}")

print("\nDone.")
