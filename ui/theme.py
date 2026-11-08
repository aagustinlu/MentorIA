"""Tema visual de la aplicación (Modo Día / Modo Oscuro).

Todos los colores viven en este archivo, en dos paletas:

    "dia"     papel envejecido / marfil con acentos terracota y salvia en tonos
              pastel. No hay blancos puros: el valor más claro es un crema suave.
    "oscuro"  carbón cálido de bajo contraste (sin negro ni blanco puros).

Cómo funciona el cambio en caliente
-----------------------------------
`Colores` (alias `C`) es una clase cuyos atributos se reemplazan al cambiar de
tema, así que `C.FONDO` siempre devuelve el color del tema activo. Para que
la interfaz se actualice sola:

  1. La mayor parte del estilo vive en la hoja de estilos global (selectores por
     `objectName` o por propiedad: `rol`, `primario`, `seleccionada`...). Al
     cambiar de tema se regenera y se aplica a toda la aplicación.
  2. Los widgets que pintan con colores "a mano" (mapa de nodos, HTML de las
     lecciones, fórmulas...) se suscriben con `al_cambiar_tema(self.metodo)`.

Uso:
    from ui.theme import aplicar_tema
    aplicar_tema(app, "oscuro")         # al arrancar (tema guardado)

    from ui.theme import gestor_tema
    gestor_tema().aplicar("dia")        # en caliente, p. ej. desde Configuración
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget


TEMA_DIA = "dia"
TEMA_OSCURO = "oscuro"
TEMA_POR_DEFECTO = TEMA_DIA


# ── Paletas ───────────────────────────────────────────────────────────────────


PALETAS: dict[str, dict[str, str | int]] = {
    
    TEMA_DIA: {
        # Superficies
        "FONDO": "#EEE8DB",
        "SUPERFICIE": "#FAF7EF",
        "CAMPO": "#F3EEE4",
        "HOVER": "#E8E1D4",
        "BORDE": "#D5CCBC",
        "BORDE_SUAVE": "#E3DCCE",
        "DESACTIVADO_FONDO": "#E7E0D4",

        # Texto
        "TEXTO": "#303630",
        "TEXTO_SUAVE": "#686C62",
        "TEXTO_TENUE": "#89897F",

        # Acento: verde bosque natural
        "ACENTO": "#47775C",
        "ACENTO_HOVER": "#3F6B50",
        "ACENTO_PRESIONADO": "#365C45",
        "ACENTO_SUAVE": "#E3EDE3",
        "ACENTO_BORDE": "#C5D7C6",
        "ACENTO_TEXTO": "#3D674C",
        "TEXTO_SOBRE_ACENTO": "#FFFFFF",
        "ACENTO_DESACTIVADO": "#C8D6C8",
        "TEXTO_SOBRE_ACENTO_DESACTIVADO": "#758477",

        # Estados
        "COMPLETADO": "#668267",
        "ACTUAL": "#55768A",
        "BLOQUEADO": "#A69D89",
        "PENDIENTE": "#B18B53",
        "OK_TEXTO": "#58785B",
        "ERROR": "#A65E50",
        "ERROR_SUAVE": "#F0E1DA",

        # Código
        "CODIGO_FONDO": "#EAE8DF",
        "CODIGO_TEXTO": "#343D37",
        "CODIGO_INLINE_FONDO": "#E2E3D8",
        "CODIGO_INLINE_TEXTO": "#405044",

        # Varios
        "SCROLL": "#C9C1B2",
        "SCROLL_HOVER": "#A69D8D",
        "TOOLTIP_FONDO": "#303630",
        "TOOLTIP_TEXTO": "#F1EDE3",
        "SOMBRA": "#403B30",
        "SOMBRA_ALFA": 35,
    },


    TEMA_OSCURO: {
        # Superficies
        "FONDO": "#202522",
        "SUPERFICIE": "#292F2B",
        "CAMPO": "#1C221F",
        "HOVER": "#343B35",
        "BORDE": "#414941",
        "BORDE_SUAVE": "#353D37",
        "DESACTIVADO_FONDO": "#252B27",

        # Texto
        "TEXTO": "#E8E5DA",
        "TEXTO_SUAVE": "#B5B7AA",
        "TEXTO_TENUE": "#858C80",

        # Acento: naranja tostado
        "ACENTO": "#35B879",
        "ACENTO_HOVER": "#43C789",
        "ACENTO_PRESIONADO": "#279B65",
        "ACENTO_SUAVE": "#293C32",
        "ACENTO_BORDE": "#426B53",
        "ACENTO_TEXTO": "#65D39B",
        "TEXTO_SOBRE_ACENTO": "#14251B",
        "ACENTO_DESACTIVADO": "#3C5747",
        "TEXTO_SOBRE_ACENTO_DESACTIVADO": "#91A99A",

        # Estados
        "COMPLETADO": "#8EB18A",
        "ACTUAL": "#80A9C5",
        "BLOQUEADO": "#625F55",
        "PENDIENTE": "#D0AA63",
        "OK_TEXTO": "#A3C69C",
        "ERROR": "#D9877C",
        "ERROR_SUAVE": "#402C29",

        # Código
        "CODIGO_FONDO": "#171D1A",
        "CODIGO_TEXTO": "#D6DCCF",
        "CODIGO_INLINE_FONDO": "#303A33",
        "CODIGO_INLINE_TEXTO": "#DCE2D5",

        # Varios
        "SCROLL": "#505950",
        "SCROLL_HOVER": "#687267",
        "TOOLTIP_FONDO": "#343B35",
        "TOOLTIP_TEXTO": "#E8E5DA",
        "SOMBRA": "#000000",
        "SOMBRA_ALFA": 100,
    },
}



class Colores:
    """Colores del tema activo. Se leen siempre como `C.NOMBRE`."""

    FONDO: str
    SUPERFICIE: str
    CAMPO: str
    HOVER: str
    BORDE: str
    BORDE_SUAVE: str
    DESACTIVADO_FONDO: str

    TEXTO: str
    TEXTO_SUAVE: str
    TEXTO_TENUE: str

    ACENTO: str
    ACENTO_HOVER: str
    ACENTO_PRESIONADO: str
    ACENTO_SUAVE: str
    ACENTO_BORDE: str
    ACENTO_TEXTO: str
    TEXTO_SOBRE_ACENTO: str
    ACENTO_DESACTIVADO: str
    TEXTO_SOBRE_ACENTO_DESACTIVADO: str

    COMPLETADO: str
    ACTUAL: str
    BLOQUEADO: str
    PENDIENTE: str
    OK_TEXTO: str
    ERROR: str
    ERROR_SUAVE: str

    CODIGO_FONDO: str
    CODIGO_TEXTO: str
    CODIGO_INLINE_FONDO: str
    CODIGO_INLINE_TEXTO: str

    SCROLL: str
    SCROLL_HOVER: str
    TOOLTIP_FONDO: str
    TOOLTIP_TEXTO: str
    SOMBRA: str
    SOMBRA_ALFA: int

    nombre: str = TEMA_POR_DEFECTO

    @classmethod
    def cargar(cls, nombre: str) -> None:
        """Sustituye los colores de la clase por los de la paleta `nombre`."""
        for clave, valor in PALETAS[nombre].items():
            setattr(cls, clave, valor)
        cls.nombre = nombre


Colores.cargar(TEMA_POR_DEFECTO)
C = Colores

FUENTE = '"Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif'


# ── Hoja de estilos global ────────────────────────────────────────────────────

def _estilo_global() -> str:
    """Construye la hoja de estilos con los colores del tema activo."""
    return f"""
