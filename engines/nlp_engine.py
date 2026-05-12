"""
RiskPulse — NLPEngine
=====================
Rupture 1 : Extraction automatique d'entités et de relations
depuis du texte brut, puis construction d'un graphe de connaissances.

Technologie : spaCy NER + NetworkX
Auteur      : RiskPulse Team
1Regle      : Moteur IA principal — composant NLP
"""

import re
import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

import networkx as nx

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  TYPES DE DONNÉES
# ─────────────────────────────────────────────

ENTITY_TYPES = {
    "PER":  "Personne",
    "ORG":  "Organisation",
    "GPE":  "Lieu / Pays",
    "LOC":  "Lieu",
    "MONEY": "Montant",
    "DATE": "Date",
    "PERCENT": "Pourcentage",
    "MISC": "Autre",
    # fallback pour les labels spaCy en anglais
    "PERSON": "Personne",
    "NORP":   "Groupe",
    "FAC":    "Infrastructure",
    "PRODUCT": "Produit",
    "EVENT":  "Événement",
    "WORK_OF_ART": "Œuvre",
    "LAW":    "Loi",
    "LANGUAGE": "Langue",
    "CARDINAL": "Nombre",
    "ORDINAL": "Ordinal",
    "QUANTITY": "Quantité",
}

# Couleurs par type d'entité pour la visualisation
ENTITY_COLORS = {
    "Personne":       "#e74c3c",
    "Organisation":   "#3498db",
    "Lieu / Pays":    "#2ecc71",
    "Lieu":           "#27ae60",
    "Montant":        "#f39c12",
    "Date":           "#9b59b6",
    "Pourcentage":    "#e67e22",
    "Groupe":         "#1abc9c",
    "Produit":        "#d35400",
    "Autre":          "#95a5a6",
}


@dataclass
class Entity:
    """Représente une entité extraite du texte."""
    id: str
    name: str
    type_raw: str          # Label brut spaCy (PER, ORG…)
    type_label: str        # Label lisible
    frequency: int = 1
    risk_score: float = 0.0
    mentions: List[str] = field(default_factory=list)

    @property
    def color(self) -> str:
        return ENTITY_COLORS.get(self.type_label, "#95a5a6")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type_raw": self.type_raw,
            "type_label": self.type_label,
            "frequency": self.frequency,
            "risk_score": self.risk_score,
            "color": self.color,
        }


@dataclass
class Relation:
    """Représente une relation entre deux entités."""
    source_id: str
    target_id: str
    weight: float = 1.0
    sentence: str = ""

    def to_dict(self) -> dict:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "weight": self.weight,
        }


# ─────────────────────────────────────────────
#  NLPEngine
# ─────────────────────────────────────────────

