# RiskPulse

**AI-powered risk mapping, propagation, and predictive analytics.**

RiskPulse extracts entities and relations from any text, builds a weighted
knowledge graph, and reveals systemic risks through AI-powered propagation
and counterfactual simulations. It includes a persistent knowledge base,
continuous monitoring, multilingual translation, a banking compliance pack,
predictive forecasting, a REST API, and multi-user RBAC.

---

## Features

| Category          | Capability                                                  |
| ----------------- | ----------------------------------------------------------- |
| **Text analysis** | NLP entity / relation extraction (spaCy fr/en)              |
| **Risk scoring**  | Composite 0-1 score per entity with explainable drivers     |
| **Crisis match**  | Topology similarity to 6 historical crises (Lehman, etc.)   |
| **Cascade**       | Quantified expected loss + VaR 95/99 in monetary units      |
| **Predictive**    | 30/60/90-day forecasts + Monte Carlo stress tests           |
| **Knowledge base**| Persistent SQLite store with fuzzy entity resolution        |
| **Monitoring**    | Watch lists + RSS sources + auto-cycle every 15 min         |
| **Enrichment**    | Wikidata + Wikipedia for every entity                       |
| **Banking pack**  | AML / KYC / FATF / sanctions / SAR & DD reports             |
| **Translation**   | 5 languages (EN / FR / AR / IT / ES) + RTL support          |
| **AI insights**   | LLM-powered natural language summaries (Grok/Claude)        |
| **REST API**      | FastAPI + Python SDK + auto-generated OpenAPI docs          |
| **Multi-user**    | 3 roles (Admin / Analyst / Viewer) + full audit log         |

---

## Quick start

```bash
# 1. Install Python 3.12+ and dependencies
pip install -r requirements.txt

# 2. Download the spaCy language models
python -m spacy download fr_core_news_sm
python -m spacy download en_core_web_sm

# 3. (Optional) compile translations
cd ui_qt/locales
python update_ts.py        # extract strings
python auto_translate.py   # translate fr/ar/it/es
python compile_qm.py       # compile .qm

# 4. Launch
python main_qt.py
```

**Default credentials** : `admin` / `admin`. Change them immediately from
the `Users & Audit` view after first login.

---

## Architecture

```
main_qt.py                    Entry point (login -> MainWindow)
controller/risk_controller.py Orchestrator
engines/
  nlp_engine.py               spaCy + regex NER + cooccurrence graph
  propagation_engine.py       SIR-adapted weighted propagation
  centrality_analyzer.py      PageRank + Betweenness + Closeness
  models.py                   IsolationForest vs GraphBased (2x2 matrix)
  risk_intelligence.py        Risk scoring + crisis match + cascades
  predictive_engine.py        Forecast + trends + Monte Carlo
  banking_pack.py             AML / KYC / sanctions detection
services/
  knowledge_base.py           SQLite store + entity resolution
  watchlist.py                Watch list + sources + alerts
  monitoring_engine.py        Background scrape + analyze + alert
  enrichment.py               Wikidata + Wikipedia client
  auth_service.py             PBKDF2 hashing + sessions
  permissions.py              18 permissions x 3 roles
api/                          REST API (FastAPI) + Python SDK
ui_qt/                        Premium minimalist PySide6 UI
utils/                        Logging + paths + error hooks
```

---

## User data location

In production builds (frozen), RiskPulse stores user data under:

| OS      | Path                                              |
| ------- | ------------------------------------------------- |
| Windows | `%APPDATA%\RiskPulse\data\`                       |
| macOS   | `~/Library/Application Support/RiskPulse/data/`   |
| Linux   | `~/.config/RiskPulse/data/`                       |

In source mode, data goes to `./data/`.

To force source mode in a frozen build (debugging) :
```
set RISKPULSE_DEV=1
```

---

## REST API

Start the API server from the `API & SDK` view, then:

```bash
# Health
curl http://localhost:8765/v1/health

# Analyze a text
curl -X POST http://localhost:8765/v1/analyze \
  -H "X-API-Key: <your_key>" \
  -H "Content-Type: application/json" \
  -d '{"text": "Bank Al-Maghrib announces...", "language": "fr"}'
```

Or via the Python SDK:
```python
from api.sdk import RiskPulseClient
c = RiskPulseClient(api_key="<your_key>", base_url="http://localhost:8765")
print(c.analyze("..."))
```

OpenAPI documentation auto-generated at `http://localhost:8765/docs`.

---

## License

Proprietary. All rights reserved.

(c) C. Abdoulaye
