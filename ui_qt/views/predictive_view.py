"""
Vue Predictive Analytics — passage descriptif -> predictif.

Quatre sections :
  1. Trend leaderboard       — entites aux trajectoires les plus inquietantes
  2. Risk forecast            — courbe avec intervalle de confiance (selection entite)
  3. Monte Carlo stress test  — distribution des pertes sur 1000 runs
  4. Crisis trajectory match  — similarite a des patterns historiques
"""

import logging
import threading
from PySide6.QtCore import Qt, Signal, QMargins, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPolygonF, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QComboBox, QSplitter, QMessageBox, QSizePolicy,
)

from ..components import Card, MetricCard
from ..i18n import tr
from ._base import build_header
from services.knowledge_base import get_kb

logger = logging.getLogger(__name__)


TREND_COLORS = {
    "rising":   "#e8a0a0",
    "falling":  "#84cc9e",
    "stable":   "#9caec1",
}


# ─────────────────────────────────────────────
#  SPARKLINE / CHART WIDGET (custom QPainter)
# ─────────────────────────────────────────────

class ForecastChart(QWidget):
    """
    Mini-chart custom : courbe historique + forecast + bande de confiance.
    Tout en QPainter, monochrome premium.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._historical: list[tuple[str, float]] = []
        self._forecast:   list[tuple[str, float]] = []
        self._conf_low:   list[tuple[str, float]] = []
        self._conf_high:  list[tuple[str, float]] = []
        self._title = ""
        self._setMinimumSize(420, 230)

    def _setMinimumSize(self, w, h):
        self.setMinimumSize(w, h)

    def set_data(self, hist, fc, low, high, title=""):
        self._historical = hist or []
        self._forecast = fc or []
        self._conf_low = low or []
        self._conf_high = high or []
        self._title = title
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        W, H = self.width(), self.height()

        # Padding
        pad_l, pad_r, pad_t, pad_b = 12, 12, 24, 30

        # Background
        p.fillRect(self.rect(), QColor("#0c0c0f"))

        # Si rien a tracer
        if not self._historical and not self._forecast:
            p.setPen(QColor("#52525b"))
            f = QFont("JetBrains Mono", 9)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter,
                       "Select an entity to see its forecast")
            return

        # Combine all points pour les axes
        all_pts = self._historical + self._forecast
        all_low = self._conf_low
        all_high = self._conf_high
        if not all_pts:
            return

        y_values = [v for _, v in all_pts]
        if all_low: y_values += [v for _, v in all_low]
        if all_high: y_values += [v for _, v in all_high]
        y_min = min(y_values + [0])
        y_max = max(y_values + [1])
        # Fixe la plage [0, 1] minimum
        y_min = max(0.0, y_min - 0.05)
        y_max = min(1.0, y_max + 0.05)

        n_total = len(all_pts)
        if n_total < 2:
            return

        def to_xy(i, v):
            x = pad_l + (i / max(1, n_total - 1)) * (W - pad_l - pad_r)
            y = pad_t + (1 - (v - y_min) / (y_max - y_min)) * (H - pad_t - pad_b)
            return QPointF(x, y)

        # Title
        if self._title:
            p.setPen(QColor("#a1a1aa"))
            p.setFont(QFont("JetBrains Mono", 8))
            p.drawText(pad_l, pad_t - 8, self._title)

        # Grid horizontal (0.25, 0.5, 0.75)
        p.setPen(QPen(QColor("#1c1c20"), 1, Qt.DashLine))
        p.setFont(QFont("JetBrains Mono", 7))
        for tv in (0.25, 0.5, 0.75):
            if y_min <= tv <= y_max:
                y = pad_t + (1 - (tv - y_min) / (y_max - y_min)) * (H - pad_t - pad_b)
                p.drawLine(pad_l, y, W - pad_r, y)
                p.setPen(QColor("#3f3f46"))
                p.drawText(2, y + 3, f"{tv:.2f}")
                p.setPen(QPen(QColor("#1c1c20"), 1, Qt.DashLine))

        # Separation historique / forecast
        n_hist = len(self._historical)
        if n_hist and self._forecast:
            sep_x = pad_l + ((n_hist - 1) / max(1, n_total - 1)) * (W - pad_l - pad_r)
            p.setPen(QPen(QColor("#27272a"), 1, Qt.DashLine))
            p.drawLine(sep_x, pad_t, sep_x, H - pad_b)
            p.setPen(QColor("#52525b"))
            p.setFont(QFont("JetBrains Mono", 7))
            p.drawText(sep_x + 4, pad_t + 10, "FORECAST →")

        # Bande de confiance (polygone)
        if self._conf_low and self._conf_high and len(self._conf_low) == len(self._conf_high):
            base_idx = n_hist - 1 if n_hist else 0
            poly_pts = []
            # Top edge (high)
            for j, (_, v) in enumerate(self._conf_high):
                poly_pts.append(to_xy(base_idx + j, v))
            # Bottom edge reverse (low)
            for j in range(len(self._conf_low) - 1, -1, -1):
                _, v = self._conf_low[j]
                poly_pts.append(to_xy(base_idx + j, v))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(227, 192, 142, 35))   # amber 14%
            p.drawPolygon(QPolygonF(poly_pts))

        # Courbe historique
        if self._historical:
            p.setPen(QPen(QColor("#e4e4e7"), 2))
            for i in range(len(self._historical) - 1):
                p1 = to_xy(i, self._historical[i][1])
                p2 = to_xy(i + 1, self._historical[i + 1][1])
                p.drawLine(p1, p2)
            # Points
            p.setBrush(QColor("#e4e4e7"))
            for i, (_, v) in enumerate(self._historical):
                pt = to_xy(i, v)
                p.drawEllipse(pt, 3, 3)

        # Courbe forecast (en pointille)
        if self._forecast:
            base_idx = n_hist - 1 if n_hist else 0
            p.setPen(QPen(QColor("#e3c08e"), 2, Qt.DashLine))
            prev = None
            if n_hist:
                prev = to_xy(n_hist - 1, self._historical[-1][1])
            for j, (_, v) in enumerate(self._forecast):
                pt = to_xy(base_idx + j, v)
                if prev:
                    p.drawLine(prev, pt)
                prev = pt
            # Point final
            if self._forecast:
                p.setBrush(QColor("#e3c08e"))
                last = to_xy(base_idx + len(self._forecast) - 1,
                              self._forecast[-1][1])
                p.drawEllipse(last, 4, 4)

        # Legendes des bornes en bas
        if self._historical:
            p.setPen(QColor("#52525b"))
            p.setFont(QFont("JetBrains Mono", 7))
            p.drawText(pad_l, H - 8, self._historical[0][0])
            if self._forecast:
                last_date = self._forecast[-1][0]
                p.drawText(W - pad_r - 60, H - 8, last_date)

        p.end()


# ─────────────────────────────────────────────
#  HISTOGRAM WIDGET
# ─────────────────────────────────────────────

class HistogramChart(QWidget):
    """Histogramme custom monochrome (pour Monte Carlo distribution)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bins: list[tuple[float, int]] = []
        self._var_95: float = 0
        self._var_99: float = 0
        self._mean: float = 0
        self.setMinimumSize(420, 180)

    def set_data(self, bins, mean, var_95, var_99):
        self._bins = bins or []
        self._mean = mean
        self._var_95 = var_95
        self._var_99 = var_99
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        W, H = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 12, 12, 8, 20

        p.fillRect(self.rect(), QColor("#0c0c0f"))

        if not self._bins:
            p.setPen(QColor("#52525b"))
            p.setFont(QFont("JetBrains Mono", 9))
            p.drawText(self.rect(), Qt.AlignCenter,
                       "Run a Monte Carlo simulation to see the distribution")
            return

        x_min = min(b[0] for b in self._bins)
        x_max = max(b[0] for b in self._bins)
        y_max = max(b[1] for b in self._bins) or 1
        chart_w = W - pad_l - pad_r
        chart_h = H - pad_t - pad_b
        bin_w = chart_w / len(self._bins)

        # Bars
        for i, (center, count) in enumerate(self._bins):
            x = pad_l + i * bin_w
            h = (count / y_max) * chart_h
            y = H - pad_b - h
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#27272a"))
            p.drawRect(int(x), int(y), int(bin_w - 1.5), int(h))

        # VaR lines
        def line_at(value, color, label):
            if x_max == x_min:
                return
            x = pad_l + ((value - x_min) / (x_max - x_min)) * chart_w
            p.setPen(QPen(QColor(color), 1, Qt.DashLine))
            p.drawLine(int(x), pad_t, int(x), H - pad_b)
            p.setFont(QFont("JetBrains Mono", 7))
            p.setPen(QColor(color))
            p.drawText(int(x) + 3, pad_t + 10, label)

        line_at(self._mean,  "#9caec1", "MEAN")
        line_at(self._var_95, "#e3c08e", "VAR 95%")
        line_at(self._var_99, "#e8a0a0", "VAR 99%")

        # Axe X labels
        p.setPen(QColor("#52525b"))
        p.setFont(QFont("JetBrains Mono", 7))
        p.drawText(pad_l, H - 4, f"{x_min:.0f}M")
        p.drawText(W - pad_r - 40, H - 4, f"{x_max:.0f}M")

        p.end()


