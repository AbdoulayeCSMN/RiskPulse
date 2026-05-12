"""
RiskPulse — PropagationEngine
===============================
Rupture 2 : Simulation de propagation de risque en temps réel
            sur un graphe de connaissances pondéré.

Rupture 5 : Simulations contrefactuelles (modifier le graphe
            et observer l'impact sur la propagation).

Algorithme : SIR adapté (Susceptible → Infected → Recovered)
             modifié pour graphes pondérés et risques continus.

4Regle : moteur IA principal — composant simulation
"""

import time
import copy
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  ÉTATS DE PROPAGATION
# ─────────────────────────────────────────────

class NodeState(Enum):
    SAFE     = "safe"      # 🟢 Sain — non exposé
    EXPOSED  = "exposed"   # 🟡 Exposé — faiblement affecté
    INFECTED = "infected"  # 🟠 Infecté — modérément risqué
    CRITICAL = "critical"  # 🔴 Critique — fortement risqué


# Seuils de transition entre états
STATE_THRESHOLDS = {
    NodeState.SAFE:     (0.00, 0.25),
    NodeState.EXPOSED:  (0.25, 0.50),
    NodeState.INFECTED: (0.50, 0.75),
    NodeState.CRITICAL: (0.75, 1.01),
}

# Couleurs associées (pour la visualisation)
STATE_COLORS = {
    NodeState.SAFE:     "#2ecc71",   # vert
    NodeState.EXPOSED:  "#f1c40f",   # jaune
    NodeState.INFECTED: "#e67e22",   # orange
    NodeState.CRITICAL: "#e74c3c",   # rouge
}


def risk_to_state(risk: float) -> NodeState:
    for state, (low, high) in STATE_THRESHOLDS.items():
        if low <= risk < high:
            return state
    return NodeState.CRITICAL


@dataclass
class PropagationStep:
    """Capture l'état du réseau à un instant T de la simulation."""
    step: int
    risk_levels: Dict[str, float]   # node_id → niveau de risque [0, 1]
    newly_infected: List[str]       # nœuds qui ont changé d'état ce step
    total_infected: int
    max_risk: float

    def to_dict(self) -> dict:
        return {
            "step":             self.step,
            "risk_levels":      {k: round(v, 4) for k, v in self.risk_levels.items()},
            "newly_infected":   self.newly_infected,
            "total_infected":   self.total_infected,
            "max_risk":         round(self.max_risk, 4),
        }


@dataclass
class PropagationResult:
    """Résultat complet d'une simulation."""
    source_node: str
    initial_intensity: float
    steps: List[PropagationStep] = field(default_factory=list)
    final_risk_levels: Dict[str, float] = field(default_factory=dict)
    converged: bool = False
    n_steps: int = 0
    simulation_time: float = 0.0

    def get_heatmap(self) -> Dict[str, float]:
        """Retourne le niveau de risque final pour chaque nœud."""
        return self.final_risk_levels

    def get_states(self) -> Dict[str, NodeState]:
        return {nid: risk_to_state(r) for nid, r in self.final_risk_levels.items()}

    def to_dict(self) -> dict:
        return {
            "source_node":       self.source_node,
            "initial_intensity": self.initial_intensity,
            "n_steps":           self.n_steps,
            "converged":         self.converged,
            "simulation_time":   self.simulation_time,
            "final_risk":        {k: round(v, 4) for k, v in self.final_risk_levels.items()},
            "steps":             [s.to_dict() for s in self.steps],
            "summary":           self._summary(),
        }

    def _summary(self) -> dict:
        states = self.get_states()
        return {
            "critical": sum(1 for s in states.values() if s == NodeState.CRITICAL),
            "infected": sum(1 for s in states.values() if s == NodeState.INFECTED),
            "exposed":  sum(1 for s in states.values() if s == NodeState.EXPOSED),
            "safe":     sum(1 for s in states.values() if s == NodeState.SAFE),
        }


# ─────────────────────────────────────────────
#  PROPAGATION ENGINE
# ─────────────────────────────────────────────