* {{
    font-family: {FUENTE};
}}

QLabel {{
    color: {C.TEXTO};
    background: transparent;
}}

/* ── Roles tipográficos (ver helper `rol`) ────────────── */
QLabel[rol="titulo"] {{
    font-size: 22px;
    font-weight: 600;
    color: {C.TEXTO};
}}

QLabel[rol="subtitulo"] {{
    font-size: 12px;
    color: {C.TEXTO_SUAVE};
}}

QLabel[rol="subtitulo"][error="true"] {{
    color: {C.ERROR};
}}

QLabel[rol="seccion"] {{
    font-size: 11px;
    font-weight: 600;
    color: {C.TEXTO_TENUE};
    letter-spacing: 1px;
}}

QLabel[rol="enlace"] {{
    color: {C.ACENTO_TEXTO};
    font-size: 12px;
}}

QLabel[rol="descripcion"] {{
    color: {C.TEXTO_SUAVE};
    font-size: 13px;
}}

QLabel[rol="suave"] {{
    color: {C.TEXTO_SUAVE};
}}

QLabel[rol="letra"] {{
    color: {C.TEXTO_SUAVE};
    font-weight: 600;
}}

QLabel[rol="acento"] {{
    color: {C.ACENTO_TEXTO};
}}

QLabel[rol="ok"] {{
    color: {C.OK_TEXTO};
    font-weight: 600;
}}

QLabel[rol="error"] {{
    color: {C.ERROR};
    font-weight: 600;
}}

/* ── Tarjetas ─────────────────────────────────────────── */
#tarjeta {{
    background-color: {C.SUPERFICIE};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 14px;
}}

