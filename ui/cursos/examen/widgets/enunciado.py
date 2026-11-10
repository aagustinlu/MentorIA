
import re
from ui.theme import fs
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

# Abre/cierra un bloque de código (``` o ```python) dentro de un enunciado
_VALLA_CODIGO = re.compile(r"```[A-Za-z0-9_+#-]*[ \t]*\n?")


def crear_codigo(codigo: str) -> QPlainTextEdit:
    widget = QPlainTextEdit()
    widget.setReadOnly(True)

    fuente = QFont("Consolas")
    fuente.setStyleHint(QFont.StyleHint.Monospace)
    fuente.setPixelSize(fs(14))
    widget.setFont(fuente)

    widget.setPlainText(codigo)
    widget.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
    # Colores en la hoja global (theme.py): siguen al tema solos
    widget.setObjectName("codigoBloque")

    lineas = max(1, widget.document().blockCount())
    widget.setFixedHeight(min(lineas * widget.fontMetrics().lineSpacing() + 36, 220))
    return widget


def crear_enunciado(texto: str, tam: int = 17) -> QWidget:
    """Enunciado con texto y bloques de código intercalados."""
    contenedor = QWidget()
    layout = QVBoxLayout(contenedor)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    # split() alterna: texto, código, texto, código...
    for i, segmento in enumerate(_VALLA_CODIGO.split(texto)):
        if i % 2 == 1:
            codigo = segmento.strip("\n")
            if codigo.strip():
                layout.addWidget(crear_codigo(codigo))
        else:
            limpio = segmento.replace("`", "").strip()
            if limpio:
                etiqueta = QLabel(limpio)
                etiqueta.setWordWrap(True)
                etiqueta.setTextFormat(Qt.TextFormat.PlainText)
                etiqueta.setStyleSheet(f"font-size: {fs(tam)}px; font-weight: 600;")
                layout.addWidget(etiqueta)

    return contenedor