from cvfit.cv import parsear
from cvfit.match import evaluar

CV_FUERTE = """# Ana Pérez
**Fullstack | React · .NET**

Córdoba | ana@example.com

## PERFIL

Desarrolladora con 4 años en sistemas productivos.

## EXPERIENCIA

### Empresa Uno | 2022 – 2024
- APIs en .NET 8 con SQL Server
- Front en React y Next.js con TypeScript
- Pipelines CI/CD en Azure

## IDIOMAS

- Inglés: C1 avanzado
"""

CV_DEBIL = """# Juan Pérez
**Soporte técnico**

## EXPERIENCIA

### Empresa | 2020 – 2024
- Atención de tickets
- Instalación de routers
"""

AVISO = """Fullstack Engineer
Requisitos excluyentes:
- React y TypeScript excluyente
- .NET excluyente
Deseables: Next.js, Azure
Remoto
"""


def test_encaje_alto_cuando_respalda_los_excluyentes():
    resultado = evaluar(parsear(CV_FUERTE), AVISO)
    assert resultado.score >= 75
    assert resultado.veredicto == "alta"
    assert resultado.faltantes == []


def test_encaje_bajo_cuando_no_hay_nada():
    resultado = evaluar(parsear(CV_DEBIL), AVISO)
    assert resultado.score < 50
    assert "React" in resultado.faltantes
    assert ".NET" in resultado.faltantes


def test_gaps_separan_excluyentes_de_deseables():
    resultado = evaluar(parsear(CV_FUERTE), "Excluyente: Kubernetes. Deseable: Redis.")
    assert "Kubernetes" in resultado.faltantes
    assert "Redis" in resultado.blandas_faltantes


def test_aviso_sin_tecnologias_es_no_confiable():
    resultado = evaluar(parsear(CV_FUERTE), "Buscamos alguien con muchas ganas.")
    assert resultado.confiable is False
    assert resultado.observaciones


def test_detecta_ingles_insuficiente():
    cv_b1 = CV_FUERTE.replace("C1 avanzado", "B1")
    resultado = evaluar(parsear(cv_b1), AVISO + "\nInglés avanzado")
    assert any("inglés" in o.lower() for o in resultado.observaciones)


def test_cuenta_requisitos_totales():
    resultado = evaluar(parsear(CV_FUERTE), AVISO)
    assert resultado.total_requisitos >= 4