QFrame#tarjetaEntrada {{
    background-color: {C.SUPERFICIE};
    border: 1px solid {C.BORDE};
    border-radius: 16px;
}}

QFrame#revision {{
    background-color: {C.FONDO};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 10px;
}}

/* ── Opciones del examen ──────────────────────────────── */
QFrame#opcion {{
    background-color: {C.SUPERFICIE};
    border: 1px solid {C.BORDE};
    border-radius: 10px;
}}
QFrame#opcion:hover {{
    border-color: {C.ACENTO_BORDE};
    background-color: {C.HOVER};
}}
QFrame#opcion[seleccionada="true"] {{
    background-color: {C.ACENTO_SUAVE};
    border: 2px solid {C.ACENTO};
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
    background-color: {C.DESACTIVADO_FONDO};
    color: {C.TEXTO_TENUE};
    border-color: {C.BORDE_SUAVE};
}}

QPushButton[primario="true"] {{
    background-color: {C.ACENTO};
    color: {C.TEXTO_SOBRE_ACENTO};
    border: none;
}}
QPushButton[primario="true"]:hover {{
    background-color: {C.ACENTO_HOVER};
}}
QPushButton[primario="true"]:pressed {{
    background-color: {C.ACENTO_PRESIONADO};
}}
QPushButton[primario="true"]:disabled {{
    background-color: {C.ACENTO_DESACTIVADO};
    color: {C.TEXTO_SOBRE_ACENTO_DESACTIVADO};
}}

QPushButton#btnEliminarCurso {{
    background: transparent;
    border: none;
    color: {C.TEXTO_TENUE};
    font-size: 12px;
    padding: 6px 10px;
}}
QPushButton#btnEliminarCurso:hover {{
    background-color: {C.ERROR_SUAVE};
    color: {C.ERROR};
    border-radius: 8px;
}}

QPushButton#BotonAdjuntar {{
    padding: 0;
    border-radius: 10px;
    color: {C.TEXTO_SUAVE};
}}
QPushButton#BotonAdjuntar[adjunto="true"] {{
    background-color: {C.ACENTO_SUAVE};
    border: 1px solid {C.ACENTO_BORDE};
    color: {C.ACENTO_TEXTO};
}}

QPushButton#BotonEnviar {{
    padding: 0;
    border-radius: 10px;
    background-color: {C.ACENTO};
    color: {C.TEXTO_SOBRE_ACENTO};
    border: none;
}}
QPushButton#BotonEnviar:hover {{
    background-color: {C.ACENTO_HOVER};
}}
QPushButton#BotonEnviar:pressed {{
    background-color: {C.ACENTO_PRESIONADO};
}}
QPushButton#BotonEnviar:disabled {{
    background-color: {C.ACENTO_DESACTIVADO};
    color: {C.TEXTO_SOBRE_ACENTO_DESACTIVADO};
}}

/* ── Campos de texto ──────────────────────────────────── */
QLineEdit {{
    background-color: {C.CAMPO};
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

QTextEdit#campoPrompt {{
    background-color: {C.CAMPO};
    color: {C.TEXTO};
    border: 1px solid {C.BORDE};
    border-radius: 10px;
    padding: 8px 12px;
    selection-background-color: {C.ACENTO_BORDE};
    selection-color: {C.TEXTO};
}}
QTextEdit#campoPrompt:focus {{
    border: 1px solid {C.ACENTO};
}}

/* Bloques de código (lecciones y examen) */
QPlainTextEdit#codigoBloque {{
    background: {C.CODIGO_FONDO};
    color: {C.CODIGO_TEXTO};
    border: none;
    border-radius: 10px;
    padding: 10px;
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
    background-color: {C.HOVER};
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
    background: {C.SCROLL};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C.SCROLL_HOVER};
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {C.SCROLL};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {C.SCROLL_HOVER};
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
    background-color: {C.TOOLTIP_FONDO};
    color: {C.TOOLTIP_TEXTO};
    border: 1px solid {C.BORDE};
    padding: 6px 8px;
}}

QGraphicsView {{
    background-color: {C.FONDO};
    border: 1px solid {C.BORDE_SUAVE};
    border-radius: 14px;
}}

QMessageBox {{
    background-color: {C.FONDO};
}}

