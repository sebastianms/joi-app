# Feature Specification: Widget Generation & Canvas Rendering

**Feature Branch**: `004-widget-generation`
**Created**: 2026-04-22
**Status**: Draft

---

## Overview

Cuando el Data Agent (Feature 003) emite una extracción exitosa conforme al contrato `data_extraction.v1`, el sistema debe transformarla en una **visualización viva** que aparezca en el panel derecho (Canvas) del usuario. Esta feature entrega el **Agente Arquitecto/Generador** (Agente 2 de la arquitectura multi-agente) y el **motor de Canvas dinámico** que renderiza el widget de forma aislada y segura, cerrando el último bloque de la Fase 5 del roadmap.

El Canvas hoy es un placeholder; al terminar esta feature, el panel derecho muestra widgets reales generados a demanda y los mantiene visibles durante la sesión, complementando el Agent Trace permanente del chat (que sigue siendo la fuente de observabilidad introducida en Feature 003).

Esta feature NO entrega colecciones, dashboards, ni edición persistente de widgets — esos son responsabilidad de la Phase 6 del roadmap. Aquí se entrega el ciclo completo "extracción → widget renderizado en pantalla" como un shippable slice independiente.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Visualización por defecto a partir de una extracción (Priority: P1)

Tras una extracción exitosa del Data Agent, el usuario ve un widget renderizado en el Canvas derecho que representa los datos devueltos. Sin tener que pedirlo explícitamente, el sistema selecciona una representación visual razonable (por ejemplo, una tabla cuando el resultado es tabular genérico, o un gráfico básico cuando la forma de los datos lo sugiere claramente).

**Why this priority**: Es el núcleo funcional de la feature. Sin un widget visible para una extracción exitosa, el Canvas sigue siendo un placeholder y la promesa central del producto ("interpretar datos y renderizar widgets en tiempo real") no se cumple.

**Independent Test**: Disparar una extracción exitosa de un dataset baseline (filas y columnas) desde el chat. Verificar que el panel derecho deja de mostrar el placeholder y exhibe un widget que refleja correctamente las columnas y filas devueltas, sin que el usuario haya tenido que dar instrucciones adicionales sobre el tipo de visualización.

**Acceptance Scenarios**:
1. **Given** una extracción exitosa con N>0 filas y al menos una columna, **When** el chat recibe la respuesta del Data Agent, **Then** el Canvas renderiza un widget cuya representación refleja todas las columnas y al menos las primeras filas del resultado.
2. **Given** una extracción exitosa con datos numéricos agregables (ej. una columna categórica + una columna numérica), **When** el sistema selecciona la visualización, **Then** el widget elegido es apto para esa forma de datos (ej. gráfico de barras, no una tabla cruda) y el usuario lo percibe como una mejora frente a una tabla.
3. **Given** una extracción exitosa con `row_count: 0`, **When** el Canvas la procesa, **Then** muestra un estado vacío informativo ("sin resultados para esta consulta") en lugar de un widget en blanco o un error.
4. **Given** una extracción con `truncated: true`, **When** se renderiza el widget, **Then** el widget incluye un indicador visible de truncación que comunica al usuario que está viendo un subconjunto del total.

---

### User Story 2 — Widget propuesto explícitamente por el usuario (Priority: P2)

El usuario puede expresar en el chat el tipo de visualización deseado ("muéstramelo como gráfico de líneas", "prefiero una tabla"). Cuando el deseo es expresable y compatible con la forma de los datos, el sistema honra esa preferencia para esa interacción y la usa para regenerar el widget actual.

**Why this priority**: Eleva la experiencia del usuario que sabe qué quiere ver. No bloquea el MVP porque US1 ya entrega un widget útil por defecto; US2 reduce fricción para usuarios avanzados.

**Independent Test**: Tras un widget renderizado por defecto (tabla), enviar un nuevo mensaje del tipo "muéstralo como gráfico de barras" y verificar que el Canvas reemplaza la tabla por un gráfico de barras coherente con los mismos datos, sin requerir reejecutar la extracción de datos.

