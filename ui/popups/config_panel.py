from functools import partial

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

from services.config_service import ConfigService
from ui.interruptor_tema import InterruptorTema
from ui.theme import TEMA_DIA, TEMA_OSCURO, al_cambiar_tema, gestor_tema, rol

from ui.popups.dialogs.cambiar_nombre_dialog import CambiarNombreDialog
from ui.popups.dialogs.cambiar_apikey import CambiarApikeyDialog


class ConfigPanel(QWidget):
    """Panel de configuración (contiene acciones)."""



    def __init__(self, panel_izquierdo=None):
        super().__init__()

        self.panel_izquierdo = panel_izquierdo
        
        self.config_service = ConfigService()

        # Ancho fijo; el alto lo da el contenido (el diálogo se ajusta a él)
        self.setFixedWidth(320)


        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        titulo = QLabel("Configuración")
        rol(titulo, "titulo")
        layout.addWidget(titulo)
        layout.addSpacing(6)


        self.btn_cambiar_nombre = QPushButton("Cambiar nombre")
        self.btn_cambiar_nombre.clicked.connect(self._abrir_cambiar_nombre)

        self.btn_cambiar_apikey = QPushButton("Cambiar Api Key")
        self.btn_cambiar_apikey.clicked.connect(self._abrir_cambiar_apikey)

        layout.addWidget(self.btn_cambiar_nombre)
        layout.addWidget(self.btn_cambiar_apikey)

        # ── Apariencia: alterna entre Modo Día y Modo Oscuro ──────────
        layout.addSpacing(12)
        seccion = QLabel("APARIENCIA")
        rol(seccion, "seccion")
        layout.addWidget(seccion)

        fila_tema = QHBoxLayout()
        fila_tema.setSpacing(12)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        self.lbl_tema = QLabel("Tema")
        self.lbl_modo = QLabel()
        rol(self.lbl_modo, "subtitulo")
        textos.addWidget(self.lbl_tema)
        textos.addWidget(self.lbl_modo)

        self.interruptor_tema = InterruptorTema()
        self.interruptor_tema.set_oscuro(gestor_tema().es_oscuro)
        self.interruptor_tema.toggled.connect(self._cambiar_tema)

        fila_tema.addLayout(textos, 1)
        fila_tema.addWidget(self.interruptor_tema)
        layout.addLayout(fila_tema)

        self._actualizar_texto_modo()
        # Mantiene el interruptor coherente si el tema cambia desde otro lugar
        al_cambiar_tema(self._sincronizar_interruptor)

        layout.addStretch()


        self.setLayout(layout)

    # ── Tema ─────────────────────────────────────────────────────────

    def _cambiar_tema(self, oscuro: bool):
        animacion = self.interruptor_tema._animacion

        try:
            animacion.finished.disconnect()
        except TypeError:
            pass

        animacion.finished.connect(
            partial(self._aplicar_tema_elegido, oscuro)
        )

    def _aplicar_tema_elegido(self, oscuro: bool):
        nombre = TEMA_OSCURO if oscuro else TEMA_DIA

        # Se aplica en toda la aplicación y se recuerda para el próximo arranque
        gestor_tema().aplicar(nombre)
        if not self.config_service.guardar_tema(nombre):
            print("No se pudo guardar el tema elegido.")

    def _sincronizar_interruptor(self, _nombre: str = ""):
        self.interruptor_tema.set_oscuro(gestor_tema().es_oscuro)
        self._actualizar_texto_modo()

    def _actualizar_texto_modo(self):
        self.lbl_modo.setText(
            "Modo oscuro" if gestor_tema().es_oscuro else "Modo día"
        )

    def _abrir_cambiar_nombre(self):
        
        dialog = CambiarNombreDialog(self)
        
        if self.panel_izquierdo:
            dialog.nombre_cambiado.connect (
                lambda nuevo_nombre:
                self.panel_izquierdo.nombre_label.setText(f"<b>{nuevo_nombre}</b>")
            )
        
        dialog.exec()
        
    def _abrir_cambiar_apikey(self):
        dialog = CambiarApikeyDialog(self)

        if self.panel_izquierdo:
            # Tu panel izquierdo hoy solo muestra el nombre. Si agregas un label para el token,
            # aquí puedes actualizarlo con el nuevo valor.
            dialog.apikey_cambiada.connect(lambda _: None)

        dialog.exec()



