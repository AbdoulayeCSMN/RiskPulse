"""
Licensing service : ED25519-signed offline activation keys.

Architecture
------------
- Aucune dependance serveur. Tout est verifie offline avec une signature
  ED25519 (cle publique embarquee dans l'app, cle privee gardee par toi).
- Plans :
    FREE        : core features + trial 14 jours pour les plans superieurs
    PRO         : NLP avance, Predictive, Banking Pack, Audit log
    ENTERPRISE  : Tout + REST API + Multi-user RBAC + Watch lists illimitees
- Trial de 14 jours auto declenche au premier lancement. La date du premier
  lancement est ecrite dans data/license.json (et hashee dans la KB pour
  detecter une reset locale grossiere).
- Format de la cle (texte) : Base64URL(JSON payload) + "." + Base64URL(sig)
    payload = {
        "v":     1,
        "plan":  "PRO" | "ENTERPRISE",
        "email": "user@example.com",
        "iat":   1700000000,
        "exp":   1731536000        # 0 => perpetuelle
    }
- Verification : signature ED25519 du JSON payload bytes-equivalent.
"""

from __future__ import annotations

import base64
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Optional, Set

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from utils.paths import paths

log = logging.getLogger("riskpulse.licensing")


# ─────────────────────────────────────────────────────────────────────────────
# CLE PUBLIQUE EMBARQUEE
# ─────────────────────────────────────────────────────────────────────────────
# Cette cle publique correspond a la cle privee que TOI seul possede
# (generee par tools/generate_license.py). Personne ne peut forger une
# licence valide sans cette cle privee.
#
# A REMPLACER apres avoir genere la paire avec tools/generate_license.py
# (commande : python tools/generate_license.py --init)
PUBLIC_KEY_B64 = "Lk3cz3QZ1HGkRW4syhR96vbKprctyDn1B4zdnBx-w0c"

TRIAL_DAYS = 14


class Plan(str, Enum):
    FREE        = "FREE"
    PRO         = "PRO"
    ENTERPRISE  = "ENTERPRISE"


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE MAP
# ─────────────────────────────────────────────────────────────────────────────
# Chaque feature mappe au plan MINIMUM qui peut l'utiliser.
# Pendant le trial, l'utilisateur a temporairement le plan ENTERPRISE.

FEATURE_MIN_PLAN = {
    # Core (FREE) ─────────────────────────────────────
    "analyse_basic":        Plan.FREE,
    "knowledge_base":       Plan.FREE,
    "i18n":                 Plan.FREE,
    "export_pdf":           Plan.FREE,
    # Pro ─────────────────────────────────────────────
    "nlp_advanced":         Plan.PRO,
    "predictive":           Plan.PRO,
    "banking_pack":         Plan.PRO,
    "ai_insights":          Plan.PRO,
    "audit_log":            Plan.PRO,
    "watchlist":            Plan.PRO,
    # Enterprise ──────────────────────────────────────
    "rest_api":             Plan.ENTERPRISE,
    "multi_user":           Plan.ENTERPRISE,
    "monitoring_unlimited": Plan.ENTERPRISE,
    "wikidata_enrichment":  Plan.ENTERPRISE,
}

