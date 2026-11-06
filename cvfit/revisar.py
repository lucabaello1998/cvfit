"""Revisión del CV: qué arreglaría un reclutador antes de que lo mandes.

Son reglas explícitas, sin LLM: no reescriben experiencia, sólo marcan lo que sobra, lo que falta y
lo que se puede decir mejor. La base son las guías públicas de reclutamiento (Harvard MCS: active
voice, sin pronombres, resultados cuantificados, sin foto ni edad; Indeed: cronológico salvo huecos o
cambio de rubro; Jobscan: un bullet = verbo de acción + resultado medible + palabra clave).

Nada de esto inventa: cuando sugiere una reescritura, reusa el texto del propio CV y deja el número
a completar por quien lo vivió.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .cv import CV

ALTO, MEDIO, BAJO = "alto", "medio", "bajo"

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")
TELEFONO = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{3,4}")
ANIO = re.compile(r"\b(?:19|20)\d{2}\b")
MESES = r"(?:ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic)"
RANGO = re.compile(
    rf"({MESES}[a-z]*\.?\s*)?((?:19|20)\d{{2}})\s*(?:[-–—]|a|hasta)\s*({MESES}[a-z]*\.?\s*)?"
    r"((?:19|20)\d{2}|actual|presente|hoy)",
    re.I,
)
ACTUAL = re.compile(r"\b(actual|presente|hoy)\b", re.I)

PRONOMBRES = re.compile(r"\b(yo|mi|mis|me|nosotros|nuestro|nuestra)\b", re.I)
RELLENO = re.compile(
    r"\b(proactiv[oa]|din[aá]mic[oa]|comprometid[oa]|apasionad[oa]|"
    r"trabajo en equipo|orientad[oa] a resultados|autodidacta|resiliente|"
    r"ganas de aprender|habilidades comunicativas|pensamiento cr[ií]tico)\b",
    re.I,
)
REFERENCIAS = re.compile(r"\breferencias?\b", re.I)
EDAD = re.compile(r"\b(edad|estado civil|fecha de nacimiento|dni)\b", re.I)

# Arranques débiles: describen el cargo en vez del logro. Cada uno tiene una salida gramatical.
PATRONES = [
    (re.compile(r"^(?:fui |era )?responsable\s+de(l)?\s+", re.I), "cargo"),
    (re.compile(r"^(?:estuve\s+)?(?:a cargo|encargad[oa])\s+de(l)?\s+", re.I), "cargo"),
    (re.compile(r"^me\s+encargu[eé]\s+de(l)?\s+", re.I), "cargo"),
    (re.compile(r"^(?:ten[ií]a|tuve)\s+a\s+cargo\s+", re.I), "cargo"),
    (re.compile(r"^(?:particip[eé]|form[eé]\s+parte|colabor[eé])\s+(?:en\s+)?", re.I), "aporte"),
    (re.compile(r"^ayud[eé]\s+(?:a\s+)?", re.I), "aporte"),
    (re.compile(r"^trabaj[eé]\s+(?:en|con)\s+", re.I), "ocupacion"),
    (re.compile(r"^(?:realic[eé]|hice)\s+", re.I), "ejecucion"),
]

VERBOS_POR_TEMA = [
    (re.compile(r"\b(equipo|personas|devs|desarrolladores|junior|celula|squad)\b", re.I), "Lideré"),
    (re.compile(r"\b(pipeline|deploy|despliegue|ci/cd|automatiz|script)\b", re.I), "Automaticé"),
    (re.compile(r"\b(bug|incidente|error|vulnerabilidad|ca[ií]da|timing)\b", re.I), "Resolví"),
    (re.compile(r"\b(migraci[oó]n|migramos|migr[eé])\b", re.I), "Migré"),
    (re.compile(r"\b(reporte|dashboard|tablero|m[eé]trica|indicador)\b", re.I), "Armé"),
    (re.compile(r"\b(sistema|aplicaci[oó]n|api|servicio|plataforma|feature|funcionalidad)\b", re.I), "Mantuve"),
]

VERBOS_SUGERIDOS = {
    "Liderazgo": ["Lideré", "Coordiné", "Supervisé", "Delegué", "Priorizé"],
    "Construcción": ["Desarrollé", "Implementé", "Construí", "Diseñé", "Integré"],
    "Mejora": ["Optimicé", "Reduje", "Automaticé", "Simplifiqué", "Aceleré"],
    "Operación": ["Mantuve", "Operé", "Monitoreé", "Documenté", "Resolví"],
    "Comunicación": ["Presenté", "Negocié", "Coordiné", "Documenté", "Capacité"],
}

GUIA_ESTILOS = [
    {
        "nombre": "ATS",
        "cuando": "Siempre que el CV entre por un portal o no sepas quién lo va a leer.",
        "detalle": (
            "Una columna, títulos estándar y sin foto: es lo que mejor leen los filtros "
            "(el 99,7% de los reclutadores filtra por palabra clave)."
        ),
    },
    {
        "nombre": "Clásico",
        "cuando": "Cuando lo mandás por mail a una persona, a una consultora o lo llevás impreso.",
        "detalle": (
            "Una columna con un acento de color: ordena la lectura sin ensuciar el parseo. "
            "Es el que se ve mejor en una entrevista."
        ),
    },
    {
        "nombre": "Compacto",
        "cuando": "Cuando tenés muchos años o proyectos y necesitás que entre en dos páginas.",
        "detalle": (
            "Dos columnas: algunos ATS las leen mal, así que usalo cuando ya sabés que hay "
            "una persona del otro lado."
        ),
    },
]

CONSEJOS = [
    {
        "titulo": "La fórmula del bullet",
        "cuerpo": [
            "Verbo de acción + qué hiciste + resultado medible + contexto.",
            "«Trabajé con el equipo para arreglar bugs» no dice nada. "
            "«Priorizé 50 tickets y bajé 22% las caídas críticas en Q3» sí.",
            "Si el bullet no cambia ninguna decisión de quien lee, sobra.",
        ],
    },
    {
        "titulo": "De dónde sacar el número",
        "cuerpo": [
            "Volumen: cuántos sistemas, tickets, clientes, personas.",
            "Tiempo: de cuántas horas a cuántas, cuántos días tardaba antes.",
            "Plata: costo evitado, horas ahorradas, facturación.",
            "Calidad: % de error, uptime, incidencias, cobertura de tests.",
            "Alcance: cuántos equipos o áreas usaron lo que hiciste.",
        ],
    },
    {
        "titulo": "Lo que resta puntos",
        "cuerpo": [
            "Primera persona («yo», «me encargué»): el CV se escribe en tercera implícita.",
            "«Responsable de»: describe el cargo, no lo que lograste.",
            "Adjetivos sin evidencia: proactivo, dinámico, apasionado.",
            "Listar tecnologías sin decir qué hiciste con ellas.",
            "Objetivo genérico («busco desarrollarme»): mejor un resumen con lo que aportás.",
            "Foto, edad o estado civil: en un ATS no suman y abren la puerta a sesgos.",
        ],
    },
    {
        "titulo": "Antes de apretar enviar",
        "cuerpo": [
            "Abrí el PDF y mirá que no se corte nada ni queden páginas casi vacías.",
            "Nombrá el archivo CV_Nombre_Puesto.pdf, no «cv final final 2».",
            "Un solo mail y un solo teléfono, los que revisás.",
            "El título del CV debería parecerse al título del aviso: es la primera palabra clave.",
            "Leelo en voz alta: si te trabás, quien lee también.",
        ],
    },
]


@dataclass(frozen=True)
class Hallazgo:
    area: str
    nivel: str
    mensaje: str
    como: str


@dataclass(frozen=True)
class Reescritura:
    original: str
    propuesta: str
    motivo: str


@dataclass
class Revision:
    hallazgos: list[Hallazgo] = field(default_factory=list)
    reescrituras: list[Reescritura] = field(default_factory=list)
    bien: list[str] = field(default_factory=list)

    @property
    def altos(self) -> int:
        return sum(1 for h in self.hallazgos if h.nivel == ALTO)

    @property
    def medios(self) -> int:
        return sum(1 for h in self.hallazgos if h.nivel == MEDIO)

    @property
    def estado(self) -> str:
        if self.altos:
            return "mal"
        if self.medios:
            return "medio"
        return "ok"

    def agregar(self, area: str, nivel: str, mensaje: str, como: str) -> None:
        self.hallazgos.append(Hallazgo(area, nivel, mensaje, como))


def _con_digitos(texto: str) -> bool:
    return bool(re.search(r"\d", texto))


def _bullets_de_experiencia(cv: CV) -> list[str]:
    salida: list[str] = []
    for seccion in cv.secciones:
        if any(palabra in seccion.nombre.lower() for palabra in ("experiencia", "trabajo", "empleo")):
            salida.extend(seccion.bullets)
            for bloque in seccion.bloques:
                salida.extend(bloque.bullets)
    return salida or cv.bullets


def _titulo_de_bloque(bloque) -> str:
    return f"{bloque.titulo} {bloque.subtitulo}".strip()


MESES_NUM = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
}


@dataclass(frozen=True)
class Periodo:
    """Puesto con fechas llevadas a meses absolutos, para comparar sin adivinar."""

    titulo: str
    inicio: int
    fin: int | None


def _mes(nombre: str | None, por_defecto: int) -> int:
    if not nombre:
        return por_defecto
    return MESES_NUM.get(nombre.strip().lower()[:3], por_defecto)


def _fechas(cv: CV) -> list[Periodo]:
    salida: list[Periodo] = []
    for seccion in cv.secciones:
        if not any(p in seccion.nombre.lower() for p in ("experiencia", "trabajo", "empleo")):
            continue
        for bloque in seccion.bloques:
            if bloque.nivel != 1:  # los sub-bloques son proyectos dentro del puesto
                continue
            titulo = _titulo_de_bloque(bloque)
            rango = RANGO.search(titulo)
            if rango:
                inicio = int(rango.group(2)) * 12 + _mes(rango.group(1), 1) - 1
                fin_texto = rango.group(4)
                fin = (
                    None
                    if ACTUAL.search(fin_texto)
                    else int(fin_texto) * 12 + _mes(rango.group(3), 12) - 1
                )
                salida.append(Periodo(titulo, inicio, fin))
                continue
            anios = sorted(int(a) for a in ANIO.findall(titulo))
            if len(anios) >= 2:
                salida.append(Periodo(titulo, anios[0] * 12, anios[-1] * 12 + 11))
            elif anios:
                salida.append(Periodo(titulo, anios[0] * 12, None))
    return salida


def _faltantes(cv: CV) -> tuple[bool, bool, bool, bool]:
    def hay(*nombres: str) -> bool:
        return cv.seccion(*nombres) is not None

    experiencia = hay("experiencia", "trabajo", "empleo", "proyectos")
    educacion = hay("educaci", "formaci", "estudios", "carrera")
    habilidades = hay("stack", "habilidad", "tecnolog", "conocimiento", "herramienta", "skill")
    perfil = hay("perfil", "resumen", "sobre", "acerca", "summary")
    return experiencia, educacion, habilidades, perfil


def _verbos_de(texto: str) -> str:
    for patron, verbo in VERBOS_POR_TEMA:
        if patron.search(texto):
            return verbo
    return "Gestioné"


REDUNDANTE = {
    "Migré": "migraci",
    "Mantuve": "mantenim",
    "Automaticé": "automatizaci",
    "Documenté": "documentaci",
    "Optimicé": "optimizaci",
}


def _contraer(texto: str) -> str:
    texto = re.sub(r"\bde el\b", "del", texto)
    return re.sub(r"\ba el\b", "al", texto)


def _aporte(resto: str) -> str:
    if re.search(r"\b(equipo|squad|c[eé]lula|grupo|cap[ií]tulo)\b", resto, re.I):
        return f"Formé parte de {resto}"
    if re.search(r"\b(nuevos|nuevas|junior|juniors|ingresantes|compañer|clientes|usuarios)\b", resto, re.I):
        return f"Acompañé a {resto}"
    return f"Contribuí a {resto}"


def _propuesta(texto: str) -> Reescritura | None:
    for patron, tipo in PATRONES:
        coincidencia = patron.match(texto)
        if not coincidencia:
            continue
        resto = texto[coincidencia.end():].strip(" .")
        if len(resto) < 6:
            return None
        if coincidencia.groups() and coincidencia.group(1):
            resto = "el " + resto

        if tipo == "cargo":
            verbo = _verbos_de(resto)
            if REDUNDANTE.get(verbo) and re.match(rf"(el |la )?{REDUNDANTE[verbo]}", resto, re.I):
                verbo = "Ejecuté"
            propuesta = f"{verbo} {resto}"
        elif tipo == "aporte":
            propuesta = _aporte(resto)
        elif tipo == "ocupacion":
            propuesta = f"Me ocupé de {resto}"
        else:
            propuesta = f"Ejecuté {resto}"

        if re.match(r"(el |la )?\w+ci[oó]n\b", resto):
            propuesta = f"Ejecuté {resto}"
        propuesta = _contraer(propuesta)
        if _con_digitos(resto):
            motivo = (
                "Arrancá por el verbo en pasado y cerrá con lo que cambió: ya tenés el número, "
                "falta el resultado."
            )
        else:
            motivo = (
                "Arrancá por el verbo en pasado y sumá el resultado: cuántos, cuánto bajó o en "
                "cuánto tiempo. Elegí el verbo que refleje lo que hacías."
            )
        return Reescritura(texto, propuesta, motivo)
    return None


def revisar(cv: CV, estilo: str = "ats") -> Revision:
    """Devuelve hallazgos accionables, reescrituras sugeridas y lo que ya está bien."""
    revision = Revision()
    experiencia, educacion, habilidades, perfil = _faltantes(cv)
    bullets = _bullets_de_experiencia(cv)
    texto_completo = cv.crudo
    encabezado = "\n".join(cv.crudo.replace("\r\n", "\n").split("\n")[:6])
    contacto = cv.contacto or encabezado

    # --- contacto ---
    if not EMAIL.search(contacto):
        revision.agregar("contacto", ALTO, "No encuentro un mail en el CV.", "Sumá un mail que revises todos los días, en el encabezado.")
    if not TELEFONO.search(contacto):
        revision.agregar("contacto", ALTO, "No encuentro un teléfono en el CV.", "Poné el número con código de área, en el mismo renglón que el mail.")
    if not re.search(r"linkedin\.com|github\.com", texto_completo, re.I):
        revision.agregar("contacto", BAJO, "No hay LinkedIn ni GitHub.", "Para un perfil técnico suman: el reclutador los abre antes de la entrevista.")
    if EDAD.search(texto_completo):
        revision.agregar("contacto", BAJO, "Hay edad, estado civil o DNI.", "No suman en un ATS y abren la puerta a sesgos: se sacan.")

    # --- estructura ---
    if not experiencia:
        revision.agregar("estructura", ALTO, "No hay sección de experiencia.", "Abrí una sección EXPERIENCIA con puestos, empresa y fechas: es lo primero que se mira.")
    if not educacion:
        revision.agregar("estructura", MEDIO, "No hay sección de educación.", "Agregá EDUCACIÓN con título, institución y año, aunque siga en curso.")
    if not habilidades:
        revision.agregar("estructura", MEDIO, "No hay sección de stack o habilidades.", "Armá una tabla por área (frontend, backend, datos) en vez de una lista suelta.")
    if not perfil:
        revision.agregar("estructura", BAJO, "No hay perfil ni resumen.", "Dos o tres líneas arriba: qué hacés, con qué stack y cuántos años.")
    if cv.seccion("objetivo"):
        revision.agregar("estructura", BAJO, "Tenés una sección «objetivo».", "Un objetivo dice lo que querés; un resumen dice lo que aportás. Cambialo por PERFIL.")
    if REFERENCIAS.search(texto_completo):
        revision.agregar("estructura", BAJO, "Figuran referencias.", "No se listan: se piden en la entrevista. Ese espacio rinde más con un logro.")

    # --- fechas ---
    fechas = _fechas(cv)
    for seccion in cv.secciones:
        if not any(p in seccion.nombre.lower() for p in ("experiencia", "trabajo", "empleo")):
            continue
        for bloque in seccion.bloques:
            if bloque.nivel != 1:
                continue
            titulo = _titulo_de_bloque(bloque)
            if titulo and not ANIO.search(titulo):
                revision.agregar(
                    "fechas",
                    MEDIO,
                    f"«{titulo[:60]}» no tiene fechas.",
                    "Cada puesto necesita mes y año: sin fechas no se puede ver continuidad.",
                )
    ordenados = sorted(fechas, key=lambda p: p.inicio, reverse=True)
    if [p.titulo for p in fechas] != [p.titulo for p in ordenados]:
        revision.agregar(
            "estructura",
            MEDIO,
            "Los puestos no están del más reciente al más viejo.",
            "Ese es el orden que espera cualquiera que lea un CV: primero lo último.",
        )
    for previo, actual in zip(ordenados, ordenados[1:], strict=False):
        if actual.fin is None:
            continue
        if previo.inicio - actual.fin > 12:
            revision.agregar(
                "fechas",
                MEDIO,
                f"Hueco de más de un año antes de «{previo.titulo[:50]}».",
                "Si fue estudio, freelance o búsqueda, decilo en una línea: un hueco explicado deja de ser duda.",
            )
        elif previo.inicio < actual.fin - 12:
            revision.agregar(
                "fechas",
                MEDIO,
                f"Fechas solapadas entre «{actual.titulo[:40]}» y «{previo.titulo[:40]}».",
                "Si fueron en paralelo, aclaralo; si no, corregí el año.",
            )

    # --- redacción ---
    sin_numero = [b for b in bullets if not _con_digitos(b)]
    if bullets and len(sin_numero) == len(bullets):
        revision.agregar("redaccion", ALTO, "Ningún bullet tiene un número.", "Sin resultados medibles el CV se lee como una lista de tareas. Sumá al menos uno por puesto.")
    elif len(sin_numero) >= 3:
        revision.agregar(
            "redaccion",
            MEDIO,
            f"{len(sin_numero)} de {len(bullets)} bullets no tienen números.",
            "No hace falta en todos: alcanza con que cada puesto tenga uno o dos con resultado.",
        )
    primera_persona = [b for b in bullets if PRONOMBRES.search(b)]
    if primera_persona:
        revision.agregar(
            "redaccion",
            MEDIO,
            f"{len(primera_persona)} bullet(s) en primera persona.",
            "El CV va sin «yo» ni «me encargué»: arrancá directo por el verbo en pasado.",
        )
    relleno = RELLENO.findall(texto_completo)
    if relleno:
        revision.agregar(
            "redaccion",
            MEDIO,
            f"Adjetivos sin evidencia: {', '.join(sorted(set(r.lower() for r in relleno)))[:80]}.",
            "Cada adjetivo ocupa una línea que podría tener un logro. Si lo dejás, respaldalo con un hecho.",
        )
    debiles = [b for b in bullets if any(patron.match(b) for patron, _tipo in PATRONES)]
    if debiles:
        revision.agregar(
            "redaccion",
            MEDIO,
            f"{len(debiles)} bullet(s) empiezan con «responsable de» o similar.",
            "Eso describe el cargo, no el logro. Abajo tenés las reescrituras propuestas.",
        )
    largos = [b for b in bullets if len(b) > 240]
    if largos:
        revision.agregar("redaccion", BAJO, f"{len(largos)} bullet(s) de más de 240 caracteres.", "Un bullet debería entrar en dos renglones: si no, partilo en dos.")
    iniciales = [b.split()[0].lower() for b in bullets if b.split()]
    repetidos = {palabra for palabra in iniciales if iniciales.count(palabra) >= 3 and len(palabra) > 3}
    if repetidos:
        revision.agregar("redaccion", BAJO, f"Varios bullets empiezan igual: {', '.join(sorted(repetidos))}.", "Variá el verbo: el primer tercio del renglón es lo único que se escanea.")
    mayusculas = {s.nombre for s in cv.secciones}
    if any(s.isupper() for s in mayusculas) and any(not s.isupper() for s in mayusculas):
        revision.agregar("formato", BAJO, "Títulos de sección mezclados: unos en mayúsculas y otros no.", "Elegí uno y usalo en todas: la consistencia se nota.")
    if estilo == "ats" and re.search(r"foto|perfil\.(jpg|png)", texto_completo, re.I):
        revision.agregar("formato", BAJO, "Estás en ATS con foto.", "En ATS la foto no suma y a veces resta: para un portal, mandalo sin foto.")

    # --- reescrituras ---
    vistas: set[str] = set()
    for bullet in bullets:
        if len(revision.reescrituras) >= 6:
            break
        propuesta = _propuesta(bullet)
        if propuesta and propuesta.propuesta.lower() not in vistas:
            vistas.add(propuesta.propuesta.lower())
            revision.reescrituras.append(propuesta)

    # --- lo que está bien ---
    if EMAIL.search(contacto) and TELEFONO.search(contacto):
        revision.bien.append("El contacto está completo.")
    if bullets:
        con_numero = len(bullets) - len(sin_numero)
        if con_numero:
            revision.bien.append(f"{con_numero} de {len(bullets)} bullets tienen números ({round(100 * con_numero / len(bullets))}%).")
        if not primera_persona:
            revision.bien.append("Ningún bullet está en primera persona.")
    if len(fechas) >= 2 and all(ANIO.search(p.titulo) for p in fechas):
        revision.bien.append("Todos los puestos tienen fechas.")
    if habilidades and perfil:
        revision.bien.append("Tiene resumen y stack: se entiende en diez segundos.")
    if not relleno:
        revision.bien.append("No hay adjetivos de relleno.")

    orden = {ALTO: 0, MEDIO: 1, BAJO: 2}
    revision.hallazgos.sort(key=lambda h: orden.get(h.nivel, 3))
    return revision
