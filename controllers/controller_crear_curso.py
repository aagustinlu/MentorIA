from __future__ import annotations

from pathlib import Path
import sys
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ai_service import GestorDeIA
from services.database import BaseDatosProyecto
from services.repositories.curso_repository import CursoRepository
from models.models import CursoModel, LeccionModel
from ui.cursos.curso import CursoMenu


class CrearCursoController:
    """
    Controller principal para crear un curso:
    1. Llama a la IA (GestorDeIA) para generar titulo/descripcion/lecciones.
    2. Persiste el curso + lecciones en la BD mediante CursoRepository.
    3. Devuelve un CursoModel listo para mostrarse en la UI.
    """

    def __init__(self, texto: str, ruta: Optional[str] = None):
        self.ruta = ruta
        self.fuente = texto

        self.db = BaseDatosProyecto("storage/sistema_estudios.db")
        self.repo_cursos = CursoRepository(self.db)

        # Leer api_key del perfil guardado en BD
        perfil = self.db.obtener_perfil()          # (nombre, token) | None
        self.api_key: Optional[str] = perfil[1] if perfil else None

    # ── Flujo principal ───────────────────────────────────────────────────────

    def crear_curso(self) -> Optional[CursoModel]:
        """Genera el curso con IA, lo persiste en BD y devuelve el CursoModel."""

        curso_ia = self._generar_curso_ia()
        if not curso_ia:
            print("[CrearCursoController] La IA no devolvió un curso.")
            return None

        # Convertir CursoGeneracion → CursoModel con sus LeccionModel
        lecciones: list[LeccionModel] = [
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

        curso_model = CursoModel(
            titulo=curso_ia.titulo_curso,
            descripcion=curso_ia.descripcion_curso,
            fuente=self.fuente,
            lecciones=lecciones,
        )

        # Guardar en BD (curso + lecciones en una sola transacción)
        curso_id = self.repo_cursos.guardar(curso_model)
        if isinstance(curso_id, int):
            curso_model.id = curso_id
            print(f"[CrearCursoController] Curso guardado con id={curso_id}, "
                  f"{len(lecciones)} lecciones.")
        else:
            print("[CrearCursoController] Error al guardar el curso en BD.")

        return curso_model

    def mostrar_curso(self, widget) -> None:
        """Crea el curso y abre la ventana de la UI."""
        curso = self.crear_curso()
        if curso:
            
            
            
            self._ventana_curso = CursoMenu(curso)
            self._ventana_curso.show()

    # ── Generación IA ─────────────────────────────────────────────────────────

    def _generar_curso_ia(self):
        gestor = GestorDeIA(api_key=self.api_key)
        if self.ruta:
            return gestor.generar_curso(fuente=self.fuente, ruta=self.ruta)
        return gestor.generar_curso(fuente=self.fuente)
