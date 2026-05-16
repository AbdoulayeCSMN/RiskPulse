"""TopBar minimaliste : logo + user badge + selecteur de langue + toggle theme."""

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QComboBox
)
from PySide6.QtCore import Signal, Qt

from ..i18n import SUPPORTED_LANGUAGES
from .user_badge import UserBadge


class TopBar(QFrame):
    theme_toggled    = Signal()
    language_changed = Signal(str)
    logout_requested = Signal()

    def __init__(self, app_name: str, subtitle: str, version: str, parent=None):
        super().__init__(parent)
        self.setObjectName("topbar")
        self.setFixedHeight(52)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 18, 0)
        layout.setSpacing(20)

        # Logo
        self._logo = QLabel(app_name.upper())
        self._logo.setObjectName("logo")
        layout.addWidget(self._logo)

        # Separateur fin
        sep = QFrame()
        sep.setFixedSize(1, 20)
        sep.setStyleSheet("background-color: rgba(255,255,255,0.06);")
        layout.addWidget(sep)

        # Sous-titre
        self._subtitle = QLabel(subtitle)
        self._subtitle.setProperty("class", "subtitle")
        layout.addWidget(self._subtitle)

        layout.addStretch()

        # Licence badge (trial countdown / plan)
        self._license_lbl = QLabel("")
        self._license_lbl.setProperty("class", "caption")
        self._license_lbl.setCursor(Qt.PointingHandCursor)
        self._license_lbl.mousePressEvent = self._on_license_click  # type: ignore
        layout.addWidget(self._license_lbl)
        self._refresh_license_badge()

        # User badge
        self._user_badge = UserBadge(parent=self)
        self._user_badge.logout_requested.connect(self.logout_requested.emit)
        layout.addWidget(self._user_badge)

        # Selecteur de langue (style minimaliste)
        self._lang_combo = QComboBox()
        self._lang_combo.setFixedWidth(120)
        for code, name in SUPPORTED_LANGUAGES.items():
            self._lang_combo.addItem(name, userData=code)
        self._lang_combo.currentIndexChanged.connect(self._on_lang_change)
        layout.addWidget(self._lang_combo)

        # Toggle theme : bouton texte minimaliste
        self._theme_btn = QPushButton("DARK")
        self._theme_btn.setProperty("variant", "ghost")
        self._theme_btn.setFixedSize(60, 28)
        self._theme_btn.setCursor(Qt.PointingHandCursor)
        self._theme_btn.clicked.connect(self.theme_toggled.emit)
        layout.addWidget(self._theme_btn)

        # Version
        self._version = QLabel(f"v{version}")
        self._version.setProperty("class", "caption")
        layout.addWidget(self._version)

    def set_language(self, code: str):
        idx = self._lang_combo.findData(code)
        if idx >= 0:
            self._lang_combo.blockSignals(True)
            self._lang_combo.setCurrentIndex(idx)
            self._lang_combo.blockSignals(False)

    def update_theme_icon(self, is_dark: bool):
        self._theme_btn.setText("LIGHT" if is_dark else "DARK")

    def set_subtitle(self, text: str):
        self._subtitle.setText(text)

    def set_user(self, user):
        """Affiche/masque le badge user."""
        self._user_badge.set_user(user)

    def _on_lang_change(self, idx: int):
        code = self._lang_combo.itemData(idx)
        if code:
            self.language_changed.emit(code)

    # ── Licence badge ─────────────────────────

    def _refresh_license_badge(self):
        try:
            from services.licensing import get_license_manager
            mgr = get_license_manager()
            st = mgr.state
            if st.is_trial and st.trial_active():
                days = st.trial_days_left()
                self._license_lbl.setText(f"TRIAL · {days}d")
            else:
                self._license_lbl.setText(st.effective_plan().value)
        except Exception:
            self._license_lbl.setText("")

    def _on_license_click(self, _ev):
        # Trouve la MainWindow et navigue vers la vue License
        w = self.window()
        if w is not None and hasattr(w, "_navigate"):
            w._navigate("license")

    def refresh_license(self):
        self._refresh_license_badge()
