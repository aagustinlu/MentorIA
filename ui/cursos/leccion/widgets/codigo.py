
import sys
from pathlib import Path
from html import unescape

from PyQt6.QtWidgets import (
    QSizePolicy,
    QPlainTextEdit
)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


PROJECT_ROOT = Path(__file__).resolve().parents[4]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from ui.theme import fs

from services.fuente_multiidioma import (
    crear_fuente_multidioma,
)


class WidgetCodigo(QPlainTextEdit):

    def __init__(self, bloque, parent=None):
        super().__init__(parent)

        self.bloque = bloque

        # Decodificamos las entidades HTML.
        contenido = self.decodificar_entidades(bloque.contenido)

        self.setReadOnly(True)

        # Configuramos la fuente.
        self.setFont(self.crear_fuente())

        # Mostramos el código como texto plano.
        self.setPlainText(contenido)

        # Configuración de desplazamiento.
        self.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        # Apariencia: colores en la hoja global (theme.py), siguen al tema solos.
        self.setObjectName("codigoBloque")

        self.setMinimumSize(0, 0)
        self.setMaximumHeight(250)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        # Altura según la cantidad de líneas.
        lineas = max(1, self.document().blockCount())
        altura_linea = self.fontMetrics().lineSpacing()
        altura = lineas * altura_linea + 36

        self.setFixedHeight(min(altura, 250))


    def decodificar_entidades(self, contenido_original):

        # Decodificamos entidades HTML (&lt;, &gt;, &quot;, etc.).
        contenido_decodificado = unescape(contenido_original)

        return contenido_decodificado


    def crear_fuente(self):

        fuente = crear_fuente_multidioma(pixeles=fs(14))

        fuente.setStyleHint(QFont.StyleHint.Monospace)
        fuente.setPixelSize(fs(14))

        return fuente
