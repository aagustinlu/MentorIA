import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import (
    Qt
)

# Asegura que el proyecto raíz esté en sys.path para imports absolutos
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.popup import Configuraciones
from ui.theme import Colores as C, al_cambiar_tema, fs, rol, tarjeta
from services.database import BaseDatosProyecto



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