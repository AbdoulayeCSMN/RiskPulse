"""
RiskPulse — Modèles IA
========================
Rupture 4 : Comparaison de deux approches algorithmiques fondamentalement différentes.

Modèle A : IsolationForest — analyse chaque entité INDIVIDUELLEMENT
           (approche classique ML, ignore la structure du réseau)

Modèle B : Graph-based Scoring — analyse chaque entité via ses CONNEXIONS
           (approche graphe, exploite la topologie du réseau)

La comparaison révèle pourquoi l'approche graphe est supérieure
pour détecter les risques systémiques.

2Regle : comparaison deux algorithmes minimum obligatoire
"""

import time
import logging
import pickle
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import numpy as np
import networkx as nx
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  RÉSULTAT DE PRÉDICTION
# ─────────────────────────────────────────────

@dataclass
class PredictionResult:
    """Résultat unifié pour les deux modèles."""
    node_id: str
    node_name: str
    score: float          # Score de risque normalisé [0, 1]
    is_anomaly: bool      # True = suspect/risqué
    confidence: float     # Confiance de la prédiction [0, 1]
    explanation: str      # Explication textuelle
    model_name: str       # "IsolationForest" ou "GraphBased"

    def to_dict(self) -> dict:
        return {
            "node_id":    self.node_id,
            "node_name":  self.node_name,
            "score":      round(float(self.score), 4),
            "is_anomaly": bool(self.is_anomaly),
            "confidence": round(float(self.confidence), 4),
            "explanation": self.explanation,
            "model_name": self.model_name,
        }


# ─────────────────────────────────────────────
#  MODÈLE A — ISOLATION FOREST
# ─────────────────────────────────────────────

