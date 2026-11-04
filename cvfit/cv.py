"""Parser de CV en Markdown a una estructura que las plantillas pueden renderizar.

No pretende entender cualquier Markdown: entiende el CV que se usa acá.
H1 = nombre, primera línea de énfasis = título, H2 = sección, H3 = bloque, "-" = bullet,
y tablas de dos o tres columnas (stack / proyectos).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

NEGRITA = re.compile(r"\*\*(.+?)\*\*")
ENLACE = re.compile(r"\[(.+?)\]\((.+?)\)")


@dataclass
class Bloque:
    titulo: str = ""
    subtitulo: str = ""
    notas: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    nivel: int = 1  # 1 = puesto/empresa (H3), 2 = subtítulo en negrita dentro del puesto


@dataclass
class Seccion:
    nombre: str
    parrafos: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    bloques: list[Bloque] = field(default_factory=list)
    tabla: list[list[str]] = field(default_factory=list)


@dataclass
class CV:
    nombre: str
    titulo: str
    contacto: str
    secciones: list[Seccion]
    crudo: str

    def seccion(self, *nombres: str) -> Seccion | None:
        buscados = [n.lower() for n in nombres]
        for seccion in self.secciones:
            if any(b in seccion.nombre.lower() for b in buscados):
                return seccion
        return None

    @property
    def bullets(self) -> list[str]:
        salida: list[str] = []
        for seccion in self.secciones:
            salida.extend(seccion.bullets)
            for bloque in seccion.bloques:
                salida.extend(bloque.bullets)
        return salida

    @property
    def tecnologias(self) -> list[str]:
        """Todas las tecnologías declaradas, en el orden en que aparecen."""
        vistas: dict[str, None] = {}
        for seccion in self.secciones:
            for fila in seccion.tabla:
                if len(fila) >= 2:
                    for pieza in re.split(r"[,/;|]", fila[1]):
                        pieza = pieza.strip()
                        if pieza and len(pieza) < 40:
                            vistas.setdefault(pieza, None)
            for texto in [*seccion.parrafos, *seccion.bullets, *(b for bl in seccion.bloques for b in bl.bullets)]:
                for pieza in re.findall(r"\b[A-Za-z][\w.+#/-]{1,20}\b", texto):
                    vistas.setdefault(pieza, None)
        return list(vistas)


def _limpiar(texto: str) -> str:
    texto = NEGRITA.sub(r"\1", texto)
    texto = ENLACE.sub(r"\1", texto)
    return texto.strip()


def parsear(markdown: str) -> CV:
    lineas = markdown.replace("\r\n", "\n").split("\n")
    nombre, titulo, contacto = "", "", ""
    secciones: list[Seccion] = []
    actual: Seccion | None = None
    bloque: Bloque | None = None
    tabla_en_curso: list[list[str]] = []
    sueltos_parrafos: list[str] = []
    sueltos_bullets: list[str] = []

    def cerrar_tabla() -> None:
        nonlocal tabla_en_curso
        if actual is not None and tabla_en_curso:
            actual.tabla.extend(tabla_en_curso)
        tabla_en_curso = []

    for linea in lineas:
        limpia = linea.strip()

        if limpia.startswith("# "):
            cerrar_tabla()
            nombre = _limpiar(limpia[2:])
            continue

        if limpia.startswith("## "):
            cerrar_tabla()
            actual = Seccion(nombre=_limpiar(limpia[3:]))
            secciones.append(actual)
            bloque = None
            continue

        if limpia.startswith("### "):
            cerrar_tabla()
            if actual is None:
                actual = Seccion(nombre="EXPERIENCIA")
                secciones.append(actual)
            bloque = Bloque(titulo=_limpiar(limpia[4:]))
            actual.bloques.append(bloque)
            continue

        if limpia.startswith("|") and limpia.endswith("|"):
            celdas = [c.strip() for c in limpia.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in celdas):
                # separador: la fila anterior era el encabezado de la tabla
                if tabla_en_curso:
                    tabla_en_curso.pop()
                continue
            tabla_en_curso.append([_limpiar(c) for c in celdas])
            continue
        cerrar_tabla()

        if limpia.startswith("---") or not limpia:
            continue

        if limpia.startswith(("- ", "* ")):
            texto = _limpiar(limpia[2:])
            if bloque is not None:
                bloque.bullets.append(texto)
            elif actual is not None:
                actual.bullets.append(texto)
            else:
                sueltos_bullets.append(texto)
            continue

        texto = _limpiar(limpia)
        if not nombre:
            continue
        if not secciones and not contacto and not titulo and texto:
            titulo = texto
            continue
        if not secciones and not contacto and "|" in texto:
            contacto = texto
            continue
        if bloque is not None and not bloque.bullets and bloque.nivel == 1 and not bloque.subtitulo:
            bloque.subtitulo = texto
            continue
        if bloque is not None:
            # línea en negrita dentro de un puesto (ej. "Portal de gestión logística"):
            # abre un sub-bloque, así sus bullets quedan debajo y no sueltos en la sección
            if actual is None:
                actual = Seccion(nombre="EXPERIENCIA")
                secciones.append(actual)
            bloque = Bloque(subtitulo=texto, nivel=2)
            actual.bloques.append(bloque)
            continue
        if actual is not None:
            actual.parrafos.append(texto)
        else:
            sueltos_parrafos.append(texto)

    if not secciones and (sueltos_parrafos or sueltos_bullets):
        # CV sin un solo H2 (texto pegado o extraído de un PDF sin estructura): no se tira nada
        secciones.append(Seccion(nombre="EXPERIENCIA", parrafos=sueltos_parrafos, bullets=sueltos_bullets))

    return CV(nombre=nombre, titulo=titulo, contacto=contacto, secciones=secciones, crudo=markdown)


def cargar(ruta) -> CV:
    from pathlib import Path

    return parsear(Path(ruta).read_text(encoding="utf-8-sig"))
