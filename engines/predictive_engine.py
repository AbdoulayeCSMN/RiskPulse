"""
RiskPulse — Predictive Engine
==============================
Etape 5 : passer d'un outil descriptif a un outil predictif.

Quatre composants :
  1. RiskForecaster     — prevision 30/60/90j par entite avec intervalle de confiance
  2. TrendAnalyzer      — momentum, volatilite, classification (rising/falling/stable)
  3. MonteCarloSimulator — stress test sur 1000 scenarios, distribution des pertes
  4. TrajectoryMatcher  — similarite trajectoires courantes avec patterns de crise

Aucune dependance externe payante. Algos statistiques classiques.
"""

from __future__ import annotations
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  1. RISK FORECASTER
# ─────────────────────────────────────────────

@dataclass
class ForecastResult:
    entity_id:        int
    entity_name:      str
    n_observations:   int
    historical:       list[tuple[str, float]]    # (date_iso, score)
    forecast:         list[tuple[str, float]]    # (date_iso, score) future
    confidence_low:   list[tuple[str, float]]
    confidence_high:  list[tuple[str, float]]
    horizon_days:     int
    current_score:    float
    forecast_score:   float           # valeur a t = horizon
    momentum:         float           # delta/jour
    volatility:       float           # std dev des delta
    trend:            str             # rising / falling / stable
    method:           str             # linear / exponential / insufficient

    def to_dict(self) -> dict:
        return {
            "entity_id":       self.entity_id,
            "entity_name":     self.entity_name,
            "n_observations":  self.n_observations,
            "historical":      self.historical,
            "forecast":        self.forecast,
            "confidence_low":  self.confidence_low,
            "confidence_high": self.confidence_high,
            "horizon_days":    self.horizon_days,
            "current_score":   round(self.current_score, 3),
            "forecast_score":  round(self.forecast_score, 3),
            "momentum":        round(self.momentum, 5),
            "volatility":      round(self.volatility, 3),
            "trend":           self.trend,
            "method":          self.method,
        }


