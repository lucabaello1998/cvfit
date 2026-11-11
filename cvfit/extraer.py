"""Extracción de texto desde archivos: .md/.txt, .docx y .pdf.

Sin dependencias externas. DOCX es un ZIP con XML (fácil). PDF es el caso difícil: se descomprimen
los streams, se leen los operadores de texto y se aplica el mapa ToUnicode cuando el PDF lo trae.

PDF es best-effort: un CV de dos columnas o escaneado va a salir desordenado o vacío, y el programa
lo dice en vez de inventar un CV.
"""

from __future__ import annotations

import base64
import contextlib
import io
import re
import zipfile

SOPORTADOS = {".md", ".markdown", ".txt", ".docx", ".pdf"}

PDF_STREAM = re.compile(rb"stream\r?\n(.*?)endstream", re.S)
NUMERO = rb"-?\d+(?:\.\d+)?"
TOKEN = re.compile(
    rb"\((?:[^()\\]|\\.)*\)"
    rb"|<[0-9A-Fa-f\s]+>"
    rb"|" + NUMERO + rb"|TJ|Tj|T\*|Td|TD|Tm|Tf|TL|ET|BT|'|\"|\[|\]"
)
PALABRAS_COMUNES = frozenset(
    [
        "de",
        "la",
        "el",
        "en",
        "y",
        "con",
        "para",
        "por",
        "del",
        "los",
        "las",
        "un",
        "una",
        "al",
        "se",
        "su",
        "que",
        "años",
        "experiencia",
        "desarrollo",
        "proyecto",
        "and",
        "the",
        "with",
        "for",
        "experience",
        "development",
        "of",
        "to",
        "in",
        "on",
        "at",
    ]
)
ESC = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f", b"(": b"(", b")": b")", b"\\": b"\\"}


class ExtraccionError(Exception):
    """El archivo no se pudo leer (escaneado, cifrado, formato raro)."""


def extraer_desde_archivo(ruta) -> str:
    from pathlib import Path

    camino = Path(ruta)
    sufijo = camino.suffix.lower()
    if sufijo not in SOPORTADOS:
        raise ExtraccionError(f"formato no soportado: {sufijo}. Probá con .md, .txt, .docx o .pdf")
    datos = camino.read_bytes()
    if sufijo in (".md", ".markdown", ".txt"):
        return datos.decode("utf-8-sig", "replace")
    if sufijo == ".docx":
        return desde_docx(datos)
    return desde_pdf(datos)


# --------------------------------------------------------------------------- DOCX


# Un CV real no pasa de unos pocos MB. El tope evita que un .docx armado como
# zip bomb (o con una parte gigante) se descomprima entero en memoria.
LIMITE_DOCX = 25 * 1024 * 1024


def desde_docx(datos: bytes) -> str:
    try:
        archivo = zipfile.ZipFile(io.BytesIO(datos))
        info = archivo.getinfo("word/document.xml")
        total = sum(parte.file_size for parte in archivo.infolist())
        if info.file_size > LIMITE_DOCX or total > LIMITE_DOCX * 2:
            raise ExtraccionError(
                f"el .docx descomprime {total // (1024 * 1024)} MB y el límite es {LIMITE_DOCX // (1024 * 1024)} MB"
            )
        xml = archivo.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as error:
        raise ExtraccionError("el .docx no se pudo abrir (¿es un .doc viejo renombrado?)") from error

    from xml.etree import ElementTree as ET

    espacio = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError as error:
        raise ExtraccionError("el .docx tiene XML inválido") from error

    salida: list[str] = []
    for parrafo in raiz.iter(f"{{{espacio['w']}}}p"):
        texto = "".join(nodo.text or "" for nodo in parrafo.iter(f"{{{espacio['w']}}}t"))
        texto = texto.strip()
        if not texto:
            continue

        estilo = parrafo.find("w:pPr/w:pStyle", espacio)
        referencia = (estilo.get(f"{{{espacio['w']}}}val") if estilo is not None else "") or ""
        bajo = referencia.lower()

        if "heading1" in bajo or "título1" in bajo or "titulo1" in bajo:
            salida.append(f"# {texto}")
        elif "heading2" in bajo or "título2" in bajo or "titulo2" in bajo:
            salida.append(f"## {texto.upper()}")
        elif "heading3" in bajo or "título3" in bajo or "titulo3" in bajo:
            salida.append(f"### {texto}")
        elif parrafo.find("w:pPr/w:numPr", espacio) is not None:
            salida.append(f"- {texto}")
        elif len(texto) < 90 and texto.isupper():
            salida.append(f"## {texto}")
        else:
            salida.append(texto)

    if not salida:
        raise ExtraccionError("el .docx no tiene texto (¿es una imagen escaneada?)")
    return "\n\n".join(salida)


