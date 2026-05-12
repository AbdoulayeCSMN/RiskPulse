"""
RiskPulse — Constantes UI
==========================
Toutes les constantes de l'interface centralisées ici.
Aucune valeur magique dans le code de l'application.
"""

from dataclasses import dataclass
from typing import Tuple

# ─────────────────────────────────────────────
#  APPLICATION
# ─────────────────────────────────────────────

APP_NAME         = "RiskPulse"
APP_VERSION      = "1.0.0"
APP_SUBTITLE     = "Cartographie et Propagation de Risques par IA"
APP_AUTHOR       = "C. ABDOULAYE"
APP_MIN_WIDTH    = 900
APP_MIN_HEIGHT   = 600
APP_DEFAULT_W    = 1280
APP_DEFAULT_H    = 760

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────

SIDEBAR_WIDTH        = 300
SIDEBAR_ICON_SIZE    = 14
SIDEBAR_ITEM_HEIGHT  = 42
SIDEBAR_PADDING_X    = 18
SIDEBAR_SECTION_H    = 28

# Navigation items : (id, label, rupture_tag)
NAV_ITEMS = [
    ("analyse",      "Analyse de Texte",   "R1"),
    ("propagation",  "Propagation",        "R2 R3"),
    ("comparaison",  "Comparaison IA",     "R4"),
    ("contrefactuel","Simulations What-If", "R5"),
    ("traduction",   "Traduction",         ""),
    ("dashboard",    "Tableau de Bord",    ""),
    ("parametres",   "Parametres",         ""),
]

# ─────────────────────────────────────────────
#  TOPBAR
# ─────────────────────────────────────────────

TOPBAR_HEIGHT   = 50
LOGO_FONT_SIZE  = 18
STATUS_FONT_SIZE = 10

# ─────────────────────────────────────────────
#  ESPACEMENTS
# ─────────────────────────────────────────────

PAD_XS  = 4
PAD_SM  = 8
PAD_MD  = 12
PAD_LG  = 18
PAD_XL  = 24
PAD_XXL = 36

RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 10

# ─────────────────────────────────────────────
#  TYPOGRAPHIE
# ─────────────────────────────────────────────

FONT_FAMILY_PRIMARY   = "Jetbrains Mono" # Segoe UI
FONT_FAMILY_MONO      = "Consolas"
FONT_FAMILY_FALLBACK  = "Jetbrains Mono"

@dataclass(frozen=True)
class FontSpec:
    family: str
    size: int
    weight: str = "normal"
    slant: str  = "roman"

    def as_tuple(self) -> Tuple:
        t = (self.family, self.size)
        if self.weight != "normal":
            t += (self.weight,)
        if self.slant != "roman":
            t += (self.slant,)
        return t

FONT_H1       = FontSpec(FONT_FAMILY_PRIMARY, 20, "bold")
FONT_H2       = FontSpec(FONT_FAMILY_PRIMARY, 15, "bold")
FONT_H3       = FontSpec(FONT_FAMILY_PRIMARY, 13, "bold")
FONT_BODY     = FontSpec(FONT_FAMILY_PRIMARY, 11)
FONT_BODY_SM  = FontSpec(FONT_FAMILY_PRIMARY, 10)
FONT_CAPTION  = FontSpec(FONT_FAMILY_PRIMARY, 9)
FONT_MONO     = FontSpec(FONT_FAMILY_MONO,    10)
FONT_LOGO     = FontSpec(FONT_FAMILY_PRIMARY, 18, "bold")
FONT_NAV      = FontSpec(FONT_FAMILY_PRIMARY, 11)
FONT_NAV_SM   = FontSpec(FONT_FAMILY_PRIMARY, 9)
FONT_BTN      = FontSpec(FONT_FAMILY_PRIMARY, 11, "bold")
FONT_METRIC   = FontSpec(FONT_FAMILY_PRIMARY, 24, "bold")
FONT_LABEL    = FontSpec(FONT_FAMILY_PRIMARY, 10)

