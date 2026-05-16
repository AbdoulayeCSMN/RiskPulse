"""Test bout-en-bout du Banking Pack."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
db = Path("data/knowledge.db")
if db.exists(): db.unlink()

from controller.risk_controller import RiskController

# Texte volontairement riche en signaux AML
TEXT = """
Bank Al-Maghrib a annonce le gel des avoirs de la société offshore Cayman Trust Holdings
suite a une enquête de FinCEN. Cette société, domiciliée aux Iles Caimans, etait suspectée
de blanchiment via des operations de smurfing en cryptomonnaie.

Le ministre des Finances Ahmed Benali, ancien depute, dirigeait egalement WafaCash
Maroc qui collaborait avec une banque iranienne via des transferts vers la Syria.
Le LEI 549300ABCDE12345FG67 a ete identifie. Plusieurs IBAN MA64011519000001234567890
ont apparu dans les transactions.

Goldman Sachs et JPMorgan ont chacun finance le projet a hauteur de 500 millions USD.
Le code SWIFT GSBKUS33 a ete utilise. L'AMF et la SEC enquêtent conjointement avec OFAC
sur les liens entre l'entité et un fonds souverain au Panama.

Le pattern de layering observe est conforme aux methodes du FATF blacklist.
"""

ctrl = RiskController(language='fr')
print("=== Analyse ===")
analysis = ctrl.analyze_text(TEXT)
banking = analysis.get("banking", {})

print()
print("=== AML Summary ===")
summary = banking.get("summary", {})
print(f"  Verdict           : {summary.get('verdict')}")
print(f"  Critical entities : {summary.get('n_critical')}")
print(f"  High entities     : {summary.get('n_high')}")
print(f"  Identifiers       : {summary.get('n_identifiers')}")
print(f"  Headline alerts   : {summary.get('headline_alerts')}")
print()

print("=== Sectoral metrics ===")
for k, v in banking.get("sectoral_metrics", {}).items():
    print(f"  {k:18s}: {v}")
print()

print("=== Regulatory alerts ===")
for a in banking.get("regulatory_alerts", []):
    print(f"  [{a['severity'].upper():8s}] {a['code']:25s} {a['message']}")
print()

print("=== Flagged profiles (top 8) ===")
flagged = [p for p in banking.get("profiles", []) if p["flags"]]
flagged.sort(key=lambda p: -p["aml_score"])
for p in flagged[:8]:
    print(f"  {p['aml_verdict']:10s} {p['aml_score']:.2f}  {p['name']:30s}  cat={p['category']}")
    for f in p["flags"][:3]:
        print(f"      └── [{f['severity']:7s}] {f['code']:25s} {f['label']}")
print()

print("=== Identifiers detected ===")
ids = banking.get("identifiers", {})
for k, v in ids.items():
    if v:
        print(f"  {k.upper():5s}: {', '.join(v)}")
print()

# Test PDF SAR generation
try:
    from services.reports.sar_template import generate_sar_pdf, generate_dd_pdf
    sar_path = "/tmp/test_sar.pdf"
    generate_sar_pdf(analysis, sar_path)
    import os
    print(f"=== SAR PDF generated : {os.path.getsize(sar_path):,} bytes ===")
    dd_path = "/tmp/test_dd.pdf"
    generate_dd_pdf(analysis, dd_path)
    print(f"=== DD PDF  generated : {os.path.getsize(dd_path):,} bytes ===")
except Exception as e:
    print(f"PDF generation failed : {e}")
