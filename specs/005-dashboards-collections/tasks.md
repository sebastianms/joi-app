# Tasks: Feature 005 — Dashboards, Collections & RAG Cache

**Branch**: `005-dashboards-collections` | **Date**: 2026-04-24 | **Status**: Setup ✅ | Foundational ✅ | US1 ✅ | US2 ✅ | US3 ✅ | US4–US5 pendientes

> Formato: `- [ ] T### [P?] [US?] Descripción con ruta exacta`.
> `[P]` = paralelizable con hermanas (distinto archivo, sin dependencias).
> `[US1..5]` = user story servida (solo en bloques de user stories).
>
> **Checkpoints de bloque**: al cerrar cada bloque (Setup, Foundational, cada US, Polish) ejecutar `deckard` review, revisar ADLs, correr suite de tests, hacer commits por grupo y `git push`.

---

## Setup

- [x] T001 Añadir servicio `qdrant` al [docker-compose.yml](docker-compose.yml) con imagen `qdrant/qdrant:v1.10.0`, puerto `6333`, volumen `./qdrant/storage:/qdrant/storage`, healthcheck HTTP `/healthz`.
- [x] T002 [P] Añadir variables al [backend/.env.example](backend/.env.example): `QDRANT_URL=http://qdrant:6333`, `EMBEDDING_MODEL=text-embedding-3-small`, `VECTOR_STORE_ENCRYPTION_KEY=<generar>`.
- [x] T003 [P] Añadir dependencias core al [backend/requirements.txt](backend/requirements.txt): `langchain-core`, `langchain-community`, `langchain-qdrant`, `qdrant-client`. Extras lazy documentados en comentario: `langchain-chroma`, `langchain-pinecone`, `langchain-weaviate`, `langchain-postgres`.
- [x] T004 [P] Añadir dependencias frontend a [frontend/package.json](frontend/package.json): `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`. Ejecutar `npm install` y verificar lockfile.
- [x] T005 [P] Crear directorios nuevos en `backend/app/services/`: `embeddings/`, `widget_cache/`. Añadir `__init__.py` vacíos.
- [x] T006 [P] Crear directorios nuevos en `frontend/src/components/`: `collections/`, `dashboards/`. Añadir `.gitkeep`.
- [x] T007 Añadir `./qdrant/storage/` a `.gitignore`.

---

## Foundational (bloquean todas las user stories)

### Modelos + migraciones

- [x] T010 Extender [backend/app/models/widget.py](backend/app/models/widget.py) (Pydantic + SQLAlchemy ORM) con `is_saved: bool = False`, `display_name: Optional[str]`, `saved_at: Optional[datetime]`. Añadir índices conforme a `data-model.md`.
- [x] T011 Crear [backend/app/models/collection.py](backend/app/models/collection.py): `Collection`, `CollectionWidget` junction (PK compuesta) con constraint UNIQUE `(session_id, name)` en collections.
- [x] T012 Crear [backend/app/models/dashboard.py](backend/app/models/dashboard.py): `Dashboard`, `DashboardItem`, ORMs + constraint UNIQUE `(dashboard_id, widget_id)` en items.
- [x] T013 Crear [backend/app/models/vector_store_config.py](backend/app/models/vector_store_config.py): `VectorStoreConfig` Pydantic + `VectorStoreConfigORM` + enum `VectorStoreProvider`.
- [x] T014 Crear [backend/app/models/widget_cache.py](backend/app/models/widget_cache.py): `WidgetCacheEntry` Pydantic + `WidgetCacheEntryORM` con soft-delete (`invalidated_at`). Añadido `CacheIndexRequest` dataclass (fix [F1] Deckard).
- [x] T015 Registrar todas las tablas nuevas en `Base.metadata` dentro de [backend/app/main.py](backend/app/main.py) (lifespan crea si no existen).

### Abstracción del vector store y embeddings

