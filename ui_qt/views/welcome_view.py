"""
Welcome view — premier ecran de l'application.
=================================================
Met en valeur la proposition de valeur, guide l'utilisateur vers l'action.
Inspire Linear / Vercel / Raycast.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout,
)

from ..components import Card
from ..i18n import tr


class WelcomeView(QWidget):
    """Page d'accueil — montree quand aucune analyse n'a encore ete faite."""

    # Signaux pour declencher des actions depuis la MainWindow
    start_analysis = Signal()
    start_demo     = Signal()
    open_recent    = Signal(str)

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(60, 60, 60, 60)
        outer.setSpacing(0)
        outer.setAlignment(Qt.AlignTop)

        # ── Section heros ──
        hero = QVBoxLayout()
        hero.setSpacing(12)
        hero.setAlignment(Qt.AlignLeft)

        self._eyebrow = QLabel(tr("WELCOME"))
        self._eyebrow.setProperty("class", "caption")
        hero.addWidget(self._eyebrow)

        self._title = QLabel(tr("Map risks. Simulate propagation. Decide with clarity."))
        self._title.setProperty("class", "h1")
        self._title.setWordWrap(True)
        self._title.setStyleSheet("font-size: 28px; line-height: 1.3;")
        self._title.setMaximumWidth(720)
        hero.addWidget(self._title)

        self._subtitle = QLabel(tr(
            "RiskPulse extracts entities and relations from any text, "
            "builds a knowledge graph, and reveals systemic risks through "
            "AI-powered propagation and what-if simulations."
        ))
        self._subtitle.setProperty("class", "subtitle")
        self._subtitle.setWordWrap(True)
        self._subtitle.setMaximumWidth(680)
        self._subtitle.setStyleSheet("font-size: 12px; line-height: 1.6;")
        hero.addWidget(self._subtitle)

        # CTAs
        cta_row = QHBoxLayout()
        cta_row.setSpacing(10)
        cta_row.setContentsMargins(0, 18, 0, 0)

        self._btn_analyse = QPushButton(tr("New analysis  →"))
        self._btn_analyse.setProperty("variant", "primary")
        self._btn_analyse.setMinimumHeight(42)
        self._btn_analyse.setMinimumWidth(180)
        self._btn_analyse.clicked.connect(self.start_analysis.emit)
        cta_row.addWidget(self._btn_analyse)

        self._btn_demo = QPushButton(tr("Try a demo scenario"))
        self._btn_demo.setMinimumHeight(42)
        self._btn_demo.setMinimumWidth(180)
        self._btn_demo.clicked.connect(self.start_demo.emit)
        cta_row.addWidget(self._btn_demo)

        cta_row.addStretch()
        hero.addLayout(cta_row)

        outer.addLayout(hero)
        outer.addSpacing(48)

        # ── Section "capabilities" ──
        self._caps_section_lbl = QLabel(tr("CAPABILITIES"))
        self._caps_section_lbl.setProperty("class", "caption")
        outer.addWidget(self._caps_section_lbl)
        outer.addSpacing(12)

        caps_grid = QGridLayout()
        caps_grid.setSpacing(16)

        # Cles source (en anglais) -> on stocke pour pouvoir retranslate
        self._capabilities_src = [
            ("01", "Knowledge graph extraction",
             "Entities and relations detected from raw text via NLP."),
            ("02", "Risk propagation",
             "SIR-adapted simulation across weighted graphs."),
            ("03", "Hidden critical nodes",
             "PageRank + Betweenness + Closeness composite scoring."),
            ("04", "Model comparison",
             "IsolationForest vs GraphBased anomaly detection."),
            ("05", "What-if simulations",
             "Add or remove links and measure the counterfactual impact."),
            ("06", "Multilingual translation",
             "Five languages with persistent translation history."),
        ]
        self._cap_widgets: list[tuple[QLabel, QLabel]] = []
        for i, (num, name_src, desc_src) in enumerate(self._capabilities_src):
            cap_card, name_lbl, desc_lbl = self._build_capability_card(
                num, tr(name_src), tr(desc_src)
            )
            caps_grid.addWidget(cap_card, i // 3, i % 3)
            self._cap_widgets.append((name_lbl, desc_lbl))

        outer.addLayout(caps_grid)
        outer.addStretch(1)

        # ── Footer ──
        sep = QFrame()
        sep.setObjectName("divider")
        sep.setFixedHeight(1)
        outer.addWidget(sep)
        outer.addSpacing(12)

        foot_row = QHBoxLayout()
        self._hint_lbl = QLabel(tr("TIP — Press") + "  Ctrl+K  " + tr("to open the command palette"))
        self._hint_lbl.setProperty("class", "caption")
        foot_row.addWidget(self._hint_lbl)
        foot_row.addStretch()
        self._version_lbl = QLabel("RISKPULSE  ·  V1.0.0")
        self._version_lbl.setProperty("class", "caption")
        foot_row.addWidget(self._version_lbl)
        outer.addLayout(foot_row)

    def _build_capability_card(self, num: str, name: str, desc: str):
        """Retourne (frame, name_label, desc_label) pour permettre la retranslation."""
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)

        top = QHBoxLayout()
        num_lbl = QLabel(num)
        num_lbl.setProperty("class", "caption")
        num_lbl.setStyleSheet("letter-spacing: 1.5px;")
        top.addWidget(num_lbl)
        top.addStretch()
        arrow = QLabel("→")
        arrow.setProperty("class", "caption")
        top.addWidget(arrow)
        lay.addLayout(top)

        name_lbl = QLabel(name)
        name_lbl.setProperty("class", "h3")
        name_lbl.setWordWrap(True)
        lay.addWidget(name_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setProperty("class", "subtitle")
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("line-height: 1.5;")
        lay.addWidget(desc_lbl)

        lay.addStretch()
        return card, name_lbl, desc_lbl

    # ── Hooks ─────────────────────────────────

    def on_show(self):
        pass

    def on_analysis_updated(self):
        pass

    def retranslate(self):
        self._eyebrow.setText(tr("WELCOME"))
        self._title.setText(tr("Map risks. Simulate propagation. Decide with clarity."))
        self._subtitle.setText(tr(
            "RiskPulse extracts entities and relations from any text, "
            "builds a knowledge graph, and reveals systemic risks through "
            "AI-powered propagation and what-if simulations."
        ))
        self._btn_analyse.setText(tr("New analysis  →"))
        self._btn_demo.setText(tr("Try a demo scenario"))
        self._hint_lbl.setText(tr("TIP — Press") + "  Ctrl+K  " + tr("to open the command palette"))
        self._caps_section_lbl.setText(tr("CAPABILITIES"))
        # Retraduit les capability cards depuis leurs cles source
        for (name_lbl, desc_lbl), (_, name_src, desc_src) in zip(
            self._cap_widgets, self._capabilities_src
        ):
            name_lbl.setText(tr(name_src))
            desc_lbl.setText(tr(desc_src))
