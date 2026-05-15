"""
Vue AI Comparison — Matrice 2x2 entre Modele A et Modele B.

L'idee : transformer une metrique abstraite ("Agreement 92%") en argument
metier visuel. Les 4 quadrants montrent qui flag quoi et pourquoi
l'analyse structurelle est superieure.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QSizePolicy,
)

from ..components import Card, MetricCard
from ..i18n import tr
from ._base import build_header


# Couleurs des quadrants (premium minimaliste)
QUAD_COLORS = {
    "both":    "#84cc9e",   # vert sourd : confiance forte
    "only_b":  "#e3c08e",   # ambre : la valeur ajoutee
    "only_a":  "#9caec1",   # bleu froid : anomalie indiv
    "neither": "#52525b",   # gris : neutre
}


class ComparaisonView(QWidget):

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        self._caption_lbl, self._title_lbl = build_header(
            outer, tr("METHODOLOGY"), tr("AI Comparison")
        )

        self._subtitle = QLabel(tr(
            "Two independent algorithms cross-validate the analysis. "
            "Their divergence is where the real value lies."
        ))
        self._subtitle.setProperty("class", "subtitle")
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        # ── Description des 2 modeles (ligne) ──
        desc_row = QHBoxLayout()
        desc_row.setSpacing(16)

        self._card_a = self._build_model_desc(
            label="MODEL A",
            name=tr("ISOLATIONFOREST"),
            paradigm=tr("Individual ML"),
            question=tr("Is this entity atypical taken individually?"),
            mechanism=tr("Examines per-entity features (frequency, degree, type). Detects statistical outliers."),
            sees=tr("Detects: individual anomalies, frequency outliers, atypical types"),
            misses=tr("Misses: structural pivots, bridges between communities"),
            accent="#9caec1",
        )
        desc_row.addWidget(self._card_a)

        self._card_b = self._build_model_desc(
            label="MODEL B",
            name=tr("GRAPHBASED"),
            paradigm=tr("Structural Graph"),
            question=tr("Is this entity critical by its position in the network?"),
            mechanism=tr("Ignores individual features. Uses centrality and topology of the entire network."),
            sees=tr("Detects: hidden hubs, bridges, structural pivots"),
            misses=tr("Misses: text-level anomalies (extreme mentions, unusual types)"),
            accent="#e3c08e",
        )
        desc_row.addWidget(self._card_b)

        outer.addLayout(desc_row)

        # ── Matrice 2x2 ──
        self._matrix_card = Card(tr("Detection Matrix"))
        self._matrix_grid = QGridLayout()
        self._matrix_grid.setSpacing(10)
        self._matrix_card.layout().addLayout(self._matrix_grid)
        outer.addWidget(self._matrix_card, 1)

        self._render_matrix_skeleton()

        # ── Verdict ──
        self._verdict_card = Card(tr("Why this matrix matters"))
        self._verdict_label = QLabel(tr("Run an analysis to see the comparison."))
        self._verdict_label.setProperty("class", "subtitle")
        self._verdict_label.setWordWrap(True)
        self._verdict_card.layout().addWidget(self._verdict_label)
        outer.addWidget(self._verdict_card)

    def _build_model_desc(self, label, name, paradigm, question,
                           mechanism, sees, misses, accent):
        c = QFrame()
        c.setObjectName("card")
        l = QVBoxLayout(c)
        l.setContentsMargins(16, 14, 16, 14)
        l.setSpacing(4)

        # Top : Label + paradigme
        top = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {accent}; font-weight: 700; font-size: 9px; letter-spacing: 2px;"
        )
        top.addWidget(lbl)
        top.addStretch()
        p = QLabel(paradigm.upper())
        p.setStyleSheet("color: #52525b; font-size: 9px; letter-spacing: 1px;")
        top.addWidget(p)
        l.addLayout(top)

        # Nom
        nm = QLabel(name)
        nm.setStyleSheet("color: #e4e4e7; font-size: 14px; font-weight: 700; letter-spacing: 1px;")
        l.addWidget(nm)

        # Question philosophique en italique
        q = QLabel('"' + question + '"')
        q.setStyleSheet("color: #9ca3af; font-style: italic; font-size: 10px;")
        q.setWordWrap(True)
        l.addWidget(q)

        # Mecanisme
        m = QLabel(mechanism)
        m.setStyleSheet("color: #a1a1aa; font-size: 10px; line-height: 1.5;")
        m.setWordWrap(True)
        m.setContentsMargins(0, 4, 0, 4)
        l.addWidget(m)

        # Sees / Misses
        s = QLabel("+ " + sees)
        s.setStyleSheet("color: #84cc9e; font-size: 9px;")
        s.setWordWrap(True)
        l.addWidget(s)

        x = QLabel("− " + misses)
        x.setStyleSheet("color: #e8a0a0; font-size: 9px;")
        x.setWordWrap(True)
        l.addWidget(x)

        return c

    # ── Matrice ──────────────────────────────

    def _render_matrix_skeleton(self):
        # Headers de colonnes
        col_a_yes = QLabel("MODEL A · FLAGS")
        col_a_yes.setProperty("class", "caption")
        col_a_yes.setAlignment(Qt.AlignCenter)
        col_a_no  = QLabel("MODEL A · PASSES")
        col_a_no.setProperty("class", "caption")
        col_a_no.setAlignment(Qt.AlignCenter)

        # Headers de lignes
        row_b_yes = QLabel("MODEL B\nFLAGS")
        row_b_yes.setProperty("class", "caption")
        row_b_yes.setAlignment(Qt.AlignCenter)
        row_b_no  = QLabel("MODEL B\nPASSES")
        row_b_no.setProperty("class", "caption")
        row_b_no.setAlignment(Qt.AlignCenter)

        self._matrix_grid.addWidget(QLabel(""),    0, 0)
        self._matrix_grid.addWidget(col_a_yes,     0, 1)
        self._matrix_grid.addWidget(col_a_no,      0, 2)
        self._matrix_grid.addWidget(row_b_yes,     1, 0)
        self._matrix_grid.addWidget(row_b_no,      2, 0)

        # 4 quadrants vides
        self._quad_both    = self._build_quadrant(
            tr("CROSS-VALIDATED RISK"),
            tr("Flagged by both algorithms — high confidence."),
            QUAD_COLORS["both"],
        )
        self._quad_only_b  = self._build_quadrant(
            tr("HIDDEN SYSTEMIC RISK"),
            tr("Invisible to classical ML — only structural analysis sees it. This is the unique value."),
            QUAD_COLORS["only_b"],
        )
        self._quad_only_a  = self._build_quadrant(
            tr("INDIVIDUAL ANOMALY"),
            tr("Atypical in isolation but not structurally critical. Often textual noise."),
            QUAD_COLORS["only_a"],
        )
        self._quad_neither = self._build_quadrant(
            tr("WITHIN NORMS"),
            tr("Neither algorithm flags. Entity behaves and connects normally."),
            QUAD_COLORS["neither"],
        )

        self._matrix_grid.addWidget(self._quad_both,    1, 1)
        self._matrix_grid.addWidget(self._quad_only_b,  1, 2)
        self._matrix_grid.addWidget(self._quad_only_a,  2, 1)
        self._matrix_grid.addWidget(self._quad_neither, 2, 2)

        self._matrix_grid.setColumnStretch(0, 0)
        self._matrix_grid.setColumnStretch(1, 1)
        self._matrix_grid.setColumnStretch(2, 1)
        self._matrix_grid.setRowStretch(0, 0)
        self._matrix_grid.setRowStretch(1, 1)
        self._matrix_grid.setRowStretch(2, 1)

    def _build_quadrant(self, title: str, desc: str, accent: str) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        f.setStyleSheet(
            "QFrame#card {"
            "  background-color: #121215;"
            f"  border: 1px solid #1c1c20;"
            "  border-radius: 6px;"
            "}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        # Header : titre + count
        head = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {accent}; font-weight: 700; font-size: 10px; letter-spacing: 1.5px;"
        )
        head.addWidget(title_lbl)
        head.addStretch()
        count_lbl = QLabel("—")
        count_lbl.setStyleSheet(
            f"color: {accent}; font-weight: 700; font-size: 18px;"
        )
        head.addWidget(count_lbl)
        lay.addLayout(head)

        # Description
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #6b7280; font-size: 9px; line-height: 1.4;")
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)

        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1c1c20;")
        lay.addWidget(sep)

        # Container pour la liste d'entites
        entities_layout = QVBoxLayout()
        entities_layout.setSpacing(3)
        entities_layout.setContentsMargins(0, 4, 0, 0)
        lay.addLayout(entities_layout, 1)

        # On stocke des refs pour update
        f._count_lbl = count_lbl
        f._entities_layout = entities_layout
        f._accent = accent
        return f

    def _fill_quadrant(self, quad: QFrame, items: list, score_key: str):
        """Vide puis remplit un quadrant avec les entites."""
        # Vide
        while quad._entities_layout.count():
            it = quad._entities_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

        # Met a jour le count
        quad._count_lbl.setText(str(len(items)) if items else "0")

        if not items:
            ph = QLabel(tr("— none —"))
            ph.setStyleSheet("color: #3f3f46; font-size: 10px;")
            quad._entities_layout.addWidget(ph)
            return

        for it in items[:6]:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 0, 0, 0)
            name = QLabel(it["node_name"][:24])
            name.setStyleSheet("color: #e4e4e7; font-size: 10px;")
            row.addWidget(name, 1)
            score = QLabel(f"{it.get(score_key, 0):.2f}")
            score.setStyleSheet(f"color: {quad._accent}; font-size: 10px;")
            row.addWidget(score)
            rw = QWidget()
            rw.setLayout(row)
            quad._entities_layout.addWidget(rw)

        if len(items) > 6:
            more = QLabel(f"+ {len(items)-6} {tr('more')}")
            more.setStyleSheet("color: #52525b; font-size: 9px;")
            quad._entities_layout.addWidget(more)

    # ── Hooks ─────────────────────────────────

    def _render(self, comp: dict):
        c = comp.get("comparison", comp)

        self._fill_quadrant(self._quad_both,    c.get("both_flag",   []), "score_b")
        self._fill_quadrant(self._quad_only_b,  c.get("only_b_flag", []), "score_b")
        self._fill_quadrant(self._quad_only_a,  c.get("only_a_flag", []), "score_a")

        # Neither : on a juste un count
        while self._quad_neither._entities_layout.count():
            it = self._quad_neither._entities_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        self._quad_neither._count_lbl.setText(str(c.get("n_neither", 0)))
        ph = QLabel(tr("Normal nodes within network norms"))
        ph.setStyleSheet("color: #52525b; font-size: 10px;")
        ph.setWordWrap(True)
        self._quad_neither._entities_layout.addWidget(ph)

        # Verdict global
        verdict = c.get("verdict_label", "")
        msg = c.get("verdict_msg") or c.get("key_insight", "")

        verdict_color = {
            "SYSTEMIC_RISK_DETECTED": "#e3c08e",
            "RISK_CONFIRMED":         "#84cc9e",
            "NO_SIGNIFICANT_RISK":    "#9caec1",
        }.get(verdict, "#9ca3af")

        n_only_b = c.get("n_only_b", 0)
        only_b_names = ", ".join(
            e["node_name"] for e in c.get("only_b_flag", [])[:3]
        )

        if n_only_b > 0:
            value_pitch = (
                f'<span style="color:{verdict_color}; font-weight: 700;">'
                f'{n_only_b} HIDDEN SYSTEMIC RISK{"S" if n_only_b > 1 else ""} DETECTED'
                f'</span><br/><br/>'
                f"{tr('Entities')}: <b style='color: #e4e4e7;'>{only_b_names}</b>"
                f"{'...' if len(c.get('only_b_flag', [])) > 3 else ''}<br/><br/>"
                f"{tr('These entities are invisible to traditional anomaly detection.')} "
                f"{tr('Their atypical features are normal — but their structural position in the network is critical.')} "
                f"<b style='color: #e3c08e;'>{tr('This is exactly what RiskPulse adds beyond classical ML.')}</b>"
            )
        else:
            value_pitch = (
                f'<span style="color:{verdict_color}; font-weight: 700;">{verdict.replace("_", " ")}</span><br/><br/>'
                f"{msg}<br/><br/>"
                f"{tr('In this network, both algorithms converge — no hidden systemic risk for now.')}"
            )

        self._verdict_label.setText(value_pitch)
        self._verdict_label.setTextFormat(Qt.RichText)

    def on_analysis_updated(self):
        if self._controller and self._controller.current_analysis:
            comp = self._controller.current_analysis.get("comparison", {})
            self._render(comp)

    def on_show(self):
        self.on_analysis_updated()

    def retranslate(self):
        self._caption_lbl.setText(tr("METHODOLOGY"))
        self._title_lbl.setText(tr("AI Comparison"))
        self._subtitle.setText(tr(
            "Two independent algorithms cross-validate the analysis. "
            "Their divergence is where the real value lies."
        ))
        self._matrix_card.set_title(tr("Detection Matrix"))
        self._verdict_card.set_title(tr("Why this matrix matters"))
        # Note : les labels internes des quadrants nécessiteraient une refonte
        # plus profonde — pour la démo, retranslate sur le verdict suffit
        if self._controller and self._controller.current_analysis:
            self.on_analysis_updated()
