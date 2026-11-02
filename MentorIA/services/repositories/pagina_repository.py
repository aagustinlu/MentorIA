import sqlite3
from pathlib import Path
import sys


# Asegura que la raíz del proyecto esté en sys.path (permite ejecutar este módulo directo)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

    
from models.models import PaginaModel
from services.database import BaseDatos

# Modelos auxiliares para estado de lecciones (compatibles con la UI)
from pydantic import BaseModel
from typing import Literal, List


class LeccionRepository:

    def __init__(self, db: BaseDatos):
        self.db = db
    
    def guardar(self, pagina: PaginaModel, leccion_id: int):
        
        try:
            with self.db._conectar() as conexion:
                cursor = conexion.cursor()
                
                cursor.execute(
                    sql,
                    (pagina.indice, )
                )
                
                conexion.commit()
                
        except sqlite3.Error as e:
            print(f"Error al guardar la pagina: {e}")
            return False
        
    
    def obtener(self, id:int) -> PaginaModel | None:
        
        sql = """
            SELECT id, 
        """ 