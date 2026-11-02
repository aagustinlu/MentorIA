from __future__ import annotations

import sqlite3
from pathlib import Path
import sys
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.models import LeccionModel
from services.database import BaseDatos


class LeccionRepository:

    def __init__(self, db: BaseDatos):
        self.db = db

    def guardar(self, curso_id: int, posicion: int, titulo: str, resumen: str) -> int | bool:
        """Inserta una lección y devuelve su id."""
        sql = """
            INSERT INTO lecciones (curso_id, position, titulo, summary, estado)
            VALUES (?, ?, ?, ?, 'locked')
        """
        try:
            with self.db._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql, (curso_id, posicion, titulo, resumen))
                conexion.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"[LeccionRepository] Error al guardar lección: {e}")
            return False

    def obtener_lecciones(self, curso_id: int) -> list[LeccionModel]:
        """Devuelve lecciones de un curso con estado derivado de lesson_progress."""
        sql = """
            SELECT
                l.id,
                l.position,
                l.titulo,
                l.summary,
                COALESCE(lp.completed, 0) AS completed
            FROM lecciones l
            LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id
            WHERE l.curso_id = ?
            ORDER BY l.position ASC
        """
        try:
            with self.db._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql, (curso_id,))
                rows = cursor.fetchall()

                primera_incompleta = next(
                    (r[0] for r in rows if r[4] == 0), None
                )

                result: list[LeccionModel] = []
                for r in rows:
                    lec_id, position, titulo, summary, completed = r

                    if completed == 1:
                        estado: Literal["completed", "current", "locked"] = "completed"
                    elif lec_id == primera_incompleta:
                        estado = "current"
                    else:
                        estado = "locked"

                    result.append(
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
                return result
        except sqlite3.Error as e:
            print(f"[LeccionRepository] Error al obtener lecciones del curso {curso_id}: {e}")
            return []
