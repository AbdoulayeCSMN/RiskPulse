"""RiskPulse — Vue Comparaison Modeles (Rupture R4)"""
import tkinter as tk
from tkinter import ttk
import threading
from ui.theme import ThemedMixin
from ui.components.widgets import ThemedFrame, ThemedLabel, Button, Card, RuptureBadge, Separator, MetricCard
from ui.constants import PAD_XS, PAD_SM, PAD_MD, PAD_LG

class ComparaisonView(ThemedFrame):
    def __init__(self, parent, controller, app, **kwargs):
        super().__init__(parent, bg_key="bg_primary", **kwargs)
        self._controller = controller; self._app = app; self._init_theme(); self._build()

    def _build(self):
        header = ThemedFrame(self, bg_key="bg_primary")
        header.pack(fill="x", padx=PAD_LG, pady=(PAD_LG, PAD_MD))
        ThemedLabel(header, text="Comparaison des Modeles IA", font_key="h1", fg_key="text_primary", bg_key="bg_primary").pack(side="left")
        RuptureBadge(header, "R4").pack(side="right")

        body = ThemedFrame(self, bg_key="bg_primary")
        body.pack(fill="both", expand=True, padx=PAD_LG, pady=(0, PAD_LG))
        body.columnconfigure(0, weight=1); body.columnconfigure(1, weight=1); body.rowconfigure(1, weight=1)

        # Descriptions des modeles
        for col, title, desc, color in [
            (0, "Modele A — IsolationForest", "Analyse individuelle de chaque entite\nsans tenir compte des relations.", "chart_1"),
            (1, "Modele B — GraphBased", "Analyse structurelle du reseau entier\nvia la topologie des connexions.", "rupture_4"),
        ]:
            card = Card(body, title=title, bg_key="bg_card", accent_color=self.c(color))
            card.grid(row=0, column=col, sticky="ew", padx=(0 if col > 0 else 0, PAD_SM if col == 0 else 0), pady=(0, PAD_SM))
            ThemedLabel(card.content, text=desc, font_key="body_sm", fg_key="text_secondary", bg_key="bg_card", wraplength=300).pack(anchor="w")

        # Resultats
        results_card = Card(body, title="Comparaison des resultats", bg_key="bg_card", accent_color=self.c("rupture_4"))
        results_card.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self._results_frame = ThemedFrame(results_card.content, bg_key="bg_card")
        self._results_frame.pack(fill="both", expand=True)
        ThemedLabel(self._results_frame, text="Lancez une analyse pour voir la comparaison.", font_key="body_sm", fg_key="text_muted", bg_key="bg_card").pack(expand=True)

    def _render(self, comp):
        for w in self._results_frame.winfo_children():
            w.destroy()
        c = comp.get("comparison", {})

        # Stats
        row = ThemedFrame(self._results_frame, bg_key="bg_card")
        row.pack(fill="x", pady=(0, PAD_MD))
        for label, val, color in [
            ("Anomalies A", str(c.get("n_anomalies_a", 0)), "chart_1"),
            ("Anomalies B", str(c.get("n_anomalies_b", 0)), "rupture_4"),
            ("Accord", f"{c.get('agreement_rate', 0):.1%}", "success"),
        ]:
            f = ThemedFrame(row, bg_key="bg_card")
            f.pack(side="left", fill="both", expand=True)
            tk.Label(f, text=val, font=self.font("metric"), bg=self.c("bg_card"), fg=self.c(color)).pack(anchor="center")
            tk.Label(f, text=label, font=self.font("caption"), bg=self.c("bg_card"), fg=self.c("text_muted")).pack(anchor="center")

        Separator(self._results_frame).pack(fill="x", pady=PAD_SM)
        insight = c.get("key_insight", "")
        bg = "success_light" if "convergent" in insight else "warning_light"
        fg = "success" if "convergent" in insight else "warning"
        ThemedLabel(self._results_frame, text=insight, font_key="body", fg_key=fg, bg_key=bg, wraplength=500, pady=PAD_SM).pack(fill="x", padx=PAD_SM)

        only_b = c.get("only_b_detects", [])
        if only_b:
            Separator(self._results_frame).pack(fill="x", pady=PAD_SM)
            ThemedLabel(self._results_frame, text="Entites detectees UNIQUEMENT par le Modele B (risque systemique) :", font_key="label", fg_key="text_secondary", bg_key="bg_card").pack(anchor="w")
            for node in only_b:
                r = ThemedFrame(self._results_frame, bg_key="bg_card")
                r.pack(fill="x", pady=2)
                # Petite pastille ronde au lieu d'un baton
                tk.Label(r, text="•", font=self.font("h3"),
                         bg=self.c("bg_card"), fg=self.c("rupture_4")).pack(side="left", padx=(0, PAD_XS))
                tk.Label(r, text=node["node_name"], font=self.font("body_sm"), bg=self.c("bg_card"), fg=self.c("text_primary"), width=22, anchor="w").pack(side="left", padx=PAD_SM)
                tk.Label(r, text=f"score B = {node['score_b']:.3f}", font=self.font("caption"), bg=self.c("bg_card"), fg=self.c("rupture_4")).pack(side="left")
                tk.Label(r, text=node.get("explanation", "")[:50], font=self.font("caption"), bg=self.c("bg_card"), fg=self.c("text_muted")).pack(side="left", padx=PAD_SM)

    def on_analysis_updated(self):
        if self._controller and self._controller.current_analysis:
            comp = self._controller.current_analysis.get("comparison", {})
            self._render(comp)

    def on_show(self):
        self.on_analysis_updated()
