import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
    QLabel,
    QSizePolicy,
)
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import (
    QEvent,
    Qt,
    pyqtSignal,
)

# Asegura que el proyecto raíz esté en sys.path para imports absolutos
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.database import BaseDatosProyecto
from services.resolver_rutas import resolver_ruta_recurso
from ui.ventana_principal.panel_izquierdo import PanelIzquierdo
from ui.ventana_principal.panel_derecho import PanelDerecho
from ui.navegacion import BarraNavegacion
from ui.cursos.curso import CursoMenu
from ui.start import PantallaRegistro

class PantallaInicio(QWidget):
    """Pantalla de inicio: panel con tu progreso y la lista de cursos."""

    ANCHO_LOGO = 180   # px lógicos; el panel izquierdo mide 250

    def __init__(self, nombre: str, db: BaseDatosProyecto):
        super().__init__()
        self.nombre = nombre
        self.db = db
        self.iniciar_ui()

    def iniciar_ui(self):
        perfil = self.db.obtener_perfil()
        nombre_bd = perfil[0] if perfil else self.nombre

        stats = self.db.contar_progreso_cursos()
        cursos_completados = stats.get("cursos_completados", 0)
        cursos_pendientes = stats.get("cursos_pendientes", 0)


        self.panel_izquierdo = PanelIzquierdo(
            nombre_bd,
            cursos_completados,
            cursos_pendientes,
            self.db,
            stats.get("lecciones_completadas", 0),
        )

        # Generar el lado derecho del layout principal
        self.panel_derecho = PanelDerecho(self.db)
        self.panel_derecho.cargar_cursos()

        # Generar el layout completo
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(20)
        layout_principal.addWidget(self.panel_izquierdo)
        layout_principal.addWidget(self.panel_derecho, 1)

    def refrescar(self):
        """Se llama al volver al inicio desde cualquier otra pantalla."""
        self.panel_izquierdo.refrescar_progreso()


