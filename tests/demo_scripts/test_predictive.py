"""Test predictive : forecast + trends + Monte Carlo + trajectory match."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
db = Path("data/knowledge.db")
if db.exists(): db.unlink()

from controller.risk_controller import RiskController, DEMO_SCENARIOS
from services.knowledge_base import get_kb
from engines.predictive_engine import (
    RiskForecaster, TrendAnalyzer, MonteCarloSimulator, TrajectoryMatcher
)

# 1) Genere de l'historique en lancant plusieurs analyses
ctrl = RiskController(language='fr')
kb = get_kb()
print("=== Generation historique : 3 analyses ===")
ctrl.analyze_text(DEMO_SCENARIOS['crise_financiere']['text'])
ctrl.analyze_text(DEMO_SCENARIOS['reseau_business']['text'])
# Reanalyse pour multiplier les occurrences
ctrl.analyze_text(DEMO_SCENARIOS['crise_financiere']['text'])
print(f"  -> {kb.stats()['n_analyses']} analyses, {kb.stats()['n_entities']} entites")
print()

# 2) Trend analysis
print("=== TREND LEADERBOARD ===")
analyzer = TrendAnalyzer(kb)
trends = analyzer.analyze_all(min_observations=1, top_n=10)
print(f"  Trends calcules : {len(trends)}")
for t in trends[:5]:
    d = t.to_dict()
    print(f"  {d['entity_name']:25s}  score={d['current_score']:.2f}  "
          f"d30={d['delta_30d']:+.2f}  mom={d['momentum']:+.5f}  "
          f"vol={d['volatility']:.2f}  trend={d['trend']}")
print()

# 3) Forecast detaille pour une entite
print("=== FORECAST : Investcorp Maroc ===")
ents = kb.list_entities(limit=10)
target = next((e for e in ents if "investcorp" in e.canonical_name), ents[0])
hist = kb.get_entity_history(target.id)
fc = RiskForecaster().forecast(target.display_name, target.id,
                                hist["appearances"], horizon_days=30)
if fc:
    print(f"  Entite          : {fc.entity_name}")
    print(f"  Observations    : {fc.n_observations}")
    print(f"  Method          : {fc.method}")
    print(f"  Current score   : {fc.current_score:.3f}")
    print(f"  Forecast 30d    : {fc.forecast_score:.3f}")
    print(f"  Trend           : {fc.trend}")
    print(f"  Momentum        : {fc.momentum:+.5f}/jour")
    print(f"  Volatility      : {fc.volatility:.3f}")
    print(f"  Forecast trajectory ({len(fc.forecast)} points):")
    for d, v in fc.forecast[:5]:
        print(f"    {d}  ->  {v:.3f}")
print()

# 4) Trajectory match
print("=== TRAJECTORY MATCH ===")
scores = [v for _, v in (fc.historical if fc else [])]
print(f"  Historical shape : {scores}")
matcher = TrajectoryMatcher()
matches = matcher.match(scores, min_points=2)
print(f"  Patterns testes  : {len(matches)}")
for m in matches[:3]:
    print(f"  {m.similarity*100:5.1f}%  {m.pattern_label}")
print()

# 5) Monte Carlo
print("=== MONTE CARLO STRESS TEST ===")
G = ctrl.get_graph()
ents = {eid: {"sentences": []} for eid in G.nodes()}
sim = MonteCarloSimulator(G, ents)
result = sim.simulate(n_runs=500, failure_prob=0.15)
print(f"  Runs           : {result.n_runs}")
print(f"  Mean loss      : {result.mean_loss:.0f}M")
print(f"  Median loss    : {result.median_loss:.0f}M")
print(f"  VaR 95%        : {result.var_95:.0f}M")
print(f"  VaR 99%        : {result.var_99:.0f}M")
print(f"  Max loss       : {result.max_loss:.0f}M")
print(f"  Histogram bins : {len(result.histogram)}")
print(f"  Worst scenarios:")
for s in result.worst_scenarios[:3]:
    print(f"    loss={s['loss']:.0f}M  failed={s['failed_nodes']}")