- [x] T020 Crear [backend/app/services/embeddings/litellm_embeddings.py](backend/app/services/embeddings/litellm_embeddings.py): clase `LiteLLMEmbeddings(Embeddings)` con `embed_documents`, `embed_query`, cache LRU in-memory.
- [x] T021 Crear [backend/app/services/widget_cache/vector_store_factory.py](backend/app/services/widget_cache/vector_store_factory.py): `build_vector_store(config, embeddings) -> VectorStore`. Despacho por provider con imports lazy.
- [x] T022 Crear [backend/app/services/widget_cache/bootstrap.py](backend/app/services/widget_cache/bootstrap.py): `ensure_widget_cache_collection()` registrado en `main.lifespan`. Degradación graceful si Qdrant no disponible.
- [x] T023 Crear [backend/app/services/widget_cache/cache_service.py](backend/app/services/widget_cache/cache_service.py): `CacheService` con `search/index/invalidate_by_connection`. Filtros obligatorios por `session_id`, `connection_id`, `data_schema_hash`. Fallback no-bloqueante (FR-013).

### Cifrado de credenciales BYO

- [x] T025 Crear [backend/app/services/security/encryption.py](backend/app/services/security/encryption.py): Fernet/SHA-256. `VECTOR_STORE_ENCRYPTION_KEY` requerida; RuntimeError claro si no está seteada.

### Repositorios

- [x] T030 [P] Crear [backend/app/repositories/collection_repository.py](backend/app/repositories/collection_repository.py): CRUD + operaciones N:M (add/remove widget). Queries siempre filtran por `session_id`.
- [x] T031 [P] Crear [backend/app/repositories/dashboard_repository.py](backend/app/repositories/dashboard_repository.py): CRUD + `update_layout(dashboard_id, items)` con clamping de width [1,12].
- [x] T032 [P] Crear [backend/app/repositories/vector_store_config_repository.py](backend/app/repositories/vector_store_config_repository.py): upsert por session (unique), encrypt/decrypt transparente.
- [x] T033 [P] Crear [backend/app/repositories/widget_cache_repository.py](backend/app/repositories/widget_cache_repository.py): acepta `WidgetCacheEntryORM` directamente (no fields sueltos). NO toca el vector store.

---

## User Story 1 — Guardar widget en colecciones (P1)

- [x] T050 [P] [US1] Endpoint `POST /api/widgets/{id}/save` en [backend/app/api/endpoints/widgets.py](backend/app/api/endpoints/widgets.py): marca `is_saved`, asigna `display_name`, asocia a `collection_ids` (multi, Q3 N:M). Valida que el widget tiene datos válidos (rechaza fallbacks).
- [x] T051 [P] [US1] Endpoint `DELETE /api/widgets/{id}/save` en mismo archivo: revierte, falla 409 si el widget está en algún dashboard.
- [x] T052 [P] [US1] Endpoint `POST /api/collections` y `GET /api/collections` en nuevo archivo [backend/app/api/endpoints/collections.py](backend/app/api/endpoints/collections.py).
- [x] T053 [US1] Frontend: componente [frontend/src/components/collections/SaveWidgetDialog.tsx](frontend/src/components/collections/SaveWidgetDialog.tsx) con multi-select de colecciones, creación inline, validación de nombre duplicado.
- [x] T054 [US1] Integrar botón "Guardar" en el toolbar del widget renderizado (actualizar componente del canvas existente con data-role `widget-save-button`).
- [x] T055 [US1] Hook [frontend/src/hooks/use-collections.ts](frontend/src/hooks/use-collections.ts) para CRUD básico y cache local (SWR-like).

---

## User Story 2 — Administrar colecciones (P1)

- [x] T060 [P] [US2] Endpoints `PATCH /api/collections/{id}`, `DELETE /api/collections/{id}` en [backend/app/api/endpoints/collections.py](backend/app/api/endpoints/collections.py).
- [x] T061 [P] [US2] Endpoints `GET /api/collections/{id}/widgets`, `POST /api/collections/{id}/widgets` (bulk add), `DELETE /api/collections/{id}/widgets/{widget_id}` en mismo archivo.
- [x] T062 [US2] Frontend: página [frontend/src/app/collections/page.tsx](frontend/src/app/collections/page.tsx) con lista de colecciones, widgets por colección, acciones rename/delete/move.
- [x] T063 [P] [US2] Componente [frontend/src/components/collections/CollectionList.tsx](frontend/src/components/collections/CollectionList.tsx).
- [x] T064 [P] [US2] Componente [frontend/src/components/collections/CollectionManager.tsx](frontend/src/components/collections/CollectionManager.tsx) para operaciones de widget (mover entre colecciones, preview del widget).

---

## User Story 3 — Componer dashboard con grid (P1)

