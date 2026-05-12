"""
RiskPulse — CentralityAnalyzer
================================
Rupture 3 : Détection des nœuds critiques CACHÉS
(entités non mentionnées explicitement mais centrales dans le réseau).

Métriques : PageRank + Betweenness + Closeness → score composite
3Regle     : Comparaison de deux approches algorithmiques
"""

import logging
from typing import Dict, List, Tuple
import networkx as nx

logger = logging.getLogger(__name__)


class CentralityAnalyzer:
    """
    Analyse la centralité de chaque nœud du graphe selon 3 métriques,
    puis calcule un score composite pour identifier les nœuds critiques.

    La rupture clé : révèle des nœuds qui ont un poids structurel fort
    même s'ils apparaissent peu dans le texte source.
    """

    def __init__(self, graph: nx.Graph, top_n: int = 5):
        self.G = graph
        self.top_n = top_n
        self.pagerank_scores: Dict[str, float] = {}
        self.betweenness_scores: Dict[str, float] = {}
        self.closeness_scores: Dict[str, float] = {}
        self.composite_scores: Dict[str, float] = {}
        self._analyzed = False

    # ── Analyse principale ────────────────────

    def analyze(self) -> dict:
        """
        Lance l'analyse complète de centralité.

        Returns:
            {
                "pagerank": dict,
                "betweenness": dict,
                "closeness": dict,
                "composite": dict,
                "critical_nodes": List[dict],
                "hidden_critical": List[dict],
            }
        """
        if self.G.number_of_nodes() == 0:
            logger.warning("Graphe vide — analyse de centralité ignorée")
            return self._empty_result()

        # ── Calcul des métriques ──
        self.pagerank_scores    = self._compute_pagerank()
        self.betweenness_scores = self._compute_betweenness()
        self.closeness_scores   = self._compute_closeness()
        self.composite_scores   = self._compute_composite()

        # ── Nœuds critiques ──
        critical_nodes  = self._get_top_nodes(self.composite_scores)
        hidden_critical = self._get_hidden_critical(critical_nodes)

        # ── Enrichit le graphe avec les scores ──
        self._annotate_graph()

        self._analyzed = True
        logger.info(f"Centralité analysée — {len(critical_nodes)} nœuds critiques identifiés")

        return {
            "pagerank":       self.pagerank_scores,
            "betweenness":    self.betweenness_scores,
            "closeness":      self.closeness_scores,
            "composite":      self.composite_scores,
            "critical_nodes": critical_nodes,
            "hidden_critical": hidden_critical,
        }

    # ── PageRank ──────────────────────────────

    def _compute_pagerank(self) -> Dict[str, float]:
        """
        PageRank : mesure l'influence globale d'un nœud.
        Un nœud avec un PageRank élevé est référencé par
        beaucoup d'autres nœuds importants.
        """
        try:
            # Utilise les poids des arêtes
            scores = nx.pagerank(
                self.G,
                alpha=0.85,           # facteur d'amortissement standard
                weight='weight',
                max_iter=200,
                tol=1e-6,
            )
            return self._normalize_scores(scores)
        except nx.PowerIterationFailedConvergence:
            logger.warning("PageRank n'a pas convergé — valeurs brutes utilisées")
            return self._normalize_scores(
                nx.pagerank(self.G, alpha=0.85, max_iter=50)
            )

    # ── Betweenness ───────────────────────────

    def _compute_betweenness(self) -> Dict[str, float]:
        """
        Betweenness Centrality : mesure le rôle de pont d'un nœud.
        Un nœud avec betweenness élevée est sur beaucoup de plus
        courts chemins entre d'autres paires de nœuds.
        → Révèle les "intermédiaires clés" du réseau.
        """
        try:
            scores = nx.betweenness_centrality(
                self.G,
                weight='weight',
                normalized=True,
            )
            return self._normalize_scores(scores)
        except Exception as e:
            logger.error(f"Erreur betweenness : {e}")
            return {node: 0.0 for node in self.G.nodes()}

    # ── Closeness ─────────────────────────────

    def _compute_closeness(self) -> Dict[str, float]:
        """
        Closeness Centrality : mesure la proximité moyenne
        d'un nœud à tous les autres.
        → Révèle les nœuds qui peuvent 'atteindre' tout le réseau rapidement.
        """
        try:
            scores = nx.closeness_centrality(self.G)
            return self._normalize_scores(scores)
        except Exception as e:
            logger.error(f"Erreur closeness : {e}")
            return {node: 0.0 for node in self.G.nodes()}

    # ── Score composite ───────────────────────

    def _compute_composite(self) -> Dict[str, float]:
        """
        Score composite pondéré des 3 métriques.

        Pondération :
          - PageRank    35% (influence globale)
          - Betweenness 45% (rôle de pont = criticité pour la propagation)
          - Closeness   20% (proximité réseau)

        Le betweenness est le plus important car c'est lui
        qui détermine la vitesse de propagation d'un risque.
        """
        composite = {}
        for node in self.G.nodes():
            pr = self.pagerank_scores.get(node, 0.0)
            bw = self.betweenness_scores.get(node, 0.0)
            cl = self.closeness_scores.get(node, 0.0)
            composite[node] = round(0.35 * pr + 0.45 * bw + 0.20 * cl, 4)

        return self._normalize_scores(composite)

    # ── Nœuds critiques ───────────────────────

    def _get_top_nodes(self, scores: Dict[str, float]) -> List[dict]:
        """Retourne les top N nœuds selon le score composite."""
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        result = []
        for node_id, score in sorted_nodes[:self.top_n]:
            node_data = self.G.nodes[node_id]
            result.append({
                "id":            node_id,
                "name":          node_data.get("label", node_id),
                "type":          node_data.get("type", "?"),
                "composite":     round(score, 4),
                "pagerank":      round(self.pagerank_scores.get(node_id, 0), 4),
                "betweenness":   round(self.betweenness_scores.get(node_id, 0), 4),
                "closeness":     round(self.closeness_scores.get(node_id, 0), 4),
                "frequency":     node_data.get("frequency", 1),
                "degree":        self.G.degree(node_id),
            })
        return result

    def _get_hidden_critical(self, critical_nodes: List[dict]) -> List[dict]:
        """
        Rupture 3 : identifie les nœuds critiques
        dont la fréquence dans le texte est faible (≤ 1)
        mais dont le score de centralité est élevé (≥ 0.5).

        Ce sont les entités CACHÉES — pas ou peu mentionnées explicitement,
        mais structurellement importantes dans le réseau.

        Note : on scanne TOUS les nœuds, pas seulement le top N,
        car un nœud caché peut très bien ne pas figurer dans le top.
        """
        hidden = []
        # Construction de la liste complète des nœuds avec scores
        all_nodes = []
        for nid, score in self.composite_scores.items():
            node_data = self.G.nodes[nid]
            all_nodes.append({
                "id":            nid,
                "name":          node_data.get("label", nid),
                "type":          node_data.get("type", "?"),
                "composite":     round(score, 4),
                "pagerank":      round(self.pagerank_scores.get(nid, 0), 4),
                "betweenness":   round(self.betweenness_scores.get(nid, 0), 4),
                "closeness":     round(self.closeness_scores.get(nid, 0), 4),
                "frequency":     node_data.get("frequency", 1),
                "degree":        self.G.degree(nid),
            })

        for node in all_nodes:
            if node["frequency"] <= 1 and node["composite"] >= 0.5:
                node_copy = dict(node)
                node_copy["reason"] = self._explain_why_critical(node)
                hidden.append(node_copy)

        # Trier par score décroissant
        hidden.sort(key=lambda x: x["composite"], reverse=True)
        return hidden[:10]  # Limiter à 10 pour l'affichage

    def _explain_why_critical(self, node: dict) -> str:
        """Génère une explication textuelle de la criticité d'un nœud."""
        reasons = []
        if node["betweenness"] >= 0.6:
            reasons.append("nœud pont entre plusieurs communautés")
        if node["pagerank"] >= 0.6:
            reasons.append("forte influence globale dans le réseau")
        if node["closeness"] >= 0.6:
            reasons.append("proximité maximale à toutes les entités")
        if node["degree"] >= 4:
            reasons.append(f"connecté à {node['degree']} autres entités")
        return "; ".join(reasons) if reasons else "centralité structurelle élevée"

    # ── Annotation du graphe ──────────────────

    def _annotate_graph(self):
        """Met à jour les attributs des nœuds du graphe avec les scores."""
        for node_id in self.G.nodes():
            self.G.nodes[node_id]['pagerank']   = round(self.pagerank_scores.get(node_id, 0), 4)
            self.G.nodes[node_id]['betweenness'] = round(self.betweenness_scores.get(node_id, 0), 4)
            self.G.nodes[node_id]['closeness']   = round(self.closeness_scores.get(node_id, 0), 4)
            self.G.nodes[node_id]['composite']   = round(self.composite_scores.get(node_id, 0), 4)
            # Taille proportionnelle au score composite
            base_size = self.G.nodes[node_id].get('size', 10)
            composite = self.composite_scores.get(node_id, 0)
            self.G.nodes[node_id]['size'] = int(base_size + composite * 20)

    # ── Utilitaires ───────────────────────────

    def _normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Normalise un dict de scores entre 0 et 1."""
        if not scores:
            return {}
        max_val = max(scores.values())
        min_val = min(scores.values())
        span = max_val - min_val
        if span == 0:
            return {k: 0.5 for k in scores}
        return {k: round((v - min_val) / span, 4) for k, v in scores.items()}

    def _empty_result(self) -> dict:
        return {
            "pagerank": {}, "betweenness": {}, "closeness": {},
            "composite": {}, "critical_nodes": [], "hidden_critical": [],
        }

    # ── Accès aux résultats ───────────────────

    def get_composite_scores(self) -> Dict[str, float]:
        return self.composite_scores

    def get_critical_nodes(self) -> List[dict]:
        if not self._analyzed:
            self.analyze()
        return self._get_top_nodes(self.composite_scores)

    def get_node_score(self, node_id: str) -> float:
        return self.composite_scores.get(node_id, 0.0)