class VentanaPrincipal(QWidget):
    """Única ventana de la aplicación.

    Las pantallas se apilan dentro de un QStackedWidget:

        registro (solo la primera vez)  ·  inicio  ·  curso › lección / examen

    Salvo en el inicio, arriba se muestra la barra de navegación con el botón
    «Volver al inicio».
    """
    
    TAMANO_START = (650, 480)
    TAMANO_INICIO = (920, 640)

    def __init__(self, nombre: str | None = None):
        super().__init__()

        self.db = BaseDatosProyecto("storage/sistema_estudios.db")
        self.pantalla_inicio: PantallaInicio | None = None
        self.panel_izquierdo = None   # panel de progreso del inicio (lo lee el panel de cursos)
        self.pantalla_registro: PantallaRegistro | None = None

        # Pantallas apiladas sobre el inicio: [(widget, título para las migas)]
        self._pantallas: list[tuple[QWidget, str]] = []

        self.iniciar_ui()

        perfil = self.db.obtener_perfil()
        if perfil:
            self._mostrar_inicio(perfil[0])
        elif nombre:
            self._mostrar_inicio(nombre)
        else:
            self._mostrar_registro()

    # ── Construcción ──────────────────────────────────────────────────────

    def iniciar_ui(self):
        self.setWindowTitle("MentorIA")
        ruta_icono = resolver_ruta_recurso("files/img/Mentoria Logo.png")
        self.setWindowIcon(QIcon(ruta_icono))
        self.resize(*self.TAMANO_INICIO)
        self.setMinimumSize(600, 450)

        self.barra = BarraNavegacion()
        self.barra.inicio_solicitado.connect(self.ir_a_inicio)
        self.barra.volver_solicitado.connect(self.volver)
        self.barra.hide()

        self.pila = QStackedWidget()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)
        layout.addWidget(self.barra)
        layout.addWidget(self.pila, 1)

    def centrar_ventana(self):
        pantalla = self.screen().availableGeometry()
        ventana = self.frameGeometry()

        ventana.moveCenter(pantalla.center())
        self.move(ventana.topLeft())
    
    def _mostrar_registro(self):
        self.pantalla_registro = PantallaRegistro()
        self.pantalla_registro.registrado.connect(self._tras_registro)

        self.pila.addWidget(self.pantalla_registro)
        self.pila.setCurrentWidget(self.pantalla_registro)

        self.barra.hide()

        # Ventana más pequeña para el registro
        self.resize(*self.TAMANO_START)
        self.centrar_ventana()

    def _tras_registro(self, nombre: str):
        registro, self.pantalla_registro = self.pantalla_registro, None
        self._mostrar_inicio(nombre)
        if registro is not None:
            self.pila.removeWidget(registro)
            registro.deleteLater()

    def _mostrar_inicio(self, nombre: str):
        self.pantalla_inicio = PantallaInicio(nombre, self.db)
        self.panel_izquierdo = self.pantalla_inicio.panel_izquierdo

        self.pantalla_inicio.panel_derecho.curso_solicitado.connect(
            self.mostrar_curso
        )

        self.pila.addWidget(self.pantalla_inicio)
        self.pila.setCurrentWidget(self.pantalla_inicio)

        # Restaurar dimensiones de la pantalla principal
        self.resize(*self.TAMANO_INICIO)
        self.centrar_ventana() 

        self._actualizar_barra()

    # ── Navegación ────────────────────────────────────────────────────────

    def mostrar_curso(self, curso):
        """Reemplaza el inicio por la pantalla del curso."""
        pantalla = CursoMenu(curso)
        # Cada lección completada actualiza los contadores del inicio
        pantalla.progreso_cambiado.connect(self.pantalla_inicio.refrescar)
        pantalla.pantalla_solicitada.connect(self.mostrar_pantalla)
        pantalla.pantalla_quitada.connect(self.quitar_pantalla)
        self.mostrar_pantalla(pantalla, pantalla.titulo or "Curso")

    def mostrar_pantalla(self, widget: QWidget, titulo: str):
        """Apila una pantalla nueva y la muestra."""
        self._pantallas.append((widget, titulo))
        self.pila.addWidget(widget)
        self.pila.setCurrentWidget(widget)
        self._actualizar_barra()
        self._enfocar(widget)

    def quitar_pantalla(self, widget: QWidget):
        """Quita `widget` (y todo lo apilado encima) y muestra la pantalla anterior.

        No pide confirmación: se usa cuando el cierre ya está decidido.
        """
        posicion = next(
            (i for i, (w, _t) in enumerate(self._pantallas) if w is widget), None
        )
        if posicion is None:
            return

        quitadas = self._pantallas[posicion:]
        self._pantallas = self._pantallas[:posicion]
        for pantalla, _titulo in quitadas:
            self.pila.removeWidget(pantalla)
            pantalla.deleteLater()

        if self._pantallas:
            self.pila.setCurrentWidget(self._pantallas[-1][0])
        elif self.pantalla_inicio is not None:
            self.pila.setCurrentWidget(self.pantalla_inicio)
            self.pantalla_inicio.refrescar()
        self._actualizar_barra()

    def ir_a_inicio(self):
        """Botón «Volver al inicio»: cierra curso, lección o examen abiertos."""
        if not self._pantallas or not self._puede_salir():
            return
        self.quitar_pantalla(self._pantallas[0][0])
        if self.pantalla_inicio is not None:
            self._enfocar(self.pantalla_inicio)

    def volver(self):
        """Vuelve un nivel (de la lección o el examen al mapa del curso)."""
        if not self._pantallas or not self._puede_salir():
            return
        self.quitar_pantalla(self._pantallas[-1][0])

    def _puede_salir(self) -> bool:
        """Las pantallas con trabajo en curso (el examen) pueden pedir confirmación."""
        actual = self._pantallas[-1][0]
        comprobar = getattr(actual, "puede_salir", None)
        return True if comprobar is None else bool(comprobar())

    def _actualizar_barra(self):
        """La barra se muestra en todas las pantallas salvo en el inicio."""
        en_inicio = not self._pantallas
        self.barra.setVisible(not en_inicio and self.pantalla_registro is None)
        if not en_inicio:
            self.barra.mostrar_ruta(
                [t for _w, t in self._pantallas], con_volver=len(self._pantallas) > 1
            )

    @staticmethod
    def _enfocar(widget: QWidget):
        widget.setFocus(Qt.FocusReason.OtherFocusReason)

    def closeEvent(self, event):
        # Un examen a medias pregunta antes de perder las respuestas
        if self._pantallas and not self._puede_salir():
            event.ignore()
            return
        super().closeEvent(event)


if __name__ == "__main__":
    from .theme import aplicar_tema

    app = QApplication(sys.argv)
    aplicar_tema(app)

    ventana = VentanaPrincipal("Ejemplo")
    ventana.show()

    sys.exit(app.exec())
