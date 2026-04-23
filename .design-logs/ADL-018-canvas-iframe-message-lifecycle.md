# ADL-018: Ciclo de vida de mensajes entre el host y el iframe sandboxed del Canvas

**Fecha:** 2026-04-23
**Estado:** Activo
**Área:** Frontend
**Autor:** AI Session

---

## Contexto

La Feature 004 aisla cada widget en un `<iframe sandbox="allow-scripts" srcdoc="...">` con CSP que bloquea `connect-src`, `allow-same-origin`, `allow-top-navigation` y `allow-forms` (ver spec FR-008 y R4 de `specs/004-widget-generation/research.md`). La comunicación con el widget se hace exclusivamente vía `postMessage` siguiendo un protocolo versionado (`widget:init`, `widget:ready`, `widget:error`, `widget:resize`).

Durante la validación manual del flujo de US2 (preferencia del usuario — "muéstralo como tabla" tras un widget ya visible) encontramos dos problemas que hacían que el overlay de "Renderizando el widget…" nunca desapareciera:

1. **El check `event.source !== iframeWindow` descartaba todos los mensajes.** Con `sandbox="allow-scripts"` sin `allow-same-origin`, el navegador asigna un **origen opaco** al iframe; la referencia del `contentWindow` en el host y el `event.source` del mensaje son objetos distintos, por lo que la comparación por identidad de referencia falla siempre.
2. **El `widget:init` solo se enviaba en el evento `onLoad` del iframe.** El `srcdoc` del iframe solo depende del bundle de runtime (estable entre widgets), por lo que el iframe no recarga cuando cambia el `WidgetSpec`. El `onLoad` solo dispara la primera vez; el segundo widget nunca recibía el `init` y por lo tanto nunca emitía `widget:ready`.

---

## Decisión

Adoptar dos reglas operativas en el hook `useCanvas`:

1. **Validación por forma de mensaje, no por identidad de fuente.** El listener `message` aplica los guards del protocolo (`isWidgetReadyMessage`, `isWidgetErrorMessage`, `isWidgetResizeMessage`) y descarta silenciosamente cualquier mensaje no conforme. No se compara `event.source` contra `contentWindow`.
2. **Reemitir `widget:init` en cada cambio de `WidgetSpec`.** El envío del `init` vive en un `useEffect` con deps `[widgetSpec, dataRows]` y guard por `useRef` sobre el `widget_id` para que no se re-emita por referencias cambiadas del mismo spec. El `onLoad` del iframe deja de ser el punto de envío.

Complementariamente, el cambio de spec se detecta también vía `useRef<string | null>` sobre `widget_id` en lugar del patrón "adjust state during render" previo; eso evita resets en cascada de `loading_stage` cuando el árbol re-renderiza por motivos no relacionados (p.ej. `isSending` del chat).

---

## Justificación

- **Correctitud frente al contrato del navegador.** La decisión #1 reconoce que el sandbox con origen opaco es un invariante elegido intencionalmente (FR-008 exige no `allow-same-origin`). Cualquier heurística basada en identidad de referencia es frágil por diseño; el protocolo versionado ya aporta la autenticidad del mensaje.
- **Idempotencia del runtime.** La decisión #2 aprovecha que el runtime del iframe (`entry.tsx`) ya maneja re-renders idempotentes: guarda `state.root` y re-invoca `state.root.render(...)` al recibir un nuevo `widget:init`. No hace falta recargar el iframe entre widgets; basta con re-invocar el contrato.
- **Alineación con el timeout de bootstrap.** El timer de 4s (`BOOTSTRAP_TIMEOUT_MS`) se reinicia en el mismo efecto que emite el `init`, manteniendo semántica consistente entre el primer widget y los siguientes.

---

## Consecuencias

### ✅ Positivas
- Los cambios de widget dentro de una misma sesión (US2 preferencia, y también US4 fallback tras error) renderizan correctamente sin recargar el iframe.
- Menos acoplamiento entre el ciclo de vida del iframe y el del spec — el runtime queda libre de "montar/desmontar" entre widgets, lo que reduce el tiempo visible del overlay de bootstrap.
- La validación por forma de mensaje es robusta frente a navegadores que implementen orígenes opacos de formas diferentes o futuras extensiones del sandbox.

