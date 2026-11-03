"""Encaje CV ↔ aviso.

Devuelve cobertura de requisitos, veredicto y —lo más útil— los gaps, ordenados por cuánto pesan.
Nunca dice "entrás": dice cuánto del aviso podés respaldar con lo que ya está en tu CV.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import aviso as modulo_aviso
from .cv import CV

PESO_DURO = 3
PESO_BLANDO = 1


@dataclass
class Resultado:
    score: int
    veredicto: str
    cubiertas: list[str] = field(default_factory=list)
    faltantes: list[str] = field(default_factory=list)
    blandas_faltantes: list[str] = field(default_factory=list)
    observaciones: list[str] = field(default_factory=list)
    confiable: bool = True
    total_requisitos: int = 0

    @property
    def emoji(self) -> str:
        return {"alta": "verde", "media": "amarillo", "baja": "rojo"}[self.veredicto]


def tecnologias_en(texto: str) -> set[str]:
    """Tecnologías del diccionario presentes en un texto cualquiera."""
    plano = re.sub(r"\s+", " ", texto.lower())
    encontradas = set()
    for canonico, alias in modulo_aviso.TECNOLOGIAS.items():
        if any(modulo_aviso._buscar_alias(plano, variante) for variante in alias):
            encontradas.add(canonico)
    return encontradas


def _anios_del_cv(cv: CV) -> int | None:
    if coincidencias := re.findall(r"(\d)\s*-\s*(\d)\s*años", cv.crudo, re.IGNORECASE):
        return max(int(a) for _, a in coincidencias)
    if coincidencias := re.findall(r"(\d{1,2})\s*\+?\s*años", cv.crudo, re.IGNORECASE):
        return max(int(c) for c in coincidencias)
    return None


def _nivel_ingles_cv(cv: CV) -> str:
    bajo = cv.crudo.lower()
    if re.search(r"inglés[^\n]{0,40}(c1|c2|avanzado|fluido)", bajo) or "advanced english" in bajo:
        return "avanzado"
    if re.search(r"inglés[^\n]{0,40}(b1|b2|intermedio)", bajo):
        return "intermedio"
    return ""


def evaluar(cv: CV, aviso_texto: str) -> Resultado:
    aviso = modulo_aviso.analizar(aviso_texto)
    del_cv = tecnologias_en(cv.crudo)

    pedidas = aviso.skills
    resultado = Resultado(score=0, veredicto="baja", total_requisitos=len(pedidas))

    if not pedidas:
        resultado.observaciones.append(
            "El aviso no menciona tecnologías reconocibles: el puntaje se basa en muy poca información."
        )
        resultado.confiable = False
        resultado.score = 0
        resultado.veredicto = "baja"
        return resultado

    peso_total = 0
    peso_cubierto = 0
    for skill in pedidas:
        peso = PESO_DURO if skill in aviso.duros else PESO_BLANDO
        peso_total += peso
        if skill in del_cv:
            peso_cubierto += peso
            resultado.cubiertas.append(skill)
        elif skill in aviso.duros:
            resultado.faltantes.append(skill)
        else:
            resultado.blandas_faltantes.append(skill)

    resultado.score = round(100 * peso_cubierto / peso_total) if peso_total else 0
    resultado.cubiertas.sort()
    resultado.faltantes.sort()
    resultado.blandas_faltantes.sort()

    # --- observaciones que no son tecnología pero deciden entrevistas ---
    anios_cv = _anios_del_cv(cv)
    if aviso.anios and anios_cv and aviso.anios > anios_cv:
        resultado.observaciones.append(
            f"El aviso pide {aviso.anios}+ años y tu CV declara {anios_cv}. Preparate para justificarlo."
        )
    elif aviso.anios and not anios_cv:
        resultado.observaciones.append(f"El aviso pide {aviso.anios}+ años y el CV no declara años explícitos.")

    ingles_cv = _nivel_ingles_cv(cv)
    if aviso.ingles == "avanzado" and ingles_cv != "avanzado":
        resultado.observaciones.append(
            "El aviso pide inglés avanzado/fluido y el CV declara B1/B2: es un filtro real, no un detalle."
        )

    if aviso.modalidad == "presencial":
        resultado.observaciones.append("La búsqueda es presencial: confirmá ubicación y días antes de avanzar.")
    elif aviso.modalidad == "híbrido":
        resultado.observaciones.append("La búsqueda es híbrida: aclaró cuántos días y dónde.")

    if aviso.seniority in ("lead",) and "lead" not in cv.crudo.lower():
        resultado.observaciones.append("El aviso apunta a un rol de liderazgo y tu CV no lo menciona como tal.")

    if resultado.faltantes:
        resultado.observaciones.append(
            f"Requisitos declarados como excluyentes que tu CV no respalda: {', '.join(resultado.faltantes)}."
        )

    if len(pedidas) < 4:
        resultado.confiable = False
        resultado.observaciones.append("Pocos requisitos detectados: el porcentaje es orientativo.")

    resultado.veredicto = "alta" if resultado.score >= 75 else "media" if resultado.score >= 50 else "baja"
    return resultado
