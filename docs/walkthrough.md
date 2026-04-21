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

## Próximo slice — Feature 003 (Phase 5 del roadmap)
Multi-Agent Pipeline & Rendering Canvas: agente de datos (Text-to-SQL), agente arquitecto/generador de widgets, sanitización e inyección dinámica en el canvas derecho.
