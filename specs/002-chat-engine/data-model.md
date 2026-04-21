# Data Model: Chat Engine & Hybrid Triage

**Feature Branch**: `002-chat-engine`

## Entities

### `Message` (Pydantic Model / Posible Tabla Temporal en SQLite)
Representa un mensaje individual dentro de una sesión de chat.

- `id`: UUID (Primary Key)
- `session_id`: UUID (Relación a la sesión del usuario)
- `role`: Enum (`user`, `assistant`, `system`)
- `content`: Text
- `created_at`: Timestamp

*Nota:* Dado que los historiales son efímeros en esta fase según el spec, se manejarán principalmente en memoria o usando `ChatMessageHistory` de LangChain asociado a un `session_id` temporal, en lugar de guardarlos permanentemente en disco.

### `TriageResult` (Pydantic Model - Internal)
Representa el resultado del motor de triage (no se persiste).

- `intent_type`: Enum (`simple`, `complex`)
- `confidence`: Float (0.0 a 1.0)
- `matched_pattern`: String (Opcional, para debug si fue por regex)
- `suggested_route`: String (ej. 'direct_response', 'agent_pipeline')
