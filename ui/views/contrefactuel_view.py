"""
RiskPulse — Vue Simulations Contrefactuelles
=============================================
Rupture 5 : Modifier le graphe (supprimer/ajouter un lien)
et observer l'impact sur la propagation en temps reel.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from ui.theme import ThemedMixin
from ui.components.widgets import (
    ThemedFrame, ThemedLabel, Button, Card,
    Separator,
)
from ui.constants import PAD_XS, PAD_SM, PAD_MD, PAD_LG


class ContrefactuelView(ThemedFrame):

    def __init__(self, parent, controller, app, **kwargs):
        super().__init__(parent, bg_key="bg_primary", **kwargs)
        self._controller  = controller
        self._app         = app
        self._node_id_map = {}
        self._edge_id_map = {}
        self._init_theme()
        self._build()

    def _build(self):
        self._build_header()
        body = ThemedFrame(self, bg_key="bg_primary")
        body.pack(fill="both", expand=True, padx=PAD_LG, pady=(0, PAD_LG))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)
        self._build_controls(body)
        self._build_results(body)

    def _build_header(self):
        h = ThemedFrame(self, bg_key="bg_primary")
        h.pack(fill="x", padx=PAD_LG, pady=(PAD_LG, PAD_MD))
        left = ThemedFrame(h, bg_key="bg_primary")
        left.pack(side="left", fill="y")
        ThemedLabel(left, text="Simulations What-If",
                    font_key="h1", fg_key="text_primary", bg_key="bg_primary").pack(anchor="w")
        ThemedLabel(left,
                    text="Supprimez ou ajoutez un lien dans le graphe et comparez la propagation avant / apres.",
                    font_key="body_sm", fg_key="text_secondary", bg_key="bg_primary").pack(anchor="w", pady=(2, 0))

    def _build_controls(self, parent):
        left = ThemedFrame(parent, bg_key="bg_primary")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_MD))

        # Source
        src = Card(left, title="Source du risque", bg_key="bg_card")
        src.pack(fill="x", pady=(0, PAD_SM))
        ThemedLabel(src.content, text="Noeud source :", font_key="label",
                    fg_key="text_muted", bg_key="bg_card").pack(anchor="w")
        self._source_var = tk.StringVar(value="Choisir...")
        self._source_cb  = ttk.Combobox(src.content, textvariable=self._source_var,
                                         state="readonly", font=self.font("body_sm"))
        self._source_cb.pack(fill="x", pady=(PAD_XS, PAD_SM))
        ThemedLabel(src.content, text="Intensite :", font_key="label",
                    fg_key="text_muted", bg_key="bg_card").pack(anchor="w")
        self._intensity_var = tk.DoubleVar(value=0.85)
        int_row = ThemedFrame(src.content, bg_key="bg_card")
        int_row.pack(fill="x", pady=(PAD_XS, 0))
        self._int_lbl = ThemedLabel(int_row, text="0.85", font_key="h3",
                                     fg_key="rupture_2", bg_key="bg_card")
        self._int_lbl.pack(side="right", padx=(PAD_SM, 0))
        ttk.Scale(int_row, from_=0.1, to=1.0, orient="horizontal",
                  variable=self._intensity_var,
                  command=lambda v: self._int_lbl.configure(text=f"{float(v):.2f}")
                  ).pack(side="left", fill="x", expand=True, pady=PAD_SM, ipady=4)

        # Supprimer un lien
        rm = Card(left, title="Supprimer un lien existant", bg_key="bg_card",
                  accent_color=self.c("rupture_2"))
        rm.pack(fill="x", pady=(0, PAD_SM))
        ThemedLabel(rm.content, text="Lien a supprimer :", font_key="label",
                    fg_key="text_muted", bg_key="bg_card").pack(anchor="w")
        self._edge_var = tk.StringVar(value="Choisir un lien...")
        self._edge_cb  = ttk.Combobox(rm.content, textvariable=self._edge_var,
                                       state="readonly", font=self.font("body_sm"))
        self._edge_cb.pack(fill="x", pady=(PAD_XS, PAD_SM))
        Button(rm.content, text="Simuler la suppression",
               command=self._run_remove, variant="danger", size="md").pack(fill="x")

        # Ajouter un lien
        add = Card(left, title="Ajouter un nouveau lien", bg_key="bg_card",
                   accent_color=self.c("success"))
        add.pack(fill="x", pady=(0, PAD_SM))
        for label, attr_var, attr_cb in [
            ("Noeud A :", "_add_u_var", "_add_u_cb"),
            ("Noeud B :", "_add_v_var", "_add_v_cb"),
        ]:
            ThemedLabel(add.content, text=label, font_key="label",
                        fg_key="text_muted", bg_key="bg_card").pack(anchor="w")
            var = tk.StringVar(value="Choisir...")
            setattr(self, attr_var, var)
            cb = ttk.Combobox(add.content, textvariable=var,
                               state="readonly", font=self.font("body_sm"))
            cb.pack(fill="x", pady=(PAD_XS, PAD_SM))
            setattr(self, attr_cb, cb)

        ThemedLabel(add.content, text="Poids du nouveau lien :", font_key="label",
                    fg_key="text_muted", bg_key="bg_card").pack(anchor="w")
        self._weight_var = tk.DoubleVar(value=0.5)
        wrow = ThemedFrame(add.content, bg_key="bg_card")
        wrow.pack(fill="x", pady=(PAD_XS, PAD_SM))
        self._weight_lbl = ThemedLabel(wrow, text="0.50", font_key="h3",
                                        fg_key="success", bg_key="bg_card")
        self._weight_lbl.pack(side="right", padx=(PAD_SM, 0))
        ttk.Scale(wrow, from_=0.1, to=1.0, orient="horizontal",
                  variable=self._weight_var,
                  command=lambda v: self._weight_lbl.configure(text=f"{float(v):.2f}")
                  ).pack(side="left", fill="x", expand=True, pady=PAD_SM, ipady=4)
        Button(add.content, text="Simuler l'ajout",
               command=self._run_add, variant="success", size="md").pack(fill="x")

    def _build_results(self, parent):
        right = ThemedFrame(parent, bg_key="bg_primary")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        comp = Card(right, title="Comparaison Avant / Apres", bg_key="bg_card",
                    accent_color=self.c("rupture_5"))
        comp.pack(fill="both", expand=True)

        self._placeholder = ThemedLabel(
            comp.content,
            text="Selectionnez un noeud source et un lien,\npuis lancez une simulation.",
            font_key="body_sm", fg_key="text_muted", bg_key="bg_card")
        self._placeholder.pack(expand=True)

        self._res_frame = ThemedFrame(comp.content, bg_key="bg_card")

        interp = Card(right, title="Interpretation", bg_key="bg_card",
                      accent_color=self.c("accent_primary"))
        interp.pack(fill="x", pady=(PAD_SM, 0))
        self._interp_lbl = ThemedLabel(
            interp.content, text="—",
            font_key="body", fg_key="text_secondary", bg_key="bg_card",
            wraplength=460)
        self._interp_lbl.pack(anchor="w", pady=PAD_SM)

    # ── Actions ───────────────────────────────

    def _run_remove(self):
        if not self._validate_inputs():
            return
        source = self._node_id_map.get(self._source_var.get())
        edge   = self._edge_id_map.get(self._edge_var.get())
        if not edge:
            messagebox.showwarning("Lien manquant", "Selectionnez un lien a supprimer.")
            return
        self._app.set_status("Simulation — suppression du lien...", "info", 0.5)
        intensity = self._intensity_var.get()
        threading.Thread(
            target=lambda: self.after(0, lambda: self._render(
                self._controller.run_counterfactual_remove(source, intensity, *edge)
            )),
            daemon=True
        ).start()

    def _run_add(self):
        if not self._validate_inputs():
            return
        source = self._node_id_map.get(self._source_var.get())
        u = self._node_id_map.get(self._add_u_var.get())
        v = self._node_id_map.get(self._add_v_var.get())
        if not u or not v:
            messagebox.showwarning("Noeuds manquants", "Selectionnez les deux noeuds du nouveau lien.")
            return
        if u == v:
            messagebox.showwarning("Erreur", "Les deux noeuds doivent etre differents.")
            return
        self._app.set_status("Simulation — ajout du lien...", "info", 0.5)
        intensity = self._intensity_var.get()
        weight    = self._weight_var.get()
        threading.Thread(
            target=lambda: self.after(0, lambda: self._render(
                self._controller.run_counterfactual_add(source, intensity, u, v, weight)
            )),
            daemon=True
        ).start()

    def _validate_inputs(self):
        if not self._controller or not self._controller.get_graph():
            messagebox.showwarning("Attention", "Lancez d'abord une analyse de texte.")
            return False
        if not self._node_id_map.get(self._source_var.get()):
            messagebox.showwarning("Noeud manquant", "Selectionnez un noeud source.")
            return False
        return True

    # ── Rendu ─────────────────────────────────

    def _render(self, result: dict):
        if "error" in result:
            messagebox.showerror("Erreur", result["error"])
            self._app.set_status("Erreur simulation", "error")
            return

        self._placeholder.pack_forget()
        self._res_frame.pack(fill="both", expand=True)
        for w in self._res_frame.winfo_children():
            w.destroy()

        impact = result.get("impact", {})
        action = result.get("action", "")

        ThemedLabel(self._res_frame, text=action, font_key="h3",
                    fg_key="accent_text", bg_key="bg_card").pack(anchor="w", pady=(0, PAD_SM))
        # Separator(self._res_frame).pack(fill="x", pady=PAD_SM)

        # Metriques
        mrow = ThemedFrame(self._res_frame, bg_key="bg_card")
        mrow.pack(fill="x", pady=(0, PAD_SM))
        avg_before = impact.get("avg_risk_before", 0)
        avg_after  = impact.get("avg_risk_after",  0)
        delta      = impact.get("avg_risk_delta",  0)
        improved   = len(impact.get("improved_nodes", []))
        worsened   = len(impact.get("worsened_nodes", []))

        for label, val, ck in [
            ("Risque moyen AVANT", f"{avg_before:.3f}", "chart_1"),
            ("Risque moyen APRES", f"{avg_after:.3f}",  "success" if delta <= 0 else "error"),
            ("Delta",              f"{delta:+.3f}",      "success" if delta <= 0 else "error"),
            ("Ameliorations",      str(improved),        "success"),
            ("Degradations",       str(worsened),        "error"),
        ]:
            f = ThemedFrame(mrow, bg_key="bg_card")
            f.pack(side="left", fill="both", expand=True)
            tk.Label(f, text=val, font=self.font("h2"),
                     bg=self.c("bg_card"), fg=self.c(ck)).pack(anchor="center")
            tk.Label(f, text=label, font=self.font("caption"),
                     bg=self.c("bg_card"), fg=self.c("text_muted")).pack(anchor="center")

        # Separator(self._res_frame).pack(fill="x", pady=PAD_SM)

        # Colonnes ameliorations / degradations
        cols = ThemedFrame(self._res_frame, bg_key="bg_card")
        cols.pack(fill="both", expand=True)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        for col, title, nodes, ck in [
            (0, f"Moins exposees ({improved})", impact.get("improved_nodes", []), "success"),
            (1, f"Plus exposees  ({worsened})",  impact.get("worsened_nodes",  []), "error"),
        ]:
            f = ThemedFrame(cols, bg_key="bg_card")
            f.grid(row=0, column=col, sticky="nsew", padx=PAD_XS)
            ThemedLabel(f, text=title, font_key="label",
                        fg_key=ck, bg_key="bg_card").pack(anchor="w", pady=(0, PAD_XS))
            shown = nodes[:8] if nodes else []
            for nid in shown:
                r = ThemedFrame(f, bg_key="bg_card")
                r.pack(fill="x", pady=1)
                tk.Frame(r, width=6, height=6, bg=self.c(ck)
                         ).pack(side="left", anchor="center", padx=(0, PAD_XS))
                tk.Label(r, text=nid.replace("_", " ").title()[:26],
                         font=self.font("body_sm"), bg=self.c("bg_card"),
                         fg=self.c("text_primary"), anchor="w"
                         ).pack(side="left", fill="x")
            if not shown:
                ThemedLabel(f, text="Aucun", font_key="caption",
                            fg_key="text_muted", bg_key="bg_card").pack(anchor="w")

        interp = result.get("interpretation", "")
        ck = "success" if "reduit" in interp.lower() else (
             "error"   if "augmente" in interp.lower() else "text_secondary")
        self._interp_lbl.configure(text=interp, fg=self.c(ck))
        self._app.set_status("Simulation contrefactuelle terminee", "success")

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        if not self._controller:
            return
        nodes = self._controller.get_node_list()
        labels = [n["label"] for n in nodes]
        self._node_id_map = {n["label"]: n["id"] for n in nodes}
        for cb in (self._source_cb, self._add_u_cb, self._add_v_cb):
            cb.configure(values=labels)
        edges = self._controller.get_edge_list()
        self._edge_id_map = {e["label"]: (e["u"], e["v"]) for e in edges}
        self._edge_cb.configure(values=[e["label"] for e in edges])

    def on_show(self):
        if self._controller and self._controller.get_graph():
            self.on_analysis_updated()
