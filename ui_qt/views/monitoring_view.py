"""
Vue Watch & Monitor — l'agent qui surveille pendant ton sommeil.

Trois sections :
  1. Watch list   — entites surveillees + seuils
  2. Sources      — RSS / URLs surveilles
  3. Alerts feed  — historique chronologique des alertes
"""

import logging
import threading
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QDoubleSpinBox, QComboBox, QMessageBox,
    QInputDialog, QSizePolicy,
)

from ..components import Card, MetricCard
from ..i18n import tr
from ._base import build_header
from services.watchlist import get_watchlist
from services.monitoring_engine import get_engine
from services.feed_ingester import SUGGESTED_FEEDS

logger = logging.getLogger(__name__)


VERDICT_COLORS = {
    "CRITICAL": "#e8a0a0",
    "HIGH":     "#e3c08e",
    "MODERATE": "#9caec1",
    "LOW":      "#84cc9e",
    "MINIMAL":  "#52525b",
}


class MonitoringView(QWidget):

    _cycle_done = Signal(dict)
    _alert_received = Signal(dict)

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._wl = get_watchlist()
        try:
            self._engine = get_engine(controller=controller,
                                      on_alert=lambda a: self._alert_received.emit(a))
        except Exception:
            self._engine = None
        self._build()
        self._cycle_done.connect(self._on_cycle_done)
        self._alert_received.connect(self._on_alert_received)
        self.refresh()

    # ── Construction ───────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        # Header + actions
        head_row = QHBoxLayout()
        head_col = QVBoxLayout()
        self._caption_lbl, self._title_lbl = build_header(
            head_col, tr("AGENT"), tr("Watch & Monitor")
        )
        head_row.addLayout(head_col, 1)

        actions = QHBoxLayout()
        self._btn_run = QPushButton(tr("Check now"))
        self._btn_run.setProperty("variant", "primary")
        self._btn_run.clicked.connect(self._run_cycle)
        actions.addWidget(self._btn_run)
        self._btn_mark_seen = QPushButton(tr("Mark all read"))
        self._btn_mark_seen.clicked.connect(self._mark_all_seen)
        actions.addWidget(self._btn_mark_seen)
        aw = QWidget(); aw.setLayout(actions)
        head_row.addWidget(aw, 0, Qt.AlignTop)
        outer.addLayout(head_row)

        self._subtitle = QLabel(tr(
            "RiskPulse silently watches your sources, analyzes new content, "
            "and alerts you when a watched entity crosses a risk threshold."
        ))
        self._subtitle.setProperty("class", "subtitle")
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        # Stats
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._stat_watches = MetricCard(tr("Watched"),   "—")
        self._stat_sources = MetricCard(tr("Sources"),   "—")
        self._stat_alerts  = MetricCard(tr("Unread"),    "—")
        self._stat_last    = MetricCard(tr("Last check"),"—")
        for s in (self._stat_watches, self._stat_sources,
                  self._stat_alerts, self._stat_last):
            s.setMinimumHeight(82)
            stats_row.addWidget(s)
        outer.addLayout(stats_row)

        # Corps : 2 colonnes (watchlist+sources | alerts)
        body = QHBoxLayout()
        body.setSpacing(20)
        outer.addLayout(body, 1)

        # ── Colonne gauche : watchlist + sources ──
        left = QVBoxLayout()
        left.setSpacing(12)

        # Watchlist
        self._watch_card = Card(tr("Watched Entities"))
        wl_inner = QVBoxLayout()
        wl_inner.setSpacing(6)

        # Add form
        add_row = QHBoxLayout()
        self._watch_input = QLineEdit()
        self._watch_input.setPlaceholderText(tr("Entity name to watch..."))
        self._watch_input.returnPressed.connect(self._add_watch)
        add_row.addWidget(self._watch_input, 1)
        self._watch_threshold = QDoubleSpinBox()
        self._watch_threshold.setRange(0.0, 1.0)
        self._watch_threshold.setSingleStep(0.05)
        self._watch_threshold.setDecimals(2)
        self._watch_threshold.setValue(0.6)
        self._watch_threshold.setFixedWidth(80)
        add_row.addWidget(self._watch_threshold)
        self._btn_add_watch = QPushButton(tr("Add"))
        self._btn_add_watch.clicked.connect(self._add_watch)
        add_row.addWidget(self._btn_add_watch)
        wl_inner.addLayout(add_row)

        sep = QFrame(); sep.setObjectName("divider"); sep.setFixedHeight(1)
        wl_inner.addWidget(sep)

        self._watches_list = QVBoxLayout()
        self._watches_list.setSpacing(2)
        wl_inner.addLayout(self._watches_list)
        wl_inner.addStretch()
        self._watch_card.layout().addLayout(wl_inner)
        left.addWidget(self._watch_card)

        # Sources
        self._sources_card = Card(tr("Monitored Sources"))
        sr_inner = QVBoxLayout()
        sr_inner.setSpacing(6)
        add_src_row = QHBoxLayout()
        self._src_input = QLineEdit()
        self._src_input.setPlaceholderText(tr("URL or RSS feed..."))
        self._src_input.returnPressed.connect(self._add_source)
        add_src_row.addWidget(self._src_input, 1)
        self._src_type_cb = QComboBox()
        self._src_type_cb.addItems(["rss", "url"])
        self._src_type_cb.setFixedWidth(80)
        add_src_row.addWidget(self._src_type_cb)
        self._btn_add_src = QPushButton(tr("Add"))
        self._btn_add_src.clicked.connect(self._add_source)
        add_src_row.addWidget(self._btn_add_src)
        sr_inner.addLayout(add_src_row)

        # Suggestions
        sug_row = QHBoxLayout()
        sug_lbl = QLabel(tr("Suggested:"))
        sug_lbl.setProperty("class", "caption")
        sug_row.addWidget(sug_lbl)
        for s in SUGGESTED_FEEDS:
            btn = QPushButton(s["label"])
            btn.setStyleSheet(
                "QPushButton { padding: 2px 8px; font-size: 9px; }"
            )
            btn.clicked.connect(lambda _=False, sg=s: self._add_suggested(sg))
            sug_row.addWidget(btn)
        sug_row.addStretch()
        sr_inner.addLayout(sug_row)

        sep2 = QFrame(); sep2.setObjectName("divider"); sep2.setFixedHeight(1)
        sr_inner.addWidget(sep2)

        self._sources_list = QVBoxLayout()
        self._sources_list.setSpacing(2)
        sr_inner.addLayout(self._sources_list)
        sr_inner.addStretch()
        self._sources_card.layout().addLayout(sr_inner)
        left.addWidget(self._sources_card)

        left_w = QWidget(); left_w.setLayout(left)
        body.addWidget(left_w, 1)

        # ── Colonne droite : alerts feed ──
        self._alerts_card = Card(tr("Alerts Feed"))
        self._alerts_layout = QVBoxLayout()
        self._alerts_layout.setSpacing(8)
        self._alerts_placeholder = QLabel(tr("No alerts yet."))
        self._alerts_placeholder.setProperty("class", "subtitle")
        self._alerts_placeholder.setAlignment(Qt.AlignCenter)
        self._alerts_layout.addWidget(self._alerts_placeholder)
        self._alerts_card.layout().addLayout(self._alerts_layout)
        body.addWidget(self._alerts_card, 1)

    # ── Helpers de rendu ──────────────────────

    def _clear(self, layout):
        while layout.count():
            it = layout.takeAt(0)
            w = it.widget()
            if w: w.deleteLater()

    def refresh(self):
        """Recharge toute la vue depuis la base."""
        watches = self._wl.list_watches()
        sources = self._wl.list_sources()
        alerts  = self._wl.list_alerts(limit=50)
        unread  = self._wl.count_unread_alerts()

        self._stat_watches.set_value(str(len(watches)))
        self._stat_sources.set_value(str(len(sources)))
        self._stat_alerts.set_value(str(unread))
        last_check = "—"
        if sources:
            checks = [s.get("last_check") for s in sources if s.get("last_check")]
            if checks:
                last_check = max(checks)[11:16]
        self._stat_last.set_value(last_check)

        self._render_watches(watches)
        self._render_sources(sources)
        self._render_alerts(alerts)

    def _render_watches(self, watches):
        self._clear(self._watches_list)
        if not watches:
            ph = QLabel(tr("No watched entities. Add one above."))
            ph.setProperty("class", "subtitle")
            self._watches_list.addWidget(ph)
            return
        for w in watches:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 4, 0, 4)
            dot = QLabel("●")
            dot_color = "#84cc9e" if w["enabled"] else "#3f3f46"
            dot.setStyleSheet(f"color: {dot_color}; font-size: 9px;")
            row.addWidget(dot)
            name = QLabel(w["name"])
            name.setStyleSheet("color: #e4e4e7; font-size: 11px;")
            row.addWidget(name, 1)
            thr = QLabel(f"≥ {w['threshold']:.2f}")
            thr.setStyleSheet("color: #52525b; font-size: 10px;")
            thr.setFixedWidth(60)
            row.addWidget(thr)
            score = w.get("last_score")
            if score is not None:
                sc = QLabel(f"{score:.2f}")
                sc_color = "#e8a0a0" if score >= w["threshold"] else "#9ca3af"
                sc.setStyleSheet(f"color: {sc_color}; font-size: 11px;")
                sc.setFixedWidth(50)
                row.addWidget(sc)
            else:
                row.addWidget(QLabel(""))
            del_btn = QPushButton("×")
            del_btn.setFixedWidth(28)
            del_btn.setStyleSheet(
                "QPushButton { padding: 0; font-size: 14px; color: #52525b; }"
                "QPushButton:hover { color: #e8a0a0; }"
            )
            del_btn.clicked.connect(lambda _=False, wid=w["id"]: self._remove_watch(wid))
            row.addWidget(del_btn)
            rw = QWidget(); rw.setLayout(row)
            self._watches_list.addWidget(rw)

    def _render_sources(self, sources):
        self._clear(self._sources_list)
        if not sources:
            ph = QLabel(tr("No sources configured. Add one or pick a suggestion above."))
            ph.setProperty("class", "subtitle")
            ph.setWordWrap(True)
            self._sources_list.addWidget(ph)
            return
        for s in sources:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 4, 0, 4)
            type_lbl = QLabel(s["type"].upper())
            type_lbl.setStyleSheet(
                "color: #e3c08e; font-size: 9px; letter-spacing: 1px;"
            )
            type_lbl.setFixedWidth(40)
            row.addWidget(type_lbl)
            label = QLabel(s["label"] or s["url"])
            label.setStyleSheet("color: #e4e4e7; font-size: 11px;")
            label.setToolTip(s["url"])
            row.addWidget(label, 1)
            items_seen = s.get("items_seen") or 0
            items_lbl = QLabel(f"{items_seen} items")
            items_lbl.setStyleSheet("color: #52525b; font-size: 10px;")
            items_lbl.setFixedWidth(70)
            row.addWidget(items_lbl)
            status = s.get("last_status") or "—"
            st_lbl = QLabel(status[:8])
            st_color = "#84cc9e" if status == "OK" else ("#e8a0a0" if "ERROR" in status else "#52525b")
            st_lbl.setStyleSheet(f"color: {st_color}; font-size: 9px;")
            st_lbl.setFixedWidth(60)
            row.addWidget(st_lbl)
            del_btn = QPushButton("×")
            del_btn.setFixedWidth(28)
            del_btn.setStyleSheet(
                "QPushButton { padding: 0; font-size: 14px; color: #52525b; }"
                "QPushButton:hover { color: #e8a0a0; }"
            )
            del_btn.clicked.connect(lambda _=False, sid=s["id"]: self._remove_source(sid))
            row.addWidget(del_btn)
            rw = QWidget(); rw.setLayout(row)
            self._sources_list.addWidget(rw)

    def _render_alerts(self, alerts):
        self._clear(self._alerts_layout)
        if not alerts:
            ph = QLabel(tr("No alerts yet. Run 'Check now' to fetch sources."))
            ph.setProperty("class", "subtitle")
            ph.setAlignment(Qt.AlignCenter)
            self._alerts_layout.addWidget(ph)
            return

        for a in alerts:
            block = QFrame()
            block.setStyleSheet(
                "QFrame { border-left: 2px solid #e3c08e; padding-left: 12px; }"
                if a["seen"] == 0 else
                "QFrame { border-left: 2px solid #27272a; padding-left: 12px; }"
            )
            lay = QVBoxLayout(block)
            lay.setContentsMargins(12, 6, 0, 6)
            lay.setSpacing(2)

            # Top : timestamp + verdict
            top = QHBoxLayout()
            ts = QLabel((a["timestamp"] or "")[:16])
            ts.setStyleSheet("color: #52525b; font-size: 9px;")
            top.addWidget(ts)
            top.addStretch()
            v = a["verdict"] or "—"
            vcol = VERDICT_COLORS.get(v, "#9ca3af")
            v_lbl = QLabel(v)
            v_lbl.setStyleSheet(f"color: {vcol}; font-size: 9px; font-weight: 700;")
            top.addWidget(v_lbl)
            lay.addLayout(top)

            # Entite + score
            ent = QLabel(f"{a['entity_name']}  ·  {a['score']:.2f}")
            ent.setStyleSheet("color: #e4e4e7; font-size: 12px; font-weight: 700;")
            lay.addWidget(ent)

            # Message
            msg = QLabel(a["message"] or "")
            msg.setStyleSheet("color: #a1a1aa; font-size: 10px;")
            msg.setWordWrap(True)
            lay.addWidget(msg)

            # Source link
            if a.get("source_url"):
                src_lbl = QLabel(f"→ {a['source_url'][:80]}")
                src_lbl.setStyleSheet("color: #6b7280; font-size: 9px;")
                lay.addWidget(src_lbl)

            self._alerts_layout.addWidget(block)

    # ── Actions ───────────────────────────────

    def _add_watch(self):
        name = self._watch_input.text().strip()
        if not name:
            return
        thr = float(self._watch_threshold.value())
        self._wl.add_watch(name, threshold=thr)
        self._watch_input.clear()
        self.refresh()
        self._app.toast(f"{tr('Now watching')}: {name}", "success")

    def _remove_watch(self, wid: int):
        self._wl.remove_watch(wid)
        self.refresh()

    def _add_source(self):
        url = self._src_input.text().strip()
        if not url:
            return
        src_type = self._src_type_cb.currentText()
        self._wl.add_source(url, label=url, source_type=src_type)
        self._src_input.clear()
        self.refresh()
        self._app.toast(f"{tr('Source added')}: {url[:50]}", "success")

    def _add_suggested(self, sug: dict):
        self._wl.add_source(sug["url"], label=sug["label"], source_type=sug["type"])
        self.refresh()
        self._app.toast(f"{tr('Suggested source added')}: {sug['label']}", "success")

    def _remove_source(self, sid: int):
        self._wl.remove_source(sid)
        self.refresh()

    def _mark_all_seen(self):
        self._wl.mark_all_seen()
        self.refresh()
        if hasattr(self._app, "update_alerts_badge"):
            self._app.update_alerts_badge()

    def _run_cycle(self):
        if not self._engine:
            self._app.toast(tr("Engine not available"), "error")
            return
        sources = self._wl.list_sources(enabled_only=True)
        if not sources:
            self._app.toast(tr("Add at least one source first"), "warning")
            return
        watches = self._wl.list_watches(enabled_only=True)
        if not watches:
            self._app.toast(tr("Add at least one watched entity"), "warning")
            return

        self._btn_run.setEnabled(False)
        self._btn_run.setText(tr("Checking..."))
        self._app.set_status(tr("Monitoring cycle running..."), "info", 0.3)

        def _job():
            try:
                summary = self._engine.run_cycle(max_items_per_source=3)
                self._cycle_done.emit(summary)
            except Exception as e:
                logger.exception("Monitoring cycle failed")
                self._cycle_done.emit({"error": str(e)})

        threading.Thread(target=_job, daemon=True).start()

    def _on_cycle_done(self, summary: dict):
        self._btn_run.setEnabled(True)
        self._btn_run.setText(tr("Check now"))
        if "error" in summary:
            self._app.toast(summary["error"], "error")
            return
        n_sources = summary.get("n_sources", 0)
        n_items = summary.get("n_items", 0)
        n_alerts = summary.get("n_alerts", 0)
        msg = (f"{tr('Cycle done')}: {n_items} {tr('new items')}, "
               f"{n_alerts} {tr('alerts')} ({n_sources} {tr('sources')})")
        self._app.set_status(msg, "success", 1.0)
        if n_alerts > 0:
            self._app.toast(f"{n_alerts} {tr('new alert(s)')}", "warning")
        else:
            self._app.toast(tr("Cycle completed, no new alerts"), "info")
        self.refresh()
        if hasattr(self._app, "update_alerts_badge"):
            self._app.update_alerts_badge()

    def _on_alert_received(self, alert: dict):
        # Toast en temps reel (en plus de l'alerte persistee)
        self._app.toast(
            f"⚡ {alert.get('entity_name','')}  ·  {alert.get('verdict','')}  "
            f"({alert.get('score',0):.2f})",
            "warning",
        )
        if hasattr(self._app, "update_alerts_badge"):
            self._app.update_alerts_badge()

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        self.refresh()

    def on_show(self):
        self.refresh()

    def retranslate(self):
        self._caption_lbl.setText(tr("AGENT"))
        self._title_lbl.setText(tr("Watch & Monitor"))
        self._subtitle.setText(tr(
            "RiskPulse silently watches your sources, analyzes new content, "
            "and alerts you when a watched entity crosses a risk threshold."
        ))
        self._btn_run.setText(tr("Check now"))
        self._btn_mark_seen.setText(tr("Mark all read"))
        self._btn_add_watch.setText(tr("Add"))
        self._btn_add_src.setText(tr("Add"))
        self._watch_input.setPlaceholderText(tr("Entity name to watch..."))
        self._src_input.setPlaceholderText(tr("URL or RSS feed..."))
        self._stat_watches.set_label(tr("Watched"))
        self._stat_sources.set_label(tr("Sources"))
        self._stat_alerts.set_label(tr("Unread"))
        self._stat_last.set_label(tr("Last check"))
        self._watch_card.set_title(tr("Watched Entities"))
        self._sources_card.set_title(tr("Monitored Sources"))
        self._alerts_card.set_title(tr("Alerts Feed"))
