"""
Activation dialog : permet a l'utilisateur de coller sa cle de licence
et de l'activer hors-ligne.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QFrame,
)

from ..i18n import tr
from services.licensing import get_license_manager


class ActivationDialog(QDialog):
    """Dialog d'activation de licence. Modal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Activate License"))
        self.setMinimumSize(560, 360)
        self.setModal(True)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        cap = QLabel(tr("LICENSE"))
        cap.setProperty("class", "caption")
        root.addWidget(cap)

        title = QLabel(tr("Activate your RiskPulse license"))
        title.setProperty("class", "h2")
        root.addWidget(title)

        sep = QFrame()
        sep.setObjectName("divider")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        hint = QLabel(tr(
            "Paste the license key you received by email. The key is verified "
            "offline using a cryptographic signature — no internet required."
        ))
        hint.setWordWrap(True)
        hint.setProperty("class", "caption")
        root.addWidget(hint)

        self.key_edit = QPlainTextEdit()
        self.key_edit.setPlaceholderText("eyJ2IjoxLCJwbGFuIjoiUFJP...   .   xxxxx")
        self.key_edit.setMinimumHeight(110)
        root.addWidget(self.key_edit, 1)

        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setProperty("class", "caption")
        root.addWidget(self.status_lbl)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton(tr("Cancel"))
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)

        activate = QPushButton(tr("Activate"))
        activate.setProperty("class", "primary")
        activate.setDefault(True)
        activate.clicked.connect(self._on_activate)
        btns.addWidget(activate)
        root.addLayout(btns)

    def _on_activate(self):
        raw = self.key_edit.toPlainText().strip()
        if not raw:
            self.status_lbl.setText(tr("Please paste a license key."))
            return
        mgr = get_license_manager()
        st = mgr.activate(raw)
        if st.error:
            self.status_lbl.setText(f"✗ {st.error}")
            return
        plan = st.plan.value
        email = st.email or "—"
        self.status_lbl.setText(
            f"✓ {tr('License activated')} — {plan} ({email})"
        )
        # Ferme apres 800ms
        from PySide6.QtCore import QTimer
        QTimer.singleShot(800, self.accept)
