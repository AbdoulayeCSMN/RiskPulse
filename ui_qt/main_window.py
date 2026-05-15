"""
RiskPulse — Main Window (PySide6)
===================================
TopBar + Sidebar + StackedView + StatusBar.
Inclut welcome screen, command palette, toasts, raccourcis clavier,
persistance (taille, position, derniere vue, theme, langue).
"""

import logging
from typing import Dict
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QScrollArea, QFrame, QLabel,
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QKeySequence, QShortcut

from .components import (
    Sidebar, NavItem, TopBar, StatusBar,
    ToastManager, CommandPalette, Command, AboutDialog,
)
from .theme import ThemeManager
from .i18n import I18nManager, tr

logger = logging.getLogger(__name__)


APP_NAME    = "RiskPulse"
APP_VERSION = "1.0.0"


def build_nav_items() -> list[NavItem]:
    """Items de navigation. Welcome est exclu - c'est l'ecran d'accueil non navigable."""
    return [
        NavItem("analyse",       tr("Text Analysis")),
        NavItem("intelligence",  tr("Risk Intelligence")),
        NavItem("predictive",    tr("Predictive")),
        NavItem("banking",       tr("AML & Compliance")),
        NavItem("knowledge",     tr("Knowledge Base")),
        NavItem("monitoring",    tr("Watch & Monitor")),
        NavItem("api",           tr("API & SDK")),
        NavItem("insights",      tr("AI Insights")),
        NavItem("propagation",   tr("Risk Propagation")),
        NavItem("comparaison",   tr("AI Comparison")),
        NavItem("contrefactuel", tr("What-If Simulations")),
        NavItem("traduction",    tr("Translation")),
        NavItem("dashboard",     tr("Dashboard")),
        NavItem("parametres",    tr("Settings")),
    ]


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.tm = ThemeManager.instance()
        self.i18n = I18nManager.instance()
        self.settings = QSettings("RiskPulse", "RiskPulse")

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(900, 600)

        self._build_ui()
        self._setup_toasts()
        self._setup_shortcuts()
        self._connect_signals()
        self._restore_state()
        self._setup_monitoring_timer()

    # ── Construction UI ───────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # TopBar
        self.topbar = TopBar(
            app_name=APP_NAME,
            subtitle=tr("AI-powered risk mapping and propagation"),
            version=APP_VERSION,
        )
        self.topbar.set_language(self.i18n.current)
        self.topbar.update_theme_icon(self.tm.is_dark)
        root.addWidget(self.topbar)

        # Body
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        root.addWidget(body, 1)

        # Sidebar
        self.sidebar = Sidebar(build_nav_items())
        self.sidebar.set_section_label(tr("NAVIGATION"))
        self.sidebar.set_footer("© C. ABDOULAYE")
        body_layout.addWidget(self.sidebar)

        # Stack des vues
        self.stack = QStackedWidget()
        self.stack.setObjectName("view_stack")
        body_layout.addWidget(self.stack, 1)

        # StatusBar
        self.statusbar = StatusBar()
        self.statusbar.set_right(f"{APP_NAME.upper()}  ·  V{APP_VERSION}")
        root.addWidget(self.statusbar)

        # Charge les vues
        self._views: Dict[str, QWidget] = {}
        self._view_order: list[str] = []
        self._load_views()

    def _load_views(self):
        from .views.welcome_view       import WelcomeView
        from .views.analyse_view       import AnalyseView
        from .views.intelligence_view  import IntelligenceView
        from .views.predictive_view    import PredictiveView
        from .views.banking_view       import BankingView
        from .views.knowledge_view     import KnowledgeView
        from .views.monitoring_view    import MonitoringView
        from .views.api_view           import ApiView
        from .views.insights_view      import InsightsView
        from .views.propagation_view   import PropagationView
        from .views.comparaison_view   import ComparaisonView
        from .views.contrefactuel_view import ContrefactuelView
        from .views.traduction_view    import TraductionView
        from .views.dashboard_view     import DashboardView
        from .views.parametres_view    import ParametresView

        # Welcome en premier — pas dans la sidebar mais dans le stack
        welcome = WelcomeView(controller=self.controller, app=self)
        welcome.start_analysis.connect(lambda: self._navigate("analyse"))
        welcome.start_demo.connect(self._run_random_demo)
        self._add_view("welcome", welcome)

        view_classes = {
            "analyse":       AnalyseView,
            "intelligence":  IntelligenceView,
            "predictive":    PredictiveView,
            "banking":       BankingView,
            "knowledge":     KnowledgeView,
            "monitoring":    MonitoringView,
            "api":           ApiView,
            "insights":      InsightsView,
            "propagation":   PropagationView,
            "comparaison":   ComparaisonView,
            "contrefactuel": ContrefactuelView,
            "traduction":    TraductionView,
            "dashboard":     DashboardView,
            "parametres":    ParametresView,
        }
        for vid in [item.id for item in build_nav_items()]:
            ViewClass = view_classes.get(vid)
            try:
                view = ViewClass(controller=self.controller, app=self)
            except Exception as e:
                logger.exception(f"Erreur vue {vid}")
                view = self._make_error_view(vid, str(e))
            self._add_view(vid, view)

    def _add_view(self, vid: str, view: QWidget):
        scroll = QScrollArea()
        scroll.setWidget(view)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.stack.addWidget(scroll)
        self._views[vid] = view
        self._view_order.append(vid)

    def _make_error_view(self, view_id: str, msg: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(60, 60, 60, 60)
        cap = QLabel(tr("ERROR"))
        cap.setProperty("class", "caption")
        layout.addWidget(cap)
        h = QLabel(f"{tr('Failed to load view')}: {view_id}")
        h.setProperty("class", "h2")
        layout.addWidget(h)
        d = QLabel(msg)
        d.setProperty("class", "caption")
        d.setWordWrap(True)
        layout.addWidget(d)
        layout.addStretch()
        return w

    # ── Toasts ─────────────────────────────────

    def _setup_toasts(self):
        self.toasts = ToastManager.instance()
        self.toasts.install(self)

    def toast(self, message: str, level: str = "info"):
        self.toasts.show(message, level)

    # ── Monitoring auto (timer) ───────────────

    def _setup_monitoring_timer(self):
        """
        Lance un cycle de monitoring toutes les 15 min en arriere-plan.
        Le cycle ne tourne que s'il y a au moins 1 source + 1 watch enabled.
        """
        from PySide6.QtCore import QTimer
        self._monitoring_timer = QTimer(self)
        self._monitoring_timer.timeout.connect(self._background_monitor_tick)
        self._monitoring_timer.start(15 * 60 * 1000)   # 15 minutes

        # Premier tick differé après 30s pour laisser l'app demarrer
        QTimer.singleShot(30 * 1000, self._background_monitor_tick)

    def _background_monitor_tick(self):
        """Tick silencieux du moniteur. Ne bloque pas l'UI."""
        try:
            from services.watchlist import get_watchlist
            wl = get_watchlist()
            if not wl.list_sources(enabled_only=True):
                return
            if not wl.list_watches(enabled_only=True):
                return

            from services.monitoring_engine import get_engine
            engine = get_engine(controller=self.controller,
                                 on_alert=self._on_monitoring_alert)

            import threading
            def _job():
                try:
                    engine.run_cycle(max_items_per_source=3)
                except Exception:
                    logger.exception("Background monitoring failed")
                # Refresh badge sur le thread UI
                from PySide6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(self, "update_alerts_badge",
                                          Qt.QueuedConnection)
            threading.Thread(target=_job, daemon=True).start()
        except Exception:
            logger.exception("Monitoring tick failed")

    def _on_monitoring_alert(self, alert: dict):
        # Toast en temps reel si la vue Monitoring n'est pas active
        if self._current_view != "monitoring":
            self.toast(
                f"⚡ {alert.get('entity_name','')} · {alert.get('verdict','')} "
                f"({alert.get('score',0):.2f})",
                "warning",
            )

    def update_alerts_badge(self):
        """Met a jour le compteur d'alertes dans la sidebar."""
        try:
            from services.watchlist import get_watchlist
            n = get_watchlist().count_unread_alerts()
            self.sidebar.set_badge("monitoring", str(n) if n > 0 else "")
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Repositionne les toasts
        if hasattr(self, "toasts"):
            self.toasts._reposition()

    # ── Raccourcis clavier ────────────────────

    def _setup_shortcuts(self):
        # Ctrl+K = command palette
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self._open_palette)
        # Ctrl+H = home (welcome)
        QShortcut(QKeySequence("Ctrl+H"), self, activated=lambda: self._navigate("welcome"))
        # Ctrl+1..7 = navigation directe
        nav = [item.id for item in build_nav_items()]
        for i, vid in enumerate(nav, 1):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self,
                      activated=lambda v=vid: self._navigate(v))
        # Ctrl+T = toggle theme
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self._toggle_theme)
        # F1 = about
        QShortcut(QKeySequence("F1"), self, activated=self._open_about)
        # Ctrl+Q = quit
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)

    # ── Command palette ───────────────────────

    def _build_commands(self) -> list[Command]:
        cmds = []
        # Navigation
        nav_keys = {item.id: item.label for item in build_nav_items()}
        for i, (vid, label) in enumerate(nav_keys.items(), 1):
            cmds.append(Command(
                id=f"nav.{vid}",
                name=f"{tr('Go to')} {label}",
                category=tr("Navigate"),
                shortcut=f"Ctrl+{i}",
                action=lambda v=vid: self._navigate(v),
            ))
        cmds.append(Command(
            id="nav.welcome", name=tr("Go to Welcome"), category=tr("Navigate"),
            shortcut="Ctrl+H", action=lambda: self._navigate("welcome"),
        ))
        # Theme
        cmds.append(Command(
            id="theme.toggle", name=tr("Toggle theme (dark / light)"),
            category=tr("Appearance"), shortcut="Ctrl+T",
            action=self._toggle_theme,
        ))
        # Langue
        for code, name in [("en", "English"), ("fr", "Francais"),
                            ("ar", "العربية"), ("it", "Italiano"),
                            ("es", "Espanol")]:
            cmds.append(Command(
                id=f"lang.{code}", name=f"{tr('Set language')}: {name}",
                category=tr("Language"), shortcut="",
                action=lambda c=code: self._on_language_changed(c),
            ))
        # Actions
        cmds.append(Command(
            id="action.demo", name=tr("Run a random demo scenario"),
            category=tr("Action"), shortcut="",
            action=self._run_random_demo,
        ))
        cmds.append(Command(
            id="action.about", name=tr("About RiskPulse"),
            category=tr("Help"), shortcut="F1",
            action=self._open_about,
        ))
        cmds.append(Command(
            id="action.quit", name=tr("Quit RiskPulse"),
            category=tr("Action"), shortcut="Ctrl+Q",
            action=self.close,
        ))
        return cmds

    def _open_palette(self):
        palette = CommandPalette(self._build_commands(), parent=self)
        palette.exec()

    def _open_about(self):
        dlg = AboutDialog(parent=self)
        dlg.exec()

    # ── Signaux ───────────────────────────────

    def _connect_signals(self):
        self.sidebar.navigate.connect(self._navigate)
        self.topbar.theme_toggled.connect(self._toggle_theme)
        self.topbar.language_changed.connect(self._on_language_changed)
        self.i18n.language_changed.connect(self._retranslate)
        self.tm.theme_changed.connect(lambda _: self.topbar.update_theme_icon(self.tm.is_dark))

    def _navigate(self, view_id: str):
        if view_id not in self._views:
            return
        idx = self._view_order.index(view_id)
        self.stack.setCurrentIndex(idx)
        # La sidebar n'a pas welcome
        if view_id != "welcome":
            self.sidebar.set_active(view_id)
        else:
            # Desactiver tous les items de sidebar
            self.sidebar.set_active("__none__")

        view = self._views.get(view_id)
        if view and hasattr(view, "on_show"):
            view.on_show()

    def _toggle_theme(self):
        self.tm.toggle()
        self.toast(f"{tr('Theme switched to')} {self.tm.name}", "info")

    def _on_language_changed(self, code: str):
        self.i18n.set_language(code)

    def _retranslate(self, _code: str):
        self.topbar.set_subtitle(tr("AI-powered risk mapping and propagation"))
        new_labels = {item.id: item.label for item in build_nav_items()}
        self.sidebar.update_labels(new_labels)
        self.sidebar.set_section_label(tr("NAVIGATION"))
        for view in self._views.values():
            if hasattr(view, "retranslate"):
                view.retranslate()

    # ── Demo ──────────────────────────────────

    def _run_random_demo(self):
        import random
        try:
            scenarios = self.controller.get_demo_scenarios()
            if not scenarios:
                return
            scenario = random.choice(scenarios)
            self.toast(f"{tr('Loading demo')}: {scenario['title']}", "info")
            # Bascule vers l'analyse et lance
            self._navigate("analyse")
            analyse = self._views.get("analyse")
            if analyse and hasattr(analyse, "_run_full_demo"):
                analyse._run_full_demo()
        except Exception as e:
            self.toast(str(e), "error")

    # ── API publique ──────────────────────────

    def set_status(self, message: str, level: str = "info", progress: float = -1):
        self.statusbar.set_status(message, level)
        if progress >= 0:
            self.statusbar.set_progress(progress)

    def notify_analysis_done(self):
        for view in self._views.values():
            if hasattr(view, "on_analysis_updated"):
                view.on_analysis_updated()
        self.toast(tr("Analysis complete"), "success")

    # ── Persistance ───────────────────────────

    def _restore_state(self):
        geom = self.settings.value("window/geometry")
        if geom:
            self.restoreGeometry(geom)
        else:
            self.resize(1380, 820)

        # Theme
        theme = self.settings.value("ui/theme", self.tm.name)
        if theme in ("dark", "light"):
            self.tm.set_theme(theme)

        # Derniere vue
        last_view = self.settings.value("ui/last_view", "welcome")
        if last_view in self._views:
            self._navigate(last_view)
        else:
            self._navigate("welcome")

    def closeEvent(self, event):
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("ui/theme",  self.tm.name)
        self.settings.setValue("ui/last_view",
            self._view_order[self.stack.currentIndex()]
            if self._view_order else "welcome")
        super().closeEvent(event)
