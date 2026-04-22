# Research: Feature 004 — Widget Generation & Canvas Rendering

> Decisiones técnicas requeridas por el plan de implementación. Cada entrada tiene Decision / Rationale / Alternatives Considered, trazada a los FR del spec y a las clarificaciones acordadas en Session 2026-04-22.

---

## R1 — Catálogo de tipos de widget y reglas de aplicabilidad (FR-005, FR-004)

**Decisión**: se publica un catálogo cerrado de 8 tipos con reglas determinísticas de aplicabilidad basadas en la forma de la `DataExtraction` (número de columnas, tipos detectados, cardinalidad).

| Tipo | Código | Aplicabilidad mínima | Notas |
|---|---|---|---|
| Tabla | `table` | Siempre aplicable (fallback universal) | Cubre cualquier combinación de columnas/tipos. |
| Barras | `bar_chart` | ≥1 categórica (string, 2–50 valores únicos) + ≥1 numérica (integer/float) | Si hay varias numéricas, se usa la primera como default. |
| Líneas | `line_chart` | ≥1 temporal (datetime) o numérica ordenable + ≥1 numérica | Requiere orden; cardinalidad de la serie ≤ 500 puntos. |
| Pastel | `pie_chart` | 1 categórica (2–10 valores únicos) + 1 numérica positiva | Proporciones. Se descarta si hay negativos. |
| KPI | `kpi` | `row_count == 1` Y una única columna numérica, O una extracción agregada (`COUNT`, `SUM`, etc. inferido por alias) | Valor único destacado. |
| Scatter | `scatter_plot` | ≥2 numéricas, sin requerir categorías | Hasta 2000 puntos (por readability). |
| Heatmap | `heatmap` | 2 categóricas (cada una 2–30 valores únicos) + 1 numérica | Matriz de intensidad. |
| Área | `area_chart` | ≥1 temporal + ≥1 numérica (o misma combinación que líneas pero con acumulación permitida) | Útil para evolución. |

**Regla de selección determinística** (FR-004):

1. Si `row_count == 0` → estado vacío (no widget).
2. Si `row_count == 1` y 1 numérica → `kpi`.
3. Si 1 temporal + ≥1 numérica y ≤500 filas → `line_chart`.
4. Si 2 categóricas pequeñas + 1 numérica → `heatmap`.
5. Si 1 categórica pequeña + 1 numérica → `bar_chart` (o `pie_chart` si categórica ≤10 valores Y todos los numéricos positivos Y el heurístico pide proporción — conservador: default a `bar_chart`).
6. Si ≥2 numéricas sin categóricas → `scatter_plot`.
7. Fallback universal → `table`.

**Rationale**: determinístico = latencia cero + auditable + testeable, coherente con el guard SQL (ADL-005) y el triage (Feature 002).

**Alternatives considered**:
- Decisión del LLM: descartado en Clarify (no determinístico, latencia mayor).
- Híbrido heurística+LLM: descartado (doble camino, dos métricas que sostener). Podría reactivarse post-MVP si SC-007 no se cumple.

---

## R2 — Modos de render y selector de librería UI (FR-002, FR-002a, FR-002b)

**Decisión**: `RenderModeProfile` soporta tres modos, configurables en el Setup Wizard:

- `ui_framework` (default) — catálogo cerrado con shortlist **shadcn/ui, Bootstrap, HeroUI**. Agente genera código de componente usando elementos de la librería elegida, bajo un prompt pre-instruido.
- `free_code` — agente emite código ejecutable libre; misma superficie de aislamiento (FR-008), mayor dependencia del LLM.
- `design_system` — **inhabilitado en el MVP** (UI visible en el wizard con badge "próximamente", selección imposible).

**Default de librería UI**: `shadcn/ui` (coherente con tech-stack.md existente; Tailwind ya disponible).

**Rationale**: confirmado con el usuario en Clarify #1. Entrega flexibilidad sin sacrificar consistencia visual para el 80% que no va a tocar el wizard.

