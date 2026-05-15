"""
Vue AI Insights — interrogation Grok sur l'analyse courante.
Genere un resume executif + permet questions libres.
"""

import threading
import logging
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QMessageBox, QLineEdit, QPlainTextEdit, QInputDialog,
)

from ..components import Card
from ..i18n import tr, I18nManager
from ._base import build_header
from services.llm_service import (
    GrokClient, generate_executive_summary, ask_question,
    load_api_key, save_api_key,
)

logger = logging.getLogger(__name__)


class InsightsView(QWidget):

    _llm_done  = Signal(str, str)   # (text, question)
    _llm_error = Signal(str)

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._client = GrokClient()
        self._build()
        self._llm_done.connect(self._on_response)
        self._llm_error.connect(self._on_error)

    # ── Construction ───────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        self._caption_lbl, self._title_lbl = build_header(
            outer, tr("AI POWERED"), tr("AI Insights")
        )

        self._subtitle = QLabel(tr(
            "Grok analyzes your risk graph and explains findings in natural language."
        ))
        self._subtitle.setProperty("class", "subtitle")
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        # ── Banniere si pas de cle API ──
        self._api_banner = self._build_api_banner()
        outer.addWidget(self._api_banner)
        # Sync l'etat de la banniere maintenant que tout est construit
        self._refresh_banner()

        # ── Actions ──
        actions = QHBoxLayout()
        actions.setSpacing(10)

        self._btn_summary = QPushButton(tr("Generate Executive Summary"))
        self._btn_summary.setProperty("variant", "primary")
        self._btn_summary.setMinimumHeight(38)
        self._btn_summary.clicked.connect(self._gen_summary)
        actions.addWidget(self._btn_summary)

        self._btn_clear = QPushButton(tr("Clear"))
        self._btn_clear.clicked.connect(self._clear_output)
        actions.addWidget(self._btn_clear)

        actions.addStretch()

        # Modele utilise
        self._model_lbl = QLabel("MODEL  ·  grok-2-latest")
        self._model_lbl.setProperty("class", "caption")
        actions.addWidget(self._model_lbl)

        outer.addLayout(actions)

        # ── Output ──
        self._output_card = Card(tr("AI Output"))
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setMinimumHeight(360)
        self._output.setPlaceholderText(tr(
            "Click 'Generate Executive Summary' to let Grok analyze your data, "
            "or ask a specific question below."
        ))
        self._output_card.layout().addWidget(self._output)
        outer.addWidget(self._output_card, 1)

        # ── Question libre ──
        q_card = Card(tr("Ask a question"))
        q_layout = QHBoxLayout()
        q_layout.setSpacing(8)

        self._question_input = QLineEdit()
        self._question_input.setPlaceholderText(tr(
            "e.g. Which entities are the most exposed to systemic risk?"
        ))
        self._question_input.returnPressed.connect(self._ask)
        q_layout.addWidget(self._question_input, 1)

        self._btn_ask = QPushButton(tr("Ask Grok"))
        self._btn_ask.clicked.connect(self._ask)
        q_layout.addWidget(self._btn_ask)

        q_card.layout().addLayout(q_layout)
        outer.addWidget(q_card)

    def _build_api_banner(self) -> QFrame:
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
        lay.setContentsMargins(16, 12, 12, 12)
        lay.setSpacing(12)

        tag = QLabel("GROK")
        tag.setStyleSheet(
            "color: #e3c08e; font-weight: 700; letter-spacing: 1.5px; font-size: 10px;"
        )
        tag.setFixedWidth(50)
        lay.addWidget(tag)

        self._banner_msg = QLabel(tr("Connect to Grok to enable AI insights."))
        self._banner_msg.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        lay.addWidget(self._banner_msg, 1)

        self._btn_connect = QPushButton(tr("Add API key"))
        self._btn_connect.clicked.connect(self._configure_api)
        lay.addWidget(self._btn_connect)

        return banner

    def _refresh_banner(self):
        self._client = GrokClient()
        if self._client.is_configured:
            self._api_banner.hide()
        else:
            self._api_banner.show()
            self._banner_msg.setText(tr("Connect to Grok to enable AI insights."))

    def _configure_api(self):
        text, ok = QInputDialog.getText(
            self, tr("Grok API key"),
            tr("Paste your xAI Grok API key (starts with xai-):"),
            QLineEdit.Password,
            load_api_key() or "",
        )
        if ok and text.strip():
            save_api_key(text.strip())
            self._refresh_banner()
            self._app.toast(tr("Grok API key saved"), "success")

    # ── Actions ───────────────────────────────

    def _gen_summary(self):
        if not self._controller.current_analysis:
            self._app.toast(tr("Run an analysis first"), "warning")
            return
        if not self._client.is_configured:
            self._app.toast(tr("Add your Grok API key first"), "warning")
            return

        self._btn_summary.setEnabled(False)
        self._btn_summary.setText(tr("Grok is thinking..."))
        self._output.setPlaceholderText(tr("Waiting for Grok..."))
        self._output.clear()
        self._app.set_status(tr("Querying Grok..."), "info", 0.5)

        analysis = self._controller.current_analysis
        lang = I18nManager.instance().current

        def _job():
            try:
                text = generate_executive_summary(self._client, analysis, language=lang)
                self._llm_done.emit(text, "")
            except Exception as e:
                logger.exception("Grok summary failed")
                self._llm_error.emit(str(e))

        threading.Thread(target=_job, daemon=True).start()

    def _ask(self):
        question = self._question_input.text().strip()
        if not question:
            return
        if not self._controller.current_analysis:
            self._app.toast(tr("Run an analysis first"), "warning")
            return
        if not self._client.is_configured:
            self._app.toast(tr("Add your Grok API key first"), "warning")
            return

        self._btn_ask.setEnabled(False)
        self._btn_ask.setText(tr("Asking..."))
        self._app.set_status(tr("Asking Grok..."), "info", 0.5)

        analysis = self._controller.current_analysis
        lang = I18nManager.instance().current

        def _job():
            try:
                text = ask_question(self._client, analysis, question, language=lang)
                self._llm_done.emit(text, question)
            except Exception as e:
                logger.exception("Grok ask failed")
                self._llm_error.emit(str(e))

        threading.Thread(target=_job, daemon=True).start()

    def _on_response(self, text: str, question: str = ""):
        self._btn_summary.setEnabled(True)
        self._btn_summary.setText(tr("Generate Executive Summary"))
        self._btn_ask.setEnabled(True)
        self._btn_ask.setText(tr("Ask Grok"))

        if question:
            # Append a la suite
            self._output.append("\n---")
            self._output.append(f"\n**Q : {question}**\n")
            self._output.append(text)
            self._question_input.clear()
        else:
            self._output.setPlainText(text)

        self._app.set_status(tr("Grok response received"), "success", 1.0)

    def _on_error(self, msg: str):
        self._btn_summary.setEnabled(True)
        self._btn_summary.setText(tr("Generate Executive Summary"))
        self._btn_ask.setEnabled(True)
        self._btn_ask.setText(tr("Ask Grok"))
        QMessageBox.critical(self, tr("Grok error"), msg)
        self._app.set_status(tr("Grok error"), "error")

    def _clear_output(self):
        self._output.clear()

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        pass

    def on_show(self):
        self._refresh_banner()

    def retranslate(self):
        self._caption_lbl.setText(tr("AI POWERED"))
        self._title_lbl.setText(tr("AI Insights"))
        self._subtitle.setText(tr(
            "Grok analyzes your risk graph and explains findings in natural language."
        ))
        self._btn_summary.setText(tr("Generate Executive Summary"))
        self._btn_clear.setText(tr("Clear"))
        self._btn_ask.setText(tr("Ask Grok"))
        self._btn_connect.setText(tr("Add API key"))
        self._banner_msg.setText(tr("Connect to Grok to enable AI insights."))
        self._question_input.setPlaceholderText(tr(
            "e.g. Which entities are the most exposed to systemic risk?"
        ))
