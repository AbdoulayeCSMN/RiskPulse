"""Screenshot vue Banking + génère le SAR PDF en local."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

from pathlib import Path
db = Path("data/knowledge.db")
if db.exists(): db.unlink()

TEXT = """
Bank Al-Maghrib a annonce le gel des avoirs de la société offshore Cayman Trust Holdings
suite a une enquête de FinCEN. Cette société, domiciliée aux Iles Caimans, etait suspectée
de blanchiment via des operations de smurfing en cryptomonnaie.

Le ministre des Finances Ahmed Benali, ancien depute, dirigeait egalement WafaCash
Maroc qui collaborait avec une banque iranienne via des transferts vers la Syria.
Le LEI 549300ABCDE12345FG67 a ete identifie. Plusieurs IBAN MA64011519000001234567890
ont apparu dans les transactions.

Goldman Sachs et JPMorgan ont chacun finance le projet a hauteur de 500 millions USD.
Le code SWIFT GSBKUS33 a ete utilise. L'AMF et la SEC enquêtent conjointement avec OFAC
sur les liens entre l'entité et un fonds souverain au Panama.

Le pattern de layering observe est conforme aux methodes du FATF blacklist.
"""

from controller.risk_controller import RiskController
ctrl = RiskController(language='fr')
ctrl.analyze_text(TEXT)

# Genere le SAR PDF a cote du screenshot
from services.reports.sar_template import generate_sar_pdf, generate_dd_pdf
generate_sar_pdf(ctrl.current_analysis, "riskpulse_sar_demo.pdf")
generate_dd_pdf(ctrl.current_analysis,  "riskpulse_dd_demo.pdf")
print("PDFs generated : riskpulse_sar_demo.pdf, riskpulse_dd_demo.pdf")

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
w._navigate("banking")
w.notify_analysis_done()

def capture():
    pixmap = w.grab()
    pixmap.save("riskpulse_qt_banking.png", "PNG")
    print(f"Saved screenshot (size: {w.width()}x{w.height()})")
    app.quit()

QTimer.singleShot(1500, capture)
app.exec()
