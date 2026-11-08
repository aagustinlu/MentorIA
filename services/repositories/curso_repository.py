from __future__ import annotations

import sqlite3
from pathlib import Path
import sys
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.models import CursoModel, LeccionModel
from services.database import BaseDatosProyecto


class RepositorioError(Exception):
    """Error al persistir datos en la BD (sqlite3.Error)."""


class CursoRepository:
    """Repository para persistir y consultar cursos + lecciones."""

    def __init__(self, bd: BaseDatosProyecto):
        self.db = bd

    # Cursos

    def guardar(self, curso: CursoModel) -> int:
        """
        Inserta el curso Y sus lecciones.

        Devuelve el curso_id generado. Lanza RepositorioError si falla.
        """
        
        sql_curso = "INSERT INTO cursos (titulo, descripcion, fuente) VALUES (?, ?, ?)"
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql_curso, (curso.titulo, curso.descripcion, curso.fuente))
                curso_id = cursor.lastrowid

                # Guardar lecciones dentro de la misma transacción
                for posicion, leccion in enumerate(curso.lecciones or []):
                    cursor.execute(
                        """INSERT INTO lecciones
                               (curso_id, position, titulo, summary, estado)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            curso_id,
                            posicion,
                            leccion.titulo,
                            leccion.resumen,
                            leccion.estado or "locked",
                        ),
                    )

                conexion.commit()
                return curso_id
        except sqlite3.Error as e:
            raise RepositorioError(f"No se pudo guardar el curso: {e}") from e

    def obtener(self, id: int) -> Optional[CursoModel]:
        """Lee un curso con todas sus lecciones desde la BD."""
        
        sql = """
            SELECT id, titulo, descripcion, fuente, created_at
            FROM cursos
            WHERE id = ?
        """
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql, (id,))
                row = cursor.fetchone()
                if not row:
                    return None

                curso_id, titulo, descripcion, fuente, created_at = row
                lecciones = self._obtener_lecciones(conexion, curso_id)

                return CursoModel(
                    id=curso_id,
                    titulo=titulo,
                    descripcion=descripcion,
                    fuente=fuente,
                    created_at=str(created_at) if created_at is not None else None,
                    lecciones=lecciones,
                )
        except sqlite3.Error as e:
            print(f"[CursoRepository] Error al obtener curso {id}: {e}")
            return None

    def obtener_lista(self) -> list[dict]:
        """Lista cursos disponibles (id, titulo, descripcion)."""
        sql = "SELECT id, titulo, descripcion FROM cursos ORDER BY created_at DESC"
        try:
            with self.db.conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()
                return [{"id": r[0], "titulo": r[1], "descripcion": r[2]} for r in rows]
        except sqlite3.Error as e:
            print(f"[CursoRepository] Error al listar cursos: {e}")
            return []

    # ── Lecciones ─────────────────────────────────────────────────────────────

    def _obtener_lecciones(
        self, conexion: sqlite3.Connection, curso_id: int
    ) -> list[LeccionModel]:
        """Lee lecciones de un curso y calcula su estado (completed/current/locked)."""
        sql = """
            SELECT
                l.id,
                l.position,
                l.titulo,
                l.summary,
                l.estado,
                COALESCE(lp.completed, 0) AS completed
            FROM lecciones l
            LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id
            WHERE l.curso_id = ?
            ORDER BY l.position ASC, l.id ASC
        """
        cursor = conexion.cursor()
        cursor.execute(sql, (curso_id,))
        rows = cursor.fetchall()

        # Derivar estado real desde lesson_progress
        primera_incompleta = None
        for r in rows:
            if r[5] == 0:          # completed == 0
                primera_incompleta = r[0]
                break

        lecciones: list[LeccionModel] = []
        for r in rows:
            lec_id, position, titulo, summary, estado_db, completed = r

            if completed == 1:
                estado = "completed"
            elif lec_id == primera_incompleta:
                estado = "current"
            else:
                estado = "locked"

            lecciones.append(
                LeccionModel(
                    id=lec_id,
                    curso_id=curso_id,
                    titulo=titulo,
                    resumen=summary or "",
                    posicion=position or 0,
                    estado=estado,
                    paginas=[],
                )
            )
        return lecciones
