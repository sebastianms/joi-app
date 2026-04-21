# Data Model: Feature 003 — Data Agent

**Date**: 2026-04-21
**Status**: Completed

Este documento define las entidades, sus atributos, relaciones y reglas de validación para la Feature 003. Separa entidades **persistidas** (en `joi_app.db`) de entidades **en memoria** (solo durante la sesión activa) según las decisiones tomadas en Clarify y documentadas en `research.md`.

---

## Resumen del Modelo

```
┌─────────────────────┐       ┌──────────────────────────┐
│   UserSession       │       │ DataSourceConnection     │
│   [persisted]       │       │  [persisted, Feature 001]│
│                     │       │                          │
│ - session_id PK     │       │ - id PK                  │
│ - rag_enabled       │       │ - user_session_id  ─────┐│
│ - created_at        │       │ - source_type            ││
│ - updated_at        │       │ - connection_string      ││
└─────────────────────┘       │ - file_path              ││
         │                    │ - status                 ││
         │                    └──────────────────────────┘│
         │                                                │
         │ (1 sesión activa referencia 1 conexión activa) │
         └────────────────────────────────────────────────┘
                         ▲
                         │ consumida por
                         │
┌────────────────────────┴───────────────────────┐
│  DataExtraction  [in-memory, por sesión]       │
│                                                │
│  - extraction_id                               │
│  - session_id (FK lógico a UserSession)        │
│  - connection_id (FK lógico a DataSourceConn.) │
│  - source_type (SQL | JSON)                    │
│  - query_plan  (QueryPlan)                     │
│  - columns[]                                   │
│  - rows[]                                      │
│  - row_count                                   │
│  - truncated (bool)                            │
│  - status (success | error)                    │
│  - error (ExtractionError?)                    │
│  - generated_at                                │
│  - contract_version ("v1")                    │
└────────────────────────────────────────────────┘
         │
         │ referenciada por
         ▼
┌────────────────────────────────────────────────┐
│  AgentTrace  [in-memory, adjunto al Message]   │
│                                                │
│  - trace_id                                    │
│  - extraction_id                               │
│  - pipeline ("sql" | "json")                   │
│  - query_display (string legible)              │
│  - preview_rows[] (primeras N filas)           │
│  - security_rejection (bool)                   │
│  - collapsed (bool, estado UI)                 │
│  - created_at                                  │
└────────────────────────────────────────────────┘
```

---

## Entidad 1 — `UserSession` (PERSISTED)

Primera entidad de sesión persistida en el proyecto. Hoy las sesiones viven solo en memoria (`ChatManagerService._history`). Esta feature introduce su persistencia para sostener el flag `rag_enabled`.

### Atributos

| Campo | Tipo | Nulabilidad | Descripción |
|---|---|---|---|
| `session_id` | `str` (UUID string) | NOT NULL, PK | Identificador único. Generado en el frontend (`crypto.randomUUID()`) y propagado al backend en el primer `/api/chat/messages`. |
| `rag_enabled` | `bool` | NOT NULL, default `true` | Controla si la memoria RAG del Data Agent está activa para esta sesión. |
| `created_at` | `datetime` (UTC) | NOT NULL, default `now()` | Marca de creación de la sesión. |
| `updated_at` | `datetime` (UTC) | NOT NULL, default `now()`, on update `now()` | Marca de última actualización. |

### Reglas de Validación

- `session_id` debe ser un string no vacío (mínimo 1 carácter). En la práctica será un UUID v4, pero no se fuerza el formato para mantener compatibilidad con los tests existentes del chat que usan strings arbitrarios.
- `rag_enabled` por defecto `true`. Expuesto al backend vía API interna (no hay UI en esta feature, pero existe endpoint/servicio para modificarlo a futuro).
- Tabla: `user_sessions`. Índice implícito por PK.

### Migración

Feature 003 introduce esta tabla en `joi_app.db`. Estrategia:

