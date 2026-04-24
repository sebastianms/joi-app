# API Contracts: Feature 005

**Base URL**: `/api` (igual al resto del backend).
**Auth**: header `X-Joi-Session-Id` (mismo contrato de ADL-014).
**Errores**: formato estándar `{ error: {code, message, details?} }`.

---

## Colecciones

### `POST /api/collections`
Crear colección.
```json
// Request
{ "name": "Ventas Q1" }
// Response 201
{ "id": "uuid", "name": "Ventas Q1", "widget_count": 0, "created_at": "..." }
```
Errores: `409 DUPLICATE_NAME`, `422 NAME_REQUIRED`.

### `GET /api/collections`
Lista.
```json
// Response 200
[{ "id": "...", "name": "...", "widget_count": 3, "updated_at": "..." }]
```

### `PATCH /api/collections/{id}`
Renombrar. Body `{ "name": "…" }`. Errores: `404`, `409`.

### `DELETE /api/collections/{id}`
Elimina la colección; los widgets asociados permanecen (los registros en `collection_widgets` caen por cascade).

### `POST /api/collections/{id}/widgets`
Asociar widgets. Body `{ "widget_ids": ["…"] }`. Response 200 `{ "added": N, "skipped": M }` (skipped = ya presentes).

### `DELETE /api/collections/{id}/widgets/{widget_id}`
Desasociar. 204.

---

## Widgets guardados

### `POST /api/widgets/{id}/save`
Marca `is_saved=true`, asigna `display_name` y múltiples colecciones.
```json
// Request
{ "display_name": "Ventas Q1 por región", "collection_ids": ["c1","c2"] }
// Response 200
{ "widget": {...}, "collection_ids": ["c1","c2"] }
```
Errores: `409 DUPLICATE_DISPLAY_NAME`, `422 WIDGET_NOT_SAVEABLE` (widget con error), `404`.

### `DELETE /api/widgets/{id}/save`
Revierte a no-persistido (remueve de todas las colecciones; si está en un dashboard, 409).

### `GET /api/widgets?is_saved=true`
Lista de widgets guardados de la sesión (paginado).

---

## Dashboards

### `POST /api/dashboards`
```json
// Request
{ "name": "Resumen ejecutivo" }
// Response 201
{ "id": "...", "name": "...", "items": [], "created_at": "..." }
```

### `GET /api/dashboards`
Lista resumida.

### `GET /api/dashboards/{id}`
Incluye `items` completos con posición y referencia al widget hidratado.

### `PATCH /api/dashboards/{id}`
Renombrar. `{ "name": "…" }`.

### `DELETE /api/dashboards/{id}`
Cascade sobre items. Widgets subyacentes permanecen.

### `PATCH /api/dashboards/{id}/layout`
Actualiza posiciones en batch.
```json
// Request
{ "items": [
  { "widget_id": "...", "grid_x": 0, "grid_y": 0, "width": 6, "height": 4 },
  ...
]}
// Response 200: dashboard actualizado
```
Valida no-solapamiento y widths 1..12. Errores: `422 LAYOUT_INVALID`.

### `POST /api/dashboards/{id}/items`
Agregar widget existente. `{ "widget_id": "…", "grid_x":…, "grid_y":…, "width":…, "height":… }`. Errores: `409 WIDGET_ALREADY_IN_DASHBOARD`, `422 WIDGET_NOT_SAVED`.

### `DELETE /api/dashboards/{id}/items/{widget_id}`
Remove item.

---

## Vector store config (BYO)

### `POST /api/vector-store/validate`
Valida credenciales sin persistir.
```json
// Request
{ "provider": "pinecone", "connection_params": { "api_key": "…", "index_name": "joi-cache", "environment": "us-east1-gcp" } }
// Response 200
{ "valid": true, "provider": "pinecone", "latency_ms": 180 }
// Response 422
{ "error": { "code": "VECTOR_STORE_UNREACHABLE", "message": "…", "details": {...} } }
```

### `POST /api/vector-store/config`
Upsert de la config. Body idéntico a validate. Reemplaza cualquier config previa de la sesión. Response 200 `{ provider, is_default: false, validated_at }`.

### `GET /api/vector-store/config`
Devuelve la config activa (sin credenciales). Si no hay, responde `{ provider: "qdrant", is_default: true }`.

### `DELETE /api/vector-store/config`
Resetea al default (Qdrant interno). El caché previo en el provider del usuario NO se migra.

### `GET /api/vector-store/health`
Estado actual: `{ provider, healthy: true|false, last_check: "…" }`. Se invoca en el health endpoint global.

---

## Widget cache (búsqueda y reuso)

> Contratos expuestos principalmente para debugging y para el flujo de reuso manual. La búsqueda automática ocurre dentro del pipeline `/chat` y devuelve `cache_suggestion` inline.

### `POST /api/widget-cache/search`
```json
// Request
{ "prompt": "ventas mensuales por región 2025", "connection_id": "c1" }
// Response 200
{ "candidates": [
  { "id":"…", "widget_id":"…", "display_name":"…", "score": 0.91, "widget_type":"bar_chart", "created_at":"…" }
]}
```

### `POST /api/widget-cache/{id}/reuse`
Clona el widget cacheado como si fuera una nueva generación, re-ejecuta la query de datos contra la conexión actual.
```json
// Response 200
{ "widget": {...}, "source": "cache", "original_cache_entry_id": "…" }
```
Efectos: `hit_count += 1`, `last_used_at = now()`.

### `DELETE /api/widget-cache/{id}`
Invalidación manual (`invalidated_at = now()` + removal del point en el provider).

---

## Extensión del endpoint existente `POST /api/chat`

Respuesta enriquecida con campo opcional `cache_suggestion`:
```json
{
  "reply": "...",
  "agent_trace": {...},
  "widget_generation_trace": {...},
  "cache_suggestion": {
    "cache_entry_id": "…",
    "widget_id": "…",
    "display_name": "Ventas Q1 por región",
    "widget_type": "bar_chart",
    "score": 0.91,
    "preview_thumbnail_url": "/api/widgets/…/thumbnail"
  }
}
```
Flag de request `{ "skip_cache": true }` fuerza generación ignorando el caché (respaldando FR-014 / botón "Generar uno nuevo").

---

## Triage hook para US4 (recuperación por nombre)

No expone endpoint nuevo — se integra dentro del pipeline de `/api/chat`. Cuando el triage detecta intención "muéstrame X":
- Se busca por `display_name` fuzzy en `widgets WHERE is_saved=TRUE AND session_id=…`.
- Si hit único → response incluye `recovered_widget: {...}` y el canvas lo renderiza sin Agente Generador.
- Si múltiples → response incluye `candidates: [{id, display_name}, ...]` y `reply` con un mensaje tipo "¿Cuál quieres ver?".
