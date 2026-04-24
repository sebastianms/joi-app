# Quickstart: Feature 006 — Escenarios de validación

Ejecutar tras cerrar Implement. Precondición: app corriendo vía `dev.sh` o `docker compose up`, Feature 005 ya mergeada.

---

## Escenario 1 — Primera visita dispara el onboarding wizard (US5, Q3)

1. Abrir devtools, `localStorage.clear()` y recargar `/`.
2. El modal `OnboardingWizard` aparece sobre el shell.
3. Paso 1 "Conecta tus datos" muestra CTA a `/setup`.
4. Navegar con "Siguiente" al paso 2 y 3; presionar "Empezar".
5. Verificar que `joi_onboarding_completed === "true"` en localStorage y que el wizard no reaparece al recargar.
6. Click en "¿Cómo funciona?" del header: el wizard reabre. Cerrar con ESC: no sobrescribe el flag.

---

## Escenario 2 — Responsive: dual-panel ↔ tabs en 768px (US2, Q2)

1. En Playwright setear viewport a `1024x720`. Verificar que existe `[data-role="chat-panel"]` y `[data-role="canvas-panel"]` simultáneamente.
2. Setear viewport a `375x800` (phone). Verificar que aparece `[role="tablist"]` con `[data-role="layout-tab-chat"]` activo y el canvas oculto.
3. Click en `layout-tab-canvas`. El panel del canvas se muestra; el chat queda `hidden`.
4. Volver a `1024x720`: ambos paneles visibles de nuevo; no hay sticky tabs.

---

## Escenario 3 — Identidad visual aplicada a chat y canvas (US1, US3, US4)

1. Generar un widget normalmente.
2. Verificar visualmente:
   - Burbuja de usuario a la derecha con fondo `--joi-accent/10`.
   - Mensaje del agente sin burbuja, avatar "Joi" a la izquierda.
   - `AgentTrace` colapsado con icono terminal; al expandir se ven keywords SQL resaltadas.
   - `WidgetGenerationTrace` con badge pulsante durante generación.
   - Canvas muestra estado `generating` con animación de líneas (no spinner genérico).
   - Al completar, transición suave a `rendering`.

---

## Escenario 4 — Setup redesignado con render-mode selector (US6, Q4)

1. Navegar a `/setup`.
2. Verificar shell con identidad visual (bg dark, glass sutil en el form).
3. Paso de conexión: inputs con glow en focus.
4. Paso render-mode: 4 tarjetas con preview. Seleccionar "bootstrap".
5. Guardar. Generar un widget nuevo. Verificar que el iframe del canvas boot-strapea con CSS de Bootstrap y que el componente usa clases Bootstrap.
6. Volver al setup, cambiar a "shadcn". El widget actual se re-bootstrappea (o se pide confirmación de recarga según impl).

**Esto cubre Escenarios 6–7 y 11–12 del quickstart de Feature 004.**

---

## Escenario 5 — Preservación de los 22 tests E2E (SC-004)

1. Correr `npm run test:e2e` en `frontend/`.
2. Todos los tests pasan sin modificar asserts.
3. Todos los `data-role` / `aria-label` referenciados por los tests siguen existiendo.

---

## Escenario 6 — Bundle size budget (Q5)

1. En `main` (HEAD del inicio de feature): `cd frontend && npm run build`. Anotar First Load JS por ruta.
2. Tras cerrar Implement, en la branch `006-visual-redesign`: repetir build.
3. Diff `<= +10KB gzipped` en cada ruta y en shared JS.
4. Si se excede, perfilar con `next build --profile` y eliminar bloat antes de mergear.

---

## Escenario 7 — Lighthouse Accessibility (SC)

1. `npx lighthouse http://localhost:3000/ --only-categories=accessibility` → score ≥ 90.
2. Repetir para `/setup`, `/collections`, `/dashboards/<any>`.
3. Score de contraste, focus, aria coverage: sin errores críticos.

---

## Escenario 8 — Integración visual con componentes de Feature 005

1. Navegar a `/collections` creado en Feature 005: ve los mismos tokens CSS y glass sutil.
2. Navegar a `/dashboards/<id>`: el grid respeta la paleta; el indicador de error localizado (widget con conexión perdida) usa `--joi-accent-warm`, no rojo.
3. Generar un widget que dispare `CacheReuseSuggestion`: la tarjeta usa la identidad visual.

---

## Escenario 9 — Reset completo (contrato localStorage)

1. Borrar las 3 keys (`joi_session_id`, `joi_onboarding_completed`, `joi_render_mode`).
2. Recargar.
3. El wizard aparece, el backend crea nueva sesión, el render-mode vuelve a `shadcn` default.
