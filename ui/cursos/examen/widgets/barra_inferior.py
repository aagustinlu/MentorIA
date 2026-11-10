from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from ui.theme import primario, repulir, rol

from ..paginas import PAGINA_INICIO, PAGINA_PREGUNTAS, PAGINA_RESULTADOS


class BarraInferior(QHBoxLayout):
    """Crea los botones; el controlador conecta sus señales y llama a `mostrar_pagina`."""

    def __init__(self, hay_intentos_previos: bool):
        super().__init__()

        self.btn_comenzar = QPushButton()
        primario(self.btn_comenzar)
        self.btn_comenzar.setText("Repetir examen" if hay_intentos_previos else "Comenzar examen")

        self.btn_anterior = QPushButton("Anterior")

        self.lbl_progreso = QLabel()
        self.lbl_progreso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_progreso.setMinimumWidth(170)
        rol(self.lbl_progreso, "subtitulo")

        self.btn_siguiente = QPushButton("Siguiente")
        primario(self.btn_siguiente)

        self.btn_reintentar = QPushButton("Reintentar")
        primario(self.btn_reintentar)

        self.btn_certificado = QPushButton("Descargar certificado")
        self.btn_cerrar = QPushButton("Cerrar")

        botones = (
            self.btn_comenzar, self.btn_anterior, self.btn_siguiente,
            self.btn_reintentar, self.btn_certificado, self.btn_cerrar,
        )
        for boton in botones:
            boton.setMinimumWidth(110)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_comenzar.setMinimumWidth(150)
        self.btn_siguiente.setMinimumWidth(150)
        self.btn_reintentar.setMinimumWidth(240)
        self.btn_certificado.setMinimumWidth(200)

        self.setSpacing(12)
        self.addStretch()
        self.addWidget(self.btn_comenzar)
        self.addWidget(self.btn_anterior)
        self.addWidget(self.lbl_progreso)
        self.addWidget(self.btn_siguiente)
        self.addWidget(self.btn_reintentar)
        self.addWidget(self.btn_certificado)
        self.addWidget(self.btn_cerrar)
        self.addStretch()

    def mostrar_pagina(
        self,
        pagina: int,
        *,
        aprobado: bool,
        curso_aprobado: bool,
        con_certificado: bool,
    ) -> None:
        """
        aprobado:        el intento recién terminado fue aprobado (pantalla de resultados).
        curso_aprobado:  el curso ya estaba aprobado al abrir la ventana.
        con_certificado: existe el callback para descargar el certificado.
        """
        en_inicio = pagina == PAGINA_INICIO
        en_preguntas = pagina == PAGINA_PREGUNTAS
        en_resultados = pagina == PAGINA_RESULTADOS

        self.btn_comenzar.setVisible(en_inicio)
        self.btn_anterior.setVisible(en_preguntas)
        self.lbl_progreso.setVisible(en_preguntas)
        self.btn_siguiente.setVisible(en_preguntas)
        self.btn_reintentar.setVisible(en_resultados and not aprobado)

        # Certificado: al aprobar (resultados) o, en el inicio, si el curso ya estaba aprobado.
        # Es la acción principal al aprobar; en el inicio queda en segundo plano.
        hay_certificado = (en_resultados and aprobado) or (en_inicio and curso_aprobado)
        self.btn_certificado.setVisible(con_certificado and hay_certificado)
        self.btn_certificado.setProperty("primario", en_resultados)
        repulir(self.btn_certificado)

        self.btn_cerrar.setVisible(en_resultados)
