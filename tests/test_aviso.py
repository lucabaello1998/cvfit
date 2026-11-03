from cvfit.aviso import analizar

AVISO = """Full-Stack Engineer (React + .NET)
Requisitos excluyentes:
- 5+ años de experiencia
- React y TypeScript excluyente
- .NET / C# excluyente
Deseables: Next.js, Azure, Docker
Modalidad: 100% remoto
Inglés avanzado
"""


def test_detecta_tecnologias():
    aviso = analizar(AVISO)
    assert "React" in aviso.skills
    assert "TypeScript" in aviso.skills
    assert ".NET" in aviso.skills
    assert "C#" in aviso.skills
    assert "Next.js" in aviso.skills


def test_marca_excluyentes():
    aviso = analizar(AVISO)
    assert "React" in aviso.duros
    assert ".NET" in aviso.duros
    assert "Docker" not in aviso.duros


def test_extrae_anios_modalidad_e_idioma():
    aviso = analizar(AVISO)
    assert aviso.anios == 5
    assert aviso.modalidad == "remoto"
    assert aviso.ingles == "avanzado"


def test_aviso_vacio_no_inventa():
    aviso = analizar("Hola, buscamos gente con ganas.")
    assert aviso.skills == {}
    assert aviso.anios is None


def test_no_confunde_palabras_con_tecnologias():
    aviso = analizar("Trabajamos con gente reactiva y con mucho go")
    assert aviso.skills == {}
