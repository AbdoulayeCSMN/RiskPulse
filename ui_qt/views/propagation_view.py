"""Vue Propagation de Risque — PySide6 (premium minimaliste)."""

import threading
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QSlider, QFrame, QMessageBox,
    QScrollArea, QSizePolicy,
)

from ..components import Card, MetricCard
from ..i18n import tr
from ._base import build_header

logger = logging.getLogger(__name__)


# Etats de propagation (couleurs sourdes alignees sur la palette)
STATE_COLORS = {
    "safe":     "#84cc9e",
    "exposed":  "#e3c08e",
    "infected": "#cf9a6a",
    "critical": "#e8a0a0",
}
STATE_KEYS = {
    "safe":     "Safe",
    "exposed":  "Exposed",
    "infected": "Infected",
    "critical": "Critical",
}


class PropagationView(QWidget):

    _propagation_done  = Signal(dict)
    _propagation_error = Signal(str)

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._node_id_map: dict[str, str] = {}
        self._build()
        self._propagation_done.connect(self._render)
        self._propagation_error.connect(self._on_error)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        self._caption_lbl, self._title_lbl = build_header(
            outer, tr("MODULE"), tr("Risk Propagation")
        )

        # Corps : 2 colonnes (controls | results)
        body = QHBoxLayout()
        body.setSpacing(20)
        outer.addLayout(body, 1)

        # ─ Colonne gauche : controles ─
        controls_col = QVBoxLayout()
        controls_col.setSpacing(12)
        controls_col.setContentsMargins(0, 0, 0, 0)

        # Card : Source du risque
        self._src_card = Card(tr("Risk Source"))
        src_layout = QVBoxLayout()
        src_layout.setSpacing(8)

        self._lbl_node = QLabel(tr("Source node"))
        self._lbl_node.setProperty("class", "subtitle")
        src_layout.addWidget(self._lbl_node)

        self._node_cb = QComboBox()
        self._node_cb.setPlaceholderText(tr("Choose..."))
        src_layout.addWidget(self._node_cb)

        src_layout.addSpacing(4)
        self._lbl_intensity = QLabel(tr("Risk intensity"))
        self._lbl_intensity.setProperty("class", "subtitle")
        src_layout.addWidget(self._lbl_intensity)

        slider_row = QHBoxLayout()
        self._intensity = QSlider(Qt.Horizontal)
        self._intensity.setRange(10, 100)
        self._intensity.setValue(85)
        self._intensity.valueChanged.connect(
            lambda v: self._intensity_val.setText(f"{v/100:.2f}")
        )
        slider_row.addWidget(self._intensity, 1)
        self._intensity_val = QLabel("0.85")
        self._intensity_val.setProperty("class", "h2")
        self._intensity_val.setFixedWidth(50)
        self._intensity_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider_row.addWidget(self._intensity_val)
        src_layout.addLayout(slider_row)

        src_layout.addSpacing(8)
        self._btn_run = QPushButton(tr("Simulate Propagation"))
        self._btn_run.setProperty("variant", "primary")
        self._btn_run.setMinimumHeight(36)
        self._btn_run.clicked.connect(self._run)
        src_layout.addWidget(self._btn_run)

        self._src_card.layout().addLayout(src_layout)
        controls_col.addWidget(self._src_card)

        # Card : legende
        self._legend_card = Card(tr("State Legend"))
        legend_layout = QGridLayout()
        legend_layout.setSpacing(8)
        self._state_lbls = {}
        for row, (key, name_key) in enumerate(STATE_KEYS.items()):
            dot = QFrame()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {STATE_COLORS[key]}; border-radius: 4px;")
            legend_layout.addWidget(dot, row, 0)
            lbl = QLabel(tr(name_key))
            lbl.setProperty("class", "subtitle")
            self._state_lbls[key] = lbl
            legend_layout.addWidget(lbl, row, 1)
            legend_layout.setColumnStretch(1, 1)
        self._legend_card.layout().addLayout(legend_layout)
        controls_col.addWidget(self._legend_card)
        controls_col.addStretch()

        controls_widget = QWidget()
        controls_widget.setLayout(controls_col)
        controls_widget.setFixedWidth(340)
        body.addWidget(controls_widget)

        # ─ Colonne droite : resultats ─
        self._results_card = Card(tr("Propagation Results"))
        self._results_layout = QVBoxLayout()
        self._results_layout.setSpacing(12)

        self._placeholder = QLabel(
            tr("Run an analysis in 'Text Analysis' then simulate propagation.")
        )
        self._placeholder.setProperty("class", "subtitle")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setWordWrap(True)
        self._results_layout.addWidget(self._placeholder)

        self._results_card.layout().addLayout(self._results_layout)
        body.addWidget(self._results_card, 1)

    # ── Actions ───────────────────────────────

    def _run(self):
        if not self._controller or not self._controller.get_graph():
            QMessageBox.warning(self, tr("Warning"),
                                tr("Run a text analysis first."))
            return
        label = self._node_cb.currentText()
        node_id = self._node_id_map.get(label)
        if not node_id:
            QMessageBox.warning(self, tr("Missing node"),
                                tr("Select a source node."))
            return
        intensity = self._intensity.value() / 100
        self._app.set_status(tr("Simulating propagation..."), "info", 0.5)
        self._btn_run.setEnabled(False)
        self._btn_run.setText(tr("Running..."))

        def _job():
            try:
                result = self._controller.run_propagation(node_id, intensity)
                self._propagation_done.emit(result)
            except Exception as e:
                logger.exception("Propagation failed")
                self._propagation_error.emit(str(e))

        threading.Thread(target=_job, daemon=True).start()

    def _on_error(self, msg: str):
        self._btn_run.setEnabled(True)
        self._btn_run.setText(tr("Simulate Propagation"))
        QMessageBox.critical(self, tr("Error"), msg)

    def _render(self, result: dict):
        self._btn_run.setEnabled(True)
        self._btn_run.setText(tr("Simulate Propagation"))

        if "error" in result:
            QMessageBox.critical(self, tr("Error"), result["error"])
            return

        # Vide le layout
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._app.set_status(
            f"{tr('Propagation done')}: {result.get('n_steps', 0)} {tr('steps')}",
            "success", 1.0
        )

        # Resume par etat (MetricCards)
        summary = result.get("summary", {})
        row = QHBoxLayout()
        row.setSpacing(8)
        for state in ["critical", "infected", "exposed", "safe"]:
            count = summary.get(state, 0)
            mc = MetricCard(label=tr(STATE_KEYS[state]), value=str(count))
            mc.setMinimumHeight(82)
            # Tinte legere via le label
            row.addWidget(mc)
        row_w = QWidget()
        row_w.setLayout(row)
        self._results_layout.addWidget(row_w)

        # Liste des nœuds (top 10 par risque)
        from engines.propagation_engine import risk_to_state
        risks = result.get("final_risk", {})
        names = result.get("node_names", {})
        sorted_risks = sorted(risks.items(), key=lambda x: x[1], reverse=True)[:10]

        section_lbl = QLabel(tr("RISK LEVEL BY ENTITY (TOP 10)"))
        section_lbl.setProperty("class", "caption")
        section_lbl.setContentsMargins(0, 12, 0, 4)
        self._results_layout.addWidget(section_lbl)

        for nid, risk in sorted_risks:
            state = risk_to_state(risk).value
            color = STATE_COLORS.get(state, "#9ca3af")
            name = names.get(nid, nid).replace("_", " ").title()

            line = QWidget()
            ll = QHBoxLayout(line)
            ll.setContentsMargins(0, 4, 0, 4)
            ll.setSpacing(12)

            name_lbl = QLabel(name[:30])
            name_lbl.setFixedWidth(180)
            ll.addWidget(name_lbl)

            # Barre de progression custom
            bar_bg = QFrame()
            bar_bg.setFixedHeight(4)
            bar_bg.setStyleSheet("background-color: #1c1c20; border-radius: 2px;")
            bar_layout = QHBoxLayout(bar_bg)
            bar_layout.setContentsMargins(0, 0, 0, 0)
            bar_fg = QFrame()
            bar_fg.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
            bar_layout.addWidget(bar_fg)
            bar_layout.addStretch(int((1 - risk) * 100))
            bar_layout.setStretch(0, int(risk * 100))
            ll.addWidget(bar_bg, 1)

            risk_lbl = QLabel(f"{risk:.2f}")
            risk_lbl.setStyleSheet(f"color: {color};")
            risk_lbl.setFixedWidth(40)
            risk_lbl.setAlignment(Qt.AlignRight)
            ll.addWidget(risk_lbl)

            self._results_layout.addWidget(line)

        self._results_layout.addStretch()

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        if not self._controller:
            return
        nodes = self._controller.get_node_list()
        self._node_id_map = {n["label"]: n["id"] for n in nodes}
        self._node_cb.clear()
        self._node_cb.addItems([n["label"] for n in nodes])

    def on_show(self):
        if self._controller and self._controller.get_graph():
            self.on_analysis_updated()

    def retranslate(self):
        self._caption_lbl.setText(tr("MODULE"))
        self._title_lbl.setText(tr("Risk Propagation"))
        self._src_card.set_title(tr("Risk Source"))
        self._lbl_node.setText(tr("Source node"))
        self._lbl_intensity.setText(tr("Risk intensity"))
        self._btn_run.setText(tr("Simulate Propagation"))
        self._legend_card.set_title(tr("State Legend"))
        for k, lbl in self._state_lbls.items():
            lbl.setText(tr(STATE_KEYS[k]))
        self._results_card.set_title(tr("Propagation Results"))
