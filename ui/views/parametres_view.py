"""
RiskPulse — Vue Parametres
============================

Fonctionnalites :
  - Choix du modele IA actif
  - Reglage des seuils (contamination, decay, max_steps)
  - Choix des langues de traduction
  - Reglage du mode de prediction
  - Changement de theme (dark / light / midnight)
  - Langue de l'interface
  - Reinitialisation des parametres par defaut
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict

from ui.theme import ThemeManager, ThemedMixin
from ui.components.widgets import (
    ThemedFrame, ThemedLabel, Button, Card,
    Separator,
)
from ui.constants import (
    PAD_XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    LANGUAGES,
)


# Valeurs par defaut des parametres IA
DEFAULTS = {
    "contamination": 0.10,
    "n_estimators":  100,
    "decay":         0.30,
    "max_steps":     50,
    "top_n_critical": 5,
    "language":      "fr",
    "theme":         "dark",
    "propagation_speed": 1.0,
    "convergence_threshold": 0.001,
}


class ParametresView(ThemedFrame):

    def __init__(self, parent, controller, app, **kwargs):
        super().__init__(parent, bg_key="bg_primary", **kwargs)
        self._controller = controller
        self._app        = app
        self._init_theme()
        self._vars: Dict[str, tk.Variable] = {}
        self._build()

    # ── Construction ──────────────────────────

    def _build(self):
        self._build_header()
        body = ThemedFrame(self, bg_key="bg_primary")
        body.pack(fill="both", expand=True, padx=PAD_LG, pady=(0, PAD_LG))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(2, weight=1)

        self._build_model_a_section(body)
        self._build_propagation_section(body)
        self._build_interface_section(body)
        self._build_analysis_section(body)
        self._build_actions(body)

    def _build_header(self):
        h = ThemedFrame(self, bg_key="bg_primary")
        h.pack(fill="x", padx=PAD_LG, pady=(PAD_LG, PAD_MD))
        ThemedLabel(h, text="Parametres",
                    font_key="h1", fg_key="text_primary", bg_key="bg_primary").pack(side="left")
        ThemedLabel(h,
                    text="Configurez les modeles IA, les seuils et les preferences d'interface.",
                    font_key="body_sm", fg_key="text_secondary",
                    bg_key="bg_primary").pack(side="left", padx=PAD_LG, anchor="center")

    # ── Section Modele A ──────────────────────

    def _build_model_a_section(self, parent):
        card = Card(parent, title="Modele A — IsolationForest", bg_key="bg_card",
                    accent_color=self.c("chart_1"))
        card.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM), pady=(0, PAD_SM))

        self._make_slider(
            card.content,
            key="contamination",
            label="Taux de contamination",
            description="Proportion estimee d'anomalies dans les donnees.",
            from_=0.01, to=0.5, resolution=0.01, default=DEFAULTS["contamination"],
            format_fn=lambda v: f"{float(v):.2f}",
        )
        # Separator(card.content).pack(fill="x", pady=PAD_SM)
        self._make_spinbox(
            card.content,
            key="n_estimators",
            label="Nombre d'arbres (n_estimators)",
            description="Plus d'arbres = plus precis mais plus lent.",
            from_=10, to=500, increment=10, default=DEFAULTS["n_estimators"],
        )
        # Separator(card.content).pack(fill="x", pady=PAD_SM)
        self._make_spinbox(
            card.content,
            key="top_n_critical",
            label="Nombre de noeuds critiques affiches",
            description="Top N noeuds a afficher dans les resultats.",
            from_=3, to=20, increment=1, default=DEFAULTS["top_n_critical"],
        )

    # ── Section Propagation ───────────────────

    def _build_propagation_section(self, parent):
        card = Card(parent, title="Moteur de Propagation (Rupture R2)", bg_key="bg_card",
                    accent_color=self.c("rupture_2"))
        card.grid(row=0, column=1, sticky="nsew", pady=(0, PAD_SM))

        self._make_slider(
            card.content,
            key="decay",
            label="Coefficient d'amortissement",
            description="Attenuation du risque a chaque saut dans le reseau.",
            from_=0.0, to=0.9, resolution=0.05, default=DEFAULTS["decay"],
            format_fn=lambda v: f"{float(v):.2f}",
        )
        # Separator(card.content).pack(fill="x", pady=PAD_SM)
        self._make_spinbox(
            card.content,
            key="max_steps",
            label="Nombre maximum d'etapes",
            description="La simulation s'arrete apres ce nombre d'iterations.",
            from_=5, to=200, increment=5, default=DEFAULTS["max_steps"],
        )
        # Separator(card.content).pack(fill="x", pady=PAD_SM)
        self._make_slider(
            card.content,
            key="propagation_speed",
            label="Vitesse de propagation",
            description="Multiplicateur de vitesse pour la simulation.",
            from_=0.1, to=3.0, resolution=0.1, default=DEFAULTS["propagation_speed"],
            format_fn=lambda v: f"{float(v):.1f}x",
        )

    # ── Section Interface ─────────────────────

    def _build_interface_section(self, parent):
        card = Card(parent, title="Interface et Affichage", bg_key="bg_card",
                    accent_color=self.c("accent_primary"))
        card.grid(row=1, column=0, sticky="nsew", padx=(0, PAD_SM), pady=(0, PAD_SM))

        # Theme
        ThemedLabel(card.content, text="Theme de l'interface :",
                    font_key="label", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")
        self._vars["theme"] = tk.StringVar(value=DEFAULTS["theme"])
        themes_row = ThemedFrame(card.content, bg_key="bg_card")
        themes_row.pack(fill="x", pady=(PAD_XS, PAD_MD))
        for theme_id, theme_label in [("dark", "Sombre"), ("light", "Clair"), ("midnight", "Minuit")]:
            rb = tk.Radiobutton(
                themes_row,
                text=theme_label,
                value=theme_id,
                variable=self._vars["theme"],
                bg=self.c("bg_card"),
                fg=self.c("text_primary"),
                selectcolor=self.c("accent_light"),
                activebackground=self.c("bg_card"),
                activeforeground=self.c("text_primary"),
                font=self.font("body_sm"),
                command=lambda t=theme_id: self._preview_theme(t),
            )
            rb.pack(side="left", padx=PAD_SM)

        # Separator(card.content).pack(fill="x", pady=PAD_SM)

        # Langue NLP
        ThemedLabel(card.content, text="Langue d'analyse NLP :",
                    font_key="label", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")
        self._vars["language"] = tk.StringVar(value="Francais")
        lang_labels = {"fr": "Francais", "en": "Anglais"}
        ttk.Combobox(
            card.content,
            textvariable=self._vars["language"],
            values=list(lang_labels.values()),
            state="readonly",
            font=self.font("body_sm"),
        ).pack(fill="x", pady=(PAD_XS, PAD_MD))

    # ── Section Analyse ───────────────────────

    def _build_analysis_section(self, parent):
        card = Card(parent, title="Parametres d'Analyse", bg_key="bg_card",
                    accent_color=self.c("chart_2"))
        card.grid(row=1, column=1, sticky="nsew", pady=(0, PAD_SM))

        # Langues de traduction
        ThemedLabel(card.content, text="Langues de traduction disponibles :",
                    font_key="label", fg_key="text_muted", bg_key="bg_card").pack(anchor="w", pady=(0, PAD_XS))
        self._lang_vars: Dict[str, tk.BooleanVar] = {}
        lang_row = ThemedFrame(card.content, bg_key="bg_card")
        lang_row.pack(fill="x", pady=(0, PAD_MD))
        defaults_on = {"fr", "ar", "en"}
        for code, label in LANGUAGES.items():
            var = tk.BooleanVar(value=code in defaults_on)
            self._lang_vars[code] = var
            cb = tk.Checkbutton(
                lang_row, text=label, variable=var,
                bg=self.c("bg_card"), fg=self.c("text_primary"),
                selectcolor=self.c("accent_light"),
                activebackground=self.c("bg_card"),
                font=self.font("body_sm"),
            )
            cb.pack(side="left", padx=PAD_SM)

        # Separator(card.content).pack(fill="x", pady=PAD_SM)

        # Seuil de convergence
        self._make_slider(
            card.content,
            key="convergence_threshold",
            label="Seuil de convergence",
            description="Delta minimum pour arreter la propagation.",
            from_=0.0001, to=0.01, resolution=0.0001,
            default=DEFAULTS["convergence_threshold"],
            format_fn=lambda v: f"{float(v):.4f}",
        )

        # Separator(card.content).pack(fill="x", pady=PAD_SM)

        # Info modele B
        info = ThemedFrame(card.content, bg_key="info_light")
        info.pack(fill="x", pady=(0, PAD_SM))
        ThemedLabel(info,
            text="  Modele B (GraphBased) : aucun parametre externe.\n  Le scoring est derive de la topologie du graphe.",
            font_key="caption", fg_key="info", bg_key="info_light",
        ).pack(anchor="w", pady=PAD_SM, padx=PAD_SM)

    # ── Boutons d'action ──────────────────────

    def _build_actions(self, parent):
        actions = ThemedFrame(parent, bg_key="bg_primary")
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(PAD_SM, 0))

        Button(actions, text="Appliquer les parametres",
               command=self._apply,
               variant="primary", size="lg").pack(side="left")
        Button(actions, text="Reinitialiser les valeurs par defaut",
               command=self._reset,
               variant="ghost", size="md").pack(side="left", padx=PAD_SM)

        self._applied_lbl = ThemedLabel(
            actions, text="",
            font_key="body_sm", fg_key="success", bg_key="bg_primary")
        self._applied_lbl.pack(side="left", padx=PAD_MD)

    # ── Widgets helpers ───────────────────────

    def _make_slider(self, parent, key, label, description,
                     from_, to, resolution, default, format_fn=None):
        ThemedLabel(parent, text=label, font_key="label",
                    fg_key="text_secondary", bg_key="bg_card").pack(anchor="w")
        if description:
            ThemedLabel(parent, text=description, font_key="caption",
                        fg_key="text_muted", bg_key="bg_card").pack(anchor="w")
        var = tk.DoubleVar(value=default)
        self._vars[key] = var
        row = ThemedFrame(parent, bg_key="bg_card")
        row.pack(fill="x", pady=(PAD_XS, PAD_SM))
        fmt = format_fn or (lambda v: f"{float(v):.3f}")
        val_lbl = ThemedLabel(row, text=fmt(default), font_key="h3",
                               fg_key="accent_text", bg_key="bg_card")
        val_lbl.pack(side="right", padx=(PAD_SM, 0))
        ttk.Scale(
            row, from_=from_, to=to,
            orient="horizontal", variable=var,
            command=lambda v: val_lbl.configure(text=fmt(v)),
        ).pack(side="left", fill="x", expand=True, pady=PAD_XS)

    def _make_spinbox(self, parent, key, label, description, from_, to, increment, default):
        ThemedLabel(parent, text=label, font_key="label",
                    fg_key="text_secondary", bg_key="bg_card").pack(anchor="w")
        if description:
            ThemedLabel(parent, text=description, font_key="caption",
                        fg_key="text_muted", bg_key="bg_card").pack(anchor="w")
        var = tk.IntVar(value=default)
        self._vars[key] = var
        sb = ttk.Spinbox(
            parent, from_=from_, to=to, increment=increment,
            textvariable=var, font=self.font("body_sm"), width=10,
        )
        sb.pack(anchor="w", pady=(PAD_XS, PAD_SM))

    # ── Actions ───────────────────────────────

    def _preview_theme(self, theme_id: str):
        """Apercu du theme sans appliquer les autres parametres."""
        ThemeManager.instance().set_theme(theme_id)
        self._app.topbar.update_theme_btn(ThemeManager.instance().is_dark)

    def _apply(self):
        if not self._controller:
            messagebox.showwarning("Attention", "Controleur IA non disponible.")
            return

        lang_label = self._vars.get("language", tk.StringVar()).get()
        lang_code  = {v: k for k, v in {"fr": "Francais", "en": "Anglais"}.items()}.get(lang_label, "fr")

        params = {
            "contamination":           float(self._vars["contamination"].get()),
            "n_estimators":            int(self._vars["n_estimators"].get()),
            "decay":                   float(self._vars["decay"].get()),
            "max_steps":               int(self._vars["max_steps"].get()),
            "top_n_critical":          int(self._vars["top_n_critical"].get()),
            "language":                lang_code,
            "convergence_threshold":   float(self._vars["convergence_threshold"].get()),
        }

        self._controller.set_model_params(params)

        # Theme
        theme = self._vars.get("theme", tk.StringVar(value="dark")).get()
        ThemeManager.instance().set_theme(theme)
        self._app.topbar.update_theme_btn(ThemeManager.instance().is_dark)

        self._applied_lbl.configure(text="Parametres appliques avec succes.")
        self.after(3000, lambda: self._applied_lbl.configure(text=""))
        self._app.set_status("Parametres IA mis a jour", "success")

    def _reset(self):
        if not messagebox.askyesno("Reinitialiser",
                "Reinitialiser tous les parametres aux valeurs par defaut ?"):
            return
        mappings = {
            "contamination":         DEFAULTS["contamination"],
            "n_estimators":          DEFAULTS["n_estimators"],
            "decay":                 DEFAULTS["decay"],
            "max_steps":             DEFAULTS["max_steps"],
            "top_n_critical":        DEFAULTS["top_n_critical"],
            "propagation_speed":     DEFAULTS["propagation_speed"],
            "convergence_threshold": DEFAULTS["convergence_threshold"],
        }
        for key, val in mappings.items():
            if key in self._vars:
                self._vars[key].set(val)

        if "theme" in self._vars:
            self._vars["theme"].set(DEFAULTS["theme"])
            ThemeManager.instance().set_theme(DEFAULTS["theme"])
            self._app.topbar.update_theme_btn(ThemeManager.instance().is_dark)

        self._applied_lbl.configure(text="Valeurs par defaut restaurees.")
        self.after(3000, lambda: self._applied_lbl.configure(text=""))

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        pass

    def on_show(self):
        pass
