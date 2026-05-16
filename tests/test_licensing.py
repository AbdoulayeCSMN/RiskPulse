"""Test E2E licensing : trial, activation valide, expiry, forge rejetee."""
from __future__ import annotations

import os
import sys
import time
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Isole les ecritures dans un dossier temp AVANT d'importer le module.
_TMP = Path(tempfile.mkdtemp(prefix="riskpulse_lic_"))
os.environ["RISKPULSE_DEV"] = "1"

# Patch utils.paths.data_dir vers le tmp
from utils.paths import paths  # noqa: E402
paths._user_dir = _TMP
(paths._user_dir / "data").mkdir(parents=True, exist_ok=True)


def _reset_manager():
    """Reinstancie le singleton entre tests."""
    from services import licensing
    licensing.LicenseManager._instance = None
    # Vide license.json
    lic = paths.data_dir / "license.json"
    if lic.exists():
        lic.unlink()


def test_trial_starts_on_first_run():
    print("\n=== Trial auto au premier lancement ===")
    _reset_manager()
    from services.licensing import get_license_manager, Plan
    mgr = get_license_manager()
    assert mgr.state.is_trial, "Trial doit demarrer auto"
    assert mgr.state.trial_active(), "Trial doit etre actif"
    assert mgr.state.effective_plan() == Plan.ENTERPRISE, "Trial = Enterprise"
    assert mgr.can_use("predictive"), "Trial doit autoriser predictive"
    assert mgr.can_use("rest_api"), "Trial doit autoriser REST API"
    days = mgr.state.trial_days_left()
    assert 13 <= days <= 14, f"Trial doit etre ~14 jours (got {days})"
    print(f"  [OK] Trial actif, {days} jours restants, plan effectif = ENTERPRISE")


def test_activate_valid_key():
    print("\n=== Activation cle valide (PRO 30j) ===")
    _reset_manager()
    from services.licensing import get_license_manager, Plan
    from tools.generate_license import generate_license
    key = generate_license("PRO", "alice@example.com", days=30, perpetual=False)
    mgr = get_license_manager()
    st = mgr.activate(key)
    assert not st.error, f"Activation doit reussir : {st.error}"
    assert st.plan == Plan.PRO
    assert st.email == "alice@example.com"
    assert mgr.can_use("predictive"), "PRO doit avoir predictive"
    assert mgr.can_use("banking_pack"), "PRO doit avoir banking_pack"
    assert not mgr.can_use("rest_api"), "PRO ne doit PAS avoir rest_api"
    print(f"  [OK] PRO active, predictive=on, rest_api=off")


def test_activate_enterprise():
    print("\n=== Activation cle ENTERPRISE perpetuelle ===")
    _reset_manager()
    from services.licensing import get_license_manager
    from tools.generate_license import generate_license
    key = generate_license("ENTERPRISE", "bob@corp.com", days=0, perpetual=True)
    mgr = get_license_manager()
    st = mgr.activate(key)
    assert not st.error, st.error
    assert not st.expires_at, "Perpetual => exp falsy (None ou 0)"
    assert mgr.can_use("rest_api"), "ENTERPRISE doit avoir REST API"
    assert mgr.can_use("multi_user"), "ENTERPRISE doit avoir multi_user"
    print(f"  [OK] ENTERPRISE perpetuelle, toutes features actives")


def test_expired_key_rejected():
    print("\n=== Cle expiree rejetee ===")
    _reset_manager()
    from services.licensing import get_license_manager, Plan
    from tools.generate_license import generate_license
    # Cle deja expiree : on signe avec exp=now-86400
    import json, base64, time as _t
    from cryptography.hazmat.primitives import serialization
    from tools.generate_license import PRIV, b64url
    priv = serialization.load_pem_private_key(PRIV.read_bytes(), password=None)
    payload = {"v":1, "plan":"PRO", "email":"x@y.com",
                "iat": int(_t.time()) - 7200, "exp": int(_t.time()) - 3600}
    pb = json.dumps(payload, sort_keys=True, separators=(",",":")).encode()
    sig = priv.sign(pb)
    expired_key = b64url(pb) + "." + b64url(sig)
    mgr = get_license_manager()
    st = mgr.activate(expired_key)
    assert st.error and "expir" in st.error.lower(), f"Doit signaler expiration : {st.error}"
    # Le plan effectif retombe en FREE (le trial est toujours la mais on a
    # ecrase l'etat -- ici on s'attend a FREE puisqu'aucune licence valide)
    print(f"  [OK] Cle expiree rejetee : {st.error}")


def test_forged_key_rejected():
    print("\n=== Cle forgee rejetee (mauvaise signature) ===")
    _reset_manager()
    from services.licensing import get_license_manager
    import json, base64
    payload = {"v":1, "plan":"ENTERPRISE", "email":"hacker@evil.com",
                "iat":0, "exp":0}
    pb = json.dumps(payload, sort_keys=True, separators=(",",":")).encode()
    # Signature aleatoire
    fake_sig = b"\x00" * 64
    forged = (base64.urlsafe_b64encode(pb).rstrip(b"=").decode()
                + "." + base64.urlsafe_b64encode(fake_sig).rstrip(b"=").decode())
    mgr = get_license_manager()
    st = mgr.activate(forged)
    assert st.error, "Doit rejeter une cle forgee"
    assert "signature" in st.error.lower() or "invalide" in st.error.lower(), st.error
    print(f"  [OK] Cle forgee rejetee : {st.error}")


def test_malformed_key_rejected():
    print("\n=== Cle malformee rejetee ===")
    _reset_manager()
    from services.licensing import get_license_manager
    mgr = get_license_manager()
    for bad in ["pas_un_point", "abc.def.ghi", "", "@@@.###"]:
        st = mgr.activate(bad)
        assert st.error, f"Doit rejeter '{bad}'"
    print(f"  [OK] 4 formes malformees rejetees")


def test_feature_gating_free():
    print("\n=== Feature gating FREE (trial expire) ===")
    _reset_manager()
    from services.licensing import get_license_manager, Plan
    mgr = get_license_manager()
    # Force trial expire
    mgr.state.is_trial   = True
    mgr.state.trial_ends = int(time.time()) - 1
    mgr.state.plan       = Plan.FREE
    assert mgr.state.effective_plan() == Plan.FREE
    assert mgr.can_use("analyse_basic"), "FREE doit avoir l'analyse de base"
    assert mgr.can_use("knowledge_base")
    assert not mgr.can_use("predictive"), "FREE ne doit PAS avoir predictive"
    assert not mgr.can_use("banking_pack")
    assert not mgr.can_use("rest_api")
    print(f"  [OK] FREE = core only, premium gating actif")


if __name__ == "__main__":
    try:
        test_trial_starts_on_first_run()
        test_activate_valid_key()
        test_activate_enterprise()
        test_expired_key_rejected()
        test_forged_key_rejected()
        test_malformed_key_rejected()
        test_feature_gating_free()
        print("\n=== ALL OK ===")
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
