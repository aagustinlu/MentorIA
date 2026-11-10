import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QMainWindow,
    QWidget,
)
from PyQt6.QtGui import QIcon
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
from ui.ventana_principal.panel_izquierdo import PanelIzquierdo
from ui.ventana_principal.panel_derecho import PanelDerecho


class VentanaPrincipal(QMainWindow):
    
    curso_seleccionado = pyqtSignal(int)
    
    
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
        layout_principal = QHBoxLayout()
        layout_principal.setContentsMargins(22, 22, 22, 22)
        layout_principal.setSpacing(20)
        
        layout_principal.addWidget(
            self.panel_izquierdo,
        )

        layout_principal.addWidget(
            self.panel_derecho,
            1
        )

        wid = QWidget(self)
        self.setCentralWidget(wid)
        
        wid.setLayout(layout_principal)

    def event(self, e):
        # Al volver a esta ventana (p. ej. tras cerrar una lección) se actualiza el progreso
        if e.type() == QEvent.Type.WindowActivate:
            self.panel_izquierdo.refrescar_progreso()
        return super().event(e)

    def closeEvent(self, event):
        # Al cerrar la ventana principal se cierran también curso y lecciones abiertos
        QApplication.closeAllWindows()
        super().closeEvent(event)
        
    def mostrarCurso(self):
        self.curso_seleccionado.emit(1)  # Emitir señal con el ID del curso seleccionado


if __name__ == "__main__":
    from .theme import aplicar_tema

    app = QApplication(sys.argv)
    aplicar_tema(app)

    ventana = VentanaPrincipal("Ejemplo")
    ventana.show()

    sys.exit(app.exec())