# Feature Specification: Dashboards, Collections & RAG Cache

**Feature Branch**: `005-dashboards-collections`
**Created**: 2026-04-24
**Status**: Draft
**Phase**: Phase 6 — Shippable Slice 4

---

## Contexto

Hasta Feature 004, Joi-App genera widgets bajo demanda pero **los widgets son volátiles**: al recargar la sesión o cambiar de prompt, se pierden. El usuario no puede:

- Guardar un widget útil para consultarlo luego.
- Componer una vista persistente con varios widgets (dashboard).
- Reutilizar widgets previos cuando pregunta algo semánticamente equivalente (cada prompt gasta tokens y tiempo del Agente Generador).

Feature 005 cierra ese loop entregando **persistencia y reuso** sobre la base multi-agente ya funcional. Incluye además la activación del **RAG como caché de widgets** — infraestructura que hasta ahora estaba diferida (ADL-010) y que el usuario confirmó como parte del MVP de esta feature.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Guardar un widget en una colección (Priority: P1)

**Como** usuario que acaba de generar un widget útil,
**quiero** etiquetarlo y guardarlo en una colección nombrada,
**para** poder volver a él en sesiones posteriores sin re-prompting.

**Why this priority**: Sin persistencia, todo valor generado se pierde al cerrar la pestaña. Es el prerrequisito de todo lo demás (dashboards, RAG, recuperación desde chat).

**Independent Test**: Generar un widget, presionar "Guardar", asignarle nombre y colección, recargar la app, abrir la colección y verificar que el widget aparece y se re-renderiza correctamente.

**Acceptance Scenarios**:
1. **Given** un widget recién generado en el canvas, **When** el usuario hace click en "Guardar" y selecciona una colección existente, **Then** el widget queda asociado a esa colección y persiste entre sesiones.
2. **Given** el usuario está guardando un widget, **When** ingresa un nombre de colección que no existe, **Then** el sistema crea la colección y asocia el widget.
3. **Given** un widget sin datos asociados (fallback o error), **When** el usuario intenta guardar, **Then** el sistema rechaza la acción con mensaje claro.

---

### User Story 2 — Administrar colecciones (Priority: P1)

**Como** usuario con múltiples widgets guardados,
**quiero** listar, renombrar, eliminar y reubicar widgets entre colecciones,
**para** mantener mi biblioteca organizada.

**Why this priority**: Sin gestión básica, las colecciones se vuelven inusables después de pocas semanas.

**Independent Test**: Crear dos colecciones con widgets, renombrar una, mover un widget entre ellas, eliminar la otra y verificar que los widgets afectados se comportan según la regla de cascada definida.

**Acceptance Scenarios**:
1. **Given** al menos una colección con widgets, **When** el usuario abre la vista de colecciones, **Then** ve la lista con nombre, conteo de widgets y fecha de última modificación.
2. **Given** una colección existente, **When** el usuario la renombra, **Then** el cambio persiste y se refleja en todas las referencias.
3. **Given** un widget en Colección A, **When** el usuario lo mueve a Colección B, **Then** deja de aparecer en A y aparece en B.
4. **Given** una colección con widgets, **When** el usuario la elimina, **Then** el sistema pregunta si eliminar en cascada o mover los widgets a "Sin colección" (decisión por Clarify).

---

### User Story 3 — Componer un dashboard (Priority: P1)

**Como** usuario que guardó varios widgets relacionados,
**quiero** arrastrarlos a un dashboard personalizado con layout en grid,
**para** tener una vista consolidada de los datos que me importan.

**Why this priority**: Es el entregable distintivo de Joi-App frente a un generador one-shot: convertir widgets sueltos en una vista viva y reordenable.

**Independent Test**: Crear un dashboard, arrastrar tres widgets desde distintas colecciones, reordenarlos en el grid, cerrar y reabrir la app, verificar que el layout persiste.

**Acceptance Scenarios**:
1. **Given** al menos un widget guardado, **When** el usuario crea un nuevo dashboard y lo nombra, **Then** el dashboard queda disponible para añadir widgets.
2. **Given** un dashboard vacío, **When** el usuario arrastra widgets desde una colección, **Then** los widgets se añaden y pueden reposicionarse y redimensionarse en un grid.
3. **Given** un dashboard con layout personalizado, **When** el usuario recarga la aplicación, **Then** el layout se restaura exactamente igual.
4. **Given** un widget en un dashboard, **When** el usuario lo elimina del dashboard, **Then** desaparece de esa vista pero permanece en su colección.
5. **Given** un dashboard abierto, **When** la fuente de datos original del widget no está disponible, **Then** el widget muestra un estado de alerta (decisión final sobre comportamiento en Clarify Q5) sin romper los demás widgets.

---

### User Story 4 — Recuperar widget guardado desde el chat (Priority: P2)