# ─────────────────────────────────────────────
#  PREDICTIVE VIEW
# ─────────────────────────────────────────────

class PredictiveView(QWidget):

    _mc_done  = Signal(dict)
    _mc_error = Signal(str)

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._kb = get_kb()
        self._trends: list[dict] = []
        self._build()
        self._mc_done.connect(self._on_mc_done)
        self._mc_error.connect(self._on_mc_error)

    # ── Construction ──────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        head_row = QHBoxLayout()
        head_col = QVBoxLayout()
        self._caption_lbl, self._title_lbl = build_header(
            head_col, tr("FORECAST"), tr("Predictive Analytics")
        )
        head_row.addLayout(head_col, 1)

        actions = QHBoxLayout()
        self._btn_refresh = QPushButton(tr("Refresh trends"))
        self._btn_refresh.clicked.connect(self.refresh)
        actions.addWidget(self._btn_refresh)
        self._btn_mc = QPushButton(tr("Run Monte Carlo"))
        self._btn_mc.setProperty("variant", "primary")
        self._btn_mc.clicked.connect(self._run_monte_carlo)
        actions.addWidget(self._btn_mc)
        aw = QWidget(); aw.setLayout(actions)
        head_row.addWidget(aw, 0, Qt.AlignTop)
        outer.addLayout(head_row)

        self._subtitle = QLabel(tr(
            "Forecast risk evolution, detect accelerating trends, "
            "stress-test the network with Monte Carlo simulations, "
            "and match entity trajectories to historical crisis precursors."
        ))
        self._subtitle.setProperty("class", "subtitle")
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        # Stats
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._stat_obs       = MetricCard(tr("Observations"),  "—")
        self._stat_rising    = MetricCard(tr("Rising"),        "—")
        self._stat_falling   = MetricCard(tr("Falling"),       "—")
        self._stat_volatile  = MetricCard(tr("Avg volatility"), "—")
        for s in (self._stat_obs, self._stat_rising,
                  self._stat_falling, self._stat_volatile):
            s.setMinimumHeight(82)
            stats_row.addWidget(s)
        outer.addLayout(stats_row)

        # Corps : 2 colonnes
        body = QHBoxLayout()
        body.setSpacing(20)
        outer.addLayout(body, 1)

        # Colonne gauche : leaderboard tendances
        self._leaderboard_card = Card(tr("Trend Leaderboard"))
        self._leaderboard_layout = QVBoxLayout()
        self._leaderboard_layout.setSpacing(4)
        ph_lb = QLabel(tr("Run analyses with overlapping entities to build trends."))
        ph_lb.setProperty("class", "subtitle")
        ph_lb.setWordWrap(True)
        self._leaderboard_layout.addWidget(ph_lb)
        self._lb_placeholder = ph_lb
        self._leaderboard_card.layout().addLayout(self._leaderboard_layout)
        body.addWidget(self._leaderboard_card, 5)

        # Colonne droite : forecast + monte carlo + trajectory
        right = QVBoxLayout()
        right.setSpacing(12)

        # Forecast
        self._forecast_card = Card(tr("Risk Forecast (30 days)"))
        fc_inner = QVBoxLayout()
        fc_inner.setSpacing(6)
        selector_row = QHBoxLayout()
        selector_row.setSpacing(8)
        sel_lbl = QLabel(tr("ENTITY"))
        sel_lbl.setProperty("class", "caption")
        selector_row.addWidget(sel_lbl)
        self._entity_cb = QComboBox()
        self._entity_cb.setPlaceholderText(tr("Select an entity..."))
        self._entity_cb.currentIndexChanged.connect(self._on_entity_changed)
        selector_row.addWidget(self._entity_cb, 1)
        fc_inner.addLayout(selector_row)
        self._fc_chart = ForecastChart()
        fc_inner.addWidget(self._fc_chart)
        # KPI sous le graphe
        self._fc_kpis = QLabel("")
        self._fc_kpis.setStyleSheet("color: #a1a1aa; font-size: 10px;")
        fc_inner.addWidget(self._fc_kpis)
        self._forecast_card.layout().addLayout(fc_inner)
        right.addWidget(self._forecast_card)

        # Monte Carlo
        self._mc_card = Card(tr("Monte Carlo Stress Test"))
        mc_inner = QVBoxLayout()
        mc_inner.setSpacing(6)
        self._mc_chart = HistogramChart()
        mc_inner.addWidget(self._mc_chart)
        self._mc_kpis = QLabel(tr("Click 'Run Monte Carlo' to simulate 1000 scenarios."))
        self._mc_kpis.setStyleSheet("color: #a1a1aa; font-size: 10px;")
        self._mc_kpis.setWordWrap(True)
        mc_inner.addWidget(self._mc_kpis)
        self._mc_card.layout().addLayout(mc_inner)
        right.addWidget(self._mc_card)

        # Trajectory match
        self._traj_card = Card(tr("Crisis Trajectory Match"))
        self._traj_layout = QVBoxLayout()
        self._traj_layout.setSpacing(4)
        ph_t = QLabel(tr("Select an entity above to see crisis pattern matches."))
        ph_t.setProperty("class", "subtitle")
        ph_t.setWordWrap(True)
        self._traj_layout.addWidget(ph_t)
        self._traj_placeholder = ph_t
        self._traj_card.layout().addLayout(self._traj_layout)
        right.addWidget(self._traj_card)

        right_w = QWidget(); right_w.setLayout(right)
        body.addWidget(right_w, 6)

    # ── Helpers ─────────────────────────────

    def _clear(self, layout):
        while layout.count():
            it = layout.takeAt(0)
            w = it.widget()
            if w: w.deleteLater()

    # ── Refresh leaderboard ─────────────────

    def refresh(self):
        """Recalcule le leaderboard de tendances depuis la KB."""
        from engines.predictive_engine import TrendAnalyzer
        analyzer = TrendAnalyzer(self._kb)
        trends = analyzer.analyze_all(min_observations=1, top_n=30)
        self._trends = [t.to_dict() for t in trends]

        # Stats globales
        n_total = sum(t["n_observations"] for t in self._trends)
        n_rising  = sum(1 for t in self._trends if t["trend"] == "rising")
        n_falling = sum(1 for t in self._trends if t["trend"] == "falling")
        avg_vol = (sum(t["volatility"] for t in self._trends) /
                   max(1, len(self._trends)))
        self._stat_obs.set_value(str(n_total))
        self._stat_rising.set_value(str(n_rising))
        self._stat_falling.set_value(str(n_falling))
        self._stat_volatile.set_value(f"{avg_vol:.2f}")

        # Render leaderboard
        self._render_leaderboard()

        # Combo entites
        self._populate_entity_combo()

    def _render_leaderboard(self):
        self._clear(self._leaderboard_layout)
        if not self._trends:
            ph = QLabel(tr("No entity history yet — run analyses first."))
            ph.setProperty("class", "subtitle")
            ph.setAlignment(Qt.AlignCenter)
            self._leaderboard_layout.addWidget(ph)
            return

        # Header
        header = QHBoxLayout()
        for txt, w in [(tr("ENTITY"), 180), (tr("SCORE"), 60),
                       (tr("Δ 30D"), 70), (tr("MOMENTUM"), 80),
                       (tr("VOLATILITY"), 80), (tr("TREND"), 0)]:
            lbl = QLabel(txt)
            lbl.setProperty("class", "caption")
            if w: lbl.setFixedWidth(w)
            header.addWidget(lbl, 1 if not w else 0)
        hw = QWidget(); hw.setLayout(header)
        self._leaderboard_layout.addWidget(hw)
        sep = QFrame(); sep.setObjectName("divider"); sep.setFixedHeight(1)
        self._leaderboard_layout.addWidget(sep)

        for t in self._trends[:25]:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 3, 0, 3)

            name = QLabel(t["entity_name"][:28])
            name.setStyleSheet("color: #e4e4e7; font-size: 11px;")
            name.setFixedWidth(180)
            row.addWidget(name)

            score = QLabel(f"{t['current_score']:.2f}")
            score.setStyleSheet("color: #e4e4e7; font-size: 11px;")
            score.setFixedWidth(60)
            row.addWidget(score)

            delta = t["delta_30d"]
            delta_color = ("#e8a0a0" if delta > 0.05 else
                           "#84cc9e" if delta < -0.05 else "#9ca3af")
            delta_lbl = QLabel(f"{delta:+.2f}")
            delta_lbl.setStyleSheet(f"color: {delta_color}; font-size: 11px;")
            delta_lbl.setFixedWidth(70)
            row.addWidget(delta_lbl)

            mom = QLabel(f"{t['momentum']:+.4f}")
            mom.setStyleSheet("color: #a1a1aa; font-size: 10px;")
            mom.setFixedWidth(80)
            row.addWidget(mom)

            vol = QLabel(f"{t['volatility']:.2f}")
            vol.setStyleSheet("color: #a1a1aa; font-size: 10px;")
            vol.setFixedWidth(80)
            row.addWidget(vol)

            trend_color = TREND_COLORS.get(t["trend"], "#9ca3af")
            tlbl = QLabel(t["trend"].upper())
            tlbl.setStyleSheet(
                f"color: {trend_color}; font-weight: 700; font-size: 9px; letter-spacing: 1px;"
            )
            row.addWidget(tlbl)

            rw = QWidget(); rw.setLayout(row)
            # Cliquable : selectionne dans le combo
            rw.mousePressEvent = lambda _, eid=t["entity_id"]: self._select_entity_by_id(eid)
            rw.setCursor(Qt.PointingHandCursor)
            self._leaderboard_layout.addWidget(rw)
        self._leaderboard_layout.addStretch()

    # ── Combo entites ───────────────────────

    def _populate_entity_combo(self):
        self._entity_cb.blockSignals(True)
        self._entity_cb.clear()
        for t in self._trends:
            self._entity_cb.addItem(t["entity_name"], userData=t["entity_id"])
        self._entity_cb.blockSignals(False)
        if self._trends:
            self._on_entity_changed(0)

    def _select_entity_by_id(self, eid: int):
        for i in range(self._entity_cb.count()):
            if self._entity_cb.itemData(i) == eid:
                self._entity_cb.setCurrentIndex(i)
                return

    def _on_entity_changed(self, idx):
        if idx < 0:
            return
        eid = self._entity_cb.itemData(idx)
        name = self._entity_cb.itemText(idx)
        if not eid:
            return

        # Recupere l'historique
        history = self._kb.get_entity_history(eid)
        apps = history.get("appearances", [])

        # Forecast
        from engines.predictive_engine import RiskForecaster, TrajectoryMatcher
        fc = RiskForecaster().forecast(name, eid, apps, horizon_days=30)
        if fc:
            self._fc_chart.set_data(
                fc.historical, fc.forecast,
                fc.confidence_low, fc.confidence_high,
                title=f"{name.upper()}  ·  n={fc.n_observations} obs  ·  {fc.method}",
            )
            self._fc_kpis.setText(
                f"CURRENT  {fc.current_score:.2f}   "
                f"FORECAST  {fc.forecast_score:.2f}   "
                f"DELTA  {fc.forecast_score - fc.current_score:+.2f}   "
                f"MOMENTUM  {fc.momentum:+.4f}/d   "
                f"TREND  {fc.trend.upper()}"
            )
        else:
            self._fc_chart.set_data([], [], [], [])
            self._fc_kpis.setText(tr("No data."))

        # Trajectory match
        scores = [v for _, v in (fc.historical if fc else [])]
        matcher = TrajectoryMatcher()
        matches = matcher.match(scores, min_points=3)
        self._render_trajectory(matches)

    def _render_trajectory(self, matches):
        self._clear(self._traj_layout)
        if not matches:
            ph = QLabel(tr("Need at least 3 observations of this entity to compare trajectories."))
            ph.setProperty("class", "subtitle")
            ph.setWordWrap(True)
            self._traj_layout.addWidget(ph)
            return

        for m in matches[:3]:
            m_dict = m.to_dict() if hasattr(m, "to_dict") else m
            block = QFrame()
            block.setStyleSheet(
                "QFrame { border-left: 2px solid #27272a; padding-left: 10px; }"
            )
            lay = QVBoxLayout(block)
            lay.setContentsMargins(10, 4, 0, 4)
            lay.setSpacing(2)
            top = QHBoxLayout()
            name = QLabel(m_dict["pattern_label"])
            name.setStyleSheet("color: #e4e4e7; font-weight: 700; font-size: 11px;")
            top.addWidget(name)
            top.addStretch()
            sim = QLabel(f"{m_dict['similarity']*100:.0f}%")
            sim_color = ("#e3c08e" if m_dict["similarity"] > 0.7
                         else "#9caec1")
            sim.setStyleSheet(
                f"color: {sim_color}; font-weight: 700; font-size: 13px;"
            )
            top.addWidget(sim)
            lay.addLayout(top)
            desc = QLabel(m_dict["description"])
            desc.setStyleSheet("color: #a1a1aa; font-size: 10px;")
            desc.setWordWrap(True)
            lay.addWidget(desc)
            self._traj_layout.addWidget(block)

    # ── Monte Carlo ─────────────────────────

    def _run_monte_carlo(self):
        if not self._controller or not self._controller.get_graph():
            self._app.toast(tr("Run a text analysis first"), "warning")
            return
        self._btn_mc.setEnabled(False)
        self._btn_mc.setText(tr("Running 1000 simulations..."))
        self._app.set_status(tr("Monte Carlo stress test running..."), "info", 0.4)

        controller = self._controller

        def _job():
            try:
                from engines.predictive_engine import MonteCarloSimulator
                G = controller.get_graph()
                ents = controller.current_entities or {}
                ent_for_sim = {eid: {"sentences": e.get("sentences", [])
                                       if isinstance(e, dict)
                                       else getattr(e, "sentences", [])}
                                for eid, e in ents.items()}
                sim = MonteCarloSimulator(G, ent_for_sim)
                result = sim.simulate(n_runs=1000, failure_prob=0.15)
                self._mc_done.emit(result.to_dict())
            except Exception as e:
                logger.exception("Monte Carlo failed")
                self._mc_error.emit(str(e))

        threading.Thread(target=_job, daemon=True).start()

    def _on_mc_done(self, result: dict):
        self._btn_mc.setEnabled(True)
        self._btn_mc.setText(tr("Run Monte Carlo"))
        self._app.set_status(tr("Monte Carlo done"), "success", 1.0)

        self._mc_chart.set_data(
            result.get("histogram", []),
            result.get("mean_loss", 0),
            result.get("var_95", 0),
            result.get("var_99", 0),
        )
        msg = (
            f"MEAN  {result.get('mean_loss', 0):.0f}M    "
            f"MEDIAN  {result.get('median_loss', 0):.0f}M    "
            f"VAR 95%  {result.get('var_95', 0):.0f}M    "
            f"VAR 99%  {result.get('var_99', 0):.0f}M    "
            f"MAX  {result.get('max_loss', 0):.0f}M"
        )
        self._mc_kpis.setText(msg)
        self._app.toast(
            f"{tr('Stress test')}: VaR 95% = {result.get('var_95', 0):.0f}M",
            "info"
        )

    def _on_mc_error(self, msg: str):
        self._btn_mc.setEnabled(True)
        self._btn_mc.setText(tr("Run Monte Carlo"))
        QMessageBox.critical(self, tr("Monte Carlo error"), msg)

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        self.refresh()

    def on_show(self):
        self.refresh()

    def retranslate(self):
        self._caption_lbl.setText(tr("FORECAST"))
        self._title_lbl.setText(tr("Predictive Analytics"))
        self._subtitle.setText(tr(
            "Forecast risk evolution, detect accelerating trends, "
            "stress-test the network with Monte Carlo simulations, "
            "and match entity trajectories to historical crisis precursors."
        ))
        self._btn_refresh.setText(tr("Refresh trends"))
        self._btn_mc.setText(tr("Run Monte Carlo"))
        self._stat_obs.set_label(tr("Observations"))
        self._stat_rising.set_label(tr("Rising"))
        self._stat_falling.set_label(tr("Falling"))
        self._stat_volatile.set_label(tr("Avg volatility"))
        self._leaderboard_card.set_title(tr("Trend Leaderboard"))
        self._forecast_card.set_title(tr("Risk Forecast (30 days)"))
        self._mc_card.set_title(tr("Monte Carlo Stress Test"))
        self._traj_card.set_title(tr("Crisis Trajectory Match"))
