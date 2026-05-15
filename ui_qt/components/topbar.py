"""TopBar minimaliste : logo + selecteur de langue + toggle theme via texte."""

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QComboBox
)
from PySide6.QtCore import Signal, Qt

from ..i18n import SUPPORTED_LANGUAGES


class TopBar(QFrame):
    theme_toggled    = Signal()
    language_changed = Signal(str)

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

    def _on_lang_change(self, idx: int):
        code = self._lang_combo.itemData(idx)
        if code:
            self.language_changed.emit(code)
