"""
RiskPulse — Internationalisation (i18n)
========================================
Gestion centralisee des traductions via QTranslator (systeme natif Qt).

Langues supportees : fr, en, ar, it, es
Detection automatique de la langue OS au premier lancement.
Persistance dans data/preferences.json.
"""

import json
import locale
import logging
from pathlib import Path
from typing import Callable, List, Optional

from PySide6.QtCore import QLocale, QTranslator, QObject, Signal, QCoreApplication

logger = logging.getLogger(__name__)


SUPPORTED_LANGUAGES = {
    "fr": "Francais",
    "en": "English",
    "ar": "العربية",
    "it": "Italiano",
    "es": "Espanol",
}

DEFAULT_LANGUAGE = "en"   # Fallback international

try:
    from utils.paths import paths as _paths
    PREFS_PATH = _paths.preferences
except Exception:
    PREFS_PATH = Path("data") / "preferences.json"


class I18nManager(QObject):
    """
    Gestionnaire de langue centralise.

    - Charge le fichier .qm correspondant
    - Notifie les widgets via le signal `language_changed`
    - Persiste le choix utilisateur
    """

    language_changed = Signal(str)   # emet le nouveau code langue

    _instance: "I18nManager | None" = None

    def __init__(self):
        super().__init__()
        self._translator   = QTranslator()
        self._current_lang = DEFAULT_LANGUAGE
        self._app: Optional[QCoreApplication] = None
        I18nManager._instance = self

    @classmethod
    def instance(cls) -> "I18nManager":
        if cls._instance is None:
            cls._instance = I18nManager()
        return cls._instance

    # ── Initialisation ─────────────────────────

    def install(self, app: QCoreApplication):
        """A appeler une fois au demarrage avec le QApplication."""
        self._app = app
        lang = self._load_preference() or self._detect_os_language()
        self.set_language(lang, notify=False)

    def _detect_os_language(self) -> str:
        """Detecte la langue de l'OS, fallback DEFAULT_LANGUAGE."""
        try:
            qlocale = QLocale.system().name()  # ex: "fr_FR"
            code = qlocale.split("_")[0].lower()
            if code in SUPPORTED_LANGUAGES:
                return code
        except Exception:
            pass
        try:
            sys_locale = locale.getlocale()[0] or ""
            code = sys_locale.split("_")[0].lower()
            if code in SUPPORTED_LANGUAGES:
                return code
        except Exception:
            pass
        return DEFAULT_LANGUAGE

    # ── Changement de langue ───────────────────

    def set_language(self, code: str, notify: bool = True):
        """Charge le .qm correspondant et notifie tous les widgets."""
        if code not in SUPPORTED_LANGUAGES:
            logger.warning(f"Langue inconnue : {code}, fallback {DEFAULT_LANGUAGE}")
            code = DEFAULT_LANGUAGE

        if self._app is None:
            self._current_lang = code
            return

        # Decharge l'ancien translator
        self._app.removeTranslator(self._translator)
        self._translator = QTranslator()

        # Charge le nouveau .qm.
        # En mode frozen (exe), les .qm sont dans le bundle PyInstaller,
        # qui peut etre soit a cote de l'exe, soit dans _MEIPASS.
        qm_path = self._locate_qm(code)
        if qm_path.exists():
            if self._translator.load(str(qm_path)):
                self._app.installTranslator(self._translator)
                logger.info(f"Langue chargee : {code}")
            else:
                logger.warning(f"Echec chargement {qm_path}")
        else:
            # Pas de .qm = on reste en langue source (les chaines sont en anglais dans le code)
            logger.info(f"Pas de fichier .qm pour {code}, utilisation langue source")

        self._current_lang = code
        self._save_preference(code)

        # ── RTL pour l'arabe ──
        try:
            from PySide6.QtCore import Qt
            direction = Qt.RightToLeft if code == "ar" else Qt.LeftToRight
            self._app.setLayoutDirection(direction)
        except Exception:
            pass

        if notify:
            self.language_changed.emit(code)

    @property
    def current(self) -> str:
        return self._current_lang

    @property
    def is_rtl(self) -> bool:
        return self._current_lang == "ar"

    def _locate_qm(self, code: str) -> Path:
        """Trouve le .qm dans tous les emplacements possibles (dev + frozen)."""
        candidates = [
            Path(__file__).parent / "locales" / f"riskpulse_{code}.qm",
        ]
        # Mode frozen : essaie via utils.paths.resource
        try:
            from utils.paths import paths
            candidates.append(
                paths.resource("ui_qt", "locales", f"riskpulse_{code}.qm")
            )
            candidates.append(
                paths.resource("locales", f"riskpulse_{code}.qm")
            )
        except Exception:
            pass
        for c in candidates:
            if c.exists():
                return c
        # Retourne le 1er candidat (qui n'existe pas) pour le message d'erreur
        return candidates[0]

    # ── Persistance ─────────────────────────────

    def _load_preference(self) -> Optional[str]:
        try:
            if PREFS_PATH.exists():
                with open(PREFS_PATH, "r", encoding="utf-8") as f:
                    return json.load(f).get("language")
        except Exception as e:
            logger.warning(f"Lecture prefs echouee : {e}")
        return None

    def _save_preference(self, code: str):
        try:
            PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if PREFS_PATH.exists():
                with open(PREFS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["language"] = code
            with open(PREFS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Sauvegarde prefs echouee : {e}")


def tr(text: str, context: str = "") -> str:
    """
    Helper de traduction : QCoreApplication.translate.

    Important : on utilise un contexte VIDE par defaut car pyside6-lupdate
    extrait nos `tr(...)` (appels de fonction libres, hors classe QObject)
    sous un <name /> vide. Le contexte doit donc correspondre.
    """
    return QCoreApplication.translate(context, text)
