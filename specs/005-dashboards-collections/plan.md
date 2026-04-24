# Implementation Plan: Feature 005 — Dashboards, Collections & RAG Cache

**Branch**: `005-dashboards-collections` | **Date**: 2026-04-24 | **Status**: Plan drafted post-Clarify

---

## Summary

Feature 005 agrega **persistencia de widgets** (colecciones + dashboards con layout en grid) y **caché semántico** de widgets vía RAG construido sobre **LangChain** con **Qdrant por defecto** y **BYO vector store** opcional. Reactivation controlada de la infraestructura RAG que estaba diferida por ADL-010. El Agente Generador gana un paso previo de consulta al caché; la UI suma vistas de colecciones, editor de dashboards drag-and-drop, una tarjeta de sugerencia de reuso en el chat, y un paso en el Setup Wizard para conectar un vector store propio.

Principios rectores para la implementación:
- **Reutilizar el modelo `Widget` existente** ([backend/app/models/widget.py](backend/app/models/widget.py)); no crear un modelo paralelo. Marcar con flag `is_saved` y `display_name` las instancias persistidas.
- **DB secundaria SQLite** sigue siendo la fuente de verdad de metadata; Qdrant sólo contiene embeddings + payload mínimo para búsqueda.
- **Sesión-scoped everywhere**: tanto tablas como filtros de Qdrant llevan `session_id`.
- **Fallback no bloqueante** si Qdrant está caído (FR-013): el pipeline generador procede sin caché.

---

## Technical Context

| Área | Elección | Justificación |
|---|---|---|
| Language/Version | Python 3.11 (backend), TypeScript 5 / React 19 (frontend) — sin cambios | Stack vigente del repo |
| Primary Dependencies (nuevas, backend) | `langchain-core`, `langchain-community`, `langchain-qdrant` (core). Extras lazy: `langchain-chroma`, `langchain-pinecone`, `langchain-weaviate`, `langchain-postgres` | Abstracción de VectorStore + BYO |
| Primary Dependencies (nuevas, frontend) | `@dnd-kit/core`, `@dnd-kit/sortable` | Grid drag-and-drop accesible |
| Embeddings | `text-embedding-3-small` vía LiteLLM envuelto como `Embeddings` de LangChain (`LiteLLMEmbeddings`) | Multilingüe, barato, agnóstico del provider |
| Storage de metadata | SQLite secundaria existente (`joi.db`) — nuevas tablas `collections`, `collection_widgets`, `dashboards`, `dashboard_items`, `widget_cache_entries`, `vector_store_configs` | ADL-003 mantiene esta DB como estado de app |
| Vector store (default) | Qdrant en contenedor Docker (`docker-compose.yml`) con volumen persistente | Clarify Q1 |
| Vector store (BYO) | Cualquiera soportado por LangChain; validado en runtime al conectar | Clarify Q1 refinado — FR-016 a FR-019 |
| Testing | pytest (backend), Playwright (E2E ya existente) | Alineado con Features 001–004 |
| Target Platform | Docker compose local + deployment futuro | Sin cambio |
| Project Type | web-service (FastAPI + Next.js) | Sin cambio |

---

## Constitution Check

| Constraint | Estado |
|---|---|
| `mission.md` — "Persistencia de dashboards y configuración en DB secundaria aislada" | ✅ Feature alineada; se mantiene SQLite como estado de app. |
| `mission.md` — "Multitenancy por sesión" | ✅ Clarify Q4 confirma aislamiento estricto por `UserSession`. |
| `mission.md` — "Aislamiento de escritura (solo lectura en DB original)" | ✅ El RAG y los dashboards no tocan las fuentes de datos originales; SQLAlchemy sigue envuelto en `ReadOnlySqlGuard` (ADL-005). |
| `tech-stack.md` — "Vector Store (RAG): diferido post-MVP" | ⚠️ **Se supersede en Feature 005**. Nuevo ADL-023 lo registra; este plan actualiza `tech-stack.md` como parte de A5 con: RAG sobre LangChain, Qdrant default, BYO vector store habilitado. |
| `tech-stack.md` — "LLMs agnóstico vía LiteLLM" | ✅ Embeddings van también por LiteLLM. |
| `roadmap.md` Phase 6 | ✅ Cierra esta phase. |

No hay violaciones que requieran entradas en Complexity Tracking.

---

## Project Structure

