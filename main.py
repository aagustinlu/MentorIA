from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QCoreApplication

import sys

from services.database import BaseDatosProyecto
from ui.start import VentanaInicial
from ui.ventana_principal import VentanaPrincipal
from ui.theme import TEMA_POR_DEFECTO, aplicar_tema


# Configurar Qt antes de crear QApplication
QCoreApplication.setAttribute(
    Qt.ApplicationAttribute.AA_ShareOpenGLContexts
)

def main():
    ruta_base_datos = "storage/sistema_estudios.db"
    db = BaseDatosProyecto(ruta_base_datos)

    usuario_existente = db.obtener_perfil()  # (nombre, token) o None
    tema_guardado = db.obtener_ajuste("tema", TEMA_POR_DEFECTO)

    app = QApplication(sys.argv)
    aplicar_tema(app, tema_guardado)

    if usuario_existente:
        nombre, _token = usuario_existente
        ventana = VentanaPrincipal(nombre)
    else:
        ventana = VentanaInicial()

    
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

