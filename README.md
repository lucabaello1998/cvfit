# cvfit

**Arrastrás tu CV (PDF, Word o Markdown) y pegás el aviso. Te dice cuánto de ese aviso podés
respaldar, qué te falta, y te devuelve el CV adaptado — sin inventar una sola línea.**

Corre local: tu CV no sale de tu máquina.

![CV en formato ATS](docs/capturas/cv-ats.png)

## El problema

Adaptar el CV a cada aviso a mano cuesta 40 minutos y se hace mal: se agregan las palabras del
aviso aunque no haya evidencia, y el reclutador lo detecta en la entrevista.

Y al revés: se postula a 30 búsquedas sin saber que en 20 el requisito excluyente ya te dejó afuera.

## Qué hace

```
CV.pdf|.docx|.md  +  aviso.txt  →  cobertura  →  gaps  →  CV adaptado en 3 estilos
```

| Salida | Qué es |
|---|---|
| **Cobertura** | % de requisitos del aviso que tu CV ya menciona, ponderado: los excluyentes pesan 3× |
| **Gaps** | Lo que el aviso pide y el CV no respalda, separado en excluyentes y deseables |
| **Observaciones** | Lo que no es tecnología pero decide: años, inglés, modalidad, seniority |
| **CV adaptado** | Reordenado por relevancia, con resumen reescrito y recorte de bullets |
| **Estilos** | `ats` (una columna, sin tablas), `clasico` (una columna con acento), `compacto` (dos columnas) |

### La regla que lo hace distinto

Adaptar es **reordenar y resaltar**, no maquillar. Todo texto generado se valida contra el CV
original: si el resumen propuesto menciona una tecnología que el CV no declara, el resumen se
descarta y queda el original. El campo `sin_respaldo` lista lo que el aviso pide y el CV no puede
sostener, para que decidas vos si es un gap real o algo que omitiste.

No hay LLM en el camino crítico: son reglas explícitas y auditables. Cada punto se puede discutir.

## Uso

### Con interfaz

```bash
python -m cvfit.servidor        # http://localhost:8765
```

Arrastrás el CV a la zona de archivo (**Markdown, TXT, Word `.docx` o PDF**) o lo pegás como texto a
la izquierda, el aviso a la derecha, y ves el puntaje, los gaps y la previsualización del CV adaptado
(con selector de estilo e impresión a PDF).

La extracción de `.docx` y `.pdf` la hace el propio programa con la biblioteca estándar: `zipfile` +
XML para Word, y descompresión de streams + mapa `ToUnicode` para PDF. No hay dependencias ni
servicio externo, así que el CV tampoco sale de la máquina al subirlo.

### Por consola

```bash
python -m cvfit.analizar --cv ejemplos/cv.md --aviso ejemplos/aviso.txt --estilo ats --salida cv.html
python -m cvfit.analizar --cv ~/Downloads/CV.pdf --aviso aviso.txt --estilo ats --salida cv.html
```

```
94% — Encaje alto: podés respaldar casi todo lo que pide el aviso.

respaldados (12/13): .NET, Azure, C#, CI/CD, IA generativa, Inglés, Next.js, Playwright, ...
deseables que faltan:   Docker

distinto en el CV:
  · resumen reescrito con React, .NET, TypeScript, C#
  · RESULTADOS DESTACADOS: 7 → 4 bullets
  · Desarrollador Fullstack — Grupo CETA: 13 → 4 bullets
```

## El CV de entrada

Un archivo `.md`, `.txt`, `.docx` o `.pdf` — el formato que ya tengas. En Markdown:

```markdown
# Nombre Apellido
**Título | Stack**

Ciudad | email | teléfono

## EXPERIENCIA

### Puesto — Empresa | 2024 – 2026
- Logro con número
- Otro logro

## STACK

| Área | Tecnologías |
|---|---|
| Backend | C#/.NET, PostgreSQL |
```

H2 = sección, H3 = puesto, `-` = bullet, tablas de dos columnas = stack o proyectos. Las líneas en
negrita dentro de un puesto abren un subtítulo, así los bullets quedan debajo y no sueltos.

## Qué NO hace

- **No dice si entrás.** Ninguna herramienta puede. Dice cuánto del aviso podés respaldar y qué te
  falta; la decisión es de quien te entrevista.
- No inventa experiencia, ni títulos, ni años, ni idiomas.
- No postula. Para eso está [job-radar](https://github.com/lucabaello1998/job-radar), que encuentra
  y escribe el mensaje; la postulación la apretás vos.
- No traduce el CV. Si el aviso está en inglés, el CV tiene que estar en inglés antes de entrar.

## Límites de la extracción de PDF

El PDF es el formato más hostil que existe. Acá se lee con la biblioteca estándar y sin OCR:

| Caso | Qué pasa |
|---|---|
| PDF exportado desde Word / Google Docs / LaTeX | Funciona: se leen los `ToUnicode` de cada fuente |
| PDF con fuentes sin mapa de caracteres | **Se rechaza con un mensaje claro** en vez de devolver texto basura |
| PDF escaneado (una foto) | Se rechaza: no hay texto, haría falta OCR |
| PDF a dos columnas | El texto sale, pero las columnas se intercalan por renglón: revisalo en el textarea |
| PDF con contraseña | Se rechaza |

Un PDF no escribe líneas, escribe bloques sueltos: un cambio de negrita, un bullet o una palabra en
otro color es un bloque nuevo con su propia posición. Por eso el texto se reconstruye **por
coordenadas**: todo lo que comparte altura se une de izquierda a derecha, y los renglones cortados
por el ancho de la página se vuelven a pegar. Sin eso sale una palabra por renglón.

La regla es la misma que en el resto del proyecto: si no se puede leer, se dice. Nunca se adivina.
Un `.docx` exportado desde Word es la opción más confiable para un CV con diseño.

## Tests

```bash
python -m pytest -q      # 45 tests
```

Cubren el parser, la detección de requisitos (incluidos los falsos positivos típicos: "reactiva" no
es React, "go" no es Go), el encaje, la regla anti-invención, que la plantilla ATS no emita tablas
ni grillas, y la extracción de archivos con un `.docx` y PDFs armados a mano en el propio test —
incluido el caso de un PDF que escribe cada palabra en un bloque aparte.

## Licencia

MIT.
