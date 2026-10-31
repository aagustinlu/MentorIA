from __future__ import annotations

from pathlib import Path
import sys
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ai_service import GestorDeIA
from services.database import BaseDatos
from services.repositories.curso_repository import CursoRepository
from ui.cursos.curso import CursoMenu


class CrearCursoControllerRepo:
    """Controller que usa BaseDatos + CursoRepository para la parte de cursos.

    Nota: La persistencia de lecciones/páginas/bloques no está implementada todavía
    en repositorios, así que el UI recibirá el curso generado (modelo Pydantic)
    y al abrirlo se mostrará correctamente como "cargado" en memoria.
    """

    def __init__(self, texto: str, ruta: Optional[str] = None):
        self.ruta = ruta
        self.fuente = texto

        self.db = BaseDatos("storage/sistema_estudios.db")
        self.repo_cursos = CursoRepository(self.db)

        # Si existe token/perfil, se usa para IA. Si no, se crea con api_key=None.
        self.api_key: Optional[str] = None
        try:
            # services/database.py actual no expone obtener_perfil,
            # así que lo dejamos opcional.
            if hasattr(self.db, "obtener_perfil"):
                perfil = self.db.obtener_perfil()
                self.api_key = perfil[1] if perfil else None
        except Exception:
            self.api_key = None

    def crear_curso(self):
        curso = self.generar_curso_ia()
        if not curso:
            return None

        # Persistimos el curso (título/descr/fuente). Guardamos también lecciones
        # como parte del modelo, pero el repo actual carga lecciones desde DB.
        # Aún no persistimos lecciones desde aquí.
        self.repo_cursos.guardar(curso_to_persistir(curso, self.fuente))
        return curso

    def generar_curso_ia(self):
        gestor = GestorDeIA(api_key=self.api_key)  # api_key puede ser None si no usas IA

        if self.ruta:
            return gestor.generar_curso(fuente=self.fuente, ruta=self.ruta)
        return gestor.generar_curso(fuente=self.fuente)

    def mostrar_curso(self, widget=None):
        curso = self.crear_curso()
        if curso:
            CursoMenu(curso)


def curso_to_persistir(curso, fuente: str):
    """Normaliza el modelo que devuelve la IA a CursoModel del dominio.

    La IA devuelve CursoGeneracion (titulo_curso/descripcion_curso/lecciones),
    mientras que CursoModel usa (titulo/descripcion/fuente/lecciones).
    """

    # Evitamos import circular; CursoMenu ya normaliza dict/model si corresponde.
    from models.models import CursoModel, LeccionModel

    lecciones_model: list[LeccionModel] = []
    for le in getattr(curso, "lecciones", []) or []:
        lecciones_model.append(
            LeccionModel(
                titulo=getattr(le, "titulo", ""),
                resumen=getattr(le, "resumen", ""),
                posicion=0,
                estado="locked",
                paginas=[],
            )
        )

    return CursoModel(
        titulo=getattr(curso, "titulo_curso", ""),
        descripcion=getattr(curso, "descripcion_curso", ""),
        fuente=fuente,
        lecciones=lecciones_model,
    )

