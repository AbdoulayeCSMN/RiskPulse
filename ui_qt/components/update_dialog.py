"""
Dialogue d'update : verifie, telecharge, applique.
Lancable depuis Settings ou auto au boot.
"""

import threading
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QFrame, QPlainTextEdit, QMessageBox,
)

from ..i18n import tr
from services.updater import get_updater, UpdateInfo


class UpdateDialog(QDialog):
    """Frameless modal : check / preview notes / download / apply."""

    _check_done    = Signal(object)   # UpdateInfo
    _progress_sig  = Signal(int, int) # (downloaded, total)
    _download_done = Signal(object)   # Path or None

    STATE_CHECKING    = "checking"
    STATE_NO_UPDATE   = "no_update"
    STATE_AVAILABLE   = "available"
    STATE_DOWNLOADING = "downloading"
    STATE_READY       = "ready"
    STATE_ERROR       = "error"

    def __init__(self, current_version: str, parent=None,
                  auto_check: bool = True):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setFixedSize(520, 380)
        self._current_version = current_version
        self._updater = get_updater(current_version=current_version)
        self._info: UpdateInfo | None = None
        self._archive_path = None
        self._build()
        self._check_done.connect(self._on_check_done)
        self._progress_sig.connect(self._on_progress)
        self._download_done.connect(self._on_download_done)
        if auto_check:
            self._set_state(self.STATE_CHECKING)
            self._launch_check()

    # ── Construction ──────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("update_dialog")
        container.setStyleSheet(
            "QFrame#update_dialog {"
            "  background-color: #0e0e11;"
            "  border: 1px solid #27272a;"
            "  border-radius: 8px;"
            "}"
        )
        outer.addWidget(container)

        inner = QVBoxLayout(container)
        inner.setContentsMargins(40, 32, 40, 24)
        inner.setSpacing(0)

        # Title
        title = QLabel(tr("Software Update"))
        title.setStyleSheet(
            "color: #e4e4e7; font-size: 22px; font-weight: 700;"
            "letter-spacing: 1px;"
        )
        inner.addWidget(title)
        inner.addSpacing(2)

        self._caption = QLabel(tr("CHECKING FOR UPDATES…"))
        self._caption.setStyleSheet(
            "color: #52525b; font-size: 9px; letter-spacing: 2px;"
        )
        inner.addWidget(self._caption)
        inner.addSpacing(20)

        # Versions
        ver_row = QHBoxLayout()
        for label, value, color in [
            (tr("CURRENT"), self._current_version, "#a1a1aa"),
            (tr("LATEST"),  "—",                   "#e4e4e7"),
        ]:
            block = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #52525b; font-size: 9px; letter-spacing: 1.5px;")
            block.addWidget(lbl)
            v = QLabel(value)
            v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: 700;")
            block.addWidget(v)
            if label == tr("LATEST"):
                self._latest_lbl = v
            ver_row.addLayout(block)
            ver_row.addSpacing(40)
        ver_row.addStretch()
        inner.addLayout(ver_row)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1c1c20;")
        sep.setContentsMargins(0, 12, 0, 12)
        inner.addWidget(sep)

        # Notes
        self._notes_lbl = QLabel(tr("RELEASE NOTES"))
        self._notes_lbl.setStyleSheet(
            "color: #52525b; font-size: 9px; letter-spacing: 1.5px;"
        )
        inner.addWidget(self._notes_lbl)
        inner.addSpacing(4)

        self._notes_text = QPlainTextEdit()
        self._notes_text.setReadOnly(True)
        self._notes_text.setStyleSheet(
            "QPlainTextEdit { background-color: transparent; border: none;"
            "  color: #a1a1aa; font-size: 10px; padding: 0; }"
        )
        self._notes_text.setMaximumHeight(120)
        self._notes_text.setPlainText("…")
        inner.addWidget(self._notes_text)
        inner.addStretch()

        # Progress (cache par defaut)
        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.setStyleSheet(
            "QProgressBar { background: #1c1c20; border: none; border-radius: 2px; }"
            "QProgressBar::chunk { background: #84cc9e; border-radius: 2px; }"
        )
        self._progress.hide()
        inner.addWidget(self._progress)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #a1a1aa; font-size: 10px;")
        inner.addWidget(self._status_lbl)
        inner.addSpacing(12)

        # Actions
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_skip = QPushButton(tr("Skip"))
        self._btn_skip.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_skip)
        self._btn_main = QPushButton(tr("Check"))
        self._btn_main.setProperty("variant", "primary")
        self._btn_main.setMinimumWidth(140)
        self._btn_main.clicked.connect(self._on_main_action)
        btn_row.addWidget(self._btn_main)
        inner.addLayout(btn_row)

    # ── State machine ─────────────────────────

    def _set_state(self, state: str):
        self._state = state
        if state == self.STATE_CHECKING:
            self._caption.setText(tr("CHECKING FOR UPDATES…"))
            self._btn_main.setEnabled(False)
            self._btn_main.setText(tr("Please wait..."))
            self._notes_text.setPlainText(tr("Contacting update server..."))
        elif state == self.STATE_NO_UPDATE:
            self._caption.setText(tr("YOU ARE UP TO DATE"))
            self._btn_main.setEnabled(True)
            self._btn_main.setText(tr("OK"))
            self._btn_main.clicked.disconnect()
            self._btn_main.clicked.connect(self.accept)
            self._notes_text.setPlainText(
                tr("RiskPulse {0} is the latest version.").format(self._current_version)
            )
        elif state == self.STATE_AVAILABLE:
            self._caption.setText(tr("UPDATE AVAILABLE"))
            self._btn_main.setEnabled(True)
            self._btn_main.setText(tr("Download {0} MB").format(
                round((self._info.size or 0) / 1e6) if self._info else 0
            ))
        elif state == self.STATE_DOWNLOADING:
            self._caption.setText(tr("DOWNLOADING…"))
            self._btn_main.setEnabled(False)
            self._btn_main.setText(tr("Downloading..."))
            self._progress.show()
        elif state == self.STATE_READY:
            self._caption.setText(tr("READY TO INSTALL"))
            self._btn_main.setEnabled(True)
            self._btn_main.setText(tr("Install & restart"))
            self._progress.hide()
        elif state == self.STATE_ERROR:
            self._caption.setText(tr("ERROR"))
            self._btn_main.setEnabled(True)
            self._btn_main.setText(tr("Retry"))
            self._progress.hide()

    # ── Actions ───────────────────────────────

    def _on_main_action(self):
        if self._state in (self.STATE_AVAILABLE, self.STATE_ERROR):
            if self._state == self.STATE_ERROR:
                self._set_state(self.STATE_CHECKING)
                self._launch_check()
            else:
                self._launch_download()
        elif self._state == self.STATE_READY:
            self._launch_apply()
        elif self._state == self.STATE_NO_UPDATE:
            self.accept()

    def _launch_check(self):
        def _job():
            info = self._updater.check()
            self._check_done.emit(info)
        threading.Thread(target=_job, daemon=True).start()

    def _on_check_done(self, info: UpdateInfo):
        self._info = info
        if info.error:
            self._status_lbl.setText(info.error)
            self._set_state(self.STATE_ERROR)
            return
        self._latest_lbl.setText(info.latest or "—")
        if not info.available:
            self._set_state(self.STATE_NO_UPDATE)
            return
        self._notes_text.setPlainText(info.notes or tr("(No release notes provided.)"))
        self._set_state(self.STATE_AVAILABLE)

    def _launch_download(self):
        self._set_state(self.STATE_DOWNLOADING)
        self._progress.setRange(0, 100)
        info = self._info

        def _job():
            try:
                path = self._updater.download(
                    info,
                    on_progress=lambda d, t: self._progress_sig.emit(d, t),
                )
                self._download_done.emit(path)
            except Exception as e:
                self._download_done.emit(None)

        threading.Thread(target=_job, daemon=True).start()

    def _on_progress(self, downloaded: int, total: int):
        if total:
            pct = int(downloaded * 100 / total)
            self._progress.setValue(pct)
            self._status_lbl.setText(
                f"{downloaded / 1e6:.1f} / {total / 1e6:.1f} MB ({pct}%)"
            )

    def _on_download_done(self, path):
        if not path:
            self._status_lbl.setText(tr("Download failed. Check your connection."))
            self._set_state(self.STATE_ERROR)
            return
        self._archive_path = path
        self._status_lbl.setText(tr("Download verified (SHA-256 OK)."))
        self._set_state(self.STATE_READY)

    def _launch_apply(self):
        if not self._archive_path:
            return
        ans = QMessageBox.question(
            self,
            tr("Install update"),
            tr("RiskPulse will close, install the update, and restart. Continue?"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        ok = self._updater.apply(self._archive_path, restart=True)
        if ok:
            self.accept()
            # L'app va etre fermee par le batch script
            import sys
            sys.exit(0)
        else:
            self._status_lbl.setText(tr("Apply failed. See logs."))
            self._set_state(self.STATE_ERROR)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(e)
