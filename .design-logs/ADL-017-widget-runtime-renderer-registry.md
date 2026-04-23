# ADL-017: Widget Runtime Renderer Registry con Auto-Registro por Side-Effect

**Fecha:** 2026-04-23
**Estado:** Activo
**Área:** Arquitectura / Frontend runtime
**Autor:** AI Session

---

## Contexto

El runtime que corre dentro del iframe sandbox (T120, [frontend/src/lib/widget-runtime/entry.tsx](../frontend/src/lib/widget-runtime/entry.tsx)) debe despachar un `widget:init` entrante a uno de 8 renderers distintos según `spec.widget_type` (`table`, `bar_chart`, `line_chart`, `pie_chart`, `kpi`, `scatter_plot`, `heatmap`, `area_chart`).

Este runtime se empaqueta como un bundle IIFE (`esbuild --format=iife`) que se inyecta en el `srcdoc` del iframe. Tiene restricciones específicas:

- **Bundle size** (T132): debe quedar bajo 300KB gzipped. Cualquier renderer no usado debe ser tree-shakeable idealmente, pero en un IIFE eso no aplica — todo se incluye si se importa.
- **Extensibilidad**: post-MVP se planea habilitar modo Storybook (R2) con componentes dinámicos; la arquitectura debe permitir nuevos tipos sin reescribir el dispatcher.
- **Separación de responsabilidades**: el entry (orquestador del protocolo postMessage) no debería conocer los renderers individualmente; eso es violación de OCP y hace el archivo difícil de revisar cuando crece.

Dos estrategias típicas para este dispatch:

1. **Switch central**: `entry.tsx` hace `switch (spec.widget_type) { case "table": return <Table .../>; ...`.
2. **Registry con side-effect**: cada archivo renderer llama `registerRenderer(type, Component)` al cargarse; el entry simplemente consulta el registry.

---

## Decisión

Adoptamos el **registry con auto-registro por side-effect**, estructurado en tres piezas:

- [registry.ts](../frontend/src/lib/widget-runtime/registry.ts) — `Map<WidgetType, ComponentType<RendererProps>>` con `registerRenderer()` / `getRenderer()`.
- [renderers/index.ts](../frontend/src/lib/widget-runtime/renderers/index.ts) — barrel que importa cada archivo renderer por side-effect; `export {}` para forzar que sea un módulo.
- [entry.tsx](../frontend/src/lib/widget-runtime/entry.tsx) — importa `./renderers` al top-level (para disparar los side-effects) y luego llama `getRenderer(spec.widget_type)` para dispatch.

Añadir un renderer nuevo (T121–T128 y futuros) es una operación de dos líneas:

```ts
// en frontend/src/lib/widget-runtime/renderers/table.tsx
import { registerRenderer } from "../registry";
function TableRenderer({ spec, rows }: RendererProps) { /* ... */ }
registerRenderer("table", TableRenderer);

// en frontend/src/lib/widget-runtime/renderers/index.ts
import "./table";  // ← sólo se agrega esta línea
```

Ningún cambio en el entry ni en el registry.

---

## Justificación

- **Open/Closed Principle**: el entry queda cerrado a modificaciones cuando se añade un nuevo tipo de widget. Solo se abre el barrel y se crea un archivo nuevo.
- **Archivos pequeños y enfocados**: cada renderer vive solo, ~30–60 líneas. Code review se hace por renderer, no en un archivo monolítico.
- **Separación de contratos**: el entry habla protocolo (postMessage, ready/error/resize) y delega render al registry. Los renderers hablan UI; no ven el protocolo.
- **Testeable**: unit tests pueden registrar renderers mock, invocar el dispatcher y verificar que llama al correcto sin montar iframes reales.
- **Compatible con bundle IIFE**: los side-effects se ejecutan determinísticamente al cargar el bundle. No dependen de resolución dinámica en runtime.
- **Preparado para Storybook post-MVP**: si en el futuro se carga un renderer custom desde una URL o embed, basta con que ese módulo llame `registerRenderer()` al ejecutarse — mismo patrón.

