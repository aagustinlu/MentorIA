from pathlib import Path
import sys

# Asegura que la raíz del proyecto esté en sys.path (permite ejecutar este módulo directo)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from controllers.controller_crear_curso import CrearCursoController
from services.database import BaseDatosProyecto

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from PyQt6.QtCore import QEvent, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from ui.theme import Colores as C, fs, repulir, rol
from services.fuente_multiidioma import crear_fuente_multidioma


RUTA_BD = "storage/sistema_estudios.db"


# ── Worker: genera el curso sin congelar la interfaz ─────────────────────────

class GenerarCursoWorker(QThread):
    
    terminado = pyqtSignal(object)   # CursoModel o None
    error = pyqtSignal(str)

    def __init__(self, texto: str, ruta: str | None = None):
        super().__init__()
        self.texto = texto
        self.ruta = ruta

    def run(self):
        try:
            db = BaseDatosProyecto(RUTA_BD)
            controller = CrearCursoController.desde_bd(db)
            self.terminado.emit(controller.crear_curso(self.texto, self.ruta))
        except Exception as e:
            self.error.emit(str(e))


# ── Popup de entrada ─────────────────────────────────────────────────────────

class CampoEntrada(QDialog):
    """Popup para escribir el prompt del curso.

    Al terminar la generación se cierra solo (accept) y deja el curso creado
    en `self.curso_creado`, para que quien lo abrió decida qué mostrar.
    """

    ALTURA_MIN = 40
    ALTURA_MAX = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        # Sin bordes nativos y con fondo transparente (para ver la tarjeta redondeada)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.archivo_cargado = None
        self.curso_creado = None
        self._worker: GenerarCursoWorker | None = None
        self._generando = False

        # Animación suave de "Generando…"
        self._puntos = 0
        self._timer = QTimer(self)
        self._timer.setInterval(450)
        self._timer.timeout.connect(self._animar_estado)

        self.initUI()

    # ── Construcción de la UI ────────────────────────────────────────────

    def initUI(self):
        self.setWindowTitle("Nuevo curso")

        # Layout raíz: deja margen para que se vea la sombra de la tarjeta
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 24, 24, 24)
        raiz.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        self.tarjeta = QFrame()
        self.tarjeta.setObjectName("tarjetaEntrada")
        self.tarjeta.setFixedWidth(620)
        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(36)
        sombra.setOffset(0, 6)
        color_sombra = QColor(C.SOMBRA)
        color_sombra.setAlpha(C.SOMBRA_ALFA)
        sombra.setColor(color_sombra)
        self.tarjeta.setGraphicsEffect(sombra)
        raiz.addWidget(self.tarjeta)

        interior = QVBoxLayout(self.tarjeta)
        interior.setContentsMargins(16, 16, 16, 12)
        interior.setSpacing(10)

        # Fuente base
        fuente_sistema = crear_fuente_multidioma(pixeles=fs(14))

        # Fila principal: [ + ] [ texto ] [ → ]
        self.layout_principal = QHBoxLayout()
        self.layout_principal.setSpacing(10)
        self.layout_principal.setAlignment(Qt.AlignmentFlag.AlignBottom)

        # 1. Botón para adjuntar archivo
        self.attach_button = QPushButton("+")
        self.attach_button.setObjectName("BotonAdjuntar")
        self.attach_button.setFont(crear_fuente_multidioma(pixeles=fs(18)))
        self.attach_button.setFixedSize(44, 44)
        self.attach_button.setToolTip("Adjuntar un archivo como material de estudio")
        self.attach_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_button.clicked.connect(self.adjuntar_un_archivo)

        # 2. Campo de texto multilínea
        self.input_field = QTextEdit()
        self.input_field.setObjectName("campoPrompt")  # aspecto en theme.py
        self.input_field.setFont(fuente_sistema)
        self.input_field.setPlaceholderText("¿Qué te gustaría aprender?")
        self.input_field.setAcceptRichText(False)
        self.input_field.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.input_field.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.input_field.textChanged.connect(self.ajustar_altura)
        self.input_field.installEventFilter(self)

        # 3. Botón para enviar
        self.send_button = QPushButton("→")
        self.send_button.setObjectName("BotonEnviar")
        self.send_button.setFont(crear_fuente_multidioma(pixeles=fs(18)))
        self.send_button.setFixedSize(44, 44)
        self.send_button.setToolTip("Crear curso")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self.procesar_envio)

        self.layout_principal.addWidget(self.attach_button)
        self.layout_principal.addWidget(self.input_field, 1)
        self.layout_principal.addWidget(self.send_button)
        interior.addLayout(self.layout_principal)

        # Línea de estado / ayuda
        self.estado = QLabel("Enter para crear  ·  Shift+Enter para nueva línea  ·  Esc para cerrar")
        rol(self.estado, "subtitulo")
        self.estado.setWordWrap(True)
        self.estado.setContentsMargins(4, 0, 4, 0)
        interior.addWidget(self.estado)

        # Todo el estilo del popup (tarjeta, campo, botones) vive en la hoja global
        # de theme.py, así que cambia solo con el tema.

        self.ajustar_altura()

    # ── Comportamiento del campo de texto ────────────────────────────────

    def ajustar_altura(self):
        documento = self.input_field.document()
        altura_contenido = int(documento.size().height()) + 20

        altura_final = max(self.ALTURA_MIN, min(altura_contenido, self.ALTURA_MAX))
        self.input_field.setFixedHeight(altura_final)

        if altura_contenido > self.ALTURA_MAX:
            self.input_field.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.input_field.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def eventFilter(self, obj, event):
        if obj is self.input_field and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.procesar_envio()
                    return True
        return super().eventFilter(obj, event)

    # ── Adjuntar archivo ─────────────────────────────────────────────────

    def adjuntar_un_archivo(self):
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar un único archivo", "", "Todos los archivos (*.*)"
        )
        if archivo:
            self.archivo_cargado = archivo
            nombre_corto = Path(archivo).name

            self.attach_button.setText("✓")
            self.attach_button.setProperty("adjunto", True)
            self.attach_button.style().unpolish(self.attach_button)
            self.attach_button.style().polish(self.attach_button)
            self.attach_button.setToolTip(f"Archivo cargado: {nombre_corto}")

            self._mostrar_estado(f"Adjunto: {nombre_corto}")

    # ── Envío y generación ───────────────────────────────────────────────

    def procesar_envio(self):
        if self._generando:
            return

        texto = self.input_field.toPlainText().strip()

        # Sin texto ni archivo no hay nada que generar (y no bloqueamos la UI)
        if not texto and not self.archivo_cargado:
            return

        self._establecer_bloqueo(True)
        self._generando = True
        self._puntos = 0
        self._animar_estado()
        self._timer.start()

        # self.archivo_cargado es la ruta completa del archivo seleccionado,
        # la cual GestorDeIA usa como `ruta` para subir el archivo.
        self._worker = GenerarCursoWorker(texto=texto, ruta=self.archivo_cargado)
        self._worker.terminado.connect(self._on_curso_generado)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_curso_generado(self, curso):
        self._finalizar_worker()

        if curso:
            # Curso listo → el popup se cierra solo
            self.curso_creado = curso
            self.accept()
        else:
            self._establecer_bloqueo(False)
            self._mostrar_estado("No se pudo generar el curso. Intenta de nuevo.", error=True)

    def _on_error(self, mensaje: str):
        self._finalizar_worker()
        self._establecer_bloqueo(False)
        self._mostrar_estado(f"Ocurrió un error.", error=True)
        print(mensaje)

    def _finalizar_worker(self):
        self._timer.stop()
        self._generando = False
        if self._worker is not None:
            # El hilo está terminando; esperamos para no destruirlo en ejecución
            self._worker.wait()

    # ── Utilidades de UI ─────────────────────────────────────────────────

    def _establecer_bloqueo(self, bloquear: bool):
        self.attach_button.setEnabled(not bloquear)
        self.input_field.setEnabled(not bloquear)
        self.send_button.setEnabled(not bloquear)
        if not bloquear:
            self.input_field.setFocus()

    def _animar_estado(self):
        self._puntos = (self._puntos % 3) + 1
        self._mostrar_estado("Generando tu curso" + "." * self._puntos)

    def _mostrar_estado(self, texto: str, error: bool = False):
        self.estado.setProperty("error", error)
        repulir(self.estado)
        self.estado.setText(texto)

    # Evita cerrar el popup mientras la IA trabaja (se destruiría el hilo en ejecución)
    def reject(self):
        if self._generando:
            return
        super().reject()


if __name__ == '__main__':
    from ui.theme import aplicar_tema

    app = QApplication(sys.argv)
    aplicar_tema(app)
    window = CampoEntrada()
    window.show()
    sys.exit(app.exec())