**Acceptance Scenarios**:
1. **Given** un widget renderizado en el Canvas, **When** el usuario solicita un cambio de tipo de visualización compatible con los datos actuales, **Then** el Canvas actualiza el widget al nuevo tipo conservando los mismos datos sin re-ejecutar la consulta a la fuente.
2. **Given** una solicitud de tipo de visualización **incompatible** con los datos disponibles (ej. un gráfico de líneas sobre datos puramente categóricos sin orden), **When** el sistema intenta cumplirla, **Then** explica en el chat por qué no es aplicable y propone alternativas válidas, sin romper el widget actual.

---

### User Story 3 — Aislamiento visual y de ejecución del widget (Priority: P1)

El widget renderizado en el Canvas no debe poder afectar al chat, al setup wizard, ni a otros componentes de la aplicación: ni romper su estilo, ni leer su estado, ni ejecutar acciones fuera de su superficie. Si el agente generador produce código defectuoso o malicioso, el resto de la aplicación sigue operando.

**Why this priority**: Es un requisito duro derivado de la Success Metric "Cero modificaciones no deseadas" del [mission.md](../mission.md). Un widget que pueda contaminar la app rompe la confianza fundamental del producto, equivalente al rol que cumple el guard read-only en el Data Agent.

**Independent Test**: Inyectar manualmente una `WidgetSpec` adversarial (intenta acceder a cookies, modifica el DOM fuera de su contenedor, navega a otra URL, lanza un alert global). Verificar que: (a) el widget falla a renderizar o se muestra contenido pero el efecto adversarial NO ocurre, (b) el chat sigue operativo, (c) el incidente queda registrado de forma observable.

**Acceptance Scenarios**:
1. **Given** un widget cuyo código contiene una instrucción que intentaría modificar elementos fuera del Canvas, **When** se renderiza, **Then** el efecto queda confinado al contenedor del widget y el resto de la UI no se ve afectado.
2. **Given** un widget cuyo código intenta ejecutar una acción de navegación o redirección global, **When** se renderiza, **Then** la acción es bloqueada y el usuario percibe el widget en estado de error contenido en su contenedor.
3. **Given** un widget cuyo estilo intenta sobrescribir los estilos globales (ej. `body`, `html`, clases del chat), **When** se renderiza, **Then** los estilos aplican únicamente dentro de la superficie del widget.

---

### User Story 4 — Errores de generación o render no rompen la sesión (Priority: P2)

Cuando el Agente Generador no logra producir una `WidgetSpec` válida, o cuando el motor del Canvas no logra renderizar la spec recibida, el usuario obtiene un mensaje claro y un fallback útil (típicamente la representación tabular cruda de los datos), sin perder la extracción ni la sesión del chat.

**Why this priority**: Reduce fricción y aumenta confianza, pero no bloquea el MVP: US1 entrega el flujo principal exitoso. Se prioriza P2 porque los errores son inevitables en un sistema con LLMs.

**Independent Test**: Forzar una falla del agente generador (timeout, respuesta no parseable, spec inválida) y verificar que (a) el Canvas muestra un fallback (tabla cruda o mensaje), (b) el Agent Trace registra el error de generación, (c) el usuario puede mandar un nuevo prompt sin reiniciar nada.

**Acceptance Scenarios**:
1. **Given** una extracción exitosa pero un fallo del Agente Generador, **When** ocurre, **Then** el Canvas muestra como fallback la tabla cruda de los datos y un mensaje explicativo, y la sesión sigue operativa.
2. **Given** una `WidgetSpec` aparentemente válida pero que falla a renderizarse, **When** ocurre, **Then** el Canvas muestra un mensaje de error contenido en su superficie, y los widgets renderizados anteriormente en la sesión no se ven afectados.
3. **Given** cualquier falla del pipeline de generación o render, **When** ocurre, **Then** el evento queda registrado en el Agent Trace con código y mensaje, en línea con la observabilidad ya establecida en Feature 003.

---

### Edge Cases

