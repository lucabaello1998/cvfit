from cvfit.adaptar import adaptar
from cvfit.cv import parsear
from cvfit.plantillas import render

CV = """# Ana Pérez
**Fullstack | React · .NET**

Córdoba | ana@example.com

## PERFIL

Desarrolladora con 4 años de experiencia en sistemas productivos.

## RESULTADOS DESTACADOS

- Redujo el bundle un 57% con code-splitting
- Atendió tickets de soporte en guardia
- Diseñó el esquema JWT con refresh tokens

## EXPERIENCIA

### Empresa Uno | 2022 – 2024

Responsabilidad end-to-end.

- APIs en .NET 8 con SQL Server
- Front en React y Next.js con TypeScript
- Configuró monitoreo de procesos
- Instaló routers y switches
"""

AVISO = "Excluyente: React, Next.js, TypeScript y .NET. Remoto."


def test_resumen_usa_solo_tecnologias_del_cv():
    adaptado = adaptar(parsear(CV), AVISO)
    assert "React" in adaptado.resumen or "Next.js" in adaptado.resumen
    for inventada in ("Kubernetes", "AWS", "GraphQL"):
        assert inventada not in adaptado.resumen


def test_no_inventa_tecnologias_que_el_cv_no_tiene():
    adaptado = adaptar(parsear(CV), "Excluyente: Rust, Kubernetes y Go.")
    assert "Rust" in adaptado.sin_respaldo
    assert "Kubernetes" in adaptado.sin_respaldo


def test_reordena_bullets_por_relevancia():
    adaptado = adaptar(parsear(CV), AVISO)
    resultados = next(s for s in adaptado.secciones if "RESULTADOS" in s.nombre.upper())
    assert "bundle" in resultados.bullets[0]


def test_recorta_bullets_irrelevantes():
    adaptado = adaptar(parsear(CV), AVISO, max_bullets=2)
    experiencia = next(s for s in adaptado.secciones if "EXPERIENCIA" in s.nombre.upper())
    assert len(experiencia.bloques[0].bullets) <= 2


def test_plantilla_ats_sin_tablas_ni_grid():
    adaptado = adaptar(parsear(CV), AVISO)
    html = render(adaptado, "ats")
    assert "<table" not in html
    assert "grid-template-columns" not in html
    assert "Ana Pérez" in html


def test_plantilla_compacto_usa_dos_columnas():
    adaptado = adaptar(parsear(CV), AVISO)
    assert "column-count:2" in render(adaptado, "compacto")


def test_estilo_desconocido_cae_en_ats():
    adaptado = adaptar(parsear(CV), AVISO)
    assert render(adaptado, "inventado") == render(adaptado, "ats")


def test_no_muestra_secciones_vacias():
    cv = parsear("# Ana Pérez\n\n## EXPERIENCIA\n\n- algo con React\n\n## IDIOMAS\n")
    adaptado = adaptar(cv, "React")
    assert all(s.nombre != "IDIOMAS" for s in adaptado.secciones)


def test_escapa_html_del_cv():
    cv = parsear("# Nombre <script>alert(1)</script>\n\n## EXPERIENCIA\n\n- algo")
    html = render(adaptar(cv, "React"), "ats")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
