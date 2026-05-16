"""Test live retranslation : bascule de langue + screenshot par langue."""
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

# Auto-login admin pour bypass le LoginDialog
from services.auth_service import get_auth
auth = get_auth()
auth.login("admin", "admin")

from controller.risk_controller import RiskController
ctrl = RiskController(language="en")
from ui_qt.main_window import MainWindow
w = MainWindow(ctrl)
w.resize(1500, 900)
w.show()
w.raise_()
w.activateWindow()

# Sequence : change la langue toutes les 2 secondes et capture
LANGS = ["en", "fr", "es", "it", "ar"]
i18n = I18nManager.instance()
captures_done = [0]

def do_capture():
    idx = captures_done[0]
    if idx >= len(LANGS):
        app.quit()
        return
    lang = LANGS[idx]
    i18n.set_language(lang)
    # Force navigation a welcome pour capturer la vue d'accueil
    w._navigate("welcome")
    QTimer.singleShot(800, lambda: save_and_next(lang))

def save_and_next(lang):
    pixmap = w.grab()
    pixmap.save(f"riskpulse_i18n_{lang}.png", "PNG")
    print(f"Saved : riskpulse_i18n_{lang}.png")
    captures_done[0] += 1
    QTimer.singleShot(500, do_capture)

QTimer.singleShot(1000, do_capture)
app.exec()
print("\nDone.")
