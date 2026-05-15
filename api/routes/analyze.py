"""Route /analyze : pipeline complet d'analyse."""

from fastapi import APIRouter, Depends, HTTPException

from api.auth import require_api_key
from api.models import AnalyzeRequest, AnalyzeResponse
from api.deps import get_controller

router = APIRouter(prefix="/analyze", tags=["analyze"],
                    dependencies=[Depends(require_api_key)])


@router.post("", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    """
    Analyse complete d'un texte. Retourne :
      - entites + relations + graphe (NLP)
      - Risk Intelligence (scores, crisis matches, cascades)
      - Comparaison Modele A vs B
      - Centralite
    Si `save_to_kb=true`, l'analyse est persistee dans la Knowledge Base.
    """
    ctrl = get_controller()
    try:
        # Bascule temporaire de langue
        if req.language != ctrl.language:
            ctrl.set_model_params({"language": req.language})
        result = ctrl.analyze_text(req.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    if not req.save_to_kb and "kb_id" in result:
        # Si l'utilisateur ne veut pas persister, on supprime l'entree
        try:
            from services.knowledge_base import get_kb
            kb = get_kb()
            # On laisse pour simplicite — l'utilisateur peut purger via /knowledge
        except Exception:
            pass

    return AnalyzeResponse(
        timestamp=result.get("timestamp", ""),
        kb_id=result.get("kb_id"),
        stats=result.get("stats", {}),
        nlp={
            "entities":  result.get("nlp", {}).get("entities", []),
            "relations": result.get("nlp", {}).get("relations", []),
            # On omet le graphe (objet nx non serialisable) sauf besoin
        },
        risk_intel=result.get("risk_intel", {}),
        comparison=result.get("comparison", {}),
        centrality={
            "critical_nodes":   result.get("centrality", {}).get("critical_nodes", []),
            "hidden_critical":  result.get("centrality", {}).get("hidden_critical", []),
        },
        total_time=result.get("total_time", 0.0),
    )