# --------------------------------------------------------------------------- PDF


def desde_pdf(datos: bytes) -> str:
    if datos[:1024].find(b"/Encrypt") >= 0:
        raise ExtraccionError("el PDF está protegido con contraseña")

    cmap: dict[str, str] = {}
    contenidos: list[bytes] = []

    for crudo in PDF_STREAM.findall(datos):
        cuerpo = _descomprimir(crudo)
        if b"beginbfchar" in cuerpo or b"beginbfrange" in cuerpo:
            cmap.update(_leer_cmap(cuerpo))
        elif b"BT" in cuerpo and (b"Tj" in cuerpo or b"TJ" in cuerpo):
            contenidos.append(cuerpo)

    if not contenidos:
        raise ExtraccionError(
            "no se encontró texto en el PDF: puede ser una imagen escaneada. Convertilo a .docx o pasalo por un OCR."
        )

    lineas = [_texto_de_stream(cuerpo, cmap) for cuerpo in contenidos]
    texto = "\n".join(lineas)
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()

    if _proporcion_legible(texto) < 0.55:
        raise ExtraccionError(
            "el PDF usa fuentes sin mapa de caracteres y el texto sale ilegible. "
            "Abrilo y guardalo de nuevo como PDF/DOCX desde Word o Google Docs."
        )
    if len(texto) < 40:
        raise ExtraccionError("el PDF casi no tiene texto: probablemente sea un escaneo.")
    return texto


def _descomprimir(crudo: bytes) -> bytes:
    """FlateDecode y/o ASCII85Decode. Si no reconoce el filtro, devuelve los bytes tal cual."""
    import zlib

    datos = crudo.strip(b"\r\n")

    if datos[:1] == b"\x78":
        try:
            return zlib.decompress(datos)
        except zlib.error:
            pass

    if datos.endswith(b"~>"):
        try:
            decodificado = base64.a85decode(datos, adobe=True)
        except ValueError:
            return datos
        try:
            return zlib.decompress(decodificado)
        except zlib.error:
            return decodificado

    return datos


def _leer_cmap(cuerpo: bytes) -> dict[str, str]:
    mapa: dict[str, str] = {}
    for bloque in re.findall(rb"beginbfchar(.*?)endbfchar", cuerpo, re.S):
        for origen, destino in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", bloque):
            mapa[origen.decode().lower()] = _hex_a_texto(destino)
    for bloque in re.findall(rb"beginbfrange(.*?)endbfrange", cuerpo, re.S):
        for inicio, fin, destino in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", bloque):
            base = int(inicio, 16)
            cantidad = int(fin, 16) - base
            inicial = _hex_a_texto(destino)
            for salto in range(min(cantidad + 1, 256)):
                if inicial:
                    mapa[f"{base + salto:04x}"] = chr(ord(inicial[0]) + salto)
    return mapa


def _hex_a_texto(valor: bytes) -> str:
    try:
        return bytes.fromhex(valor.decode()).decode("utf-16-be", "ignore")
    except (ValueError, UnicodeDecodeError):
        return ""


def _decodificar_pdf(cadena: bytes) -> bytes:
    salida = bytearray()
    i = 0
    while i < len(cadena):
        byte = cadena[i : i + 1]
        if byte == b"\\" and i + 1 < len(cadena):
            siguiente = cadena[i + 1 : i + 2]
            if siguiente in ESC:
                salida += ESC[siguiente]
                i += 2
                continue
            octal = re.match(rb"[0-7]{1,3}", cadena[i + 1 : i + 4])
            if octal:
                salida.append(int(octal.group(), 8))
                i += 1 + len(octal.group())
                continue
            i += 1
            continue
        salida += byte
        i += 1
    return bytes(salida)


def _ancho_de_codigo(cmap: dict[str, str]) -> int:
    """Los PDFs con fuentes Type0 usan códigos de 2 bytes; los simples, de 1."""
    if not cmap:
        return 1
    return 2 if any(len(clave) == 4 for clave in cmap) else 1


