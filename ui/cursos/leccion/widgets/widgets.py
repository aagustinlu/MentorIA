import sys
import re
from pathlib import Path

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QLabel,
    QSizePolicy,
    QTextBrowser
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from urllib.parse import unquote


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.fuente_multiidioma import (
    crear_fuente_multidioma,
    css_fuente_multidioma,
    FUENTE_JAPONESA_PATH,
    reparar_mojibake_utf8,
)

from ui.theme import Colores as C
from html import unescape

class TextoAutoAltura(QTextBrowser):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameStyle(0)
        self.setOpenExternalLinks(True)

        # Fuente instalada desde el propio proyecto.
        self.setFont(crear_fuente_multidioma(15))
        self.document().setDefaultFont(crear_fuente_multidioma(15))

        # Estilo de lectura. El selector universal también alcanza tablas,
        # encabezados y celdas que la IA incluya dentro del HTML.
        self.setStyleSheet(
            f"QTextBrowser {{ background: transparent; border: none; "
            f"color: {C.TEXTO}; font-size: 15px; }}"
        )
        
        familia_css = css_fuente_multidioma()
        
        self.document().setDefaultStyleSheet(f"""
            * {{ font-family: {familia_css} !important; }}
            body {{ color: {C.TEXTO}; }}
            p {{ margin-top: 0px; margin-bottom: 10px; line-height: 150%; }}
            li {{ margin-bottom: 4px; line-height: 150%; }}
            h1, h2, h3 {{ color: {C.TEXTO}; margin-top: 12px; margin-bottom: 6px; }}
            table {{ border-collapse: collapse; }}
            th, td {{ padding: 6px; }}
            a {{ color: {C.ACENTO}; }}
            code {{ font-family: Consolas, 'Cascadia Mono', monospace;
                    background-color: #EFEDE8; color: #3B4248; }}
        """)

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

        # Reduce el espacio interno del documento.
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

        # Un pequeño margen para evitar recortar la última línea.
        self.setFixedHeight(max(1, int(altura + 4)))
        

