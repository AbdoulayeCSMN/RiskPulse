"""Card : conteneur avec coins arrondis et bordure subtile (via QSS)."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt


class Card(QFrame):
    """
    Carte moderne. Le style est applique via objectName='card' (voir theme.py).
    Usage :
        card = Card(title="Titre")
        card.layout().addWidget(...)
    """

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(8)

        self._title_label: QLabel | None = None
        if title:
            self.set_title(title)

    def set_title(self, title: str):
        if self._title_label is None:
            self._title_label = QLabel(title)
            self._title_label.setProperty("class", "h3")
            self._layout.insertWidget(0, self._title_label)
        else:
            self._title_label.setText(title)


class MetricCard(QFrame):
    """
    Carte metrique minimaliste : label en haut (caption), valeur en grand en bas.
    Pas de bordure flashy. Visuel premium type Linear/Vercel.
    """

    def __init__(self, label: str = "", value: str = "—", parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Label en HAUT (uppercase, espace, sourd)
        self._label_lbl = QLabel(label.upper() if label else "")
        self._label_lbl.setProperty("class", "metric-label")
        layout.addWidget(self._label_lbl)

        # Valeur en BAS (grande, refined)
        self._value_lbl = QLabel(value)
        self._value_lbl.setProperty("class", "metric")
        layout.addWidget(self._value_lbl)

        layout.addStretch()

    def set_value(self, value: str):
        self._value_lbl.setText(str(value))

    def set_label(self, label: str):
        self._label_lbl.setText(label.upper() if label else "")
