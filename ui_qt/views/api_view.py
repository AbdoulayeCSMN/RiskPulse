"""
Vue API & SDK — controle du serveur REST + cle API + endpoints.
"""

import logging
import webbrowser
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QPlainTextEdit, QMessageBox,
)

from ..components import Card, MetricCard
from ..i18n import tr
from ._base import build_header

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Endpoints documentes pour l'UI
# ─────────────────────────────────────────────

ENDPOINTS = [
    ("GET",    "/v1/health",                "Sante + uptime + stats KB"),
    ("GET",    "/v1/version",               "Version + features"),
    ("POST",   "/v1/analyze",               "Analyse complete d'un texte"),
    ("GET",    "/v1/entities",              "Liste les entites de la KB"),
    ("GET",    "/v1/entities/{id}",         "Detail entite + historique"),
    ("POST",   "/v1/entities/{id}/enrich",  "Enrichissement Wikidata"),
    ("GET",    "/v1/watchlist",             "Watch list"),
    ("POST",   "/v1/watchlist",             "Ajouter une entite a surveiller"),
    ("GET",    "/v1/sources",               "Sources surveillees"),
    ("POST",   "/v1/sources",               "Ajouter une source"),
    ("POST",   "/v1/monitor/run",           "Lancer un cycle de monitoring"),
    ("GET",    "/v1/alerts",                "Liste des alertes"),
    ("POST",   "/v1/forecast",              "Prediction de risque d'une entite"),
    ("POST",   "/v1/monte-carlo",           "Stress test Monte Carlo"),
    ("GET",    "/v1/trends",                "Leaderboard des tendances"),
]