def _mapear(bruto: bytes, cmap: dict[str, str], ancho: int) -> str:
    if not cmap:
        return _a_texto(bruto)
    trozos = [cmap.get(bruto[i : i + ancho].hex(), "") for i in range(0, len(bruto) - ancho + 1, ancho)]
    return "".join(trozos)


def _texto_de_stream(cuerpo: bytes, cmap: dict[str, str]) -> str:
    """Reconstruye el texto por coordenadas, no por orden de escritura.

    Un PDF no escribe "líneas": escribe bloques sueltos. Un cambio de negrita, un bullet o una
    palabra en otro color es un bloque nuevo con su propia posición. Cortar línea en cada bloque
    deja una palabra por renglón. Acá se junta todo lo que comparte altura (y) y después se ordena
    de izquierda a derecha, que es como lo lee un humano.
    """
    ancho = _ancho_de_codigo(cmap)
    corridas: list[tuple[float, float, str, float]] = []  # (y, x, texto, tamaño)

    x = y = 0.0
    tamano = 10.0
    leading = 0.0
    girado = False  # `1 0 0 -1 ... cm`: la y crece hacia abajo
    numeros: list[bytes] = []
    en_arreglo = False
    buffer: list[str] = []
    inicio: tuple[float, float] | None = None

    def cerrar() -> None:
        nonlocal buffer, inicio
        if buffer and inicio is not None:
            texto = "".join(buffer)
            if texto.strip():
                corridas.append((inicio[0], inicio[1], texto, tamano))
        buffer = []
        inicio = None

    def agregar(texto: str) -> None:
        nonlocal inicio
        if inicio is None:
            inicio = (y, x)
        buffer.append(texto)

    for token in TOKEN.findall(cuerpo):
        if token[:1].isdigit() or token[:1] == b"-":
            numeros.append(token)
            # dentro de un TJ, un salto negativo grande es un espacio entre palabras
            if en_arreglo and float(token) <= -120:
                agregar(" ")
            continue

        if token.startswith(b"("):
            agregar(_mapear(_decodificar_pdf(token[1:-1]), cmap, ancho))
        elif token.startswith(b"<"):
            hexadecimal = re.sub(rb"\s+", b"", token[1:-1]).decode("ascii", "ignore").lower()
            if len(hexadecimal) % 2:
                hexadecimal = hexadecimal[:-1]
            bruto = bytes.fromhex(hexadecimal)
            agregar(_mapear(bruto, cmap, ancho) if cmap else _a_texto(bruto))
        elif token == b"[":
            en_arreglo = True
        elif token == b"]":
            en_arreglo = False
        elif token == b"Tf" and numeros:
            with contextlib.suppress(ValueError):
                tamano = float(numeros[-1])
            numeros.clear()
        elif token == b"TL" and numeros:
            with contextlib.suppress(ValueError):
                leading = float(numeros[-1])
            numeros.clear()
        elif token == b"Tm" and len(numeros) >= 6:
            if inicio is not None:
                cerrar()
            matriz = numeros[-6:]
            try:
                x, y = float(matriz[4]), float(matriz[5])
                girado = float(matriz[3]) < 0
            except ValueError:
                pass
            numeros.clear()
        elif token in (b"Td", b"TD") and len(numeros) >= 2:
            desplazamiento_x, desplazamiento_y = float(numeros[-2]), float(numeros[-1])
            if desplazamiento_y != 0 and inicio is not None:
                cerrar()  # se movió de renglón
            x += desplazamiento_x
            y += desplazamiento_y
            if token == b"TD":
                leading = -desplazamiento_y
            numeros.clear()
        elif token in (b"T*", b"'", b'"'):
            cerrar()
            paso = leading or tamano * 1.2
            y += paso if girado else -paso
            x = 0.0
            numeros.clear()
        elif token in (b"ET", b"BT"):
            cerrar()
            numeros.clear()

    cerrar()

    if not corridas:
        return ""

    sentido = 1 if girado else -1
    corridas.sort(key=lambda corrida: (sentido * corrida[0], corrida[1]))

    lineas: list[list[tuple[float, float, str, float]]] = []
    for corrida in corridas:
        if lineas and abs(corrida[0] - lineas[-1][0][0]) <= max(2.0, corrida[3] * 0.4):
            lineas[-1].append(corrida)
        else:
            lineas.append([corrida])

    unidas: list[str] = []
    for linea in lineas:
        unidas.extend(_unir_linea(linea))
    return "\n".join(linea for linea in unidas if linea.strip())


