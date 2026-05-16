"""
Test du binaire produit. Lance l'exe en mode test et verifie qu'il boote
sans crash en 10s. Pas de test des vues, juste le startup.

Usage : python build_scripts/test_exe.py
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "dist" / "RiskPulse" / "RiskPulse.exe"


def main():
    if not EXE.exists():
        print(f"!! Executable not found: {EXE}")
        print(f"   Run: python build_scripts/build.py")
        return 1

    size_mb = EXE.stat().st_size / 1e6
    bundle_size = sum(f.stat().st_size for f in EXE.parent.rglob("*")) / 1e6
    print(f"  Executable : {EXE}")
    print(f"  Exe size   : {size_mb:.1f} MB")
    print(f"  Bundle size: {bundle_size:.0f} MB")
    print()
    print("  Launching for 10s to verify it boots...")

    proc = subprocess.Popen(
        [str(EXE)],
        cwd=str(EXE.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        time.sleep(10)
        if proc.poll() is None:
            print("  OK : process is alive after 10s")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            return 0
        else:
            print(f"  FAIL : process exited with code {proc.returncode}")
            stdout, stderr = proc.communicate(timeout=5)
            if stdout:
                print(f"  stdout: {stdout.decode(errors='replace')[:500]}")
            if stderr:
                print(f"  stderr: {stderr.decode(errors='replace')[:1000]}")
            return 1
    except Exception as e:
        print(f"!! Error during test: {e}")
        if proc.poll() is None:
            proc.kill()
        return 1


if __name__ == "__main__":
    sys.exit(main())
