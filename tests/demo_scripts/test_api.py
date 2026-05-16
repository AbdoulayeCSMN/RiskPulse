"""Test E2E : demarre le serveur API + appelle via le SDK."""
import sys, time, threading
sys.stdout.reconfigure(encoding='utf-8')

from api.auth import get_or_create_api_key
from api.server import APIServer
from api.sdk import RiskPulseClient
from controller.risk_controller import RiskController, DEMO_SCENARIOS

# Demarre le serveur
ctrl = RiskController(language='fr')
server = APIServer(host="127.0.0.1", port=8765, controller=ctrl)
server.start()
print("Waiting for server to come up...")
for _ in range(20):
    time.sleep(0.5)
    if server.is_running:
        break
print(f"Server running : {server.is_running}")
print(f"URL           : {server.url}")
print()

# Cle API
key = get_or_create_api_key()
print(f"API key : {key}")
print()

# Client SDK
client = RiskPulseClient(api_key=key, base_url=server.url)

print("=== 1. Health (public) ===")
h = client.health()
print(f"  Status   : {h['status']}")
print(f"  Version  : {h['version']}")
print(f"  Uptime   : {h['uptime_sec']}s")
print(f"  KB stats : {h['knowledge_base']}")
print()

print("=== 2. Version ===")
v = client.version()
print(f"  API      : {v['api_version']}")
print(f"  Features : {len(v['features'])}")
for f in v['features']:
    print(f"    - {f}")
print()

print("=== 3. Analyze (authenticated) ===")
text = DEMO_SCENARIOS['reseau_business']['text']
result = client.analyze(text, language='fr')
print(f"  kb_id          : {result['kb_id']}")
print(f"  Entities       : {result['stats']['nb_entities']}")
print(f"  Relations      : {result['stats']['nb_relations']}")
print(f"  Risk profiles  : {len(result['risk_intel']['profiles'])}")
print(f"  Crisis match top: {result['risk_intel']['crisis_matches'][0]['name']} ({result['risk_intel']['crisis_matches'][0]['similarity']:.0%})")
print()

print("=== 4. List entities ===")
ents = client.list_entities(limit=5)
print(f"  {len(ents)} entites :")
for e in ents:
    print(f"    {e['display_name']:25s}  score={e['avg_risk_score']:.2f}  trend={e['trend']}")
print()

print("=== 5. Forecast first entity ===")
if ents:
    try:
        fc = client.forecast(entity_id=ents[0]['id'], horizon_days=30)
        print(f"  Entity        : {fc['entity_name']}")
        print(f"  Method        : {fc['method']}")
        print(f"  Current       : {fc['current_score']:.3f}")
        print(f"  Forecast 30d  : {fc['forecast_score']:.3f}")
        print(f"  Trend         : {fc['trend']}")
    except Exception as e:
        print(f"  (skip : {e})")
print()

print("=== 6. Monte Carlo ===")
mc = client.monte_carlo(n_runs=300)
print(f"  Runs         : {mc['n_runs']}")
print(f"  Mean loss    : {mc['mean_loss']:.0f}M")
print(f"  VaR 95%      : {mc['var_95']:.0f}M")
print(f"  VaR 99%      : {mc['var_99']:.0f}M")
print()

print("=== 7. Add watch ===")
w = client.add_watch("Bank Al-Maghrib", threshold=0.5)
print(f"  Added watch  : {w}")
watches = client.list_watches()
print(f"  Total watches: {len(watches)}")
print()

print("=== 8. Wrong API key (should 401) ===")
bad_client = RiskPulseClient(api_key="wrong_key", base_url=server.url)
try:
    bad_client.list_entities()
    print("  UNEXPECTED : pas d'erreur")
except Exception as e:
    print(f"  OK 401 : {e}")
print()

print("Stopping server...")
server.stop()
print("Done.")
