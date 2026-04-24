# Research: Feature 006 — Visual Redesign & UX Polish

**Fecha**: 2026-04-24

---

## R1 — Validación visual previa al congelamiento de tokens (Clarify Q1)

**Decisión**: Producir un mockup estático antes de emitir tokens CSS definitivos.

**Plan concreto**:
- Crear `docs/visual-mockup/` con un HTML de página única que renderice todo el shell principal (header + dual panel + chat stub + canvas stub + onboarding card stub + CacheReuseSuggestion stub) usando los hex propuestos en D4 del spec.
- Tipografías: Geist Sans ya presente.
- El mockup NO requiere hidratación React, puede ser HTML/CSS puro.
- Usuario lo revisa, propone ajustes (p.ej. "el accent es muy saturado", "el warm no se lee sobre el bg"), se itera y se cierra con valores finales.

**Rationale**: evita escribir tokens CSS y refactorizar componentes para darse cuenta en QA que la paleta no convence. Coste: ~30 min de iteración visual contra horas de retrabajo.

**Alternativas descartadas**:
- Figma: fricción de herramienta y versión.
- Storybook: agrega infra; Feature 006 NO debe sumar dependencias.

---

## R2 — Breakpoint 768px (Tailwind `md`) para dual↔tabs (Clarify Q2)

**Decisión**: En `< 768px` se renderiza un componente `LayoutTabs` con dos pestañas (Chat, Canvas). En `≥ 768px` se mantiene el split pane existente.

**Implementación**:
- Hook `useLayoutMode()` escucha `window.matchMedia("(min-width: 768px)")` con cleanup. SSR-safe con default `"dual"`.
- `LayoutTabs` tiene `role="tablist"`, cada tab con `aria-selected` y `data-role="layout-tab-<chat|canvas>"`.
- La pestaña activa persiste en el estado del componente raíz; al volver a desktop, ambos paneles se muestran igual que antes (no hay estado sticky tabs).

**Rationale**: `md` es el estándar Tailwind y coincide con el mobile/tablet-landscape natural.

**Alternativas descartadas**:
- Aspect ratio (Q2 opción 4): difícil de testear en Playwright (`page.setViewportSize` fuerza width/height pero los helpers de matchMedia con aspect-ratio son menos estables).

---

## R3 — Onboarding wizard: trigger y persistencia (Clarify Q3)

**Decisión**:
- Trigger: `if (localStorage.getItem("joi_session_id") === null) open()`.
- Persistencia de "visto": `localStorage.setItem("joi_onboarding_completed", "true")`. Al completar cualquiera de los 3 pasos o al "Omitir", se marca.
- Reapertura manual: botón "¿Cómo funciona?" en el header siempre abre el wizard, sin tocar el flag.
- El wizard NO bloquea la app: es un modal con overlay dismissable con ESC y click fuera.

**Rationale**:
- La sesión existe desde la primera interacción backend (ADL-014). Mientras no exista, es primera visita.
- El flag `onboarding_completed` no requiere columna en DB (sería over-engineering para un flag de cliente).

**Contrato localStorage**: documentado en `contracts/localstorage.md`.

---

## R4 — Render-mode selector + adaptadores UI (Clarify Q4)

**Decisión**: Cerrar el backlog diferido de Feature 004 dentro de esta feature.

**Alcance concreto**:
- Setup incluye `RenderModeStep` con 4 opciones: `shadcn` (default), `bootstrap`, `heroui`, `design_system_disabled`. El campo `design_system_disabled` deshabilita el picker de Design System pero mantiene shadcn como runtime (alineado con ADL-022).
- Adaptadores en `frontend/src/lib/widget-runtime/adapters/`:
  - `shadcn.tsx`: wrapper que usa `@/components/ui/*` existentes.
  - `bootstrap.tsx`: carga CDN de Bootstrap CSS dentro del iframe sandbox al montar.
  - `heroui.tsx`: usa HeroUI (si la lib ya está) o placeholder con stubs equivalentes.
- Registry `render-mode-registry.ts`: mapea `render_mode → adapter`. El runtime del widget consulta el registry al bootstrap y aplica el adapter correspondiente.
- El runtime bundle (`public/widget-runtime.bundle.js`) se rebuildeará con los adaptadores; actualizar script `build:widget-runtime`.

**Cobertura de Escenarios 6–7 y 11–12 del quickstart de Feature 004**: los tasks de esta feature incluyen automatizarlos en Playwright.

**ADL**: crear ADL-024 (o actualizar ADL-022) documentando la activación del render-mode profile.

---

## R5 — Baseline de bundle + verificación manual (Clarify Q5)

**Decisión**:
- Congelar baseline: correr `cd frontend && npm run build` sobre el HEAD de `main` al 2026-04-24 (o fecha de kickoff del Implement), anotar `Route / First Load JS` gzipped reportado por Next.js y documentarlo en un bloque del Plan y en `contracts/css-tokens.md`.
- Verificación: en el PR que cierra US1 (tokens + layout) y en el final, correr `npm run build` localmente, comparar. Si diff > +10KB gzipped, bloquear merge hasta optimizar (p.ej. eliminar keyframes duplicados, tree-shake íconos).
- No se añade `size-limit`, `bundle-analyzer` ni GitHub Action.

**Rationale**: bajo overhead; el cambio es puramente visual y cualquier bloat masivo lo captura un reviewer atento.

---

## R6 — Preservación de contratos de testing

**Decisión**:
- Cada componente rediseñado conserva sus `data-role` y `aria-label` actuales. Al renombrar un componente, se mantienen los atributos.
- Antes de cerrar cada task de redesign se corre el subset de Playwright que toca ese componente.
- Tarea de Polish: correr la suite completa de 22 E2E y Lighthouse.

**Rationale**: evita tener que reescribir tests en paralelo al rediseño — el rediseño es cosmético, no funcional.

---

## Referencias

- ADL-022 (render-mode-profile-deferred) — se supersede al cerrar esta feature.
- Feature 005 (Dashboards) — esta feature estiliza los componentes creados allá.
- spec.md de Feature 004 — escenarios 6–7 y 11–12 del quickstart se cubren aquí.
