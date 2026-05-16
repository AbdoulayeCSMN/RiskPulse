"""
Vue Analyse de Texte — PySide6
================================
Saisie de texte, choix de scenario demo, lancement de l'analyse NLP,
affichage des resultats (entites, relations, graphe).
"""

import os
import tempfile
import threading
import webbrowser
import logging

from PySide6.QtCore import Qt, Signal, QObject, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QComboBox, QTextEdit, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QFileDialog, QMessageBox, QSizePolicy,
)

from ..components import Card, MetricCard
from ..i18n import tr

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  WORKER (thread separe pour le NLP)
# ─────────────────────────────────────────────

class AnalysisWorker(QObject):
    finished = Signal(dict)
    error    = Signal(str)

    def __init__(self, controller, text: str):
        super().__init__()
        self.controller = controller
        self.text = text

    def run(self):
        try:
            result = self.controller.analyze_text(self.text)
            self.finished.emit(result)
        except Exception as e:
            logger.exception("Analysis failed")
            self.error.emit(str(e))


# ─────────────────────────────────────────────
#  VUE ANALYSE
# ─────────────────────────────────────────────

class AnalyseView(QWidget):

    PLACEHOLDER_KEY = ("Paste or type your text here...\n\n"
                       "Examples: financial reports, news articles,\n"
                       "legal decisions, security incidents...\n\n"
                       "Choose a demo scenario above\n"
                       "or import a text file.")

    # Signaux Qt thread-safe (marshalling automatique vers le thread UI)
    _analysis_done  = Signal(dict)
    _analysis_error = Signal(str)
    _demo_done      = Signal(dict)
    _url_done       = Signal(str, str)   # (text, url)
    _url_error      = Signal(str)

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._analysis = None
        self._graph_html = None
        self._build()
        self._apply_permissions()

    def _apply_permissions(self):
        """Greise les boutons selon les permissions du user courant."""
        try:
            from services.permissions import PERM, can
            self._btn_analyse.setEnabled(can(PERM.RUN_ANALYSIS))
            self._btn_demo.setEnabled(can(PERM.RUN_DEMO))
            self._btn_import.setEnabled(can(PERM.RUN_ANALYSIS))
            if not can(PERM.RUN_ANALYSIS):
                self._btn_analyse.setToolTip(tr("Read-only role — analysis disabled"))
        except Exception:
            pass

        # Connecte les signaux aux slots UI (Qt::AutoConnection = queue si thread different)
        self._analysis_done.connect(self._on_done)
        self._analysis_error.connect(self._on_error)
        self._demo_done.connect(self._on_demo_done)
        self._url_done.connect(self._on_url_done)
        self._url_error.connect(self._on_url_error)

    # ── Construction ───────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        # ── Header : titre + sous-titre + indicateur ──
        header = QVBoxLayout()
        header.setSpacing(6)

        self._title_caption = QLabel(tr("MODULE"))
        self._title_caption.setProperty("class", "caption")
        header.addWidget(self._title_caption)

        self._title = QLabel(tr("Text Analysis"))
        self._title.setProperty("class", "h1")
        header.addWidget(self._title)

        outer.addLayout(header)

        # Separateur horizontal fin (couleur via QSS adaptative)
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setObjectName("divider")
        outer.addWidget(sep)

        # ── Corps : splitter horizontal (saisie | resultats) ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)
        outer.addWidget(splitter, 1)

        # Panneau gauche
        self._left_panel = self._build_input_panel()
        splitter.addWidget(self._left_panel)

        # Panneau droit
        self._right_panel = self._build_results_panel()
        splitter.addWidget(self._right_panel)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([600, 480])

    # ── Panneau gauche : saisie ───────────────

    def _build_input_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._scenario_lbl = QLabel(tr("Scenario:"))
        self._scenario_lbl.setProperty("class", "subtitle")
        toolbar.addWidget(self._scenario_lbl)

        self._demo_cb = QComboBox()
        self._demo_cb.setMinimumWidth(200)
        self._rebuild_demo_combo()
        self._demo_cb.currentIndexChanged.connect(self._on_demo_selected)
        toolbar.addWidget(self._demo_cb)

        self._btn_url = QPushButton(tr("From URL"))
        self._btn_url.setProperty("variant", "secondary")
        self._btn_url.clicked.connect(self._fetch_url)
        toolbar.addWidget(self._btn_url)

        self._btn_import = QPushButton(tr("Import"))
        self._btn_import.setProperty("variant", "secondary")
        self._btn_import.clicked.connect(self._import_file)
        toolbar.addWidget(self._btn_import)

        self._btn_clear = QPushButton(tr("Clear"))
        self._btn_clear.setProperty("variant", "ghost")
        self._btn_clear.clicked.connect(self._clear_text)
        toolbar.addWidget(self._btn_clear)

        toolbar.addStretch()

        self._char_lbl = QLabel("0 chars")
        self._char_lbl.setProperty("class", "caption")
        toolbar.addWidget(self._char_lbl)

        layout.addLayout(toolbar)

        # Zone de texte
        self._text = QTextEdit()
        self._text.setPlaceholderText(tr(self.PLACEHOLDER_KEY))
        self._text.textChanged.connect(self._on_text_change)
        layout.addWidget(self._text, 1)

        # Boutons d'action
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self._btn_analyse = QPushButton(tr("Run Analysis"))
        self._btn_analyse.setProperty("variant", "primary")
        self._btn_analyse.setMinimumHeight(42)
        self._btn_analyse.clicked.connect(self._run_analysis)
        btn_bar.addWidget(self._btn_analyse)

        self._btn_demo = QPushButton(tr("Full Demo Mode"))
        self._btn_demo.setProperty("variant", "success")
        self._btn_demo.setMinimumHeight(42)
        self._btn_demo.clicked.connect(self._run_full_demo)
        btn_bar.addWidget(self._btn_demo)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        return panel

    # ── Panneau droit : resultats ─────────────

    def _build_results_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Stats en haut (MetricCards)
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._stat_entities  = MetricCard(tr("Entities"),  "—")
        self._stat_relations = MetricCard(tr("Relations"), "—")
        self._stat_density   = MetricCard(tr("Density"),   "—")
        self._stat_time      = MetricCard(tr("Time"),      "—")
        for s in (self._stat_entities, self._stat_relations, self._stat_density, self._stat_time):
            stats_row.addWidget(s)
        layout.addLayout(stats_row)

        # Tabs
        self._tabs = QTabWidget()
        self._build_entities_tab()
        self._build_relations_tab()
        self._build_graph_tab()
        layout.addWidget(self._tabs, 1)

        return panel

    def _build_entities_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        self._ent_table = QTableWidget(0, 3)
        self._ent_table.setHorizontalHeaderLabels([tr("Entity"), tr("Type"), tr("Freq.")])
        self._ent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._ent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._ent_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._ent_table.verticalHeader().setVisible(False)
        self._ent_table.setAlternatingRowColors(True)
        self._ent_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._ent_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self._ent_table, 1)

        # Critical nodes
        crit_card = Card(tr("Most influential nodes"))
        self._crit_layout = QVBoxLayout()
        self._crit_layout.setSpacing(4)
        crit_card.layout().addLayout(self._crit_layout)
        layout.addWidget(crit_card)

        self._tabs.addTab(tab, tr("Entities"))

    def _build_relations_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 0)

        self._rel_table = QTableWidget(0, 3)
        self._rel_table.setHorizontalHeaderLabels([tr("Source"), tr("Target"), tr("Weight")])
        self._rel_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._rel_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._rel_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._rel_table.verticalHeader().setVisible(False)
        self._rel_table.setAlternatingRowColors(True)
        self._rel_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._rel_table, 1)

        self._tabs.addTab(tab, tr("Relations"))

    def _build_graph_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self._graph_info = QLabel(tr("Run an analysis to generate the graph."))
        self._graph_info.setProperty("class", "caption")
        toolbar.addWidget(self._graph_info, 1)

        self._btn_open_graph = QPushButton(tr("Open in browser"))
        self._btn_open_graph.clicked.connect(self._open_graph)
        self._btn_open_graph.setEnabled(False)
        toolbar.addWidget(self._btn_open_graph)
        layout.addLayout(toolbar)

        # WebView intégrée (QtWebEngine)
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self._web_view = QWebEngineView()
            self._web_view.setMinimumHeight(360)
            # HTML placeholder
            self._web_view.setHtml(self._placeholder_graph_html())
            layout.addWidget(self._web_view, 1)
            self._web_available = True
        except ImportError:
            self._web_view = None
            self._web_available = False
            ph = QLabel(tr("QtWebEngine not available. Install: pip install PySide6-Addons"))
            ph.setAlignment(Qt.AlignCenter)
            ph.setProperty("class", "subtitle")
            layout.addWidget(ph, 1)

        self._tabs.addTab(tab, tr("Graph"))

    def _placeholder_graph_html(self) -> str:
        return """<!DOCTYPE html><html><head><style>
        body{background:#0a0a0c;color:#52525b;font-family:'JetBrains Mono',monospace;
             display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
        .box{text-align:center;}
        .tag{font-size:9px;letter-spacing:2px;color:#3f3f46;margin-bottom:8px;}
        .msg{font-size:11px;}
        </style></head><body><div class="box">
        <div class="tag">GRAPH</div>
        <div class="msg">Run an analysis to render the interactive graph here.</div>
        </div></body></html>"""

    # ── Interactions ──────────────────────────

    def _rebuild_demo_combo(self):
        self._demo_cb.blockSignals(True)
        self._demo_cb.clear()
        self._demo_cb.addItem(tr("Choose a scenario..."), userData=None)
        try:
            scenarios = self._controller.get_demo_scenarios()
            for s in scenarios:
                self._demo_cb.addItem(s["title"], userData=s["key"])
        except Exception:
            pass
        self._demo_cb.blockSignals(False)

    def _on_demo_selected(self, idx: int):
        key = self._demo_cb.itemData(idx)
        if not key:
            return
        try:
            from controller.risk_controller import DEMO_SCENARIOS
            self._text.setPlainText(DEMO_SCENARIOS[key]["text"].strip())
        except Exception as e:
            QMessageBox.warning(self, tr("Error"), str(e))

    def _on_text_change(self):
        n = len(self._text.toPlainText())
        self._char_lbl.setText(f"{n:,} chars")

    def _clear_text(self):
        self._text.clear()
        self._char_lbl.setText("0 chars")

    def _fetch_url(self):
        """Fetch + extraction du texte principal depuis une URL."""
        from PySide6.QtWidgets import QInputDialog, QLineEdit
        url, ok = QInputDialog.getText(
            self, tr("Fetch from URL"),
            tr("Paste an article URL (https://...):"),
            QLineEdit.Normal,
        )
        if not ok or not url.strip():
            return

        url = url.strip()
        self._app.set_status(f"{tr('Fetching')}: {url[:60]}...", "info", 0.3)
        self._btn_url.setEnabled(False)

        def _job():
            try:
                text = self._scrape_url(url)
                self._url_done.emit(text, url)
            except Exception as e:
                logger.exception("URL fetch failed")
                self._url_error.emit(str(e))

        threading.Thread(target=_job, daemon=True).start()

    def _scrape_url(self, url: str) -> str:
        """Scraping minimal : telecharge HTML, extrait le texte des balises."""
        import urllib.request
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 RiskPulse/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # BeautifulSoup si dispo, sinon fallback regex
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
                tag.decompose()
            # Privilegie article / main si present
            article = soup.find("article") or soup.find("main") or soup.body
            text = article.get_text(separator="\n", strip=True) if article else ""
        except ImportError:
            import re
            # Fallback : strip tags
            text = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.I)
            text = re.sub(r"<style.*?</style>",   " ", text, flags=re.DOTALL | re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

        # Nettoyage : enleve les lignes trop courtes (probablement navigation)
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 40]
        return "\n\n".join(lines)

    def _on_url_done(self, text: str, url: str):
        self._btn_url.setEnabled(True)
        if not text or len(text) < 100:
            self._app.toast(tr("Could not extract content from this URL"), "warning")
            return
        self._text.setPlainText(text)
        self._app.toast(f"{tr('Fetched')} {len(text):,} {tr('characters from')} {url[:50]}", "success")
        self._app.set_status(tr("URL content ready for analysis"), "success", 1.0)

    def _on_url_error(self, msg: str):
        self._btn_url.setEnabled(True)
        QMessageBox.critical(self, tr("URL fetch error"), msg)
        self._app.set_status(tr("URL fetch failed"), "error")

    def _import_file(self):
        filters = (
            f"{tr('Text files')} (*.txt);;"
            f"PDF (*.pdf);;"
            f"JSON (*.json);;"
            f"CSV (*.csv);;"
            f"{tr('All files')} (*.*)"
        )
        path, _ = QFileDialog.getOpenFileName(self, tr("Import file"), "", filters)
        if not path:
            return
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".pdf":
                content = self._read_pdf(path)
            else:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            self._text.setPlainText(content)
            self._app.set_status(f"{tr('Imported')}: {os.path.basename(path)}", "success")
        except Exception as e:
            QMessageBox.critical(self, tr("Import error"), str(e))

    def _read_pdf(self, path: str) -> str:
        try:
            from pypdf import PdfReader
        except ImportError:
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                raise RuntimeError(tr("Install pypdf to read PDFs:") + " pip install pypdf")
        reader = PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in reader.pages)

    # ── Analyse ───────────────────────────────

    def _run_analysis(self):
        text = self._text.toPlainText().strip()
        if len(text) < 20:
            QMessageBox.warning(self, tr("Text too short"),
                                tr("Text must be at least 20 characters."))
            return

        self._btn_analyse.setEnabled(False)
        self._btn_analyse.setText(tr("Analyzing..."))
        self._app.set_status(tr("Extracting entities and building graph..."), "info", 0.3)

        # Lance dans un thread. Les signaux Qt sont thread-safe (QueuedConnection auto).
        def _job():
            try:
                result = self._controller.analyze_text(text)
                self._analysis_done.emit(result)
            except Exception as e:
                logger.exception("Analysis failed")
                self._analysis_error.emit(str(e))

        threading.Thread(target=_job, daemon=True).start()

    def _on_done(self, result: dict):
        self._btn_analyse.setEnabled(True)
        self._btn_analyse.setText(tr("Run Analysis"))

        if "error" in result:
            QMessageBox.critical(self, tr("Analysis error"), result["error"])
            self._app.set_status(tr("Analysis error"), "error")
            return

        self._analysis = result
        stats = result.get("stats", {})
        self._app.set_status(
            f"{stats.get('nb_entities', 0)} {tr('entities detected in')} "
            f"{stats.get('processing_time', 0):.3f}s",
            "success", 1.0,
        )
        self._render(result)
        if hasattr(self._app, "notify_analysis_done"):
            self._app.notify_analysis_done()

    def _on_error(self, msg: str):
        self._btn_analyse.setEnabled(True)
        self._btn_analyse.setText(tr("Run Analysis"))
        QMessageBox.critical(self, tr("Analysis error"), msg)
        self._app.set_status(tr("Analysis error"), "error")

    def _run_full_demo(self):
        import random
        try:
            scenarios = self._controller.get_demo_scenarios()
            if not scenarios:
                return
            key = random.choice(scenarios)["key"]
            from controller.risk_controller import DEMO_SCENARIOS
            self._text.setPlainText(DEMO_SCENARIOS[key]["text"].strip())
            self._btn_demo.setEnabled(False)
            self._btn_demo.setText(tr("Running demo..."))
            self._app.set_status(tr("Demo mode running..."), "info", 0.2)

            def _job():
                try:
                    result = self._controller.load_demo_scenario(key)
                    self._demo_done.emit(result)
                except Exception as e:
                    logger.exception("Demo failed")
                    self._analysis_error.emit(str(e))

            threading.Thread(target=_job, daemon=True).start()
        except Exception as e:
            QMessageBox.critical(self, tr("Demo error"), str(e))

    def _on_demo_done(self, result: dict):
        self._btn_demo.setEnabled(True)
        self._btn_demo.setText(tr("Full Demo Mode"))
        if "error" in result:
            QMessageBox.critical(self, tr("Demo error"), result["error"])
            return
        analysis = result.get("analysis", {})
        self._analysis = analysis
        self._render(analysis)
        if hasattr(self._app, "notify_analysis_done"):
            self._app.notify_analysis_done()
        stats = analysis.get("stats", {})
        self._app.set_status(
            f"{tr('Demo complete')}: {stats.get('nb_entities', 0)} "
            f"{tr('entities in')} {analysis.get('total_time', 0):.2f}s",
            "success", 1.0,
        )

    # ── Rendu ─────────────────────────────────

    def _render(self, result: dict):
        stats = result.get("stats", {})
        self._stat_entities.set_value(str(stats.get("nb_entities", 0)))
        self._stat_relations.set_value(str(stats.get("nb_relations", 0)))
        self._stat_density.set_value(f"{stats.get('density', 0):.3f}")
        self._stat_time.set_value(f"{stats.get('processing_time', 0):.2f}s")

        self._render_entities(result.get("nlp", {}).get("entities", []))
        self._render_relations(result.get("nlp", {}).get("relations", []))
        self._render_critical(result.get("centrality", {}).get("critical_nodes", [])[:5])
        self._render_graph(stats)
        self._generate_pyvis()

    def _render_entities(self, entities: list):
        self._ent_table.setRowCount(len(entities))
        for i, e in enumerate(entities):
            self._ent_table.setItem(i, 0, QTableWidgetItem(e.get("name", "")))
            self._ent_table.setItem(i, 1, QTableWidgetItem(e.get("type_label", "")))
            self._ent_table.setItem(i, 2, QTableWidgetItem(str(e.get("frequency", ""))))

    def _render_relations(self, relations: list):
        self._rel_table.setRowCount(len(relations))
        for i, r in enumerate(relations):
            src = r.get("source", "").replace("_", " ").title()
            tgt = r.get("target", "").replace("_", " ").title()
            self._rel_table.setItem(i, 0, QTableWidgetItem(src))
            self._rel_table.setItem(i, 1, QTableWidgetItem(tgt))
            self._rel_table.setItem(i, 2, QTableWidgetItem(f"{r.get('weight', 0):.1f}"))

    def _render_critical(self, nodes: list):
        # Vide le layout
        while self._crit_layout.count():
            item = self._crit_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        if not nodes:
            lbl = QLabel(tr("No data."))
            lbl.setProperty("class", "caption")
            self._crit_layout.addWidget(lbl)
            return
        for i, n in enumerate(nodes, 1):
            row = QHBoxLayout()
            num = QLabel(f"#{i}")
            num.setFixedWidth(28)
            num.setProperty("class", "caption")
            row.addWidget(num)
            name = QLabel(n.get("name", "")[:28])
            row.addWidget(name, 1)
            score = QLabel(f"{n.get('composite', 0):.3f}")
            score.setProperty("class", "caption")
            row.addWidget(score)
            wrapper = QWidget()
            wrapper.setLayout(row)
            self._crit_layout.addWidget(wrapper)

    def _render_graph(self, stats: dict):
        self._graph_info.setText(
            f"{tr('Graph')}: {stats.get('nb_entities', 0)} {tr('nodes')}, "
            f"{stats.get('nb_relations', 0)} {tr('edges')}\n"
            f"{tr('Density')}: {stats.get('density', 0):.4f}   "
            f"{tr('Components')}: {stats.get('nb_components', 0)}"
        )
        self._btn_open_graph.setEnabled(True)

    def _generate_pyvis(self):
        try:
            from pyvis.network import Network
            G = self._controller.get_graph()
            if G is None:
                return
            # cdn_resources='in_line' embarque vis.js+css directement dans le HTML
            # -> aucune requete reseau, fonctionne offline et avec QtWebEngine
            net = Network(
                height="700px", width="100%",
                bgcolor="#0a0a0c",
                font_color="#e4e4e7",
                directed=False,
                notebook=False,
                cdn_resources="in_line",
            )
            # Style des noeuds : monochrome
            for nid, attrs in G.nodes(data=True):
                net.add_node(
                    nid,
                    label=attrs.get("label", nid)[:25],
                    color={"background": "#16161a", "border": "#52525b",
                            "highlight": {"background": "#27272a", "border": "#e4e4e7"}},
                    font={"color": "#e4e4e7", "face": "JetBrains Mono", "size": 14},
                    borderWidth=1,
                )
            for u, v, attrs in G.edges(data=True):
                w = attrs.get("weight", 1.0)
                net.add_edge(u, v, value=w,
                             color={"color": "#27272a", "highlight": "#9ca3af"},
                             smooth=False)
            net.set_options("""
            {
              "physics": {
                "stabilization": {"iterations": 100},
                "barnesHut": {"gravitationalConstant": -8000, "springLength": 120}
              },
              "interaction": {"hover": true, "tooltipDelay": 200}
            }
            """)
            self._graph_html = os.path.join(tempfile.gettempdir(), "riskpulse_graph.html")
            # Contournement bug Windows : PyVis.save_graph() ouvre le fichier
            # en cp1252 et plante sur les caracteres Unicode du vis.js minifie.
            # On recupere le HTML via generate_html() et on l'ecrit en UTF-8.
            html = net.generate_html(notebook=False)
            # Strip Bootstrap remote references (on ne les utilise pas, et elles
            # bloquent le rendu dans QtWebEngine quand le reseau est lent ou KO)
            import re as _re
            html = _re.sub(
                r'<link[^>]+href=["\']https://cdn\.jsdelivr\.net/[^"\']+["\'][^>]*>',
                "", html,
            )
            html = _re.sub(
                r'<script[^>]+src=["\']https://cdn\.jsdelivr\.net/[^"\']+["\'][^>]*></script>',
                "", html,
            )
            with open(self._graph_html, "w", encoding="utf-8") as f:
                f.write(html)

            # Charge dans la WebView integree
            if self._web_available and self._web_view is not None:
                from PySide6.QtCore import QUrl
                self._web_view.load(QUrl.fromLocalFile(self._graph_html))
        except Exception as e:
            logger.exception("PyVis generation failed")
            self._graph_html = None

    def _open_graph(self):
        if self._graph_html and os.path.exists(self._graph_html):
            webbrowser.open(f"file:///{self._graph_html.replace(os.sep, '/')}")
        else:
            QMessageBox.information(self, tr("Visualization"),
                                    tr("Install pyvis to enable graph visualization:") + " pip install pyvis")

    # ── Hooks ─────────────────────────────────

    def on_show(self):
        pass

    def on_analysis_updated(self):
        pass

    def retranslate(self):
        """Re-applique les libelles apres changement de langue."""
        self._title.setText(tr("Text Analysis"))
        self._scenario_lbl.setText(tr("Scenario:"))
        self._btn_url.setText(tr("From URL"))
        self._btn_import.setText(tr("Import"))
        self._btn_clear.setText(tr("Clear"))
        self._btn_analyse.setText(tr("Run Analysis"))
        self._btn_demo.setText(tr("Full Demo Mode"))
        self._text.setPlaceholderText(tr(self.PLACEHOLDER_KEY))
        self._stat_entities.set_label(tr("Entities"))
        self._stat_relations.set_label(tr("Relations"))
        self._stat_density.set_label(tr("Density"))
        self._stat_time.set_label(tr("Time"))
        self._tabs.setTabText(0, tr("Entities"))
        self._tabs.setTabText(1, tr("Relations"))
        self._tabs.setTabText(2, tr("Graph"))
        self._btn_open_graph.setText(tr("Open interactive graph"))
        self._ent_table.setHorizontalHeaderLabels([tr("Entity"), tr("Type"), tr("Freq.")])
        self._rel_table.setHorizontalHeaderLabels([tr("Source"), tr("Target"), tr("Weight")])
        self._rebuild_demo_combo()
