"""Screenshot vue Knowledge Base avec 3 analyses persistees."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

# Reset KB pour avoir des donnees propres
from pathlib import Path
db = Path("data/knowledge.db")
if db.exists():
    db.unlink()

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
from controller.risk_controller import RiskController, DEMO_SCENARIOS
controller = RiskController(language="fr")

# Lance 3 analyses pour avoir des donnees
for k in ('crise_financiere', 'reseau_business', 'chaine_appro'):
    controller.analyze_text(DEMO_SCENARIOS[k]["text"])

from ui_qt.main_window import MainWindow
w = MainWindow(controller)
w.resize(1500, 980)
w.show()
w.raise_()
w.activateWindow()
w._navigate("knowledge")

def capture():
    # Selectionne la 1ere ligne pour montrer le detail
    if w._views["knowledge"]._table.rowCount() > 0:
        w._views["knowledge"]._table.selectRow(0)
    pixmap = w.grab()
    pixmap.save("riskpulse_qt_knowledge.png", "PNG")
    print(f"Saved (size: {w.width()}x{w.height()})")
    app.quit()

QTimer.singleShot(1800, capture)
app.exec()
