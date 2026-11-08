import sys
import random
from pathlib import Path




from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsSimpleTextItem,
    QGraphicsTextItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
    QProgressDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QIcon

# Asegura que el proyecto raíz esté en sys.path para imports absolutos
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.models import CursoModel, LeccionModel
from ui.theme import Colores as C, al_cambiar_tema, fs, rol, tarjeta

ruta_logo = PROJECT_ROOT / "files" / "img" / "Mentoria Logo.png"

def _parsear_curso_para_ui(curso_data) -> CursoModel:
    """Normaliza datos (dict o CursoModel) al esquema de dominio."""

    if isinstance(curso_data, CursoModel):
        return curso_data

    if not isinstance(curso_data, dict):
        raise TypeError("curso_data debe ser dict o CursoModel")

    titulo = curso_data.get("titulo", curso_data.get("titulo_curso", ""))
    descripcion = curso_data.get("descripcion", curso_data.get("descripcion_curso", ""))

    lecciones_raw = curso_data.get("lecciones", curso_data.get("lessons", []))

    lecciones_model: list[LeccionModel] = []
    for i, le in enumerate(lecciones_raw):
        if isinstance(le, LeccionModel):
            lecciones_model.append(le)
        elif isinstance(le, dict):
            lecciones_model.append(
                LeccionModel(
                    titulo=le.get("titulo", ""),
                    resumen=le.get("resumen", le.get("summary", "")),
                    posicion=le.get("posicion", le.get("position", i)),
                    estado=le.get("estado", "locked"),
                    paginas=[],
                )
            )
        else:
            raise TypeError("Cada lección debe ser dict o LeccionModel")

    return CursoModel(
        id=curso_data.get("id"),
        titulo=titulo,
        descripcion=descripcion,
        fuente=curso_data.get("fuente", ""),
        lecciones=lecciones_model,
    )


# ── Worker para generar lección en segundo plano ──────────────────────────────

class GenerarLeccionWorker(QThread):
    """Hilo para generar el contenido de una lección sin bloquear la UI."""

    terminado = pyqtSignal(object)   # LeccionModel o None
    error = pyqtSignal(str)

    def __init__(self, leccion_id: int, db):
        super().__init__()
        self.leccion_id = leccion_id
        self.db = db

    def run(self):
        try:
            from services.ai_service import GestorDeIA

            info = self.db.obtener_info_leccion(self.leccion_id)
            if not info:
                self.error.emit("No se encontró información de la lección.")
                return

            titulo, summary, curso_id, fuente = info

            curso = self.db.obtener_curso(curso_id)
            curso_titulo = curso.titulo if curso else ""

            perfil = self.db.obtener_perfil()
            api_key = perfil[1] if perfil else None
            if not api_key:
                self.error.emit("No hay API Key configurada. Ve a Configuración.")
                return

            gestor = GestorDeIA(api_key=api_key)
            contenido = gestor.generar_contenido_leccion(
                curso_titulo=curso_titulo,
                titulo=titulo,
                descripcion=summary or "",
                fuente=fuente or "",
            )

            # Guardar en BD
            self.db.guardar_contenido_leccion(self.leccion_id, contenido.paginas)

            # Releer desde BD para tener el LeccionModel completo
            leccion_model = self.db.obtener_contenido_leccion(self.leccion_id)
            self.terminado.emit(leccion_model)

        except Exception as e:
            self.error.emit(str(e))


# ── Worker para generar la evaluación final en segundo plano ──────────────────

