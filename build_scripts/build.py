"""
Script de build production.

Usage :
    python build_scripts/build.py            # build complet (clean + smoke test + exe)
    python build_scripts/build.py --fast     # skip smoke test
    python build_scripts/build.py --clean    # uniquement nettoie

Sortie : dist/RiskPulse/RiskPulse.exe
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "build_scripts" / "riskpulse.spec"
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def step(msg: str):
    print(f"\n{'=' * 70}\n  {msg}\n{'=' * 70}")


def run(cmd: list, cwd: Path = ROOT, env_extra: dict = None) -> int:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    import os
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(cmd, cwd=cwd, env=env)
    return proc.returncode


def clean():
    step("Cleaning previous build artifacts")
    for p in (DIST, BUILD):
        if p.exists():
            print(f"  Removing {p}")
            shutil.rmtree(p, ignore_errors=True)
    # Pycache cleanup
    for root, dirs, _ in __import__("os").walk(ROOT):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(Path(root) / d, ignore_errors=True)


def smoke_test() -> bool:
    step("Running smoke test (12 checks)")
    rc = run([sys.executable, "-m", "tests.smoke_test"])
    if rc != 0:
        print("\n!! Smoke test FAILED. Aborting build.")
        return False
    return True


def compile_qm():
    step("Compiling translations (.ts -> .qm)")
    qm_dir = ROOT / "ui_qt" / "locales"
    has_qm = any(qm_dir.glob("*.qm"))
    if has_qm:
        print("  .qm files already present, skipping")
        return
    run([sys.executable, "ui_qt/locales/compile_qm.py"])


def build_exe():
    step("Building executable (PyInstaller)")
    t0 = time.time()
    rc = run([
        sys.executable, "-m", "PyInstaller",
        str(SPEC),
        "--noconfirm",
        "--clean",
        "--log-level", "WARN",
    ])
    if rc != 0:
        print("\n!! PyInstaller failed.")
        return False
    elapsed = time.time() - t0
    exe = DIST / "RiskPulse" / "RiskPulse.exe"
    if not exe.exists():
        print(f"\n!! Expected output not found: {exe}")
        return False

    size_mb = sum(f.stat().st_size for f in (DIST / "RiskPulse").rglob("*")) / 1e6
    print(f"\n  Build complete in {elapsed:.1f}s")
    print(f"  Output : {exe}")
    print(f"  Bundle size : {size_mb:.0f} MB")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--clean", action="store_true",
                    help="Only clean, don't build")
    p.add_argument("--fast",  action="store_true",
                    help="Skip smoke test")
    args = p.parse_args()

    clean()
    if args.clean:
        print("\nClean done.")
        return 0

    compile_qm()

    if not args.fast:
        if not smoke_test():
            return 1

    if not build_exe():
        return 1

    print("\n" + "=" * 70)
    print("  BUILD OK")
    print(f"  Test : {DIST}/RiskPulse/RiskPulse.exe")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
