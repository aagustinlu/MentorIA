import json
import secrets
from datetime import datetime
import sqlite3
from pathlib import Path

from models.models import CertificadoModel, CursoModel, ExamenModel, LeccionModel, PreguntaModel


# Modelos auxiliares para estado de lecciones (compatibles con la UI)
from pydantic import BaseModel
from typing import Literal, List


class LeccionConEstado(BaseModel):
    id: int
    position: int
    titulo: str
    estado: Literal["completed", "current", "locked"]


class LeccionesCursoConEstado(BaseModel):
    curso_id: int
    lecciones: List[LeccionConEstado]


class BaseDatosProyecto:

    def __init__(self, ruta_bd: str):
        self.ruta_completa = Path(ruta_bd)
        # Aseguramos que la carpeta donde se guardará el archivo exista
        self.ruta_completa.parent.mkdir(parents=True, exist_ok=True)
        # Creamos las tablas iniciales
        self.inicializar_tablas()

    def _conectar(self):
        """Abre la conexión con SQLite."""
        return sqlite3.connect(str(self.ruta_completa))

    def conectar(self) -> sqlite3.Connection:
        """Abre una conexión con SQLite (API pública para los repositories)."""
        return self._conectar()

    def inicializar_tablas(self):
        """Crea las tablas si no existen y actualiza columnas faltantes."""
        
        # 1. Tu lista de creación básica (se ejecuta de forma segura con IF NOT EXISTS)
        sql_usuario_tablas = [
            '''
            CREATE TABLE IF NOT EXISTS perfil_usuario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                token TEXT NOT NULL
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS cursos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descripcion TEXT,
                fuente TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS lecciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curso_id INTEGER,
                position INTEGER,
                titulo TEXT,
                summary TEXT,
                content TEXT,
                estado TEXT DEFAULT 'locked',
                FOREIGN KEY(curso_id) REFERENCES cursos(id)
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS paginas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                leccion_id INTEGER NOT NULL,
                posicion INTEGER NOT NULL,
                FOREIGN KEY(leccion_id) REFERENCES lecciones(id)
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS bloques (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pagina_id INTEGER NOT NULL,
                posicion INTEGER NOT NULL,
                tipo TEXT,
                contenido TEXT,
                FOREIGN KEY(pagina_id) REFERENCES paginas(id)
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS lesson_progress (
                lesson_id INTEGER,
                completed INTEGER DEFAULT 0,
                mastery INTEGER DEFAULT 0,
                FOREIGN KEY(lesson_id) REFERENCES lecciones(id)
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY,
                course_id INTEGER,
                titulo TEXT
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS exam_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                posicion INTEGER NOT NULL,
                leccion_id INTEGER,
                enunciado TEXT NOT NULL,
                opciones TEXT NOT NULL,
                correcta INTEGER NOT NULL,
                explicacion TEXT,
                FOREIGN KEY(exam_id) REFERENCES exams(id)
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS ajustes (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS exam_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                aciertos INTEGER NOT NULL,
                total INTEGER NOT NULL,
                aprobado INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(exam_id) REFERENCES exams(id)
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS certificados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL UNIQUE,
                codigo TEXT NOT NULL UNIQUE,
                nombre TEXT NOT NULL,
                curso_titulo TEXT NOT NULL,
                aciertos INTEGER NOT NULL,
                total INTEGER NOT NULL,
                emitido_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(course_id) REFERENCES cursos(id)
            );
            ''',
        ]

        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                
                # Crear tablas bases inexistentes
                for stmt in sql_usuario_tablas:
                    cursor.execute(stmt)
                
                # 2. SISTEMA DE VERIFICACIÓN / MIGRACIÓN INTERNA
                # Si en el futuro agregás 'duracion' a cursos o 'score' a exams, los agregás acá:
                columnas_requeridas = {
                    "cursos": [
                        ("fuente", "TEXT"),
                        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
                    ],
                    "lecciones": [
                        ("estado", "TEXT DEFAULT 'locked'")
                    ],
                    "exams": [
                        ("titulo", "TEXT")
                    ]
                }

                for tabla, columnas in columnas_requeridas.items():
                    # Obtenemos las columnas reales que ya existen en la BD del usuario
                    cursor.execute(f"PRAGMA table_info({tabla});")
                    columnas_existentes = [info[1] for info in cursor.fetchall()]

                    for nombre_col, tipo_col in columnas:
                        if nombre_col not in columnas_existentes:
                            # La columna no existe en la BD vieja: se agrega dinámicamente sin romper nada
                            cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre_col} {tipo_col};")
                            print(f"Migración: Columna '{nombre_col}' añadida con éxito a la tabla '{tabla}'.")

                conexion.commit()
                print("Estructura de la base de datos verificada y actualizada correctamente.")
                
        except sqlite3.Error as e:
            print(f"Error al verificar o crear las tablas: {e}")


    """Guardado de Datos"""
    
    # --- Guardar Cursos ---
    
    def guardar_curso(self, titulo: str, descripcion: str, fuente: str):
        sql = "INSERT INTO cursos (titulo, descripcion, fuente) VALUES (?, ?, ?)"
    
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql, 
                               (titulo, descripcion, fuente))
                
                conexion.commit()

                curso_id = cursor.lastrowid
                
                return curso_id
            
        except sqlite3.Error as e:
            print(f"Error al crear curso: {e}")
            return False
        
    
    # --- Guardar Leccion ---
     
    def guardar_leccion(self, curso_id, position, titulo, summary):
        sql = "INSERT INTO lecciones (curso_id, position, titulo, summary) VALUES (?, ?, ?, ?)"
    
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql, 
                               (curso_id, position, titulo, summary))
                conexion.commit()
                
                return True
        except sqlite3.Error as e:
            print(f"Error al crear leccion: {e}")
            return False
        
        
    # --- FUNCIONES PARA EL USUARIO ---

    def registrar_usuario(self, nombre: str, token: str) -> bool:
        """Guarda el nombre y token del usuario por primera vez."""
        
        sql = "INSERT INTO perfil_usuario (nombre, token) VALUES (?, ?)"
        
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql, (nombre, token))
                conexion.commit()
                print(f"Usuario '{nombre}' registrado con éxito.")
                return True
        except sqlite3.Error as e:
            print(f"Error al registrar usuario: {e}")
            return False

    def modificar_perfil(self, nuevo_nombre: str, nuevo_token: str, id_usuario: int = 1) -> bool:
        """Permite al usuario modificar su nombre o su token más adelante."""
        sql = "UPDATE perfil_usuario SET nombre = ?, token = ? WHERE id = ?"
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql, (nuevo_nombre, nuevo_token, id_usuario))
                conexion.commit()
                print("Perfil actualizado correctamente.")
                return True
        except sqlite3.Error as e:
            print(f"Error al actualizar perfil: {e}")
            return False

    def cambiar_nombre_usuario(self, nuevo_nombre: str) -> bool:
        """Modifica únicamente el nombre del usuario manteniendo el token actual."""
        perfil_actual = self.obtener_perfil()
        
        if perfil_actual:
            token_actual = perfil_actual[1] # Mantenemos el token viejo
            
            # Usamos self para llamar al método interno de la clase
            exito = self.modificar_perfil(nuevo_nombre=nuevo_nombre, nuevo_token=token_actual, id_usuario=1)
            
            if exito:
                print(f"¡Nombre cambiado a '{nuevo_nombre}' con éxito!")
                return True
            else:
                print("No se pudo actualizar el nombre en la base de datos.")
                return False
        else:
            print("Error: No se encontró ningún usuario registrado para modificar.")
            return False
        
    def cambiar_apikey(self, nueva_apikey: str) -> bool:
        """Modifica únicamente el nombre del usuario manteniendo el token actual."""
        perfil_actual = self.obtener_perfil()
        
        if perfil_actual:
            nombre_actual = perfil_actual[0] # Mantenemos el token viejo
            
            # Usamos self para llamar al método interno de la clase
            exito = self.modificar_perfil(nuevo_nombre = nombre_actual, nuevo_token=nueva_apikey, id_usuario=1)
            
            if exito:
                print(f"Api Key cambiada a '{nueva_apikey}' con éxito!")
                return True
            else:
                print("No se pudo actualizar la api key en la base de datos.")
                return False
        else:
            print("Error: No se encontró ningún usuario registrado para modificar.")
            return False
    
        
    # --- Ajustes de la aplicación (tema, etc.) ---

    def obtener_ajuste(self, clave: str, defecto: str | None = None) -> str | None:
        """Devuelve el valor guardado para `clave`, o `defecto` si no existe."""
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute("SELECT valor FROM ajustes WHERE clave = ?", (clave,))
                fila = cursor.fetchone()
                return fila[0] if fila else defecto
        except sqlite3.Error as e:
            print(f"Error al leer el ajuste '{clave}': {e}")
            return defecto

    def guardar_ajuste(self, clave: str, valor: str) -> bool:
        """Crea o actualiza un ajuste de la aplicación."""
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO ajustes (clave, valor) VALUES (?, ?)",
                    (clave, valor),
                )
                conexion.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error al guardar el ajuste '{clave}': {e}")
            return False

    # --- Lectura de los datos
    
    def obtener_perfil(self):
        """Devuelve los datos del usuario logueado."""
        sql = "SELECT nombre, token FROM perfil_usuario LIMIT 1"
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql)
                return cursor.fetchone() # Devuelve una tupla (nombre, token) o None
        except sqlite3.Error as e:
            print(f"Error al obtener perfil: {e}")
            return None
        
    def obtener_curso(self, id: int) -> CursoModel | None:
        sql = """
            SELECT id, titulo, descripcion, fuente, created_at
            FROM cursos
            WHERE id = ?
        """
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql, (id,))
                row = cursor.fetchone()
                if not row:
                    return None

                curso_id, titulo, descripcion, fuente, created_at = row

                # Obtener lecciones con estado derivado desde lesson_progress
                lecciones_estado = self.obtener_lecciones_curso(curso_id)
                lecciones_model: list[LeccionModel] = []
                if lecciones_estado and lecciones_estado.lecciones:
                    for i, l in enumerate(lecciones_estado.lecciones):
                        lecciones_model.append(
                            LeccionModel(
                                id=l.id,
                                curso_id=curso_id,
                                titulo=l.titulo,
                                resumen="",
                                posicion=l.position,
                                estado=l.estado,
                                paginas=[],
                            )
                        )

                return CursoModel(
                    id=curso_id,
                    titulo=titulo,
                    descripcion=descripcion,
                    fuente=fuente,
                    created_at=str(created_at) if created_at is not None else None,
                    lecciones=lecciones_model,
                )
        except sqlite3.Error as e:
            print(f"Error al obtener curso: {e}")
            return None

    def obtener_cursos_usuario(self):
        """Devuelve los cursos disponibles. (No existe user_id en schema actual, por eso se listan todos)."""
        sql = "SELECT id, titulo, descripcion FROM cursos ORDER BY created_at DESC"
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()  # (id, titulo, descripcion)
                return [
                    {"id": r[0], "titulo": r[1], "descripcion": r[2]} for r in rows
                ]
        except sqlite3.Error as e:
            print(f"Error al obtener cursos del usuario: {e}")
            return []

    def eliminar_curso(self, curso_id: int) -> bool:
        """
        Elimina un curso y TODO lo que depende de él (lecciones, páginas,
        bloques, progreso y exámenes) en una sola transacción.

        La BD no usa ON DELETE CASCADE, así que se borra a mano de hijos a padre.
        Si algo falla se hace rollback y el curso queda intacto.
        Devuelve True si el curso existía y fue eliminado.
        """
        ids_lecciones = "SELECT id FROM lecciones WHERE curso_id = ?"
        ids_paginas = f"SELECT id FROM paginas WHERE leccion_id IN ({ids_lecciones})"

        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()

                cursor.execute(
                    f"DELETE FROM bloques WHERE pagina_id IN ({ids_paginas})",
                    (curso_id,),
                )
                cursor.execute(
                    f"DELETE FROM paginas WHERE leccion_id IN ({ids_lecciones})",
                    (curso_id,),
                )
                cursor.execute(
                    f"DELETE FROM lesson_progress WHERE lesson_id IN ({ids_lecciones})",
                    (curso_id,),
                )
                cursor.execute("DELETE FROM lecciones WHERE curso_id = ?", (curso_id,))
                self._borrar_examenes_curso(cursor, curso_id)
                cursor.execute("DELETE FROM certificados WHERE course_id = ?", (curso_id,))
                cursor.execute("DELETE FROM cursos WHERE id = ?", (curso_id,))
                eliminado = cursor.rowcount > 0

                conexion.commit()
                return eliminado
        except sqlite3.Error as e:
            print(f"[BD] Error al eliminar curso {curso_id}: {e}")
            return False

    def obtener_lecciones_curso(self, curso_id: int):
        """Devuelve lecciones con estado como Pydantic Model.

        Prioridad:
        1) lesson_progress.completed => estado derived (completed/current/locked)
        """

        sql = """
            SELECT
                l.id,
                l.position,
                l.titulo,
                COALESCE(
                    (SELECT MAX(lp.completed)
                       FROM lesson_progress lp
                      WHERE lp.lesson_id = l.id),
                    0
                ) as completed
            FROM lecciones l
            WHERE l.curso_id = ?
            ORDER BY l.position ASC, l.id ASC
        """
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql, (curso_id,))
                rows = cursor.fetchall()

                # Derived estado simple según completadas.
                # - Si está completed=1 => completed
                # - Si no => current (primera no completada) o locked
                lecciones_base = [
                    {"id": r[0], "position": r[1], "titulo": r[2], "completed": r[3]} for r in rows
                ]

                # Regla: la primera lección NO completada es la actual (azul).
                #  - todas las anteriores  -> completed (verde, habilitadas)
                #  - todas las posteriores -> locked    (gris, bloqueadas)
                indice_actual = next(
                    (i for i, le in enumerate(lecciones_base) if le["completed"] == 0),
                    len(lecciones_base),   # si todas están completas, no hay actual
                )

                result: list[LeccionConEstado] = []
                for i, le in enumerate(lecciones_base):
                    if i < indice_actual:
                        estado = "completed"
                    elif i == indice_actual:
                        estado = "current"
                    else:
                        estado = "locked"

                    result.append(
                        LeccionConEstado(
                            id=le["id"],
                            position=le["position"],
                            titulo=le["titulo"],
                            estado=estado,
                        )
                    )

                return LeccionesCursoConEstado(
                    curso_id=curso_id,
                    lecciones=result,
                )

        except sqlite3.Error as e:
            print(f"Error al obtener lecciones del curso {curso_id}: {e}")
            return LeccionesCursoConEstado(curso_id=curso_id, lecciones=[])



    def contar_progreso_cursos(self):
        """Cuenta cursos completados/pendientes a partir de lesson_progress."""
        cursos = self.obtener_cursos_usuario()
        total_completados = 0
        total_pendientes = 0
        total_lecciones_completadas = 0

        for curso in cursos:
            lecciones_model = self.obtener_lecciones_curso(curso["id"])
            if not lecciones_model or not lecciones_model.lecciones:
                # Curso sin lecciones => pendiente
                total_pendientes += 1
                continue

            total_lecciones_completadas += sum(
                1 for l in lecciones_model.lecciones if l.estado == "completed"
            )

            # Completado si todas las lecciones están completed Y el examen final está aprobado
            if (
                all(l.estado == "completed" for l in lecciones_model.lecciones)
                and self.examen_aprobado(curso["id"])
            ):
                total_completados += 1
            else:
                total_pendientes += 1

        return {
            "cursos_completados": total_completados,
            "cursos_pendientes": total_pendientes,
            "lecciones_completadas": total_lecciones_completadas,
        }

    # ── Contenido de lecciones (paginas + bloques) ────────────────────────────

    def leccion_tiene_contenido(self, leccion_id: int) -> bool:
        """Devuelve True si la lección ya tiene páginas guardadas en la BD."""
        sql = "SELECT COUNT(*) FROM paginas WHERE leccion_id = ?"
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql, (leccion_id,))
                count = cursor.fetchone()[0]
                return count > 0
        except sqlite3.Error as e:
            print(f"[BD] Error al verificar contenido de lección {leccion_id}: {e}")
            return False

    def guardar_contenido_leccion(self, leccion_id: int, paginas) -> bool:
        """
        Guarda las páginas y bloques de una lección generada por la IA.
        'paginas' es una lista de PaginaGeneracion (con campo .bloques).
        Borra el contenido previo antes de insertar (idempotente).
        """
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()

                # Borrar contenido anterior si existía
                cursor.execute(
                    "DELETE FROM bloques WHERE pagina_id IN "
                    "(SELECT id FROM paginas WHERE leccion_id = ?)",
                    (leccion_id,),
                )
                cursor.execute("DELETE FROM paginas WHERE leccion_id = ?", (leccion_id,))

                for pos_pag, pagina in enumerate(paginas):
                    cursor.execute(
                        "INSERT INTO paginas (leccion_id, posicion) VALUES (?, ?)",
                        (leccion_id, pos_pag),
                    )
                    pagina_id = cursor.lastrowid

                    bloques = getattr(pagina, "bloques", getattr(pagina, "contenido", []))
                    for pos_bloque, bloque in enumerate(bloques):
                        cursor.execute(
                            "INSERT INTO bloques (pagina_id, posicion, tipo, contenido) "
                            "VALUES (?, ?, ?, ?)",
                            (
                                pagina_id,
                                pos_bloque,
                                bloque.tipo,
                                bloque.contenido,
                            ),
                        )

                conexion.commit()
                print(f"[BD] Contenido de lección {leccion_id} guardado "
                      f"({len(paginas)} páginas).")
                return True
        except sqlite3.Error as e:
            print(f"[BD] Error al guardar contenido de lección {leccion_id}: {e}")
            return False

    def obtener_contenido_leccion(self, leccion_id: int):
        """
        Devuelve el contenido de la lección como LeccionModel con paginas y bloques,
        o None si no hay contenido guardado.
        """
        from models.models import LeccionModel, PaginaModel, BloqueModel

        sql_info = "SELECT id, titulo, summary, position FROM lecciones WHERE id = ?"
        sql_paginas = "SELECT id, posicion FROM paginas WHERE leccion_id = ? ORDER BY posicion ASC"
        sql_bloques = (
            "SELECT id, posicion, tipo, contenido FROM bloques "
            "WHERE pagina_id = ? ORDER BY posicion ASC"
        )
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()

                cursor.execute(sql_info, (leccion_id,))
                row = cursor.fetchone()
                if not row:
                    return None

                lec_id, titulo, summary, position = row

                cursor.execute(sql_paginas, (leccion_id,))
                paginas_rows = cursor.fetchall()
                if not paginas_rows:
                    return None

                paginas: list[PaginaModel] = []
                for pag_id, pag_pos in paginas_rows:
                    cursor.execute(sql_bloques, (pag_id,))
                    bloques_rows = cursor.fetchall()
                    bloques = [
                        BloqueModel(
                            id=b[0],
                            posicion=b[1],
                            tipo=b[2],
                            contenido=b[3],
                        )
                        for b in bloques_rows
                    ]
                    paginas.append(
                        PaginaModel(id=pag_id, posicion=pag_pos, bloques=bloques)
                    )

                return LeccionModel(
                    id=lec_id,
                    titulo=titulo,
                    resumen=summary or "",
                    posicion=position or 0,
                    estado="current",
                    paginas=paginas,
                )
        except sqlite3.Error as e:
            print(f"[BD] Error al obtener contenido de lección {leccion_id}: {e}")
            return None

    def obtener_info_leccion(self, leccion_id: int):
        """Devuelve (titulo, summary, curso_id, fuente_curso) para una lección."""
        sql = """
            SELECT l.titulo, l.summary, l.curso_id, c.fuente
            FROM lecciones l
            JOIN cursos c ON c.id = l.curso_id
            WHERE l.id = ?
        """
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                cursor.execute(sql, (leccion_id,))
                return cursor.fetchone()  # (titulo, summary, curso_id, fuente) | None
        except sqlite3.Error as e:
            print(f"[BD] Error al obtener info lección {leccion_id}: {e}")
            return None

    def completar_leccion(self, leccion_id: int) -> bool:
        """
        Marca como completada la lección ACTUAL de su curso (la que desbloquea
        a la siguiente). Solo se permite completar la lección en estado
        'current': así es imposible saltearse lecciones desde la capa de datos.
        Devuelve True si quedó guardada.
        """
        info = self.obtener_info_leccion(leccion_id)
        if not info:
            return False

        curso_id = info[2]
        lecciones = self.obtener_lecciones_curso(curso_id).lecciones
        actual = next((l for l in lecciones if l.estado == "current"), None)

        if actual is None or actual.id != leccion_id:
            print(f"[BD] La lección {leccion_id} no es la actual; no se puede completar.")
            return False

        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                # lesson_progress no tiene UNIQUE(lesson_id): borramos e insertamos
                cursor.execute("DELETE FROM lesson_progress WHERE lesson_id = ?", (leccion_id,))
                cursor.execute(
                    "INSERT INTO lesson_progress (lesson_id, completed) VALUES (?, 1)",
                    (leccion_id,),
                )
                conexion.commit()
            return True
        except sqlite3.Error as e:
            print(f"[BD] Error al completar lección {leccion_id}: {e}")
            return False

    # ── Evaluación final ──────────────────────────────────────────────────────

    @staticmethod
    def _borrar_examenes_curso(cursor, curso_id: int) -> None:
        """Borra examen(es), preguntas e intentos de un curso (dentro de la transacción del llamador)."""
        ids_examenes = "SELECT id FROM exams WHERE course_id = ?"
        cursor.execute(f"DELETE FROM exam_attempts WHERE exam_id IN ({ids_examenes})", (curso_id,))
        cursor.execute(f"DELETE FROM exam_questions WHERE exam_id IN ({ids_examenes})", (curso_id,))
        cursor.execute("DELETE FROM exams WHERE course_id = ?", (curso_id,))

    def guardar_examen(self, curso_id: int, titulo: str, preguntas, ids_lecciones: list[int],
                       reemplazar: bool = True):
        """
        Guarda el examen generado por la IA.
        'preguntas' es una lista de PreguntaGeneracion; 'leccion_numero' (desde 1)
        se traduce al id real con 'ids_lecciones'. Devuelve el id del examen o None.

        reemplazar=True  -> borra el examen anterior del curso (con sus intentos).
        reemplazar=False -> conserva los exámenes anteriores (y sus intentos): se usa
                            al renovar el examen tras un intento fallido. `obtener_examen`
                            siempre devuelve el más reciente.
        """
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()
                if reemplazar:
                    self._borrar_examenes_curso(cursor, curso_id)

                cursor.execute(
                    "INSERT INTO exams (course_id, titulo) VALUES (?, ?)",
                    (curso_id, titulo),
                )
                examen_id = cursor.lastrowid

                for posicion, p in enumerate(preguntas):
                    n = p.leccion_numero
                    leccion_id = ids_lecciones[n - 1] if 1 <= n <= len(ids_lecciones) else None
                    cursor.execute(
                        "INSERT INTO exam_questions "
                        "(exam_id, posicion, leccion_id, enunciado, opciones, correcta, explicacion) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            examen_id,
                            posicion,
                            leccion_id,
                            p.enunciado,
                            json.dumps(p.opciones, ensure_ascii=False),
                            p.indice_correcta,
                            p.explicacion,
                        ),
                    )

                conexion.commit()
                print(f"[BD] Examen {examen_id} del curso {curso_id} guardado "
                      f"({len(preguntas)} preguntas).")
                return examen_id
        except sqlite3.Error as e:
            print(f"[BD] Error al guardar examen del curso {curso_id}: {e}")
            return None

    def obtener_examen(self, curso_id: int) -> ExamenModel | None:
        """Devuelve el examen del curso con sus preguntas, o None si aún no se generó."""
        sql_examen = "SELECT id, titulo FROM exams WHERE course_id = ? ORDER BY id DESC LIMIT 1"
        sql_preguntas = """
            SELECT q.id, q.posicion, q.leccion_id, l.titulo,
                   q.enunciado, q.opciones, q.correcta, q.explicacion
            FROM exam_questions q
            LEFT JOIN lecciones l ON l.id = q.leccion_id
            WHERE q.exam_id = ?
            ORDER BY q.posicion ASC
        """
        try:
            with self._conectar() as conexion:
                cursor = conexion.cursor()

                cursor.execute(sql_examen, (curso_id,))
                fila = cursor.fetchone()
                if not fila:
                    return None
                examen_id, titulo = fila

                cursor.execute(sql_preguntas, (examen_id,))
                preguntas = [
                    PreguntaModel(
                        id=r[0],
                        posicion=r[1],
                        leccion_id=r[2],
                        leccion_titulo=r[3],
                        enunciado=r[4],
                        opciones=json.loads(r[5]),
                        correcta=r[6],
                        explicacion=r[7] or "",
                    )
                    for r in cursor.fetchall()
                ]
                if not preguntas:
                    return None

                return ExamenModel(
                    id=examen_id,
                    curso_id=curso_id,
                    titulo=titulo or "Evaluación final",
                    preguntas=preguntas,
                )
        except (sqlite3.Error, ValueError) as e:
            print(f"[BD] Error al obtener examen del curso {curso_id}: {e}")
            return None

    def obtener_enunciados_examenes(self, curso_id: int, limite: int = 200) -> dict[int | None, list[str]]:
        """
        Enunciados de todas las preguntas de los exámenes anteriores del curso,
        agrupados por `leccion_id` (None = sin lección). Sirve para pedirle a la IA
        que no los repita al generar un examen nuevo.
        """
        sql = """
            SELECT q.leccion_id, q.enunciado
            FROM exam_questions q
            JOIN exams e ON e.id = q.exam_id
            WHERE e.course_id = ?
            ORDER BY q.id DESC
            LIMIT ?
        """
        agrupados: dict[int | None, list[str]] = {}
        try:
            with self._conectar() as conexion:
                for leccion_id, enunciado in conexion.execute(sql, (curso_id, limite)).fetchall():
                    agrupados.setdefault(leccion_id, []).append(enunciado)
        except sqlite3.Error as e:
            print(f"[BD] Error al obtener preguntas previas del curso {curso_id}: {e}")
        return agrupados

    def examen_debe_renovarse(self, curso_id: int) -> bool:
        """
        True si el examen actual del curso ya se intentó, el último intento fue
        desaprobado y el curso todavía no está aprobado: toca generar uno nuevo.
        """
        sql = """
            SELECT a.aprobado
            FROM exam_attempts a
            WHERE a.exam_id = (SELECT id FROM exams WHERE course_id = ? ORDER BY id DESC LIMIT 1)
            ORDER BY a.id DESC
            LIMIT 1
        """
        try:
            with self._conectar() as conexion:
                fila = conexion.execute(sql, (curso_id,)).fetchone()
            return fila is not None and not fila[0] and not self.examen_aprobado(curso_id)
        except sqlite3.Error as e:
            print(f"[BD] Error al consultar si el examen del curso {curso_id} debe renovarse: {e}")
            return False

    def registrar_intento_examen(self, examen_id: int, aciertos: int, total: int, aprobado: bool) -> bool:
        sql = "INSERT INTO exam_attempts (exam_id, aciertos, total, aprobado) VALUES (?, ?, ?, ?)"
        try:
            with self._conectar() as conexion:
                conexion.execute(sql, (examen_id, aciertos, total, 1 if aprobado else 0))
                conexion.commit()
                return True
        except sqlite3.Error as e:
            print(f"[BD] Error al registrar intento del examen {examen_id}: {e}")
            return False

    def examen_aprobado(self, curso_id: int) -> bool:
        """True si el examen final del curso tiene al menos un intento aprobado."""
        sql = """
            SELECT 1
            FROM exam_attempts a
            JOIN exams e ON e.id = a.exam_id
            WHERE e.course_id = ? AND a.aprobado = 1
            LIMIT 1
        """
        try:
            with self._conectar() as conexion:
                return conexion.execute(sql, (curso_id,)).fetchone() is not None
        except sqlite3.Error as e:
            print(f"[BD] Error al consultar aprobación del curso {curso_id}: {e}")
            return False

    def obtener_estado_examen(self, curso_id: int) -> dict:
        """
        Resumen para la pantalla de inicio del examen:
        {"intentos": int, "aprobado": bool, "mejor": (aciertos, total) | None}
        """
        estado = {"intentos": 0, "aprobado": False, "mejor": None}
        sql_resumen = """
            SELECT COUNT(*), COALESCE(MAX(a.aprobado), 0)
            FROM exam_attempts a
            JOIN exams e ON e.id = a.exam_id
            WHERE e.course_id = ?
        """
        sql_mejor = """
            SELECT a.aciertos, a.total
            FROM exam_attempts a
            JOIN exams e ON e.id = a.exam_id
            WHERE e.course_id = ?
            ORDER BY CAST(a.aciertos AS REAL) / a.total DESC, a.id DESC
            LIMIT 1
        """
        try:
            with self._conectar() as conexion:
                intentos, aprobado = conexion.execute(sql_resumen, (curso_id,)).fetchone()
                estado["intentos"] = intentos
                estado["aprobado"] = bool(aprobado)
                if intentos:
                    estado["mejor"] = tuple(conexion.execute(sql_mejor, (curso_id,)).fetchone())
        except sqlite3.Error as e:
            print(f"[BD] Error al obtener estado del examen del curso {curso_id}: {e}")
        return estado


    # --- Certificados de finalización ---

    _COLUMNAS_CERTIFICADO = (
        "id, course_id, codigo, nombre, curso_titulo, aciertos, total, emitido_at"
    )

    @staticmethod
    def _fila_a_certificado(fila) -> CertificadoModel:
        return CertificadoModel(
            id=fila[0],
            curso_id=fila[1],
            codigo=fila[2],
            nombre=fila[3],
            curso_titulo=fila[4],
            aciertos=fila[5],
            total=fila[6],
            emitido_at=str(fila[7]),
        )

    def obtener_certificado(self, curso_id: int) -> CertificadoModel | None:
        """Certificado ya emitido para el curso, o None si todavía no existe."""
        sql = f"SELECT {self._COLUMNAS_CERTIFICADO} FROM certificados WHERE course_id = ?"
        try:
            with self._conectar() as conexion:
                fila = conexion.execute(sql, (curso_id,)).fetchone()
            return self._fila_a_certificado(fila) if fila else None
        except sqlite3.Error as e:
            print(f"[BD] Error al obtener el certificado del curso {curso_id}: {e}")
            return None

    def obtener_o_emitir_certificado(self, curso_id: int) -> CertificadoModel | None:
        """
        Devuelve el certificado del curso; si no existe pero el examen final ya
        está aprobado, lo emite en ese momento (cubre cursos aprobados antes de
        que existieran los certificados). Devuelve None si el curso no está aprobado.

        Hay un solo certificado por curso: aprobar de nuevo no genera otro, así
        el código y la fecha siguen siendo los de la primera aprobación.
        """
        existente = self.obtener_certificado(curso_id)
        if existente is not None:
            return existente
        if not self.examen_aprobado(curso_id):
            return None

        sql_curso = "SELECT titulo FROM cursos WHERE id = ?"
        # El intento aprobado con mejor puntaje (a igualdad, el primero)
        sql_intento = """
            SELECT a.aciertos, a.total
            FROM exam_attempts a
            JOIN exams e ON e.id = a.exam_id
            WHERE e.course_id = ? AND a.aprobado = 1 AND a.total > 0
            ORDER BY CAST(a.aciertos AS REAL) / a.total DESC, a.id ASC
            LIMIT 1
        """
        sql_insert = """
            INSERT OR IGNORE INTO certificados
                (course_id, codigo, nombre, curso_titulo, aciertos, total)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            with self._conectar() as conexion:
                curso = conexion.execute(sql_curso, (curso_id,)).fetchone()
                intento = conexion.execute(sql_intento, (curso_id,)).fetchone()
                if curso is None or intento is None:
                    return None

                perfil = conexion.execute("SELECT nombre FROM perfil_usuario LIMIT 1").fetchone()
                nombre = (perfil[0] if perfil and perfil[0] else "").strip() or "Estudiante"

                # El código lleva el año y 8 hex aleatorios; si colisionara (casi
                # imposible), UNIQUE hace que el INSERT se ignore y se reintenta.
                for _ in range(5):
                    codigo = f"MENT-{datetime.now().year}-{secrets.token_hex(4).upper()}"
                    cursor = conexion.execute(
                        sql_insert,
                        (curso_id, codigo, nombre, curso[0], intento[0], intento[1]),
                    )
                    if cursor.rowcount:
                        break
                conexion.commit()
        except sqlite3.Error as e:
            print(f"[BD] Error al emitir el certificado del curso {curso_id}: {e}")
            return None

        return self.obtener_certificado(curso_id)


# --- PRUEBA DE FUNCIONAMIENTO ---
if __name__ == "__main__":
    db = BaseDatosProyecto("storage/sistema_estudios.db")

    db.inicializar_tablas()
    
    datos = db.obtener_perfil()
    if datos:
        print(f"Datos Actuales -> Nombre: {datos[0]}, Token: {datos[1]}")

    print("Cursos:", db.obtener_cursos_usuario())
    