class GenerarExamenWorker(QThread):

    terminado = pyqtSignal(object)   # ExamenModel o None
    error = pyqtSignal(str)

    def __init__(self, curso_id: int, db):
        super().__init__()
        self.curso_id = curso_id
        self.db = db

    def run(self):
        try:
            from services.ai_service import GestorDeIA

            curso = self.db.obtener_curso(self.curso_id)
            if not curso or not curso.lecciones:
                self.error.emit("No se encontró el curso o no tiene lecciones.")
                return

            # Solo lecciones con contenido guardado (las completadas siempre lo tienen)
            lecciones = []
            for leccion in curso.lecciones:
                contenido = self.db.obtener_contenido_leccion(leccion.id)
                if contenido:
                    lecciones.append(contenido)
            if not lecciones:
                self.error.emit("El curso no tiene contenido de lecciones para evaluar.")
                return

            
            perfil = self.db.obtener_perfil()
            api_key = perfil[1] if perfil else None

            if not api_key:
                self.error.emit("No hay API Key configurada. Ve a Configuración.")
                return


            gestor = GestorDeIA(api_key=api_key)
            preguntas = gestor.generar_examen(curso.titulo, lecciones)

            examen_id = self.db.guardar_examen(
                self.curso_id,
                f"Evaluación final: {curso.titulo}",
                preguntas,
                [leccion.id for leccion in lecciones],
            )
            if examen_id is None:
                self.error.emit("No se pudo guardar la evaluación en la base de datos.")
                return

            self.terminado.emit(self.db.obtener_examen(self.curso_id))

        except Exception as e:
            self.error.emit(str(e))


# ── Nodo visual ───────────────────────────────────────────────────────────────

class NodoCircular(QGraphicsEllipseItem):
    def __init__(
        self,
        panel_derecho,
        x,
        y,
        radio,
        estado,
        titulo,
        leccion_id=None,
        es_examen=False,
    ):
        super().__init__(-radio, -radio, radio * 2, radio * 2)

        self.panel_derecho = panel_derecho
        self.titulo = titulo
        self.leccion_id = leccion_id
        self.estado = estado
        self.es_examen = es_examen

        # Verde (completed) y azul (current) se pueden abrir; gris (locked) no.
        self.habilitado = estado in ("completed", "current")

        if estado == "completed":
            color = C.COMPLETADO
        elif estado == "current":
            color = C.ACTUAL
        else:
            color = C.BLOQUEADO

        self.setPos(x, y)
        self.setBrush(QBrush(QColor(color)))
        # Borde claro: da un aspecto suave de "botón" sobre el fondo
        self.setPen(QPen(QColor(C.SUPERFICIE), 4))
        self.setZValue(1)

        # Al pasar el cursor por encima se muestra el título de la lección
        self.setToolTip(titulo)

        if self.habilitado:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFlag(
                QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable
            )
        else:
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
            if es_examen:
                self.setToolTip(f"{titulo}\n(bloqueada: completa todas las lecciones para desbloquearla)")
            else:
                self.setToolTip(f"{titulo}\n(bloqueada: completa la lección actual para desbloquearla)")

        if es_examen:
            # Estrella centrada: distingue la evaluación final de las lecciones
            self.marca = QGraphicsSimpleTextItem("★", self)
            fuente = self.marca.font()
            fuente.setPixelSize(int(radio))
            self.marca.setFont(fuente)
            self.marca.setBrush(QBrush(QColor(C.TEXTO_SOBRE_ACENTO)))
            rect = self.marca.boundingRect()
            self.marca.setPos(-rect.width() / 2, -rect.height() / 2)
            # Los clics pasan a través de la estrella hasta el nodo
            self.marca.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        # Texto/etiqueta del nodo
        self.texto = QGraphicsTextItem(titulo)
        self.texto.setDefaultTextColor(QColor(C.TEXTO))
        self.texto.setHtml(
            f"""
            <div style="
                background-color: {C.SUPERFICIE};
                padding: 6px 10px;
                color: {C.TEXTO};
            ">
                {titulo}
            </div>
            """
        )
        self.texto.setZValue(2)
        self.texto.hide()

    def mousePressEvent(self, event):
        if not self.habilitado:
            # Nodo gris: se ignora el clic por completo
            event.accept()
            return
        self.panel_derecho.nodo_seleccionado(self)
        super().mousePressEvent(event)


# ── Panel izquierdo (info del curso) ─────────────────────────────────────────

