"""
RiskPulse — Systeme de Themes
==============================
Gestion centralisee des couleurs, polices et styles.

Usage :
    from ui.theme import ThemeManager
    tm = ThemeManager()
    tm.set_theme("dark")
    color = tm.c("bg_primary")
"""

from dataclasses import dataclass
from typing import Dict, Callable, List
import tkinter as tk

from ui.constants import (
    FONT_FAMILY_PRIMARY, FONT_FAMILY_MONO,
    FONT_H1, FONT_H2, FONT_H3, FONT_BODY, FONT_BODY_SM,
    FONT_CAPTION, FONT_MONO, FONT_LOGO, FONT_NAV, FONT_NAV_SM,
    FONT_BTN, FONT_METRIC, FONT_LABEL,
)


# ─────────────────────────────────────────────
#  PALETTES DE COULEURS
# ─────────────────────────────────────────────

THEMES: Dict[str, Dict[str, str]] = {

    "dark": {
        # Fonds
        "bg_primary":      "#0f1923",
        "bg_secondary":    "#162030",
        "bg_tertiary":     "#1c2a3a",
        "bg_card":         "#1a2636",
        "bg_card_hover":   "#1f2f42",
        "bg_input":        "#141e2a",
        "bg_sidebar":      "#0c1520",
        "bg_topbar":       "#0c1520",
        "bg_modal":        "#162030",
        "bg_tooltip":      "#0c1520",

        # Textes
        "text_primary":    "#e8edf2",
        "text_secondary":  "#8fa4b8",
        "text_muted":      "#556677",
        "text_inverse":    "#0f1923",
        "text_link":       "#4a9eda",
        "text_logo":       "#ffffff",

        # Accents — palette bleue professionnelle
        "accent_primary":  "#2a7fc1",
        "accent_hover":    "#3591d8",
        "accent_light":    "#1a3f60",
        "accent_text":     "#7ec8e3",

        # Statuts
        "success":         "#27ae60",
        "success_light":   "#0d3320",
        "warning":         "#e67e22",
        "warning_light":   "#2d1a08",
        "error":           "#c0392b",
        "error_light":     "#2d0e0a",
        "info":            "#2980b9",
        "info_light":      "#0d2035",

        # Bordures
        "border":          "#1e2f40",
        "border_focus":    "#2a7fc1",
        "border_subtle":   "#162030",

        # Sidebar
        "sidebar_item":        "#0c1520",
        "sidebar_item_hover":  "#162030",
        "sidebar_item_active": "#1a3f60",
        "sidebar_text":        "#8fa4b8",
        "sidebar_text_active": "#7ec8e3",
        "sidebar_indicator":   "#2a7fc1",

        # Boutons
        "btn_primary_bg":      "#2a7fc1",
        "btn_primary_fg":      "#ffffff",
        "btn_primary_hover":   "#3591d8",
        "btn_secondary_bg":    "#1c2a3a",
        "btn_secondary_fg":    "#8fa4b8",
        "btn_secondary_hover": "#253547",
        "btn_danger_bg":       "#c0392b",
        "btn_danger_fg":       "#ffffff",
        "btn_danger_hover":    "#e74c3c",
        "btn_success_bg":      "#27ae60",
        "btn_success_fg":      "#ffffff",
        "btn_success_hover":   "#2ecc71",

        # Graphes / metriques
        "chart_1":  "#2a7fc1",
        "chart_2":  "#27ae60",
        "chart_3":  "#e67e22",
        "chart_4":  "#9b59b6",
        "chart_5":  "#e74c3c",

        # Ruptures
        "rupture_1": "#27ae60",
        "rupture_2": "#c0392b",
        "rupture_3": "#d35400",
        "rupture_4": "#8e44ad",
        "rupture_5": "#2980b9",

        # Scrollbar
        "scrollbar_bg":    "#0c1520",
        "scrollbar_thumb": "#253547",
    },

    "light": {
        # Fonds
        "bg_primary":      "#f5f7fa",
        "bg_secondary":    "#ffffff",
        "bg_tertiary":     "#eef1f5",
        "bg_card":         "#ffffff",
        "bg_card_hover":   "#f0f4f8",
        "bg_input":        "#ffffff",
        "bg_sidebar":      "#1a2a3e",
        "bg_topbar":       "#1a2a3e",
        "bg_modal":        "#ffffff",
        "bg_tooltip":      "#2c3e50",

        # Textes
        "text_primary":    "#1a2535",
        "text_secondary":  "#5a6a7a",
        "text_muted":      "#9aaabb",
        "text_inverse":    "#ffffff",
        "text_link":       "#2a7fc1",
        "text_logo":       "#ffffff",

        # Accents
        "accent_primary":  "#2a7fc1",
        "accent_hover":    "#1a6fa8",
        "accent_light":    "#ddeef8",
        "accent_text":     "#2a7fc1",

        # Statuts
        "success":         "#27ae60",
        "success_light":   "#e8f8f0",
        "warning":         "#e67e22",
        "warning_light":   "#fef3e7",
        "error":           "#c0392b",
        "error_light":     "#fce8e6",
        "info":            "#2980b9",
        "info_light":      "#e8f2fb",

        # Bordures
        "border":          "#dce3eb",
        "border_focus":    "#2a7fc1",
        "border_subtle":   "#eef1f5",

        # Sidebar (reste sombre en light mode — convention UI moderne)
        "sidebar_item":        "#1a2a3e",
        "sidebar_item_hover":  "#243550",
        "sidebar_item_active": "#2a7fc1",
        "sidebar_text":        "#8fa4c0",
        "sidebar_text_active": "#ffffff",
        "sidebar_indicator":   "#4ac0e8",

        # Boutons
        "btn_primary_bg":      "#2a7fc1",
        "btn_primary_fg":      "#ffffff",
        "btn_primary_hover":   "#1a6fa8",
        "btn_secondary_bg":    "#dce3eb",
        "btn_secondary_fg":    "#1a2535",
        "btn_secondary_hover": "#c8d3e0",
        "btn_danger_bg":       "#c0392b",
        "btn_danger_fg":       "#ffffff",
        "btn_danger_hover":    "#a93226",
        "btn_success_bg":      "#27ae60",
        "btn_success_fg":      "#ffffff",
        "btn_success_hover":   "#229954",

        # Graphes
        "chart_1":  "#2a7fc1",
        "chart_2":  "#27ae60",
        "chart_3":  "#e67e22",
        "chart_4":  "#9b59b6",
        "chart_5":  "#e74c3c",

        # Ruptures
        "rupture_1": "#27ae60",
        "rupture_2": "#c0392b",
        "rupture_3": "#e67e22",
        "rupture_4": "#9b59b6",
        "rupture_5": "#2980b9",

        # Scrollbar
        "scrollbar_bg":    "#f5f7fa",
        "scrollbar_thumb": "#c8d3de",
    },

    "midnight": {
        # Variante sombre premium — tons profonds
        "bg_primary":      "#080e14",
        "bg_secondary":    "#0d1520",
        "bg_tertiary":     "#111d2a",
        "bg_card":         "#101825",
        "bg_card_hover":   "#141f2e",
        "bg_input":        "#0a1018",
        "bg_sidebar":      "#060c12",
        "bg_topbar":       "#060c12",
        "bg_modal":        "#0d1520",
        "bg_tooltip":      "#060c12",

        "text_primary":    "#d0dce8",
        "text_secondary":  "#6a8aa8",
        "text_muted":      "#3a5068",
        "text_inverse":    "#080e14",
        "text_link":       "#38a0d8",
        "text_logo":       "#e8f4ff",

        "accent_primary":  "#1a6fa8",
        "accent_hover":    "#2a7fc1",
        "accent_light":    "#0a2038",
        "accent_text":     "#5ab8e8",

        "success":         "#1e8449",
        "success_light":   "#071a10",
        "warning":         "#ca6f1e",
        "warning_light":   "#200e04",
        "error":           "#a93226",
        "error_light":     "#1e0806",
        "info":            "#1a6fa8",
        "info_light":      "#071020",

        "border":          "#111d2a",
        "border_focus":    "#1a6fa8",
        "border_subtle":   "#0d1520",

        "sidebar_item":        "#060c12",
        "sidebar_item_hover":  "#0d1520",
        "sidebar_item_active": "#0a2038",
        "sidebar_text":        "#6a8aa8",
        "sidebar_text_active": "#5ab8e8",
        "sidebar_indicator":   "#1a6fa8",

        "btn_primary_bg":      "#1a6fa8",
        "btn_primary_fg":      "#e8f4ff",
        "btn_primary_hover":   "#2a7fc1",
        "btn_secondary_bg":    "#111d2a",
        "btn_secondary_fg":    "#6a8aa8",
        "btn_secondary_hover": "#162030",
        "btn_danger_bg":       "#a93226",
        "btn_danger_fg":       "#ffffff",
        "btn_danger_hover":    "#c0392b",
        "btn_success_bg":      "#1e8449",
        "btn_success_fg":      "#ffffff",
        "btn_success_hover":   "#27ae60",

        "chart_1":  "#1a6fa8",
        "chart_2":  "#1e8449",
        "chart_3":  "#ca6f1e",
        "chart_4":  "#7d3c98",
        "chart_5":  "#a93226",

        "rupture_1": "#1e8449",
        "rupture_2": "#a93226",
        "rupture_3": "#ca6f1e",
        "rupture_4": "#7d3c98",
        "rupture_5": "#1a6fa8",

        "scrollbar_bg":    "#060c12",
        "scrollbar_thumb": "#111d2a",
    },
}


