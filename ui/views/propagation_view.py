"""RiskPulse — Vue Propagation (Ruptures R2 + R3)"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from ui.theme import ThemedMixin
from ui.components.widgets import ThemedFrame, ThemedLabel, Button, Card, RuptureBadge, Separator
from ui.constants import PAD_XS, PAD_SM, PAD_MD, PAD_LG, RISK_COLORS, RISK_LABELS

class PropagationView(ThemedFrame):
    def __init__(self, parent, controller, app, **kwargs):
        super().__init__(parent, bg_key="bg_primary", **kwargs)
        self._controller = controller; self._app = app
        self._node_id_map: dict = {}
        self._init_theme(); self._build()

    def _build(self):
        header = ThemedFrame(self, bg_key="bg_primary")
        header.pack(fill="x", padx=PAD_LG, pady=(PAD_LG, PAD_MD))
        ThemedLabel(header, text="Propagation de Risque", font_key="h1", fg_key="text_primary", bg_key="bg_primary").pack(side="left", anchor="w")
        RuptureBadge(header, "R2").pack(side="right", padx=PAD_SM)
        RuptureBadge(header, "R3").pack(side="right")

        body = ThemedFrame(self, bg_key="bg_primary")
        body.pack(fill="both", expand=True, padx=PAD_LG, pady=(0, PAD_LG))
        body.columnconfigure(0, weight=1); body.columnconfigure(1, weight=2); body.rowconfigure(0, weight=1)

        # Panneau gauche : controles
        ctrl = ThemedFrame(body, bg_key="bg_primary")
        ctrl.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_MD))

        cfg_card = Card(ctrl, title="Configuration de la simulation",
                        bg_key="bg_card", accent_color=self.c("rupture_2"))
        cfg_card.pack(fill="x", pady=(0, PAD_SM))

        ThemedLabel(cfg_card.content, text="Noeud source :", font_key="label", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")
        self._node_var = tk.StringVar(value="Choisir un noeud...")
        self._node_cb = ttk.Combobox(cfg_card.content, textvariable=self._node_var, state="readonly", font=self.font("body_sm"))
        self._node_cb.pack(fill="x", pady=(PAD_XS, PAD_SM))

        ThemedLabel(cfg_card.content, text="Intensite du risque :", font_key="label", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")
        self._intensity_var = tk.DoubleVar(value=0.85)
        intensity_frame = ThemedFrame(cfg_card.content, bg_key="bg_card")
        intensity_frame.pack(fill="x", pady=(PAD_XS, PAD_SM))
        self._intensity_lbl = ThemedLabel(intensity_frame, text="0.85", font_key="h3", fg_key="rupture_2", bg_key="bg_card")
        self._intensity_lbl.pack(side="right", padx=(PAD_SM, 0))
        scale = ttk.Scale(intensity_frame, from_=0.1, to=1.0, orient="horizontal", variable=self._intensity_var,
                          command=lambda v: self._intensity_lbl.configure(text=f"{float(v):.2f}"))
        scale.pack(side="left", fill="x", expand=True, pady=PAD_XS)

        Button(cfg_card.content, text="Simuler la propagation", command=self._run_propagation, variant="danger", size="lg").pack(fill="x", pady=(PAD_SM, 0))

        # Legende
        legend_card = Card(ctrl, title="Legende des etats", bg_key="bg_card")
        legend_card.pack(fill="x", pady=(0, PAD_SM))
        for state, label in RISK_LABELS.items():
            row = ThemedFrame(legend_card.content, bg_key="bg_card")
            row.pack(fill="x", pady=2)
            tk.Frame(row, width=16, height=16, bg=RISK_COLORS[state]).pack(side="left", padx=(0, PAD_SM))
            ThemedLabel(row, text=label, font_key="body_sm", fg_key="text_primary", bg_key="bg_card").pack(side="left", anchor="w")

        # Panneau droit : resultats
        right = ThemedFrame(body, bg_key="bg_primary")
        right.grid(row=0, column=1, sticky="nsew")

        results_card = Card(right, title="Resultats de la propagation", bg_key="bg_card", accent_color=self.c("rupture_2"))
        results_card.pack(fill="both", expand=True)
        self._results_frame = ThemedFrame(results_card.content, bg_key="bg_card")
        self._results_frame.pack(fill="both", expand=True)

        self._placeholder = ThemedLabel(self._results_frame,
            text="Lancez une analyse dans 'Analyse de Texte' puis simulez la propagation.",
            font_key="body_sm", fg_key="text_muted", bg_key="bg_card")
        self._placeholder.pack(expand=True)

        # Nœuds critiques caches
        hidden_card = Card(right, title="Noeuds critiques caches detectes (R3)", bg_key="bg_card", accent_color=self.c("rupture_3"))
        hidden_card.pack(fill="x", pady=(PAD_SM, 0))
        self._hidden_frame = ThemedFrame(hidden_card.content, bg_key="bg_card")
        self._hidden_frame.pack(fill="x")
        ThemedLabel(self._hidden_frame, text="Aucune analyse disponible.", font_key="caption", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")

    def _run_propagation(self):
        if not self._controller or not self._controller.get_graph():
            messagebox.showwarning("Attention", "Lancez d'abord une analyse de texte.")
            return
        label = self._node_var.get()
        if not label or label == "Choisir un noeud...":
            messagebox.showwarning("Noeud manquant", "Selectionnez un noeud source.")
            return
        node_id = self._node_id_map.get(label)
        if not node_id:
            messagebox.showwarning("Noeud invalide", "Noeud source introuvable dans le graphe.")
            return
        intensity = self._intensity_var.get()
        self._app.set_status("Simulation de propagation...", "info", 0.5)

        # Indicateur de progression dans les resultats
        for w in self._results_frame.winfo_children():
            w.destroy()
        prog = ThemedLabel(
            self._results_frame,
            text=f"Simulation depuis '{label}' (intensite {intensity:.2f})...",
            font_key="body_sm", fg_key="accent_text", bg_key="bg_card",
        )
        prog.pack(expand=True, pady=PAD_MD)

        def _run():
            result = self._controller.run_propagation(node_id, intensity)
            self.after(0, lambda: self._render_propagation(result))

        threading.Thread(target=_run, daemon=True).start()

    def _render_propagation(self, result: dict):
        self._app.set_status(f"Propagation terminee : {result.get('n_steps', 0)} etapes", "success")
        for w in self._results_frame.winfo_children():
            w.destroy()

        summary = result.get("summary", {})
        stats_row = ThemedFrame(self._results_frame, bg_key="bg_card")
        stats_row.pack(fill="x", pady=(0, PAD_SM))

        for state in ["critical", "infected", "exposed", "safe"]:
            count = summary.get(state, 0)
            color = RISK_COLORS.get(state, self.c("text_muted"))
            frame = ThemedFrame(stats_row, bg_key="bg_card")
            frame.pack(side="left", fill="both", expand=True)
            tk.Label(frame, text=str(count), font=self.font("h2"), bg=self.c("bg_card"), fg=color).pack(anchor="center")
            tk.Label(frame, text=RISK_LABELS[state], font=self.font("caption"), bg=self.c("bg_card"), fg=self.c("text_muted")).pack(anchor="center")

        # Separator(self._results_frame).pack(fill="x", pady=PAD_SM)

        # Risques par noeud (top 10)
        ThemedLabel(self._results_frame, text="Niveau de risque par entite (top 10) :", font_key="label", fg_key="text_secondary", bg_key="bg_card").pack(anchor="w")

        from engines.propagation_engine import risk_to_state
        risks = result.get("final_risk", {})
        names = result.get("node_names", {})
        sorted_risks = sorted(risks.items(), key=lambda x: x[1], reverse=True)[:10]

        for node_id, risk in sorted_risks:
            state = risk_to_state(risk)
            color = RISK_COLORS.get(state.value, self.c("text_muted"))
            row = ThemedFrame(self._results_frame, bg_key="bg_card")
            row.pack(fill="x", pady=1)
            name = names.get(node_id, node_id).replace("_", " ").title()[:25]
            tk.Label(row, text=name, font=self.font("body_sm"), bg=self.c("bg_card"), fg=self.c("text_primary"), anchor="w", width=22).pack(side="left")
            bar_bg = tk.Frame(row, height=10, bg=self.c("bg_tertiary"), width=120)
            bar_bg.pack(side="left", padx=PAD_SM)
            bar_bg.pack_propagate(False)
            tk.Frame(bar_bg, height=10, bg=color, width=int(120 * risk)).place(x=0, y=0)
            tk.Label(row, text=f"{risk:.2f}", font=self.font("caption"), bg=self.c("bg_card"), fg=color).pack(side="left")

    def on_analysis_updated(self):
        if not self._controller:
            return
        nodes = self._controller.get_node_list()
        labels = [n["label"] for n in nodes]
        self._node_id_map = {n["label"]: n["id"] for n in nodes}
        self._node_cb.configure(values=labels)

        # Pre-selection : noeud le plus critique selon centralite
        analysis = self._controller.current_analysis or {}
        critical = analysis.get("centrality", {}).get("critical_nodes", [])
        if critical and labels:
            top_name = critical[0].get("name")
            # Match insensible a la casse
            for lbl in labels:
                if lbl.lower() == str(top_name).lower():
                    self._node_var.set(lbl)
                    break
            else:
                self._node_var.set(labels[0])
        elif labels:
            self._node_var.set(labels[0])

        # Render hidden critical nodes
        for w in self._hidden_frame.winfo_children():
            w.destroy()
        analysis = self._controller.current_analysis
        hidden = analysis.get("centrality", {}).get("hidden_critical", [])
        if hidden:
            for node in hidden:
                row = ThemedFrame(self._hidden_frame, bg_key="bg_card")
                row.pack(fill="x", pady=1)
                tk.Frame(row, width=8, height=8, bg=self.c("rupture_3")).pack(side="left", padx=(0, PAD_SM), anchor="center")
                tk.Label(row, text=f"{node['name']} — {node.get('reason','')[:50]}", font=self.font("body_sm"), bg=self.c("bg_card"), fg=self.c("warning"), anchor="w").pack(side="left", fill="x")
        else:
            ThemedLabel(self._hidden_frame, text="Aucun noeud cache detecte sur cette analyse.", font_key="caption", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")

    def on_show(self):
        if self._controller and self._controller.get_graph():
            self.on_analysis_updated()
