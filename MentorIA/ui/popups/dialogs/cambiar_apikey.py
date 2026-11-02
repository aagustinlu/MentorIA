from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton

from services.config_service import ConfigService
from ui.theme import primario


class CambiarApikeyDialog(QDialog):
    apikey_cambiada = pyqtSignal(str)

    def __init__(self, parent=None, config_service: ConfigService | None = None):
        super().__init__(parent)
        self.setWindowTitle("Cambiar Api Key")
        self.config_service = config_service or ConfigService()

        self.setMinimumWidth(340)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)

        self.txt_apik = QLabel("Ingresa tu nueva Api Key:")
        self.ingresar_apikey = QLineEdit()

        self.btn_confirmar = QPushButton("Confirmar")
        self.btn_cancelar = QPushButton("Cancelar")
        primario(self.btn_confirmar)

        self.btn_confirmar.clicked.connect(self._confirmar)
        self.btn_cancelar.clicked.connect(self.reject)

        layout.addWidget(self.txt_apik)
        layout.addWidget(self.ingresar_apikey)
        layout.addStretch()

        layout.addWidget(self.btn_confirmar)
        layout.addWidget(self.btn_cancelar)

        self.setLayout(layout)

    def _confirmar(self):
        nueva_apikey = self.ingresar_apikey.text().strip()
        if not nueva_apikey:
            return

        if self.config_service.cambiar_api_key(nueva_apikey):
            self.apikey_cambiada.emit(nueva_apikey)
            self.accept()
        else:
            # Mantener el dialog abierto si falla.
            self.reject()

