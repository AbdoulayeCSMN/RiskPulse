"""
RiskPulse — Composants UI Reutilisables
========================================
Widgets custom construits sur tkinter/ttk.
Chaque composant supporte le theme dynamique via ThemedMixin.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, List, Tuple

from ui.theme import ThemeManager, ThemedMixin
from ui.constants import (
    PAD_XS, PAD_SM, PAD_MD, PAD_LG,
    BTN_HEIGHT_SM, BTN_HEIGHT_MD, BTN_HEIGHT_LG, BTN_PAD_X,
    CARD_RADIUS, CARD_BORDER_W,
    INPUT_HEIGHT, PROGRESSBAR_H,
    ANIM_DURATION_FAST,
)


# ─────────────────────────────────────────────
#  FRAME DE BASE AVEC THEME
# ─────────────────────────────────────────────

class ThemedFrame(tk.Frame, ThemedMixin):
    def __init__(self, parent, bg_key="bg_primary", **kwargs):
        self._init_theme()
        super().__init__(parent, bg=self.c(bg_key), **kwargs)
        self._bg_key = bg_key

    def _on_theme_change(self):
        try:
            self.configure(bg=self.c(self._bg_key))
        except tk.TclError:
            pass


class ThemedLabel(tk.Label, ThemedMixin):
    def __init__(self, parent, text="", font_key="body",
                 fg_key="text_primary", bg_key="bg_primary", **kwargs):
        self._init_theme()
        super().__init__(
            parent, text=text,
            font=self.font(font_key),
            fg=self.c(fg_key),
            bg=self.c(bg_key),
            **kwargs
        )
        self._font_key = font_key
        self._fg_key   = fg_key
        self._bg_key   = bg_key

    def _on_theme_change(self):
        try:
            self.configure(fg=self.c(self._fg_key), bg=self.c(self._bg_key))
        except tk.TclError:
            pass


# ─────────────────────────────────────────────
#  BOUTONS
# ─────────────────────────────────────────────

def _round_rect_coords(x1, y1, x2, y2, r):
    """Genere les coordonnees d'un rectangle arrondi pour Canvas.create_polygon."""
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2 - r, y1,
        x2,     y1,
        x2,     y1 + r,
        x2,     y1 + r,
        x2,     y2 - r,
        x2,     y2 - r,
        x2,     y2,
        x2 - r, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1 + r, y2,
        x1,     y2,
        x1,     y2 - r,
        x1,     y2 - r,
        x1,     y1 + r,
        x1,     y1 + r,
        x1,     y1,
        x1 + r, y1,
    ]


