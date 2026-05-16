import sys
sys.stdout.reconfigure(encoding='utf-8')
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)
from ui.app import RiskPulseApp
app = RiskPulseApp()
print('Vues chargees :', list(app._views.keys()))
for k, v in app._views.items():
    view = v.get("view")
    print(f'  {k} : type={type(view).__name__}')
app.destroy()
