"""
RiskPulse — Vue Tableau de Bord
=================================
nb donnees traitees, taux d'erreur, temps de traitement.

Affiche :
  - Metriques cles en cartes
  - Comparaison des deux modeles (barres)
  - Distribution des types d'entites (camembert simplifie)
  - Top noeuds critiques
  - Journal des operations
  - Boutons d'export CSV / JSON
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import csv
import os
from datetime import datetime

from ui.theme import ThemedMixin
from ui.components.widgets import (
    ThemedFrame, ThemedLabel, Button, Card,
    MetricCard, ProgressBar, Separator
)
from ui.constants import (
    PAD_XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    DASHBOARD_METRICS,
)


class DashboardView(ThemedFrame):

    def __init__(self, parent, controller, app, **kwargs):
        super().__init__(parent, bg_key="bg_primary", **kwargs)
        self._controller = controller
        self._app        = app
        self._init_theme()
        self._build()

    # ── Construction ──────────────────────────

    def _build(self):
        self._build_header()

        # Zone scrollable
        outer = ThemedFrame(self, bg_key="bg_primary")
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=self.c("bg_primary"), highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self._scroll_frame = ThemedFrame(canvas, bg_key="bg_primary")
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        self._scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(
                canvas.find_withtag("all")[0] if canvas.find_withtag("all") else 1,
                width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._build_metrics_row()
        self._build_models_comparison()
        self._build_bottom_row()
        self._build_log_panel()

        self._render_empty_state()

    def _build_header(self):
        h = ThemedFrame(self, bg_key="bg_primary")
        h.pack(fill="x", padx=PAD_LG, pady=(PAD_LG, PAD_MD))
        left = ThemedFrame(h, bg_key="bg_primary")
        left.pack(side="left", fill="y")
        ThemedLabel(left, text="Tableau de Bord",
                    font_key="h1", fg_key="text_primary", bg_key="bg_primary").pack(anchor="w")
        ThemedLabel(left, text="Vue synthetique de toutes les analyses et metriques IA.",
                    font_key="body_sm", fg_key="text_secondary", bg_key="bg_primary").pack(anchor="w")

        right = ThemedFrame(h, bg_key="bg_primary")
        right.pack(side="right", fill="y")
        Button(right, text="Exporter PDF",
               command=self._export_pdf,
               variant="primary", size="sm").pack(side="right", padx=(PAD_SM, 0))
        Button(right, text="Exporter CSV",
               command=self._export_csv,
               variant="secondary", size="sm").pack(side="right", padx=(PAD_SM, 0))
        Button(right, text="Exporter JSON",
               command=self._export_json,
               variant="secondary", size="sm").pack(side="right")

    def _build_metrics_row(self):
        row = ThemedFrame(self._scroll_frame, bg_key="bg_primary")
        row.pack(fill="x", padx=PAD_LG, pady=(0, PAD_MD))

        self._metric_cards = {}
        metrics = [
            ("nb_entities",      "Entites",       "chart_1"),
            ("nb_relations",     "Relations",      "chart_2"),
            ("model_a_anomalies","Anomalies A",    "chart_3"),
            ("model_b_anomalies","Anomalies B",    "rupture_4"),
            ("processing_time",  "Temps (s)",      "chart_5"),
            ("graph_density",    "Densite",        "accent_primary"),
        ]
        for key, label, color in metrics:
            card = ThemedFrame(row, bg_key="bg_card")
            card.pack(side="left", fill="both", expand=True, padx=(0, PAD_SM))
            #tk.Frame(card, height=3, bg=self.c(color)).pack(fill="x")
            inner = ThemedFrame(card, bg_key="bg_card")
            inner.pack(padx=PAD_MD, pady=PAD_MD)
            val_lbl = tk.Label(inner, text="—", font=self.font("metric"),
                               bg=self.c("bg_card"), fg=self.c(color))
            val_lbl.pack(anchor="center")
            tk.Label(inner, text=label, font=self.font("caption"),
                     bg=self.c("bg_card"), fg=self.c("text_muted")).pack(anchor="center")
            self._metric_cards[key] = val_lbl

    def _build_models_comparison(self):
        comp_card = Card(
            self._scroll_frame,
            title="Comparaison Modele A (IsolationForest) vs Modele B (GraphBased)",
            bg_key="bg_card",
            accent_color=self.c("rupture_4"),
        )
        comp_card.pack(fill="x", padx=PAD_LG, pady=(0, PAD_MD))

        self._comp_frame = ThemedFrame(comp_card.content, bg_key="bg_card")
        self._comp_frame.pack(fill="x")

        self._insight_lbl = ThemedLabel(
            comp_card.content, text="Aucune analyse disponible.",
            font_key="body_sm", fg_key="text_muted", bg_key="bg_card",
            wraplength=700,
        )
        self._insight_lbl.pack(anchor="w", pady=(PAD_SM, 0))

    def _build_bottom_row(self):
        row = ThemedFrame(self._scroll_frame, bg_key="bg_primary")
        row.pack(fill="x", padx=PAD_LG, pady=(0, PAD_MD))
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)

        # Top noeuds critiques
        critical_card = Card(row, title="Top 5 Noeuds Critiques", bg_key="bg_card",
                             accent_color=self.c("rupture_2"))
        critical_card.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM))
        self._critical_frame = ThemedFrame(critical_card.content, bg_key="bg_card")
        self._critical_frame.pack(fill="x")
        ThemedLabel(self._critical_frame, text="En attente d'analyse...",
                    font_key="caption", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")

        # Types d'entites
        types_card = Card(row, title="Repartition des Entites", bg_key="bg_card",
                          accent_color=self.c("chart_2"))
        types_card.grid(row=0, column=1, sticky="nsew")
        self._types_frame = ThemedFrame(types_card.content, bg_key="bg_card")
        self._types_frame.pack(fill="x")
        ThemedLabel(self._types_frame, text="En attente d'analyse...",
                    font_key="caption", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")

    def _build_log_panel(self):
        log_card = Card(self._scroll_frame, title="Journal des operations",
                        bg_key="bg_card")
        log_card.pack(fill="x", padx=PAD_LG, pady=(0, PAD_LG))

        self._log_frame = ThemedFrame(log_card.content, bg_key="bg_card")
        self._log_frame.pack(fill="x")
        ThemedLabel(self._log_frame, text="Aucune operation enregistree.",
                    font_key="caption", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")

    # ── Rendu ─────────────────────────────────

    def _render_empty_state(self):
        pass

    def _render(self, data: dict):
        # Metriques
        for key, lbl in self._metric_cards.items():
            val = data.get(key, "—")
            if isinstance(val, float):
                val = f"{val:.3f}"
            lbl.configure(text=str(val))

        # Comparaison modeles
        for w in self._comp_frame.winfo_children():
            w.destroy()

        a = data.get("model_a_anomalies", 0)
        b = data.get("model_b_anomalies", 0)
        max_val = max(a, b, 1)
        agr = data.get("agreement_rate", 0)

        for label, val, color in [
            ("Modele A — IsolationForest", a, "chart_1"),
            ("Modele B — GraphBased",      b, "rupture_4"),
        ]:
            bar_row = ThemedFrame(self._comp_frame, bg_key="bg_card")
            bar_row.pack(fill="x", pady=2)
            tk.Label(bar_row, text=label, font=self.font("body_sm"),
                     bg=self.c("bg_card"), fg=self.c("text_secondary"),
                     width=30, anchor="w").pack(side="left")
            bar_bg = tk.Frame(bar_row, height=18, bg=self.c("bg_tertiary"))
            bar_bg.pack(side="left", fill="x", expand=True, padx=PAD_SM)
            bar_bg.pack_propagate(False)
            fill_ratio = val / max_val if max_val > 0 else 0
            tk.Frame(bar_bg, height=18, bg=self.c(color)
                     ).place(relx=0, rely=0, relheight=1, relwidth=fill_ratio)
            tk.Label(bar_row, text=str(val), font=self.font("body_sm"),
                     bg=self.c("bg_card"), fg=self.c(color), width=4).pack(side="left")

        # Accord
        accord_row = ThemedFrame(self._comp_frame, bg_key="bg_card")
        accord_row.pack(fill="x", pady=(PAD_SM, 0))
        tk.Label(accord_row, text=f"Taux d'accord : {agr:.1%}",
                 font=self.font("label"), bg=self.c("bg_card"),
                 fg=self.c("success" if agr > 0.7 else "warning")).pack(side="left")

        insight = data.get("key_insight", "")
        color = "success" if "convergent" in insight else "warning"
        self._insight_lbl.configure(text=insight, fg=self.c(color))

        # Top noeuds critiques
        for w in self._critical_frame.winfo_children():
            w.destroy()
        critical = data.get("critical_nodes", [])
        COLORS = ["rupture_2", "rupture_3", "rupture_4", "chart_1", "text_muted"]
        for i, node in enumerate(critical[:5]):
            row = ThemedFrame(self._critical_frame, bg_key="bg_card")
            row.pack(fill="x", pady=1)
            color = self.c(COLORS[i % len(COLORS)])
            tk.Label(row, text=f"#{i+1}", font=self.font("caption"),
                     bg=color, fg="#fff", width=3, pady=2).pack(side="left")
            tk.Label(row, text=node["name"][:24], font=self.font("body_sm"),
                     bg=self.c("bg_card"), fg=self.c("text_primary"),
                     anchor="w").pack(side="left", padx=PAD_SM, fill="x", expand=True)
            tk.Label(row, text=f"{node['composite']:.3f}",
                     font=self.font("caption"),
                     bg=self.c("bg_card"), fg=color).pack(side="right", padx=PAD_SM)
        if not critical:
            ThemedLabel(self._critical_frame, text="Aucune donnee.",
                        font_key="caption", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")

        # Types d'entites
        for w in self._types_frame.winfo_children():
            w.destroy()
        types = data.get("entity_types", {})
        total_ent = sum(types.values()) if types else 1
        type_colors = ["chart_1", "chart_2", "chart_3", "chart_4", "chart_5"]
        for i, (typ, count) in enumerate(sorted(types.items(), key=lambda x: x[1], reverse=True)):
            row = ThemedFrame(self._types_frame, bg_key="bg_card")
            row.pack(fill="x", pady=1)
            color = self.c(type_colors[i % len(type_colors)])
            tk.Label(row, text=typ, font=self.font("body_sm"),
                     bg=self.c("bg_card"), fg=self.c("text_primary"),
                     width=16, anchor="w").pack(side="left")
            bar_bg = tk.Frame(row, height=12, bg=self.c("bg_tertiary"), width=100)
            bar_bg.pack(side="left", padx=PAD_SM)
            bar_bg.pack_propagate(False)
            tk.Frame(bar_bg, height=12, bg=color,
                     width=int(100 * count / total_ent)).place(x=0, y=0)
            tk.Label(row, text=str(count), font=self.font("caption"),
                     bg=self.c("bg_card"), fg=color).pack(side="left")
        if not types:
            ThemedLabel(self._types_frame, text="Aucune donnee.",
                        font_key="caption", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")

        # Journal
        for w in self._log_frame.winfo_children():
            w.destroy()
        logs = data.get("operation_log", [])
        log_colors = {
            "analyze":      "chart_1",
            "propagation":  "rupture_2",
            "counterfactual": "rupture_5",
            "export":       "chart_2",
            "params":       "text_muted",
            "demo":         "chart_3",
            "init":         "text_muted",
        }
        for entry in reversed(logs[-15:]):
            row = ThemedFrame(self._log_frame, bg_key="bg_card")
            row.pack(fill="x", pady=1)
            ts   = entry.get("timestamp", "")[:16]
            op   = entry.get("operation", "")
            msg  = entry.get("message", "")
            color = self.c(log_colors.get(op, "text_muted"))
            tk.Label(row, text=ts, font=self.font("caption"),
                     bg=self.c("bg_card"), fg=self.c("text_muted"),
                     width=14, anchor="w").pack(side="left")
            tk.Label(row, text=f"[{op.upper()}]", font=self.font("caption"),
                     bg=color, fg="#fff", padx=3).pack(side="left", padx=PAD_XS)
            tk.Label(row, text=msg[:70], font=self.font("caption"),
                     bg=self.c("bg_card"), fg=self.c("text_secondary"),
                     anchor="w").pack(side="left", padx=PAD_XS)
        if not logs:
            ThemedLabel(self._log_frame, text="Aucune operation enregistree.",
                        font_key="caption", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")

    # ── Export ────────────────────────────────

    def _export_csv(self):
        if not self._controller or not self._controller.current_analysis:
            messagebox.showwarning("Attention", "Aucune analyse disponible.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Tous", "*.*")],
            initialfile="riskpulse_metriques.csv",
        )
        if not path:
            return
        data = self._controller.get_dashboard_data()
        rows = [
            ["Metrique", "Valeur"],
            ["Entites",         data.get("nb_entities", 0)],
            ["Relations",       data.get("nb_relations", 0)],
            ["Densite",         data.get("graph_density", 0)],
            ["Anomalies A",     data.get("model_a_anomalies", 0)],
            ["Anomalies B",     data.get("model_b_anomalies", 0)],
            ["Accord",          data.get("agreement_rate", 0)],
            ["Temps (s)",       data.get("processing_time", 0)],
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        messagebox.showinfo("Export reussi", f"CSV exporte vers :\n{path}")

    def _export_json(self):
        if not self._controller:
            return
        path = self._controller.export_analysis_json()
        if path:
            messagebox.showinfo("Export reussi", f"JSON exporte vers :\n{path}")

    def _export_pdf(self):
        if not self._controller or not self._controller.current_analysis:
            messagebox.showwarning("Attention", "Aucune analyse disponible.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("Tous", "*.*")],
            initialfile=f"riskpulse_rapport_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        )
        if not path:
            return
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
        except ImportError:
            messagebox.showwarning(
                "ReportLab manquant",
                "Installez reportlab pour l'export PDF :\n    pip install reportlab"
            )
            return

        data = self._controller.get_dashboard_data()
        c = rl_canvas.Canvas(path, pagesize=A4)
        W, H = A4

        # ─ Titre ─
        c.setFillColorRGB(0.165, 0.498, 0.757)
        c.rect(0, H - 3 * cm, W, 3 * cm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(2 * cm, H - 1.6 * cm, "RiskPulse — Rapport d'Analyse")
        c.setFont("Helvetica", 11)
        c.drawString(2 * cm, H - 2.3 * cm,
                     f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}")

        # ─ Metriques ─
        y = H - 4 * cm
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(2 * cm, y, "Metriques cles")
        y -= 0.7 * cm
        c.setFont("Helvetica", 10)
        for label, key, fmt in [
            ("Entites detectees", "nb_entities", "{}"),
            ("Relations extraites", "nb_relations", "{}"),
            ("Densite du graphe", "graph_density", "{:.4f}"),
            ("Composantes connexes", "nb_components", "{}"),
            ("Degre moyen", "avg_degree", "{:.2f}"),
            ("Temps de traitement", "processing_time", "{:.3f} s"),
            ("Anomalies (Modele A)", "model_a_anomalies", "{}"),
            ("Anomalies (Modele B)", "model_b_anomalies", "{}"),
            ("Taux d'accord modeles", "agreement_rate", "{:.1%}"),
        ]:
            val = data.get(key, 0)
            try:
                txt = fmt.format(val)
            except Exception:
                txt = str(val)
            c.drawString(2.3 * cm, y, f"- {label} : {txt}")
            y -= 0.5 * cm

        # ─ Insight ─
        insight = data.get("key_insight", "")
        if insight:
            y -= 0.3 * cm
            c.setFont("Helvetica-Bold", 12)
            c.drawString(2 * cm, y, "Conclusion comparative")
            y -= 0.5 * cm
            c.setFont("Helvetica-Oblique", 10)
            for line in self._wrap(insight, 90):
                c.drawString(2.3 * cm, y, line)
                y -= 0.45 * cm

        # ─ Top noeuds critiques ─
        critical = data.get("critical_nodes", [])
        if critical:
            y -= 0.3 * cm
            c.setFont("Helvetica-Bold", 12)
            c.drawString(2 * cm, y, "Top noeuds critiques")
            y -= 0.55 * cm
            c.setFont("Helvetica", 10)
            for i, n in enumerate(critical[:5], 1):
                line = f"  {i}. {n['name'][:40]}  |  score : {n['composite']:.3f}  |  type : {n.get('type','?')}"
                c.drawString(2.3 * cm, y, line)
                y -= 0.45 * cm

        # ─ Noeuds caches ─
        hidden = data.get("hidden_critical", [])
        if hidden:
            y -= 0.3 * cm
            c.setFont("Helvetica-Bold", 12)
            c.drawString(2 * cm, y, "Noeuds critiques caches (Rupture 3)")
            y -= 0.55 * cm
            c.setFont("Helvetica", 10)
            for n in hidden[:5]:
                line = f"  - {n['name'][:30]} : {n.get('reason','')[:60]}"
                c.drawString(2.3 * cm, y, line)
                y -= 0.45 * cm

        # ─ Pied ─
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(2 * cm, 1.5 * cm,
                     "RiskPulse v1.0 — Cartographie automatique et propagation de risques par IA")

        c.save()
        messagebox.showinfo("Export reussi", f"PDF exporte vers :\n{path}")

    def _wrap(self, text: str, width: int = 90):
        """Découpe simple d'un texte en lignes pour le PDF."""
        words = text.split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 > width:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lines.append(cur)
        return lines

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        if not self._controller:
            return
        data = self._controller.get_dashboard_data()
        if "error" not in data:
            self._render(data)

    def on_show(self):
        self.on_analysis_updated()
