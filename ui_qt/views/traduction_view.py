"""Vue Traduction — PySide6."""

import threading
import json
from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QFrame, QMessageBox, QFileDialog,
)

from ..components import Card
from ..i18n import tr, SUPPORTED_LANGUAGES
from ._base import build_header


SOURCE_TYPES = ["Full analysis report", "Critical nodes", "Model comparison", "Custom text"]


class TraductionView(QWidget):

    _translation_done  = Signal(str, str, str)   # (result, target_name, target_code)
    _translation_error = Signal(str)

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._history: list = []
        self._current_translation = ""
        self._build()
        self._translation_done.connect(self._on_done)
        self._translation_error.connect(self._on_error)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        self._caption_lbl, self._title_lbl = build_header(
            outer, tr("MODULE"), tr("Translation")
        )

        # Toolbar : source + langue + actions
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self._lbl_src_type = QLabel(tr("Source:"))
        self._lbl_src_type.setProperty("class", "subtitle")
        toolbar.addWidget(self._lbl_src_type)

        self._src_type_cb = QComboBox()
        for t in SOURCE_TYPES:
            self._src_type_cb.addItem(tr(t), userData=t)
        self._src_type_cb.currentIndexChanged.connect(self._on_src_type_changed)
        toolbar.addWidget(self._src_type_cb)

        self._lbl_target = QLabel(tr("Target:"))
        self._lbl_target.setProperty("class", "subtitle")
        toolbar.addWidget(self._lbl_target)

        self._target_cb = QComboBox()
        for code, name in SUPPORTED_LANGUAGES.items():
            if code != "fr":
                self._target_cb.addItem(name, userData=code)
        toolbar.addWidget(self._target_cb)

        toolbar.addStretch()

        self._btn_translate = QPushButton(tr("Translate"))
        self._btn_translate.setProperty("variant", "primary")
        self._btn_translate.clicked.connect(self._run_translation)
        toolbar.addWidget(self._btn_translate)

        self._btn_export = QPushButton(tr("Export PDF"))
        self._btn_export.clicked.connect(self._export_pdf)
        toolbar.addWidget(self._btn_export)

        outer.addLayout(toolbar)

        # Corps : source | cible (cote a cote)
        cols = QHBoxLayout()
        cols.setSpacing(20)

        self._src_card = Card(tr("Source text"))
        self._src_text = QTextEdit()
        self._src_text.setMinimumHeight(280)
        self._src_card.layout().addWidget(self._src_text)
        cols.addWidget(self._src_card)

        self._tgt_card = Card(tr("Translation"))
        self._tgt_text = QTextEdit()
        self._tgt_text.setReadOnly(True)
        self._tgt_text.setMinimumHeight(280)
        self._tgt_card.layout().addWidget(self._tgt_text)
        cols.addWidget(self._tgt_card)

        outer.addLayout(cols, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setProperty("class", "subtitle")
        outer.addWidget(self._status_lbl)

    # ── Source text ───────────────────────────

    def _on_src_type_changed(self, _idx):
        text = self._get_source_text()
        if text:
            self._src_text.setPlainText(text)

    def _get_source_text(self) -> str:
        src_type = self._src_type_cb.currentData()
        if src_type == "Custom text":
            return self._src_text.toPlainText().strip()

        if not self._controller or not self._controller.current_analysis:
            return self._src_text.toPlainText().strip()

        a = self._controller.current_analysis

        if src_type == "Full analysis report":
            stats = a.get("stats", {})
            nodes = a.get("centrality", {}).get("critical_nodes", [])
            comp  = a.get("comparison", {}).get("comparison", {})
            lines = [
                "RISKPULSE — ANALYSIS REPORT",
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "",
                "NETWORK",
                f"Entities: {stats.get('nb_entities', 0)}",
                f"Relations: {stats.get('nb_relations', 0)}",
                f"Density: {stats.get('density', 0):.4f}",
                "",
                "CRITICAL NODES",
            ]
            for i, n in enumerate(nodes[:5], 1):
                lines.append(f"  {i}. {n['name']} — score {n['composite']:.3f}")
            lines += [
                "",
                "MODEL COMPARISON",
                f"Model A: {comp.get('n_anomalies_a', 0)} anomalies",
                f"Model B: {comp.get('n_anomalies_b', 0)} anomalies",
                f"Agreement: {comp.get('agreement_rate', 0):.0%}",
            ]
            return "\n".join(lines)

        elif src_type == "Critical nodes":
            nodes = a.get("centrality", {}).get("critical_nodes", [])
            lines = ["CRITICAL NODES", ""]
            for i, n in enumerate(nodes, 1):
                lines.append(f"{i}. {n['name']} — type {n.get('type','?')} — score {n['composite']:.3f}")
            return "\n".join(lines)

        elif src_type == "Model comparison":
            comp = a.get("comparison", {}).get("comparison", {})
            return (
                f"MODEL A vs MODEL B\n\n"
                f"Model A (IsolationForest): {comp.get('n_anomalies_a',0)} anomalies\n"
                f"Model B (GraphBased)     : {comp.get('n_anomalies_b',0)} anomalies\n"
                f"Agreement rate: {comp.get('agreement_rate',0):.0%}\n\n"
                f"{comp.get('key_insight','')}"
            )

        return ""

    # ── Traduction ────────────────────────────

    def _run_translation(self):
        text = self._src_text.toPlainText().strip() or self._get_source_text()
        if not text:
            QMessageBox.warning(self, tr("Empty text"), tr("Nothing to translate."))
            return
        target_code = self._target_cb.currentData() or "en"
        target_name = self._target_cb.currentText()

        self._tgt_text.clear()
        self._status_lbl.setText(f"{tr('Translating to')} {target_name}...")
        self._btn_translate.setEnabled(False)
        self._app.set_status(f"{tr('Translating to')} {target_name}...", "info", 0.5)

        def _job():
            try:
                result = self._translate(text, target_code)
                self._translation_done.emit(result, target_name, target_code)
            except Exception as e:
                self._translation_error.emit(str(e))

        threading.Thread(target=_job, daemon=True).start()

    def _translate(self, text: str, code: str) -> str:
        # deep-translator (synchrone)
        try:
            from deep_translator import GoogleTranslator
            chunks = [text[i:i+4500] for i in range(0, len(text), 4500)]
            parts = []
            for chunk in chunks:
                t = GoogleTranslator(source="auto", target=code).translate(chunk)
                parts.append(t or chunk)
            return "\n".join(parts)
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback : Google translate API publique
        try:
            import urllib.request, urllib.parse, json as _json
            encoded = urllib.parse.quote(text[:2000])
            url = (f"https://translate.googleapis.com/translate_a/single"
                   f"?client=gtx&sl=auto&tl={code}&dt=t&q={encoded}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = _json.loads(resp.read().decode())
            return "".join(part[0] for part in data[0] if part[0])
        except Exception:
            pass

        return f"[{tr('Translation unavailable')} — {code.upper()}]\n\n" + text[:800]

    def _on_done(self, translated: str, target_name: str, target_code: str):
        self._btn_translate.setEnabled(True)
        self._status_lbl.setText("")
        self._tgt_text.setPlainText(translated)
        self._current_translation = translated
        self._app.set_status(f"{tr('Translation complete')}: {target_name}", "success", 1.0)
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            "target": target_code,
            "source": self._src_text.toPlainText()[:200],
            "translation": translated[:200],
        })

    def _on_error(self, msg: str):
        self._btn_translate.setEnabled(True)
        self._status_lbl.setText("")
        QMessageBox.critical(self, tr("Translation error"), msg)

    # ── Export PDF ────────────────────────────

    def _export_pdf(self):
        if not self._current_translation:
            QMessageBox.warning(self, tr("Nothing to export"),
                                tr("Translate first."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Export PDF"), "translation.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4
            c = rl_canvas.Canvas(path, pagesize=A4)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, 800, "RiskPulse — Translation")
            c.setFont("Helvetica", 10)
            y = 770
            for line in self._current_translation.split("\n"):
                if y < 60:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = 800
                c.drawString(50, y, line[:100])
                y -= 14
            c.save()
            QMessageBox.information(self, tr("Export complete"), path)
        except ImportError:
            QMessageBox.warning(self, "ReportLab",
                                tr("Install reportlab to export PDF: pip install reportlab"))

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        pass

    def on_show(self):
        pass

    def retranslate(self):
        self._caption_lbl.setText(tr("MODULE"))
        self._title_lbl.setText(tr("Translation"))
        self._lbl_src_type.setText(tr("Source:"))
        self._lbl_target.setText(tr("Target:"))
        self._btn_translate.setText(tr("Translate"))
        self._btn_export.setText(tr("Export PDF"))
        self._src_card.set_title(tr("Source text"))
        self._tgt_card.set_title(tr("Translation"))
        # Rebuild source types
        cur = self._src_type_cb.currentData()
        self._src_type_cb.blockSignals(True)
        self._src_type_cb.clear()
        for t in SOURCE_TYPES:
            self._src_type_cb.addItem(tr(t), userData=t)
        idx = self._src_type_cb.findData(cur)
        if idx >= 0:
            self._src_type_cb.setCurrentIndex(idx)
        self._src_type_cb.blockSignals(False)