- **Opción inicial**: crear la tabla en `lifespan` de FastAPI (`app.main.lifespan`) junto a las demás tablas existentes, usando el mismo mecanismo de `Base.metadata.create_all()`. Consistente con el approach actual (no hay Alembic todavía).
- **Lazy upsert**: cuando llega un `session_id` nuevo al `ChatManagerService`, se hace `get_or_create` — si no existe, se inserta con `rag_enabled=true`.

### Relaciones

- **1:N lógico** con `DataSourceConnection.user_session_id` (una sesión puede registrar varias conexiones a lo largo del tiempo, aunque el MVP típicamente usa una activa).
- **1:N lógico** con `DataExtraction.session_id` (en memoria, no FK física).

---

## Entidad 2 — `DataExtraction` (IN-MEMORY)

Resultado de una invocación al Data Agent. Se adjunta al historial del chat en memoria del `ChatManagerService`. No se persiste.

### Atributos

| Campo | Tipo | Nulabilidad | Descripción |
|---|---|---|---|
| `extraction_id` | `str` (UUID) | NOT NULL | Identificador único de esta extracción. Usable como referencia estable desde la UI. |
| `session_id` | `str` | NOT NULL | FK lógico a `UserSession`. |
| `connection_id` | `str` | NOT NULL | FK lógico a `DataSourceConnection`. |
| `source_type` | `SourceType` enum | NOT NULL | Valores: `SQL_POSTGRESQL`, `SQL_MYSQL`, `SQL_SQLITE`, `JSON`. |
| `query_plan` | `QueryPlan` (sub-entidad) | NOT NULL | Ver sub-entidad más abajo. |
| `columns` | `list[ColumnDescriptor]` | NOT NULL, puede estar vacía | Ver sub-entidad. |
| `rows` | `list[dict[str, Any]]` | NOT NULL, puede estar vacía | Cada fila es un dict de `nombre_columna → valor`. |
| `row_count` | `int` | NOT NULL, ≥ 0 | Filas totales devueltas. |
| `truncated` | `bool` | NOT NULL, default `false` | `true` si el resultado excedió el límite y fue recortado. |
| `status` | `"success" \| "error"` | NOT NULL | Estado final de la extracción. |
| `error` | `ExtractionError` (sub-entidad) | Nullable | Presente solo si `status="error"`. |
| `generated_at` | `datetime` UTC | NOT NULL | Timestamp de finalización. |
| `contract_version` | `str` | NOT NULL, default `"v1"` | Versión del contrato (`data_extraction.v1`). |

### Sub-entidad: `QueryPlan`

Representación agnóstica de la consulta ejecutada.

| Campo | Tipo | Descripción |
|---|---|---|
| `language` | `"sql" \| "jsonpath"` | Tipo de expresión. |
| `expression` | `str` | La consulta completa (SQL string o JSONPath string). Auditado en el trace. |
| `parameters` | `dict[str, Any]` (opcional) | Parámetros bindeados si la consulta es parametrizada. |
| `generated_by_model` | `str` | Nombre/alias del modelo que la generó (para observabilidad). Ej: `"claude-sonnet-4-5"`, `"gpt-4o-mini"`. |

### Sub-entidad: `ColumnDescriptor`

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | `str` | Nombre de la columna como se expuso en el resultado. |
| `type` | `str` | Tipo detectado (`"string"`, `"integer"`, `"float"`, `"boolean"`, `"datetime"`, `"null"`, `"unknown"`). |

### Sub-entidad: `ExtractionError`

| Campo | Tipo | Descripción |
|---|---|---|
| `code` | `ErrorCode` enum | Ver lista abajo. |
| `message` | `str` | Mensaje legible para el usuario (en español). |
| `technical_detail` | `str` | Detalle técnico para el trace (stack trace resumido, error del driver). |

