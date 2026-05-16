"""
Logging production-ready.

- Console minimaliste (INFO+)
- Fichier principal data/logs/riskpulse.log (rotation 5MB, 5 backups)
- Fichier d'erreurs separate data/logs/errors.log (rotation idem)
- Format compact, lisible, machine-friendly
- Mutes les libs trop verbeuses (urllib3, networkx, etc.)
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from typing import Optional

from .paths import paths


LOG_FORMAT = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Libs externes a calmer
NOISY_LIBS = (
    "urllib3", "PIL", "matplotlib", "fontTools",
    "spacy", "thinc", "numexpr",
)

_initialized = False


def setup_logging(level: int = logging.INFO,
                   console: bool = True) -> None:
    """
    A appeler une seule fois au demarrage. Idempotent.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)   # filtrage fait par handler
    # Vide les handlers preexistants (basicConfig, etc.)
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # ── Console : compact, niveau INFO+ ──
    if console:
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(level)
        sh.setFormatter(fmt)
        root.addHandler(sh)

    # ── Fichier principal : rotation 5MB x 5 ──
    try:
        fh = logging.handlers.RotatingFileHandler(
            paths.main_log, maxBytes=5_000_000, backupCount=5,
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception as e:
        sys.stderr.write(f"Cannot create main log file: {e}\n")

    # ── Fichier erreurs : rotation idem, niveau ERROR+ ──
    try:
        eh = logging.handlers.RotatingFileHandler(
            paths.error_log, maxBytes=2_000_000, backupCount=3,
            encoding="utf-8",
        )
        eh.setLevel(logging.ERROR)
        eh.setFormatter(fmt)
        root.addHandler(eh)
    except Exception:
        pass

    # ── Calme les libs verbeuses ──
    for name in NOISY_LIBS:
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger("riskpulse").info(
        f"Logging initialized. Logs at: {paths.logs_dir}"
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Helper. Prefixe automatiquement 'riskpulse.' si pas deja la."""
    if name and not name.startswith("riskpulse"):
        name = f"riskpulse.{name}"
    return logging.getLogger(name or "riskpulse")
