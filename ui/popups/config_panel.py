from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel

from ui.theme import rol

from ui.popups.dialogs.cambiar_nombre_dialog import CambiarNombreDialog
from ui.popups.dialogs.cambiar_apikey import CambiarApikeyDialog


class ConfigPanel(QWidget):
    """Panel de configuración (contiene acciones)."""



    def __init__(self, panel_izquierdo=None):
        super().__init__()

        self.panel_izquierdo = panel_izquierdo
        
        # Evitar cualquier estiramiento del panel (tamaño fijo real)
        self.setFixedWidth(260)
        self.setFixedHeight(170)


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

        layout.addStretch()


        self.setLayout(layout)

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



