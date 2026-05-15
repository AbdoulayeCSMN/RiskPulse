"""
RiskPulse — Risk Intelligence Engine
======================================
Le moteur qui transforme un graphe d'entités en intelligence de risque
quantitative et actionnable.

Trois composants :
  1. RiskScorer       — score 0..1 par entité, verdict, justification
  2. CrisisMatcher    — similarite topologique a des crises historiques
  3. CascadeEstimator — pertes monetaires en cas de defaillance + VaR

Toutes les valeurs sont **dérivées du graphe** (sans données externes pour
la démo), mais la modélisation suit des heuristiques validées en GRC :
  - Concentration de Herfindahl
  - Eigenvector centrality
  - Cycle detection (boucles de dépendance = amplificateurs de cascade)
  - Sectoral diversity proxy
"""

from __future__ import annotations
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  CONSTANTES — verdicts & seuils
# ─────────────────────────────────────────────

VERDICTS = [
    (0.85, "CRITICAL",  "Defaillance probable - impact systemique"),
    (0.65, "HIGH",      "Risque eleve - surveillance renforcee requise"),
    (0.40, "MODERATE",  "Risque present - surveillance reguliere"),
    (0.20, "LOW",       "Risque maitrise - controle standard"),
    (0.00, "MINIMAL",   "Risque negligeable"),
]


def _verdict(score: float) -> tuple[str, str]:
    for threshold, label, msg in VERDICTS:
        if score >= threshold:
            return label, msg
    return "MINIMAL", "Risque negligeable"


# ─────────────────────────────────────────────
#  RISK SCORER
# ─────────────────────────────────────────────

@dataclass
class EntityRisk:
    """Profil de risque complet d'une entite."""
    node_id:        str
    name:           str
    score:          float                          # 0..1
    verdict:        str                            # CRITICAL / HIGH / ...
    verdict_msg:    str
    drivers:        list[dict] = field(default_factory=list)
    # Sous-scores normalises (pour transparence + UI)
    centrality:     float = 0.0
    concentration:  float = 0.0
    cycle_exposure: float = 0.0
    cumulative_role:float = 0.0
    sentiment:      float = 0.5    # neutre par defaut

    def to_dict(self) -> dict:
        return {
            "node_id":         self.node_id,
            "name":            self.name,
            "score":           round(self.score, 4),
            "verdict":         self.verdict,
            "verdict_msg":     self.verdict_msg,
            "drivers":         self.drivers,
            "centrality":      round(self.centrality, 4),
            "concentration":   round(self.concentration, 4),
            "cycle_exposure":  round(self.cycle_exposure, 4),
            "cumulative_role": round(self.cumulative_role, 4),
            "sentiment":       round(self.sentiment, 4),
        }