**`ErrorCode` values**:
- `NO_CONNECTION` — no hay fuente activa para la sesión.
- `SECURITY_REJECTION` — `ReadOnlySqlGuard` bloqueó la consulta.
- `QUERY_SYNTAX` — sintaxis inválida generada por el LLM.
- `TARGET_NOT_FOUND` — tabla/campo/path inexistente.
- `PERMISSION_DENIED` — la fuente rechazó por permisos.
- `TIMEOUT` — se excedió el tiempo límite.
- `EMPTY_RESULT` — (no es error técnicamente, pero se marca en éxito con 0 filas; no se usa aquí).
- `AMBIGUOUS_PROMPT` — el agente no pudo mapear el prompt a una consulta concreta.
- `SOURCE_UNAVAILABLE` — la fuente no respondió.
- `UNKNOWN` — cualquier otro error no clasificado.

### Invariantes

- Si `status="success"`, entonces `error` es `null` y `rows.length == row_count`.
- Si `status="error"`, entonces `error` es no-null y `rows` suele estar vacío (puede no estarlo si la error ocurre tras una extracción parcial; en ese caso `truncated=true`).
- `row_count` ≤ límite configurado (default 1000 por FR-006).

---

## Entidad 3 — `AgentTrace` (IN-MEMORY)

Vista de observabilidad emparejada a cada `DataExtraction`. Adjunta al `Message` del asistente en el historial del chat.

### Atributos

| Campo | Tipo | Descripción |
|---|---|---|
| `trace_id` | `str` (UUID) | Identificador único. |
| `extraction_id` | `str` | FK a la `DataExtraction` correspondiente. |
| `pipeline` | `"sql" \| "json"` | Pipeline que procesó la solicitud. |
| `query_display` | `str` | Consulta formateada para mostrar (SQL pretty-printed o JSONPath). |
| `preview_rows` | `list[dict]` | Primeras N filas (N configurable, default 10). Subconjunto de `DataExtraction.rows`. |
| `preview_columns` | `list[ColumnDescriptor]` | Columnas de la preview (pueden ser todas o un subset). |
| `security_rejection` | `bool` | `true` si la consulta fue bloqueada por `ReadOnlySqlGuard`. |
| `collapsed` | `bool` | Estado UI inicial (default `true`, el usuario expande si quiere ver). |
| `created_at` | `datetime` UTC | Timestamp. |

### Reglas de construcción

- Se construye **siempre** tras una invocación al Data Agent, haya o no extracción exitosa.
- Si la extracción falló antes de ejecutar (p.ej. no hay conexión, prompt ambiguo), el trace contiene `query_display=""`, `preview_rows=[]`, y el mensaje del error en `ExtractionError.message` (accesible vía `extraction_id`).
- Si el security guard rechazó, `security_rejection=true` y `query_display` contiene la SQL bloqueada (para que el usuario vea qué intentó generar el LLM).

---

## Entidad 4 — `Message` extendido (IN-MEMORY)

El `Message` existente del Feature 002 se extiende de forma **retrocompatible** con dos campos opcionales que solo se rellenan cuando el role es `assistant` y hubo invocación del Data Agent.

### Cambios sobre [backend/app/models/chat.py:14-16](backend/app/models/chat.py#L14-L16)

```python
class Message(BaseModel):
    role: Role
    content: str
    # Campos nuevos, opcionales, retrocompatibles:
    extraction: Optional[DataExtraction] = None
    trace: Optional[AgentTrace] = None
```

### Cambios sobre `ChatResponse` ([backend/app/models/chat.py:28-30](backend/app/models/chat.py#L28-L30))

```python
class ChatResponse(BaseModel):
    response: str
    intent_type: IntentType
    # Campos nuevos, opcionales:
    extraction: Optional[DataExtraction] = None
    trace: Optional[AgentTrace] = None
```

**Garantía retrocompatible**: los consumidores existentes que solo leen `response` + `intent_type` siguen funcionando. Los nuevos consumidores (Feature 003 frontend) leen `extraction` y `trace` cuando están presentes.

---

## Entidad 5 — Memoria RAG por Sesión (NAMESPACES EXTERNOS)

