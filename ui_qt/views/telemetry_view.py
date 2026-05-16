"""
Vue Telemetry : crashes recents, top errors, feature usage, export support.
Tout est local, jamais envoye.
"""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QMessageBox,
    QTextEdit, QSplitter,
)

from ..components import Card
from ..i18n import tr
from ._base import build_header
from services.telemetry import get_telemetry


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


class TelemetryView(QWidget):

    def __init__(self, controller=None, app=None):
        super().__init__()
        self.controller = controller
        self.app = app
        self._build()
        self._refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(16)

        self.cap, self.title = build_header(
            root, tr("DIAGNOSTICS"), tr("Telemetry & Crash Reports"),
        )

        # Opt-in card
        opt_card = Card()
        ocl = QVBoxLayout(opt_card)
        ocl.setContentsMargins(20, 18, 20, 18)
        ocl.setSpacing(8)
        self.opt_label = QLabel(tr(
            "Local diagnostics stay on this machine. Nothing is sent over "
            "the network. Enable to count feature usage and help reproduce "
            "issues."
        ))
        self.opt_label.setWordWrap(True)
        self.opt_label.setProperty("class", "caption")
        ocl.addWidget(self.opt_label)

        self.opt_chk = QCheckBox(tr("Enable local telemetry (opt-in)"))
        self.opt_chk.setChecked(get_telemetry().enabled)
        self.opt_chk.toggled.connect(self._on_toggle_opt_in)
        ocl.addWidget(self.opt_chk)

        actions = QHBoxLayout()
        self.export_btn = QPushButton(tr("Export support bundle (.zip)"))
        self.export_btn.setProperty("class", "primary")
        self.export_btn.clicked.connect(self._on_export)
        actions.addWidget(self.export_btn)

        self.clear_btn = QPushButton(tr("Clear local diagnostics"))
        self.clear_btn.clicked.connect(self._on_clear)
        actions.addWidget(self.clear_btn)
        actions.addStretch()
        ocl.addLayout(actions)
        root.addWidget(opt_card)

        # Counts
        self.counts_lbl = QLabel("")
        self.counts_lbl.setProperty("class", "caption")
        root.addWidget(self.counts_lbl)

        # Splitter : crashes (left) + selected traceback (right)
        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)

        # Crashes table
        self.crashes_table = QTableWidget(0, 4)
        self.crashes_table.setHorizontalHeaderLabels([
            tr("When"), tr("Type"), tr("Message"), tr("Thread"),
        ])
        self.crashes_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.crashes_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.crashes_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.crashes_table.itemSelectionChanged.connect(self._on_select_crash)
        split.addWidget(self.crashes_table)

        # Traceback viewer
        self.tb_view = QTextEdit()
        self.tb_view.setReadOnly(True)
        self.tb_view.setPlaceholderText(tr("Select a crash to see its traceback"))
        self.tb_view.setStyleSheet(
            "font-family: 'JetBrains Mono', Consolas, monospace; font-size: 11px;"
        )
        split.addWidget(self.tb_view)
        split.setSizes([520, 520])

        # Top errors + feature usage
        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        # Top errors
        topc = Card()
        tcl = QVBoxLayout(topc)
        tcl.setContentsMargins(16, 14, 16, 14)
        tcl.setSpacing(6)
        h1 = QLabel(tr("Top error types"))
        h1.setProperty("class", "h3")
        tcl.addWidget(h1)
        self.top_errors_table = QTableWidget(0, 3)
        self.top_errors_table.setHorizontalHeaderLabels([
            tr("Type"), tr("Count"), tr("Last"),
        ])
        self.top_errors_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.top_errors_table.setEditTriggers(QTableWidget.NoEditTriggers)
        tcl.addWidget(self.top_errors_table)
        bottom.addWidget(topc, 1)

        # Feature usage
        feat = Card()
        fcl = QVBoxLayout(feat)
        fcl.setContentsMargins(16, 14, 16, 14)
        fcl.setSpacing(6)
        h2 = QLabel(tr("Feature usage"))
        h2.setProperty("class", "h3")
        fcl.addWidget(h2)
        self.feat_table = QTableWidget(0, 2)
        self.feat_table.setHorizontalHeaderLabels([tr("Feature"), tr("Uses")])
        self.feat_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.feat_table.setEditTriggers(QTableWidget.NoEditTriggers)
        fcl.addWidget(self.feat_table)
        bottom.addWidget(feat, 1)

        root.addLayout(bottom)

    # ── Actions ─────────────────────────────────────

    def _on_toggle_opt_in(self, checked: bool):
        get_telemetry().set_enabled(checked)
        if self.app and hasattr(self.app, "toast"):
            self.app.toast(
                tr("Telemetry enabled") if checked else tr("Telemetry disabled"),
                "info",
            )

    def _on_export(self):
        try:
            path = get_telemetry().export_support_bundle()
            if self.app and hasattr(self.app, "toast"):
                self.app.toast(f"{tr('Bundle exported')}: {path.name}", "success")
            QMessageBox.information(
                self, tr("Support bundle exported"),
                f"{tr('Saved to')}:\n{path}\n\n"
                f"{tr('You can email this file to support to help diagnose issues.')}"
            )
        except Exception as exc:
            QMessageBox.warning(self, tr("Export failed"), str(exc))

    def _on_clear(self):
        ans = QMessageBox.question(
            self, tr("Clear diagnostics"),
            tr("Delete all locally stored events and crashes?"),
        )
        if ans == QMessageBox.Yes:
            get_telemetry().clear()
            self._refresh()

    def _on_select_crash(self):
        items = self.crashes_table.selectedItems()
        if not items:
            self.tb_view.clear()
            return
        row = items[0].row()
        tb = self.crashes_table.item(row, 0).data(Qt.UserRole)
        self.tb_view.setPlainText(tb or "")

    # ── Refresh ─────────────────────────────────────

    def _refresh(self):
        t = get_telemetry()
        counts = t.counts()
        self.counts_lbl.setText(
            f"{counts['events']} {tr('events')} · {counts['crashes']} {tr('crashes')}"
        )

        # Crashes table
        crashes = t.list_crashes(limit=100)
        self.crashes_table.setRowCount(len(crashes))
        for i, c in enumerate(crashes):
            ts_item = QTableWidgetItem(_fmt_ts(c["ts"]))
            # Stocke le traceback dans data(UserRole) du premier item de la ligne
            ts_item.setData(Qt.UserRole, c["traceback"])
            self.crashes_table.setItem(i, 0, ts_item)
            self.crashes_table.setItem(i, 1, QTableWidgetItem(c["exc_type"] or "?"))
            self.crashes_table.setItem(i, 2, QTableWidgetItem(
                (c["exc_value"] or "")[:120]))
            self.crashes_table.setItem(i, 3, QTableWidgetItem(c["thread_name"] or ""))

        # Top errors
        tops = t.top_errors(limit=10)
        self.top_errors_table.setRowCount(len(tops))
        for i, r in enumerate(tops):
            self.top_errors_table.setItem(i, 0, QTableWidgetItem(r["exc_type"] or "?"))
            self.top_errors_table.setItem(i, 1, QTableWidgetItem(str(r["count"])))
            self.top_errors_table.setItem(i, 2, QTableWidgetItem(
                _fmt_ts(r["last_ts"]) if r["last_ts"] else "—"))

        # Feature usage
        feats = t.feature_usage(limit=20)
        self.feat_table.setRowCount(len(feats))
        for i, r in enumerate(feats):
            self.feat_table.setItem(i, 0, QTableWidgetItem(r["feature"] or "?"))
            self.feat_table.setItem(i, 1, QTableWidgetItem(str(r["count"])))

    def on_show(self):
        self._refresh()

    def retranslate(self):
        self.cap.setText(tr("DIAGNOSTICS"))
        self.title.setText(tr("Telemetry & Crash Reports"))
        self.opt_chk.setText(tr("Enable local telemetry (opt-in)"))
        self.export_btn.setText(tr("Export support bundle (.zip)"))
        self.clear_btn.setText(tr("Clear local diagnostics"))
        self._refresh()
