import os
import sys
import threading
from pathlib import Path 
from playsound import playsound

# Configuración de rutas del proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Definimos la carpeta contenedora de sonidos
ruta_sonido = PROJECT_ROOT / "files" / "sounds"


class SoundPlayer:
    # Definimos el diccionario usando los objetos Path dinámicos
    SOUND_MAPPING = {
        "exito": ruta_sonido / "exito effect.mp3",
        "error": ruta_sonido / "error effect.mp3",
    }

    def __init__(self):
        pass

    def _execute_play(self, file_path: Path):
        
        if not os.path.exists(file_path):
            print(f"Error: El archivo no existe en la ruta: {file_path}")
            return

        try:
            playsound(str(file_path))
        except Exception as e:
            print(f"Error crítico al reproducir el archivo: {e}")

    def play(self, sound_type: str, background: bool = True):
        file_path = self.SOUND_MAPPING.get(sound_type)

        if not file_path:
            print(f"Tipo de sonido desconocido: '{sound_type}'")
            return

        if background:
            thread = threading.Thread(
                target=self._execute_play, args=(file_path,), daemon=True
            )
            thread.start()
        else:
            self._execute_play(file_path)
