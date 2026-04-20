# Joi-App

> *"She's not your wife. She's not real. I know."* — Joi, Blade Runner 2049

Plataforma de generación dinámica de UI con IA. El sistema interpreta datos y contratos para renderizar **widgets** en tiempo real mediante un sistema multi-agente, manteniendo independencia de proveedores tecnológicos.

![Coverage](docs/coverage-badge.svg)
[![CI](https://github.com/sebastianms/joi-app/actions/workflows/ci.yml/badge.svg)](https://github.com/sebastianms/joi-app/actions/workflows/ci.yml)

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | Next.js + Tailwind CSS + shadcn/ui |
| Backend | Python + FastAPI + LangChain |
| DB Secundaria | SQLite (vía SQLAlchemy async) |
| Cache Vectorial | LangChain Vector Store (Chroma local) |
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
