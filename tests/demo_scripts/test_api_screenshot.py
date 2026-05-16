"""Screenshot vue API & SDK."""
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
ctrl = RiskController(language="fr")
from ui_qt.main_window import MainWindow
w = MainWindow(ctrl)
w.resize(1500, 1000)
w.show()
w.raise_()
w.activateWindow()
w._navigate("api")

# Demarre le serveur pour montrer le statut ONLINE
def start_server():
    av = w._views.get("api")
    if av:
        av._start()

QTimer.singleShot(800, start_server)

def capture():
    pixmap = w.grab()
    pixmap.save("riskpulse_qt_api.png", "PNG")
    print(f"Saved (size: {w.width()}x{w.height()})")
    app.quit()

QTimer.singleShot(3500, capture)
app.exec()
