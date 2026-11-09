"""
Ventana de la evaluación final (opción múltiple).

Flujo de una sola ventana, con tres pantallas:
    0. Inicio      -> datos del examen y botón «Comenzar»
    1. Preguntas   -> una por vez, se puede volver atrás y cambiar respuestas
    2. Resultados  -> puntaje, aprobado/no aprobado y repaso de lo fallado

La lógica (mezcla de opciones, calificación) vive en `SesionExamen`
(services/examen_service.py); aquí solo hay interfaz.
"""

import math
import re
import sys
from functools import partial
from html import escape
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# Asegura que la raíz del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.models import ExamenModel
from services.examen_service import PORCENTAJE_APROBACION, ResultadoExamen, SesionExamen
from ui.theme import Colores as C, al_cambiar_tema, fs, primario, repulir, rol, tarjeta


PAGINA_INICIO, PAGINA_PREGUNTAS, PAGINA_RESULTADOS = 0, 1, 2

# Abre/cierra un bloque de código (``` o ```python) dentro de un enunciado
_VALLA_CODIGO = re.compile(r"```[A-Za-z0-9_+#-]*[ \t]*\n?")


# ==========================================================
# Utilidades de interfaz
# ==========================================================

def _vaciar(layout) -> None:
    """Elimina todos los widgets de un layout."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout() is not None:
            _vaciar(item.layout())


def _crear_scroll(contenido: QWidget) -> QScrollArea:
    """Área desplazable transparente (mismo estilo que las páginas de lección)."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    scroll.viewport().setAutoFillBackground(False)
    scroll.setWidget(contenido)
    # Después de setWidget(): Qt lo reactiva ahí y pintaría un rectángulo del
    # color de la ventana sobre la tarjeta.
    contenido.setAutoFillBackground(False)
    return scroll


def _crear_codigo(codigo: str) -> QPlainTextEdit:
    widget = QPlainTextEdit()
    widget.setReadOnly(True)

    fuente = QFont("Consolas")
    fuente.setStyleHint(QFont.StyleHint.Monospace)
    fuente.setPixelSize(fs(14))
    widget.setFont(fuente)

    widget.setPlainText(codigo)
    widget.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
    # Colores en la hoja global (theme.py): siguen al tema solos
    widget.setObjectName("codigoBloque")

    lineas = max(1, widget.document().blockCount())
    widget.setFixedHeight(min(lineas * widget.fontMetrics().lineSpacing() + 36, 220))
    return widget


def _crear_enunciado(texto: str, tam: int = 17) -> QWidget:

    
    contenedor = QWidget()
    layout = QVBoxLayout(contenedor)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    # split() alterna: texto, código, texto, código...
    for i, segmento in enumerate(_VALLA_CODIGO.split(texto)):
        if i % 2 == 1:
            codigo = segmento.strip("\n")
            if codigo.strip():
                layout.addWidget(_crear_codigo(codigo))
        else:
            limpio = segmento.replace("`", "").strip()
            if limpio:
                etiqueta = QLabel(limpio)
                etiqueta.setWordWrap(True)
                etiqueta.setTextFormat(Qt.TextFormat.PlainText)
                etiqueta.setStyleSheet(f"font-size: {fs(tam)}px; font-weight: 600;")
                layout.addWidget(etiqueta)

    return contenedor