- **Extracción con error**: si la `data_extraction.v1` llega con `status: "error"`, el Canvas no intenta renderizar un widget; muestra un estado correspondiente al error y deja la observabilidad al chat.
- **Sucesivas extracciones**: cuando el usuario hace una nueva consulta antes de "guardar" el widget actual, el Canvas reemplaza el widget anterior por el nuevo. La gestión de múltiples widgets simultáneos (colecciones, dashboards) queda fuera de scope.
- **Datos extremos**: extracciones con muchísimas columnas o filas truncadas al máximo; el widget seleccionado debe seguir siendo legible o degradar a tabla con scroll.
- **Tipos heterogéneos**: una columna marcada como `unknown` no debe romper la generación; el widget la trata como string o la oculta de forma segura.
- **Latencia del agente**: la generación del widget toma tiempo; el Canvas debe mostrar un estado de carga discernible y no quedar en blanco.
- **Mensaje del usuario sin extracción previa**: una solicitud de cambio de visualización sin un widget previo debe responder explicando que primero hay que pedir datos, sin error.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE invocar al Agente Arquitecto/Generador cada vez que el Data Agent emita una extracción con `status: "success"` y `row_count > 0`, sin requerir intervención adicional del usuario.
- **FR-002**: El Agente Arquitecto/Generador DEBE producir una **WidgetSpec** versionada (`widget_spec.v1`) que describa de forma autocontenida el widget a renderizar: tipo de visualización, datos bindeados (o referencia a la extracción origen), opciones visuales mínimas, y metadatos de auditoría (modelo usado, timestamp, referencia al `extraction_id`, **modo de render activo**).
- **FR-002a**: El sistema DEBE soportar al menos tres **modos de render** de widget, seleccionables por el usuario durante la configuración inicial (Setup Wizard) y persistidos por sesión/conexión:
  - **(a) Framework UI preseleccionado** — el agente produce una WidgetSpec que referencia componentes de una librería conocida por el sistema (por ejemplo shadcn/ui, Bootstrap, HeroUI). El LLM generador opera pre-instruido con el catálogo de componentes de esa librería, sin tener que descubrirlo en cada llamada.
  - **(b) Código UI libre generado por el LLM** — el agente produce código de componente ejecutable, sin amarre a un catálogo. Mayor flexibilidad, mayor superficie de aislamiento exigida al Canvas.
  - **(c) Design System propio vía Storybook** — el agente se instruye con los componentes del Design System cargado por el usuario. **Diferido a post-MVP**; el modo queda declarado en el contrato y en la UI del wizard, pero en esta feature se entrega inhabilitado con un mensaje "próximamente".
- **FR-002b**: Cuando el modo de render activo sea **Framework UI preseleccionado**, el sistema DEBE poner a disposición del Agente Generador el catálogo de componentes de la librería elegida de forma **eficiente** (sin re-transmitirlo completo en cada invocación). La estrategia concreta para cumplirlo — por ejemplo, un índice recuperable tipo RAG, un system prompt cacheado, o componentes embebidos — se decide en la fase Plan. [NEEDS CLARIFICATION: estrategia de inyección de catálogo de componentes al LLM generador].
- **FR-003**: La WidgetSpec DEBE ser un contrato estable y versionado entre el agente y el Canvas, equivalente en madurez al contrato `data_extraction.v1`. Cambios incompatibles emiten una nueva versión sin romper consumidores previos.
- **FR-004**: El sistema DEBE seleccionar automáticamente un tipo de widget razonable a partir de la forma de los datos (columnas, tipos, conteos) cuando el usuario no exprese una preferencia explícita. La selección DEBE ser **determinística**: aplica un conjunto de reglas heurísticas sobre la forma de la extracción (número y tipos de columnas, cardinalidad, presencia de columnas temporales, etc.) que devuelven exactamente un tipo del catálogo de FR-005 o, en último recurso, "tabla" como fallback universal. El Agente Generador NO participa en la elección del tipo cuando no hay preferencia explícita: solo produce la configuración visual (bindings, etiquetas, formato) del tipo ya elegido por la heurística. Las reglas concretas se detallan en Plan y deben ser auditables y testeables.
- **FR-005**: El sistema DEBE soportar al menos los siguientes **ocho tipos de visualización** en el MVP, todos disponibles transversalmente para los tres modos de render (FR-002a):
  - **Tabla** — representación tabular cruda; default seguro para datos heterogéneos.
  - **Gráfico de barras** — categórica + numérica.
  - **Gráfico de líneas** — series temporales o categóricas ordenadas.
  - **Gráfico de pastel** — proporciones de un total.
  - **KPI numérico** — un único valor agregado destacado.
  - **Gráfico de dispersión (scatter)** — relación entre dos numéricas.
  - **Heatmap** — matriz de intensidad sobre dos dimensiones discretas.
  - **Gráfico de área** — series acumulativas o evolución de magnitudes.

  Para cada tipo, el sistema DEBE definir explícitamente las **reglas de aplicabilidad** sobre la forma de los datos de la extracción (cuántas columnas, qué tipos, cardinalidad mínima/máxima), de modo que la selección automática (FR-004) y la validación de preferencia explícita (FR-006) sean determinísticas. Las reglas concretas se detallan en Plan.
