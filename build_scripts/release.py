"""
Pipeline complet de release :
  1. Smoke test
  2. Build (PyInstaller)
  3. Sign (optionnel, si CERT_FILE est defini en env)
  4. Hash SHA-256
  5. Pack ZIP portable
  6. Genere manifest JSON (pour l'auto-updater)

Sortie : dist/release/
  - RiskPulse-{version}-portable.zip
  - RiskPulse-{version}.sha256
  - manifest.json

Usage :
    python build_scripts/release.py --version 1.0.1 --notes "Bug fixes"
    python build_scripts/release.py --version 1.0.1 --notes-file CHANGELOG_1.0.1.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
RELEASE_DIR = DIST / "release"
SPEC = ROOT / "build_scripts" / "riskpulse.spec"
PYTHON_VENV = ROOT / "venv_build" / "Scripts" / "python.exe"


def step(msg: str):
    print(f"\n{'=' * 70}\n  {msg}\n{'=' * 70}")


def run(cmd, cwd: Path = ROOT, check: bool = True) -> int:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    proc = subprocess.run(cmd, cwd=cwd)
    if check and proc.returncode != 0:
        print(f"  FAILED (exit {proc.returncode})")
        sys.exit(proc.returncode)
    return proc.returncode


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(64 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def smoke_test():
    step("Smoke test")
    py = PYTHON_VENV if PYTHON_VENV.exists() else sys.executable
    run([str(py), "-m", "tests.smoke_test"])


def build():
    step("PyInstaller build")
    py = PYTHON_VENV if PYTHON_VENV.exists() else sys.executable
    # Nettoie d'abord
    for p in (DIST / "RiskPulse", ROOT / "build"):
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
    run([str(py), "-m", "PyInstaller", str(SPEC), "--noconfirm",
          "--clean", "--log-level", "WARN"])
    exe = DIST / "RiskPulse" / "RiskPulse.exe"
    if not exe.exists():
        raise RuntimeError(f"Build failed: {exe} not found")
    return exe


def sign(exe: Path):
    """Signe l'exe si un certificat est configure. Optionnel."""
    cert_file = os.environ.get("CERT_FILE")
    cert_pass = os.environ.get("CERT_PASSWORD", "")
    if not cert_file:
        print("  CERT_FILE not set, skipping signing (use sign.ps1 manually)")
        return
    step("Code signing")
    args = ["powershell.exe", "-File",
            str(ROOT / "build_scripts" / "sign.ps1"),
            "-CertFile", cert_file]
    if cert_pass:
        args += ["-CertPassword", cert_pass]
    args += ["-TargetFile", str(exe)]
    run(args)


def pack(version: str, exe: Path) -> Path:
    step("Packing ZIP")
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    zip_name = f"RiskPulse-{version}-portable.zip"
    zip_path = RELEASE_DIR / zip_name
    if zip_path.exists():
        zip_path.unlink()
    bundle = DIST / "RiskPulse"
    print(f"  Compressing {bundle} -> {zip_path}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in bundle.rglob("*"):
            if f.is_file():
                arcname = Path("RiskPulse") / f.relative_to(bundle)
                z.write(f, arcname)
    size_mb = zip_path.stat().st_size / 1e6
    print(f"  ZIP size : {size_mb:.0f} MB")
    return zip_path


def manifest(version: str, zip_path: Path, notes: str, base_url: str = ""):
    step("Generating manifest")
    sha = sha256_file(zip_path)
    size = zip_path.stat().st_size
    # SHA file
    sha_file = RELEASE_DIR / f"RiskPulse-{version}.sha256"
    sha_file.write_text(f"{sha}  {zip_path.name}\n")
    print(f"  SHA-256 : {sha}")
    print(f"  Size    : {size}")
    # Manifest JSON
    manifest_data = {
        "latest":      version,
        "released_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "channel":     "stable",
        "min_version": "1.0.0",
        "url":         f"{base_url}/{zip_path.name}" if base_url else zip_path.name,
        "sha256":      sha,
        "size":        size,
        "notes":       notes,
        "mandatory":   False,
    }
    manifest_path = RELEASE_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Manifest : {manifest_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--version",    required=True, help="ex. 1.0.1")
    p.add_argument("--notes",      default="",     help="Release notes inline")
    p.add_argument("--notes-file", default="",     help="Path to notes md file")
    p.add_argument("--base-url",   default="",     help="URL prefix for the manifest")
    p.add_argument("--skip-smoke", action="store_true")
    p.add_argument("--skip-build", action="store_true",
                    help="Use existing dist/RiskPulse/")
    args = p.parse_args()

    notes = args.notes
    if args.notes_file and Path(args.notes_file).exists():
        notes = Path(args.notes_file).read_text(encoding="utf-8")
    if not notes:
        notes = f"RiskPulse {args.version} - see CHANGELOG.md for details."

    print(f"\nRiskPulse Release Pipeline")
    print(f"  Version : {args.version}")
    print(f"  Notes   : {notes[:60]}...")

    if not args.skip_smoke:
        smoke_test()

    if args.skip_build:
        exe = DIST / "RiskPulse" / "RiskPulse.exe"
        if not exe.exists():
            print(f"!! --skip-build but {exe} not found")
            return 1
    else:
        exe = build()

    sign(exe)
    zip_path = pack(args.version, exe)
    manifest(args.version, zip_path, notes, args.base_url)

    print("\n" + "=" * 70)
    print("  RELEASE READY")
    print(f"  Drop : {RELEASE_DIR}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
