
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

from ui.theme import Colores as C, al_cambiar_tema, fs


class TextoAutoAltura(QTextBrowser):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Último HTML mostrado: hay que volver a cargarlo cuando cambia el tema
        # (el documento "hornea" los colores de la hoja de estilos al cargarse).
        self._html_actual: str | None = None

        self.setFrameStyle(0)
        self.setOpenExternalLinks(True)

        # Configuramos la fuente multidioma.
        fuente = crear_fuente_multidioma(pixeles=fs(15))

        self.setFont(fuente)
        self.document().setDefaultFont(fuente)

        # Colores del tema (estilo del widget + hoja del documento)
        self._aplicar_tema()
        al_cambiar_tema(self._aplicar_tema)

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


    def _aplicar_tema(self, _nombre: str = ""):

        # Estilo general del widget.
        self.setStyleSheet(
            f"QTextBrowser {{ background: transparent; border: none; "
            f"color: {C.TEXTO}; font-size: {fs(15)}px; }}"
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
                color: {C.ACENTO_TEXTO};
            }}

            code, pre {{
                font-family: Consolas, 'Cascadia Mono', monospace !important;
                background-color: {C.CODIGO_INLINE_FONDO};
                color: {C.CODIGO_INLINE_TEXTO};
            }}
        """)

        # Si ya hay contenido, se recarga para que adopte los colores nuevos.
        if self._html_actual is not None:
            super().setHtml(self._html_actual)
            self.ajustar_altura()


    def setHtml(self, html):
        self._html_actual = html
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
