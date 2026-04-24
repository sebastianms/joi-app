# Data Model: Feature 006 — Visual Redesign & UX Polish

**Fecha**: 2026-04-24

## Resumen

Feature 006 **no introduce tablas nuevas** en la DB secundaria. Es un rediseño visual + activación de infraestructura de render-mode que ya existe en el modelo backend.

---

## Backend — sin cambios en schema

- El modelo `RenderModeProfile` ya vive en [backend/app/models/render_mode.py](backend/app/models/render_mode.py) desde Feature 004 (T010).
- Tabla `render_mode_profiles` ya se crea en `main.lifespan` (Feature 004 T011).
- Feature 006 simplemente **comienza a consumirla**: el Setup guarda la elección del usuario y el runtime del widget la lee al bootstrap.

### Flujo de datos render-mode

1. Usuario elige mode en `RenderModeStep` del Setup.
2. POST a endpoint ya existente de Feature 004 (o activar el endpoint que haya quedado stub) para persistir `RenderModeProfile` asociado a la `UserSession`.
3. El runtime del widget, al cargar, llama al backend por el mode activo y aplica el adapter correspondiente.

Si algún endpoint de Feature 004 quedó como stub por ADL-022, Feature 006 lo implementa en tasks.

---

## Frontend — contrato de `localStorage`

Estas keys ya existen parcialmente; Feature 006 las formaliza.

| Key | Tipo | Responsable de escribir | Consumidor | Invariantes |
|---|---|---|---|---|
| `joi_session_id` | UUID string | Backend vía primer `POST /api/session` | Todo el frontend | Una sola sesión por tab; no se pisa. (ADL-014) |
| `joi_onboarding_completed` | `"true"` o ausente | `OnboardingWizard` al completar/omitir | `useOnboardingWizard` | Escribe solo `true`; eliminarlo fuerza reopen. |
| `joi_render_mode` | `"shadcn" \| "bootstrap" \| "heroui" \| "design_system_disabled"` | `RenderModeStep` + `useRenderMode` | Runtime del widget | Debe coincidir con `RenderModeProfile` persistido en backend — fuente de verdad es backend; localStorage es caché. |

---

## Tokens CSS — contrato semántico

Los valores concretos quedan pendientes hasta Fase 0 (validación visual). Los nombres y roles:

| Token | Rol | Dónde se usa |
|---|---|---|
| `--joi-bg` | Fondo base de la app | `body`, shells |
| `--joi-surface` | Superficie de panels | `ChatPanel`, `CanvasPanel`, `SetupShell` |
| `--joi-surface-elevated` | Overlays, cards, tooltips | Modals, `CacheReuseSuggestion` |
| `--joi-border` | Bordes sutiles | Dividers, panel borders |
| `--joi-accent` | Color primario de acción | Botones primarios, focus rings |
| `--joi-accent-warm` | Alertas/truncación | Banners de warning, estados de "fallback" |
| `--joi-text` | Texto principal | `p`, `span`, inputs |
| `--joi-muted` | Texto secundario | Timestamps, hints |
| `--joi-glow` | Glow del acento | `box-shadow` del input activo, botón primary hover |

Cambios futuros de paleta modifican **valores**, no nombres (Feature no debería tocar componentes de nuevo).

---

## Diagramas

No se incluye ERD porque no hay cambios relacionales. La única entidad lógica nueva es conceptual: el contrato de tokens CSS y localStorage.
