"""
RiskPulse — Vue Module de Traduction
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import json
from datetime import datetime
from typing import List, Dict, Optional

from ui.theme import ThemedMixin
from ui.components.widgets import (
    ThemedFrame, ThemedLabel, Button, Card, Separator,
)
from ui.constants import PAD_XS, PAD_SM, PAD_MD, PAD_LG, LANGUAGES, FILETYPES_JSON


class TraductionView(ThemedFrame):

    def __init__(self, parent, controller, app, **kwargs):
        super().__init__(parent, bg_key="bg_primary", **kwargs)
        self._controller = controller
        self._app        = app
        self._history: List[Dict] = []
        self._current_translation: Optional[str] = None
        self._init_theme()
        self._build()

    # ─────────────────────────────────────────
    #  CONSTRUCTION
    # ─────────────────────────────────────────

    def _build(self):
        self._build_header()
        body = ThemedFrame(self, bg_key="bg_primary")
        body.pack(fill="both", expand=True, padx=PAD_LG, pady=(0, PAD_LG))

        pane = tk.PanedWindow(
            body, orient="horizontal",
            bg=self.c("bg_primary"), sashwidth=6, sashrelief="flat", bd=0,
        )
        pane.pack(fill="both", expand=True)

        left = ThemedFrame(pane, bg_key="bg_primary")
        pane.add(left, minsize=400)
        self._build_translation_panel(left)

        right = ThemedFrame(pane, bg_key="bg_primary")
        pane.add(right, minsize=260)
        self._build_history_panel(right)

    def _build_header(self):
        h = ThemedFrame(self, bg_key="bg_primary")
        h.pack(fill="x", padx=PAD_LG, pady=(PAD_LG, PAD_MD))
        ThemedLabel(h, text="Traduction",
                    font_key="h1", fg_key="text_primary", bg_key="bg_primary").pack(side="left")

    def _build_translation_panel(self, parent):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        # Toolbar
        toolbar = Card(parent, bg_key="bg_card")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, PAD_SM))
        toolbar.content.columnconfigure(1, weight=1)

        row1 = ThemedFrame(toolbar.content, bg_key="bg_card")
        row1.pack(fill="x", pady=(0, PAD_SM))

        ThemedLabel(row1, text="Rapport :", font_key="label",
                    fg_key="text_muted", bg_key="bg_card").pack(side="left", anchor="center", padx=(0, PAD_SM))

        self._src_type_var = tk.StringVar(value="Rapport d'analyse complet")
        ttk.Combobox(
            row1, textvariable=self._src_type_var,
            values=[
                "Rapport d'analyse complet",
                "Noeuds critiques",
                "Comparaison des modeles",
                "Texte personnalise",
            ],
            state="readonly", width=30, font=self.font("body_sm"),
        ).pack(side="left")

        ThemedLabel(row1, text="Vers :", font_key="label",
                    fg_key="text_muted", bg_key="bg_card").pack(side="left", anchor="center", padx=(PAD_MD, PAD_SM))

        self._lang_var = tk.StringVar(value="Arabe")
        ttk.Combobox(
            row1, textvariable=self._lang_var,
            values=list(LANGUAGES.values()),
            state="readonly", width=12, font=self.font("body_sm"),
        ).pack(side="left")

        row2 = ThemedFrame(toolbar.content, bg_key="bg_card")
        row2.pack(fill="x")

        Button(row2, text="Traduire", command=self._run_translation,
               variant="primary", size="md").pack(side="left")
        Button(row2, text="Exporter PDF", command=self._export_pdf,
               variant="secondary", size="sm").pack(side="left", padx=PAD_SM)
        Button(row2, text="Effacer", command=self._clear,
               variant="ghost", size="sm").pack(side="right")

        # Zones source / traduit
        panels = ThemedFrame(parent, bg_key="bg_primary")
        panels.grid(row=1, column=0, sticky="nsew")
        panels.rowconfigure(0, weight=1)
        panels.columnconfigure(0, weight=1)
        panels.columnconfigure(1, weight=1)

        # Source
        src_card = Card(panels, title="Texte source", bg_key="bg_card")
        src_card.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_XS))
        src_card.content.rowconfigure(0, weight=1)
        self._src_text = self._make_textbox(src_card.content, editable=True)

        # Traduit
        tgt_card = Card(panels, title="Texte traduit", bg_key="bg_card",
                        accent_color=self.c("accent_primary"))
        tgt_card.grid(row=0, column=1, sticky="nsew", padx=(PAD_XS, 0))
        tgt_card.content.rowconfigure(0, weight=1)
        self._status_lbl = ThemedLabel(
            tgt_card.content, text="",
            font_key="caption", fg_key="text_muted", bg_key="bg_card")
        self._status_lbl.pack(anchor="w")
        self._tgt_text = self._make_textbox(tgt_card.content, editable=False)

        # Evaluation
        rating_card = Card(parent, title="Evaluer la qualite", bg_key="bg_card")
        rating_card.grid(row=2, column=0, sticky="ew", pady=(PAD_SM, 0))

        rrow = ThemedFrame(rating_card.content, bg_key="bg_card")
        rrow.pack(fill="x")
        self._rating_var = tk.IntVar(value=0)
        self._star_btns = []
        for i in range(1, 6):
            b = tk.Label(rrow, text="☆", font=(self.font("h2")[0], 18),
                         bg=self.c("bg_card"), fg=self.c("text_muted"), cursor="hand2")
            b.pack(side="left", padx=1)
            b.bind("<Button-1>", lambda e, v=i: self._set_rating(v))
            b.bind("<Enter>",    lambda e, v=i: self._hover_stars(v))
            b.bind("<Leave>",    lambda e: self._hover_stars(self._rating_var.get()))
            self._star_btns.append(b)

        Button(rrow, text="Enregistrer", command=self._save_rating,
               variant="secondary", size="sm").pack(side="right")

    def _make_textbox(self, parent, editable: bool) -> tk.Text:
        frame = ThemedFrame(parent, bg_key="bg_card")
        frame.pack(fill="both", expand=True, pady=(PAD_XS, 0))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        t = tk.Text(
            frame,
            bg=self.c("bg_input"), fg=self.c("text_primary"),
            font=self.font("body_sm"), relief="flat",
            wrap="word", padx=PAD_SM, pady=PAD_SM,
            height=8, width=30,
            insertbackground=self.c("accent_text"),
            highlightthickness=1,
            highlightbackground=self.c("border"),
            highlightcolor=self.c("border_focus"),
            state="normal" if editable else "disabled",
        )
        sc = ttk.Scrollbar(frame, command=t.yview)
        t.configure(yscrollcommand=sc.set)
        sc.grid(row=0, column=1, sticky="ns")
        t.grid(row=0, column=0, sticky="nsew")
        return t

    def _build_history_panel(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        card = Card(parent, title="Historique", bg_key="bg_card")
        card.grid(row=0, column=0, sticky="nsew")

        # Toolbar (pack — coherent avec le titre du Card)
        th = ThemedFrame(card.content, bg_key="bg_card")
        th.pack(fill="x", pady=(0, PAD_XS))
        Button(th, text="Exporter", command=self._export_history,
               variant="ghost", size="sm").pack(side="right")
        Button(th, text="Effacer", command=self._clear_history,
               variant="ghost", size="sm").pack(side="right", padx=(0, PAD_XS))

        # Separator(card.content).pack(fill="x", pady=(0, PAD_XS))

        # Zone scrollable
        scroll_wrap = ThemedFrame(card.content, bg_key="bg_card")
        scroll_wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(scroll_wrap, bg=self.c("bg_card"), highlightthickness=0)
        sc = ttk.Scrollbar(scroll_wrap, command=canvas.yview)
        self._hist_inner = ThemedFrame(canvas, bg_key="bg_card")
        canvas.create_window((0, 0), window=self._hist_inner, anchor="nw")
        canvas.configure(yscrollcommand=sc.set)
        self._hist_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(1, width=e.width))
        sc.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Stats
        stats_card = Card(parent, title="Statistiques", bg_key="bg_card")
        stats_card.grid(row=1, column=0, sticky="ew", pady=(PAD_SM, 0))
        sr = ThemedFrame(stats_card.content, bg_key="bg_card")
        sr.pack(fill="x")
        self._st_total  = self._mini_stat(sr, "0",  "Traductions")
        self._st_rating = self._mini_stat(sr, "—",  "Note moy.")
        self._st_langs  = self._mini_stat(sr, "0",  "Langues")

    def _mini_stat(self, parent, val, label) -> ThemedLabel:
        f = ThemedFrame(parent, bg_key="bg_card")
        f.pack(side="left", fill="both", expand=True)
        v = ThemedLabel(f, text=val, font_key="h2", fg_key="accent_text", bg_key="bg_card")
        v.pack(anchor="center", pady=(PAD_SM, 0))
        ThemedLabel(f, text=label, font_key="caption",
                    fg_key="text_muted", bg_key="bg_card").pack(anchor="center", pady=(0, PAD_SM))
        return v

    # ─────────────────────────────────────────
    #  TRADUCTION
    # ─────────────────────────────────────────

    def _run_translation(self):
        text = self._get_source_text()
        if not text.strip():
            messagebox.showwarning("Texte vide",
                "Aucun texte a traduire. Lancez d'abord une analyse ou choisissez 'Texte personnalise'.")
            return

        lang_label = self._lang_var.get()
        lang_code  = {v: k for k, v in LANGUAGES.items()}.get(lang_label, "en")

        self._status_lbl.configure(text=f"Traduction vers {lang_label}...")
        self._tgt_text.configure(state="normal")
        self._tgt_text.delete("1.0", "end")
        self._tgt_text.configure(state="disabled")
        self._app.set_status(f"Traduction en cours vers {lang_label}...", "info", 0.5)

        def _worker():
            result = self._translate(text, lang_code)
            self.after(0, lambda: self._on_done(result, text, lang_label, lang_code))

        threading.Thread(target=_worker, daemon=True).start()

    def _translate(self, text: str, lang_code: str) -> str:
        """
        Traduction synchrone. Essaie plusieurs backends dans l'ordre.
        """
        # ── Tentative 1 : deep_translator (stable, synchrone) ──
        try:
            from deep_translator import GoogleTranslator
            chunks = [text[i:i+4500] for i in range(0, len(text), 4500)]
            parts = []
            for chunk in chunks:
                translated = GoogleTranslator(source="auto", target=lang_code).translate(chunk)
                parts.append(translated or chunk)
            return "\n".join(parts)
        except ImportError:
            pass
        except Exception:
            pass

        # ── Tentative 2 : googletrans legacy (synchrone via requests) ──
        try:
            import urllib.request, urllib.parse, json as _json
            encoded = urllib.parse.quote(text[:2000])
            url = (f"https://translate.googleapis.com/translate_a/single"
                   f"?client=gtx&sl=auto&tl={lang_code}&dt=t&q={encoded}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = _json.loads(resp.read().decode())
            return "".join(part[0] for part in data[0] if part[0])
        except Exception:
            pass

        # ── Fallback : retour informatif ──
        return (
            f"[Traduction vers {lang_code.upper()}]\n\n"
            "Pour activer la traduction automatique, installez :\n"
            "    pip install deep-translator\n\n"
            f"--- Texte source ({len(text)} caracteres) ---\n\n{text[:800]}"
            + ("..." if len(text) > 800 else "")
        )

    def _on_done(self, translated: str, source: str, lang_label: str, lang_code: str):
        self._status_lbl.configure(text="")
        self._current_translation = translated

        self._tgt_text.configure(state="normal")
        self._tgt_text.delete("1.0", "end")
        self._tgt_text.insert("1.0", translated)
        self._tgt_text.configure(state="disabled")

        entry = {
            "id":         len(self._history) + 1,
            "timestamp":  datetime.now().strftime("%d/%m %H:%M"),
            "lang_label": lang_label,
            "lang_code":  lang_code,
            "source":     source[:80] + ("..." if len(source) > 80 else ""),
            "translated": translated[:80] + ("..." if len(translated) > 80 else ""),
            "rating":     0,
            "comment":    "",
            "full_source": source,
            "full_trans":  translated,
        }
        self._history.append(entry)
        self._render_history()
        self._update_stats()
        self._app.set_status(f"Traduction terminee vers {lang_label}", "success")

    # ─────────────────────────────────────────
    #  SOURCE TEXT
    # ─────────────────────────────────────────

    def _get_source_text(self) -> str:
        src_type = self._src_type_var.get()
        if src_type == "Texte personnalise":
            return self._src_text.get("1.0", "end").strip()

        if not self._controller or not self._controller.current_analysis:
            return self._src_text.get("1.0", "end").strip()

        a = self._controller.current_analysis

        if src_type == "Rapport d'analyse complet":
            stats = a.get("stats", {})
            nodes = a.get("centrality", {}).get("critical_nodes", [])
            comp  = a.get("comparison", {}).get("comparison", {})
            lines = [
                "RAPPORT D'ANALYSE — RISKPULSE",
                f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                "",
                "RESEAU",
                f"Entites : {stats.get('nb_entities', 0)}",
                f"Relations : {stats.get('nb_relations', 0)}",
                f"Densite : {stats.get('density', 0):.4f}",
                f"Composantes : {stats.get('nb_components', 1)}",
                f"Temps de traitement : {stats.get('processing_time', 0):.3f}s",
                "",
                "NOEUDS CRITIQUES",
            ]
            for i, n in enumerate(nodes[:5], 1):
                lines.append(f"  {i}. {n['name']} — score {n['composite']:.3f}")
            lines += [
                "",
                "COMPARAISON DES MODELES",
                f"Modele A : {comp.get('n_anomalies_a', 0)} anomalie(s)",
                f"Modele B : {comp.get('n_anomalies_b', 0)} anomalie(s)",
                f"Accord : {comp.get('agreement_rate', 0):.1%}",
                f"Conclusion : {comp.get('key_insight', '')}",
            ]
            return "\n".join(lines)

        elif src_type == "Noeuds critiques":
            nodes = a.get("centrality", {}).get("critical_nodes", [])
            hidden = a.get("centrality", {}).get("hidden_critical", [])
            lines = ["NOEUDS CRITIQUES DU RESEAU", ""]
            for i, n in enumerate(nodes, 1):
                lines.append(f"{i}. {n['name']}  |  type : {n.get('type','?')}  |  score : {n['composite']:.3f}")
            if hidden:
                lines += ["", f"NOEUDS A FAIBLE VISIBILITE ({len(hidden)}) :"]
                for n in hidden:
                    lines.append(f"  - {n['name']} : {n.get('reason','')}")
            return "\n".join(lines)

        elif src_type == "Comparaison des modeles":
            comp   = a.get("comparison", {}).get("comparison", {})
            only_b = comp.get("only_b_detects", [])
            lines = [
                "COMPARAISON MODELE A vs MODELE B",
                "",
                f"Modele A (IsolationForest) : {comp.get('n_anomalies_a',0)} anomalie(s)",
                f"Modele B (GraphBased)       : {comp.get('n_anomalies_b',0)} anomalie(s)",
                f"Taux d'accord : {comp.get('agreement_rate',0):.1%}",
                "",
                f"Conclusion : {comp.get('key_insight','')}",
            ]
            if only_b:
                lines += ["", "Detecte uniquement par Modele B :"]
                for n in only_b:
                    lines.append(f"  - {n['node_name']} (score {n['score_b']:.3f}) : {n.get('explanation','')}")
            return "\n".join(lines)

        return self._src_text.get("1.0", "end").strip()

    # ─────────────────────────────────────────
    #  EVALUATION
    # ─────────────────────────────────────────

    def _set_rating(self, v: int):
        self._rating_var.set(v)
        self._hover_stars(v)

    def _hover_stars(self, v: int):
        for i, b in enumerate(self._star_btns, 1):
            b.configure(
                text="★" if i <= v else "☆",
                fg=self.c("warning") if i <= v else self.c("text_muted"),
            )

    def _save_rating(self):
        if not self._history:
            messagebox.showinfo("Information", "Aucune traduction a evaluer.")
            return
        r = self._rating_var.get()
        if r == 0:
            messagebox.showwarning("Note manquante", "Selectionnez une note (1 a 5 etoiles).")
            return
        self._history[-1]["rating"] = r
        self._render_history()
        self._update_stats()

    # ─────────────────────────────────────────
    #  HISTORIQUE
    # ─────────────────────────────────────────

    def _render_history(self):
        for w in self._hist_inner.winfo_children():
            w.destroy()
        for entry in reversed(self._history):
            row = ThemedFrame(self._hist_inner, bg_key="bg_card")
            row.pack(fill="x", pady=1)
            row.bind("<Enter>", lambda e, r=row: r.configure(bg=self.c("bg_card_hover")))
            row.bind("<Leave>", lambda e, r=row: r.configure(bg=self.c("bg_card")))
            row.bind("<Button-1>", lambda e, ent=entry: self._restore(ent))

            tk.Label(row, text=entry["timestamp"], font=self.font("caption"),
                     bg=self.c("bg_card"), fg=self.c("text_muted"),
                     width=10, anchor="w").pack(side="left", padx=PAD_XS)
            tk.Label(row, text=entry["lang_label"][:8], font=self.font("caption"),
                     bg=self.c("accent_primary"), fg="#ffffff",
                     padx=3, pady=1).pack(side="left", padx=PAD_XS)
            tk.Label(row, text=entry["source"][:28], font=self.font("caption"),
                     bg=self.c("bg_card"), fg=self.c("text_primary"),
                     anchor="w", width=20).pack(side="left", padx=PAD_XS)
            stars = ("★" * entry["rating"] + "☆" * (5 - entry["rating"])) if entry["rating"] else "—"
            tk.Label(row, text=stars, font=self.font("caption"),
                     bg=self.c("bg_card"),
                     fg=self.c("warning") if entry["rating"] else self.c("text_muted"),
                     ).pack(side="right", padx=PAD_XS)

    def _restore(self, entry: dict):
        self._src_text.delete("1.0", "end")
        self._src_text.insert("1.0", entry.get("full_source", entry["source"]))
        self._tgt_text.configure(state="normal")
        self._tgt_text.delete("1.0", "end")
        self._tgt_text.insert("1.0", entry.get("full_trans", entry["translated"]))
        self._tgt_text.configure(state="disabled")

    def _update_stats(self):
        total  = len(self._history)
        rated  = [e["rating"] for e in self._history if e["rating"] > 0]
        avg    = sum(rated) / len(rated) if rated else 0
        langs  = len(set(e["lang_code"] for e in self._history))
        self._st_total.configure(text=str(total))
        self._st_rating.configure(text=f"{avg:.1f}/5" if rated else "—")
        self._st_langs.configure(text=str(langs))

    def _clear_history(self):
        if not self._history:
            return
        if messagebox.askyesno("Confirmation", "Effacer tout l'historique ?"):
            self._history.clear()
            self._render_history()
            self._update_stats()

    def _export_history(self):
        if not self._history:
            messagebox.showinfo("Vide", "Aucune traduction a exporter.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=FILETYPES_JSON,
            initialfile="historique_traductions.json",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Export reussi", f"Fichier sauvegarde :\n{path}")

    def _clear(self):
        self._src_text.delete("1.0", "end")
        self._tgt_text.configure(state="normal")
        self._tgt_text.delete("1.0", "end")
        self._tgt_text.configure(state="disabled")
        self._status_lbl.configure(text="")
        self._current_translation = None

    def _export_pdf(self):
        if not self._current_translation:
            messagebox.showwarning("Rien a exporter", "Lancez d'abord une traduction.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("Tous", "*.*")],
            initialfile="rapport_traduit.pdf",
        )
        if not path:
            return
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4
            c = rl_canvas.Canvas(path, pagesize=A4)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, 800, "RiskPulse — Rapport Traduit")
            c.setFont("Helvetica", 10)
            y = 770
            for line in self._current_translation.split("\n"):
                if y < 60:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = 800
                c.drawString(50, y, line[:100])
                y -= 14
            c.save()
            messagebox.showinfo("Export reussi", f"PDF sauvegarde :\n{path}")
        except ImportError:
            messagebox.showwarning(
                "ReportLab manquant",
                "Installez reportlab pour l'export PDF :\n    pip install reportlab"
            )

    # ─────────────────────────────────────────
    #  HOOKS
    # ─────────────────────────────────────────

    def on_analysis_updated(self):
        pass

    def on_show(self):
        src_type = self._src_type_var.get()
        if src_type != "Texte personnalise":
            text = self._get_source_text()
            if text:
                self._src_text.delete("1.0", "end")
                self._src_text.insert("1.0", text)
