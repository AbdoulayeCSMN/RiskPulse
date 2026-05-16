"""
Evaluation de production sur 3 cas reels documentes.

Cas 1 : Credit Suisse / UBS (mars 2023) — fusion forcee suite a perte de confiance
Cas 2 : FTX collapse (novembre 2022) — interconnexions Alameda/FTX/regulateurs
Cas 3 : Reseau d'evasion fiscale offshore (style Panama Papers)

Pour chaque cas, on inspecte :
  - Entites extraites (precision NLP)
  - Risk profiles (verdicts crédibles ?)
  - Crisis matches (top 3 patterns historiques)
  - Cascade scenarios (ordres de grandeur)
  - Banking flags (AML / sanctions / FATF)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force UTF-8 stdout for Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from controller.risk_controller import RiskController
from engines.banking_pack import BankingAnalyzer


# ─────────────────────────────────────────────
#  TEXTES REELS (basés sur faits publics documentés)
# ─────────────────────────────────────────────

CASE_1_CREDIT_SUISSE = """
Le Conseil federal suisse a annonce le rachat d'urgence de Credit Suisse par UBS pour
3 milliards de francs suisses, sous la pression de la FINMA et de la Banque Nationale
Suisse (BNS). Credit Suisse, l'une des plus grandes banques du monde, avait perdu la
confiance des marches apres des trimestres de pertes massives liees aux scandales Archegos
Capital Management et Greensill Capital. La BNS a fourni une ligne de liquidite de
100 milliards de francs suisses. Le rapport annuel de Credit Suisse avait revele des
faiblesses materielles dans les controles internes. Le PDG Ulrich Korner et le president
Axel Lehmann ont fait l'objet de critiques sur la gestion de crise. Les obligations
AT1 emises par Credit Suisse ont ete depreciees a zero, declenchant des poursuites de
detenteurs internationaux. JPMorgan Chase et Goldman Sachs avaient signale des sorties
de capitaux massives dans les semaines precedentes. La fusion cree un geant bancaire
suisse avec plus de 5000 milliards d'actifs sous gestion.
"""

CASE_2_FTX = """
La plateforme d'echange de cryptomonnaies FTX, dirigee par Sam Bankman-Fried, a depose
le bilan apres la revelation de transferts de fonds clients vers Alameda Research, son
hedge fund partenaire. Alameda Research detenait un portefeuille massif de tokens FTT
emis par FTX, creant un risque de contagion. Binance, initialement interessee par un
rachat, s'est retiree apres examen des comptes. Le PDG Sam Bankman-Fried a ete arrete
aux Bahamas et extrade vers les Etats-Unis. La SEC, le DOJ et la CFTC ont ouvert des
enquetes simultanees. FTX International etait enregistree aux Bahamas, FTX US au
Delaware. Les fonds Sequoia Capital et SoftBank avaient investi des centaines de millions
dans FTX et ont passe leur participation a zero. Caroline Ellison, ex-PDG d'Alameda, a
plaide coupable et coopere avec les procureurs. Plus de 1 million de creanciers sont
affectes, pour un trou estime entre 6 et 8 milliards USD.
"""

CASE_3_OFFSHORE_NETWORK = """
Une enquete journalistique internationale a revele un reseau complexe d'evasion fiscale
implique des structures dans les Iles Vierges Britanniques, le Panama et les Iles
Caimans. La societe Holding Ventures International, basee aux BVI, possede des
participations dans plusieurs filiales : Apex Trading Cayman, Meridian Capital Panama
et Sirius Trust Luxembourg. L'identite du beneficiaire effectif reste masquee derriere
plusieurs niveaux de nominees. Le ministre Mohammed Tazi, ancien membre du gouvernement
marocain, apparait comme administrateur de plusieurs de ces entites via le cabinet
Mossack Fonseca. Des transferts de fonds suspects entre Apex Trading et la societe
SwissPrivate Banking AG ont attire l'attention de la FINMA. Bank Al-Maghrib a ouvert
une enquete preliminaire. L'OCDE a inclus ces juridictions sur sa liste grise. Le total
des actifs masques est estime a plus de 500 millions USD.
"""


CASES = [
    {
        "id":      "case1",
        "title":   "Credit Suisse / UBS (mars 2023)",
        "text":    CASE_1_CREDIT_SUISSE,
        "expected_themes": [
            "banking crisis", "regulator intervention",
            "loss of confidence", "forced merger",
        ],
        "expected_crisis_match": ["Lehman Brothers", "Northern Rock"],
    },
    {
        "id":      "case2",
        "title":   "FTX collapse (nov. 2022)",
        "text":    CASE_2_FTX,
        "expected_themes": [
            "crypto exchange failure", "commingling client funds",
            "regulatory dragnet", "investor wipeout",
        ],
        "expected_crisis_match": ["Madoff", "Wirecard"],
    },
    {
        "id":      "case3",
        "title":   "Reseau offshore (style Panama Papers)",
        "text":    CASE_3_OFFSHORE_NETWORK,
        "expected_themes": [
            "tax evasion", "shell companies", "beneficial ownership opacity",
            "PEP exposure", "FATF jurisdictions",
        ],
        "expected_crisis_match": ["Wirecard", "Enron"],
    },
]


# ─────────────────────────────────────────────
#  ANALYSE
# ─────────────────────────────────────────────

def analyze_case(ctrl: RiskController, case: dict) -> dict:
    print("\n" + "=" * 80)
    print(f"  CASE {case['id'].upper()} :  {case['title']}")
    print("=" * 80)

    result = ctrl.analyze_text(case["text"])
    if "error" in result:
        print(f"  ❌ ANALYSIS FAILED : {result['error']}")
        return result

    # ── 1. Entites ──
    entities = result["nlp"]["entities"]
    print(f"\n[1] ENTITIES EXTRACTED  ({len(entities)})")
    for e in entities[:10]:
        print(f"    {e['name']:35s}  type={e.get('type_label', '?'):15s}  freq={e.get('frequency', 1)}")

    # ── 2. Risk profiles top 5 ──
    profiles = result["risk_intel"]["profiles"]
    print(f"\n[2] RISK PROFILES (top 5)")
    for p in profiles[:5]:
        drivers = ", ".join(f"{d['label']}={d['value']:.2f}" for d in p["drivers"][:3])
        print(f"    {p['verdict']:10s}  {p['score']:.2f}  {p['name']:30s}  [{drivers}]")

    # ── 3. Crisis matches ──
    crisis = result["risk_intel"]["crisis_matches"]
    print(f"\n[3] CRISIS PATTERN MATCHES (top 3)")
    for c in crisis[:3]:
        print(f"    {c['similarity']*100:5.1f}%  {c['name']} ({c['year']}, {c['sector']})")

    # ── 4. Cascades ──
    cascades = result["risk_intel"]["cascades"]
    print(f"\n[4] CASCADE SCENARIOS (top 3 nodes)")
    for c in cascades[:3]:
        print(f"    IF {c['source_name']} fails -> {c['expected_loss']:.0f}M expected loss")
        print(f"       VaR 95% = {c['var_95']:.0f}M, {c['affected_count']} entities, ~{c['propagation_days']}d propagation")

    # ── 5. AI Comparison ──
    comp = result["comparison"]["comparison"]
    print(f"\n[5] AI MODEL COMPARISON")
    print(f"    Both flag        : {comp.get('n_both', 0)}")
    print(f"    Only Model B     : {comp.get('n_only_b', 0)}  (hidden systemic risk)")
    print(f"    Only Model A     : {comp.get('n_only_a', 0)}  (individual anomaly)")
    print(f"    Verdict          : {comp.get('verdict_label', '?')}")
    if comp.get("only_b_flag"):
        for e in comp["only_b_flag"][:3]:
            print(f"      Hidden : {e['node_name']} (score B={e['score_b']:.2f})")

    # ── 6. Banking Pack ──
    print(f"\n[6] BANKING PACK (AML/KYC)")
    banking = BankingAnalyzer(result).analyze()
    summary = banking["summary"]
    print(f"    Verdict        : {summary['verdict']}")
    print(f"    Critical AML   : {summary['n_critical']}")
    print(f"    High AML       : {summary['n_high']}")
    alerts = banking.get("regulatory_alerts", [])
    if alerts:
        print(f"    Regulatory alerts :")
        for a in alerts:
            print(f"      [{a['severity'].upper():8s}] {a['message']}")
    # Top 3 entities by AML score
    bank_profs = banking["profiles"]
    bank_profs.sort(key=lambda p: -p["aml_score"])
    print(f"    Top 3 AML risk :")
    for p in bank_profs[:3]:
        if p["aml_score"] > 0:
            flags = ", ".join(f["code"] for f in p["flags"][:3])
            print(f"      {p['aml_verdict']:8s}  {p['aml_score']:.2f}  {p['name'][:25]:25s}  [{flags}]")

    return result


def main():
    bar = "=" * 80
    print("\n" + bar)
    print("    RISKPULSE -- PRODUCTION CREDIBILITY EVALUATION")
    print(bar)

    ctrl = RiskController(language="fr")

    for case in CASES:
        analyze_case(ctrl, case)

    print("\n" + "=" * 80)
    print("  Evaluation complete. See output above + manual interpretation below.")
    print("=" * 80)


if __name__ == "__main__":
    main()
