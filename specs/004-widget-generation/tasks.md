# Tasks: Feature 004 — Widget Generation & Canvas Rendering

**Branch**: `004-widget-generation` | **Date**: 2026-04-22 | **Status**: In Progress — US1 next (T101)

> Formato por task: `- [ ] T### [P?] [US?] Descripción con ruta exacta`.
> `[P]` = paralelizable con tareas hermanas (distinto archivo, sin dependencias).
> `[US1..4]` = user story a la que sirve (solo en el bloque de user stories).
>
> **Checkpoints de validación obligatoria (Phase 5)**: tras cada task, marcarla `[/]` en progreso, esperar aprobación del usuario, luego `[x]`.

---

## Setup (bloque inicial)

- [x] T001 Añadir `recharts` al frontend: `cd frontend && npm install recharts` (verificar que no rompe el lockfile actual).
- [x] T002 [P] Crear directorio del runtime bundle: `frontend/src/lib/widget-runtime/` (vacío, placeholder `.gitkeep`).
- [x] T003 [P] Crear directorio de contracts iframe: `frontend/src/types/` ya existe — añadir `widget.ts`, `render-mode.ts`, `postmessage.ts` como archivos vacíos con `// generated from specs/004-widget-generation/contracts/*`.
- [x] T004 [P] Añadir variable de entorno `LLM_MODEL_WIDGET` al `backend/.env.example` con comentario apuntando a R6 de `specs/004-widget-generation/research.md`.
- [x] T005 [P] Añadir `frontend/public/widget-runtime.bundle.js` a `.gitignore` (output del build dedicado; nunca se commitea).
- [x] T006 [P] Crear directorio `backend/app/services/widget/` y `backend/app/services/widget/manifests/` con `__init__.py`.
- [x] T007 Añadir script `build:widget-runtime` a `frontend/package.json` que empaquete `src/lib/widget-runtime/entry.tsx` → `public/widget-runtime.bundle.js` (usa esbuild o el bundler ya disponible en el repo). Documentar el comando.

---

## Foundational (bloquean todas las user stories)

Estos elementos son prerequisito para cualquier flujo de US1–US4. **Completar antes de avanzar a user stories.**

- [x] T010 Definir `RenderModeProfile` Pydantic + `RenderModeProfileORM` (SQLAlchemy) en [backend/app/models/render_mode.py](backend/app/models/render_mode.py) siguiendo el esquema de [data-model.md](specs/004-widget-generation/data-model.md). Incluir validador que rechace `mode=design_system`.
- [x] T011 Registrar la tabla `render_mode_profiles` en el `Base.metadata` y asegurar que `main.lifespan()` la crea junto a las existentes.
- [x] T012 Implementar [backend/app/repositories/render_mode_repository.py](backend/app/repositories/render_mode_repository.py) con `get_or_create(session_id)` (default `ui_framework` + `shadcn`) y `update(session_id, profile)`.
- [x] T013 [P] Definir los modelos Pydantic `WidgetSpec`, `WidgetBindings`, `VisualOptions`, `WidgetCode`, `WidgetGenerationTrace` en [backend/app/models/widget.py](backend/app/models/widget.py). Validar con el schema `contracts/widget-spec-v1.schema.json` en tests.
- [x] T014 [P] Extender `AgentTrace` en [backend/app/models/extraction.py](backend/app/models/extraction.py) con campo opcional `widget_generation: WidgetGenerationTrace | None = None`.
- [x] T015 [P] Extender `ChatResponse` en [backend/app/models/chat.py](backend/app/models/chat.py) con campos opcionales `widget_spec: WidgetSpec | None = None` y `render_mode_profile: RenderModeProfile | None = None`. Serializar con `exclude_none=True` (ADL-012).
- [x] T016 Añadir `Purpose="widget"` al routing de [backend/app/services/litellm_client.py](backend/app/services/litellm_client.py), leyendo `LLM_MODEL_WIDGET` con fallback al default. No romper purposes existentes (`sql`, `json`, `chat`).
- [x] T017 [P] Añadir los 3 manifests estáticos en [backend/app/services/widget/manifests/shadcn.md](backend/app/services/widget/manifests/shadcn.md), [bootstrap.md](backend/app/services/widget/manifests/bootstrap.md), [heroui.md](backend/app/services/widget/manifests/heroui.md) (≤ 2KB cada uno, auditar en review).
- [x] T018 [P] Crear tipos TypeScript del contrato en [frontend/src/types/widget.ts](frontend/src/types/widget.ts), [render-mode.ts](frontend/src/types/render-mode.ts), [postmessage.ts](frontend/src/types/postmessage.ts) generados/sincronizados con los schemas JSON.