def crear_texto(bloque):
    
    # Aplicamos la fuente del proyecto también al HTML generado por la IA.
    fuente_multiidioma = f"font-family: {css_fuente_multidioma()};"

    # Primero decodificamos escapes URL (%E3%81%82) y luego reparamos
    # secuencias que hayan llegado como UTF-8 leído por error como Latin-1.
    contenido_original = unquote(bloque.contenido)
    contenido = reparar_mojibake_utf8(contenido_original)

    if contenido != contenido_original:
        print("[HTML] Se repararon caracteres UTF-8 mal decodificados.")

    widget = TextoAutoAltura()
    
    html_mostrado = f"""
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

    widget.setHtml(html_mostrado)


    return widget

# ------------------------------------------------------
# Título
# ------------------------------------------------------

# ------------------------------------------------------
# Título
# ------------------------------------------------------

def crear_titulo(bloque):

    # Decodificamos caracteres URL.
    contenido_original = unquote(bloque.contenido)

    # Decodificamos entidades HTML (&aacute;, &#225;, etc.).
    contenido_decodificado = unescape(contenido_original)

    # Reparamos posibles errores de codificación UTF-8.
    contenido = reparar_mojibake_utf8(contenido_decodificado)

    if contenido != contenido_original:
        print("[Título] Se repararon caracteres especiales.")

    widget = QLabel()

    widget.setFont(crear_fuente_multidioma(26))
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setText(contenido)

    widget.setWordWrap(True)
    widget.setIndent(0)

    widget.setStyleSheet("""
        QLabel {
            font-size: 26px;
            font-weight: 600;
            margin-top: 8px;
            margin-bottom: 4px;
        }
    """)

    widget.setMinimumSize(0, 0)

    widget.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Preferred,
    )

    return widget

# ------------------------------------------------------
# Código
# ------------------------------------------------------

def crear_codigo(bloque):
    widget = QPlainTextEdit()

    widget.setReadOnly(True)

    fuente_codigo = crear_fuente_multidioma(14)
    fuente_codigo.setStyleHint(QFont.StyleHint.Monospace)
    fuente_codigo.setPixelSize(14)
    widget.setFont(fuente_codigo)

    widget.setPlainText(bloque.contenido)

    widget.setLineWrapMode(
        QPlainTextEdit.LineWrapMode.WidgetWidth
    )

    widget.setVerticalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )

    widget.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )

    widget.setStyleSheet(f"""
        QPlainTextEdit {{
            background: {C.CODIGO_FONDO};
            color: {C.CODIGO_TEXTO};
            border: none;
            border-radius: 10px;
            padding: 10px;
        }}
    """)

    widget.setMinimumSize(0, 0)
    widget.setMaximumHeight(250)

    widget.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Preferred,
    )

    # Altura aproximada según la cantidad de líneas.
    lineas = max(1, widget.document().blockCount())
    altura_linea = widget.fontMetrics().lineSpacing()
    altura = lineas * altura_linea + 36

    widget.setFixedHeight(min(altura, 250))

    return widget

# ------------------------------------------------------
# Fórmulas matemáticas
# ------------------------------------------------------



def crear_formula(bloque):
    widget = QWebEngineView()

    widget.setMinimumSize(0, 0)
    widget.setMaximumHeight(300)
    widget.setFixedHeight(60)


    widget.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Fixed
    )

    # Escapamos el contenido para insertarlo de forma segura
    # dentro del HTML.
    from html import escape
    formula = escape(bloque.contenido)

    url_fuente = QUrl.fromLocalFile(str(FUENTE_JAPONESA_PATH)).toString()
    familia_css = css_fuente_multidioma()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">

        <script>
        MathJax = {{
            tex: {{
                inlineMath: [['\\\\(', '\\\\)']],
                displayMath: [['\\\\[', '\\\\]']]
            }},
            startup: {{
                typeset: false
            }}
        }};
        </script>

        <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>

        
    <style>
        @font-face {{
            font-family: "NotoSansJPLocal";
            src: url("{url_fuente}") format("truetype");
            font-style: normal;
            font-weight: 100 900;
        }}

        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            background: transparent;
        }}

        html {{
            overflow-y: hidden;
        }}

        body {{
            font-family: "NotoSansJPLocal", {familia_css};
            box-sizing: border-box;
            text-align: center;
            font-size: 22px;
            padding: 4px 0;
            overflow-x: auto;
            overflow-y: hidden;
        }}

        #formula {{
            width: 100%;
            box-sizing: border-box;
        }}

        mjx-container[display="true"] {{
            max-width: none !important;
            overflow: visible !important;
        }}

        ::-webkit-scrollbar {{
            height: 8px;
        }}

        ::-webkit-scrollbar-thumb {{
            background: #999;
            border-radius: 4px;
        }}

        ::-webkit-scrollbar-track {{
            background: transparent;
        }}
    </style>
    </head>

    <body>
        <div id="formula">\\[FORMULA_AQUI\\]</div>

        <script>
        window.addEventListener("load", async () => {{
            await MathJax.startup.promise;
            await MathJax.typesetPromise();

            requestAnimationFrame(() => {{
                const altura = document.documentElement.scrollHeight;
                document.title = "altura:" + altura;
            }});
        }});
        </script>
    </body>
    </html>
    """

    html = html.replace("FORMULA_AQUI", formula)

    def ajustar_altura(titulo):
        if titulo.startswith("altura:"):
            try:
                altura = int(titulo.split(":")[1])
                widget.setFixedHeight(
                    min(max(altura + 4, 40), 300)
                )
            except ValueError:
                pass

    widget.titleChanged.connect(ajustar_altura)
    widget.setHtml(html, QUrl.fromLocalFile(str(PROJECT_ROOT) + "/"))

    return widget
