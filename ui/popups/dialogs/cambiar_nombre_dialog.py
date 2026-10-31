from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton

from services.config_service import ConfigService
from ui.theme import primario


class CambiarNombreDialog(QDialog):
    nombre_cambiado = pyqtSignal(str)

    def __init__(self, parent=None, config_service: ConfigService | None = None):
        super().__init__(parent)
        self.setWindowTitle("Cambiar nombre")
        self.config_service = config_service or ConfigService()

        self.setMinimumWidth(340)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)

        self.txt_nombr = QLabel("Ingresa tu nuevo nombre:")
        self.ingresar_nombre = QLineEdit()

        self.btn_confirmar = QPushButton("Confirmar")
        self.btn_cancelar = QPushButton("Cancelar")
        primario(self.btn_confirmar)

        self.btn_confirmar.clicked.connect(self._confirmar)
        self.btn_cancelar.clicked.connect(self.reject)

        layout.addWidget(self.txt_nombr)
        layout.addWidget(self.ingresar_nombre)
        layout.addStretch()

        layout.addWidget(self.btn_confirmar)
        layout.addWidget(self.btn_cancelar)

        self.setLayout(layout)

    def _confirmar(self):
        nuevo_nombre = self.ingresar_nombre.text().strip()
        if not nuevo_nombre:
            return

        if self.config_service.cambiar_nombre(nuevo_nombre):
            self.nombre_cambiado.emit(nuevo_nombre)
            self.accept()
        else:
            # Mantener el dialog abierto si falla.
            self.reject()

