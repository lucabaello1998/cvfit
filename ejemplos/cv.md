# Luca Nicolas Baello
**Desarrollador Fullstack SSR | React · Next.js · C#/.NET · Azure DevOps · IA**

Buenos Aires, Argentina | luca.baello@gmail.com | +54 11 5339-3386 | linkedin.com/in/luca-baello

---

## PERFIL

Desarrollador fullstack semi-senior (SSR) con 3-5 años de experiencia en sistemas productivos end-to-end. Especializado en React/Next.js + C#/.NET con Clean Architecture. Foco en performance, seguridad, DevOps y uso cotidiano de IA generativa (Claude, Copilot, MCP). Responsable de features completas desde el esquema de base de datos hasta el despliegue en producción.

---

## RESULTADOS DESTACADOS

- **668 work items** cerrados — 1º de la organización (11 proyectos, ~32/mes)
- **Seguridad**: Diseñó el primer esquema JWT de la organización con rotación y revocación de refresh tokens — primera implementación del patrón en la organización
- **Vulnerability fix**: Detectó y reportó una timing attack en el login; el equipo la corrigió (diferencia explotable de **46ms a 0.77ms**), cubierta con tests automatizados
- **Performance Frontend**: Implementó el code-splitting manual de vendors del front de fichaje (CETA_CONTROL_FRONT): el chunk de entrada bajó de **598 kB a 255 kB (-57%)**, con cacheo de vendors entre deploys
- **Delivery**: Responsable de releases del ERP de Payroll — gestionó 86 de los 114 merges de entorno, con 705 commits propios en 18 meses
- **Mobile offline-first**: Construyó app de fichaje PWA con geolocalización, captura de cámara, persistencia local y sincronización diferida
- **DevOps**: Configuró y mantuvo pipelines CI/CD en Azure DevOps (YAML, artifacts, self-hosted agents) hacia testing, preproducción y producción on-premise con IIS

---

## STACK

| Área | Tecnologías |
|---|---|
| **Frontend** | React 19, Next.js 15, TypeScript, Zustand, Tailwind CSS, PrimeReact, Material UI, PWA/offline-first |
| **Backend** | C#/.NET 8, Node.js, Express, REST APIs, Webhooks, WebSockets (SignalR), Clean Architecture, CQRS (MediatR) |
| **Datos** | SQL Server, MySQL, PostgreSQL/PostGIS, Firebase/Supabase, EF Core, Dapper |
| **Mobile** | Flutter, Capacitor (Android) |
| **DevOps** | Azure DevOps, CI/CD YAML pipelines, IIS, self-hosted agents, on-premise |
| **IA aplicada** | GitHub Copilot, Claude, OpenCode, MCP, Prompt Engineering, Ollama (local LLMs) |
| **Testing** | Playwright, Vitest, xUnit, Testing Library, MSW |

---

## EXPERIENCIA

### Desarrollador Fullstack — Grupo CETA Capital Humano | Ago 2024 – Sep 2026

Responsabilidad end-to-end sobre features en 6 sistemas productivos para operaciones internas y clientes externos.

**Portal de gestión logística (TMS/WMS)**
- Diseñó el esquema de autenticación JWT con rotación y revocación de refresh tokens — primera implementación de este patrón en la organización
- Detectó y reportó una vulnerabilidad de timing attack en el login; el equipo la corrigió (46ms → 0.77ms de diferencia explotable), cubierta con tests automatizados
- Implementó el picking por recorrido con atomicidad multi-picker, el ABM de artículos/stock y el flujo de colectas
- Desarrolló la app móvil del chofer offline-first (Capacitor) y los tiers de APK chofer/depósito

**App móvil de fichaje PWA offline-first**
- Construyó el flujo de entrada/salida combinando geolocalización, captura de cámara y persistencia local con sincronización diferida
- Diagnóstico y resolución de incidencias productivas de paginación, historial y flujo de aprobación entre colaborador y supervisor
- Implementó el code-splitting manual de vendors del front: el chunk de entrada bajó de 598 kB a 255 kB (-57%), con el resto en chunks que sólo se descargan al usarse

**Sistema de inventario y legajos de RRHH**
- Desarrolló ABMs completos (legajos, proveedores, almacenes, prioridades) incluyendo lógica de transferencia entre depósitos y devoluciones
- Refactorizó toda la arquitectura frontend del módulo hacia una estructura mantenible que el equipo hoy extiende

**Gestión personal y portal regulatorio (2 sistemas)**
- Pantallas de importación de nómina y gestión de sectores, premios y penalidades para cliente externo del sector alimenticio
- Flujo de carga, revisión y aprobación/objeción de expedientes del portal regulatorio, con visualización de PDF integrada

**DevOps e infraestructura (transversal a todos los proyectos)**
- Configuración y mantenimiento de pipelines CI/CD en Azure DevOps (YAML, artifacts, self-hosted agents)
- Despliegue on-premise con IIS, monitoreo de procesos críticos y resolución de incidentes en producción

### Programador Fullstack — Universidad Nacional de Hurlingham | Mar 2023 – Oct 2023

- Desarrollo de sitios y aplicaciones web para organismos gubernamentales y empresas privadas
- Metodologías ágiles (Scrum, Kanban) con React, Node.js, Express, PHP, MySQL y Sequelize
- Gestión de versiones mediante GitHub, branches y forks

### Coordinador de Proyectos Corporativos — Claro | Jun 2022 – Mar 2023

- Gestión de clientes corporativos y coordinación con equipos técnicos
- Desarrollo de CRM personalizado con PHP, SQL y jQuery
- Automatización de procesos administrativos con Python

### Soporte Técnico N1/N2/N3 — Telecentro | Oct 2023 – Ago 2024

- Diagnóstico y resolución de incidencias de conectividad, routers, redes mesh, IPs, FTTH, IPTV y redes coaxiales

---

## EDUCACIÓN

**Licenciatura en Informática** — Universidad Nacional de Hurlingham (En curso)

---

## IDIOMAS

- Español: nativo
- Inglés: B1/B2 (lectura técnica y comunicación escrita; fluidez oral en desarrollo)

---

## PROYECTOS DESTACADOS

| Proyecto | Stack | Descripción |
|---|---|---|
| **Ceta-Logistica** | .NET 8 + React 19 + Capacitor | Monorepo TMS/WMS con 50+ módulos, app móvil dual (chofer/depósito) |
| **CETA_PAYROLL** | Next.js + .NET 8 | Sistema payroll/RRHH completo, 110+ tablas, multi-tenant |
| **REM_V3** | .NET 8 + React + Shadcn | Sistema regulatorio farmacéutico, 3 bases de datos |
| **FletAR** | Flutter + .NET 8 + PostGIS | App móvil logística con SignalR, GPS en tiempo real, chat |
| **CETA_CONTROL_FRONT** | React + Capacitor + MUI | PWA fichaje offline-first con geofencing |
| **claude-cockpit** | JavaScript | Dashboard local para Claude Code (costos, conversaciones, MCPs) |
| **ai-progress** | PowerShell/WPF | Widget de progreso para agentes de IA (tareas + uso de Claude/Codex/OpenCode) |
