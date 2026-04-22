# Data Model: Feature 004 — Widget Generation & Canvas Rendering

> Entidades introducidas por la feature. Mezcla de persistidas (SQLite `joi_app.db`) y en memoria (ciclo de vida de sesión).

---

## Entidades persistidas

### RenderModeProfile

Configuración del framework visual elegido por el usuario en el Setup Wizard. Una fila por `session_id`.

**Storage**: tabla `render_mode_profiles` en `joi_app.db` (SQLite, SQLAlchemy + aiosqlite).

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID (PK) | Identificador interno. |
| `session_id` | String (UNIQUE, NOT NULL) | Liga con `UserSession.session_id` de Feature 003. |
| `mode` | Enum (`ui_framework`, `free_code`, `design_system`) | Modo de render activo. |
| `ui_library` | Enum (`shadcn`, `bootstrap`, `heroui`, NULL) | Librería concreta cuando `mode == ui_framework`; NULL en otros modos. |
| `design_system_ref` | String (NULL) | Referencia futura al Storybook cargado; NULL en MVP. |
| `created_at` | Timestamp | Creación. |
| `updated_at` | Timestamp | Última modificación. |

**Reglas**:
- `mode == ui_framework` ⇒ `ui_library` NOT NULL.
- `mode == design_system` ⇒ DEBE rechazarse con error en el MVP (modo diferido).
- Default al crear (lazy, primera vez que se consulta para una sesión sin perfil): `mode=ui_framework`, `ui_library=shadcn`.

**Índices**: `session_id` UNIQUE.

**Migración**: `render_mode_profiles` se crea en `main.lifespan()` junto con el resto de tablas vía `Base.metadata.create_all`. No requiere migración de datos (tabla nueva).

---

## Entidades en memoria

### WidgetSpec

Contrato de salida del Agente Arquitecto/Generador. Versionado como `widget_spec.v1`. Consumido por el motor de Canvas y opcionalmente serializado en el `ChatResponse` para el frontend.

| Campo | Tipo | Descripción |
|---|---|---|
| `contract_version` | Literal `"v1"` | Versión del contrato. |
| `widget_id` | UUID | Identificador único de esta generación. |
| `extraction_id` | UUID | Referencia a la `DataExtraction` origen (Feature 003). |
| `session_id` | String | Sesión del usuario. |
| `render_mode` | Enum (`ui_framework`, `free_code`) | Modo activo para este widget. `design_system` no se emite en MVP. |
| `ui_library` | Enum (`shadcn`, `bootstrap`, `heroui`, NULL) | Relevante si `render_mode == ui_framework`. |
| `widget_type` | Enum | Uno de `table`, `bar_chart`, `line_chart`, `pie_chart`, `kpi`, `scatter_plot`, `heatmap`, `area_chart`. |
| `selection_source` | Enum (`deterministic`, `user_preference`, `fallback`) | Cómo se eligió `widget_type`. |
| `bindings` | Object | Mapping de columnas a roles visuales (x, y, series, value). Estructura depende del `widget_type`. |
| `visual_options` | Object | Título, subtítulos, etiquetas de ejes, formato de columnas. Opcional. |
| `code` | Object (NULL) | Presente si `render_mode == free_code` o `ui_framework`. Contiene `{ html, css, js }` listos para inyectar en el iframe. NULL si `widget_type == table` en modo `fallback` (el runtime usa el renderer nativo). |
| `data_reference` | Object | `{ extraction_id, columns, rows }` — se inyectan por postMessage, NO se serializan dentro de `code`. |
| `truncation_badge` | Boolean | Hereda `truncated` de la extracción; el runtime lo refleja visualmente. |
| `generated_by_model` | String | Alias del modelo que generó el código. `"deterministic"` si es fallback puro. |
| `generated_at` | ISO-8601 UTC | Timestamp. |

**Ciclo de vida**: construida por `WidgetArchitectService` en el backend, serializada dentro de `ChatResponse.widget_spec`, consumida por el frontend y descartada al cambiar de sesión. No se persiste.

---

### CanvasState

Estado actual del panel derecho por sesión, vive en el cliente (React state, NO en backend).

