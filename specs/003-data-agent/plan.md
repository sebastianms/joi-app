# Implementation Plan: Feature 003 — Data Agent

**Branch**: `003-data-agent` | **Date**: 2026-04-21 | **Status**: Ready for Tasks

---

## Summary

**Requisito primario**: reemplazar el placeholder actual de intenciones complejas en `ChatManagerService` por una invocación real al Data Agent. El agente genera consultas read-only sobre la fuente conectada por el usuario (SQL o JSON) y devuelve un contrato `data_extraction.v1` estable, acompañado por un "Agent Trace" observable en el chat.

**Enfoque técnico**: dos pipelines separados convergiendo en el mismo contrato de salida.
- **Pipeline SQL**: Vanna 2.0+ como orquestador Text-to-SQL con `AgentMemory` (RAG activable por sesión), usando LiteLLM como gateway LLM agnóstico.
- **Pipeline JSON**: adapter dedicado con LLM liviano (vía el mismo LiteLLM) que emite JSONPath sobre el archivo cargado en memoria.
- **Defensa read-only**: credenciales de BD de solo lectura (responsabilidad del usuario) + `ReadOnlySqlGuard` pre-ejecución.
- **Persistencia nueva**: tabla `user_sessions` en `joi_app.db` para sostener el flag `rag_enabled` por sesión.
- **Vector store**: Chroma local embebido, una colección por `session_id`.

---

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5 + React 19 + Next.js 16 (frontend).
**Primary Dependencies (nuevas para esta feature)**:
- `vanna` (Text-to-SQL framework — R1 de research.md).
- `litellm` (LLM gateway unificado — R2).
- `chromadb` (vector store embebido — R6).
- `jsonpath-ng` (pipeline JSON — R3).
- `sqlparse` (opcional, hardening del guard — R4).
**Dependencias heredadas**: FastAPI, SQLAlchemy + aiosqlite, Pydantic 2, asyncpg, aiomysql (Feature 001).
**Storage**:
- `joi_app.db` (SQLite local, ADL-003) — estado relacional, ahora con nueva tabla `user_sessions`.
- `backend/chroma_data/` (Chroma embebido) — memoria RAG por sesión.
- `backend/uploads/` (JSONs cargados, ADL-001) — lectura por el pipeline JSON.
**Testing**: pytest + pytest-asyncio (unit), Playwright (E2E frontend, ADL-002). Fixtures in-memory para SQLite; fixtures de fuente JSON pequeña; mocks de LiteLLM para tests sin red.
**Target Platform**: Linux/macOS local + Docker (según `docker-compose.yml` existente).
**Project Type**: web app (backend + frontend desacoplados).

---

## Constitution Check

| Invariante | Origen | Cómo lo cumple el plan |
|---|---|---|
| 100% read-only sobre fuentes | mission.md Success Metric | Defensa en dos capas (R4): credenciales read-only + `ReadOnlySqlGuard`. FR-002, FR-003. SC-001. |
| Agnosticismo LLM | mission.md Success Metric | LiteLLM como gateway único (R2). El `spec.md` no nombra proveedores; el plan permite hot-swap vía env vars. FR-016. |
| Multi-agente | tech-stack.md | Feature 003 implementa el Agente 1 (Data Agent). Agente 2 queda para Feature 004. Mismo contrato de salida mantiene el acoplamiento bajo. |
| Capa RAG | tech-stack.md + mission.md | `AgentMemory` de Vanna + Chroma, activable por sesión. US5, FR-012 a FR-015. |
| Triage híbrido | tech-stack.md | Sin cambios en esta feature. La capa probabilística queda diferida. |
| Almacenamiento local SQLite | ADL-003 | Tabla nueva `user_sessions` se crea en el mismo `joi_app.db` con aiosqlite async. |
| Conectores existentes | ADL-001 | Data Agent **consume** `DataSourceConnection` sin reimplementar acceso a fuentes. |
| Chat panel único | ADL-004 | Agent Trace se renderiza dentro del `ChatPanel` existente, sin regenerar `session_id`, respetando selectores estables. |
| E2E con aria-label | ADL-002 | Nuevos elementos UI (trace colapsable) deben exponer `aria-label` y `data-role` estables. |

**Resultado**: ✅ Sin violaciones. No se requiere Complexity Tracking.

---

## Project Structure

Los cambios se concentran en el backend; el frontend recibe una extensión mínima del hook y un componente nuevo para el trace.