---

## User Story 1 — Visualización por defecto desde extracción (P1)

Ciclo completo "extracción exitosa → widget visible". Modelos → servicios → endpoint → runtime iframe → canvas.

- [x] T101 [US1] Implementar selector determinístico en [backend/app/services/widget/type_selector.py](backend/app/services/widget/type_selector.py) con las 7 reglas de R1 + fallback a `table`.
- [x] T102 [P] [US1] Implementar [backend/app/services/widget/applicability.py](backend/app/services/widget/applicability.py): validador que dado un `widget_type` + `data_extraction.columns/rows` devuelva compatible/incompatible + alternativas válidas.
- [x] T103 [P] [US1] Implementar [backend/app/services/widget/fallback_builder.py](backend/app/services/widget/fallback_builder.py): construye `WidgetSpec` tipo `table` desde una `DataExtraction` sin invocar LLM (R8).
- [ ] T104 [US1] Implementar [backend/app/services/widget/prompt_builder.py](backend/app/services/widget/prompt_builder.py): ensambla system_prompt_base + manifest de la librería activa + target `widget_type` + descripción de datos. Prefix estable para prompt caching.
- [ ] T105 [US1] Implementar [backend/app/services/widget/generator.py](backend/app/services/widget/generator.py): recibe contexto, invoca LiteLLM con `Purpose="widget"`, parsea respuesta, valida contra `widget_spec.v1` schema, retorna `WidgetSpec` o error estructurado. Timeout configurable (default ~8s interno, distinto del iframe timeout).
- [ ] T106 [US1] Implementar fachada [backend/app/services/widget/architect_service.py](backend/app/services/widget/architect_service.py): orquesta (type_selector | applicability) → generator → fallback_builder. Emite `WidgetGenerationTrace` al AgentTrace. Inyectado por DI (ADL-011).
- [ ] T107 [US1] Integrar `architect_service` en [backend/app/services/chat_manager.py](backend/app/services/chat_manager.py): tras extracción con `status=success` Y `row_count > 0`, invocar arquitecto y adjuntar `widget_spec` al `ChatResponse`. Respetar FR-015 (no invocar si `status=error`).
- [x] T108 [P] [US1] Tests unitarios del selector: [backend/tests/unit/test_type_selector.py](backend/tests/unit/test_type_selector.py) — un caso por tipo del catálogo + fallback + row_count=0.
- [x] T109 [P] [US1] Tests unitarios de applicability: [backend/tests/unit/test_applicability.py](backend/tests/unit/test_applicability.py) — incompatibilidades (ej. heatmap con KPI) + alternativas sugeridas.
- [x] T110 [P] [US1] Tests unitarios de fallback_builder: [backend/tests/unit/test_fallback_builder.py](backend/tests/unit/test_fallback_builder.py) — verificar que tabla es determinística y no llama LLM.
- [ ] T111 [P] [US1] Tests unitarios del generador: [backend/tests/unit/test_widget_generator.py](backend/tests/unit/test_widget_generator.py) con LiteLLM mockeado (ADL-015): happy path, respuesta no parseable → error.
- [ ] T112 [P] [US1] Tests unitarios del architect: [backend/tests/unit/test_architect_service.py](backend/tests/unit/test_architect_service.py) — happy path, generator timeout → fallback, spec inválida → fallback.
- [ ] T113 [US1] Test integración: [backend/tests/integration/test_chat_with_widget.py](backend/tests/integration/test_chat_with_widget.py) — `POST /api/chat/messages` con prompt complejo retorna `ChatResponse` con `widget_spec` válida contra el schema.
- [ ] T120 [US1] Implementar runtime entry en [frontend/src/lib/widget-runtime/entry.tsx](frontend/src/lib/widget-runtime/entry.tsx): escucha `widget:init`, valida `protocol_version`, dispatch por `widget_type`, emite `widget:ready`/`widget:error`/`widget:resize`.
- [ ] T121 [P] [US1] Renderer `table` en [frontend/src/lib/widget-runtime/renderers/table.tsx](frontend/src/lib/widget-runtime/renderers/table.tsx).
- [ ] T122 [P] [US1] Renderer `bar_chart` en [renderers/bar-chart.tsx](frontend/src/lib/widget-runtime/renderers/bar-chart.tsx) usando Recharts.
- [ ] T123 [P] [US1] Renderer `line_chart` en [renderers/line-chart.tsx](frontend/src/lib/widget-runtime/renderers/line-chart.tsx).
- [ ] T124 [P] [US1] Renderer `pie_chart` en [renderers/pie-chart.tsx](frontend/src/lib/widget-runtime/renderers/pie-chart.tsx).
- [ ] T125 [P] [US1] Renderer `kpi` en [renderers/kpi.tsx](frontend/src/lib/widget-runtime/renderers/kpi.tsx).
- [ ] T126 [P] [US1] Renderer `scatter_plot` en [renderers/scatter.tsx](frontend/src/lib/widget-runtime/renderers/scatter.tsx).
- [ ] T127 [P] [US1] Renderer `heatmap` en [renderers/heatmap.tsx](frontend/src/lib/widget-runtime/renderers/heatmap.tsx) (SVG custom, R5).
- [ ] T128 [P] [US1] Renderer `area_chart` en [renderers/area-chart.tsx](frontend/src/lib/widget-runtime/renderers/area-chart.tsx).
- [ ] T129 [P] [US1] Adaptador shadcn en [frontend/src/lib/widget-runtime/adapters/shadcn.tsx](frontend/src/lib/widget-runtime/adapters/shadcn.tsx) (wrappers de Card/Table/etc. sin dependencia de red).
- [ ] T130 [P] [US1] Adaptador bootstrap en [adapters/bootstrap.tsx](frontend/src/lib/widget-runtime/adapters/bootstrap.tsx) (clases CSS inline).
- [ ] T131 [P] [US1] Adaptador heroui en [adapters/heroui.tsx](frontend/src/lib/widget-runtime/adapters/heroui.tsx).
- [ ] T132 [US1] Verificar el build `npm run build:widget-runtime` produce `public/widget-runtime.bundle.js` < 300KB gzipped (reporte en PR).
- [ ] T133 [US1] Implementar hook [frontend/src/hooks/use-canvas.ts](frontend/src/hooks/use-canvas.ts): maneja `CanvasState`, monta iframe con `srcdoc`, envía `widget:init`, escucha `ready/error/resize`, aplica timeout de 4s.
- [ ] T134 [US1] Implementar [frontend/src/components/canvas/widget-frame.tsx](frontend/src/components/canvas/widget-frame.tsx): `<iframe sandbox="allow-scripts" srcdoc={...}>` con CSP inyectada (R4). `aria-label`/`data-role` estables (ADL-002).
- [ ] T135 [US1] Implementar [frontend/src/components/canvas/widget-loading.tsx](frontend/src/components/canvas/widget-loading.tsx): skeleton para `generating` y `bootstrapping`.
- [ ] T136 [P] [US1] [frontend/src/components/canvas/widget-empty-state.tsx](frontend/src/components/canvas/widget-empty-state.tsx) para `row_count=0`.
- [ ] T137 [P] [US1] [frontend/src/components/canvas/truncation-badge.tsx](frontend/src/components/canvas/truncation-badge.tsx) (también usado en US1 cuando la extracción viene truncada — FR-013).
- [ ] T138 [US1] Implementar [frontend/src/components/canvas/canvas-panel.tsx](frontend/src/components/canvas/canvas-panel.tsx): orquesta `use-canvas`, renderiza `WidgetFrame | WidgetLoading | WidgetEmptyState | WidgetErrorBanner` según estado.
- [ ] T139 [US1] Reemplazar placeholder en [frontend/src/app/page.tsx](frontend/src/app/page.tsx) por `<CanvasPanel />`. Conectar con el `useChat` para recibir `widgetSpec` del último mensaje con extracción.
- [ ] T140 [US1] Extender [frontend/src/hooks/use-chat.ts](frontend/src/hooks/use-chat.ts) con campo `widgetSpec` opcional en `Message`.
- [ ] T141 [US1] Extender [frontend/src/components/chat/agent-trace-block.tsx](frontend/src/components/chat/agent-trace-block.tsx) con sección `widget_generation` contigua al trace del Data Agent.
- [ ] T142 [US1] Ejecutar **Escenario 1** de `quickstart.md` manual en navegador; reportar screenshot + latencia p95 del bootstrap.

