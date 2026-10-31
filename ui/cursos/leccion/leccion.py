import sys
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QSizePolicy,
    QScrollArea,
    QMessageBox,
)
from PyQt6.QtCore import Qt

# Asegura que la raíz del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.models import LeccionModel
from ui.theme import Colores as C, primario, rol, tarjeta


from services.fuente_multiidioma import (
    registrar_fuente_multidioma
)

from ui.cursos.leccion.widgets.widgets import (
    crear_texto,
    crear_titulo,
    crear_codigo,
    crear_formula
)


# ==========================================================
# Menú principal de la lección
# ==========================================================

class LeccionMenu(QWidget):

    def __init__(self, leccion_model, estado="completed", on_completar=None):
        """
        estado:       "current" (azul) muestra el botón «Completar lección»;
                      "completed" (verde) es modo repaso, sin botón.
        on_completar: callable(leccion_id) -> bool que persiste el progreso
                      y desbloquea la siguiente lección.
        """
        super().__init__()

        # La fuente debe registrarse cuando QApplication ya existe.
        registrar_fuente_multidioma()

        self.LeccionModel = leccion_model
        self.estado = estado
        self.on_completar = on_completar
        self.indice = 0

        self.iniciar_ui()

    def iniciar_ui(self):
        self.setWindowTitle("Ejemplo")

        # Tamaño inicial de la ventana
        self.resize(720, 580)
        self.setMaximumHeight(700)

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 16)
        layout_principal.setSpacing(14)

        # Pila de páginas (dentro de una tarjeta blanca, como una hoja de lectura)
        self.pila_paginas = QStackedWidget()
        self.pila_paginas.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.tarjeta_lectura = QWidget()
        tarjeta(self.tarjeta_lectura)
        layout_tarjeta = QVBoxLayout(self.tarjeta_lectura)
        layout_tarjeta.setContentsMargins(8, 12, 8, 12)
        layout_tarjeta.addWidget(self.pila_paginas)

        self.rellenar_pila()

        if self.pila_paginas.count() > 0:
            self.pila_paginas.setCurrentIndex(0)

        # Indicador de página actual
        self.label_indice = QLabel(
            f"1 / {self.pila_paginas.count()}"
        )
        self.label_indice.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.label_indice.setMinimumWidth(60)
        rol(self.label_indice, "subtitulo")

        # Botones de navegación
        self.btn_retroceder = QPushButton("Anterior")
        self.btn_retroceder.clicked.connect(
            self.retroceder_pagina
        )

        self.btn_avanzar = QPushButton("Siguiente")
        primario(self.btn_avanzar)
        # En la última página de la lección actual este botón pasa a ser
        # «Completar lección» (ver actualizar_boton_completar).
        self.btn_avanzar.clicked.connect(
            self.avanzar_o_completar
        )

        # Aviso para lecciones ya completadas (modo repaso)
        self.lbl_completada = QLabel("✓ Lección completada")
        self.lbl_completada.setStyleSheet(
            f"color: {C.COMPLETADO}; font-weight: 600;"
        )

        for boton in (self.btn_retroceder, self.btn_avanzar):
            boton.setMinimumWidth(110)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)

        # Ancho fijo suficiente para «Completar lección» (evita que el layout "salte")
        self.btn_avanzar.setMinimumWidth(150)

        layout_inferior = QHBoxLayout()
        layout_inferior.setSpacing(12)

        layout_inferior.addStretch()
        layout_inferior.addWidget(self.btn_retroceder)
        layout_inferior.addWidget(self.label_indice)
        layout_inferior.addWidget(self.btn_avanzar)
        layout_inferior.addSpacing(12)
        layout_inferior.addWidget(self.lbl_completada)
        layout_inferior.addStretch()

        # Distribución principal
        layout_principal.addWidget(self.tarjeta_lectura, 1)
        layout_principal.addLayout(layout_inferior)

        self.actualizar_navegacion()

    def añadir_pagina(self, pagina_num):
        pagina_model = self.LeccionModel.paginas[pagina_num]
        pagina = MostrarPagina(pagina_model)

        self.pila_paginas.addWidget(pagina)

    def rellenar_pila(self):
        paginas = len(self.LeccionModel.paginas)

        for i in range(paginas):
            self.añadir_pagina(i)

    def actualizar_navegacion(self):
        total = self.pila_paginas.count()

        if total == 0:
            self.label_indice.setText("0 / 0")
            self.btn_retroceder.setEnabled(False)
            self.btn_avanzar.setEnabled(False)
            self.actualizar_boton_completar()
            return

        self.label_indice.setText(
            f"{self.indice + 1} / {total}"
        )

        self.btn_retroceder.setEnabled(self.indice > 0)
        self.btn_avanzar.setEnabled(
            self.indice < total - 1
        )
        self.actualizar_boton_completar()

    def es_leccion_actual(self) -> bool:
        return self.estado == "current" and self.on_completar is not None

    def en_ultima_pagina(self) -> bool:
        total = self.pila_paginas.count()
        return total == 0 or self.indice >= total - 1

    def modo_completar(self) -> bool:
        """True si el botón de la derecha debe completar la lección."""
        return self.es_leccion_actual() and self.en_ultima_pagina()

    def actualizar_boton_completar(self):
        """
        En la última página de la lección actual, «Siguiente» se convierte
        en «Completar lección». En lecciones ya completadas (repaso) sigue
        siendo «Siguiente» (deshabilitado en la última página).
        """
        if self.modo_completar():
            self.btn_avanzar.setText("Completar lección")
            self.btn_avanzar.setEnabled(True)
        else:
            self.btn_avanzar.setText("Siguiente")

        self.lbl_completada.setVisible(self.estado == "completed")

    def avanzar_o_completar(self):
        if self.modo_completar():
            self.completar_leccion()
        else:
            self.avanzar_pagina()

    def completar_leccion(self):
        if self.on_completar is None:
            return

        if self.on_completar(self.LeccionModel.id):
            self.estado = "completed"
            # Al completar, la ventana se cierra para agilizar el flujo
            self.close()
        else:
            QMessageBox.warning(
                self,
                "No se pudo completar",
                "No se pudo guardar el progreso de la lección.",
            )

    def avanzar_pagina(self):
        if self.indice + 1 < self.pila_paginas.count():
            self.indice += 1
            self.pila_paginas.setCurrentIndex(self.indice)
            self.actualizar_navegacion()

    def retroceder_pagina(self):
        if self.indice > 0:
            self.indice -= 1
            self.pila_paginas.setCurrentIndex(self.indice)
            self.actualizar_navegacion()


