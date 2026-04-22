# ADL-014: session_id en localStorage como contrato de sesión del frontend

**Fecha:** 2026-04-22
**Estado:** Activo
**Área:** Frontend
**Autor:** AI Session

---

## Contexto
El Data Agent (Feature 003) necesita propagar un `session_id` emitido por el backend a través de múltiples superficies: el setup wizard lo recibe al crear/validar la conexión, el chat lo adjunta en cada request a `/api/chat/messages`, y los tests E2E de Playwright deben poder pre-sembrar sesiones válidas sin orquestar el flujo completo del wizard.

El chat es una SPA Next.js que corre 100% client-side contra el backend FastAPI, así que el front necesita **leer** el `session_id` para incluirlo en los fetch. Además, la sesión debe sobrevivir refrescos de página para no forzar al usuario a re-configurar la conexión en cada recarga.

---

## Decisión
Se adopta la clave `joi_session_id` en `localStorage` como **contrato canónico** para propagar el `session_id` entre el setup wizard, el hook `use-chat` y los tests E2E. Playwright inyecta la sesión vía `page.addInitScript()` antes de `page.goto()` para pre-sembrar escenarios sin interceptar HTTP.

---

## Justificación
- Es la única opción que satisface las tres restricciones simultáneas: **lectura desde JS del cliente**, **persistencia entre recargas** y **inyectabilidad desde Playwright** sin mocks de red.
- Mantiene el frontend desacoplado del mecanismo de transporte: cualquier componente que necesite sesión lee la misma key, sin prop drilling ni contextos globales.
- Habilita tests E2E deterministas y rápidos — el helper `gotoWithSession` en `frontend/e2e/data-agent.spec.ts` pre-siembra la key y `use-chat` la consume naturalmente, sin interceptar requests.

---

## Consecuencias

### ✅ Positivas
- Contrato simple y descubrible: cualquier feature futura que necesite sesión sabe dónde buscarla.
- Tests E2E sin `page.route()` HTTP mocking — reducen fragilidad y reflejan el camino real.
- Sobrevive recargas del navegador sin infraestructura adicional (cookies, servidor de sesión).

### ⚠️ Trade-offs aceptados
- El `session_id` queda expuesto a cualquier JS del mismo origen (incluidos scripts de terceros si se agregan en el futuro). Revisar esta decisión si se integran analytics/tag managers externos.
- No hay expiración automática — si el backend invalida la sesión, el front debe detectar el error y limpiar la key manualmente.
- Funciona sólo en el navegador; si en algún momento se renderizan mensajes del chat desde el servidor (SSR/RSC), ese path debe resolver la sesión por otro medio.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Cookie `HttpOnly` | No es legible desde JS, y el chat SPA necesita adjuntar el id explícitamente en los fetch del cliente. |
| Cookie accesible a JS | Mismos pros que localStorage pero con semántica de envío automático al backend en cada request, lo cual no queremos (queremos control explícito sobre qué llamadas llevan sesión). |
| Query param en la URL | Fricción UX (URLs feas, se copian/pegan con credenciales de sesión), y obliga a sincronizar estado entre rutas. |
| Estado global en memoria (Zustand/Context) | No sobrevive recarga — obligaría al usuario a repetir el setup en cada refresh. |
| `sessionStorage` | Muere al cerrar la pestaña; en la práctica los usuarios esperan que la sesión persista entre sesiones del navegador. |

---

## Decisiones Relacionadas
- ADL-003 (Local State Storage) — esta decisión concreta la política de persistencia cliente específicamente para el `session_id` del Data Agent.
- ADL-002 (E2E Testing Strategy) — complementa con el mecanismo concreto de inyección de sesión en Playwright.
- ADL-013 (Data Agent Architecture) — el `session_id` es el identificador que atraviesa todos los componentes descritos en esa arquitectura.

---

## Notas para el AI (Memoria Técnica)
- **Siempre** leer/escribir la sesión del Data Agent vía `localStorage.getItem("joi_session_id")` / `setItem`. No introducir cookies, nuevas keys ni contextos paralelos para transportar el `session_id`.
- En tests E2E de Playwright, usar el helper `gotoWithSession` (`frontend/e2e/data-agent.spec.ts`) o replicar su patrón con `page.addInitScript()`. **No** volver a interceptar requests con `page.route()` para inyectar sesión.
- Si se detectan integraciones de terceros en el frontend (analytics, tag managers), reabrir esta decisión — el `session_id` queda expuesto a cualquier script del mismo origen.
- Si el backend retorna error de sesión inválida, limpiar la key antes de reintentar el flujo de setup.