class Button(tk.Canvas, ThemedMixin):
    """
    Bouton moderne a coins arrondis (Canvas-based).
    Variantes : primary, secondary, danger, success, ghost
    """

    VARIANTS = {
        "primary":   ("btn_primary_bg",   "btn_primary_fg",   "btn_primary_hover"),
        "secondary": ("btn_secondary_bg", "btn_secondary_fg", "btn_secondary_hover"),
        "danger":    ("btn_danger_bg",    "btn_danger_fg",    "btn_danger_hover"),
        "success":   ("btn_success_bg",   "btn_success_fg",   "btn_success_hover"),
        "ghost":     ("bg_tertiary",      "text_secondary",   "bg_card_hover"),
    }

    SIZES = {
        "sm": (BTN_HEIGHT_SM, 13, 6),   # height, padding_x, radius
        "md": (BTN_HEIGHT_MD, 18, 7),
        "lg": (BTN_HEIGHT_LG, 22, 8),
    }

    def __init__(
        self, parent,
        text: str = "",
        command: Optional[Callable] = None,
        variant: str = "primary",
        size: str = "md",
        icon: str = "",
        disabled: bool = False,
        **kwargs
    ):
        self._init_theme()
        self._command  = command
        self._variant  = variant
        self._disabled = disabled
        self._icon     = icon
        self._text     = f"{icon}  {text}" if icon else text
        self._hover    = False
        self._size_key = size

        height, pad_x, radius = self.SIZES.get(size, self.SIZES["md"])
        self._height = height
        self._pad_x  = pad_x
        self._radius = radius

        # Determine parent bg pour transparence visuelle
        parent_bg = self._infer_parent_bg(parent)

        super().__init__(
            parent,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=parent_bg,
            cursor="hand2" if not disabled else "arrow",
            **kwargs,
        )

        # Mesure la largeur necessaire pour le texte
        self._parent_bg = parent_bg
        self._compute_width()
        self._draw()

        if not disabled:
            self.bind("<Enter>",      self._on_enter)
            self.bind("<Leave>",      self._on_leave)
            self.bind("<Button-1>",   self._on_click)
            self.bind("<Configure>",  lambda e: self._draw())

    def _infer_parent_bg(self, parent) -> str:
        """Cherche la couleur de fond du parent pour rendre les coins arrondis 'transparents'."""
        try:
            return parent.cget("bg")
        except Exception:
            return self.c("bg_primary")

    def _compute_width(self):
        # Approximation : largeur moyenne caractere = 7.5 px en taille 11 bold
        fnt = self.font("btn")
        try:
            from tkinter import font as tkfont
            f = tkfont.Font(font=fnt)
            text_w = f.measure(self._text)
        except Exception:
            text_w = len(self._text) * 8
        self._width = max(text_w + self._pad_x * 2, self._height + 8)
        self.configure(width=self._width)

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or self._width
        h = self._height

        bg_key, fg_key, hover_key = self.VARIANTS.get(
            self._variant, self.VARIANTS["primary"]
        )
        fill = self.c(hover_key if self._hover else bg_key)
        fg = self.c(fg_key)

        # Dessine le rectangle arrondi
        self.create_polygon(
            _round_rect_coords(1, 1, w - 1, h - 1, self._radius),
            smooth=True, fill=fill, outline="",
        )

        # Texte centre
        self.create_text(
            w / 2, h / 2,
            text=self._text,
            font=self.font("btn"),
            fill=fg,
            anchor="center",
        )

    def _on_enter(self, e=None):
        self._hover = True
        self._draw()

    def _on_leave(self, e=None):
        self._hover = False
        self._draw()

    def _on_click(self, e=None):
        if not self._disabled and self._command:
            self._command()

    def set_disabled(self, disabled: bool):
        self._disabled = disabled
        self.configure(cursor="arrow" if disabled else "hand2")

    def configure(self, **kwargs):
        # Permet aux vues de changer le texte via .configure(text=...)
        if "text" in kwargs:
            self._text = kwargs.pop("text")
            self._compute_width()
            self._draw()
        return super().configure(**kwargs)

    def _on_theme_change(self):
        try:
            self._parent_bg = self._infer_parent_bg(self.master)
            self.configure(bg=self._parent_bg)
            self._draw()
        except tk.TclError:
            pass


# ─────────────────────────────────────────────
#  CARTE (Card)
# ─────────────────────────────────────────────

class Card(tk.Frame, ThemedMixin):
    """
    Carte moderne avec coins arrondis (dessinee via Canvas en arriere-plan)
    et bordure subtile. Supporte un titre et une couleur d'accent laterale.
    """

    RADIUS = 10

    def __init__(
        self, parent,
        title: str = "",
        accent_color: str = "",
        bg_key: str = "bg_card",
        padx: int = PAD_MD,
        pady: int = PAD_MD,
        **kwargs
    ):
        self._init_theme()
        self._bg_key  = bg_key
        self._accent  = accent_color
        self._padx    = padx
        self._pady    = pady
        self._title   = title

        # Background du parent (pour faire apparaitre les coins comme transparents)
        parent_bg = self._infer_parent_bg(parent)
        self._parent_bg = parent_bg

        super().__init__(parent, bg=parent_bg, **kwargs)

        # Canvas pour le fond arrondi (place : en arriere-plan, ne contribue pas a la taille)
        self._canvas = tk.Canvas(
            self, bg=parent_bg,
            highlightthickness=0, bd=0,
        )
        self._canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Frame "content" via PACK (contribue a la taille naturelle de la Card)
        self.content = tk.Frame(self, bg=self.c(bg_key))
        self.content.pack(
            fill="both", expand=True,
            padx=padx, pady=pady,
        )

        # Bind redraw on resize
        self.bind("<Configure>", self._on_resize)

        # Titre eventuel
        if title:
            ThemedLabel(
                self.content, text=title,
                font_key="label", fg_key="text_secondary", bg_key=bg_key,
                anchor="w",
            ).pack(anchor="w", fill="x", pady=(0, PAD_SM))

    def _infer_parent_bg(self, parent) -> str:
        try:
            return parent.cget("bg")
        except Exception:
            return self.c("bg_primary")

    def _on_resize(self, e=None):
        self._draw_background()

    def _draw_background(self):
        c = self._canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 4 or h < 4:
            return

        fill = self.c(self._bg_key)
        border = self.c("border_subtle")
        r = self.RADIUS

        # Fond principal arrondi avec bordure subtile (pas d'accent, pas d'ombre)
        c.create_polygon(
            _round_rect_coords(1, 1, w - 1, h - 1, r),
            smooth=True, fill=fill, outline=border, width=1,
        )

    def _on_theme_change(self):
        try:
            self._parent_bg = self._infer_parent_bg(self.master)
            self.configure(bg=self._parent_bg)
            self._canvas.configure(bg=self._parent_bg)
            self.content.configure(bg=self.c(self._bg_key))
            self._draw_background()
        except tk.TclError:
            pass