- **FR-006**: Cuando el usuario exprese explícitamente un tipo de visualización en el chat, el sistema DEBE intentar honrarla sobre los datos del widget actual sin re-ejecutar la consulta a la fuente. Si la preferencia es incompatible con los datos (regla de aplicabilidad del tipo en FR-005 no se cumple), DEBE explicarlo en el chat y proponer alternativas válidas del catálogo.
- **FR-006a**: La detección de preferencia explícita de tipo de visualización DEBE ocurrir como **extensión del triage determinístico** ya introducido por Feature 002: reglas regex/keyword sobre el mensaje del usuario mapean frases al tipo correspondiente del catálogo de FR-005 (por ejemplo: "barras", "gráfico de barras", "bar chart" → `bar_chart`; "tabla", "table" → `table`; y equivalentes para líneas, pastel, KPI, scatter, heatmap, área). Cuando ninguna regla matchea con confianza, el sistema trata el mensaje como sin preferencia explícita y delega el flujo a la selección determinística de FR-004. NO se introduce un clasificador LLM adicional en esta feature.
- **FR-007**: El motor del Canvas DEBE renderizar la WidgetSpec en el panel derecho de la UI, reemplazando cualquier widget previamente visible para la sesión.
- **FR-008**: El motor del Canvas DEBE aislar la ejecución y el estilo del widget de tal forma que el código del widget NO PUEDA: (a) modificar elementos del DOM fuera de su contenedor, (b) leer cookies, almacenamiento local u otra información de la app principal, (c) navegar la ventana principal a otra URL, (d) sobrescribir estilos globales. La estrategia de aislamiento es **iframe sandbox con comunicación vía postMessage**, aplicada uniformemente a los tres modos de render (FR-002a). Los flags concretos del atributo `sandbox`, la política CSP del iframe y el protocolo postMessage se detallan en Plan.
- **FR-008a**: La comunicación entre la app principal y el widget aislado DEBE ocurrir exclusivamente por un **protocolo postMessage versionado y tipado**, que cubra como mínimo: inyección inicial de `WidgetSpec` + datos, notificación de render completo, notificación de error del widget, y solicitud de redimensionado. Mensajes no conformes al protocolo DEBEN ser ignorados.
- **FR-008b**: El motor del Canvas DEBE aplicar un **timeout de bootstrapping** al iframe: si el widget no reporta render completo dentro del umbral, se trata como fallo de render y se dispara el fallback de FR-009. El umbral concreto se fija en Plan.
- **FR-009**: Cuando el motor del Canvas reciba una WidgetSpec que no pueda renderizar (spec inválida, error de ejecución, dependencia faltante), DEBE mostrar un mensaje de error contenido en la superficie del Canvas y exponer como fallback la representación tabular cruda de los datos asociados, sin afectar al chat ni a la sesión.
- **FR-010**: Cuando el Agente Arquitecto/Generador falle en producir una WidgetSpec válida (timeout, respuesta no parseable, validación fallida del contrato), el sistema DEBE entregar al Canvas una WidgetSpec de fallback equivalente a "tabla cruda de los datos extraídos" para mantener un resultado visible al usuario.
- **FR-011**: El sistema DEBE registrar cada invocación del Agente Arquitecto/Generador (exitosa o fallida) en el Agent Trace de la conversación, en línea con el mecanismo introducido por Feature 003. El trace DEBE incluir como mínimo: referencia al `extraction_id` de origen, tipo de widget seleccionado (o intento), modelo utilizado, estado (éxito | fallback | error) y mensaje legible.
- **FR-012**: El sistema DEBE mostrar un estado de carga discernible en el Canvas mientras el Agente Generador está trabajando, evitando que el panel derecho quede en blanco entre la extracción y el renderizado.
- **FR-013**: El sistema DEBE comunicar visualmente al usuario cuando el widget representa un resultado **truncado** (`truncated: true` en la extracción origen), de modo que el usuario pueda decidir si reformular para obtener más datos.
- **FR-014**: El motor del Canvas DEBE preservar el estado del widget actual mientras el siguiente widget está siendo generado; el reemplazo ocurre solo cuando la nueva WidgetSpec esté lista o haya fallado a un fallback.
- **FR-015**: Cuando el Data Agent emita una extracción con `status: "error"`, el sistema NO DEBE invocar al Agente Generador; el Canvas DEBE reflejar el estado de error correspondiente o mantener su estado previo, dejando el detalle en el Agent Trace existente.
- **FR-016**: El sistema DEBE utilizar un modelo de lenguaje apropiado al propósito de generación de widgets, distinto e independiente de los modelos usados por el Data Agent (`sql` y `json`). La selección concreta NO forma parte de esta especificación; se gobierna por la capa de routing de modelos ya establecida.