def _unir_linea(corrida: list[tuple[float, float, str, float]]) -> list[str]:
    """Une las corridas de una misma altura, de izquierda a derecha.

    Cada corrida es un bloque de texto independiente del PDF (un cambio de negrita, un bullet, una
    celda). Entre bloques va un espacio; nunca se pegan dos palabras.
    """
    partes: list[str] = []
    for _, _, texto, _ in sorted(corrida, key=lambda c: c[1]):
        if partes and texto[:1] not in ".,;:)]!?" and not partes[-1].endswith((" ", "(", "-")):
            partes.append(" ")
        partes.append(texto)
    return ["".join(partes).rstrip()]


def _a_texto(bruto: bytes) -> str:
    try:
        return bruto.decode("cp1252")
    except UnicodeDecodeError:
        return bruto.decode("latin-1", "replace")


def _proporcion_legible(texto: str) -> float:
    """Qué proporción de palabras parece lenguaje real y no bytes decodificados al azar.

    Un PDF sin ToUnicode devuelve texto printable pero sin sentido: la cuenta de "caracteres
    imprimibles" lo daba por bueno. Lo que distingue es que las palabras tengan vocales y que
    aparezcan palabras funcionales.
    """
    if not texto.strip():
        return 0.0

    tokens = [token for token in re.findall(r"\S+", texto) if any(c.isalnum() for c in token)]
    if not tokens:
        return 0.0

    palabras = sum(1 for token in tokens if len(token) >= 3)
    plausibles = sum(
        1 for token in tokens if len(token) >= 3 and token.isalpha() and re.search(r"[aeiouáéíóúüAEIOUÁÉÍÓÚÜ]", token)
    )
    comunes = sum(1 for token in tokens if token.lower().strip(".,;:()[]\"'") in PALABRAS_COMUNES)

    # Texto real: palabras de 3+ letras con vocales, y alguna palabra funcional.
    # Bytes sueltos decodificados: muchos tokens de uno o dos caracteres y ningún lenguaje.
    calidad = max(plausibles / len(tokens), min(1.0, comunes / 3))
    return min(calidad, (palabras / len(tokens)) / 0.3)


# --------------------------------------------------------------------------- estructura


SECCIONES_CONOCIDAS = (
    "perfil",
    "resumen",
    "experiencia",
    "experiencia laboral",
    "educación",
    "educacion",
    "stack",
    "tecnologías",
    "tecnologias",
    "habilidades",
    "skills",
    "idiomas",
    "proyectos",
    "certificaciones",
)


PAGINA = re.compile(r"^(p[áa]gina|page|p[áa]g\.?)\s*\d+(\s*(de|of)\s*\d+)?$", re.IGNORECASE)
PAGINA_EN_LINEA = re.compile(r"\b(p[áa]gina|page)\s+\d+(\s*(de|of)\s*\d+)?", re.IGNORECASE)
TELEFONO = re.compile(r"^[\d\s()+.-]{7,}$")


def _parece_nombre(linea: str) -> bool:
    """2 a 4 palabras capitalizadas sin símbolos: 'Luca Nicolás Baello'."""
    limpia = linea.strip()
    if not limpia or len(limpia) > 60 or any(c in limpia for c in "|@/:"):
        return False
    palabras = limpia.split()
    if not 2 <= len(palabras) <= 4:
        return False
    return all(palabra[:1].isupper() and palabra.replace("-", "").replace("'", "").isalpha() for palabra in palabras)


def _sin_tildes(texto: str) -> str:
    return texto.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")


def _es_titulo(limpia: str) -> bool:
    """¿Esta línea es el título de una sección?

    1) Empieza con un nombre conocido ("EXPERIENCIA PROFESIONAL DESTACADA").
    2) Es corta, en mayúsculas y sin punto final: así titulan los CVs exportados de Word/Canva
       ("MÉTRICAS DE IMPACTO PRODUCTIVO"). Sin esto, el contenido se acumula en la sección anterior.
    """
    bajo = _sin_tildes(limpia.lower().strip(" :|"))
    if any(
        bajo == seccion or (bajo.startswith(seccion + " ") and len(limpia) <= 45 and not limpia.endswith("."))
        for seccion in SECCIONES_CONOCIDAS
    ):
        return True

    palabras = limpia.split()
    return 2 <= len(palabras) <= 7 and len(limpia) <= 60 and not limpia.endswith((".", ",", ";")) and limpia.isupper()