---

## User Story 2 — Preferencia explícita del usuario (P2)

Detección de preferencia en el chat + regeneración sin re-ejecutar la extracción.

- [ ] T201 [US2] Extender [backend/app/services/triage_engine.py](backend/app/services/triage_engine.py) con pass adicional que busque las 8 regex de R10 cuando el intent es `complex` o hay extracción previa en sesión. Devolver `preferred_widget_type` en el `TriageResult`.
- [ ] T202 [P] [US2] Tests unitarios del triage extendido: [backend/tests/unit/test_triage_widget_preference.py](backend/tests/unit/test_triage_widget_preference.py) — 8 tipos + múltiples matches → None + frases en español/inglés.
- [ ] T203 [US2] En [architect_service.py](backend/app/services/widget/architect_service.py), cuando `preferred_widget_type` presente: aplicar `applicability` sobre la extracción previa. Si compatible → generar con ese tipo (`selection_source=user_preference`). Si incompatible → NO generar widget, emitir mensaje explicativo en el chat + alternativas (FR-006).
- [ ] T204 [US2] Mantener la **misma** `extraction_id` en el nuevo `WidgetSpec` (reutilizar la extracción de la sesión). Verificar que no se invoca al Data Agent de nuevo.
- [ ] T205 [US2] En [chat_manager.py](backend/app/services/chat_manager.py): ruta "preferencia sobre extracción previa" que toma la última `DataExtraction` de la sesión (en memoria) y la pasa al architect sin llamar al Data Agent.
- [ ] T206 [P] [US2] Test integración: invocar dos `POST /api/chat/messages` en secuencia (primero prompt de datos, luego "prefiero tabla") y verificar mismo `extraction_id`, distinto `widget_id`, `selection_source=user_preference`.
- [ ] T207 [P] [US2] Test integración para caso incompatible: KPI previo + "muéstramelo como heatmap" → respuesta del chat explica y propone alternativas; el widget actual permanece.
- [ ] T208 [US2] Ejecutar **Escenarios 4 y 5** de `quickstart.md` manual; reportar latencia p95 del swap.

