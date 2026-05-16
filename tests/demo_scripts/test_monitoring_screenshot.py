"""Screenshot vue Watch & Monitor avec donnees pre-remplies."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

from pathlib import Path
db = Path("data/knowledge.db")
if db.exists():
    db.unlink()

# Pre-remplir
from controller.risk_controller import RiskController, DEMO_SCENARIOS
from services.watchlist import get_watchlist
from services.monitoring_engine import get_engine
from services.feed_ingester import FeedItem

ctrl = RiskController(language='fr')
wl = get_watchlist()
engine = get_engine(controller=ctrl)

# Watches
wl.add_watch("Investcorp Maroc", threshold=0.5)
wl.add_watch("Cashplus", threshold=0.4)
wl.add_watch("Banque Centrale", threshold=0.7)

# Sources suggerees
wl.add_source("https://www.reuters.com/markets/finance/rss",
              "Reuters Finance", "rss")
wl.add_source("https://www.lemonde.fr/economie/rss_full.xml",
              "Le Monde Economie", "rss")

# Simule 2 cycles d'analyse pour generer des alertes
analyse1 = ctrl.analyze_text(DEMO_SCENARIOS['crise_financiere']['text'])
analyse2 = ctrl.analyze_text(DEMO_SCENARIOS['reseau_business']['text'])
for analyse in (analyse1, analyse2):
    fake_item = FeedItem(title=f"Article actualite finance",
                         summary="...", link="https://example.com/news/article")
    engine._check_alerts(analyse, wl.list_watches(enabled_only=True),
                          fake_item, analyse.get("kb_id"))

# Marque une source comme verifiee
for s in wl.list_sources():
    wl.update_source_status(s["id"], "OK", items_added=4)

# Screenshot
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QFontDatabase

app = QApplication(sys.argv)
if "JetBrains Mono" in QFontDatabase.families():
    app.setFont(QFont("JetBrains Mono", 10))

from ui_qt.theme import ThemeManager
ThemeManager.instance().install(app, "dark")
from ui_qt.i18n import I18nManager
I18nManager.instance().install(app)

# Reutilise le ctrl deja initialise
from ui_qt.main_window import MainWindow
w = MainWindow(ctrl)
w.resize(1500, 980)
w.show()
w.raise_()
w.activateWindow()
w._navigate("monitoring")
w.update_alerts_badge()

def capture():
    pixmap = w.grab()
    pixmap.save("riskpulse_qt_monitoring.png", "PNG")
    print(f"Saved (size: {w.width()}x{w.height()})")
    app.quit()

QTimer.singleShot(1800, capture)
app.exec()