**Alternatives considered**:
- Modo único parametrizado (catálogo cerrado de chart configs JSON): descartado en Clarify.
- Modo único de código libre: descartado por superficie de ataque y calidad inconsistente.

---

## R3 — Estrategia de inyección del catálogo de componentes al LLM (FR-002b)

**Decisión** (resuelve el `[NEEDS CLARIFICATION]` pendiente en FR-002b): **System prompt cacheado por librería UI**, SIN RAG en el MVP.

Implementación:
- Por cada librería soportada (`shadcn`, `bootstrap`, `heroui`) se mantiene en el repo un "component manifest" estático: `backend/app/services/widget/manifests/<lib>.md` con la lista de componentes relevantes para visualizaciones (Card, Table, Tabs, Button, Chart primitives si aplica) + ejemplos mínimos de uso + restricciones.
- En runtime, el Agente Generador arma el prompt = system_prompt_base + manifest de la librería activa + WidgetSpec target + datos de la extracción.
- LiteLLM (ya configurado en Feature 003) activa **prompt caching** del proveedor cuando está disponible (Anthropic, OpenAI reciente), reutilizando el prefijo estable.

**Rationale**:
- Sin RAG: los manifests son estáticos (una librería = un manifest), caben en pocos KB. RAG sería overkill y suma latencia + store nuevo.
- Consistente con ADL-010 (RAG diferido post-MVP) y con la filosofía determinística.
- La cache del proveedor amortiza el costo de tokens del manifest.
- Cuando se reactive el modo Storybook (post-MVP), la misma estructura se extiende cargando componentes dinámicamente; el agente generador no cambia.

**Alternatives considered**:
- Chroma + embeddings del catálogo: descartado — volumen insuficiente para justificar vector store, y Chroma ya existe solo para memoria de Feature 003.
- Fine-tuning del modelo por librería: descartado — complejidad operativa masiva.
- Inyección completa del catálogo sin cache: descartado — costo de tokens y latencia en cada llamada.

---

## R4 — Mecanismo de aislamiento del Canvas (FR-008, FR-008a, FR-008b)

**Decisión**: **iframe sandbox + postMessage**, aplicado uniformemente a los tres modos de render.

**Flags de `sandbox`**:
```
sandbox="allow-scripts"
```
Sin `allow-same-origin`, sin `allow-top-navigation`, sin `allow-forms`, sin `allow-popups`. El iframe recibe `srcdoc` con HTML + CSS + JS del widget.

**Política CSP** inyectada en el documento del iframe:
```
Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'
```
Sin `connect-src`: el widget no puede llamar a red. Las imágenes solo como data URIs. Scripts y estilos inline son necesarios para ejecutar el bundle que se inyecta.

**Protocolo postMessage** (formalizado en `contracts/postmessage-protocol.schema.json`):

| Dirección | Tipo | Payload |
|---|---|---|
| App → iframe | `widget:init` | `{ widget_spec, data_rows, data_columns, theme }` |
| iframe → App | `widget:ready` | `{ extraction_id }` (confirma render completo) |
| iframe → App | `widget:error` | `{ extraction_id, code, message }` |
| iframe → App | `widget:resize` | `{ extraction_id, height }` |

**Bootstrapping timeout** (FR-008b): **4 segundos** desde `widget:init` hasta `widget:ready`. Si se vence, se dispara fallback (FR-009).

**Rationale**: confirmado en Clarify #2. Es el único mecanismo que aísla JS ejecutable hermético sin confiar en el código del widget. El costo de latencia (~50–100ms por bootstrap) es aceptable frente al SC-002 (6s p95).

**Alternatives considered**:
- Shadow DOM + CSP: menor aislamiento de JS, fragil frente a modo `free_code`. Descartado en Clarify.
- Híbrido (Shadow DOM para `ui_framework`, iframe para `free_code`): descartado por complejidad dual. El usuario prefirió uniformidad.
- Web Workers: no renderizan UI — no aplica.

