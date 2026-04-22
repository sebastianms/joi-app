# Tasks: Feature 003 — Data Agent

**Branch**: `003-data-agent` | **Date**: 2026-04-21
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` (todos completados).

---

## Legenda

- `[ ]` / `[x]` / `[/]` — pendiente / completada / en curso.
- `TNNN` — identificador secuencial.
- `[P]` — paralelizable con otras `[P]` adyacentes (archivos distintos, sin dependencias).
- `[US1]`…`[US5]` — user story a la que pertenece.
- Polish y Setup no llevan `[US*]`.

Regla de progreso: antes de iniciar una tarea, marcarla `[/]`. Tras validación del usuario, marcarla `[x]`. Nunca avanzar sin validación explícita (ver `spec-driven-dev` skill, Phase 5).

---

## Setup Sub-tasks

- [x] **T001** Crear archivo `backend/chroma_data/.gitkeep` y agregar `backend/chroma_data/` al `.gitignore` del repo.
- [x] **T002** [P] Agregar dependencias nuevas al `backend/requirements.txt` (o `pyproject.toml` equivalente): `vanna`, `litellm`, `chromadb`, `jsonpath-ng`, `sqlparse`. Ejecutar `pip install -r requirements.txt` y verificar instalación limpia.
- [x] **T003** [P] Crear fixtures de datos de prueba para tests e2e:
  - `backend/tests/fixtures/sales_sample.db` (SQLite con tabla `sales(id, region, amount, sold_at)` y ~50 filas).
  - `backend/tests/fixtures/products_sample.json` (array de ~30 productos con `{id, name, category, price, stock}`).
- [x] **T004** [P] Extender `.env.example` del backend con: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` (todas opcionales), `RAG_DEFAULT_ENABLED=true`, `QUERY_TIMEOUT_SECONDS=10`, `MAX_ROWS_PER_EXTRACTION=1000`, `TRACE_PREVIEW_ROWS=10`, `LLM_MODEL_SQL`, `LLM_MODEL_JSON`.

---

## Foundational Sub-tasks

> Bloquean TODAS las user stories. Completar antes de entrar a US1.

### Data model base (persistencia + Pydantic)

- [x] **T005** Crear [backend/app/models/user_session.py](backend/app/models/user_session.py) con el SQLAlchemy model `UserSession` según `data-model.md` (campos: `session_id` PK, `rag_enabled` default `true`, `created_at`, `updated_at`).
- [x] **T006** Registrar `UserSession` en el `lifespan` de [backend/app/main.py](backend/app/main.py) para que `Base.metadata.create_all()` lo incluya al startup.
- [x] **T007** Crear [backend/app/repositories/user_session_repository.py](backend/app/repositories/user_session_repository.py) con métodos: `get_or_create(session_id) -> UserSession`, `get_by_id(session_id) -> UserSession | None`, `set_rag_enabled(session_id, enabled: bool) -> UserSession`.
- [x] **T008** [P] Crear [backend/app/models/extraction.py](backend/app/models/extraction.py) con los Pydantic models: `SourceType` enum, `ErrorCode` enum, `ColumnDescriptor`, `QueryPlan`, `ExtractionError`, `DataExtraction`, `AgentTrace`. Todos son modelos en memoria (Pydantic BaseModel), **no** SQLAlchemy. Incluir `contract_version: Literal["v1"] = "v1"`.
- [x] **T009** Extender [backend/app/models/chat.py](backend/app/models/chat.py): agregar campos opcionales `extraction: Optional[DataExtraction] = None` y `trace: Optional[AgentTrace] = None` a `Message` y `ChatResponse`. Asegurar retrocompatibilidad (defaults a `None`).

### Tests de modelos (fundacional)

- [x] **T010** [P] Crear [backend/tests/unit/test_user_session_repository.py](backend/tests/unit/test_user_session_repository.py): cubrir `get_or_create` idempotente, `set_rag_enabled` y `updated_at` que cambia.
- [x] **T011** [P] Crear [backend/tests/unit/test_extraction_models.py](backend/tests/unit/test_extraction_models.py): validar que `DataExtraction` con `status="error"` fuerza `error` no-null, serialización JSON cumple el schema `data_extraction.v1`.

