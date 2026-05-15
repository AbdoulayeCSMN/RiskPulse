"""Base view : composants partages (header avec caption/title/divider)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QFrame, QWidget


def build_header(parent_layout: QVBoxLayout, caption: str, title: str) -> tuple[QLabel, QLabel]:
    """
    Construit un header standard : 'MODULE' caption + grand titre + divider.
    Retourne (caption_lbl, title_lbl) pour permettre la retraduction.
    """
    caption_lbl = QLabel(caption)
    caption_lbl.setProperty("class", "caption")
    parent_layout.addWidget(caption_lbl)

    title_lbl = QLabel(title)
    title_lbl.setProperty("class", "h1")
    parent_layout.addWidget(title_lbl)

    sep = QFrame()
    sep.setObjectName("divider")
    sep.setFixedHeight(1)
    parent_layout.addWidget(sep)
    parent_layout.addSpacing(8)

    return caption_lbl, title_lbl