class RiskScorer:
    """
    Calcule un score quantitatif (0..1) par entite, avec justification.

    Pondération (configurable) :
      - 35% centralite composite (PageRank + Betweenness)
      - 20% concentration (peu de voisins -> plus de risque concentre)
      - 20% cycle exposure (entité dans un cycle = amplification de cascade)
      - 15% cumulative_role (un dirigeant qui cumule plusieurs mandats)
      - 10% sentiment (mots negatifs dans les phrases qui la mentionnent)
    """

    WEIGHTS = {
        "centrality":      0.35,
        "concentration":   0.20,
        "cycle_exposure":  0.20,
        "cumulative_role": 0.15,
        "sentiment":       0.10,
    }

    # Mots qui signalent un sentiment negatif (multilingue, basique)
    NEGATIVE_WORDS = {
        "pertes", "perte", "loss", "losses", "défaillance", "default", "faillite",
        "crise", "crisis", "scandale", "scandal", "fraude", "fraud",
        "litige", "lawsuit", "investigation", "enquête", "sanction",
        "baisse", "decline", "drop", "chute", "collapse", "effondrement",
        "exposé", "exposed", "risqué", "risky", "vulnérable", "vulnerable",
        "difficulté", "difficulties", "trouble", "concerns", "préoccupations",
    }

    def __init__(self, graph: nx.Graph, entities: dict = None):
        self.G = graph
        self.entities = entities or {}     # node_id -> dict (incluant sentences)
        self._pagerank: Dict[str, float] = {}
        self._betweenness: Dict[str, float] = {}
        self._cycles: set[str] = set()

    def analyze(self) -> List[EntityRisk]:
        """Retourne la liste des profils de risque, triee par score decroissant."""
        if self.G.number_of_nodes() == 0:
            return []

        # ── Pre-calculs sur le graphe ──
        try:
            self._pagerank = nx.pagerank(self.G, weight="weight", max_iter=200)
        except Exception:
            self._pagerank = {n: 1.0 / max(1, self.G.number_of_nodes()) for n in self.G.nodes()}
        try:
            self._betweenness = nx.betweenness_centrality(self.G, weight="weight", normalized=True)
        except Exception:
            self._betweenness = {n: 0.0 for n in self.G.nodes()}

        # Cycles : noeuds appartenant a au moins un cycle simple
        try:
            cycles = nx.cycle_basis(self.G.to_undirected())
            self._cycles = {n for c in cycles for n in c}
        except Exception:
            self._cycles = set()

        results: List[EntityRisk] = []
        for node_id in self.G.nodes():
            risk = self._score_entity(node_id)
            results.append(risk)

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _score_entity(self, node_id: str) -> EntityRisk:
        data = self.G.nodes[node_id]
        name = data.get("label", node_id)

        # ── Sous-score 1 : centralite composite ──
        pr = self._pagerank.get(node_id, 0.0)
        bw = self._betweenness.get(node_id, 0.0)
        centrality = self._normalize_pair(pr, bw, weights=(0.6, 0.4))

        # ── Sous-score 2 : concentration ──
        # Si une entite a 100% de son poids vers UN SEUL voisin -> concentration max
        neighbors = list(self.G.neighbors(node_id))
        if neighbors:
            weights = np.array([
                self.G[node_id][nb].get("weight", 1.0) for nb in neighbors
            ], dtype=float)
            weights = weights / weights.sum()
            herfindahl = float((weights ** 2).sum())   # 0..1, 1 = total concentration
            concentration = herfindahl
        else:
            concentration = 0.0

        # ── Sous-score 3 : cycle exposure ──
        # Une entite dans un cycle amplifie le risque (feedback loop)
        if node_id in self._cycles:
            # Plus on a de voisins dans des cycles, plus le risque est eleve
            cycle_neighbors = sum(1 for nb in neighbors if nb in self._cycles)
            cycle_exposure = min(1.0, 0.4 + 0.15 * cycle_neighbors)
        else:
            cycle_exposure = 0.0

        # ── Sous-score 4 : role cumulatif ──
        # Heuristique : si une entite "Personne" est connectee a plusieurs orgs
        # via des relations a fort poids -> role cumulatif (cumul de mandats)
        ent_type = data.get("type", "?")
        if ent_type in ("Personne", "PERSON", "PER"):
            degree = self.G.degree(node_id)
            cumulative_role = min(1.0, 0.25 * degree)
        else:
            cumulative_role = 0.0

        # ── Sous-score 5 : sentiment ──
        sentiment = self._sentiment_score(node_id)

        # ── Score composite ──
        sub = {
            "centrality":      centrality,
            "concentration":   concentration,
            "cycle_exposure":  cycle_exposure,
            "cumulative_role": cumulative_role,
            "sentiment":       sentiment,
        }
        score = sum(self.WEIGHTS[k] * v for k, v in sub.items())
        score = max(0.0, min(1.0, score))

        # ── Drivers : justification automatique top-3 ──
        drivers = self._build_drivers(sub, neighbors, cycle_exposure)

        verdict, msg = _verdict(score)

        return EntityRisk(
            node_id=node_id,
            name=name,
            score=score,
            verdict=verdict,
            verdict_msg=msg,
            drivers=drivers,
            centrality=centrality,
            concentration=concentration,
            cycle_exposure=cycle_exposure,
            cumulative_role=cumulative_role,
            sentiment=sentiment,
        )

    def _normalize_pair(self, a: float, b: float,
                        weights: tuple = (0.5, 0.5)) -> float:
        """Combine 2 metriques deja normalisees, en sortant 0..1."""
        # Normalise par le max observe (eviter qu'un PR de 0.05 ait l'air faible)
        all_pr = list(self._pagerank.values()) or [1.0]
        all_bw = list(self._betweenness.values()) or [1.0]
        max_pr = max(all_pr) or 1.0
        max_bw = max(all_bw) or 1.0
        norm_a = a / max_pr
        norm_b = b / max_bw
        return weights[0] * norm_a + weights[1] * norm_b

    def _sentiment_score(self, node_id: str) -> float:
        """Retourne 0..1, 1 = entierement neutre, 0 = sentiment tres negatif.
        Pour le score de RISQUE on inverse : negative_count -> augmente le risque.
        On retourne donc 1 - neutralite = "risque sentiment".
        """
        entity = self.entities.get(node_id, {})
        sentences = entity.get("sentences", []) or []
        if not sentences:
            return 0.0

        neg_hits = 0
        total_words = 0
        for s in sentences:
            words = s.lower().split()
            total_words += len(words)
            for w in words:
                w_clean = w.strip(".,;:!?()[]\"'")
                if w_clean in self.NEGATIVE_WORDS:
                    neg_hits += 1

        if total_words == 0:
            return 0.0
        # Ratio puis amplification douce
        ratio = neg_hits / max(1, total_words / 10)   # par 10 mots
        return min(1.0, ratio)

    def _build_drivers(self, sub: dict, neighbors: list,
                       cycle_exposure: float) -> list[dict]:
        """Top 3 facteurs explicatifs du score, formates pour affichage."""
        explanations = {
            "centrality":      ("Position pivot",         "high"),
            "concentration":   ("Concentration sectorielle", "high"),
            "cycle_exposure":  ("Boucle de dependance",    "high"),
            "cumulative_role": ("Cumul de mandats",        "med"),
            "sentiment":       ("Signaux negatifs detectes", "med"),
        }
        ranked = sorted(sub.items(), key=lambda x: x[1], reverse=True)
        drivers = []
        for key, val in ranked:
            if val < 0.15:
                continue
            label, severity = explanations.get(key, (key, "low"))
            drivers.append({
                "key":      key,
                "label":    label,
                "value":    round(val, 3),
                "severity": severity,
            })
        return drivers[:3]


