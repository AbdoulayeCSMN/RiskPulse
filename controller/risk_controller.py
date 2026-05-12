"""
RiskPulse — RiskController
============================
Orchestrateur principal : coordonne tous les moteurs IA.

Responsabilités :
  - Recevoir un texte brut depuis l'interface
  - Orchestrer le pipeline complet
  - Exposer des méthodes simples pour Tkinter et WinForms
  - Gérer le mode démo (scénarios simulés)
  - Journaliser toutes les opérations (Exi : journalisation obligatoire)

Exi : architecture logicielle claire — couche logique métier
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import networkx as nx
import numpy as np


class _NumpyJSONEncoder(json.JSONEncoder):
    """Encodeur JSON qui sait serialiser les types numpy (bool_, int64, float64, array)."""
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

from engines.nlp_engine import NLPEngine
from engines.centrality_analyzer import CentralityAnalyzer
from engines.models import ModelComparator
from engines.propagation_engine import PropagationEngine, STATE_COLORS

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  SCÉNARIOS DE DÉMONSTRATION
#  (Bakkas : mode démonstration obligatoire)
# ─────────────────────────────────────────────

DEMO_SCENARIOS = {
    "crise_financiere": {
        "title": "Crise Financière Fictive",
        "description": "Réseau de 7 entités financières interconnectées avec risque de contagion",
        "text": """
            La Banque Centrale a annoncé une baisse des taux d'intérêt suite aux difficultés 
            rencontrées par le Fonds Alpha Capital. Le Fonds Alpha Capital, principal partenaire 
            de la Banque Centrale, a été fortement exposé aux marchés émergents via son 
            partenariat avec InvestCorp Maroc. InvestCorp Maroc collabore également avec 
            TechVentures SA et FinTech Global pour ses opérations de crédit. 
            TechVentures SA est liée à DataBridge International par un accord de partage de données.
            DataBridge International alimente en données FinTech Global et InvestCorp Maroc.
            Le Directeur Ahmed Benali dirige à la fois le Fonds Alpha Capital et siège 
            au conseil d'administration de TechVentures SA.
            La Banque Centrale a investi 500 millions MAD dans ces structures interconnectées.
            FinTech Global a déclaré des pertes de 200 millions MAD liées à InvestCorp Maroc.
        """,
        "inject_node": "fonds_alpha_capital",
        "inject_intensity": 0.9,
    },
    "attaque_cyber": {
        "title": "Attaque Cybersécurité en Cascade",
        "description": "Propagation d'une cyberattaque à travers une infrastructure critique",
        "text": """
            Le Serveur Principal de la Direction Informatique a été compromis par un malware.
            La Direction Informatique gère l'accès au Système de Paie et au Système RH.
            Le Système de Paie est connecté à la Base de Données Financière.
            La Base de Données Financière est partagée avec le Service Comptabilité.
            Le Service Comptabilité utilise également le Portail Client externe.
            Le Portail Client est hébergé par le Prestataire CloudPro.
            CloudPro fournit aussi des services au Service Comptabilité et à la Direction Marketing.
            L'administrateur Mohamed Fassi a accès au Serveur Principal et à la Base de Données.
            La Direction Marketing est liée au Portail Client pour les campagnes digitales.
        """,
        "inject_node": "serveur_principal",
        "inject_intensity": 1.0,
    },
    "reseau_juridique": {
        "title": "Réseau de Conformité Juridique",
        "description": "Relations entre entités dans un litige commercial complexe",
        "text": """
            Le Cabinet Juridique Berrada représente la Société Holding SOMED dans un litige 
            contre FinanceCorp International. La Société Holding SOMED contrôle trois filiales :
            ImmoCorp Maroc, AgroTech Sud et Logistique Atlas.
            ImmoCorp Maroc a signé des contrats avec FinanceCorp International pour le financement 
            d'un projet immobilier. AgroTech Sud est liée à Logistique Atlas par un contrat 
            de transport et de distribution. Le Tribunal de Commerce de Casablanca supervise 
            le dossier impliquant le Cabinet Juridique Berrada et FinanceCorp International.
            Maître Salma Idrissi du Cabinet Juridique Berrada défend aussi AgroTech Sud 
            dans un contentieux séparé avec Logistique Atlas.
        """,
        "inject_node": "financecorp_international",
        "inject_intensity": 0.75,
    },
    "chaine_appro": {
        "title": "Chaîne d'Approvisionnement Sous Stress",
        "description": "Disruption d'une chaîne logistique internationale",
        "text": """
            Le Fournisseur Principal AsiaComponents a informé TransportHub Maroc 
            d'un retard de livraison de 6 semaines. TransportHub Maroc livre Usine Nord 
            et Usine Sud qui approvisionnent le Distributeur Central.
            Le Distributeur Central fournit 500 points de vente via LogiPartner.
            AsiaComponents dépend de RawMaterials Corp pour ses matières premières.
            RawMaterials Corp est également fournisseur de BackupSupplier Europe.
            BackupSupplier Europe peut potentiellement remplacer AsiaComponents 
            pour Usine Nord mais pas pour Usine Sud.
            Le Directeur Achats Karim Tahiri coordonne les relations entre 
            TransportHub Maroc et le Distributeur Central.
        """,
        "inject_node": "asiacomponents",
        "inject_intensity": 0.8,
    },
    "reseau_business": {
        "title": "Analyse Concurrentielle — Écosystème FinTech",
        "description": "Cartographie des acteurs d'un écosystème FinTech marocain",
        "text": """
            WafaCash et CashPlus sont les deux leaders du transfert d'argent au Maroc.
            WafaCash est une filiale du Groupe Attijariwafa Bank.
            CashPlus collaborate avec Banque Populaire pour son réseau d'agences.
            M2T Payment est une startup FinTech soutenue par CDG Invest.
            CDG Invest a également investi dans WafaCash et dans PayTech Maroc.
            PayTech Maroc développe une solution de paiement concurrente à M2T Payment.
            Bank Al-Maghrib régule l'ensemble des opérateurs : WafaCash, CashPlus, 
            M2T Payment et PayTech Maroc. L'Association Professionnelle des FinTech 
            regroupe M2T Payment, PayTech Maroc et CashPlus.
            Le PDG Mehdi Alaoui dirige à la fois PayTech Maroc et siège au conseil de M2T Payment.
        """,
        "inject_node": "cdg_invest",
        "inject_intensity": 0.6,
    },
}


# ─────────────────────────────────────────────
#  RISK CONTROLLER
# ─────────────────────────────────────────────

class RiskController:
    """
    Orchestrateur principal de RiskPulse.
    Point d'entrée unique pour Tkinter et WinForms.
    """

    def __init__(self, language: str = "fr", output_dir: str = "data/exports"):
        self.language = language
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # ── Moteurs IA ──
        self.nlp_engine = NLPEngine(language=language)
        self.comparator = ModelComparator()
        self.propagation_engine: Optional[PropagationEngine] = None
        self.centrality_analyzer: Optional[CentralityAnalyzer] = None

        # ── État courant ──
        self.current_graph: Optional[nx.Graph] = None
        self.current_entities: dict = {}
        self.current_analysis: dict = {}
        self.operation_log: List[dict] = []

        # ── Chargement du modèle NLP ──
        self._nlp_ready = self.nlp_engine.load_model()
        self._log("init", f"RiskController initialisé — NLP: {'prêt' if self._nlp_ready else 'fallback regex'}")

    # ──────────────────────────────────────────
    #  PIPELINE COMPLET
    # ──────────────────────────────────────────

    def analyze_text(self, text: str) -> dict:
        """
        Pipeline complet : texte brut → résultats complets.

        Étapes :
          1. NLP → extraction entités + relations + graphe
          2. Centralité → nœuds critiques cachés
          3. Comparaison modèles A vs B
          4. Préparation du moteur de propagation

        Returns: dict complet avec toutes les données pour l'interface
        """
        self._log("analyze", f"Analyse démarrée ({len(text)} caractères)")
        start = time.time()

        # ── Étape 1 : NLP ──
        nlp_result = self.nlp_engine.process(text)
        self.current_graph = nlp_result["graph"]
        self.current_entities = {e["id"]: e for e in nlp_result["entities"]}

        if self.current_graph.number_of_nodes() < 2:
            return {"error": "Pas assez d'entités détectées. Essayez un texte plus long."}

        # ── Étape 2 : Centralité ──
        self.centrality_analyzer = CentralityAnalyzer(self.current_graph)
        centrality_result = self.centrality_analyzer.analyze()

        # ── Étape 3 : Comparaison modèles ──
        comparison_result = self.comparator.run_both(self.current_graph)

        # ── Étape 4 : Initialisation propagation ──
        self.propagation_engine = PropagationEngine(self.current_graph)

        total_time = round(time.time() - start, 3)

        self.current_analysis = {
            "timestamp":   datetime.now().isoformat(),
            "nlp":         nlp_result,
            "centrality":  centrality_result,
            "comparison":  comparison_result,
            "stats":       nlp_result["stats"],
            "total_time":  total_time,
            "text_length": len(text),
        }

        self._log("analyze", f"Analyse terminée en {total_time}s — "
                             f"{nlp_result['stats'].get('nb_entities', 0)} entités, "
                             f"{nlp_result['stats'].get('nb_relations', 0)} relations")

        return self.current_analysis

    # ──────────────────────────────────────────
    #  PROPAGATION (Rupture 2)
    # ──────────────────────────────────────────

    def run_propagation(
        self,
        source_node: str,
        intensity: float = 0.8,
        speed: float = 1.0,
    ) -> dict:
        """Lance la simulation de propagation."""
        if not self.propagation_engine:
            return {"error": "Veuillez d'abord analyser un texte."}

        self._log("propagation", f"Propagation depuis '{source_node}' (intensité={intensity})")

        result = self.propagation_engine.propagate(source_node, intensity, speed)
        result_dict = result.to_dict()

        # Enrichit avec les noms lisibles
        result_dict["node_names"] = {
            nid: self.current_graph.nodes[nid].get("label", nid)
            for nid in result.final_risk_levels
            if nid in self.current_graph.nodes()
        }
        result_dict["state_colors"] = {k.value: v for k, v in STATE_COLORS.items()}

        return result_dict

    # ──────────────────────────────────────────
    #  CONTREFACTUELS (Rupture 5)
    # ──────────────────────────────────────────

    def run_counterfactual_remove(
        self,
        source_node: str,
        intensity: float,
        node_u: str,
        node_v: str,
    ) -> dict:
        """Simulation contrefactuelle : suppression d'un lien."""
        if not self.propagation_engine:
            return {"error": "Veuillez d'abord analyser un texte."}
        self._log("counterfactual", f"Suppression du lien {node_u}↔{node_v}")
        return self.propagation_engine.counterfactual_remove_edge(
            source_node, intensity, (node_u, node_v)
        )

    def run_counterfactual_add(
        self,
        source_node: str,
        intensity: float,
        node_u: str,
        node_v: str,
        weight: float = 0.5,
    ) -> dict:
        """Simulation contrefactuelle : ajout d'un lien."""
        if not self.propagation_engine:
            return {"error": "Veuillez d'abord analyser un texte."}
        self._log("counterfactual", f"Ajout du lien {node_u}↔{node_v} (poids={weight})")
        return self.propagation_engine.counterfactual_add_edge(
            source_node, intensity, (node_u, node_v), weight
        )

    # ──────────────────────────────────────────
    #  MODE DÉMO (Bakkas obligatoire)
    # ──────────────────────────────────────────

    def load_demo_scenario(self, scenario_key: str) -> dict:
        """
        Charge et analyse un scénario de démonstration.
        Bakkas : mode démonstration avec données simulées.
        """
        if scenario_key not in DEMO_SCENARIOS:
            return {"error": f"Scénario inconnu : {scenario_key}. "
                             f"Disponibles : {list(DEMO_SCENARIOS.keys())}"}

        scenario = DEMO_SCENARIOS[scenario_key]
        self._log("demo", f"Chargement scénario : {scenario['title']}")

        # Analyse du texte du scénario
        analysis = self.analyze_text(scenario["text"])
        if "error" in analysis:
            return analysis

        # Lance automatiquement la propagation recommandée
        # (cherche le nœud source le plus proche du mot-clé)
        source_node = self._find_best_source_node(scenario.get("inject_node", ""))
        intensity   = scenario.get("inject_intensity", 0.8)

        propagation = {}
        if source_node:
            propagation = self.run_propagation(source_node, intensity)

        return {
            "scenario":    scenario_key,
            "title":       scenario["title"],
            "description": scenario["description"],
            "analysis":    analysis,
            "propagation": propagation,
            "source_node": source_node,
            "intensity":   intensity,
        }

    def _find_best_source_node(self, keyword: str) -> Optional[str]:
        """Trouve le nœud dont l'ID ou le nom correspond le mieux au mot-clé."""
        if not self.current_graph or not keyword:
            return None
        keyword = keyword.lower().replace("_", " ")
        best, best_score = None, 0
        for nid in self.current_graph.nodes():
            label = self.current_graph.nodes[nid].get("label", "").lower()
            score = sum(1 for word in keyword.split() if word in label or word in nid.lower())
            if score > best_score:
                best, best_score = nid, score
        return best

    def get_demo_scenarios(self) -> List[dict]:
        """Retourne la liste des scénarios disponibles (pour le menu UI)."""
        return [
            {"key": k, "title": v["title"], "description": v["description"]}
            for k, v in DEMO_SCENARIOS.items()
        ]

    # ──────────────────────────────────────────
    #  EXPORT / IMPORT (Exi obligatoire)
    # ──────────────────────────────────────────

    def export_analysis_json(self, filename: Optional[str] = None) -> str:
        """Exporte l'analyse courante en JSON."""
        if not self.current_analysis:
            return ""
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_{ts}.json"
        path = self.output_dir / filename

        export_data = {
            "riskpulse_version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "entities": list(self.current_entities.values()),
            "stats": self.current_analysis.get("stats", {}),
            "centrality": {
                "critical_nodes": self.current_analysis.get("centrality", {}).get("critical_nodes", []),
                "hidden_critical": self.current_analysis.get("centrality", {}).get("hidden_critical", []),
            },
            "comparison_summary": self.current_analysis.get("comparison", {}).get("comparison", {}),
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, cls=_NumpyJSONEncoder)

        self._log("export", f"JSON exporté : {path}")
        return str(path)

    def export_graph_json(self, filename: Optional[str] = None) -> str:
        """Exporte le graphe au format JSON (pour WinForms et visualisation externe)."""
        if not self.current_graph:
            return ""
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"graph_{ts}.json"
        path = self.output_dir / filename
        graph_data = self.nlp_engine.export_graph_json()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2, cls=_NumpyJSONEncoder)
        self._log("export", f"Graphe JSON exporté : {path}")
        return str(path)

    def import_text_file(self, filepath: str) -> str:
        """Importe un fichier texte (TXT). Pour PDF, utiliser le module séparé."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        self._log("import", f"Fichier importé : {filepath} ({len(content)} chars)")
        return content

    # ──────────────────────────────────────────
    #  DASHBOARD (Exi obligatoire)
    # ──────────────────────────────────────────

    def get_dashboard_data(self) -> dict:
        """
        Retourne toutes les métriques pour le dashboard.
        Bakkas : nb données, taux erreur, temps, courbes.
        """
        if not self.current_analysis:
            return {"error": "Aucune analyse disponible."}

        stats  = self.current_analysis.get("stats", {})
        comp   = self.current_analysis.get("comparison", {})
        cent   = self.current_analysis.get("centrality", {})

        return {
            # Métriques réseau
            "nb_entities":      stats.get("nb_entities", 0),
            "nb_relations":     stats.get("nb_relations", 0),
            "graph_density":    stats.get("density", 0),
            "nb_components":    stats.get("nb_components", 0),
            "avg_degree":       stats.get("avg_degree", 0),
            "processing_time":  self.current_analysis.get("total_time", 0),

            # Métriques IA
            "model_a_anomalies": comp.get("comparison", {}).get("n_anomalies_a", 0),
            "model_b_anomalies": comp.get("comparison", {}).get("n_anomalies_b", 0),
            "agreement_rate":    comp.get("comparison", {}).get("agreement_rate", 0),
            "key_insight":       comp.get("comparison", {}).get("key_insight", ""),

            # Nœuds critiques
            "critical_nodes":   cent.get("critical_nodes", [])[:5],
            "hidden_critical":  cent.get("hidden_critical", []),

            # Scores pour graphiques
            "all_scores":        self.comparator.get_all_scores(),
            "entity_types":      stats.get("entity_types", {}),

            # Log des opérations
            "operation_log":     self.operation_log[-20:],
        }

    # ──────────────────────────────────────────
    #  PARAMÉTRAGE IA (Exi obligatoire)
    # ──────────────────────────────────────────

    def set_model_params(self, params: dict):
        """
        Paramétrage dynamique des modèles IA.
        Gestion des paramètres IA obligatoire.
        """
        if "contamination" in params:
            self.comparator.model_a.contamination = float(params["contamination"])
        if "n_estimators" in params:
            self.comparator.model_a.n_estimators = int(params["n_estimators"])
        if "decay" in params and self.propagation_engine:
            self.propagation_engine.set_decay(float(params["decay"]))
        if "max_steps" in params and self.propagation_engine:
            self.propagation_engine.set_max_steps(int(params["max_steps"]))
        if "top_n_critical" in params and self.centrality_analyzer:
            self.centrality_analyzer.top_n = int(params["top_n_critical"])
        if "language" in params:
            self.language = params["language"]
            self.nlp_engine = NLPEngine(language=params["language"])
            self.nlp_engine.load_model()
        self._log("params", f"Paramètres IA mis à jour : {params}")

    # ──────────────────────────────────────────
    #  JOURNALISATION (Exi obligatoire)
    # ──────────────────────────────────────────

    def _log(self, operation: str, message: str):
        """Journalise toutes les opérations."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "message":   message,
        }
        self.operation_log.append(entry)
        logger.info(f"[{operation.upper()}] {message}")

    def save_log(self, filepath: Optional[str] = None) -> str:
        """Sauvegarde le journal des opérations."""
        if not filepath:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(self.output_dir / f"log_{ts}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.operation_log, f, ensure_ascii=False, indent=2, cls=_NumpyJSONEncoder)
        return filepath

    # ──────────────────────────────────────────
    #  ACCÈS DIRECT (pour WinForms)
    # ──────────────────────────────────────────

    def get_graph(self) -> Optional[nx.Graph]:
        return self.current_graph

    def get_entities(self) -> dict:
        return self.current_entities

    def get_node_list(self) -> List[dict]:
        """Liste des nœuds pour les combobox de l'interface."""
        if not self.current_graph:
            return []
        return [
            {
                "id":    nid,
                "label": self.current_graph.nodes[nid].get("label", nid),
                "type":  self.current_graph.nodes[nid].get("type", "?"),
            }
            for nid in self.current_graph.nodes()
        ]

    def get_edge_list(self) -> List[dict]:
        """Liste des arêtes pour les contrefactuels."""
        if not self.current_graph:
            return []
        return [
            {
                "u":      u,
                "v":      v,
                "label":  f"{self.current_graph.nodes[u].get('label', u)} ↔ "
                          f"{self.current_graph.nodes[v].get('label', v)}",
                "weight": round(self.current_graph[u][v].get("weight", 1.0), 2),
            }
            for u, v in self.current_graph.edges()
        ]