# ==========================================================
# Visualización de una página
# ==========================================================
        
class MostrarPagina(QWidget):

    def __init__(self, pagina_model):
        super().__init__()

        self.PaginaModel = pagina_model

        self.widgets = {
            "texto": crear_texto,
            "codigo": crear_codigo,
            "titulo": crear_titulo,
            "formula": crear_formula,
        }

        self.iniciar_ui()
        
    # ------------------------------------------------------
    # Diseño de la página
    # ------------------------------------------------------

    def iniciar_ui(self):
        pagina = QVBoxLayout(self)
        pagina.setContentsMargins(0, 0, 0, 0)
        pagina.setSpacing(0)

        # Área desplazable para lecciones largas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setMinimumSize(0, 0)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setAutoFillBackground(False)

        scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        # Contenedor de bloques
        contenido = QWidget()
        contenido.setMinimumSize(0, 0)

        layout_contenido = QVBoxLayout(contenido)
        layout_contenido.setContentsMargins(24, 10, 24, 10)
        layout_contenido.setSpacing(8)

        for bloque in self.PaginaModel.bloques:
            widget = self.crear_widget(bloque)

            layout_contenido.addWidget(widget)

        # Mantiene los bloques arriba cuando sobra espacio.
        layout_contenido.addStretch()

        scroll.setWidget(contenido)
        contenido.setAutoFillBackground(False)
        pagina.addWidget(scroll)

    # ------------------------------------------------------
    # Selección del widget según el tipo de bloque
    # ------------------------------------------------------

    def crear_widget(self, bloque):
        try:
            return self.widgets[bloque.tipo](bloque)
        except KeyError:
            raise ValueError(
                f"Tipo de bloque desconocido: {bloque.tipo}"
            )