class PanelIzquierdo(QWidget):
    def __init__(self, curso):
        super().__init__()
        self.curso = curso
        self.iniciar_ui()

    def iniciar_ui(self):
        if isinstance(self.curso, CursoModel):
            titulo = self.curso.titulo
            descripcion = self.curso.descripcion
        else:
            titulo = self.curso.get("titulo", "")
            descripcion = self.curso.get("descripcion", "")

        tarjeta(self)
        self.setMinimumWidth(220)
        self.setMaximumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 22, 20, 20)
        layout.setSpacing(10)

        self.etiqueta = QLabel("CURSO")
        rol(self.etiqueta, "seccion")

        self.titulo = QLabel(titulo)
        self.titulo.setWordWrap(True)
        self.titulo.setStyleSheet(f"font-size: {fs(18)}px; font-weight: 600;")

        self.descripcion = QLabel(descripcion)
        self.descripcion.setWordWrap(True)
        self.descripcion.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        rol(self.descripcion, "descripcion")

        layout.addWidget(self.etiqueta)
        layout.addWidget(self.titulo)
        layout.addWidget(self.descripcion)
        layout.addStretch(1)


# ── Panel derecho (mapa de nodos) ─────────────────────────────────────────────

class PanelDerecho(QGraphicsView):
    # Se emite cada vez que el usuario completa una lección
    leccion_completada = pyqtSignal()
    # Se emite cada vez que se registra un intento de la evaluación final
    examen_actualizado = pyqtSignal()

    def __init__(self, lecciones: list[dict], db=None, curso_id=None):
        super().__init__()
        # Se normalizan los estados: anteriores = verde, actual = azul, resto = gris
        self.lecciones = self._normalizar_estados(lecciones)
        self.cantidad = len(lecciones)
        self.db = db
        self.curso_id = curso_id
        self._estado_por_id: dict[int, str] = {}

        self.escena = QGraphicsScene(self)
        self.setScene(self.escena)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.setGeometry(100, 100, 600, 600)
        self.setWindowTitle("Nodos Circulares en PyQt6")

        self.nodo_activo: NodoCircular | None = None
        self.nodos: list[NodoCircular] = []

        # Referencia a ventanas de lección abiertas (evita que el GC las destruya)
        self._ventanas_leccion: list = []
        # Worker activo
        self._worker: GenerarLeccionWorker | None = None
        # Diálogo de progreso
        self._progreso: QProgressDialog | None = None
        # Ventana de la evaluación final (solo se permite una abierta)
        self._ventana_examen = None

        self.crear_camino_nodos()

        # Los nodos se pintan con colores fijos al crearlos: se redibujan
        # cuando cambia el tema.
        al_cambiar_tema(self._al_cambiar_tema)

    def _al_cambiar_tema(self, _nombre: str = ""):
        self.crear_camino_nodos()

    @staticmethod
    def _normalizar_estados(lecciones: list[dict]) -> list[dict]:
        """
        Aplica la regla de progreso (lista ordenada de la primera a la última):
          - antes de la lección actual   -> "completed" (verde, habilitada)
          - la lección actual            -> "current"   (azul, habilitada)
          - después de la lección actual -> "locked"    (gris, bloqueada)
        La actual es la marcada como "current"; si no hay ninguna, la primera
        que no esté completada. Si todas están completadas, no hay actual.
        """
        copia = [dict(le) for le in lecciones]

        indice_actual = next(
            (i for i, le in enumerate(copia) if le.get("estado") == "current"), None
        )
        if indice_actual is None:
            indice_actual = next(
                (i for i, le in enumerate(copia) if le.get("estado") != "completed"),
                len(copia),
            )

        for i, le in enumerate(copia):
            if i < indice_actual:
                le["estado"] = "completed"
            elif i == indice_actual:
                le["estado"] = "current"
            else:
                le["estado"] = "locked"
        return copia

    def crear_camino_nodos(self):
        self.escena.clear()
        self.nodos.clear()
        self.nodo_activo = None
        self._estado_por_id = {
            le["id"]: le["estado"] for le in self.lecciones if le.get("id") is not None
        }

        radio_nodo = 25
        centro_x = 250
        inicio_y = 80
        separacion_y = 150
        rango_desviacion_x = 80

        radio_examen = 32

        anterior = None  # (x, y) del nodo previo, para dibujar el camino

        # La evaluación final es el último nodo del camino (queda arriba del todo)
        entradas = list(self.lecciones)
        if self.db is not None and self.curso_id is not None and self.lecciones:
            entradas.append({
                "id": None,
                "titulo": "Evaluación final",
                "estado": self._estado_examen(),
                "es_examen": True,
            })

        for i, leccion in enumerate(entradas[::-1]):
            y = inicio_y + (i * separacion_y)
            # Semilla fija por nodo: el camino no "salta" al redibujarlo
            # cuando se completa una lección.
            rng = random.Random(f"{self.curso_id}-{i}")
            desviacion_x = rng.randint(-rango_desviacion_x, rango_desviacion_x)
            x = centro_x + desviacion_x

            if anterior is not None:
                linea = self.escena.addLine(
                    anterior[0], anterior[1], x, y,
                    QPen(QColor(C.BORDE), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap),
                )
                linea.setZValue(0)
            anterior = (x, y)

            estado = leccion.get("estado", "locked")
            titulo = leccion.get("titulo", "")
            leccion_id = leccion.get("id")
            es_examen = leccion.get("es_examen", False)
            radio = radio_examen if es_examen else radio_nodo

            nodo = NodoCircular(
                self, x, y, radio, estado, titulo,
                leccion_id=leccion_id, es_examen=es_examen,
            )

            self.nodos.append(nodo)
            self.escena.addItem(nodo)
            self.escena.addItem(nodo.texto)
            nodo.texto.setPos(x + radio + 15, y - 15)

    def _estado_examen(self) -> str:
        """
        locked    -> faltan lecciones por completar
        current   -> todas completadas, examen sin aprobar
        completed -> examen aprobado (curso terminado)
        """
        if not all(le.get("estado") == "completed" for le in self.lecciones):
            return "locked"
        return "completed" if self.db.examen_aprobado(self.curso_id) else "current"

    def nodo_seleccionado(self, nodo: NodoCircular):
        # Defensa extra: una lección bloqueada nunca se abre
        if not nodo.habilitado:
            return

        # Actualizar etiqueta visible
        if self.nodo_activo is nodo:
            # Si hace doble clic en el mismo nodo, abrir la lección igualmente
            self._abrir_leccion(nodo)
            return

        if self.nodo_activo:
            self.nodo_activo.texto.hide()

        self.nodo_activo = nodo

        if self.nodo_activo:
            self.nodo_activo.texto.show()

        # Abrir la lección al seleccionar el nodo
        self._abrir_leccion(nodo)

    def _abrir_leccion(self, nodo: NodoCircular):
        """Abre la lección: carga desde BD o genera con IA si no existe."""
        leccion_id = nodo.leccion_id

        if not nodo.habilitado:
            return

        if nodo.es_examen:
            self._abrir_examen()
            return

        if leccion_id is None or self.db is None:
            QMessageBox.warning(
                self,
                "Sin datos",
                "Esta lección no tiene ID asociado en la base de datos.",
            )
            return

        # ¿Ya existe contenido en BD?
        if self.db.leccion_tiene_contenido(leccion_id):
            leccion_model = self.db.obtener_contenido_leccion(leccion_id)
            if leccion_model:
                self._mostrar_leccion(leccion_model)
                return

        # No existe → generar con IA
        self._generar_leccion(leccion_id)

    def _generar_leccion(self, leccion_id: int):
        """Lanza el worker para generar la lección con la IA."""
        if self._worker and self._worker.isRunning():
            QMessageBox.information(
                self, "Generando", "Ya hay una lección generándose, espera un momento."
            )
            return

        
        self._mostrar_progreso("Generando lección con IA…")

        self._worker = GenerarLeccionWorker(leccion_id, self.db)
        self._worker.terminado.connect(self._on_leccion_generada)
        self._worker.error.connect(self._on_error_generacion)
        self._worker.start()

    def _mostrar_progreso(self, texto: str):
        """Muestra el diálogo de espera mientras la IA trabaja en segundo plano."""
        self._progreso = QProgressDialog(
            texto, None, 0, 0, self
        )
        self._progreso.setWindowTitle("Por favor espera")
        self._progreso.setWindowModality(Qt.WindowModality.WindowModal)
        self._progreso.setCancelButton(None)
        self._progreso.setMinimumDuration(0)

        # El aspecto del diálogo de progreso vive en la hoja global (theme.py)
        self._progreso.show()

    def _cerrar_progreso(self):
        if self._progreso:
            self._progreso.close()
            self._progreso = None

    def _on_leccion_generada(self, leccion_model):
        if self._progreso:
            self._progreso.close()
            self._progreso = None

        if leccion_model:
            self._mostrar_leccion(leccion_model)
        else:
            QMessageBox.critical(self, "Error", "No se pudo generar el contenido de la lección.")

    def _on_error_generacion(self, mensaje: str):
        if self._progreso:
            self._progreso.close()
            self._progreso = None
        QMessageBox.critical(self, "Error al generar lección", mensaje)

    def _mostrar_leccion(self, leccion_model):
        """Instancia y muestra la ventana LeccionMenu."""
        from ui.cursos.leccion.leccion import LeccionMenu

        estado = self._estado_por_id.get(leccion_model.id, "locked")
        if estado == "locked":
            return  # nunca se muestra una lección bloqueada

        ventana = LeccionMenu(
            leccion_model,
            estado=estado,
            on_completar=self._completar_leccion,
        )
        ventana.setWindowTitle(f"Lección: {leccion_model.titulo}")
        ventana.show()
        # Guardamos referencia para que Qt no destruya la ventana
        self._ventanas_leccion.append(ventana)

    def _completar_leccion(self, leccion_id) -> bool:
        """
        Marca la lección actual como completada, desbloquea la siguiente
        y redibuja el mapa. Devuelve True si se completó.
        """
        indice = next(
            (i for i, le in enumerate(self.lecciones) if le.get("id") == leccion_id),
            None,
        )
        if indice is None or self.lecciones[indice]["estado"] != "current":
            return False

        # Persistir en la BD (si hay una)
        if self.db is not None and leccion_id is not None:
            if not self.db.completar_leccion(leccion_id):
                return False

        # Actualizar el estado en memoria: esta pasa a verde y la siguiente a azul
        self.lecciones[indice]["estado"] = "completed"
        if indice + 1 < len(self.lecciones):
            self.lecciones[indice + 1]["estado"] = "current"
        self.lecciones = self._normalizar_estados(self.lecciones)

        self.crear_camino_nodos()
        self.leccion_completada.emit()

        if all(le["estado"] == "completed" for le in self.lecciones):
            QMessageBox.information(
                self,
                "¡Lecciones completadas!",
                "Terminaste todas las lecciones. Ya puedes rendir la evaluación final "
                "(el nodo con la estrella, al final del camino) para completar el curso.",
            )
        return True

    # ── Evaluación final ──────────────────────────────────────────────────────

    def _abrir_examen(self):
        """Abre la evaluación final: la carga desde BD o, la primera vez, la genera con IA."""
        if self.db is None or self.curso_id is None:
            return

        if self._ventana_examen is not None and self._ventana_examen.isVisible():
            self._ventana_examen.raise_()
            self._ventana_examen.activateWindow()
            return

        examen = self.db.obtener_examen(self.curso_id)
        if examen is not None:
            self._mostrar_examen(examen)
        else:
            self._generar_examen()

    def _generar_examen(self):
        if self._worker and self._worker.isRunning():
            QMessageBox.information(
                self, "Generando", "Ya hay algo generándose, espera un momento."
            )
            return

        self._mostrar_progreso("Generando la evaluación final con IA…")

        self._worker = GenerarExamenWorker(self.curso_id, self.db)
        self._worker.terminado.connect(self._on_examen_generado)
        self._worker.error.connect(self._on_error_examen)
        self._worker.start()

    def _on_examen_generado(self, examen):
        self._cerrar_progreso()
        if examen:
            self._mostrar_examen(examen)
        else:
            QMessageBox.critical(self, "Error", "No se pudo generar la evaluación final.")

    def _on_error_examen(self, mensaje: str):
        self._cerrar_progreso()
        QMessageBox.critical(self, "Error al generar la evaluación", mensaje)

    def _mostrar_examen(self, examen):
        from ui.cursos.examen.examen import ExamenMenu

        ventana = ExamenMenu(
            examen,
            estado=self.db.obtener_estado_examen(self.curso_id),
            on_finalizar=lambda resultado, examen_id=examen.id: self._finalizar_examen(
                examen_id, resultado
            ),
        )
        ventana.show()
        self._ventana_examen = ventana
        # Se cierra junto con el curso, igual que las lecciones
        self._ventanas_leccion.append(ventana)

    def _finalizar_examen(self, examen_id, resultado) -> bool:
        """Guarda el intento. Si se aprobó, el curso queda completado y se redibuja el mapa."""
        if not self.db.registrar_intento_examen(
            examen_id, resultado.aciertos, resultado.total, resultado.aprobado
        ):
            return False

        self.crear_camino_nodos()
        self.examen_actualizado.emit()
        return True

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.position().toPoint())
            if item is None and self.nodo_activo:
                self.nodo_activo.texto.hide()
                self.nodo_activo = None
        super().mousePressEvent(event)


