"""
RiskPulse — Theme premium minimaliste
=======================================
Direction artistique : Linear / Raycast / Arc browser.
Palette monochrome, accents tres discrets, typographie JetBrains Mono.
"""

from typing import Dict
from PySide6.QtCore import QObject, Signal


# ─────────────────────────────────────────────
#  PALETTES MONOCHROMES
# ─────────────────────────────────────────────

PALETTES: Dict[str, Dict[str, str]] = {

    "dark": {
        # Fonds — gradient sourd de noirs (4-8% de luminance)
        "bg_window":       "#0a0a0c",
        "bg_surface":      "#0e0e11",
        "bg_card":         "#121215",
        "bg_card_hover":   "#16161a",
        "bg_input":        "#0c0c0f",
        "bg_sidebar":      "#08080a",
        "bg_topbar":       "#08080a",
        "bg_overlay":      "#1a1a1f",

        # Textes — echelle de gris precise
        "text_primary":    "#e4e4e7",
        "text_secondary":  "#a1a1aa",
        "text_muted":      "#52525b",
        "text_dim":        "#3f3f46",
        "text_inverse":    "#0a0a0c",

        # Accent — un seul, tres sobre (cyan delave premium)
        "accent":          "#9ca3af",      # gris-bleu clair, jamais saturé
        "accent_strong":   "#e4e4e7",      # blanc cassé pour le hover
        "accent_subtle":   "#1a1a1f",
        "accent_underline": "#3f3f46",

        # Statuts — desatures, jamais fluo
        "success":         "#84cc9e",
        "success_subtle":  "#0f1611",
        "warning":         "#e3c08e",
        "warning_subtle":  "#171311",
        "error":           "#e8a0a0",
        "error_subtle":    "#191112",
        "info":            "#9caec1",
        "info_subtle":     "#0f1217",

        # Bordures — tres proches du fond (8-12% delta)
        "border":          "#1c1c20",
        "border_strong":   "#27272a",
        "border_focus":    "#52525b",
        "divider":         "#18181b",

        # Charts — palette sourde, jamais saturee
        "chart_1":         "#9ca3af",
        "chart_2":         "#84cc9e",
        "chart_3":         "#e3c08e",
        "chart_4":         "#b69cc4",
        "chart_5":         "#e8a0a0",
    },

    "light": {
        # Light mode — papier creme, pas blanc pur
        "bg_window":       "#fafaf9",
        "bg_surface":      "#ffffff",
        "bg_card":         "#ffffff",
        "bg_card_hover":   "#f4f4f5",
        "bg_input":        "#ffffff",
        "bg_sidebar":      "#fafaf9",
        "bg_topbar":       "#ffffff",
        "bg_overlay":      "#ffffff",

        "text_primary":    "#18181b",
        "text_secondary":  "#52525b",
        "text_muted":      "#a1a1aa",
        "text_dim":        "#d4d4d8",
        "text_inverse":    "#fafaf9",

        "accent":          "#52525b",
        "accent_strong":   "#18181b",
        "accent_subtle":   "#f4f4f5",
        "accent_underline": "#d4d4d8",

        "success":         "#4d7c5f",
        "success_subtle":  "#f0f7f2",
        "warning":         "#a16207",
        "warning_subtle":  "#fef9ed",
        "error":           "#9f1f30",
        "error_subtle":    "#fdf2f3",
        "info":            "#5b6b80",
        "info_subtle":     "#f3f5f8",

        "border":          "#e4e4e7",
        "border_strong":   "#d4d4d8",
        "border_focus":    "#71717a",
        "divider":         "#f4f4f5",

        "chart_1":         "#52525b",
        "chart_2":         "#4d7c5f",
        "chart_3":         "#a16207",
        "chart_4":         "#7d6896",
        "chart_5":         "#9f1f30",
    },
}


# ─────────────────────────────────────────────
#  TYPOGRAPHIE — JetBrains Mono partout
# ─────────────────────────────────────────────

FONT_STACK = '"JetBrains Mono", "JetBrains Mono Medium", "Cascadia Code", "SF Mono", "Consolas", monospace'


# ─────────────────────────────────────────────
#  THEME MANAGER
# ─────────────────────────────────────────────

