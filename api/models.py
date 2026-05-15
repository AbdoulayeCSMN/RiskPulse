"""
RiskPulse API — Pydantic schemas (request / response).
"""

from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
#  COMMON
# ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    name: str = "RiskPulse"
    uptime_sec: float
    knowledge_base: dict


class VersionResponse(BaseModel):
    api_version: str
    server_version: str
    features: list[str]


# ─────────────────────────────────────────────
#  ANALYZE
# ─────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=20, max_length=200_000,
                       description="Texte a analyser (20-200000 caracteres)")
    language: str = Field("fr", pattern="^(fr|en|ar|it|es)$")
    save_to_kb: bool = True


class AnalyzeResponse(BaseModel):
    timestamp: str
    kb_id: Optional[int] = None
    stats: dict
    nlp: dict
    risk_intel: dict
    comparison: dict
    centrality: dict
    total_time: float


# ─────────────────────────────────────────────
#  ENTITIES
# ─────────────────────────────────────────────

class EntitySummary(BaseModel):
    id: int
    canonical_name: str
    display_name: str
    type_label: str
    first_seen: str
    last_seen: str
    n_analyses: int
    avg_risk_score: float
    max_risk_score: float
    trend: str


class EntityHistory(BaseModel):
    entity: dict
    appearances: list[dict]
    neighbors: list[dict]
    enrichment: Optional[dict] = None


# ─────────────────────────────────────────────
#  WATCHLIST
# ─────────────────────────────────────────────

class WatchRequest(BaseModel):
    name: str
    threshold: float = Field(0.6, ge=0.0, le=1.0)
    notes: str = ""


class WatchItem(BaseModel):
    id: int
    name: str
    threshold: float
    enabled: bool
    last_score: Optional[float] = None
    last_check: Optional[str] = None


class SourceRequest(BaseModel):
    url: str
    label: str = ""
    type: str = Field("rss", pattern="^(rss|url)$")


# ─────────────────────────────────────────────
#  ALERTS
# ─────────────────────────────────────────────

class Alert(BaseModel):
    id: int
    timestamp: str
    entity_name: str
    score: float
    delta: float
    verdict: str
    title: str
    message: str
    source_url: str
    seen: bool


# ─────────────────────────────────────────────
#  FORECAST / MONTE CARLO
# ─────────────────────────────────────────────

class ForecastRequest(BaseModel):
    entity_id: int
    horizon_days: int = Field(30, ge=1, le=365)


class MonteCarloRequest(BaseModel):
    n_runs: int = Field(1000, ge=100, le=10000)
    failure_prob: float = Field(0.15, ge=0.01, le=0.5)