# ── Ventana principal del curso ───────────────────────────────────────────────

class CursoMenu(QWidget):
    # Avisa a la ventana principal para que actualice el progreso del inicio
    progreso_cambiado = pyqtSignal()

    def __init__(self, curso, db=None):
        super().__init__()
        self.curso_model = _parsear_curso_para_ui(curso)
        self.curso_raw = curso
        self.titulo = self.curso_model.titulo if self.curso_model else ""
        self.db = db

        # Si no se pasa db, intentar instanciar uno por defecto
        if self.db is None:
            try:
                from services.database import BaseDatosProyecto
                self.db = BaseDatosProyecto("storage/sistema_estudios.db")
            except Exception:
                pass

        self.iniciar_ui()

    def iniciar_ui(self):
        self.setWindowTitle(f"Curso: {self.titulo}")
        self.setWindowIcon(QIcon(str(ruta_logo)))
        self.resize(860, 600)

        layout_principal = QHBoxLayout()
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(18)
        self.layout_izquierdo = PanelIzquierdo(self.curso_model)

        # Construir lista de lecciones para el panel derecho
        lecciones_para_ui: list[dict] = []
        for le in self.curso_model.lecciones:
            if isinstance(le, LeccionModel):
                lecciones_para_ui.append({
                    "id": le.id,
                    "titulo": le.titulo,
                    "estado": le.estado,
                })
            elif isinstance(le, dict):
                lecciones_para_ui.append(le)

        self.layout_derecho = PanelDerecho(
            lecciones_para_ui, db=self.db, curso_id=self.curso_model.id
        )
        self.layout_derecho.leccion_completada.connect(self.progreso_cambiado)
        self.layout_derecho.examen_actualizado.connect(self.progreso_cambiado)

        layout_principal.addWidget(self.layout_izquierdo, stretch=1)
        layout_principal.addWidget(self.layout_derecho, stretch=10)

        self.setLayout(layout_principal)

    def closeEvent(self, event):
        # Al cerrar el curso se cierran también las lecciones que abrió
        for ventana in self.layout_derecho._ventanas_leccion:
            ventana.close()
        super().closeEvent(event)


# ── Prueba standalone ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    curso_dict = {
        "id": 1,
        "titulo": "Matemáticas Derivadas",
        "descripcion": "Curso de cálculo diferencial",
        "lessons": [
            {"id": 1, "titulo": "Introducción", "estado": "completed"},
            {"id": 2, "titulo": "Límites", "estado": "current"},
            {"id": 3, "titulo": "Regla de la Cadena", "estado": "locked"},
        ],
    }

    from ui.theme import aplicar_tema

    app = QApplication(sys.argv)
    aplicar_tema(app)
    ventana = CursoMenu(curso_dict)
    ventana.show()
    sys.exit(app.exec())
