from __future__ import annotations

from typing import Optional

from models.models import CursoModel, LeccionModel
from services.ai_service import GestorDeIA
from services.database import BaseDatosProyecto
from services.repositories.curso_repository import CursoRepository


class CrearCursoController:
    """
    1. Llama a la IA (GestorDeIA) para generar titulo/descripcion/lecciones.
    2. Convierte la respuesta en un CursoModel con sus LeccionModel.
    3. Lo persiste mediante CursoRepository.
    """

    def __init__(self, repo_cursos: CursoRepository, gestor_ia: GestorDeIA):
        self.repo_cursos = repo_cursos
        self.gestor_ia = gestor_ia

    @classmethod
    def desde_bd(cls, db: BaseDatosProyecto) -> CrearCursoController:
        """Arma el controller usando la api_key del perfil guardado en la BD.

        Lanza ValueError si no hay una API key válida (lo valida GestorDeIA).
        """
        perfil = db.obtener_perfil()  # (nombre, token) | None
        api_key = perfil[1] if perfil else None
        return cls(CursoRepository(db), GestorDeIA(api_key=api_key))

    # ── Flujo principal ───────────────────────────────────────────────────────

    def crear_curso(self, texto: str, ruta: Optional[str] = None) -> Optional[CursoModel]:
        """Genera el curso con IA, lo guarda y lo devuelve con su id asignado.

        Devuelve None si la IA no generó un curso. Si falla el guardado,
        propaga RepositorioError (no devuelve un curso sin persistir).
        """
        curso_ia = self.gestor_ia.generar_curso(fuente=texto, ruta=ruta)
        if not curso_ia:
            print("[CrearCursoController] La IA no devolvió un curso.")
            return None

        lecciones = [
            LeccionModel(
                titulo=le.titulo,
                resumen=le.resumen,
                posicion=pos,
                estado="locked",
                paginas=[],
            )
            for pos, le in enumerate(curso_ia.lecciones or [])
        ]
        # La primera lección es la actual (desbloqueada)
        if lecciones:
            lecciones[0].estado = "current"

        curso = CursoModel(
            titulo=curso_ia.titulo_curso,
            descripcion=curso_ia.descripcion_curso,
            fuente=texto,
            lecciones=lecciones,
        )

        # Curso + lecciones en una sola transacción
        curso.id = self.repo_cursos.guardar(curso)
        return curso
