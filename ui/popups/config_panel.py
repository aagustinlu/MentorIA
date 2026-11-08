from functools import partial

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QButtonGroup, QFrame,
)

from services.config_service import ConfigService
from ui.interruptor_tema import InterruptorTema
from ui.theme import TEMA_DIA, TEMA_OSCURO, al_cambiar_tema, gestor_tema, rol

from ui.popups.dialogs.cambiar_nombre_dialog import CambiarNombreDialog
from ui.popups.dialogs.cambiar_apikey import CambiarApikeyDialog


class ConfigPanel(QWidget):
    """Panel de configuración: menú lateral (General / Apariencia) + contenido."""

    def __init__(self, panel_izquierdo=None):
        super().__init__()

        self.panel_izquierdo = panel_izquierdo
        self.config_service = ConfigService()

        self.setFixedWidth(560)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(14)

        # Título a todo el ancho (en la columna del menú no entraba)
        """
        titulo = QLabel("Configuración")
        rol(titulo, "titulo")
        raiz.addWidget(titulo)
        """
        
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        raiz.addLayout(cuerpo, 1)

        # ── Menú lateral ─────────────────────────────────────────────
        menu = QVBoxLayout()
        menu.setContentsMargins(0, 0, 0, 0)
        menu.setSpacing(6)

        self._grupo_menu = QButtonGroup(self)
        self._grupo_menu.setExclusive(True)

        self.btn_general = self._crear_boton_menu("General")
        self.btn_apariencia = self._crear_boton_menu("Apariencia")

        self._grupo_menu.addButton(self.btn_general, 0)
        self._grupo_menu.addButton(self.btn_apariencia, 1)
        menu.addWidget(self.btn_general)
        menu.addWidget(self.btn_apariencia)
        menu.addStretch()

        contenedor_menu = QWidget()
        contenedor_menu.setLayout(menu)
        contenedor_menu.setFixedWidth(150)

        separador = QFrame()
        separador.setObjectName("separadorConfig")
        separador.setFixedWidth(1)

        # ── Contenido (una página por sección) ───────────────────────
        self.paginas = QStackedWidget()
        self.paginas.addWidget(self._crear_pagina_general())
        self.paginas.addWidget(self._crear_pagina_apariencia())

        self._grupo_menu.idClicked.connect(self.paginas.setCurrentIndex)
        self.btn_general.setChecked(True)

        cuerpo.addWidget(contenedor_menu)
        cuerpo.addWidget(separador)
        cuerpo.addWidget(self.paginas, 1)

        # Mantiene el interruptor coherente si el tema cambia desde otro lugar
        self._actualizar_texto_modo()
        al_cambiar_tema(self._sincronizar_interruptor)

    # ── Construcción de la UI ────────────────────────────────────────

    def _crear_boton_menu(self, texto: str) -> QPushButton:
        btn = QPushButton(texto)
        btn.setObjectName("menuConfig")
        btn.setCheckable(True)
        return btn

    def _crear_pagina_general(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        seccion = QLabel("GENERAL")
        rol(seccion, "seccion")
        layout.addWidget(seccion)

        self.btn_cambiar_nombre = QPushButton("Cambiar nombre")
        self.btn_cambiar_nombre.clicked.connect(self._abrir_cambiar_nombre)

        self.btn_cambiar_apikey = QPushButton("Cambiar Api Key")
        self.btn_cambiar_apikey.clicked.connect(self._abrir_cambiar_apikey)

        layout.addWidget(self.btn_cambiar_nombre)
        layout.addWidget(self.btn_cambiar_apikey)
        layout.addStretch()
        return pagina

    def _crear_pagina_apariencia(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

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
        layout.addStretch()
        return pagina

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

    # ── General ──────────────────────────────────────────────────────

    def _abrir_cambiar_nombre(self):
        dialog = CambiarNombreDialog(self)

        if self.panel_izquierdo:
            dialog.nombre_cambiado.connect(
                lambda nuevo_nombre:
                self.panel_izquierdo.nombre_label.setText(f"<b>{nuevo_nombre}</b>")
            )

        dialog.exec()

    def _abrir_cambiar_apikey(self):
        dialog = CambiarApikeyDialog(self)

        if self.panel_izquierdo:
            # Si agregas un label para el token en el panel izquierdo,
            # aquí puedes actualizarlo con el nuevo valor.
            dialog.apikey_cambiada.connect(lambda _: None)

        dialog.exec()