# ─────────────────────────────────────────────
#  CARTE METRIQUE
# ─────────────────────────────────────────────

class MetricCard(tk.Frame, ThemedMixin):
    """
    Carte metrique a coins arrondis (Canvas).
    Affiche une valeur, un label et une couleur d'accent en haut.
    """

    RADIUS = 8

    def __init__(
        self, parent,
        label: str,
        value: str = "—",
        accent: str = "",
        **kwargs
    ):
        self._init_theme()
        self._accent_color = accent or self.c("accent_primary")

        parent_bg = self._infer_parent_bg(parent)
        self._parent_bg = parent_bg

        super().__init__(parent, bg=parent_bg, **kwargs)

        self._canvas = tk.Canvas(self, bg=parent_bg, highlightthickness=0, bd=0)
        self._canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Contenu via PACK (contribue a la taille naturelle)
        self.content = tk.Frame(self, bg=self.c("bg_card"))
        self.content.pack(
            fill="both", expand=True,
            padx=PAD_MD, pady=PAD_MD,
        )

        self._val_lbl = ThemedLabel(
            self.content, text=value, font_key="metric",
            fg_key="text_primary", bg_key="bg_card",
        )
        self._val_lbl.pack(anchor="w")
        ThemedLabel(
            self.content, text=label, font_key="caption",
            fg_key="text_muted", bg_key="bg_card",
        ).pack(anchor="w")

        self.bind("<Configure>", lambda e: self._draw())

    def _infer_parent_bg(self, parent) -> str:
        try:
            return parent.cget("bg")
        except Exception:
            return self.c("bg_primary")

    def _draw(self):
        c = self._canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 4 or h < 4:
            return
        fill = self.c("bg_card")
        border = self.c("border_subtle")
        r = self.RADIUS

        c.create_polygon(
            _round_rect_coords(1, 1, w - 2, h - 2, r),
            smooth=True, fill=fill, outline=border, width=1,
        )

    def set_value(self, value: str):
        self._val_lbl.configure(text=str(value))

    def _on_theme_change(self):
        try:
            self._parent_bg = self._infer_parent_bg(self.master)
            self.configure(bg=self._parent_bg)
            self._canvas.configure(bg=self._parent_bg)
            self.content.configure(bg=self.c("bg_card"))
            self._draw()
        except tk.TclError:
            pass


# ─────────────────────────────────────────────
#  BARRE DE PROGRESSION
# ─────────────────────────────────────────────

class ProgressBar(ThemedFrame):
    """Barre de progression custom avec animation."""

    def __init__(self, parent, height: int = PROGRESSBAR_H,
                 color_key: str = "accent_primary", **kwargs):
        super().__init__(parent, bg_key="bg_tertiary", **kwargs)
        self._color_key = color_key
        self._value     = 0.0

        self.configure(height=height)
        self._fill = tk.Frame(self, bg=self.c(color_key), height=height)
        self._fill.place(x=0, y=0, relheight=1, relwidth=0)

    def set_value(self, value: float):
        """value entre 0 et 1."""
        self._value = max(0.0, min(1.0, value))
        self._fill.place(relwidth=self._value)

    def _on_theme_change(self):
        super()._on_theme_change()
        try:
            self._fill.configure(bg=self.c(self._color_key))
        except tk.TclError:
            pass


# ─────────────────────────────────────────────
#  CHAMP DE TEXTE (Input)
# ─────────────────────────────────────────────

