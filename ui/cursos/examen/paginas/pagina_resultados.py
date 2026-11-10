"""
Pantalla de resultados: puntaje, veredicto y repaso de lo fallado.
"""

from html import escape

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from services.examen_service import PORCENTAJE_APROBACION, ResultadoExamen
from ui.theme import Colores as C, fs, rol

from ..widgets.enunciado import crear_enunciado
from ..widgets.utiles import crear_scroll, vaciar


class PaginaResultados:
    """Contiene el área desplazable (`.widget`) y sabe dibujar un resultado en ella."""

    def __init__(self):
        self._contenido = QWidget()
        self._layout = QVBoxLayout(self._contenido)
        self._layout.setContentsMargins(28, 22, 28, 22)
        self._layout.setSpacing(12)
        self.widget = crear_scroll(self._contenido)

    def mostrar(
        self,
        resultado: ResultadoExamen,
        *,
        con_certificado: bool,
        examen_nuevo_al_reintentar: bool,
    ) -> None:
        layout = self._layout
        vaciar(layout)

        etiqueta = QLabel("RESULTADO")
        rol(etiqueta, "seccion")

        puntaje = QLabel(f"{resultado.aciertos} de {resultado.total} correctas · {resultado.porcentaje}%")
        puntaje.setStyleSheet(f"font-size: {fs(26)}px; font-weight: 600;")

        if resultado.aprobado:
            texto, rol_veredicto = "✓ ¡Aprobado! Completaste el curso.", "ok"
            if con_certificado:
                texto += " Ya puedes descargar tu certificado."
        else:
            texto = (
                f"No alcanzaste el {PORCENTAJE_APROBACION}% necesario. "
                "Repasa los temas indicados e inténtalo de nuevo"
                + (": el próximo intento tendrá preguntas nuevas." if examen_nuevo_al_reintentar else ".")
            )
            rol_veredicto = "error"
        veredicto = QLabel(texto)
        veredicto.setWordWrap(True)
        rol(veredicto, rol_veredicto)
        veredicto.setStyleSheet(f"font-size: {fs(15)}px;")

        layout.addWidget(etiqueta)
        layout.addWidget(puntaje)
        layout.addWidget(veredicto)

        if resultado.errores:
            layout.addSpacing(10)
            seccion = QLabel("PARA REPASAR")
            rol(seccion, "seccion")
            layout.addWidget(seccion)
            for revision in resultado.errores:
                layout.addWidget(self._crear_revision(revision))
        else:
            perfecto = QLabel("Respondiste todas las preguntas correctamente.")
            rol(perfecto, "suave")
            perfecto.setStyleSheet(f"font-size: {fs(14)}px;")
            layout.addWidget(perfecto)

        layout.addStretch(1)

    @staticmethod
    def _crear_revision(revision) -> QFrame:
        pregunta = revision.pregunta

        marco = QFrame()
        marco.setObjectName("revision")  # aspecto en la hoja global (theme.py)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        layout.addWidget(crear_enunciado(pregunta.enunciado, tam=15))

        if revision.elegida is None:
            tu_respuesta = f"<span style='color:{C.ERROR};'>✗</span> Sin responder"
        else:
            tu_respuesta = (
                f"<span style='color:{C.ERROR};'>✗</span> "
                f"Tu respuesta: {escape(revision.elegida)}"
            )
        correcta = (
            f"<span style='color:{C.OK_TEXTO};'>✓</span> "
            f"Correcta: {escape(revision.correcta)}"
        )
        for html in (tu_respuesta, correcta):
            linea = QLabel(html)
            linea.setTextFormat(Qt.TextFormat.RichText)
            linea.setWordWrap(True)
            linea.setStyleSheet(f"font-size: {fs(13)}px;")
            layout.addWidget(linea)

        if pregunta.explicacion:
            explicacion = QLabel(pregunta.explicacion)
            explicacion.setTextFormat(Qt.TextFormat.PlainText)
            explicacion.setWordWrap(True)
            rol(explicacion, "suave")
            explicacion.setStyleSheet(f"font-size: {fs(13)}px;")
            layout.addWidget(explicacion)

        if pregunta.leccion_titulo:
            repasar = QLabel(f"Repasar: {pregunta.leccion_titulo}")
            repasar.setTextFormat(Qt.TextFormat.PlainText)
            repasar.setWordWrap(True)
            rol(repasar, "acento")
            repasar.setStyleSheet(f"font-size: {fs(12)}px; font-weight: 600;")
            layout.addWidget(repasar)

        return marco
