
import sys
from pathlib import Path
from html import escape

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QSizePolicy
from PyQt6.QtCore import QUrl


PROJECT_ROOT = Path(__file__).resolve().parents[4]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from services.fuente_multiidioma import (
    css_fuente_multidioma,
    FUENTE_JAPONESA_PATH,
)


class WidgetFormula(QWebEngineView):

    def __init__(self, bloque, parent=None):

        super().__init__(parent)

        self.setMinimumSize(0, 0)
        self.setMaximumHeight(300)
        self.setFixedHeight(60)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        # Preparamos el contenido matemático.
        formula = self.escapar_contenido(bloque.contenido)

        # Construimos el documento HTML.
        html = self.definir_html(formula)

        # Escuchamos los cambios de título para ajustar la altura.
        self.titleChanged.connect(self.ajustar_altura)

        # Cargamos el HTML.
        base_url = QUrl.fromLocalFile(str(PROJECT_ROOT) + "/")
        self.setHtml(html, base_url)


    def escapar_contenido(self, contenido):

        # Escapamos el contenido para insertarlo de forma segura
        # dentro del HTML.
        return escape(contenido)


    def definir_html(self, formula):

        # Configuramos la fuente japonesa y las fuentes alternativas.
        url_fuente = QUrl.fromLocalFile(
            str(FUENTE_JAPONESA_PATH)
        ).toString()

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

            <div id="formula">\\[{formula}\\]</div>

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

        return html


    def ajustar_altura(self, titulo):

        if titulo.startswith("altura:"):

            try:
                altura = int(titulo.split(":")[1])

                self.setFixedHeight(
                    min(max(altura + 4, 40), 300)
                )

            except ValueError:
                pass
