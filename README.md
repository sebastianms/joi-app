# Joi · App

> *"She's not your wife. She's not real. I know."* — Joi, Blade Runner 2049

**Joi** convierte tus datos en visualizaciones interactivas en segundos. Conectas tu base de datos (SQL o JSON), le preguntas en lenguaje natural, y la app genera el widget correcto en tiempo real — tabla, gráfico de barras, KPI, mapa de calor — sin que tengas que escribir una línea de código.

![Coverage](docs/coverage-badge.svg)
[![CI](https://github.com/sebastianms/joi-app/actions/workflows/ci.yml/badge.svg)](https://github.com/sebastianms/joi-app/actions/workflows/ci.yml)

---

## ¿Qué hace?

### Hablas, ella visualiza

Escribe un mensaje como *"muéstrame las ventas por región del último trimestre"* y Joi:

1. Interpreta la intención y genera el SQL correcto.
2. Ejecuta la consulta de forma segura (solo `SELECT`, nunca escritura).
3. Elige el tipo de widget más adecuado para los datos devueltos.
4. Genera el código del widget y lo renderiza en el canvas, en vivo.

Si los datos cambian de forma, el widget cambia con ellos. Si el generador falla, siempre hay una tabla con los datos crudos como fallback.

### Memoria semántica

Joi recuerda los widgets que ya generaste. Si vuelves a pedir algo similar, te ofrece reutilizar el widget anterior en lugar de regenerar. Esto reduce la latencia y el costo de API a cero en consultas repetidas.

### Colecciones y dashboards

Guarda los widgets que te parecen útiles, agrúpalos en colecciones y compónalos en dashboards personalizados con drag-and-drop. Un dashboard puede mezclar widgets de diferentes fuentes de datos.

### Agnóstica de proveedor

Usa Anthropic, OpenAI o Gemini — el mismo `.env` controla qué modelo va a cada agente. Para el vector store puedes usar Qdrant (incluido en Docker Compose), Chroma, Pinecone, Weaviate o PGVector.

---

## Cómo funciona por dentro

```
Usuario: "ventas por mes 2025"
         │
         ▼
  Triage Engine ─── consulta simple? ──► responde directamente
         │
         │ consulta de datos
         ▼
  Data Agent
  ├─ genera SQL
  ├─ guard read-only (solo SELECT)
  └─ ejecuta → DataExtraction (JSON)
         │
         ▼
  Cache RAG ─── hit semántico (score ≥ 0.85)? ──► sugiere widget guardado
         │
         │ miss → pipeline completo
         ▼
  Agente Arquitecto
  └─ selector determinístico → tipo de widget óptimo
         │
         ▼
  Agente Generador (LLM)
  └─ WidgetSpec con bindings validados
         │
         ▼
  Canvas (iframe sandboxed + Recharts)
  └─ widget visible, interactivo, aislado del DOM host
```

**Tipos de widget soportados:**
`table` · `bar_chart` · `line_chart` · `area_chart` · `pie_chart` · `kpi` · `scatter_plot` · `heatmap`

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Frontend | Next.js 15 · Tailwind CSS v4 · shadcn/ui |
| Backend | Python 3.13 · FastAPI · LiteLLM (agnóstico de LLM) |
| Base de datos | SQLite vía SQLAlchemy async (desarrollo) / PostgreSQL (producción) |
| Cache vectorial | Qdrant (default Docker) · Chroma · Pinecone · Weaviate · PGVector |
| Tests | pytest · pytest-asyncio · Playwright E2E |
| CI | GitHub Actions |

---

## Levantar el proyecto

### Requisitos previos

- Python 3.11+
- Node.js 18+
- Docker (solo para Qdrant — el vector store)

### Primera vez

**Backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Abre `.env` y completa al menos una API key de LLM:

```env
# Elige uno (o más):
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# Y configura los modelos para ese proveedor:
LLM_MODEL_CHAT=anthropic/claude-haiku-4-5-20251001
LLM_MODEL_SQL=anthropic/claude-haiku-4-5-20251001
LLM_MODEL_WIDGET=anthropic/claude-haiku-4-5-20251001

# Modelo de embeddings (debe coincidir con el proveedor):
EMBEDDING_MODEL=gemini/text-embedding-004   # o text-embedding-3-small para OpenAI
```

**Frontend:**

```bash
cd frontend
npm install
npm run build:widget-runtime   # compila el bundle del sandbox de widgets
```

### Arranque diario

```bash
# 1. Vector store en background (solo la primera vez o tras reiniciar Docker)
docker compose up qdrant -d

# 2. Backend + Frontend juntos
./dev.sh
```

`./dev.sh` espera a que el backend responda antes de arrancar el frontend. No hace falta coordinarlos manualmente.

| Servicio | URL |
|---|---|
| App | http://localhost:3000 |
| API | http://localhost:8000/api |
| Swagger | http://localhost:8000/docs |
| Qdrant UI | http://localhost:6333/dashboard |

### Docker completo (producción / CI)

```bash
docker compose up --build
```

---

## Tests

```bash
# Backend — suite completa (< 5 s, sin servicios externos)
cd backend && .venv/bin/pytest

# Con cobertura
cd backend && .venv/bin/pytest --cov=app --cov-report=term-missing

# E2E (requiere backend + frontend corriendo)
cd frontend && ./dev-e2e.sh   # desde la raíz: ./dev-e2e.sh
```

La suite E2E levanta sus propios procesos, siembra la base de datos de test y los cierra al terminar.

---

## Configuración avanzada

### Cambiar el modelo LLM

Joi usa LiteLLM, así que el formato de modelo es `proveedor/nombre-del-modelo`:

```env
LLM_MODEL_WIDGET=gemini/gemini-2.5-flash
LLM_MODEL_SQL=anthropic/claude-sonnet-4-6
LLM_MODEL_CHAT=openai/gpt-4o-mini
```

Cada propósito puede usar un proveedor distinto. Los modelos más capaces para generación de widgets (`LLM_MODEL_WIDGET`) dan mejores resultados en la calidad del código generado.

### Vector store BYO (Bring Your Own)

Qdrant corre en Docker Compose por defecto. Para usar otro proveedor:

1. Ve a `/setup → Vector Store`.
2. Elige el proveedor e ingresa las credenciales (se cifran con AES-256 antes de persistir).
3. Haz click en "Validar conexión" — Joi hace un ping real antes de guardar.

Si el vector store no está disponible, el cache se degrada a miss y la sesión continúa normalmente.

### Render-mode del widget

Los widgets pueden renderizarse con diferentes frameworks UI. Configurable en `/setup → Widgets`:

- **shadcn** (default) — componentes Radix + Tailwind
- **Bootstrap 5** — clases CSS clásicas
- **HeroUI** — componentes React modernos
- **Sin framework** — HTML/CSS puro

---

## Estructura del repositorio

```
joi-app/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints FastAPI
│   │   ├── models/       # SQLAlchemy ORM
│   │   ├── repositories/ # Acceso a datos
│   │   └── services/     # Agentes, cache RAG, embeddings, triage
│   └── tests/            # Unit + integration tests
├── frontend/
│   ├── src/
│   │   ├── app/          # Páginas Next.js (App Router)
│   │   ├── components/   # Componentes React
│   │   ├── hooks/        # Custom hooks
│   │   └── lib/          # Utilidades, storage, widget runtime
│   └── e2e/              # Tests Playwright
├── specs/                # Documentación SDD (features, roadmap, ADLs)
└── .design-logs/         # Architectural Decision Logs (ADL-001 → ADL-023)
```
