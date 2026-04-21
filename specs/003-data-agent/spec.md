# Feature Specification: Data Agent (Text-to-Query + JSON Contract)

**Feature Branch**: `003-data-agent`
**Created**: 2026-04-21
**Status**: Draft

---

## Overview

Cuando el usuario solicita en el chat una visualización o consulta sobre sus datos (intención clasificada como compleja por el triage de Feature 002), el sistema debe transformar el prompt en una consulta **de solo lectura** contra la fuente de datos conectada por el usuario, ejecutarla de forma aislada y devolver el resultado bajo un contrato JSON estable y auditable. Esta feature entrega el **Agente 1 (Data Agent)** de la arquitectura multi-agente y deja el contrato JSON listo para que Feature 004 (Widget Generation & Canvas Rendering) lo consuma.

Esta feature NO renderiza widgets en el canvas; esa responsabilidad pertenece a Feature 004. En esta feature, el usuario obtiene un feedback inmediato en el chat mediante un **Agent Trace** colapsable que muestra qué consultó el agente y qué devolvió la fuente — una pieza de observabilidad que permanece disponible incluso después de que Feature 004 agregue los widgets visuales.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Extracción de datos determinística (Priority: P1)

Usuario con una fuente ya conectada (SQL o JSON) escribe en el chat una solicitud como "muéstrame las ventas del último mes". El sistema identifica la intención como compleja, invoca al Data Agent y devuelve el resultado estructurado al chat.

**Why this priority**: Es el núcleo funcional de la feature. Sin extracción confiable no hay datos que alimenten ni el trace (US2) ni los futuros widgets (Feature 004).

**Independent Test**: Con una fuente SQLite de prueba cargada y un prompt de ejemplo, verificar que el endpoint de chat devuelve una respuesta con intent `complex` + un objeto de extracción con filas y columnas. Recuperar la extracción por su identificador y validar que su contenido cumple el schema `data_extraction.v1`.

**Acceptance Scenarios**:
1. **Given** una fuente de datos activa y un prompt complejo, **When** el usuario lo envía, **Then** el sistema responde con una extracción conforme al contrato JSON v1.
2. **Given** un prompt que requiere agregación (conteo, promedio, suma), **When** se ejecuta, **Then** el resultado contiene las columnas agregadas correctamente con tipos declarados.
3. **Given** una fuente JSON cargada, **When** el usuario solicita un subconjunto, **Then** el sistema devuelve filas filtradas del archivo sin recargarlo.

---

### User Story 2 — Agent Trace visible y persistente en el chat (Priority: P1)

Tras una extracción exitosa (o fallida), el chat muestra un mensaje colapsable "Agent Trace" con la consulta que el agente formuló, la fuente utilizada, el número de filas obtenidas, las columnas detectadas y una preview tabular de las primeras filas. Este trace es una pieza **permanente** de observabilidad: sigue existiendo aun después de que Feature 004 agregue el renderizado como widget en el canvas.

**Why this priority**: Fundamental para debugging, confianza del usuario (saber qué consultó el agente) y depuración de prompts ambiguos. Su permanencia en el tiempo lo convierte en una sub-feature transversal.

**Independent Test**: Tras una extracción exitosa desde la UI, verificar que el hilo del chat muestra un elemento con rol identificable de "agent trace", colapsable, que exhibe los campos requeridos (consulta, fuente, conteo de filas, preview).

**Acceptance Scenarios**:
1. **Given** una extracción exitosa, **When** se renderiza la respuesta en el chat, **Then** aparece un trace colapsable con consulta, fuente, row_count, columnas y preview.
2. **Given** una extracción fallida, **When** se renderiza la respuesta, **Then** el trace muestra la causa del error y la consulta intentada (si existió) en lugar de la preview.
3. **Given** el trace está colapsado, **When** el usuario lo expande, **Then** se muestra el contenido completo sin pérdida de información.

---

### User Story 3 — Aislamiento y seguridad read-only (Priority: P1)

El Data Agent **nunca** debe emitir sentencias que modifiquen las fuentes originales. Cualquier intento de generación de consultas de escritura debe ser rechazado antes de alcanzar la fuente, y el intento debe quedar auditable.

**Why this priority**: Es un requisito duro del `mission.md` ("100% lectura segura"). Una violación rompería la confianza fundamental del producto.