---

## User Story 1 — Extracción de datos determinística (P1)

**Objetivo**: con una fuente SQL conectada, el endpoint de chat procesa un prompt complejo y devuelve una `DataExtraction` conforme al contrato.

### Seguridad (bloqueante de US1)

- [x] **T012** [US1] Crear [backend/app/services/read_only_sql_guard.py](backend/app/services/read_only_sql_guard.py) con `ReadOnlySqlGuard.validate(sql: str) -> None | raises SecurityRejectionError`. Implementación: whitelist primer token (`SELECT`, `WITH`, `SHOW`, `EXPLAIN`) + blacklist de tokens peligrosos (ver lista en `research.md` R4). Opcionalmente tokenizar con `sqlparse`.
- [x] **T013** [US1] [P] Crear [backend/tests/unit/test_read_only_sql_guard.py](backend/tests/unit/test_read_only_sql_guard.py): casos permitidos (SELECT simple, WITH CTE, SELECT con subquery, EXPLAIN), casos rechazados (cada token de la blacklist al menos una vez, incluyendo variantes: `DELETE`, `DROP TABLE`, `; DELETE FROM`, `PRAGMA writable_schema=ON`, SQL multi-statement).

### LLM Gateway (bloqueante de US1)

- [x] **T014** [US1] Crear [backend/app/services/litellm_client.py](backend/app/services/litellm_client.py) con un singleton que configura LiteLLM a partir de env vars (keys + modelos). Exponer función `get_client() -> LiteLLMClient` y `chat_completion(messages, purpose: Literal["sql", "json", "chat"]) -> str`.
- [x] **T015** [US1] Reemplazar el contenido de [backend/app/services/llm_gateway.py](backend/app/services/llm_gateway.py): `EchoLLMGateway` → `LiteLLMGateway` que usa el cliente del T014 con `purpose="chat"`. Mantener la interfaz `LLMGateway` para no romper `ChatManagerService`.
- [x] **T016** [US1] [P] Crear [backend/tests/unit/test_litellm_gateway.py](backend/tests/unit/test_litellm_gateway.py): mockear `litellm.completion`; verificar que `LiteLLMGateway.complete(history)` llama con los mensajes correctos y routing por purpose.

### SQL Pipeline (US1)

- [x] **T017** [US1] Crear [backend/app/services/agents/__init__.py](backend/app/services/agents/__init__.py) (package marker).
- [x] **T018** [US1] ~~Crear `LiteLLMVannaService(vanna.core.llm.base.LlmService)`~~ — **REDEFINIDO por ADL-009**: Vanna eliminado del stack. `SqlAgentAdapter` (T019) consume `litellm_client.acompletion(..., purpose="sql")` directamente. No se crea archivo dedicado; `backend/app/services/litellm_client.py` ya expone `acompletion` (commit donde se agregó).
- [x] **T019** [US1] Crear [backend/app/services/agents/sql_agent_adapter.py](backend/app/services/agents/sql_agent_adapter.py) con `SqlAgentAdapter.extract(prompt, connection, session_id) -> DataExtraction` (parámetro `rag_enabled` removido — ver ADL-010):
  1. Construir prompt NL→SQL con `system_prompt` que incluya dialecto (`POSTGRESQL`/`MYSQL`/`SQLITE`) y schema de la conexión (tablas + columnas + tipos).
  2. Llamar `litellm_client.acompletion(messages, purpose="sql")` para generar SQL. Extraer el string SQL del response OpenAI-style.
  3. Pasar por `ReadOnlySqlGuard` (T012). Si rechaza → devuelve `DataExtraction(status="error", error.code="SECURITY_REJECTION", query_plan.expression=<sql rechazada>)`.
  4. Ejecutar con SQLAlchemy (`create_engine(connection_string).connect().execute(text(sql))`) envuelto en `asyncio.wait_for(asyncio.to_thread(...), QUERY_TIMEOUT_SECONDS)`. Mapear excepciones de driver a `ErrorCode` (ver T037).
  5. Truncar a `MAX_ROWS_PER_EXTRACTION`; setear `truncated=True` si aplica.
  6. Construir `DataExtraction` poblado (columns, rows, row_count, query_plan con `generated_by_model = settings.LLM_MODEL_SQL`).
