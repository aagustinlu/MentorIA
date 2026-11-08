import sys
import time

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)

from PyQt6.QtCore import QEvent, QSize, Qt, QThread, pyqtSignal

from .popup import Configuraciones
from .cursos.crear_curso_menu import CampoEntrada
from .theme import Colores as C, al_cambiar_tema, primario, rol, tarjeta
from services.database import BaseDatosProyecto

from .cursos.curso import CursoMenu


class ConsultarSaldoWorker(QThread):
    """Consulta el saldo de Groq en segundo plano (es una llamada de red)."""

    resultado = pyqtSignal(object)   # SaldoGroq o None

    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key

    def run(self):
        try:
            from services.ai_service import GestorDeIA

            self.resultado.emit(GestorDeIA(api_key=self.api_key).consultar_saldo())
        except Exception as e:
            print(f"[ConsultarSaldoWorker] {e}")
            self.resultado.emit(None)


def _fmt(n) -> str:
    """12345 -> '12.345'"""
    return "—" if n is None else f"{n:,}".replace(",", ".")


class PanelIzquierdo(QWidget):
    def __init__(
        self,
        nombre: str,
        cursos_completados: int,
        cursos_pendientes: int,
        db: BaseDatosProyecto | None = None,
        lecciones_completadas: int = 0,
    ):
        super().__init__()

        self.db = db
        self._worker: ConsultarSaldoWorker | None = None

        tarjeta(self)
        self.setFixedWidth(230)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 22, 20, 20)
        layout.setSpacing(6)

        self.nombre_label = QLabel(f"<b>{nombre}</b>")
        self.nombre_label.setStyleSheet("font-size: 18px;")
        self.nombre_label.setWordWrap(True)

        self.subtitulo = QLabel("Tu espacio de estudio")
        rol(self.subtitulo, "subtitulo")

        self.titulo_progreso = QLabel("PROGRESO")
        rol(self.titulo_progreso, "seccion")

        self.texto_cursos_completados = QLabel()
        self.texto_cursos_pendientes = QLabel()
        self.texto_lecciones_completadas = QLabel()
        self.mostrar_progreso(
            cursos_completados, cursos_pendientes, lecciones_completadas
        )

        self.titulo_saldo = QLabel("DISPONIBLE")
        rol(self.titulo_saldo, "seccion")

        self.tokens_disponible = QLabel("Tokens este minuto: …")
        rol(self.tokens_disponible, "subtitulo")

        self.solicitudes_disponibles = QLabel("Solicitudes hoy: …")
        rol(self.solicitudes_disponibles, "subtitulo")

        self.btn_config = QPushButton("Configuración")
        self.btn_config.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_config.clicked.connect(self.mostrar_confg)

        # Los puntos de color del progreso van dentro de HTML: se regeneran
        # al cambiar de tema.
        al_cambiar_tema(self._al_cambiar_tema)

        layout.addWidget(self.nombre_label)
        layout.addWidget(self.subtitulo)
        layout.addSpacing(22)
        layout.addWidget(self.titulo_progreso)
        layout.addSpacing(2)
        layout.addWidget(self.texto_cursos_completados)
        layout.addWidget(self.texto_cursos_pendientes)
        layout.addWidget(self.texto_lecciones_completadas)
        layout.addSpacing(18)
        layout.addWidget(self.titulo_saldo)
        layout.addSpacing(2)
        layout.addWidget(self.tokens_disponible)
        layout.addWidget(self.solicitudes_disponibles)
        layout.addStretch()

        layout.addWidget(self.btn_config)

        self.setLayout(layout)

    @staticmethod
    def _cantidad(n: int, singular: str, plural: str) -> str:
        return f"{n} {singular if n == 1 else plural}"

    def _al_cambiar_tema(self, _nombre: str = ""):
        self.mostrar_progreso(*self._ultimo_progreso)

    def mostrar_progreso(
        self, cursos_completados: int, cursos_pendientes: int, lecciones_completadas: int
    ):
        self._ultimo_progreso = (
            cursos_completados, cursos_pendientes, lecciones_completadas
        )
        self.texto_cursos_completados.setText(self._fila(
            C.COMPLETADO,
            self._cantidad(cursos_completados, "curso completado", "cursos completados"),
        ))
        self.texto_cursos_pendientes.setText(self._fila(
            C.PENDIENTE,
            self._cantidad(cursos_pendientes, "curso pendiente", "cursos pendientes"),
        ))

    def refrescar_progreso(self):
        """Vuelve a leer el progreso desde la BD y actualiza los contadores."""
        if self.db is None:
            return
        stats = self.db.contar_progreso_cursos()
        self.mostrar_progreso(
            stats.get("cursos_completados", 0),
            stats.get("cursos_pendientes", 0),
            stats.get("lecciones_completadas", 0),
        )

    def actualizar_saldo(self):
        """Pide el saldo a Groq sin bloquear la UI. Seguro de llamar varias veces."""
        if self.db is None or (self._worker and self._worker.isRunning()):
            return

        perfil = self.db.obtener_perfil()
        api_key = perfil[1] if perfil else None
        if not api_key:
            return

        self._worker = ConsultarSaldoWorker(api_key)
        self._worker.resultado.connect(self._mostrar_saldo)
        self._worker.start()

    def _mostrar_saldo(self, saldo):
        if saldo is None:
            self.tokens_disponible.setText("Saldo no disponible")
            self.solicitudes_disponibles.setText("")
            return

        # Si Groq envía el límite diario de tokens se muestra; si no, el del minuto
        if saldo.tokens_dia is not None:
            self.tokens_disponible.setText(f"Tokens hoy: {_fmt(saldo.tokens_dia)}")
        else:
            self.tokens_disponible.setText(f"Tokens este minuto: {_fmt(saldo.tokens_minuto)}")
        self.solicitudes_disponibles.setText(f"Solicitudes hoy: {_fmt(saldo.solicitudes_dia)}")

    @staticmethod
    def _fila(color: str, texto: str) -> str:
        return f"<span style='color:{color};'>●</span>&nbsp;&nbsp;{texto}"

    def mostrar_confg(self):
        dialog = Configuraciones(self)
        dialog.exec()


