"""Test E2E pour le monitoring : ajout watch + source, cycle, alertes."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

# Reset KB pour test propre
from pathlib import Path
db = Path("data/knowledge.db")
if db.exists():
    db.unlink()

from controller.risk_controller import RiskController, DEMO_SCENARIOS
from services.watchlist import get_watchlist
from services.monitoring_engine import get_engine

ctrl = RiskController(language='fr')
wl = get_watchlist()
engine = get_engine(controller=ctrl, on_alert=lambda a: print(f"  >>> ALERT! {a['entity_name']} {a['verdict']} {a['score']:.2f}"))

# 1) Setup : 2 entites surveillees avec seuils
print("=== SETUP WATCHLIST ===")
wl.add_watch("Investcorp Maroc", threshold=0.5)
wl.add_watch("Cashplus",         threshold=0.4)
wl.add_watch("Inexistant Corp",  threshold=0.3)
for w in wl.list_watches():
    print(f"  watching: {w['name']} (>= {w['threshold']:.2f})")
print()

# 2) Pas de RSS reel dans le test E2E (besoin internet) -> on simule via
#    une analyse manuelle qui declenchera les alertes.
print("=== SIMULATION : 2 analyses contenant ces entites ===")
analysis1 = ctrl.analyze_text(DEMO_SCENARIOS['crise_financiere']['text'])
analysis2 = ctrl.analyze_text(DEMO_SCENARIOS['reseau_business']['text'])

# Maintenant on appelle _check_alerts directement avec ces analyses
from services.feed_ingester import FeedItem
fake_item = FeedItem(title="Test news", summary="...", link="https://example.com/news/1")

watches_now = wl.list_watches(enabled_only=True)
print()
print("=== CHECK ALERTS sur analyse #1 (Crise financiere) ===")
n1 = engine._check_alerts(analysis1, watches_now, fake_item, analysis1.get("kb_id"))
print(f"  {n1} alerte(s) declenchee(s)")
print()
print("=== CHECK ALERTS sur analyse #2 (Reseau business) ===")
watches_now = wl.list_watches(enabled_only=True)
n2 = engine._check_alerts(analysis2, watches_now, fake_item, analysis2.get("kb_id"))
print(f"  {n2} alerte(s) declenchee(s)")
print()

# 3) Recap
print("=== RECAP FINAL ===")
print(f"Total alertes : {len(wl.list_alerts())}")
print(f"Non lues      : {wl.count_unread_alerts()}")
print()
for a in wl.list_alerts(limit=20):
    seen = " " if a["seen"] else "●"
    print(f"  {seen} [{a['timestamp'][11:16]}] {a['entity_name']:20s} {a['verdict']:8s} {a['score']:.2f}  {a['message'][:60]}")
