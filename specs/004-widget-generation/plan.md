# Implementation Plan: Feature 004 — Widget Generation & Canvas Rendering

**Branch**: `004-widget-generation` | **Date**: 2026-04-22 | **Status**: Ready for Tasks

---

## Summary

**Requisito primario**: cerrar la Fase 5 del roadmap transformando cada `data_extraction.v1` exitosa en un widget renderizado en el Canvas derecho, manteniendo el aislamiento como invariante duro.

**Enfoque técnico**:
- **Selector determinístico** de tipo de widget (8 tipos) sobre la forma de la extracción — latencia cero, auditable (ver [research.md#R1](research.md)).
- **Agente Arquitecto/Generador** que produce `widget_spec.v1` usando LiteLLM con `Purpose="widget"`, operando bajo uno de dos modos: `ui_framework` (default) con un **system prompt cacheado** del manifest de la librería elegida (shadcn/ui | Bootstrap | HeroUI), o `free_code` (código libre). El tercer modo (`design_system` vía Storybook) queda **inhabilitado en MVP**.
- **Motor del Canvas**: iframe sandbox con `allow-scripts` + CSP hermética + protocolo postMessage versionado. Un único `widget-runtime.bundle.js` (React + Recharts + adaptadores por librería) sirve los 8 tipos dentro del iframe.
- **Fallback universal**: cualquier falla (generador timeout, spec inválida, iframe timeout 4s, render error) produce automáticamente una `WidgetSpec` de tabla construida por transformación determinística, sin invocar LLM.
- **Integración con chat**: `ChatResponse` se extiende retrocompatible con `widget_spec` y `render_mode_profile`. `AgentTrace` se extiende con sub-objeto `widget_generation`.
- **Persistencia nueva**: tabla `render_mode_profiles` en `joi_app.db` ligada a `session_id`.
- **Setup Wizard**: nuevo paso "Framework visual" (extiende Feature 001).

---

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5 + React 19 + Next.js 16 (frontend).

**Primary Dependencies (nuevas para esta feature)**:
- **Backend**: ninguna nueva crítica; reutiliza `litellm` (Feature 003), `sqlalchemy + aiosqlite` (ADL-003), `pydantic 2`. Solo un módulo nuevo `widget_manifests/` con texto estático.
- **Frontend**: `recharts` (~50KB gzipped) para los 6 tipos de charts estándar; heatmap custom en SVG. React 19 y Tailwind ya presentes.

**Dependencias heredadas**: FastAPI, SQLAlchemy, LiteLLM, ChatManagerService, TriageEngine, DataAgentService.

**Storage**:
- `joi_app.db` — tabla nueva `render_mode_profiles`.
- Runtime bundle servido como asset estático de Next.js (`frontend/public/widget-runtime.bundle.js`) construido por un paso de build dedicado.
- NO se introducen nuevos stores persistentes (no Chroma adicional, no filesystem extra).

**Testing**:
- **Backend**: pytest + pytest-asyncio. Unit: selector determinístico, validador de WidgetSpec, builder de fallback, regex de preferencia. Integration: endpoint `/api/chat/messages` con widget generado (LiteLLM mockeado).
- **Frontend**: Vitest + React Testing Library para componentes; Playwright para E2E (escenarios 1, 4, 6, 8 de quickstart).
- **Adversarial**: suite específica de widgets maliciosos (Escenario 6) ejecutada en CI.

**Target Platform**: Linux/macOS local + Docker (`docker-compose.yml` existente).

**Project Type**: web app (backend + frontend desacoplados).

---

## Constitution Check

| Invariante | Origen | Cómo lo cumple el plan |
|---|---|---|
| 100% read-only sobre fuentes | mission.md | No aplica directamente — Feature 004 consume `DataExtraction` ya generada. |
| Aislamiento visual/ejecución | mission.md ("cero modificaciones no deseadas") | iframe `sandbox="allow-scripts"` + CSP hermética + postMessage versionado. FR-008, FR-008a, FR-008b. SC-003. |
| Agnosticismo LLM | mission.md + tech-stack.md | Modelo del generador seleccionado por env var vía LiteLLM (`Purpose="widget"`). Hot-swap sin tocar código (R6). |
| Multi-agente | tech-stack.md | Feature 004 implementa el Agente 2 (Arquitecto/Generador). Contrato `widget_spec.v1` estable, paralelo a `data_extraction.v1`. |
| Triage híbrido | tech-stack.md | Extensión determinística del TriageEngine con regex de preferencia de widget (FR-006a, R10). NO se introduce capa probabilística. |
| Almacenamiento local SQLite | ADL-003 | `render_mode_profiles` en `joi_app.db` con SQLAlchemy + aiosqlite. |
| Chat panel único | ADL-004 | `WidgetGenerationTrace` se renderiza dentro del `AgentTraceBlock` existente, sin estructura paralela. |
| E2E con aria-label | ADL-002 | `CanvasPanel`, `WidgetFrame`, `WidgetLoadingIndicator`, `WidgetErrorBanner` exponen selectores `aria-label` y `data-role` estables. |
| DI por parámetro | ADL-011 | `WidgetArchitectService` inyectado por FastAPI Depends en `ChatManagerService`. |
| Pydantic exclude_none | ADL-012 | `WidgetSpec` y extensiones de `ChatResponse` serializan con `exclude_none=True`. |
| Session id localStorage | ADL-014 | `RenderModeProfile.session_id` usa exactamente el mismo identificador. |
| Mock LLM para E2E | ADL-015 | El generador respeta el modo `MOCK_LLM_RESPONSES`; el mock entrega WidgetSpecs deterministas para Playwright. |

**Resultado**: ✅ Sin violaciones. No se requiere Complexity Tracking.

---

## Project Structure

```text
backend/
├── app/
│   ├── api/endpoints/
│   │   ├── chat.py                                 # extensión retrocompatible: adjunta widget_spec a ChatResponse
│   │   └── render_mode.py                          # NUEVO — GET/PUT /api/render-mode/profile
│   ├── models/
│   │   ├── chat.py                                 # extender ChatResponse con widget_spec y render_mode_profile
│   │   ├── widget.py                               # NUEVO — WidgetSpec, WidgetBindings, VisualOptions, WidgetCode
│   │   ├── render_mode.py                          # NUEVO — RenderModeProfile (Pydantic) + RenderModeProfileORM (SQLAlchemy)
│   │   └── extraction.py                           # extender AgentTrace con widget_generation (Feature 003)
│   ├── repositories/
│   │   └── render_mode_repository.py               # NUEVO — get_or_create, update
│   ├── services/
│   │   ├── chat_manager.py                         # tras extracción exitosa: invocar WidgetArchitectService y adjuntar spec
│   │   ├── triage_engine.py                        # extender con regex de preferencia de widget (R10)
│   │   ├── litellm_client.py                       # añadir Purpose="widget" + env var LLM_MODEL_WIDGET
│   │   └── widget/
│   │       ├── __init__.py                         # NUEVO
│   │       ├── architect_service.py                # NUEVO — fachada: selector + generador + fallback + trace
│   │       ├── type_selector.py                    # NUEVO — reglas determinísticas de R1
│   │       ├── applicability.py                    # NUEVO — valida compatibilidad tipo ↔ extracción (FR-006)
│   │       ├── fallback_builder.py                 # NUEVO — construye WidgetSpec de tabla sin LLM (R8)
│   │       ├── generator.py                        # NUEVO — invoca LiteLLM con prompt armado + valida schema
│   │       ├── prompt_builder.py                   # NUEVO — ensambla system_prompt_base + manifest
│   │       └── manifests/
│   │           ├── shadcn.md                       # NUEVO — catálogo de componentes shadcn (estático)
│   │           ├── bootstrap.md                    # NUEVO
│   │           └── heroui.md                       # NUEVO
│   └── main.py                                     # registrar creación de render_mode_profiles en lifespan
└── tests/
    ├── unit/
    │   ├── test_type_selector.py                   # NUEVO — 8 tipos + fallback
    │   ├── test_applicability.py                   # NUEVO — incompatibilidades (ej. heatmap con KPI)
    │   ├── test_fallback_builder.py                # NUEVO — tabla pura sin LLM
    │   ├── test_widget_generator.py                # NUEVO — LiteLLM mockeado, validación schema
    │   ├── test_architect_service.py               # NUEVO — happy path + fallback + error dispatch
    │   ├── test_triage_widget_preference.py        # NUEVO — regex de los 8 tipos
    │   └── test_render_mode_repository.py          # NUEVO
    ├── integration/
    │   └── test_chat_with_widget.py                # NUEVO — /api/chat/messages emite widget_spec válido
    └── adversarial/
        └── test_widget_sandbox_specs.py            # NUEVO — fixtures adversariales (backend-side, genera specs maliciosas para E2E)

frontend/
├── src/
│   ├── components/
│   │   ├── canvas/
│   │   │   ├── canvas-panel.tsx                    # NUEVO — orquesta estado, recibe WidgetSpec, monta iframe
│   │   │   ├── widget-frame.tsx                    # NUEVO — <iframe sandbox srcdoc> + postMessage handler
│   │   │   ├── widget-loading.tsx                  # NUEVO — skeleton durante generating/bootstrapping
│   │   │   ├── widget-error-banner.tsx             # NUEVO — error contenido
│   │   │   ├── widget-empty-state.tsx              # NUEVO — row_count=0
│   │   │   └── truncation-badge.tsx                # NUEVO
│   │   ├── chat/
│   │   │   ├── message-list.tsx                    # sin cambios estructurales
│   │   │   └── agent-trace-block.tsx               # extender con sección widget_generation
│   │   └── setup-wizard/
│   │       └── render-mode-step.tsx                # NUEVO — paso "Framework visual" (modo c deshabilitado)
│   ├── hooks/
│   │   ├── use-chat.ts                             # extender Message con widgetSpec
│   │   └── use-canvas.ts                           # NUEVO — maneja CanvasState, postMessage in/out, timeouts
│   ├── types/
│   │   ├── widget.ts                               # NUEVO — tipos TS de widget_spec.v1
│   │   ├── render-mode.ts                          # NUEVO
│   │   └── postmessage.ts                          # NUEVO — tipos del protocolo
│   ├── lib/
│   │   └── widget-runtime/                         # NUEVO — código fuente del bundle
│   │       ├── entry.tsx                           # escucha widget:init, dispatch por widget_type
│   │       ├── renderers/
│   │       │   ├── table.tsx
│   │       │   ├── bar-chart.tsx
│   │       │   ├── line-chart.tsx
│   │       │   ├── pie-chart.tsx
│   │       │   ├── kpi.tsx
│   │       │   ├── scatter.tsx
│   │       │   ├── heatmap.tsx                     # SVG custom
│   │       │   └── area-chart.tsx
│   │       └── adapters/
│   │           ├── shadcn.tsx
│   │           ├── bootstrap.tsx
│   │           └── heroui.tsx
│   └── app/page.tsx                                # reemplazar placeholder del canvas por <CanvasPanel />
├── public/
│   └── widget-runtime.bundle.js                    # NUEVO — output del build dedicado (servido a iframes)
└── build scripts                                   # añadir paso `build:widget-runtime` a package.json

.design-logs/
├── ADL-016-widget-generation-architecture.md       # NUEVO — R2, R3, R6
├── ADL-017-canvas-iframe-sandbox.md                # NUEVO — R4, R5
├── ADL-018-deterministic-widget-selector.md        # NUEVO — R1
└── ADL-019-render-mode-profile-wizard.md           # NUEVO — R7

specs/
└── roadmap.md                                      # actualizar Fase 5: marcar bullets 2 y 3 como completados al cierre
```

---

## Phase 0 — Research (completado)

Ver [research.md](research.md). Resumen:

| # | Decisión | Referencia |
|---|---|---|
| R1 | Catálogo de 8 tipos + selector determinístico | research.md#R1 |
| R2 | Tres modos de render (ui_framework default, free_code, design_system diferido) | research.md#R2 |
| R3 | System prompt cacheado con manifest estático por librería (sin RAG) | research.md#R3 |
| R4 | iframe sandbox + CSP + postMessage v1, timeout 4s | research.md#R4 |
| R5 | Runtime bundle único: React + Recharts + adaptadores | research.md#R5 |
| R6 | LiteLLM `Purpose="widget"` con `LLM_MODEL_WIDGET` env var | research.md#R6 |
| R7 | Setup Wizard step nuevo "Framework visual" | research.md#R7 |
| R8 | Fallback tabular determinístico sin LLM | research.md#R8 |
| R9 | CanvasState en memoria cliente (no persistir) | research.md#R9 |
| R10 | Extensión regex del TriageEngine | research.md#R10 |
| R11 | Observabilidad vía logs estructurados | research.md#R11 |

---

## Phase 1 — Design (completado)

- **Data model**: [data-model.md](data-model.md) — `RenderModeProfile` (persistida), `WidgetSpec` · `CanvasState` · `WidgetGenerationTrace` (memoria), extensiones retrocompatibles a `ChatResponse` y `AgentTrace`.
- **Contracts**:
  - [contracts/widget-spec-v1.schema.json](contracts/widget-spec-v1.schema.json) — JSON Schema Draft 2020-12 del `widget_spec.v1`.
  - [contracts/postmessage-protocol.schema.json](contracts/postmessage-protocol.schema.json) — protocolo Canvas ↔ iframe v1.
  - [contracts/api-spec.json](contracts/api-spec.json) — OpenAPI 3.1 del endpoint extendido de chat y el nuevo `/api/render-mode/profile`.
- **Quickstart**: [quickstart.md](quickstart.md) — 12 escenarios de validación manual.

---

## Secuencia de Implementación

Se formaliza en `tasks.md` (Phase 4). Esbozo aquí:

1. **Fundación backend**: modelos Pydantic/SQLAlchemy (`WidgetSpec`, `RenderModeProfile`), tabla + repositorio, extensión retrocompatible de `ChatResponse` y `AgentTrace`.
2. **Selector determinístico**: `type_selector.py` + `applicability.py` con tests exhaustivos del catálogo (R1).
3. **Fallback builder**: `fallback_builder.py` — tabla cruda desde extracción, sin LLM (R8).
4. **LiteLLM `widget`**: añadir propósito + env var + routing. Verificar que purposes existentes siguen funcionando.
5. **Prompt + manifests**: `prompt_builder.py` + `manifests/{shadcn,bootstrap,heroui}.md` estáticos.
6. **Generador LLM**: `generator.py` invoca LiteLLM, valida contra `widget_spec.v1.schema.json`, retorna spec o error estructurado.
7. **Fachada**: `architect_service.py` orquesta (selector | preferencia) → generador → fallback, emite `WidgetGenerationTrace`.
8. **Endpoints**: `render_mode.py` (GET/PUT). Integración de `architect_service` en `ChatManagerService` tras extracción.
9. **Extensión triage**: regex de preferencia de widget (R10), tests.
10. **Frontend runtime bundle**: build dedicado; renderers de los 8 tipos; adaptadores por librería; entry postMessage.
11. **Frontend canvas**: `canvas-panel.tsx`, `widget-frame.tsx`, `use-canvas.ts`; reemplazar placeholder de `page.tsx`.
12. **Frontend trace**: extensión de `agent-trace-block.tsx` con `widget_generation`.
13. **Frontend wizard**: `render-mode-step.tsx` — tres opciones + modo Storybook deshabilitado.
14. **Quickstart manual**: ejecutar los 12 escenarios.
15. **ADL-016 a ADL-019**: redactar tras implementación.
16. **Polish**: actualizar `roadmap.md`, `.gitignore` (bundle output), README.

---

## Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| LLM genera código que el iframe ejecuta pero no matchea el schema `widget_spec.v1` | Alto | Validación dura por Pydantic + JSON Schema en el generador; cualquier desviación → fallback (R8). |
| Bootstrap del iframe lento degrada SC-002 | Medio | Bundle servido con cache agresiva + pre-warming del iframe al abrir la app. Medición en Escenario 1. |
| CSP rompe librerías UI que cargan fonts/imgs externas | Medio | `img-src data:` + fonts inline en el bundle. Sin `connect-src`. Verificar en Escenario 1 por librería. |
| Recharts no cubre heatmap nativo | Bajo (conocido) | Implementación SVG custom en `renderers/heatmap.tsx` (~50 líneas). |
| Mock LLM de Playwright no devuelve WidgetSpecs realistas | Medio | Fixtures determinísticas por Escenario en `tests/adversarial` y mock response por scenario. |
| Manifest de librería muy grande rompe cache del proveedor | Bajo | Mantenerlos ≤ 2KB cada uno; auditar en revisión. |
| Sesiones existentes sin `render_mode_profiles` | Bajo | Lazy get_or_create con default (`ui_framework` + `shadcn`). |
| Widget truncated confunde al usuario | Bajo | Badge visible obligatorio en el iframe + mensaje en el chat. |

---

## Criterios de Salida de la Feature

- [ ] Los 12 escenarios de `quickstart.md` pasan.
- [ ] Todos los tests unitarios, integración y adversariales del backend pasan.
- [ ] Tests E2E Playwright cubren escenarios 1, 4, 6, 8.
- [ ] No se rompió ninguna suite existente de Features 001/002/003.
- [ ] ADL-016 a ADL-019 mergeados.
- [ ] `roadmap.md` actualizado: Fase 5 cerrada.
- [ ] Feature 005 (Phase 6 — colecciones/dashboards) puede consumir `widget_spec.v1` sin ambigüedad (verificado leyendo el contrato en frío).

---

## Progress Tracking

- [x] Phase 0 — Research: `research.md`.
- [x] Phase 1 — Design: `data-model.md`, `contracts/`, `quickstart.md`.
- [ ] Phase 4 — Tasks: `tasks.md` (siguiente).
- [ ] Phase 5 — Implement.

---

## Complexity Tracking

No aplica. Constitution Check sin violaciones.
