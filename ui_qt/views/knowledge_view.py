"""
Vue Knowledge Base — base de connaissance persistante.
Affiche toutes les entites jamais analysees, leur historique et leurs liens.
"""

import logging
import threading
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QMessageBox,
)

from ..components import Card, MetricCard
from ..i18n import tr
from ._base import build_header
from services.knowledge_base import get_kb

logger = logging.getLogger(__name__)


# Couleurs verdict (alignees palette premium)
VERDICT_COLORS = {
    "CRITICAL": "#e8a0a0",
    "HIGH":     "#e3c08e",
    "MODERATE": "#9caec1",
    "LOW":      "#84cc9e",
    "MINIMAL":  "#52525b",
}

TREND_INFO = {
    "rising":  ("↑", "#e8a0a0"),
    "falling": ("↓", "#84cc9e"),
    "stable":  ("·", "#52525b"),
    "new":     ("●", "#e3c08e"),
}


class KnowledgeView(QWidget):

    _enrichment_done  = Signal(int, dict)   # (entity_id, enrichment dict)
    _enrichment_error = Signal(int, str)

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._kb = get_kb()
        self._current_entity_id = None
        self._build()
        self._enrichment_done.connect(self._on_enrichment_done)
        self._enrichment_error.connect(self._on_enrichment_error)

    # ── Construction ──────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        # Header
        head_row = QHBoxLayout()
        head_col = QVBoxLayout()
        self._caption_lbl, self._title_lbl = build_header(
            head_col, tr("MEMORY"), tr("Knowledge Base")
        )
        head_row.addLayout(head_col, 1)

        # Boutons header
        actions = QHBoxLayout()
        self._btn_refresh = QPushButton(tr("Refresh"))
        self._btn_refresh.clicked.connect(self.refresh)
        actions.addWidget(self._btn_refresh)
        self._btn_clear = QPushButton(tr("Clear KB"))
        self._btn_clear.clicked.connect(self._clear_kb)
        actions.addWidget(self._btn_clear)
        aw = QWidget(); aw.setLayout(actions)
        head_row.addWidget(aw, 0, Qt.AlignTop)
        outer.addLayout(head_row)

        self._subtitle = QLabel(tr(
            "Every analysis enriches your private knowledge base. "
            "Browse all entities, track their risk evolution over time, and discover cross-analysis connections."
        ))
        self._subtitle.setProperty("class", "subtitle")
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        # Stats row
        self._stats_row = QHBoxLayout()
        self._stats_row.setSpacing(8)
        self._stat_analyses    = MetricCard(tr("Analyses"),       "—")
        self._stat_entities    = MetricCard(tr("Unique entities"),"—")
        self._stat_appearances = MetricCard(tr("Total mentions"), "—")
        self._stat_avg_risk    = MetricCard(tr("Avg risk"),       "—")
        for s in (self._stat_analyses, self._stat_entities,
                  self._stat_appearances, self._stat_avg_risk):
            s.setMinimumHeight(82)
            self._stats_row.addWidget(s)
        outer.addLayout(self._stats_row)

        # Search bar
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        s_lbl = QLabel(tr("SEARCH"))
        s_lbl.setProperty("class", "caption")
        search_row.addWidget(s_lbl)
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("Filter entities by name..."))
        self._search.textChanged.connect(self._on_search)
        search_row.addWidget(self._search, 1)
        outer.addLayout(search_row)

        # Splitter : table + detail
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)
        outer.addWidget(splitter, 1)

        self._table = self._build_entity_table()
        splitter.addWidget(self._table)

        self._detail_panel = self._build_detail_panel()
        splitter.addWidget(self._detail_panel)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([600, 480])

    def _build_entity_table(self) -> QTableWidget:
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels([
            tr("Entity"), tr("Type"), tr("Verdict"),
            tr("Avg score"), tr("Analyses"), tr("Trend"),
        ])
        h = table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setAlternatingRowColors(True)
        table.itemSelectionChanged.connect(self._on_row_selected)
        return table

    def _build_detail_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Profile card
        self._profile_card = Card(tr("Entity Profile"))
        self._profile_layout = QVBoxLayout()
        self._profile_layout.setSpacing(8)
        self._profile_placeholder = QLabel(tr("Select an entity to see its history."))
        self._profile_placeholder.setProperty("class", "subtitle")
        self._profile_placeholder.setAlignment(Qt.AlignCenter)
        self._profile_layout.addWidget(self._profile_placeholder)
        self._profile_card.layout().addLayout(self._profile_layout)
        layout.addWidget(self._profile_card)

        # Timeline card
        self._timeline_card = Card(tr("Risk Timeline"))
        self._timeline_layout = QVBoxLayout()
        self._timeline_layout.setSpacing(4)
        self._timeline_card.layout().addLayout(self._timeline_layout)
        layout.addWidget(self._timeline_card, 1)

        # Neighbors card
        self._neighbors_card = Card(tr("Co-occurring Entities"))
        self._neighbors_layout = QVBoxLayout()
        self._neighbors_layout.setSpacing(4)
        self._neighbors_card.layout().addLayout(self._neighbors_layout)
        layout.addWidget(self._neighbors_card)

        # External Data card (Wikidata + Wikipedia)
        self._enrich_card = Card(tr("External Data"))
        self._enrich_layout = QVBoxLayout()
        self._enrich_layout.setSpacing(6)
        self._enrich_card.layout().addLayout(self._enrich_layout)
        layout.addWidget(self._enrich_card)

        return panel

    # ── Data refresh ───────────────────────────

    def refresh(self):
        """Recharge la KB et met a jour la vue."""
        stats = self._kb.stats()
        self._stat_analyses.set_value(str(stats["n_analyses"]))
        self._stat_entities.set_value(str(stats["n_entities"]))
        self._stat_appearances.set_value(str(stats["n_appearances"]))
        self._stat_avg_risk.set_value(f"{stats['avg_risk']:.2f}")
        self._populate_table(self._search.text())

    def _populate_table(self, search: str = ""):
        self._table.setRowCount(0)
        entities = self._kb.list_entities(search=search, limit=200)
        self._table.setRowCount(len(entities))

        for row, e in enumerate(entities):
            # Entity
            it_name = QTableWidgetItem(e.display_name)
            it_name.setData(Qt.UserRole, e.id)
            self._table.setItem(row, 0, it_name)

            # Type
            self._table.setItem(row, 1, QTableWidgetItem(e.type_label or "—"))

            # Verdict (basé sur avg_risk_score)
            verdict = self._score_to_verdict(e.avg_risk_score)
            it_verdict = QTableWidgetItem(verdict)
            from PySide6.QtGui import QColor, QBrush
            it_verdict.setForeground(QBrush(QColor(VERDICT_COLORS.get(verdict, "#9ca3af"))))
            self._table.setItem(row, 2, it_verdict)

            # Avg score
            self._table.setItem(row, 3, QTableWidgetItem(f"{e.avg_risk_score:.2f}"))

            # Analyses count
            self._table.setItem(row, 4, QTableWidgetItem(str(e.n_analyses)))

            # Trend
            arrow, color = TREND_INFO.get(e.trend, ("·", "#52525b"))
            it_trend = QTableWidgetItem(arrow)
            from PySide6.QtGui import QColor, QBrush
            it_trend.setForeground(QBrush(QColor(color)))
            self._table.setItem(row, 5, it_trend)

    def _score_to_verdict(self, score: float) -> str:
        if score >= 0.85: return "CRITICAL"
        if score >= 0.65: return "HIGH"
        if score >= 0.40: return "MODERATE"
        if score >= 0.20: return "LOW"
        return "MINIMAL"

    # ── Selection ───────────────────────────

    def _on_row_selected(self):
        items = self._table.selectedItems()
        if not items:
            return
        eid = items[0].data(Qt.UserRole)
        if not eid:
            return
        self._render_detail(eid)

    def _render_detail(self, entity_id: int):
        history = self._kb.get_entity_history(entity_id)
        if not history:
            return
        self._current_entity_id = entity_id
        ent = history["entity"]
        appearances = history.get("appearances", [])
        neighbors = history.get("neighbors", [])

        # ── Profile ──
        self._clear(self._profile_layout)
        grid = QGridLayout()
        grid.setSpacing(8)
        rows = [
            (tr("Canonical"),    ent.get("canonical_name", "").title()),
            (tr("Type"),         ent.get("type_label", "—")),
            (tr("First seen"),   (ent.get("first_seen") or "—")[:16]),
            (tr("Last seen"),    (ent.get("last_seen")  or "—")[:16]),
            (tr("Analyses"),     str(ent.get("n_analyses", 0))),
            (tr("Avg risk"),     f"{ent.get('avg_risk_score') or 0:.3f}"),
            (tr("Max risk"),     f"{ent.get('max_risk_score') or 0:.3f}"),
            (tr("Trend"),        (ent.get("trend") or "—").upper()),
        ]
        for i, (k, v) in enumerate(rows):
            kl = QLabel(k.upper())
            kl.setStyleSheet("color: #52525b; font-size: 8px; letter-spacing: 1px;")
            vl = QLabel(str(v))
            vl.setStyleSheet("color: #e4e4e7; font-size: 11px;")
            grid.addWidget(kl, i // 2, (i % 2) * 2)
            grid.addWidget(vl, i // 2, (i % 2) * 2 + 1)
        self._profile_layout.addLayout(grid)

        # ── Timeline ──
        self._clear(self._timeline_layout)
        if not appearances:
            ph = QLabel(tr("No appearances recorded."))
            ph.setProperty("class", "subtitle")
            self._timeline_layout.addWidget(ph)
        else:
            # Header
            header = QHBoxLayout()
            for txt, w in [(tr("DATE"), 130), (tr("SCORE"), 60),
                           (tr("VERDICT"), 80), (tr("ANALYSIS"), 0)]:
                lbl = QLabel(txt)
                lbl.setProperty("class", "caption")
                if w:
                    lbl.setFixedWidth(w)
                header.addWidget(lbl, 1 if not w else 0)
            hw = QWidget(); hw.setLayout(header)
            self._timeline_layout.addWidget(hw)

            sep = QFrame(); sep.setObjectName("divider"); sep.setFixedHeight(1)
            self._timeline_layout.addWidget(sep)

            for app in appearances[-10:]:
                row = QHBoxLayout()
                row.setSpacing(8)
                row.setContentsMargins(0, 4, 0, 4)

                ts = QLabel((app.get("timestamp") or "")[:16])
                ts.setStyleSheet("color: #a1a1aa; font-size: 10px;")
                ts.setFixedWidth(130)
                row.addWidget(ts)

                score = QLabel(f"{app.get('risk_score') or 0:.2f}")
                score.setStyleSheet("color: #e4e4e7; font-size: 10px;")
                score.setFixedWidth(60)
                row.addWidget(score)

                verdict = app.get("verdict") or "—"
                vcol = VERDICT_COLORS.get(verdict, "#9ca3af")
                v_lbl = QLabel(verdict)
                v_lbl.setStyleSheet(f"color: {vcol}; font-size: 10px; font-weight: 600;")
                v_lbl.setFixedWidth(80)
                row.addWidget(v_lbl)

                ttl = QLabel((app.get("title") or "")[:50])
                ttl.setStyleSheet("color: #9ca3af; font-size: 10px;")
                row.addWidget(ttl, 1)

                rw = QWidget(); rw.setLayout(row)
                self._timeline_layout.addWidget(rw)

            # Mini "sparkline" textuelle de l'evolution du score
            scores = [a.get("risk_score") or 0 for a in appearances]
            if len(scores) > 1:
                first = scores[0]; last = scores[-1]
                delta = last - first
                evo = QLabel(
                    f"Evolution : {first:.2f} → {last:.2f}   ({'+' if delta>=0 else ''}{delta:.2f})"
                )
                evo_color = "#e8a0a0" if delta > 0.05 else ("#84cc9e" if delta < -0.05 else "#9ca3af")
                evo.setStyleSheet(f"color: {evo_color}; font-size: 11px; font-weight: 700;")
                evo.setContentsMargins(0, 6, 0, 0)
                self._timeline_layout.addWidget(evo)

        # ── Neighbors ──
        self._clear(self._neighbors_layout)
        if not neighbors:
            ph = QLabel(tr("No co-occurrences yet."))
            ph.setProperty("class", "subtitle")
            self._neighbors_layout.addWidget(ph)
        else:
            for n in neighbors:
                row = QHBoxLayout()
                row.setSpacing(8)
                row.setContentsMargins(0, 2, 0, 2)
                name = QLabel(n["name"][:30])
                name.setStyleSheet("color: #e4e4e7; font-size: 10px;")
                row.addWidget(name, 1)
                cnt = QLabel(f"×{n['count']}")
                cnt.setStyleSheet("color: #9ca3af; font-size: 10px;")
                cnt.setFixedWidth(40)
                row.addWidget(cnt)
                score = QLabel(f"{n['score']:.2f}")
                score.setStyleSheet("color: #e3c08e; font-size: 10px;")
                score.setFixedWidth(40)
                row.addWidget(score)
                w = QWidget(); w.setLayout(row)
                self._neighbors_layout.addWidget(w)

        # ── External Data (Wikidata) ──
        enrichment = self._kb.get_enrichment(entity_id)
        self._render_enrichment(entity_id, enrichment)

    # ── Enrichissement Wikidata ───────────────

    def _render_enrichment(self, entity_id: int, data: dict | None):
        """Affiche le panneau External Data ou propose un enrich."""
        self._clear(self._enrich_layout)

        if not data:
            # Pas encore enrichie
            row = QHBoxLayout()
            ph = QLabel(tr("This entity has not been enriched yet."))
            ph.setProperty("class", "subtitle")
            ph.setWordWrap(True)
            row.addWidget(ph, 1)
            btn = QPushButton(tr("Enrich now"))
            btn.setProperty("variant", "primary")
            btn.clicked.connect(lambda: self._trigger_enrich(entity_id))
            row.addWidget(btn)
            rw = QWidget(); rw.setLayout(row)
            self._enrich_layout.addWidget(rw)
            return

        if data.get("status") == "not_found":
            row = QHBoxLayout()
            ph = QLabel(tr("No Wikidata match found for this entity."))
            ph.setProperty("class", "subtitle")
            ph.setWordWrap(True)
            row.addWidget(ph, 1)
            btn = QPushButton(tr("Retry"))
            btn.clicked.connect(lambda: self._trigger_enrich(entity_id, force=True))
            row.addWidget(btn)
            rw = QWidget(); rw.setLayout(row)
            self._enrich_layout.addWidget(rw)
            return

        # ── Status enriched : affiche les donnees ──
        # Header (badge ENRICHED + bouton refresh)
        head = QHBoxLayout()
        badge = QLabel("ENRICHED")
        badge.setStyleSheet(
            "color: #84cc9e; font-weight: 700; font-size: 9px; letter-spacing: 1.5px;"
            "border: 1px solid #84cc9e; padding: 1px 5px; border-radius: 3px;"
        )
        head.addWidget(badge)
        head.addStretch()
        if data.get("wikidata_id"):
            wd_lbl = QLabel(f"Wikidata · {data['wikidata_id']}")
            wd_lbl.setStyleSheet("color: #52525b; font-size: 9px;")
            head.addWidget(wd_lbl)
        refresh = QPushButton("↻")
        refresh.setFixedSize(24, 22)
        refresh.setStyleSheet(
            "QPushButton { padding: 0; color: #52525b; font-size: 12px; }"
            "QPushButton:hover { color: #e4e4e7; }"
        )
        refresh.clicked.connect(lambda: self._trigger_enrich(entity_id, force=True))
        head.addWidget(refresh)
        hw = QWidget(); hw.setLayout(head)
        self._enrich_layout.addWidget(hw)

        # Label officiel + description
        if data.get("wikidata_label"):
            lbl = QLabel(data["wikidata_label"])
            lbl.setStyleSheet("color: #e4e4e7; font-size: 12px; font-weight: 700;")
            self._enrich_layout.addWidget(lbl)
        if data.get("wikidata_desc"):
            desc = QLabel(data["wikidata_desc"])
            desc.setStyleSheet("color: #a1a1aa; font-size: 10px; font-style: italic;")
            desc.setWordWrap(True)
            self._enrich_layout.addWidget(desc)

        # Grille de facts (2 colonnes)
        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setContentsMargins(0, 6, 0, 6)
        facts = [
            (tr("Type"),       data.get("type_label")),
            (tr("Country"),    data.get("country")),
            (tr("City"),       data.get("city")),
            (tr("Sector"),     data.get("sector")),
            (tr("Founded"),    (data.get("founded") or "")[:10]),
            (tr("Employees"),  data.get("employees")),
            (tr("Revenue"),    data.get("revenue")),
            (tr("Parent"),     data.get("parent_org")),
        ]
        facts = [(k, v) for k, v in facts if v]
        for i, (k, v) in enumerate(facts):
            kl = QLabel(k.upper())
            kl.setStyleSheet("color: #52525b; font-size: 8px; letter-spacing: 1px;")
            vl = QLabel(str(v))
            vl.setStyleSheet("color: #e4e4e7; font-size: 10px;")
            vl.setWordWrap(True)
            grid.addWidget(kl, i // 2, (i % 2) * 2)
            grid.addWidget(vl, i // 2, (i % 2) * 2 + 1)
        self._enrich_layout.addLayout(grid)

        # Subsidiaries
        subs_json = data.get("subsidiaries_json")
        if subs_json:
            try:
                import json as _json
                subs = _json.loads(subs_json)
                if subs:
                    sl = QLabel("SUBSIDIARIES")
                    sl.setStyleSheet("color: #52525b; font-size: 8px; letter-spacing: 1px;")
                    self._enrich_layout.addWidget(sl)
                    sub_txt = " · ".join(s for s in subs[:5] if s)
                    sw = QLabel(sub_txt)
                    sw.setStyleSheet("color: #e4e4e7; font-size: 10px;")
                    sw.setWordWrap(True)
                    self._enrich_layout.addWidget(sw)
            except Exception:
                pass

        # Wikipedia summary
        if data.get("wikipedia_summary"):
            sep = QFrame(); sep.setObjectName("divider"); sep.setFixedHeight(1)
            self._enrich_layout.addWidget(sep)
            wl = QLabel("WIKIPEDIA")
            wl.setStyleSheet("color: #52525b; font-size: 8px; letter-spacing: 1px;")
            self._enrich_layout.addWidget(wl)
            summary = QLabel(data["wikipedia_summary"][:500] + "...")
            summary.setStyleSheet("color: #a1a1aa; font-size: 10px;")
            summary.setWordWrap(True)
            self._enrich_layout.addWidget(summary)

        # Liens
        if data.get("website") or data.get("wikipedia_url"):
            links_row = QHBoxLayout()
            links_row.setSpacing(12)
            if data.get("website"):
                w_lbl = QLabel(f'<a href="{data["website"]}" style="color: #9caec1;">→ {tr("Website")}</a>')
                w_lbl.setOpenExternalLinks(True)
                w_lbl.setStyleSheet("font-size: 10px;")
                links_row.addWidget(w_lbl)
            if data.get("wikipedia_url"):
                wp_lbl = QLabel(f'<a href="{data["wikipedia_url"]}" style="color: #9caec1;">→ Wikipedia</a>')
                wp_lbl.setOpenExternalLinks(True)
                wp_lbl.setStyleSheet("font-size: 10px;")
                links_row.addWidget(wp_lbl)
            links_row.addStretch()
            lw = QWidget(); lw.setLayout(links_row)
            self._enrich_layout.addWidget(lw)

    def _trigger_enrich(self, entity_id: int, force: bool = False):
        """Lance l'enrichissement Wikidata dans un thread."""
        # Placeholder UI : loading
        self._clear(self._enrich_layout)
        loading = QLabel(tr("Fetching Wikidata + Wikipedia..."))
        loading.setProperty("class", "subtitle")
        loading.setAlignment(Qt.AlignCenter)
        self._enrich_layout.addWidget(loading)

        if hasattr(self._app, "toast"):
            self._app.toast(tr("Enrichment running..."), "info")

        def _job():
            try:
                data = self._kb.enrich_entity(entity_id, force=force)
                self._enrichment_done.emit(entity_id, data or {})
            except Exception as e:
                logger.exception("Enrichment failed")
                self._enrichment_error.emit(entity_id, str(e))

        threading.Thread(target=_job, daemon=True).start()

    def _on_enrichment_done(self, entity_id: int, data: dict):
        # Re-render seulement si on est encore sur la meme entite
        if self._current_entity_id != entity_id:
            return
        self._render_enrichment(entity_id, data)
        if hasattr(self._app, "toast"):
            if data.get("status") == "enriched":
                self._app.toast(tr("Enrichment complete"), "success")
            else:
                self._app.toast(tr("No Wikidata match"), "warning")

    def _on_enrichment_error(self, entity_id: int, msg: str):
        if hasattr(self._app, "toast"):
            self._app.toast(f"Enrichment error: {msg}", "error")
        self._render_enrichment(entity_id, None)

    # ── Actions ───────────────────────────────

    def _on_search(self, text: str):
        self._populate_table(text)

    def _clear_kb(self):
        ans = QMessageBox.question(
            self, tr("Clear Knowledge Base"),
            tr("Delete ALL analyses and entities from the knowledge base?\n\n"
               "This cannot be undone."),
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans == QMessageBox.Yes:
            self._kb.clear_all()
            self.refresh()
            if hasattr(self._app, "toast"):
                self._app.toast(tr("Knowledge Base cleared"), "info")

    def _clear(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                # nested layout
                while item.layout().count():
                    inner = item.layout().takeAt(0)
                    iw = inner.widget()
                    if iw: iw.deleteLater()

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        # Une nouvelle analyse a ete persistee : refresh
        self.refresh()

    def on_show(self):
        self.refresh()

    def retranslate(self):
        self._caption_lbl.setText(tr("MEMORY"))
        self._title_lbl.setText(tr("Knowledge Base"))
        self._subtitle.setText(tr(
            "Every analysis enriches your private knowledge base. "
            "Browse all entities, track their risk evolution over time, and discover cross-analysis connections."
        ))
        self._btn_refresh.setText(tr("Refresh"))
        self._btn_clear.setText(tr("Clear KB"))
        self._search.setPlaceholderText(tr("Filter entities by name..."))
        self._stat_analyses.set_label(tr("Analyses"))
        self._stat_entities.set_label(tr("Unique entities"))
        self._stat_appearances.set_label(tr("Total mentions"))
        self._stat_avg_risk.set_label(tr("Avg risk"))
        self._profile_card.set_title(tr("Entity Profile"))
        self._timeline_card.set_title(tr("Risk Timeline"))
        self._neighbors_card.set_title(tr("Co-occurring Entities"))
        self._enrich_card.set_title(tr("External Data"))
        self._table.setHorizontalHeaderLabels([
            tr("Entity"), tr("Type"), tr("Verdict"),
            tr("Avg score"), tr("Analyses"), tr("Trend"),
        ])