# ─────────────────────────────────────────────
#  CRISIS PATTERN MATCHER
# ─────────────────────────────────────────────

@dataclass
class CrisisPattern:
    """Une crise historique, decrite par sa signature topologique."""
    name:        str
    year:        int
    sector:      str
    summary:     str
    # Signature topologique normalisee
    density:     float
    avg_degree:  float
    clustering:  float
    cycles_pct:  float        # % noeuds dans un cycle
    asymmetry:   float        # disparite degree (gini-like)
    n_critical:  int          # nombre de noeuds tres centraux
    casualties:  str          # un mot sur l'impact


# Bibliotheque de crises historiques avec signatures topologiques observees.
# Les chiffres sont des heuristiques basees sur les rapports post-mortem.
HISTORICAL_CRISES: List[CrisisPattern] = [
    CrisisPattern(
        name="Lehman Brothers", year=2008, sector="Banque d'investissement",
        summary="Defaut d'un acteur central tres connecte, cascade via les CDO et "
                "les prets interbancaires. Topology dense, betweenness elevee.",
        density=0.35, avg_degree=4.2, clustering=0.55, cycles_pct=0.75,
        asymmetry=0.62, n_critical=3, casualties="600B USD pertes systeme",
    ),
    CrisisPattern(
        name="Long-Term Capital Management", year=1998, sector="Hedge fund",
        summary="Un acteur peripherique mais avec leverage extreme. Apparemment isole "
                "mais devoile comme hub cache lors du stress. Signature : faible "
                "frequence textuelle, betweenness anormale.",
        density=0.22, avg_degree=3.1, clustering=0.40, cycles_pct=0.45,
        asymmetry=0.78, n_critical=1, casualties="3.6B USD bailout",
    ),
    CrisisPattern(
        name="Madoff", year=2008, sector="Asset management",
        summary="Schema Ponzi avec un acteur central qui collecte de multiples "
                "feeders. Star topology : 1 hub, beaucoup de feuilles.",
        density=0.18, avg_degree=2.4, clustering=0.15, cycles_pct=0.10,
        asymmetry=0.88, n_critical=1, casualties="65B USD declares",
    ),
    CrisisPattern(
        name="Wirecard", year=2020, sector="FinTech / paiement",
        summary="Fraude comptable via un reseau de filiales offshore. Cycles "
                "complexes entre entites liees, asymetrie topologique forte.",
        density=0.30, avg_degree=3.8, clustering=0.48, cycles_pct=0.60,
        asymmetry=0.70, n_critical=2, casualties="1.9B EUR portes manquants",
    ),
    CrisisPattern(
        name="Enron", year=2001, sector="Energie",
        summary="Entites ad hoc (SPE) creant des cycles de dette opaque. Topology "
                "avec beaucoup de cycles courts et un acteur central.",
        density=0.40, avg_degree=4.5, clustering=0.62, cycles_pct=0.80,
        asymmetry=0.65, n_critical=2, casualties="74B USD market cap perdu",
    ),
    CrisisPattern(
        name="Northern Rock", year=2007, sector="Banque de detail",
        summary="Bank run sur un acteur dependant a 80% du marche monetaire. "
                "Topology : un hub avec dependance massive a un type de funding.",
        density=0.25, avg_degree=3.0, clustering=0.35, cycles_pct=0.30,
        asymmetry=0.80, n_critical=1, casualties="Nationalisation 2008",
    ),
]


