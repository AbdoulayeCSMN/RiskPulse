"""Vue Parametres — PySide6."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QSlider, QSpinBox, QDoubleSpinBox, QComboBox,
    QRadioButton, QButtonGroup, QFrame, QMessageBox,
)

from ..components import Card
from ..i18n import tr, SUPPORTED_LANGUAGES, I18nManager
from ..theme import ThemeManager
from ._base import build_header


DEFAULTS = {
    "contamination":         0.10,
    "n_estimators":          100,
    "top_n_critical":        5,
    "decay":                 0.30,
    "max_steps":             50,
    "propagation_speed":     1.0,
    "convergence_threshold": 0.001,
}


class ParametresView(QWidget):

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._vars: dict = {}
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        self._caption_lbl, self._title_lbl = build_header(
            outer, tr("CONFIGURATION"), tr("Settings")
        )

        # 2 colonnes
        grid = QGridLayout()
        grid.setSpacing(20)

        # Card Modele A
        self._card_a = Card(tr("Model A — IsolationForest"))
        la = QVBoxLayout()
        la.setSpacing(12)
        self._add_slider(la, "contamination", tr("Contamination rate"),
                         tr("Estimated proportion of anomalies in data."),
                         0.01, 0.5, 0.01, DEFAULTS["contamination"], pct=False, dec=2)
        self._add_spin(la, "n_estimators", tr("Number of trees"),
                       tr("More trees = more accurate but slower."),
                       10, 500, 10, DEFAULTS["n_estimators"])
        self._add_spin(la, "top_n_critical", tr("Top N critical nodes"),
                       tr("How many critical nodes to display."),
                       3, 20, 1, DEFAULTS["top_n_critical"])
        self._card_a.layout().addLayout(la)
        grid.addWidget(self._card_a, 0, 0)

        # Card Propagation
        self._card_p = Card(tr("Propagation Engine"))
        lp = QVBoxLayout()
        lp.setSpacing(12)
        self._add_slider(lp, "decay", tr("Decay coefficient"),
                         tr("Risk attenuation per hop in the network."),
                         0.0, 0.9, 0.05, DEFAULTS["decay"], dec=2)
        self._add_spin(lp, "max_steps", tr("Max steps"),
                       tr("Simulation stops after this many iterations."),
                       5, 200, 5, DEFAULTS["max_steps"])
        self._add_slider(lp, "propagation_speed", tr("Propagation speed"),
                         tr("Speed multiplier for the simulation."),
                         0.1, 3.0, 0.1, DEFAULTS["propagation_speed"], dec=1, suffix="x")
        self._card_p.layout().addLayout(lp)
        grid.addWidget(self._card_p, 0, 1)

        # Card Interface
        self._card_i = Card(tr("Interface"))
        li = QVBoxLayout()
        li.setSpacing(12)

        # Theme
        theme_lbl = QLabel(tr("Theme"))
        theme_lbl.setProperty("class", "subtitle")
        li.addWidget(theme_lbl)
        theme_row = QHBoxLayout()
        self._theme_group = QButtonGroup(self)
        for tid, label in [("dark", tr("Dark")), ("light", tr("Light"))]:
            rb = QRadioButton(label)
            if tid == ThemeManager.instance().name:
                rb.setChecked(True)
            rb.toggled.connect(lambda checked, t=tid: checked and self._preview_theme(t))
            self._theme_group.addButton(rb)
            theme_row.addWidget(rb)
        theme_row.addStretch()
        li.addLayout(theme_row)

        # Langue
        lang_lbl = QLabel(tr("Language"))
        lang_lbl.setProperty("class", "subtitle")
        lang_lbl.setContentsMargins(0, 8, 0, 0)
        li.addWidget(lang_lbl)

        self._lang_cb = QComboBox()
        for code, name in SUPPORTED_LANGUAGES.items():
            self._lang_cb.addItem(name, userData=code)
        idx = self._lang_cb.findData(I18nManager.instance().current)
        if idx >= 0:
            self._lang_cb.setCurrentIndex(idx)
        self._lang_cb.currentIndexChanged.connect(self._on_lang_change)
        li.addWidget(self._lang_cb)
        li.addStretch()

        self._card_i.layout().addLayout(li)
        grid.addWidget(self._card_i, 1, 0)

        # Card Analyse
        self._card_an = Card(tr("Analysis"))
        lan = QVBoxLayout()
        lan.setSpacing(12)
        self._add_slider(lan, "convergence_threshold", tr("Convergence threshold"),
                         tr("Minimum delta to stop propagation."),
                         0.0001, 0.01, 0.0001, DEFAULTS["convergence_threshold"], dec=4)
        info = QLabel(tr("Model B (GraphBased) has no external parameters — scoring is derived from graph topology."))
        info.setProperty("class", "caption")
        info.setWordWrap(True)
        info.setContentsMargins(0, 8, 0, 0)
        lan.addWidget(info)
        lan.addStretch()
        self._card_an.layout().addLayout(lan)
        grid.addWidget(self._card_an, 1, 1)

        outer.addLayout(grid)

        # Actions
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._btn_apply = QPushButton(tr("Apply settings"))
        self._btn_apply.setProperty("variant", "primary")
        self._btn_apply.setMinimumHeight(36)
        self._btn_apply.clicked.connect(self._apply)
        actions.addWidget(self._btn_apply)
        self._btn_reset = QPushButton(tr("Reset to defaults"))
        self._btn_reset.clicked.connect(self._reset)
        actions.addWidget(self._btn_reset)
        actions.addStretch()
        self._applied_lbl = QLabel("")
        self._applied_lbl.setProperty("class", "subtitle")
        self._applied_lbl.setStyleSheet("color: #84cc9e;")
        actions.addWidget(self._applied_lbl)
        outer.addLayout(actions)
        outer.addStretch()

    # ── Helpers de construction ─────────────

    def _add_slider(self, parent_layout, key, label, desc, mn, mx, step, default,
                    pct=False, dec=2, suffix=""):
        lbl = QLabel(label)
        lbl.setProperty("class", "subtitle")
        parent_layout.addWidget(lbl)
        if desc:
            d = QLabel(desc)
            d.setProperty("class", "caption")
            d.setWordWrap(True)
            parent_layout.addWidget(d)

        # On utilise QDoubleSpinBox a la place du QSlider pour la precision
        spin = QDoubleSpinBox()
        spin.setRange(mn, mx)
        spin.setSingleStep(step)
        spin.setDecimals(dec)
        spin.setValue(default)
        spin.setSuffix(suffix)
        spin.setMinimumHeight(28)
        parent_layout.addWidget(spin)
        self._vars[key] = spin

    def _add_spin(self, parent_layout, key, label, desc, mn, mx, step, default):
        lbl = QLabel(label)
        lbl.setProperty("class", "subtitle")
        parent_layout.addWidget(lbl)
        if desc:
            d = QLabel(desc)
            d.setProperty("class", "caption")
            d.setWordWrap(True)
            parent_layout.addWidget(d)
        spin = QSpinBox()
        spin.setRange(mn, mx)
        spin.setSingleStep(step)
        spin.setValue(default)
        spin.setMinimumHeight(28)
        parent_layout.addWidget(spin)
        self._vars[key] = spin

    # ── Actions ─────────────────────────────

    def _preview_theme(self, theme_id: str):
        ThemeManager.instance().set_theme(theme_id)

    def _on_lang_change(self, idx):
        code = self._lang_cb.itemData(idx)
        if code:
            I18nManager.instance().set_language(code)

    def _apply(self):
        if not self._controller:
            return
        params = {}
        for key, w in self._vars.items():
            if isinstance(w, QDoubleSpinBox):
                params[key] = float(w.value())
            elif isinstance(w, QSpinBox):
                params[key] = int(w.value())
        try:
            self._controller.set_model_params(params)
            self._applied_lbl.setText(tr("Settings applied"))
            self._app.set_status(tr("AI settings updated"), "success", 1.0)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self._applied_lbl.setText(""))
        except Exception as e:
            QMessageBox.critical(self, tr("Error"), str(e))

    def _reset(self):
        ans = QMessageBox.question(
            self, tr("Reset"), tr("Reset all settings to defaults?")
        )
        if ans != QMessageBox.Yes:
            return
        for key, val in DEFAULTS.items():
            if key in self._vars:
                self._vars[key].setValue(val)
        self._applied_lbl.setText(tr("Defaults restored"))

    # ── Hooks ───────────────────────────────

    def on_analysis_updated(self):
        pass

    def on_show(self):
        pass

    def retranslate(self):
        self._caption_lbl.setText(tr("CONFIGURATION"))
        self._title_lbl.setText(tr("Settings"))
        self._card_a.set_title(tr("Model A — IsolationForest"))
        self._card_p.set_title(tr("Propagation Engine"))
        self._card_i.set_title(tr("Interface"))
        self._card_an.set_title(tr("Analysis"))
        self._btn_apply.setText(tr("Apply settings"))
        self._btn_reset.setText(tr("Reset to defaults"))
