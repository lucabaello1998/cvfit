"""Tests de la revisión: que marque lo que un reclutador marcaría, sin inventar nada."""

from __future__ import annotations

from cvfit.cv import parsear
from cvfit.revisar import CONSEJOS, GUIA_ESTILOS, revisar

BASE = """# Ana Prueba
**Desarrolladora Fullstack | React · .NET**

Buenos Aires | ana@ejemplo.com | +54 11 5555-5555 | linkedin.com/in/ana

## PERFIL

Desarrolladora fullstack con 5 años en producto.

## EXPERIENCIA

### Desarrolladora — Empresa | Mar 2021 – Actual
- Migré 3 servicios a contenedores y bajé el deploy de 40 a 8 minutos
- Priorizé 60 tickets y reduje 22% los incidentes en producción
- Automaticé las pruebas de integración: 8 horas menos por release

### Junior — Otra | Ene 2019 – Feb 2021
- Implementé 12 pantallas del portal de clientes
- Documenté la API y bajé 30% las consultas al equipo

## EDUCACIÓN

### Licenciatura en Informática — UNAHUR | 2018 – 2023

## STACK

| Área | Tecnologías |
|---|---|
| Backend | C#/.NET, PostgreSQL |
"""


def hallazgos(texto: str, estilo: str = "ats"):
    return revisar(parsear(texto), estilo)


def mensajes(texto: str) -> str:
    return " | ".join(h.mensaje for h in hallazgos(texto).hallazgos)


def test_cv_completo_no_tiene_altos_ni_medios():
    revision = hallazgos(BASE)
    assert revision.altos == 0
    assert revision.medios == 0
    assert revision.estado == "ok"


def test_falta_mail_y_telefono_son_altos():
    texto = BASE.replace("ana@ejemplo.com", "mail").replace("+54 11 5555-5555", "tel")
    revision = hallazgos(texto)
    assert revision.altos == 2
    assert revision.estado == "mal"
    assert "mail" in " ".join(h.mensaje for h in revision.hallazgos)
    assert any("teléfono" in h.mensaje for h in revision.hallazgos)


def test_sin_experiencia_es_alto():
    texto = "# Ana\n\n**Dev**\n\nana@ejemplo.com | +54 11 5555-5555\n\n## EDUCACIÓN\n\n### Lic. — UNAHUR | 2020 – 2024\n"
    assert any("experiencia" in h.mensaje.lower() for h in hallazgos(texto).hallazgos if h.nivel == "alto")


def test_sin_educacion_ni_stack_son_medios():
    texto = BASE.split("## EDUCACIÓN")[0]
    mensajes_ = mensajes(texto)
    assert "educación" in mensajes_.lower()
    assert "stack" in mensajes_.lower()


def test_objetivo_y_referencias_se_marcan():
    texto = BASE.replace("## PERFIL", "## OBJETIVO") + "\n## REFERENCIAS\n\nA disposición.\n"
    mensajes_ = mensajes(texto).lower()
    assert "objetivo" in mensajes_
    assert "referencias" in mensajes_


def test_bullets_sin_numeros_cuentan():
    texto = BASE.replace("Migré 3 servicios", "Migré servicios").replace(
        "Priorizé 60 tickets y reduje 22% los incidentes en producción", "Priorizé tickets"
    ).replace(
        "Automaticé las pruebas de integración: 8 horas menos por release",
        "Automaticé las pruebas de integración",
    ).replace(
        "Documenté la API y bajé 30% las consultas al equipo", "Documenté la API"
    )
    revision = hallazgos(texto)
    assert any("no tienen números" in h.mensaje for h in revision.hallazgos)
    assert revision.medios >= 1


def test_primera_persona_y_relleno():
    texto = BASE.replace(
        "- Documenté la API y bajé 30% las consultas al equipo",
        "- Yo documenté la API. Soy proactiva, dinámica y apasionada.",
    )
    mensajes_ = mensajes(texto).lower()
    assert "primera persona" in mensajes_
    assert "adjetivos sin evidencia" in mensajes_