```text
backend/app/
├── models/
│   ├── collection.py              # Collection, CollectionWidget (junction)
│   ├── dashboard.py               # Dashboard, DashboardItem
│   ├── vector_store_config.py     # VectorStoreConfig (ORM + Pydantic)
│   ├── widget_cache.py            # WidgetCacheEntry (metadata ORM; vector vive en el provider)
│   └── widget.py                  # [EXTENDED] añadir is_saved, display_name
├── repositories/
│   ├── collection_repository.py
│   ├── dashboard_repository.py
│   ├── vector_store_config_repository.py
│   └── widget_cache_repository.py # consume VectorStore de LangChain vía factory
├── services/
│   ├── embeddings/
│   │   ├── __init__.py
│   │   └── litellm_embeddings.py  # LangChain `Embeddings` wrapper sobre LiteLLM
│   ├── widget_cache/
│   │   ├── __init__.py
│   │   ├── vector_store_factory.py  # build_vector_store(session, embeddings) → VectorStore
│   │   ├── cache_service.py       # índice + búsqueda + invalidación (LangChain API only)
│   │   └── bootstrap.py           # asegura índice/colección al startup del provider default
│   └── widget/                    # existente — nuevo hook pre-generación
│       └── generator_orchestrator.py  # [EXTENDED] consulta caché antes del LLM
└── api/
    ├── collections.py             # POST/GET/PATCH/DELETE /collections
    ├── dashboards.py              # POST/GET/PATCH/DELETE /dashboards
    ├── vector_store.py            # POST/GET /vector-store/config, POST /vector-store/validate, GET /vector-store/health
    └── widget_cache.py            # POST /widget-cache/search, DELETE /widget-cache/{id}, POST /widget-cache/{id}/reuse

frontend/src/
├── app/
│   └── collections/page.tsx       # vista de colecciones
│   └── dashboards/[id]/page.tsx   # editor de dashboard
├── components/
│   ├── collections/
│   │   ├── CollectionList.tsx
│   │   ├── SaveWidgetDialog.tsx   # multi-select de colecciones (Q3 N:M)
│   │   └── CollectionManager.tsx
│   ├── dashboards/
│   │   ├── DashboardGrid.tsx      # dnd-kit sortable grid
│   │   ├── DashboardItem.tsx
│   │   └── NewDashboardDialog.tsx
│   ├── chat/
│   │   └── CacheReuseSuggestion.tsx  # tarjeta "Usar este widget / Generar uno nuevo"
│   └── setup/
│       └── VectorStoreStep.tsx    # paso opcional del wizard: BYO vector store
├── hooks/
│   ├── useCollections.ts
│   ├── useDashboards.ts
│   ├── useVectorStoreConfig.ts
│   └── useWidgetCacheSuggestion.ts
└── types/
    ├── collection.ts
    ├── dashboard.ts
    ├── vector-store.ts
    └── widget-cache.ts

docker-compose.yml                 # [MODIFIED] + servicio qdrant (default)
backend/.env.example               # [MODIFIED] + QDRANT_URL, EMBEDDING_MODEL, VECTOR_STORE_ENCRYPTION_KEY
backend/requirements.txt           # [MODIFIED] + langchain-core, langchain-community, langchain-qdrant (extras opcionales lazy)
frontend/package.json              # [MODIFIED] + @dnd-kit/core, @dnd-kit/sortable
```

---

## High-Level Pipeline Changes

### Pipeline de generación (post-006)

```
Prompt → Triage (existente)
       → [NEW] Cache lookup en Qdrant (filtro: session_id, invalidated_at IS NULL)
           ├─ hit ≥ 0.85 → devuelve CacheReuseSuggestion al chat → usuario elige
           │   ├─ "Usar este widget"  → render directo (re-ejecuta query de datos)
           │   └─ "Generar uno nuevo" → continúa al Agente Generador
           └─ miss        → continúa al Agente Generador
       → Agente Generador (existente)
       → [NEW] Tras éxito, indexar WidgetCacheEntry en Qdrant
       → Render en canvas (existente)
```

### Persistencia de widgets

Al hacer click en "Guardar":
1. `Widget` existente se marca `is_saved=true` y recibe `display_name`.
2. Se inserta una fila en `collection_widgets` por cada colección seleccionada.
3. Si el widget ya estaba cacheado en Qdrant, se añade `saved_widget_id` a su payload para deduplicación.

---

## Complexity Tracking

> Sin violaciones pendientes. Todas las decisiones están ancladas a un FR y/o a una respuesta de Clarify.
