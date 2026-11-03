"""Adaptación del CV a un aviso concreto, con una regla dura: no se inventa nada.

Todo texto generado se valida contra el CV original: si aparece una tecnología que el CV no
declara, el texto se descarta y queda el original. Adaptar es reordenar y resaltar, no maquillar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import aviso as modulo_aviso
from .cv import CV, Seccion
from .match import tecnologias_en


@dataclass
class Adaptado:
    nombre: str
    titulo: str
    contacto: str
    resumen: str
    secciones: list[Seccion]
    cambios: list[str] = field(default_factory=list)
    sin_respaldo: list[str] = field(default_factory=list)


def _relevancia(texto: str, objetivo: set[str]) -> int:
    return len(tecnologias_en(texto) & objetivo)


def _posicion(texto: str, skill: str) -> int:
    """Dónde aparece por primera vez la tecnología en el aviso (para priorizar el resumen)."""
    bajo = re.sub(r"\s+", " ", texto.lower())
    posiciones = []
    for variante in modulo_aviso.TECNOLOGIAS.get(skill, []):
        encontrado = bajo.find(variante)
        if encontrado >= 0:
            posiciones.append(encontrado)
    return min(posiciones) if posiciones else 9999


def _resumen(cv: CV, aviso) -> tuple[str, str]:
    """Resumen reescrito con lo que el aviso pide y el CV respalda."""
    original = ""
    if seccion := cv.seccion("perfil", "resumen", "profile", "summary"):
        original = " ".join(seccion.parrafos) or (seccion.bullets[0] if seccion.bullets else "")

    del_cv = tecnologias_en(cv.crudo)
    # primero los excluyentes, después por orden de aparición en el aviso
    ordenadas = sorted(aviso.skills, key=lambda s: (s not in aviso.duros, _posicion(aviso.texto, s)))
    utiles = [s for s in ordenadas if s in del_cv][:4]
    if not utiles:
        return original, "sin cambios (el aviso no pide nada que el CV declare)"

    anios = re.findall(r"(\d)\s*-\s*(\d)\s*años", cv.crudo, re.IGNORECASE)
    tramo = f"{anios[0][0]}-{anios[0][1]} años" if anios else "experiencia"

    propuesto = (
        f"Desarrollador fullstack SSR con {tramo} en sistemas productivos end-to-end. "
        f"Experiencia directa en {', '.join(utiles)}. "
        "Responsable de features completas: del esquema de base de datos al despliegue en producción."
    )

    sin_respaldo = tecnologias_en(propuesto) - del_cv
    if sin_respaldo:
        return original, f"resumen descartado: pedía {', '.join(sorted(sin_respaldo))} sin respaldo en el CV"
    return propuesto, f"resumen reescrito con {', '.join(utiles)}"


def _ordenar_bullets(bullets: list[str], objetivo: set[str], conservar_minimo: int = 4) -> list[tuple[str, int]]:
    """Ordena por relevancia y devuelve (bullet, puntaje)."""
    puntuados = [(b, _relevancia(b, objetivo)) for b in bullets]
    relevantes = [p for p in puntuados if p[1] > 0]
    neutros = [p for p in puntuados if p[1] == 0]
    relevantes.sort(key=lambda p: -p[1])
    if len(relevantes) < conservar_minimo:
        relevantes.extend(neutros[: conservar_minimo - len(relevantes)])
    return relevantes


def adaptar(cv: CV, aviso_texto: str, max_bullets: int = 6) -> Adaptado:
    aviso = modulo_aviso.analizar(aviso_texto)
    objetivo = set(aviso.skills)
    cambios: list[str] = []
    sin_respaldo: list[str] = []

    resumen, nota = _resumen(cv, aviso)
    cambios.append(nota)

    secciones: list[Seccion] = []
    for seccion in cv.secciones:
        nombre = seccion.nombre.lower()

        if "perfil" in nombre or "resumen" in nombre:
            continue  # el resumen se reemplaza arriba

        nueva = Seccion(nombre=seccion.nombre, parrafos=list(seccion.parrafos), tabla=list(seccion.tabla))

        if seccion.bloques:
            # El límite se aplica sobre el grupo completo (puesto + sus subtítulos),
            # no por bloque suelto: si no, un CV con subtítulos nunca recorta nada.
            grupos: list[list] = []
            for bloque in seccion.bloques:
                if bloque.nivel == 1 or not grupos:
                    grupos.append([bloque])
                else:
                    grupos[-1].append(bloque)

            for grupo in grupos:
                todos = [(bloque, bullet) for bloque in grupo for bullet in bloque.bullets]
                if len(todos) > max_bullets:
                    permitidos = {b for b, _ in _ordenar_bullets([b for _, b in todos], objetivo)[:max_bullets]}
                    titulo = grupo[0].titulo or grupo[0].subtitulo or "experiencia"
                    cambios.append(f"{titulo[:48]}: {len(todos)} → {len(permitidos)} bullets")
                else:
                    permitidos = {b for _, b in todos}
                for bloque in grupo:
                    nuevo = type(bloque)(
                        **{**bloque.__dict__, "bullets": [b for b in bloque.bullets if b in permitidos]}
                    )
                    if nuevo.nivel == 2 and not nuevo.bullets:
                        continue  # un subtítulo sin bullets es un título huérfano
                    nueva.bloques.append(nuevo)

        if seccion.bullets:
            ordenados = _ordenar_bullets(seccion.bullets, objetivo)
            recortados = [b for b, _ in ordenados[:max_bullets]]
            nueva.bullets = recortados
            if len(recortados) < len(seccion.bullets):
                cambios.append(f"{seccion.nombre}: {len(seccion.bullets)} → {len(recortados)} bullets")

        secciones.append(nueva)

    # secciones con más encaje primero (Resultados/Experiencia antes que lo periférico)
    def peso(seccion: Seccion) -> int:
        texto = " ".join([*seccion.parrafos, *seccion.bullets, *(b for bl in seccion.bloques for b in bl.bullets)])
        return _relevancia(texto, objetivo)

    fijas = {"educaci", "idioma", "educación", "lenguaje"}
    secciones.sort(key=lambda s: (any(f in s.nombre.lower() for f in fijas), -peso(s)))

    # tablas (proyectos): reordenar filas por relevancia
    for seccion in secciones:
        if seccion.tabla:
            seccion.tabla.sort(key=lambda fila: -_relevancia(" ".join(fila), objetivo))

    for skill in sorted(objetivo - tecnologias_en(cv.crudo)):
        sin_respaldo.append(skill)

    return Adaptado(
        nombre=cv.nombre,
        titulo=cv.titulo,
        contacto=cv.contacto,
        resumen=resumen,
        secciones=secciones,
        cambios=cambios,
        sin_respaldo=sin_respaldo,
    )