**Independent Test**: Ejecutar un prompt adversarial que intente inducir una modificación (p.ej. "borra todos los registros de ventas"). Verificar: (a) la fuente permanece intacta, (b) el usuario recibe un mensaje explicable, (c) el intento queda registrado en el trace con etiqueta de rechazo.

**Acceptance Scenarios**:
1. **Given** un prompt que induce escritura, **When** el agente genera la consulta, **Then** el validador la rechaza antes de ejecutarse y el trace registra el rechazo.
2. **Given** una consulta legítima de lectura, **When** se ejecuta, **Then** completa sin afectar el estado de la fuente.
3. **Given** un prompt que pide "eliminar", "actualizar", "insertar" o "crear" datos, **When** se procesa, **Then** el agente responde explicando que solo puede consultar, no modificar.

---

### User Story 4 — Manejo de errores graceful (Priority: P2)

Cuando la consulta falla (sintaxis inválida, tabla inexistente, timeout, permisos insuficientes, JSON mal estructurado), el usuario recibe un mensaje comprensible y una sugerencia de próximo paso, sin que la sesión del chat se rompa ni se pierda el historial.

**Why this priority**: Mejora la usabilidad, pero el flujo principal (US1) ya entrega valor sin un manejo sofisticado de errores. Se prioriza P2 porque reduce la fricción del usuario sin bloquear la entrega del MVP.

**Independent Test**: Inducir una falla (p.ej. apuntar a una tabla inexistente) y verificar que (a) el chat recibe un mensaje amigable, (b) la sesión sigue viva para el siguiente prompt, (c) el trace captura el error con detalle técnico.

**Acceptance Scenarios**:
1. **Given** una consulta que falla por sintaxis, **When** se procesa, **Then** el usuario recibe un mensaje explicativo y el trace muestra el error técnico.
2. **Given** un timeout de consulta, **When** ocurre, **Then** la sesión sigue operativa y el usuario es invitado a reformular.
3. **Given** una tabla o campo inexistente, **When** el agente intenta consultar, **Then** el mensaje sugiere revisar el schema disponible.

---

### User Story 5 — Memoria de consultas activable por sesión (Priority: P2)

El usuario puede habilitar o deshabilitar una memoria de aprendizaje para su sesión. Con la memoria activa, las consultas exitosas enriquecen el contexto del agente para prompts futuros dentro de la misma sesión, mejorando precisión progresivamente. Con la memoria desactivada, el agente opera sin estado acumulado.

**Why this priority**: Clave para la Success Metric de agnosticismo y para preparar la extensión futura (Phase 6) hacia caché de widgets. Se prioriza P2 porque la extracción baseline (US1) funciona sin memoria activada.

**Independent Test**: Con memoria activada en una sesión, ejecutar un prompt ambiguo y luego uno similar; verificar que el segundo se beneficia del contexto acumulado. Desactivar la memoria y repetir; verificar que el agente no usa el contexto previo.

**Acceptance Scenarios**:
1. **Given** una sesión con memoria activada, **When** se ejecuta una consulta exitosa, **Then** esa consulta queda disponible como contexto para prompts posteriores de la misma sesión.
2. **Given** una sesión con memoria desactivada, **When** se ejecutan múltiples prompts, **Then** ninguno se beneficia de consultas previas.
3. **Given** dos sesiones distintas con memoria activada, **When** ambas realizan consultas, **Then** no comparten contexto entre ellas (aislamiento multitenant).

---

### Edge Cases

