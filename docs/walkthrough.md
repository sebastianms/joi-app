# Walkthrough

Historial de slices entregados, con referencia a la spec SDD correspondiente.

## Feature 001 — Setup Wizard & Data Connectors
Estado: completada. Ruta: `/setup`.

Permite al usuario configurar fuentes de datos (PostgreSQL, MySQL, SQLite, JSON) mediante un asistente con tabs. Cada formulario valida inputs en el cliente (Zod) y confirma la conexión contra el backend antes de persistirla.

## Feature 002 — Chat Engine & Hybrid Triage
Estado: completada.

### Backend
- `POST /api/chat/messages` — Endpoint de conversación.
- `ChatManagerService` — Mantiene el historial por `session_id` en memoria y orquesta triage + LLM.
- `TriageEngineService` — Capa determinística (regex + keywords) que clasifica la intención como `simple` o `complex` antes de llamar al LLM. Las intenciones complejas devuelven un placeholder hasta que se implemente el pipeline de agentes (Feature 003).
- `EchoLLMGateway` — Implementación stub del gateway LLM; la abstracción `LLMGateway` permite sustituirlo por un proveedor real (OpenAI, Anthropic, Gemini) sin tocar el manager.

### Frontend
- Layout principal dual: `ChatPanel` a la izquierda, canvas placeholder a la derecha. El setup wizard se mueve a `/setup` con enlace desde el header.
- `useChat` (hook) — Gestiona mensajes, estado de envío, errores y genera `session_id` con `crypto.randomUUID`.
- `MessageInput` — Input controlado con submit vía click o Enter.
- `MessageList` — Burbujas diferenciadas usuario/asistente, auto-scroll y typing indicator. Roles ARIA (`log`, `aria-live`) para accesibilidad.
- `ChatPanel` — Ensambla hook + lista + input, muestra alertas de error.

### Tests
- `backend/tests/unit/test_chat_models.py`, `test_triage_engine.py` — unitarios.
- `backend/tests/integration/test_chat_endpoint.py` — integración del endpoint.
- `frontend/e2e/chat-basic.spec.ts` — flujos e2e simple y complejo.

### Limitaciones
- El historial es efímero (en memoria del proceso). Se perderá al reiniciar el backend o refrescar el frontend.
- Intenciones complejas aún no invocan pipeline real de agentes; devuelven placeholder.

## Feature 003 — Data Agent
Estado: completada (US1–US4). Ruta: `POST /api/chat/messages` (mismo endpoint de chat).

### Flujo end-to-end

1. El usuario envía un mensaje con intención compleja (p.ej. "muéstrame las ventas por mes").
2. `TriageEngineService` clasifica la intención como `complex`.
3. `DataAgentService` resuelve la conexión activa para la sesión y enruta al adapter según el tipo de fuente:
   - **SQL** (`SqlAgentAdapter`): genera SQL con LiteLLM → valida con `ReadOnlySqlGuard` → ejecuta con SQLAlchemy.
   - **JSON** (`JsonAgentAdapter`): genera un JSONPath con LiteLLM → ejecuta con `jsonpath-ng`.
4. El resultado se empaqueta como `DataExtraction` (contrato `data_extraction.v1`) y un `AgentTrace`.
5. `ChatManagerService` formatea el response textual y devuelve `extraction` + `trace` en el payload HTTP.
6. El frontend renderiza un `AgentTraceBlock` colapsable debajo del mensaje del asistente.

### Seguridad
`ReadOnlySqlGuard` bloquea cualquier SQL que no sea `SELECT`/`WITH`/`SHOW`/`EXPLAIN`. Si el LLM genera una sentencia de mutación, el trace registra `security_rejection=true` y la fuente no se modifica.

### Manejo de errores
Los errores (sin conexión, tabla inexistente, timeout, rechazo de seguridad) nunca levantan una excepción HTTP: van dentro de `extraction.error` con `status="error"` y HTTP 200. La sesión permanece funcional después de cualquier error.

### Escenarios verificados
Los escenarios 1–5 y 9–11 del `specs/003-data-agent/quickstart.md` están cubiertos por tests automatizados. Los escenarios de US5 (RAG) quedan pendientes hasta que se reactive esa User Story.

### Tests
- `backend/tests/unit/` — `test_sql_agent_adapter.py`, `test_json_agent_adapter.py`, `test_chat_manager.py`, `test_read_only_sql_guard.py`, `test_extraction_models.py`.
- `backend/tests/integration/` — `test_chat_with_data_agent.py`, `test_security_rejection.py`, `test_error_recovery.py`.
- `frontend/e2e/` — flujo "prompt complejo → Agent Trace colapsado → expandir".

### Limitaciones
- US5 (memoria RAG activable por sesión) diferida post-MVP. `UserSession.rag_enabled` existe en el modelo pero no está activo. Ver ADL-010.
- La capa probabilística del triage (LLM classifier) sigue diferida; el clasificador actual es determinístico (regex + keywords).

## Próximo slice — Phase 5 continuación
Agente Arquitecto/Generador de widgets, sanitización e inyección dinámica en el canvas derecho.