- [x] T070 [P] [US3] Endpoints `POST/GET/PATCH/DELETE /api/dashboards` + `GET /api/dashboards/{id}` en [backend/app/api/endpoints/dashboards.py](backend/app/api/endpoints/dashboards.py).
- [x] T071 [US3] Endpoint `PATCH /api/dashboards/{id}/layout` con validación de grid (widths 1–12): [backend/app/api/endpoints/dashboards.py](backend/app/api/endpoints/dashboards.py).
- [x] T072 [P] [US3] Endpoints `POST /api/dashboards/{id}/items`, `DELETE /api/dashboards/{id}/items/{widget_id}` en mismo archivo.
- [x] T073 [US3] Frontend: ruta dinámica [frontend/src/app/dashboards/[id]/page.tsx](frontend/src/app/dashboards/[id]/page.tsx).
- [x] T074 [US3] Componente [frontend/src/components/dashboards/DashboardGrid.tsx](frontend/src/components/dashboards/DashboardGrid.tsx): dnd-kit SortableContext, 12-col grid.
- [x] T075 [P] [US3] Componente [frontend/src/components/dashboards/DashboardItem.tsx](frontend/src/components/dashboards/DashboardItem.tsx) con drag handle y placeholder de rehidratación (Q5 pendiente US4).
- [x] T076 [P] [US3] Componente [frontend/src/components/dashboards/NewDashboardDialog.tsx](frontend/src/components/dashboards/NewDashboardDialog.tsx).
- [x] T077 [US3] Hook [frontend/src/hooks/useDashboards.ts](frontend/src/hooks/useDashboards.ts) con mutations optimistas para el layout.

---

## User Story 4 — Recuperar widget guardado desde chat (P2)

- [ ] T080 [US4] Extender el triage determinístico existente (archivo del triage actual — verificar en `backend/app/services/triage/`) con patrones de recuperación (`muéstra(me)?|abre|trae|enseña`) + detección de nombres mediante fuzzy match (`rapidfuzz`).
- [ ] T081 [US4] En el pipeline `/api/chat`, si triage detecta intención de recuperación → buscar `widgets` saved por nombre → si match único devolver `recovered_widget`, si múltiples devolver `candidates`.
- [ ] T082 [US4] Añadir `rapidfuzz` a [backend/requirements.txt](backend/requirements.txt) (ligero).
- [ ] T083 [P] [US4] Frontend: manejar los nuevos campos `recovered_widget` / `candidates` en el handler del chat; renderizar lista clickeable cuando hay candidates.

---

## User Story 5 — RAG cache de widgets (P1)

- [ ] T090 [US5] Extender el pipeline del generador en [backend/app/services/widget/generator_orchestrator.py](backend/app/services/widget/generator_orchestrator.py) (o archivo equivalente existente) con:
  1. Antes del LLM: `CacheService.search(...)`.
  2. Si hay hit ≥ 0.85 → devolver `cache_suggestion` inline en la response de `/chat`, abortar generación.
  3. Si no hay hit o `skip_cache=true` en el request → continuar al LLM.
  4. Tras generación exitosa → `CacheService.index(...)`.
- [ ] T091 [US5] Extender schema de request/response de `/api/chat` (Pydantic): añadir `skip_cache: bool = False` en request, `cache_suggestion: Optional[CacheSuggestion]` en response.
- [ ] T092 [P] [US5] Endpoint `POST /api/widget-cache/search` en [backend/app/api/widget_cache.py](backend/app/api/widget_cache.py).
- [ ] T093 [P] [US5] Endpoint `POST /api/widget-cache/{id}/reuse` — clona widget, re-ejecuta query, incrementa `hit_count`, `last_used_at`.
- [ ] T094 [P] [US5] Endpoint `DELETE /api/widget-cache/{id}` — soft delete + remoción del point en provider.
- [ ] T095 [US5] Hook para invalidación al eliminar `Connection`: listener/handler que llama `CacheService.invalidate_by_connection(...)`.
- [ ] T096 [US5] Frontend: componente [frontend/src/components/chat/CacheReuseSuggestion.tsx](frontend/src/components/chat/CacheReuseSuggestion.tsx) con preview, score, dos botones "Usar este widget" / "Generar uno nuevo".
- [ ] T097 [US5] Hook [frontend/src/hooks/useWidgetCacheSuggestion.ts](frontend/src/hooks/useWidgetCacheSuggestion.ts) que orquesta `reuse` vs `skip_cache=true`.
- [ ] T098 [US5] Extender `WidgetGenerationTrace` para distinguir visualmente `source: "cache" | "generated" | "recovered"`.