---

## R5 — Librería del lado iframe para renderizar componentes (FR-007)

**Decisión**: **bundle compartido inyectado en el iframe** (un único `widget-runtime.bundle.js` servido por el backend/estático) que contiene:

- React 19 + ReactDOM (ya presente en frontend).
- Los adaptadores por librería UI (shadcn primitives, Bootstrap CSS, HeroUI).
- Una librería de charts mínima: **Recharts** (~50KB gzipped, buena cobertura del catálogo de R1: bar/line/area/scatter/pie; heatmap se implementa con SVG custom porque Recharts no lo incluye nativo).
- Un runtime dispatcher que recibe `widget:init` y renderiza según `widget_spec.widget_type`.

**Rationale**:
- Coherente con tech-stack.md (Next.js/React ya es el framework del frontend; reutilizar competencias).
- Un solo bundle = un solo cache del navegador = bootstrap rápido tras la primera carga.
- Recharts cubre 7/8 tipos del catálogo sin reinventar primitives SVG.
- Heatmap custom en SVG es ~50 líneas de código, aceptable.

**Alternatives considered**:
- Librerías chart distintas (Chart.js, ECharts, Vega-Lite): descartadas por tamaño o por no ser React-first.
- Generar primitives SVG para todo a mano: descartado, reinventa la rueda y perjudica SC-002.
- Importar charts vía CDN dinámico: descartado, incompatible con CSP (`connect-src 'none'`).

---

## R6 — Routing del modelo LLM para el Agente Generador (FR-016)

**Decisión**: nueva entrada en `LiteLLMClient` con `Purpose="widget"`, independiente de `sql` y `json` ya usados en Feature 003. Modelo default: el que el operador configure vía env var `LLM_MODEL_WIDGET` (fallback al default de LiteLLM).

**Rationale**: el propósito "generar código UI" es distinto de SQL (razonamiento relacional) y JSON (mapping ligero). Separar permite al operador elegir el modelo óptimo (p.ej. Claude Sonnet o GPT-4.1 con buena generación de código). Sin cambios estructurales en `litellm_client`; solo una clave más en el diccionario de routing.

**Alternatives considered**:
- Reusar `Purpose="sql"`: descartado, acopla decisiones operativas no relacionadas.
- Propósito por modo de render (ui_framework / free_code): descartado por prematuro; si post-MVP se detectan gaps de calidad, se introduce.

---

## R7 — Integración del selector de framework visual en el Setup Wizard (FR-002a, dep. con Feature 001)

**Decisión**: agregar un **Step 2** al Setup Wizard existente: **"Elige tu framework visual"**, disponible tras conectar al menos una fuente. Expone las tres opciones (shadcn/ui default, Bootstrap, HeroUI, Design System propio "próximamente" deshabilitado) y persiste la elección en una tabla nueva `render_mode_profiles` ligada al `session_id`.

Se consulta de forma lazy: si la sesión no tiene perfil al momento de generar un widget, se aplica el default (`ui_framework` + `shadcn`).

**Rationale**: honra el compromiso asumido en el spec (extensión explícita de Feature 001). No rompe el flujo actual — las sesiones existentes heredan el default sin migración.

**Alternatives considered**:
- Diálogo modal al primer widget: rechazado, rompe el flujo del chat.
- Parámetro por request en el chat: rechazado, fricción innecesaria.
- Perfil por `DataSourceConnection`: rechazado, el framework es visual (no depende de la fuente). Por sesión es suficiente.

---

## R8 — Fallback tabular y manejo de errores (FR-009, FR-010)

**Decisión**: el motor del Canvas mantiene un **renderer tabular embebido en el runtime bundle** que NO depende del Agente Generador. Cualquier fallo (generador timeout, spec inválida, iframe timeout, render error interno) dispara automáticamente un `WidgetSpec` de fallback con `widget_type="table"` construido a partir de `data_extraction.columns` y `data_extraction.rows`, sin invocar al LLM.

