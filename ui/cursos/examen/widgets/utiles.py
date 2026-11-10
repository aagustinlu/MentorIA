from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QScrollArea,
    QWidget,
)


def vaciar(layout) -> None:
    """Elimina todos los widgets de un layout."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout() is not None:
            vaciar(item.layout())


def crear_scroll(contenido: QWidget) -> QScrollArea:
    """Área desplazable transparente (mismo estilo que las páginas de lección)."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    scroll.viewport().setAutoFillBackground(False)
    scroll.setWidget(contenido)
    # Después de setWidget(): Qt lo reactiva ahí y pintaría un rectángulo del
    # color de la ventana sobre la tarjeta.
    contenido.setAutoFillBackground(False)
    return scroll