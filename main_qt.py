"""
RiskPulse — Point d'entree PySide6.
"""

import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)

sys.path.insert(0, os.path.dirname(__file__))


def main():
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QTimer

    app = QApplication(sys.argv)
    app.setApplicationName("RiskPulse")
    app.setOrganizationName("RiskPulse")

    # JetBrains Mono
    from PySide6.QtGui import QFont, QFontDatabase
    families = QFontDatabase.families()
    if "JetBrains Mono" in families:
        font = QFont("JetBrains Mono", 10)
        font.setStyleStrategy(QFont.PreferAntialias)
        app.setFont(font)

    # Theme (apres le QApplication, avant le splash)
    from ui_qt.theme import ThemeManager
    tm = ThemeManager.instance()
    tm.install(app, theme="dark")

    # Splash
    from ui_qt.components.splash import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # i18n
    splash.set_status("Loading language pack")
    from ui_qt.i18n import I18nManager
    i18n = I18nManager.instance()
    i18n.install(app)

    # Controller (NLP, peut prendre 1-2s)
    splash.set_status("Loading AI engines")
    from controller.risk_controller import RiskController
    controller = RiskController(
        language=i18n.current if i18n.current in ("fr", "en") else "en"
    )

    splash.set_status("Building interface")
    from ui_qt.main_window import MainWindow
    window = MainWindow(controller)

    # Affiche la fenetre puis ferme le splash
    def _show_main():
        window.show()
        window.raise_()
        window.activateWindow()
        splash.close()

    QTimer.singleShot(400, _show_main)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
