"""Sidebar minimaliste : indicateur actif = ligne fine a gauche."""

from dataclasses import dataclass
from typing import List
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy, QWidget
)
from PySide6.QtCore import Signal, Qt


@dataclass
class NavItem:
    id: str
    label: str


class Sidebar(QFrame):
    """Sidebar avec navigation. Emet `navigate(view_id)` au clic."""

    navigate = Signal(str)

    def __init__(self, items: List[NavItem], parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 24, 0, 16)
        layout.setSpacing(2)

        # Section header
        self._section_lbl = QLabel("  NAVIGATION")
        self._section_lbl.setProperty("class", "caption")
        self._section_lbl.setContentsMargins(18, 0, 18, 14)
        layout.addWidget(self._section_lbl)

        # Items
        self._items = items
        self._buttons: dict[str, QPushButton] = {}
        self._active: str | None = None

        for item in items:
            btn = QPushButton(item.label)
            btn.setProperty("role", "nav")
            btn.setProperty("active", "false")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, vid=item.id: self._on_click(vid))
            layout.addWidget(btn)
            self._buttons[item.id] = btn

        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Footer discret
        self._footer = QLabel("")
        self._footer.setProperty("class", "caption")
        self._footer.setContentsMargins(18, 0, 18, 0)
        layout.addWidget(self._footer)

    def set_footer(self, text: str):
        self._footer.setText(text)

    def set_section_label(self, text: str):
        self._section_lbl.setText("  " + text)

    def update_labels(self, labels: dict[str, str]):
        for item in self._items:
            new = labels.get(item.id, item.label)
            item.label = new
            # Conserve un badge eventuellement deja affiche
            existing = self._buttons[item.id].text()
            if "  ·  " in existing:
                _, badge = existing.rsplit("  ·  ", 1)
                self._buttons[item.id].setText(f"{new}  ·  {badge}")
            else:
                self._buttons[item.id].setText(new)

    def set_badge(self, item_id: str, badge_text: str):
        """Affiche/masque un badge a droite de l'item (ex. compteur d'alertes)."""
        btn = self._buttons.get(item_id)
        if not btn:
            return
        for it in self._items:
            if it.id == item_id:
                if badge_text:
                    btn.setText(f"{it.label}  ·  {badge_text}")
                else:
                    btn.setText(it.label)
                break

    def _on_click(self, view_id: str):
        self.set_active(view_id)
        self.navigate.emit(view_id)

    def set_active(self, view_id: str):
        for vid, btn in self._buttons.items():
            is_active = vid == view_id
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._active = view_id
