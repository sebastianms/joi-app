# Tasks: Feature 006 — Visual Redesign & UX Polish

**Branch**: `006-visual-redesign` | **Date**: 2026-04-24 | **Status**: Draft (post-Plan)

> Formato: `- [ ] T### [P?] [US?] Descripción con ruta exacta`.
> `[P]` = paralelizable. `[US1..6]` solo en bloques de user stories.
> **Checkpoints de bloque**: al cerrar cada bloque ejecutar `deckard` review, ADL check, suite completa (`npm run test:e2e` + Lighthouse), commits por grupo y `git push`.

---

## Pre-requisito — Feature 005 mergeada

Esta feature consume componentes creados por Feature 005 (`CacheReuseSuggestion`, `DashboardGrid`, `VectorStoreStep`). No empezar T010 hasta que Feature 005 esté en `main`.

---

## Phase 0 — Visual validation (bloqueante, Clarify Q1)

- [ ] T001 Crear [docs/visual-mockup/index.html](docs/visual-mockup/index.html) con el shell completo usando los hex propuestos (bg #0a0d12, surface #111520, accent #00d4ff, warm #f5a623) + tipografía Geist Sans. Incluir: header, dual panel, una burbuja user, una del agente, AgentTrace colapsado, canvas idle, canvas generating, CacheReuseSuggestion stub, onboarding card stub.
- [ ] T002 **STOP & ASK**: presentar el mockup al usuario. Ajustar valores hasta aprobación explícita. Anotar los valores finales en [contracts/css-tokens.md](specs/006-visual-redesign/contracts/css-tokens.md) antes de continuar.

---

## Setup

- [ ] T005 Anotar baseline de bundle en [contracts/css-tokens.md](specs/006-visual-redesign/contracts/css-tokens.md): correr `cd frontend && npm run build` en HEAD de main, registrar First Load JS por ruta.
- [ ] T006 [P] Crear [frontend/src/lib/storage/joi-storage.ts](frontend/src/lib/storage/joi-storage.ts) con helpers tipados para las 3 keys de localStorage documentadas en [contracts/localstorage.md](specs/006-visual-redesign/contracts/localstorage.md). Prohibir `localStorage.*` directo en componentes (agregar regla ESLint si hay config).
- [ ] T007 [P] Crear directorios nuevos: `frontend/src/components/{layout,onboarding,canvas}/`, `frontend/src/lib/widget-runtime/adapters/`. `.gitkeep` en los vacíos.

---

## Foundational (bloquean US1–US6)

- [ ] T010 Actualizar [frontend/src/app/globals.css](frontend/src/app/globals.css) con los tokens CSS definitivos (post-T002), bloque `@theme` de Tailwind v4, keyframes custom (`pulse-accent`, `construct-lines`, `glow-in`), y reset dark-first.
- [ ] T011 Crear [frontend/src/hooks/useLayoutMode.ts](frontend/src/hooks/useLayoutMode.ts) (contrato: devuelve `"dual" | "tabs"`, listener `matchMedia` 768px, SSR-safe).

---

## User Story 1 — Identidad visual Blade Runner (P1)

- [ ] T020 [US1] Aplicar tokens al shell raíz en [frontend/src/app/layout.tsx](frontend/src/app/layout.tsx): bg, texto, tipografía global con tracking.
- [ ] T021 [P] [US1] Crear [frontend/src/components/layout/AppHeader.tsx](frontend/src/components/layout/AppHeader.tsx) con logo/nombre, navegación mínima, indicador de sesión, botón "¿Cómo funciona?".
- [ ] T022 [P] [US1] Crear [frontend/src/components/layout/PanelSeparator.tsx](frontend/src/components/layout/PanelSeparator.tsx) con profundidad (border + shadow sutil).
- [ ] T023 [US1] Auditar todo el repo por hardcodes de color (`#`, `rgb`, `text-[...]`) y reemplazar por tokens. Comando de referencia: `grep -rn "text-\[\|bg-\[\|border-\[" frontend/src/components/`.

---

## User Story 2 — Layout dual rediseñado con responsive (P1, Q2)

- [ ] T030 [US2] Crear [frontend/src/components/layout/LayoutTabs.tsx](frontend/src/components/layout/LayoutTabs.tsx) según [contracts/components.md](specs/006-visual-redesign/contracts/components.md#layouttabs). `role=tablist`, dos tabs, keyboard nav.
- [ ] T031 [US2] Actualizar [frontend/src/app/page.tsx](frontend/src/app/page.tsx) para usar `useLayoutMode()` y alternar entre split-pane y `LayoutTabs`. Preservar `data-role="chat-panel"` y `"canvas-panel"`.
- [ ] T032 [P] [US2] Añadir Playwright test que ejercita viewports 1024/375 y valida los atributos de tabs (Escenario 2 del quickstart).

---

## User Story 3 — Componentes de chat rediseñados (P1)

- [ ] T040 [US3] Rediseñar [frontend/src/components/chat/MessageBubble.tsx](frontend/src/components/chat/MessageBubble.tsx): variantes user/agent, tokens CSS, avatar Joi para agente. Preservar `data-role`.
- [ ] T041 [P] [US3] Rediseñar [frontend/src/components/chat/AgentTrace.tsx](frontend/src/components/chat/AgentTrace.tsx) con collapse + CSS syntax highlight (regex keywords SQL).
- [ ] T042 [P] [US3] Rediseñar [frontend/src/components/chat/WidgetGenerationTrace.tsx](frontend/src/components/chat/WidgetGenerationTrace.tsx) con badge `source`, pulse animado en `in-progress`. Consume el campo `source` que Feature 005 introdujo.
- [ ] T043 [P] [US3] Crear [frontend/src/components/chat/TypingIndicator.tsx](frontend/src/components/chat/TypingIndicator.tsx) con animación de procesamiento.
- [ ] T044 [US3] Estilar `CacheReuseSuggestion` (componente de Feature 005) con los tokens CSS y estados hover/focus.

---

## User Story 4 — Canvas con estados visuales ricos (P1)

- [ ] T050 [US4] Definir el tipo discriminado `CanvasState` en [frontend/src/types/canvas.ts](frontend/src/types/canvas.ts) según `contracts/components.md`.
- [ ] T051 [P] [US4] Crear [frontend/src/components/canvas/IdleState.tsx](frontend/src/components/canvas/IdleState.tsx) con patrón de puntos + copy de invitación.
- [ ] T052 [P] [US4] Crear [frontend/src/components/canvas/GeneratingState.tsx](frontend/src/components/canvas/GeneratingState.tsx) con animación de líneas progresivas (no spinner).
- [ ] T053 [P] [US4] Crear [frontend/src/components/canvas/BootstrappingOverlay.tsx](frontend/src/components/canvas/BootstrappingOverlay.tsx) con progress sobre iframe.
- [ ] T054 [P] [US4] Crear [frontend/src/components/canvas/CanvasErrorState.tsx](frontend/src/components/canvas/CanvasErrorState.tsx) con tono warning (warm), sin rojo alarma.
- [ ] T055 [US4] Integrar en [frontend/src/components/canvas/CanvasPanel.tsx](frontend/src/components/canvas/CanvasPanel.tsx) con transiciones 200ms ease entre estados.

---

## User Story 5 — Onboarding wizard de primera visita (P2, Q3)

- [ ] T060 [US5] Crear [frontend/src/hooks/useOnboardingWizard.ts](frontend/src/hooks/useOnboardingWizard.ts) según `contracts/components.md`.
- [ ] T061 [P] [US5] Crear [frontend/src/components/onboarding/WizardStepConnect.tsx](frontend/src/components/onboarding/WizardStepConnect.tsx).
- [ ] T062 [P] [US5] Crear [frontend/src/components/onboarding/WizardStepAsk.tsx](frontend/src/components/onboarding/WizardStepAsk.tsx) con ejemplo de prompt.
- [ ] T063 [P] [US5] Crear [frontend/src/components/onboarding/WizardStepGenerate.tsx](frontend/src/components/onboarding/WizardStepGenerate.tsx) con preview estático de un widget.
- [ ] T064 [US5] Crear [frontend/src/components/onboarding/OnboardingWizard.tsx](frontend/src/components/onboarding/OnboardingWizard.tsx) orquestando los 3 pasos + overlay dismissable.
- [ ] T065 [US5] Integrar `OnboardingWizard` en `layout.tsx` controlado por `useOnboardingWizard`. Botón "¿Cómo funciona?" en `AppHeader` llama `open()`.
- [ ] T066 [P] [US5] Playwright test: `localStorage.clear()` + reload → wizard aparece → completar → flag queda en localStorage → reload → no reaparece (Escenario 1 del quickstart).

---

## User Story 6 — Setup rediseñado + render-mode selector (P2, Q4)

**Cierra backlog diferido de Feature 004 (T129–T131, T501–T507).**

- [ ] T070 [US6] Rediseñar shell de [frontend/src/app/setup/page.tsx](frontend/src/app/setup/page.tsx) con [frontend/src/components/setup/SetupShell.tsx](frontend/src/components/setup/SetupShell.tsx) que aplica identidad visual.
- [ ] T071 [P] [US6] Rediseñar `ConnectionForm` existente con inputs estilizados (border sutil + glow en focus), feedback de conexión con check animado y errores con copy accionable.
- [ ] T072 [US6] Integrar `VectorStoreStep` de Feature 005 en el wizard de setup como paso opcional con la identidad visual. Banner "Usando Qdrant por defecto" cuando no hay BYO.
- [ ] T073 [US6] Activar endpoints backend de render-mode si quedaron como stub de Feature 004 (validar [backend/app/api/](backend/app/api/) y completar). Contract: `GET /api/render-mode`, `PUT /api/render-mode`.
- [ ] T074 [P] [US6] Crear [frontend/src/hooks/useRenderMode.ts](frontend/src/hooks/useRenderMode.ts) según `contracts/components.md`.
- [ ] T075 [P] [US6] Crear [frontend/src/components/setup/RenderModeStep.tsx](frontend/src/components/setup/RenderModeStep.tsx) con 4 tarjetas (`shadcn`, `bootstrap`, `heroui`, `design_system_disabled`).
- [ ] T076 [P] [US6] Crear [frontend/src/components/setup/RenderModePreview.tsx](frontend/src/components/setup/RenderModePreview.tsx).
- [ ] T077 [US6] Implementar adaptadores UI del runtime en [frontend/src/lib/widget-runtime/adapters/shadcn.tsx](frontend/src/lib/widget-runtime/adapters/shadcn.tsx), `bootstrap.tsx`, `heroui.tsx`.
- [ ] T078 [US6] Crear [frontend/src/lib/widget-runtime/render-mode-registry.ts](frontend/src/lib/widget-runtime/render-mode-registry.ts) mapeando mode → adapter.
- [ ] T079 [US6] Integrar registry en el entrypoint del runtime (`entry.tsx` o equivalente) para aplicar el adapter activo al bootstrap.
- [ ] T080 [US6] Actualizar script `build:widget-runtime` si el bundle cambió (mismo comando, verificar output).
- [ ] T081 [US6] Playwright: automatizar Escenarios 6–7 y 11–12 del quickstart de Feature 004 (cambio de render-mode cambia widget en runtime).

---

## Polish (cross-cutting)

- [ ] T200 Correr Lighthouse Accessibility sobre `/`, `/setup`, `/collections`, `/dashboards/<id>`. Score ≥ 90 en los 4. Documentar en el PR.
- [ ] T201 Correr suite E2E completa (`npm run test:e2e`). Confirmar que los 22 tests originales + los nuevos (Escenarios 1, 2, 5, 6–7/11–12) pasan.
- [ ] T202 Re-medir bundle (Clarify Q5). Diff contra baseline de T005. Si > +10KB gzipped, optimizar antes de mergear.
- [ ] T203 [P] Actualizar [ADL-022](.design-logs/ADL-022-render-mode-profile-deferred.md) con nota de supersedencia (pasar a "Superseded by Feature 006") o crear ADL-024 con los detalles de activación.
- [ ] T204 Actualizar [specs/roadmap.md](specs/roadmap.md) marcando Phase 7 como `[DONE]` al cerrar la feature.
- [ ] T205 Actualizar [README.md](README.md) con screenshot de la nueva identidad visual (opcional, si se considera valioso).
- [ ] T206 Deckard review sobre todos los archivos tocados. Criticidad ≥ 8 resuelta.

---

## Dependencias

- Phase 0 (T001–T002) bloquea a Foundational.
- Setup (T005–T007) paralelizable.
- Foundational (T010–T011) antes de US1–US6.
- US1 (T020–T023) antes de US2–US6 (los componentes posteriores ya usan tokens).
- US2, US3, US4 paralelizables entre sí post-US1.
- US5 y US6 también paralelizables post-US1.
- Polish al final.

## Convenciones

- Ningún color hardcodeado fuera de `globals.css` o el mockup (T001).
- Ningún `localStorage.*` directo en componentes — solo vía `joi-storage.ts`.
- Al tocar un componente testeado por E2E, verificar que `data-role` se mantiene antes del commit.
- Ningún `package.json` nuevo install (regla dura de la feature).
