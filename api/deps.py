"""Dependencies injectees dans les routes — accessor au RiskController courant."""

from typing import Optional

_controller_ref: Optional[object] = None


def set_controller(controller):
    """Appele depuis le serveur au demarrage."""
    global _controller_ref
    _controller_ref = controller


def get_controller():
    """Retourne le RiskController partage. Cree-en un par defaut si manquant."""
    global _controller_ref
    if _controller_ref is None:
        from controller.risk_controller import RiskController
        _controller_ref = RiskController(language="fr")
    return _controller_ref
