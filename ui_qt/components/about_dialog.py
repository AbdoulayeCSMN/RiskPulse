"""About dialog : credits, version, licence."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)


class AboutDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setFixedSize(520, 360)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("about")
        container.setStyleSheet(
            "QFrame#about {"
            "  background-color: #0e0e11;"
            "  border: 1px solid #27272a;"
            "  border-radius: 8px;"
            "}"
        )
        outer.addWidget(container)

        inner = QVBoxLayout(container)
        inner.setContentsMargins(40, 36, 40, 28)
        inner.setSpacing(0)

        # Logo
        logo = QLabel("RISKPULSE")
        logo.setStyleSheet(
            "color: #e4e4e7; font-size: 26px; font-weight: 700;"
            "letter-spacing: 2px;"
        )
        inner.addWidget(logo)
        inner.addSpacing(2)

        tag = QLabel("AI-POWERED RISK MAPPING")
        tag.setStyleSheet("color: #52525b; font-size: 9px; letter-spacing: 2px;")
        inner.addWidget(tag)
        inner.addSpacing(28)

        # Description
        desc = QLabel(
            "RiskPulse extracts entities and relations from any text, "
            "builds a weighted knowledge graph, and reveals systemic risks "
            "through AI-powered propagation and counterfactual simulations."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a1a1aa; font-size: 11px; line-height: 1.6;")
        inner.addWidget(desc)
        inner.addSpacing(24)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1c1c20;")
        inner.addWidget(sep)
        inner.addSpacing(16)

        # Metadata
        meta = [
            ("VERSION",   "1.0.0"),
            ("BUILD",     "2026.05"),
            ("AUTHOR",    "C. ABDOULAYE"),
            ("LICENSE",   "Proprietary"),
        ]
        for k, v in meta:
            row = QHBoxLayout()
            kl = QLabel(k)
            kl.setStyleSheet("color: #52525b; font-size: 9px; letter-spacing: 1.5px;")
            kl.setFixedWidth(80)
            row.addWidget(kl)
            vl = QLabel(v)
            vl.setStyleSheet("color: #e4e4e7; font-size: 11px;")
            row.addWidget(vl)
            row.addStretch()
            inner.addLayout(row)
            inner.addSpacing(4)

        inner.addStretch()

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("CLOSE")
        close_btn.setMinimumWidth(100)
        close_btn.setMinimumHeight(32)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        inner.addLayout(btn_row)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