---

## User Story 3 — Aislamiento visual y de ejecución (P1)

Sandbox iframe + CSP + postMessage protocol + timeout 4s. Suite adversarial.

- [ ] T301 [US3] Verificar que [widget-frame.tsx](frontend/src/components/canvas/widget-frame.tsx) aplica exactamente `sandbox="allow-scripts"` (sin `allow-same-origin`, `allow-top-navigation`, etc.) y CSP definida en R4 dentro del `srcdoc` (meta tag).
- [ ] T302 [P] [US3] Verificar en [use-canvas.ts](frontend/src/hooks/use-canvas.ts) que TODO mensaje entrante del iframe pasa por un validador contra `postmessage-protocol.schema.json`; mensajes no conformes son descartados silenciosamente.
- [ ] T303 [P] [US3] Implementar timeout de bootstrap: si `widget:ready` no llega en 4000ms desde `widget:init`, dispatch → estado `error` con code `RENDER_TIMEOUT` y trigger de fallback (FR-008b).
- [ ] T304 [US3] Fixtures adversariales backend-side en [backend/tests/adversarial/test_widget_sandbox_specs.py](backend/tests/adversarial/test_widget_sandbox_specs.py): generan 5 `WidgetSpec` maliciosas (navegación global, cookie access, fetch externo, estilos globales, alert loop). Estas specs se exponen vía endpoint de test/debug para consumirlas desde Playwright.
- [ ] T305 [US3] Test E2E Playwright que inyecta cada spec adversarial y verifica: (a) la app principal no cambia, (b) ningún fetch externo, (c) `widget:error` se recibe con `code=RUNTIME_ERROR`, (d) el `WidgetGenerationTrace` refleja el fallo. Ubicación: [frontend/tests/e2e/widget-isolation.spec.ts](frontend/tests/e2e/widget-isolation.spec.ts).
- [ ] T306 [P] [US3] Test E2E del timeout de bootstrap: spec con bucle infinito → fallback tabular aparece en ≤ 5s. Ubicación: [frontend/tests/e2e/widget-timeout.spec.ts](frontend/tests/e2e/widget-timeout.spec.ts).
- [ ] T307 [US3] Ejecutar **Escenarios 6 y 7** de `quickstart.md`.

