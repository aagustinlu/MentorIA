import sys
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QLabel,
    QSizePolicy,
)
from PyQt6.QtCore import Qt

from urllib.parse import unquote


PROJECT_ROOT = Path(__file__).resolve().parents[4]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.fuente_multiidioma import (
    crear_fuente_multidioma,
    reparar_mojibake_utf8,
)

from html import unescape


class WidgetTitulo(QLabel):
    
    def __init__(self, bloque):

        super().__init__()

        contenido = self.decodificar_caracteres_url(bloque.contenido)
        
        
        self.setFont(crear_fuente_multidioma(26))
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setText(contenido)

        self.setWordWrap(True)
        self.setIndent(0)

        self.setStyleSheet("""
            QLabel {
                font-size: 26px;
                font-weight: 600;
                margin-top: 8px;
                margin-bottom: 4px;
            }
        """)

        self.setMinimumSize(0, 0)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        
    
    def decodificar_caracteres_url(self, contenido_original):
        
        # Decodificamos caracteres URL.
        contenido_original = unquote(contenido_original)

        # Decodificamos entidades HTML (&aacute;, &#225;, etc.).
        contenido_decodificado = unescape(contenido_original)

        # Reparamos posibles errores de codificación UTF-8.
        contenido = reparar_mojibake_utf8(contenido_decodificado)

        
        return contenido
