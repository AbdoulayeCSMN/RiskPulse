"""
User badge — affiche dans la topbar : nom + role + menu Logout.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QAction
from PySide6.QtWidgets import QPushButton, QMenu


ROLE_COLORS = {
    "admin":   "#e3c08e",
    "analyst": "#9caec1",
    "viewer":  "#84cc9e",
}


class UserBadge(QPushButton):
    """Bouton ghost qui affiche l'utilisateur + menu deroulant."""

    logout_requested = Signal()

    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self._user = user
        self.setProperty("variant", "ghost")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(28)
        self.setMinimumWidth(140)
        self._build_menu()
        self.set_user(user)
        self.clicked.connect(self._show_menu)

    def _build_menu(self):
        self._menu = QMenu(self)
        self._menu.setStyleSheet(
            "QMenu { background-color: #0e0e11; border: 1px solid #27272a;"
            "  border-radius: 6px; padding: 4px; color: #e4e4e7;"
            "  font-family: 'JetBrains Mono'; font-size: 10px; }"
            "QMenu::item { padding: 6px 18px; border-radius: 3px; }"
            "QMenu::item:selected { background-color: #16161a; }"
            "QMenu::separator { height: 1px; background: #1c1c20; margin: 4px 0; }"
        )

        act_logout = QAction("Sign out", self)
        act_logout.triggered.connect(self.logout_requested.emit)
        self._menu.addAction(act_logout)

    def set_user(self, user):
        self._user = user
        if not user:
            self.setText("Not signed in")
            return
        role_color = ROLE_COLORS.get(user.role, "#9ca3af")
        # Affichage compact : NOM  •  ROLE
        self.setText(f" {user.username.upper()}  ·  {user.role.upper()} ")
        # Couleur du badge selon role
        self.setStyleSheet(
            "QPushButton {"
            "  background-color: transparent;"
            "  border: 1px solid #27272a;"
            "  border-radius: 4px;"
            "  padding: 4px 10px;"
            f"  color: {role_color};"
            "  font-size: 10px; font-weight: 600; letter-spacing: 1px;"
            "}"
            "QPushButton:hover { background-color: #16161a; }"
        )

    def _show_menu(self):
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self._menu.exec(pos)