Se emite `WidgetGenerationTrace` con `status="fallback"` en la cadena del chat para transparencia.

**Rationale**: garantiza SC-004 (100% visualización útil) sin agregar paths extra. La construcción del fallback es pura transformación determinística.

**Alternatives considered**:
- Reintento automático del agente: descartado, suma latencia y opaca el problema real.
- Mensaje de error sin widget: descartado, viola SC-001.

---

## R9 — Persistencia y ciclo de vida del `CanvasState`

**Decisión**: **en memoria**, por sesión, exactamente igual que `ChatManagerService._history` y el `AgentTrace` de Feature 003. Se pierde al reiniciar el backend o al abrir una nueva sesión.

**Rationale**:
- Coherente con ADL-014 (sesión en localStorage, estado en memoria) y con la decisión del MVP de no persistir widgets (Phase 6 lo cambia).
- Simplifica enormemente: no hay migración, no hay garbage collection, no hay consultas al `joi_app.db`.

**Alternatives considered**:
- Persistir en `joi_app.db`: descartado, Phase 6 lo va a rehacer.
- Persistir en el cliente (localStorage): descartado, fragmentaría la observabilidad.

---

## R10 — Extensión del triage determinístico (FR-006a)

**Decisión**: se añade un segundo pass al `TriageEngine` actual (Feature 002) que, **cuando el intent ya es `complex` o cuando hay una extracción previa en la sesión**, busca en el mensaje patrones regex para mapear a tipos del catálogo. Si matchea, el resultado emite una señal `preferred_widget_type` en el `TriageResult`, consumida aguas abajo por el Agente Generador.

Ejemplos de patrones (lista inicial, puede ampliarse):
- `/\b(bar(ra|s)?|gr[aá]fico de barras|bar chart)\b/i` → `bar_chart`
- `/\b(tabla|table)\b/i` → `table`
- `/\b(l[ií]nea(s)?|line chart|serie(s)? temporal(es)?)\b/i` → `line_chart`
- `/\b(pastel|torta|pie|donut)\b/i` → `pie_chart`
- `/\b(kpi|indicador|m[eé]trica)\b/i` → `kpi`
- `/\b(scatter|dispersi[oó]n|puntos)\b/i` → `scatter_plot`
- `/\b(heatmap|mapa de calor)\b/i` → `heatmap`
- `/\b(área|area chart)\b/i` → `area_chart`

Si dos o más tipos matchean, **no se asume preferencia** (fallback a selección determinística de R1). Criterio conservador.

**Rationale**: confirmado en Clarify #5. Extiende — no reemplaza — el `TriageEngine` existente; retrocompatible.

**Alternatives considered**:
- Clasificador LLM: descartado en Clarify.
- Triage + LLM de respaldo: descartado por complejidad.

---

## R11 — Métricas de observabilidad del Agente Generador

**Decisión**: emitir (a) conteo de generaciones exitosas/fallbacks/errores por sesión, (b) latencia por etapa (triage → generación → iframe bootstrap → render ready), (c) distribución de tipos de widget. Storage: logs estructurados con `session_id` + `extraction_id`. No se introduce sistema de métricas externo en el MVP.

**Rationale**: necesario para evaluar SC-002 (p95 < 6s) y SC-007 (elección razonable 80%). Alcance liviano, no requiere infra adicional.

**Alternatives considered**:
- Prometheus: post-MVP.
- Datadog/Sentry: fuera de scope MVP.

---

## ADLs a crear en Implement

| ADL | Tema |
|---|---|
| ADL-016 | Widget generation architecture (R2, R3, R6 consolidados) |
| ADL-017 | Canvas iframe sandbox + postMessage protocol (R4, R5) |
| ADL-018 | Deterministic widget type selector (R1) |
| ADL-019 | RenderModeProfile & Setup Wizard extension (R7) |