```text
backend/
├── app/
│   ├── api/
│   │   └── endpoints/
│   │       └── chat.py                      # extensión retrocompatible: usa ChatResponse extendido
│   ├── db/
│   │   └── base.py                          # (ya existe; se asegura que user_sessions se registre)
│   ├── models/
│   │   ├── chat.py                          # extender Message y ChatResponse con extraction y trace
│   │   ├── connection.py                    # sin cambios
│   │   ├── extraction.py                    # NUEVO — DataExtraction, QueryPlan, AgentTrace, ColumnDescriptor, ExtractionError, SourceType, ErrorCode
│   │   └── user_session.py                  # NUEVO — SQLAlchemy model de UserSession
│   ├── repositories/
│   │   ├── connection_repository.py         # sin cambios
│   │   └── user_session_repository.py       # NUEVO — get_or_create, update_rag_enabled
│   ├── services/
│   │   ├── chat_manager.py                  # reemplaza placeholder COMPLEX por invocación al DataAgentService
│   │   ├── llm_gateway.py                   # EchoLLMGateway → LiteLLMGateway (usa el cliente LiteLLM compartido)
│   │   ├── triage_engine.py                 # sin cambios
│   │   ├── litellm_client.py                # NUEVO — singleton LiteLLM configurado por env vars
│   │   ├── read_only_sql_guard.py           # NUEVO — whitelist primer token + blacklist tokens peligrosos (+ sqlparse opcional)
│   │   ├── data_agent_service.py            # NUEVO — fachada: triage COMPLEX → selecciona pipeline → construye DataExtraction + AgentTrace
│   │   ├── agents/
│   │   │   ├── __init__.py                  # NUEVO
│   │   │   ├── sql_agent_adapter.py         # NUEVO — envuelve vanna.Agent + LiteLLMService + AgentMemory por sesión
│   │   │   ├── json_agent_adapter.py        # NUEVO — LLM liviano + jsonpath-ng; carga archivo JSON desde uploads/
│   │   │   └── litellm_vanna_service.py     # NUEVO — LiteLLMService(vanna.core.llm.base.LlmService)
│   │   └── rag_memory.py                    # NUEVO — factory de AgentMemory apuntando a colección session_{session_id} en Chroma
│   └── main.py                              # registrar la creación de la tabla user_sessions en lifespan
├── chroma_data/                             # NUEVO directorio (en .gitignore)
└── tests/
    ├── unit/
    │   ├── test_read_only_sql_guard.py      # NUEVO — casos de rechazo por cada token prohibido + casos permitidos
    │   ├── test_data_agent_service.py       # NUEVO — routing SQL vs JSON, errores mapeados, trace construido
    │   ├── test_sql_agent_adapter.py        # NUEVO — con LiteLLM mockeado
    │   ├── test_json_agent_adapter.py       # NUEVO — fixture JSON, JSONPath generado, truncación
    │   ├── test_user_session_repository.py  # NUEVO — get_or_create, idempotencia
    │   └── test_rag_memory_isolation.py     # NUEVO — dos sesiones no ven documentos de la otra (SC-007)
    ├── integration/
    │   └── test_chat_with_data_agent.py     # NUEVO — endpoint /api/chat/messages con intent complex end-to-end mockeando LiteLLM
    └── fixtures/
        ├── sales_sample.db                  # NUEVO — SQLite con tabla sales (ver quickstart)
        └── products_sample.json             # NUEVO — JSON array de productos

frontend/src/
├── components/chat/
│   ├── chat-panel.tsx                       # sin cambios estructurales
│   ├── message-list.tsx                     # renderiza MessageItem; si message.trace → renderiza AgentTraceBlock
│   ├── message-input.tsx                    # sin cambios
│   └── agent-trace-block.tsx                # NUEVO — elemento colapsable con query, preview, rejection flag
├── hooks/
│   └── use-chat.ts                          # extender tipo Message con extraction y trace opcionales
└── types/
    └── extraction.ts                        # NUEVO — tipos TypeScript del contrato data_extraction.v1 (generados o escritos a mano)

.design-logs/
└── ADL-005-data-agent-architecture.md       # NUEVO — consolida R1+R2+R3+R6 (Vanna, LiteLLM, pipelines duales, Chroma + RAG por sesión)

specs/
└── roadmap.md                               # actualización cosmética: marcar Phase 5 bullet 1 + nota RAG ya integrado
```

---

## Phase 0 — Research (completado)

Ver [research.md](research.md). Resumen:

| # | Decisión | Referencia |
|---|---|---|
| R1 | Vanna-AI 2.0 como Text-to-SQL | research.md#R1 |
| R2 | LiteLLM como gateway LLM único | research.md#R2 |
| R3 | Pipeline JSON dedicado (no JsonRunner Vanna) | research.md#R3 |
| R4 | Defensa read-only en 2 capas | research.md#R4 |
| R5 | AgentMemory de Vanna + namespaces por sesión | research.md#R5 |
| R6 | Chroma local embebido | research.md#R6 |
| R7 | ADL-005 consolida las 4 decisiones | research.md#R7 |
| R8 | Extender ChatResponse retrocompatible | research.md#R8 |
| R9 | DataExtraction y trace en memoria (no persistir) | research.md#R9 |

