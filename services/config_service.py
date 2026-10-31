from services.database import BaseDatosProyecto


class ConfigService:
    def __init__(self, ruta_db: str = "storage/sistema_estudios.db"):
        self.ruta_db = ruta_db
        self.db = BaseDatosProyecto(self.ruta_db)

    def cambiar_nombre(self, nuevo_nombre: str) -> bool:
        """Cambia únicamente el nombre del usuario manteniendo el token."""
        
        return self.db.cambiar_nombre_usuario(nuevo_nombre)

    def cambiar_api_key(self, nueva_apikey: str) -> bool:
        
        return self.db.cambiar_apikey(nueva_apikey)