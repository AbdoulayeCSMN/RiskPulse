"""
RiskPulse — Point d'entree principal
"""
import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)

sys.path.insert(0, os.path.dirname(__file__))


def _enable_hidpi_awareness():
    """
    Active la HiDPI awareness sur Windows.
    Sans ca, Tkinter est dessine en 96 DPI puis upscale par Windows,
    ce qui produit un rendu flou sur les ecrans a echelle > 100%.

    Cette fonction doit etre appelee AVANT la creation de tout Tk().
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # Windows 8.1+ : PER_MONITOR_AWARE (valeur 2) = ideal pour multi-ecran
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            # Fallback Windows 7 / 8
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception as e:
        logging.getLogger(__name__).warning(f"HiDPI awareness non activee : {e}")


def main():
    _enable_hidpi_awareness()
    from ui.app import RiskPulseApp
    app = RiskPulseApp()
    app.run()

if __name__ == "__main__":
    main()