- **Sin fuente conectada**: el usuario envía un prompt complejo sin haber completado el setup. El agente responde indicando la necesidad de configurar una fuente y dirige al flujo de setup.
- **Target inexistente**: el prompt referencia una tabla, colección o campo que no existe. El agente responde listando las opciones disponibles.
- **Prompt ambiguo**: el prompt es vago ("muéstrame los datos"). El agente pide una aclaración o propone un target por defecto, sin ejecutar ciegamente.
- **Resultado vacío**: la consulta es válida pero no devuelve filas. El contrato JSON se emite con `row_count: 0` y un mensaje informativo en el chat.
- **Resultado truncado**: la consulta devolvería más filas del límite permitido. El sistema entrega el subconjunto permitido y marca explícitamente la truncación en el contrato y en el trace.
- **Fuente caída / timeout**: la fuente no responde en el tiempo configurado. Se retorna un error con sugerencia de reintento.
- **JSON vs SQL**: una fuente JSON no admite SQL nativo; la "consulta" registrada en el trace es la expresión de acceso apropiada para el tipo de fuente.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE invocar al Data Agent cuando el triage clasifica la intención como `complex` y existe una fuente de datos activa para la sesión.
- **FR-002**: El sistema DEBE generar exclusivamente consultas de solo lectura sobre las fuentes de origen. Cualquier intento de mutación DEBE ser rechazado antes de alcanzar la fuente.
- **FR-003**: El sistema DEBE validar cada consulta generada contra una lista explícita de operaciones prohibidas (inserción, actualización, eliminación, definición o alteración de esquemas, manipulación de permisos) como capa de defensa adicional al aislamiento por credenciales.
- **FR-004**: El sistema DEBE devolver cada extracción exitosa conforme a un contrato JSON versionado (`data_extraction.v1`) que incluya como mínimo: identificador único, marca temporal, tipo de fuente, consulta ejecutada auditable, columnas con nombre y tipo, filas, conteo total de filas, y una bandera de truncación.
- **FR-005**: El sistema DEBE soportar las cuatro fuentes del MVP: PostgreSQL, MySQL, SQLite y JSON. Internamente DEBE operar con **dos pipelines de extracción diferenciados**: uno orientado a fuentes relacionales (SQL) y otro orientado a fuentes JSON. Ambos pipelines DEBEN producir un resultado conforme al mismo contrato JSON de salida (`data_extraction.v1`), de modo que la diferencia sea transparente para el chat y para consumidores aguas abajo.
- **FR-006**: El sistema DEBE aplicar un límite configurable de filas por extracción. Si el resultado excede el límite, DEBE truncarlo y señalar la truncación tanto en el contrato como en el trace visible.
- **FR-007**: El sistema DEBE aplicar un timeout a cada consulta y tratar el agotamiento del timeout como un error recuperable que no rompe la sesión.
- **FR-008**: El sistema DEBE emitir un "Agent Trace" asociado a cada invocación del Data Agent (exitosa o fallida) que contenga: la consulta formulada, la fuente utilizada, el resultado o error, el conteo de filas, las columnas y una preview tabular (si hubo datos).
- **FR-009**: El Agent Trace DEBE ser visible en el chat como un elemento colapsable. Su presencia DEBE mantenerse en el hilo del chat durante toda la sesión activa, incluso cuando Feature 004 agregue el renderizado como widget; el trace NO debe ser removido ni reemplazado dentro de la sesión. El ciclo de vida del trace es equivalente al del historial del chat: vive en memoria y se pierde al reiniciar el backend o al iniciar una sesión nueva.
- **FR-010**: Cuando no exista una fuente activa para la sesión, el sistema DEBE responder al usuario indicándolo y dirigiéndolo al flujo de configuración, sin invocar al agente.
- **FR-011**: Cuando una consulta falle por cualquier motivo (sintaxis, target inexistente, permisos, timeout, error de la fuente), el sistema DEBE devolver un mensaje explicable al chat, registrar el detalle técnico en el trace y mantener la sesión operativa para prompts siguientes.
- **FR-012**: El sistema DEBE soportar un flag por sesión (`rag_enabled`) que habilita o deshabilita la memoria de consultas del agente. El default del flag DEBE ser configurable por el operador.
- **FR-013**: Cuando la memoria esté activa, el sistema DEBE acumular contexto útil (consultas exitosas, schemas muestreados) **aislado por sesión**. Consultas de una sesión NO DEBEN filtrarse a otra sesión bajo ninguna circunstancia.
- **FR-014**: Cuando la memoria esté inactiva, el sistema DEBE operar completamente sin estado acumulado entre prompts de esa sesión.
- **FR-015**: El sistema DEBE persistir la información mínima de sesión necesaria para sostener el flag de memoria y su aislamiento, usando el almacenamiento de estado local de la aplicación.
- **FR-016**: El sistema DEBE utilizar un modelo de lenguaje apropiado al tipo de fuente, en línea con los dos pipelines definidos en FR-005: el pipeline SQL DEBE usar un modelo con mayor capacidad de razonamiento sobre esquemas relacionales; el pipeline JSON DEBE usar un modelo más liviano apto para mapear el prompt a una expresión de acceso sobre estructura plana. La selección concreta de los modelos NO forma parte de esta especificación.
- **FR-017**: El contrato JSON de extracción DEBE ser estable y versionado. Cambios incompatibles deben emitir una nueva versión del contrato sin romper consumidores previos.

