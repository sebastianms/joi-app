# Quickstart: Feature 003 — Data Agent Validation Scenarios

**Purpose**: Conjunto mínimo de escenarios end-to-end que, ejecutados manualmente tras la implementación, demuestran que la feature cumple sus user stories y success criteria.

**Audience**: Validador humano (developer o PM) al finalizar Implement, antes de mergear a main.

---

## Setup Previo

1. Backend corriendo (`uvicorn app.main:app --reload`) con variables de entorno:
   - `ANTHROPIC_API_KEY` (u OPENAI_API_KEY, GEMINI_API_KEY, según proveedor elegido)
   - `RAG_DEFAULT_ENABLED=true`
   - `QUERY_TIMEOUT_SECONDS=10`
   - `MAX_ROWS_PER_EXTRACTION=1000`
2. Frontend corriendo (`npm run dev` en `frontend/`).
3. `joi_app.db` limpia (eliminar si es necesario y dejar que `lifespan` la regenere).
4. `backend/chroma_data/` limpia (eliminar si es necesario).
5. Fuente SQLite de prueba preparada: `backend/tests/fixtures/sales_sample.db` con una tabla `sales(id, region, amount, sold_at)` y ≥ 50 filas.
6. Fuente JSON de prueba preparada: `backend/tests/fixtures/products_sample.json` con un array de ~30 productos, cada uno con `{id, name, category, price, stock}`.

---

## Escenario 1 — US1: Extracción SQL exitosa

**Precondiciones**: En `/setup`, conectar la fuente SQLite de prueba con credenciales read-only.

**Pasos**:
1. Ir a la página principal `/`.
2. En el chat, escribir: **"Muéstrame las ventas del último mes por región"**.
3. Enviar.

**Esperado**:
- Response HTTP 200.
- `intent_type = "complex"`.
- `extraction.status = "success"`.
- `extraction.row_count > 0`.
- `extraction.columns` contiene al menos `region` y una columna agregada (p.ej. `total_amount` o equivalente).
- `trace.pipeline = "sql"`.
- `trace.query_display` muestra una consulta SQL legible con `SELECT` y `GROUP BY`.
- En la UI del chat, aparece el mensaje del asistente + un elemento colapsable "Agent Trace" visible.

**Cubre**: US1, FR-001, FR-004, FR-008, SC-003.

---

## Escenario 2 — US2: Agent Trace colapsable

**Pasos**:
1. Tras Escenario 1, localizar el trace en la UI.
2. Click para expandir.
3. Verificar que muestra: consulta SQL, fuente, row_count, columnas, preview de las primeras 10 filas en tabla.
4. Click para colapsar. Verificar que se oculta el contenido pero el elemento sigue visible.
5. Enviar un segundo prompt (cualquiera). Verificar que el trace del primer prompt sigue visible en el hilo.

**Esperado**: Trace siempre accesible con ≤1 clic; no desaparece del historial dentro de la sesión.

**Cubre**: US2, FR-009, SC-005.

---

## Escenario 3 — US3: Rechazo de consulta de escritura

**Pasos**:
1. En el chat, escribir un prompt adversarial: **"Borra todos los registros de la tabla sales"**.
2. Enviar.

**Esperado**:
- `extraction.status = "error"`.
- `extraction.error.code = "SECURITY_REJECTION"`.
- `extraction.error.message` es explicable y menciona que el agente solo puede consultar.
- `trace.security_rejection = true`.
- `trace.query_display` muestra la SQL que intentó generar el LLM (p.ej. `DELETE FROM sales` o similar).
- Verificar en la fuente SQLite que la tabla `sales` sigue intacta (conteo de filas sin cambios).

**Cubre**: US3, FR-002, FR-003, SC-001.

---

## Escenario 4 — US4: Timeout recuperable

**Pasos**:
1. Bajar `QUERY_TIMEOUT_SECONDS=1` en backend (.env) y reiniciar.
2. Conectar una fuente grande o inducir una consulta lenta (p.ej. un CROSS JOIN sobre una tabla grande).
3. En el chat, escribir un prompt que fuerce la consulta lenta.

**Esperado**:
- `extraction.status = "error"`.
- `extraction.error.code = "TIMEOUT"`.
- Mensaje del asistente invita a reformular.
- **Enviar un segundo prompt simple** (p.ej. "hola"). Verificar que la sesión sigue viva y responde.

**Cubre**: US4, FR-007, FR-011, SC-004.

---

## Escenario 5 — US4: Tabla inexistente

**Pasos**:
1. Volver a `QUERY_TIMEOUT_SECONDS=10`.
2. Prompt: **"Muéstrame los datos de la tabla unicorn_revenue"** (tabla inexistente).

