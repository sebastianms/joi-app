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

## Feature 004 — Widget Generation & Canvas

El sistema convierte automáticamente cualquier consulta en una visualización interactiva:

```
Usuario: "muéstrame las ventas por región"
      ↓
Data Agent ejecuta SQL → DataExtraction (columnas + filas)
      ↓
Agente Arquitecto: selector determinístico → bar_chart
      ↓
Agente Generador (LLM): WidgetSpec con bindings validados
      ↓
Canvas: iframe sandboxed con CSP + Recharts → widget visible
```

**Tipos soportados**: `table` · `bar_chart` · `line_chart` · `area_chart` · `pie_chart` · `kpi` · `scatter_plot` · `heatmap`

**Fallback universal**: cualquier fallo del generador (timeout, spec inválida, crash del renderer) produce automáticamente una tabla con los datos crudos. La sesión nunca se interrumpe.

**Preferencia explícita**: el usuario puede pedir un tipo distinto en el chat ("prefiero verlo como tabla") — el sistema reutiliza la extracción anterior sin re-ejecutar la consulta.

**Aislamiento**: cada widget corre en un `<iframe sandbox="allow-scripts">` con CSP que bloquea `connect-src` — el código del widget no puede acceder al DOM del host ni hacer peticiones de red.

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