QProgressDialog {{
    background-color: {C.FONDO};
    border: 1px solid {C.BORDE};
    border-radius: 12px;
}}
QProgressDialog QLabel {{
    font-size: 13px;
    font-weight: 500;
}}
QProgressBar {{
    border: 1px solid {C.BORDE_SUAVE};
    background-color: {C.SUPERFICIE};
    border-radius: 6px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {C.ACENTO};
    border-radius: 5px;
}}
"""


def _paleta() -> QPalette:
    paleta = QPalette()
    roles = {
        QPalette.ColorRole.Window: C.FONDO,
        QPalette.ColorRole.WindowText: C.TEXTO,
        QPalette.ColorRole.Base: C.CAMPO,
        QPalette.ColorRole.AlternateBase: C.FONDO,
        QPalette.ColorRole.Text: C.TEXTO,
        QPalette.ColorRole.Button: C.SUPERFICIE,
        QPalette.ColorRole.ButtonText: C.TEXTO,
        QPalette.ColorRole.Highlight: C.ACENTO_BORDE,
        QPalette.ColorRole.HighlightedText: C.TEXTO,
        QPalette.ColorRole.PlaceholderText: C.TEXTO_TENUE,
        QPalette.ColorRole.ToolTipBase: C.TOOLTIP_FONDO,
        QPalette.ColorRole.ToolTipText: C.TOOLTIP_TEXTO,
        QPalette.ColorRole.Link: C.ACENTO_TEXTO,
        QPalette.ColorRole.LinkVisited: C.ACENTO_TEXTO,
    }
    for rol_paleta, color in roles.items():
        paleta.setColor(rol_paleta, QColor(color))

    # Texto atenuado cuando un control está deshabilitado
    for rol_paleta in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        paleta.setColor(QPalette.ColorGroup.Disabled, rol_paleta, QColor(C.TEXTO_TENUE))
    return paleta


# ── Gestor de temas ───────────────────────────────────────────────────────────

class GestorTema(QObject):
    """Aplica un tema a toda la aplicación y avisa a los widgets que pintan a mano."""

    tema_cambiado = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._inicializado = False

    @property
    def nombre(self) -> str:
        return Colores.nombre

    @property
    def es_oscuro(self) -> bool:
        return Colores.nombre == TEMA_OSCURO

    def aplicar(self, nombre: str, app: QApplication | None = None) -> None:
        """Activa el tema `nombre` ("dia" u "oscuro"). Un nombre desconocido usa el de día."""
        if nombre not in PALETAS:
            nombre = TEMA_POR_DEFECTO

        app = app or QApplication.instance()
        if app is None:
            Colores.cargar(nombre)
            return

        # Se congelan los repintados para que el cambio no parpadee a medias
        ventanas = app.topLevelWidgets()
        for ventana in ventanas:
            ventana.setUpdatesEnabled(False)
        try:
            Colores.cargar(nombre)

            if not self._inicializado:
                app.setStyle("Fusion")
                app.setFont(QFont("Segoe UI", 10))
                self._inicializado = True

            app.setPalette(_paleta())
            app.setStyleSheet(_estilo_global())
        finally:
            for ventana in ventanas:
                ventana.setUpdatesEnabled(True)

        # Después de la hoja de estilos: los widgets que repintan a mano leen ya
        # los colores nuevos.
        self.tema_cambiado.emit(nombre)


_gestor: GestorTema | None = None


def gestor_tema() -> GestorTema:
    """Gestor único de la aplicación (se crea la primera vez que se pide)."""
    global _gestor
    if _gestor is None:
        _gestor = GestorTema()
    return _gestor


def aplicar_tema(app: QApplication, nombre: str = TEMA_POR_DEFECTO) -> None:
    """Aplica estilo base, paleta, fuente y hoja de estilos global."""
    gestor_tema().aplicar(nombre, app)


def al_cambiar_tema(slot) -> None:
    """Suscribe `slot` al cambio de tema.

    Pasa siempre un método de un QObject (p. ej. `self._aplicar_tema`): Qt lo
    desconecta solo cuando el widget se destruye. Con lambdas no ocurre.
    """
    gestor_tema().tema_cambiado.connect(slot)


# ── Helpers ───────────────────────────────────────────────────────────────────

def rol(widget: QWidget, nombre: str) -> QWidget:
    """Asigna un 'rol' tipográfico (titulo, subtitulo, seccion, enlace, ok, error...)."""
    widget.setProperty("rol", nombre)
    return widget


def primario(boton: QPushButton) -> QPushButton:
    """Marca un botón como acción principal (relleno de color)."""
    boton.setProperty("primario", True)
    return boton


def tarjeta(widget: QWidget) -> QWidget:
    """Convierte un QWidget en una tarjeta con fondo de superficie y bordes redondeados."""
    from PyQt6.QtCore import Qt

    widget.setObjectName("tarjeta")
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    return widget


def repulir(widget: QWidget) -> None:
    """Vuelve a evaluar los selectores de estilo tras cambiar una propiedad dinámica."""
    estilo = widget.style()
    estilo.unpolish(widget)
    estilo.polish(widget)
    widget.update()
