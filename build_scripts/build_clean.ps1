# Build dans le venv dedie (evite les scans tensorflow/torch/pyqt5)
# Usage : .\build_scripts\build_clean.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$VenvPy = Join-Path $Root "venv_build\Scripts\python.exe"

if (-not (Test-Path $VenvPy)) {
    Write-Host "!! venv_build/ introuvable. Cree-le d'abord :" -ForegroundColor Red
    Write-Host "    python -m venv venv_build"
    Write-Host "    .\venv_build\Scripts\python.exe -m pip install -r requirements.txt pyinstaller"
    Write-Host "    .\venv_build\Scripts\python.exe -m spacy download fr_core_news_sm"
    Write-Host "    .\venv_build\Scripts\python.exe -m spacy download en_core_web_sm"
    exit 1
}

Write-Host "=== Cleaning ===" -ForegroundColor Cyan
Remove-Item -Path "build", "dist" -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force

Write-Host "=== Building with clean venv ===" -ForegroundColor Cyan
$T0 = Get-Date
& $VenvPy -m PyInstaller build_scripts/riskpulse.spec --noconfirm --clean --log-level INFO 2>&1 | Tee-Object -FilePath build.log
$Elapsed = (Get-Date) - $T0

$Exe = Join-Path $Root "dist\RiskPulse\RiskPulse.exe"
if (Test-Path $Exe) {
    $SizeMB = (Get-ChildItem -Path "dist\RiskPulse" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host ""
    Write-Host "=== BUILD OK ($([math]::Round($Elapsed.TotalSeconds))s) ===" -ForegroundColor Green
    Write-Host "  Output : $Exe"
    Write-Host "  Bundle size : $([math]::Round($SizeMB)) MB"
} else {
    Write-Host ""
    Write-Host "=== BUILD FAILED ===" -ForegroundColor Red
    Write-Host "Check build.log for details"
    exit 1
}
