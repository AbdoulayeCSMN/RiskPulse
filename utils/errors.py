"""
Error handling production-ready.

- Hook global Python  (sys.excepthook)
- Hook Qt              (Qt.qInstallMessageHandler) — masque les warnings benins
- Hook threading       (threading.excepthook)
- Wrapper context manager `safely(...)`

Le but : aucune stack trace ne doit etre visible a l'utilisateur final.
"""

from __future__ import annotations

import logging
import sys
import threading
import traceback
from contextlib import contextmanager
from typing import Callable, Optional

logger = logging.getLogger("riskpulse.errors")

# Reference vers MainWindow pour pouvoir afficher un toast si dispo
_main_window_ref = None


def set_main_window(w):
    """Permet aux hooks d'afficher des toasts si la MainWindow existe."""
    global _main_window_ref
    _main_window_ref = w


def _show_toast(message: str, level: str = "error"):
    """Tente d'afficher un toast si la MainWindow est dispo."""
    if _main_window_ref is None:
        return
    try:
        _main_window_ref.toast(message, level)
    except Exception:
        pass


# ─────────────────────────────────────────────
#  Hook : Python uncaught
# ─────────────────────────────────────────────

def _python_excepthook(exc_type, exc_value, tb):
    # Permet de garder Ctrl+C
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, tb)
        return
    msg = "".join(traceback.format_exception(exc_type, exc_value, tb))
    logger.error("Uncaught exception:\n%s", msg)
    try:
        from services.telemetry import get_telemetry
        get_telemetry().record_crash(exc_type, exc_value, tb, thread_name="main")
    except Exception:
        pass
    _show_toast(f"Internal error: {exc_value}", "error")


# ─────────────────────────────────────────────
#  Hook : threading
# ─────────────────────────────────────────────

def _thread_excepthook(args):
    if issubclass(args.exc_type, KeyboardInterrupt):
        return
    msg = "".join(traceback.format_exception(args.exc_type, args.exc_value,
                                              args.exc_traceback))
    logger.error("Thread '%s' crashed:\n%s", args.thread.name, msg)
    try:
        from services.telemetry import get_telemetry
        get_telemetry().record_crash(args.exc_type, args.exc_value,
                                       args.exc_traceback,
                                       thread_name=args.thread.name)
    except Exception:
        pass
    _show_toast(f"Background task failed: {args.exc_value}", "warning")


# ─────────────────────────────────────────────
#  Hook : Qt messages
# ─────────────────────────────────────────────

def _qt_message_handler(mode, ctx, message):
    # Filtre les bruits connus de Qt
    benign = (
        "QWindowsWindow::setGeometry",
        "QXcbConnection",
        "OpenType support",
        "Font directory",
    )
    if any(b in message for b in benign):
        return
    try:
        from PySide6.QtCore import QtMsgType
        if mode == QtMsgType.QtDebugMsg:
            logger.debug("[Qt] %s", message)
        elif mode == QtMsgType.QtInfoMsg:
            logger.info("[Qt] %s", message)
        elif mode == QtMsgType.QtWarningMsg:
            logger.warning("[Qt] %s", message)
        elif mode == QtMsgType.QtCriticalMsg:
            logger.error("[Qt] %s", message)
        elif mode == QtMsgType.QtFatalMsg:
            logger.critical("[Qt] %s", message)
    except Exception:
        logger.info("[Qt] %s", message)


# ─────────────────────────────────────────────
#  Installation
# ─────────────────────────────────────────────

def install_exception_hooks(install_qt: bool = True):
    """A appeler une fois au demarrage."""
    sys.excepthook = _python_excepthook
    threading.excepthook = _thread_excepthook

    if install_qt:
        try:
            from PySide6.QtCore import qInstallMessageHandler
            qInstallMessageHandler(_qt_message_handler)
        except Exception:
            pass

    logger.debug("Global exception hooks installed.")


# ─────────────────────────────────────────────
#  Context manager pour wrap des operations
# ─────────────────────────────────────────────

@contextmanager
def safely(operation: str = "operation",
            on_error: Optional[Callable[[Exception], None]] = None,
            silent: bool = False):
    """
    Wrappe une operation. Si elle plante, on log + toast + on n'interrompt pas.

        with safely("export PDF"):
            generate_pdf(...)
    """
    try:
        yield
    except Exception as e:
        logger.exception("Failed during %s", operation)
        if on_error:
            try:
                on_error(e)
            except Exception:
                pass
        if not silent:
            _show_toast(f"{operation} failed: {e}", "error")
