"""Test enrichissement Wikidata sur entites reelles."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from services.enrichment import enrich_name

print("=== Test 1 : Apple Inc. ===")
data = enrich_name("Apple Inc.", lang="en")
print(f"Status        : {data.status}")
print(f"Wikidata QID  : {data.wikidata_id}")
print(f"Label         : {data.wikidata_label}")
print(f"Description   : {data.wikidata_desc}")
print(f"Type          : {data.type_label}")
print(f"Country       : {data.country}")
print(f"City          : {data.city}")
print(f"Sector        : {data.sector}")
print(f"Founded       : {data.founded}")
print(f"Employees     : {data.employees}")
print(f"Website       : {data.website}")
print(f"Wikipedia     : {data.wikipedia_url}")
print(f"WP summary    : {(data.wikipedia_summary or '')[:120]}...")
print()

print("=== Test 2 : Bank Al-Maghrib ===")
data2 = enrich_name("Bank Al-Maghrib", lang="fr")
print(f"Status        : {data2.status}")
print(f"Wikidata QID  : {data2.wikidata_id}")
print(f"Label         : {data2.wikidata_label}")
print(f"Type          : {data2.type_label}")
print(f"Country       : {data2.country}")
print(f"Founded       : {data2.founded}")
print(f"Wikipedia     : {data2.wikipedia_url}")
print(f"WP summary    : {(data2.wikipedia_summary or '')[:120]}...")
print()

print("=== Test 3 : entite imaginaire ===")
data3 = enrich_name("Foobar Imaginary Corp XYZ123", lang="en")
print(f"Status        : {data3.status}")
print(f"Wikidata QID  : {data3.wikidata_id}")
print()

# Test cache
print("=== Test 4 : cache via KB ===")
from pathlib import Path
db = Path("data/knowledge.db")
if db.exists(): db.unlink()
from services.knowledge_base import get_kb
from controller.risk_controller import RiskController
ctrl = RiskController(language='fr')
kb = get_kb()

# Cree une entite manuellement
result = ctrl.analyze_text(
    "Apple Inc. a annoncé un partenariat avec Microsoft Corporation pour le secteur cloud."
)
print(f"Entities created : {kb.stats()['n_entities']}")

# Enrichit la 1ere
ents = kb.list_entities(limit=5)
if ents:
    eid = ents[0].id
    print(f"Enrichissement de : {ents[0].display_name} (id={eid})")
    enrich = kb.enrich_entity(eid)
    if enrich:
        print(f"  status={enrich.get('status')}")
        print(f"  label={enrich.get('wikidata_label')}")
        print(f"  qid={enrich.get('wikidata_id')}")
        print(f"  country={enrich.get('country')}")
        print(f"  type={enrich.get('type_label')}")
    # Re-fetch (devrait venir du cache)
    cached = kb.get_enrichment(eid)
    print(f"  Cache OK : {cached is not None}")