| Campo | Tipo | Descripción |
|---|---|---|
| `session_id` | String | Sesión actual. |
| `current_widget_spec` | `WidgetSpec \| null` | Widget visible. |
| `loading_stage` | Enum (`idle`, `generating`, `bootstrapping`, `ready`, `error`) | Estado de carga visible. |
| `last_error` | Object (NULL) | `{ code, message }` si el último render falló. |
| `previous_widget_spec` | `WidgetSpec \| null` | Se mantiene visible durante la generación del siguiente (FR-014). |

**Ciclo de vida**: puro estado React en el componente `CanvasPanel`. Se reinicia al recargar la página.

---

### WidgetGenerationTrace

Extensión del `AgentTrace` ya introducido por Feature 003. Se adjunta al mismo mensaje del chat que contiene la `DataExtraction`, complementando el trace existente con información del Agente Generador.

| Campo | Tipo | Descripción |
|---|---|---|
| `trace_id` | UUID | Identificador. |
| `extraction_id` | UUID | Liga con la extracción origen. |
| `widget_id` | UUID (NULL) | Si se generó una WidgetSpec exitosa. |
| `widget_type_attempted` | Enum (NULL) | Tipo intentado (o `NULL` si falló antes de decidir). |
| `status` | Enum (`success`, `fallback`, `error`) | Resultado. |
| `message` | String | Mensaje legible en español. |
| `generated_by_model` | String (NULL) | Modelo LLM usado; NULL si fallback determinístico. |
| `generation_ms` | Integer | Latencia del agente. |
| `render_ms` | Integer (NULL) | Latencia desde `widget:init` hasta `widget:ready`; NULL si falló en backend. |
| `error_code` | Enum (`GENERATOR_TIMEOUT`, `SPEC_INVALID`, `RENDER_TIMEOUT`, `RENDER_ERROR`, `UNKNOWN`, NULL) | Presente solo si `status != success`. |
| `generated_at` | ISO-8601 UTC | Timestamp. |

**Integración**: se anida en el mismo campo `ChatResponse.trace` que Feature 003, bajo una sub-estructura opcional `widget_generation`. El componente `AgentTraceBlock` del frontend se extiende para mostrar ambos bloques de forma contigua.

**Ciclo de vida**: memoria, vida igual al historial del chat.

---

## Extensiones a contratos existentes

### `ChatResponse` (Feature 003)

Se extiende de forma **retrocompatible**:

```python
class ChatResponse(BaseModel):
    message: Message
    extraction: DataExtraction | None = None
    trace: AgentTrace | None = None
    widget_spec: WidgetSpec | None = None           # NUEVO
    render_mode_profile: RenderModeProfileRef | None = None  # NUEVO (informativo)
```

El frontend existente ignora los campos nuevos sin error (Pydantic `extra='allow'` en el cliente TS). Clientes que soporten la feature consumen `widget_spec` y lo pasan a `CanvasPanel`.

### `AgentTrace` (Feature 003)

Se agrega un sub-objeto opcional:

```python
class AgentTrace(BaseModel):
    # ... campos existentes ...
    widget_generation: WidgetGenerationTrace | None = None  # NUEVO
```

---

## Relaciones

```text
UserSession (Feature 003, persistida)
  ├── rag_enabled
  └── session_id ──── RenderModeProfile (nueva, persistida)
                        ├── mode
                        └── ui_library

DataExtraction (memoria, Feature 003)
  └── extraction_id ──── WidgetSpec (memoria, nueva)
                            ├── widget_id
                            ├── widget_type
                            └── code

AgentTrace (memoria, Feature 003)
  └── widget_generation ──── WidgetGenerationTrace (memoria, nueva)

ChatResponse (extendida)
  ├── message
  ├── extraction
  ├── trace
  ├── widget_spec            ← nuevo
  └── render_mode_profile    ← nuevo
```

---

## Resumen de cambios a `joi_app.db`

| Tabla | Cambio |
|---|---|
| `user_sessions` | Sin cambios (heredada de Feature 003). |
| `render_mode_profiles` | **Nueva**, ver esquema arriba. |
| `data_source_connections` | Sin cambios (heredada de Feature 001). |
