"""
Vue Risk Intelligence — l'écran de **valeur métier**.

Trois sections :
  1. Risk Profiles    — chaque entité, son score, son verdict, ses drivers
  2. Crisis Matches   — similarité topologique avec crises historiques
  3. Cascade Forecast — pertes monétaires estimées par défaillance
"""

import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QSizePolicy, QPushButton,
)

from ..components import Card
from ..i18n import tr
from ._base import build_header

logger = logging.getLogger(__name__)


# Couleurs de verdict (alignées palette monochrome premium)
VERDICT_COLORS = {
    "CRITICAL": "#e8a0a0",
    "HIGH":     "#e3c08e",
    "MODERATE": "#9caec1",
    "LOW":      "#84cc9e",
    "MINIMAL":  "#52525b",
}

SEVERITY_COLORS = {
    "high": "#e8a0a0",
    "med":  "#e3c08e",
    "low":  "#52525b",
}


class IntelligenceView(QWidget):

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._build()

    # ── Construction ─────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        self._caption_lbl, self._title_lbl = build_header(
            outer, tr("INTELLIGENCE"), tr("Risk Intelligence")
        )

        self._subtitle = QLabel(tr(
            "Quantitative risk scoring, historical crisis matching, "
            "and cascade impact estimation."
        ))
        self._subtitle.setProperty("class", "subtitle")
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        # Container scrollable interne
        body = QHBoxLayout()
        body.setSpacing(20)
        outer.addLayout(body, 1)

        # ── Colonne gauche : profils ──
        self._profiles_card = Card(tr("Risk Profiles"))
        self._profiles_layout = QVBoxLayout()
        self._profiles_layout.setSpacing(6)
        self._profiles_placeholder = QLabel(tr("Run an analysis to score entities."))
        self._profiles_placeholder.setProperty("class", "subtitle")
        self._profiles_placeholder.setAlignment(Qt.AlignCenter)
        self._profiles_layout.addWidget(self._profiles_placeholder)
        self._profiles_card.layout().addLayout(self._profiles_layout)
        body.addWidget(self._profiles_card, 5)

        # ── Colonne droite : crises + cascades ──
        right = QVBoxLayout()
        right.setSpacing(12)

        self._crisis_card = Card(tr("Crisis Pattern Matching"))
        self._crisis_layout = QVBoxLayout()
        self._crisis_layout.setSpacing(8)
        ph_c = QLabel(tr("Awaiting analysis..."))
        ph_c.setProperty("class", "subtitle")
        self._crisis_layout.addWidget(ph_c)
        self._crisis_placeholder = ph_c
        self._crisis_card.layout().addLayout(self._crisis_layout)
        right.addWidget(self._crisis_card)

        self._cascade_card = Card(tr("Cascade Forecast"))
        self._cascade_layout = QVBoxLayout()
        self._cascade_layout.setSpacing(8)
        ph_k = QLabel(tr("Awaiting analysis..."))
        ph_k.setProperty("class", "subtitle")
        self._cascade_layout.addWidget(ph_k)
        self._cascade_placeholder = ph_k
        self._cascade_card.layout().addLayout(self._cascade_layout)
        right.addWidget(self._cascade_card)

        right_w = QWidget()
        right_w.setLayout(right)
        body.addWidget(right_w, 4)

    # ── Rendu ─────────────────────────────────

    def _clear(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _render(self, ri: dict):
        self._render_profiles(ri.get("profiles", []))
        self._render_crises(ri.get("crisis_matches", []))
        self._render_cascades(ri.get("cascades", []))

    def _render_profiles(self, profiles: list):
        self._clear(self._profiles_layout)
        if not profiles:
            ph = QLabel(tr("No profiles available."))
            ph.setProperty("class", "subtitle")
            self._profiles_layout.addWidget(ph)
            return

        # En-tête de colonnes
        header = QHBoxLayout()
        for txt, w in [(tr("VERDICT"), 80), (tr("SCORE"), 60),
                       (tr("ENTITY"), 180), (tr("DRIVERS"), 0)]:
            lbl = QLabel(txt)
            lbl.setProperty("class", "caption")
            if w:
                lbl.setFixedWidth(w)
            header.addWidget(lbl, 1 if not w else 0)
        hw = QWidget(); hw.setLayout(header)
        self._profiles_layout.addWidget(hw)

        sep = QFrame()
        sep.setObjectName("divider")
        sep.setFixedHeight(1)
        self._profiles_layout.addWidget(sep)

        # Lignes
        for p in profiles[:20]:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 4, 0, 4)

            # Pastille verdict + texte
            color = VERDICT_COLORS.get(p["verdict"], "#52525b")
            v_lbl = QLabel(p["verdict"])
            v_lbl.setStyleSheet(
                f"color: {color}; font-weight: 700; font-size: 9px; letter-spacing: 1px;"
            )
            v_lbl.setFixedWidth(80)
            row.addWidget(v_lbl)

            # Score
            s_lbl = QLabel(f"{p['score']:.2f}")
            s_lbl.setStyleSheet("color: #e4e4e7; font-size: 11px;")
            s_lbl.setFixedWidth(60)
            row.addWidget(s_lbl)

            # Nom
            n_lbl = QLabel(p["name"][:30])
            n_lbl.setStyleSheet("color: #e4e4e7;")
            n_lbl.setFixedWidth(180)
            row.addWidget(n_lbl)

            # Drivers (compactés en chips)
            drivers_layout = QHBoxLayout()
            drivers_layout.setSpacing(4)
            drivers_layout.setContentsMargins(0, 0, 0, 0)
            for d in p.get("drivers", []):
                chip = QLabel(f" {d['label']} {d['value']:.2f} ")
                sev_color = SEVERITY_COLORS.get(d["severity"], "#52525b")
                chip.setStyleSheet(
                    f"color: {sev_color}; font-size: 9px;"
                    f"border: 1px solid {sev_color}; border-radius: 3px;"
                    f"padding: 1px 4px; background-color: rgba(0,0,0,0.2);"
                )
                drivers_layout.addWidget(chip)
            drivers_layout.addStretch()
            dw = QWidget(); dw.setLayout(drivers_layout)
            row.addWidget(dw, 1)

            rw = QWidget(); rw.setLayout(row)
            self._profiles_layout.addWidget(rw)

        self._profiles_layout.addStretch()

    def _render_crises(self, crises: list):
        self._clear(self._crisis_layout)
        if not crises:
            ph = QLabel(tr("No pattern matches."))
            ph.setProperty("class", "subtitle")
            self._crisis_layout.addWidget(ph)
            return

        for c in crises[:3]:
            block = QFrame()
            block.setStyleSheet(
                "QFrame { border-left: 2px solid #27272a; padding-left: 12px; }"
            )
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(12, 4, 0, 4)
            block_layout.setSpacing(2)

            # Top : nom + similarité
            top = QHBoxLayout()
            name = QLabel(f"{c['name'].upper()} · {c['year']}")
            name.setStyleSheet("color: #e4e4e7; font-weight: 600; letter-spacing: 1px;")
            top.addWidget(name)
            top.addStretch()
            sim = QLabel(f"{c['similarity']*100:.0f}%")
            sim_color = "#e3c08e" if c["similarity"] > 0.7 else "#9caec1"
            sim.setStyleSheet(
                f"color: {sim_color}; font-weight: 700; font-size: 13px;"
            )
            top.addWidget(sim)
            block_layout.addLayout(top)

            sector = QLabel(c["sector"])
            sector.setProperty("class", "caption")
            block_layout.addWidget(sector)

            summary = QLabel(c["summary"])
            summary.setProperty("class", "subtitle")
            summary.setStyleSheet("color: #a1a1aa; font-size: 10px;")
            summary.setWordWrap(True)
            block_layout.addWidget(summary)

            cas = QLabel(f"→ {c['casualties']}")
            cas.setStyleSheet("color: #e8a0a0; font-size: 10px;")
            block_layout.addWidget(cas)

            self._crisis_layout.addWidget(block)

    def _render_cascades(self, cascades: list):
        self._clear(self._cascade_layout)
        if not cascades:
            ph = QLabel(tr("No cascade scenarios."))
            ph.setProperty("class", "subtitle")
            self._cascade_layout.addWidget(ph)
            return

        for c in cascades[:3]:
            block = QFrame()
            block.setStyleSheet(
                "QFrame { border-left: 2px solid #e3c08e; padding-left: 12px; }"
            )
            lay = QVBoxLayout(block)
            lay.setContentsMargins(12, 4, 0, 4)
            lay.setSpacing(4)

            title = QLabel(f"{tr('IF')}  {c['source_name'].upper()}  {tr('FAILS')}")
            title.setStyleSheet(
                "color: #e4e4e7; font-weight: 700; letter-spacing: 1px; font-size: 10px;"
            )
            lay.addWidget(title)

            # Grille de KPIs
            grid = QGridLayout()
            grid.setSpacing(8)
            kpis = [
                (tr("Expected loss"),  f"{c['expected_loss']:.0f} M"),
                (tr("VaR 95%"),        f"{c['var_95']:.0f} M"),
                (tr("Entities hit"),   str(c['affected_count'])),
                (tr("Propagation"),    f"{c['propagation_days']} {tr('days')}"),
            ]
            for i, (k, v) in enumerate(kpis):
                kl = QLabel(k.upper())
                kl.setStyleSheet("color: #52525b; font-size: 8px; letter-spacing: 1px;")
                vl = QLabel(v)
                vl.setStyleSheet("color: #e4e4e7; font-size: 13px; font-weight: 600;")
                grid.addWidget(kl, 0, i)
                grid.addWidget(vl, 1, i)
            lay.addLayout(grid)

            self._cascade_layout.addWidget(block)

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        if not self._controller or not self._controller.current_analysis:
            return
        ri = self._controller.current_analysis.get("risk_intel", {})
        self._render(ri)

    def on_show(self):
        self.on_analysis_updated()

    def retranslate(self):
        self._caption_lbl.setText(tr("INTELLIGENCE"))
        self._title_lbl.setText(tr("Risk Intelligence"))
        self._subtitle.setText(tr(
            "Quantitative risk scoring, historical crisis matching, "
            "and cascade impact estimation."
        ))
        self._profiles_card.set_title(tr("Risk Profiles"))
        self._crisis_card.set_title(tr("Crisis Pattern Matching"))
        self._cascade_card.set_title(tr("Cascade Forecast"))