---

## Phase 1 — Design (completado)

- **Data model**: [data-model.md](data-model.md) — entidades `UserSession` (persistida), `DataExtraction`, `AgentTrace`, `QueryPlan`, `ColumnDescriptor`, `ExtractionError` (en memoria), extensión retrocompatible de `Message` y `ChatResponse`, memoria RAG como colecciones Chroma por sesión.
- **Contracts**:
  - [contracts/data-extraction-v1.schema.json](contracts/data-extraction-v1.schema.json) — JSON Schema Draft 2020-12 del contrato `data_extraction.v1`.
  - [contracts/api-spec.json](contracts/api-spec.json) — OpenAPI 3.1 de la extensión del endpoint `POST /api/chat/messages`.
- **Quickstart**: [quickstart.md](quickstart.md) — 11 escenarios de validación manual end-to-end.

---

## Secuencia de Implementación

El orden propuesto respeta dependencias técnicas y permite frecuentes puntos de validación. Se detalla en `tasks.md` (Phase 4). Esbozo aquí:

1. **Fundación**: crear modelos Pydantic/SQLAlchemy nuevos (`UserSession`, `DataExtraction`, `AgentTrace`), extender `chat.py`, crear la tabla y el repositorio de `UserSession`.
2. **Seguridad**: implementar `ReadOnlySqlGuard` con tests exhaustivos de rechazo/aceptación (antes del pipeline, porque es bloqueante).
3. **LLM gateway**: introducir `litellm` + `LiteLLMGateway` + `LiteLLMVannaService`. Reemplazar `EchoLLMGateway`. Verificar que el chat simple sigue funcionando.
4. **Pipeline SQL**: `SqlAgentAdapter` (Vanna + LiteLLMVannaService + AgentMemory opcional). Tests con LiteLLM mockeado.
5. **Pipeline JSON**: `JsonAgentAdapter` con LiteLLM + jsonpath-ng.
6. **RAG memory**: `rag_memory.py` + Chroma; namespaces por sesión; tests de aislamiento.
7. **Fachada**: `DataAgentService` que decide pipeline por `source_type`, maneja errores, construye `DataExtraction` + `AgentTrace`.
8. **Integración al chat**: `ChatManagerService.handle()` invoca al `DataAgentService` cuando intent=COMPLEX. Se acopla via dependency injection.
9. **Frontend**: tipos TS del contrato, extensión del hook `useChat`, componente `AgentTraceBlock`, integración en `MessageList`.
10. **Quickstart manual**: ejecutar los 11 escenarios.
11. **ADL-005**: redactar con los trade-offs finales observados en implementación.
12. **Polish**: actualizar `roadmap.md`, `.gitignore`, README si procede.

---

## Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| LiteLLM no propaga bien tool use de Vanna | Alto | Spike al inicio de step 3; si hay gap, extender el adapter. Fallback: usar adapters oficiales de Vanna solo para el agente. |
| Chroma async bloquea event loop | Medio | `asyncio.to_thread` como wrapper si es necesario. Benchmark en step 6. |
| LLM genera SQL correcta pero que evade el regex guard | Medio | Combinación whitelist + blacklist + hardening con sqlparse tokenizer. Tests adversariales en step 2. |
| Timeout no honrado por driver MySQL | Medio | `statement_timeout` + wrapper con `asyncio.wait_for()` como segunda línea. |
| Sesiones nuevas llegan sin `UserSession` preexistente | Bajo | `get_or_create` lazy al primer chat; default `rag_enabled=true`. |
| Colecciones Chroma crecen sin límite | Bajo | Fuera de scope MVP. Nota en ADL-005 + follow-up en Phase 6. |

---

## Criterios de Salida de la Feature

- [ ] Los 11 escenarios de `quickstart.md` pasan.
- [ ] Todos los tests unitarios e integración del backend pasan.
- [ ] Tests E2E del frontend (incluyendo Agent Trace) pasan.
- [ ] No se rompió ninguna suite existente de Feature 001/002.
- [ ] `ADL-005-data-agent-architecture.md` mergeado.
- [ ] `roadmap.md` actualizado.
- [ ] Feature 004 puede consumir `data_extraction.v1` sin ambigüedad (verificado leyendo los contratos en frío).

---

## Progress Tracking

- [x] Phase 0 — Research: `research.md`.
- [x] Phase 1 — Design: `data-model.md`, `contracts/`, `quickstart.md`.
- [ ] Phase 4 — Tasks: `tasks.md` (siguiente).
- [ ] Phase 5 — Implement.

---

## Complexity Tracking

No aplica. Constitution Check sin violaciones.