class PanelDerecho(QWidget):
    ALTO_FILA_CURSO = 48

    def __init__(self, db: BaseDatosProyecto):
        super().__init__()

        self.db = db

        layout_principal = QVBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(14)

        layout_superior = QHBoxLayout()

        self.titulo = QLabel("Mis cursos")
        rol(self.titulo, "titulo")

        self.btn_crear = QPushButton("+  Nuevo curso")
        primario(self.btn_crear)
        self.btn_crear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_crear.clicked.connect(self.abrir_crear_curso)

        self.lista_cursos = QListWidget()
        self.lista_cursos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lista_cursos.itemSelectionChanged.connect(
            self._on_seleccion_curso
        )

        layout_superior.addWidget(self.titulo)
        layout_superior.addStretch()
        layout_superior.addWidget(self.btn_crear)

        layout_principal.addLayout(layout_superior)
        layout_principal.addWidget(self.lista_cursos)

        self.setLayout(layout_principal)

    def cargar_cursos(self):
        self.lista_cursos.clear()

        cursos = self.db.obtener_cursos_usuario()

        for curso in cursos:
            titulo = curso.get("titulo", "(sin título)")
            curso_id = curso.get("id")

            item = QListWidgetItem()

            # Guardamos el id del curso dentro del item
            item.setData(
                Qt.ItemDataRole.UserRole,
                curso_id
            )

            self.lista_cursos.addItem(item)

            # La fila lleva el título y un botón para eliminar el curso
            fila = self._crear_fila_curso(curso_id, titulo)
            item.setSizeHint(QSize(0, self.ALTO_FILA_CURSO))
            self.lista_cursos.setItemWidget(item, fila)

    def _crear_fila_curso(self, curso_id: int, titulo: str) -> QWidget:
        fila = QWidget()
        fila.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QHBoxLayout(fila)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(8)

        etiqueta = QLabel(titulo)
        etiqueta.setStyleSheet("font-size: 14px;")
        # Deja pasar el clic para que seleccionar la fila siga abriendo el curso
        etiqueta.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        btn_eliminar = QPushButton("Eliminar")
        btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eliminar.setToolTip("Eliminar este curso")
        # Estilo en la hoja global (ver theme.py): sigue al tema solo
        btn_eliminar.setObjectName("btnEliminarCurso")
        btn_eliminar.clicked.connect(
            lambda _checked=False, cid=curso_id, t=titulo: self._confirmar_eliminar_curso(cid, t)
        )

        layout.addWidget(etiqueta, 1)
        layout.addWidget(btn_eliminar)
        return fila

    def _confirmar_eliminar_curso(self, curso_id: int, titulo: str):
        caja = QMessageBox(self)
        caja.setIcon(QMessageBox.Icon.Warning)
        caja.setWindowTitle("Eliminar curso")
        caja.setText(f"¿Eliminar el curso «{titulo}»?")
        caja.setInformativeText(
            "Se borrarán también sus lecciones y tu progreso. "
            "Esta acción no se puede deshacer."
        )
        btn_eliminar = caja.addButton("Eliminar", QMessageBox.ButtonRole.DestructiveRole)
        btn_cancelar = caja.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        caja.setDefaultButton(btn_cancelar)
        caja.setEscapeButton(btn_cancelar)
        caja.exec()

        if caja.clickedButton() is not btn_eliminar:
            return

        self._eliminar_curso(curso_id)

    def _eliminar_curso(self, curso_id: int):
        if not self.db.eliminar_curso(curso_id):
            QMessageBox.critical(
                self, "Error", "No se pudo eliminar el curso. Intenta de nuevo."
            )
            return

        # Si el curso eliminado estaba abierto, se cierra junto con sus lecciones
        abierto = getattr(self, "_curso_menu_abierto", None)
        if abierto is not None and getattr(abierto.curso_model, "id", None) == curso_id:
            abierto.close()
            self._curso_menu_abierto = None

        self.cargar_cursos()
        self._refrescar_progreso()

    def _mostrar_curso_menu(self, curso) -> bool:
        """Abre la ventana del curso. Devuelve True si se abrió bien."""
        try:
            # * Guardar referencia para evitar que el widget se destruya por GC
            self._curso_menu_abierto = CursoMenu(curso)
            # Cada lección completada actualiza los contadores del inicio
            self._curso_menu_abierto.progreso_cambiado.connect(self._refrescar_progreso)
            self._curso_menu_abierto.show()
            return True

        except Exception as e:
            import traceback
            print("ERROR al abrir curso:", e)
            traceback.print_exc()
            return False

    def _refrescar_progreso(self):
        panel = getattr(self.window(), "panel_izquierdo", None)
        if panel is not None:
            panel.refrescar_progreso()

    def _on_seleccion_curso(self):

        item = self.lista_cursos.currentItem()

        # 1. En caso que no haya un item seleccionado no se ejecutara nada
        if not item:
            return

        # 2. Contrariamente, si hay un item seleccionado, se abre el menu

        curso_id = item.data(
            Qt.ItemDataRole.UserRole
        )

        print(f"Curso seleccionado: {curso_id}")

        curso = self.db.obtener_curso(curso_id)

        if not self._mostrar_curso_menu(curso):
            return

        # 3. Una vez que se abrio el menu exitosamente, quitamos la seleccion del menu por si quiere abrirlo denuevo

        # * Bloqueamos las señales para que no se ejecute 2 veces la accion

        self.lista_cursos.blockSignals(True)

        # * Quitamos la seleccion
        self.lista_cursos.clearSelection() # Quita el color de la seleccion
        self.lista_cursos.setCurrentItem(None) # Quita el foco del item actual

        # * Activamos la señal denuevo

        self.lista_cursos.blockSignals(False)

        # Más adelante:
        # lecciones = self.db.obtener_lecciones_curso(curso_id)
        # abrir vista del curso

    def abrir_crear_curso(self):
        popup_menu_curso = CampoEntrada(self.window())
        popup_menu_curso.exec()

        # Recargar la lista al cerrar el popup
        self.cargar_cursos()

        # Un curso nuevo cuenta como pendiente
        self._refrescar_progreso()

        # Si el popup se cerró porque el curso se generó, lo abrimos aquí.
        # Se relee desde la BD para que las lecciones traigan su id
        # (necesario para poder abrirlas desde el mapa de nodos).
        curso = popup_menu_curso.curso_creado

        # La generación gastó tokens: actualizamos el saldo mostrado
        panel = getattr(self.window(), "panel_izquierdo", None)
        if panel is not None:
            panel.actualizar_saldo()

        if curso is not None:
            curso_bd = self.db.obtener_curso(curso.id) if curso.id else None
            self._mostrar_curso_menu(curso_bd or curso)