### Key Entities *(agnósticas de tecnología)*

- **WidgetSpec**: Contrato de salida del Agente Arquitecto/Generador. Atributos clave: identificador único, versión del contrato, referencia a la `data_extraction` origen, **modo de render activo** (framework UI preseleccionado | código libre | design system propio), tipo de visualización elegido, datos bindeados (o referencia explícita al `extraction_id`), opciones visuales mínimas (título, etiquetas de ejes, formato de columnas relevantes), metadatos de auditoría (modelo generador, timestamp, motivo de la elección, librería/design system en uso si aplica).
- **RenderModeProfile**: Configuración por sesión/conexión que fija el modo de render activo y, si aplica, la librería UI seleccionada. Se inicializa durante el Setup Wizard (o hereda el default del operador) y es consultado tanto por el Agente Generador como por el motor del Canvas para instrumentarse de manera coherente. Ciclo de vida persistido en el almacenamiento local, en línea con el resto de la configuración del wizard (ADL-003).
- **CanvasState**: Estado actual del panel derecho para una sesión. Atributos clave: WidgetSpec activa (si existe), estado de carga, último error visible (si existe), referencia al `session_id`. Su ciclo de vida es equivalente al historial del chat: vive en memoria de sesión y NO se persiste (consistente con el ciclo del Agent Trace establecido en Feature 003).
- **WidgetGenerationTrace**: Vista de observabilidad asociada a cada invocación del Agente Generador. Atributos clave: referencia al `extraction_id`, tipo de widget intentado, estado (éxito | fallback | error), mensaje legible, modelo usado, timestamp. Se integra al Agent Trace existente del chat sin sustituirlo.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En el 100% de las extracciones exitosas con `row_count > 0`, el usuario ve un widget renderizado en el Canvas (sea el seleccionado por el agente o el fallback tabular). En ningún escenario el Canvas queda en blanco tras una extracción exitosa.
- **SC-002**: El tiempo desde que el Data Agent emite la extracción hasta que el widget aparece en el Canvas es menor a 6 segundos en el p95 de las consultas baseline.
- **SC-003**: El 100% de los intentos de un widget para acceder, modificar o navegar fuera de su contenedor son contenidos por el aislamiento del Canvas, verificable por una suite de pruebas adversariales.
- **SC-004**: Tras cualquier fallo del Agente Generador (timeout, spec inválida, respuesta no parseable), el usuario obtiene una visualización útil (mínimo: tabla cruda) en el 100% de los casos, y la sesión del chat sigue operativa para el siguiente prompt.
- **SC-005**: Cuando el usuario solicita explícitamente un tipo de visualización compatible con los datos actuales, el Canvas refleja el cambio en menos de 3 segundos en el p95, sin re-ejecutar la consulta a la fuente.
- **SC-006**: Cada invocación al Agente Generador (exitosa o fallida) produce una entrada visible en el Agent Trace del chat, accesible desde el chat en menos de 1 clic.
- **SC-007**: Sobre un conjunto baseline de extracciones representativas, la elección automática de tipo de widget es percibida como "razonable o mejor" por evaluadores humanos en al menos el 80% de los casos.

