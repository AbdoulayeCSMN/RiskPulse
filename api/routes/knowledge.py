"""Routes /entities : Knowledge Base."""

from fastapi import APIRouter, Depends, HTTPException, Query
from api.auth import require_api_key
from api.models import EntitySummary, EntityHistory
from services.knowledge_base import get_kb

router = APIRouter(prefix="/entities", tags=["knowledge"],
                    dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[EntitySummary])
def list_entities(search: str = Query("", description="Filtre par nom"),
                   limit: int = Query(50, ge=1, le=500)):
    """Liste les entites connues dans la Knowledge Base."""
    kb = get_kb()
    ents = kb.list_entities(search=search, limit=limit)
    return [EntitySummary(**{
        "id": e.id, "canonical_name": e.canonical_name,
        "display_name": e.display_name, "type_label": e.type_label,
        "first_seen": e.first_seen, "last_seen": e.last_seen,
        "n_analyses": e.n_analyses,
        "avg_risk_score": e.avg_risk_score, "max_risk_score": e.max_risk_score,
        "trend": e.trend,
    }) for e in ents]


@router.get("/{entity_id}", response_model=EntityHistory)
def get_entity(entity_id: int):
    """Detail complet d'une entite : profil + historique + voisins + enrichissement."""
    kb = get_kb()
    history = kb.get_entity_history(entity_id)
    if not history:
        raise HTTPException(status_code=404, detail="Entity not found")
    enrichment = kb.get_enrichment(entity_id)
    return EntityHistory(
        entity=history.get("entity", {}),
        appearances=history.get("appearances", []),
        neighbors=history.get("neighbors", []),
        enrichment=enrichment,
    )


@router.post("/{entity_id}/enrich")
def enrich_entity(entity_id: int, lang: str = Query("fr"),
                   force: bool = Query(False)):
    """Lance (ou re-lance avec force=true) l'enrichissement Wikidata+Wikipedia."""
    kb = get_kb()
    try:
        result = kb.enrich_entity(entity_id, lang=lang, force=force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Entity not found")
    return result
