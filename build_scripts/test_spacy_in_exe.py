"""Lance l'exe avec un script de diagnostic spaCy."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE_DIR = ROOT / "dist" / "RiskPulse"

# Cree un script Python qui sera execute par RiskPulse... non,
# l'exe est compile, on ne peut pas injecter de code.
# A la place : on inspecte le bundle.

print(f"Bundle dir : {EXE_DIR}")
print(f"_internal contents : {[p.name for p in (EXE_DIR / '_internal').iterdir() if 'core' in p.name or 'spacy' in p.name]}")

import sys as _sys
sys.path.insert(0, str(EXE_DIR / "_internal"))
print(f"sys.path[0] : {sys.path[0]}")

try:
    import fr_core_news_sm
    print(f"OK : fr_core_news_sm imported from {fr_core_news_sm.__file__}")
    nlp = fr_core_news_sm.load()
    print(f"OK : model loaded, pipeline = {nlp.pipe_names}")
except Exception as e:
    print(f"FAIL : {type(e).__name__}: {e}")