class VentanaPrincipal(QWidget):
    def __init__(self, nombre: str):
        super().__init__()

        self.nombre = nombre

        self.db = BaseDatosProyecto(
            "storage/sistema_estudios.db"
        )

        self.iniciar_ui()

    def iniciar_ui(self):
        self.setWindowTitle("AsistIA")
        self.resize(820, 540)

        perfil = self.db.obtener_perfil()

        if perfil:
            nombre_bd = perfil[0]
        else:
            nombre_bd = self.nombre

        stats = self.db.contar_progreso_cursos()

        cursos_completados = stats.get(
            "cursos_completados", 0
        )

        cursos_pendientes = stats.get(
            "cursos_pendientes", 0
        )

        layout_principal = QHBoxLayout()
        layout_principal.setContentsMargins(22, 22, 22, 22)
        layout_principal.setSpacing(20)

        self.panel_izquierdo = PanelIzquierdo(
            nombre_bd,
            cursos_completados,
            cursos_pendientes,
            self.db,
            stats.get("lecciones_completadas", 0),
        )

        self.panel_derecho = PanelDerecho(self.db)
        self.panel_derecho.cargar_cursos()

        layout_principal.addWidget(
            self.panel_izquierdo,
        )

        layout_principal.addWidget(
            self.panel_derecho,
            1
        )

        self.setLayout(layout_principal)

        # Para no consultar a Groq cada vez que la ventana recupera el foco
        self._ultimo_saldo = 0.0

    def showEvent(self, event):
        super().showEvent(event)
        self._refrescar_saldo(minimo_segundos=0)

    def event(self, e):
        # Al volver a esta ventana (p. ej. tras cerrar una lección) se refresca el saldo
        if e.type() == QEvent.Type.WindowActivate:
            self._refrescar_saldo(minimo_segundos=30)
            self.panel_izquierdo.refrescar_progreso()
        return super().event(e)

    def _refrescar_saldo(self, minimo_segundos: int):
        ahora = time.monotonic()
        if ahora - self._ultimo_saldo >= minimo_segundos:
            self._ultimo_saldo = ahora
            self.panel_izquierdo.actualizar_saldo()

    def closeEvent(self, event):
        # Al cerrar la ventana principal se cierran también curso y lecciones abiertos
        QApplication.closeAllWindows()

        # Evita destruir el hilo del saldo si aún está consultando
        worker = self.panel_izquierdo._worker
        if worker is not None and worker.isRunning():
            worker.wait(3000)

        super().closeEvent(event)


if __name__ == "__main__":
    from .theme import aplicar_tema

    app = QApplication(sys.argv)
    aplicar_tema(app)

    ventana = VentanaPrincipal("Ejemplo")
    ventana.show()

    sys.exit(app.exec())