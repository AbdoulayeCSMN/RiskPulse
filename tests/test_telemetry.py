"""Test E2E telemetry : opt-in filtre, crash capture, scrub, export zip."""
from __future__ import annotations

import os
import sys
import tempfile
import shutil
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Isole dans un tmp avant import
_TMP = Path(tempfile.mkdtemp(prefix="riskpulse_telem_"))
os.environ["RISKPULSE_DEV"] = "1"

from utils.paths import paths  # noqa: E402
paths._user_dir = _TMP
(paths._user_dir / "data").mkdir(parents=True, exist_ok=True)


def _reset_singleton():
    from services import telemetry
    telemetry.Telemetry._instance = None
    # Vide telemetry.db et preferences
    for f in (paths.data_dir / "telemetry.db",
               paths.preferences):
        if f.exists():
            f.unlink()


def test_optin_filters_events():
    print("\n=== Opt-out : aucun event enregistre ===")
    _reset_singleton()
    from services.telemetry import get_telemetry
    t = get_telemetry()
    assert not t.enabled, "Telemetry doit etre opt-out par defaut"
    t.event("test_event", {"x": 1})
    t.feature_used("predictive")
    counts = t.counts()
    assert counts["events"] == 0, f"Aucun event quand opt-out, got {counts}"
    print(f"  [OK] Opt-out filtre tous les events (counts={counts})")


def test_optin_records_events():
    print("\n=== Opt-in : events enregistres ===")
    _reset_singleton()
    from services.telemetry import get_telemetry
    t = get_telemetry()
    t.set_enabled(True)
    t.event("app_start", {"version": "1.0.1"})
    t.feature_used("predictive")
    t.feature_used("predictive")
    t.feature_used("banking_pack")
    t.view_shown("analyse")
    counts = t.counts()
    assert counts["events"] == 5, f"5 events attendus, got {counts}"
    usage = t.feature_usage()
    assert any(u["feature"] == "predictive" and u["count"] == 2 for u in usage)
    print(f"  [OK] Opt-in enregistre {counts['events']} events, "
            f"predictive utilise 2x")


def test_crash_capture_always():
    print("\n=== Crash : capture meme en opt-out ===")
    _reset_singleton()
    from services.telemetry import get_telemetry
    t = get_telemetry()
    assert not t.enabled
    try:
        raise ValueError("oops at C:\\Users\\johndoe\\secret.txt -- email me at j@x.com")
    except ValueError:
        import sys as _s
        et, ev, tb = _s.exc_info()
        t.record_crash(et, ev, tb, thread_name="testthread")
    crashes = t.list_crashes()
    assert len(crashes) == 1, f"1 crash attendu, got {len(crashes)}"
    c = crashes[0]
    assert c["exc_type"] == "ValueError"
    assert "<HOME>" in c["exc_value"], f"PATH scrub manquant : {c['exc_value']}"
    assert "<EMAIL>" in c["exc_value"], f"Email scrub manquant : {c['exc_value']}"
    assert "C:\\Users\\johndoe" not in c["traceback"]
    assert "j@x.com" not in c["traceback"]
    print(f"  [OK] Crash capture en opt-out, PATH + EMAIL scrub")


def test_top_errors_and_clear():
    print("\n=== Top errors + clear ===")
    _reset_singleton()
    from services.telemetry import get_telemetry
    t = get_telemetry()
    for _ in range(3):
        try: raise ValueError("a")
        except ValueError:
            import sys as _s
            et, ev, tb = _s.exc_info()
            t.record_crash(et, ev, tb)
    for _ in range(2):
        try: raise KeyError("b")
        except KeyError:
            import sys as _s
            et, ev, tb = _s.exc_info()
            t.record_crash(et, ev, tb)
    tops = t.top_errors()
    assert tops[0]["exc_type"] == "ValueError" and tops[0]["count"] == 3
    assert tops[1]["exc_type"] == "KeyError"   and tops[1]["count"] == 2
    print(f"  [OK] Top errors trie correctement")
    t.clear()
    assert t.counts()["crashes"] == 0
    print(f"  [OK] clear() vide la base")


def test_export_bundle():
    print("\n=== Export support bundle ===")
    _reset_singleton()
    from services.telemetry import get_telemetry
    t = get_telemetry()
    t.set_enabled(True)
    t.event("app_start")
    try: raise RuntimeError("boom")
    except RuntimeError:
        import sys as _s
        et, ev, tb = _s.exc_info()
        t.record_crash(et, ev, tb)

    zip_path = t.export_support_bundle()
    assert zip_path.exists(), f"Zip manquant : {zip_path}"
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        assert "telemetry.db" in names, f"telemetry.db manquant : {names}"
        assert "meta.json" in names, f"meta.json manquant : {names}"
        meta = z.read("meta.json").decode("utf-8")
        assert "RuntimeError" not in meta  # meta n'expose pas les crashes bruts
        assert "counts" in meta
    print(f"  [OK] Bundle {zip_path.name} contient telemetry.db + meta.json")


def test_scrub_helpers():
    print("\n=== Scrub helpers ===")
    from services.telemetry import scrub
    s = "trace at C:\\Users\\alice\\app.py line 12, mail bob@corp.com"
    out = scrub(s)
    assert "<HOME>" in out and "<EMAIL>" in out
    assert "alice" not in out and "bob@" not in out
    print(f"  [OK] scrub() masque path + email")


if __name__ == "__main__":
    try:
        test_optin_filters_events()
        test_optin_records_events()
        test_crash_capture_always()
        test_top_errors_and_clear()
        test_export_bundle()
        test_scrub_helpers()
        print("\n=== ALL OK ===")
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
