"""
Runtime hook injecte au demarrage de l'exe.

Sert a :
  - Exposer les modeles spaCy bundled (qui sont au top-level du bundle)
  - Eteindre certaines verbosites par defaut
"""

import os
import sys


def _setup_frozen_paths():
    """Ajoute les dossiers ou se trouvent les modeles spaCy bundles."""
    if not getattr(sys, "frozen", False):
        return

    # PyInstaller onefolder : MEIPASS = dossier _internal/
    # Onefile : MEIPASS = repertoire temporaire extrait
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(meipass)

    # Fallback : a cote de l'exe (cas du onefolder)
    exe_dir = os.path.dirname(sys.executable)
    candidates.append(exe_dir)
    candidates.append(os.path.join(exe_dir, "_internal"))

    for c in candidates:
        if c and os.path.isdir(c) and c not in sys.path:
            sys.path.insert(0, c)


_setup_frozen_paths()

# Reduit la verbosite spaCy / thinc au demarrage
os.environ.setdefault("SPACY_WARNING_IGNORE", "W008,W007")