---

## Consecuencias

### ✅ Positivas

- Añadir un widget_type nuevo es mecánico: archivo + línea en barrel. Sin riesgo de olvidarse de agregar un case en un switch.
- Los renderers no necesitan "saber" del dispatcher; solo conocen sus props (`{ spec, rows }`).
- El registry expone `listRegisteredTypes()` para debugging y para test coverage (se puede assertar que los 8 tipos están registrados).
- Un widget_type desconocido produce `widget:error` con code `SPEC_INVALID` de forma uniforme, sin crash del runtime.

### ⚠️ Trade-offs aceptados

- **Tree-shaking limitado**: en un bundle IIFE todos los renderers importados se incluyen, aunque un despliegue específico nunca los use. Aceptable: los 8 renderers caben en el presupuesto de 300KB (T132).
- **Orden de ejecución**: los side-effects corren en orden de import del barrel. No es un problema funcional (el registry es un Map, no hay dependencias entre renderers), pero hay que ser disciplinado si alguna vez se agrega lógica compartida en el barrel.
- **Magia implícita**: un desarrollador nuevo puede preguntarse "¿dónde se conecta el table renderer con el dispatch?" — la respuesta es "en el registry al importar". Mitigado con el comment en `renderers/index.ts` y este ADL.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| **Switch central en `entry.tsx`** | Viola OCP — cada nuevo tipo requiere modificar el entry. El entry mezcla protocolo y render. Difícil de revisar cuando crece a 8+ casos. |
| **Mapa literal importado** (`renderers = { table: TableRenderer, bar_chart: BarChartRenderer, ... }`) | Equivalente al registry en resultado, pero requiere tocar el diccionario central cada vez que se agrega un tipo. Pierde el beneficio de aislamiento de archivo. |
| **Dynamic import por string** (`await import(\`./renderers/${type}\`)`) | Incompatible con bundle IIFE (todos los chunks deben estar incluidos al empaquetar). Suma latencia de boot sin beneficio. |
| **Factory function con switch interno** | Solo traslada el switch a otra ubicación. No resuelve OCP. |
| **Decorator pattern (`@renderer("table")`)** | Requiere experimental decorators en TS config del runtime; complejidad sin beneficio frente a `registerRenderer()`. |

---

## Decisiones Relacionadas

- **Research R4** — iframe sandbox: el runtime corre aislado y recibe widgets vía postMessage. El registry es un detalle de implementación interno del bundle, no expuesto fuera del iframe.
- **Research R5** — bundle compartido: un solo `widget-runtime.bundle.js` contiene todos los renderers. El registry centraliza esa lista sin multiplicar el bundle.
- **ADL-002** — E2E testing strategy: los tests Playwright de T305/T306 pueden inspeccionar qué renderer está activo mirando el DOM, pero idealmente van a assertar el outcome (el widget se ve, no crashea) — no el detalle de registry.

---

## Notas para el AI (Memoria Técnica)

- **Nunca** importar renderers directamente en `entry.tsx`. El entry solo importa el barrel (`./renderers`), nunca `./renderers/table` individualmente.
- **Sí** añadir una línea `import "./<nombre>";` en `renderers/index.ts` cada vez que se cree un renderer. Sin eso, `registerRenderer()` no corre y `getRenderer()` devuelve `undefined`.
- Si en algún momento `listRegisteredTypes()` devuelve menos de 8 en producción, el problema es un import faltante en el barrel. Revisar primero ahí antes de debuggear el dispatcher.
- El registry NO es un singleton de módulo reusable fuera del iframe: cada bundle tiene su propio Map. Si la app principal necesitara un patrón similar (ej. para componentes del Canvas), debe construirse aparte — no importar este registry.
- Cuando llegue el modo Storybook post-MVP (R2), la estrategia natural es exponer `registerRenderer` al scope del iframe (ej. `window.WidgetRuntime.register`) y que el embed dinámico llame esa función. Esta ADL ya prepara ese terreno.