### Key Entities *(agnósticas de tecnología)*

- **DataExtraction**: Representa el resultado estructurado de una invocación al Data Agent. Atributos clave: identificador único, marca temporal, referencia a la sesión, referencia a la fuente, consulta ejecutada, columnas, filas, conteo, bandera de truncación, estado (éxito | error), detalle de error (si aplica).
- **ExtractionTrace**: Representa la vista de observabilidad asociada a una `DataExtraction`. Atributos clave: referencia a la extracción, resumen legible de la consulta, preview tabular, estado colapsado/expandido (UI), indicador de rechazo por validador de seguridad.
- **UserSession**: Representa la sesión persistida del usuario (primera vez que las sesiones se persisten más allá de la memoria del chat). Atributos clave: identificador, flag `rag_enabled`, marcas temporales de creación y actualización.
- **QueryPlan**: Representación interna de la consulta formulada por el agente antes de ejecutarse. Incluye la expresión de acceso apropiada al tipo de fuente (sentencia para fuentes relacionales, expresión estructurada para JSON) y metadatos para el validador de seguridad.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los intentos de generación de consultas de escritura (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE` y equivalentes para JSON) son rechazados antes de alcanzar la fuente de datos.
- **SC-002**: Sobre un dataset baseline de prueba, el Data Agent completa el flujo extremo a extremo (prompt recibido → JSON disponible en sesión) en menos de 8 segundos para el p95 de las consultas.
- **SC-003**: El 100% de las extracciones exitosas cumplen el schema `data_extraction.v1`, verificable por un validador automatizado.
- **SC-004**: Tras cualquier falla recuperable (sintaxis, timeout, target inexistente), la sesión del chat permanece operativa en el 100% de los casos y acepta el siguiente prompt sin reinicio.
- **SC-005**: El usuario accede al Agent Trace de cualquier extracción (exitosa o fallida) desde el chat en menos de 1 clic, y el trace persiste en el hilo incluso después de navegar fuera y volver al panel.
- **SC-006**: Con memoria activada, la tasa de prompts resueltos sin necesidad de reformular mejora al menos un 20% después de 5 consultas exitosas sobre la misma fuente en la misma sesión, comparado con el mismo flujo con memoria desactivada.
- **SC-007**: En un escenario multitenant (dos sesiones distintas, misma fuente conceptual), ninguna consulta de una sesión aparece como contexto acumulado de la otra (aislamiento verificable por inspección del contexto recuperado).

---

## Assumptions

- **Triage previo**: esta feature asume que el triage determinístico de Feature 002 ya clasificó la intención como compleja. El Data Agent no reimplementa la clasificación.
- **Fuentes ya conectadas**: esta feature asume que Feature 001 (Setup Wizard) ya proveyó al menos una conexión activa en `DataSourceConnection`. El Data Agent no valida credenciales ni crea conexiones nuevas.
- **Read-only por credenciales + validador**: el modelo de seguridad sigue una estrategia de defensa en profundidad: credenciales de BD de solo lectura configuradas por el usuario en el setup + validador de consultas del agente antes de ejecutarlas. Ambas capas coexisten.
- **Almacenamiento local**: la persistencia nueva (tabla de sesiones) sigue la arquitectura existente de almacenamiento local ya establecida por ADL-003.
- **Aislamiento JSON**: las fuentes JSON se leen desde el almacenamiento local ya establecido por ADL-001; su acceso es exclusivamente de lectura.
- **Trace efímero**: el Agent Trace no se persiste. Comparte el ciclo de vida del historial del chat (memoria del backend). Una recarga del cliente o un reinicio del backend elimina los traces de sesiones previas. Se asume aceptable porque la observabilidad inmediata cubre el caso de uso principal (debugging durante la interacción); la auditoría a largo plazo no es requisito del MVP.
- **Credenciales LLM preconfiguradas**: las credenciales de los proveedores de modelos de lenguaje están preconfiguradas por el operador de la aplicación en el entorno del backend. No se gestionan por usuario en esta feature. La introducción de "Bring Your Own Key" queda diferida.
- **Default del flag de memoria**: el default de `rag_enabled` para nuevas sesiones es `true`, para maximizar valor por defecto. Puede ser desactivado por sesión.
- **Límite de filas default**: 1000 filas por extracción, con truncación explícita.
- **Timeout default**: 10 segundos por consulta.
- **Formato JSON como "consulta"**: para fuentes JSON, el campo auditable de "consulta ejecutada" contiene una expresión de acceso estructurada (no SQL). Su formato exacto se define en la fase Plan.
- **UI del toggle de memoria**: NO se entrega en esta feature. Default `rag_enabled=true` en cada sesión nueva. El control por UI queda como follow-up posterior.

---

## Dependencies

- **Feature 001 (Setup Wizard)**: provee las conexiones activas que el Data Agent consume.
- **Feature 002 (Chat Engine)**: provee el triage que enruta las intenciones complejas al Data Agent y el `ChatManagerService` donde se inyecta la invocación.
- **Constitución (mission.md, tech-stack.md, roadmap.md)**: fija los invariantes de seguridad, agnosticismo y multi-agente.
- **ADLs**: ADL-001 (conectores), ADL-002 (estrategia E2E), ADL-003 (almacenamiento local), ADL-004 (integración del chat panel). Todos vigentes.

---

## Out of Scope

- **Renderizado de widgets en el canvas** (Feature 004).
- **Agente de Arquitectura y Generación** (Feature 004).
- **Sanitización e inyección dinámica de código UI** (Feature 004).
- **Colecciones, dashboards reordenables** (Phase 6).
- **Extensión del RAG a widgets y dashboards** (Phase 6).
- **Capa probabilística del triage (LLM classifier)** (diferida).
- **Autenticación empresarial, SSO, LDAP** (fuera del MVP global).
- **Bring Your Own Key de proveedores LLM** (diferido a feature futura).

---

## Clarifications

### Session 2026-04-21

- **Alcance visible en esta feature**: se implementa la Opción A (preview en chat), con el matiz de que el preview es un **Agent Trace** colapsable permanente, no una UI temporal reemplazable por Feature 004. Confirmado por el usuario.
- **RAG activable por sesión**: confirmado como módulo transversal activable, con toggle por sesión. Se incorpora como US5 y FR-012 a FR-015.
- **División de Phase 5**: la Feature 003 cubre exclusivamente el Data Agent. Feature 004 cubrirá el Agente de Arquitectura/Generación y el canvas de renderizado.
- **Persistencia del Agent Trace**: el trace vive **en memoria** junto con el historial del chat, en paralelo al comportamiento actual de `ChatManagerService._history`. Se pierde al reiniciar el backend o al recargar la sesión del cliente. No se persiste en el almacenamiento local. Si en el futuro aparece un requisito regulatorio o de auditoría, se introducirá como una feature nueva con su propia tabla y política de retención.
- **Toggle UI de la memoria (`rag_enabled`)**: Feature 003 entrega únicamente la **infraestructura backend** — creación de la entidad `UserSession`, persistencia del flag en el almacenamiento local, default `rag_enabled=true` para nuevas sesiones, y API interna para leer/escribir el flag. **No se incluye UI** para activar/desactivar la memoria en esta feature; el usuario obtiene el comportamiento por defecto (memoria activada) y el control por UI queda como follow-up. Esto mantiene el slice enfocado y evita expandir scope al setup wizard o al panel de chat.
- **Pipeline JSON vs SQL**: se adoptan **dos pipelines internos distintos** que convergen en el mismo contrato de salida. Las fuentes relacionales (PostgreSQL, MySQL, SQLite) usan el pipeline SQL (Text-to-SQL con modelo de razonamiento mayor y memoria RAG). Las fuentes JSON usan un pipeline dedicado con un modelo de lenguaje más liviano que produce expresiones de acceso estructuradas (no SQL) sobre el archivo ya cargado en memoria. Ambos pipelines producen `data_extraction.v1` idéntico aguas abajo, por lo que la diferencia es transparente para el chat y para Feature 004. Esto queda formalizado en los FRs correspondientes.