---

## User Story 4 — Errores no rompen la sesión (P2)

Fallback universal + error banner + continuidad del chat.

- [ ] T401 [US4] En [architect_service.py](backend/app/services/widget/architect_service.py), asegurar que CUALQUIER excepción del generador (timeout, parse error, schema invalid, LiteLLM 5xx) se captura y dispara `fallback_builder`. Nunca propaga al endpoint.
- [ ] T402 [P] [US4] En `WidgetGenerationTrace`, setear `status=fallback` + `error_code` apropiado (`GENERATOR_TIMEOUT`, `SPEC_INVALID`, `UNKNOWN`).
- [ ] T403 [US4] Implementar [frontend/src/components/canvas/widget-error-banner.tsx](frontend/src/components/canvas/widget-error-banner.tsx) para mostrar error contenido dentro del Canvas cuando `last_error` está presente (render error en el iframe, no fallas del generador — esas usan fallback tabular).
- [ ] T404 [US4] En [use-canvas.ts](frontend/src/hooks/use-canvas.ts): al recibir `widget:error`, preservar `previous_widget_spec` visible hasta que el usuario haga nuevo prompt (FR-014).
- [ ] T405 [P] [US4] Test integración: mock de LiteLLM devuelve respuesta no parseable → `ChatResponse.widget_spec.widget_type=table`, `selection_source=fallback`, chat response exitoso 200. Ubicación: [backend/tests/integration/test_chat_with_widget.py](backend/tests/integration/test_chat_with_widget.py) (extender).
- [ ] T406 [P] [US4] Test E2E Playwright: forzar mock generador fallido → tabla aparece → enviar nuevo prompt → widget normal aparece (sesión operativa). Ubicación: [frontend/tests/e2e/widget-fallback.spec.ts](frontend/tests/e2e/widget-fallback.spec.ts).
- [ ] T407 [US4] Ejecutar **Escenarios 3, 8, 9, 10** de `quickstart.md`.

---

## Setup Wizard — extensión (soporta US1–US2)

Paso nuevo "Framework visual" + endpoints `/api/render-mode/profile`. Se puede avanzar en paralelo con US1 porque no bloquea el flujo por defecto (lazy default).

- [ ] T501 Implementar endpoints [backend/app/api/endpoints/render_mode.py](backend/app/api/endpoints/render_mode.py): `GET /api/render-mode/profile?session_id=...` y `PUT /api/render-mode/profile`. Registrar el router en [backend/app/api/api.py](backend/app/api/api.py).
- [ ] T502 [P] Tests unitarios del repo: [backend/tests/unit/test_render_mode_repository.py](backend/tests/unit/test_render_mode_repository.py) — `get_or_create` idempotente, update, rechazo de `design_system`.
- [ ] T503 [P] Test integración del endpoint: [backend/tests/integration/test_render_mode_api.py](backend/tests/integration/test_render_mode_api.py) — GET default, PUT válido, PUT `design_system` → 400.
- [ ] T504 Implementar [frontend/src/components/setup-wizard/render-mode-step.tsx](frontend/src/components/setup-wizard/render-mode-step.tsx): 4 opciones (shadcn default seleccionada, Bootstrap, HeroUI, Design System deshabilitado con badge "próximamente"). Usa el endpoint PUT.
- [ ] T505 Insertar el step en el flujo del wizard ya existente (posterior a conexión de datos). Verificar que sesiones existentes siguen funcionando con el default lazy.
- [ ] T506 Test E2E Playwright del wizard: [frontend/tests/e2e/render-mode-wizard.spec.ts](frontend/tests/e2e/render-mode-wizard.spec.ts) — cambiar a Bootstrap → generar widget → `widget_spec.ui_library=bootstrap` verificable.
- [ ] T507 Ejecutar **Escenarios 11 y 12** de `quickstart.md`.

