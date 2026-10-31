from typing import Literal, Optional
import codecs
from pydantic import BaseModel, Field, field_validator, ValidationInfo


# ==========================================================
# Modelos utilizados por la IA
# ==========================================================

class BloqueGeneracion(BaseModel):

    tipo: Literal[
        "texto",
        "codigo",
        "titulo",
        "formula",
    ]

    contenido: str = Field(
        description="HTML enriquecido que luego será mostrado en la interfaz."
    )


class PaginaGeneracion(BaseModel):

    bloques: list[BloqueGeneracion] = Field(
        description="Bloques que componen la página."
    )


class ContenidoLeccionGeneracion(BaseModel):

    paginas: list[PaginaGeneracion] = Field(
        description="Contenido completo de la lección."
    )


class LeccionGeneracion(BaseModel):

    titulo: str = Field(
        description="Nombre de la lección."
    )

    resumen: str = Field(
        description="Resumen de la lección."
    )

    paginas: Optional[list[PaginaGeneracion]] = Field(
        default=None,
        description="Contenido de la lección. Solo se utiliza cuando se genera un curso completo."
    )


class CursoGeneracion(BaseModel):

    titulo_curso: str = Field(
        description="Nombre del curso."
    )

    descripcion_curso: str = Field(
        description="Descripción general del curso."
    )

    lecciones: list[LeccionGeneracion]


class PreguntaGeneracion(BaseModel):

    leccion_numero: int = Field(
        description="Número (empezando en 1) de la lección del material de la que sale la pregunta."
    )

    enunciado: str = Field(
        description="Texto de la pregunta."
    )

    opciones: list[str] = Field(
        description=(
            "Opciones de respuesta: entre 3 y 5, idealmente 4. "
            "Texto plano, sin letras ni numeración."
        )
    )

    indice_correcta: int = Field(
        description="Posición (empezando en 0) de la única opción correcta dentro de 'opciones'."
    )

    explicacion: str = Field(
        description="Explicación breve de por qué esa opción es la correcta."
    )


class ExamenGeneracion(BaseModel):

    preguntas: list[PreguntaGeneracion]


# ==========================================================
# Modelos del dominio (Base de datos + UI)
# ==========================================================


class BloqueModel(BaseModel):

    id: Optional[int] = Field(
        default=None,
        description="ID del bloque en la base de datos."
    )

    posicion: int = Field(
        description="Posición del bloque dentro de la página."
    )

    tipo: Literal[
        "texto",
        "codigo",
        "titulo",
        "formula",
    ]

    contenido: str = Field(
        description="HTML enriquecido mostrado por PyQt6."
    )

    @field_validator("contenido", mode="before")
    @classmethod
    def limpiar_escapes(cls, v: str, info: ValidationInfo) -> str:
        if isinstance(v, str):
            # 1. Si el texto viene con barras literales para saltos de línea o comillas (\\n, \\\")
            if r"\n" in v or r'\"' in v or r"\'" in v:
                try:
                    v = codecs.decode(v, "unicode_escape")
                except Exception:
                    pass
            
            # 2. Si el bloque es de tipo 'codigo', limpiamos cualquier etiqueta HTML residual 
            # como <code>, </code>, <pre>, </pre> que haya generado el LLM o la fuente de datos
            tipo_bloque = info.data.get("tipo")
            if tipo_bloque == "codigo":
                # Elimina etiquetas HTML envolventes si vinieron incluidas
                import re
                v = re.sub(r'</?(code|pre)[^>]*>', '', v, flags=re.IGNORECASE).strip()

        return v


class PaginaModel(BaseModel):

    id: Optional[int] = Field(
        default=None,
        description="ID de la página."
    )

    posicion: int = Field(
        description="Posición de la página dentro de la lección."
    )

    bloques: list[BloqueModel]


class LeccionModel(BaseModel):

    id: Optional[int] = Field(
        default=None,
        description="ID de la lección."
    )

    curso_id: Optional[int] = Field(
        default=None,
        description="Curso al que pertenece."
    )

    titulo: str = Field(
        description="Nombre de la lección."
    )

    resumen: str = Field(
        description="Resumen de la lección."
    )

    posicion: int = Field(
        description="Orden de la lección dentro del curso."
    )

    estado: Literal[
        "completed",
        "current",
        "locked",
    ]

    paginas: list[PaginaModel] = Field(
        default_factory=list
    )


class CursoModel(BaseModel):

    id: Optional[int] = Field(
        default=None,
        description="ID del curso."
    )

    titulo: str = Field(
        description="Nombre del curso."
    )

    descripcion: str = Field(
        description="Descripción del curso."
    )

    created_at: Optional[str] = Field(
        default=None,
        description="Fecha de creación."
    )

    fuente: str = Field(
        description="Material utilizado para generar el curso."
    )

    lecciones: list[LeccionModel] = Field(
        default_factory=list
    )


class PreguntaModel(BaseModel):

    id: Optional[int] = Field(
        default=None,
        description="ID de la pregunta en la base de datos."
    )

    posicion: int = Field(
        description="Posición de la pregunta dentro del examen."
    )

    leccion_id: Optional[int] = Field(
        default=None,
        description="Lección de la que sale la pregunta."
    )

    leccion_titulo: Optional[str] = Field(
        default=None,
        description="Título de esa lección (para sugerir qué repasar)."
    )

    enunciado: str

    opciones: list[str]

    correcta: int = Field(
        description="Índice (desde 0) de la opción correcta dentro de 'opciones'."
    )

    explicacion: str = ""


class ExamenModel(BaseModel):

    id: Optional[int] = Field(
        default=None,
        description="ID del examen."
    )

    curso_id: int

    titulo: str

    preguntas: list[PreguntaModel] = Field(
        default_factory=list
    )