- [x] **T020** [US1] [P] Crear [backend/tests/unit/test_sql_agent_adapter.py](backend/tests/unit/test_sql_agent_adapter.py): mockear `litellm_client.acompletion` y la ejecución SQLAlchemy; casos: éxito con filas, rechazo por guard, timeout, target inexistente, truncación.

### Fachada y wiring al chat (US1)

- [x] **T021** [US1] Crear [backend/app/services/data_agent_service.py](backend/app/services/data_agent_service.py) con `DataAgentService.extract(session_id, prompt) -> tuple[DataExtraction, AgentTrace]`:
  1. Resolver `DataSourceConnection` activa para `session_id` via `ConnectionRepository`. Si no hay → retornar extraction con `error.code="NO_CONNECTION"`.
  2. Resolver `UserSession` (T007) — el campo `rag_enabled` se lee pero **no se usa** en MVP (ADL-010); se mantiene forward-compat.
  3. Rutear: `source_type in {POSTGRESQL, MYSQL, SQLITE}` → `SqlAgentAdapter` (T019); `source_type == JSON` → `JsonAgentAdapter` (T026, pero el stub vacío es suficiente aquí — completa US1 solo con SQL).
  4. Construir `AgentTrace` desde la `DataExtraction` devuelta (preview primeras `TRACE_PREVIEW_ROWS`, `query_display` desde `query_plan.expression`, `pipeline` según adapter).
  5. Retornar tupla.
