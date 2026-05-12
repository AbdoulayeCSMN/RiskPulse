"""
RiskPulse — Vue Analyse de Texte
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import webbrowser
import os
import tempfile

from ui.theme import ThemedMixin
from ui.components.widgets import (
    ThemedFrame, ThemedLabel, Button, Card,
    Separator, MetricCard,
)
from ui.constants import (
    PAD_XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    DEMO_LABELS, FILETYPES_TEXT,
)


class AnalyseView(ThemedFrame):

    def __init__(self, parent, controller, app, **kwargs):
        super().__init__(parent, bg_key="bg_primary", **kwargs)
        self._controller         = controller
        self._app                = app
        self._analysis           = None
        self._placeholder_active = True
        self._graph_html         = None
        self._init_theme()
        self._build()

    # ─────────────────────────────────────────
    #  CONSTRUCTION
    # ─────────────────────────────────────────

    def _build(self):
        # Titre
        self._build_header()

        # Corps : PanedWindow pour redimensionnement libre
        pane = tk.PanedWindow(
            self,
            orient="horizontal",
            bg=self.c("bg_primary"),
            sashrelief="flat",
            sashwidth=6,
            bd=0,
        )
        pane.pack(fill="both", expand=True, padx=PAD_LG, pady=(0, PAD_LG))

        # Panneau gauche
        left_outer = ThemedFrame(pane, bg_key="bg_primary")
        pane.add(left_outer, minsize=380, width=520)
        self._build_input_panel(left_outer)

        # Panneau droit
        right_outer = ThemedFrame(pane, bg_key="bg_primary")
        pane.add(right_outer, minsize=280)
        self._build_results_panel(right_outer)

    def _build_header(self):
        h = ThemedFrame(self, bg_key="bg_primary")
        h.pack(fill="x", padx=PAD_LG, pady=(PAD_LG, PAD_MD))

        ThemedLabel(
            h, text="Analyse de Texte",
            font_key="h1", fg_key="text_primary", bg_key="bg_primary",
        ).pack(side="left", anchor="w")

    # ── Panneau saisie ────────────────────────

    def _build_input_panel(self, parent):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        # ── Barre d'outils ──
        toolbar = ThemedFrame(parent, bg_key="bg_primary")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, PAD_SM))

        ThemedLabel(
            toolbar, text="Scenario :",
            font_key="body_sm", fg_key="text_muted", bg_key="bg_primary",
        ).pack(side="left", anchor="center", padx=(0, PAD_SM))

        self._demo_var = tk.StringVar(value="Choisir un scenario...")
        demo_cb = ttk.Combobox(
            toolbar,
            textvariable=self._demo_var,
            values=list(DEMO_LABELS.values()),
            state="readonly",
            width=24,
            font=self.font("body_sm"),
        )
        demo_cb.pack(side="left", anchor="center")
        demo_cb.bind("<<ComboboxSelected>>", self._on_demo_selected)

        Button(
            toolbar, text="Importer",
            command=self._import_file,
            variant="secondary", size="sm",
        ).pack(side="left", padx=PAD_SM)

        Button(
            toolbar, text="Effacer",
            command=self._clear_text,
            variant="ghost", size="sm",
        ).pack(side="left")

        self._char_lbl = ThemedLabel(
            toolbar, text="0 car.",
            font_key="caption", fg_key="text_muted", bg_key="bg_primary",
        )
        self._char_lbl.pack(side="right", anchor="center")

        # ── Zone de texte ──
        text_frame = ThemedFrame(parent, bg_key="bg_card")
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self._text = tk.Text(
            text_frame,
            bg=self.c("bg_input"),
            fg=self.c("text_muted"),
            font=self.font("body"),
            relief="flat",
            insertbackground=self.c("accent_text"),
            selectbackground=self.c("accent_primary"),
            wrap="word",
            padx=PAD_MD,
            pady=PAD_MD,
            highlightthickness=1,
            highlightbackground=self.c("border"),
            highlightcolor=self.c("border_focus"),
        )
        vscroll = ttk.Scrollbar(text_frame, command=self._text.yview)
        self._text.configure(yscrollcommand=vscroll.set)
        vscroll.grid(row=0, column=1, sticky="ns")
        self._text.grid(row=0, column=0, sticky="nsew")

        self._PLACEHOLDER = (
            "Collez ou saisissez votre texte ici...\n\n"
            "Exemples : rapports financiers, articles de presse,\n"
            "decisions juridiques, incidents de securite...\n\n"
            "Choisissez un scenario de demonstration ci-dessus\n"
            "ou importez un fichier texte."
        )
        self._text.insert("1.0", self._PLACEHOLDER)
        self._text.bind("<FocusIn>",  self._on_focus_in)
        self._text.bind("<FocusOut>", self._on_focus_out)
        self._text.bind("<KeyRelease>", self._on_key)

        # ── Bouton analyser ──
        btn_bar = ThemedFrame(parent, bg_key="bg_primary")
        btn_bar.grid(row=2, column=0, sticky="ew", pady=(PAD_SM, 0))

        self._btn_analyse = Button(
            btn_bar,
            text="Lancer l'analyse",
            command=self._run_analysis,
            variant="primary",
            size="lg",
        )
        self._btn_analyse.pack(side="left")

        Button(
            btn_bar,
            text="Mode demo complet",
            command=self._run_full_demo,
            variant="success",
            size="lg",
        ).pack(side="left", padx=PAD_SM)

    # ── Panneau résultats ─────────────────────

    def _build_results_panel(self, parent):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        # Onglets
        tab_bar = ThemedFrame(parent, bg_key="bg_primary")
        tab_bar.grid(row=0, column=0, sticky="ew", pady=(0, PAD_SM))

        self._tab_btns   = {}
        self._tab_frames = {}
        self._active_tab = None

        for tid, label in [
            ("entites",   "Entites"),
            ("relations", "Relations"),
            ("graphe",    "Graphe"),
        ]:
            b = Button(
                tab_bar, text=label,
                command=lambda t=tid: self._show_tab(t),
                variant="secondary", size="sm",
            )
            b.pack(side="left", padx=(0, PAD_XS))
            self._tab_btns[tid] = b

        # Frames des onglets
        container = ThemedFrame(parent, bg_key="bg_primary")
        container.grid(row=1, column=0, sticky="nsew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        for tid in ("entites", "relations", "graphe"):
            f = ThemedFrame(container, bg_key="bg_primary")
            f.grid(row=0, column=0, sticky="nsew")
            self._tab_frames[tid] = f

        self._build_entites_tab()
        self._build_relations_tab()
        self._build_graphe_tab()

        self._show_tab("entites")

    def _build_entites_tab(self):
        f = self._tab_frames["entites"]
        f.rowconfigure(1, weight=1)
        f.columnconfigure(0, weight=1)

        # Stats
        stats = ThemedFrame(f, bg_key="bg_primary")
        stats.grid(row=0, column=0, sticky="ew", pady=(0, PAD_SM))
        self._s_ent  = self._mini_stat(stats, "—", "Entites")
        self._s_rel  = self._mini_stat(stats, "—", "Relations")
        self._s_den  = self._mini_stat(stats, "—", "Densite")
        self._s_time = self._mini_stat(stats, "—", "Temps")

        # Liste
        card = Card(f, bg_key="bg_card")
        card.grid(row=1, column=0, sticky="nsew")
        card.rowconfigure(0, weight=1)

        # header colonnes
        hdr = ThemedFrame(card.content, bg_key="bg_card")
        hdr.pack(fill="x", pady=(0, PAD_XS))
        for col, w in [("Entite", 20), ("Type", 14), ("Freq.", 5)]:
            tk.Label(hdr, text=col, font=self.font("label"),
                     bg=self.c("bg_card"), fg=self.c("text_muted"),
                     width=w, anchor="w").pack(side="left")

        Separator(card.content).pack(fill="x", pady=(0, PAD_XS))

        # Zone scrollable
        canvas = tk.Canvas(card.content, bg=self.c("bg_card"), highlightthickness=0)
        sc = ttk.Scrollbar(card.content, command=canvas.yview)
        self._ent_inner = ThemedFrame(canvas, bg_key="bg_card")
        canvas.create_window((0, 0), window=self._ent_inner, anchor="nw")
        canvas.configure(yscrollcommand=sc.set)
        self._ent_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(1, width=e.width))
        sc.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        # Noeuds critiques
        crit = Card(f, bg_key="bg_card", accent_color=self.c("rupture_3"))
        crit.grid(row=2, column=0, sticky="ew", pady=(PAD_SM, 0))
        ThemedLabel(crit.content, text="Noeuds les plus influents",
                    font_key="label", fg_key="text_muted", bg_key="bg_card").pack(anchor="w", pady=(0, PAD_XS))
        self._crit_frame = ThemedFrame(crit.content, bg_key="bg_card")
        self._crit_frame.pack(fill="x")
        ThemedLabel(self._crit_frame, text="En attente d'analyse...",
                    font_key="caption", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")

    def _build_relations_tab(self):
        f = self._tab_frames["relations"]
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

        card = Card(f, bg_key="bg_card")
        card.grid(row=0, column=0, sticky="nsew")

        canvas = tk.Canvas(card.content, bg=self.c("bg_card"), highlightthickness=0)
        sc = ttk.Scrollbar(card.content, command=canvas.yview)
        self._rel_inner = ThemedFrame(canvas, bg_key="bg_card")
        canvas.create_window((0, 0), window=self._rel_inner, anchor="nw")
        canvas.configure(yscrollcommand=sc.set)
        self._rel_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(1, width=e.width))
        sc.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

    def _build_graphe_tab(self):
        f = self._tab_frames["graphe"]
        f.rowconfigure(1, weight=1)
        f.columnconfigure(0, weight=1)

        btn_bar = ThemedFrame(f, bg_key="bg_primary")
        btn_bar.grid(row=0, column=0, sticky="ew", pady=(0, PAD_SM))

        Button(btn_bar, text="Ouvrir le graphe interactif",
               command=self._open_graph,
               variant="primary", size="sm").pack(side="left")

        card = Card(f, bg_key="bg_card")
        card.grid(row=1, column=0, sticky="nsew")

        self._graph_lbl = ThemedLabel(
            card.content,
            text="Lancez une analyse pour generer le graphe.",
            font_key="body_sm", fg_key="text_muted", bg_key="bg_card",
            wraplength=280,
        )
        self._graph_lbl.pack(expand=True, pady=PAD_XL)

    def _mini_stat(self, parent, val, label) -> ThemedLabel:
        # MetricCard arrondie a la place du Frame plat
        accent_map = {
            "Entites":   self.c("chart_1"),
            "Relations": self.c("chart_2"),
            "Densite":   self.c("chart_3"),
            "Temps":     self.c("chart_5"),
        }
        card = MetricCard(parent, label=label, value=val,
                          accent=accent_map.get(label, self.c("accent_primary")),
                          height=80)
        card.pack(side="left", fill="both", expand=True, padx=(0, PAD_XS))
        return card._val_lbl

    # ── Navigation onglets ────────────────────

    def _show_tab(self, tid: str):
        for t, f in self._tab_frames.items():
            if t == tid:
                f.lift()
            else:
                f.lower()
        for t, b in self._tab_btns.items():
            if t == tid:
                b.configure(bg=self.c("accent_primary"), fg="#ffffff")
            else:
                b.configure(bg=self.c("bg_card"), fg=self.c("text_secondary"))

    # ── Interactions texte ────────────────────

    def _on_focus_in(self, e=None):
        if self._placeholder_active:
            self._text.delete("1.0", "end")
            self._text.configure(fg=self.c("text_primary"))
            self._placeholder_active = False

    def _on_focus_out(self, e=None):
        if not self._text.get("1.0", "end").strip():
            self._text.insert("1.0", self._PLACEHOLDER)
            self._text.configure(fg=self.c("text_muted"))
            self._placeholder_active = True

    def _on_key(self, e=None):
        n = 0 if self._placeholder_active else len(self._text.get("1.0", "end").strip())
        self._char_lbl.configure(text=f"{n:,} car.")

    def _clear_text(self):
        self._text.delete("1.0", "end")
        self._text.configure(fg=self.c("text_muted"))
        self._text.insert("1.0", self._PLACEHOLDER)
        self._placeholder_active = True
        self._char_lbl.configure(text="0 car.")

    def _on_demo_selected(self, e=None):
        selected = self._demo_var.get()
        key = {v: k for k, v in DEMO_LABELS.items()}.get(selected)
        if not key:
            return
        try:
            from controller.risk_controller import DEMO_SCENARIOS
            text = DEMO_SCENARIOS[key]["text"].strip()
            self._text.delete("1.0", "end")
            self._text.configure(fg=self.c("text_primary"))
            self._text.insert("1.0", text)
            self._placeholder_active = False
            self._on_key()
        except Exception as ex:
            messagebox.showerror("Erreur", str(ex))

    def _import_file(self):
        path = filedialog.askopenfilename(filetypes=FILETYPES_TEXT)
        if not path:
            return
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".pdf":
                content = self._read_pdf(path)
            elif ext == ".json":
                import json as _json
                with open(path, "r", encoding="utf-8") as fh:
                    data = _json.load(fh)
                # Si le JSON contient une cle 'text', l'extraire; sinon, le rendre lisible
                if isinstance(data, dict) and "text" in data:
                    content = data["text"]
                else:
                    content = _json.dumps(data, ensure_ascii=False, indent=2)
            elif ext == ".csv":
                import csv as _csv
                lines = []
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    reader = _csv.reader(fh)
                    for row in reader:
                        lines.append(" ".join(row))
                content = "\n".join(lines)
            else:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            self._text.delete("1.0", "end")
            self._text.configure(fg=self.c("text_primary"))
            self._text.insert("1.0", content)
            self._placeholder_active = False
            self._on_key()
            self._app.set_status(f"Fichier importe : {os.path.basename(path)}", "success")
        except Exception as ex:
            messagebox.showerror("Erreur import", str(ex))

    def _read_pdf(self, path: str) -> str:
        """Lit un PDF via PyPDF2 si disponible, sinon message d'erreur."""
        try:
            from pypdf import PdfReader
        except ImportError:
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                raise RuntimeError(
                    "Lecture PDF indisponible. Installez : pip install pypdf"
                )
        reader = PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in reader.pages)

    # ── Analyse ───────────────────────────────

    def _run_analysis(self):
        if self._placeholder_active:
            messagebox.showwarning("Texte manquant",
                "Veuillez saisir ou importer un texte avant de lancer l'analyse.")
            return
        text = self._text.get("1.0", "end").strip()
        if len(text) < 20:
            messagebox.showwarning("Texte trop court",
                "Le texte doit contenir au moins 20 caracteres.")
            return
        if not self._controller:
            messagebox.showerror("Erreur", "Le controleur IA n'est pas disponible.")
            return

        self._btn_analyse.configure(text="Analyse en cours...")
        self._app.set_status("Extraction des entites et construction du graphe...", "info", 0.3)

        def _worker():
            result = self._controller.analyze_text(text)
            self.after(0, lambda: self._on_done(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _run_full_demo(self):
        """Mode demo : charge un scenario aleatoire et lance le pipeline complet."""
        import random
        try:
            from controller.risk_controller import DEMO_SCENARIOS
        except Exception as ex:
            messagebox.showerror("Erreur", str(ex))
            return

        # Choix d'un scenario aleatoire
        keys = list(DEMO_SCENARIOS.keys())
        key = random.choice(keys)
        scenario = DEMO_SCENARIOS[key]

        # Insertion du texte dans la zone
        self._text.delete("1.0", "end")
        self._text.configure(fg=self.c("text_primary"))
        self._text.insert("1.0", scenario["text"].strip())
        self._placeholder_active = False
        self._on_key()
        self._demo_var.set(scenario["title"])

        self._app.set_status(f"Mode demo : {scenario['title']}...", "info", 0.2)

        # Lancement
        self._btn_analyse.configure(text="Demo en cours...")

        def _worker():
            result = self._controller.load_demo_scenario(key)
            self.after(0, lambda: self._on_demo_done(result, scenario))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_demo_done(self, result: dict, scenario: dict):
        self._btn_analyse.configure(text="Lancer l'analyse")
        if "error" in result:
            messagebox.showerror("Erreur demo", result["error"])
            self._app.set_status("Erreur en mode demo", "error")
            return

        analysis = result.get("analysis", {})
        propagation = result.get("propagation", {})
        self._analysis = analysis
        self._render(analysis)

        # Message synthese
        stats = analysis.get("stats", {})
        prop_sum = propagation.get("summary", {}) if propagation else {}
        summary = (
            f"Demo: {scenario['title']}\n\n"
            f"- {stats.get('nb_entities', 0)} entites detectees\n"
            f"- {stats.get('nb_relations', 0)} relations extraites\n"
        )
        if prop_sum:
            summary += (
                f"- Propagation : {prop_sum.get('critical', 0)} critiques, "
                f"{prop_sum.get('infected', 0)} infectes\n"
            )
        summary += "\nNaviguez vers les autres vues pour explorer les resultats."

        self._app.set_status(
            f"Demo terminee : {stats.get('nb_entities',0)} entites en {analysis.get('total_time',0):.2f}s",
            "success",
        )
        self._app.notify_analysis_done()
        messagebox.showinfo("Mode demo termine", summary)

    def _on_done(self, result: dict):
        self._btn_analyse.configure(text="Lancer l'analyse")
        if "error" in result:
            messagebox.showerror("Erreur d'analyse", result["error"])
            self._app.set_status("Erreur d'analyse", "error")
            return

        self._analysis = result
        stats = result["stats"]
        self._app.set_status(
            f"{stats.get('nb_entities',0)} entites detectees en {stats.get('processing_time',0):.3f}s",
            "success",
        )
        self._render(result)
        self._app.notify_analysis_done()

    # ── Rendu des résultats ───────────────────

    def _render(self, r: dict):
        stats = r["stats"]
        self._s_ent.configure(text=str(stats.get("nb_entities", 0)))
        self._s_rel.configure(text=str(stats.get("nb_relations", 0)))
        self._s_den.configure(text=f"{stats.get('density', 0):.3f}")
        self._s_time.configure(text=f"{stats.get('processing_time', 0):.2f}s")

        self._render_entites(r)
        self._render_relations(r)
        self._render_critical(r)
        self._render_graph(r)

    def _render_entites(self, r: dict):
        for w in self._ent_inner.winfo_children():
            w.destroy()

        TYPE_COLORS = {
            "Organisation": "chart_1",
            "Personne":     "chart_5",
            "Montant":      "chart_3",
            "Lieu / Pays":  "chart_2",
        }

        for ent in r["nlp"]["entities"]:
            row = ThemedFrame(self._ent_inner, bg_key="bg_card")
            row.pack(fill="x", pady=1)
            row.bind("<Enter>", lambda e, rw=row: rw.configure(bg=self.c("bg_card_hover")))
            row.bind("<Leave>", lambda e, rw=row: rw.configure(bg=self.c("bg_card")))

            tk.Label(row, text=ent["name"][:22],
                     font=self.font("body_sm"), bg=self.c("bg_card"),
                     fg=self.c("text_primary"), anchor="w", width=20,
                     ).pack(side="left", padx=(PAD_SM, 0))

            ck = TYPE_COLORS.get(ent.get("type_label", ""), "text_muted")
            tk.Label(row, text=ent.get("type_label", "")[:12],
                     font=self.font("caption"),
                     bg=self.c(ck), fg="#ffffff",
                     padx=3, pady=1,
                     ).pack(side="left", padx=PAD_SM)

            tk.Label(row, text=f"x{ent['frequency']}",
                     font=self.font("caption"),
                     bg=self.c("bg_card"), fg=self.c("text_muted"),
                     ).pack(side="right", padx=PAD_SM)

    def _render_relations(self, r: dict):
        for w in self._rel_inner.winfo_children():
            w.destroy()

        for rel in r["nlp"]["relations"]:
            row = ThemedFrame(self._rel_inner, bg_key="bg_card")
            row.pack(fill="x", pady=1, padx=PAD_XS)
            src = rel["source"].replace("_", " ").title()[:18]
            tgt = rel["target"].replace("_", " ").title()[:18]
            tk.Label(row, text=src, font=self.font("body_sm"),
                     bg=self.c("bg_card"), fg=self.c("text_primary"),
                     anchor="e", width=18).pack(side="left")
            tk.Label(row, text=f"  w={rel['weight']:.0f}",
                     font=self.font("caption"),
                     bg=self.c("bg_card"), fg=self.c("accent_text"),
                     ).pack(side="left")
            tk.Label(row, text="→", font=self.font("body_sm"),
                     bg=self.c("bg_card"), fg=self.c("text_muted"),
                     ).pack(side="left", padx=PAD_XS)
            tk.Label(row, text=tgt, font=self.font("body_sm"),
                     bg=self.c("bg_card"), fg=self.c("text_primary"),
                     anchor="w", width=18).pack(side="left")

    def _render_critical(self, r: dict):
        for w in self._crit_frame.winfo_children():
            w.destroy()
        nodes = r.get("centrality", {}).get("critical_nodes", [])[:5]
        COLORS = ["rupture_2", "rupture_3", "rupture_4", "chart_1", "text_muted"]
        for i, n in enumerate(nodes):
            row = ThemedFrame(self._crit_frame, bg_key="bg_card")
            row.pack(fill="x", pady=1)
            color = self.c(COLORS[i % len(COLORS)])
            tk.Label(row, text=f"#{i+1}", font=self.font("caption"),
                     bg=color, fg="#fff", width=3, pady=1).pack(side="left")
            tk.Label(row, text=n["name"][:24], font=self.font("body_sm"),
                     bg=self.c("bg_card"), fg=self.c("text_primary"),
                     anchor="w").pack(side="left", padx=PAD_SM, fill="x", expand=True)
            tk.Label(row, text=f"{n['composite']:.3f}",
                     font=self.font("caption"),
                     bg=self.c("bg_card"), fg=color).pack(side="right", padx=PAD_SM)
        if not nodes:
            ThemedLabel(self._crit_frame, text="Aucune donnee.",
                        font_key="caption", fg_key="text_muted", bg_key="bg_card").pack(anchor="w")

    def _render_graph(self, r: dict):
        stats = r["stats"]
        self._graph_lbl.configure(
            text=f"Graphe : {stats['nb_entities']} noeuds  |  {stats['nb_relations']} aretes\n"
                 f"Densite : {stats['density']:.4f}   Composantes : {stats['nb_components']}\n\n"
                 f"Cliquez sur 'Ouvrir le graphe interactif'\npour voir la visualisation."
        )
        self._generate_pyvis()

    def _generate_pyvis(self):
        try:
            from pyvis.network import Network
            G = self._controller.get_graph()
            if G is None:
                return
            net = Network(height="600px", width="100%",
                          bgcolor=self.c("bg_card"),
                          font_color=self.c("text_primary"))
            net.from_nx(G)
            self._graph_html = os.path.join(tempfile.gettempdir(), "riskpulse_graph.html")
            net.save_graph(self._graph_html)
        except ImportError:
            self._graph_html = None
        except Exception:
            self._graph_html = None

    def _open_graph(self):
        if self._graph_html and os.path.exists(self._graph_html):
            webbrowser.open(f"file:///{self._graph_html.replace(os.sep, '/')}")
        else:
            messagebox.showinfo(
                "Visualisation",
                "Installez pyvis pour la visualisation interactive :\n"
                "pip install pyvis\n\nSinon, exportez le graphe en JSON via le Tableau de Bord."
            )

    # ── Hooks ─────────────────────────────────

    def on_show(self):
        pass

    def on_analysis_updated(self):
        pass

    def _on_theme_change(self):
        super()._on_theme_change()
        try:
            self._text.configure(
                bg=self.c("bg_input"),
                fg=self.c("text_primary" if not self._placeholder_active else "text_muted"),
                insertbackground=self.c("accent_text"),
                highlightbackground=self.c("border"),
                highlightcolor=self.c("border_focus"),
            )
        except tk.TclError:
            pass