---

## Assumptions

- **Extracción ya disponible**: esta feature asume que el Data Agent (Feature 003) ya emitió una `data_extraction.v1` válida. La feature NO re-ejecuta consultas a las fuentes de datos.
- **Agent Trace ya operativo**: esta feature reutiliza el mecanismo de Agent Trace ya introducido por Feature 003 — el `WidgetGenerationTrace` se integra como una entrada adicional, no como un sistema paralelo.
- **Canvas único**: en esta feature, el Canvas mantiene **un solo widget visible a la vez por sesión**. El soporte de múltiples widgets simultáneos (colecciones, dashboards) pertenece a la Phase 6 del roadmap.
- **Sin persistencia de widgets**: los widgets generados NO se guardan al cerrar la sesión o reiniciar el backend. La persistencia y el guardado en colecciones son responsabilidad de la Phase 6.
- **Default sin preferencia**: cuando el usuario no exprese tipo de visualización, el sistema decide por sí mismo. El usuario nunca queda atrapado en un diálogo bloqueante para elegir tipo de widget.
- **Catálogo mínimo cubre el MVP**: para el MVP basta con un conjunto pequeño de tipos de visualización. La extensión del catálogo es iterativa post-MVP.
- **Credenciales LLM preconfiguradas**: las credenciales del proveedor del modelo generador están preconfiguradas por el operador, igual que en Feature 003.
- **Contrato versionado**: la WidgetSpec sigue la misma política de versionado que `data_extraction.v1`. La primera versión publicada es `widget_spec.v1`.
- **Triage extendido o no**: la detección de preferencia explícita de visualización en el chat se resuelve en Plan; si requiere extender el triage o agregar un clasificador específico es una decisión técnica, no de producto.
- **Extensión del Setup Wizard**: esta feature asume que el Setup Wizard (Feature 001) se extiende con un paso de **selección de framework visual** (modos de render a/b/c). Ese paso estaba diferido en el roadmap como "Módulo de selección de framework UI y carga de Design System" y se reactiva como parte del alcance de 004. La UI concreta y el flujo del wizard se detallan en Plan.
- **Modo default**: cuando el usuario no elija en el wizard, el default es **(a) Framework UI preseleccionado** con la librería concreta definida en Plan, por ser el modo con menor superficie de ataque y mayor consistencia visual.

---

## Dependencies

- **Feature 003 (Data Agent)**: provee el contrato de entrada `data_extraction.v1` y el mecanismo de Agent Trace.
- **Feature 002 (Chat Engine)**: provee el flujo conversacional donde se reciben preferencias explícitas de visualización (US2) y donde se exhibe el `WidgetGenerationTrace`.
- **Feature 001 (Setup Wizard)**: (a) asegura que existe una conexión activa que ya alimentó la extracción; (b) DEBE extenderse con un paso de selección de framework visual (modos de render) que alimenta la entidad `RenderModeProfile` de esta feature.
- **Constitución ([mission.md](../mission.md), [tech-stack.md](../tech-stack.md), [roadmap.md](../roadmap.md))**: la feature satisface el bloque pendiente de la Fase 5 del roadmap y respeta los invariantes de agnosticismo y aislamiento.

---

## Out of Scope