class PropagationEngine:
    """
    Moteur de simulation de propagation de risque.

    Algorithme SIR adapté aux graphes pondérés :
    - Le risque se propage depuis un nœud source
    - La transmission est proportionnelle au poids de l'arête
    - L'atténuation dépend de la distance et du coefficient d'amortissement
    - La simulation s'arrête quand le réseau converge (delta < seuil)

    Rupture 2 : visualisation animée étape par étape
    Rupture 5 : contrefactuels — modifier le graphe et relancer
    """

    DEFAULT_DECAY       = 0.3    # Atténuation par saut
    DEFAULT_MAX_STEPS   = 50
    DEFAULT_CONVERGENCE = 0.001  # Delta min pour arrêt

    def __init__(
        self,
        graph: nx.Graph,
        decay: float = DEFAULT_DECAY,
        max_steps: int = DEFAULT_MAX_STEPS,
        convergence_threshold: float = DEFAULT_CONVERGENCE,
        step_callback: Optional[Callable] = None,
    ):
        self.original_graph = graph
        self.graph = copy.deepcopy(graph)   # copie de travail
        self.decay = decay
        self.max_steps = max_steps
        self.convergence_threshold = convergence_threshold
        self.step_callback = step_callback  # appelé à chaque step (pour l'animation Tkinter)
        self.last_result: Optional[PropagationResult] = None

    # ── Simulation principale ─────────────────

    def propagate(
        self,
        source_node: str,
        intensity: float = 1.0,
        speed: float = 1.0,
    ) -> PropagationResult:
        """
        Lance la simulation de propagation depuis un nœud source.

        Args:
            source_node : nœud d'injection du risque
            intensity   : niveau initial du risque [0, 1]
            speed       : vitesse de propagation (pour l'animation)

        Returns:
            PropagationResult avec l'historique complet
        """
        start = time.time()

        if source_node not in self.graph.nodes():
            raise ValueError(f"Nœud source inconnu : {source_node}")

        intensity = max(0.0, min(1.0, intensity))

        # Initialisation des niveaux de risque
        risk_levels: Dict[str, float] = {
            node: 0.0 for node in self.graph.nodes()
        }
        risk_levels[source_node] = intensity

        result = PropagationResult(
            source_node=source_node,
            initial_intensity=intensity,
        )

        prev_levels = None
        step = 0

        for step in range(self.max_steps):
            new_levels = self._propagate_step(risk_levels, speed)
            newly_infected = self._detect_newly_infected(risk_levels, new_levels)

            snap = PropagationStep(
                step=step + 1,
                risk_levels=dict(new_levels),
                newly_infected=newly_infected,
                total_infected=sum(1 for v in new_levels.values() if v >= 0.5),
                max_risk=max(new_levels.values()),
            )
            result.steps.append(snap)

            # Callback pour animation temps réel (Tkinter)
            if self.step_callback:
                self.step_callback(snap)

            # Test de convergence
            if prev_levels is not None:
                delta = max(abs(new_levels[n] - prev_levels[n]) for n in new_levels)
                if delta < self.convergence_threshold:
                    result.converged = True
                    break

            prev_levels = dict(new_levels)
            risk_levels = new_levels

        result.final_risk_levels = risk_levels
        result.n_steps = step + 1
        result.simulation_time = round(time.time() - start, 4)

        # Annote le graphe avec les niveaux finaux
        self._annotate_graph(risk_levels)

        self.last_result = result
        logger.info(
            f"Propagation terminée : {step+1} étapes, "
            f"{'convergée' if result.converged else 'max atteint'}, "
            f"{result._summary()}"
        )
        return result

    # ── Étape de propagation ──────────────────

    def _propagate_step(
        self,
        risk_levels: Dict[str, float],
        speed: float = 1.0,
    ) -> Dict[str, float]:
        """
        Calcule les nouveaux niveaux de risque après une étape.

        Pour chaque nœud :
        - Reçoit la MOYENNE pondérée du risque de ses voisins (pas la somme)
        - L'amortissement décay réduit progressivement la transmission
        - Le risque ne peut que croître (irréversibilité)
        - Plafonnement à 1.0 pour éviter la saturation
        """
        new_levels: Dict[str, float] = {}

        for node in self.graph.nodes():
            current_risk = risk_levels.get(node, 0.0)

            neighbors = list(self.graph.neighbors(node))
            if neighbors:
                total_weight = 0.0
                weighted_risk = 0.0
                for neighbor in neighbors:
                    edge_weight = self.graph[node][neighbor].get(
                        'weight_norm',
                        self.graph[node][neighbor].get('weight', 1.0)
                    )
                    edge_weight = max(0.0, min(edge_weight, 1.0))
                    total_weight += edge_weight
                    weighted_risk += risk_levels.get(neighbor, 0.0) * edge_weight

                # Risque moyen pondéré reçu des voisins
                avg_neighbor_risk = weighted_risk / total_weight if total_weight > 0 else 0
                # Transmission attenuee par decay et speed
                transmission = avg_neighbor_risk * speed * (1.0 - self.decay)
            else:
                transmission = 0.0

            # Le risque accumulé ne peut que croître; on prend le max
            new_risk = max(current_risk, transmission)
            new_levels[node] = round(min(new_risk, 1.0), 6)

        return new_levels

    def _detect_newly_infected(
        self,
        old_levels: Dict[str, float],
        new_levels: Dict[str, float],
    ) -> List[str]:
        """Détecte les nœuds qui ont franchi le seuil d'infection ce step."""
        newly = []
        for node in new_levels:
            old_state = risk_to_state(old_levels.get(node, 0))
            new_state = risk_to_state(new_levels.get(node, 0))
            if new_state != old_state and new_state in (NodeState.INFECTED, NodeState.CRITICAL):
                newly.append(node)
        return newly

    def _annotate_graph(self, risk_levels: Dict[str, float]):
        """Met à jour les attributs de visualisation du graphe."""
        for node_id, risk in risk_levels.items():
            if node_id in self.graph.nodes():
                state = risk_to_state(risk)
                self.graph.nodes[node_id]['risk_propagated'] = risk
                self.graph.nodes[node_id]['state'] = state.value
                self.graph.nodes[node_id]['color'] = STATE_COLORS[state]

    # ── Contrefactuels (Rupture 5) ────────────

    def counterfactual_remove_edge(
        self,
        source_node: str,
        intensity: float,
        edge_to_remove: tuple,
    ) -> dict:
        """
        Rupture 5 : Simule la propagation SANS une arête spécifique.
        "Que se passerait-il si ce lien n'existait pas ?"

        Retourne la comparaison avant/après suppression.
        """
        u, v = edge_to_remove

        # Simulation avec l'arête
        self.graph = copy.deepcopy(self.original_graph)
        result_before = self.propagate(source_node, intensity)

        # Suppression de l'arête + simulation
        self.graph = copy.deepcopy(self.original_graph)
        if self.graph.has_edge(u, v):
            self.graph.remove_edge(u, v)
        result_after = self.propagate(source_node, intensity)

        # Comparaison
        impact = self._compare_results(result_before, result_after)

        # Remet le graphe original
        self.graph = copy.deepcopy(self.original_graph)

        return {
            "action":        f"Suppression du lien {u} ↔ {v}",
            "before":        result_before.get_heatmap(),
            "after":         result_after.get_heatmap(),
            "impact":        impact,
            "interpretation": self._interpret_impact(impact),
        }

    def counterfactual_add_edge(
        self,
        source_node: str,
        intensity: float,
        new_edge: tuple,
        weight: float = 0.5,
    ) -> dict:
        """
        Rupture 5 : Simule la propagation AVEC un nouveau lien.
        "Que se passerait-il si ce nouveau partenariat existait ?"
        """
        u, v = new_edge

        # Simulation sans le nouveau lien
        self.graph = copy.deepcopy(self.original_graph)
        result_before = self.propagate(source_node, intensity)

        # Ajout du lien + simulation
        self.graph = copy.deepcopy(self.original_graph)
        self.graph.add_edge(u, v, weight=weight, weight_norm=weight)
        result_after = self.propagate(source_node, intensity)

        impact = self._compare_results(result_before, result_after)
        self.graph = copy.deepcopy(self.original_graph)

        return {
            "action":         f"Ajout du lien {u} ↔ {v} (poids={weight})",
            "before":         result_before.get_heatmap(),
            "after":          result_after.get_heatmap(),
            "impact":         impact,
            "interpretation": self._interpret_impact(impact),
        }

    def _compare_results(
        self,
        before: PropagationResult,
        after: PropagationResult,
    ) -> dict:
        """Compare deux résultats de propagation."""
        before_map = before.get_heatmap()
        after_map  = after.get_heatmap()

        deltas = {}
        improved = []   # nœuds moins risqués après modification
        worsened = []   # nœuds plus risqués après modification

        for node in before_map:
            delta = after_map.get(node, 0) - before_map.get(node, 0)
            deltas[node] = round(delta, 4)
            if delta < -0.1:
                improved.append(node)
            elif delta > 0.1:
                worsened.append(node)

        avg_risk_before = np.mean(list(before_map.values()))
        avg_risk_after  = np.mean(list(after_map.values()))

        return {
            "deltas":           deltas,
            "improved_nodes":   improved,
            "worsened_nodes":   worsened,
            "avg_risk_before":  round(avg_risk_before, 4),
            "avg_risk_after":   round(avg_risk_after, 4),
            "avg_risk_delta":   round(avg_risk_after - avg_risk_before, 4),
            "n_steps_before":   before.n_steps,
            "n_steps_after":    after.n_steps,
        }

    def _interpret_impact(self, impact: dict) -> str:
        delta = impact["avg_risk_delta"]
        improved = len(impact["improved_nodes"])
        worsened = len(impact["worsened_nodes"])

        if delta < -0.05:
            return (f"Cette modification RÉDUIT le risque moyen de {abs(delta):.1%}. "
                    f"{improved} entité(s) sont moins exposées.")
        elif delta > 0.05:
            return (f"Cette modification AUGMENTE le risque moyen de {delta:.1%}. "
                    f"{worsened} entité(s) supplémentaire(s) sont exposées.")
        else:
            return "Cette modification a un impact neutre sur la propagation globale."

    # ── Paramétrage ───────────────────────────

    def set_decay(self, decay: float):
        self.decay = max(0.0, min(1.0, decay))

    def set_max_steps(self, max_steps: int):
        self.max_steps = max(1, max_steps)

    def reset_graph(self):
        """Remet le graphe dans son état original."""
        self.graph = copy.deepcopy(self.original_graph)

    def get_last_result(self) -> Optional[PropagationResult]:
        return self.last_result

    def get_annotated_graph(self) -> nx.Graph:
        return self.graph

    def get_node_states(self) -> Dict[str, str]:
        """Retourne les états actuels de chaque nœud (pour la visualisation)."""
        if not self.last_result:
            return {}
        return {
            nid: risk_to_state(risk).value
            for nid, risk in self.last_result.final_risk_levels.items()
        }
