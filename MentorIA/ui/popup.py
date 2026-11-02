from PyQt6.QtWidgets import QDialog, QVBoxLayout
from ui.popups.config_panel import ConfigPanel

class Configuraciones(QDialog):
    def __init__(self, panel_izquierdo=None):
        super().__init__(panel_izquierdo)

        self.setWindowTitle("Configuración")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.config_panel = ConfigPanel(panel_izquierdo)
        
        layout.addWidget(self.config_panel)
        self.setLayout(layout)