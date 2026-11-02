import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QHBoxLayout,
                             QVBoxLayout, QLabel, QPushButton, QLineEdit)
from PyQt6.QtCore import Qt
from services.database import BaseDatosProyecto
from ui.theme import primario, rol, tarjeta


class VentanaInicial(QWidget):
    def __init__(self):
        super().__init__()
        self.iniciar_ui()

    def iniciar_ui(self):
        self.setWindowTitle("AsistIA")
        self.resize(420, 420)

        # Layout exterior: centra una tarjeta sobre el fondo
        exterior = QVBoxLayout(self)
        exterior.setContentsMargins(28, 28, 28, 28)

        self.card = QWidget()
        tarjeta(self.card)
        exterior.addWidget(self.card)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(32, 30, 32, 28)
        layout.setSpacing(6)

        self.titulo = QLabel("Bienvenido a AsistIA")
        rol(self.titulo, "titulo")

        self.subtitulo = QLabel("Crea cursos a tu medida y estudia a tu ritmo.")
        rol(self.subtitulo, "subtitulo")
        self.subtitulo.setWordWrap(True)

        self.text_nomb = QLabel("Nombre")
        rol(self.text_nomb, "subtitulo")
        self.ingresar_nombre = QLineEdit()
        self.ingresar_nombre.setPlaceholderText("¿Cómo te llamas?")

        self.text_tok = QLabel("Tu token")
        rol(self.text_tok, "subtitulo")
        self.text_ayuda_token = QLabel("¿Cómo conseguir tu token?")
        rol(self.text_ayuda_token, "enlace")

        self.ingresar_token = QLineEdit()
        self.ingresar_token.setPlaceholderText("Pega aquí tu token")

        self.btn_reg = QPushButton("Registrarse")
        primario(self.btn_reg)
        self.btn_reg.setMinimumHeight(38)
        self.btn_reg.setCursor(Qt.CursorShape.PointingHandCursor)

        # Se crea un layout horizontal para el apartado del token
        # (Izquierda: Tu token | Derecha: Cómo conseguir tu token)
        layout_token = QHBoxLayout()
        layout_token.addWidget(self.text_tok)
        layout_token.addStretch()
        layout_token.addWidget(self.text_ayuda_token)

        # Apartado del titulo
        layout.addWidget(self.titulo)
        layout.addWidget(self.subtitulo)
        layout.addSpacing(22)

        # Apartado del nombre
        layout.addWidget(self.text_nomb)
        layout.addWidget(self.ingresar_nombre)
        layout.addSpacing(10)

        # Apartado del token
        layout.addLayout(layout_token)
        layout.addWidget(self.ingresar_token)

        # Apartado del boton de Registro
        layout.addStretch()
        layout.addWidget(self.btn_reg)

        # Conectar el botón al registro
        self.btn_reg.clicked.connect(self.Registrar)
        # Enter en cualquiera de los campos también registra
        self.ingresar_nombre.returnPressed.connect(self.Registrar)
        self.ingresar_token.returnPressed.connect(self.Registrar)

    def Registrar(self):
        nombre = self.ingresar_nombre.text().strip()
        token = self.ingresar_token.text().strip()

        if not nombre or not token:
            # UX simple: en vez de QMessageBox, limpiamos para que puedas ver el flujo
            # (podemos mejorar esto luego)
            return

        ruta_base_datos = "storage/sistema_estudios.db"
        db = BaseDatosProyecto(ruta_base_datos)

        ok = db.registrar_usuario(nombre, token)
        if ok:
            # Import local para evitar dependencias circulares en imports
            from ui.main_window import VentanaPrincipal
            self.ventana_principal = VentanaPrincipal(nombre)
            self.ventana_principal.show()
            self.close()

if __name__ == "__main__":
    from ui.theme import aplicar_tema

    app = QApplication(sys.argv)
    aplicar_tema(app)
    ventana = VentanaInicial()
    ventana.show()
    sys.exit(app.exec())