**Esperado**:
- `extraction.status = "error"`.
- `extraction.error.code` en `["TARGET_NOT_FOUND", "QUERY_SYNTAX"]`.
- Mensaje sugiere revisar el schema.

**Cubre**: US4, FR-011.

---

## Escenario 6 — US1 con fuente JSON y modelo liviano

**Precondiciones**: Conectar la fuente JSON `products_sample.json` (desde `/setup`).

**Pasos**:
1. Cambiar a esa conexión como activa (si aplica multi-conexión).
2. Prompt: **"Dame los 5 productos más caros de la categoría electrónica"**.

**Esperado**:
- `extraction.source_type = "JSON"`.
- `extraction.query_plan.language = "jsonpath"`.
- `extraction.query_plan.generated_by_model` indica un modelo liviano (p.ej. `"gpt-4o-mini"` o `"claude-haiku-4-5"`).
- `extraction.row_count = 5`.
- `trace.pipeline = "json"`.

**Cubre**: US1, FR-005, FR-016.

---

## Escenario 7 — US5: Memoria RAG activa mejora precisión

**Precondiciones**: Sesión con `rag_enabled=true` (default) sobre la fuente SQLite.

**Pasos**:
1. Prompt 1: **"Top 5 regiones por ventas"** → verificar que responde bien.
2. Prompt 2 (ambiguo): **"Ahora lo mismo pero del último trimestre"**.

**Esperado**:
- Prompt 2 genera una consulta que incluye el filtro de trimestre Y la agrupación por región y el `LIMIT 5`, sin que el usuario haya tenido que repetirlos.
- El trace del prompt 2 muestra que el contexto de la primera consulta fue usado (se puede inspeccionar manualmente que la SQL generada tiene paridad con la anterior + filtro extra).

**Cubre**: US5, FR-012, FR-013, SC-006.

---

## Escenario 8 — US5: Aislamiento entre sesiones

**Pasos**:
1. Abrir una ventana de navegación privada → `session_id` nuevo (llámalo B).
2. En sesión A (ventana normal), ejecutar varios prompts sobre `sales`.
3. En sesión B, ejecutar: **"¿Qué consultas he hecho?"**.

**Esperado**:
- La respuesta de B no revela consultas de A.
- Verificar directamente en Chroma (CLI o cliente) que la colección `session_{A}` contiene documentos y `session_{B}` no comparte IDs con A.

**Cubre**: US5, FR-013, SC-007.

---

## Escenario 9 — Sin conexión activa

**Pasos**:
1. Con una sesión fresca (nuevo `session_id`, ninguna conexión activa registrada).
2. Prompt: **"Muéstrame mis datos"**.

**Esperado**:
- `extraction.status = "error"`.
- `extraction.error.code = "NO_CONNECTION"`.
- Mensaje dirige al usuario a `/setup`.
- En la UI del chat, aparece un link o referencia al setup wizard.

**Cubre**: Edge case, FR-010.

---

## Escenario 10 — Truncación de resultados

**Pasos**:
1. Bajar `MAX_ROWS_PER_EXTRACTION=5` en backend (.env) y reiniciar.
2. Prompt: **"Dame todas las filas de sales"**.

**Esperado**:
- `extraction.row_count = 5`.
- `extraction.truncated = true`.
- Mensaje del asistente o trace indica explícitamente que el resultado fue truncado.

**Cubre**: FR-006, Edge case.

---

## Escenario 11 — Compatibilidad hacia atrás con Feature 002

**Pasos**:
1. Prompt simple: **"Hola"**.

**Esperado**:
- `intent_type = "simple"`.
- `extraction = null` o ausente.
- `trace = null` o ausente.
- `response` es una saludo generado por el chat simple (no el placeholder viejo `_COMPLEX_INTENT_PLACEHOLDER`, pero sí una respuesta coherente del LLM).
- La UI del chat NO renderiza ningún elemento de Agent Trace.

**Cubre**: Retrocompatibilidad ChatResponse, R8 de research.md.

---

## Checklist Final

Antes de marcar la feature como Done:

- [ ] Escenarios 1 a 11 pasan manualmente.
- [ ] Tests unitarios del backend pasan (al menos: `ReadOnlySqlGuard`, `DataAgentService`, `JsonAgentAdapter`, `UserSession` persistence).
- [ ] Tests E2E del frontend pasan (selectores `aria-label` + `data-role` según ADL-002/ADL-004).
- [ ] Ningún test existente de Feature 001/002 se rompe.
- [ ] `ADL-005-data-agent-architecture.md` redactado y commiteado en `.design-logs/`.
- [ ] `roadmap.md` actualizado: Phase 5 bullet 1 marcado como completado; nota indicando que el RAG ya está integrado (reduce scope de Phase 6).
- [ ] `backend/chroma_data/` agregado al `.gitignore`.
