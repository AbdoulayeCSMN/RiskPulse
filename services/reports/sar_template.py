"""
Templates de rapport bancaires :
  - SAR (Suspicious Activity Report) — format reglementaire FinCEN-inspired
  - Due Diligence Report             — profil de contrepartie

Genere via ReportLab, mise en page premium monochrome.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as rl_canvas


# ─────────────────────────────────────────────
#  HELPERS DE LAYOUT
# ─────────────────────────────────────────────

PRIMARY = (0.09, 0.09, 0.10)        # near-black
ACCENT  = (0.62, 0.75, 0.62)        # subtle green
WARN    = (0.91, 0.75, 0.55)
ERROR   = (0.91, 0.63, 0.63)
MUTED   = (0.45, 0.45, 0.45)
TEXT    = (0.10, 0.10, 0.10)
LIGHT   = (0.93, 0.93, 0.93)


def _draw_header(c: rl_canvas.Canvas, W: float, H: float,
                 doc_type: str, doc_id: str):
    """Bandeau en tete : RISKPULSE + type de document."""
    c.setFillColorRGB(*PRIMARY)
    c.rect(0, H - 3.2 * cm, W, 3.2 * cm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(2 * cm, H - 1.5 * cm, "RISKPULSE")
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.7, 0.7, 0.7)
    c.drawString(2 * cm, H - 2.0 * cm, "AI-POWERED RISK MAPPING")
    # Doc type a droite
    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(1, 1, 1)
    c.drawRightString(W - 2 * cm, H - 1.5 * cm, doc_type)
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.7, 0.7, 0.7)
    c.drawRightString(W - 2 * cm, H - 2.0 * cm, f"ID  {doc_id}")
    c.drawRightString(W - 2 * cm, H - 2.5 * cm,
                       datetime.now().strftime("%Y-%m-%d  %H:%M"))


def _draw_footer(c: rl_canvas.Canvas, W: float, H: float, page_num: int):
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(*MUTED)
    c.drawString(2 * cm, 1.2 * cm,
                  "RiskPulse v1.0 · CONFIDENTIAL · for compliance use only")
    c.drawRightString(W - 2 * cm, 1.2 * cm, f"Page  {page_num}")


def _section_title(c, y, label):
    c.setFillColorRGB(*MUTED)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(2 * cm, y, label.upper())
    c.setStrokeColorRGB(*LIGHT)
    c.setLineWidth(0.5)
    c.line(2 * cm, y - 0.15 * cm, 18 * cm, y - 0.15 * cm)
    return y - 0.6 * cm


def _kv(c, y, key, value, value_color=None):
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(*MUTED)
    c.drawString(2.3 * cm, y, key.upper())
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(*(value_color or TEXT))
    c.drawString(7 * cm, y, str(value))
    return y - 0.55 * cm


def _wrap(text: str, max_chars: int = 90) -> list[str]:
    """Decoupe un texte en lignes pour PDF."""
    words = (text or "").split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def _ensure_room(c, y, needed_cm, W, H, page_num):
    """Si y < marge basse, saute de page."""
    if y < (needed_cm * cm + 2 * cm):
        _draw_footer(c, W, H, page_num)
        c.showPage()
        page_num += 1
        _draw_header(c, W, H, c._doc_type, c._doc_id)
        y = H - 4.5 * cm
    return y, page_num


# ─────────────────────────────────────────────
#  SAR — Suspicious Activity Report
# ─────────────────────────────────────────────

def generate_sar_pdf(analysis: dict, output_path: str):
    """
    Genere un PDF de SAR a partir d'une analyse RiskPulse.
    Sections :
      1. Header + executive summary
      2. Subject information (entites a haut risque AML)
      3. Suspicious activity description (flags + alertes)
      4. Supporting evidence (identifiers IBAN/BIC/LEI)
      5. Recommended actions
    """
    banking = analysis.get("banking", {})
    profiles = banking.get("profiles", [])
    alerts = banking.get("regulatory_alerts", [])
    identifiers = banking.get("identifiers", {})
    summary = banking.get("summary", {})

    doc_id = f"SAR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    c = rl_canvas.Canvas(output_path, pagesize=A4)
    c._doc_type = "SUSPICIOUS ACTIVITY REPORT"
    c._doc_id = doc_id
    W, H = A4
    page_num = 1
    _draw_header(c, W, H, c._doc_type, c._doc_id)

    y = H - 4.5 * cm

    # ── Executive summary ──
    y = _section_title(c, y, "Executive summary")
    verdict = summary.get("verdict", "STANDARD_KYC")
    verdict_color = (ERROR if verdict == "ESCALATION_REQUIRED" else
                     WARN if verdict == "ENHANCED_DUE_DILIGENCE" else
                     ACCENT)
    y = _kv(c, y, "Verdict",        verdict.replace("_", " "), verdict_color)
    y = _kv(c, y, "Critical risks", str(summary.get("n_critical", 0)))
    y = _kv(c, y, "High risks",     str(summary.get("n_high", 0)))
    y = _kv(c, y, "Identifiers",    str(summary.get("n_identifiers", 0)))
    y = _kv(c, y, "Total entities", str(len(profiles)))
    y -= 0.3 * cm

    # ── Subject information ──
    y = _section_title(c, y, "Subjects of interest")
    critical_subjects = [p for p in profiles
                          if p["aml_verdict"] in ("HIGH", "CRITICAL")
                          or p["sanctions_hit"] or p["pep_indicator"]]
    critical_subjects.sort(key=lambda p: -p["aml_score"])

    if not critical_subjects:
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColorRGB(*MUTED)
        c.drawString(2.3 * cm, y, "No subjects flagged at HIGH or CRITICAL level.")
        y -= 0.5 * cm
    else:
        for p in critical_subjects[:10]:
            y, page_num = _ensure_room(c, y, 3, W, H, page_num)
            # Nom + verdict
            c.setFont("Helvetica-Bold", 11)
            c.setFillColorRGB(*TEXT)
            c.drawString(2.3 * cm, y, f"• {p['name']}")
            vcol = (ERROR if p["aml_verdict"] == "CRITICAL" else
                    WARN  if p["aml_verdict"] == "HIGH"     else MUTED)
            c.setFont("Helvetica-Bold", 9)
            c.setFillColorRGB(*vcol)
            c.drawRightString(W - 2 * cm, y, p["aml_verdict"])
            y -= 0.45 * cm

            # Sous-ligne : category + AML score
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(*MUTED)
            cat = (p.get("category") or "entity").upper()
            c.drawString(2.5 * cm, y, f"Category : {cat}    AML score : {p['aml_score']:.2f}")
            y -= 0.4 * cm

            # Flags lines
            for f in p.get("flags", [])[:5]:
                c.setFont("Helvetica", 8)
                c.setFillColorRGB(*TEXT)
                c.drawString(2.5 * cm, y, f"  – [{f['code']}]  {f['label']}")
                if f.get("detail"):
                    y -= 0.32 * cm
                    c.setFillColorRGB(*MUTED)
                    for line in _wrap(f["detail"], 100)[:2]:
                        c.drawString(3 * cm, y, line)
                        y -= 0.32 * cm
                y -= 0.35 * cm
            y -= 0.2 * cm

    # ── Regulatory alerts ──
    y, page_num = _ensure_room(c, y, 3, W, H, page_num)
    y = _section_title(c, y, "Regulatory alerts")
    if not alerts:
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColorRGB(*MUTED)
        c.drawString(2.3 * cm, y, "No regulatory alerts triggered.")
        y -= 0.5 * cm
    else:
        for a in alerts:
            sev_color = (ERROR if a["severity"] == "critical" else
                         WARN  if a["severity"] == "high"     else MUTED)
            c.setFont("Helvetica-Bold", 9)
            c.setFillColorRGB(*sev_color)
            c.drawString(2.3 * cm, y, f"[{a['severity'].upper()}]  {a['code']}")
            y -= 0.4 * cm
            c.setFont("Helvetica", 9)
            c.setFillColorRGB(*TEXT)
            for line in _wrap(a["message"], 95):
                c.drawString(2.5 * cm, y, line)
                y -= 0.4 * cm
            y -= 0.1 * cm

    # ── Supporting evidence : identifiers ──
    y, page_num = _ensure_room(c, y, 3, W, H, page_num)
    y = _section_title(c, y, "Supporting evidence — Identifiers")
    total_ids = sum(len(v) for v in identifiers.values())
    if total_ids == 0:
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColorRGB(*MUTED)
        c.drawString(2.3 * cm, y, "No IBAN/BIC/LEI codes extracted from the source text.")
        y -= 0.5 * cm
    else:
        for key, values in identifiers.items():
            if not values:
                continue
            c.setFont("Helvetica-Bold", 9)
            c.setFillColorRGB(*MUTED)
            c.drawString(2.3 * cm, y, key.upper())
            y -= 0.4 * cm
            c.setFont("Courier", 9)
            c.setFillColorRGB(*TEXT)
            for v in values:
                c.drawString(2.5 * cm, y, v)
                y -= 0.35 * cm
            y -= 0.2 * cm

    # ── Recommended actions ──
    y, page_num = _ensure_room(c, y, 4, W, H, page_num)
    y = _section_title(c, y, "Recommended actions")
    actions = _recommend_actions(summary, alerts, profiles)
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(*TEXT)
    for i, action in enumerate(actions, 1):
        for j, line in enumerate(_wrap(action, 95)):
            y, page_num = _ensure_room(c, y, 1, W, H, page_num)
            prefix = f"{i}. " if j == 0 else "   "
            c.drawString(2.3 * cm, y, prefix + line)
            y -= 0.42 * cm
        y -= 0.15 * cm

    _draw_footer(c, W, H, page_num)
    c.save()


# ─────────────────────────────────────────────
#  Due Diligence Report
# ─────────────────────────────────────────────

def generate_dd_pdf(analysis: dict, output_path: str):
    """
    Genere un PDF de Due Diligence : profil entites + crisis matches + cascade.
    Plus complet que le SAR : couvre tout, pas juste les flags AML.
    """
    nlp = analysis.get("nlp", {})
    stats = analysis.get("stats", {})
    risk_intel = analysis.get("risk_intel", {})
    banking = analysis.get("banking", {})

    doc_id = f"DD-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    c = rl_canvas.Canvas(output_path, pagesize=A4)
    c._doc_type = "DUE DILIGENCE REPORT"
    c._doc_id = doc_id
    W, H = A4
    page_num = 1
    _draw_header(c, W, H, c._doc_type, c._doc_id)

    y = H - 4.5 * cm

    # ── Overview ──
    y = _section_title(c, y, "Network overview")
    y = _kv(c, y, "Entities detected",  stats.get("nb_entities", 0))
    y = _kv(c, y, "Relations extracted", stats.get("nb_relations", 0))
    y = _kv(c, y, "Network density",    f"{stats.get('density', 0):.4f}")
    y = _kv(c, y, "Components",         stats.get("nb_components", 0))
    y = _kv(c, y, "Processing time",    f"{stats.get('processing_time', 0):.3f}s")
    y -= 0.3 * cm

    # ── Top risk profiles (RiskIntel) ──
    y = _section_title(c, y, "Top risk entities (composite scoring)")
    profiles = risk_intel.get("profiles", [])[:8]
    for p in profiles:
        y, page_num = _ensure_room(c, y, 2, W, H, page_num)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(*TEXT)
        c.drawString(2.3 * cm, y, f"• {p['name']}")
        c.setFont("Helvetica-Bold", 9)
        col = (ERROR if p["verdict"] == "CRITICAL" else
               WARN  if p["verdict"] == "HIGH"     else MUTED)
        c.setFillColorRGB(*col)
        c.drawRightString(W - 2 * cm, y, f"{p['verdict']}  {p['score']:.2f}")
        y -= 0.4 * cm
        # drivers
        drivers = p.get("drivers", [])
        if drivers:
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(*MUTED)
            drv_txt = "  ·  ".join(f"{d['label']} {d['value']:.2f}" for d in drivers)
            for line in _wrap(drv_txt, 100):
                c.drawString(2.5 * cm, y, line)
                y -= 0.35 * cm
        y -= 0.1 * cm

    # ── Crisis pattern matching ──
    y, page_num = _ensure_room(c, y, 4, W, H, page_num)
    y = _section_title(c, y, "Historical crisis pattern matching")
    for cr in risk_intel.get("crisis_matches", [])[:3]:
        y, page_num = _ensure_room(c, y, 2.5, W, H, page_num)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(*TEXT)
        c.drawString(2.3 * cm, y, f"{cr['name']} ({cr['year']})")
        c.setFont("Helvetica-Bold", 9)
        c.setFillColorRGB(*WARN)
        c.drawRightString(W - 2 * cm, y, f"{cr['similarity']*100:.0f}% similar")
        y -= 0.4 * cm
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(*MUTED)
        c.drawString(2.5 * cm, y, cr["sector"])
        y -= 0.32 * cm
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(*TEXT)
        for line in _wrap(cr["summary"], 100):
            c.drawString(2.5 * cm, y, line)
            y -= 0.35 * cm
        y -= 0.15 * cm

    # ── Cascades ──
    y, page_num = _ensure_room(c, y, 4, W, H, page_num)
    y = _section_title(c, y, "Cascade forecast")
    for cs in risk_intel.get("cascades", [])[:3]:
        y, page_num = _ensure_room(c, y, 1.5, W, H, page_num)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(*TEXT)
        c.drawString(2.3 * cm, y, f"If {cs['source_name']} fails →")
        y -= 0.4 * cm
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(*MUTED)
        c.drawString(2.5 * cm, y,
            f"Expected loss : {cs['expected_loss']:.0f}M   "
            f"VaR 95% : {cs['var_95']:.0f}M   "
            f"Entities hit : {cs['affected_count']}   "
            f"Propagation : {cs['propagation_days']}d")
        y -= 0.5 * cm

    # ── Banking summary ──
    if banking:
        y, page_num = _ensure_room(c, y, 4, W, H, page_num)
        y = _section_title(c, y, "AML & compliance signals")
        summary = banking.get("summary", {})
        sectoral = banking.get("sectoral_metrics", {})
        y = _kv(c, y, "AML verdict",  summary.get("verdict", "—").replace("_", " "))
        y = _kv(c, y, "Critical",     summary.get("n_critical", 0))
        y = _kv(c, y, "High",         summary.get("n_high", 0))
        y = _kv(c, y, "Banks detected", sectoral.get("n_banks", 0))
        y = _kv(c, y, "Regulators",     sectoral.get("n_regulators", 0))

    _draw_footer(c, W, H, page_num)
    c.save()


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _recommend_actions(summary: dict, alerts: list, profiles: list) -> list[str]:
    """Construit la liste des actions recommandees selon les findings."""
    actions = []
    verdict = summary.get("verdict", "STANDARD_KYC")

    if verdict == "ESCALATION_REQUIRED":
        actions.append(
            "Escalate immediately to the Money Laundering Reporting Officer (MLRO). "
            "File a Suspicious Activity Report with the competent Financial "
            "Intelligence Unit (FIU) within 30 days."
        )
    if any(a["code"] == "SANCTIONS_HIT" for a in alerts):
        actions.append(
            "Freeze pending transactions involving the sanctioned jurisdictions "
            "and notify the OFAC compliance team."
        )
    if any(a["code"] == "PEP_PRESENT" for a in alerts):
        actions.append(
            "Apply Enhanced Due Diligence (EDD) per FATF Recommendation 12. "
            "Verify source of funds and source of wealth for the identified PEP."
        )
    if any(a["code"] == "FATF_CONCENTRATION" for a in alerts):
        actions.append(
            "Review the concentration risk: more than 40% of entities are linked "
            "to FATF-listed jurisdictions. Document the rationale of the relationship."
        )
    if any(a["code"] == "TAX_HAVEN_PRESENT" for a in alerts):
        actions.append(
            "Document the economic substance of entities domiciled in tax havens. "
            "Verify beneficial ownership at minimum two levels deep."
        )
    if not actions:
        actions.append(
            "Standard customer due diligence (CDD) is sufficient. Continue periodic "
            "monitoring and re-assess if new exposure is detected."
        )
    actions.append(
        "Retain this report and all supporting evidence for the regulatory "
        "retention period (typically 5 to 10 years depending on jurisdiction)."
    )
    return actions
