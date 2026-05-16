# RiskPulse v1.0.0 — Rapport complet & guide utilisateur

> **Document de référence**
> Version : 1.0.0 (release 2026-05-16) · Étapes 10-11 incluses dans `[Unreleased]`
> Auteur : C. Abdoulaye · Cible : utilisateurs finaux **et** équipes techniques
> Format : markdown lisible dans n'importe quel éditeur ou GitHub

---

## Table des matières

1. [Synthèse exécutive](#1-synthèse-exécutive)
2. [Vision & cas d'usage](#2-vision--cas-dusage)
3. [Architecture générale](#3-architecture-générale)
4. [Les quatre moteurs d'analyse](#4-les-quatre-moteurs-danalyse)
5. [Plateforme — services transverses](#5-plateforme--services-transverses)
6. [Interface utilisateur](#6-interface-utilisateur)
7. [Internationalisation](#7-internationalisation)
8. [Guide d'installation pas à pas](#8-guide-dinstallation-pas-à-pas)
9. [Guide d'utilisation — du premier clic à l'analyse finie](#9-guide-dutilisation--du-premier-clic-à-lanalyse-finie)
10. [Tour complet des 18 vues](#10-tour-complet-des-18-vues)
11. [Référence des raccourcis clavier](#11-référence-des-raccourcis-clavier)
12. [API REST & SDK Python](#12-api-rest--sdk-python)
13. [Licensing offline (Étape 10)](#13-licensing-offline-étape-10)
14. [Telemetry & rapports d'erreur (Étape 11)](#14-telemetry--rapports-derreur-étape-11)
15. [Distribution, build & code-signing](#15-distribution-build--code-signing)
16. [Validation — résultats des tests](#16-validation--résultats-des-tests)
17. [Maintenance & support](#17-maintenance--support)
18. [Limites connues & roadmap](#18-limites-connues--roadmap)
19. [Glossaire](#19-glossaire)
20. [Crédits & licence](#20-crédits--licence)

---

## 1. Synthèse exécutive

**RiskPulse** est une application desktop d'analyse de risque alimentée par IA, packagée pour Windows en `.exe` portable. Elle transforme un texte brut (article de presse, rapport financier, dépêche AML…) en une **cartographie de risque** complète : entités extraites, scores de criticité, chaînes de propagation, comparaisons à 6 crises historiques, prédictions à 30 jours, alertes AML/KYC, et synthèses LLM.

| Caractéristique           | Valeur                                                       |
| ------------------------- | ------------------------------------------------------------ |
| Plateforme cible          | Windows 10 / 11 (build .exe portable + installer Inno Setup) |
| Stack                     | Python 3.12 · PySide6 (Qt6) · spaCy · scikit-learn · FastAPI |
| Langues UI                | 🇬🇧 EN · 🇫🇷 FR · 🇸🇦 AR (RTL) · 🇮🇹 IT · 🇪🇸 ES (≈ 1 180 entrées) |
| Vues métier               | 18 écrans organisés par domaine                              |
| Distribution              | Portable .exe (~ 250 Mo) · installeur · auto-updater SHA-256 |
| Licensing                 | ED25519 offline · 14 j trial · plans FREE/PRO/ENTERPRISE     |
| Réseau requis             | **Aucun** (sauf RSS / Wikidata / LLM optionnels)             |
| Couverture de tests       | 12 smoke · 12 updater · 7 licensing · 6 telemetry · prod-eval |
| Volume code               | ≈ 11 000 lignes Python · 65 modules                          |

**Pour qui ?** Compliance officers, analystes risque, journalistes d'investigation, équipes due diligence, chercheurs en intelligence économique.

**Promesse produit en une phrase** : *passer d'un article de 2 paragraphes à un dossier risque exploitable en moins de 10 secondes, sans envoyer la moindre donnée dans le cloud.*

---

## 2. Vision & cas d'usage

### 2.1. Le problème résolu

Un analyste risque reçoit en moyenne **50 à 200 signaux par jour** (RSS, alertes presse, rapports interne). Pour chaque signal il doit :

1. Identifier les entités citées (personnes morales, physiques, lieux).
2. Évaluer leur sévérité (PEP ? sanction ? mention d'évasion fiscale ?).
3. Croiser avec un historique pour détecter une dérive.
4. Estimer la propagation (qui d'autre est exposé ?).
5. Décider d'une action (KYC renforcé, SAR, escalade hiérarchique).

Les solutions existantes (Bloomberg, Refinitiv, Quantexa) coûtent **30 k€ à 200 k€/an** et imposent l'envoi des documents dans le cloud du vendeur.

### 2.2. La proposition de RiskPulse

- 100 % local, **aucune donnée n'est envoyée** (sauf si l'utilisateur active explicitement Wikidata ou un LLM externe).
- Un binaire portable, installation < 1 minute.
- Tarification accessible : trial 14 jours, puis PRO ~ 49 €/mois, ENTERPRISE ~ 199 €/mois.
- Code-base entièrement auditable.

### 2.3. Cas d'usage validés (cf. [tests/production_eval.py](tests/production_eval.py))

| Cas réel                  | Résultat RiskPulse                                            |
| ------------------------- | ------------------------------------------------------------- |
| **Credit Suisse 2023**    | Trajectoire détectée comme "Lehman-like", VaR 99 = -42 %       |
| **FTX / Sam Bankman-Fried 2022** | PEP flagué, fraude détectée, motif Madoff à 78 % de similarité |
| **Panama Papers (2016)**  | 11 paradis fiscaux identifiés, 6 PEP, verdict ESCALATE_SAR    |

---

## 3. Architecture générale

```
                ┌─────────────────────────────────────────────┐
                │              UI  (PySide6 / Qt6)            │
                │   18 vues · 5 langues · thèmes dark/light    │
                └──────────────┬──────────────────────────────┘
                               │ Signal/Slot Qt
                ┌──────────────▼──────────────────────────────┐
                │            controller/risk_controller.py    │
                │  Orchestrateur : pipeline 6 étapes          │
                └──┬───────┬──────────┬──────────┬────────────┘
                   │       │          │          │
        ┌──────────▼─┐ ┌───▼────┐ ┌───▼────┐ ┌───▼───────────┐
        │  Engines   │ │Services│ │ Utils  │ │ API (FastAPI) │
        │            │ │        │ │        │ │   /v1/...     │
        │  NLP       │ │  KB    │ │ paths  │ │   X-API-Key   │
        │  RiskIntel │ │  Auth  │ │ logger │ │               │
        │  Predictive│ │  Watch │ │ errors │ └───────────────┘
        │  Banking   │ │  Updater│
        │  Models    │ │ License │
        │  Propag.   │ │ Telem.  │
        └────────────┘ └─────────┘
                   │       │
                   ▼       ▼
              ┌─────────────────┐
              │ SQLite stores   │
              │  knowledge.db   │
              │  telemetry.db   │
              │  preferences    │
              │  license.json   │
              └─────────────────┘
```

### 3.1. Principes architecturaux

- **Séparation stricte** UI ↔ logique : aucun moteur n'importe Qt.
- **Singletons explicites** pour les services à état (KB, Auth, License, Telemetry).
- **Mode frozen-aware** : `utils/paths.py` route les écritures vers `%APPDATA%\RiskPulse\` en .exe, vers le repo en dev.
- **Threads non-bloquants** : monitoring, API, downloads tournent dans des threads dédiés ; jamais sur le thread Qt.

### 3.2. Le pipeline d'analyse (controller)

Quand l'utilisateur clique sur **Analyser**, le `RiskController` exécute 6 étapes :

```
┌────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐
│ 1. NLP │→ │ 2.Centra │→ │ 3.Models │→ │ 4. Risk │→ │ 5. KB   │→ │ 6.Notif│
│        │  │ -lity    │  │ IF + GB  │  │ Intel + │  │ persist │  │ UI     │
│ Entités│  │ PageRank │  │ Anomalie │  │ Banking │  │ Audit   │  │ event  │
│ +rel.  │  │ Between. │  │ matrice  │  │ Predic. │  │         │  │        │
└────────┘  └──────────┘  └──────────┘  └─────────┘  └─────────┘  └────────┘
   ~120ms     ~30ms         ~350ms        ~80ms        ~40ms       ~5ms
```

Total ≈ 600 ms pour un texte de 2 000 caractères.

---

## 4. Les quatre moteurs d'analyse

### 4.1. NLP Engine — [engines/nlp_engine.py](engines/nlp_engine.py)

| Aspect          | Détail                                                                  |
| --------------- | ----------------------------------------------------------------------- |
| Backend         | spaCy 3.7 (`fr_core_news_sm`, `en_core_web_sm`)                         |
| Sortie          | `List[Entity]` avec `name`, `type`, `centrality`, `sentences`, `severity` |
| Heuristiques    | Suffixes corporatifs (`LLC`, `SA`, `LTD`…) → forcent `ORGANISATION`     |
| Heuristiques    | Titres PEP (`ministre`, `président`, `sénateur`…) → forcent `PERSONNE`  |
| Désambiguïsation| Fuzzy match contre la KB (RapidFuzz ratio > 90)                          |
| Performances    | ≈ 1 500 caractères / 100 ms                                              |

### 4.2. Risk Intelligence Engine — [engines/risk_intelligence.py](engines/risk_intelligence.py)

Trois composants :

1. **RiskScorer** — note composite 0..1 calculée sur 5 axes : sentiment, centralité, mots-clés crise, mentions financières négatives, vélocité de citation.
2. **CrisisMatcher** — compare la trajectoire à 6 patterns historiques pré-encodés :
   - Lehman Brothers (2008) — illiquidité brusque, contagion banking
   - LTCM (1998) — leverage extrême + corrélations cachées
   - Enron (2001) — fraude comptable, off-balance vehicles
   - Wirecard (2020) — trous fiduciaires, audit défaillant
   - Madoff (2008) — Ponzi, returns trop lisses
   - Northern Rock (2007) — bank run, funding court terme
3. **CascadeEstimator** — propage le choc sur le graphe via PageRank personnalisé ; sortie : VaR 95 / VaR 99 estimés par entité.

### 4.3. Predictive Engine — [engines/predictive_engine.py](engines/predictive_engine.py)

- **RiskForecaster** : régression linéaire pondérée par exponentielle sur la série temporelle d'apparition de l'entité ; horizon 30 j avec bande de confiance 80 % / 95 %.
- **MonteCarloSimulator** : 1 000 trajectoires stochastiques (drift + volatilité ajustée) ; donne la distribution des pertes.
- **TrajectoryMatcher** : DTW (Dynamic Time Warping) entre la courbe observée et les 6 patterns de crise.

### 4.4. Banking Pack — [engines/banking_pack.py](engines/banking_pack.py)

Conformité bancaire / AML :

| Module             | Description                                                       |
| ------------------ | ----------------------------------------------------------------- |
| FATF Greylist      | 23 juridictions à surveillance renforcée                          |
| OFAC SDN           | Sanctions US (échantillon, non-exhaustif — à brancher en prod)    |
| Tax Havens         | Liste révisée (Suisse / Luxembourg **retirés** suite faux positifs) |
| PEP Detection      | Heuristique titre + nom dans la même phrase                       |
| Fraud Keywords     | détournement, evasion fiscale, fraude comptable, commingling…    |
| Verdict            | STANDARD_KYC · ENHANCED_DD · ESCALATE_SAR                         |

Templates PDF inclus : **SAR** (Suspicious Activity Report), **DD** (Due Diligence).

---

## 5. Plateforme — services transverses

### 5.1. Knowledge Base — [services/knowledge_base.py](services/knowledge_base.py)

Base SQLite (`data/knowledge.db`) avec 10 tables :

| Table                | Rôle                                              |
| -------------------- | ------------------------------------------------- |
| `analyses`           | Une ligne par analyse exécutée                    |
| `entities`           | Référentiel d'entités dédupliquées (fuzzy)        |
| `entity_appearances` | Liens analyse ↔ entité                            |
| `entity_cooccurrences` | Matrice de co-apparitions                       |
| `watchlist`          | Watches actifs                                    |
| `sources`            | Flux RSS / URL configurés                         |
| `source_items`       | Items déjà ingérés (anti-doublon)                 |
| `alerts`             | Alertes émises par le monitoring                  |
| `entity_enrichment`  | Cache Wikidata/Wikipedia                          |
| `users` + `audit_log`| Auth + traçabilité                                |

### 5.2. Watch & Monitoring — [services/monitoring_engine.py](services/monitoring_engine.py)

Cycle automatique toutes les 15 minutes :

1. Pour chaque source activée → fetch RSS/URL (3 items max).
2. Pour chaque item → pipeline d'analyse complète.
3. Pour chaque watch → si entité matchée et score > seuil → alerte.
4. Notification : badge sidebar + toast non-intrusif.

### 5.3. Enrichment Wikidata — [services/enrichment.py](services/enrichment.py)

Aucune clé API requise. Cache local (TTL 30 jours). Champs récupérés : description, image URL, instance_of, country, founded_year, employees.

### 5.4. Auth & RBAC — [services/auth_service.py](services/auth_service.py) + [services/permissions.py](services/permissions.py)

- Hash mots de passe : **PBKDF2-SHA256** 600 000 itérations.
- Sessions persistantes (token dans `data/session.json`).
- 3 rôles · 18 permissions :

| Permission             | Admin | Analyst | Viewer |
| ---------------------- | :---: | :-----: | :----: |
| RUN_ANALYSIS           |   ✓   |    ✓    |   ✓    |
| EXPORT_PDF             |   ✓   |    ✓    |   ✓    |
| MANAGE_WATCHLIST       |   ✓   |    ✓    |        |
| MANAGE_API             |   ✓   |         |        |
| MANAGE_USERS           |   ✓   |         |        |
| VIEW_AUDIT_LOG         |   ✓   |         |        |
| …                      |       |         |        |

Bootstrap : au premier lancement, compte `admin/admin` créé automatiquement (à changer impérativement).

### 5.5. Auto-updater — [services/updater.py](services/updater.py)

- Fetch manifest JSON signé (URL configurée dans `DEFAULT_MANIFEST_URL`).
- Comparaison SemVer (supporte `v` prefix et `-rc` suffix).
- Téléchargement avec barre de progression, vérification SHA-256.
- Script .bat de remplacement atomique + backup + rollback sur erreur.
- Ctrl+U pour vérifier manuellement, check silencieux toutes les 6 h.

---

## 6. Interface utilisateur

### 6.1. Philosophie design

Inspiration **Linear / Raycast** : noir presque pur, monochrome, JetBrains Mono, **aucun emoji**, accent unique #6F9FFF pour l'interactif. Densité élevée d'information sans surcharge visuelle.

### 6.2. Anatomie de la fenêtre principale

```
┌────────────────────────────────────────────────────────────────────┐
│  RISKPULSE │ AI-powered risk mapping...    TRIAL·14d  Admin  v1.0.1│  ← TopBar (52 px)
├────────────┬───────────────────────────────────────────────────────┤
│ NAVIGATION │                                                       │
│   Analysis │                                                       │
│   Risk Int │                                                       │
│   Predict. │                  STACKED  VIEW                        │
│   AML...   │                  (la vue active)                      │
│   ...      │                                                       │
│   License  │                                                       │
│   Settings │                                                       │
│            │                                                       │
│ © CA       │                                                       │
├────────────┴───────────────────────────────────────────────────────┤
│ STATUS: Ready                              RISKPULSE · V1.0.0      │  ← StatusBar
└────────────────────────────────────────────────────────────────────┘
   ↑ Sidebar (220 px, collapsible)
```

### 6.3. Composants premium

- **Card** : conteneur avec ombre douce, radius 8 px, hover subtil.
- **MetricCard** : grand chiffre + label + delta coloré.
- **CommandPalette** (Ctrl+K) : recherche fuzzy de toutes les commandes.
- **Toast** : notifications non-bloquantes en bas-droite, auto-dismiss.
- **UpdateDialog** : flux 3 étapes (check / download / install).

---

## 7. Internationalisation

Stack Qt natif : `QTranslator` + `.ts/.qm`. Cinq langues, **1 180 chaînes** :

| Code  | Langue          | RTL   | Captures                                          |
| ----- | --------------- | :---: | ------------------------------------------------- |
| `en`  | English         |       | ![EN](docs/screenshots/riskpulse_i18n_en.png)      |
| `fr`  | Français        |       | ![FR](docs/screenshots/riskpulse_i18n_fr.png)      |
| `ar`  | العربية         | ✓ RTL | ![AR](docs/screenshots/riskpulse_i18n_ar.png)      |
| `es`  | Español         |       | ![ES](docs/screenshots/riskpulse_i18n_es.png)      |
| `it`  | Italiano        |       | ![IT](docs/screenshots/riskpulse_i18n_it.png)      |

Le sélecteur en topbar applique la langue **instantanément** (signal `language_changed` → toutes les vues retraduisent via `retranslate()`). Pour l'arabe, `Qt.RightToLeft` est appliqué sur la fenêtre.

---

## 8. Guide d'installation pas à pas

### 8.1. Installation utilisateur (Windows .exe portable)

> **Public visé** : utilisateur final, aucune compétence technique requise.

1. **Téléchargez** `RiskPulse-1.0.0-portable.zip` depuis la page Releases GitHub.
2. **Vérifiez l'empreinte** (optionnel mais recommandé) :
   - Téléchargez aussi `RiskPulse-1.0.0.sha256`.
   - Ouvrez PowerShell, tapez :
     ```powershell
     Get-FileHash RiskPulse-1.0.0-portable.zip -Algorithm SHA256
     ```
   - Le hash affiché doit correspondre exactement à celui du fichier `.sha256`.
3. **Décompressez** le ZIP n'importe où (clé USB, Bureau, Documents). Aucun droit administrateur requis.
4. **Lancez** `RiskPulse\RiskPulse.exe` en double-cliquant.
5. Au premier lancement, Windows SmartScreen peut afficher *"Windows a protégé votre PC"*. Cliquez **Informations complémentaires** → **Exécuter quand même**. (Ce message disparaît avec un certificat OV/EV — cf. section 15.)
6. Le **splash screen** s'affiche pendant ~ 3 s, puis la fenêtre principale s'ouvre. **Vous êtes prêt.**

### 8.2. Installation dev (depuis le source)

```bash
git clone https://github.com/AbdoulayeCSMN/riskpulse.git
cd riskpulse
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download fr_core_news_sm
python -m spacy download en_core_web_sm
python ui_qt/locales/compile_qm.py
python main_qt.py
```

### 8.3. Première configuration recommandée

| Action                    | Comment                                                                    |
| ------------------------- | -------------------------------------------------------------------------- |
| Changer le mot de passe admin | Vue **Users & Audit** → ligne admin → Edit → set new password           |
| Choisir la langue         | TopBar → combo droit → sélectionner                                        |
| Choisir le thème          | Ctrl+T (toggle dark/light)                                                 |
| Activer une licence       | Ctrl+L → coller la clé → Activer (sinon le trial 14 j tourne)              |
| Activer la télémétrie locale | Sidebar **Diagnostics** → cocher *Enable local telemetry*               |

---

## 9. Guide d'utilisation — du premier clic à l'analyse finie

### 9.1. Écran d'accueil

![Welcome](docs/screenshots/riskpulse_qt_welcome_dark.png)

Quatre actions principales :

- **Run analysis** → ouvre la vue **Text Analysis**.
- **Random demo** → charge un scénario aléatoire parmi 6 cas pré-installés (Madoff, FTX, Wirecard, etc.) et lance le pipeline complet.
- **Recent analyses** → liste des dernières analyses (cliquables).
- **Knowledge base summary** → 4 KPIs.

### 9.2. Workflow type — analyse d'un article de presse

**Étape 1.** Cliquez **Run analysis** ou Ctrl+1.

**Étape 2.** Collez le texte (français ou anglais) dans la grande zone. Astuce : Ctrl+V suffit.

**Étape 3.** (Optionnel) Réglez les paramètres dans le panneau de droite :
- *Sensitivity* → contamination IsolationForest (0.05 ↔ 0.30).
- *Top critical* → nombre d'entités à mettre en avant (1 ↔ 10).

**Étape 4.** Cliquez **Analyze** (ou Ctrl+Enter). Une barre de progression s'affiche en bas, l'analyse prend < 1 s pour 2 000 caractères.

**Étape 5.** Le résultat s'affiche en **3 panneaux** :
- Gauche : table des entités triée par centralité.
- Centre : graphe interactif PyVis.
- Droite : score composite + verdict.

**Étape 6.** Explorez les autres vues — toutes sont **automatiquement nourries** par cette analyse :

| Pour voir…                                | Allez dans…           |
| ----------------------------------------- | --------------------- |
| Le score crise et la similarité Lehman    | Risk Intelligence     |
| La prévision à 30 j                       | Predictive            |
| Le verdict AML/KYC + PDF SAR              | AML & Compliance      |
| La synthèse LLM en français               | AI Insights           |
| Le graphe de propagation animé            | Risk Propagation      |
| Le diff IsolationForest vs GraphBased     | AI Comparison         |

**Étape 7.** Exportez ce que vous voulez :
- **PDF** : bouton *Export* en haut à droite de chaque vue.
- **Bundle complet** : Dashboard → Export ZIP (contient PDF, JSON, image graphe).

### 9.3. Conseils pratiques

> *"Si l'analyse dit que Crédit Suisse a une similarité Lehman > 70 %, ce n'est pas un oracle. C'est un signal qui mérite une vérification humaine. RiskPulse trie le bruit ; **vous** prenez la décision."*

- Analysez **plusieurs articles** sur le même sujet → la KB consolide automatiquement et la précision monte.
- Activez le **monitoring** sur Reuters / FT / Bloomberg RSS pour recevoir des alertes en continu.
- Pour les dossiers sensibles : **désactivez** la télémétrie et le LLM externe ; tout reste local.

---

## 10. Tour complet des 18 vues

### 10.1. Text Analysis
Entrée principale. Champ texte + paramètres + résultats triple-panneau.

### 10.2. Risk Intelligence
![Intelligence](docs/screenshots/riskpulse_qt_intelligence_dark.png)
Score composite, matrice de similarité aux 6 patterns historiques, projection VaR.

### 10.3. Predictive
![Predictive](docs/screenshots/riskpulse_qt_predictive.png)
Courbe historique + forecast 30 j avec bande de confiance, leaderboard des trajectoires les plus inquiétantes, distribution Monte Carlo.

### 10.4. AML & Compliance
![Banking](docs/screenshots/riskpulse_qt_banking.png)
Tableau entités avec flags PEP / sanctions / FATF / tax haven / fraud. Bouton *Generate SAR* et *Generate DD report*.

### 10.5. Knowledge Base
![Knowledge](docs/screenshots/riskpulse_qt_knowledge.png)
Recherche full-text + facettes (type, date, score). Click sur une entité → fiche détaillée + enrichment Wikidata.

### 10.6. Watch & Monitor
![Monitoring](docs/screenshots/riskpulse_qt_monitoring.png)
Trois onglets : *Watches*, *Sources*, *Alerts*. Boutons CRUD, status "Last cycle: 12 min ago", compteur d'alertes non lues.

### 10.7. AI Insights
![Insights](docs/screenshots/riskpulse_qt_insights_dark.png)
Synthèse LLM (Grok ou Claude) en langage naturel. Configurable dans Settings.

### 10.8. Risk Propagation
Graphe animé : pulses qui se propagent le long des arêtes selon le `propagation_engine`. Sliders pour decay et speed.

### 10.9. AI Comparison
![Comparaison](docs/screenshots/riskpulse_qt_comparaison_v2.png)
Matrice 2×2 : entités flaguées par les deux modèles, par un seul, par aucun. Permet d'évaluer la robustesse.

### 10.10. What-If Simulations
Modifier le poids d'une entité ou supprimer une arête et voir l'impact sur le graphe propagé.

### 10.11. Translation
Vue traduction de texte multi-langue (utilise deep-translator).

### 10.12. Dashboard
Vue d'ensemble exécutive : 8 KPIs + 3 graphes + export ZIP global.

### 10.13. Enrichment (intégré à la fiche entité)
![Enrichment](docs/screenshots/riskpulse_qt_enrichment.png)
Description Wikipédia, photo, métadonnées Wikidata.

### 10.14. API & SDK
![API](docs/screenshots/riskpulse_qt_api.png)
Start/Stop du serveur FastAPI. Affiche l'URL, le port, la clé API à copier-coller. Lien direct vers `/docs` Swagger.

### 10.15. Users & Audit
![Users](docs/screenshots/riskpulse_qt_users.png)
Liste des comptes (admin only), création, changement de rôle, reset password. Journal d'audit avec filtres.

### 10.16. License
![License](docs/screenshots/riskpulse_qt_license_dark.png)
État du plan, jours de trial restants, dialog d'activation. Détaillé section 13.

### 10.17. Diagnostics (Telemetry)
Crashes récents, top error types, feature usage, export support bundle. Détaillé section 14.

### 10.18. Settings
Paramètres du modèle (contamination, n_estimators, decay…), choix LLM, intervalle monitoring.

---

## 11. Référence des raccourcis clavier

| Raccourci         | Action                                  |
| ----------------- | --------------------------------------- |
| **Ctrl+K**        | Command Palette (recherche d'actions)   |
| **Ctrl+H**        | Retour à l'écran d'accueil              |
| **Ctrl+1 … Ctrl+9** | Navigation directe vers la N-ième vue |
| **Ctrl+T**        | Toggle thème dark/light                 |
| **Ctrl+U**        | Vérifier les mises à jour               |
| **Ctrl+L**        | Ouvrir la vue License                   |
| **Ctrl+Q**        | Quitter                                 |
| **F1**            | About RiskPulse                         |
| **Ctrl+Enter**    | Lancer l'analyse (depuis la vue Analyse) |
| **Esc**           | Fermer dialog / palette                 |

---

## 12. API REST & SDK Python

> ⚠️ La REST API est **ENTERPRISE-only** (ou trial). Tentative de démarrage en plan PRO → `PermissionError`.

### 12.1. Démarrage

Vue **API & SDK** → clic *Start server*. URL par défaut : `http://127.0.0.1:8765`. Documentation Swagger auto-générée à `/docs`.

### 12.2. Authentification

Toutes les routes (sauf `/v1/health`) exigent le header `X-API-Key`. La clé est affichée dans la vue API et stockée dans `data/preferences.json`.

### 12.3. Routes principales

| Méthode | Route                          | Description                          |
| ------- | ------------------------------ | ------------------------------------ |
| GET     | `/v1/health`                   | Ping (sans auth)                     |
| POST    | `/v1/analyze`                  | Analyse un texte                     |
| GET     | `/v1/knowledge/entities`       | Liste paginée des entités           |
| GET     | `/v1/knowledge/entities/{id}`  | Fiche détaillée                      |
| GET     | `/v1/monitoring/alerts`        | Alertes non lues                     |
| POST    | `/v1/monitoring/cycle`         | Forcer un cycle de monitoring        |
| GET     | `/v1/predictive/forecast/{eid}`| Forecast 30 j pour une entité       |

### 12.4. SDK Python

```python
from api.sdk.client import RiskPulseClient

client = RiskPulseClient("http://127.0.0.1:8765", api_key="…")

result = client.analyze("Crédit Suisse cherche un sauveteur, l'AT1 wipeout terrorise les obligataires.")
print(result["entities"])              # liste d'entités
print(result["risk_score"])            # score composite
print(result["crisis_match"]["lehman"]) # 0.78
```

---

## 13. Licensing offline (Étape 10)

### 13.1. Principe

Chaque licence est un texte unique : `<payload_b64>.<signature_b64>`.
Le payload contient `{plan, email, iat, exp}` et la signature est ED25519. Seul le détenteur de la clé privée peut forger une licence valide. La clé publique est embarquée dans l'app, donc la vérification se fait 100 % offline.

### 13.2. Cycle de vie

```
┌─────────────────────────────────────────────────────────┐
│  Premier lancement                                       │
│  ────────────────────                                    │
│  → Trial 14 j ENTERPRISE auto-démarré                    │
│  → Badge topbar : TRIAL · 14d                            │
│                                                          │
│  Jour 15 (sans achat)                                    │
│  ──────────────────────                                  │
│  → Plan retombe sur FREE                                 │
│  → Vues premium grisées + toast d'invite à l'achat       │
│                                                          │
│  Activation d'une clé PRO                                │
│  ─────────────────────────                               │
│  Ctrl+L → coller → Activer                               │
│  → Plan PRO actif, badge "PRO" en topbar                 │
│  → Predictive, Banking, AI Insights débloqués            │
│                                                          │
│  Activation ENTERPRISE                                   │
│  ──────────────────────                                  │
│  → Tout débloqué, dont REST API et multi-user           │
└─────────────────────────────────────────────────────────┘
```

### 13.3. Plans détaillés

| Feature                | FREE | PRO | ENTERPRISE |
| ---------------------- | :--: | :-: | :--------: |
| Analyse de texte       |  ✓   |  ✓  |     ✓      |
| Knowledge Base         |  ✓   |  ✓  |     ✓      |
| 5 langues UI           |  ✓   |  ✓  |     ✓      |
| Export PDF             |  ✓   |  ✓  |     ✓      |
| NLP avancé             |      |  ✓  |     ✓      |
| Predictive             |      |  ✓  |     ✓      |
| Banking Pack           |      |  ✓  |     ✓      |
| AI Insights (LLM)      |      |  ✓  |     ✓      |
| Audit log              |      |  ✓  |     ✓      |
| Watchlist              |      |  ✓  |     ✓      |
| REST API               |      |     |     ✓      |
| Multi-user RBAC        |      |     |     ✓      |
| Monitoring illimité    |      |     |     ✓      |
| Wikidata enrichment    |      |     |     ✓      |

### 13.4. Générer des clés (côté vendeur)

```bash
# Une seule fois : créer la paire
python tools/generate_license.py --init

# Pour chaque client
python tools/generate_license.py --plan PRO --email "alice@example.com" --days 365
python tools/generate_license.py --plan ENTERPRISE --email "bob@corp.com" --perpetual
```

La clé privée `tools/keys/riskpulse_private.pem` est **gitignored**. Ne jamais la diffuser. Si elle fuite : régénérer une paire, push une update avec la nouvelle clé publique → toutes les anciennes licences deviennent invalides.

---

## 14. Telemetry & rapports d'erreur (Étape 11)

### 14.1. Promesse de confidentialité

- **Aucun envoi réseau.** Tout reste sur la machine.
- Opt-in pour les événements (`feature_used`, `view_shown`…).
- Les crashes sont capturés même en opt-out, mais ne quittent pas la machine.
- Scrub automatique : `C:\Users\<nom>` → `<HOME>`, emails → `<EMAIL>`.

### 14.2. Vue Diagnostics

Quatre cartes :

1. **Opt-in toggle** + boutons *Export bundle* / *Clear*.
2. **Crashes table** + viewer de traceback.
3. **Top error types** (agrégation par type d'exception).
4. **Feature usage** (compteurs).

### 14.3. Envoyer un support bundle

1. Sidebar → **Diagnostics**.
2. Bouton **Export support bundle (.zip)**.
3. Le zip est créé dans `data/exports/riskpulse-support-<timestamp>.zip` et contient :
   - `telemetry.db` (toutes les données locales, déjà scrubbed)
   - `logs/riskpulse.log` + `logs/errors.log`
   - `meta.json` (version, OS, comptes événements)
4. Envoyez ce zip par email au support. Aucune autre donnée n'est nécessaire.

---

## 15. Distribution, build & code-signing

### 15.1. Build local

```bash
python build_scripts/release.py --version 1.0.0 \
    --notes-file CHANGELOG.md \
    --base-url "https://github.com/USER/riskpulse/releases/download/v1.0.0"
```

Sortie dans `dist/release/` :
- `RiskPulse-1.0.0-portable.zip` (~ 250 Mo)
- `RiskPulse-1.0.0.sha256`
- `manifest.json` (pour l'auto-updater)

### 15.2. Code-signing

| Type cert       | Prix annuel       | SmartScreen                              |
| --------------- | ----------------- | ---------------------------------------- |
| Self-signed     | 0 €               | "Unknown publisher" permanent            |
| Sectigo OV      | 80 – 150 USD      | Warning quelques jours puis OK           |
| DigiCert OV     | 400 – 500 USD     | Réputation immédiate                     |
| DigiCert EV     | 600 USD+ + token  | Niveau pro, validations instantanées     |

```powershell
# Avec cert PFX
.\build_scripts\sign.ps1 -CertFile cert.pfx -CertPassword "secret"

# Self-signed (dev only)
.\build_scripts\sign.ps1 -SelfSigned
```

### 15.3. Release via GitHub Actions

```bash
git tag v1.0.0 && git push origin v1.0.0
```

Le workflow `.github/workflows/release.yml` :
1. Build sur runner Windows
2. Sign si secrets `CERT_PFX_BASE64` + `CERT_PASSWORD` configurés
3. Upload du ZIP + SHA + manifest dans la release GitHub
4. Publish `manifest.json` sur `gh-pages` pour l'auto-updater

### 15.4. Installer Inno Setup

`build_scripts/installer.iss` → produit `RiskPulse-Setup-1.0.0.exe` qui installe dans `Program Files`, crée raccourci menu démarrer et entrée *Programs and Features*.

---

## 16. Validation — résultats des tests

### 16.1. Smoke test ([tests/smoke_test.py](tests/smoke_test.py)) — **12 / 12** ✅

| Check                    | Détail                                             |
| ------------------------ | -------------------------------------------------- |
| Core imports             | Tous les engines importables                        |
| UI imports               | Toutes les vues importables                         |
| API imports              | FastAPI factory fonctionne                          |
| Utils                    | paths, logger, errors                               |
| Knowledge base           | SQLite tables initialisées                          |
| Auth bootstrap           | Compte admin/admin créé                             |
| Permissions              | 18 permissions × 3 rôles                            |
| i18n .qm present         | Fichiers .qm compilés pour 5 langues                |
| NLP pipeline             | Analyse complète sur texte de test                  |
| Risk intelligence        | Scoring + crisis match                              |
| PyVis offline            | Graphe généré sans CDN                              |
| API factory              | Endpoints `/v1/*` enregistrés                       |

### 16.2. Updater E2E ([tests/test_updater.py](tests/test_updater.py)) — **12 / 12** ✅

- Comparaison SemVer (6 cas)
- Manifest fetch + update détection
- Téléchargement + vérification SHA-256
- Rejet SHA mismatch
- Gestion gracieuse manifest unreachable

### 16.3. Licensing E2E ([tests/test_licensing.py](tests/test_licensing.py)) — **7 / 7** ✅

- Trial auto au premier lancement (14 j)
- Activation PRO valide → predictive ON, rest_api OFF
- Activation ENTERPRISE perpétuelle → toutes features
- Cle expirée rejetée
- Signature forgée rejetée
- Clés malformées rejetées
- FREE gating après expiration du trial

### 16.4. Telemetry E2E ([tests/test_telemetry.py](tests/test_telemetry.py)) — **6 / 6** ✅

- Opt-out filtre tous les events
- Opt-in enregistre + agrège
- Crash capturé même en opt-out
- Scrub PATH + EMAIL effectif
- `top_errors` agrégation correcte
- Export bundle contient `telemetry.db` + `meta.json`

### 16.5. Production evaluation ([tests/production_eval.py](tests/production_eval.py))

| Cas                | Verdict attendu      | Verdict RiskPulse                | OK |
| ------------------ | -------------------- | -------------------------------- | -- |
| Credit Suisse 2023 | "Lehman-like"         | similarité 0.82 / VaR99 -42 %    | ✓  |
| FTX 2022           | PEP + fraud + Madoff  | flagués · similarité Madoff 0.78 | ✓  |
| Panama Papers      | ESCALATE_SAR          | 11 paradis fiscaux, 6 PEP, escalate | ✓  |

---

## 17. Maintenance & support

### 17.1. Emplacement des données utilisateur

| Plateforme | Chemin                                     |
| ---------- | ------------------------------------------ |
| Windows    | `%APPDATA%\RiskPulse\data\`                 |
| macOS      | `~/Library/Application Support/RiskPulse/data/` |
| Linux      | `~/.config/RiskPulse/data/`                |

Contient : `knowledge.db`, `telemetry.db`, `preferences.json`, `session.json`, `license.json`, `logs/`, `exports/`, `cache/`.

### 17.2. Réinitialiser l'application

Fermez l'app, puis supprimez le dossier ci-dessus. Au relancement, tout repart à zéro (compte admin/admin recréé, trial redémarré).

### 17.3. Logs

`%APPDATA%\RiskPulse\data\logs\`
- `riskpulse.log` (rotation 5 Mo × 5 fichiers)
- `errors.log` (uniquement les ERROR et CRITICAL)

### 17.4. Demander de l'aide

1. Reproduire le bug.
2. Sidebar → **Diagnostics** → **Export support bundle**.
3. Envoyer le `.zip` à `support@…` (à définir) avec une description de ce que vous faisiez.

---

## 18. Limites connues & roadmap

### 18.1. Limites actuelles (v1.0.0)

- spaCy small models : précision NER inférieure aux modèles `large` (compromis taille binaire).
- OFAC SDN : seulement un échantillon embarqué, à brancher sur la liste officielle en prod.
- LLM externes (Grok, Claude) : payants et facultatifs.
- Pas encore de version Mac / Linux signée (le build fonctionne mais l'auto-updater est Windows-only).

### 18.2. Roadmap proposée

| Étape | Sujet                                                            |
| :---: | ---------------------------------------------------------------- |
| 12    | Web companion (lecture seule) — partage de dashboards par URL    |
| 13    | Plugin system — patterns de crise tiers, sources custom          |
| 14    | Marketplace patterns + sources                                   |
| 15    | Mac / Linux builds signés                                        |
| 16    | Mode collaboratif (LAN sync de la KB)                            |

---

## 19. Glossaire

| Terme            | Définition                                                                  |
| ---------------- | --------------------------------------------------------------------------- |
| **Entité**       | Personne morale, physique ou lieu détecté dans le texte                     |
| **Centralité**   | Mesure d'importance d'un nœud dans le graphe (PageRank + Betweenness)       |
| **Score composite**| Note de risque 0..1 combinant 5 axes                                     |
| **Pattern de crise**| Profil historique pré-encodé (Lehman, Madoff…)                          |
| **PEP**          | Politically Exposed Person — personne politiquement exposée                |
| **SAR**          | Suspicious Activity Report — déclaration de soupçon AML                    |
| **DD**           | Due Diligence — vigilance renforcée                                        |
| **VaR 95 / 99**  | Value-at-Risk à 95 % / 99 % de confiance                                   |
| **FATF**         | Financial Action Task Force                                                 |
| **OFAC**         | Office of Foreign Assets Control (US sanctions)                            |
| **ED25519**      | Algorithme de signature cryptographique elliptique                          |
| **Trial**        | Période d'évaluation gratuite (14 j en plan ENTERPRISE)                    |
| **Manifest**     | JSON décrivant la dernière version dispo + URL + SHA                       |

---

## 20. Crédits & licence

- **Auteur principal** : C. Abdoulaye (a.chaibousaidou@edu.umi.ac.ma)
- **Crédit IA** : assistance Claude (Anthropic) pour les itérations design/code
- **Licence code** : voir `LICENSE` (propriétaire pour le binaire, dépendances tierces sous leur licence respective, cf. `NOTICE.md`)
- **Dépendances majeures** :
  - PySide6 (LGPLv3)
  - spaCy (MIT)
  - scikit-learn (BSD-3)
  - FastAPI (MIT)
  - PyVis (BSD-3)
  - reportlab (BSD-3)
  - cryptography (Apache 2 / BSD)

---

## Annexe A — Captures complémentaires

> Les captures référencées dans ce rapport vivent dans [docs/screenshots/](docs/screenshots/) et couvrent les vues principales en thème sombre.
> Pour régénérer une capture sur votre machine :
> ```bash
> PYTHONPATH=. python tests/demo_scripts/test_qt_screenshot.py <view_id> dark
> ```

| Fichier                                              | Vue              |
| ---------------------------------------------------- | ---------------- |
| `riskpulse_qt_welcome_dark.png`                      | Welcome          |
| `riskpulse_qt_intelligence_dark.png`                 | Risk Intelligence|
| `riskpulse_qt_predictive.png`                        | Predictive       |
| `riskpulse_qt_banking.png`                           | AML & Compliance |
| `riskpulse_qt_knowledge.png`                         | Knowledge Base   |
| `riskpulse_qt_monitoring.png`                        | Watch & Monitor  |
| `riskpulse_qt_insights_dark.png`                     | AI Insights      |
| `riskpulse_qt_comparaison_v2.png`                    | AI Comparison    |
| `riskpulse_qt_enrichment.png`                        | Entity Enrichment|
| `riskpulse_qt_api.png`                               | API & SDK        |
| `riskpulse_qt_users.png`                             | Users & Audit    |
| `riskpulse_qt_license_dark.png`                      | License          |
| `riskpulse_i18n_{en,fr,ar,es,it}.png`                | Each language    |
| `riskpulse_sar_demo.pdf` · `riskpulse_dd_demo.pdf`   | PDF outputs      |

---

*Fin du rapport — RiskPulse v1.0.0 — 2026-05-16.*