class IsolationForestModel:
    """
    Modèle A : Détection d'anomalies par Isolation Forest.

    Approche CLASSIQUE :
    - Extrait des features TABULAIRES pour chaque entité (degré, fréquence…)
    - Traite chaque entité de façon INDÉPENDANTE
    - Ne tient PAS compte des relations entre entités

    Limitation mise en évidence : rate les entités risquées
    uniquement à cause de leurs connexions (risque systémique).
    """

    MODEL_NAME = "IsolationForest"

    def __init__(self, contamination: float = 0.1, n_estimators: int = 100):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42,
            max_features=1.0,
        )
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.trained = False
        self.training_time: float = 0.0
        self.last_scores: Dict[str, PredictionResult] = {}

    # ── Features ─────────────────────────────

    def _extract_features(self, graph: nx.Graph) -> Tuple[np.ndarray, List[str]]:
        """
        Extrait des features TABULAIRES pour chaque nœud.
        Ces features ne tiennent compte que des propriétés locales.
        """
        node_ids = list(graph.nodes())
        features = []

        for node in node_ids:
            data = graph.nodes[node]
            degree = graph.degree(node)

            # Voisinage immédiat uniquement
            neighbors = list(graph.neighbors(node))
            neighbor_degrees = [graph.degree(n) for n in neighbors] if neighbors else [0]
            edge_weights = [graph[node][n].get('weight', 1.0) for n in neighbors] if neighbors else [0]

            feat = [
                float(degree),                                    # degré
                float(data.get('frequency', 1)),                  # fréquence dans le texte
                float(len(neighbors)),                            # nb voisins
                float(np.mean(neighbor_degrees)),                 # degré moyen voisins
                float(np.std(neighbor_degrees)) if len(neighbor_degrees) > 1 else 0.0,
                float(np.sum(edge_weights)),                      # somme poids arêtes
                float(np.mean(edge_weights)),                     # poids moyen arêtes
                float(np.max(edge_weights)) if edge_weights else 0.0,
            ]
            features.append(feat)

        self.feature_names = [
            "degré", "fréquence", "nb_voisins",
            "degré_moy_voisins", "std_degrés_voisins",
            "somme_poids", "poids_moyen", "poids_max"
        ]

        return np.array(features), node_ids

    # ── Entraînement ─────────────────────────

    def train(self, graph: nx.Graph) -> dict:
        """Entraîne le modèle sur le graphe courant."""
        start = time.time()

        if graph.number_of_nodes() < 3:
            logger.warning("Graphe trop petit pour IsolationForest (< 3 nœuds)")
            return {"error": "Graphe trop petit"}

        X, node_ids = self._extract_features(graph)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.trained = True
        self.training_time = round(time.time() - start, 3)

        logger.info(f"IsolationForest entraîné en {self.training_time}s sur {len(node_ids)} entités")
        return {
            "model": self.MODEL_NAME,
            "n_samples": len(node_ids),
            "training_time": self.training_time,
            "contamination": self.contamination,
        }

    # ── Prédiction ────────────────────────────

    def predict_all(self, graph: nx.Graph) -> Dict[str, PredictionResult]:
        """Prédit le score de risque pour chaque nœud du graphe."""
        if not self.trained:
            self.train(graph)

        X, node_ids = self._extract_features(graph)
        X_scaled = self.scaler.transform(X)

        # scores_raw : valeurs négatives = anomalie chez sklearn
        scores_raw = self.model.decision_function(X_scaled)
        labels = self.model.predict(X_scaled)  # -1 = anomalie, 1 = normal

        # Normalise les scores en [0, 1]
        # Plus le score est élevé, plus l'entité est "risquée"
        score_min, score_max = scores_raw.min(), scores_raw.max()
        span = score_max - score_min if score_max != score_min else 1.0
        scores_normalized = 1.0 - (scores_raw - score_min) / span

        results = {}
        for i, node_id in enumerate(node_ids):
            node_data = graph.nodes[node_id]
            score = float(scores_normalized[i])
            is_anomaly = bool(labels[i] == -1)
            confidence = abs(float(scores_raw[i])) / (abs(score_min) + abs(score_max) + 1e-8)
            confidence = min(confidence, 1.0)

            results[node_id] = PredictionResult(
                node_id=node_id,
                node_name=node_data.get("label", node_id),
                score=score,
                is_anomaly=is_anomaly,
                confidence=confidence,
                explanation=self._explain(node_id, graph, score, is_anomaly),
                model_name=self.MODEL_NAME,
            )

        self.last_scores = results
        # Met à jour le graphe
        for nid, res in results.items():
            graph.nodes[nid]['risk_score_A'] = res.score
        return results

    def _explain(self, node_id: str, graph: nx.Graph, score: float, is_anomaly: bool) -> str:
        """Explication simple basée sur les features locales."""
        degree = graph.degree(node_id)
        freq = graph.nodes[node_id].get('frequency', 1)
        if is_anomaly:
            if degree > 5:
                return f"Trop connecté ({degree} liens) — comportement anormal local"
            elif freq > 3:
                return f"Fréquence élevée ({freq}) — présence inhabituelle dans le texte"
            else:
                return "Profil de features atypique par rapport aux autres entités"
        return "Entité dans les normes comportementales locales"

    # ── Persistance ───────────────────────────

    def save(self, path: str):
        with open(path, 'wb') as f:
            pickle.dump({"model": self.model, "scaler": self.scaler,
                         "features": self.feature_names, "trained": self.trained}, f)
        logger.info(f"Modèle A sauvegardé : {path}")

    def load(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        with open(path, 'rb') as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.feature_names = data["features"]
        self.trained = data["trained"]
        return True

    def get_metrics(self) -> dict:
        return {
            "model_name":    self.MODEL_NAME,
            "contamination": self.contamination,
            "n_estimators":  self.n_estimators,
            "trained":       self.trained,
            "training_time": self.training_time,
        }


# ─────────────────────────────────────────────
#  MODÈLE B — GRAPH-BASED SCORING
# ─────────────────────────────────────────────

class GraphBasedModel:
    """
    Modèle B : Scoring basé sur la structure du graphe.

    Approche GRAPHE (rupture) :
    - Analyse la TOPOLOGIE du réseau, pas juste les features locales
    - Utilise : centralité composite, clustering, communautés, k-core
    - Détecte les entités risquées VIA LEURS CONNEXIONS
    - Compare avec Modèle A pour révéler le risque systémique invisible

    La différence fondamentale : une entité peut sembler normale
    en Modèle A, mais être critique en Modèle B parce qu'elle
    est au carrefour de plusieurs sous-réseaux risqués.
    """

    MODEL_NAME = "GraphBased"

    def __init__(self):
        self.trained = False
        self.training_time: float = 0.0
        self.last_scores: Dict[str, PredictionResult] = {}
        self._graph_stats: dict = {}

    # ── Entraînement ─────────────────────────

    def train(self, graph: nx.Graph) -> dict:
        """
        'Entraînement' = calcul des métriques structurelles du graphe.
        Pas d'entraînement supervisé : le scoring est dérivé de la topologie.
        """
        start = time.time()

        if graph.number_of_nodes() < 2:
            return {"error": "Graphe trop petit"}

        # Calcule les métriques structurelles globales (référence)
        self._graph_stats = self._compute_graph_stats(graph)
        self.trained = True
        self.training_time = round(time.time() - start, 3)

        logger.info(f"GraphBased 'entraîné' en {self.training_time}s")
        return {
            "model": self.MODEL_NAME,
            "n_nodes": graph.number_of_nodes(),
            "training_time": self.training_time,
            "graph_stats": self._graph_stats,
        }

    def _compute_graph_stats(self, G: nx.Graph) -> dict:
        """Calcule les statistiques globales du graphe."""
        stats = {
            "density": nx.density(G),
            "avg_clustering": nx.average_clustering(G),
            "n_components": nx.number_connected_components(G),
        }
        try:
            stats["avg_shortest_path"] = nx.average_shortest_path_length(G) \
                if nx.is_connected(G) else 0.0
        except Exception:
            stats["avg_shortest_path"] = 0.0
        return stats

    # ── Prédiction ────────────────────────────

    def predict_all(self, graph: nx.Graph) -> Dict[str, PredictionResult]:
        """
        Score de risque graphe pour chaque nœud.
        Le score combine :
        1. Centralité composite (PageRank + Betweenness + Closeness)
        2. Coefficient de clustering local (nœud dans un cluster dense = plus exposé)
        3. K-core decomposition (nœuds dans le cœur dense = plus critiques)
        4. Score de risque des voisins (propagation directe)
        """
        if not self.trained:
            self.train(graph)

        # ── Métriques structurelles par nœud ──
        pagerank    = nx.pagerank(graph, alpha=0.85, weight='weight', max_iter=200)
        betweenness = nx.betweenness_centrality(graph, weight='weight', normalized=True)
        closeness   = nx.closeness_centrality(graph)
        clustering  = nx.clustering(graph, weight='weight')

        # K-core : nœuds dans le cœur le plus dense
        try:
            kcore = nx.core_number(graph)
            max_k = max(kcore.values()) if kcore else 1
        except Exception:
            kcore = {n: 1 for n in graph.nodes()}
            max_k = 1

        # Normalise toutes les métriques
        def norm(d):
            vals = list(d.values())
            mn, mx = min(vals), max(vals)
            span = mx - mn if mx != mn else 1.0
            return {k: (v - mn) / span for k, v in d.items()}

        pr_n  = norm(pagerank)
        bw_n  = norm(betweenness)
        cl_n  = norm(closeness)
        clu_n = norm(clustering)
        kc_n  = {k: v / max_k for k, v in kcore.items()}

        results = {}
        for node_id in graph.nodes():
            node_data = graph.nodes[node_id]

            # Score composite graphe
            # Betweenness fort = nœud pont = risque de propagation élevé
            score = (
                0.30 * pr_n.get(node_id, 0)   +
                0.35 * bw_n.get(node_id, 0)   +
                0.15 * cl_n.get(node_id, 0)   +
                0.10 * clu_n.get(node_id, 0)  +
                0.10 * kc_n.get(node_id, 0)
            )
            score = min(max(score, 0.0), 1.0)
            is_risky = score >= 0.6
            confidence = abs(score - 0.5) * 2  # distance au seuil

            results[node_id] = PredictionResult(
                node_id=node_id,
                node_name=node_data.get("label", node_id),
                score=round(score, 4),
                is_anomaly=is_risky,
                confidence=round(confidence, 4),
                explanation=self._explain(
                    node_id, graph, score,
                    bw_n.get(node_id, 0),
                    kc_n.get(node_id, 0),
                    clustering.get(node_id, 0),
                ),
                model_name=self.MODEL_NAME,
            )

        self.last_scores = results
        # Met à jour le graphe
        for nid, res in results.items():
            graph.nodes[nid]['risk_score_B'] = res.score
        return results

    def _explain(self, node_id: str, graph: nx.Graph, score: float,
                 bw: float, kcore: float, clustering: float) -> str:
        """Explication structurelle du score graphe."""
        parts = []
        if bw >= 0.6:
            parts.append("nœud pont entre plusieurs communautés du réseau")
        if kcore >= 0.7:
            parts.append("appartient au cœur dense du réseau (k-core élevé)")
        if clustering >= 0.6:
            parts.append("fortement clusterisé (groupe d'entités liées)")
        degree = graph.degree(node_id)
        if degree >= 5:
            parts.append(f"très connecté ({degree} liens directs)")
        if not parts:
            return "Score structurel modéré — position neutre dans le réseau"
        return "; ".join(parts)

    def get_metrics(self) -> dict:
        return {
            "model_name":    self.MODEL_NAME,
            "trained":       self.trained,
            "training_time": self.training_time,
            "graph_stats":   self._graph_stats,
            "approach":      "Analyse topologique du réseau (non supervisée)",
        }


# ─────────────────────────────────────────────
#  COMPARATEUR — Bakkas : comparaison obligatoire
# ─────────────────────────────────────────────

class ModelComparator:
    """
    Compare les résultats des deux modèles et produit
    un rapport de comparaison pour le dashboard et la soutenance.

    Bakkas : "comparaison de deux approches algorithmiques au minimum"
    """

    def __init__(self):
        self.model_a = IsolationForestModel()
        self.model_b = GraphBasedModel()
        self._results_a: Dict[str, PredictionResult] = {}
        self._results_b: Dict[str, PredictionResult] = {}

    def run_both(self, graph: nx.Graph) -> dict:
        """Lance les deux modèles et retourne la comparaison complète."""
        start = time.time()

        # ── Modèle A ──
        train_a = self.model_a.train(graph)
        self._results_a = self.model_a.predict_all(graph)

        # ── Modèle B ──
        train_b = self.model_b.train(graph)
        self._results_b = self.model_b.predict_all(graph)

        total_time = round(time.time() - start, 3)

        return {
            "model_a": {
                "name": IsolationForestModel.MODEL_NAME,
                "description": "Analyse individuelle des entités (features locales)",
                "results": {k: v.to_dict() for k, v in self._results_a.items()},
                "metrics": self.model_a.get_metrics(),
                "training": train_a,
            },
            "model_b": {
                "name": GraphBasedModel.MODEL_NAME,
                "description": "Analyse structurelle du réseau (topologie graphe)",
                "results": {k: v.to_dict() for k, v in self._results_b.items()},
                "metrics": self.model_b.get_metrics(),
                "training": train_b,
            },
            "comparison": self._compare(),
            "total_time": total_time,
        }

    def _compare(self) -> dict:
        """
        Produit les métriques de comparaison entre les deux modèles.
        Met en évidence les entités où les deux modèles DIVERGENT —
        c'est là que se révèle le risque systémique.
        """
        agreements = 0
        divergences = []
        only_b_risky = []   # B détecte un risque que A manque

        for node_id in self._results_a:
            res_a = self._results_a[node_id]
            res_b = self._results_b.get(node_id)
            if not res_b:
                continue

            agree = res_a.is_anomaly == res_b.is_anomaly
            if agree:
                agreements += 1
            else:
                delta = abs(res_b.score - res_a.score)
                divergences.append({
                    "node_id":   node_id,
                    "node_name": res_a.node_name,
                    "score_a":   round(res_a.score, 3),
                    "score_b":   round(res_b.score, 3),
                    "delta":     round(delta, 3),
                    "a_risky":   res_a.is_anomaly,
                    "b_risky":   res_b.is_anomaly,
                })
                # Cas critique : B détecte un risque que A manque
                if res_b.is_anomaly and not res_a.is_anomaly:
                    only_b_risky.append({
                        "node_name":   res_b.node_name,
                        "score_b":     round(res_b.score, 3),
                        "explanation": res_b.explanation,
                    })

        n = len(self._results_a)
        agreement_rate = round(agreements / n, 3) if n > 0 else 0

        return {
            "agreement_rate":  agreement_rate,
            "divergences":     sorted(divergences, key=lambda x: x["delta"], reverse=True),
            "only_b_detects":  only_b_risky,  # La vraie rupture visible
            "n_anomalies_a":   sum(1 for r in self._results_a.values() if r.is_anomaly),
            "n_anomalies_b":   sum(1 for r in self._results_b.values() if r.is_anomaly),
            "key_insight": (
                f"Modèle B détecte {len(only_b_risky)} entité(s) risquée(s) "
                f"invisibles pour Modèle A — risque systémique révélé."
            ) if only_b_risky else
                "Les deux modèles convergent sur ce réseau.",
        }

    def get_results_for_node(self, node_id: str) -> Tuple[Optional[PredictionResult], Optional[PredictionResult]]:
        return self._results_a.get(node_id), self._results_b.get(node_id)

    def get_all_scores(self) -> dict:
        """Retourne les scores bruts pour le dashboard."""
        scores = {}
        for nid in self._results_a:
            scores[nid] = {
                "score_a": self._results_a[nid].score,
                "score_b": self._results_b.get(nid, self._results_a[nid]).score,
                "name": self._results_a[nid].node_name,
            }
        return scores
