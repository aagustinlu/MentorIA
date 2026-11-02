"""
Lógica de la evaluación final, sin dependencias de interfaz ni de red.

Se divide en dos partes:

1. Preparación del examen (usada por `ai_service`):
   - convertir las lecciones guardadas en texto plano,
   - decidir cuántas preguntas generar según la cantidad de contenido,
   - agrupar lecciones en lotes para no enviar demasiado texto de una vez,
   - limpiar lo que devuelve la IA antes de guardarlo.

2. Rendición del examen (usada por la UI):
   - `SesionExamen`: orden de preguntas/opciones, respuestas y calificación.
"""

import random
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import unquote

from models.models import PreguntaGeneracion, PreguntaModel


# ==========================================================
# Parámetros del examen (ajustables desde un único lugar)
# ==========================================================

PORCENTAJE_APROBACION = 70      # % mínimo de aciertos para aprobar el curso

PALABRAS_POR_PREGUNTA = 120     # ~1 pregunta cada 120 palabras de material
MIN_PREGUNTAS = 5
MAX_PREGUNTAS = 30
MAX_OPCIONES = 5                # el prompt pide 4; se tolera de 2 a 5

# Si el material es largo se pide el examen por tandas de lecciones, para no
# superar los límites de tokens por minuto de la API.
MAX_PALABRAS_POR_LOTE = 2500


# ==========================================================
# 1. Preparación del examen
# ==========================================================