class NLPEngine:
    """
    Moteur NLP principal de RiskPulse.

    Flux :
        texte brut
            → détection langue
            → extraction entités nommées (spaCy NER)
            → résolution de coréférence simplifiée
            → extraction relations (co-occurrence dans une phrase)
            → construction graphe NetworkX pondéré
    """

    # Modèles spaCy disponibles par langue
    SPACY_MODELS = {
        "fr": "fr_core_news_sm",
        "en": "en_core_web_sm",
    }

    def __init__(self, language: str = "fr"):
        self.language = language
        self._nlp = None
        self._load_start = None
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self.graph: nx.Graph = nx.Graph()
        self.processing_time: float = 0.0

    # ── Chargement du modèle ──────────────────

    def load_model(self) -> bool:
        """
        Charge le modèle spaCy.
        Retourne True si succès, False si le modèle n'est pas installé.
        """
        try:
            import spacy
            model_name = self.SPACY_MODELS.get(self.language, "en_core_web_sm")
            self._nlp = spacy.load(model_name)
            logger.info(f"Modèle spaCy chargé : {model_name}")
            return True
        except ImportError:
            logger.warning("spaCy non installé — mode fallback regex activé")
            return False
        except OSError:
            logger.warning(f"Modèle spaCy non trouvé — mode fallback regex activé")
            return False

    def is_ready(self) -> bool:
        return self._nlp is not None

    # ── Pipeline principal ────────────────────

    def process(self, text: str) -> dict:
        """
        Pipeline complet : texte → graphe.

        Returns:
            {
                "entities": List[dict],
                "relations": List[dict],
                "graph": nx.Graph,
                "stats": dict,
                "processing_time": float
            }
        """
        start = time.time()
        self.entities = {}
        self.relations = []

        # Nettoyage du texte
        clean_text = self._clean_text(text)

        # Extraction selon disponibilité de spaCy
        if self.is_ready():
            self._extract_with_spacy(clean_text)
        else:
            self._extract_with_regex(clean_text)

        # Construction du graphe
        self.graph = self._build_graph()

        self.processing_time = round(time.time() - start, 3)

        return {
            "entities": [e.to_dict() for e in self.entities.values()],
            "relations": [r.to_dict() for r in self.relations],
            "graph": self.graph,
            "stats": self._compute_stats(),
            "processing_time": self.processing_time,
        }

    # ── Nettoyage ─────────────────────────────

    def _clean_text(self, text: str) -> str:
        """Supprime les caractères parasites, normalise les espaces."""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\'\"àâäéèêëîïôùûüçÀÂÄÉÈÊËÎÏÔÙÛÜÇ]', ' ', text)
        return text.strip()

    # ── Extraction spaCy ──────────────────────

    def _extract_with_spacy(self, text: str):
        """Extraction NER avec spaCy + co-occurrence pour les relations."""
        doc = self._nlp(text)

        # 1. Extraction des entités par phrase
        sentences = list(doc.sents)
        for sent in sentences:
            ents_in_sent = []
            for ent in sent.ents:
                if self._is_valid_entity(ent.text, ent.label_):
                    entity = self._register_entity(ent.text, ent.label_, str(sent))
                    ents_in_sent.append(entity.id)

            # 2. Relations par co-occurrence dans la même phrase
            self._add_cooccurrence_relations(ents_in_sent, str(sent))

    def _is_valid_entity(self, name: str, label: str) -> bool:
        """Filtre les entités non pertinentes (trop courtes, nombres purs…)."""
        name = name.strip()
        if len(name) < 2:
            return False
        if name.isdigit():
            return False
        if label in ("CARDINAL", "ORDINAL", "QUANTITY", "DATE", "TIME"):
            return False
        return True

    def _register_entity(self, name: str, label: str, sentence: str) -> Entity:
        """Enregistre ou met à jour une entité (résolution de coréférence simple)."""
        # Normalisation du nom
        normalized = self._normalize_name(name)
        entity_id = self._make_id(normalized)

        # Recherche d'une entité existante similaire
        existing_id = self._find_similar_entity(normalized)
        if existing_id:
            self.entities[existing_id].frequency += 1
            self.entities[existing_id].mentions.append(name)
            return self.entities[existing_id]

        # Nouvelle entité
        type_label = ENTITY_TYPES.get(label, "Autre")
        entity = Entity(
            id=entity_id,
            name=normalized,
            type_raw=label,
            type_label=type_label,
            frequency=1,
            mentions=[name],
        )
        self.entities[entity_id] = entity
        return entity

    def _normalize_name(self, name: str) -> str:
        """Normalise le nom d'une entité."""
        # Supprime les articles en début
        name = re.sub(r'^(la |le |les |l\'|un |une |des )', '', name, flags=re.IGNORECASE)
        return name.strip().title()

    def _make_id(self, name: str) -> str:
        """Crée un identifiant propre depuis un nom."""
        return re.sub(r'[^a-z0-9_]', '_', name.lower())[:40]

    def _find_similar_entity(self, name: str) -> Optional[str]:
        """
        Coréférence simple : cherche une entité existante
        dont le nom est contenu dans ou contient le nouveau nom.
        """
        name_lower = name.lower()
        for eid, entity in self.entities.items():
            existing_lower = entity.name.lower()
            # Correspondance exacte ou inclusion
            if existing_lower == name_lower:
                return eid
            if len(name_lower) > 4 and (
                name_lower in existing_lower or existing_lower in name_lower
            ):
                return eid
        return None

    # ── Relations ─────────────────────────────

    def _add_cooccurrence_relations(self, entity_ids: List[str], sentence: str):
        """
        Crée des relations entre toutes les entités co-présentes
        dans une même phrase. Le poids augmente à chaque co-occurrence.
        """
        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                src = entity_ids[i]
                tgt = entity_ids[j]
                # Cherche si la relation existe déjà
                existing = self._find_relation(src, tgt)
                if existing:
                    existing.weight += 1.0
                else:
                    self.relations.append(Relation(
                        source_id=src,
                        target_id=tgt,
                        weight=1.0,
                        sentence=sentence[:120],
                    ))

    def _find_relation(self, src: str, tgt: str) -> Optional[Relation]:
        for rel in self.relations:
            if (rel.source_id == src and rel.target_id == tgt) or \
               (rel.source_id == tgt and rel.target_id == src):
                return rel
        return None

    # ── Fallback regex (sans spaCy) ───────────

    def _extract_with_regex(self, text: str):
        """
        Mode dégradé sans spaCy.
        Détecte les entités par patterns regex simples :
        - Mots commençant par une majuscule (organisations/personnes)
        - Montants (chiffres + devises)
        """
        sentences = re.split(r'[.!?]+', text)

        for sentence in sentences:
            ents_in_sent = []

            # Montants
            for match in re.finditer(r'\d+[\s,.]?\d*\s*(€|\$|MAD|DH|million|milliard|k€|M€)', sentence):
                eid = self._register_entity(match.group(), "MONEY", sentence).id
                ents_in_sent.append(eid)

            # Mots ou groupes en majuscule (heuristique organisations/personnes)
            for match in re.finditer(r'\b([A-ZÁÀÂÉÈÊÎÏÔÙÛÜÇŒÆ][a-záàâéèêîïôùûüçœæ]+(?:\s[A-ZÁÀÂÉÈÊÎÏÔÙÛÜÇŒÆ][a-záàâéèêîïôùûüçœæ]+)*)\b', sentence):
                name = match.group()
                if len(name) > 3 and name not in ("Les", "Des", "Une", "The", "This", "That"):
                    eid = self._register_entity(name, "ORG", sentence).id
                    ents_in_sent.append(eid)

            self._add_cooccurrence_relations(list(set(ents_in_sent)), sentence)

    # ── Construction du graphe ────────────────

    def _build_graph(self) -> nx.Graph:
        """
        Construit un graphe NetworkX depuis les entités et relations extraites.

        Nœuds : entités avec leurs attributs (type, fréquence, couleur)
        Arêtes : relations avec poids normalisé
        """
        G = nx.Graph()

        # Ajout des nœuds
        for eid, entity in self.entities.items():
            G.add_node(
                eid,
                label=entity.name,
                type=entity.type_label,
                frequency=entity.frequency,
                risk_score=entity.risk_score,
                color=entity.color,
                size=10 + entity.frequency * 4,  # taille proportionnelle
            )

        # Normalisation des poids (0–1)
        max_weight = max((r.weight for r in self.relations), default=1.0)

        # Ajout des arêtes
        for rel in self.relations:
            if rel.source_id in G.nodes and rel.target_id in G.nodes:
                G.add_edge(
                    rel.source_id,
                    rel.target_id,
                    weight=rel.weight,
                    weight_norm=rel.weight / max_weight,
                    sentence=rel.sentence,
                )

        logger.info(f"Graphe construit : {G.number_of_nodes()} nœuds, {G.number_of_edges()} arêtes")
        return G

    # ── Statistiques ──────────────────────────

    def _compute_stats(self) -> dict:
        """Métriques pour le dashboard."""
        G = self.graph
        if G.number_of_nodes() == 0:
            return {}

        return {
            "nb_entities":       G.number_of_nodes(),
            "nb_relations":      G.number_of_edges(),
            "density":           round(nx.density(G), 4),
            "nb_components":     nx.number_connected_components(G),
            "avg_degree":        round(sum(d for _, d in G.degree()) / G.number_of_nodes(), 2),
            "processing_time":   self.processing_time,
            "entity_types":      self._count_entity_types(),
        }

    def _count_entity_types(self) -> dict:
        counter = defaultdict(int)
        for e in self.entities.values():
            counter[e.type_label] += 1
        return dict(counter)

    # ── Export ────────────────────────────────

    def export_graph_json(self) -> dict:
        """Exporte le graphe au format JSON (compatible avec la vue WinForms)."""
        G = self.graph
        return {
            "nodes": [
                {**data, "id": nid}
                for nid, data in G.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, **data}
                for u, v, data in G.edges(data=True)
            ],
            "stats": self._compute_stats(),
        }

    def get_graph(self) -> nx.Graph:
        return self.graph

    def get_entities(self) -> Dict[str, Entity]:
        return self.entities
