"""Screenshot vue Comparaison."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

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
from controller.risk_controller import RiskController
controller = RiskController(language="fr")
controller.load_demo_scenario("reseau_business")
from ui_qt.main_window import MainWindow
w = MainWindow(controller)
w.resize(1500, 980)
w.show()
w.raise_()
w.activateWindow()
w.notify_analysis_done()
w._navigate("comparaison")

def capture():
    pixmap = w.grab()
    pixmap.save("riskpulse_qt_comparaison_v2.png", "PNG")
    print(f"Saved (size: {w.width()}x{w.height()})")
    app.quit()

QTimer.singleShot(1500, capture)
app.exec()
