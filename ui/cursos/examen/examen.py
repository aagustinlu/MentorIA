"""
Ventana de la evaluación final (opción múltiple).

Flujo de una sola ventana, con tres pantallas:
    0. Inicio      -> datos del examen y botón «Comenzar»
    1. Preguntas   -> una por vez, se puede volver atrás y cambiar respuestas
    2. Resultados  -> puntaje, aprobado/no aprobado y repaso de lo fallado

La lógica (mezcla de opciones, calificación) vive en `SesionExamen`
(services/examen_service.py); las piezas de interfaz están en `examen_ui/`:
    widgets.py            -> utilidades y OpcionRespuesta
    pagina_inicio.py      -> pantalla de inicio
    pagina_resultados.py  -> pantalla de resultados
    barra_inferior.py     -> botones de la parte inferior

Este archivo solo coordina el flujo.
"""

import sys
from functools import partial
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# Asegura que la raíz del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.models import ExamenModel
from services import SoundPlayer
from services.examen_service import ResultadoExamen, SesionExamen
from ui.theme import al_cambiar_tema, rol, tarjeta

from .paginas import PAGINA_INICIO, PAGINA_PREGUNTAS, PAGINA_RESULTADOS
from .paginas.pagina_inicio import crear_pagina_inicio
from .paginas.pagina_resultados import PaginaResultados
from .widgets.barra_inferior import BarraInferior
from .widgets.enunciado import crear_enunciado
from .widgets.opcion_respuesta import OpcionRespuesta
from .widgets.utiles import crear_scroll, vaciar


class ExamenMenu(QWidget):

    def __init__(self, examen: ExamenModel, estado: dict | None = None, on_finalizar=None,
                 on_nuevo_examen=None, on_certificado=None):
        """
        examen:          ExamenModel con sus preguntas.
        estado:          resumen de intentos previos {"intentos", "aprobado", "mejor"}.
        on_finalizar:    callable(ResultadoExamen) -> bool que persiste el intento
                         y actualiza el progreso del curso.
        on_nuevo_examen: callable() que genera un examen nuevo (preguntas distintas)
                         y reemplaza esta ventana. Si es None, «Reintentar» repite
                         las mismas preguntas.
        on_certificado:  callable(parent_widget) que guarda el certificado del curso.
                         Si es None, no se muestra el botón de certificado.
        """
        super().__init__()

        self.examen = examen
        self.estado = estado or {}
        self.on_finalizar = on_finalizar
        self.on_nuevo_examen = on_nuevo_examen
        self.on_certificado = on_certificado

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

        self.pagina_resultados = PaginaResultados()

        self.pila = QStackedWidget()
        self.pila.addWidget(crear_pagina_inicio(self.examen, self.estado))  # PAGINA_INICIO
        self.pila.addWidget(self._crear_preguntas())                        # PAGINA_PREGUNTAS
        self.pila.addWidget(self.pagina_resultados.widget)                  # PAGINA_RESULTADOS

        self.tarjeta_examen = QWidget()
        tarjeta(self.tarjeta_examen)
        layout_tarjeta = QVBoxLayout(self.tarjeta_examen)
        layout_tarjeta.setContentsMargins(8, 12, 8, 12)
        layout_tarjeta.addWidget(self.pila)

        self.barra = BarraInferior(hay_intentos_previos=bool(self.estado.get("intentos")))
        self.barra.btn_comenzar.clicked.connect(lambda _checked=False: self.comenzar(False))
        self.barra.btn_anterior.clicked.connect(self.anterior)
        self.barra.btn_siguiente.clicked.connect(self.siguiente_o_finalizar)
        self.barra.btn_reintentar.clicked.connect(self._reintentar)
        self.barra.btn_certificado.clicked.connect(self._descargar_certificado)
        self.barra.btn_cerrar.clicked.connect(self.close)

        layout_principal.addWidget(self.tarjeta_examen, 1)
        layout_principal.addLayout(self.barra)

        self._ir_a(PAGINA_INICIO)

    def _crear_preguntas(self) -> QWidget:
        self.contenido_pregunta = QWidget()
        self.layout_pregunta = QVBoxLayout(self.contenido_pregunta)
        self.layout_pregunta.setContentsMargins(24, 14, 24, 14)
        self.layout_pregunta.setSpacing(12)
        return crear_scroll(self.contenido_pregunta)

    def _ir_a(self, pagina: int, aprobado: bool = False) -> None:
        self.pila.setCurrentIndex(pagina)
        self.barra.mostrar_pagina(
            pagina,
            aprobado=aprobado,
            curso_aprobado=bool(self.estado.get("aprobado")),
            con_certificado=self.on_certificado is not None,
        )

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

    def _descargar_certificado(self, _checked: bool = False) -> None:
        if self.on_certificado is not None:
            self.on_certificado(self)

    def _reintento_genera_nuevo(self) -> bool:
        """True si al reintentar hay que generar preguntas nuevas.

        Si el curso ya estaba aprobado no hace falta un examen nuevo:
        se repite el mismo.
        """
        return self.on_nuevo_examen is not None and not self.estado.get("aprobado")

    def _reintentar(self, _checked: bool = False) -> None:
        """Examen nuevo si aún no aprobaste; si ya habías aprobado, repite el mismo."""
        if self._reintento_genera_nuevo():
            self.on_nuevo_examen()
        else:
            self.comenzar(True)

    def mostrar_pregunta(self) -> None:
        layout = self.layout_pregunta
        vaciar(layout)

        i = self.indice
        encabezado = QLabel(f"PREGUNTA {i + 1} DE {len(self.sesion)}")
        rol(encabezado, "seccion")

        layout.addWidget(encabezado)
        layout.addWidget(crear_enunciado(self.sesion.preguntas[i].enunciado))
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

        self.barra.btn_anterior.setEnabled(self.indice > 0)
        self.barra.btn_siguiente.setText("Finalizar" if self.indice == total - 1 else "Siguiente")

        estado = f"{sin_responder} sin responder" if sin_responder else "todas respondidas"
        self.barra.lbl_progreso.setText(f"{self.indice + 1} / {total} · {estado}")

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
                "Intento no guardado",
                "No se pudo guardar el resultado de este intento. "
                "Puedes ver tu puntaje, pero no quedará registrado.",
            )

        SoundPlayer().play("exito" if resultado.aprobado else "error")
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
        self.pagina_resultados.mostrar(
            resultado,
            con_certificado=self.on_certificado is not None,
            examen_nuevo_al_reintentar=self._reintento_genera_nuevo(),
        )
        self._ir_a(PAGINA_RESULTADOS, aprobado=resultado.aprobado)

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
# Ejecutar como módulo, p. ej.:  python -m ui.windows.examen.examen_menu
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