def _es_conocida(limpia: str) -> bool:
    bajo = _sin_tildes(limpia.lower().strip(" :|"))
    return any(bajo == seccion or bajo.startswith(seccion + " ") for seccion in SECCIONES_CONOCIDAS)


def _partir_encabezado(limpia: str) -> list[str]:
    """'EDUCACIÓN ACADÉMICA IDIOMAS & COMUNICACIÓN' son dos títulos en columnas distintas."""
    plano = _sin_tildes(limpia.lower())
    for nombre in ("idiomas", "proyectos", "perfil", "experiencia", "educacion", "skills", "stack", "resumen"):
        posicion = plano.find(" " + nombre)
        if posicion > 0 and limpia[:posicion].strip(" :|—-"):
            izquierda = limpia[:posicion].strip(" :|—-")
            if _es_conocida(izquierda):
                return [izquierda, limpia[posicion:].strip(" :|—-")]
    return [limpia]


def estructurar(texto: str) -> str:
    """Convierte texto plano (PDF) en el Markdown que entiende el parser.

    Es heurística y conservadora: promueve a sección los títulos conocidos y las líneas cortas en
    mayúsculas, y a bullet las que ya venían con viñeta. Los pies de página ("Página 1") se
    descartan, y el nombre se busca entre las primeras líneas en vez de tomar la primera a ciegas.
    """
    lineas = [linea.rstrip() for linea in texto.splitlines()]
    lineas = [linea for linea in lineas if not PAGINA.match(linea.strip())]
    lineas = [re.sub(r"\s{2,}", " ", PAGINA_EN_LINEA.sub("", linea)).strip() for linea in lineas]

    salida: list[str] = []
    nombre_puesto = False
    nombre_detectado = ""

    for indice, linea in enumerate(lineas):
        limpia = linea.strip()
        if not limpia:
            salida.append("")
            continue

        # cabecera repetida de la página siguiente: "Luca Baello — CV Extendido"
        if nombre_detectado and limpia.startswith(nombre_detectado) and len(limpia) > len(nombre_detectado) + 10:
            continue

        es_seccion = _es_titulo(limpia)

        if not nombre_puesto and not es_seccion:
            if _parece_nombre(limpia):
                salida.append(f"# {limpia}")
                nombre_detectado = limpia
                nombre_puesto = True
                continue
            if indice < 5 and not TELEFONO.match(limpia) and "@" not in limpia:
                salida.append(limpia)
                continue

        if es_seccion:
            salida.extend(f"## {titulo.upper()}" for titulo in _partir_encabezado(limpia))
            continue

        if re.match(r"^[•‣▪·\-*]\s+", limpia):
            salida.append("- " + re.sub(r"^[•‣▪·\-*]\s+", "", limpia))
            continue

        salida.append(limpia)

    if not nombre_puesto:
        for posicion, linea in enumerate(salida):
            if linea.strip():
                salida[posicion] = f"# {linea.lstrip('# ').strip()}"
                break

    return "\n".join(_desenvolver(salida))


def _continua(anterior: str, actual: str) -> bool:
    """¿`actual` es la continuación de un renglón cortado por el ancho de la página?"""
    if not anterior.strip() or not actual.strip():
        return False
    if anterior.startswith("#") or actual.startswith(("#", "- ")):
        return False
    if len(anterior) < 40:
        return False
    if anterior.startswith("- "):
        return actual[:1].islower() or actual[:1] in "([¿¡"  # el bullet sigue aunque haya punto
    if not actual[:1].islower():
        return False
    return not anterior.rstrip().endswith((".", "!", "?", ":", ";"))


def _desenvolver(lineas: list[str]) -> list[str]:
    salida: list[str] = []
    for linea in lineas:
        if salida and _continua(salida[-1], linea):
            salida[-1] = salida[-1].rstrip() + " " + linea.strip()
        else:
            salida.append(linea)
    return salida