**Como** usuario conversando con Joi,
**quiero** pedir "muéstrame el widget de ventas Q1" y que Joi recupere uno ya guardado,
**para** no tener que navegar a colecciones ni regenerarlo.

**Why this priority**: Mejora el flujo conversacional pero no es bloqueante: el usuario puede navegar manualmente si US4 no está.

**Independent Test**: Guardar un widget con nombre "Ventas Q1", en una nueva conversación pedir "muéstrame Ventas Q1", verificar que aparece en el canvas sin regeneración.

**Acceptance Scenarios**:
1. **Given** un widget guardado con nombre identificable, **When** el usuario lo menciona en el chat, **Then** el triage reconoce la intención de recuperación y el canvas lo renderiza desde la DB secundaria.
2. **Given** una mención ambigua que matchea varios widgets, **When** el triage no puede decidir, **Then** Joi responde con una lista corta de candidatos para que el usuario elija.

---

### User Story 5 — RAG cache de widgets (Priority: P1)

**Como** usuario que hace preguntas semánticamente similares a lo largo del tiempo,
**quiero** que Joi reconozca cuándo una pregunta nueva se parece a una ya resuelta,
**para** recibir el widget al instante, sin esperar al LLM ni gastar tokens.

**Why this priority**: El usuario confirmó el RAG como parte del MVP de esta feature. Sin esta US, el sistema regenera desde cero cada vez; con ella, la latencia percibida y el costo caen drásticamente en el uso real.

**Independent Test**: Generar un widget con prompt "ventas mensuales por región en 2025". Formular después "ingresos por región durante 2025" sobre la misma conexión; verificar que el sistema ofrece reuso desde caché, y al aceptar, se renderiza sin invocar al Agente Generador.

**Acceptance Scenarios**:
1. **Given** un widget generado exitosamente, **When** se persiste en la DB secundaria, **Then** también se indexa en el vector store con su prompt, schema de datos, tipo de widget y código generado.
2. **Given** un prompt nuevo que excede el umbral de similitud contra una entrada cacheada válida, **When** el sistema detecta el match, **Then** muestra una sugerencia visible "Reutilizar widget anterior" con preview y el usuario decide reusar o regenerar.
3. **Given** el usuario acepta el reuso desde caché, **When** el widget se renderiza, **Then** no se invoca al LLM para generar código; los datos sí se re-ejecutan contra la fuente para refrescarse.
4. **Given** una entrada cacheada para una conexión que ya no existe o cuyo schema cambió, **When** el sistema evalúa candidatos, **Then** la entrada queda invalidada y no se ofrece al usuario.
5. **Given** un reuso desde caché, **When** el widget se renderiza, **Then** el `WidgetGenerationTrace` indica explícitamente "reutilizado desde caché" con referencia al widget original.

---

### Edge Cases

- ¿Qué sucede cuando el usuario intenta guardar un widget que falló (error banner)?
- ¿Qué pasa si el vector store no está disponible (servicio caído o corrupto)? — fallback debe ser regeneración normal sin bloquear al usuario.
- ¿Qué pasa si el usuario borra la conexión de datos de un widget guardado? — ver Clarify Q5.
- ¿Un dashboard puede contener el mismo widget dos veces (distintos filtros)? — asumido NO en el MVP; validar en Clarify.
- ¿Qué pasa cuando dos sesiones diferentes generan el mismo prompt? — el caché es por sesión o global (ver Clarify Q4 — dashboards; por simetría también aplica al caché).
- ¿Embeddings para prompts en idiomas mixtos (ES/EN)? — el modelo de embeddings debe ser multilingüe (ver research).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir al usuario guardar un widget generado asignándole nombre y una colección (existente o nueva).
- **FR-002**: El sistema MUST listar, crear, renombrar y eliminar colecciones a nivel de `UserSession`.
- **FR-003**: El sistema MUST permitir mover un widget entre colecciones sin regenerar su contenido.
- **FR-004**: El sistema MUST persistir widgets guardados, colecciones y dashboards en la DB secundaria entre sesiones del mismo `UserSession`.
- **FR-005**: El sistema MUST permitir crear dashboards con nombre y añadirles widgets ya guardados.
- **FR-006**: Los dashboards MUST soportar layout en grid con drag, reorder y resize; el layout persiste por dashboard.
- **FR-007**: El sistema MUST permitir eliminar un widget de un dashboard sin eliminarlo de su colección.
- **FR-008**: El sistema MUST reconocer intenciones del chat del tipo "muéstrame el widget X" y renderizar el widget guardado matcheante sin invocar al Agente Generador.
- **FR-009**: Tras generar un widget exitoso, el sistema MUST indexar metadata (prompt original, schema JSON de datos, tipo de widget, código generado, connection_id) en un vector store interno.
- **FR-010**: Al recibir un prompt nuevo, el sistema MUST consultar el vector store antes de invocar al Agente Generador y, si hay un candidato sobre el umbral de similitud, MUST ofrecer al usuario la opción de reusar.
- **FR-011**: El sistema MUST invalidar entradas del caché cuando la conexión asociada deja de existir o cuando el schema de datos cambia (heurística: hash del schema).
- **FR-012**: El sistema MUST indicar visualmente en el `WidgetGenerationTrace` cuándo un widget proviene de caché vs. de generación nueva.
- **FR-013**: Si el vector store no está disponible, el sistema MUST continuar generando widgets normalmente (fallback silencioso con warning en logs).
- **FR-014**: El sistema MUST permitir al usuario rechazar una sugerencia de caché y forzar regeneración (comportamiento exacto por Clarify Q2).
- **FR-015**: Las operaciones de colecciones y dashboards MUST estar aisladas por `UserSession`; ningún usuario ve colecciones/dashboards de otra sesión (excepto si se habilita compartir por URL — ver Clarify Q4).
- **FR-016**: El sistema MUST abstraer el acceso al vector store detrás de la interfaz `VectorStore` de LangChain; ningún código de negocio puede importar clientes de un proveedor específico.
- **FR-017**: El usuario MUST poder registrar un vector store propio desde el Setup Wizard seleccionando un `provider` soportado por LangChain y proveyendo las credenciales correspondientes; el sistema valida conectividad antes de guardar.
- **FR-018**: Las credenciales del vector store del usuario MUST almacenarse cifradas en reposo en la DB secundaria (reutilizar el mismo mecanismo de `connection.py` para conexiones de datos).
- **FR-019**: El sistema MUST tener exactamente un `VectorStoreConfig` activo por `UserSession`; al cambiar de proveedor, el caché previo queda accesible solo mientras el antiguo provider siga alcanzable (no hay migración automática en el MVP).

