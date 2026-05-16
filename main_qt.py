"""
RiskPulse — Point d'entree production.

Flow : Logging + hooks -> Splash -> Login -> MainWindow -> (Logout) -> re-Login.
"""

import sys
import os
import logging

# ── Path setup (avant tout import du projet) ──
sys.path.insert(0, os.path.dirname(__file__))

from utils import paths, setup_logging, get_logger, install_exception_hooks

# Logging d'abord, AVANT tout import qui logue
setup_logging(level=logging.INFO)
logger = get_logger(__name__)


def main():
    # HiDPI Windows
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    # Silence Qt warnings en mode production
    if paths.is_frozen:
        os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

    logger.info("=" * 60)
    logger.info("RiskPulse starting (frozen=%s)", paths.is_frozen)
    logger.info("App dir   : %s", paths.app_dir)
    logger.info("User dir  : %s", paths.user_dir)
    logger.info("Logs at   : %s", paths.logs_dir)

    from PySide6.QtWidgets import QApplication, QDialog

    app = QApplication(sys.argv)
    app.setApplicationName("RiskPulse")
    app.setOrganizationName("RiskPulse")

    # Hooks d'erreur (apres QApplication pour pouvoir installer le Qt hook)
    install_exception_hooks(install_qt=True)

    # Font JetBrains Mono
    from PySide6.QtGui import QFont, QFontDatabase
    if "JetBrains Mono" in QFontDatabase.families():
        font = QFont("JetBrains Mono", 10)
        font.setStyleStrategy(QFont.PreferAntialias)
        app.setFont(font)

    # Theme
    from ui_qt.theme import ThemeManager
    tm = ThemeManager.instance()
    tm.install(app, theme="dark")

    # ── Splash ──
    from ui_qt.components.splash import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    splash.set_status("Loading language pack")
    from ui_qt.i18n import I18nManager
    i18n = I18nManager.instance()
    i18n.install(app)

    splash.set_status("Initializing auth")
    from services.auth_service import get_auth
    auth = get_auth()

    splash.set_status("Loading AI engines")
    from controller.risk_controller import RiskController
    try:
        controller = RiskController(
            language=i18n.current if i18n.current in ("fr", "en") else "en"
        )
    except Exception:
        logger.exception("Controller bootstrap failed — degraded mode")
        controller = None

    splash.close()

    # ── Boucle login -> MainWindow -> logout ──
    from ui_qt.components.login_dialog import LoginDialog
    from ui_qt.main_window import MainWindow
    from utils.errors import set_main_window

    exit_code = 0
    while True:
        user = auth.restore_session()
        if not user:
            login = LoginDialog(auth)
            result = login.exec()
            if result != QDialog.Accepted or not login.user:
                logger.info("Login cancelled — exiting")
                return 0

        try:
            window = MainWindow(controller)
            set_main_window(window)
            window.show()
            window.raise_()
            window.activateWindow()
            exit_code = app.exec()
        except Exception:
            logger.exception("MainWindow crashed")
            return 1

        if auth.current_user is None:
            # Logout -> retour au login
            continue
        else:
            return exit_code


if __name__ == "__main__":
    sys.exit(main() or 0)