class ThemeManager(QObject):

    theme_changed = Signal(str)

    _instance: "ThemeManager | None" = None

    def __init__(self):
        super().__init__()
        self._theme = "dark"
        self._app = None
        ThemeManager._instance = self

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    def install(self, app, theme: str = "dark"):
        self._app = app
        self.set_theme(theme)

    @property
    def name(self) -> str:
        return self._theme

    @property
    def is_dark(self) -> bool:
        return self._theme == "dark"

    def c(self, key: str) -> str:
        return PALETTES[self._theme].get(key, "#ff00ff")

    def set_theme(self, name: str):
        if name not in PALETTES:
            return
        self._theme = name
        if self._app:
            self._app.setStyleSheet(self.build_stylesheet())
        self.theme_changed.emit(name)

    def toggle(self):
        self.set_theme("light" if self._theme == "dark" else "dark")

    # ── QSS global ─────────────────────────────

    def build_stylesheet(self) -> str:
        c = PALETTES[self._theme]
        return f"""
        /* ───────────────────────────── Base */
        * {{
            font-family: {FONT_STACK};
            font-size: 11px;
        }}
        QMainWindow, QDialog {{
            background-color: {c["bg_window"]};
            color: {c["text_primary"]};
        }}
        QWidget {{
            color: {c["text_primary"]};
            background-color: transparent;
        }}

        /* Containers qui doivent forcer le fond window (sinon defaut Qt = blanc/noir) */
        QStackedWidget, QStackedWidget > QWidget,
        QScrollArea, QScrollArea > QWidget > QWidget,
        QAbstractScrollArea::viewport {{
            background-color: {c["bg_window"]};
        }}

        /* Diviseur horizontal */
        QFrame#divider {{
            background-color: {c["border"]};
            max-height: 1px;
            min-height: 1px;
        }}

        /* ───────────────────────────── Surfaces */
        QFrame#card {{
            background-color: {c["bg_card"]};
            border: 1px solid {c["border"]};
            border-radius: 4px;
        }}
        QFrame#surface {{
            background-color: {c["bg_surface"]};
            border-radius: 4px;
        }}

        /* ───────────────────────────── Boutons */
        QPushButton {{
            background-color: transparent;
            color: {c["text_secondary"]};
            border: 1px solid {c["border"]};
            border-radius: 3px;
            padding: 7px 14px;
            font-weight: 500;
            font-size: 10px;
            letter-spacing: 0.4px;
        }}
        QPushButton:hover {{
            background-color: {c["bg_card_hover"]};
            color: {c["text_primary"]};
            border-color: {c["border_strong"]};
        }}
        QPushButton:pressed {{
            background-color: {c["bg_input"]};
        }}
        QPushButton:disabled {{
            color: {c["text_dim"]};
            border-color: {c["border"]};
        }}

        /* variant=primary : monochrome, accent discret */
        QPushButton[variant="primary"] {{
            background-color: {c["text_primary"]};
            color: {c["bg_window"]};
            border: 1px solid {c["text_primary"]};
        }}
        QPushButton[variant="primary"]:hover {{
            background-color: {c["accent_strong"]};
            border-color: {c["accent_strong"]};
        }}
        QPushButton[variant="primary"]:pressed {{
            background-color: {c["accent"]};
        }}

        /* variant=success : bordure verte sourde, fond noir */
        QPushButton[variant="success"] {{
            background-color: transparent;
            color: {c["success"]};
            border: 1px solid {c["success_subtle"]};
        }}
        QPushButton[variant="success"]:hover {{
            background-color: {c["success_subtle"]};
            border-color: {c["success"]};
        }}

        /* variant=danger : meme principe en rouge sourd */
        QPushButton[variant="danger"] {{
            background-color: transparent;
            color: {c["error"]};
            border: 1px solid {c["error_subtle"]};
        }}
        QPushButton[variant="danger"]:hover {{
            background-color: {c["error_subtle"]};
            border-color: {c["error"]};
        }}

        /* variant=ghost : aucune bordure */
        QPushButton[variant="ghost"] {{
            background-color: transparent;
            border: none;
            color: {c["text_muted"]};
            padding: 7px 10px;
        }}
        QPushButton[variant="ghost"]:hover {{
            color: {c["text_primary"]};
            background-color: {c["bg_card_hover"]};
        }}

        /* ───────────────────────────── Inputs */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {c["bg_input"]};
            border: 1px solid {c["border"]};
            border-radius: 3px;
            padding: 8px 10px;
            color: {c["text_primary"]};
            selection-background-color: {c["accent_subtle"]};
            selection-color: {c["text_primary"]};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {c["border_focus"]};
        }}
        QTextEdit, QPlainTextEdit {{
            padding: 12px 14px;
            line-height: 1.6;
        }}

        QSpinBox, QDoubleSpinBox {{
            background-color: {c["bg_input"]};
            border: 1px solid {c["border"]};
            border-radius: 3px;
            padding: 6px 10px;
            color: {c["text_primary"]};
        }}
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            width: 0; height: 0;
        }}

        /* ───────────────────────────── Combobox */
        QComboBox {{
            background-color: {c["bg_input"]};
            border: 1px solid {c["border"]};
            border-radius: 3px;
            padding: 6px 12px 6px 10px;
            color: {c["text_primary"]};
            min-width: 100px;
        }}
        QComboBox:hover {{
            border-color: {c["border_strong"]};
        }}
        QComboBox:focus, QComboBox:on {{
            border-color: {c["border_focus"]};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
            subcontrol-position: right center;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 3px solid transparent;
            border-right: 3px solid transparent;
            border-top: 4px solid {c["text_muted"]};
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c["bg_card"]};
            border: 1px solid {c["border_strong"]};
            border-radius: 3px;
            selection-background-color: {c["bg_card_hover"]};
            selection-color: {c["text_primary"]};
            outline: none;
            padding: 4px;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 6px 10px;
            border-radius: 2px;
            color: {c["text_secondary"]};
        }}
        QComboBox QAbstractItemView::item:hover {{
            color: {c["text_primary"]};
        }}

        /* ───────────────────────────── Slider */
        QSlider::groove:horizontal {{
            height: 2px;
            background: {c["border"]};
        }}
        QSlider::handle:horizontal {{
            background: {c["text_primary"]};
            width: 10px;
            height: 10px;
            margin: -4px 0;
            border-radius: 5px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {c["accent_strong"]};
        }}
        QSlider::sub-page:horizontal {{
            background: {c["text_secondary"]};
        }}

        /* ───────────────────────────── Scrollbar */
        QScrollBar:vertical, QScrollBar:horizontal {{
            background: transparent;
            border: none;
        }}
        QScrollBar:vertical {{ width: 8px; margin: 0; }}
        QScrollBar:horizontal {{ height: 8px; margin: 0; }}
        QScrollBar::handle {{
            background: {c["border_strong"]};
            border-radius: 2px;
        }}
        QScrollBar::handle:hover {{
            background: {c["text_muted"]};
        }}
        QScrollBar::handle:vertical {{ min-height: 30px; }}
        QScrollBar::handle:horizontal {{ min-width: 30px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{
            background: none; height: 0; width: 0;
        }}
        QScrollBar::add-page, QScrollBar::sub-page {{
            background: none;
        }}

        /* ───────────────────────────── Labels semantiques */
        QLabel[class="h1"] {{
            color: {c["text_primary"]};
            font-size: 18px;
            font-weight: 500;
            letter-spacing: -0.3px;
            padding: 0;
        }}
        QLabel[class="h2"] {{
            color: {c["text_primary"]};
            font-size: 14px;
            font-weight: 500;
            letter-spacing: -0.2px;
        }}
        QLabel[class="h3"] {{
            color: {c["text_secondary"]};
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }}
        QLabel[class="subtitle"] {{
            color: {c["text_muted"]};
            font-size: 10px;
            letter-spacing: 0.1px;
        }}
        QLabel[class="caption"] {{
            color: {c["text_dim"]};
            font-size: 9px;
            letter-spacing: 0.4px;
            text-transform: uppercase;
        }}
        QLabel[class="metric"] {{
            color: {c["text_primary"]};
            font-size: 26px;
            font-weight: 400;
            letter-spacing: -0.5px;
        }}
        QLabel[class="metric-label"] {{
            color: {c["text_muted"]};
            font-size: 9px;
            letter-spacing: 0.6px;
            text-transform: uppercase;
        }}

        /* ───────────────────────────── Sidebar */
        QFrame#sidebar {{
            background-color: {c["bg_sidebar"]};
            border-right: 1px solid {c["border"]};
        }}
        QPushButton[role="nav"] {{
            background-color: transparent;
            border: none;
            border-left: 3px solid transparent;
            border-radius: 0;
            padding: 9px 14px 9px 18px;
            text-align: left;
            color: {c["text_muted"]};
            font-size: 11px;
            font-weight: 400;
            letter-spacing: 0.1px;
        }}
        QPushButton[role="nav"]:hover {{
            background-color: {c["bg_card_hover"]};
            color: {c["text_secondary"]};
        }}
        QPushButton[role="nav"][active="true"] {{
            background-color: {c["accent_subtle"]};
            color: {c["text_primary"]};
            border-left: 3px solid {c["text_primary"]};
            font-weight: 500;
        }}

        /* ───────────────────────────── Topbar */
        QFrame#topbar {{
            background-color: {c["bg_topbar"]};
            border-bottom: 1px solid {c["border"]};
        }}
        QLabel#logo {{
            color: {c["text_primary"]};
            font-size: 13px;
            font-weight: 500;
            letter-spacing: 1.2px;
        }}

        /* ───────────────────────────── Status bar */
        QFrame#statusbar {{
            background-color: {c["bg_sidebar"]};
            border-top: 1px solid {c["border"]};
        }}

        /* ───────────────────────────── Tabs */
        QTabBar {{
            qproperty-drawBase: 0;
            background: transparent;
        }}
        QTabBar::tab {{
            background: transparent;
            color: {c["text_muted"]};
            padding: 8px 14px;
            border: none;
            border-bottom: 1px solid transparent;
            font-size: 10px;
            font-weight: 500;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }}
        QTabBar::tab:hover {{
            color: {c["text_secondary"]};
        }}
        QTabBar::tab:selected {{
            color: {c["text_primary"]};
            border-bottom: 1px solid {c["text_primary"]};
        }}
        QTabWidget::pane {{
            border: none;
            background: transparent;
            top: -1px;
        }}

        /* ───────────────────────────── Tables */
        QTableWidget, QTreeWidget, QListWidget {{
            background-color: transparent;
            border: 1px solid {c["border"]};
            border-radius: 4px;
            color: {c["text_secondary"]};
            outline: none;
            gridline-color: {c["divider"]};
            alternate-background-color: {c["bg_surface"]};
            font-size: 10px;
        }}
        QTableWidget::item, QListWidget::item, QTreeWidget::item {{
            padding: 8px 10px;
            border: none;
            border-bottom: 1px solid {c["divider"]};
        }}
        QTableWidget::item:selected, QListWidget::item:selected,
        QTreeWidget::item:selected {{
            background-color: {c["bg_card_hover"]};
            color: {c["text_primary"]};
        }}
        QHeaderView::section {{
            background-color: {c["bg_surface"]};
            color: {c["text_muted"]};
            padding: 8px 10px;
            border: none;
            border-bottom: 1px solid {c["border"]};
            font-size: 9px;
            font-weight: 500;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }}

        /* ───────────────────────────── Progress */
        QProgressBar {{
            background-color: {c["border"]};
            border: none;
            border-radius: 1px;
            height: 2px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {c["text_secondary"]};
        }}

        /* ───────────────────────────── Checkbox / Radio */
        QCheckBox, QRadioButton {{
            color: {c["text_secondary"]};
            spacing: 8px;
            font-size: 10px;
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 14px;
            height: 14px;
            border: 1px solid {c["border_strong"]};
            background: {c["bg_input"]};
        }}
        QCheckBox::indicator {{ border-radius: 2px; }}
        QRadioButton::indicator {{ border-radius: 7px; }}
        QCheckBox::indicator:checked {{
            background: {c["text_primary"]};
            border-color: {c["text_primary"]};
        }}
        QRadioButton::indicator:checked {{
            background: {c["bg_input"]};
            border: 4px solid {c["text_primary"]};
        }}

        /* ───────────────────────────── Tooltip */
        QToolTip {{
            background-color: {c["bg_overlay"]};
            color: {c["text_primary"]};
            border: 1px solid {c["border_strong"]};
            border-radius: 3px;
            padding: 6px 10px;
            font-size: 10px;
        }}

        /* ───────────────────────────── Splitter */
        QSplitter::handle {{
            background-color: transparent;
        }}
        QSplitter::handle:hover {{
            background-color: {c["border_strong"]};
        }}
        QSplitter::handle:horizontal {{ width: 1px; }}
        QSplitter::handle:vertical {{ height: 1px; }}

        /* ───────────────────────────── MessageBox */
        QMessageBox {{
            background-color: {c["bg_surface"]};
        }}
        """
