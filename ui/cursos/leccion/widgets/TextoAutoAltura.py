
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTextBrowser, QSizePolicy


PROJECT_ROOT = Path(__file__).resolve().parents[4]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from services.fuente_multiidioma import (
    crear_fuente_multidioma,
    css_fuente_multidioma,
)

from ui.theme import Colores as C


class TextoAutoAltura(QTextBrowser):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameStyle(0)
        self.setOpenExternalLinks(True)

        # Configuramos la fuente multidioma.
        fuente = crear_fuente_multidioma(15)

        self.setFont(fuente)
        self.document().setDefaultFont(fuente)

        # Estilo general del widget.
        self.setStyleSheet(
            f"QTextBrowser {{ background: transparent; border: none; "
            f"color: {C.TEXTO}; font-size: 15px; }}"
        )

        familia_css = css_fuente_multidioma()

        # Estilos aplicados al HTML generado por la IA.
        self.document().setDefaultStyleSheet(f"""
            * {{
                font-family: {familia_css} !important;
            }}

            body {{
                color: {C.TEXTO};
            }}

            p {{
                margin-top: 0px;
                margin-bottom: 10px;
                line-height: 150%;
            }}

            li {{
                margin-bottom: 4px;
                line-height: 150%;
            }}

            h1, h2, h3 {{
                color: {C.TEXTO};
                margin-top: 12px;
                margin-bottom: 6px;
            }}

            table {{
                border-collapse: collapse;
            }}

            th, td {{
                padding: 6px;
            }}

            a {{
                color: {C.ACENTO};
            }}

            code, pre {{
                font-family: Consolas, 'Cascadia Mono', monospace !important;
                background-color: #EFEDE8;
                color: #3B4248;
            }}
        """)

        # Desactivamos las barras de desplazamiento.
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.setMinimumHeight(0)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        # Reducimos el margen interno del documento.
        self.document().setDocumentMargin(0)


    def setHtml(self, html):
        super().setHtml(html)
        self.ajustar_altura()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.ajustar_altura()


    def ajustar_altura(self):

        ancho = self.viewport().width()

        if ancho <= 0:
            return

        documento = self.document()

        documento.setTextWidth(ancho)

        altura = documento.documentLayout().documentSize().height()

        # Un pequeño margen evita recortar la última línea.
        self.setFixedHeight(max(1, int(altura + 4)))