### Sub-bloque US5b — BYO vector store

- [ ] T100 [P] [US5] Endpoints `POST /api/vector-store/validate`, `POST /api/vector-store/config`, `GET /api/vector-store/config`, `DELETE /api/vector-store/config`, `GET /api/vector-store/health` en [backend/app/api/vector_store.py](backend/app/api/vector_store.py).
- [ ] T101 [US5] Implementar validación por provider en `vector_store_factory` (ping/similarity_search dummy) reutilizado por `/validate` y `/config`.
- [ ] T102 [US5] Añadir extras opcionales a [backend/requirements.txt](backend/requirements.txt) con marcador (comentario: "opcional — BYO providers"): `langchain-chroma`, `langchain-pinecone`, `langchain-weaviate`, `langchain-postgres`. Documentar que el factory da error legible si el extra no está instalado.
- [ ] T103 [US5] Frontend: componente [frontend/src/components/setup/VectorStoreStep.tsx](frontend/src/components/setup/VectorStoreStep.tsx) — selector de provider, form dinámico por provider, botón Validar, botón Guardar, banner "Usando Qdrant por defecto".
- [ ] T104 [US5] Integrar `VectorStoreStep` como paso opcional del Setup Wizard existente.
- [ ] T105 [P] [US5] Hook [frontend/src/hooks/useVectorStoreConfig.ts](frontend/src/hooks/useVectorStoreConfig.ts).
- [ ] T106 [US5] Tests unitarios del factory: un test por provider (mockeando el import y el cliente); verificar que Qdrant default se construye si no hay config.

---

## Polish (cross-cutting)

- [ ] T200 Health endpoint global `/api/health` incluye sub-status del vector store activo (provider + healthy).
- [ ] T201 [P] Documentar en [README.md](README.md) el flag BYO vector store y pasos para configurar Pinecone/Chroma/Weaviate/PGVector.
- [ ] T202 [P] Actualizar [backend/app/services/triage/README](backend/app/services/triage/) (si existe) con los nuevos patrones de recuperación.
- [ ] T203 Playwright E2E: automatizar Escenarios 1, 2, 4, 6 de [quickstart.md](specs/005-dashboards-collections/quickstart.md) y correr toda la suit de tests E2E.
- [ ] T204 [P] Unit tests backend: `cache_service` (hit, miss, invalidación por schema, invalidación por connection).
- [ ] T205 [P] Unit tests backend: repositorios de collections y dashboards (CRUD, cascade, N:M).
- [ ] T206 Medir latencia de cache lookup en p95; ajustar si excede 300ms (SC-006).
- [ ] T207 Crear ADL-023 en [.design-logs/ADL-023-rag-langchain-byo-vector-store.md](.design-logs/ADL-023-rag-langchain-byo-vector-store.md) documentando: supersede parcial de ADL-010, LangChain como capa, Qdrant default, lista de providers BYO soportados, strategy de embeddings, filtros obligatorios por sesión.
- [ ] T208 Actualizar [specs/roadmap.md](specs/roadmap.md) Phase 6 marcando el anclaje a esta carpeta y removiendo la nota de RAG diferido.
- [ ] T209 Actualizar [specs/tech-stack.md](specs/tech-stack.md) sección "Vector Store (RAG)" con el stack decidido.
- [ ] T210 Deckard review final sobre todos los archivos tocados; criticidad ≥ 8 corregida antes de cerrar la feature.

---

## Dependencias clave

- Setup (T001–T007) → Foundational.
- Foundational (T010–T033) → cualquier US.
- US1 (T050–T055), US2 (T060–T064), US3 (T070–T077) son paralelizables entre sí una vez cerrado Foundational.
- US4 (T080–T083) depende de US1 (widgets saved).
- US5 (T090–T106) depende de Foundational. US5b (T100–T106) paralelo al resto de US5.
- Polish al final.

## Convenciones específicas de esta feature

- Todo código que toca el vector store va a través del factory. Intento de `import qdrant_client` fuera de `langchain-qdrant`/factory → falla PR review.
- Toda query a `widget_cache` lleva filtro `session_id` obligatorio; hay un test específico para evitar regresiones de aislamiento.
- Las credenciales BYO nunca se loguean ni se devuelven por API.
