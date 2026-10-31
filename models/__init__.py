"""Paquete `models`.

Este archivo existe para que imports como:

    from models import Curso, Leccion

funcionen correctamente.

Si en el futuro agregas más modelos, expórtalos aquí.
"""

from .models import (
    # Generador por IA:
    CursoGeneracion, 
    LeccionGeneracion,
    PaginaGeneracion,
    BloqueGeneracion,
    PreguntaGeneracion,
    ExamenGeneracion,
    
    # Usados por la UI y la Base de Datos
    CursoModel,
    LeccionModel,
    PaginaModel,
    BloqueModel,
    PreguntaModel,
    ExamenModel)

__all__ = [
    "CursoGeneracion",
    "LeccionGeneracion",
    "ContenidoGeneracion",
    "BloqueGeneracion",
    "PreguntaGeneracion",
    "ExamenGeneracion",
    
    "CursoModel",
    "LeccionModel",
    "PaginaModel",
    "BloqueModel",
    "PreguntaModel",
    "ExamenModel"
]

