"""Interruptor animado para alternar entre Modo Día y Modo Oscuro.

Es un botón "checkable" (marcado = modo oscuro) que dibuja un sol o una luna
sobre una perilla que se desliza. Pinta con los colores del tema activo cada
vez que se repinta, así que cambia de aspecto solo al cambiar de tema.
"""

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    pyqtProperty,
)
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QAbstractButton

from ui.theme import Colores as C, al_cambiar_tema


class InterruptorTema(QAbstractButton):
    ANCHO = 62
    ALTO = 32
    MARGEN = 4
    DURACION_MS = 220

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setCheckable(True)
        self.setFixedSize(self.ANCHO, self.ALTO)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAccessibleName("Modo oscuro")
        self.setToolTip("Alternar entre modo día y modo oscuro")

        # 0.0 = perilla a la izquierda (día) · 1.0 = a la derecha (oscuro)
        self._posicion = 0.0

        self._animacion = QPropertyAnimation(self, b"posicion", self)
        self._animacion.setDuration(self.DURACION_MS)
        self._animacion.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self.toggled.connect(self._animar)
        # Si el tema cambia desde otro lugar, solo hay que repintar
        al_cambiar_tema(self._al_cambiar_tema)

    # ── API ──────────────────────────────────────────────────────────────

    def set_oscuro(self, oscuro: bool, animar: bool = False) -> None:
        """Fija el estado sin emitir `toggled` (no vuelve a cambiar el tema)."""
        if self.isChecked() == oscuro:
            return  # ya está así: no se interrumpe una animación en curso

        self.blockSignals(True)
        self.setChecked(oscuro)
        self.blockSignals(False)

        if animar:
            self._animar(oscuro)
        else:
            self._animacion.stop()
            self._set_posicion(1.0 if oscuro else 0.0)

    # ── Propiedad animable ───────────────────────────────────────────────

    def _get_posicion(self) -> float:
        return self._posicion

    def _set_posicion(self, valor: float) -> None:
        self._posicion = valor
        self.update()

    posicion = pyqtProperty(float, _get_posicion, _set_posicion)

    def _animar(self, oscuro: bool) -> None:

        self._animacion.stop()
        self._animacion.setStartValue(self._posicion)
        self._animacion.setEndValue(1.0 if oscuro else 0.0)
        self._animacion.start()


    def _al_cambiar_tema(self, _nombre: str = "") -> None:
        self.update()

    # ── Tamaño ───────────────────────────────────────────────────────────

    def sizeHint(self) -> QSize:
        return QSize(self.ANCHO, self.ALTO)

    # ── Pintado ──────────────────────────────────────────────────────────

    def paintEvent(self, _evento) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        ancho, alto = self.width(), self.height()

        # Pista
        pista = QRectF(1, 1, ancho - 2, alto - 2)
        borde = QColor(C.ACENTO if self.hasFocus() else C.BORDE)
        p.setPen(QPen(borde, 1.5 if self.hasFocus() else 1.0))
        p.setBrush(QColor(C.CAMPO))
        p.drawRoundedRect(pista, pista.height() / 2, pista.height() / 2)

        # Perilla
        diametro = alto - 2 * self.MARGEN
        x = self.MARGEN + self._posicion * (ancho - alto)
        perilla = QRectF(x, self.MARGEN, diametro, diametro)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C.ACENTO_HOVER if self.underMouse() else C.ACENTO))
        p.drawEllipse(perilla)

        # Icono: el sol se desvanece mientras aparece la luna
        centro = perilla.center()
        radio = diametro / 2
        color_icono = QColor(C.TEXTO_SOBRE_ACENTO)

        p.setOpacity(max(0.0, 1.0 - self._posicion * 1.4))
        self._dibujar_sol(p, centro, radio * 0.78, color_icono)

        p.setOpacity(max(0.0, self._posicion * 1.4 - 0.4))
        self._dibujar_luna(p, centro, radio * 0.78, color_icono)

        p.end()

    @staticmethod
    def _dibujar_sol(p: QPainter, centro: QPointF, radio: float, color: QColor) -> None:
        nucleo = radio * 0.46
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(centro, nucleo, nucleo)

        lapiz = QPen(color, max(1.2, radio * 0.14))
        lapiz.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(lapiz)
        for i in range(8):
            p.save()
            p.translate(centro)
            p.rotate(i * 45)
            p.drawLine(QPointF(0, -radio * 0.68), QPointF(0, -radio * 0.95))
            p.restore()

    @staticmethod
    def _dibujar_luna(p: QPainter, centro: QPointF, radio: float, color: QColor) -> None:
        r = radio * 0.82
        luna = QPainterPath()
        luna.addEllipse(centro, r, r)
        recorte = QPainterPath()
        recorte.addEllipse(QPointF(centro.x() + r * 0.62, centro.y() - r * 0.32), r * 0.88, r * 0.88)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(luna.subtracted(recorte))
