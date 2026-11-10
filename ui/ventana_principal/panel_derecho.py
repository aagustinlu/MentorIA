import sys
from pathlib import Path

from functools import lru_cache

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QStyledItemDelegate,
)
from PyQt6.QtGui import QCursor, QIcon, QPainter, QPixmap
from PyQt6.QtCore import (
    QByteArray,
    QRectF,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt6.QtSvg import QSvgRenderer

# Asegura que el proyecto raíz esté en sys.path para imports absolutos
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    
from ui.cursos.crear_curso_menu import CampoEntrada
from ui.theme import Colores as C, fs, gestor_tema, primario, rol
from services.database import BaseDatosProyecto


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
        
        
class PanelDerecho(QWidget):
    ALTO_FILA_CURSO = 48

    # Pide a la ventana principal que muestre la pantalla de un curso
    curso_solicitado = pyqtSignal(object)

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

        self.cargar_cursos()
        self._refrescar_progreso()

    def _mostrar_curso_menu(self, curso) -> bool:
        """Pide mostrar la pantalla del curso. Devuelve True si se pudo abrir."""
        try:
            self.curso_solicitado.emit(curso)
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