class _ExtractorHTML(HTMLParser):
    _BLOQUES = {
        "p", "div", "br", "ul", "ol", "li", "tr", "table", "pre",
        "blockquote", "h1", "h2", "h3", "h4", "h5", "h6",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.partes.append("\n- ")
        elif tag in self._BLOQUES:
            self.partes.append("\n")

    def handle_endtag(self, tag):
        if tag in self._BLOQUES:
            self.partes.append("\n")

    def handle_data(self, data):
        self.partes.append(data)


def html_a_texto(html: str) -> str:
    """Convierte el HTML de un bloque de lección en texto plano legible."""
    extractor = _ExtractorHTML()
    try:
        extractor.feed(html)
        extractor.close()
    except Exception:
        return re.sub(r"<[^>]+>", " ", html).strip()

    texto = "".join(extractor.partes)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n\s*\n+", "\n", texto)
    return texto.strip()


_ETIQUETAS_CODIGO = re.compile(r"</?(code|pre)[^>]*>", re.IGNORECASE)
_TIENE_ETIQUETAS = re.compile(r"</?[a-zA-Z][^>]*>")


def texto_leccion(leccion) -> str:
    """
    Texto plano de una lección (LeccionModel con páginas y bloques).
    Se aplica `unquote` a texto y títulos igual que hace la UI al mostrarlos,
    de modo que el examen se base en lo mismo que vio el usuario.
    """
    partes: list[str] = []

    for pagina in leccion.paginas:
        for bloque in pagina.bloques:
            if bloque.tipo in ("texto", "titulo"):
                texto = html_a_texto(unquote(bloque.contenido))
                if texto:
                    partes.append(f"## {texto}" if bloque.tipo == "titulo" else texto)
            elif bloque.tipo == "codigo":
                # La IA a veces envuelve el código en <pre><code>; no es parte del código
                codigo = _ETIQUETAS_CODIGO.sub("", bloque.contenido).strip()
                if codigo:
                    partes.append("Código:\n" + codigo)
            elif bloque.tipo == "formula":
                formula = bloque.contenido.strip()
                if _TIENE_ETIQUETAS.search(formula):   # a veces viene como <p>…&rarr;…</p>
                    formula = html_a_texto(formula)
                if formula:
                    partes.append("Fórmula: " + formula)

    return "\n\n".join(partes)


def repartir_preguntas(palabras_por_leccion: list[int]) -> list[int]:
    """
    Decide cuántas preguntas corresponden a cada lección.

    - El total crece con la cantidad de contenido (1 cada PALABRAS_POR_PREGUNTA),
      acotado entre MIN_PREGUNTAS y MAX_PREGUNTAS.
    - Nunca baja de una pregunta por lección, para que todo el curso quede cubierto.
    - Las preguntas restantes se reparten proporcionalmente a la extensión de
      cada lección (método del mayor resto).
    """
    n = len(palabras_por_leccion)
    if n == 0:
        return []

    total_palabras = sum(palabras_por_leccion)
    objetivo = max(
        MIN_PREGUNTAS,
        n,
        min(MAX_PREGUNTAS, round(total_palabras / PALABRAS_POR_PREGUNTA)),
    )

    extra = objetivo - n
    if extra <= 0:
        return [1] * n

    if total_palabras > 0:
        exactos = [extra * p / total_palabras for p in palabras_por_leccion]
    else:
        exactos = [extra / n] * n

    enteros = [int(e) for e in exactos]
    sobrantes = extra - sum(enteros)
    por_resto = sorted(range(n), key=lambda i: exactos[i] - enteros[i], reverse=True)
    for i in por_resto[:sobrantes]:
        enteros[i] += 1

    return [1 + e for e in enteros]


def armar_lotes(items: list[dict], max_palabras: int = MAX_PALABRAS_POR_LOTE) -> list[list[dict]]:
    """Agrupa lecciones consecutivas sin pasar de `max_palabras` por lote."""
    lotes: list[list[dict]] = []
    actual: list[dict] = []
    palabras_actual = 0

    for item in items:
        if actual and palabras_actual + item["palabras"] > max_palabras:
            lotes.append(actual)
            actual, palabras_actual = [], 0
        actual.append(item)
        palabras_actual += item["palabras"]

    if actual:
        lotes.append(actual)
    return lotes


def _quitar_letras(opciones: list[str]) -> list[str]:
    """Si TODAS las opciones empiezan con «A) », «B. », etc., se las quita."""
    letras = "ABCDE"
    if len(opciones) > len(letras):
        return opciones

    patrones = [
        re.match(rf"^\s*{letras[i]}[\)\.]\s+", op, flags=re.IGNORECASE)
        for i, op in enumerate(opciones)
    ]
    if all(patrones):
        return [op[m.end():].strip() for op, m in zip(opciones, patrones)]
    return opciones


def sanear_preguntas(preguntas, n_lecciones: int) -> list[PreguntaGeneracion]:
    """
    Descarta o corrige lo que la IA pueda haber devuelto mal:
    enunciados vacíos, índice de respuesta fuera de rango, opciones repetidas
    o vacías, demasiadas opciones y preguntas duplicadas.
    `leccion_numero` queda en 0 si no corresponde a ninguna lección.
    """
    vistas: set[str] = set()
    limpias: list[PreguntaGeneracion] = []

    for p in preguntas:
        enunciado = (p.enunciado or "").strip()
        if not enunciado:
            continue

        crudas = [(o or "").strip() for o in p.opciones]
        if not 0 <= p.indice_correcta < len(crudas):
            continue

        crudas = _quitar_letras(crudas)
        correcta = crudas[p.indice_correcta]
        if not correcta:
            continue

        # Sin vacías ni repetidas (ignorando mayúsculas)
        unicas: list[str] = []
        for o in crudas:
            if o and o.casefold() not in {u.casefold() for u in unicas}:
                unicas.append(o)

        idx = next((i for i, o in enumerate(unicas) if o.casefold() == correcta.casefold()), None)
        if idx is None or len(unicas) < 2:
            continue

        # Demasiadas opciones: se conserva la correcta y los primeros distractores
        if len(unicas) > MAX_OPCIONES:
            distractores = [i for i in range(len(unicas)) if i != idx][: MAX_OPCIONES - 1]
            conservar = sorted(distractores + [idx])
            unicas = [unicas[i] for i in conservar]
            idx = conservar.index(idx)

        clave = " ".join(enunciado.casefold().split())
        if clave in vistas:
            continue
        vistas.add(clave)

        numero = p.leccion_numero if 1 <= p.leccion_numero <= n_lecciones else 0
        limpias.append(
            PreguntaGeneracion(
                leccion_numero=numero,
                enunciado=enunciado,
                opciones=unicas,
                indice_correcta=idx,
                explicacion=(p.explicacion or "").strip(),
            )
        )

    return limpias


# ==========================================================
# 2. Rendición del examen
# ==========================================================

@dataclass
class RevisionPregunta:
    """Una pregunta fallada o sin responder, con lo necesario para repasarla."""
    pregunta: PreguntaModel
    elegida: str | None      # texto de la opción elegida (None = sin responder)
    correcta: str            # texto de la opción correcta


@dataclass
class ResultadoExamen:
    aciertos: int
    total: int
    errores: list[RevisionPregunta] = field(default_factory=list)

    @property
    def porcentaje(self) -> int:
        return round(100 * self.aciertos / self.total) if self.total else 0

    @property
    def aprobado(self) -> bool:
        # Comparación con enteros: evita errores de redondeo en el límite
        return self.total > 0 and self.aciertos * 100 >= PORCENTAJE_APROBACION * self.total


class SesionExamen:
    """
    Un intento de examen. Las opciones se mezclan en cada intento (así la
    posición de la respuesta correcta no se puede memorizar ni depende del
    sesgo de la IA). Las respuestas se guardan por posición *mostrada*.
    """

    def __init__(self, preguntas: list[PreguntaModel], barajar_preguntas: bool = False,
                 rng: random.Random | None = None):
        rng = rng or random.Random()

        lista = list(preguntas)
        if barajar_preguntas:
            rng.shuffle(lista)

        self.preguntas = lista
        # orden[i][k] = índice ORIGINAL de la opción que se muestra en la posición k
        self.orden: list[list[int]] = []
        for p in lista:
            posiciones = list(range(len(p.opciones)))
            rng.shuffle(posiciones)
            self.orden.append(posiciones)

        self.respuestas: dict[int, int] = {}   # pregunta i -> posición mostrada elegida

    def __len__(self) -> int:
        return len(self.preguntas)

    def opciones_mostradas(self, i: int) -> list[str]:
        p = self.preguntas[i]
        return [p.opciones[o] for o in self.orden[i]]

    def responder(self, i: int, posicion: int) -> None:
        if not 0 <= posicion < len(self.orden[i]):
            raise IndexError("Opción inexistente.")
        self.respuestas[i] = posicion

    def respuesta(self, i: int) -> int | None:
        return self.respuestas.get(i)

    def sin_responder(self) -> int:
        return len(self.preguntas) - len(self.respuestas)

    def es_correcta(self, i: int) -> bool:
        elegida = self.respuestas.get(i)
        return elegida is not None and self.orden[i][elegida] == self.preguntas[i].correcta

    def calificar(self) -> ResultadoExamen:
        aciertos = 0
        errores: list[RevisionPregunta] = []

        for i, p in enumerate(self.preguntas):
            if self.es_correcta(i):
                aciertos += 1
                continue
            elegida = self.respuestas.get(i)
            errores.append(
                RevisionPregunta(
                    pregunta=p,
                    elegida=None if elegida is None else p.opciones[self.orden[i][elegida]],
                    correcta=p.opciones[p.correcta],
                )
            )

        return ResultadoExamen(aciertos=aciertos, total=len(self.preguntas), errores=errores)
