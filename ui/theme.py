"""Tema visual de la aplicación.

Paleta suave y de bajo contraste (papel cálido + azul grisáceo), pensada para
estudiar sin cansar la vista. Todos los colores viven aquí para poder
ajustarlos desde un único lugar.

Uso:
    from ui.theme import aplicar_tema
    aplicar_tema(app)          # una sola vez, justo después de crear QApplication
"""

from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget


class Colores:
    FONDO = "#F6F5F2"            # fondo general (papel cálido)
    SUPERFICIE = "#FFFFFF"       # tarjetas, campos
    BORDE = "#E3E0D9"
    BORDE_SUAVE = "#ECEAE4"

    TEXTO = "#2E3338"
    TEXTO_SUAVE = "#6F767C"
    TEXTO_TENUE = "#A3A8AC"

    ACENTO = "#5B7C99"           # azul grisáceo
    ACENTO_HOVER = "#4D6D8A"
    ACENTO_PRESIONADO = "#41607B"
    ACENTO_SUAVE = "#E8EEF3"
    ACENTO_BORDE = "#CBD7E1"

    # Estados de lección
    COMPLETADO = "#8DB19B"       # salvia
    ACTUAL = "#5B7C99"
    BLOQUEADO = "#C8CBCD"

    PENDIENTE = "#C9A66B"        # ámbar apagado (cursos pendientes)
    ERROR = "#B0605A"            # rojo terroso, nada estridente

    CODIGO_FONDO = "#2F3640"     # pizarra oscura suave
    CODIGO_TEXTO = "#E6E9ED"


C = Colores

FUENTE = '"Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif'


ESTILO_GLOBAL = f"""
* {{
    font-family: {FUENTE};
}}

QLabel {{
    color: {C.TEXTO};
    background: transparent;
}}

QLabel[rol="titulo"] {{
    font-size: 22px;
    font-weight: 600;
    color: {C.TEXTO};
}}

QLabel[rol="subtitulo"] {{
    font-size: 12px;
    color: {C.TEXTO_SUAVE};
}}

QLabel[rol="seccion"] {{
    font-size: 11px;
    font-weight: 600;
    color: {C.TEXTO_TENUE};
    letter-spacing: 1px;
}}

QLabel[rol="enlace"] {{
    color: {C.ACENTO};
    font-size: 12px;
}}

/* ── Tarjetas ─────────────────────────────────────────── */
#tarjeta {{
    background-color: {C.SUPERFICIE};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 14px;
}}

/* ── Botones ──────────────────────────────────────────── */
QPushButton {{
    background-color: {C.SUPERFICIE};
    color: {C.TEXTO};
    border: 1px solid {C.BORDE};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {C.ACENTO_SUAVE};
    border-color: {C.ACENTO_BORDE};
}}
QPushButton:pressed {{
    background-color: {C.ACENTO_BORDE};
}}
QPushButton:disabled {{
    background-color: #F1F0ED;
    color: {C.TEXTO_TENUE};
    border-color: {C.BORDE_SUAVE};
}}

QPushButton[primario="true"] {{
    background-color: {C.ACENTO};
    color: #FFFFFF;
    border: none;
}}
QPushButton[primario="true"]:hover {{
    background-color: {C.ACENTO_HOVER};
}}
QPushButton[primario="true"]:pressed {{
    background-color: {C.ACENTO_PRESIONADO};
}}
QPushButton[primario="true"]:disabled {{
    background-color: #BCC9D4;
    color: #F4F6F8;
}}

/* ── Campos de texto ──────────────────────────────────── */
QLineEdit {{
    background-color: {C.SUPERFICIE};
    color: {C.TEXTO};
    border: 1px solid {C.BORDE};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {C.ACENTO_BORDE};
    selection-color: {C.TEXTO};
}}
QLineEdit:focus {{
    border: 1px solid {C.ACENTO};
}}

/* ── Lista de cursos ──────────────────────────────────── */
QListWidget {{
    background-color: {C.SUPERFICIE};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 14px;
    padding: 8px;
    outline: 0;
    font-size: 14px;
}}
QListWidget::item {{
    color: {C.TEXTO};
    padding: 12px 14px;
    border-radius: 8px;
}}
QListWidget::item:hover {{
    background-color: #F3F4F5;
}}
QListWidget::item:selected {{
    background-color: {C.ACENTO_SUAVE};
    color: {C.TEXTO};
}}

/* ── Barras de desplazamiento ─────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #D5D2CB;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #BEBBB3;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #D5D2CB;
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #BEBBB3;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0px;
    height: 0px;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* ── Varios ───────────────────────────────────────────── */
QToolTip {{
    background-color: {C.TEXTO};
    color: #FFFFFF;
    border: none;
    padding: 6px 8px;
}}

QGraphicsView {{
    background-color: {C.FONDO};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 14px;
}}

QProgressDialog, QMessageBox {{
    background-color: {C.FONDO};
}}
"""


def _paleta() -> QPalette:
    paleta = QPalette()
    paleta.setColor(QPalette.ColorRole.Window, QColor(C.FONDO))
    paleta.setColor(QPalette.ColorRole.WindowText, QColor(C.TEXTO))
    paleta.setColor(QPalette.ColorRole.Base, QColor(C.SUPERFICIE))
    paleta.setColor(QPalette.ColorRole.AlternateBase, QColor(C.FONDO))
    paleta.setColor(QPalette.ColorRole.Text, QColor(C.TEXTO))
    paleta.setColor(QPalette.ColorRole.Button, QColor(C.SUPERFICIE))
    paleta.setColor(QPalette.ColorRole.ButtonText, QColor(C.TEXTO))
    paleta.setColor(QPalette.ColorRole.Highlight, QColor(C.ACENTO_BORDE))
    paleta.setColor(QPalette.ColorRole.HighlightedText, QColor(C.TEXTO))
    paleta.setColor(QPalette.ColorRole.PlaceholderText, QColor(C.TEXTO_TENUE))
    return paleta


def aplicar_tema(app: QApplication) -> None:
    """Aplica estilo base, paleta, fuente y hoja de estilos global."""
    app.setStyle("Fusion")
    app.setPalette(_paleta())
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(ESTILO_GLOBAL)


# ── Helpers ───────────────────────────────────────────────────────────────────

def rol(widget: QWidget, nombre: str) -> QWidget:
    """Asigna un 'rol' tipográfico (titulo, subtitulo, seccion, enlace)."""
    widget.setProperty("rol", nombre)
    return widget


def primario(boton: QPushButton) -> QPushButton:
    """Marca un botón como acción principal (relleno de color)."""
    boton.setProperty("primario", True)
    return boton


def tarjeta(widget: QWidget) -> QWidget:
    """Convierte un QWidget en una tarjeta con fondo blanco y bordes redondeados."""
    from PyQt6.QtCore import Qt

    widget.setObjectName("tarjeta")
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    return widget
