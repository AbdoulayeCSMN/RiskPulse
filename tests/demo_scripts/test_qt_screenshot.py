"""Screenshot d'une vue specifique. Usage : python test_qt_screenshot.py <view> [theme]"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
VIEW  = sys.argv[1] if len(sys.argv) > 1 else "welcome"
THEME = sys.argv[2] if len(sys.argv) > 2 else "dark"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QFontDatabase

app = QApplication(sys.argv)
if "JetBrains Mono" in QFontDatabase.families():
    app.setFont(QFont("JetBrains Mono", 10))

from ui_qt.theme import ThemeManager
ThemeManager.instance().install(app, THEME)
from ui_qt.i18n import I18nManager
I18nManager.instance().install(app)
from controller.risk_controller import RiskController
controller = RiskController(language="en")
from ui_qt.main_window import MainWindow
w = MainWindow(controller)
w.resize(1400, 860)
w.show()
w.raise_()
w.activateWindow()

w._navigate(VIEW)

def capture():
    pixmap = w.grab()
    name = f"riskpulse_qt_{VIEW}_{THEME}.png"
    pixmap.save(name, "PNG")
    print(f"Saved: {name} ({w.width()}x{w.height()})")
    app.quit()

QTimer.singleShot(1500, capture)
app.exec()
