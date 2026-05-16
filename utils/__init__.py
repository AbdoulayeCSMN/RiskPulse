"""Utilitaires transverses."""
from .paths    import paths
from .logger   import setup_logging, get_logger
from .errors   import install_exception_hooks

__all__ = ["paths", "setup_logging", "get_logger", "install_exception_hooks"]
