"""
Outil offline pour generer des cles de licence RiskPulse.

USAGE
-----

1) Premiere fois : genere ta paire de cles ED25519
   --------------------------------------------------
   python tools/generate_license.py --init

   Cree :
       tools/keys/riskpulse_private.pem   (GARDE-LA secrete, ne commit pas)
       tools/keys/riskpulse_public.b64    (a coller dans services/licensing.py)

2) Generer une licence pour un client
   --------------------------------------------------
   python tools/generate_license.py \
       --plan PRO \
       --email "client@example.com" \
       --days 365

   Affiche la cle a copier-coller au client (texte unique avec un point).

3) Generer une licence perpetuelle
   --------------------------------------------------
   python tools/generate_license.py --plan ENTERPRISE --email "x@y.com" --perpetual

SECURITE
--------
- La cle privee NE QUITTE JAMAIS ta machine.
- Mets tools/keys/ dans .gitignore.
- Si la cle privee fuite -> regenere une nouvelle paire et publie une mise
  a jour avec la nouvelle cle publique (les anciennes licences seront alors
  invalides).
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

ROOT     = Path(__file__).resolve().parent
KEYS_DIR = ROOT / "keys"
PRIV     = KEYS_DIR / "riskpulse_private.pem"
PUB_B64  = KEYS_DIR / "riskpulse_public.b64"


def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def init_keypair():
    if PRIV.exists():
        print(f"!! {PRIV} existe deja. Supprime-le manuellement si tu veux regenerer.")
        sys.exit(1)
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    priv = Ed25519PrivateKey.generate()
    pub  = priv.public_key()

    priv_pem = priv.private_bytes(
        encoding             = serialization.Encoding.PEM,
        format               = serialization.PrivateFormat.PKCS8,
        encryption_algorithm = serialization.NoEncryption(),
    )
    pub_raw = pub.public_bytes(
        encoding = serialization.Encoding.Raw,
        format   = serialization.PublicFormat.Raw,
    )
    pub_b64 = b64url(pub_raw)

    PRIV.write_bytes(priv_pem)
    PUB_B64.write_text(pub_b64, encoding="ascii")

    print("\n=== Paire de cles ED25519 generee ===\n")
    print(f"  Private key : {PRIV}")
    print(f"  Public key  : {PUB_B64}")
    print(f"\nCle publique (a coller dans services/licensing.py) :")
    print(f"  PUBLIC_KEY_B64 = \"{pub_b64}\"\n")
    print("!! GARDE la cle privee secrete. Mets tools/keys/ dans .gitignore.\n")


def load_private() -> Ed25519PrivateKey:
    if not PRIV.exists():
        print(f"!! Cle privee absente : {PRIV}")
        print("   Lance d'abord : python tools/generate_license.py --init")
        sys.exit(1)
    return serialization.load_pem_private_key(PRIV.read_bytes(), password=None)


def generate_license(plan: str, email: str, days: int, perpetual: bool) -> str:
    priv = load_private()
    now  = int(time.time())
    if perpetual:
        exp = 0
    else:
        exp = int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp())

    payload = {
        "v":     1,
        "plan":  plan,
        "email": email,
        "iat":   now,
        "exp":   exp,
    }
    # Serialisation deterministe (sort_keys + separators serres) pour que la
    # verification reproduise les memes bytes.
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig           = priv.sign(payload_bytes)
    return b64url(payload_bytes) + "." + b64url(sig)


def main():
    p = argparse.ArgumentParser(description="RiskPulse license generator")
    p.add_argument("--init", action="store_true", help="Genere une paire de cles ED25519")
    p.add_argument("--plan", choices=["PRO", "ENTERPRISE"], help="Plan a vendre")
    p.add_argument("--email", default="", help="Email du client")
    p.add_argument("--days", type=int, default=365, help="Validite en jours (default 365)")
    p.add_argument("--perpetual", action="store_true", help="Licence sans expiration")
    args = p.parse_args()

    if args.init:
        init_keypair()
        return

    if not args.plan or not args.email:
        p.print_help()
        sys.exit(1)

    key = generate_license(args.plan, args.email, args.days, args.perpetual)
    print("\n=== Licence generee ===\n")
    print(f"Plan      : {args.plan}")
    print(f"Email     : {args.email}")
    print(f"Validite  : {'perpetuelle' if args.perpetual else f'{args.days} jours'}")
    print(f"\nCle a livrer au client :\n")
    print(key)
    print()


if __name__ == "__main__":
    main()
