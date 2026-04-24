# Implementation Plan: Feature 006 — Visual Redesign & UX Polish

**Branch**: `006-visual-redesign` | **Date**: 2026-04-24 | **Status**: Plan drafted post-Clarify

---

## Summary

Feature 006 aplica la identidad visual "Joi / Blade Runner 2049" a la app completa: tokens CSS dark-first, layout dual rediseñado con responsive por tabs en `<768px`, componentes de chat rediseñados, canvas con estados visuales ricos, onboarding wizard de primera visita, y setup page rediseñada **incluyendo** el render-mode selector + adaptadores UI (backlog diferido de Feature 004). Sin nuevas dependencias en `package.json`. La paleta CSS se congela **después** de una validación visual por mockup (Clarify Q1).

---

## Technical Context

| Área | Elección |
|---|---|
| Stack | Next.js + Tailwind v4 + shadcn/ui existentes; sin nuevas dependencias |
| Animaciones | CSS keyframes + `tailwindcss-animate` ya presente; **sin** Framer Motion (D2) |
| Tokens | CSS variables en [frontend/src/app/globals.css](frontend/src/app/globals.css), referenciadas vía Tailwind (v4 soporta `@theme`) |
| Responsive | Tailwind `md` breakpoint (768px) para switch dual↔tabs (Clarify Q2) |
| Accesibilidad | Contraste WCAG AA; `aria-*` + `data-role` preservados |
| Testing | Playwright existente (22 E2E) sin cambios obligatorios; lighthouse-ci opcional en verificación manual |
| Bundle budget | +≤10KB gzipped sobre main@2026-04-24 (Clarify Q5) |
| Render modes | Adaptadores UI shadcn/bootstrap/heroui dentro del widget-runtime (cierra backlog Feature 004) |

---

## Constitution Check

| Constraint | Estado |
|---|---|
| `mission.md` — Joi como identidad diferenciadora | ✅ refuerza identidad. |
| `tech-stack.md` — Tailwind + shadcn | ✅ sin cambios de stack. |
| `mission.md` — Success Metric "Fidelidad visual al design system precargado" | ✅ US6 entrega el selector + adaptadores que completan este ítem. |
| ADL-022 (render-mode-profile-deferred) | ⚠️ se **supersede** aquí; nuevo ADL "render-mode-profile-activated" o update a ADL-022 al cerrar Implement. |

Sin violaciones en Complexity Tracking.

---

## Project Structure

```text
frontend/src/
├── app/
│   ├── globals.css            # [MODIFIED] tokens CSS + keyframes + base styles
│   ├── layout.tsx             # [MODIFIED] header redesign, shell dark-first
│   ├── page.tsx               # [MODIFIED] shell dual↔tabs responsive
│   └── setup/
│       └── page.tsx           # [MODIFIED] rediseño completo + render-mode step
├── components/
│   ├── layout/
│   │   ├── AppHeader.tsx              # NEW
│   │   ├── LayoutTabs.tsx             # NEW — responsive tabs < 768px
│   │   └── PanelSeparator.tsx         # NEW
│   ├── chat/
│   │   ├── ChatPanel.tsx              # [MODIFIED]
│   │   ├── MessageBubble.tsx          # [MODIFIED] user / agent variants
│   │   ├── AgentTrace.tsx             # [MODIFIED] collapsible + CSS syntax highlight
│   │   ├── WidgetGenerationTrace.tsx  # [MODIFIED] badge + pulse
│   │   └── TypingIndicator.tsx        # NEW
│   ├── canvas/
│   │   ├── CanvasPanel.tsx            # [MODIFIED]
│   │   ├── IdleState.tsx              # NEW — patrón de puntos + copy
│   │   ├── GeneratingState.tsx        # NEW — líneas progresivas
│   │   ├── BootstrappingOverlay.tsx   # NEW
│   │   └── CanvasErrorState.tsx       # NEW
│   ├── onboarding/
│   │   ├── OnboardingWizard.tsx       # NEW — modal 3 pasos
│   │   ├── WizardStepConnect.tsx      # NEW
│   │   ├── WizardStepAsk.tsx          # NEW
│   │   └── WizardStepGenerate.tsx     # NEW
│   └── setup/
│       ├── SetupShell.tsx             # NEW — shell con la identidad visual
│       ├── ConnectionForm.tsx         # [MODIFIED] inputs con glow focus
│       ├── RenderModeStep.tsx         # NEW — selector shadcn/bootstrap/heroui
│       └── RenderModePreview.tsx      # NEW — preview por mode
├── hooks/
│   ├── useLayoutMode.ts               # NEW — devuelve 'dual' | 'tabs'
│   ├── useOnboardingWizard.ts         # NEW — lee localStorage, maneja open/close/skip
│   └── useRenderMode.ts               # NEW — selecciona el adaptador UI activo
└── lib/
    └── widget-runtime/
        ├── adapters/
        │   ├── shadcn.tsx             # NEW (cierra T129–T131 de Feature 004)
        │   ├── bootstrap.tsx          # NEW
        │   └── heroui.tsx             # NEW
        └── render-mode-registry.ts    # NEW

docs/
└── visual-mockup/                     # NEW — screenshots/HTML mockup para validar Q1
```

