# RiskPulse - Code signing script
# Signe l'executable + l'installer avec un certificat code-signing.
#
# Usage avec certificat commercial (recommande) :
#   .\build_scripts\sign.ps1 -CertFile path\to\cert.pfx -CertPassword "secret"
#
# Usage avec certificat self-signed (test local seulement) :
#   .\build_scripts\sign.ps1 -SelfSigned
#
# Usage avec cert deja dans le Windows Cert Store (avec thumbprint) :
#   .\build_scripts\sign.ps1 -Thumbprint "ABC123..."

param(
    [string]$CertFile     = "",
    [string]$CertPassword = "",
    [string]$Thumbprint   = "",
    [switch]$SelfSigned,
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [string]$TargetFile   = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Exe = if ($TargetFile) { $TargetFile } else { Join-Path $Root "dist\RiskPulse\RiskPulse.exe" }

if (-not (Test-Path $Exe)) {
    Write-Host "[!] Target not found: $Exe" -ForegroundColor Red
    exit 1
}

# Find signtool.exe
$SignTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $SignTool) {
    # Fallback : recherche dans Windows SDK
    $candidates = @(
        "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
        "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe",
        "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $SignTool = $c; break }
    }
    if (-not $SignTool) {
        Write-Host "[!] signtool.exe introuvable. Install Windows SDK ou ajoute-le au PATH." -ForegroundColor Red
        Write-Host "    https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/"
        exit 1
    }
}
Write-Host "[*] signtool : $SignTool"

# ── Determine cert source ──
$Args = @("sign", "/fd", "SHA256", "/td", "SHA256", "/tr", $TimestampUrl, "/v")

if ($SelfSigned) {
    # Genere un self-signed cert si pas deja present
    $CertPath = Join-Path $Root "build_scripts\selfsigned.pfx"
    if (-not (Test-Path $CertPath)) {
        Write-Host "[*] Generating self-signed certificate..."
        $Pass = ConvertTo-SecureString -String "riskpulse-dev" -Force -AsPlainText
        $cert = New-SelfSignedCertificate `
            -Type CodeSigningCert `
            -Subject "CN=RiskPulse Dev, O=RiskPulse, C=MA" `
            -KeyUsage DigitalSignature `
            -FriendlyName "RiskPulse Self-Signed" `
            -CertStoreLocation Cert:\CurrentUser\My `
            -NotAfter (Get-Date).AddYears(3)
        Export-PfxCertificate -Cert $cert -FilePath $CertPath -Password $Pass | Out-Null
        Write-Host "[*] Self-signed cert created : $CertPath (password: riskpulse-dev)"
        Write-Host "[!] WARNING : SmartScreen affichera 'Unknown publisher' avec ce cert."
        Write-Host "[!] Achete un cert commercial (DigiCert/Sectigo) pour la prod."
    }
    $CertFile = $CertPath
    $CertPassword = "riskpulse-dev"
}

if ($CertFile) {
    if (-not (Test-Path $CertFile)) {
        Write-Host "[!] Cert file not found : $CertFile" -ForegroundColor Red
        exit 1
    }
    $Args += @("/f", $CertFile)
    if ($CertPassword) {
        $Args += @("/p", $CertPassword)
    }
} elseif ($Thumbprint) {
    $Args += @("/sha1", $Thumbprint)
} else {
    Write-Host "[!] Indique soit -CertFile, soit -Thumbprint, soit -SelfSigned." -ForegroundColor Red
    Get-Help $PSCommandPath
    exit 1
}

$Args += $Exe

Write-Host ""
Write-Host "[*] Signing : $Exe"
Write-Host "[*] Timestamp : $TimestampUrl"
Write-Host ""

& $SignTool @Args
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Signing FAILED (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Verify signature
Write-Host ""
Write-Host "[*] Verifying signature..."
& $SignTool verify /pa /v $Exe

Write-Host ""
Write-Host "[OK] Signed : $Exe" -ForegroundColor Green

# Affiche le hash SHA256 pour la release manifest
$Hash = (Get-FileHash $Exe -Algorithm SHA256).Hash.ToLower()
$Size = (Get-Item $Exe).Length
Write-Host ""
Write-Host "  Hash SHA-256 : $Hash"
Write-Host "  Size         : $Size bytes"
