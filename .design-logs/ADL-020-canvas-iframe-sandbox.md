# ADL-020: Canvas iframe Sandbox — CSP, Bundle y Estrategia de Aislamiento

**Fecha:** 2026-04-23
**Estado:** Activo
**Área:** Arquitectura / Frontend / Seguridad
**Autor:** AI Session

---

## Contexto

Cada widget que genera Feature 004 ejecuta código JavaScript dentro del navegador. En el modo `ui_framework` este código es el runtime bundle (React + Recharts + renderers); en el modo `free_code` (post-MVP) será código emitido directamente por el LLM. En ambos casos el código corre en el contexto del usuario, en la misma pestaña que el chat principal.

El riesgo es doble:
1. **Ejecución maliciosa**: un widget adversarial podría modificar el DOM del host, exfiltrar cookies, redirigir la URL o hacer fetch a endpoints externos.
2. **Bugs del renderer**: un crash del widget no debe paralizar el chat — la sesión debe permanecer operativa (FR-009).

La decisión de aislamiento tiene que funcionar uniformemente para ambos modos de render.

---

## Decisión

### Mecanismo de aislamiento (R4)

Se usa `<iframe sandbox="allow-scripts" srcdoc="...">` como contenedor universal de todos los widgets.

**Flags de sandbox explícitos** — solo `allow-scripts`:
- ❌ `allow-same-origin` — excluido: preserva el origen opaco del iframe, impide acceso al DOM del host.
- ❌ `allow-top-navigation` — excluido: el widget no puede redirigir la URL del host.
- ❌ `allow-forms` — excluido.
- ❌ `allow-popups` — excluido.

**CSP inyectada en el `srcdoc`** (meta tag dentro del documento del iframe):
```
default-src 'none';
script-src 'unsafe-inline';
style-src 'unsafe-inline';
img-src data:;
connect-src 'none'
```

`connect-src 'none'` es la restricción más crítica: el widget no puede hacer fetch, XHR ni WebSocket a ningún destino — ni mismo origen. Las imágenes solo como data URIs. Scripts y estilos inline son necesarios para el bundle inyectado en `srcdoc`.

### Bundle compartido del runtime (R5)

Un único `widget-runtime.bundle.js` (IIFE, generado por esbuild) contiene:
- React 19 + ReactDOM
- Recharts (cubre 7/8 tipos del catálogo: bar/line/area/scatter/pie + table nativo + kpi)
- Heatmap en SVG custom (~50 líneas) — Recharts no lo incluye
- Renderer registry + dispatchers (ADL-017)
- Bindings validator (T408)

El bundle se sirve como asset estático del frontend. El `srcdoc` lo inyecta inline como `<script>`. Una vez cacheado por el navegador, el bootstrap de los widgets siguientes es ~50ms.

**Build**: `npm run build:widget-runtime` → `frontend/public/widget-runtime.bundle.js`.  
**No se commitea** (`.gitignore`). Se regenera en CI.  
**Tamaño verificado** (T132): 614 KB minified / **181.2 KB gzipped** — dentro del objetivo de 300 KB gzipped.

### Fallback ante fallo de render (FR-009)

Si el iframe no emite `widget:ready` dentro de los 4 segundos desde `widget:init` → `useCanvas` transiciona a estado `error` con código `RENDER_TIMEOUT`. El arquitecto fallback construye una tabla determinística desde la `DataExtraction`. El chat sigue operativo.

---

## Consecuencias

### ✅ Positivas
- Aislamiento hermético: probado con 5 patrones adversariales (T304) — ninguno afectó el host.
- Modelo uniforme para `ui_framework` y `free_code`: no hay bifurcación de lógica de seguridad.
- Bundle compartido = un solo cache del navegador; bootstrap rápido desde la segunda carga.

### ⚠️ Trade-offs aceptados
- `unsafe-inline` en `script-src` y `style-src` es necesario por el modelo `srcdoc`. No hay alternativa sin un servidor de nonces per-render.
- `connect-src 'none'` impide widgets que necesiten cargar datos externos (caso de uso post-MVP si se habilita modo Storybook).
- El bundle incluye TODOS los renderers aunque un widget use solo uno — tree-shaking no aplica en IIFE.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|---|---|
| Shadow DOM + CSP | Menor aislamiento de JS; frágil en modo `free_code` |
| Shadow DOM para `ui_framework`, iframe para `free_code` | Doble superficie de aislamiento, doble mantenimiento |
| Web Workers | No renderizan UI |
| CDN dinámico para charts | Incompatible con `connect-src 'none'` |

---

## Decisiones Relacionadas
- ADL-017: Widget runtime renderer registry
- ADL-018: Ciclo de vida de mensajes host ↔ iframe
- ADL-019: Arquitectura del agente generador (modos de render)

---

## Notas para el AI (Memoria Técnica)
- `sandbox="allow-scripts"` es el único flag permitido. No agregues `allow-same-origin` bajo ninguna circunstancia — anula el aislamiento de origen opaco.
- `connect-src 'none'` es no negociable en el MVP. Si un caso de uso requiere datos externos en el widget, escalar la decisión antes de cambiar la CSP.
- El bundle se genera con `npm run build:widget-runtime`. Si agregas un nuevo renderer, solo necesitas registrarlo en `renderers/index.ts` — el entry no cambia (ADL-017).
- El timeout de 4s está en `useCanvas.ts`. Si se ajusta, también actualizar el test `widget-timeout.spec.ts`.
