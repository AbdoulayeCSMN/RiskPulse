"""
Vue Banking Pack — AML / KYC / Compliance.

Trois sections :
  1. AML Overview     — metriques sectorielles + verdict global
  2. Flagged Entities — entites avec flags AML, par severite
  3. Regulatory Alerts + Identifiers (IBAN/BIC/LEI) + Export SAR
"""

import logging
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QMessageBox,
)

from ..components import Card, MetricCard
from ..i18n import tr
from ._base import build_header

logger = logging.getLogger(__name__)


SEVERITY_COLORS = {
    "critical": "#e8a0a0",
    "high":     "#e3c08e",
    "medium":   "#9caec1",
    "low":      "#84cc9e",
    "info":     "#52525b",
}

VERDICT_COLORS = {
    "CRITICAL":              "#e8a0a0",
    "HIGH":                  "#e3c08e",
    "MEDIUM":                "#9caec1",
    "LOW":                   "#84cc9e",
    "CLEAR":                 "#52525b",
    "ESCALATION_REQUIRED":   "#e8a0a0",
    "ENHANCED_DUE_DILIGENCE":"#e3c08e",
    "STANDARD_KYC":          "#84cc9e",
}

CATEGORY_ICONS = {
    "bank":         "⬢",
    "regulator":    "◆",
    "jurisdiction": "▲",
    "person":       "●",
    "entity":       "·",
}


