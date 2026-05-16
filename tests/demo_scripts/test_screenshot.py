"""Capture screenshot d'une vue specifique."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

from ui.app import RiskPulseApp

VIEW = sys.argv[1] if len(sys.argv) > 1 else "analyse"

app = RiskPulseApp()
app.controller.load_demo_scenario('crise_financiere')
app.notify_analysis_done()
app._navigate(VIEW)

app.attributes('-topmost', True)
app.lift()
app.focus_force()
app.update_idletasks()
app.update()

def _capture():
    try:
        from PIL import ImageGrab
        x, y = app.winfo_rootx(), app.winfo_rooty()
        w, h = app.winfo_width(), app.winfo_height()
        print(f"View={VIEW} at ({x},{y}) size {w}x{h}")
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        img.save(f"riskpulse_{VIEW}.png")
        print(f"Screenshot saved : riskpulse_{VIEW}.png")
    except Exception as e:
        print(f"FAIL : {e}")
    finally:
        app.attributes('-topmost', False)
        app.after(100, app.destroy)

app.after(2000, _capture)
app.mainloop()
