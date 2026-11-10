from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
)

from ui.theme import fs, repulir, rol




class OpcionRespuesta(QFrame):
    """Opción clicable con texto que se ajusta al ancho (un QPushButton no puede)."""

    clicked = pyqtSignal()

    def __init__(self, letra: str, texto: str):
        super().__init__()
        self.setObjectName("opcion")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        self.lbl_letra = QLabel(letra)
        self.lbl_letra.setFixedWidth(26)
        rol(self.lbl_letra, "letra")
        # El clic debe llegar al marco, no quedarse en las etiquetas
        self.lbl_letra.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.lbl_texto = QLabel(texto)
        self.lbl_texto.setWordWrap(True)
        self.lbl_texto.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_texto.setStyleSheet(f"font-size: {fs(14)}px;")
        self.lbl_texto.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout.addWidget(self.lbl_letra, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.lbl_texto, 1)

        self.set_seleccionada(False)

    def set_seleccionada(self, seleccionada: bool) -> None:
        # El aspecto de cada estado está en la hoja global (theme.py)
        self.setProperty("seleccionada", seleccionada)
        repulir(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
