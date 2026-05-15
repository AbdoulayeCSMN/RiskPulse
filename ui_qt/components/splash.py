"""Splash screen au demarrage — premiere impression premium."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QProgressBar
)


class SplashScreen(QWidget):
    """Fenetre sans bordure affichee au demarrage, fade-out automatique."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.SplashScreen | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(460, 280)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("splash")
        container.setStyleSheet(
            "QFrame#splash {"
            "  background-color: #0a0a0c;"
            "  border: 1px solid #27272a;"
            "  border-radius: 8px;"
            "}"
        )
        outer.addWidget(container)

        inner = QVBoxLayout(container)
        inner.setContentsMargins(40, 40, 40, 30)
        inner.setSpacing(0)
        inner.setAlignment(Qt.AlignCenter)

        # Bloc centre
        center = QVBoxLayout()
        center.setSpacing(8)
        center.setAlignment(Qt.AlignCenter)

        logo = QLabel("RISKPULSE")
        logo.setStyleSheet(
            "color: #e4e4e7; font-size: 28px; font-weight: 700;"
            "letter-spacing: 4px;"
        )
        logo.setAlignment(Qt.AlignCenter)
        center.addWidget(logo)

        tag = QLabel("AI-POWERED RISK MAPPING")
        tag.setStyleSheet(
            "color: #52525b; font-size: 9px; letter-spacing: 3px;"
        )
        tag.setAlignment(Qt.AlignCenter)
        center.addWidget(tag)

        inner.addStretch()
        inner.addLayout(center)
        inner.addStretch()

        # Progress (mince)
        self._status = QLabel("INITIALIZING")
        self._status.setStyleSheet(
            "color: #3f3f46; font-size: 9px; letter-spacing: 2px;"
        )
        self._status.setAlignment(Qt.AlignCenter)
        inner.addWidget(self._status)

    def set_status(self, text: str):
        self._status.setText(text.upper())
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.processEvents()
