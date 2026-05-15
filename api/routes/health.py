"""Routes /health et /version (publiques, sans auth)."""

import time
from fastapi import APIRouter

from api import __version__
from api.models import HealthResponse, VersionResponse
from services.knowledge_base import get_kb

router = APIRouter(tags=["system"])
_started_at = time.time()


@router.get("/health", response_model=HealthResponse)
def health():
    """Sante du service. Public, pas d'auth requise."""
    try:
        kb_stats = get_kb().stats()
    except Exception:
        kb_stats = {}
    return HealthResponse(
        status="ok",
        version=__version__,
        uptime_sec=round(time.time() - _started_at, 1),
        knowledge_base=kb_stats,
    )


@router.get("/version", response_model=VersionResponse)
def version():
    return VersionResponse(
        api_version="v1",
        server_version=__version__,
        features=[
            "analyze", "intelligence", "knowledge_base",
            "monitoring", "predictive", "enrichment", "banking_pack",
        ],
    )