### Key Entities

- **Collection**: Agrupación nombrada de widgets dentro de una sesión. Atributos: id, session_id, name, created_at, updated_at.
- **CollectionWidget**: Tabla junction N:M entre `Collection` y `SavedWidget`. Atributos: collection_id, widget_id, added_at. PK compuesta (collection_id, widget_id).
- **Dashboard**: Vista compuesta y persistente de widgets con layout en grid. Atributos: id, session_id, name, created_at, updated_at.
- **DashboardItem**: Posición de un widget dentro de un dashboard. Atributos: dashboard_id, widget_id, grid_x, grid_y, width, height, z_order.
- **WidgetCacheEntry**: Registro indexado en el vector store activo del `UserSession` (Qdrant por defecto o el configurado por el usuario) en una colección/índice `widget_cache_{session_id}` o con filtro por `session_id` según capacidades del provider. Payload: id, session_id, widget_id, prompt_text, data_schema_hash, connection_id, widget_type, created_at, hit_count, last_used_at, invalidated_at (nullable). Vector: embedding del `prompt_text`.
- **VectorStoreConfig**: Configuración del vector store asociado al `UserSession`. Atributos: id, session_id, provider (enum: `qdrant`, `chroma`, `pinecone`, `weaviate`, `pgvector`), connection_params (JSON cifrado), is_default (bool, true si es el Qdrant interno sin configuración del usuario), created_at, last_validated_at.
- **SavedWidget**: Un `Widget` (modelo existente) marcado como persistente; extiende el modelo actual con flag `is_saved` y nombre asignado por el usuario.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El usuario puede guardar un widget en menos de 15 segundos desde el momento en que se generó.
- **SC-002**: El 100 % de los widgets guardados son recuperables y renderizables tras recargar la aplicación.
- **SC-003**: Un dashboard con hasta 10 widgets carga y muestra su layout completo en menos de 3 segundos en conexión típica.
- **SC-004**: Al menos el 60 % de los prompts semánticamente equivalentes dentro de una misma sesión activan la sugerencia de reuso desde caché (medido sobre un conjunto de prompts de prueba).
- **SC-005**: Cuando el usuario acepta reusar desde caché, el tiempo hasta render es al menos 5× menor que una generación desde cero (excluye tiempo de re-ejecución de la query).
- **SC-006**: La latencia adicional introducida por la consulta al vector store en generaciones no-cacheadas es ≤ 300 ms en p95.
- **SC-007**: Cero widgets huérfanos tras eliminar colecciones o dashboards (integridad referencial verificable por query).
- **SC-008**: El fallback (vector store caído) no aumenta la tasa de errores end-to-end por encima del baseline pre-006.

---

## Assumptions

