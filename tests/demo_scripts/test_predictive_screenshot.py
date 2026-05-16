"""Screenshot vue Predictive avec donnees pre-calculees."""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

from pathlib import Path
db = Path("data/knowledge.db")
if db.exists(): db.unlink()

# Pre-remplir avec historique simule sur plusieurs dates
from controller.risk_controller import RiskController, DEMO_SCENARIOS
from services.knowledge_base import get_kb
from datetime import datetime, timedelta
import sqlite3

ctrl = RiskController(language='fr')
kb = get_kb()

# Lance 4 analyses : 2 sur la crise financière, 2 sur le réseau business
for k in ['crise_financiere', 'reseau_business', 'crise_financiere', 'reseau_business']:
    ctrl.analyze_text(DEMO_SCENARIOS[k]["text"])
    time.sleep(0.1)

# Simule des timestamps espacés sur 4 dates (pour creer une vraie tendance)
with sqlite3.connect(db) as conn:
    rows = conn.execute("SELECT id FROM analyses ORDER BY id").fetchall()
    base = datetime.now() - timedelta(days=90)
    for i, (aid,) in enumerate(rows):
        new_ts = (base + timedelta(days=i*22)).isoformat()
        conn.execute("UPDATE analyses SET timestamp=? WHERE id=?", (new_ts, aid))
        conn.execute("UPDATE entity_appearances SET timestamp=? WHERE analysis_id=?",
                      (new_ts, aid))
    conn.commit()

# Force un score legerement croissant pour Investcorp pour avoir une trajectoire visible
with sqlite3.connect(db) as conn:
    rows = conn.execute("""
        SELECT ea.id, ea.timestamp, ea.entity_id
        FROM entity_appearances ea
        JOIN entities e ON ea.entity_id = e.id
        WHERE e.canonical_name LIKE '%investcorp%'
        ORDER BY ea.timestamp
    """).fetchall()
    for i, (eid_app, ts, _) in enumerate(rows):
        new_score = 0.40 + 0.08 * i  # 0.40, 0.48, 0.56, 0.64...
        conn.execute("UPDATE entity_appearances SET risk_score=? WHERE id=?",
                      (new_score, eid_app))
    # Update avg/max sur entities
    conn.execute("""
        UPDATE entities
        SET avg_risk_score = (SELECT AVG(risk_score) FROM entity_appearances
                              WHERE entity_id = entities.id)
        WHERE canonical_name LIKE '%investcorp%'
    """)
    conn.commit()

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
w._navigate("predictive")
w.notify_analysis_done()

# Lance le Monte Carlo automatiquement pour avoir un visuel
def trigger_mc():
    pv = w._views.get("predictive")
    if pv:
        pv._run_monte_carlo()

QTimer.singleShot(800, trigger_mc)

def capture():
    pixmap = w.grab()
    pixmap.save("riskpulse_qt_predictive.png", "PNG")
    print(f"Saved (size: {w.width()}x{w.height()})")
    app.quit()

QTimer.singleShot(3500, capture)
app.exec()
