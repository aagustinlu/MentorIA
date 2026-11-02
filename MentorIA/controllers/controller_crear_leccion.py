from __future__ import annotations

from pathlib import Path
import sys
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ai_service import GestorDeIA
from services.database import BaseDatosProyecto
from models.models import ContenidoLeccionGeneracion


class CrearLeccionController:
    """
    Genera el contenido completo de una lección usando la IA.
    No crea el curso, solo genera y devuelve las páginas/bloques de una lección.
    """

    def __init__(self, fuente: str, ruta: Optional[str] = None):
        self.ruta = ruta
        self.fuente = fuente

        self.db = BaseDatosProyecto("storage/sistema_estudios.db")

        perfil = self.db.obtener_perfil()   # (nombre, token) | None
        self.api_key: Optional[str] = perfil[1] if perfil else None

    def generar_contenido_leccion(
        self,
        curso_titulo: str,
        leccion_titulo: str,
        leccion_resumen: str,
    ) -> Optional[ContenidoLeccionGeneracion]:
        """Llama a la IA y devuelve el contenido de la lección."""
        gestor = GestorDeIA(api_key=self.api_key)

        kwargs = dict(
            curso_titulo=curso_titulo,
            titulo=leccion_titulo,
            descripcion=leccion_resumen,
            fuente=self.fuente,
        )
        if self.ruta:
            kwargs["ruta"] = self.ruta

        try:
            contenido = gestor.generar_contenido_leccion(**kwargs)
            return contenido
        except Exception as e:
            print(f"[CrearLeccionController] Error al generar lección: {e}")
            return None
