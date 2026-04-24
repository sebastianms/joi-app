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
| Cache Vectorial | Qdrant (Docker) |
| Tests | pytest + pytest-asyncio + Playwright (e2e) |

## Estructura

```
joi-app/
├── backend/          # FastAPI + Python (Agentes, API, DB)
├── frontend/         # Next.js + Tailwind + shadcn/ui
├── specs/            # Documentación SDD (mission, roadmap, tech-stack, features)
└── docs/             # Artefactos generados (badges, etc.)
```

## Levantar el proyecto

### Desarrollo local (recomendado)

**Requisitos previos**: Python 3.11+, Node.js 18+, Docker (solo para Qdrant).

**Primera vez — backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar API keys
```

**Primera vez — frontend:**

```bash
cd frontend
npm install
npm run build:widget-runtime
```

**Arranque diario:**

```bash
# 1. Qdrant (vector store) — solo necesita Docker, corre en background
docker compose up qdrant -d

# 2. Backend + Frontend en un solo comando
./dev.sh
```

| Servicio     | URL                                                  |
|---|---|
| Frontend     | [http://localhost:3000](http://localhost:3000)        |
| Backend API  | [http://localhost:8000/api](http://localhost:8000/api)|
| Swagger Docs | [http://localhost:8000/docs](http://localhost:8000/docs)|
| Qdrant UI    | [http://localhost:6333/dashboard](http://localhost:6333/dashboard)|

`./dev.sh` levanta backend (uvicorn) y frontend (next dev) juntos, esperando a que el backend responda antes de arrancar el frontend. No hace falta coordinarlos manualmente.

### Docker completo

Construye y orquesta todos los servicios (producción / CI):

```bash
docker compose up --build
```

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

### Cache semántico de widgets (RAG)

Cuando el usuario repite una consulta similar a una ya generada, el sistema sugiere reutilizar el widget anterior en lugar de regenerar código. El flujo:

1. Antes de llamar al LLM, el pipeline consulta el vector store con el prompt.
2. Si hay hit con score ≥ 0.85 → devuelve `cache_suggestion` al chat (botones "Usar este widget" / "Generar uno nuevo").
3. Si no hay hit o el usuario opta por regenerar (`skip_cache=true`) → pipeline normal.
4. Tras generar con éxito → se indexa el nuevo widget.

Los filtros `session_id`, `connection_id` y `data_schema_hash` son obligatorios en toda búsqueda: un widget de otra sesión o con un schema distinto nunca se sugiere. Al eliminar una conexión, todas las entradas asociadas se soft-deletean automáticamente.

#### Vector store: Qdrant por defecto y BYO opcional

Por defecto, la app usa **Qdrant** en Docker Compose — no hace falta configurar nada. Si prefieres tu propio proveedor, ve a `/setup → Vector Store` y elige uno:

| Provider | Extra a instalar | Docs |
|---|---|---|
| Qdrant (BYO remoto) | — (ya instalado) | [qdrant.tech](https://qdrant.tech/) |
| Chroma | `pip install langchain-chroma` | [trychroma.com](https://www.trychroma.com/) |
| Pinecone | `pip install langchain-pinecone` | [pinecone.io](https://www.pinecone.io/) |
| Weaviate | `pip install langchain-weaviate` | [weaviate.io](https://weaviate.io/) |
| PGVector | `pip install langchain-postgres` | [pgvector](https://github.com/pgvector/pgvector) |

Las credenciales se cifran con Fernet (clave en `VECTOR_STORE_ENCRYPTION_KEY`) antes de persistir. El botón "Validar conexión" hace un ping real al provider antes de guardar. Si Qdrant u otro provider no está disponible, el caché se degrada a miss sin interrumpir al usuario (FR-013).

### Aislamiento de seguridad

Cada widget corre en un `<iframe sandbox="allow-scripts">` con CSP que bloquea `connect-src`. El código del widget no puede acceder al DOM del host, leer cookies ni hacer peticiones de red.

Para construir el bundle del runtime antes de levantar el frontend:

```bash
cd frontend
npm run build:widget-runtime
```

## Tests

```bash
# Backend (corre en menos de 5 s, sin servicios externos)
cd backend && .venv/bin/pytest

# Con reporte de cobertura
cd backend && .venv/bin/pytest --cov=app --cov-report=term-missing
```
