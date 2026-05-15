"""Vue Simulations What-If (contrefactuel) — PySide6."""

import threading
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QSlider, QPushButton, QMessageBox,
)

from ..components import Card, MetricCard
from ..i18n import tr
from ._base import build_header


class ContrefactuelView(QWidget):

    _counterfactual_done  = Signal(dict)
    _counterfactual_error = Signal(str)

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._node_id_map: dict = {}
        self._edge_id_map: dict = {}
        self._build()
        self._counterfactual_done.connect(self._render)
        self._counterfactual_error.connect(self._on_error)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        self._caption_lbl, self._title_lbl = build_header(
            outer, tr("MODULE"), tr("What-If Simulations")
        )

        self._subtitle = QLabel(tr("Remove or add a link in the graph and compare propagation before / after."))
        self._subtitle.setProperty("class", "subtitle")
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        body = QHBoxLayout()
        body.setSpacing(20)
        outer.addLayout(body, 1)

        # ─ Colonne controles ─
        controls_col = QVBoxLayout()
        controls_col.setSpacing(12)

        # Source du risque
        self._src_card = Card(tr("Risk Source"))
        src_l = QVBoxLayout()
        src_l.setSpacing(8)
        self._lbl_node = QLabel(tr("Source node"))
        self._lbl_node.setProperty("class", "subtitle")
        src_l.addWidget(self._lbl_node)
        self._source_cb = QComboBox()
        src_l.addWidget(self._source_cb)
        self._lbl_intensity = QLabel(tr("Intensity"))
        self._lbl_intensity.setProperty("class", "subtitle")
        src_l.addWidget(self._lbl_intensity)
        irow = QHBoxLayout()
        self._intensity = QSlider(Qt.Horizontal)
        self._intensity.setRange(10, 100)
        self._intensity.setValue(85)
        self._intensity.valueChanged.connect(
            lambda v: self._int_lbl.setText(f"{v/100:.2f}")
        )
        irow.addWidget(self._intensity, 1)
        self._int_lbl = QLabel("0.85")
        self._int_lbl.setProperty("class", "h2")
        self._int_lbl.setFixedWidth(50)
        self._int_lbl.setAlignment(Qt.AlignRight)
        irow.addWidget(self._int_lbl)
        src_l.addLayout(irow)
        self._src_card.layout().addLayout(src_l)
        controls_col.addWidget(self._src_card)

        # Supprimer un lien
        self._rm_card = Card(tr("Remove an existing link"))
        rm_l = QVBoxLayout()
        rm_l.setSpacing(8)
        self._lbl_edge = QLabel(tr("Link to remove"))
        self._lbl_edge.setProperty("class", "subtitle")
        rm_l.addWidget(self._lbl_edge)
        self._edge_cb = QComboBox()
        rm_l.addWidget(self._edge_cb)
        self._btn_rm = QPushButton(tr("Simulate removal"))
        self._btn_rm.setProperty("variant", "danger")
        self._btn_rm.setMinimumHeight(34)
        self._btn_rm.clicked.connect(self._run_remove)
        rm_l.addWidget(self._btn_rm)
        self._rm_card.layout().addLayout(rm_l)
        controls_col.addWidget(self._rm_card)

        # Ajouter un lien
        self._add_card = Card(tr("Add a new link"))
        add_l = QVBoxLayout()
        add_l.setSpacing(8)
        self._lbl_nodea = QLabel(tr("Node A"))
        self._lbl_nodea.setProperty("class", "subtitle")
        add_l.addWidget(self._lbl_nodea)
        self._add_u_cb = QComboBox()
        add_l.addWidget(self._add_u_cb)
        self._lbl_nodeb = QLabel(tr("Node B"))
        self._lbl_nodeb.setProperty("class", "subtitle")
        add_l.addWidget(self._lbl_nodeb)
        self._add_v_cb = QComboBox()
        add_l.addWidget(self._add_v_cb)
        self._lbl_weight = QLabel(tr("New link weight"))
        self._lbl_weight.setProperty("class", "subtitle")
        add_l.addWidget(self._lbl_weight)
        wrow = QHBoxLayout()
        self._weight = QSlider(Qt.Horizontal)
        self._weight.setRange(10, 100)
        self._weight.setValue(50)
        self._weight.valueChanged.connect(
            lambda v: self._w_lbl.setText(f"{v/100:.2f}")
        )
        wrow.addWidget(self._weight, 1)
        self._w_lbl = QLabel("0.50")
        self._w_lbl.setProperty("class", "h2")
        self._w_lbl.setFixedWidth(50)
        self._w_lbl.setAlignment(Qt.AlignRight)
        wrow.addWidget(self._w_lbl)
        add_l.addLayout(wrow)
        self._btn_add = QPushButton(tr("Simulate addition"))
        self._btn_add.setProperty("variant", "success")
        self._btn_add.setMinimumHeight(34)
        self._btn_add.clicked.connect(self._run_add)
        add_l.addWidget(self._btn_add)
        self._add_card.layout().addLayout(add_l)
        controls_col.addWidget(self._add_card)
        controls_col.addStretch()

        cw = QWidget()
        cw.setLayout(controls_col)
        cw.setFixedWidth(340)
        body.addWidget(cw)

        # ─ Resultats ─
        rcol = QVBoxLayout()
        rcol.setSpacing(12)
        self._results_card = Card(tr("Before / After Comparison"))
        self._results_layout = QVBoxLayout()
        self._results_layout.setSpacing(12)
        self._placeholder = QLabel(tr("Select a source node and a link,\nthen launch a simulation."))
        self._placeholder.setProperty("class", "subtitle")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setWordWrap(True)
        self._results_layout.addWidget(self._placeholder)
        self._results_card.layout().addLayout(self._results_layout)
        rcol.addWidget(self._results_card, 1)

        self._interp_card = Card(tr("Interpretation"))
        self._interp_lbl = QLabel("—")
        self._interp_lbl.setProperty("class", "subtitle")
        self._interp_lbl.setWordWrap(True)
        self._interp_card.layout().addWidget(self._interp_lbl)
        rcol.addWidget(self._interp_card)

        rw = QWidget()
        rw.setLayout(rcol)
        body.addWidget(rw, 1)

    # ── Actions ───────────────────────────────

    def _validate(self) -> tuple[bool, str | None]:
        if not self._controller or not self._controller.get_graph():
            QMessageBox.warning(self, tr("Warning"), tr("Run a text analysis first."))
            return False, None
        source = self._node_id_map.get(self._source_cb.currentText())
        if not source:
            QMessageBox.warning(self, tr("Missing node"), tr("Select a source node."))
            return False, None
        return True, source

    def _run_remove(self):
        ok, source = self._validate()
        if not ok:
            return
        edge = self._edge_id_map.get(self._edge_cb.currentText())
        if not edge:
            QMessageBox.warning(self, tr("Missing link"), tr("Select a link to remove."))
            return
        intensity = self._intensity.value() / 100
        self._app.set_status(tr("Simulating removal..."), "info", 0.5)
        self._btn_rm.setEnabled(False)

        def _job():
            try:
                r = self._controller.run_counterfactual_remove(source, intensity, *edge)
                self._counterfactual_done.emit(r)
            except Exception as e:
                self._counterfactual_error.emit(str(e))
        threading.Thread(target=_job, daemon=True).start()

    def _run_add(self):
        ok, source = self._validate()
        if not ok:
            return
        u = self._node_id_map.get(self._add_u_cb.currentText())
        v = self._node_id_map.get(self._add_v_cb.currentText())
        if not u or not v:
            QMessageBox.warning(self, tr("Missing nodes"), tr("Select both endpoints."))
            return
        if u == v:
            QMessageBox.warning(self, tr("Error"), tr("Endpoints must differ."))
            return
        intensity = self._intensity.value() / 100
        weight = self._weight.value() / 100
        self._app.set_status(tr("Simulating addition..."), "info", 0.5)
        self._btn_add.setEnabled(False)

        def _job():
            try:
                r = self._controller.run_counterfactual_add(source, intensity, u, v, weight)
                self._counterfactual_done.emit(r)
            except Exception as e:
                self._counterfactual_error.emit(str(e))
        threading.Thread(target=_job, daemon=True).start()

    def _on_error(self, msg: str):
        self._btn_rm.setEnabled(True)
        self._btn_add.setEnabled(True)
        QMessageBox.critical(self, tr("Error"), msg)

    def _render(self, result: dict):
        self._btn_rm.setEnabled(True)
        self._btn_add.setEnabled(True)

        if "error" in result:
            QMessageBox.critical(self, tr("Error"), result["error"])
            return

        # Vide
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        impact = result.get("impact", {})
        action = result.get("action", "")
        avg_before = impact.get("avg_risk_before", 0)
        avg_after  = impact.get("avg_risk_after", 0)
        delta      = impact.get("avg_risk_delta", 0)
        improved   = len(impact.get("improved_nodes", []))
        worsened   = len(impact.get("worsened_nodes", []))

        action_lbl = QLabel(action)
        action_lbl.setProperty("class", "h3")
        self._results_layout.addWidget(action_lbl)

        row = QHBoxLayout()
        row.setSpacing(8)
        cards_data = [
            ("Risk Before",  f"{avg_before:.3f}"),
            ("Risk After",   f"{avg_after:.3f}"),
            ("Delta",        f"{delta:+.3f}"),
            ("Improved",     str(improved)),
            ("Worsened",     str(worsened)),
        ]
        for lbl, val in cards_data:
            mc = MetricCard(label=tr(lbl), value=val)
            mc.setMinimumHeight(82)
            row.addWidget(mc)
        row_w = QWidget()
        row_w.setLayout(row)
        self._results_layout.addWidget(row_w)

        self._results_layout.addStretch()

        # Interpretation
        interp = result.get("interpretation", "")
        self._interp_lbl.setText(interp or "—")
        self._app.set_status(tr("Counterfactual simulation done"), "success", 1.0)

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        if not self._controller:
            return
        nodes = self._controller.get_node_list()
        self._node_id_map = {n["label"]: n["id"] for n in nodes}
        labels = [n["label"] for n in nodes]
        for cb in (self._source_cb, self._add_u_cb, self._add_v_cb):
            cb.clear()
            cb.addItems(labels)
        edges = self._controller.get_edge_list()
        self._edge_id_map = {e["label"]: (e["u"], e["v"]) for e in edges}
        self._edge_cb.clear()
        self._edge_cb.addItems([e["label"] for e in edges])

    def on_show(self):
        if self._controller and self._controller.get_graph():
            self.on_analysis_updated()

    def retranslate(self):
        self._caption_lbl.setText(tr("MODULE"))
        self._title_lbl.setText(tr("What-If Simulations"))
        self._subtitle.setText(tr("Remove or add a link in the graph and compare propagation before / after."))
        self._src_card.set_title(tr("Risk Source"))
        self._rm_card.set_title(tr("Remove an existing link"))
        self._add_card.set_title(tr("Add a new link"))
        self._lbl_node.setText(tr("Source node"))
        self._lbl_intensity.setText(tr("Intensity"))
        self._lbl_edge.setText(tr("Link to remove"))
        self._lbl_nodea.setText(tr("Node A"))
        self._lbl_nodeb.setText(tr("Node B"))
        self._lbl_weight.setText(tr("New link weight"))
        self._btn_rm.setText(tr("Simulate removal"))
        self._btn_add.setText(tr("Simulate addition"))
        self._results_card.set_title(tr("Before / After Comparison"))
        self._interp_card.set_title(tr("Interpretation"))
        self._placeholder.setText(tr("Select a source node and a link,\nthen launch a simulation."))
