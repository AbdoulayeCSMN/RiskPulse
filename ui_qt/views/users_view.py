"""
Vue Users & Audit — admin only.

Trois sections :
  1. Stats (users, active, audit entries)
  2. Users table (avec actions : promote, deactivate, reset, delete)
  3. Audit log (filtrable)
"""

import logging
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QInputDialog, QDialog,
)

from ..components import Card, MetricCard
from ..i18n import tr
from ._base import build_header
from services.auth_service import get_auth, ROLES
from services.permissions import PERM, can

logger = logging.getLogger(__name__)


ROLE_COLORS = {
    "admin":   "#e3c08e",
    "analyst": "#9caec1",
    "viewer":  "#84cc9e",
}

ACTION_COLORS = {
    "LOGIN":         "#84cc9e",
    "LOGOUT":        "#9caec1",
    "LOGIN_FAILED":  "#e8a0a0",
    "CREATE_USER":   "#e3c08e",
    "DELETE_USER":   "#e8a0a0",
    "PROMOTE_USER":  "#e3c08e",
    "RESET_PWD":     "#e3c08e",
    "DEACTIVATE":    "#e8a0a0",
    "ANALYZE":       "#9caec1",
    "EXPORT":        "#9caec1",
}


class UsersView(QWidget):
    def __init__(self, controller, app):
        super().__init__()
        self._controller = controller
        self._app = app
        self._auth = get_auth()
        self._build()

    # ── Construction ─────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(20)

        # Header
        head_row = QHBoxLayout()
        head_col = QVBoxLayout()
        self._caption_lbl, self._title_lbl = build_header(
            head_col, tr("ADMIN"), tr("Users & Audit")
        )
        head_row.addLayout(head_col, 1)

        actions = QHBoxLayout()
        self._btn_add_user = QPushButton(tr("+ New user"))
        self._btn_add_user.setProperty("variant", "primary")
        self._btn_add_user.clicked.connect(self._add_user_dialog)
        actions.addWidget(self._btn_add_user)
        self._btn_refresh = QPushButton(tr("Refresh"))
        self._btn_refresh.clicked.connect(self.refresh)
        actions.addWidget(self._btn_refresh)
        aw = QWidget(); aw.setLayout(actions)
        head_row.addWidget(aw, 0, Qt.AlignTop)
        outer.addLayout(head_row)

        # Subtitle
        self._subtitle = QLabel(tr(
            "Manage user accounts and roles, and review the full audit log "
            "of actions performed on this RiskPulse instance."
        ))
        self._subtitle.setProperty("class", "subtitle")
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        # Stats
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._stat_users  = MetricCard(tr("Users"),         "—")
        self._stat_active = MetricCard(tr("Active"),        "—")
        self._stat_admins = MetricCard(tr("Admins"),        "—")
        self._stat_audit  = MetricCard(tr("Audit entries"), "—")
        for s in (self._stat_users, self._stat_active,
                  self._stat_admins, self._stat_audit):
            s.setMinimumHeight(82)
            stats_row.addWidget(s)
        outer.addLayout(stats_row)

        # Splitter visuel : Users (top) + Audit (bottom)
        body = QVBoxLayout()
        body.setSpacing(16)
        outer.addLayout(body, 1)

        # Users card
        self._users_card = Card(tr("User Accounts"))
        users_inner = QVBoxLayout()
        self._users_table = QTableWidget(0, 7)
        self._users_table.setHorizontalHeaderLabels([
            tr("USERNAME"), tr("FULL NAME"), tr("EMAIL"),
            tr("ROLE"), tr("STATUS"), tr("LAST LOGIN"), tr("ACTIONS"),
        ])
        h = self._users_table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self._users_table.verticalHeader().setVisible(False)
        self._users_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._users_table.setAlternatingRowColors(True)
        users_inner.addWidget(self._users_table)
        self._users_card.layout().addLayout(users_inner)
        body.addWidget(self._users_card)

        # Audit card
        self._audit_card = Card(tr("Audit Log"))
        audit_inner = QVBoxLayout()
        audit_inner.setSpacing(8)
        # Filtres
        filter_row = QHBoxLayout()
        fl = QLabel(tr("FILTER"))
        fl.setProperty("class", "caption")
        filter_row.addWidget(fl)
        self._audit_filter = QLineEdit()
        self._audit_filter.setPlaceholderText(tr("Action contains..."))
        self._audit_filter.textChanged.connect(self._refresh_audit)
        filter_row.addWidget(self._audit_filter, 1)
        audit_inner.addLayout(filter_row)

        # Table
        self._audit_table = QTableWidget(0, 5)
        self._audit_table.setHorizontalHeaderLabels([
            tr("TIMESTAMP"), tr("USER"), tr("ACTION"),
            tr("DETAILS"), tr("OK"),
        ])
        h2 = self._audit_table.horizontalHeader()
        h2.setSectionResizeMode(QHeaderView.Stretch)
        h2.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h2.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h2.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._audit_table.verticalHeader().setVisible(False)
        self._audit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._audit_table.setAlternatingRowColors(True)
        audit_inner.addWidget(self._audit_table)
        self._audit_card.layout().addLayout(audit_inner)
        body.addWidget(self._audit_card, 1)

    # ── Refresh ─────────────────────────────

    def refresh(self):
        users = self._auth.list_users()
        n_users = len(users)
        n_active = sum(1 for u in users if u.active)
        n_admins = sum(1 for u in users if u.role == "admin")
        audit = self._auth.list_audit(limit=200)

        self._stat_users.set_value(str(n_users))
        self._stat_active.set_value(str(n_active))
        self._stat_admins.set_value(str(n_admins))
        self._stat_audit.set_value(str(len(audit)))

        self._render_users(users)
        self._refresh_audit()

    def _render_users(self, users: list):
        self._users_table.setRowCount(len(users))
        current_id = self._auth.current_user.id if self._auth.current_user else None
        for row, u in enumerate(users):
            self._users_table.setItem(row, 0, QTableWidgetItem(u.username))
            self._users_table.setItem(row, 1, QTableWidgetItem(u.full_name or "—"))
            self._users_table.setItem(row, 2, QTableWidgetItem(u.email or "—"))

            # Role colore
            role_item = QTableWidgetItem(u.role.upper())
            role_item.setForeground(QBrush(QColor(
                ROLE_COLORS.get(u.role, "#9ca3af")
            )))
            self._users_table.setItem(row, 3, role_item)

            # Status
            status_item = QTableWidgetItem("ACTIVE" if u.active else "DISABLED")
            status_item.setForeground(QBrush(QColor(
                "#84cc9e" if u.active else "#52525b"
            )))
            self._users_table.setItem(row, 4, status_item)

            # Last login
            ll = (u.last_login or "—")[:16]
            self._users_table.setItem(row, 5, QTableWidgetItem(ll))

            # Actions inline (boutons)
            act_widget = QWidget()
            al = QHBoxLayout(act_widget)
            al.setContentsMargins(0, 0, 0, 0)
            al.setSpacing(2)
            for label, callback, danger in [
                ("Role",  lambda _, uid=u.id: self._change_role(uid), False),
                ("Pass",  lambda _, uid=u.id: self._reset_pwd(uid), False),
                ("On/Off", lambda _, uid=u.id, act=u.active: self._toggle_active(uid, act),
                 False),
                ("Del",   lambda _, uid=u.id: self._delete_user(uid), True),
            ]:
                btn = QPushButton(label)
                btn.setStyleSheet(
                    f"QPushButton {{ padding: 2px 6px; font-size: 9px;"
                    f"  color: {'#e8a0a0' if danger else '#9ca3af'};"
                    f"  border: 1px solid #1c1c20; }}"
                    f"QPushButton:hover {{ color: #e4e4e7; border-color: #27272a; }}"
                )
                # On empeche l'admin courant de se supprimer lui-meme
                if u.id == current_id and label in ("Del", "On/Off"):
                    btn.setEnabled(False)
                btn.clicked.connect(callback)
                al.addWidget(btn)
            self._users_table.setCellWidget(row, 6, act_widget)

    def _refresh_audit(self):
        filt = self._audit_filter.text().strip()
        audit = self._auth.list_audit(limit=200, action=filt)
        self._audit_table.setRowCount(len(audit))
        for row, a in enumerate(audit):
            self._audit_table.setItem(row, 0, QTableWidgetItem(
                (a["timestamp"] or "")[:19]
            ))
            self._audit_table.setItem(row, 1, QTableWidgetItem(
                a.get("username") or "—"
            ))
            # Action colore
            action = a["action"] or ""
            ai = QTableWidgetItem(action)
            ai.setForeground(QBrush(QColor(
                ACTION_COLORS.get(action, "#9ca3af")
            )))
            self._audit_table.setItem(row, 2, ai)
            details = a.get("details") or ""
            self._audit_table.setItem(row, 3, QTableWidgetItem(details))
            ok = "✓" if a.get("success", 1) else "✗"
            ok_item = QTableWidgetItem(ok)
            ok_item.setForeground(QBrush(QColor(
                "#84cc9e" if a.get("success", 1) else "#e8a0a0"
            )))
            self._audit_table.setItem(row, 4, ok_item)

    # ── Actions ───────────────────────────────

    def _add_user_dialog(self):
        from PySide6.QtWidgets import (
            QDialog, QFormLayout, QDialogButtonBox
        )
        d = QDialog(self)
        d.setWindowTitle(tr("New user"))
        d.setFixedSize(360, 280)
        layout = QFormLayout(d)

        username = QLineEdit()
        full_name = QLineEdit()
        email = QLineEdit()
        password = QLineEdit()
        password.setEchoMode(QLineEdit.Password)
        role = QComboBox()
        role.addItems(ROLES)
        role.setCurrentText("viewer")

        layout.addRow("Username", username)
        layout.addRow("Full name", full_name)
        layout.addRow("Email", email)
        layout.addRow("Password", password)
        layout.addRow("Role", role)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(d.accept)
        btn_box.rejected.connect(d.reject)
        layout.addRow(btn_box)

        if d.exec() != QDialog.Accepted:
            return
        try:
            new_user = self._auth.register(
                username=username.text().strip(),
                password=password.text(),
                full_name=full_name.text().strip(),
                email=email.text().strip(),
                role=role.currentText(),
            )
            self._auth.log_action(
                user_id=self._auth.current_user.id,
                username=self._auth.current_user.username,
                action="CREATE_USER",
                resource_type="user", resource_id=str(new_user.id),
                details=f"Created {new_user.username} ({new_user.role})",
            )
            self._app.toast(f"User '{new_user.username}' created", "success")
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, tr("Error"), str(e))

    def _change_role(self, user_id: int):
        new_role, ok = QInputDialog.getItem(
            self, tr("Change role"), tr("New role:"),
            ROLES, 0, False
        )
        if not ok:
            return
        self._auth.set_role(user_id, new_role)
        self._auth.log_action(
            user_id=self._auth.current_user.id,
            username=self._auth.current_user.username,
            action="PROMOTE_USER",
            resource_type="user", resource_id=str(user_id),
            details=f"Role -> {new_role}",
        )
        self._app.toast(f"Role updated to {new_role}", "success")
        self.refresh()

    def _reset_pwd(self, user_id: int):
        new_pwd, ok = QInputDialog.getText(
            self, tr("Reset password"), tr("New password:"),
            QLineEdit.Password
        )
        if not ok or not new_pwd:
            return
        try:
            self._auth.reset_password(user_id, new_pwd)
            self._auth.log_action(
                user_id=self._auth.current_user.id,
                username=self._auth.current_user.username,
                action="RESET_PWD",
                resource_type="user", resource_id=str(user_id),
                details="Password reset by admin",
            )
            self._app.toast(tr("Password reset"), "success")
        except Exception as e:
            QMessageBox.warning(self, tr("Error"), str(e))

    def _toggle_active(self, user_id: int, currently_active: bool):
        self._auth.set_active(user_id, not currently_active)
        self._auth.log_action(
            user_id=self._auth.current_user.id,
            username=self._auth.current_user.username,
            action="DEACTIVATE" if currently_active else "ACTIVATE",
            resource_type="user", resource_id=str(user_id),
            details=("Deactivated" if currently_active else "Reactivated"),
        )
        self._app.toast(
            tr("User disabled") if currently_active else tr("User enabled"),
            "success"
        )
        self.refresh()

    def _delete_user(self, user_id: int):
        ans = QMessageBox.question(
            self, tr("Delete user"),
            tr("Delete this user permanently? This cannot be undone."),
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        self._auth.delete_user(user_id)
        self._auth.log_action(
            user_id=self._auth.current_user.id,
            username=self._auth.current_user.username,
            action="DELETE_USER",
            resource_type="user", resource_id=str(user_id),
            details="User permanently deleted",
        )
        self._app.toast(tr("User deleted"), "warning")
        self.refresh()

    # ── Hooks ─────────────────────────────────

    def on_analysis_updated(self):
        pass

    def on_show(self):
        self.refresh()

    def retranslate(self):
        self._caption_lbl.setText(tr("ADMIN"))
        self._title_lbl.setText(tr("Users & Audit"))
        self._subtitle.setText(tr(
            "Manage user accounts and roles, and review the full audit log "
            "of actions performed on this RiskPulse instance."
        ))
        self._btn_add_user.setText(tr("+ New user"))
        self._btn_refresh.setText(tr("Refresh"))
        self._stat_users.set_label(tr("Users"))
        self._stat_active.set_label(tr("Active"))
        self._stat_admins.set_label(tr("Admins"))
        self._stat_audit.set_label(tr("Audit entries"))
        self._users_card.set_title(tr("User Accounts"))
        self._audit_card.set_title(tr("Audit Log"))