class TextInput(ThemedFrame):
    """Champ de saisie stylise avec placeholder et focus."""

    def __init__(
        self, parent,
        placeholder: str = "",
        height: int = INPUT_HEIGHT,
        multiline: bool = False,
        **kwargs
    ):
        super().__init__(parent, bg_key="bg_input", **kwargs)
        self.configure(highlightthickness=1,
                       highlightbackground=self.c("border"),
                       highlightcolor=self.c("border_focus"))

        if multiline:
            self.widget = tk.Text(
                self,
                bg=self.c("bg_input"),
                fg=self.c("text_primary"),
                font=self.font("body"),
                relief="flat",
                insertbackground=self.c("accent_text"),
                selectbackground=self.c("accent_primary"),
                wrap="word",
                padx=PAD_SM,
                pady=PAD_SM,
            )
            self.widget.pack(fill="both", expand=True)
        else:
            self.widget = tk.Entry(
                self,
                bg=self.c("bg_input"),
                fg=self.c("text_primary"),
                font=self.font("body"),
                relief="flat",
                insertbackground=self.c("accent_text"),
                selectbackground=self.c("accent_primary"),
            )
            self.widget.pack(fill="both", expand=True, padx=PAD_SM)

        self._placeholder = placeholder
        self._has_focus    = False

        if placeholder and not multiline:
            self._show_placeholder()
            self.widget.bind("<FocusIn>",  self._on_focus_in)
            self.widget.bind("<FocusOut>", self._on_focus_out)

        self.widget.bind("<FocusIn>",  lambda e: self._set_border("border_focus"))
        self.widget.bind("<FocusOut>", lambda e: self._set_border("border"))

    def _show_placeholder(self):
        self.widget.insert(0, self._placeholder)
        self.widget.configure(fg=self.c("text_muted"))

    def _on_focus_in(self, e):
        if self.widget.get() == self._placeholder:
            self.widget.delete(0, "end")
            self.widget.configure(fg=self.c("text_primary"))

    def _on_focus_out(self, e):
        if not self.widget.get():
            self._show_placeholder()

    def _set_border(self, key: str):
        self.configure(highlightcolor=self.c(key),
                       highlightbackground=self.c(key))

    def get(self) -> str:
        val = self.widget.get() if hasattr(self.widget, "get") else self.widget.get("1.0", "end-1c")
        if val == self._placeholder:
            return ""
        return val

    def set(self, text: str):
        if isinstance(self.widget, tk.Text):
            self.widget.delete("1.0", "end")
            self.widget.insert("1.0", text)
        else:
            self.widget.delete(0, "end")
            self.widget.insert(0, text)

    def clear(self):
        self.set("")

    def _on_theme_change(self):
        try:
            self.configure(
                bg=self.c("bg_input"),
                highlightbackground=self.c("border"),
                highlightcolor=self.c("border_focus"),
            )
            self.widget.configure(
                bg=self.c("bg_input"),
                fg=self.c("text_primary"),
                insertbackground=self.c("accent_text"),
            )
        except tk.TclError:
            pass


# ─────────────────────────────────────────────
#  BADGE RUPTURE
# ─────────────────────────────────────────────

class RuptureBadge(tk.Label, ThemedMixin):
    """Petit badge rond colore identifiant une rupture (R1..R5)."""

    def __init__(self, parent, rupture_key: str, **kwargs):
        self._init_theme()
        color = self.c(f"rupture_{rupture_key[-1]}")

        super().__init__(
            parent,
            text=f" {rupture_key} ",
            font=self.font("btn"),
            bg=color,
            fg="#ffffff",
            padx=PAD_SM,
            pady=2,
            relief="flat",
            **kwargs
        )
        self._rupture_key = rupture_key

    def _on_theme_change(self):
        try:
            color = self.c(f"rupture_{self._rupture_key[-1]}")
            self.configure(bg=color)
        except tk.TclError:
            pass


# ─────────────────────────────────────────────
#  SEPARATEUR
# ─────────────────────────────────────────────

class Separator(ThemedFrame):
    def __init__(self, parent, orient="horizontal", **kwargs):
        super().__init__(parent, bg_key="border", **kwargs)
        if orient == "horizontal":
            self.configure(height=1)
        else:
            self.configure(width=1)


# ─────────────────────────────────────────────
#  SCROLLFRAME
# ─────────────────────────────────────────────

