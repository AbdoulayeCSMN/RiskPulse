"""Routes /watchlist /sources /alerts."""

from fastapi import APIRouter, Depends, HTTPException
from api.auth import require_api_key
from api.models import WatchRequest, WatchItem, SourceRequest, Alert
from services.watchlist import get_watchlist

router = APIRouter(tags=["monitoring"],
                    dependencies=[Depends(require_api_key)])


@router.get("/watchlist", response_model=list[dict])
def list_watches():
    return get_watchlist().list_watches()


@router.post("/watchlist", response_model=dict)
def add_watch(req: WatchRequest):
    wl = get_watchlist()
    wid = wl.add_watch(req.name, threshold=req.threshold, notes=req.notes)
    return {"id": wid, "name": req.name, "threshold": req.threshold}


@router.delete("/watchlist/{watch_id}")
def remove_watch(watch_id: int):
    get_watchlist().remove_watch(watch_id)
    return {"deleted": watch_id}


@router.get("/sources", response_model=list[dict])
def list_sources():
    return get_watchlist().list_sources()


@router.post("/sources", response_model=dict)
def add_source(req: SourceRequest):
    wl = get_watchlist()
    sid = wl.add_source(req.url, label=req.label, source_type=req.type)
    return {"id": sid, "url": req.url, "type": req.type}


@router.delete("/sources/{source_id}")
def remove_source(source_id: int):
    get_watchlist().remove_source(source_id)
    return {"deleted": source_id}


@router.get("/alerts")
def list_alerts(unread_only: bool = False, limit: int = 50):
    return get_watchlist().list_alerts(limit=limit, unread_only=unread_only)


@router.post("/alerts/mark-all-seen")
def mark_all_seen():
    get_watchlist().mark_all_seen()
    return {"status": "ok"}


@router.post("/monitor/run")
def run_monitoring_cycle():
    """Lance un cycle de monitoring synchrone (fetch sources + check watches)."""
    from services.monitoring_engine import get_engine
    from api.deps import get_controller
    engine = get_engine(controller=get_controller())
    try:
        result = engine.run_cycle(max_items_per_source=3)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
