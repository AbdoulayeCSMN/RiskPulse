"""Vue Dashboard — PySide6 (vue d'ensemble + exports)."""

import csv
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QFileDialog, QMessageBox, QScrollArea,
)

from ..components import Card, MetricCard
from ..i18n import tr
from ._base import build_header


class DashboardView(QWidget):

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        # ── Header avec actions ──
        header_row = QHBoxLayout()
        header_col = QVBoxLayout()
        self._caption_lbl, self._title_lbl = build_header(
            header_col, tr("OVERVIEW"), tr("Dashboard")
        )
        header_row.addLayout(header_col, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._btn_pdf = QPushButton(tr("Export PDF"))
        self._btn_pdf.setProperty("variant", "primary")
        self._btn_pdf.clicked.connect(self._export_pdf)
        actions.addWidget(self._btn_pdf)

        self._btn_csv = QPushButton(tr("Export CSV"))
        self._btn_csv.clicked.connect(self._export_csv)
        actions.addWidget(self._btn_csv)

        self._btn_json = QPushButton(tr("Export JSON"))
        self._btn_json.clicked.connect(self._export_json)
        actions.addWidget(self._btn_json)

        actions_w = QWidget()
        actions_w.setLayout(actions)
        actions_w.setMaximumHeight(64)
        header_row.addWidget(actions_w, 0, Qt.AlignTop)
        outer.addLayout(header_row)

        # ── Ligne de metric cards ──
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(8)

        self._metrics = {}
        for key, label in [
            ("nb_entities",       "Entities"),
            ("nb_relations",      "Relations"),
            ("model_a_anomalies", "Anomalies A"),
            ("model_b_anomalies", "Anomalies B"),
            ("processing_time",   "Time (s)"),
            ("graph_density",     "Density"),
        ]:
            mc = MetricCard(label=tr(label), value="—")
            mc.setMinimumHeight(90)
            metrics_row.addWidget(mc)
            self._metrics[key] = mc

        outer.addLayout(metrics_row)

        # ── Comparaison + Critical nodes (cote a cote) ──
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(20)

        # Card comparaison
        self._comp_card = Card(tr("Model Comparison"))
        self._comp_layout = QVBoxLayout()
        self._comp_layout.setSpacing(8)
        self._comp_placeholder = QLabel(tr("No analysis available."))
        self._comp_placeholder.setProperty("class", "subtitle")
        self._comp_layout.addWidget(self._comp_placeholder)
        self._comp_card.layout().addLayout(self._comp_layout)
        bottom_row.addWidget(self._comp_card, 1)

        # Card top critical
        self._crit_card = Card(tr("Top Critical Nodes"))
        self._crit_layout = QVBoxLayout()
        self._crit_layout.setSpacing(6)
        self._crit_placeholder = QLabel(tr("Awaiting analysis..."))
        self._crit_placeholder.setProperty("class", "subtitle")
        self._crit_layout.addWidget(self._crit_placeholder)
        self._crit_card.layout().addLayout(self._crit_layout)
        bottom_row.addWidget(self._crit_card, 1)

        outer.addLayout(bottom_row)

        # ── Operation log ──
        self._log_card = Card(tr("Operation Log"))
        self._log_layout = QVBoxLayout()
        self._log_layout.setSpacing(4)
        self._log_placeholder = QLabel(tr("No operations yet."))
        self._log_placeholder.setProperty("class", "subtitle")
        self._log_layout.addWidget(self._log_placeholder)
        self._log_card.layout().addLayout(self._log_layout)
        outer.addWidget(self._log_card, 1)

    # ── Rendu ─────────────────────────────────

    def _render(self, data: dict):
        # Metriques
        for key, mc in self._metrics.items():
            val = data.get(key, "—")
            if isinstance(val, float):
                val = f"{val:.3f}"
            mc.set_value(str(val))

        # Comparaison
        self._clear_layout(self._comp_layout)
        a = data.get("model_a_anomalies", 0)
        b = data.get("model_b_anomalies", 0)
        agr = data.get("agreement_rate", 0)

        ma = QLabel(f"{tr('Model A')}  →  {a} {tr('anomalies')}")
        ma.setProperty("class", "subtitle")
        self._comp_layout.addWidget(ma)
        mb = QLabel(f"{tr('Model B')}  →  {b} {tr('anomalies')}")
        mb.setProperty("class", "subtitle")
        self._comp_layout.addWidget(mb)
        agr_lbl = QLabel(f"{tr('Agreement')}: {agr:.0%}")
        agr_lbl.setProperty("class", "h3")
        agr_lbl.setContentsMargins(0, 8, 0, 4)
        self._comp_layout.addWidget(agr_lbl)
        insight = data.get("key_insight", "")
        if insight:
            ins = QLabel(insight)
            ins.setProperty("class", "subtitle")
            ins.setWordWrap(True)
            self._comp_layout.addWidget(ins)
        self._comp_layout.addStretch()

        # Critical
        self._clear_layout(self._crit_layout)
        critical = data.get("critical_nodes", [])
        if not critical:
            ph = QLabel(tr("No data."))
            ph.setProperty("class", "subtitle")
            self._crit_layout.addWidget(ph)
        for i, n in enumerate(critical[:5], 1):
            row = QHBoxLayout()
            num = QLabel(f"#{i}")
            num.setProperty("class", "caption")
            num.setFixedWidth(28)
            row.addWidget(num)
            name = QLabel(n.get("name", "")[:30])
            row.addWidget(name, 1)
            score = QLabel(f"{n.get('composite', 0):.3f}")
            score.setProperty("class", "subtitle")
            row.addWidget(score)
            w = QWidget(); w.setLayout(row)
            self._crit_layout.addWidget(w)
        self._crit_layout.addStretch()

        # Log
        self._clear_layout(self._log_layout)
        logs = data.get("operation_log", [])
        if not logs:
            ph = QLabel(tr("No operations yet."))
            ph.setProperty("class", "subtitle")
            self._log_layout.addWidget(ph)
        for entry in reversed(logs[-15:]):
            row = QHBoxLayout()
            ts = QLabel(entry.get("timestamp", "")[:16])
            ts.setProperty("class", "caption")
            ts.setFixedWidth(160)
            row.addWidget(ts)
            op = QLabel(entry.get("operation", "").upper())
            op.setProperty("class", "caption")
            op.setFixedWidth(120)
            row.addWidget(op)
            msg = QLabel(entry.get("message", "")[:90])
            msg.setProperty("class", "subtitle")
            row.addWidget(msg, 1)
            w = QWidget(); w.setLayout(row)
            self._log_layout.addWidget(w)
        self._log_layout.addStretch()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    # ── Exports ───────────────────────────────

    def _export_csv(self):
        if not self._controller or not self._controller.current_analysis:
            QMessageBox.warning(self, tr("Warning"), tr("No analysis available."))
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Export CSV"),
                                              "riskpulse_metrics.csv", "CSV (*.csv)")
        if not path:
            return
        data = self._controller.get_dashboard_data()
        rows = [["Metric", "Value"]]
        for key in ["nb_entities", "nb_relations", "graph_density",
                    "model_a_anomalies", "model_b_anomalies",
                    "agreement_rate", "processing_time"]:
            rows.append([key, data.get(key, 0)])
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
        QMessageBox.information(self, tr("Export complete"), path)

    def _export_json(self):
        if not self._controller:
            return
        path = self._controller.export_analysis_json()
        if path:
            QMessageBox.information(self, tr("Export complete"), path)

    def _export_pdf(self):
        if not self._controller or not self._controller.current_analysis:
            QMessageBox.warning(self, tr("Warning"), tr("No analysis available."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Export PDF"),
            f"riskpulse_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
        except ImportError:
            QMessageBox.warning(self, "ReportLab",
                                tr("Install reportlab: pip install reportlab"))
            return

        data = self._controller.get_dashboard_data()
        c = rl_canvas.Canvas(path, pagesize=A4)
        W, H = A4
        c.setFillColorRGB(0.05, 0.05, 0.06)
        c.rect(0, H - 3 * cm, W, 3 * cm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(2 * cm, H - 1.6 * cm, "RISKPULSE")
        c.setFont("Helvetica", 11)
        c.drawString(2 * cm, H - 2.3 * cm,
                     f"Analysis Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        c.setFillColorRGB(0, 0, 0)

        y = H - 4 * cm
        c.setFont("Helvetica-Bold", 13)
        c.drawString(2 * cm, y, "KEY METRICS")
        y -= 0.7 * cm
        c.setFont("Helvetica", 10)
        for label, key, fmt in [
            ("Entities", "nb_entities", "{}"),
            ("Relations", "nb_relations", "{}"),
            ("Density", "graph_density", "{:.4f}"),
            ("Anomalies A", "model_a_anomalies", "{}"),
            ("Anomalies B", "model_b_anomalies", "{}"),
            ("Agreement", "agreement_rate", "{:.1%}"),
            ("Processing time", "processing_time", "{:.3f}s"),
        ]:
            val = data.get(key, 0)
            try:
                txt = fmt.format(val)
            except Exception:
                txt = str(val)
            c.drawString(2.3 * cm, y, f"{label}  :  {txt}")
            y -= 0.5 * cm

        critical = data.get("critical_nodes", [])
        if critical:
            y -= 0.4 * cm
            c.setFont("Helvetica-Bold", 13)
            c.drawString(2 * cm, y, "TOP CRITICAL NODES")
            y -= 0.6 * cm
            c.setFont("Helvetica", 10)
            for i, n in enumerate(critical[:5], 1):
                c.drawString(2.3 * cm, y,
                             f"{i}. {n['name'][:40]}  —  score {n['composite']:.3f}")
                y -= 0.5 * cm

        c.setFont("Helvetica-Oblique", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(2 * cm, 1.5 * cm,
                     "RiskPulse v1.0 — AI risk mapping and propagation")
        c.save()
        QMessageBox.information(self, tr("Export complete"), path)

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        if not self._controller:
            return
        data = self._controller.get_dashboard_data()
        if "error" not in data:
            self._render(data)

    def on_show(self):
        self.on_analysis_updated()

    def retranslate(self):
        self._caption_lbl.setText(tr("OVERVIEW"))
        self._title_lbl.setText(tr("Dashboard"))
        self._btn_pdf.setText(tr("Export PDF"))
        self._btn_csv.setText(tr("Export CSV"))
        self._btn_json.setText(tr("Export JSON"))
        self._comp_card.set_title(tr("Model Comparison"))
        self._crit_card.set_title(tr("Top Critical Nodes"))
        self._log_card.set_title(tr("Operation Log"))
        labels = {
            "nb_entities": "Entities", "nb_relations": "Relations",
            "model_a_anomalies": "Anomalies A", "model_b_anomalies": "Anomalies B",
            "processing_time": "Time (s)", "graph_density": "Density",
        }
        for key, lbl in labels.items():
            self._metrics[key].set_label(tr(lbl))
