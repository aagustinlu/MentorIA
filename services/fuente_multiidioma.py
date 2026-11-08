
from __future__ import annotations

import sys
import re
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ==========================================================
# Fuentes de la aplicación
#
# - SpaceGrotesk: fuente principal de la interfaz.
# - Noto Sans JP: respaldo para japonés.
# - Fuentes del sistema: alternativas adicionales.
# ==========================================================

CARPETA_FUENTES = PROJECT_ROOT / "files" / "fonts"


# ── SpaceGrotesk ────────────────────────────────────────────────

ARCHIVOS_UI = (
    "SpaceGrotesk-VariableFont_wght.ttf",
)

FUENTE_UI_PATH = CARPETA_FUENTES / "SpaceGrotesk-VariableFont_wght.ttf"
FUENTE_UI_NOMBRE = "SpaceGrotesk"
FUENTE_UI_FAMILIA = None


# ── Noto Sans JP ──────────────────────────────────────────

# Preferimos las versiones estáticas para evitar problemas
# con el reconocimiento de pesos en algunas versiones de Qt.

ARCHIVOS_JAPONES = (
    "NotoSansJP-Regular.ttf",
    "NotoSansJP-Bold.ttf",
)

# Conservamos la ubicación original de tu fuente variable.
FUENTE_JAPONESA_PATH = (
    PROJECT_ROOT / "files" / "NotoSansJP-VariableFont_wght.ttf"
)

FUENTE_JAPONESA_NOMBRE = "Noto Sans JP"
FUENTE_JAPONESA_FAMILIA = None


# ── Estado del registro ───────────────────────────────────

FUENTE_JAPONESA_REGISTRADA = False
FUENTES_REGISTRADAS = False

_ARCHIVOS_REGISTRADOS = set()


# ── Alternativas del sistema ──────────────────────────────

FUENTES_RESPALDO = (
    "Segoe UI",
    "Yu Gothic UI",
    "Yu Gothic",
    "Meiryo",
    "Arial",
    "Helvetica Neue",
)


# ==========================================================
# REGISTRO DE FUENTES
# ==========================================================

def _registrar_archivo(ruta, etiqueta):
    """
    Registra un archivo de fuente en Qt y devuelve su familia.

    Evita registrar varias veces el mismo archivo.
    """

    ruta = Path(ruta)

    if not ruta.is_file():
        print(f"[Fuente] No se encontró {etiqueta}:", ruta)
        return None

    clave = str(ruta.resolve())

    # Si ya se registró anteriormente, no repetimos el proceso.
    if clave in _ARCHIVOS_REGISTRADOS:
        return None

    id_fuente = QFontDatabase.addApplicationFont(str(ruta))

    if id_fuente == -1:
        print(f"[Fuente] Qt no pudo cargar {etiqueta}.")
        return None

    _ARCHIVOS_REGISTRADOS.add(clave)

    familias = QFontDatabase.applicationFontFamilies(id_fuente)

    if not familias:
        print(f"[Fuente] No se encontró la familia de {etiqueta}.")
        return None

    return familias[0]


def registrar_fuente_multidioma():
    """
    Registra las fuentes del proyecto una sola vez.

    Debe llamarse después de crear QApplication.
    """

    global FUENTE_UI_FAMILIA
    global FUENTE_JAPONESA_FAMILIA
    global FUENTE_JAPONESA_REGISTRADA
    global FUENTES_REGISTRADAS

    if FUENTES_REGISTRADAS:
        return FUENTE_UI_FAMILIA

    # ── Fuente principal: Hunnin ──────────────────────────

    if not FUENTE_UI_FAMILIA:
        for nombre_archivo in ARCHIVOS_UI:

            familia = _registrar_archivo(
                CARPETA_FUENTES / nombre_archivo,
                nombre_archivo
            )

            if familia:
                FUENTE_UI_FAMILIA = familia
                break

    # ── Fuente secundaria: Noto Sans JP ───────────────────

    if not FUENTE_JAPONESA_FAMILIA:

        for nombre_archivo in ARCHIVOS_JAPONES:

            familia = _registrar_archivo(
                CARPETA_FUENTES / nombre_archivo,
                nombre_archivo
            )

            if familia and not FUENTE_JAPONESA_FAMILIA:
                FUENTE_JAPONESA_FAMILIA = familia

    # Si no encontramos las versiones estáticas,
    # intentamos utilizar la fuente variable original.

    if not FUENTE_JAPONESA_FAMILIA:

        FUENTE_JAPONESA_FAMILIA = _registrar_archivo(
            FUENTE_JAPONESA_PATH,
            FUENTE_JAPONESA_NOMBRE
        )

    FUENTE_JAPONESA_REGISTRADA = bool(FUENTE_JAPONESA_FAMILIA)

    # Solo consideramos completo el registro cuando
    # encontramos ambas familias.

    FUENTES_REGISTRADAS = bool(
        FUENTE_UI_FAMILIA and FUENTE_JAPONESA_FAMILIA
    )

    """
    print(
        "[Fuente] Interfaz:",
        FUENTE_UI_FAMILIA or "no cargada (se usa respaldo)",
        "| Japonés:",
        FUENTE_JAPONESA_FAMILIA or "no cargada"
    )
    """
    
    return FUENTE_UI_FAMILIA


