"""
Pantalla de inicio del examen: datos generales e intentos previos.
"""

import math

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from models.models import ExamenModel
from services.examen_service import PORCENTAJE_APROBACION
from ui.theme import fs, rol


def texto_intentos_previos(estado: dict) -> str:
    intentos = estado.get("intentos", 0)
    if not intentos:
        return ""

    lineas = []
    if estado.get("aprobado"):
        lineas.append("✓ Ya aprobaste esta evaluación.")

    mejor = estado.get("mejor")
    if mejor:
        aciertos, total = mejor
        porcentaje = round(100 * aciertos / total)
        lineas.append(
            f"Mejor resultado: {aciertos}/{total} ({porcentaje}%) · "
            f"{intentos} {'intento' if intentos == 1 else 'intentos'}"
        )
    return "\n".join(lineas)


def crear_pagina_inicio(examen: ExamenModel, estado: dict) -> QWidget:
    pagina = QWidget()
    layout = QVBoxLayout(pagina)
    layout.setContentsMargins(32, 28, 32, 24)
    layout.setSpacing(12)

    etiqueta = QLabel("EVALUACIÓN FINAL")
    rol(etiqueta, "seccion")

    titulo = QLabel(examen.titulo)
    titulo.setWordWrap(True)
    titulo.setStyleSheet(f"font-size: {fs(24)}px; font-weight: 600;")

    total = len(examen.preguntas)
    minimo = math.ceil(PORCENTAJE_APROBACION * total / 100)
    info = QLabel(
        f"{total} preguntas de opción múltiple basadas en las lecciones del curso.\n\n"
        f"Para aprobar necesitas al menos un {PORCENTAJE_APROBACION}% de respuestas "
        f"correctas ({minimo} de {total}).\n\n"
        "Antes de finalizar puedes volver atrás y cambiar tus respuestas."
    )
    info.setWordWrap(True)
    rol(info, "suave")
    info.setStyleSheet(f"font-size: {fs(14)}px;")

    layout.addWidget(etiqueta)
    layout.addWidget(titulo)
    layout.addSpacing(6)
    layout.addWidget(info)

    previo = texto_intentos_previos(estado)
    if previo:
        lbl_previo = QLabel(previo)
        lbl_previo.setWordWrap(True)
        lbl_previo.setStyleSheet(f"font-size: {fs(14)}px; font-weight: 600;")
        layout.addSpacing(10)
        layout.addWidget(lbl_previo)

    layout.addStretch(1)
    return pagina
