"""Screenshot vue Knowledge Base avec une entite enrichie Wikidata."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

from pathlib import Path
db = Path("data/knowledge.db")
if db.exists():
    db.unlink()

# Pre-remplir : 2 analyses, puis enrichir une entite connue
from controller.risk_controller import RiskController, DEMO_SCENARIOS
from services.knowledge_base import get_kb

ctrl = RiskController(language='fr')
kb = get_kb()
ctrl.analyze_text(DEMO_SCENARIOS['crise_financiere']['text'])
ctrl.analyze_text(DEMO_SCENARIOS['reseau_business']['text'])

# Trouve Banque Centrale et enrichis-la
target = None
for e in kb.list_entities(limit=50):
    if "banque" in e.canonical_name.lower() or "bank" in e.canonical_name.lower():
        target = e
        break
if not target:
    target = kb.list_entities(limit=1)[0]

# Enrichis avec "Bank Al-Maghrib" pour avoir un vrai Wikidata
print(f"Enriching entity {target.id} : {target.display_name}")
# Force enrich avec un nom connu
from services.enrichment import enrich_name
data = enrich_name("Bank Al-Maghrib", lang="fr")
kb.save_enrichment(target.id, data.as_dict())
print(f"  Status : {data.status}, QID : {data.wikidata_id}")

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
from ui_qt.main_window import MainWindow
w = MainWindow(ctrl)
w.resize(1500, 1000)
w.show()
w.raise_()
w.activateWindow()
w._navigate("knowledge")

def capture():
    kv = w._views["knowledge"]
    kv.refresh()
    # Trouve la ligne et selectionne
    for row in range(kv._table.rowCount()):
        it = kv._table.item(row, 0)
        if it and it.data(32) == target.id:   # Qt.UserRole = 32
            kv._table.selectRow(row)
            break
    QTimer.singleShot(500, _save)

def _save():
    pixmap = w.grab()
    pixmap.save("riskpulse_qt_enrichment.png", "PNG")
    print(f"Saved (size: {w.width()}x{w.height()})")
    app.quit()

QTimer.singleShot(1500, capture)
app.exec()
