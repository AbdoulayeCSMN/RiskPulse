"""
Genere RiskPulse_v1.0.0_Rapport.docx (Word complet) avec :
  - Page de garde (titre, auteur, annee)
  - Table des matieres
  - 20 sections detaillees
  - Captures depuis docs/screenshots/
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime

from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
OUT = ROOT / "RiskPulse_v1.0.0_Rapport.docx"

AUTHOR = "CHAIBOU SAIDOU ABDOULAYE"
YEAR   = "2026"
TITLE  = "RiskPulse v1.0.0"
SUBT   = "Rapport complet & guide utilisateur"

# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

doc = Document()

# Marges
for section in doc.sections:
    section.top_margin    = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin   = Cm(2.2)
    section.right_margin  = Cm(2.2)

# Styles par defaut
styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(11)

def add_heading(level: int, text: str):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)
    return h

def add_para(text: str, bold=False, italic=False, size=None, color=None,
              align=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    if size: run.font.size = Pt(size)
    if color: run.font.color.rgb = RGBColor(*color)
    if align: p.alignment = align
    return p

def add_bullet(text: str):
    p = doc.add_paragraph(text, style="List Bullet")
    return p

def add_code(text: str):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    run = p.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    # gris clair en fond via shading
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F4F4F4")
    p._p.get_or_add_pPr().append(shd)
    return p

def add_table(headers: list[str], rows: list[list[str]],
                col_widths: list[float] | None = None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Light Grid Accent 1"
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.bold = True
    for ri, row in enumerate(rows, 1):
        cells = t.rows[ri].cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    return t

def add_image(name: str, width_cm: float = 14, caption: str | None = None):
    path = SHOTS / name
    if not path.exists():
        add_para(f"[Capture manquante : {name}]", italic=True,
                  color=(0x88, 0x88, 0x88))
        return
    doc.add_picture(str(path), width=Cm(width_cm))
    last = doc.paragraphs[-1]
    last.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if caption:
        c = doc.add_paragraph(caption)
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in c.runs:
            r.italic = True
            r.font.size = Pt(9)
            r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

def page_break():
    doc.add_page_break()

# ────────────────────────────────────────────────────────────────────────────
# PAGE DE GARDE
# ────────────────────────────────────────────────────────────────────────────

# Espace haut
for _ in range(6):
    doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("RISKPULSE")
run.bold = True
run.font.size = Pt(48)
run.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("v1.0.0")
run.font.size = Pt(20)
run.font.color.rgb = RGBColor(0x6F, 0x9F, 0xFF)

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Rapport complet & guide utilisateur")
run.italic = True
run.font.size = Pt(16)
run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run(
    "Plateforme d'analyse de risque assistee par intelligence artificielle"
)
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

for _ in range(8):
    doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Auteur")
run.font.size = Pt(10)
run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run(AUTHOR)
run.bold = True
run.font.size = Pt(16)
run.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run(f"Annee {YEAR}")
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

page_break()

# ────────────────────────────────────────────────────────────────────────────
# TABLE DES MATIERES
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "Table des matieres")
toc_entries = [
    "1. Synthese executive",
    "2. Vision & cas d'usage",
    "3. Architecture generale",
    "4. Les quatre moteurs d'analyse",
    "5. Plateforme : services transverses",
    "6. Interface utilisateur",
    "7. Internationalisation",
    "8. Guide d'installation pas a pas",
    "9. Guide d'utilisation : du premier clic a l'analyse",
    "10. Tour complet des 18 vues",
    "11. Reference des raccourcis clavier",
    "12. API REST & SDK Python",
    "13. Licensing offline (Etape 10)",
    "14. Telemetry & rapports d'erreur (Etape 11)",
    "15. Distribution, build & code-signing",
    "16. Validation : resultats des tests",
    "17. Maintenance & support",
    "18. Limites connues & roadmap",
    "19. Glossaire",
    "20. Credits & licence",
]
for e in toc_entries:
    doc.add_paragraph(e, style="List Number")
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 1. SYNTHESE EXECUTIVE
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "1. Synthese executive")
add_para(
    "RiskPulse est une application desktop d'analyse de risque alimentee par IA, "
    "packagee pour Windows en .exe portable. Elle transforme un texte brut "
    "(article de presse, rapport financier, depeche AML...) en une cartographie "
    "de risque complete : entites extraites, scores de criticite, chaines de "
    "propagation, comparaisons a 6 crises historiques, predictions a 30 jours, "
    "alertes AML/KYC, et syntheses LLM."
)
add_table(
    ["Caracteristique", "Valeur"],
    [
        ["Plateforme cible",     "Windows 10 / 11 (exe portable + installer Inno Setup)"],
        ["Stack",                "Python 3.12, PySide6 (Qt6), spaCy, scikit-learn, FastAPI"],
        ["Langues UI",           "EN, FR, AR (RTL), IT, ES (~1180 entrees)"],
        ["Vues metier",          "18 ecrans organises par domaine"],
        ["Distribution",         "Portable .exe (~250 Mo), installeur, auto-updater SHA-256"],
        ["Licensing",            "ED25519 offline, trial 14 j, plans FREE/PRO/ENTERPRISE"],
        ["Reseau requis",        "Aucun (sauf RSS / Wikidata / LLM optionnels)"],
        ["Couverture tests",     "12 smoke, 12 updater, 7 licensing, 6 telemetry, prod-eval"],
        ["Volume code",          "~11 000 lignes Python, 65 modules"],
    ],
    col_widths=[5.0, 11.0],
)
add_para(
    "Pour qui ? Compliance officers, analystes risque, journalistes "
    "d'investigation, equipes due diligence, chercheurs en intelligence "
    "economique."
)
add_para(
    "Promesse produit en une phrase : passer d'un article de 2 paragraphes "
    "a un dossier risque exploitable en moins de 10 secondes, sans envoyer "
    "la moindre donnee dans le cloud.",
    italic=True,
)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 2. VISION
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "2. Vision & cas d'usage")
add_heading(2, "2.1. Le probleme resolu")
add_para(
    "Un analyste risque recoit en moyenne 50 a 200 signaux par jour. Pour chaque "
    "signal il doit identifier les entites citees, evaluer leur severite, croiser "
    "avec un historique, estimer la propagation, et decider d'une action (KYC "
    "renforce, SAR, escalade). Les solutions existantes (Bloomberg, Refinitiv, "
    "Quantexa) coutent 30 a 200 k EUR/an et imposent l'envoi des documents "
    "dans le cloud du vendeur."
)
add_heading(2, "2.2. La proposition de RiskPulse")
for b in [
    "100% local : aucune donnee n'est envoyee (sauf si l'utilisateur active explicitement Wikidata ou un LLM externe).",
    "Un binaire portable, installation en moins d'une minute.",
    "Tarification accessible : trial 14 jours puis PRO ~49 EUR/mois, ENTERPRISE ~199 EUR/mois.",
    "Code-base entierement auditable.",
]:
    add_bullet(b)

add_heading(2, "2.3. Cas d'usage valides")
add_table(
    ["Cas reel", "Resultat RiskPulse"],
    [
        ["Credit Suisse 2023", "Trajectoire detectee Lehman-like, VaR 99 = -42%"],
        ["FTX / SBF 2022",     "PEP flagrue, fraude detectee, motif Madoff 78%"],
        ["Panama Papers 2016", "11 paradis fiscaux, 6 PEP, verdict ESCALATE_SAR"],
    ],
    col_widths=[4.0, 12.0],
)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 3. ARCHITECTURE
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "3. Architecture generale")
add_para(
    "RiskPulse suit une separation stricte UI / logique : aucun moteur "
    "n'importe Qt. Les services a etat (Knowledge Base, Auth, License, "
    "Telemetry) sont des singletons explicites. Le mode frozen-aware "
    "route les ecritures vers %APPDATA%\\RiskPulse\\ en .exe, vers le "
    "repo en dev. Les threads non-bloquants (monitoring, API, downloads) "
    "tournent dans des threads dedies, jamais sur le thread Qt."
)
add_heading(2, "3.1. Diagramme")
add_code(
    "                +----------------------------------------------+\n"
    "                |               UI  (PySide6 / Qt6)            |\n"
    "                |   18 vues, 5 langues, themes dark/light       |\n"
    "                +-----------------+-----------------------------+\n"
    "                                  | Signal/Slot Qt\n"
    "                +-----------------v-----------------------------+\n"
    "                |       controller/risk_controller.py           |\n"
    "                |       Orchestrateur : pipeline 6 etapes       |\n"
    "                +---+-------+----------+--------------+---------+\n"
    "                    |       |          |              |\n"
    "          +---------v-+ +---v----+ +---v----+ +-------v-------+\n"
    "          |  Engines  | |Services| | Utils  | | API (FastAPI) |\n"
    "          |  NLP      | |  KB    | | paths  | |   /v1/...     |\n"
    "          |  Intel    | |  Auth  | | logger | |   X-API-Key   |\n"
    "          |  Predict  | |  Watch | | errors | +---------------+\n"
    "          |  Banking  | | Updater|\n"
    "          |  Models   | | License|\n"
    "          |  Propag.  | | Telem. |\n"
    "          +-----------+ +--------+\n"
    "                    |       |\n"
    "                    v       v\n"
    "                 +------------+\n"
    "                 |  SQLite    |\n"
    "                 +------------+\n"
)
add_heading(2, "3.2. Le pipeline d'analyse")
add_para(
    "Quand l'utilisateur clique sur Analyser, le RiskController execute six "
    "etapes dans l'ordre : 1) NLP extraction d'entites et relations, "
    "2) Analyse de centralite (PageRank + Betweenness), 3) Modeles "
    "IsolationForest et GraphBased en parallele, 4) Risk Intelligence + "
    "Banking + Predictive, 5) Persistance dans la Knowledge Base, "
    "6) Notification UI. Temps total approximatif : 600 ms pour 2000 caracteres."
)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 4. ENGINES
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "4. Les quatre moteurs d'analyse")

add_heading(2, "4.1. NLP Engine")
add_table(
    ["Aspect", "Detail"],
    [
        ["Backend",      "spaCy 3.7 (fr_core_news_sm, en_core_web_sm)"],
        ["Sortie",       "Liste d'Entity avec name, type, centrality, sentences, severity"],
        ["Heuristique 1","Suffixes corporatifs (LLC, SA, LTD) -> ORGANISATION"],
        ["Heuristique 2","Titres PEP (ministre, president...) -> PERSONNE"],
        ["Desambiguisation", "Fuzzy match contre la KB (RapidFuzz > 90)"],
        ["Performances", "~1500 caracteres / 100 ms"],
    ],
    col_widths=[4.0, 12.0],
)

add_heading(2, "4.2. Risk Intelligence Engine")
add_para("Trois composants :")
add_bullet("RiskScorer : note composite 0..1 sur 5 axes (sentiment, centralite, mots-cles crise, mentions financieres negatives, velocite).")
add_bullet("CrisisMatcher : compare la trajectoire a 6 patterns historiques (Lehman, LTCM, Enron, Wirecard, Madoff, Northern Rock).")
add_bullet("CascadeEstimator : propage le choc via PageRank personnalise, sortie VaR 95 / VaR 99.")

add_heading(2, "4.3. Predictive Engine")
add_bullet("RiskForecaster : regression lineaire ponderee, horizon 30 j, bande de confiance 80% / 95%.")
add_bullet("MonteCarloSimulator : 1000 trajectoires stochastiques, distribution des pertes.")
add_bullet("TrajectoryMatcher : DTW entre la courbe observee et les 6 patterns.")

add_heading(2, "4.4. Banking Pack")
add_table(
    ["Module", "Description"],
    [
        ["FATF Greylist",  "23 juridictions a surveillance renforcee"],
        ["OFAC SDN",       "Sanctions US (echantillon, a brancher en prod)"],
        ["Tax Havens",     "Liste revisee (Suisse / Luxembourg retires)"],
        ["PEP Detection",  "Heuristique titre + nom dans la meme phrase"],
        ["Fraud Keywords", "detournement, evasion fiscale, fraude comptable, commingling..."],
        ["Verdict",        "STANDARD_KYC, ENHANCED_DD, ESCALATE_SAR"],
    ],
    col_widths=[4.0, 12.0],
)
add_para("Templates PDF inclus : SAR (Suspicious Activity Report), DD (Due Diligence).")
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 5. PLATEFORME
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "5. Plateforme : services transverses")

add_heading(2, "5.1. Knowledge Base")
add_para(
    "Base SQLite (data/knowledge.db) avec 10 tables : analyses, entities, "
    "entity_appearances, entity_cooccurrences, watchlist, sources, "
    "source_items, alerts, entity_enrichment, users + audit_log."
)
add_heading(2, "5.2. Watch & Monitoring")
add_para(
    "Cycle automatique toutes les 15 minutes : fetch RSS/URL (3 items max), "
    "pipeline complet, matching watch, alerte si score depasse le seuil. "
    "Notification non-intrusive (badge sidebar + toast)."
)
add_heading(2, "5.3. Enrichment Wikidata")
add_para("Aucune cle API requise. Cache local TTL 30 jours. Champs : description, image, instance_of, country, founded_year, employees.")
add_heading(2, "5.4. Auth & RBAC")
add_para("PBKDF2-SHA256 600 000 iterations. Sessions persistantes. 3 roles, 18 permissions :")
add_table(
    ["Permission", "Admin", "Analyst", "Viewer"],
    [
        ["RUN_ANALYSIS",     "OUI", "OUI", "OUI"],
        ["EXPORT_PDF",       "OUI", "OUI", "OUI"],
        ["MANAGE_WATCHLIST", "OUI", "OUI", "-"],
        ["MANAGE_API",       "OUI", "-",   "-"],
        ["MANAGE_USERS",     "OUI", "-",   "-"],
        ["VIEW_AUDIT_LOG",   "OUI", "-",   "-"],
    ],
    col_widths=[6.0, 3.0, 3.0, 3.0],
)
add_para(
    "Bootstrap : au premier lancement, compte admin/admin cree automatiquement. "
    "A changer imperativement.",
    italic=True,
)
add_heading(2, "5.5. Auto-updater")
add_para(
    "Fetch manifest JSON signe. Comparaison SemVer (supporte 'v' prefix et "
    "'-rc' suffix). Telechargement avec progression, verification SHA-256. "
    "Script .bat de remplacement atomique + backup + rollback. Ctrl+U pour "
    "verifier manuellement."
)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 6. UI
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "6. Interface utilisateur")
add_heading(2, "6.1. Philosophie design")
add_para(
    "Inspiration Linear / Raycast : noir presque pur, monochrome, JetBrains "
    "Mono, aucun emoji, accent unique #6F9FFF pour l'interactif. Densite "
    "elevee d'information sans surcharge visuelle."
)
add_heading(2, "6.2. Anatomie de la fenetre")
add_code(
    "+----------------------------------------------------------------+\n"
    "|  RISKPULSE | subtitle...    TRIAL.14d  Admin  v1.0.0           | TopBar 52px\n"
    "+------------+---------------------------------------------------+\n"
    "| NAVIGATION |                                                   |\n"
    "|  Analysis  |                                                   |\n"
    "|  Risk Int  |                                                   |\n"
    "|  Predict.  |              STACKED  VIEW                        |\n"
    "|  AML...    |              (la vue active)                      |\n"
    "|  License   |                                                   |\n"
    "|  Settings  |                                                   |\n"
    "+------------+---------------------------------------------------+\n"
    "| STATUS: Ready                       RISKPULSE . V1.0.0         | StatusBar\n"
    "+----------------------------------------------------------------+\n"
)
add_heading(2, "6.3. Composants premium")
add_bullet("Card : conteneur avec ombre douce, radius 8 px, hover subtil.")
add_bullet("MetricCard : grand chiffre + label + delta colore.")
add_bullet("CommandPalette (Ctrl+K) : recherche fuzzy de toutes les commandes.")
add_bullet("Toast : notifications non-bloquantes en bas-droite, auto-dismiss.")
add_bullet("UpdateDialog : flux 3 etapes (check, download, install).")
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 7. I18N
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "7. Internationalisation")
add_para(
    "Stack Qt natif : QTranslator + .ts/.qm. Cinq langues, environ 1180 "
    "chaines. Le selecteur en topbar applique la langue instantanement "
    "(signal language_changed -> toutes les vues retraduisent). Pour "
    "l'arabe, Qt.RightToLeft est applique sur la fenetre."
)
add_table(
    ["Code", "Langue", "RTL"],
    [
        ["en", "English",  "-"],
        ["fr", "Francais", "-"],
        ["ar", "Arabe",    "OUI"],
        ["es", "Espanol",  "-"],
        ["it", "Italiano", "-"],
    ],
    col_widths=[3.0, 6.0, 3.0],
)
for code in ["en", "fr", "ar"]:
    add_image(f"riskpulse_i18n_{code}.png", width_cm=14,
               caption=f"UI complete en {code}")
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 8. INSTALLATION
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "8. Guide d'installation pas a pas")

add_heading(2, "8.1. Installation utilisateur (Windows .exe portable)")
add_para("Public : utilisateur final, aucune competence technique requise.")
for i, step in enumerate([
    "Telechargez RiskPulse-1.0.0-portable.zip depuis la page Releases GitHub.",
    "Verifiez l'empreinte (optionnel mais recommande) : telechargez RiskPulse-1.0.0.sha256, ouvrez PowerShell et tapez : Get-FileHash RiskPulse-1.0.0-portable.zip -Algorithm SHA256. Le hash affiche doit correspondre exactement.",
    "Decompressez le ZIP n'importe ou (cle USB, Bureau, Documents). Aucun droit administrateur requis.",
    "Lancez RiskPulse\\RiskPulse.exe en double-cliquant.",
    "Au premier lancement, Windows SmartScreen peut afficher 'Windows a protege votre PC'. Cliquez Informations complementaires puis Executer quand meme. (Ce message disparait avec un certificat OV/EV.)",
    "Le splash screen s'affiche pendant ~3 s, puis la fenetre principale s'ouvre. Vous etes pret.",
], 1):
    doc.add_paragraph(f"{i}. {step}", style="List Number")

add_heading(2, "8.2. Installation dev (depuis le source)")
add_code(
    "git clone https://github.com/AbdoulayeCSMN/riskpulse.git\n"
    "cd riskpulse\n"
    "python -m venv .venv && .venv\\Scripts\\activate\n"
    "pip install -r requirements.txt\n"
    "python -m spacy download fr_core_news_sm\n"
    "python -m spacy download en_core_web_sm\n"
    "python ui_qt/locales/compile_qm.py\n"
    "python main_qt.py\n"
)

add_heading(2, "8.3. Premiere configuration recommandee")
add_table(
    ["Action", "Comment"],
    [
        ["Changer mdp admin",      "Vue Users & Audit -> ligne admin -> Edit"],
        ["Choisir la langue",      "TopBar -> combo droit -> selectionner"],
        ["Choisir le theme",       "Ctrl+T (toggle dark/light)"],
        ["Activer une licence",    "Ctrl+L -> coller la cle -> Activer"],
        ["Activer telemetrie",     "Sidebar Diagnostics -> cocher Enable"],
    ],
    col_widths=[5.0, 11.0],
)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 9. UTILISATION
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "9. Guide d'utilisation : du premier clic a l'analyse")
add_heading(2, "9.1. Ecran d'accueil")
add_image("riskpulse_qt_welcome_dark.png", width_cm=15,
           caption="Vue Welcome au lancement de l'application")
add_para("Quatre actions principales :")
add_bullet("Run analysis : ouvre la vue Text Analysis.")
add_bullet("Random demo : charge un scenario aleatoire parmi 6 cas pre-installes (Madoff, FTX, Wirecard...) et lance le pipeline complet.")
add_bullet("Recent analyses : liste des dernieres analyses (cliquables).")
add_bullet("Knowledge base summary : 4 KPIs.")

add_heading(2, "9.2. Workflow type : analyse d'un article de presse")
for i, step in enumerate([
    "Cliquez Run analysis ou Ctrl+1.",
    "Collez le texte (francais ou anglais) dans la grande zone. Astuce : Ctrl+V suffit.",
    "(Optionnel) Reglez les parametres dans le panneau de droite (Sensitivity, Top critical).",
    "Cliquez Analyze (ou Ctrl+Enter). Une barre de progression s'affiche en bas, l'analyse prend moins d'1 seconde pour 2000 caracteres.",
    "Le resultat s'affiche en 3 panneaux : gauche = table des entites triee par centralite, centre = graphe interactif, droite = score composite + verdict.",
    "Explorez les autres vues : Risk Intelligence pour la similarite Lehman, Predictive pour la prevision 30j, AML & Compliance pour le verdict KYC, AI Insights pour la synthese LLM, Risk Propagation pour le graphe anime.",
    "Exportez : bouton Export en haut a droite de chaque vue, ou Dashboard -> Export ZIP global.",
], 1):
    doc.add_paragraph(f"{i}. {step}", style="List Number")

add_heading(2, "9.3. Conseils pratiques")
add_para(
    "Si l'analyse dit que Credit Suisse a une similarite Lehman > 70%, ce "
    "n'est pas un oracle. C'est un signal qui merite une verification humaine. "
    "RiskPulse trie le bruit ; vous prenez la decision.",
    italic=True,
)
add_bullet("Analysez plusieurs articles sur le meme sujet : la KB consolide automatiquement et la precision monte.")
add_bullet("Activez le monitoring sur Reuters / FT / Bloomberg RSS pour recevoir des alertes en continu.")
add_bullet("Pour les dossiers sensibles : desactivez la telemetrie et le LLM externe ; tout reste local.")
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 10. VUES
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "10. Tour complet des 18 vues")

views = [
    ("10.1. Text Analysis", None,
     "Entree principale. Champ texte + parametres + resultats triple-panneau (entites, graphe, score)."),
    ("10.2. Risk Intelligence", "riskpulse_qt_intelligence_dark.png",
     "Score composite, matrice de similarite aux 6 patterns historiques, projection VaR."),
    ("10.3. Predictive", "riskpulse_qt_predictive.png",
     "Courbe historique + forecast 30 j avec bande de confiance, leaderboard des trajectoires les plus inquietantes, distribution Monte Carlo."),
    ("10.4. AML & Compliance", "riskpulse_qt_banking.png",
     "Tableau entites avec flags PEP / sanctions / FATF / tax haven / fraud. Boutons Generate SAR et Generate DD report."),
    ("10.5. Knowledge Base", "riskpulse_qt_knowledge.png",
     "Recherche full-text + facettes. Click sur une entite -> fiche detaillee + enrichment Wikidata."),
    ("10.6. Watch & Monitor", "riskpulse_qt_monitoring.png",
     "Trois onglets : Watches, Sources, Alerts. Boutons CRUD, status 'Last cycle: 12 min ago', compteur d'alertes non lues."),
    ("10.7. AI Insights", "riskpulse_qt_insights_dark.png",
     "Synthese LLM (Grok ou Claude) en langage naturel. Configurable dans Settings."),
    ("10.8. Risk Propagation", None,
     "Graphe anime : pulses qui se propagent le long des aretes selon le propagation_engine. Sliders pour decay et speed."),
    ("10.9. AI Comparison", "riskpulse_qt_comparaison_v2.png",
     "Matrice 2x2 : entites flaguees par les deux modeles, par un seul, par aucun."),
    ("10.10. What-If Simulations", None,
     "Modifier le poids d'une entite ou supprimer une arete et voir l'impact sur le graphe propage."),
    ("10.11. Translation", None,
     "Vue traduction de texte multi-langue (deep-translator)."),
    ("10.12. Dashboard", None,
     "Vue d'ensemble executive : 8 KPIs + 3 graphes + export ZIP global."),
    ("10.13. Enrichment", "riskpulse_qt_enrichment.png",
     "Description Wikipedia, photo, metadata Wikidata."),
    ("10.14. API & SDK", "riskpulse_qt_api.png",
     "Start/Stop du serveur FastAPI. Affiche l'URL, le port, la cle API. Lien direct vers /docs Swagger."),
    ("10.15. Users & Audit", "riskpulse_qt_users.png",
     "Liste des comptes (admin only), creation, changement de role, reset password. Journal d'audit avec filtres."),
    ("10.16. License", "riskpulse_qt_license_dark.png",
     "Etat du plan, jours de trial restants, dialog d'activation, grille de disponibilite des features."),
    ("10.17. Diagnostics (Telemetry)", None,
     "Crashes recents, top error types, feature usage, export support bundle."),
    ("10.18. Settings", None,
     "Parametres du modele (contamination, n_estimators, decay...), choix LLM, intervalle monitoring."),
]
for title, img, desc in views:
    add_heading(2, title)
    add_para(desc)
    if img:
        add_image(img, width_cm=14)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 11. RACCOURCIS
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "11. Reference des raccourcis clavier")
add_table(
    ["Raccourci", "Action"],
    [
        ["Ctrl+K",        "Command Palette (recherche d'actions)"],
        ["Ctrl+H",        "Retour a l'ecran d'accueil"],
        ["Ctrl+1 - Ctrl+9", "Navigation directe vers la Nieme vue"],
        ["Ctrl+T",        "Toggle theme dark / light"],
        ["Ctrl+U",        "Verifier les mises a jour"],
        ["Ctrl+L",        "Ouvrir la vue License"],
        ["Ctrl+Q",        "Quitter"],
        ["F1",            "About RiskPulse"],
        ["Ctrl+Enter",    "Lancer l'analyse (depuis la vue Analyse)"],
        ["Esc",           "Fermer dialog / palette"],
    ],
    col_widths=[5.0, 11.0],
)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 12. API
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "12. API REST & SDK Python")
add_para(
    "Attention : la REST API est ENTERPRISE-only (ou trial). Tentative de "
    "demarrage en plan PRO declenche une PermissionError.",
    italic=True,
)

add_heading(2, "12.1. Demarrage")
add_para(
    "Vue API & SDK -> clic Start server. URL par defaut : "
    "http://127.0.0.1:8765. Documentation Swagger auto-generee a /docs."
)

add_heading(2, "12.2. Authentification")
add_para(
    "Toutes les routes (sauf /v1/health) exigent le header X-API-Key. La cle "
    "est affichee dans la vue API et stockee dans data/preferences.json."
)

add_heading(2, "12.3. Routes principales")
add_table(
    ["Methode", "Route", "Description"],
    [
        ["GET",  "/v1/health",                    "Ping (sans auth)"],
        ["POST", "/v1/analyze",                   "Analyse un texte"],
        ["GET",  "/v1/knowledge/entities",        "Liste paginee des entites"],
        ["GET",  "/v1/knowledge/entities/{id}",   "Fiche detaillee"],
        ["GET",  "/v1/monitoring/alerts",         "Alertes non lues"],
        ["POST", "/v1/monitoring/cycle",          "Forcer un cycle de monitoring"],
        ["GET",  "/v1/predictive/forecast/{eid}", "Forecast 30 j pour une entite"],
    ],
    col_widths=[2.5, 6.5, 7.0],
)

add_heading(2, "12.4. SDK Python")
add_code(
    "from api.sdk.client import RiskPulseClient\n\n"
    "client = RiskPulseClient(\"http://127.0.0.1:8765\", api_key=\"...\")\n\n"
    "result = client.analyze(\"Credit Suisse cherche un sauveteur, ...\")\n"
    "print(result['entities'])              # liste d'entites\n"
    "print(result['risk_score'])            # score composite\n"
    "print(result['crisis_match']['lehman']) # 0.78\n"
)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 13. LICENSING
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "13. Licensing offline (Etape 10)")

add_heading(2, "13.1. Principe")
add_para(
    "Chaque licence est un texte unique : <payload_b64>.<signature_b64>. "
    "Le payload contient {plan, email, iat, exp} et la signature est ED25519. "
    "Seul le detenteur de la cle privee peut forger une licence valide. La "
    "cle publique est embarquee dans l'app, donc la verification se fait 100% "
    "offline."
)

add_heading(2, "13.2. Cycle de vie")
add_code(
    "Premier lancement                                               \n"
    "  -> Trial 14 j ENTERPRISE auto-demarre                          \n"
    "  -> Badge topbar : TRIAL . 14d                                  \n"
    "                                                                \n"
    "Jour 15 (sans achat)                                            \n"
    "  -> Plan retombe sur FREE                                      \n"
    "  -> Vues premium grisees + toast d'invite a l'achat            \n"
    "                                                                \n"
    "Activation d'une cle PRO                                        \n"
    "  Ctrl+L -> coller -> Activer                                   \n"
    "  -> Plan PRO actif, badge 'PRO' en topbar                      \n"
    "  -> Predictive, Banking, AI Insights debloques                 \n"
)

add_heading(2, "13.3. Plans detailles")
add_table(
    ["Feature", "FREE", "PRO", "ENTERPRISE"],
    [
        ["Analyse de texte",     "X", "X", "X"],
        ["Knowledge Base",       "X", "X", "X"],
        ["5 langues UI",         "X", "X", "X"],
        ["Export PDF",           "X", "X", "X"],
        ["NLP avance",           "-", "X", "X"],
        ["Predictive",           "-", "X", "X"],
        ["Banking Pack",         "-", "X", "X"],
        ["AI Insights (LLM)",    "-", "X", "X"],
        ["Audit log",            "-", "X", "X"],
        ["Watchlist",            "-", "X", "X"],
        ["REST API",             "-", "-", "X"],
        ["Multi-user RBAC",      "-", "-", "X"],
        ["Monitoring illimite",  "-", "-", "X"],
        ["Wikidata enrichment",  "-", "-", "X"],
    ],
    col_widths=[7.0, 2.0, 2.0, 4.0],
)
add_image("riskpulse_qt_license_dark.png", width_cm=14,
           caption="Vue License avec etat trial + grille de features")

add_heading(2, "13.4. Generer des cles (cote vendeur)")
add_code(
    "# Une seule fois : creer la paire ED25519\n"
    "python tools/generate_license.py --init\n\n"
    "# Pour chaque client\n"
    "python tools/generate_license.py --plan PRO \\\n"
    "    --email \"alice@example.com\" --days 365\n\n"
    "python tools/generate_license.py --plan ENTERPRISE \\\n"
    "    --email \"bob@corp.com\" --perpetual\n"
)
add_para(
    "La cle privee tools/keys/riskpulse_private.pem est gitignored. Ne jamais "
    "la diffuser. Si elle fuite : regenerer une paire, push une update avec "
    "la nouvelle cle publique. Toutes les anciennes licences deviennent invalides.",
    italic=True,
)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 14. TELEMETRY
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "14. Telemetry & rapports d'erreur (Etape 11)")

add_heading(2, "14.1. Promesse de confidentialite")
add_bullet("Aucun envoi reseau. Tout reste sur la machine.")
add_bullet("Opt-in pour les evenements (feature_used, view_shown...).")
add_bullet("Les crashes sont captures meme en opt-out, mais ne quittent pas la machine.")
add_bullet("Scrub automatique : C:\\Users\\<nom> -> <HOME>, emails -> <EMAIL>.")

add_heading(2, "14.2. Vue Diagnostics")
add_para("Quatre cartes : opt-in toggle + export/clear, crashes table + viewer de traceback, top error types, feature usage.")

add_heading(2, "14.3. Envoyer un support bundle")
for i, step in enumerate([
    "Sidebar -> Diagnostics.",
    "Bouton Export support bundle (.zip).",
    "Le zip est cree dans data/exports/riskpulse-support-<timestamp>.zip et contient telemetry.db (deja scrubbed), logs/riskpulse.log + logs/errors.log, meta.json (version, OS, comptes).",
    "Envoyez ce zip par email au support. Aucune autre donnee n'est necessaire.",
], 1):
    doc.add_paragraph(f"{i}. {step}", style="List Number")
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 15. BUILD
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "15. Distribution, build & code-signing")

add_heading(2, "15.1. Build local")
add_code(
    "python build_scripts/release.py --version 1.0.0 \\\n"
    "    --notes-file CHANGELOG.md \\\n"
    "    --base-url \"https://github.com/USER/riskpulse/releases/download/v1.0.0\"\n"
)
add_para("Sortie dans dist/release/ : RiskPulse-1.0.0-portable.zip, RiskPulse-1.0.0.sha256, manifest.json.")

add_heading(2, "15.2. Code-signing")
add_table(
    ["Type cert", "Prix annuel", "SmartScreen"],
    [
        ["Self-signed",   "0 EUR",            "Unknown publisher permanent"],
        ["Sectigo OV",    "80 - 150 USD",     "Warning quelques jours puis OK"],
        ["DigiCert OV",   "400 - 500 USD",    "Reputation immediate"],
        ["DigiCert EV",   "600 USD+ + token", "Niveau pro, validations instantanees"],
    ],
    col_widths=[4.0, 4.0, 8.0],
)

add_heading(2, "15.3. Release via GitHub Actions")
add_code(
    "git tag v1.0.0 && git push origin v1.0.0\n"
)
add_para(
    "Le workflow .github/workflows/release.yml : 1) build sur runner Windows, "
    "2) sign si secrets CERT_PFX_BASE64 + CERT_PASSWORD configures, "
    "3) upload du ZIP + SHA + manifest dans la release GitHub, "
    "4) publish manifest.json sur gh-pages pour l'auto-updater."
)

add_heading(2, "15.4. Installer Inno Setup")
add_para("build_scripts/installer.iss produit RiskPulse-Setup-1.0.0.exe qui installe dans Program Files, cree raccourci menu demarrer.")
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 16. TESTS
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "16. Validation : resultats des tests")

add_heading(2, "16.1. Smoke test (tests/smoke_test.py) : 12 / 12 OK")
for c in [
    "Core imports : tous les engines importables",
    "UI imports : toutes les vues importables",
    "API imports : FastAPI factory fonctionne",
    "Utils : paths, logger, errors",
    "Knowledge base : SQLite tables initialisees",
    "Auth bootstrap : compte admin/admin cree",
    "Permissions : 18 permissions x 3 roles",
    "i18n .qm present : fichiers .qm compiles pour 5 langues",
    "NLP pipeline : analyse complete sur texte de test",
    "Risk intelligence : scoring + crisis match",
    "PyVis offline : graphe genere sans CDN",
    "API factory : endpoints /v1/* enregistres",
]:
    add_bullet(c)

add_heading(2, "16.2. Updater E2E : 12 / 12 OK")
add_para("Comparaison SemVer (6 cas), manifest fetch + update detection, telechargement + verification SHA-256, rejet SHA mismatch, gestion gracieuse manifest unreachable.")

add_heading(2, "16.3. Licensing E2E : 7 / 7 OK")
for c in [
    "Trial auto au premier lancement (14 j)",
    "Activation PRO valide -> predictive ON, rest_api OFF",
    "Activation ENTERPRISE perpetuelle -> toutes features",
    "Cle expiree rejetee",
    "Signature forgee rejetee",
    "Cles malformees rejetees",
    "FREE gating apres expiration du trial",
]:
    add_bullet(c)

add_heading(2, "16.4. Telemetry E2E : 6 / 6 OK")
for c in [
    "Opt-out filtre tous les events",
    "Opt-in enregistre + agrege",
    "Crash capture meme en opt-out",
    "Scrub PATH + EMAIL effectif",
    "top_errors agregation correcte",
    "Export bundle contient telemetry.db + meta.json",
]:
    add_bullet(c)

add_heading(2, "16.5. Production evaluation")
add_table(
    ["Cas",                "Verdict attendu",     "Verdict RiskPulse",                  "OK"],
    [
        ["Credit Suisse 2023", "Lehman-like",         "similarite 0.82 / VaR99 -42%",        "OUI"],
        ["FTX 2022",           "PEP + fraud + Madoff","flagues, similarite Madoff 0.78",     "OUI"],
        ["Panama Papers 2016", "ESCALATE_SAR",        "11 paradis fiscaux, 6 PEP, escalate", "OUI"],
    ],
    col_widths=[4.0, 4.0, 6.0, 2.0],
)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 17. MAINTENANCE
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "17. Maintenance & support")

add_heading(2, "17.1. Emplacement des donnees utilisateur")
add_table(
    ["Plateforme", "Chemin"],
    [
        ["Windows", "%APPDATA%\\RiskPulse\\data\\"],
        ["macOS",   "~/Library/Application Support/RiskPulse/data/"],
        ["Linux",   "~/.config/RiskPulse/data/"],
    ],
    col_widths=[4.0, 12.0],
)
add_para("Contient : knowledge.db, telemetry.db, preferences.json, session.json, license.json, logs/, exports/, cache/.")

add_heading(2, "17.2. Reinitialiser l'application")
add_para("Fermez l'app puis supprimez le dossier ci-dessus. Au relancement, tout repart a zero (compte admin/admin recree, trial redemarre).")

add_heading(2, "17.3. Logs")
add_para("%APPDATA%\\RiskPulse\\data\\logs\\")
add_bullet("riskpulse.log (rotation 5 Mo x 5 fichiers)")
add_bullet("errors.log (uniquement les ERROR et CRITICAL)")

add_heading(2, "17.4. Demander de l'aide")
for i, step in enumerate([
    "Reproduire le bug.",
    "Sidebar -> Diagnostics -> Export support bundle.",
    "Envoyer le .zip a support@... (a definir) avec une description de ce que vous faisiez.",
], 1):
    doc.add_paragraph(f"{i}. {step}", style="List Number")
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 18. ROADMAP
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "18. Limites connues & roadmap")

add_heading(2, "18.1. Limites actuelles (v1.0.0)")
add_bullet("spaCy small models : precision NER inferieure aux modeles large (compromis taille binaire).")
add_bullet("OFAC SDN : seulement un echantillon embarque, a brancher sur la liste officielle en prod.")
add_bullet("LLM externes (Grok, Claude) : payants et facultatifs.")
add_bullet("Pas encore de version Mac / Linux signee (auto-updater Windows-only).")

add_heading(2, "18.2. Roadmap proposee")
add_table(
    ["Etape", "Sujet"],
    [
        ["12", "Web companion (lecture seule) : partage de dashboards par URL"],
        ["13", "Plugin system : patterns de crise tiers, sources custom"],
        ["14", "Marketplace patterns + sources"],
        ["15", "Mac / Linux builds signes"],
        ["16", "Mode collaboratif (LAN sync de la KB)"],
    ],
    col_widths=[2.5, 13.5],
)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 19. GLOSSAIRE
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "19. Glossaire")
add_table(
    ["Terme", "Definition"],
    [
        ["Entite",          "Personne morale, physique ou lieu detecte dans le texte"],
        ["Centralite",      "Mesure d'importance d'un noeud dans le graphe (PageRank + Betweenness)"],
        ["Score composite", "Note de risque 0..1 combinant 5 axes"],
        ["Pattern de crise","Profil historique pre-encode (Lehman, Madoff...)"],
        ["PEP",             "Politically Exposed Person, personne politiquement exposee"],
        ["SAR",             "Suspicious Activity Report, declaration de soupcon AML"],
        ["DD",              "Due Diligence, vigilance renforcee"],
        ["VaR 95 / 99",     "Value-at-Risk a 95% / 99% de confiance"],
        ["FATF",            "Financial Action Task Force"],
        ["OFAC",            "Office of Foreign Assets Control (US sanctions)"],
        ["ED25519",         "Algorithme de signature cryptographique elliptique"],
        ["Trial",           "Periode d'evaluation gratuite (14 j en plan ENTERPRISE)"],
        ["Manifest",        "JSON decrivant la derniere version dispo + URL + SHA"],
    ],
    col_widths=[4.0, 12.0],
)
page_break()

# ────────────────────────────────────────────────────────────────────────────
# 20. CREDITS
# ────────────────────────────────────────────────────────────────────────────

add_heading(1, "20. Credits & licence")
add_para(f"Auteur principal : {AUTHOR}", bold=True)
add_para("Email : a.chaibousaidou@edu.umi.ac.ma")
add_para("Annee : 2026")
add_para("Credit IA : assistance Claude (Anthropic) pour les iterations design/code.")
add_para("Licence code : voir LICENSE (proprietaire pour le binaire, dependances tierces sous leur licence respective, cf. NOTICE.md).")

add_heading(2, "Dependances majeures")
for d in [
    "PySide6 (LGPLv3)",
    "spaCy (MIT)",
    "scikit-learn (BSD-3)",
    "FastAPI (MIT)",
    "PyVis (BSD-3)",
    "reportlab (BSD-3)",
    "cryptography (Apache 2 / BSD)",
]:
    add_bullet(d)

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run(f"--- Fin du rapport ---")
run.italic = True
run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run(f"RiskPulse v1.0.0 -- {AUTHOR} -- {YEAR}")
run.italic = True
run.font.size = Pt(9)
run.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)

# ────────────────────────────────────────────────────────────────────────────
# SAVE
# ────────────────────────────────────────────────────────────────────────────

doc.save(OUT)
print(f"Saved: {OUT}")
print(f"Sections: {len(toc_entries)}")
print(f"Pages estimate: ~{40 + len([v for v in views if v[1]])}")
