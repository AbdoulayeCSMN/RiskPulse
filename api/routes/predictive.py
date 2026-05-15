"""Routes /forecast et /monte-carlo."""

from fastapi import APIRouter, Depends, HTTPException
from api.auth import require_api_key
from api.models import ForecastRequest, MonteCarloRequest
from api.deps import get_controller
from services.knowledge_base import get_kb

router = APIRouter(tags=["predictive"],
                    dependencies=[Depends(require_api_key)])


@router.post("/forecast")
def forecast(req: ForecastRequest):
    """Prevision de risque pour une entite avec intervalle de confiance."""
    kb = get_kb()
    history = kb.get_entity_history(req.entity_id)
    if not history:
        raise HTTPException(status_code=404, detail="Entity not found")
    from engines.predictive_engine import RiskForecaster
    name = history.get("entity", {}).get("canonical_name", "Unknown").title()
    fc = RiskForecaster().forecast(
        name, req.entity_id, history.get("appearances", []),
        horizon_days=req.horizon_days
    )
    if not fc:
        raise HTTPException(status_code=400, detail="Not enough observations")
    return fc.to_dict()


@router.post("/monte-carlo")
def monte_carlo(req: MonteCarloRequest):
    """Stress test : N runs, distribution des pertes attendues."""
    ctrl = get_controller()
    G = ctrl.get_graph()
    if not G or G.number_of_nodes() == 0:
        raise HTTPException(status_code=400,
                             detail="No graph available. Run an analysis first.")
    from engines.predictive_engine import MonteCarloSimulator
    ents = {nid: {"sentences": []} for nid in G.nodes()}
    sim = MonteCarloSimulator(G, ents)
    result = sim.simulate(n_runs=req.n_runs, failure_prob=req.failure_prob)
    return result.to_dict()


@router.get("/trends")
def trend_leaderboard(top_n: int = 20):
    """Leaderboard des entites avec les tendances les plus inquietantes."""
    from engines.predictive_engine import TrendAnalyzer
    analyzer = TrendAnalyzer(get_kb())
    trends = analyzer.analyze_all(min_observations=1, top_n=top_n)
    return [t.to_dict() for t in trends]
