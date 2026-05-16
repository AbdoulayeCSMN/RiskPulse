"""
Login dialog — fenetre modale frameless premium.
S'affiche au demarrage avant la MainWindow.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSizePolicy, QSpacerItem,
)


class LoginDialog(QDialog):
    """
    Login frameless. Retourne le user en cas de succes,
    None si l'utilisateur ferme.
    """

    login_success = Signal(object)

    def __init__(self, auth_service, parent=None):
        super().__init__(parent)
        self.auth = auth_service
        self.user = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(440, 540)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("login")
        container.setStyleSheet(
            "QFrame#login {"
            "  background-color: #0a0a0c;"
            "  border: 1px solid #27272a;"
            "  border-radius: 8px;"
            "}"
        )
        outer.addWidget(container)

        inner = QVBoxLayout(container)
        inner.setContentsMargins(48, 44, 48, 36)
        inner.setSpacing(0)

        # Logo
        logo = QLabel("RISKPULSE")
        logo.setStyleSheet(
            "color: #e4e4e7; font-size: 26px; font-weight: 700;"
            "letter-spacing: 3px;"
        )
        logo.setAlignment(Qt.AlignCenter)
        inner.addWidget(logo)
        inner.addSpacing(4)

        tag = QLabel("AI-POWERED RISK MAPPING")
        tag.setStyleSheet("color: #52525b; font-size: 9px; letter-spacing: 2px;")
        tag.setAlignment(Qt.AlignCenter)
        inner.addWidget(tag)
        inner.addSpacing(36)

        # Caption
        cap = QLabel("SIGN IN")
        cap.setStyleSheet("color: #52525b; font-size: 9px; letter-spacing: 1.5px;")
        inner.addWidget(cap)
        inner.addSpacing(6)

        title = QLabel("Welcome back")
        title.setStyleSheet("color: #e4e4e7; font-size: 18px; font-weight: 600;")
        inner.addWidget(title)
        inner.addSpacing(24)

        # Username
        u_lbl = QLabel("USERNAME")
        u_lbl.setStyleSheet("color: #52525b; font-size: 8px; letter-spacing: 1px;")
        inner.addWidget(u_lbl)
        inner.addSpacing(4)
        self.username = QLineEdit()
        self.username.setPlaceholderText("admin")
        self.username.setMinimumHeight(36)
        self.username.setStyleSheet(
            "QLineEdit { background: #11151b; border: 1px solid #1c1c20;"
            "  border-radius: 4px; padding: 0 12px; color: #e4e4e7;"
            "  font-family: 'JetBrains Mono'; font-size: 12px; }"
            "QLineEdit:focus { border: 1px solid #52525b; }"
        )
        inner.addWidget(self.username)
        inner.addSpacing(16)

        # Password
        p_lbl = QLabel("PASSWORD")
        p_lbl.setStyleSheet("color: #52525b; font-size: 8px; letter-spacing: 1px;")
        inner.addWidget(p_lbl)
        inner.addSpacing(4)
        self.password = QLineEdit()
        self.password.setPlaceholderText("••••")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setMinimumHeight(36)
        self.password.setStyleSheet(self.username.styleSheet())
        inner.addWidget(self.password)
        inner.addSpacing(24)

        # Submit
        self.btn_login = QPushButton("SIGN IN  →")
        self.btn_login.setProperty("variant", "primary")
        self.btn_login.setMinimumHeight(42)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self._do_login)
        self.username.returnPressed.connect(self.password.setFocus)
        self.password.returnPressed.connect(self._do_login)
        inner.addWidget(self.btn_login)

        # Error label
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #e8a0a0; font-size: 10px;")
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.setMinimumHeight(20)
        inner.addSpacing(12)
        inner.addWidget(self.error_lbl)
        inner.addStretch()

        # Footer hint (default credentials)
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1c1c20;")
        inner.addWidget(sep)
        inner.addSpacing(12)
        hint = QLabel("First launch ?   Default credentials : admin / admin")
        hint.setStyleSheet("color: #3f3f46; font-size: 9px;")
        hint.setAlignment(Qt.AlignCenter)
        inner.addWidget(hint)

        # Focus username au demarrage
        self.username.setFocus()

    def _do_login(self):
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            self.error_lbl.setText("Username and password required")
            return

        try:
            user = self.auth.login(username, password)
        except Exception as e:
            self.error_lbl.setText(str(e))
            return

        if not user:
            self.error_lbl.setText("Invalid credentials")
            self.password.clear()
            self.password.setFocus()
            return

        self.user = user
        self.login_success.emit(user)
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
