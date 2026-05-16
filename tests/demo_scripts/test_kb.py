"""Test bout-en-bout : 2 analyses different, verifier accumulation KB."""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

# Reset DB pour ce test
from pathlib import Path
db = Path("data/knowledge.db")
if db.exists():
    db.unlink()

from controller.risk_controller import RiskController, DEMO_SCENARIOS
from services.knowledge_base import get_kb

ctrl = RiskController(language='fr')
kb = get_kb()

print("=== ETAT INITIAL ===")
print(json.dumps(kb.stats(), indent=2))
print()

# Analyse 1
print("=== ANALYSE 1 : Crise financière ===")
result1 = ctrl.analyze_text(DEMO_SCENARIOS['crise_financiere']['text'])
print(f"Analysis ID : {result1.get('kb_id')}")
print(f"Stats KB : {kb.stats()}")
print()

# Analyse 2
print("=== ANALYSE 2 : Reseau business ===")
result2 = ctrl.analyze_text(DEMO_SCENARIOS['reseau_business']['text'])
print(f"Analysis ID : {result2.get('kb_id')}")
print(f"Stats KB : {kb.stats()}")
print()

# Analyse 3 — meme texte (devrait remettre a jour les entites existantes)
print("=== ANALYSE 3 : meme crise financière (re-run) ===")
result3 = ctrl.analyze_text(DEMO_SCENARIOS['crise_financiere']['text'])
print(f"Stats KB : {kb.stats()}")
print()

# Top entités accumulees
print("=== TOP 8 ENTITES KNOWN ===")
entities = kb.list_entities(limit=8)
for e in entities:
    print(f"  {e.display_name:30s} | n_an={e.n_analyses} | "
          f"avg={e.avg_risk_score:.3f} | trend={e.trend}")
print()

# Detail d'une entite recurrente
if entities:
    eid = entities[0].id
    hist = kb.get_entity_history(eid)
    print(f"=== DETAIL : {entities[0].display_name} ===")
    print(f"Apparitions : {len(hist['appearances'])}")
    for a in hist['appearances']:
        print(f"  [{a['timestamp'][:16]}] score={a['risk_score']:.3f}  {a['verdict']}  {a['title'][:50]}")
    print(f"Voisins frequents : {hist['neighbors'][:5]}")