# ─────────────────────────────────────────────
#  THEME MANAGER
# ─────────────────────────────────────────────

class ThemeManager:
    """
    Gestionnaire de themes centralise.

    - Stocke le theme actif
    - Notifie les widgets abonnes lors d'un changement
    - Fournit les couleurs et polices via des methodes simples

    Usage dans un widget :
        self.tm = ThemeManager.instance()
        self.tm.subscribe(self._on_theme_change)
        bg = self.tm.c("bg_card")
        font = self.tm.font("h2")
    """

    _instance: "ThemeManager | None" = None

    def __init__(self, initial_theme: str = "dark"):
        self._theme_name = initial_theme
        self._colors = THEMES[initial_theme]
        self._observers: List[Callable] = []
        ThemeManager._instance = self

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    # ── Changement de theme ───────────────────

    def set_theme(self, name: str):
        """Change le theme et notifie tous les abonnes."""
        if name not in THEMES:
            raise ValueError(f"Theme inconnu : {name}. Disponibles : {list(THEMES.keys())}")
        self._theme_name = name
        self._colors = THEMES[name]
        self._notify_all()

    def toggle_dark_light(self):
        """Bascule entre dark et light."""
        if self._theme_name == "light":
            self.set_theme("dark")
        else:
            self.set_theme("light")

    @property
    def name(self) -> str:
        return self._theme_name

    @property
    def is_dark(self) -> bool:
        return self._theme_name != "light"

    @property
    def available_themes(self) -> List[str]:
        return list(THEMES.keys())

    # ── Couleurs ──────────────────────────────

    def c(self, key: str) -> str:
        """Retourne une couleur du theme actif."""
        color = self._colors.get(key)
        if color is None:
            # Fallback sur dark si la cle n'existe pas dans ce theme
            color = THEMES["dark"].get(key, "#ff00ff")
        return color

    def rupture_color(self, key: str) -> str:
        """Couleur d'une rupture (R1..R5)."""
        return self._colors.get(f"rupture_{key[-1]}", self.c("accent_primary"))

    # ── Polices ───────────────────────────────

    def font(self, key: str) -> tuple:
        """Retourne un tuple police compatible tkinter."""
        fonts = {
            "h1":      FONT_H1,
            "h2":      FONT_H2,
            "h3":      FONT_H3,
            "body":    FONT_BODY,
            "body_sm": FONT_BODY_SM,
            "caption": FONT_CAPTION,
            "mono":    FONT_MONO,
            "logo":    FONT_LOGO,
            "nav":     FONT_NAV,
            "nav_sm":  FONT_NAV_SM,
            "btn":     FONT_BTN,
            "metric":  FONT_METRIC,
            "label":   FONT_LABEL,
        }
        spec = fonts.get(key, FONT_BODY)
        return spec.as_tuple()

    # ── Abonnements ───────────────────────────

    def subscribe(self, callback: Callable):
        """Abonne un callback au changement de theme."""
        if callback not in self._observers:
            self._observers.append(callback)

    def unsubscribe(self, callback: Callable):
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_all(self):
        """Notifie tous les abonnes du changement de theme."""
        dead = []
        for cb in self._observers:
            try:
                cb()
            except Exception:
                dead.append(cb)
        for cb in dead:
            self._observers.remove(cb)

    # ── Utilitaires ───────────────────────────

    def apply_to_widget(self, widget: tk.Widget, **keys):
        """
        Applique des couleurs de theme a un widget tkinter.
        Ex: tm.apply_to_widget(lbl, bg="bg_card", fg="text_primary")
        """
        cfg = {k: self.c(v) for k, v in keys.items()}
        try:
            widget.configure(**cfg)
        except tk.TclError:
            pass

    def hex_to_rgb(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def blend(self, color1: str, color2: str, ratio: float = 0.5) -> str:
        """Melange deux couleurs hexa selon un ratio."""
        r1, g1, b1 = self.hex_to_rgb(color1)
        r2, g2, b2 = self.hex_to_rgb(color2)
        r = int(r1 * (1 - ratio) + r2 * ratio)
        g = int(g1 * (1 - ratio) + g2 * ratio)
        b = int(b1 * (1 - ratio) + b2 * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"


# ─────────────────────────────────────────────
#  MIXIN POUR WIDGETS AVEC THEME
# ─────────────────────────────────────────────

class ThemedMixin:
    """
    Mixin a heriter dans tout widget custom.
    Fournit self.tm, self.c() et self._on_theme_change().
    """

    def _init_theme(self):
        self.tm = ThemeManager.instance()
        self.tm.subscribe(self._on_theme_change)

    def c(self, key: str) -> str:
        return self.tm.c(key)

    def font(self, key: str) -> tuple:
        return self.tm.font(key)

    def _on_theme_change(self):
        """A surcharger dans chaque widget pour appliquer le nouveau theme."""
        pass

    def _cleanup_theme(self):
        """Appeler dans destroy() pour eviter les fuites memoire."""
        self.tm.unsubscribe(self._on_theme_change)