La memoria RAG no es una entidad del modelo de dominio en el sentido clásico (no se accede desde la app con CRUD). Se describe aquí como **colección de vectores en el store externo** (Chroma) para completitud.

### Estructura

- **Store**: Chroma local embebido, persistencia en `./backend/chroma_data/`.
- **Colección por sesión**: nombre `session_{session_id}` (p.ej. `session_a3f7...`). Cada colección contiene documentos vectorizados generados por `vanna.AgentMemory`.
- **Documentos dentro de una colección**: pares pregunta ↔ SQL exitoso ↔ snapshot de schema. El formato exacto es el que Vanna emita; no lo controlamos.
- **Ciclo de vida**: se crea al primer uso de RAG en una sesión con `rag_enabled=true`. Persiste a través de reinicios del backend. No hay purga automática en esta feature (follow-up de Phase 6).

### Aislamiento (cumplimiento de FR-013 y SC-007)

- El `DataAgentService` **solo** instancia `AgentMemory` apuntando a la colección de la `session_id` actual.
- No existe código que lea o escriba en una colección distinta a la de la sesión en curso.
- Test de aislamiento: dos sesiones simultáneas, cada una hace N consultas; recuperar memoria de sesión A no debe devolver documentos de sesión B. Verificable por unit test con Chroma.

---

## Estados y Transiciones de una Extracción

```
 [start]
    │
    ▼
 triage COMPLEX ──► no hay conexión activa ──► status=error, code=NO_CONNECTION, trace con mensaje guía a /setup
    │
    ▼ hay conexión
 pipeline seleccionado (SQL vs JSON por source_type)
    │
    ├─ pipeline SQL ──► LLM genera SQL ──► ReadOnlySqlGuard ──► rechazo ──► status=error, code=SECURITY_REJECTION
    │                                           │
    │                                           ▼ aprobado
    │                                     ejecutar en fuente con timeout
    │                                           │
    │                                           ├─ timeout ──► status=error, code=TIMEOUT
    │                                           ├─ driver error ──► status=error, code=QUERY_SYNTAX | TARGET_NOT_FOUND | PERMISSION_DENIED
    │                                           └─ ok ──► rows, truncate si > límite ──► status=success
    │
    └─ pipeline JSON ──► LLM liviano genera JSONPath ──► ejecutar en memoria
                                                            │
                                                            ├─ path inválido ──► status=error, code=QUERY_SYNTAX
                                                            ├─ target no existe ──► status=error, code=TARGET_NOT_FOUND
                                                            └─ ok ──► rows, truncate si > límite ──► status=success
    │
    ▼
 construir DataExtraction + AgentTrace
    │
    ▼
 adjuntar al Message de historial
    │
    ▼
 si rag_enabled y status=success ──► escribir aprendizaje en colección de la sesión
    │
    ▼
 devolver ChatResponse (con extraction y trace poblados)
```

---

## Límites y Constantes

| Constante | Valor default | Configurable por | Fuente |
|---|---|---|---|
| `MAX_ROWS_PER_EXTRACTION` | 1000 | Env var | FR-006, Assumption |
| `QUERY_TIMEOUT_SECONDS` | 10 | Env var | FR-007, Assumption |
| `TRACE_PREVIEW_ROWS` | 10 | Constante | Decisión de UX, no es FR crítico |
| `JSON_MAX_FILE_SIZE` | 10 MB | Ya establecido | ADL-001 (heredado) |
| `RAG_DEFAULT_ENABLED` | `true` | Env var | Clarify Session, Assumption |

---

## Dependencias del Modelo

- **Hereda de Feature 001**: `DataSourceConnection` sin cambios.
- **Hereda de Feature 002**: `Role`, `IntentType`, `TriageResult`.
- **Introduce**: `UserSession`, `DataExtraction`, `AgentTrace`, `QueryPlan`, `ColumnDescriptor`, `ExtractionError`, `SourceType`, `ErrorCode`.
- **Extiende**: `Message`, `ChatResponse` (retrocompatible, campos opcionales).
