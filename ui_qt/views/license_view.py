"""
License view : etat de la licence, activation, gestion plan.
"""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout,
)

from ..components import Card, ActivationDialog
from ..i18n import tr
from ._base import build_header
from services.licensing import get_license_manager, Plan, FEATURE_MIN_PLAN


class LicenseView(QWidget):

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

        self.cap, self.title = build_header(root, tr("LICENSE"), tr("License & Plan"))

        # Carte etat
        self.state_card = Card()
        scl = QVBoxLayout(self.state_card)
        scl.setContentsMargins(20, 18, 20, 18)
        scl.setSpacing(10)

        self.plan_lbl = QLabel("")
        self.plan_lbl.setProperty("class", "h2")
        scl.addWidget(self.plan_lbl)

        self.detail_lbl = QLabel("")
        self.detail_lbl.setProperty("class", "caption")
        self.detail_lbl.setWordWrap(True)
        scl.addWidget(self.detail_lbl)

        # Boutons
        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.activate_btn = QPushButton(tr("Activate a license key"))
        self.activate_btn.setProperty("class", "primary")
        self.activate_btn.clicked.connect(self._open_activation)
        btns.addWidget(self.activate_btn)

        self.deactivate_btn = QPushButton(tr("Remove license"))
        self.deactivate_btn.clicked.connect(self._on_deactivate)
        btns.addWidget(self.deactivate_btn)

        btns.addStretch()
        scl.addLayout(btns)
        root.addWidget(self.state_card)

        # Carte features
        self.features_card = Card()
        fcl = QVBoxLayout(self.features_card)
        fcl.setContentsMargins(20, 18, 20, 18)
        fcl.setSpacing(8)
        ftitle = QLabel(tr("Feature availability"))
        ftitle.setProperty("class", "h3")
        fcl.addWidget(ftitle)

        self.features_grid = QGridLayout()
        self.features_grid.setHorizontalSpacing(20)
        self.features_grid.setVerticalSpacing(6)
        fcl.addLayout(self.features_grid)
        root.addWidget(self.features_card)

        root.addStretch()

    def _refresh(self):
        mgr = get_license_manager()
        st = mgr.state
        plan_eff = st.effective_plan()
        self.plan_lbl.setText(f"{plan_eff.value} · {mgr.status_summary()}")
        # Detail
        if st.is_trial and st.trial_active():
            self.detail_lbl.setText(tr(
                "You are using a free 14-day trial of all Enterprise features. "
                "Buy a license anytime to keep premium features after the trial ends."
            ))
        elif st.is_valid() and st.plan != Plan.FREE:
            issued = (datetime.fromtimestamp(st.issued_at, tz=timezone.utc).strftime("%Y-%m-%d")
                       if st.issued_at else "—")
            self.detail_lbl.setText(
                f"{tr('Licensed to')} : {st.email}\n"
                f"{tr('Issued')} : {issued}"
            )
        else:
            self.detail_lbl.setText(tr(
                "No active license. Core features are free; premium features "
                "require a PRO or ENTERPRISE plan."
            ))

        # Features grid
        # Clear
        while self.features_grid.count():
            it = self.features_grid.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        row = 0
        for feature, min_plan in FEATURE_MIN_PLAN.items():
            available = mgr.can_use(feature)
            name = QLabel(feature.replace("_", " "))
            status = QLabel(("✓ " if available else "✗ ") + min_plan.value)
            status.setProperty("class", "caption" if available else "caption-warn")
            self.features_grid.addWidget(name,   row, 0)
            self.features_grid.addWidget(status, row, 1, alignment=Qt.AlignRight)
            row += 1

    def _open_activation(self):
        dlg = ActivationDialog(parent=self)
        if dlg.exec():
            self._refresh()
            if self.app and hasattr(self.app, "toast"):
                self.app.toast(tr("License updated"), "success")

    def _on_deactivate(self):
        mgr = get_license_manager()
        mgr.deactivate()
        self._refresh()
        if self.app and hasattr(self.app, "toast"):
            self.app.toast(tr("License removed"), "info")

    def on_show(self):
        self._refresh()

    def retranslate(self):
        self.cap.setText(tr("LICENSE"))
        self.title.setText(tr("License & Plan"))
        self.activate_btn.setText(tr("Activate a license key"))
        self.deactivate_btn.setText(tr("Remove license"))
        self._refresh()
