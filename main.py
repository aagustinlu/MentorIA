import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QCoreApplication

from services.database import BaseDatosProyecto
from ui.ventana_principal import VentanaPrincipal
from ui.theme import TEMA_POR_DEFECTO, aplicar_tema
from services.resolver_rutas import resolver_ruta_recurso 

# Configurar Qt antes de crear QApplication
QCoreApplication.setAttribute(
    Qt.ApplicationAttribute.AA_ShareOpenGLContexts
)

def main():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        
        appdata_dir = os.environ.get('APPDATA')
        carpeta_app = os.path.join(appdata_dir, "MentorIA")
        ruta_final_db = os.path.join(carpeta_app, "sistema_estudios.db")
    else:
        ruta_final_db = resolver_ruta_recurso("storage/sistema_estudios.db")

    
    db = BaseDatosProyecto(ruta_final_db)

    usuario_existente = db.obtener_perfil()  # (nombre, token) o None
    tema_guardado = db.obtener_ajuste("tema", TEMA_POR_DEFECTO)

    app = QApplication(sys.argv)
    aplicar_tema(app, tema_guardado)

    # Una sola ventana: si aún no hay perfil, muestra el registro dentro de ella
    nombre = usuario_existente[0] if usuario_existente else None
    ventana = VentanaPrincipal(nombre)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

