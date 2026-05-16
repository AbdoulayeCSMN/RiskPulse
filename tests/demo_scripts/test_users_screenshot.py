"""Screenshot vue Users & Audit."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

# Setup : cree quelques users + actions pour avoir du contenu visuel
from services.auth_service import get_auth
auth = get_auth()
# Login admin pour pouvoir creer + auditer
auth.login('admin', 'admin')
# Cree quelques users si absents
existing = {u.username for u in auth.list_users()}
for un, role in [('alice', 'analyst'), ('bob', 'viewer'),
                  ('charles', 'analyst'), ('dana', 'viewer')]:
    if un not in existing:
        try:
            auth.register(username=un, password='pass1234',
                          full_name=un.title(),
                          email=f'{un}@bank.ma', role=role)
        except Exception:
            pass

# Simule des actions audit log
auth.log_action(user_id=auth.current_user.id,
                username=auth.current_user.username,
                action='ANALYZE', resource_type='analysis',
                resource_id='42', details='Analyzed FinTech news (10 entities)')
auth.log_action(user_id=auth.current_user.id,
                username=auth.current_user.username,
                action='EXPORT', resource_type='report',
                resource_id='dashboard',
                details='Exported PDF dashboard report')

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
from controller.risk_controller import RiskController
ctrl = RiskController(language="fr")
from ui_qt.main_window import MainWindow
w = MainWindow(ctrl)
w.resize(1500, 1000)
w.show()
w.raise_()
w.activateWindow()
w._navigate("users")

def capture():
    pixmap = w.grab()
    pixmap.save("riskpulse_qt_users.png", "PNG")
    print(f"Saved (size: {w.width()}x{w.height()})")
    app.quit()

QTimer.singleShot(1800, capture)
app.exec()
