# Contract: Component Props

Solo se documentan componentes **nuevos** o cuyas props cambian. Los componentes existentes que solo reciben clases Tailwind nuevas no requieren contrato.

---

## `LayoutTabs`

```tsx
interface LayoutTabsProps {
  active: "chat" | "canvas";
  onTabChange(tab: "chat" | "canvas"): void;
  chatSlot: React.ReactNode;
  canvasSlot: React.ReactNode;
}
```
- `role="tablist"` en el contenedor.
- Cada `<button role="tab">` con `data-role="layout-tab-chat"` / `"layout-tab-canvas"` y `aria-selected`.
- El `<div role="tabpanel">` activo recibe el slot correspondiente. El inactivo queda montado con `hidden` para preservar estado.

## `useLayoutMode`

```tsx
function useLayoutMode(): "dual" | "tabs"
```
- SSR default: `"dual"`.
- Cliente: `window.matchMedia("(min-width: 768px)")` con listener.

---

## `OnboardingWizard`

```tsx
interface OnboardingWizardProps {
  open: boolean;
  onClose(): void;
  onComplete(): void;
}
```
- Dismissable con ESC y click overlay (salvo durante transición animada).
- Se compone de `WizardStepConnect` → `WizardStepAsk` → `WizardStepGenerate`.
- El botón "Omitir" llama `onComplete()` (se considera completado para no reaparecer).

## `useOnboardingWizard`

```tsx
function useOnboardingWizard(): {
  isOpen: boolean;
  open(): void;
  close(): void;
  complete(): void;
}
```
- Al montar: `isOpen` = `localStorage.getItem("joi_session_id") === null`.
- `complete()` escribe `joi_onboarding_completed=true` + cierra.
- `open()` NO toca el flag (para "¿Cómo funciona?").

---

## `AgentTrace` (rediseño)

Props se preservan. Comportamiento nuevo:
- `collapsed: boolean = true` default.
- Toggle con icono de terminal; animación CSS `max-height` 200ms.
- Highlight SQL: regex inline para `keywords` SQL (`SELECT`, `FROM`, ...) con clase `text-[color:var(--joi-accent)]`. Sin librería externa.
- Preserva `data-role="agent-trace"`.

## `WidgetGenerationTrace`

Props se preservan. Se agregan:
- `source: "generated" | "cache" | "recovered"` (Feature 005 ya introdujo el campo en el backend).
- Badge con color semántico:
  - `generated` → accent cyan con pulse CSS mientras `status === "in-progress"`.
  - `cache` → verde suave.
  - `recovered` → gris muted.
- Preserva `data-role="widget-generation-trace"`.

---

## `RenderModeStep`

```tsx
interface RenderModeStepProps {
  value: RenderMode;
  onChange(mode: RenderMode): void;
  onNext(): void;
}
type RenderMode = "shadcn" | "bootstrap" | "heroui" | "design_system_disabled";
```
- Muestra 4 tarjetas con preview visual (componente `RenderModePreview`).
- `data-role="render-mode-option-<mode>"` en cada tarjeta.

## `useRenderMode`

```tsx
function useRenderMode(): {
  mode: RenderMode;
  setMode(m: RenderMode): Promise<void>;
  isLoading: boolean;
}
```
- Fuente de verdad: backend (`GET /api/render-mode`).
- Cache en `localStorage.joi_render_mode`.
- `setMode` actualiza backend + localStorage + broadcastea a iframe del canvas para rebootstrap.

---

## Estados del Canvas

```tsx
type CanvasState =
  | { kind: "idle" }
  | { kind: "generating"; traceId: string }
  | { kind: "bootstrapping"; widgetId: string; progress: number }
  | { kind: "rendering"; widgetId: string }
  | { kind: "error"; code: WidgetErrorCode; message: string };
```
Cada kind tiene su componente dedicado. Transiciones CSS 200ms ease entre kinds (opacity + translateY sutil).
