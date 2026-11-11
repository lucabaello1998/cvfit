"""Comparar varios CVs contra el mismo aviso y decir cuál encaja mejor.

No hay juicio de valor ni "el mejor candidato": hay cobertura de requisitos medida igual para cada
CV. Sirve para decidir **qué versión mandar**: la que declara TypeScript, la que pone las métricas
primero, la que es de una página.
"""

from __future__ import annotations

from dataclasses import dataclass

from .cv import CV, parsear
from .match import Resultado, evaluar


@dataclass
class Candidato:
    nombre: str
    cv: CV
    resultado: Resultado

    @property
    def orden(self) -> tuple:
        """Más encaje, menos gaps excluyentes, más requisitos cubiertos. El nombre desempata."""
        return (
            -self.resultado.score,
            not self.resultado.confiable,
            len(self.resultado.faltantes),
            -len(self.resultado.cubiertas),
            self.nombre.lower(),
        )


def comparar(cvs: dict[str, CV], aviso_texto: str) -> list[Candidato]:
    """Devuelve los CVs ordenados de mejor a peor encaje contra el mismo aviso."""
    filas = [Candidato(nombre, cv, evaluar(cv, aviso_texto)) for nombre, cv in cvs.items()]
    return sorted(filas, key=lambda fila: fila.orden)


def comparar_textos(textos: dict[str, str], aviso_texto: str) -> list[Candidato]:
    """Igual que `comparar` pero desde Markdown o texto ya extraído (lo que usa el servidor)."""
    return comparar({nombre: parsear(texto) for nombre, texto in textos.items()}, aviso_texto)


@dataclass
class Oferta:
    """Un aviso candidato para el mismo CV."""

    nombre: str
    texto: str
    resultado: Resultado

    @property
    def orden(self) -> tuple:
        return (
            -self.resultado.score,
            not self.resultado.confiable,
            len(self.resultado.faltantes),
            -len(self.resultado.cubiertas),
            self.nombre.lower(),
        )


def nombre_de_aviso(texto: str, posicion: int = 1) -> str:
    """Primera línea con contenido, recortada: es lo que se ve en el ranking."""
    for linea in texto.splitlines():
        limpia = linea.strip().lstrip("#").strip()
        if limpia:
            return limpia[:60] + ("…" if len(limpia) > 60 else "")
    return f"Aviso {posicion}"


def nombrar_avisos(textos: list[str]) -> dict[str, str]:
    """Un nombre visible por aviso, sin pisarse aunque dos empiecen con la misma línea."""
    nombrados: dict[str, str] = {}
    for posicion, texto in enumerate(textos, start=1):
        base = nombre_de_aviso(texto, posicion)
        nombre = base
        repetido = 2
        while nombre in nombrados:
            nombre = f"{base} ({repetido})"
            repetido += 1
        nombrados[nombre] = texto
    return nombrados


def comparar_avisos(cv: CV | str, avisos: dict[str, str]) -> list[Oferta]:
    """El mismo CV contra varios avisos: a cuál conviene postular primero."""
    if isinstance(cv, str):
        cv = parsear(cv)
    filas = [Oferta(nombre, texto, evaluar(cv, texto)) for nombre, texto in avisos.items()]
    return sorted(filas, key=lambda fila: fila.orden)
