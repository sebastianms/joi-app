# Contract: CSS Tokens

**Archivo fuente**: [frontend/src/app/globals.css](frontend/src/app/globals.css)
**Modo de referenciado**: Tailwind v4 `@theme` block + CSS variables nativas.

> Valores **aprobados** en mockup 2026-04-25 (Clarify Q1 cerrado).

---

## Variables

```css
:root {
  --joi-bg:               #0a0d12;
  --joi-surface:          #111520;
  --joi-surface-elevated: #161b28;
  --joi-border:           rgba(255,255,255,0.08);
  --joi-accent:           #00d4ff;
  --joi-accent-warm:      #f5a623;
  --joi-text:             #e2e8f0;
  --joi-muted:            #64748b;
  --joi-glow:             rgba(0,212,255,0.15);
  --joi-success:          #22c55e;
}
```

| Token | Valor |
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
| `--joi-success` | `#22c55e` |

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
Baseline main@fadf15f@2026-04-25:
  Total static JS chunks (uncompressed): 1.1 MB
  Total static JS chunks (gzipped):      ~319 KB
  (Turbopack build — no per-route breakdown disponible en output)
```

- Verificación: re-medir al cerrar Polish. Diff > +10KB gzipped bloquea merge.

```
Polish close main@d4f8183@2026-04-25:
  Total static JS chunks (uncompressed): ~796 KB
  Total static JS chunks (gzipped):      ~240 KB
  Δ gzipped vs baseline:                 −79 KB ✅ (umbral: +10 KB)
```
