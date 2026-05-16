# RiskPulse — Packaging Windows

## Prerequis

- Python 3.12+
- Toutes les deps : `pip install -r requirements.txt`
- Modeles spaCy : `python -m spacy download fr_core_news_sm` + `en_core_web_sm`
- PyInstaller : `pip install pyinstaller`
- (Optionnel) Inno Setup 6+ : https://jrsoftware.org/isdl.php — pour l'installer

## Build du binaire

```bash
# Build complet (clean + smoke test + exe)
python build_scripts/build.py

# Skip smoke test (plus rapide)
python build_scripts/build.py --fast

# Nettoyer uniquement
python build_scripts/build.py --clean
```

Sortie : `dist/RiskPulse/RiskPulse.exe` + tous les DLL/.pyd packages.

Mode **one-folder** (pas one-file) : demarrage instantane, debug facile.

## Test rapide

```bash
python build_scripts/test_exe.py
```

Lance l'exe pendant 10s et verifie qu'il ne crash pas.

## Generer l'installer Windows (Inno Setup)

```bash
# Installer Inno Setup d'abord (https://jrsoftware.org/isdl.php)
cd build_scripts
iscc installer.iss
```

Sortie : `dist/installer/RiskPulse-Setup-1.0.0.exe` (~150-300 MB compressed).

L'installer Inno :
- Place RiskPulse dans `%LOCALAPPDATA%\Programs\RiskPulse` (pas besoin d'admin)
- Cree des raccourcis Menu + Bureau (optionnels)
- Demande la langue d'installation (EN/FR)
- Preserve `%APPDATA%\RiskPulse\data\` a la desinstallation

## Distribution sans installer (ZIP)

```bash
cd dist
Compress-Archive -Path RiskPulse -DestinationPath RiskPulse-1.0.0-portable.zip
```

L'utilisateur dezippe et lance `RiskPulse.exe` directement. Aucun install requis.

## Structure du bundle

```
dist/RiskPulse/
├── RiskPulse.exe                    Point d'entree
├── python312.dll, etc.              Runtime Python
├── _internal/                       PyInstaller bootloader cache
│   ├── PySide6/                     UI framework (~120 MB)
│   ├── spacy/                       NLP runtime
│   ├── fr_core_news_sm/             Modele spaCy FR (~15 MB)
│   ├── en_core_web_sm/              Modele spaCy EN (~12 MB)
│   ├── networkx/, sklearn/          Analytics
│   ├── fastapi/, uvicorn/           API
│   ├── ui_qt/locales/*.qm           Traductions
│   └── ...
```

## Donnees utilisateur

L'application ecrit les donnees dans `%APPDATA%\RiskPulse\data\` :
- `knowledge.db`            base SQLite persistante
- `preferences.json`        langue + theme + cle API
- `session.json`            session active (auto-login)
- `logs/`                   logs rotatifs
- `exports/`                exports PDF/CSV/JSON

Ces donnees survivent aux mises a jour de l'app.

## Troubleshooting

### "ImportError: DLL load failed"
Souvent lie a `vcredist`. Installer Microsoft Visual C++ Redistributable.

### Exe taille >500 MB
Probable inclusion de torch / tensorflow accidentelle. Verifier `excludes`
dans `riskpulse.spec`.

### Splash visible mais window vide
Probleme de Qt platform plugin. Verifier que `PySide6/plugins/platforms/`
est bien dans le bundle (`_internal/PySide6/plugins/platforms/qwindows.dll`).

### spaCy : "Can't find model 'fr_core_news_sm'"
Le hook `runtime_hook.py` doit ajouter les dossiers au sys.path. Verifier
que `fr_core_news_sm/` est bien au top level du bundle (pas dans `_internal/`).

### Lent au demarrage
Normal : ~3-5s pour charger PySide6 + spaCy en mode frozen. Le splash le masque.

## CI / release

Pour un build reproductible (recommande pour eviter le scan des libs lourdes
deja installees dans votre env principal type torch / tensorflow / pyqt5) :

```bash
# 1. Cree un venv ISOLE pour le build
python -m venv venv_build

# 2. Installe les deps build dans ce venv
venv_build\Scripts\python.exe -m pip install -U pip
venv_build\Scripts\python.exe -m pip install -r requirements.txt pyinstaller

# 3. Telecharge les modeles spaCy DANS le venv_build
venv_build\Scripts\python.exe -m spacy download fr_core_news_sm
venv_build\Scripts\python.exe -m spacy download en_core_web_sm
# (Si reseau bloque, copier depuis l'env principal :
#  Copy-Item -Recurse SRC\fr_core_news_sm venv_build\Lib\site-packages\)

# 4. Build (utilise le venv)
.\build_scripts\build_clean.ps1
# OU
venv_build\Scripts\python.exe -m PyInstaller build_scripts/riskpulse.spec --noconfirm
```

Le venv isole evite que PyInstaller scanne des centaines de MB de libs non
utilisees (torch, tensorflow, pyqt5, jupyter), ce qui peut faire passer le
build de 30+ minutes a 3-5 minutes.

## Iterations connues sur le packaging (V1.0)

Notes pour les futurs rebuilds :

| Symptome                                         | Cause                                          | Fix                                            |
| ------------------------------------------------ | ---------------------------------------------- | ---------------------------------------------- |
| `ValueError: Target module "distutils" already`  | distutils dans excludes                        | Retirer de excludes (PyInstaller en a besoin)  |
| `Aborting: PyQt5 + PySide6`                      | PyQt5 tire transitivement par pyvis            | Exclure explicitement PyQt5 / PyQt6            |
| `ModuleNotFoundError: scipy`                     | sklearn requiert scipy                         | Retirer scipy de excludes                      |
| `ModuleNotFoundError: numpy.f2py / numpy.testing`| scipy requiert tout numpy                      | Ne RIEN exclure de numpy                       |
| "Modele spaCy non trouve - mode fallback regex"  | Modeles bundled mais pas dans sys.path frozen  | Runtime hook ajoute `_internal/` au sys.path   |
| Build > 30 min                                   | Scan de torch / tensorflow / pyqt installes    | Utiliser venv_build isole                      |