class RiskForecaster:
    """
    Prevision du score AML/risque d'une entite a partir de son historique.
    Strategies (selon nb de points disponibles) :
      - n=0 : impossible (renvoie None)
      - n=1 : projection du score courant + bande d'incertitude large
      - n=2 : interpolation lineaire + extrapolation
      - n>=3 : regression lineaire OLS + intervalle de prediction
              + lissage exponentiel pour stabilite
    """

    DEFAULT_HORIZON = 30   # jours

    def forecast(self, entity_name: str, entity_id: int,
                  appearances: list[dict],
                  horizon_days: int = DEFAULT_HORIZON) -> Optional[ForecastResult]:
        """
        appearances : liste de dicts avec keys 'timestamp' (ISO) et 'risk_score'.
        Tries par timestamp croissant.
        """
        if not appearances:
            return None

        # Tri + conversion
        pts: list[tuple[datetime, float]] = []
        for a in appearances:
            ts = a.get("timestamp")
            sc = a.get("risk_score")
            if ts is None or sc is None:
                continue
            try:
                dt = datetime.fromisoformat(ts.replace("Z", ""))
                pts.append((dt, float(sc)))
            except Exception:
                continue
        if not pts:
            return None
        pts.sort(key=lambda x: x[0])

        # Reduire les doublons exacts (meme timestamp)
        deduped = []
        for dt, sc in pts:
            if deduped and deduped[-1][0] == dt:
                continue
            deduped.append((dt, sc))
        pts = deduped

        historical = [(dt.isoformat()[:10], sc) for dt, sc in pts]
        current_score = pts[-1][1]
        n = len(pts)

        # ── Strategie selon n ──
        if n == 1:
            method = "insufficient"
            forecast_score = current_score
            momentum = 0.0
            volatility = 0.2  # large incertitude
        elif n == 2:
            method = "linear"
            d_t = max((pts[1][0] - pts[0][0]).days, 1)
            d_s = pts[1][1] - pts[0][1]
            momentum = d_s / d_t
            forecast_score = current_score + momentum * horizon_days
            volatility = abs(d_s) * 0.5
        else:
            method = "linear_regression"
            # OLS sur tous les points
            t0 = pts[0][0]
            xs = np.array([(dt - t0).days for dt, _ in pts], dtype=float)
            ys = np.array([sc for _, sc in pts], dtype=float)
            # Regression
            slope, intercept = np.polyfit(xs, ys, 1)
            momentum = float(slope)
            # Predictions sur l'historique pour calculer residus
            preds = slope * xs + intercept
            residuals = ys - preds
            volatility = float(np.std(residuals)) or 0.05
            # Forecast a horizon
            last_x = xs[-1]
            forecast_x = last_x + horizon_days
            forecast_score = float(slope * forecast_x + intercept)

        # ── Clip dans [0, 1] ──
        forecast_score = max(0.0, min(1.0, forecast_score))

        # ── Tendance ──
        delta = forecast_score - current_score
        if delta > 0.08:
            trend = "rising"
        elif delta < -0.08:
            trend = "falling"
        else:
            trend = "stable"

        # ── Trajectoire forecast (echantillonne tous les 5 jours) ──
        forecast_pts: list[tuple[str, float]] = []
        conf_low: list[tuple[str, float]] = []
        conf_high: list[tuple[str, float]] = []
        last_dt = pts[-1][0]
        for d in range(0, horizon_days + 1, max(1, horizon_days // 8)):
            future_dt = last_dt + timedelta(days=d)
            # Score lineaire entre current et forecast
            ratio = d / horizon_days if horizon_days > 0 else 0
            score = current_score + (forecast_score - current_score) * ratio
            # Intervalle elargi avec le temps (sqrt(t))
            band = volatility * math.sqrt(max(1, d / 5))
            forecast_pts.append((future_dt.isoformat()[:10], round(score, 3)))
            conf_low.append((future_dt.isoformat()[:10],
                             round(max(0.0, score - 1.96 * band), 3)))
            conf_high.append((future_dt.isoformat()[:10],
                              round(min(1.0, score + 1.96 * band), 3)))

        return ForecastResult(
            entity_id=entity_id,
            entity_name=entity_name,
            n_observations=n,
            historical=historical,
            forecast=forecast_pts,
            confidence_low=conf_low,
            confidence_high=conf_high,
            horizon_days=horizon_days,
            current_score=current_score,
            forecast_score=forecast_score,
            momentum=momentum,
            volatility=volatility,
            trend=trend,
            method=method,
        )


# ─────────────────────────────────────────────
#  2. TREND ANALYZER
# ─────────────────────────────────────────────

@dataclass
class TrendMetric:
    entity_id:      int
    entity_name:    str
    current_score:  float
    delta_30d:      float
    momentum:       float   # delta/jour
    volatility:     float
    trend:          str
    n_observations: int
    acceleration:   float   # variation du momentum sur la fin

    def to_dict(self) -> dict:
        return {
            "entity_id":      self.entity_id,
            "entity_name":    self.entity_name,
            "current_score":  round(self.current_score, 3),
            "delta_30d":      round(self.delta_30d, 3),
            "momentum":       round(self.momentum, 5),
            "volatility":     round(self.volatility, 3),
            "trend":          self.trend,
            "n_observations": self.n_observations,
            "acceleration":   round(self.acceleration, 5),
        }


class TrendAnalyzer:
    """
    Pour chaque entite dans la KB, calcule un profil de tendance.
    Permet de trier le 'leaderboard' des entites au comportement le plus inquietant.
    """

    def __init__(self, knowledge_base):
        self.kb = knowledge_base

    def analyze_all(self, min_observations: int = 2,
                     top_n: int = 30) -> list[TrendMetric]:
        results: list[TrendMetric] = []
        entities = self.kb.list_entities(limit=500)
        for ent in entities:
            if ent.n_analyses < min_observations:
                continue
            history = self.kb.get_entity_history(ent.id)
            apps = history.get("appearances", [])
            metric = self._compute_metric(ent.id, ent.display_name, apps)
            if metric:
                results.append(metric)

        # Trier par "score de preoccupation" : momentum positif elevé + volatility elevee
        def concern(m: TrendMetric) -> float:
            return m.momentum * 100 + m.acceleration * 50 + m.volatility
        results.sort(key=concern, reverse=True)
        return results[:top_n]

    def _compute_metric(self, eid: int, name: str,
                         apps: list[dict]) -> Optional[TrendMetric]:
        # Re-utilise le code du Forecaster pour la coherence
        forecaster = RiskForecaster()
        fr = forecaster.forecast(name, eid, apps, horizon_days=30)
        if not fr:
            return None

        delta_30d = fr.forecast_score - fr.current_score

        # Acceleration : difference entre momentum 'recent' et 'early'
        pts = fr.historical
        if len(pts) >= 4:
            mid = len(pts) // 2
            xs_early = list(range(len(pts[:mid])))
            ys_early = [p[1] for p in pts[:mid]]
            xs_late = list(range(len(pts[mid:])))
            ys_late = [p[1] for p in pts[mid:]]
            try:
                m_early = float(np.polyfit(xs_early, ys_early, 1)[0])
                m_late = float(np.polyfit(xs_late, ys_late, 1)[0])
                acceleration = m_late - m_early
            except Exception:
                acceleration = 0.0
        else:
            acceleration = 0.0

        return TrendMetric(
            entity_id=eid, entity_name=name,
            current_score=fr.current_score,
            delta_30d=delta_30d,
            momentum=fr.momentum,
            volatility=fr.volatility,
            trend=fr.trend,
            n_observations=fr.n_observations,
            acceleration=acceleration,
        )


# ─────────────────────────────────────────────
#  3. MONTE CARLO SIMULATOR
# ─────────────────────────────────────────────

@dataclass
class MonteCarloResult:
    n_runs:         int
    mean_loss:      float
    median_loss:    float
    var_95:         float
    var_99:         float
    max_loss:       float
    min_loss:       float
    histogram:      list[tuple[float, int]]   # (bin_center, count)
    worst_scenarios:list[dict]                # top 5 worst runs avec details

    def to_dict(self) -> dict:
        return {
            "n_runs":          self.n_runs,
            "mean_loss":       round(self.mean_loss, 1),
            "median_loss":     round(self.median_loss, 1),
            "var_95":          round(self.var_95, 1),
            "var_99":          round(self.var_99, 1),
            "max_loss":        round(self.max_loss, 1),
            "min_loss":        round(self.min_loss, 1),
            "histogram":       self.histogram,
            "worst_scenarios": self.worst_scenarios,
        }


class MonteCarloSimulator:
    """
    Stress test : on perturbe aleatoirement le graphe et on calcule la
    distribution des pertes attendues.

    Modes de perturbation :
      - 'random_node_failure'  : chaque noeud peut defaillir avec prob p
      - 'random_edge_removal'  : on coupe aleatoirement K aretes
      - 'sector_shock'         : tous les noeuds d'un type defaillent
    """

    def __init__(self, graph: nx.Graph, entities: dict,
                  estimator=None, currency: str = "MAD"):
        self.graph = graph
        self.entities = entities or {}
        self.currency = currency
        # Lazy import to avoid circular
        if estimator is None:
            from engines.risk_intelligence import CascadeEstimator
            estimator = CascadeEstimator(graph, entities, currency)
        self.estimator = estimator

    def simulate(self, n_runs: int = 1000,
                  failure_prob: float = 0.15) -> MonteCarloResult:
        """
        Pour chaque run :
          1. Choisit aleatoirement les noeuds defaillants (Bernoulli p)
          2. Calcule la perte cumulee comme somme des cascades depuis ces noeuds
        """
        if self.graph.number_of_nodes() == 0:
            return MonteCarloResult(0, 0, 0, 0, 0, 0, 0, [], [])

        nodes = list(self.graph.nodes())
        losses: list[float] = []
        scenarios: list[dict] = []

        for run in range(n_runs):
            # Selection des defaillants
            failed = [n for n in nodes if random.random() < failure_prob]
            if not failed:
                losses.append(0.0)
                continue

            # Estime la perte totale (somme des cascades depuis chaque defaillant)
            total_loss = 0.0
            for node_id in failed[:5]:   # cap a 5 pour eviter explosion
                impact = self.estimator.estimate(node_id)
                if impact:
                    total_loss += impact.expected_loss
            losses.append(total_loss)
            if run < 5 or total_loss > 0:
                # On garde quelques scenarios pour le 'worst'
                scenarios.append({
                    "run":           run,
                    "failed_nodes":  [self.graph.nodes[n].get("label", n)
                                       for n in failed[:5]],
                    "loss":          total_loss,
                })

        losses_arr = np.array(losses, dtype=float)
        # Stats
        mean_loss   = float(losses_arr.mean())
        median_loss = float(np.median(losses_arr))
        var_95 = float(np.percentile(losses_arr, 95))
        var_99 = float(np.percentile(losses_arr, 99))
        max_loss = float(losses_arr.max())
        min_loss = float(losses_arr.min())

        # Histogramme : 20 bins
        hist, edges = np.histogram(losses_arr, bins=20)
        bin_centers = (edges[:-1] + edges[1:]) / 2
        histogram = [(float(c), int(h)) for c, h in zip(bin_centers, hist)]

        # Top 5 worst scenarios
        scenarios.sort(key=lambda s: -s["loss"])
        worst = scenarios[:5]

        return MonteCarloResult(
            n_runs=n_runs,
            mean_loss=mean_loss, median_loss=median_loss,
            var_95=var_95, var_99=var_99,
            max_loss=max_loss, min_loss=min_loss,
            histogram=histogram,
            worst_scenarios=worst,
        )


# ─────────────────────────────────────────────
#  4. TRAJECTORY MATCHER
# ─────────────────────────────────────────────

@dataclass
class TrajectoryMatch:
    pattern_name:    str
    pattern_label:   str
    similarity:      float          # 0..1
    pattern_shape:   list[float]
    entity_shape:    list[float]
    description:     str

    def to_dict(self) -> dict:
        return {
            "pattern_name":  self.pattern_name,
            "pattern_label": self.pattern_label,
            "similarity":    round(self.similarity, 3),
            "pattern_shape": self.pattern_shape,
            "entity_shape":  self.entity_shape,
            "description":   self.description,
        }


# Patterns de precurseur de crise — formes normalisees (5 points)
# Les chiffres sont des heuristiques basees sur l'observation post-mortem
# d'evolutions de risque dans des cas reels.
CRISIS_PRECURSORS = [
    {
        "name":  "wirecard_precursor",
        "label": "Wirecard precursor (slow build-up)",
        "shape": [0.20, 0.32, 0.48, 0.62, 0.78],
        "description": (
            "Hausse progressive et lineaire du risque sur plusieurs trimestres. "
            "Pattern typique d'une fraude comptable qui se devoile lentement."
        ),
    },
    {
        "name":  "lehman_precursor",
        "label": "Lehman precursor (sudden cliff)",
        "shape": [0.35, 0.40, 0.42, 0.55, 0.85],
        "description": (
            "Risque stable puis acceleration brutale en fin de periode. "
            "Typique d'une crise de liquidite ou d'un evenement declencheur."
        ),
    },
    {
        "name":  "madoff_precursor",
        "label": "Madoff precursor (deceptive stability)",
        "shape": [0.45, 0.42, 0.40, 0.41, 0.43],
        "description": (
            "Risque artificiellement stable a niveau eleve. Manque de variance "
            "suspecte : pattern caracteristique des schemas Ponzi."
        ),
    },
    {
        "name":  "recovery",
        "label": "Recovery trajectory (de-risking)",
        "shape": [0.65, 0.55, 0.45, 0.35, 0.25],
        "description": (
            "Reduction progressive du risque. Indique soit un dossier qui se resout, "
            "soit une entite qui sort proprement d'une situation difficile."
        ),
    },
    {
        "name":  "volatile",
        "label": "Volatile / unstable",
        "shape": [0.30, 0.60, 0.35, 0.65, 0.45],
        "description": (
            "Forte volatilite sans tendance claire. Reflete une exposition a des "
            "facteurs externes ou une situation instable."
        ),
    },
]


class TrajectoryMatcher:
    """
    Compare la trajectoire actuelle d'une entite a des patterns historiques
    via correlation (Pearson) sur les formes normalisees.
    """

    def match(self, history_scores: list[float],
              min_points: int = 3) -> list[TrajectoryMatch]:
        if len(history_scores) < min_points:
            return []

        # Resample la serie a 5 points (la taille des patterns)
        shape = self._resample(history_scores, 5)
        results: list[TrajectoryMatch] = []
        for p in CRISIS_PRECURSORS:
            sim = self._similarity(shape, p["shape"])
            results.append(TrajectoryMatch(
                pattern_name=p["name"],
                pattern_label=p["label"],
                similarity=sim,
                pattern_shape=p["shape"],
                entity_shape=shape,
                description=p["description"],
            ))
        results.sort(key=lambda x: -x.similarity)
        return results

    def _resample(self, series: list[float], target_size: int) -> list[float]:
        if len(series) == target_size:
            return list(series)
        # Interpolation lineaire
        xs_old = np.linspace(0, 1, len(series))
        xs_new = np.linspace(0, 1, target_size)
        ys_new = np.interp(xs_new, xs_old, series)
        return [float(y) for y in ys_new]

    def _similarity(self, a: list[float], b: list[float]) -> float:
        """Similarite normalisee = 1 - distance normalisee."""
        if len(a) != len(b):
            return 0.0
        arr_a = np.array(a)
        arr_b = np.array(b)
        # Normalisation min-max pour comparer les formes plutot que les niveaux
        def norm(x):
            mn, mx = x.min(), x.max()
            if mx - mn < 1e-9:
                return np.full_like(x, 0.5)
            return (x - mn) / (mx - mn)
        na, nb = norm(arr_a), norm(arr_b)
        dist = float(np.sqrt(((na - nb) ** 2).mean()))
        return max(0.0, 1.0 - dist)