class BankingView(QWidget):

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._build()

    # ── Construction ──────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        # Header
        head_row = QHBoxLayout()
        head_col = QVBoxLayout()
        self._caption_lbl, self._title_lbl = build_header(
            head_col, tr("VERTICAL · BANKING"), tr("AML & Compliance")
        )
        head_row.addLayout(head_col, 1)

        actions = QHBoxLayout()
        self._btn_sar = QPushButton(tr("Export SAR Report"))
        self._btn_sar.setProperty("variant", "primary")
        self._btn_sar.clicked.connect(self._export_sar)
        actions.addWidget(self._btn_sar)
        self._btn_dd = QPushButton(tr("Due Diligence PDF"))
        self._btn_dd.clicked.connect(self._export_dd)
        actions.addWidget(self._btn_dd)
        aw = QWidget(); aw.setLayout(actions)
        head_row.addWidget(aw, 0, Qt.AlignTop)
        outer.addLayout(head_row)

        self._subtitle = QLabel(tr(
            "Specialized analysis for banking, AML, KYC and regulatory compliance. "
            "Auto-detects sanctioned jurisdictions, FATF watch-list exposure, "
            "PEP indicators, tax-haven links and high-risk sectors."
        ))
        self._subtitle.setProperty("class", "subtitle")
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        # ── Verdict banner ──
        self._verdict_banner = self._build_verdict_banner()
        outer.addWidget(self._verdict_banner)

        # ── Sectoral metrics ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._stat_banks    = MetricCard(tr("Banks"),       "—")
        self._stat_regs     = MetricCard(tr("Regulators"),  "—")
        self._stat_persons  = MetricCard(tr("Persons"),     "—")
        self._stat_flagged  = MetricCard(tr("Flagged"),     "—")
        self._stat_avg_aml  = MetricCard(tr("Avg AML"),     "—")
        for s in (self._stat_banks, self._stat_regs, self._stat_persons,
                  self._stat_flagged, self._stat_avg_aml):
            s.setMinimumHeight(82)
            stats_row.addWidget(s)
        outer.addLayout(stats_row)

        # ── Corps : 2 colonnes ──
        body = QHBoxLayout()
        body.setSpacing(20)
        outer.addLayout(body, 1)

        # Colonne gauche : flagged entities
        self._flagged_card = Card(tr("Flagged Entities"))
        self._flagged_layout = QVBoxLayout()
        self._flagged_layout.setSpacing(6)
        self._flagged_placeholder = QLabel(tr("Run an analysis to populate."))
        self._flagged_placeholder.setProperty("class", "subtitle")
        self._flagged_placeholder.setAlignment(Qt.AlignCenter)
        self._flagged_layout.addWidget(self._flagged_placeholder)
        self._flagged_card.layout().addLayout(self._flagged_layout)
        body.addWidget(self._flagged_card, 6)

        # Colonne droite : alertes + identifiants
        right = QVBoxLayout()
        right.setSpacing(12)

        self._alerts_card = Card(tr("Regulatory Alerts"))
        self._alerts_layout = QVBoxLayout()
        self._alerts_layout.setSpacing(6)
        self._alerts_placeholder = QLabel(tr("Awaiting analysis..."))
        self._alerts_placeholder.setProperty("class", "subtitle")
        self._alerts_layout.addWidget(self._alerts_placeholder)
        self._alerts_card.layout().addLayout(self._alerts_layout)
        right.addWidget(self._alerts_card)

        self._ids_card = Card(tr("Bank Identifiers Detected"))
        self._ids_layout = QVBoxLayout()
        self._ids_layout.setSpacing(4)
        self._ids_placeholder = QLabel(tr("No IBAN/BIC/LEI detected yet."))
        self._ids_placeholder.setProperty("class", "subtitle")
        self._ids_layout.addWidget(self._ids_placeholder)
        self._ids_card.layout().addLayout(self._ids_layout)
        right.addWidget(self._ids_card)

        right_w = QWidget(); right_w.setLayout(right)
        body.addWidget(right_w, 4)

    def _build_verdict_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("api-banner")
        banner.setStyleSheet(
            "QFrame#api-banner {"
            "  background-color: #1a1a1f;"
            "  border: 1px solid #27272a;"
            "  border-radius: 4px;"
            "}"
        )
        lay = QHBoxLayout(banner)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(16)

        tag = QLabel("VERDICT")
        tag.setStyleSheet(
            "color: #52525b; font-weight: 700; letter-spacing: 1.5px; font-size: 9px;"
        )
        tag.setFixedWidth(80)
        lay.addWidget(tag)

        self._verdict_label = QLabel("—")
        self._verdict_label.setStyleSheet(
            "color: #e4e4e7; font-weight: 700; font-size: 14px; letter-spacing: 1px;"
        )
        lay.addWidget(self._verdict_label)

        lay.addStretch()

        self._verdict_msg = QLabel("")
        self._verdict_msg.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        self._verdict_msg.setWordWrap(True)
        lay.addWidget(self._verdict_msg, 2)

        return banner

    # ── Helpers ────────────────────────────

    def _clear(self, layout):
        while layout.count():
            it = layout.takeAt(0)
            w = it.widget()
            if w: w.deleteLater()

    # ── Rendu ──────────────────────────────

    def _render(self, banking: dict):
        profiles = banking.get("profiles", [])
        identifiers = banking.get("identifiers", {})
        alerts = banking.get("regulatory_alerts", [])
        sectoral = banking.get("sectoral_metrics", {})
        summary = banking.get("summary", {})

        # ── Sectoral metrics ──
        self._stat_banks.set_value(str(sectoral.get("n_banks", 0)))
        self._stat_regs.set_value(str(sectoral.get("n_regulators", 0)))
        self._stat_persons.set_value(str(sectoral.get("n_persons", 0)))
        self._stat_flagged.set_value(str(sectoral.get("n_flagged", 0)))
        self._stat_avg_aml.set_value(f"{sectoral.get('avg_aml', 0):.2f}")

        # ── Verdict banner ──
        verdict = summary.get("verdict", "STANDARD_KYC")
        verdict_color = VERDICT_COLORS.get(verdict, "#9ca3af")
        self._verdict_label.setText(verdict.replace("_", " "))
        self._verdict_label.setStyleSheet(
            f"color: {verdict_color}; font-weight: 700; font-size: 14px; letter-spacing: 1px;"
        )
        nc = summary.get("n_critical", 0)
        nh = summary.get("n_high", 0)
        ni = summary.get("n_identifiers", 0)
        msg_parts = []
        if nc: msg_parts.append(f"{nc} critical")
        if nh: msg_parts.append(f"{nh} high-risk")
        if ni: msg_parts.append(f"{ni} bank identifiers detected")
        self._verdict_msg.setText(" · ".join(msg_parts) if msg_parts else
                                    tr("No significant AML signals detected."))

        # ── Flagged entities ──
        self._clear(self._flagged_layout)
        flagged = [p for p in profiles if p.get("flags")]
        flagged.sort(key=lambda p: -p["aml_score"])
        if not flagged:
            ph = QLabel(tr("No entity flagged in this analysis."))
            ph.setProperty("class", "subtitle")
            ph.setAlignment(Qt.AlignCenter)
            self._flagged_layout.addWidget(ph)
        else:
            # Header
            header = QHBoxLayout()
            for txt, w in [("", 28), (tr("ENTITY"), 200),
                           (tr("AML"), 60), (tr("VERDICT"), 90),
                           (tr("FLAGS"), 0)]:
                lbl = QLabel(txt)
                lbl.setProperty("class", "caption")
                if w:
                    lbl.setFixedWidth(w)
                header.addWidget(lbl, 1 if not w else 0)
            hw = QWidget(); hw.setLayout(header)
            self._flagged_layout.addWidget(hw)
            sep = QFrame(); sep.setObjectName("divider"); sep.setFixedHeight(1)
            self._flagged_layout.addWidget(sep)

            for p in flagged[:20]:
                row = QHBoxLayout()
                row.setSpacing(8)
                row.setContentsMargins(0, 4, 0, 4)

                icon = QLabel(CATEGORY_ICONS.get(p["category"], "·"))
                icon.setStyleSheet("color: #9ca3af; font-size: 12px;")
                icon.setFixedWidth(28)
                row.addWidget(icon)

                name = QLabel(p["name"][:32])
                name.setStyleSheet("color: #e4e4e7; font-size: 11px;")
                name.setFixedWidth(200)
                row.addWidget(name)

                aml = QLabel(f"{p['aml_score']:.2f}")
                aml.setStyleSheet("color: #e4e4e7; font-size: 11px;")
                aml.setFixedWidth(60)
                row.addWidget(aml)

                vcol = VERDICT_COLORS.get(p["aml_verdict"], "#9ca3af")
                vl = QLabel(p["aml_verdict"])
                vl.setStyleSheet(
                    f"color: {vcol}; font-weight: 700; font-size: 9px; letter-spacing: 1px;"
                )
                vl.setFixedWidth(90)
                row.addWidget(vl)

                # Chips de flags
                flags_lay = QHBoxLayout()
                flags_lay.setSpacing(4)
                flags_lay.setContentsMargins(0, 0, 0, 0)
                for f in p["flags"][:4]:
                    chip = QLabel(f" {f['label']} ")
                    sev_color = SEVERITY_COLORS.get(f["severity"], "#52525b")
                    chip.setStyleSheet(
                        f"color: {sev_color}; font-size: 9px;"
                        f"border: 1px solid {sev_color}; border-radius: 3px;"
                        f"padding: 1px 5px; background-color: rgba(0,0,0,0.2);"
                    )
                    chip.setToolTip(f.get("detail", ""))
                    flags_lay.addWidget(chip)
                flags_lay.addStretch()
                fw = QWidget(); fw.setLayout(flags_lay)
                row.addWidget(fw, 1)

                rw = QWidget(); rw.setLayout(row)
                self._flagged_layout.addWidget(rw)
        self._flagged_layout.addStretch()

        # ── Regulatory alerts ──
        self._clear(self._alerts_layout)
        if not alerts:
            ph = QLabel(tr("No regulatory alerts."))
            ph.setProperty("class", "subtitle")
            self._alerts_layout.addWidget(ph)
        else:
            for a in alerts:
                block = QFrame()
                sev_color = SEVERITY_COLORS.get(a["severity"], "#52525b")
                block.setStyleSheet(
                    f"QFrame {{ border-left: 2px solid {sev_color}; padding-left: 10px; }}"
                )
                lay = QVBoxLayout(block)
                lay.setContentsMargins(10, 4, 0, 4)
                lay.setSpacing(2)
                top = QHBoxLayout()
                code = QLabel(a["code"])
                code.setStyleSheet(
                    f"color: {sev_color}; font-weight: 700; font-size: 9px; letter-spacing: 1px;"
                )
                top.addWidget(code)
                top.addStretch()
                sev = QLabel(a["severity"].upper())
                sev.setStyleSheet(f"color: {sev_color}; font-size: 9px;")
                top.addWidget(sev)
                lay.addLayout(top)
                msg = QLabel(a["message"])
                msg.setStyleSheet("color: #e4e4e7; font-size: 11px;")
                msg.setWordWrap(True)
                lay.addWidget(msg)
                self._alerts_layout.addWidget(block)

        # ── Identifiers ──
        self._clear(self._ids_layout)
        total_ids = sum(len(v) for v in identifiers.values())
        if total_ids == 0:
            ph = QLabel(tr("No IBAN, BIC or LEI codes detected in this text."))
            ph.setProperty("class", "subtitle")
            ph.setWordWrap(True)
            self._ids_layout.addWidget(ph)
        else:
            for key, values in identifiers.items():
                if not values:
                    continue
                lbl = QLabel(key.upper())
                lbl.setStyleSheet("color: #52525b; font-size: 9px; letter-spacing: 1px; padding-top: 4px;")
                self._ids_layout.addWidget(lbl)
                for v in values[:5]:
                    code = QLabel(v)
                    code.setStyleSheet(
                        "color: #e4e4e7; font-family: 'JetBrains Mono', monospace; font-size: 10px;"
                        "background-color: #16161a; padding: 2px 6px; border-radius: 3px;"
                    )
                    code.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    self._ids_layout.addWidget(code)

    # ── Exports ─────────────────────────────

    def _export_sar(self):
        if not self._controller or not self._controller.current_analysis:
            self._app.toast(tr("Run an analysis first"), "warning")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Export SAR Report"),
            f"SAR_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            from services.reports.sar_template import generate_sar_pdf
            generate_sar_pdf(self._controller.current_analysis, path)
            QMessageBox.information(self, tr("Export complete"), path)
            self._app.toast(tr("SAR report exported"), "success")
        except ImportError:
            QMessageBox.warning(self, "ReportLab",
                                tr("Install reportlab: pip install reportlab"))
        except Exception as e:
            QMessageBox.critical(self, tr("Export error"), str(e))

    def _export_dd(self):
        if not self._controller or not self._controller.current_analysis:
            self._app.toast(tr("Run an analysis first"), "warning")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Due Diligence PDF"),
            f"DueDiligence_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            from services.reports.sar_template import generate_dd_pdf
            generate_dd_pdf(self._controller.current_analysis, path)
            QMessageBox.information(self, tr("Export complete"), path)
            self._app.toast(tr("Due Diligence report exported"), "success")
        except Exception as e:
            QMessageBox.critical(self, tr("Export error"), str(e))

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        if not self._controller or not self._controller.current_analysis:
            return
        banking = self._controller.current_analysis.get("banking", {})
        self._render(banking)

    def on_show(self):
        self.on_analysis_updated()

    def retranslate(self):
        self._caption_lbl.setText(tr("VERTICAL · BANKING"))
        self._title_lbl.setText(tr("AML & Compliance"))
        self._subtitle.setText(tr(
            "Specialized analysis for banking, AML, KYC and regulatory compliance. "
            "Auto-detects sanctioned jurisdictions, FATF watch-list exposure, "
            "PEP indicators, tax-haven links and high-risk sectors."
        ))
        self._btn_sar.setText(tr("Export SAR Report"))
        self._btn_dd.setText(tr("Due Diligence PDF"))
        self._flagged_card.set_title(tr("Flagged Entities"))
        self._alerts_card.set_title(tr("Regulatory Alerts"))
        self._ids_card.set_title(tr("Bank Identifiers Detected"))
        self._stat_banks.set_label(tr("Banks"))
        self._stat_regs.set_label(tr("Regulators"))
        self._stat_persons.set_label(tr("Persons"))
        self._stat_flagged.set_label(tr("Flagged"))
        self._stat_avg_aml.set_label(tr("Avg AML"))