- **Colecciones y guardado de widgets** (Phase 6).
- **Dashboards reordenables y multi-widget simultáneo** (Phase 6).
- **RAG / memoria caché de widgets generados** (Phase 6).
- **Edición visual del widget por parte del usuario** (post-MVP).
- **Exportación del widget a archivos externos** (post-MVP).
- **Re-ejecución automática de la consulta de datos al cambiar de tipo de widget** (US2 explícitamente trabaja sobre los datos ya extraídos).
- **Capa probabilística del triage para clasificar la preferencia de visualización** (puede aparecer en Plan, pero su construcción detallada queda fuera de scope si se decide diferir).

---

## Clarifications

### Session 2026-04-22

- **Formato de salida del generador (modos de render múltiples)**: el sistema expone al usuario la elección del "framework visual" durante el Setup Wizard, con tres modos: (a) **Framework UI preseleccionado** (shadcn/ui, Bootstrap o HeroUI), donde el LLM generador opera pre-instruido con el catálogo de componentes para eficiencia y consistencia; (b) **Código UI libre generado por el LLM**, para máxima flexibilidad visual; (c) **Design System propio vía Storybook**, diferido a post-MVP (UI disponible pero modo inhabilitado). La estrategia concreta de inyección eficiente del catálogo al LLM en el modo (a) — RAG, system prompt cacheado, etc. — se decide en Plan y queda marcada como `[NEEDS CLARIFICATION]` en FR-002b. Formalizado en FR-002, FR-002a, FR-002b y en la entidad `RenderModeProfile`.
- **Estrategia de aislamiento del Canvas**: se adopta **iframe sandbox con postMessage** como mecanismo único de aislamiento, aplicado uniformemente a los tres modos de render. Razón: los modos (b) Código libre y (c) Design System propio amplían la superficie de ataque, por lo que conviene la opción de aislamiento más hermético. Detalles de flags `sandbox`, CSP y protocolo postMessage se detallan en Plan. Formalizado en FR-008, FR-008a y FR-008b.
- **Catálogo de tipos de widget para el MVP**: se adopta el **catálogo amplio** de ocho tipos: tabla, barras, líneas, pastel, KPI numérico, scatter, heatmap y área. Cada tipo lleva asociadas reglas explícitas de aplicabilidad sobre la forma de los datos, que aterrizan en Plan. Formalizado en FR-005.
- **Selector del tipo por defecto**: se adopta un selector **100% determinístico** basado en heurísticas sobre la forma de los datos de la extracción. Razón: latencia cero, elección auditable y testeable, alineación directa con el mismo principio que rige el triage determinístico de Feature 002 y el guard SQL de Feature 003. El Agente Generador no decide el tipo cuando no hay preferencia explícita; solo configura el tipo ya elegido. Formalizado en FR-004.
- **Detección de preferencia explícita en el chat (US2)**: se **extiende el triage determinístico** de Feature 002 con reglas regex/keyword que mapean frases ("barras", "gráfico de líneas", "scatter", etc.) a tipos del catálogo. NO se introduce un clasificador LLM adicional en esta feature. Formalizado en FR-006 y FR-006a.

## Pendientes para la fase Clarify

Estos puntos NO bloquean la spec pero requieren resolución antes del Plan. Se resolverán uno por uno en las próximas preguntas de Clarify:

1. ~~**Formato de salida del generador**~~ — resuelto en Session 2026-04-22 (modos de render múltiples).
2. ~~**Estrategia de aislamiento del Canvas**~~ — resuelto en Session 2026-04-22 (iframe sandbox + postMessage).
3. ~~**Catálogo mínimo de tipos de widget**~~ — resuelto en Session 2026-04-22 (catálogo amplio de 8 tipos).
4. ~~**Selector del tipo por defecto**~~ — resuelto en Session 2026-04-22 (heurística determinística).
5. ~~**Detección de preferencia explícita en el chat (US2)**~~ — resuelto en Session 2026-04-22 (extensión del triage determinístico).
6. **Estrategia concreta de inyección del catálogo de componentes al LLM en el modo Framework UI** (RAG, system prompt cacheado, embeddings, etc.). Afecta FR-002b. **Decisión técnica** — se resuelve en Plan, no requiere nueva pregunta de Clarify.