class ApiView(QWidget):

    _server_changed = Signal(bool)   # True quand running

    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._server = None
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._build()
        self._load_api_key()
        self._refresh_status()
        self._server_changed.connect(self._on_server_state_changed)

    # ── Construction ──────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        head_row = QHBoxLayout()
        head_col = QVBoxLayout()
        self._caption_lbl, self._title_lbl = build_header(
            head_col, tr("INTEGRATION"), tr("API & SDK")
        )
        head_row.addLayout(head_col, 1)

        actions = QHBoxLayout()
        self._btn_start = QPushButton(tr("Start server"))
        self._btn_start.setProperty("variant", "primary")
        self._btn_start.clicked.connect(self._start)
        actions.addWidget(self._btn_start)
        self._btn_stop = QPushButton(tr("Stop server"))
        self._btn_stop.clicked.connect(self._stop)
        self._btn_stop.setEnabled(False)
        actions.addWidget(self._btn_stop)
        self._btn_open = QPushButton(tr("Open Swagger"))
        self._btn_open.clicked.connect(self._open_swagger)
        self._btn_open.setEnabled(False)
        actions.addWidget(self._btn_open)
        aw = QWidget(); aw.setLayout(actions)
        head_row.addWidget(aw, 0, Qt.AlignTop)
        outer.addLayout(head_row)

        self._subtitle = QLabel(tr(
            "Expose RiskPulse as a REST API. Other applications (CRM, GRC, BI) "
            "can call your engine via HTTP. Auto-generated OpenAPI docs and "
            "Python SDK included."
        ))
        self._subtitle.setProperty("class", "subtitle")
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        # Stats
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._stat_status = MetricCard(tr("Status"),    "OFFLINE")
        self._stat_url    = MetricCard(tr("URL"),       "—")
        self._stat_port   = MetricCard(tr("Port"),      "8765")
        self._stat_endpts = MetricCard(tr("Endpoints"), str(len(ENDPOINTS)))
        for s in (self._stat_status, self._stat_url,
                  self._stat_port, self._stat_endpts):
            s.setMinimumHeight(82)
            stats_row.addWidget(s)
        outer.addLayout(stats_row)

        # Corps : 2 colonnes
        body = QHBoxLayout()
        body.setSpacing(20)
        outer.addLayout(body, 1)

        # ── Colonne gauche : credentials + endpoints ──
        left = QVBoxLayout()
        left.setSpacing(12)

        # Credentials
        self._cred_card = Card(tr("Credentials"))
        cred_inner = QVBoxLayout()
        cred_inner.setSpacing(6)
        kl = QLabel(tr("API KEY"))
        kl.setProperty("class", "caption")
        cred_inner.addWidget(kl)
        key_row = QHBoxLayout()
        self._key_input = QLineEdit()
        self._key_input.setReadOnly(True)
        self._key_input.setStyleSheet(
            "QLineEdit { font-family: 'JetBrains Mono'; font-size: 11px; "
            "color: #e3c08e; background: #11151b; }"
        )
        key_row.addWidget(self._key_input, 1)
        self._btn_copy = QPushButton(tr("Copy"))
        self._btn_copy.setFixedWidth(80)
        self._btn_copy.clicked.connect(self._copy_key)
        key_row.addWidget(self._btn_copy)
        self._btn_regen = QPushButton(tr("Regenerate"))
        self._btn_regen.setFixedWidth(100)
        self._btn_regen.clicked.connect(self._regenerate_key)
        key_row.addWidget(self._btn_regen)
        cred_inner.addLayout(key_row)

        warn = QLabel(tr(
            "Treat this key as a password. Anyone with it can analyze "
            "data, modify the watchlist, and access your knowledge base."
        ))
        warn.setStyleSheet("color: #6b7280; font-size: 9px;")
        warn.setWordWrap(True)
        cred_inner.addWidget(warn)
        self._cred_card.layout().addLayout(cred_inner)
        left.addWidget(self._cred_card)

        # Endpoints
        self._endpoints_card = Card(tr("Available Endpoints"))
        ep_inner = QVBoxLayout()
        ep_inner.setSpacing(2)
        # Header
        h = QHBoxLayout()
        for txt, w in [(tr("METHOD"), 60), (tr("PATH"), 280), (tr("DESCRIPTION"), 0)]:
            lbl = QLabel(txt)
            lbl.setProperty("class", "caption")
            if w: lbl.setFixedWidth(w)
            h.addWidget(lbl, 1 if not w else 0)
        hw = QWidget(); hw.setLayout(h)
        ep_inner.addWidget(hw)
        sep = QFrame(); sep.setObjectName("divider"); sep.setFixedHeight(1)
        ep_inner.addWidget(sep)
        # Rows
        method_colors = {
            "GET":    "#84cc9e",
            "POST":   "#9caec1",
            "DELETE": "#e8a0a0",
            "PUT":    "#e3c08e",
        }
        for method, path, desc in ENDPOINTS:
            row = QHBoxLayout()
            row.setContentsMargins(0, 2, 0, 2)
            row.setSpacing(8)
            m = QLabel(method)
            m.setStyleSheet(
                f"color: {method_colors.get(method, '#9ca3af')}; "
                f"font-size: 9px; font-weight: 700; letter-spacing: 1px;"
            )
            m.setFixedWidth(60)
            row.addWidget(m)
            p = QLabel(path)
            p.setStyleSheet("color: #e4e4e7; font-size: 10px;")
            p.setFixedWidth(280)
            row.addWidget(p)
            d = QLabel(desc)
            d.setStyleSheet("color: #a1a1aa; font-size: 10px;")
            row.addWidget(d, 1)
            rw = QWidget(); rw.setLayout(row)
            ep_inner.addWidget(rw)
        ep_inner.addStretch()
        self._endpoints_card.layout().addLayout(ep_inner)
        left.addWidget(self._endpoints_card, 1)

        lw = QWidget(); lw.setLayout(left)
        body.addWidget(lw, 5)

        # ── Colonne droite : exemples ──
        right = QVBoxLayout()
        right.setSpacing(12)

        # cURL example
        self._curl_card = Card(tr("Example: cURL"))
        self._curl_text = QPlainTextEdit()
        self._curl_text.setReadOnly(True)
        self._curl_text.setStyleSheet(
            "QPlainTextEdit { font-family: 'JetBrains Mono'; font-size: 10px; "
            "color: #e4e4e7; background: #0c0c0f; border: 1px solid #1c1c20; "
            "padding: 8px; }"
        )
        self._curl_text.setMaximumHeight(160)
        self._curl_card.layout().addWidget(self._curl_text)
        right.addWidget(self._curl_card)

        # Python SDK example
        self._py_card = Card(tr("Example: Python SDK"))
        self._py_text = QPlainTextEdit()
        self._py_text.setReadOnly(True)
        self._py_text.setStyleSheet(
            "QPlainTextEdit { font-family: 'JetBrains Mono'; font-size: 10px; "
            "color: #e4e4e7; background: #0c0c0f; border: 1px solid #1c1c20; "
            "padding: 8px; }"
        )
        self._py_text.setMaximumHeight(220)
        self._py_card.layout().addWidget(self._py_text)
        right.addWidget(self._py_card)

        right.addStretch()
        rw = QWidget(); rw.setLayout(right)
        body.addWidget(rw, 5)

    # ── State management ──────────────────────

    def _load_api_key(self):
        from api.auth import get_or_create_api_key
        key = get_or_create_api_key()
        self._key_input.setText(key)
        self._update_examples(key)

    def _update_examples(self, key: str):
        url = "http://localhost:8765"
        curl = (
            f"# Health check (public)\n"
            f"curl {url}/v1/health\n\n"
            f"# Analyze a text (authenticated)\n"
            f'curl -X POST {url}/v1/analyze \\\n'
            f'  -H "X-API-Key: {key}" \\\n'
            f'  -H "Content-Type: application/json" \\\n'
            f'  -d \'{{"text": "Bank Al-Maghrib announces ...", "language": "fr"}}\''
        )
        py = (
            f"from api.sdk import RiskPulseClient\n\n"
            f'client = RiskPulseClient(\n'
            f'    api_key="{key}",\n'
            f'    base_url="{url}",\n'
            f')\n\n'
            f'# Run a full analysis\n'
            f'result = client.analyze("Bank Al-Maghrib announces ...")\n'
            f'print(result["risk_intel"]["profiles"][:3])\n\n'
            f'# Browse known entities\n'
            f'entities = client.list_entities(search="bank", limit=10)\n\n'
            f'# Monte Carlo stress test\n'
            f'stress = client.monte_carlo(n_runs=1000)\n'
            f'print(f"VaR 95% = {{stress[\'var_95\']:.0f}}M")'
        )
        self._curl_text.setPlainText(curl)
        self._py_text.setPlainText(py)

    def _refresh_status(self):
        if self._server and self._server.is_running:
            self._stat_status.set_value("ONLINE")
            self._stat_url.set_value(self._server.url.replace("http://", ""))
        else:
            self._stat_status.set_value("OFFLINE")
            self._stat_url.set_value("—")

    # ── Actions ───────────────────────────────

    def _start(self):
        try:
            from api.server import get_server
            self._server = get_server(controller=self._controller)
            self._server.start()
            # Verifie demarrage apres 1s
            QTimer.singleShot(1500, lambda: self._server_changed.emit(True))
        except Exception as e:
            QMessageBox.critical(self, tr("Error"), str(e))

    def _stop(self):
        try:
            if self._server:
                self._server.stop()
            self._server_changed.emit(False)
        except Exception as e:
            QMessageBox.critical(self, tr("Error"), str(e))

    def _on_server_state_changed(self, running: bool):
        self._btn_start.setEnabled(not running)
        self._btn_stop.setEnabled(running)
        self._btn_open.setEnabled(running)
        if running:
            self._status_timer.start(2000)
            self._app.toast(f"{tr('API server running at')} {self._server.url}",
                            "success")
        else:
            self._status_timer.stop()
            self._app.toast(tr("API server stopped"), "info")
        self._refresh_status()

    def _open_swagger(self):
        if self._server and self._server.is_running:
            webbrowser.open(self._server.url + "/docs")

    def _copy_key(self):
        QGuiApplication.clipboard().setText(self._key_input.text())
        self._app.toast(tr("API key copied to clipboard"), "success")

    def _regenerate_key(self):
        ans = QMessageBox.question(
            self, tr("Regenerate API key"),
            tr("Existing clients will be disconnected. Continue?"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        from api.auth import regenerate_api_key
        key = regenerate_api_key()
        self._key_input.setText(key)
        self._update_examples(key)
        self._app.toast(tr("New API key generated"), "success")

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        pass

    def on_show(self):
        self._refresh_status()

    def retranslate(self):
        self._caption_lbl.setText(tr("INTEGRATION"))
        self._title_lbl.setText(tr("API & SDK"))
        self._subtitle.setText(tr(
            "Expose RiskPulse as a REST API. Other applications (CRM, GRC, BI) "
            "can call your engine via HTTP. Auto-generated OpenAPI docs and "
            "Python SDK included."
        ))
        self._btn_start.setText(tr("Start server"))
        self._btn_stop.setText(tr("Stop server"))
        self._btn_open.setText(tr("Open Swagger"))
        self._btn_copy.setText(tr("Copy"))
        self._btn_regen.setText(tr("Regenerate"))
        self._stat_status.set_label(tr("Status"))
        self._stat_url.set_label(tr("URL"))
        self._stat_port.set_label(tr("Port"))
        self._stat_endpts.set_label(tr("Endpoints"))
        self._cred_card.set_title(tr("Credentials"))
        self._endpoints_card.set_title(tr("Available Endpoints"))
        self._curl_card.set_title(tr("Example: cURL"))
        self._py_card.set_title(tr("Example: Python SDK"))