---

## Fase 0 — Visual validation (pre-Plan-freeze)

Antes de emitir tokens y empezar tasks, producir un **mockup estático** del layout dual con la paleta propuesta. El mockup:
- Vive en `docs/visual-mockup/index.html` (o Next.js page temporal `/mockup`).
- Renderiza: header + dual panels + una burbuja de chat + un canvas en estado idle + un widget stub + la tarjeta CacheReuseSuggestion de Feature 005.
- Usa los colores `#0a0d12`, `#111520`, `#00d4ff`, `#f5a623` como hex literales.
- El usuario lo valida visualmente. Ajustes antes de congelar tokens.

Este paso es **obligatorio** según Clarify Q1 — no avanzar a Task T020 (globals.css) sin aprobación.

---

## Fase 1 — Design artifacts

### `research.md`
- R1 — Validación visual antes de congelar tokens (Clarify Q1)
- R2 — Breakpoint 768px y estrategia de tabs (Clarify Q2)
- R3 — Onboarding wizard trigger y storage (Clarify Q3)
- R4 — Render-mode selector + adaptadores UI (Clarify Q4)
- R5 — Baseline de bundle y verificación manual (Clarify Q5)
- R6 — Preservación de `data-role`/`aria-label` durante el rediseño (no romper los 22 E2E)

### `data-model.md`
- Entidad mínima: no se agregan tablas nuevas. `onboarding_completed` vive en `localStorage` (Clarify Q3). Se documenta el contrato de localStorage en data-model para trazabilidad.
- `RenderModeProfile` ya existe ([backend/app/models/render_mode.py](backend/app/models/render_mode.py)) — se **activa** al cerrar el backlog de Feature 004. Se documenta cómo se consume desde el frontend vía `useRenderMode`.

### `contracts/`
- `contracts/css-tokens.md` — contrato de tokens CSS (nombres, semántica; valores se definen tras Fase 0).
- `contracts/components.md` — props públicas de `AgentTrace`, `WidgetGenerationTrace`, `OnboardingWizard`, `RenderModeStep`, `LayoutTabs`.
- `contracts/localstorage.md` — keys y shape: `joi_session_id`, `joi_onboarding_completed`, `joi_render_mode`.

### `quickstart.md`
- Primera visita dispara wizard
- Completar los 3 pasos → wizard se marca completado y nunca reaparece
- Tests E2E de los 22 escenarios existentes pasan
- Lighthouse Accessibility ≥ 90 en `/`, `/setup`, `/collections`, `/dashboards/{id}`
- Cambio de render-mode desde setup cambia el widget en runtime (cubre Escenarios 6–7, 11–12 del quickstart de Feature 004)

---

## Dependencias con Feature 005

Feature 006 arranca **después** de Feature 005 shipped. Efectos:
- El `CacheReuseSuggestion` ya existe como componente funcional; Feature 006 le aplica estilo.
- El editor de dashboards ya existe; Feature 006 estiliza `DashboardGrid` y `DashboardItem`.
- El `VectorStoreStep` del Setup ya existe; Feature 006 lo rediseña junto al resto del Setup Wizard.

Si por algún motivo se implementan en paralelo, documentar en los tasks qué componentes necesitan ser placeholder-friendly.

---

## Complexity Tracking

Ninguna violación pendiente. Todas las decisiones están ancladas a un criterio del spec o a una respuesta de Clarify.
