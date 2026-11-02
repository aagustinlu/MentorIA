from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QCoreApplication

import sys

from services.database import BaseDatosProyecto
from ui.start import VentanaInicial
from ui.main_window import VentanaPrincipal
from ui.theme import aplicar_tema

 
# Configurar Qt antes de crear QApplication
QCoreApplication.setAttribute(
    Qt.ApplicationAttribute.AA_ShareOpenGLContexts
)

def main():
    ruta_base_datos = "storage/sistema_estudios.db"
    db = BaseDatosProyecto(ruta_base_datos)

    usuario_existente = db.obtener_perfil()  # (nombre, token) o None

    app = QApplication(sys.argv)
    aplicar_tema(app)

    if usuario_existente:
        nombre, _token = usuario_existente
        ventana = VentanaPrincipal(nombre)
    else:
        ventana = VentanaInicial()

    
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