# ==========================================================
# FAMILIAS TIPOGRÁFICAS
# ==========================================================

def _lista_familias():
    """
    Devuelve las fuentes en orden de prioridad:

    1. SpaceGrotesk.
    2. Noto Sans JP.
    3. Alternativas del sistema.
    """

    familias = []

    fuente_principal = FUENTE_UI_FAMILIA or FUENTE_UI_NOMBRE
    fuente_japonesa = FUENTE_JAPONESA_FAMILIA or FUENTE_JAPONESA_NOMBRE

    familias.append(fuente_principal)
    familias.append(fuente_japonesa)

    familias.extend(FUENTES_RESPALDO)

    # Evitamos familias repetidas.
    resultado = []
    for familia in familias:
        if familia not in resultado:
            resultado.append(familia)

    return resultado


# ==========================================================
# CREACIÓN DE FUENTES
# ==========================================================

def crear_fuente_multidioma(
    tamano=15,
    pixeles=None,
    peso=QFont.Weight.Medium
):
    """
    Crea una fuente compatible con varios idiomas.

    Parámetros:
        tamano:
            Tamaño en puntos.

        pixeles:
            Tamaño en píxeles. Tiene prioridad sobre tamano.

        peso:
            Grosor de la fuente.

            Thin       = 100
            Light      = 300
            Normal     = 400
            Medium     = 500
            DemiBold   = 600
            Bold       = 700
            ExtraBold  = 800
            Black      = 900
    """

    fuente = QFont()

    fuente.setFamilies(_lista_familias())

    if pixeles is not None:
        fuente.setPixelSize(int(pixeles))
    else:
        fuente.setPointSize(int(tamano))

    fuente.setWeight(QFont.Weight(peso))

    fuente.setStyleStrategy(
        QFont.StyleStrategy.PreferAntialias
    )

    return fuente


# ==========================================================
# CSS PARA HTML Y QWEBENGINE
# ==========================================================

def css_fuente_multidioma():
    """
    Devuelve la lista de fuentes CSS.

    Permite utilizar la misma tipografía en:
    - QTextBrowser.
    - HTML generado por IA.
    - Tablas.
    - Fórmulas.
    - QWebEngineView.
    """

    familias = [
        f'"{familia}"'
        for familia in _lista_familias()
    ]

    familias.append("sans-serif")

    return ", ".join(familias)


# ==========================================================
# REPARACIÓN DE CODIFICACIÓN UTF-8
# ==========================================================

# Detecta secuencias UTF-8 interpretadas por error como Latin-1.
#
# Ejemplo:
# "あ" -> "ã\x81\x82" -> "あ"

_PATRON_MOJIBAKE_UTF8 = re.compile(
    r"(?:[\u00C2-\u00DF][\u0080-\u00BF]|"
    r"[\u00E0-\u00EF][\u0080-\u00BF]{2}|"
    r"[\u00F0-\u00F4][\u0080-\u00BF]{3})"
)


def reparar_mojibake_utf8(texto):
    """
    Repara fragmentos UTF-8 mal decodificados
    sin modificar las tildes normales.
    """

    if not isinstance(texto, str) or not texto:
        return texto

    def reparar_fragmento(coincidencia):

        fragmento = coincidencia.group(0)

        try:
            return fragmento.encode("latin-1").decode("utf-8")

        except (UnicodeEncodeError, UnicodeDecodeError):
            return fragmento

    return _PATRON_MOJIBAKE_UTF8.sub(
        reparar_fragmento,
        texto
    )
