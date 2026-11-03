"""Extracción de requisitos desde el texto de una oferta.

Sin LLM: diccionario de tecnologías con alias, más reglas para años, idioma, modalidad y
seniority. Es explícito y auditable, que es justo lo que se necesita para discutir un puntaje.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# canónico -> alias (todos en minúsculas, sin acentos)
TECNOLOGIAS: dict[str, list[str]] = {
    "React": ["react", "react.js", "reactjs"],
    "Next.js": ["next.js", "nextjs", "next js"],
    "TypeScript": ["typescript"],
    "JavaScript": ["javascript"],
    "Angular": ["angular"],
    "Vue": ["vue", "vue.js", "vuejs"],
    ".NET": [".net", "dotnet", ".net core", "asp.net", "asp net core"],
    "C#": ["c#", "csharp", "c sharp"],
    "Node.js": ["node.js", "nodejs", "node js"],
    "Java": ["java"],
    "Spring": ["spring boot", "spring"],
    "Python": ["python"],
    "PHP": ["php"],
    "Laravel": ["laravel"],
    "Ruby": ["ruby", "rails"],
    "Go": ["golang"],
    "Rust": ["rust"],
    "SQL Server": ["sql server", "mssql"],
    "PostgreSQL": ["postgresql", "postgres", "postgis"],
    "MySQL": ["mysql", "mariadb"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "GraphQL": ["graphql"],
    "REST": ["rest api", "restful"],
    "Docker": ["docker", "contenedores", "containers"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Azure": ["azure"],
    "AWS": ["aws", "amazon web services"],
    "GCP": ["gcp", "google cloud"],
    "CI/CD": ["ci/cd", "cicd", "pipeline", "pipelines"],
    "Terraform": ["terraform"],
    "Git": ["git", "github", "gitlab"],
    "Playwright": ["playwright"],
    "Cypress": ["cypress"],
    "Jest": ["jest"],
    "Vitest": ["vitest"],
    "xUnit": ["xunit", "nunit", "mstest"],
    "Flutter": ["flutter", "dart"],
    "React Native": ["react native"],
    "Android": ["android"],
    "iOS": ["ios", "swift"],
    "Tailwind": ["tailwind"],
    "SASS": ["sass", "scss"],
    "Microservicios": ["microservicios", "microservices"],
    "Kafka": ["kafka"],
    "RabbitMQ": ["rabbitmq"],
    "SignalR": ["signalr", "websockets", "websocket"],
    "Scrum": ["scrum", "kanban", "ágile", "agile"],
    "IA generativa": ["ia generativa", "generative ai", "llm", "prompt engineering", "copilot", "claude"],
    "Power BI": ["power bi"],
    "Excel": ["excel"],
    "Inglés": ["inglés", "english"],
}

CATEGORIAS: dict[str, list[str]] = {
    "Frontend": ["React", "Next.js", "TypeScript", "JavaScript", "Angular", "Vue", "Tailwind", "SASS"],
    "Backend": [".NET", "C#", "Node.js", "Java", "Spring", "Python", "PHP", "Laravel", "Ruby", "Go", "Rust"],
    "Datos": ["SQL Server", "PostgreSQL", "MySQL", "MongoDB", "Redis", "GraphQL"],
    "Cloud y DevOps": ["Docker", "Kubernetes", "Azure", "AWS", "GCP", "CI/CD", "Terraform", "Git"],
    "Testing": ["Playwright", "Cypress", "Jest", "Vitest", "xUnit"],
    "Mobile": ["Flutter", "React Native", "Android", "iOS"],
    "Arquitectura": ["Microservicios", "REST", "Kafka", "RabbitMQ", "SignalR"],
    "Blandas": ["Scrum", "IA generativa", "Power BI", "Excel", "Inglés"],
}

DUROS = re.compile(
    r"(excluyente|indispensable|imprescindible|must[- ]have|requerid[oa]|required|obligatori[oa]|"
    r"es necesario|se requiere|is required)",
    re.IGNORECASE,
)
ANIOS = re.compile(r"(\d{1,2})\s*\+?\s*(?:años|years)", re.IGNORECASE)
SENIORITY = [
    ("junior", r"\bjunior\b|\bjunior/trainee\b|\bentry[- ]level\b"),
    ("semi-senior", r"\bsemi[- ]?senior\b|\bssr\b|\bsenior\b(?!.*\b(?:staff|principal)\b)"),
    ("senior", r"\bsenior\b|\bsr\.?\b"),
    ("lead", r"\blead\b|\btech lead\b|\bprincipal\b|\bstaff\b|\bhead of\b"),
]
MODALIDAD = [
    ("remoto", r"\b100% remoto\b|\bremoto\b|\bremote\b|\bteletrabajo\b|\banywhere\b|\bhome office\b"),
    ("híbrido", r"\bhíbrido\b|\bhybrid\b"),
    ("presencial", r"\bpresencial\b|\bon[- ]?site\b|\boffice based\b"),
]
INGLES = [
    ("avanzado", r"inglés avanzado|advanced english|fluent english|inglés fluido|c1|b2\+"),
    ("intermedio", r"inglés intermedio|intermediate english|b1|b2"),
]


@dataclass
class Aviso:
    texto: str
    skills: dict[str, int] = field(default_factory=dict)  # canónico -> peso
    duros: set[str] = field(default_factory=set)
    anios: int | None = None
    seniority: str = ""
    modalidad: str = ""
    ingles: str = ""
    pais: str = ""

    @property
    def todos(self) -> list[str]:
        return sorted(self.skills, key=lambda s: -self.skills[s])


def _buscar_alias(texto: str, alias: str) -> bool:
    # \b no funciona con ".net" ni "c#": se arma un borde manual
    patron = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
    return re.search(patron, texto) is not None


def analizar(texto: str) -> Aviso:
    plano = re.sub(r"\s+", " ", texto.lower())
    aviso = Aviso(texto=texto)

    for canonico, alias in TECNOLOGIAS.items():
        for variante in alias:
            if _buscar_alias(plano, variante):
                aviso.skills[canonico] = aviso.skills.get(canonico, 0) + 1
                break

    # requisito duro: la tecnología aparece en un fragmento con marcador de exigencia.
    # Se parte por línea, punto y coma, o punto seguido de espacio (para no romper ".NET" ni "Next.js").
    for fragmento in re.split(r"\n|;|\.\s", texto):
        if not DUROS.search(fragmento):
            continue
        bajo = fragmento.lower()
        for canonico, alias in TECNOLOGIAS.items():
            if any(_buscar_alias(bajo, v) for v in alias):
                aviso.duros.add(canonico)

    if coincidencias := ANIOS.findall(plano):
        aviso.anios = max(int(c) for c in coincidencias)

    for etiqueta, patron in SENIORITY:
        if re.search(patron, plano):
            aviso.seniority = etiqueta

    for etiqueta, patron in MODALIDAD:
        if re.search(patron, plano):
            aviso.modalidad = etiqueta
            break

    for etiqueta, patron in INGLES:
        if re.search(patron, plano):
            aviso.ingles = etiqueta

    for pais, patron in [("Argentina", r"argentina|buenos aires|caba"), ("Uruguay", r"uruguay"), ("Chile", r"chile")]:
        if re.search(patron, plano):
            aviso.pais = pais
            break

    return aviso
