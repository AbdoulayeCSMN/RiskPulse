# Release workflow

## Vue d'ensemble

```
                  developer's machine                       internet
                  ====================                      ========
                                                 +------+
   tests + build + sign  ─────────┐              | user |
        (release.py)              │              +------+
                                  ▼                  │
                       dist/release/                 │ check Ctrl+U
                       ├── RiskPulse-1.0.0-portable.zip       │
                       ├── RiskPulse-1.0.0.sha256             │
                       └── manifest.json                      ▼
                                  │                 +-----------+
                                  ▼                 | RiskPulse |
                       GitHub Release            ◄──┤ Updater   │
                       (zip + sha + manifest)       +-----------+
```

## Workflow recommande

### 1. Pre-release : tag local et test

```bash
# Run smoke test + 3 cas reels
python -m tests.smoke_test
python tests/production_eval.py

# Update CHANGELOG.md (move Unreleased -> [1.0.1])
```

### 2. Build production

```bash
# Local : utilise le venv dedie
python build_scripts/release.py --version 1.0.1 \
       --notes-file CHANGELOG_1.0.1.md \
       --base-url https://github.com/USER/riskpulse/releases/download/v1.0.1
```

Sortie : `dist/release/`
- `RiskPulse-1.0.1-portable.zip` (~250 MB)
- `RiskPulse-1.0.1.sha256` (le hash)
- `manifest.json` (pour l'auto-updater)

### 3. Sign (optionnel mais recommande)

```powershell
# Avec un certificat commercial (DigiCert / Sectigo / Certum / SSL.com)
.\build_scripts\sign.ps1 -CertFile path\to\cert.pfx -CertPassword "secret"

# Ou avec un cert deja installe dans Windows Cert Store
.\build_scripts\sign.ps1 -Thumbprint "ABC123DEF456..."

# Self-signed (pour tester uniquement, SmartScreen affichera Unknown publisher)
.\build_scripts\sign.ps1 -SelfSigned
```

Le script signe avec :
- Algo SHA-256
- Timestamp RFC3161 (par defaut : DigiCert)
- Verification automatique post-signature

### 4. Publish via GitHub Actions

Le plus simple :

```bash
git tag v1.0.1
git push origin v1.0.1
```

Le workflow `.github/workflows/release.yml` se charge automatiquement de :
1. Build sur Windows runner
2. Sign (si les secrets `CERT_PFX_BASE64` + `CERT_PASSWORD` sont configures)
3. Upload du ZIP + SHA + manifest comme release GitHub
4. Publish `manifest.json` sur la branche `gh-pages` pour l'auto-updater

### 5. Pointer l'auto-updater

Edite `services/updater.py` :
```python
DEFAULT_MANIFEST_URL = "https://USER.github.io/riskpulse/releases/latest.json"
```

L'app verifiera cette URL toutes les 6 heures + au boot (silencieux), ou
sur demande (`Ctrl+U`).

## Obtenir un certificat code-signing

Sans certificat commercial, Windows SmartScreen affichera "Unknown publisher"
au premier lancement. Ce n'est pas bloquant mais ca degrade l'experience.

### Options (du moins au plus cher)

| Type                | Prix annuel | Notes                                              |
| ------------------- | ----------- | -------------------------------------------------- |
| **Self-signed**     | 0           | Pour test uniquement. SmartScreen warn toujours.   |
| **Sectigo OV**      | 80-150 USD  | Identite verifiee. SmartScreen warn quelques jours.|
| **DigiCert OV**     | 400-500 USD | Identite verifiee, reputation immediate.           |
| **DigiCert EV**     | 600+ USD    | Hardware token. Reputation immediate, niveau pro.  |

Recommandation pratique : **Sectigo OV** pour V1 (rapport qualite/prix).
Si le produit prend, basculer en **DigiCert EV** plus tard.

### Lien d'achat rapide

- DigiCert : https://www.digicert.com/code-signing/
- Sectigo : https://sectigostore.com/code-signing
- SSL.com : https://www.ssl.com/certificates/code-signing/
- Certum : https://shop.certum.eu/data-safety/code-signing-certificates/

### Configurer le cert dans GitHub Actions

```bash
# Encode le .pfx en base64 (Windows PowerShell)
$bytes = [IO.File]::ReadAllBytes("path\to\cert.pfx")
$b64 = [Convert]::ToBase64String($bytes)
$b64 | Out-File -FilePath cert.b64 -Encoding ascii
# Copy the contents of cert.b64 into GitHub secret CERT_PFX_BASE64
# Add CERT_PASSWORD as another secret
```

## Manifest update server (sans GitHub Pages)

Si tu heberges toi-meme le manifest, le serveur doit servir :

```
GET https://riskpulse.io/releases/latest.json
Content-Type: application/json

{
    "latest":       "1.0.1",
    "released_at":  "2026-06-01T00:00:00Z",
    "channel":      "stable",
    "min_version":  "1.0.0",
    "url":          "https://riskpulse.io/releases/RiskPulse-1.0.1-portable.zip",
    "sha256":       "abc123def456...",
    "size":         262144000,
    "notes":        "Bug fixes and performance improvements.",
    "mandatory":    false
}
```

L'app supporte aussi un manifest local (`file://`) pour les deploiements
hors-ligne.
