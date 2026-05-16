"""
RiskPulse — Auth service.

- Hash de mots de passe via PBKDF2-SHA256 (built-in, sans dependance).
- Session locale persistée dans data/session.json.
- 3 roles : admin / analyst / viewer.
- Bootstrap automatique d'un compte admin/admin au premier lancement.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from services.knowledge_base import get_kb

logger = logging.getLogger(__name__)

try:
    from utils.paths import paths
    SESSION_PATH = paths.session
except Exception:
    SESSION_PATH = Path("data") / "session.json"

# Roles disponibles, du plus puissant au moins
ROLES = ["admin", "analyst", "viewer"]

PBKDF2_ITERATIONS = 200_000
SALT_BYTES = 16
HASH_BYTES = 32


# ─────────────────────────────────────────────
#  Hash utils
# ─────────────────────────────────────────────

def _hash_password(password: str, salt: bytes) -> str:
    """PBKDF2-SHA256, retourne hex."""
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS, HASH_BYTES
    )
    return derived.hex()


def _new_salt() -> bytes:
    return secrets.token_bytes(SALT_BYTES)


# ─────────────────────────────────────────────
#  Dataclass
# ─────────────────────────────────────────────

@dataclass
class User:
    id:         int
    username:   str
    email:      str
    full_name:  str
    role:       str          # admin | analyst | viewer
    created_at: str
    last_login: Optional[str]
    active:     bool

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_analyst(self) -> bool:
        return self.role in ("admin", "analyst")

    @property
    def is_viewer(self) -> bool:
        return self.role in ("admin", "analyst", "viewer")

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "username":   self.username,
            "email":      self.email,
            "full_name":  self.full_name,
            "role":       self.role,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "active":     bool(self.active),
        }


# ─────────────────────────────────────────────
#  AuthService
# ─────────────────────────────────────────────

class AuthService:
    """Login / register / list / promote users."""

    def __init__(self):
        self.kb = get_kb()
        self._current_user: Optional[User] = None
        self._bootstrap_admin_if_needed()

    # ── Bootstrap ──

    def _bootstrap_admin_if_needed(self):
        """Cree un admin/admin si la table est vide."""
        with self.kb._conn() as c:
            row = c.execute("SELECT COUNT(*) FROM users").fetchone()
            if row[0] > 0:
                return
        logger.info("Bootstrap : creation du compte admin par defaut (admin/admin)")
        self.register(
            username="admin", password="admin",
            full_name="Administrator", email="admin@local",
            role="admin",
        )

    # ── Register ──

    def register(self, *, username: str, password: str,
                  full_name: str = "", email: str = "",
                  role: str = "viewer") -> User:
        if not username or not password:
            raise ValueError("Username and password required")
        if role not in ROLES:
            raise ValueError(f"Invalid role: {role}")
        if len(password) < 4:
            raise ValueError("Password too short (min 4 chars)")

        salt = _new_salt()
        pwd_hash = _hash_password(password, salt)
        ts = datetime.now().isoformat()

        with self.kb._conn() as c:
            try:
                cur = c.execute("""
                    INSERT INTO users
                      (username, email, full_name, password_hash, salt,
                       role, created_at, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (username, email, full_name, pwd_hash, salt.hex(),
                       role, ts))
                uid = cur.lastrowid
            except Exception as e:
                raise ValueError(f"Username already exists: {username}") from e

        return self._user_by_id(uid)

    # ── Login ──

    def login(self, username: str, password: str) -> Optional[User]:
        with self.kb._conn() as c:
            row = c.execute(
                "SELECT * FROM users WHERE username=? AND active=1",
                (username,)
            ).fetchone()
            if not row:
                self._audit_failed_login(username, "user_not_found")
                return None

            salt = bytes.fromhex(row["salt"])
            expected = row["password_hash"]
            actual = _hash_password(password, salt)
            if not secrets.compare_digest(expected, actual):
                self._audit_failed_login(username, "wrong_password")
                return None

            c.execute("UPDATE users SET last_login=? WHERE id=?",
                       (datetime.now().isoformat(), row["id"]))

        user = self._user_by_id(row["id"])
        self._current_user = user
        self._save_session(user)
        self.log_action(
            user_id=user.id, username=user.username,
            action="LOGIN", details="Successful login", success=True,
        )
        return user

    def _audit_failed_login(self, username: str, reason: str):
        self.log_action(
            user_id=None, username=username,
            action="LOGIN_FAILED", details=reason, success=False,
        )

    def logout(self):
        if self._current_user:
            self.log_action(
                user_id=self._current_user.id,
                username=self._current_user.username,
                action="LOGOUT", details="User logged out",
            )
        self._current_user = None
        try:
            if SESSION_PATH.exists():
                SESSION_PATH.unlink()
        except Exception:
            pass

    # ── Session ──

    def _save_session(self, user: User):
        SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        token = secrets.token_hex(24)
        with open(SESSION_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "user_id":  user.id,
                "username": user.username,
                "token":    token,
                "ts":       datetime.now().isoformat(),
            }, f, indent=2)

    def restore_session(self) -> Optional[User]:
        """Reprend la session depuis disk si elle existe."""
        if not SESSION_PATH.exists():
            return None
        try:
            with open(SESSION_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            user = self._user_by_id(data.get("user_id"))
            if user and user.active:
                self._current_user = user
                return user
        except Exception as e:
            logger.warning(f"Session restore failed : {e}")
        return None

    @property
    def current_user(self) -> Optional[User]:
        return self._current_user

    # ── CRUD ──

    def list_users(self) -> list[User]:
        with self.kb._conn() as c:
            rows = c.execute(
                "SELECT * FROM users ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_user(r) for r in rows]

    def _user_by_id(self, uid: int) -> Optional[User]:
        with self.kb._conn() as c:
            row = c.execute(
                "SELECT * FROM users WHERE id=?", (uid,)
            ).fetchone()
        return self._row_to_user(row) if row else None

    def _row_to_user(self, row) -> User:
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"] or "",
            full_name=row["full_name"] or "",
            role=row["role"],
            created_at=row["created_at"],
            last_login=row["last_login"],
            active=bool(row["active"]),
        )

    def set_role(self, user_id: int, role: str):
        if role not in ROLES:
            raise ValueError(f"Invalid role: {role}")
        with self.kb._conn() as c:
            c.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))

    def set_active(self, user_id: int, active: bool):
        with self.kb._conn() as c:
            c.execute("UPDATE users SET active=? WHERE id=?",
                       (1 if active else 0, user_id))

    def reset_password(self, user_id: int, new_password: str):
        if len(new_password) < 4:
            raise ValueError("Password too short (min 4 chars)")
        salt = _new_salt()
        h = _hash_password(new_password, salt)
        with self.kb._conn() as c:
            c.execute(
                "UPDATE users SET password_hash=?, salt=? WHERE id=?",
                (h, salt.hex(), user_id),
            )

    def delete_user(self, user_id: int):
        with self.kb._conn() as c:
            c.execute("DELETE FROM users WHERE id=?", (user_id,))

    # ── Audit log ──

    def log_action(self, *, user_id: Optional[int] = None,
                    username: str = "", action: str = "",
                    resource_type: str = "", resource_id: str = "",
                    details: str = "", success: bool = True,
                    ip_address: str = ""):
        with self.kb._conn() as c:
            c.execute("""
                INSERT INTO audit_log
                  (timestamp, user_id, username, action,
                   resource_type, resource_id, details,
                   ip_address, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(), user_id, username, action,
                resource_type, resource_id, details, ip_address,
                1 if success else 0,
            ))

    def list_audit(self, limit: int = 100,
                    user_id: Optional[int] = None,
                    action: str = "") -> list[dict]:
        with self.kb._conn() as c:
            q = "SELECT * FROM audit_log WHERE 1=1 "
            args = []
            if user_id is not None:
                q += "AND user_id=? "
                args.append(user_id)
            if action:
                q += "AND action LIKE ? "
                args.append(f"%{action}%")
            q += "ORDER BY timestamp DESC LIMIT ?"
            args.append(limit)
            rows = c.execute(q, args).fetchall()
        return [dict(r) for r in rows]


# Singleton
_auth: Optional[AuthService] = None

def get_auth() -> AuthService:
    global _auth
    if _auth is None:
        _auth = AuthService()
    return _auth
