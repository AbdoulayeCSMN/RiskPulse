"""Test E2E auto-updater (sans serveur reel) : manifest local + verification SHA."""
import sys, hashlib, json, http.server, socketserver, threading, tempfile, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from services.updater import Updater, version_gt


def test_version_compare():
    print("\n=== Version comparison ===")
    cases = [
        ("1.0.1", "1.0.0", True),
        ("1.0.0", "1.0.1", False),
        ("2.0.0", "1.9.9", True),
        ("1.0.0", "1.0.0", False),
        ("v1.0.1", "1.0.0", True),         # accept 'v' prefix
        ("1.0.1-rc1", "1.0.0", True),       # ignore pre-release
    ]
    for a, b, expected in cases:
        got = version_gt(a, b)
        status = "OK" if got == expected else "FAIL"
        print(f"  [{status}] {a} > {b} = {got} (expected {expected})")


def test_manifest_check():
    print("\n=== Manifest check (local HTTP server) ===")
    # Cree un manifest temporaire + serveur HTTP local
    tmp = Path(tempfile.mkdtemp())
    fake_zip = tmp / "fake-update.zip"
    # Cree un faux zip valide (bundle RiskPulse minimal)
    with zipfile.ZipFile(fake_zip, "w") as z:
        z.writestr("RiskPulse/RiskPulse.exe", b"fake-exe-content")
        z.writestr("RiskPulse/README.txt", b"This is a test update.")

    sha = hashlib.sha256(fake_zip.read_bytes()).hexdigest()
    size = fake_zip.stat().st_size
    manifest = {
        "latest":       "9.9.9",
        "released_at":  "2026-06-01T00:00:00Z",
        "channel":      "stable",
        "url":          f"http://localhost:8899/{fake_zip.name}",
        "sha256":       sha,
        "size":         size,
        "notes":        "Test release notes.\nBug fixes.",
        "mandatory":    False,
    }
    (tmp / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Lance le serveur HTTP sur 8899
    import os
    os.chdir(tmp)
    httpd = socketserver.TCPServer(("127.0.0.1", 8899),
                                     http.server.SimpleHTTPRequestHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    print(f"  Local server : http://localhost:8899  (dir: {tmp})")

    try:
        # Test 1 : current < latest => update available
        updater = Updater(current_version="1.0.0",
                           manifest_url="http://localhost:8899/manifest.json")
        info = updater.check()
        assert info.available, f"Expected available, got: {info.to_dict()}"
        assert info.latest == "9.9.9"
        assert info.sha256 == sha
        print(f"  [OK] Update detected : {info.current} -> {info.latest}")
        print(f"       Notes preview   : {info.notes[:50]}")

        # Test 2 : current == latest => no update
        updater2 = Updater(current_version="9.9.9",
                            manifest_url="http://localhost:8899/manifest.json")
        info2 = updater2.check()
        assert not info2.available, f"Expected NOT available, got: {info2.to_dict()}"
        print(f"  [OK] No update when current == latest")

        # Test 3 : download + verify SHA
        path = updater.download(info)
        assert path is not None, "Download failed"
        assert path.exists(), f"File missing: {path}"
        downloaded_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        assert downloaded_sha == sha, "SHA mismatch (should not happen if download verified)"
        print(f"  [OK] Download verified : {path.stat().st_size} bytes, SHA OK")

        # Test 4 : download fails with bad SHA
        bad_info = info
        bad_info.sha256 = "0" * 64
        path2 = updater.download(bad_info)
        assert path2 is None, "Download should fail on SHA mismatch"
        print(f"  [OK] Rejected file with wrong SHA-256")

    finally:
        httpd.shutdown()
        os.chdir("/")


def test_unreachable_manifest():
    print("\n=== Manifest unreachable ===")
    updater = Updater(current_version="1.0.0",
                       manifest_url="http://localhost:1/no-such-manifest.json")
    info = updater.check(timeout=2)
    assert not info.available
    assert info.error
    print(f"  [OK] Error caught gracefully : {info.error[:60]}")


if __name__ == "__main__":
    test_version_compare()
    test_manifest_check()
    test_unreachable_manifest()
    print("\n=== ALL OK ===")