---

## Polish (cierre)

- [ ] T901 Redactar [.design-logs/ADL-016-widget-generation-architecture.md](.design-logs/ADL-016-widget-generation-architecture.md) consolidando R2, R3, R6.
- [ ] T902 [P] Redactar [.design-logs/ADL-017-canvas-iframe-sandbox.md](.design-logs/ADL-017-canvas-iframe-sandbox.md) consolidando R4, R5.
- [ ] T903 [P] Redactar [.design-logs/ADL-018-deterministic-widget-selector.md](.design-logs/ADL-018-deterministic-widget-selector.md) consolidando R1.
- [ ] T904 [P] Redactar [.design-logs/ADL-019-render-mode-profile-wizard.md](.design-logs/ADL-019-render-mode-profile-wizard.md) consolidando R7.
- [ ] T905 Actualizar [specs/roadmap.md](specs/roadmap.md): marcar bullets 2 y 3 de Fase 5 como completados, mover referencia a Feature 004.
- [ ] T906 [P] Añadir sección "Feature 004 — Widgets" al README con screenshot del Canvas y ejemplo de prompt → widget.
- [ ] T907 Ejecutar suite completa de tests: backend (unit + integration + adversarial) + frontend (unit + E2E). Reportar tiempos.
- [ ] T908 Verificar que las suites de Features 001/002/003 siguen pasando (no-regression).
- [ ] T909 Ejecutar los 12 escenarios de `quickstart.md` de punta a cabo en orden como smoke test final.
- [ ] T910 Bump de versión en `frontend/package.json` y `backend/pyproject.toml` (minor), tag `v0.4.0-feature-004`.

---

## Dependencias y orden de ejecución

```
Setup (T001–T007)
    ↓
Foundational (T010–T018) — bloque obligatorio
    ↓
    ├── US1 (T101–T142) — backend generator + runtime bundle + canvas UI
    │       ↓
    │   Setup Wizard extension (T501–T507) — puede arrancar en paralelo con US1 tras Foundational
    │       ↓
    ├── US3 (T301–T307) — requiere widget-frame y use-canvas de US1
    ├── US2 (T201–T208) — requiere architect_service y extraction previa de US1
    └── US4 (T401–T407) — requiere architect_service y canvas de US1
                ↓
            Polish (T901–T910)
```

**Paralelismo intra-US1**: T120–T141 pueden avanzar en paralelo una vez T013 (tipos Pydantic) y T018 (tipos TS) están listos. Los renderers T121–T128 son todos `[P]` entre sí.

**Paralelismo cross-US**: US2, US3, US4 pueden ejecutarse en paralelo una vez US1 llega a T139 (canvas montado en page.tsx).

---

## Mapeo Task ↔ Requisito

| Requisito / SC | Tasks clave |
|---|---|
| FR-001, FR-015 | T107 |
| FR-002, FR-003 | T013, T105, T111 |
| FR-002a, FR-002b | T010, T104, T017, T501, T504 |
| FR-004 | T101, T108 |
| FR-005 | T101, T121–T128 |
| FR-006, FR-006a | T201, T202, T203, T207 |
| FR-007, FR-014 | T134, T138, T404 |
| FR-008, FR-008a, FR-008b | T301, T302, T303, T305 |
| FR-009, FR-010 | T106, T401, T403, T405 |
| FR-011 | T106, T141 |
| FR-012, FR-013 | T135, T137 |
| FR-016 | T016 |
| SC-001 | T107, T139, T142 |
| SC-002 | T132, T142 |
| SC-003 | T301, T304, T305 |
| SC-004 | T401, T405, T406 |
| SC-005 | T203, T208 |
| SC-006 | T141 |
| SC-007 | T101 (+ evaluación manual en T909) |

---

## Totales

- **Setup**: 7 tasks
- **Foundational**: 9 tasks
- **US1**: 26 tasks (13 backend, 13 frontend)
- **US2**: 8 tasks
- **US3**: 7 tasks
- **US4**: 7 tasks
- **Setup Wizard extension**: 7 tasks
- **Polish**: 10 tasks

**Total**: 81 tasks.
