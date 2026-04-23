# Joi-App

> *"She's not your wife. She's not real. I know."* — Joi, Blade Runner 2049

Plataforma de generación dinámica de UI con IA. El sistema interpreta datos y contratos para renderizar **widgets** en tiempo real mediante un sistema multi-agente, manteniendo independencia de proveedores tecnológicos.

![Coverage](docs/coverage-badge.svg)
[![CI](https://github.com/sebastianms/joi-app/actions/workflows/ci.yml/badge.svg)](https://github.com/sebastianms/joi-app/actions/workflows/ci.yml)

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | Next.js + Tailwind CSS + shadcn/ui |
| Backend | Python + FastAPI + LiteLLM (LLM agnóstico) |
| DB Secundaria | SQLite (vía SQLAlchemy async) |
| Cache Vectorial | Diferido post-MVP (ver ADL-010) |
| Tests | pytest + pytest-asyncio + Playwright (e2e) |

## Estructura

```
joi-app/
├── backend/          # FastAPI + Python (Agentes, API, DB)
├── frontend/         # Next.js + Tailwind + shadcn/ui
├── specs/            # Documentación SDD (mission, roadmap, tech-stack, features)
└── docs/             # Artefactos generados (badges, etc.)
```

## Docker (Recomendado)

Levanta toda la plataforma con un solo comando (construye y orquesta backend y frontend):

```bash
docker-compose up --build
```
- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend API: [http://localhost:8000/api](http://localhost:8000/api)
- Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Capacidades del sistema

### Conexión a datos

El Setup Wizard conecta la app a cualquier fuente de datos en segundos. Soporta **PostgreSQL, MySQL, SQLite y JSON**. La conexión queda guardada en sesión — no hace falta reconectar en cada visita.

### Chat con inteligencia contextual

El motor de triage interpreta el mensaje del usuario y decide en tiempo real si puede responderlo de forma directa o si requiere consultar la base de datos. Las consultas simples (saludos, ayuda, preferencias de visualización) se resuelven sin tocar la DB — sin latencia, sin costos LLM innecesarios.

### Pipeline multi-agente Text-to-SQL

Para consultas de datos, tres agentes trabajan en secuencia:

```
Usuario: "muéstrame las ventas por región"
      ↓
Data Agent: genera SQL → guard read-only → ejecuta → DataExtraction
      ↓
Agente Arquitecto: selector determinístico → tipo de widget óptimo
      ↓
Agente Generador (LLM): WidgetSpec con bindings validados
      ↓
Canvas: iframe sandboxed + Recharts → widget visible
```

El guard SQL garantiza que solo se ejecuten sentencias `SELECT` — ninguna operación de escritura puede llegar a la base de datos del usuario.

### Visualizaciones automáticas

El sistema elige el tipo de widget más adecuado según la forma de los datos, sin intervención del usuario:

`table` · `bar_chart` · `line_chart` · `area_chart` · `pie_chart` · `kpi` · `scatter_plot` · `heatmap`

**Preferencia explícita**: el usuario puede pedir un tipo distinto ("prefiero verlo como tabla") y el sistema reutiliza la extracción anterior sin re-ejecutar la consulta SQL.

**Fallback universal**: cualquier fallo del generador (timeout, spec inválida, crash del renderer) produce automáticamente una tabla con los datos crudos. La sesión nunca se interrumpe.

### Aislamiento de seguridad

Cada widget corre en un `<iframe sandbox="allow-scripts">` con CSP que bloquea `connect-src`. El código del widget no puede acceder al DOM del host, leer cookies ni hacer peticiones de red.

Para construir el bundle del runtime antes de levantar el frontend:

```bash
cd frontend
npm run build:widget-runtime
```

## Dev Setup (Local)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Tests (backend)
cd backend
pytest
```
