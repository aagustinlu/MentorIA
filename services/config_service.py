from services.database import BaseDatosProyecto

CLAVE_TEMA = "tema"


class ConfigService:
    def __init__(self, ruta_db: str = "storage/sistema_estudios.db"):
        self.ruta_db = ruta_db
        self.db = BaseDatosProyecto(self.ruta_db)

    def cambiar_nombre(self, nuevo_nombre: str) -> bool:
        """Cambia únicamente el nombre del usuario manteniendo el token."""
        
        return self.db.cambiar_nombre_usuario(nuevo_nombre)

    def cambiar_api_key(self, nueva_apikey: str) -> bool:
        
        return self.db.cambiar_apikey(nueva_apikey)

    def obtener_tema(self, defecto: str = "dia") -> str:
        """Tema guardado ("dia" u "oscuro")."""
        return self.db.obtener_ajuste(CLAVE_TEMA, defecto) or defecto

    def guardar_tema(self, nombre: str) -> bool:
        """Recuerda el tema elegido para la próxima vez que se abra la aplicación."""
        return self.db.guardar_ajuste(CLAVE_TEMA, nombre)