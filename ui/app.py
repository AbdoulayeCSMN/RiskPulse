"""
RiskPulse — Fenetre Principale
================================
Architecture :
  TopBar     — logo, theme toggle, status
  Sidebar    — navigation principale
  ViewRouter — zone centrale qui affiche la vue active

Toutes les vues sont instanciees une seule fois
et montrees/cachees selon la navigation (performance).
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional

from ui.theme import ThemeManager, ThemedMixin
from ui.components.widgets import (
    ThemedFrame, ThemedLabel, Button,
    StatusBar, Separator
)
from ui.constants import (
    APP_NAME, APP_VERSION, APP_SUBTITLE, APP_AUTHOR,
    APP_MIN_WIDTH, APP_MIN_HEIGHT, APP_DEFAULT_W, APP_DEFAULT_H,
    SIDEBAR_WIDTH, SIDEBAR_ITEM_HEIGHT, SIDEBAR_PADDING_X, SIDEBAR_SECTION_H,
    TOPBAR_HEIGHT, NAV_ITEMS,
    PAD_XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    FONT_LOGO, FONT_NAV, FONT_NAV_SM, FONT_H3,
    RUPTURE_LABELS,
)


# ─────────────────────────────────────────────
#  TOPBAR
# ─────────────────────────────────────────────

class TopBar(ThemedFrame):
    """Barre superieure : logo, sous-titre, theme toggle, version."""

    def __init__(self, parent, on_theme_toggle: callable, **kwargs):
        super().__init__(parent, bg_key="bg_topbar", **kwargs)
        self.configure(height=TOPBAR_HEIGHT)
        self.pack_propagate(False)

        # Separateur bas
        # self._border = tk.Frame(self, height=1, bg=self.c("border"))
        # self._border.pack(side="bottom", fill="x")

        # Zone gauche — logo
        left = ThemedFrame(self, bg_key="bg_topbar")
        left.pack(side="left", fill="y", padx=PAD_LG)

        self._logo = ThemedLabel(
            left, text=APP_NAME,
            font_key="logo",
            fg_key="text_logo",
            bg_key="bg_topbar",
        )
        self._logo.pack(side="left", anchor="w", pady=(0, 0))

        # Separateur vertical
        # tk.Frame(left, width=1, bg=self.c("border")).pack(
        #     side="left", fill="y", padx=PAD_MD, pady=PAD_SM
        # )

        self._subtitle = ThemedLabel(
            left, text=APP_SUBTITLE,
            font_key="caption",
            fg_key="text_muted",
            bg_key="bg_topbar",
        )
        self._subtitle.pack(side="left", anchor="w")

        # Zone droite — controls
        right = ThemedFrame(self, bg_key="bg_topbar")
        right.pack(side="right", fill="y", padx=PAD_LG)

        # Theme toggle
        self._theme_btn = Button(
            right,
            text="Mode Clair",
            command=on_theme_toggle,
            variant="ghost",
            size="sm",
        )
        self._theme_btn.pack(side="right", anchor="center", pady=PAD_SM)

        # Version
        ThemedLabel(
            right, text=f"v{APP_VERSION}",
            font_key="caption",
            fg_key="text_muted",
            bg_key="bg_topbar",
        ).pack(side="right", anchor="center", padx=PAD_MD)

    def update_theme_btn(self, is_dark: bool):
        self._theme_btn.configure(
            text="Mode Clair" if is_dark else "Mode Sombre"
        )

    def _on_theme_change(self):
        try:
            self.configure(bg=self.c("bg_topbar"))
            self._border.configure(bg=self.c("border"))
            for child in self.winfo_children():
                if isinstance(child, ThemedFrame):
                    child.configure(bg=self.c("bg_topbar"))
        except tk.TclError:
            pass


# ─────────────────────────────────────────────
#  ITEM DE NAVIGATION
# ─────────────────────────────────────────────

class NavItem(ThemedFrame):
    """
    Item de la sidebar.
    Affiche l'indicateur actif, le label et le badge rupture.
    """

    def __init__(
        self, parent,
        nav_id: str,
        label: str,
        rupture_tag: str,
        on_click: callable,
        **kwargs
    ):
        super().__init__(parent, bg_key="sidebar_item", **kwargs)
        self._nav_id     = nav_id
        self._on_click   = on_click
        self._is_active  = False
        self._rupture    = rupture_tag

        self.configure(height=SIDEBAR_ITEM_HEIGHT, cursor="hand2")
        self.pack_propagate(False)

        # Indicateur laterale gauche (barre coloree)
        # self._indicator = tk.Frame(self, width=3, bg=self.c("sidebar_item"))
        # self._indicator.pack(side="left", fill="y")

        # Zone de contenu
        content = ThemedFrame(self, bg_key="sidebar_item")
        content.pack(side="left", fill="both", expand=True,
                     padx=SIDEBAR_PADDING_X, pady=0)

        # Label principal
        self._label_lbl = ThemedLabel(
            content, text=label,
            font_key="nav",
            fg_key="sidebar_text",
            bg_key="sidebar_item",
        )
        self._label_lbl.pack(side="left", anchor="w")

        # (badges rupture retirés de l'interface)

        # Bindings hover sur tous les enfants
        # Abdoulaye sait self._indicator
        for widget in [self, content, self._label_lbl]:
            widget.bind("<Enter>",    self._on_enter)
            widget.bind("<Leave>",    self._on_leave)
            widget.bind("<Button-1>", self._on_press)

    def _on_enter(self, e=None):
        if not self._is_active:
            self._set_bg("sidebar_item_hover")

    def _on_leave(self, e=None):
        if not self._is_active:
            self._set_bg("sidebar_item")

    def _on_press(self, e=None):
        self._on_click(self._nav_id)

    def set_active(self, active: bool):
        self._is_active = active
        if active:
            self._set_bg("sidebar_item_active")
            self._label_lbl.configure(
                fg=self.c("sidebar_text_active"),
                font=self.font("h3"),
            )
            # self._indicator.configure(bg=self.c("sidebar_indicator"))
        else:
            self._set_bg("sidebar_item")
            self._label_lbl.configure(
                fg=self.c("sidebar_text"),
                font=self.font("nav"),
            )
            # self._indicator.configure(bg=self.c("sidebar_item"))

    def _set_bg(self, key: str):
        try:
            self.configure(bg=self.c(key))
            for w in self.winfo_children():
                w.configure(bg=self.c(key))
                for ww in w.winfo_children():
                    if isinstance(ww, (ThemedFrame, ThemedLabel)):
                        ww.configure(bg=self.c(key))
        except tk.TclError:
            pass

    def _on_theme_change(self):
        self.set_active(self._is_active)


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────

class Sidebar(ThemedFrame):
    """
    Panneau de navigation lateral.
    Contient les items de navigation et la section des ruptures.
    """

    def __init__(self, parent, on_navigate: callable, **kwargs):
        super().__init__(parent, bg_key="bg_sidebar", **kwargs)
        self.configure(width=SIDEBAR_WIDTH)
        self.pack_propagate(False)

        self._items: Dict[str, NavItem] = {}
        self._on_navigate = on_navigate

        self._build_header()
        self._build_nav()
        self._build_ruptures_section()
        self._build_footer()

    def _build_header(self):
        header = ThemedFrame(self, bg_key="bg_sidebar")
        header.pack(fill="x", padx=SIDEBAR_PADDING_X, pady=(PAD_LG, PAD_MD))

        ThemedLabel(
            header, text="NAVIGATION",
            font_key="caption",
            fg_key="text_muted",
            bg_key="bg_sidebar",
        ).pack(anchor="w")

        # Separator(self).pack(fill="x", padx=PAD_MD)

    def _build_nav(self):
        for nav_id, label, rupture in NAV_ITEMS:
            item = NavItem(
                self,
                nav_id=nav_id,
                label=label,
                rupture_tag=rupture,
                on_click=self._on_item_click,
            )
            item.pack(fill="x")
            self._items[nav_id] = item

    def _build_ruptures_section(self):
        pass  # Retiré de l'interface utilisateur

    def _build_footer(self):
        footer = ThemedFrame(self, bg_key="bg_sidebar")
        footer.pack(side="bottom", fill="x", padx=SIDEBAR_PADDING_X, pady=PAD_MD)

        # Separator(self).pack(side="bottom", fill="x", padx=PAD_MD, pady=(0, PAD_SM))

        ThemedLabel(
            footer, text=APP_AUTHOR,
            font_key="caption",
            fg_key="text_muted",
            bg_key="bg_sidebar",
            wraplength=SIDEBAR_WIDTH - 32,
        ).pack(anchor="w")

    def _on_item_click(self, nav_id: str):
        self.set_active(nav_id)
        self._on_navigate(nav_id)

    def set_active(self, nav_id: str):
        for item_id, item in self._items.items():
            item.set_active(item_id == nav_id)

    def _on_theme_change(self):
        super()._on_theme_change()
        try:
            self.configure(bg=self.c("bg_sidebar"))
            for w in self.winfo_children():
                try:
                    w.configure(bg=self.c("bg_sidebar"))
                except tk.TclError:
                    pass
        except tk.TclError:
            pass


# ─────────────────────────────────────────────
#  APPLICATION PRINCIPALE
# ─────────────────────────────────────────────

class RiskPulseApp(tk.Tk):
    """
    Fenetre principale de RiskPulse.

    Architecture :
      - Initialise le ThemeManager
      - Construit TopBar + Sidebar + ViewRouter
      - Charge le RiskController (moteur IA)
      - Gere la navigation entre les vues
    """

    def __init__(self):
        super().__init__()

        # ── HiDPI : ajuste le scaling Tk interne au facteur reel de l'ecran ──
        # Apres SetProcessDpiAwareness, l'ecran a sa vraie densite.
        # On dit a Tk d'utiliser le meme facteur, sinon tout devient minuscule.
        self._apply_hidpi_scaling()

        # ── Theme ──
        self.tm = ThemeManager(initial_theme="dark")

        # ── Fenetre ──
        self.title(f"{APP_NAME} — {APP_SUBTITLE}")
        self.minsize(APP_MIN_WIDTH, APP_MIN_HEIGHT)
        self.geometry(f"{APP_DEFAULT_W}x{APP_DEFAULT_H}")
        self.resizable(True, True)
        self.configure(bg=self.tm.c("bg_primary"))

        # ── Style ttk global ──
        self._configure_ttk_style()

        # ── Controller IA ──
        self._init_controller()

        # ── Layout ──
        self._build_ui()

        # ── Vue initiale ──
        self._navigate("analyse")

        # ── Bindings globaux ──
        self.bind("<Control-d>", lambda e: self._toggle_theme())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Abonnement au theme
        self.tm.subscribe(self._on_theme_change)

    # ── Initialisation ────────────────────────

    def _apply_hidpi_scaling(self):
        """
        Ajuste le scaling Tk au facteur DPI reel de l'ecran.
        Sans ca, apres SetProcessDpiAwareness, tout le texte est minuscule.

        Le facteur tk scaling = points / pixel. Tk considere 72 points = 1 pouce.
        Pour un ecran 96 DPI standard : scaling = 96/72 = 1.333 (= 100%)
        Pour un ecran 144 DPI (150%)  : scaling = 144/72 = 2.0
        """
        import sys
        if sys.platform != "win32":
            return
        try:
            import ctypes
            # GetDpiForSystem : valeur reelle en DPI (96 = 100%, 120 = 125%, 144 = 150%...)
            user32 = ctypes.windll.user32
            try:
                dpi = user32.GetDpiForSystem()
            except AttributeError:
                # Fallback : recupere via DC
                hdc = user32.GetDC(0)
                dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX = 88
                user32.ReleaseDC(0, hdc)

            # Applique le scaling Tk
            scaling = dpi / 72.0
            self.tk.call("tk", "scaling", scaling)

            # Ajuste la geometrie par defaut en consequence
            scale_ratio = dpi / 96.0
            if scale_ratio > 1.05:
                # Sur ecran HiDPI, on doit aussi agrandir la fenetre minimale
                # car les widgets s'agrandissent automatiquement
                pass  # geometrie est en pixels logiques, Tk gere le reste
        except Exception:
            pass

    def _init_controller(self):
        from controller.risk_controller import RiskController
        try:
            self.controller = RiskController(language="fr")
            self._status_msg = "Moteur IA initialise"
        except Exception as e:
            self.controller = None
            self._status_msg = f"Erreur init: {e}"

    def _configure_ttk_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        c = self.tm.c

        # ── Scrollbar moderne, fine, sans fleches ──
        style.layout("Vertical.TScrollbar", [
            ("Vertical.Scrollbar.trough", {"children": [
                ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})
            ], "sticky": "ns"})
        ])
        style.layout("Horizontal.TScrollbar", [
            ("Horizontal.Scrollbar.trough", {"children": [
                ("Horizontal.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})
            ], "sticky": "ew"})
        ])
        style.configure("Vertical.TScrollbar",
            background=c("scrollbar_thumb"),
            troughcolor=c("bg_primary"),
            borderwidth=0, arrowsize=0,
            relief="flat", width=8,
        )
        style.configure("Horizontal.TScrollbar",
            background=c("scrollbar_thumb"),
            troughcolor=c("bg_primary"),
            borderwidth=0, arrowsize=0,
            relief="flat",
        )
        style.map("Vertical.TScrollbar",
            background=[("active", c("accent_primary"))],
        )
        style.map("Horizontal.TScrollbar",
            background=[("active", c("accent_primary"))],
        )

        # ── Combobox moderne ──
        style.configure("TCombobox",
            background=c("bg_input"),
            foreground=c("text_primary"),
            fieldbackground=c("bg_input"),
            selectbackground=c("accent_primary"),
            selectforeground="#ffffff",
            arrowcolor=c("text_secondary"),
            bordercolor=c("border"),
            lightcolor=c("border"),
            darkcolor=c("border"),
            borderwidth=1,
            padding=6,
        )
        style.map("TCombobox",
            fieldbackground=[("readonly", c("bg_input")), ("focus", c("bg_input"))],
            foreground=[("readonly", c("text_primary"))],
            bordercolor=[("focus", c("border_focus")), ("active", c("border_focus"))],
            arrowcolor=[("active", c("accent_text"))],
        )

        # ── Liste deroulante du combobox ──
        self.option_add("*TCombobox*Listbox.background",       c("bg_card"))
        self.option_add("*TCombobox*Listbox.foreground",       c("text_primary"))
        self.option_add("*TCombobox*Listbox.selectBackground", c("accent_primary"))
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.option_add("*TCombobox*Listbox.borderWidth",      0)
        self.option_add("*TCombobox*Listbox.relief",           "flat")
        self.option_add("*TCombobox*Listbox.font",             self.tm.font("body_sm"))

        # ── Scale moderne ──
        style.layout("Horizontal.TScale", [
            ("Horizontal.Scale.trough", {"sticky": "ew", "children": [
                ("Horizontal.Scale.slider", {"side": "left", "sticky": ""})
            ]}),
        ])
        style.configure("Horizontal.TScale",
            background=c("bg_card"),
            troughcolor=c("bg_tertiary"),
            bordercolor=c("bg_tertiary"),
            lightcolor=c("accent_primary"),
            darkcolor=c("accent_primary"),
            sliderthickness=14,
            troughrelief="flat",
        )
        style.map("Horizontal.TScale",
            background=[("active", c("bg_card"))],
        )

        # ── Spinbox moderne ──
        style.configure("TSpinbox",
            fieldbackground=c("bg_input"),
            background=c("bg_input"),
            foreground=c("text_primary"),
            bordercolor=c("border"),
            arrowcolor=c("text_secondary"),
            borderwidth=1,
            padding=6,
        )
        style.map("TSpinbox",
            fieldbackground=[("focus", c("bg_input"))],
            bordercolor=[("focus", c("border_focus"))],
        )

        # ── Notebook (au cas ou on en utiliserait) ──
        style.configure("TNotebook", background=c("bg_primary"), borderwidth=0)
        style.configure("TNotebook.Tab",
            background=c("bg_secondary"),
            foreground=c("text_secondary"),
            padding=(14, 8),
            borderwidth=0,
        )
        style.map("TNotebook.Tab",
            background=[("selected", c("bg_card"))],
            foreground=[("selected", c("accent_text"))],
        )

    # ── Construction UI ───────────────────────

    def _build_ui(self):
        c = self.tm.c

        # TopBar
        self.topbar = TopBar(
            self,
            on_theme_toggle=self._toggle_theme,
        )
        self.topbar.pack(fill="x", side="top")

        # Zone principale
        main = ThemedFrame(self, bg_key="bg_primary")
        main.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = Sidebar(
            main,
            on_navigate=self._navigate,
        )
        self.sidebar.pack(side="left", fill="y")

        # Separateur vertical
        tk.Frame(main, width=1, bg=c("border")).pack(side="left", fill="y")

        # Zone des vues
        self._view_container = ThemedFrame(main, bg_key="bg_primary")
        self._view_container.pack(side="left", fill="both", expand=True)

        # Status bar
        self.status_bar = StatusBar(self)
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.set_status(self._status_msg)

        # Instancie les vues
        self._views: Dict[str, ThemedFrame] = {}
        self._current_view: Optional[str] = None
        self._load_views()

    def _load_views(self):
        """Charge toutes les vues (instanciation unique)."""
        from ui.views.analyse_view import AnalyseView
        from ui.views.propagation_view import PropagationView
        from ui.views.comparaison_view import ComparaisonView
        from ui.views.contrefactuel_view import ContrefactuelView
        from ui.views.traduction_view import TraductionView
        from ui.views.dashboard_view import DashboardView
        from ui.views.parametres_view import ParametresView

        view_classes = {
            "analyse":       AnalyseView,
            "propagation":   PropagationView,
            "comparaison":   ComparaisonView,
            "contrefactuel": ContrefactuelView,
            "traduction":    TraductionView,
            "dashboard":     DashboardView,
            "parametres":    ParametresView,
        }

        for view_id, ViewClass in view_classes.items():
            try:
                wrapper = self._make_scrollable_wrapper()
                view = ViewClass(
                    wrapper["inner"],
                    controller=self.controller,
                    app=self,
                )
                view.pack(fill="both", expand=True)
                wrapper["outer"].place(relx=0, rely=0, relwidth=1, relheight=1)
                wrapper["outer"].lower()
                # On stocke a la fois le wrapper (pour navigation) et la vue
                wrapper["view"] = view
                self._views[view_id] = wrapper
            except Exception as e:
                fallback = ThemedFrame(self._view_container, bg_key="bg_primary")
                ThemedLabel(
                    fallback, text=f"Vue '{view_id}' non disponible : {e}",
                    fg_key="error", bg_key="bg_primary",
                ).pack(expand=True)
                fallback.place(relx=0, rely=0, relwidth=1, relheight=1)
                fallback.lower()
                self._views[view_id] = {"outer": fallback, "view": fallback, "inner": fallback}

    def _make_scrollable_wrapper(self) -> dict:
        """
        Cree un conteneur scrollable :
            outer (Frame)
              |- canvas (Canvas)
              |   |- inner (Frame)  <-- la vue est packee ici
              |- vscroll (Scrollbar)
        """
        outer = ThemedFrame(self._view_container, bg_key="bg_primary")

        canvas = tk.Canvas(
            outer, bg=self.tm.c("bg_primary"),
            highlightthickness=0, bd=0,
        )
        vscroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)

        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = ThemedFrame(canvas, bg_key="bg_primary")
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _sync_inner_size():
            """Synchronise inner avec canvas : remplit toujours, scroll si deborde."""
            canvas.update_idletasks()
            cw = canvas.winfo_width()
            ch = canvas.winfo_height()
            inner.update_idletasks()
            req_h = inner.winfo_reqheight()
            # inner.width = canvas.width (toujours)
            # inner.height = max(canvas.height, contenu) -> remplit OU scroll
            target_h = max(ch, req_h)
            canvas.itemconfig(window_id, width=cw, height=target_h)
            canvas.configure(scrollregion=(0, 0, cw, target_h))
            # Masque ou montre la scrollbar selon besoin
            if req_h <= ch:
                vscroll.pack_forget()
            else:
                vscroll.pack(side="right", fill="y", before=canvas)

        def _on_inner_configure(e):
            _sync_inner_size()

        def _on_canvas_configure(e):
            _sync_inner_size()

        def _on_mousewheel(e):
            if canvas.bbox("all") and canvas.bbox("all")[3] > canvas.winfo_height():
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        return {"outer": outer, "canvas": canvas, "inner": inner, "vscroll": vscroll}

    # ── Navigation ────────────────────────────

    def _navigate(self, view_id: str):
        if view_id not in self._views:
            return

        # Cache la vue courante
        if self._current_view and self._current_view in self._views:
            self._views[self._current_view]["outer"].lower()

        # Affiche la nouvelle vue
        wrapper = self._views[view_id]
        wrapper["outer"].lift()
        self._current_view = view_id
        self.sidebar.set_active(view_id)

        # Notification a la vue
        view = wrapper.get("view")
        if view is not None and hasattr(view, "on_show"):
            view.on_show()

    # ── Theme ─────────────────────────────────

    def _toggle_theme(self):
        self.tm.toggle_dark_light()
        self.topbar.update_theme_btn(self.tm.is_dark)
        self._configure_ttk_style()

    def _on_theme_change(self):
        try:
            self.configure(bg=self.tm.c("bg_primary"))
        except tk.TclError:
            pass

    # ── API pour les vues ─────────────────────

    def set_status(self, message: str, level: str = "info", progress: float = -1):
        self.status_bar.set_status(message, level)
        if progress >= 0:
            self.status_bar.set_progress(progress)

    def notify_analysis_done(self):
        """Appelee par AnalyseView apres une analyse reussie."""
        for view_id, wrapper in self._views.items():
            view = wrapper.get("view") if isinstance(wrapper, dict) else wrapper
            if view is not None and hasattr(view, "on_analysis_updated"):
                view.on_analysis_updated()

    # ── Fermeture ─────────────────────────────

    def _on_close(self):
        if self.controller:
            try:
                self.controller.save_log()
            except Exception:
                pass
        self.tm.unsubscribe(self._on_theme_change)
        self.destroy()

    def run(self):
        self.mainloop()