class CrisisMatcher:
    """Calcule la similarite topologique entre le graphe courant et chaque crise."""

    def __init__(self, graph: nx.Graph):
        self.G = graph

    def signature(self) -> dict:
        """Calcule la signature topologique du graphe courant."""
        G = self.G
        n = G.number_of_nodes()
        if n < 2:
            return {"density": 0, "avg_degree": 0, "clustering": 0,
                    "cycles_pct": 0, "asymmetry": 0, "n_critical": 0}

        density = nx.density(G)
        degrees = [d for _, d in G.degree()]
        avg_degree = float(np.mean(degrees))
        try:
            clustering = float(nx.average_clustering(G))
        except Exception:
            clustering = 0.0

        try:
            cycles = nx.cycle_basis(G.to_undirected())
            in_cycle = {x for c in cycles for x in c}
            cycles_pct = len(in_cycle) / n
        except Exception:
            cycles_pct = 0.0

        # Asymetrie = degre maximum vs moyen
        if degrees:
            asymmetry = (max(degrees) - avg_degree) / max(1.0, max(degrees))
        else:
            asymmetry = 0.0

        try:
            pr = nx.pagerank(G, max_iter=100)
            n_critical = sum(1 for v in pr.values() if v > 0.10)
        except Exception:
            n_critical = 0

        return {
            "density":     density,
            "avg_degree":  avg_degree,
            "clustering":  clustering,
            "cycles_pct":  cycles_pct,
            "asymmetry":   asymmetry,
            "n_critical":  n_critical,
        }

    def match(self) -> List[dict]:
        """
        Retourne la liste des crises classees par similarite decroissante.
        Score = 1 - distance normalisee (euclidienne ponderee).
        """
        sig = self.signature()
        results = []
        for crisis in HISTORICAL_CRISES:
            sim = self._similarity(sig, crisis)
            results.append({
                "name":       crisis.name,
                "year":       crisis.year,
                "sector":     crisis.sector,
                "summary":    crisis.summary,
                "casualties": crisis.casualties,
                "similarity": round(sim, 3),
                "signature":  {
                    "density":     crisis.density,
                    "avg_degree":  crisis.avg_degree,
                    "clustering":  crisis.clustering,
                    "cycles_pct":  crisis.cycles_pct,
                    "asymmetry":   crisis.asymmetry,
                    "n_critical":  crisis.n_critical,
                },
            })
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results

    def _similarity(self, sig: dict, c: CrisisPattern) -> float:
        # Distance euclidienne sur features normalisees, puis 1 - dist
        features = [
            (sig["density"],     c.density),
            (sig["avg_degree"] / 10.0, c.avg_degree / 10.0),   # rescale
            (sig["clustering"],  c.clustering),
            (sig["cycles_pct"],  c.cycles_pct),
            (sig["asymmetry"],   c.asymmetry),
        ]
        weights = [0.2, 0.15, 0.2, 0.25, 0.2]
        dist = math.sqrt(sum(w * (a - b) ** 2 for w, (a, b) in zip(weights, features)))
        # Normalise : la distance max possible est ~1.0 avec ces features
        return max(0.0, 1.0 - dist)


# ─────────────────────────────────────────────
#  CASCADE ESTIMATOR
# ─────────────────────────────────────────────

@dataclass
class CascadeImpact:
    """Estimation chiffree de l'impact d'une defaillance."""
    source_id:       str
    source_name:     str
    expected_loss:   float       # MAD (ou unite par defaut)
    var_95:          float       # Value-at-Risk 95%
    affected_count:  int
    propagation_days: int
    affected_entities: list[dict]    # liste des noeuds touches + magnitude
    method:          str = "graph_proximity"

    def to_dict(self) -> dict:
        return {
            "source_id":         self.source_id,
            "source_name":       self.source_name,
            "expected_loss":     round(self.expected_loss, 0),
            "var_95":            round(self.var_95, 0),
            "affected_count":    self.affected_count,
            "propagation_days":  self.propagation_days,
            "affected_entities": self.affected_entities,
            "method":            self.method,
        }