### ⚠️ Trade-offs aceptados
- **Superficie de ataque por mensajes no autenticados**: cualquier script de la misma página del host puede, en teoría, emitir un `postMessage` que matchee los guards del protocolo y engañar al host. El riesgo se mitiga porque (a) el host solo consume cuatro tipos de mensaje con efectos acotados — `ready` solo cambia `loading_stage`, `resize` solo ajusta altura, `error` muestra un banner, y ninguno ejecuta código; (b) el `extraction_id` viaja en cada mensaje y podría añadirse validación contra el spec actual si aparece un vector de explotación.
- **Responsabilidad idempotente en el runtime**: cualquier nuevo renderer que se registre en `widget-runtime` debe ser idempotente ante `render()` múltiple sobre el mismo `root`. React lo es por defecto, pero efectos laterales (workers, listeners globales) deben limpiarse en `useEffect` returns.
- El `onLoad` del iframe queda como no-op útil (se dispara para la primera carga del bundle, pero el init efectivo viene del effect).

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Re-montar el iframe (cambiar `srcdoc` o agregar `key`) en cada spec | Descarga y re-parseo del bundle completo (~600KB) por cada cambio de widget; rompe SC-002 (p95 < 6s); incrementa latencia del swap de US2 muy por encima de SC-005 (< 3s). |
| Mantener el check `event.source` y remover `sandbox` same-origin | Violaría FR-008 y abriría superficie de ataque enorme. El aislamiento es no negociable. |
| Guardar referencia al `contentWindow` en un ref y usar `ref.current === event.source` | Mismo problema: bajo sandbox opaco la comparación sigue fallando. El origen opaco aplica aunque el contentWindow sea accesible desde el host. |
| Usar `MessageChannel` en lugar de `postMessage` global | Funcionalmente posible, pero requiere enviar un `MessagePort` al iframe en el `init` inicial y el iframe debe coordinar el `onmessage` sobre ese port. Complejidad adicional sin beneficio claro sobre la validación por forma. |
| Detectar cambio de spec con el patrón "adjust state during render" (setLastAppliedSpec) | Frágil: cualquier re-render del árbol (incluyendo los causados por `setIsSending`) puede disparar una cascada que resetea `loading_stage` después de que `ready` ya se recibió. El efecto con `useRef` es más predecible. |

---

## Decisiones Relacionadas
- **Feature 004 spec y research** (`specs/004-widget-generation/`) — define el contrato postMessage, los flags de sandbox y el timeout de bootstrap que este ADL implementa.
- **ADL-017 (Widget runtime renderer registry)** — el runtime idempotente que permite re-invocar `init` sin recarga del iframe depende del registry y su patrón de `state.root` persistente.
- **ADL-015 (Mock LLM responses)** — los escenarios E2E que validan este ciclo de vida (Esc 4 de preferencia, Esc 5 incompatibilidad) corren sobre el mock router sin tokens.

---

## Notas para el AI (Memoria Técnica)
- **No reintroducir** el check `event.source === iframeWindow` en el listener del host. El sandbox opaco rompe la igualdad por referencia y hace que todos los mensajes sean descartados. Si aparece un requisito de autenticidad adicional, usar el `extraction_id` dentro del payload y validarlo contra `current_widget_spec.extraction_id`.
- **No mover** el envío de `widget:init` de vuelta a `onLoad` del iframe. El `srcdoc` es estable entre specs por diseño (cachea el bundle), y `onLoad` solo dispara la primera vez que el iframe se monta. Cualquier nuevo camino que cambie la spec debe pasar por el effect que detecta cambios por `widget_id`.
- **Todo renderer** nuevo registrado en `widget-runtime/renderers/*` debe ser idempotente ante múltiples `root.render()` con specs distintas. Si necesita recursos externos (workers, intervals), limpiarlos en el componente.
- **Timeout de bootstrap**: al reemitir `init`, siempre primero `clearTimer()` y luego reinstalar el `setTimeout`. El valor vive en `BOOTSTRAP_TIMEOUT_MS = 4000`; si se ajusta, actualizar FR-008b y R4 de la spec de Feature 004.
- **Runtime bundle** (`public/widget-runtime.bundle.js`) se compila por separado con `npm run build:widget-runtime`. No lo toca Next.js. Si cambia `entry.tsx`, `protocol.ts`, los renderers o el registry, es obligatorio re-compilar el bundle para que los cambios sean visibles en el iframe.
