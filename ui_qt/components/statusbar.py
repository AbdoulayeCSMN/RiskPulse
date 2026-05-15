"""Barre de statut en bas de la fenetre."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import QTimer


class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusbar")
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        self._status = QLabel("Ready")
        self._status.setProperty("class", "caption")
        layout.addWidget(self._status)

        layout.addStretch()

        self._progress = QProgressBar()
        self._progress.setFixedWidth(180)
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.hide()
        layout.addWidget(self._progress)

        self._right = QLabel("")
        self._right.setProperty("class", "caption")
        layout.addWidget(self._right)

        # Timer pour masquer la barre de progression automatiquement
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._progress.hide)

    def set_status(self, message: str, level: str = "info"):
        colors = {
            "info":    "text_muted",
            "success": "success",
            "warning": "warning",
            "error":   "error",
        }
        # Le style est applique via le QSS — on garde simple
        self._status.setText(message)

    def set_progress(self, value: float):
        """value entre 0 et 1."""
        self._progress.show()
        self._progress.setValue(int(max(0, min(1, value)) * 100))
        if value >= 1.0:
            self._hide_timer.start(800)

    def set_right(self, text: str):
        self._right.setText(text)
