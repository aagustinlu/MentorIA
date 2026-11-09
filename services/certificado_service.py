"""
Generación del certificado de finalización en PDF.

Sin dependencias de interfaz ni de base de datos: recibe un `CertificadoModel`
y escribe un PDF A4 horizontal. Usa reportlab (`pip install reportlab`).

Tipografías: Plus Jakarta Sans (ya incluida en files/fonts). Si el nombre o el
título del curso tienen caracteres japoneses/chinos, esa línea se dibuja con
Noto Sans JP, que también viene en el proyecto. Si falta algún archivo de
fuente se cae a Helvetica en lugar de fallar.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from models.models import CertificadoModel


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CARPETA_FUENTES = PROJECT_ROOT / "files" / "fonts"
RUTA_LOGOTIPO = PROJECT_ROOT / "files" / "img" / "Mentoria Logotipo.png"


# ==========================================================
# Paleta (la del tema claro de la aplicación, ver ui/theme.py)
# ==========================================================

PAPEL = HexColor("#FAF7EF")
TEXTO = HexColor("#303630")
TEXTO_SUAVE = HexColor("#686C62")
TEXTO_TENUE = HexColor("#73746A")
BORDE = HexColor("#D5CCBC")
VERDE = HexColor("#02BD65")
VERDE_OSCURO = HexColor("#2F6B49")


# ==========================================================
# Fuentes
# ==========================================================

# (nombre interno, archivo, fallback si falta el archivo)
_FUENTES = {
    "normal":    ("MentorIA-Regular",  "PlusJakartaSans-Regular.ttf",  "Helvetica"),
    "cursiva":   ("MentorIA-Italic",   "PlusJakartaSans-Italic.ttf",   "Helvetica-Oblique"),
    "semibold":  ("MentorIA-SemiBold", "PlusJakartaSans-SemiBold.ttf", "Helvetica-Bold"),
    "negrita":   ("MentorIA-Bold",     "PlusJakartaSans-Bold.ttf",     "Helvetica-Bold"),
    "jp_normal": ("MentorIA-JP",       "NotoSansJP-Regular.ttf",       None),
    "jp_negrita": ("MentorIA-JP-Bold", "NotoSansJP-Bold.ttf",          None),
}

# Kana, kanji, signos CJK y formas de ancho completo
_CJK = re.compile(r"[\u3000-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]")

_registradas: dict[str, str] = {}


def _fuente(estilo: str, texto: str = "") -> str:
    """Nombre de fuente para `estilo`, cambiando a Noto Sans JP si el texto lo necesita."""
    if _CJK.search(texto):
        estilo = "jp_negrita" if estilo in ("negrita", "semibold") else "jp_normal"

    if estilo in _registradas:
        return _registradas[estilo]

    nombre, archivo, respaldo = _FUENTES[estilo]
    ruta = CARPETA_FUENTES / archivo
    try:
        pdfmetrics.registerFont(TTFont(nombre, str(ruta)))
        resultado = nombre
    except Exception:
        # Sin archivo de fuente: Helvetica cubre el español. Para CJK no hay
        # respaldo posible, pero tampoco se interrumpe la generación.
        resultado = respaldo or "Helvetica"

    _registradas[estilo] = resultado
    return resultado


# ==========================================================
# Utilidades
# ==========================================================

_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def formatear_fecha(emitido_at: str) -> str:
    """'2026-11-08 21:30:00' (UTC, como lo guarda SQLite) -> '8 de noviembre de 2026' (hora local)."""
    try:
        fecha = datetime.strptime(emitido_at[:19], "%Y-%m-%d %H:%M:%S")
        fecha = fecha.replace(tzinfo=timezone.utc).astimezone()
    except ValueError:
        return emitido_at
    return f"{fecha.day} de {_MESES[fecha.month - 1]} de {fecha.year}"


def nombre_archivo_sugerido(certificado: CertificadoModel) -> str:
    """Nombre de archivo seguro para guardar el PDF: 'Certificado - <curso>.pdf'."""
    titulo = re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", certificado.curso_titulo)
    titulo = " ".join(titulo.split())[:80].strip(" .") or "curso"
    return f"Certificado - {titulo}.pdf"


def _ajustar_una_linea(texto: str, estilo: str, tam_max: float, tam_min: float, ancho: float):
    """Reduce el tamaño hasta que el texto entre en `ancho`. Si ni así entra, lo recorta con «…»."""
    tam = tam_max
    while tam > tam_min and pdfmetrics.stringWidth(texto, _fuente(estilo, texto), tam) > ancho:
        tam -= 1
    fuente = _fuente(estilo, texto)
    while len(texto) > 1 and pdfmetrics.stringWidth(texto, fuente, tam) > ancho:
        texto = texto[:-2].rstrip() + "…"
    return texto, fuente, tam


def _ajustar_varias_lineas(texto: str, estilo: str, ancho: float):
    """
    Devuelve (líneas, fuente, tamaño, interlineado) para un título de hasta 3 líneas:
    prueba tamaños de mayor a menor y, si no alcanza, recorta con «…».
    """
    fuente = _fuente(estilo, texto)
    for tam, max_lineas in ((30, 2), (26, 2), (22, 2), (20, 3)):
        lineas = simpleSplit(texto, fuente, tam, ancho)
        if len(lineas) <= max_lineas:
            return lineas, fuente, tam, tam * 1.22

    lineas = simpleSplit(texto, fuente, 20, ancho)[:3]
    lineas[-1] = lineas[-1].rstrip()
    while len(lineas[-1]) > 1 and pdfmetrics.stringWidth(lineas[-1] + "…", fuente, 20) > ancho:
        lineas[-1] = lineas[-1][:-1]
    lineas[-1] += "…"
    return lineas, fuente, 20, 20 * 1.22


def _texto_centrado(c: canvas.Canvas, x: float, y: float, texto: str, fuente: str,
                    tam: float, color, espaciado: float = 0) -> None:
    """Texto centrado en x, con espaciado entre letras opcional (títulos en versalitas)."""
    ancho = pdfmetrics.stringWidth(texto, fuente, tam) + espaciado * max(0, len(texto) - 1)
    t = c.beginText(x - ancho / 2, y)
    t.setFont(fuente, tam)
    t.setFillColor(color)
    t.setCharSpace(espaciado)
    t.textOut(texto)
    c.drawText(t)


def _cargar_logotipo():
    """Logotipo recortado a su contenido (el PNG trae mucho margen transparente)."""
    try:
        from PIL import Image

        imagen = Image.open(RUTA_LOGOTIPO).convert("RGBA")
        caja = imagen.getchannel("A").getbbox()
        if caja:
            imagen = imagen.crop(caja)
        return ImageReader(imagen), imagen.width / imagen.height
    except Exception:
        return None, 1.0


# ==========================================================
# Dibujo
# ==========================================================

def _dibujar_marco(c: canvas.Canvas, w: float, h: float) -> None:
    c.setFillColor(PAPEL)
    c.rect(0, 0, w, h, stroke=0, fill=1)

    c.setStrokeColor(VERDE_OSCURO)
    c.setLineWidth(2.2)
    c.rect(22, 22, w - 44, h - 44, stroke=1, fill=0)

    c.setStrokeColor(VERDE)
    c.setLineWidth(0.8)
    c.rect(30, 30, w - 60, h - 60, stroke=1, fill=0)

    # Esquinas: ángulos gruesos dentro del marco fino
    c.setStrokeColor(VERDE)
    c.setLineWidth(3)
    c.setLineCap(0)
    largo, m = 28, 38
    for x, y, dx, dy in (
        (m, m, 1, 1), (w - m, m, -1, 1), (m, h - m, 1, -1), (w - m, h - m, -1, -1),
    ):
        p = c.beginPath()
        p.moveTo(x + dx * largo, y)
        p.lineTo(x, y)
        p.lineTo(x, y + dy * largo)
        c.drawPath(p, stroke=1, fill=0)


def _dibujar_sello(c: canvas.Canvas, cx: float, cy: float, porcentaje: int) -> None:
    import math

    # Cintas (detrás del sello)
    c.setFillColor(VERDE_OSCURO)
    for lado in (-1, 1):
        p = c.beginPath()
        p.moveTo(cx + lado * 6, cy - 26)
        p.lineTo(cx + lado * 30, cy - 28)
        p.lineTo(cx + lado * 24, cy - 48)
        p.lineTo(cx + lado * 17, cy - 41)
        p.lineTo(cx + lado * 9, cy - 56)
        p.close()
        c.drawPath(p, stroke=0, fill=1)

    # Borde festoneado
    c.setFillColor(VERDE)
    for i in range(28):
        ang = 2 * math.pi * i / 28
        c.circle(cx + 36 * math.cos(ang), cy + 36 * math.sin(ang), 5.2, stroke=0, fill=1)
    c.circle(cx, cy, 36, stroke=0, fill=1)

    c.setStrokeColor(PAPEL)
    c.setLineWidth(1.1)
    c.circle(cx, cy, 29, stroke=1, fill=0)

    # "100%" tiene un dígito más: se achica para que no toque el aro interior
    tam = 19 if porcentaje < 100 else 15
    _texto_centrado(c, cx, cy - 2, f"{porcentaje}%", _fuente("negrita"), tam, PAPEL)
    _texto_centrado(c, cx, cy - 15, "APROBADO", _fuente("negrita"), 6.3, PAPEL, espaciado=1.2)


def _dibujar_dato(c: canvas.Canvas, x: float, y: float, etiqueta: str, valor: str) -> None:
    """Etiqueta en versalitas y, debajo, el valor; ambos centrados en x."""
    _texto_centrado(c, x, y + 16, etiqueta, _fuente("semibold"), 7.5, TEXTO_TENUE, espaciado=1.4)
    c.setStrokeColor(BORDE)
    c.setLineWidth(0.8)
    c.line(x - 110, y + 8, x + 110, y + 8)
    texto, fuente, tam = _ajustar_una_linea(valor, "semibold", 12.5, 9, 215)
    _texto_centrado(c, x, y - 8, texto, fuente, tam, TEXTO)


def generar_certificado_pdf(certificado: CertificadoModel, ruta_destino: str | Path) -> Path:
    """Escribe el certificado en `ruta_destino` (se le agrega .pdf si no lo tiene) y devuelve la ruta."""
    ruta = Path(ruta_destino)
    if ruta.suffix.lower() != ".pdf":
        ruta = ruta.with_name(ruta.name + ".pdf")

    ancho_pagina, alto_pagina = landscape(A4)
    w, h = ancho_pagina, alto_pagina
    centro = w / 2
    ancho_texto = w - 170

    c = canvas.Canvas(str(ruta), pagesize=(w, h))
    c.setTitle(f"Certificado - {certificado.curso_titulo}")
    c.setAuthor("MentorIA")
    c.setSubject(f"Certificado de finalización {certificado.codigo}")

    _dibujar_marco(c, w, h)

    # Logotipo
    logo, proporcion = _cargar_logotipo()
    if logo is not None:
        alto_logo = 50
        c.drawImage(
            logo, centro - alto_logo * proporcion / 2, h - 104,
            width=alto_logo * proporcion, height=alto_logo, mask="auto",
        )

    # Encabezado
    _texto_centrado(c, centro, h - 140, "CERTIFICADO DE FINALIZACIÓN",
                    _fuente("semibold"), 12, VERDE_OSCURO, espaciado=3)
    _texto_centrado(c, centro, h - 178, "MentorIA certifica que",
                    _fuente("cursiva"), 14, TEXTO_SUAVE)

    # Nombre del estudiante
    nombre, f_nombre, t_nombre = _ajustar_una_linea(
        certificado.nombre.strip() or "Estudiante", "negrita", 44, 22, ancho_texto
    )
    _texto_centrado(c, centro, h - 236, nombre, f_nombre, t_nombre, TEXTO)
    c.setStrokeColor(BORDE)
    c.setLineWidth(0.8)
    c.line(centro - 210, h - 249, centro + 210, h - 249)

    # Curso
    _texto_centrado(c, centro, h - 280, "ha completado satisfactoriamente el curso",
                    _fuente("cursiva"), 14, TEXTO_SUAVE)

    lineas, f_curso, t_curso, interlineado = _ajustar_varias_lineas(
        " ".join(certificado.curso_titulo.split()), "negrita", ancho_texto
    )
    y = h - 324
    for linea in lineas:
        _texto_centrado(c, centro, y, linea, f_curso, t_curso, VERDE_OSCURO)
        y -= interlineado

    # Resultado del examen
    _texto_centrado(
        c, centro, y - 8,
        f"Evaluación final aprobada con {certificado.porcentaje}% de respuestas correctas "
        f"({certificado.aciertos} de {certificado.total})",
        _fuente("normal"), 11, TEXTO_SUAVE,
    )

    # Pie: fecha · sello · código
    _dibujar_dato(c, 160, 104, "FECHA DE EMISIÓN", formatear_fecha(certificado.emitido_at))
    _dibujar_sello(c, centro, 126, certificado.porcentaje)
    _dibujar_dato(c, w - 160, 104, "CÓDIGO DEL CERTIFICADO", certificado.codigo)

    _texto_centrado(
        c, centro, 45,
        "Certificado de aprendizaje personal emitido por MentorIA. "
        "El contenido del curso fue generado con inteligencia artificial.",
        _fuente("normal"), 7.5, TEXTO_TENUE,
    )

    c.showPage()
    c.save()
    return ruta