# ─────────────────────────────────────────────
#  COMPOSANTS — TAILLES
# ─────────────────────────────────────────────

BTN_HEIGHT_SM  = 28
BTN_HEIGHT_MD  = 34
BTN_HEIGHT_LG  = 42
BTN_PAD_X      = 16

CARD_RADIUS    = 8
CARD_BORDER_W  = 1

INPUT_HEIGHT   = 34
INPUT_RADIUS   = 6

METRIC_CARD_W  = 180
METRIC_CARD_H  = 90

PROGRESSBAR_H  = 6

# ─────────────────────────────────────────────
#  RUPTURES — LABELS (pour affichage UI)
# ─────────────────────────────────────────────

RUPTURE_LABELS = {
    "R1": "NLP  Graphe automatique",
    "R2": "Propagation temps reel",
    "R3": "Noeuds critiques caches",
    "R4": "Modele A vs Modele B",
    "R5": "Simulations What-If",
}

RUPTURE_COLORS_DARK  = {
    "R1": "#3d9b6e",
    "R2": "#69de52",
    "R3": "#eab592",
    "R4": "#8e44ad",
    "R5": "#2980b9",
}

RUPTURE_COLORS_LIGHT = {
    "R1": "#27ae60",
    "R2": "#e74c3c",
    "R3": "#e67e22",
    "R4": "#9b59b6",
    "R5": "#2980b9",
}

# ─────────────────────────────────────────────
#  ETATS DE RISQUE (propagation)
# ─────────────────────────────────────────────

RISK_COLORS = {
    "safe":     "#27ae60",
    "exposed":  "#ffd84b",
    "infected": "#f88520",
    "critical": "#ea2d18",
}

RISK_LABELS = {
    "safe":     "Sain",
    "exposed":  "Expose",
    "infected": "Infecte",
    "critical": "Critique",
}

# ─────────────────────────────────────────────
#  ANIMATIONS
# ─────────────────────────────────────────────

ANIM_DURATION_FAST   = 150   # ms
ANIM_DURATION_NORMAL = 250
ANIM_DURATION_SLOW   = 400
ANIM_FPS             = 60

# ─────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────

DASHBOARD_METRICS = [
    ("nb_entities",      "Entites",      ""),
    ("nb_relations",     "Relations",    ""),
    ("model_a_anomalies","Anomalies A",  ""),
    ("model_b_anomalies","Anomalies B",  ""),
    ("processing_time",  "Temps (s)",    ""),
    ("graph_density",    "Densite",      ""),
]

# ─────────────────────────────────────────────
#  SCENARIOS DEMO (labels UI)
# ─────────────────────────────────────────────

DEMO_LABELS = {
    "crise_financiere": "Crise Financiere",
    "attaque_cyber":    "Attaque Cyber",
    "reseau_juridique": "Reseau Juridique",
    "chaine_appro":     "Chaine Appro.",
    "reseau_business":  "Ecosysteme FinTech",
}

# ─────────────────────────────────────────────
#  LANGUES (module traduction)
# ─────────────────────────────────────────────

LANGUAGES = {
    "fr": "Francais",
    "ar": "Arabe",
    "en": "Anglais",
    "it": "Italien",
    "es": "Espagnol",
}

# ─────────────────────────────────────────────
#  FICHIERS / EXTENSIONS
# ─────────────────────────────────────────────

FILETYPES_TEXT = [
    ("Fichiers texte",    "*.txt"),
    ("Fichiers PDF",      "*.pdf"),
    ("Fichiers JSON",     "*.json"),
    ("Fichiers CSV",      "*.csv"),
    ("Tous les fichiers", "*.*"),
]

FILETYPES_JSON = [
    ("Fichiers JSON", "*.json"),
    ("Tous les fichiers", "*.*"),
]

FILETYPES_CSV = [
    ("Fichiers CSV", "*.csv"),
    ("Tous les fichiers", "*.*"),
]

EXPORT_DIR = "data/exports"
LOG_DIR    = "data/logs"
