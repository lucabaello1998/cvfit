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
