"""
Barra de navegación de la ventana única de MentorIA.

La aplicación tiene una sola ventana. Las pantallas (curso, lección, examen)
se apilan dentro de ella y esta barra, visible en todas menos en el inicio,
ofrece:

    [ 🏠 Inicio ]  [ ‹ Volver ]   Inicio › Curso › Lección: …

El botón «Inicio» es accesible:
    - nombre y descripción para lectores de pantalla,
    - se alcanza con Tab y se activa con Espacio/Enter,
    - atajo Alt+Inicio (Alt+Home),
    - anillo de foco visible (ver theme.py, QPushButton#btnInicio),
    - área de clic cómoda (alto mínimo de 40 px).
"""

from functools import lru_cache

from PyQt6.QtCore import QByteArray, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QIcon, QKeySequence, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from ui.theme import Colores as C, al_cambiar_tema


# ── Íconos vectoriales (nítidos a cualquier tamaño y recoloreables) ───────────

_SVG_CASA = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 10.5 12 3l9 7.5"/>
  <path d="M5 9.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9.5"/>
</svg>"""

_SVG_ATRAS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M15 5 8 12l7 7"/>
</svg>"""


@lru_cache(maxsize=None)
def _icono(svg: str, color: str, lado: int) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg.format(color=color).encode()))
    pixmap = QPixmap(lado * 2, lado * 2)      # 2x para pantallas de alta densidad
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(Qt.GlobalColor.transparent)
    pintor = QPainter(pixmap)
    renderer.render(pintor, QRectF(0, 0, lado, lado))
    pintor.end()
    return QIcon(pixmap)


# ── Botones ───────────────────────────────────────────────────────────────────

class _BotonConIcono(QPushButton):
    """Botón con ícono SVG que se recolorea solo al cambiar el tema."""

    LADO_ICONO = 18
    SVG = ""

    def __init__(self, texto: str, nombre_objeto: str):
        super().__init__(texto)
        self.setObjectName(nombre_objeto)
        self.setIconSize(QSize(self.LADO_ICONO, self.LADO_ICONO))
        self.setMinimumHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)   # alcanzable con Tab
        self._pintar_icono()
        al_cambiar_tema(self._al_cambiar_tema)

    def _al_cambiar_tema(self, _nombre: str = "") -> None:
        self._pintar_icono()

    def _pintar_icono(self) -> None:
        self.setIcon(_icono(self.SVG, C.TEXTO, self.LADO_ICONO))


class BotonInicio(_BotonConIcono):
    """«Volver al inicio»: casa + texto, con atajo Alt+Inicio."""

    SVG = _SVG_CASA

    def __init__(self):
        super().__init__("Inicio", "btnInicio")
        self.setToolTip("Volver al inicio (Alt+Inicio)")
        self.setAccessibleName("Volver al inicio")
        self.setAccessibleDescription(
            "Cierra esta pantalla y regresa a la pantalla de inicio con tus cursos."
        )
        self.setShortcut(QKeySequence("Alt+Home"))


class BotonVolver(_BotonConIcono):
    """«Volver» a la pantalla anterior (p. ej. de una lección al mapa del curso)."""

    SVG = _SVG_ATRAS

    def __init__(self):
        super().__init__("Volver", "btnVolver")
        self.setToolTip("Volver a la pantalla anterior (Alt+←)")
        self.setAccessibleName("Volver a la pantalla anterior")
        self.setShortcut(QKeySequence("Alt+Left"))


# ── Migas de pan ──────────────────────────────────────────────────────────────

class EtiquetaElidida(QLabel):
    """Etiqueta de una línea que recorta con «…» en vez de ensanchar la ventana."""

    def __init__(self, texto: str = ""):
        super().__init__(texto)
        self._completo = texto
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)

    def setText(self, texto: str) -> None:   # noqa: N802 (API de Qt)
        self._completo = texto
        self.setToolTip(texto)
        self._ajustar()

    def resizeEvent(self, evento) -> None:   # noqa: N802
        super().resizeEvent(evento)
        self._ajustar()

    def _ajustar(self) -> None:
        recortado = QFontMetrics(self.font()).elidedText(
            self._completo, Qt.TextElideMode.ElideRight, max(0, self.width())
        )
        super().setText(recortado)


# ── Barra ─────────────────────────────────────────────────────────────────────

class BarraNavegacion(QWidget):
    inicio_solicitado = pyqtSignal()
    volver_solicitado = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("barraNavegacion")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.btn_inicio = BotonInicio()
        self.btn_inicio.clicked.connect(lambda _checked=False: self.inicio_solicitado.emit())

        self.btn_volver = BotonVolver()
        self.btn_volver.clicked.connect(lambda _checked=False: self.volver_solicitado.emit())

        self.migas = EtiquetaElidida()
        self.migas.setProperty("rol", "subtitulo")
        self.migas.setAccessibleName("Ubicación actual")

        layout.addWidget(self.btn_inicio)
        layout.addWidget(self.btn_volver)
        layout.addSpacing(6)
        layout.addWidget(self.migas, 1)

        # Orden de tabulación: Inicio → Volver
        QWidget.setTabOrder(self.btn_inicio, self.btn_volver)

    def mostrar_ruta(self, titulos: list[str], con_volver: bool) -> None:
        """`titulos`: nombres de las pantallas apiladas, de la primera a la actual."""
        self.migas.setText("  ›  ".join(["Inicio", *titulos]))
        self.btn_volver.setVisible(con_volver)
        if con_volver and len(titulos) >= 2:
            self.btn_volver.setToolTip(f"Volver a «{titulos[-2]}» (Alt+←)")
            self.btn_volver.setAccessibleDescription(f"Regresa a {titulos[-2]}.")