class CascadeEstimator:
    """
    Estime l'impact financier d'une defaillance d'un noeud.

    Heuristique simplifiee (en demo, sans donnees externes) :
      - Exposition de base = montants mentionnes dans le texte autour du noeud
      - Propagation = fraction du poids des aretes a chaque hop, avec decay
      - VaR95 = expected_loss × 1.65 (approximation normale, n'est PAS un calcul
        de VaR rigoureux, mais raisonnable pour une demo)
      - Duree de propagation = diametre du sous-graphe touche × constante
    """

    DECAY = 0.55              # par hop
    DEFAULT_BASE_LOSS = 100   # millions, si rien d'autre

    def __init__(self, graph: nx.Graph, entities: dict = None,
                 currency: str = "MAD"):
        self.G = graph
        self.entities = entities or {}
        self.currency = currency

    def estimate(self, source_id: str) -> Optional[CascadeImpact]:
        if source_id not in self.G:
            return None
        source_data = self.G.nodes[source_id]
        source_name = source_data.get("label", source_id)

        # ── Base loss : montants mentionnes dans le texte autour de l'entite ──
        base_loss = self._extract_base_loss(source_id)

        # ── Propagation BFS avec decay ──
        affected: dict[str, float] = {}
        visited = {source_id: 1.0}
        frontier = [source_id]
        depth = 0
        max_depth = 4

        while frontier and depth < max_depth:
            next_frontier = []
            for node in frontier:
                base_exposure = visited[node]
                for nb in self.G.neighbors(node):
                    edge_w = self.G[node][nb].get("weight", 1.0)
                    edge_norm = min(1.0, edge_w / 4.0)
                    propagated = base_exposure * self.DECAY * edge_norm
                    if propagated > 0.05:
                        old = visited.get(nb, 0.0)
                        if propagated > old:
                            visited[nb] = propagated
                            affected[nb] = propagated
                            next_frontier.append(nb)
            frontier = list(set(next_frontier))
            depth += 1

        # ── Conversion en pertes ──
        # Chaque noeud touche herite d'une fraction de la base loss
        affected_loss = sum(affected.values()) * base_loss
        expected_loss = base_loss + affected_loss
        var_95 = expected_loss * 1.65

        # ── Liste des entites touchees + magnitude ──
        affected_list = []
        for nid, exposure in sorted(affected.items(), key=lambda x: -x[1]):
            n_data = self.G.nodes[nid]
            affected_list.append({
                "id":         nid,
                "name":       n_data.get("label", nid),
                "exposure":   round(exposure, 3),
                "loss_share": round(exposure * base_loss, 0),
            })

        # ── Duree estimee ──
        # 1.5 jours par hop dans un reseau financier (chiffre de demonstration)
        propagation_days = max(1, int(depth * 1.5))

        return CascadeImpact(
            source_id=source_id,
            source_name=source_name,
            expected_loss=expected_loss,
            var_95=var_95,
            affected_count=len(affected),
            propagation_days=propagation_days,
            affected_entities=affected_list,
        )

    def _extract_base_loss(self, node_id: str) -> float:
        """
        Recupere une exposition de base depuis le texte (montants mentionnes).
        Fallback : 100 millions (unite par defaut).
        """
        import re
        entity = self.entities.get(node_id, {})
        sentences = entity.get("sentences", []) or []
        if not sentences:
            return self.DEFAULT_BASE_LOSS

        max_amount = 0.0
        for sent in sentences:
            # Capture : "500 millions", "1.2 milliard", "200M USD"
            for m in re.finditer(
                r"(\d+(?:[.,]\d+)?)\s*(millions?|milliards?|million|billion|M|Md|Mds)",
                sent.lower(),
            ):
                val = float(m.group(1).replace(",", "."))
                unit = m.group(2)
                if "milliard" in unit or "billion" in unit or unit in ("Md", "Mds"):
                    val *= 1000
                max_amount = max(max_amount, val)

        return max_amount if max_amount > 0 else self.DEFAULT_BASE_LOSS

    def estimate_top_risks(self, top_n: int = 3) -> list[CascadeImpact]:
        """Estime les cascades pour les noeuds les plus centraux du graphe."""
        if self.G.number_of_nodes() == 0:
            return []
        try:
            pr = nx.pagerank(self.G, max_iter=100)
        except Exception:
            pr = {n: 1 for n in self.G.nodes()}
        top_nodes = sorted(pr.items(), key=lambda x: -x[1])[:top_n]
        results = []
        for node_id, _ in top_nodes:
            r = self.estimate(node_id)
            if r:
                results.append(r)
        return results
