"""
Command Palette — Ctrl+K
==========================
Inspire Linear / Raycast : recherche universelle dans l'app.
Liste filtrable de commandes (navigation, actions, theme, langue).
"""

from dataclasses import dataclass
from typing import Callable, List
from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QHBoxLayout, QWidget,
)


@dataclass
class Command:
    id: str
    name: str
    category: str
    shortcut: str
    action: Callable[[], None]


class CommandPalette(QDialog):
    """Dialog modale plein-ecran flou avec recherche."""

    def __init__(self, commands: List[Command], parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedWidth(600)
        self._all_commands = commands
        self._filtered = commands
        self._build()
        self._refresh_list()

    def _build(self):
        # Frame container avec coins arrondis
        from PySide6.QtWidgets import QFrame
        container = QFrame()
        container.setObjectName("palette")
        container.setStyleSheet(
            "QFrame#palette {"
            "  background-color: #0e0e11;"
            "  border: 1px solid #27272a;"
            "  border-radius: 8px;"
            "}"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        inner = QVBoxLayout(container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # Search bar
        self._input = QLineEdit()
        self._input.setPlaceholderText("Search commands...")
        self._input.setStyleSheet(
            "QLineEdit {"
            "  background-color: transparent;"
            "  border: none;"
            "  border-bottom: 1px solid #1c1c20;"
            "  color: #e4e4e7;"
            "  padding: 18px 22px;"
            "  font-size: 13px;"
            "}"
        )
        self._input.textChanged.connect(self._filter)
        inner.addWidget(self._input)

        # List
        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget {"
            "  background-color: transparent;"
            "  border: none;"
            "  outline: none;"
            "  padding: 6px;"
            "}"
            "QListWidget::item {"
            "  padding: 10px 14px;"
            "  border-radius: 4px;"
            "  color: #a1a1aa;"
            "}"
            "QListWidget::item:selected {"
            "  background-color: #1a1a1f;"
            "  color: #e4e4e7;"
            "}"
            "QListWidget::item:hover {"
            "  background-color: #16161a;"
            "}"
        )
        self._list.itemActivated.connect(self._run_selected)
        inner.addWidget(self._list)

        # Footer hint
        footer = QLabel("  ↵  RUN     ESC  CLOSE     ↑↓  NAVIGATE")
        footer.setStyleSheet(
            "color: #52525b; font-size: 9px; letter-spacing: 1px;"
            "padding: 10px 18px; border-top: 1px solid #1c1c20;"
        )
        inner.addWidget(footer)

    def _filter(self, text: str):
        text = text.lower().strip()
        if not text:
            self._filtered = self._all_commands
        else:
            self._filtered = [
                c for c in self._all_commands
                if text in c.name.lower() or text in c.category.lower()
            ]
        self._refresh_list()

    def _refresh_list(self):
        self._list.clear()
        for cmd in self._filtered:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, cmd)

            widget = QWidget()
            row = QHBoxLayout(widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)

            cat = QLabel(cmd.category.upper())
            cat.setStyleSheet("color: #52525b; font-size: 9px; letter-spacing: 1px;")
            cat.setFixedWidth(80)
            row.addWidget(cat)

            name = QLabel(cmd.name)
            name.setStyleSheet("color: inherit;")
            row.addWidget(name, 1)

            if cmd.shortcut:
                sc = QLabel(cmd.shortcut)
                sc.setStyleSheet(
                    "color: #52525b; font-size: 10px;"
                    "background-color: #16161a; padding: 2px 6px;"
                    "border-radius: 3px; border: 1px solid #27272a;"
                )
                row.addWidget(sc)

            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _run_selected(self, item: QListWidgetItem):
        cmd: Command = item.data(Qt.UserRole)
        self.accept()
        try:
            cmd.action()
        except Exception:
            pass

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        if event.key() in (Qt.Key_Down, Qt.Key_Up):
            self._list.keyPressEvent(event)
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            item = self._list.currentItem()
            if item:
                self._run_selected(item)
            return
        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        # Center on parent
        if self.parent():
            pg = self.parent().geometry()
            self.move(pg.center().x() - self.width() // 2,
                      pg.top() + 120)
        self._input.setFocus()
