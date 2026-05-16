"""Test E2E auth + permissions + audit log."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
db = Path("data/knowledge.db")
if db.exists():
    db.unlink()
session = Path("data/session.json")
if session.exists():
    session.unlink()

from services.auth_service import get_auth, ROLES
from services.permissions import PERM, can, role_has

auth = get_auth()

print("=== 1. Bootstrap admin ===")
users = auth.list_users()
print(f"  Users initiaux : {len(users)}")
for u in users:
    print(f"    {u.username} ({u.role}) active={u.active}")
print()

print("=== 2. Login admin/admin ===")
user = auth.login("admin", "admin")
print(f"  Logged in : {user.username} role={user.role}")
print(f"  Current   : {auth.current_user.username}")
print()

print("=== 3. Permissions ===")
for perm in [PERM.RUN_ANALYSIS, PERM.MANAGE_USERS, PERM.CLEAR_KB, PERM.EXPORT_DATA]:
    print(f"  {perm:20s} -> admin={can(perm)}, "
          f"analyst={role_has('analyst', perm)}, "
          f"viewer={role_has('viewer', perm)}")
print()

print("=== 4. Cree des users ===")
analyst = auth.register(username="alice", password="alice123",
                          full_name="Alice Analyst", email="alice@bank.ma",
                          role="analyst")
print(f"  Created : {analyst.username} ({analyst.role})")
viewer = auth.register(username="bob", password="bob1234",
                         full_name="Bob Viewer", role="viewer")
print(f"  Created : {viewer.username} ({viewer.role})")
print()

print("=== 5. Login alice (analyst) ===")
auth.logout()
alice = auth.login("alice", "alice123")
print(f"  Logged in : {alice.username}")
print(f"  Can RUN_ANALYSIS : {can(PERM.RUN_ANALYSIS)}")
print(f"  Can MANAGE_USERS : {can(PERM.MANAGE_USERS)}")
print(f"  Can CLEAR_KB     : {can(PERM.CLEAR_KB)}")
print()

print("=== 6. Login bob (viewer) ===")
auth.logout()
bob = auth.login("bob", "bob1234")
print(f"  Logged in : {bob.username}")
print(f"  Can VIEW_KB      : {can(PERM.VIEW_KB)}")
print(f"  Can RUN_ANALYSIS : {can(PERM.RUN_ANALYSIS)}")
print(f"  Can EXPORT_DATA  : {can(PERM.EXPORT_DATA)}")
print()

print("=== 7. Mauvais password ===")
auth.logout()
bad = auth.login("admin", "wrong_password")
print(f"  Result : {bad}")
print()

print("=== 8. User inactif ===")
auth.login("admin", "admin")
auth.set_active(bob.id, False)
auth.logout()
result = auth.login("bob", "bob1234")
print(f"  Bob disabled, login result : {result}")
print()

print("=== 9. Reset password ===")
auth.login("admin", "admin")
auth.reset_password(viewer.id, "newpass")
auth.set_active(viewer.id, True)
auth.logout()
bob2 = auth.login("bob", "newpass")
print(f"  After reset+enable, login : {bob2.username if bob2 else 'FAIL'}")
print()

print("=== 10. Audit log ===")
audit = auth.list_audit(limit=30)
print(f"  {len(audit)} entrees d'audit")
for a in audit[:10]:
    ok = "OK" if a.get("success", 1) else "FAIL"
    print(f"  [{a['timestamp'][11:19]}] {(a.get('username') or '-'):10s} "
          f"{a['action']:15s} {ok}  {(a.get('details') or '')[:50]}")