def test_edad_y_dni_se_marcan_bajo():
    texto = BASE.replace("Buenos Aires |", "Buenos Aires | 29 años | DNI 30111222 |")
    revision = hallazgos(texto)
    assert any(h.area == "contacto" and h.nivel == "bajo" for h in revision.hallazgos)


def test_hueco_de_mas_de_un_anio():
    texto = BASE.replace("Ene 2019 – Feb 2021", "Ene 2017 – Feb 2018")
    assert any("hueco" in h.mensaje.lower() for h in hallazgos(texto).hallazgos)


def test_fechas_solapadas():
    texto = BASE.replace("Ene 2019 – Feb 2021", "Ene 2020 – Dic 2022")
    assert any("solapadas" in h.mensaje.lower() for h in hallazgos(texto).hallazgos)


def test_puesto_sin_fechas():
    texto = BASE.replace("### Junior — Otra | Ene 2019 – Feb 2021", "### Junior — Otra")
    assert any("no tiene fechas" in h.mensaje for h in hallazgos(texto).hallazgos)


def test_orden_cronologico_invertido():
    texto = BASE.replace(
        "### Junior — Otra | Ene 2019 – Feb 2021", "### Junior — Otra | Mar 2022 – Dic 2023"
    )
    assert any("más reciente" in h.mensaje for h in hallazgos(texto).hallazgos)


def test_reescritura_de_responsable_de():
    texto = BASE.replace(
        "- Migré 3 servicios a contenedores y bajé el deploy de 40 a 8 minutos",
        "- Responsable de 3 servicios en producción",
    )
    reescritura = hallazgos(texto).reescrituras[0]
    assert reescritura.propuesta.startswith("Gestioné 3 servicios")
    assert "responsable" not in reescritura.propuesta.lower()


def test_reescritura_conserva_el_articulo_del():
    texto = BASE.replace(
        "- Migré 3 servicios a contenedores y bajé el deploy de 40 a 8 minutos",
        "- Responsable del equipo de frontend",
    )
    assert hallazgos(texto).reescrituras[0].propuesta == "Lideré el equipo de frontend"


def test_reescritura_de_participacion_no_repite_el_sustantivo():
    texto = BASE.replace(
        "- Migré 3 servicios a contenedores y bajé el deploy de 40 a 8 minutos",
        "- Participé en la migración a la nube",
    )
    assert hallazgos(texto).reescrituras[0].propuesta == "Ejecuté la migración a la nube"


def test_reescritura_de_equipo_y_de_personas():
    texto = BASE.replace(
        "- Migré 3 servicios a contenedores y bajé el deploy de 40 a 8 minutos",
        "- Colaboré en el equipo de frontend",
    ).replace(
        "- Implementé 12 pantallas del portal de clientes", "- Ayudé a los nuevos ingresos"
    )
    propuestas = [r.propuesta for r in hallazgos(texto).reescrituras]
    assert propuestas[0] == "Formé parte del equipo de frontend"
    assert propuestas[1] == "Acompañé a los nuevos ingresos"


def test_una_buena_bullet_no_se_reescribe():
    assert hallazgos(BASE).reescrituras == []


def test_lo_que_esta_bien():
    bien = hallazgos(BASE).bien
    assert any("contacto" in texto.lower() for texto in bien)
    assert any("números" in texto for texto in bien)
    assert any("fechas" in texto for texto in bien)


def test_guia_y_consejos_para_la_interfaz():
    assert len(GUIA_ESTILOS) == 3
    assert {g["nombre"] for g in GUIA_ESTILOS} == {"ATS", "Clásico", "Compacto"}
    assert all(g["cuando"] and g["detalle"] for g in GUIA_ESTILOS)
    assert len(CONSEJOS) >= 4
    assert all(c["titulo"] and c["cuerpo"] for c in CONSEJOS)
