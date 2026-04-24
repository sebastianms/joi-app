# Contract: CSS Tokens

**Archivo fuente**: [frontend/src/app/globals.css](frontend/src/app/globals.css)
**Modo de referenciado**: Tailwind v4 `@theme` block + CSS variables nativas.

> Los **valores** se definen al completar Fase 0 (validación visual, Clarify Q1). Este contrato fija los **nombres, roles y reglas de uso**.

---

## Variables

```css
:root {
  --joi-bg:               <hex>;            /* fondo base */
  --joi-surface:          <hex>;            /* panels */
  --joi-surface-elevated: <hex>;            /* overlays */
  --joi-border:           <rgba>;           /* bordes sutiles */
  --joi-accent:           <hex>;            /* acción primaria */
  --joi-accent-warm:      <hex>;            /* alertas */
  --joi-text:             <hex>;            /* texto principal */
  --joi-muted:            <hex>;            /* texto secundario */
  --joi-glow:             <rgba>;           /* glow del acento */
}
```

Valores propuestos (pre-validación):

| Token | Valor propuesto |
|---|---|
| `--joi-bg` | `#0a0d12` |
| `--joi-surface` | `#111520` |
| `--joi-surface-elevated` | `#161b28` |
| `--joi-border` | `rgba(255,255,255,0.08)` |
| `--joi-accent` | `#00d4ff` |
| `--joi-accent-warm` | `#f5a623` |
| `--joi-text` | `#e2e8f0` |
| `--joi-muted` | `#64748b` |
| `--joi-glow` | `rgba(0,212,255,0.15)` |

---

## Reglas

1. **Nunca hardcodear color** en componentes (`text-[#00d4ff]` está prohibido). Referenciar siempre por token.
2. **No usar** variables `--tw-*` internas de Tailwind; los tokens son la capa pública.
3. **Glass morphism** solo en `ChatPanel`, `CanvasPanel`, `AppHeader`, `OnboardingWizard`. Implementación: `bg-[color:var(--joi-surface)]/60` + `backdrop-blur-md` + `border border-[color:var(--joi-border)]`. No en botones ni inputs.
4. **Glow** solo en `:focus-visible` y `:hover` de elementos interactivos primarios. Implementación: `box-shadow: 0 0 0 3px var(--joi-glow)`.
5. Modo claro **no soportado**. Las queries `@media (prefers-color-scheme: light)` no aplican cambios.
6. Los valores deben cumplir **WCAG AA** en contraste texto/bg. Se verifica antes de mergear.

---

## Baseline de bundle (Clarify Q5)

- Medir `npm run build` en frontend sobre HEAD `main` al iniciar Implement. Registrar aquí:

```
Baseline main@<commit-sha>@2026-04-24:
  Route `/`              First Load JS: <TBD>kB gzipped
  Route `/setup`         First Load JS: <TBD>kB gzipped
  Shared JS              <TBD>kB gzipped
```

- Verificación: re-medir al cerrar Polish. Diff > +10KB gzipped bloquea merge.