- [x] **T022** [US1] Modificar [backend/app/services/chat_manager.py:23-41](backend/app/services/chat_manager.py#L23-L41):
  - Eliminar `_COMPLEX_INTENT_PLACEHOLDER` y la rama que lo usa.
  - En rama `COMPLEX`: invocar `DataAgentService.extract(session_id, message)`. Popular `response` con un mensaje natural (p.ej. `f"Encontré {row_count} filas…"` o el `error.message` si falló). Popular `extraction` y `trace` en el `ChatResponse` y en el `Message` del asistente.
  - ~~Inyectar `DataAgentService` por constructor.~~ `DataAgentService` se inyecta por parámetro en `handle()` porque depende de `AsyncSession` por request; `ChatManagerService` se mantiene singleton para preservar el historial en memoria.
- [x] **T023** [US1] Actualizar [backend/app/api/endpoints/chat.py](backend/app/api/endpoints/chat.py) si la dependency injection de `ChatManagerService` requiere pasar el `DataAgentService` nuevo (probablemente vía `Depends`).
- [x] **T024** [US1] [P] Crear [backend/tests/integration/test_chat_with_data_agent.py](backend/tests/integration/test_chat_with_data_agent.py): llamada end-to-end a `POST /api/chat/messages` con mock de LiteLLM y fuente SQLite fixture. Verifica que el response cumple el contrato `data_extraction.v1`.

### Frontend — recepción del contrato (US1)

- [x] **T025** [US1] [P] Crear [frontend/src/types/extraction.ts](frontend/src/types/extraction.ts) con los tipos TypeScript del contrato (`DataExtraction`, `AgentTrace`, `QueryPlan`, `ColumnDescriptor`, `ExtractionError`, enums). Mantener alineación 1:1 con el JSON Schema [contracts/data-extraction-v1.schema.json](contracts/data-extraction-v1.schema.json).

**Checkpoint US1**: T012→T024 completos y validados. Escenario 1 de `quickstart.md` pasa manualmente antes de avanzar.

---

## User Story 6 — JSON Pipeline (parte de FR-005, FR-016)

*Aunque el spec organiza por US1–US5, el pipeline JSON es una rama arquitectónica distinta y merece sus propias tareas. Se etiqueta como `[US1]` por ser parte de "extracción determinística" para fuentes JSON.*

- [x] **T026** [US1] Crear [backend/app/services/agents/json_agent_adapter.py](backend/app/services/agents/json_agent_adapter.py) con `JsonAgentAdapter.extract(prompt, connection, session_id) -> DataExtraction` (parámetro `rag_enabled` removido — ver ADL-010):
  1. Leer el archivo JSON desde `connection.file_path` (ya validado ≤10MB por ADL-001).
  2. Construir un prompt para LiteLLM con `purpose="json"` que pida un JSONPath o filtro estructurado dado el schema observado.
  3. Parsear y ejecutar el JSONPath con `jsonpath-ng` sobre el contenido cargado.
  4. Mapear el resultado a `rows` con columnas detectadas automáticamente (inspección de keys del primer elemento).
  5. Trunca + construir `DataExtraction` (idéntico contrato que el SQL pipeline).
- [x] **T027** [US1] [P] Crear [backend/tests/unit/test_json_agent_adapter.py](backend/tests/unit/test_json_agent_adapter.py): mockear LLM; usar fixture `products_sample.json`; casos: filtro por categoría, top-N, JSONPath inválido, target inexistente, truncación.
- [x] **T028** [US1] Ajustar el routing en `DataAgentService` (T021) para invocar `JsonAgentAdapter` cuando `source_type == JSON`. Verificar test de routing.

**Checkpoint JSON pipeline**: Escenario 6 de `quickstart.md` pasa manualmente.

---

## User Story 2 — Agent Trace visible y persistente en el chat (P1)

**Objetivo**: el trace aparece en el chat como elemento colapsable accesible con ≤1 clic.

- [x] **T029** [US2] Extender el hook [frontend/src/hooks/use-chat.ts](frontend/src/hooks/use-chat.ts): el tipo interno de `Message` debe incluir `extraction?: DataExtraction | null` y `trace?: AgentTrace | null`. El `fetch` a `/api/chat/messages` debe copiar `extraction` y `trace` del response al `Message` del asistente agregado al historial.
- [x] **T030** [US2] Crear [frontend/src/components/chat/agent-trace-block.tsx](frontend/src/components/chat/agent-trace-block.tsx): componente con `<details>/<summary>` HTML (colapsable nativo, accesible). Summary: `"Agent Trace — <pipeline> — <row_count> filas"`. Cuerpo: `query_display` en `<pre>`, tabla de `preview_rows`, badge `"Rechazo de seguridad"` si `security_rejection=true`. Exponer `aria-label="Agent trace"` y `data-role="agent-trace"` para selectores E2E (ADL-002, ADL-004).
- [x] **T031** [US2] Modificar [frontend/src/components/chat/message-list.tsx](frontend/src/components/chat/message-list.tsx): después de renderizar el contenido del mensaje del asistente, si `message.trace` existe, renderizar `<AgentTraceBlock trace={message.trace} extraction={message.extraction} />`.
- [ ] **T032** [US2] [P] Agregar test unitario [frontend/src/components/chat/agent-trace-block.test.tsx](frontend/src/components/chat/agent-trace-block.test.tsx): renderiza con y sin `security_rejection`, con filas vacías, con preview completa.
- [ ] **T033** [US2] [P] Agregar test E2E Playwright (reusar setup existente de Feature 002): flujo completo "enviar prompt complejo → ver Agent Trace colapsado → expandir → verificar contenido". Selector: `[data-role="agent-trace"]`.

**Checkpoint US2**: Escenario 2 de `quickstart.md` pasa.

---

## User Story 3 — Aislamiento y seguridad read-only (P1)

**Objetivo**: ataque adversarial no modifica la fuente; el trace registra el rechazo.

*La mayoría del trabajo ya está hecho en T012–T013 (guard) y T019 (integración en SqlAgentAdapter). Estas tareas cierran el ciclo UX + observabilidad.*

- [ ] **T034** [US3] Verificar en `SqlAgentAdapter` (T019) que cuando el guard rechaza, la `DataExtraction` emitida tiene `query_plan.expression = <sql rechazada>` (no vacía) para que el trace la muestre. Si falta, ajustar.
- [ ] **T035** [US3] Verificar que `AgentTraceBlock` (T030) resalta visualmente cuando `security_rejection=true` (badge rojo o similar). Si falta, ajustar.
- [ ] **T036** [US3] [P] Agregar test de integración [backend/tests/integration/test_security_rejection.py](backend/tests/integration/test_security_rejection.py): prompt adversarial (via mock de LiteLLM que devuelve `DELETE FROM sales`) → verificar que la fuente SQLite fixture NO cambia (conteo filas antes=después) y el response tiene `error.code=SECURITY_REJECTION`.

**Checkpoint US3**: Escenario 3 de `quickstart.md` pasa.

---

## User Story 4 — Manejo de errores graceful (P2)

**Objetivo**: timeouts, targets inexistentes, sintaxis inválida no rompen la sesión.

*El manejo técnico vive en `SqlAgentAdapter` (T019) y `JsonAgentAdapter` (T026). Estas tareas validan y refinan.*

- [ ] **T037** [US4] Revisar mapeo de excepciones a `ErrorCode` en ambos adapters (T019, T026). Casos requeridos: `asyncio.TimeoutError`→`TIMEOUT`, `sqlalchemy.exc.OperationalError` con `no such table`→`TARGET_NOT_FOUND`, `sqlalchemy.exc.ProgrammingError`→`QUERY_SYNTAX`, `PermissionError`/driver permission errors→`PERMISSION_DENIED`, `ConnectionError`→`SOURCE_UNAVAILABLE`.
- [ ] **T038** [US4] Verificar que tras un error, `ChatManagerService` NO levanta excepción: el error va dentro de `extraction.error` con HTTP 200. El historial del `Message` se escribe aun cuando `status="error"`.
- [ ] **T039** [US4] [P] Agregar test [backend/tests/integration/test_error_recovery.py](backend/tests/integration/test_error_recovery.py): tras error, enviar un segundo prompt simple en la misma sesión y verificar que responde.
- [ ] **T040** [US4] [P] Mejorar `response` textual en `ChatManagerService` (T022) para que los mensajes de error sean informativos: p.ej. `error.code == "TARGET_NOT_FOUND"` → `"No encontré una tabla llamada 'X'. ¿Querías referirte a una de estas: [lista]?"` (la lista puede ser best-effort; si es costoso, dejar mensaje genérico).

**Checkpoint US4**: Escenarios 4 y 5 de `quickstart.md` pasan.

---

## User Story 5 — Memoria RAG activable por sesión (P2) — **DIFERIDO POST-MVP**

> **ADL-010**: US5 queda fuera del alcance del MVP. Stack RAG se re-decide cuando US5 se reactive (ADL-007 queda archivada; Chroma/Vanna ya no son deps). El campo `UserSession.rag_enabled` (T007) se mantiene en el modelo como forward-compat pero **no se consulta en ningún pipeline activo**.

- [-] **T041** [US5] *DEFERRED* — Implementar `build_agent_memory(...)`. Stack a definir en nueva ADL cuando US5 se reactive.
- [-] **T042** [US5] *DEFERRED* — Integrar RAG en `SqlAgentAdapter`. Punto de integración: paso `generate` del adapter (inyectar few-shot en el prompt), no un `Agent` externo.
- [-] **T043** [US5] *DEFERRED* — Tests de aislamiento cross-session.
- [-] **T044** [US5] *DEFERRED* — Tests de toggle `rag_enabled`.
- [-] **T045** [US5] *DEFERRED* — Endpoint admin `PATCH /api/sessions/{session_id}`.

**Checkpoint US5**: N/A para MVP. Se cierra cuando se reactive US5.

---

## Edge Cases (cross-cutting)

- [ ] **T046** Verificar edge "sin conexión activa" (Escenario 9): `DataAgentService` (T021) devuelve `error.code="NO_CONNECTION"` y el response incluye un mensaje que referencia `/setup`. Test en [backend/tests/integration/test_no_connection.py](backend/tests/integration/test_no_connection.py).
- [ ] **T047** Verificar edge "truncación" (Escenario 10): bajar `MAX_ROWS_PER_EXTRACTION` y confirmar `truncated=true` en ambos adapters. Test en test_sql_agent_adapter y test_json_agent_adapter.
- [ ] **T048** Verificar edge "resultado vacío": `row_count=0`, `truncated=false`, `status="success"`. Mensaje textual: `"La consulta no devolvió filas."`.
- [ ] **T049** Verificar edge "compatibilidad hacia atrás" (Escenario 11): mensaje simple no rompe, `extraction=null`, `trace=null`. Agregar assert en el test existente de Feature 002 si no lo cubre ya.

---

## Polish Sub-tasks

- [ ] **T050** Ejecutar los 11 escenarios de [quickstart.md](quickstart.md) manualmente con backend y frontend reales. Documentar en un comentario del PR cualquier desviación.
- [ ] **T051** Verificar que la suite completa pasa: `pytest backend/tests/` + `npm test` + `npx playwright test`.
- [ ] **T052** Redactar [.design-logs/ADL-005-data-agent-architecture.md](.design-logs/ADL-005-data-agent-architecture.md) siguiendo el formato de los ADLs existentes. Contenido: consolidar R1, R2, R3, R6 de `research.md`. Incluir "Notas para el AI" con invariantes clave (read-only, aislamiento de sesión, agnosticismo LiteLLM).
- [ ] **T053** Actualizar [specs/roadmap.md](specs/roadmap.md):
  - Marcar Phase 5 bullet 1 (`Desarrollo del Agente de Datos`) como `[x]`.
  - Agregar nota en Phase 6 indicando que la infraestructura RAG **no** está operativa (US5 diferido, ver ADL-010).
- [ ] **T054** Actualizar [docs/walkthrough.md](docs/walkthrough.md) agregando una sección breve "Feature 003 — Data Agent" que explique el flujo end-to-end y apunte a los escenarios vigentes del quickstart (US1–US4; los de US5 quedan fuera).
- [-] **T055** *DEFERRED* — Verificación Chroma/.gitignore. Sin Chroma en el MVP (ADL-010), no hay artefactos a ignorar. `backend/chroma_data/` puede dejarse por compatibilidad futura o limpiarse; sin efecto en MVP.
- [ ] **T056** Revisión final de seguridad: grep en el código por llamadas directas a `litellm.completion` sin pasar por el gateway (anti-pattern); grep por ejecución de SQL que no pase por `ReadOnlySqlGuard` (anti-pattern).

---

## Resumen de Dependencias entre Tasks

```
Setup (T001-T004)
   └─► Foundational (T005-T011)
            └─► US1 Security (T012-T013) ──┐
            └─► US1 LLM Gateway (T014-T016) ─┤
            └─► US1 SQL Pipeline (T017-T020) ├─► US1 Fachada + Chat (T021-T024)
            └─► Frontend types (T025) ───────┘
                                                  └─► JSON Pipeline (T026-T028) [paralelo a US2]
                                                  └─► US2 Frontend Trace (T029-T033)
                                                  └─► US3 Verificación (T034-T036)
                                                  └─► US4 Error handling (T037-T040)
                                                  └─► US5 RAG (T041-T045)
                                                        └─► Edge Cases (T046-T049)
                                                              └─► Polish (T050-T056)
```

**Paralelización máxima**: tras completar T024 (integración chat+US1), US2, JSON pipeline, US3/US4/US5 pueden avanzar en paralelo (afectan archivos distintos). Los checkpoints de user story sirven como barreras naturales de validación.

---

## Criterios de Aceptación Global

La feature se considera completa únicamente cuando:

- [ ] Todas las tasks T001–T056 están en `[x]`.
- [ ] Los 11 escenarios del [quickstart.md](quickstart.md) pasan manualmente.
- [ ] Tests automatizados pasan sin regresiones en Features 001/002.
- [ ] ADL-005 mergeado.
- [ ] `roadmap.md` y `walkthrough.md` actualizados.
