"""
Toast notifications non bloquantes.
Style premium : apparait en bas-droite, disparait apres 4s, anime.
"""

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, Property
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtGui import QPainter, QColor


class Toast(QFrame):
    """Une notification toast individuelle."""

    LEVELS = {
        "info":    ("INFO",    "#9caec1"),
        "success": ("DONE",    "#84cc9e"),
        "warning": ("WARN",    "#e3c08e"),
        "error":   ("ERROR",   "#e8a0a0"),
    }

    def __init__(self, parent: QWidget, message: str, level: str = "info",
                 duration_ms: int = 4000):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setFixedWidth(360)

        tag_text, color = self.LEVELS.get(level, self.LEVELS["info"])

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        tag = QLabel(tag_text)
        tag.setStyleSheet(
            f"color: {color}; font-weight: 600; letter-spacing: 1px; font-size: 9px;"
        )
        tag.setFixedWidth(46)
        lay.addWidget(tag)

        msg = QLabel(message)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #e4e4e7; font-size: 11px;")
        lay.addWidget(msg, 1)

        self.setStyleSheet(
            "QFrame#toast {"
            "  background-color: #16161a;"
            "  border: 1px solid #27272a;"
            "  border-radius: 4px;"
            "}"
        )

        # Auto-dismiss
        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_out(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(220)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.deleteLater)
        self.anim.start()


class ToastManager:
    """Gestionnaire singleton de toasts empiles."""

    _instance: "ToastManager | None" = None

    def __init__(self):
        self._parent: QWidget | None = None
        self._toasts: list[Toast] = []
        ToastManager._instance = self

    @classmethod
    def instance(cls) -> "ToastManager":
        if cls._instance is None:
            cls._instance = ToastManager()
        return cls._instance

    def install(self, parent: QWidget):
        self._parent = parent

    def show(self, message: str, level: str = "info", duration: int = 4000):
        if not self._parent:
            return
        toast = Toast(self._parent, message, level, duration)
        toast.show()
        self._toasts.append(toast)
        toast.destroyed.connect(lambda *_: self._remove(toast))
        self._reposition()

    def _remove(self, t: Toast):
        if t in self._toasts:
            self._toasts.remove(t)
        self._reposition()

    def _reposition(self):
        if not self._parent:
            return
        # Empile en bas-droite
        margin = 24
        y = self._parent.height() - margin
        for toast in reversed(self._toasts):
            try:
                toast.adjustSize()
                w = toast.width()
                h = toast.height()
                x = self._parent.width() - w - margin
                y -= h
                toast.move(x, y)
                toast.raise_()
                y -= 8  # gap entre toasts
            except RuntimeError:
                # Toast deleteLater'd
                pass
