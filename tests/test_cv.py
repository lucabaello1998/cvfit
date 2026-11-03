from cvfit.cv import parsear

CV = """# Ana Pérez
**Backend Developer | .NET · SQL**

Córdoba, Argentina | ana@example.com

---

## PERFIL

Desarrolladora con 4 años de experiencia.

## EXPERIENCIA

### Empresa Uno | 2022 – 2024
- Construyó APIs en .NET 8
- Migró la base a PostgreSQL

### Empresa Dos | 2020 – 2022
- Mantenimiento de sistema legacy

## STACK

| Área | Tecnologías |
|---|---|
| Backend | C#/.NET, PostgreSQL |
| Frontend | React |

## IDIOMAS

- Inglés: B1
"""


def test_parsea_encabezado_y_contacto():
    cv = parsear(CV)
    assert cv.nombre == "Ana Pérez"
    assert cv.titulo.startswith("Backend Developer")
    assert "ana@example.com" in cv.contacto


def test_parsea_secciones_y_bloques():
    cv = parsear(CV)
    nombres = [s.nombre for s in cv.secciones]
    assert "PERFIL" in nombres
    assert "EXPERIENCIA" in nombres
    experiencia = cv.seccion("experiencia")
    assert experiencia is not None
    assert len(experiencia.bloques) == 2
    assert experiencia.bloques[0].titulo == "Empresa Uno | 2022 – 2024"
    assert len(experiencia.bloques[0].bullets) == 2


def test_parsea_tabla_de_stack():
    cv = parsear(CV)
    stack = cv.seccion("stack")
    assert stack is not None
    assert stack.tabla[0] == ["Backend", "C#/.NET, PostgreSQL"]
    assert stack.tabla[1] == ["Frontend", "React"]


def test_bullets_incluye_bloques_anidados():
    cv = parsear(CV)
    bullets = cv.bullets
    assert "Construyó APIs en .NET 8" in bullets
    assert "Mantenimiento de sistema legacy" in bullets
    assert "Inglés: B1" in bullets
    assert len(bullets) == 4


def test_seccion_inexistente_devuelve_none():
    cv = parsear(CV)
    assert cv.seccion("certificaciones") is None
