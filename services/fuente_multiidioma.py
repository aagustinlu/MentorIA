import sys
import re
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ==========================================================
# Fuente multidioma (Noto Sans JP)
# ==========================================================

FUENTE_JAPONESA_PATH = PROJECT_ROOT / "files" / "NotoSansJP-VariableFont_wght.ttf"
FUENTE_JAPONESA_FAMILIA = None
FUENTE_JAPONESA_REGISTRADA = False


def registrar_fuente_multidioma():
    """Registra la fuente del proyecto una sola vez en Qt."""
    global FUENTE_JAPONESA_FAMILIA, FUENTE_JAPONESA_REGISTRADA

    if FUENTE_JAPONESA_REGISTRADA:
        return FUENTE_JAPONESA_FAMILIA

    FUENTE_JAPONESA_REGISTRADA = True

    if not FUENTE_JAPONESA_PATH.is_file():
        print(
            "[Fuente] No se encontró Noto Sans JP en:",
            FUENTE_JAPONESA_PATH
        )
        return None

    id_fuente = QFontDatabase.addApplicationFont(str(FUENTE_JAPONESA_PATH))

    if id_fuente == -1:
        print("[Fuente] Qt no pudo cargar Noto Sans JP.")
        return None

    familias = QFontDatabase.applicationFontFamilies(id_fuente)

    if familias:
        FUENTE_JAPONESA_FAMILIA = familias[0]
        print(f"[Fuente] Fuente cargada correctamente: {FUENTE_JAPONESA_FAMILIA}")
    else:
        print("[Fuente] La fuente se registró, pero Qt no informó su familia.")

    return FUENTE_JAPONESA_FAMILIA


def crear_fuente_multidioma(tamano=15):
    """Crea una fuente que prioriza Noto Sans JP y conserva alternativas."""
    familia = FUENTE_JAPONESA_FAMILIA
    fuente = QFont()

    familias = []
    if familia:
        familias.append(familia)

    familias.extend([
        "Yu Gothic UI",
        "Yu Gothic",
        "Meiryo",
        "MS Gothic",
        "Segoe UI",
        "Arial",
    ])

    fuente.setFamilies(familias)
    fuente.setPointSize(tamano)
    return fuente


def css_fuente_multidioma():
    """Devuelve una lista CSS de fuentes con Noto Sans JP en primer lugar."""
    familia = FUENTE_JAPONESA_FAMILIA
    familias = []

    if familia:
        familias.append(f'"{familia}"')

    familias.extend([
        '"Yu Gothic UI"',
        '"Yu Gothic"',
        '"Meiryo"',
        '"MS Gothic"',
        '"Segoe UI"',
        'Arial',
        'sans-serif',
    ])

    return ", ".join(familias)


# Detecta secuencias UTF-8 que fueron interpretadas por error como Latin-1.
# Ejemplo: "あ" -> "ã\x81\x82" -> "あ".
_PATRON_MOJIBAKE_UTF8 = re.compile(
    r"(?:[\u00C2-\u00DF][\u0080-\u00BF]|"
    r"[\u00E0-\u00EF][\u0080-\u00BF]{2}|"
    r"[\u00F0-\u00F4][\u0080-\u00BF]{3})"
)


def reparar_mojibake_utf8(texto):
    """Repara fragmentos UTF-8 mal decodificados sin tocar tildes normales."""
    if not isinstance(texto, str) or not texto:
        return texto

    def reparar_fragmento(coincidencia):
        fragmento = coincidencia.group(0)
        try:
            return fragmento.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return fragmento

    return _PATRON_MOJIBAKE_UTF8.sub(reparar_fragmento, texto)