class ScrollFrame(ThemedFrame):
    """Frame avec scrollbar verticale."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.canvas = tk.Canvas(
            self, bg=self.c("bg_primary"),
            highlightthickness=0, bd=0,
        )
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical",
            command=self.canvas.yview,
        )
        self.inner = ThemedFrame(self.canvas, bg_key="bg_primary")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self._window = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_inner_configure(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self._window, width=e.width)

    def _on_mousewheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _on_theme_change(self):
        super()._on_theme_change()
        try:
            self.canvas.configure(bg=self.c("bg_primary"))
            self.inner.configure(bg=self.c("bg_primary"))
        except tk.TclError:
            pass


# ─────────────────────────────────────────────
#  STATUS BAR
# ─────────────────────────────────────────────

class StatusBar(ThemedFrame):
    """Barre de statut en bas de la fenetre."""

    LEVEL_PREFIX = {
        "info":    "•",
        "success": "✓",
        "warning": "!",
        "error":   "✗",
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg_key="bg_sidebar", **kwargs)
        self.configure(height=24)
        self.pack_propagate(False)

        # Indicateur de niveau (point coloré)
        self._dot = tk.Label(
            self, text="•",
            font=("Segoe UI", 14, "bold"),
            bg=self.c("bg_sidebar"),
            fg=self.c("text_muted"),
        )
        self._dot.pack(side="left", padx=(PAD_MD, PAD_XS), pady=0)

        self._status_lbl = ThemedLabel(
            self, text="Pret",
            font_key="caption",
            fg_key="text_secondary",
            bg_key="bg_sidebar",
        )
        self._status_lbl.pack(side="left", padx=(0, PAD_MD), pady=PAD_XS)

        self._right_lbl = ThemedLabel(
            self, text="RiskPulse v1.0",
            font_key="caption",
            fg_key="text_muted",
            bg_key="bg_sidebar",
        )
        self._right_lbl.pack(side="right", padx=PAD_MD, pady=PAD_XS)

        self._progress = ProgressBar(self, height=2)
        self._progress.pack(side="bottom", fill="x")

    def set_status(self, message: str, level: str = "info"):
        colors = {
            "info":    "text_secondary",
            "success": "success",
            "warning": "warning",
            "error":   "error",
        }
        dot_colors = {
            "info":    "accent_text",
            "success": "success",
            "warning": "warning",
            "error":   "error",
        }
        fg = colors.get(level, "text_secondary")
        self._status_lbl.configure(text=message, fg=self.c(fg))
        try:
            self._dot.configure(fg=self.c(dot_colors.get(level, "text_muted")))
        except tk.TclError:
            pass

    def set_progress(self, value: float):
        self._progress.set_value(value)

    def _on_theme_change(self):
        super()._on_theme_change()
        try:
            self.configure(bg=self.c("bg_sidebar"))
            self._status_lbl.configure(bg=self.c("bg_sidebar"))
            self._right_lbl.configure(bg=self.c("bg_sidebar"))
            self._dot.configure(bg=self.c("bg_sidebar"))
        except tk.TclError:
            pass


# ─────────────────────────────────────────────
#  LISTE AVEC STYLE
# ─────────────────────────────────────────────

class StyledListbox(ThemedFrame):
    """Listbox stylisee avec scrollbar."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg_key="bg_input", **kwargs)
        self.configure(highlightthickness=1,
                       highlightbackground=self.c("border"))

        self.listbox = tk.Listbox(
            self,
            bg=self.c("bg_input"),
            fg=self.c("text_primary"),
            font=self.font("body"),
            relief="flat",
            selectbackground=self.c("accent_primary"),
            selectforeground="#ffffff",
            activestyle="none",
            highlightthickness=0,
            bd=0,
        )
        scroll = ttk.Scrollbar(self, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.listbox.pack(fill="both", expand=True, padx=2, pady=2)

    def set_items(self, items: List[str]):
        self.listbox.delete(0, "end")
        for item in items:
            self.listbox.insert("end", item)

    def get_selected(self) -> Optional[str]:
        sel = self.listbox.curselection()
        return self.listbox.get(sel[0]) if sel else None

    def bind_select(self, callback: Callable):
        self.listbox.bind("<<ListboxSelect>>", lambda e: callback(self.get_selected()))

    def _on_theme_change(self):
        super()._on_theme_change()
        try:
            self.configure(bg=self.c("bg_input"),
                           highlightbackground=self.c("border"))
            self.listbox.configure(
                bg=self.c("bg_input"),
                fg=self.c("text_primary"),
                selectbackground=self.c("accent_primary"),
            )
        except tk.TclError:
            pass