class OpcionRespuesta(QFrame):
    """Opción clicable con texto que se ajusta al ancho (un QPushButton no puede)."""

    clicked = pyqtSignal()

    def __init__(self, letra: str, texto: str):
        super().__init__()
        self.setObjectName("opcion")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        self.lbl_letra = QLabel(letra)
        self.lbl_letra.setFixedWidth(26)
        rol(self.lbl_letra, "letra")
        # El clic debe llegar al marco, no quedarse en las etiquetas
        self.lbl_letra.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.lbl_texto = QLabel(texto)
        self.lbl_texto.setWordWrap(True)
        self.lbl_texto.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_texto.setStyleSheet(f"font-size: {fs(14)}px;")
        self.lbl_texto.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout.addWidget(self.lbl_letra, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.lbl_texto, 1)

        self.set_seleccionada(False)

    def set_seleccionada(self, seleccionada: bool) -> None:
        # El aspecto de cada estado está en la hoja global (theme.py)
        self.setProperty("seleccionada", seleccionada)
        repulir(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ==========================================================
# Ventana del examen
# ==========================================================

class ExamenMenu(QWidget):

    def __init__(self, examen: ExamenModel, estado: dict | None = None, on_finalizar=None,
                 on_nuevo_examen=None):
        """
        examen:          ExamenModel con sus preguntas.
        estado:          resumen de intentos previos {"intentos", "aprobado", "mejor"}.
        on_finalizar:    callable(ResultadoExamen) -> bool que persiste el intento
                         y actualiza el progreso del curso.
        on_nuevo_examen: callable() que genera un examen nuevo (preguntas distintas)
                         y reemplaza esta ventana. Si es None, «Reintentar» repite
                         las mismas preguntas.
        """
        super().__init__()

        self.examen = examen
        self.estado = estado or {}
        self.on_finalizar = on_finalizar
        self.on_nuevo_examen = on_nuevo_examen

        self.sesion: SesionExamen | None = None
        self.indice = 0
        self.opciones_ui: list[OpcionRespuesta] = []
        self._en_curso = False
        self._ultimo_resultado: ResultadoExamen | None = None

        self.iniciar_ui()

        # La pantalla de resultados lleva marcas ✓/✗ coloreadas dentro de HTML:
        # se regenera al cambiar de tema.
        al_cambiar_tema(self._al_cambiar_tema)

    # ------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------

    def iniciar_ui(self):
        self.setWindowTitle(self.examen.titulo)
        self.resize(720, 600)

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 16)
        layout_principal.setSpacing(14)

        self.pila = QStackedWidget()
        self.pila.addWidget(self._crear_inicio())        # PAGINA_INICIO
        self.pila.addWidget(self._crear_preguntas())     # PAGINA_PREGUNTAS
        self.pila.addWidget(self._crear_resultados())    # PAGINA_RESULTADOS

        self.tarjeta_examen = QWidget()
        tarjeta(self.tarjeta_examen)
        layout_tarjeta = QVBoxLayout(self.tarjeta_examen)
        layout_tarjeta.setContentsMargins(8, 12, 8, 12)
        layout_tarjeta.addWidget(self.pila)

        layout_principal.addWidget(self.tarjeta_examen, 1)
        layout_principal.addLayout(self._crear_barra_inferior())

        self._ir_a(PAGINA_INICIO)

    def _crear_inicio(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(12)

        etiqueta = QLabel("EVALUACIÓN FINAL")
        rol(etiqueta, "seccion")

        titulo = QLabel(self.examen.titulo)
        titulo.setWordWrap(True)
        titulo.setStyleSheet(f"font-size: {fs(24)}px; font-weight: 600;")

        total = len(self.examen.preguntas)
        minimo = math.ceil(PORCENTAJE_APROBACION * total / 100)
        info = QLabel(
            f"{total} preguntas de opción múltiple basadas en las lecciones del curso.\n\n"
            f"Para aprobar necesitas al menos un {PORCENTAJE_APROBACION}% de respuestas "
            f"correctas ({minimo} de {total}).\n\n"
            "Antes de finalizar puedes volver atrás y cambiar tus respuestas."
        )
        info.setWordWrap(True)
        rol(info, "suave")
        info.setStyleSheet(f"font-size: {fs(14)}px;")

        layout.addWidget(etiqueta)
        layout.addWidget(titulo)
        layout.addSpacing(6)
        layout.addWidget(info)

        previo = self._texto_intentos_previos()
        if previo:
            lbl_previo = QLabel(previo)
            lbl_previo.setWordWrap(True)
            lbl_previo.setStyleSheet(f"font-size: {fs(14)}px; font-weight: 600;")
            layout.addSpacing(10)
            layout.addWidget(lbl_previo)

        layout.addStretch(1)
        return pagina

    def _texto_intentos_previos(self) -> str:
        intentos = self.estado.get("intentos", 0)
        if not intentos:
            return ""

        lineas = []
        if self.estado.get("aprobado"):
            lineas.append("✓ Ya aprobaste esta evaluación.")

        mejor = self.estado.get("mejor")
        if mejor:
            aciertos, total = mejor
            porcentaje = round(100 * aciertos / total)
            lineas.append(
                f"Mejor resultado: {aciertos}/{total} ({porcentaje}%) · "
                f"{intentos} {'intento' if intentos == 1 else 'intentos'}"
            )
        return "\n".join(lineas)

    def _crear_preguntas(self) -> QWidget:
        self.contenido_pregunta = QWidget()
        self.layout_pregunta = QVBoxLayout(self.contenido_pregunta)
        self.layout_pregunta.setContentsMargins(24, 14, 24, 14)
        self.layout_pregunta.setSpacing(12)
        return _crear_scroll(self.contenido_pregunta)

    def _crear_resultados(self) -> QWidget:
        self.contenido_resultados = QWidget()
        self.layout_resultados = QVBoxLayout(self.contenido_resultados)
        self.layout_resultados.setContentsMargins(28, 22, 28, 22)
        self.layout_resultados.setSpacing(12)
        return _crear_scroll(self.contenido_resultados)

    def _crear_barra_inferior(self) -> QHBoxLayout:
        """Una sola barra; cada pantalla muestra solo los botones que le corresponden."""
        self.btn_comenzar = QPushButton()
        primario(self.btn_comenzar)
        self.btn_comenzar.setText(
            "Repetir examen" if self.estado.get("intentos") else "Comenzar examen"
        )
        self.btn_comenzar.clicked.connect(lambda _checked=False: self.comenzar(False))

        self.btn_anterior = QPushButton("Anterior")
        self.btn_anterior.clicked.connect(self.anterior)

        self.lbl_progreso = QLabel()
        self.lbl_progreso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_progreso.setMinimumWidth(170)
        rol(self.lbl_progreso, "subtitulo")

        self.btn_siguiente = QPushButton("Siguiente")
        primario(self.btn_siguiente)
        self.btn_siguiente.clicked.connect(self.siguiente_o_finalizar)

        self.btn_reintentar = QPushButton(
            "Reintentar" if self.on_nuevo_examen else "Reintentar"
        )
        primario(self.btn_reintentar)
        self.btn_reintentar.clicked.connect(self._reintentar)

        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.clicked.connect(self.close)

        botones = (
            self.btn_comenzar, self.btn_anterior, self.btn_siguiente,
            self.btn_reintentar, self.btn_cerrar,
        )
        for boton in botones:
            boton.setMinimumWidth(110)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_comenzar.setMinimumWidth(150)
        self.btn_siguiente.setMinimumWidth(150)
        self.btn_reintentar.setMinimumWidth(240)

        layout = QHBoxLayout()
        layout.setSpacing(12)
        layout.addStretch()
        layout.addWidget(self.btn_comenzar)
        layout.addWidget(self.btn_anterior)
        layout.addWidget(self.lbl_progreso)
        layout.addWidget(self.btn_siguiente)
        layout.addWidget(self.btn_reintentar)
        layout.addWidget(self.btn_cerrar)
        layout.addStretch()
        return layout

    def _ir_a(self, pagina: int, aprobado: bool = False) -> None:
        self.pila.setCurrentIndex(pagina)

        en_inicio = pagina == PAGINA_INICIO
        en_preguntas = pagina == PAGINA_PREGUNTAS
        en_resultados = pagina == PAGINA_RESULTADOS

        self.btn_comenzar.setVisible(en_inicio)
        self.btn_anterior.setVisible(en_preguntas)
        self.lbl_progreso.setVisible(en_preguntas)
        self.btn_siguiente.setVisible(en_preguntas)
        self.btn_reintentar.setVisible(en_resultados and not aprobado)
        self.btn_cerrar.setVisible(en_resultados)

    # ------------------------------------------------------
    # Rendición del examen
    # ------------------------------------------------------

    def comenzar(self, barajar_preguntas: bool = False) -> None:
        """Empieza un intento. En los reintentos también se mezcla el orden de las preguntas."""
        self.sesion = SesionExamen(self.examen.preguntas, barajar_preguntas=barajar_preguntas)
        self.indice = 0
        self._en_curso = True
        self._ir_a(PAGINA_PREGUNTAS)
        self.mostrar_pregunta()

    def _reintentar(self, _checked: bool = False) -> None:
        """Tras un intento fallido: examen nuevo con preguntas distintas (o el mismo, si no hay generador)."""
        if self.on_nuevo_examen is not None:
            self.on_nuevo_examen()
        else:
            self.comenzar(True)

    def mostrar_pregunta(self) -> None:
        layout = self.layout_pregunta
        _vaciar(layout)

        i = self.indice
        encabezado = QLabel(f"PREGUNTA {i + 1} DE {len(self.sesion)}")
        rol(encabezado, "seccion")

        layout.addWidget(encabezado)
        layout.addWidget(_crear_enunciado(self.sesion.preguntas[i].enunciado))
        layout.addSpacing(6)

        elegida = self.sesion.respuesta(i)
        self.opciones_ui = []
        for k, texto in enumerate(self.sesion.opciones_mostradas(i)):
            opcion = OpcionRespuesta("ABCDE"[k], texto)
            opcion.set_seleccionada(k == elegida)
            opcion.clicked.connect(partial(self.elegir, k))
            self.opciones_ui.append(opcion)
            layout.addWidget(opcion)

        layout.addStretch(1)
        self._actualizar_navegacion()

    def elegir(self, posicion: int) -> None:
        self.sesion.responder(self.indice, posicion)
        for k, opcion in enumerate(self.opciones_ui):
            opcion.set_seleccionada(k == posicion)
        self._actualizar_navegacion()

    def _actualizar_navegacion(self) -> None:
        total = len(self.sesion)
        sin_responder = self.sesion.sin_responder()

        self.btn_anterior.setEnabled(self.indice > 0)
        self.btn_siguiente.setText("Finalizar" if self.indice == total - 1 else "Siguiente")

        estado = f"{sin_responder} sin responder" if sin_responder else "todas respondidas"
        self.lbl_progreso.setText(f"{self.indice + 1} / {total} · {estado}")

    def anterior(self) -> None:
        if self.indice > 0:
            self.indice -= 1
            self.mostrar_pregunta()

    def siguiente_o_finalizar(self) -> None:
        if self.indice < len(self.sesion) - 1:
            self.indice += 1
            self.mostrar_pregunta()
        else:
            self.finalizar()

    def finalizar(self) -> None:
        sin_responder = self.sesion.sin_responder()
        if sin_responder:
            respuesta = QMessageBox.question(
                self,
                "Finalizar examen",
                f"Te {'queda' if sin_responder == 1 else 'quedan'} {sin_responder} "
                f"{'pregunta' if sin_responder == 1 else 'preguntas'} sin responder "
                "(contarán como incorrectas).\n\n¿Finalizar igualmente?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return

        resultado = self.sesion.calificar()
        self._en_curso = False

        if self.on_finalizar is not None and not self.on_finalizar(resultado):
            QMessageBox.warning(
                self,
                "No se pudo guardar",
                "No se pudo guardar el resultado del examen. Puedes verlo ahora, "
                "pero no quedará registrado.",
            )

        self._mostrar_resultados(resultado)

    # ------------------------------------------------------
    # Resultados
    # ------------------------------------------------------

    def _al_cambiar_tema(self, _nombre: str = "") -> None:
        if (
            self._ultimo_resultado is not None
            and self.pila.currentIndex() == PAGINA_RESULTADOS
        ):
            self._mostrar_resultados(self._ultimo_resultado)

    def _mostrar_resultados(self, resultado: ResultadoExamen) -> None:
        self._ultimo_resultado = resultado
        layout = self.layout_resultados
        _vaciar(layout)

        etiqueta = QLabel("RESULTADO")
        rol(etiqueta, "seccion")

        puntaje = QLabel(f"{resultado.aciertos} de {resultado.total} correctas · {resultado.porcentaje}%")
        puntaje.setStyleSheet(f"font-size: {fs(26)}px; font-weight: 600;")

        if resultado.aprobado:
            texto, rol_veredicto = "✓ ¡Aprobado! Completaste el curso.", "ok"
        else:
            texto = (
                f"No alcanzaste el {PORCENTAJE_APROBACION}% necesario. "
                "Repasa los temas indicados e inténtalo de nuevo"
                + (": el próximo intento tendrá preguntas nuevas." if self.on_nuevo_examen else ".")
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
        self._ir_a(PAGINA_RESULTADOS, aprobado=resultado.aprobado)

    def _crear_revision(self, revision) -> QFrame:
        pregunta = revision.pregunta

        marco = QFrame()
        marco.setObjectName("revision")  # aspecto en la hoja global (theme.py)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        layout.addWidget(_crear_enunciado(pregunta.enunciado, tam=15))

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

    # ------------------------------------------------------
    # Cierre
    # ------------------------------------------------------

    def closeEvent(self, event):
        # Evita perder un intento a medias por cerrar la ventana sin querer
        if self._en_curso and self.sesion is not None and self.sesion.respuestas:
            respuesta = QMessageBox.question(
                self,
                "Salir del examen",
                "Si sales ahora perderás las respuestas de este intento.\n\n¿Salir igualmente?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        super().closeEvent(event)


# ==========================================================
# Prueba independiente (sin IA ni base de datos)
# ==========================================================

if __name__ == "__main__":
    from models.models import PreguntaModel
    from ui.theme import aplicar_tema

    demo = ExamenModel(
        id=1,
        curso_id=1,
        titulo="Evaluación final: Curso de prueba",
        preguntas=[
            PreguntaModel(
                posicion=0,
                leccion_titulo="Clases y objetos",
                enunciado="¿Qué es una clase?",
                opciones=["Un molde para crear objetos", "Una variable", "Un bucle", "Un archivo"],
                correcta=0,
                explicacion="Una clase define los atributos y métodos de sus objetos.",
            ),
            PreguntaModel(
                posicion=1,
                leccion_titulo="Encapsulación",
                enunciado="¿Qué imprime este código?\n```python\nx = 2\nprint(x * 3)\n```",
                opciones=["5", "6", "23", "Error"],
                correcta=1,
                explicacion="2 * 3 = 6.",
            ),
        ],
    )

    app = QApplication(sys.argv)
    aplicar_tema(app)
    ventana = ExamenMenu(demo, on_finalizar=lambda resultado: True)
    ventana.show()
    sys.exit(app.exec())