_PLAN_RANK = {Plan.FREE: 0, Plan.PRO: 1, Plan.ENTERPRISE: 2}


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LicenseState:
    plan:          Plan          = Plan.FREE
    email:         str           = ""
    expires_at:    Optional[int] = None       # epoch seconds, None = perpetual
    issued_at:     Optional[int] = None
    is_trial:      bool          = False
    trial_started: Optional[int] = None
    trial_ends:    Optional[int] = None
    raw_key:       str           = ""
    error:         str           = ""

    def is_valid(self) -> bool:
        if self.error:
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True

    def effective_plan(self) -> Plan:
        """Plan reel applique : trial -> ENTERPRISE, sinon plan paye, sinon FREE."""
        if self.is_trial and self.trial_active():
            return Plan.ENTERPRISE
        if self.is_valid() and self.plan != Plan.FREE:
            return self.plan
        return Plan.FREE

    def trial_active(self) -> bool:
        return bool(self.is_trial and self.trial_ends and time.time() < self.trial_ends)

    def trial_days_left(self) -> int:
        if not self.trial_ends:
            return 0
        secs = self.trial_ends - time.time()
        return max(0, int(secs // 86400))

    def to_dict(self) -> dict:
        return {
            "plan":          self.plan.value,
            "email":         self.email,
            "expires_at":    self.expires_at,
            "issued_at":     self.issued_at,
            "is_trial":      self.is_trial,
            "trial_started": self.trial_started,
            "trial_ends":    self.trial_ends,
            "raw_key":       self.raw_key,
            "error":         self.error,
        }


# ─────────────────────────────────────────────────────────────────────────────
# LICENSE MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class LicenseManager:
    """Singleton qui charge / verifie / persiste la licence."""

    _instance: Optional["LicenseManager"] = None
    _lock = RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.state = LicenseState()
        self._path = paths.data_dir / "license.json"
        self._load()

    # ── Persistence ─────────────────────────────────

    def _load(self):
        """Charge license.json ou demarre le trial au premier lancement."""
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                # Si une raw_key est presente, on la re-verifie (anti-tamper).
                raw_key = data.get("raw_key", "")
                if raw_key:
                    st = self._verify_key(raw_key)
                    # Reapplique les infos trial du fichier (pas dans la cle)
                    st.is_trial      = bool(data.get("is_trial"))
                    st.trial_started = data.get("trial_started")
                    st.trial_ends    = data.get("trial_ends")
                    self.state = st
                else:
                    # Trial-only state
                    self.state = LicenseState(
                        plan          = Plan(data.get("plan", "FREE")),
                        is_trial      = bool(data.get("is_trial")),
                        trial_started = data.get("trial_started"),
                        trial_ends    = data.get("trial_ends"),
                    )
            except Exception as exc:
                log.warning("license.json corrupted, restarting trial: %s", exc)
                self._start_trial()
        else:
            self._start_trial()

    def _save(self):
        try:
            self._path.write_text(
                json.dumps(self.state.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            log.error("Cannot save license.json: %s", exc)

    def _start_trial(self):
        now = int(time.time())
        ends = int((datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)).timestamp())
        self.state = LicenseState(
            plan          = Plan.FREE,
            is_trial      = True,
            trial_started = now,
            trial_ends    = ends,
        )
        self._save()
        log.info("Trial started, %d days, ends at %s", TRIAL_DAYS,
                  datetime.fromtimestamp(ends, tz=timezone.utc).isoformat())

    # ── Verification ────────────────────────────────

    @staticmethod
    def _b64url_decode(s: str) -> bytes:
        pad = "=" * (-len(s) % 4)
        return base64.urlsafe_b64decode(s + pad)

    def _verify_key(self, raw: str) -> LicenseState:
        """Verifie la signature ED25519 de la cle et retourne un LicenseState."""
        try:
            raw = raw.strip().replace("\n", "").replace(" ", "")
            if "." not in raw:
                return LicenseState(error="Format invalide : '.' manquant")
            payload_b64, sig_b64 = raw.split(".", 1)
            payload_bytes = self._b64url_decode(payload_b64)
            sig_bytes     = self._b64url_decode(sig_b64)

            if PUBLIC_KEY_B64 == "REPLACE_WITH_YOUR_PUBLIC_KEY_BASE64":
                return LicenseState(error="Cle publique non configuree (build dev)")

            pub_raw = self._b64url_decode(PUBLIC_KEY_B64)
            pub     = Ed25519PublicKey.from_public_bytes(pub_raw)
            pub.verify(sig_bytes, payload_bytes)

            payload = json.loads(payload_bytes.decode("utf-8"))
            plan    = Plan(payload.get("plan", "FREE"))
            exp     = payload.get("exp") or None
            iat     = payload.get("iat") or None
            email   = payload.get("email", "")

            st = LicenseState(
                plan       = plan,
                email      = email,
                issued_at  = iat,
                expires_at = exp,
                raw_key    = raw,
            )
            if exp and time.time() > exp:
                st.error = "Licence expiree"
            return st

        except InvalidSignature:
            return LicenseState(error="Signature invalide (cle forgee ou corrompue)")
        except Exception as exc:
            return LicenseState(error=f"Cle illisible : {exc}")

    # ── API publique ────────────────────────────────

    def activate(self, raw_key: str) -> LicenseState:
        """Active une cle. Retourne le LicenseState resultant."""
        st = self._verify_key(raw_key)
        if st.error:
            log.warning("License activation failed: %s", st.error)
            return st
        # L'achat termine le trial : on conserve trial_started pour l'audit
        # mais on coupe is_trial / trial_ends pour que effective_plan() reflete
        # le plan paye et pas un trial Enterprise residuel.
        st.is_trial      = False
        st.trial_started = self.state.trial_started
        st.trial_ends    = None
        self.state = st
        self._save()
        log.info("License activated: plan=%s email=%s exp=%s",
                  st.plan.value, st.email, st.expires_at)
        return st

    def deactivate(self):
        """Supprime la licence (garde le trial)."""
        was_trial      = self.state.is_trial
        trial_started  = self.state.trial_started
        trial_ends     = self.state.trial_ends
        self.state = LicenseState(
            plan          = Plan.FREE,
            is_trial      = was_trial,
            trial_started = trial_started,
            trial_ends    = trial_ends,
        )
        self._save()

    def can_use(self, feature: str) -> bool:
        """True si la feature est dispo dans le plan effectif courant."""
        required = FEATURE_MIN_PLAN.get(feature, Plan.ENTERPRISE)
        return _PLAN_RANK[self.state.effective_plan()] >= _PLAN_RANK[required]

    def required_plan(self, feature: str) -> Plan:
        return FEATURE_MIN_PLAN.get(feature, Plan.ENTERPRISE)

    def status_summary(self) -> str:
        st = self.state
        if st.is_trial and st.trial_active():
            return f"Trial Enterprise - {st.trial_days_left()} jours restants"
        if not st.is_valid():
            return f"FREE (licence : {st.error or 'aucune'})"
        if st.expires_at:
            d = datetime.fromtimestamp(st.expires_at, tz=timezone.utc).strftime("%Y-%m-%d")
            return f"{st.plan.value} - expire le {d}"
        return f"{st.plan.value} - perpetuelle"


# Singleton accessor
def get_license_manager() -> LicenseManager:
    return LicenseManager()
