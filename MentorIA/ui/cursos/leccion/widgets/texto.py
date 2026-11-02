
import sys
from pathlib import Path
from urllib.parse import unquote

from PyQt6.QtCore import Qt

from .TextoAutoAltura import TextoAutoAltura

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.fuente_multiidioma import (
    css_fuente_multidioma,
    reparar_mojibake_utf8
)




class WidgetTexto(TextoAutoAltura):

    def __init__(self, bloque):

        super().__init__()

        fuente_multiidioma = f"font-family: {css_fuente_multidioma()};"

        contenido = self.decodificar_html(bloque.contenido)

        html_mostrado = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body>
                <div style="{fuente_multiidioma}">
                    {contenido}
                </div>
            </body>
            </html>
        """

        self.setHtml(html_mostrado)

    def decodificar_html(self, contenido_original):

        # Decodificamos caracteres codificados en URL.
        contenido_original = unquote(contenido_original)

        # Reparamos posibles errores de codificación UTF-8.
        contenido = reparar_mojibake_utf8(contenido_original)

        return contenido
