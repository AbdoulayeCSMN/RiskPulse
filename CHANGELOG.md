# Changelog

All notable changes to RiskPulse are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Licensing (Étape 10)
- Offline commercial activation via ED25519 cryptographic signatures.
- Plans : FREE (core), PRO (NLP avancé, Predictive, Banking, AI Insights),
  ENTERPRISE (REST API, multi-user, monitoring illimité, Wikidata enrichment).
- 14-day automatic trial granting ENTERPRISE features on first launch.
- Offline key generator (`tools/generate_license.py --init` + `--plan`).
- License view + activation dialog (Ctrl+L).
- Feature gating at navigation level + REST API server start.
- Trial countdown badge in topbar.
- Zero infrastructure cost : public key embedded, private key offline.

#### Telemetry & crash reports (Étape 11)
- Local-first diagnostics : SQLite store in `data/telemetry.db`, opt-in.
- Crash capture from `sys.excepthook` + `threading.excepthook` (always on,
  local-only — never sent over network).
- Automatic PII scrubbing : Windows/Unix home paths and emails replaced
  with `<HOME>` / `<EMAIL>` markers.
- Diagnostics view (sidebar) : recent crashes, top error types, feature
  usage counters, traceback viewer.
- Support bundle export : zips `telemetry.db` + `logs/` + meta into
  `data/exports/riskpulse-support-<ts>.zip` for manual email to support.
- Event counters : `app_start`, `app_quit`, `view_shown`, `feature_used`.
- Zero network egress by design.

## [1.0.0] - 2026-05-16

### Added

#### Engines
- NLP entity / relation extraction via spaCy (fr / en).
- Risk Intelligence engine : scoring composite, crisis matching against
  6 historical patterns (Lehman, LTCM, Enron, Wirecard, Madoff, Northern Rock),
  cascade impact estimation with VaR 95 / 99.
- Predictive engine : 30-day forecast with confidence interval,
  Monte Carlo stress test (1000 runs), crisis trajectory matching.
- Banking pack : AML / KYC scoring with FATF list, OFAC sanctions, tax-haven
  detection, PEP flagging, fraud / Ponzi / money-laundering vocabulary
  detection, SAR & Due Diligence PDF templates.
- IsolationForest vs GraphBased dual-model comparison with 2x2 detection
  matrix.

#### Platform
- Knowledge Base persistante (SQLite) with fuzzy entity resolution.
- Watch list + RSS source monitoring with auto-cycle every 15 min and
  threshold-based alerts.
- Wikidata + Wikipedia enrichment for every entity (cached locally).
- REST API (FastAPI) with auto-generated OpenAPI docs + Python SDK.
- Multi-user RBAC : Admin / Analyst / Viewer roles, PBKDF2 hashing,
  persistent sessions, full audit log.

#### UX
- Premium minimalist UI inspired by Linear / Raycast (JetBrains Mono).
- 5 languages : EN / FR / AR (RTL) / IT / ES.
- AI Insights view : LLM-powered natural language summaries (Grok / Claude).
- Welcome screen, command palette (Ctrl+K), toast notifications,
  splash screen, about dialog.

#### Distribution
- Windows portable exe (PyInstaller).
- Inno Setup installer.
- Auto-update mechanism with SHA-256 verification + rollback.
- Code-signing infrastructure (commercial cert or self-signed).
- GitHub Actions release workflow.

[Unreleased]: https://github.com/AbdoulayeCSMN/riskpulse/compare/v1.0.0...HEAD
[1.0.0]:      https://github.com/AbdoulayeCSMN/riskpulse/releases/tag/v1.0.0