- El stack RAG se añade en Feature 005, superseding parcialmente ADL-010 (nuevo ADL-023 lo documenta).
- **Confirmado Q1**: Qdrant corre como servicio en `docker-compose.yml`; no se usa storage embebido.
- El modelo de embeddings debe ser multilingüe para soportar prompts en español e inglés (decisión de modelo concreto se toma en Phase 3 — research.md).
- **Confirmado Q2**: umbral fijo `cosine ≥ 0.85`; siempre se pide confirmación explícita del usuario antes de reusar.
- **Confirmado Q3**: la relación widget ↔ colección es N:M vía tabla junction `collection_widgets`.
- **Confirmado Q4**: dashboards, colecciones y caché RAG son estrictamente por sesión; no hay compartir por URL en el MVP.
- **Confirmado Q5**: los widgets re-ejecutan su query al abrir un dashboard; no se persisten snapshots de datos; los errores de conexión se aíslan por widget.

---

## Clarifications

### Session 2026-04-24

- **Q1 — Stack RAG y BYO vector store**: El pipeline RAG se implementa sobre **LangChain** como capa de abstracción. El vector store **por defecto** es **Qdrant en Docker** (servicio en `docker-compose.yml`, volumen persistente). Además, el usuario puede **conectar su propio vector store** desde el Setup Wizard eligiendo entre los backends que expone LangChain (Qdrant remoto, Chroma, Pinecone, Weaviate, PGVector, etc.) e ingresando URL/API key/credenciales. Implicancias:
  - El código del backend nunca habla directamente con `qdrant-client`; usa `langchain_core.vectorstores.VectorStore`.
  - Nueva entidad `VectorStoreConfig` por `UserSession` que guarda `provider`, `connection_params` (cifrado en reposo), `is_default`.
  - Setup Wizard añade un paso opcional "Conecta tu vector store (opcional — Joi usa Qdrant por defecto)".
  - Embeddings permanecen bajo control de Joi (LiteLLM). Chunking y pipeline también.
  - Healthcheck del vector store reporta por provider; fallback FR-013 aplica cualquiera sea el backend.
- **Q2 — Umbral y UX de reuso**: Umbral **fijo** de cosine similarity **≥ 0.85** hardcoded en el backend. Cuando hay match, el sistema NUNCA reusa automáticamente; siempre presenta al usuario una tarjeta de sugerencia en el chat con preview del widget anterior (nombre, tipo, fecha) y dos acciones explícitas: **"Usar este widget"** o **"Generar uno nuevo"**. Esto refina FR-010 y FR-014: el rechazo es la opción "Generar uno nuevo", que fuerza el pipeline de generación sin consultar el caché para ese prompt.
- **Q3 — Relación widget ↔ colección**: Relación **N:M** (un widget puede estar en varias colecciones simultáneamente). Implicancias: se requiere tabla junction `collection_widgets (collection_id, widget_id)`; la UI de guardar debe permitir seleccionar múltiples colecciones; al eliminar una colección, los widgets se desasocian pero no se borran si están referenciados en otras; la noción de "Sin colección" equivale a "cero filas en la junction". La entidad `CollectionWidget` en Key Entities queda confirmada como junction table; `SavedWidget` no lleva `collection_id` directo.
- **Q4 — Visibilidad**: **Todo por sesión**. Colecciones, dashboards y entradas del caché RAG (`WidgetCacheEntry`) se aíslan estrictamente por `UserSession.id`. No hay compartir vía URL en el MVP. Implicancias: toda query de Qdrant se filtra por `session_id` (payload filter); el endpoint `/widget-cache/search` nunca devuelve entradas de otras sesiones; FR-015 queda confirmado sin excepciones.
- **Q5 — Fuente de datos no disponible al abrir dashboard**: **Re-ejecutar siempre + alertar por widget si falla**. Cada `DashboardItem` dispara su query al montar; si la conexión fue eliminada o la query falla, ese widget muestra un estado de error localizado (mensaje + botón "Reintentar"), los demás widgets del dashboard renderizan normalmente. No se persiste snapshot de datos. Invalidación del caché RAG: si la conexión referenciada en `WidgetCacheEntry.connection_id` ya no existe, o si el `data_schema_hash` actual difiere del cacheado, la entrada se marca inválida (flag `invalidated_at`) y no se ofrece en búsquedas. Esto refina FR-011, FR-013 y AC5 de US3.

---

## Alcance explícito (qué NO entra)

- No edición colaborativa en tiempo real (deferred scope de mission.md).
- No autenticación / cuentas; todo sigue siendo por `UserSession`.
- No exportación de dashboards a PDF/imagen en el MVP.
- No versionado histórico de widgets (cada widget guardado es una entidad única; editar regenera).
- No se replantea el pipeline de generación — el RAG se intercepta ANTES del Agente Generador, no lo reemplaza.
- No se introduce un scheduler de refresh automático de datos; los widgets re-ejecutan su query al abrirse.
