import sys
from functools import lru_cache

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
    QSizePolicy,
    QStyledItemDelegate,
)
from PyQt6.QtGui import QCursor, QIcon, QPainter, QPixmap
from PyQt6.QtCore import (
    QByteArray,
    QEvent,
    QRectF,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt6.QtSvg import QSvgRenderer

from .popup import Configuraciones
from .cursos.crear_curso_menu import CampoEntrada
from .theme import Colores as C, al_cambiar_tema, fs, gestor_tema, primario, rol, tarjeta
from services.database import BaseDatosProyecto

from .cursos.curso import CursoMenu


# Ícono de tacho dibujado como vector: se ve nítido a cualquier tamaño y no
# arrastra fondo de color como una captura.
_SVG_TACHO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 6h18"/>
  <path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/>
  <path d="M6 6l1 14a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-14"/>
  <path d="M10 11v6M14 11v6"/>
</svg>"""


@lru_cache(maxsize=None)
def icono_tacho(color: str, lado: int = 18) -> QIcon:
    renderer = QSvgRenderer(QByteArray(_SVG_TACHO.format(color=color).encode()))
    pixmap = QPixmap(lado * 2, lado * 2)      # 2x para pantallas de alta densidad
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, lado, lado))
    painter.end()
    return QIcon(pixmap)


class BotonTacho(QPushButton):
    """Botón con ícono de tacho: el círculo se marca solo al hacer hover.

    Tiene dos paletas (fondo claro / fondo oscuro) para que el ícono siempre se vea.
    """

    LADO = 32            # el botón es un cuadrado de LADO x LADO
    RADIO = 16           # LADO/2 = círculo; 8 = cuadrado de esquinas redondeadas
    ICONO = 16

    # fondo oscuro? -> (color en reposo, color al apuntar, RGB del fondo al apuntar)
    PALETAS = {
        False: ("#8f8579", "#c0564b", "192, 86, 75"),
        True: ("#d6cdc0", "#f0897c", "240, 137, 124"),
    }

    def __init__(self):
        super().__init__()
        self.setObjectName("btnEliminarIcono")
        self.setIconSize(QSize(self.ICONO, self.ICONO))
        self.setFixedSize(self.LADO, self.LADO)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Eliminar este curso")
        self._oscuro: bool | None = None
        self.usar_modo_oscuro(False)

    def usar_modo_oscuro(self, oscuro: bool):
        if oscuro == self._oscuro:
            return
        self._oscuro = oscuro
        self._reposo, self._hover, rgb = self.PALETAS[oscuro]
        self.setIcon(icono_tacho(self._reposo, self.ICONO))
        # Sin fondo ni borde en reposo; el círculo aparece solo al apuntar el botón
        self.setStyleSheet(
            "QPushButton#btnEliminarIcono {"
            " background: transparent;"
            " border: none;"
            f" border-radius: {self.RADIO}px;"
            " padding: 0; margin: 0; min-width: 0; min-height: 0; }"
            "QPushButton#btnEliminarIcono:hover {"
            f" background: rgba({rgb}, 40); }}"
        )

    def enterEvent(self, event):
        self.setIcon(icono_tacho(self._hover, self.ICONO))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(icono_tacho(self._reposo, self.ICONO))
        super().leaveEvent(event)

    def hideEvent(self, event):
        self.setIcon(icono_tacho(self._reposo, self.ICONO))
        super().hideEvent(event)


class FilaCurso(QWidget):
    """Fila de un curso: el título y un tacho que solo aparece con el mouse encima."""

    eliminar_pedido = pyqtSignal(int, str)   # id y título del curso

    MARGEN_IZQ = 14
    MARGEN_DER = 8

    def __init__(self, curso_id: int, titulo: str):
        super().__init__()
        self.curso_id = curso_id
        self.titulo = titulo
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._layout = QHBoxLayout(self)
        layout = self._layout
        layout.setContentsMargins(self.MARGEN_IZQ, 0, self.MARGEN_DER, 0)
        layout.setSpacing(8)

        etiqueta = QLabel(titulo)
        etiqueta.setStyleSheet(f"font-size: {fs(14)}px;")
        # Deja pasar el clic para que seleccionar la fila siga abriendo el curso
        etiqueta.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.btn_eliminar = BotonTacho()
        # Oculto por defecto, pero conservando su lugar para que el título no salte
        politica = self.btn_eliminar.sizePolicy()
        politica.setRetainSizeWhenHidden(True)
        self.btn_eliminar.setSizePolicy(politica)
        self.btn_eliminar.hide()
        self.btn_eliminar.clicked.connect(
            lambda _checked=False: self.eliminar_pedido.emit(self.curso_id, self.titulo)
        )

        layout.addWidget(etiqueta, 1)
        layout.addWidget(self.btn_eliminar)

    def enterEvent(self, event):
        self._mostrar_tacho(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.btn_eliminar.setVisible(False)
        super().leaveEvent(event)

    def ajustar_margenes(self, extra_izq: int, extra_der: int):
        """Suma margen interno para que el contenido no cambie de lugar cuando la
        fila se agranda hasta cubrir todo el rectángulo del item."""
        izq = self.MARGEN_IZQ + max(0, extra_izq)
        der = self.MARGEN_DER + max(0, extra_der)
        if (izq, der) != (self._layout.contentsMargins().left(),
                          self._layout.contentsMargins().right()):
            self._layout.setContentsMargins(izq, 0, der, 0)

    def sincronizar_hover(self):
        """Muestra el tacho solo si el mouse realmente está sobre la fila."""
        pos = self.mapFromGlobal(QCursor.pos())
        self._mostrar_tacho(self.rect().contains(pos))

    def _mostrar_tacho(self, visible: bool):
        if visible:
            self.btn_eliminar.usar_modo_oscuro(gestor_tema().es_oscuro)
        self.btn_eliminar.setVisible(visible)


class DelegadoFilaCurso(QStyledItemDelegate):
    """Hace que la fila ocupe TODO el rectángulo del item.

    Por defecto Qt acota el widget de la fila al área del texto (descontando el
    padding/margen del estilo), mientras que el resaltado del item sí llega hasta
    los bordes: ahí el mouse estaba sobre el item pero no sobre la fila y el tacho
    no aparecía. Con la fila cubriendo todo el item, el hover funciona hasta los
    extremos.
    """

    def updateEditorGeometry(self, editor, option, index):
        super().updateEditorGeometry(editor, option, index)   # rect del texto
        if not isinstance(editor, FilaCurso):
            return
        interior = editor.geometry()
        total = option.rect
        editor.ajustar_margenes(
            interior.left() - total.left(),
            total.right() - interior.right(),
        )
        editor.setGeometry(total)


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
        
        tarjeta(self)
        self.setFixedWidth(250)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 22, 20, 20)
        layout.setSpacing(6)

        self.nombre_label = QLabel(f"<b>{nombre}</b>")
        self.nombre_label.setStyleSheet(f"font-size: {fs(18)}px;")
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
        self.lista_cursos.setItemDelegate(DelegadoFilaCurso(self.lista_cursos))
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
        fila = FilaCurso(curso_id, titulo)
        fila.eliminar_pedido.connect(
            lambda cid, t, f=fila: self._confirmar_eliminar_curso(cid, t, f)
        )
        return fila


    def _confirmar_eliminar_curso(
        self, curso_id: int, titulo: str, fila: FilaCurso | None = None
    ):
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
            # Con el diálogo abierto el mouse pudo salir de la fila
            if fila is not None:
                fila.sincronizar_hover()
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

        if curso is not None:
            curso_bd = self.db.obtener_curso(curso.id) if curso.id else None
            self._mostrar_curso_menu(curso_bd or curso)


class VentanaPrincipal(QWidget):
    ANCHO_LOGO = 180   # px lógicos; el panel izquierdo mide 250

    def __init__(self, nombre: str):
        super().__init__()

        self.nombre = nombre

        self.db = BaseDatosProyecto(
            "storage/sistema_estudios.db"
        )

        self.iniciar_ui()

    def iniciar_ui(self):
        self.setWindowTitle("MentorIA")
        self.setWindowIcon(QIcon("./files/img/Mentoria Logo.png"))
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

        # Generar el lado izquierdo del layout principal
        # > Se crea el logo: proporcional (sin setScaledContents) y centrado
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        logo = QPixmap("./files/img/Mentoria Logotipo.png")
        if not logo.isNull():
            dpr = self.devicePixelRatioF()
            logo = logo.scaledToWidth(
                int(self.ANCHO_LOGO * dpr), Qt.TransformationMode.SmoothTransformation
            )
            logo.setDevicePixelRatio(dpr)
            self.logo_label.setPixmap(logo)

        self.panel_izquierdo = PanelIzquierdo(
            nombre_bd,
            cursos_completados,
            cursos_pendientes,
            self.db,
            stats.get("lecciones_completadas", 0),
        )

        self.layout_izquierdo = QVBoxLayout()
        self.layout_izquierdo.addWidget(
            self.logo_label, 0, Qt.AlignmentFlag.AlignHCenter
        )
        self.layout_izquierdo.addWidget(self.panel_izquierdo, 1)

        # Generar el lado derecho del layout principal
        self.panel_derecho = PanelDerecho(self.db)
        self.panel_derecho.cargar_cursos()
        
        # Generar el layout completo
        layout_principal = QHBoxLayout()
        layout_principal.setContentsMargins(22, 22, 22, 22)
        layout_principal.setSpacing(20)
        
        layout_principal.addLayout(
            self.layout_izquierdo,
        )

        layout_principal.addWidget(
            self.panel_derecho,
            1
        )

        self.setLayout(layout_principal)

    def event(self, e):
        # Al volver a esta ventana (p. ej. tras cerrar una lección) se actualiza el progreso
        if e.type() == QEvent.Type.WindowActivate:
            self.panel_izquierdo.refrescar_progreso()
        return super().event(e)

    def closeEvent(self, event):
        # Al cerrar la ventana principal se cierran también curso y lecciones abiertos
        QApplication.closeAllWindows()
        super().closeEvent(event)


if __name__ == "__main__":
    from .theme import aplicar_tema

    app = QApplication(sys.argv)
    aplicar_tema(app)

    ventana = VentanaPrincipal("Ejemplo")
    ventana.show()

    sys.exit(app.exec())