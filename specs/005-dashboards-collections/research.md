# Research: Feature 005 — Dashboards, Collections & RAG Cache

**Fecha**: 2026-04-24
**Objetivo**: Fijar las decisiones técnicas derivadas de las respuestas del Clarify antes de empezar `tasks.md`.

---

## R1 — Stack RAG: LangChain con Qdrant default + BYO vector store

**Decisión**:
- Toda la lógica de RAG se construye sobre `langchain-core` + `langchain-community` usando la abstracción `VectorStore`.
- **Default provider**: Qdrant 1.x oficial (imagen `qdrant/qdrant:latest`) como servicio en `docker-compose.yml` con volumen persistente en `./qdrant/storage`.
- **BYO providers soportados en el MVP**: Qdrant (remoto del usuario), Chroma, Pinecone, Weaviate, PGVector. Ampliable porque la abstracción LangChain lo permite sin tocar el pipeline.
- El provider activo se decide por `UserSession` leyendo `VectorStoreConfig`; si no existe, se usa el Qdrant default.

**Rationale**:
- LangChain normaliza la API (add_documents, similarity_search_with_score, filters) entre proveedores.
- Permite cumplir FR-017 (BYO) sin reescribir pipeline por cada provider.
- Qdrant como default minimiza fricción: el usuario típico nunca tiene que configurar nada.
- FR-016 obliga a que ningún servicio importe `qdrant-client` directamente — sólo el factory del provider Qdrant lo usa.

**Alternativas consideradas y descartadas**:
- Escribir una abstracción propia (interface Python) sobre los clientes nativos: reinventa lo que LangChain ya hace y aumenta la deuda de mantenimiento.
- BYO Retriever / BYO chain completa: descartado por Clarify refinado (sobreingeniería).
- SQLite + `sqlite-vec` como default: descartado por la decisión inicial del usuario a favor de Qdrant.

**Consecuencias**:
- Nueva dependencia Python: `langchain-core`, `langchain-community`, `langchain-qdrant`, y los extras opcionales `langchain-chroma`, `langchain-pinecone`, `langchain-weaviate`, `langchain-postgres` (cargados lazy para no inflar el contenedor).
- Healthcheck por provider: el backend expone `GET /vector-store/health` que valida conectividad del provider activo de la sesión.
- Volumen persistente de Qdrant → considerar en backups.
- Las credenciales de BYO providers se cifran en reposo reusando el helper que ya protege conexiones de datos ([backend/app/models/connection.py](backend/app/models/connection.py)).

---

## R2 — Modelo de embeddings: `text-embedding-3-small` vía LiteLLM (controlado por Joi)

**Decisión**: Joi controla embeddings independientemente del vector store elegido. Se usa `text-embedding-3-small` de OpenAI a través del gateway LiteLLM ya configurado. Dimensión 1536. Variable `EMBEDDING_MODEL` en `.env` con default `text-embedding-3-small`. Se implementa como un `Embeddings` de LangChain (`LiteLLMEmbeddings`) que envuelve al gateway existente.

**Rationale**:
- La app ya tiene LiteLLM ([backend/app/services/llm/litellm_client.py](backend/app/services/llm/litellm_client.py) — ADL-009) y las API keys configuradas. Añadir embeddings es un endpoint más del mismo cliente.
- Multilingüe suficiente para español+inglés mezclados (Edge Cases del spec).
- Barato (~$0.02 / 1M tokens); el índice se mantiene en centavos incluso con miles de widgets.
- Dimensión 1536 manejable por todos los providers soportados sin tuning especial.
- Clarify refinado Q1 aclaró: embeddings son responsabilidad de Joi, no del usuario BYO. Esto evita que prompts se embeban con modelos incompatibles entre providers del usuario.

**Alternativas consideradas**:
- Permitir BYO embeddings: descartado por la decisión de Clarify refinado.
- `all-MiniLM-L6-v2` local con `sentence-transformers`: sin costo variable pero suma ~400MB al contenedor y rompe con ADL-006.
- `text-embedding-3-large`: mejor calidad marginal, 5× más caro, innecesario para prompts cortos.

**Consecuencias**:
- Depende de conectividad saliente al proveedor del modelo. Si falla → mismo fallback que vector store caído (FR-013).
- Cambiar `EMBEDDING_MODEL` en producción invalida todo el índice vectorial (dimensiones distintas). Documentar esto como operational note.
- El vector del prompt se calcula una sola vez por generación y se usa tanto para búsqueda como para indexación post-éxito.

---

## R2b — Factory de VectorStore por sesión

**Decisión**: Se implementa `backend/app/services/widget_cache/vector_store_factory.py` con la firma:

```python
def build_vector_store(session: UserSession, embeddings: Embeddings) -> VectorStore: ...
```

Lee `VectorStoreConfig` de la sesión; si no existe, construye un `QdrantVectorStore` apuntando al servicio interno (`QDRANT_URL`). Si existe, despacha por `provider`:

| Provider | Clase LangChain | Parámetros esperados |
|---|---|---|
| `qdrant` | `langchain_qdrant.QdrantVectorStore` | url, api_key (opcional) |
| `chroma` | `langchain_chroma.Chroma` | host, port, ssl, collection_name |
| `pinecone` | `langchain_pinecone.PineconeVectorStore` | api_key, index_name, environment |
| `weaviate` | `langchain_weaviate.WeaviateVectorStore` | url, api_key |
| `pgvector` | `langchain_postgres.PGVector` | connection_string |

Los imports se hacen lazy dentro de cada branch para no forzar instalar todos los extras.

**Validación de conectividad** (FR-017): antes de persistir el `VectorStoreConfig`, el factory corre una operación trivial (`similarity_search` vacío o ping del provider). Si falla, la API devuelve 422 con el error del provider — no se guarda config inválida.

**Rationale**: un único punto de verdad para mapear config → cliente; todos los servicios upstream (cache_service, bootstrap, health) piden el `VectorStore` al factory y no conocen el provider.

---

## R3 — Grid drag-and-drop: `@dnd-kit/core` + `@dnd-kit/sortable`

**Decisión**: Usar `@dnd-kit` (v6+) para el editor de dashboards.

**Rationale**:
- Accesible por default (teclado, ARIA), crítico para SC accesibilidad.
- Headless — no impone estilos, se integra con Tailwind/shadcn existentes.
- Activamente mantenido, soporta React 19.
- API declarativa; más fácil de testear que react-grid-layout.

**Alternativas consideradas**:
- `react-grid-layout`: feature-rich (resize real con handles) pero su CSS chocaría con los tokens de D4 de Feature 006 (Visual Redesign) que viene después. Bundle más pesado.
- HTML5 DnD puro: posible pero requiere mucho glue para reordenar y manejar focus.

**Consecuencias**:
- Para el **resize** (cambiar width/height de un item) escribimos un handler custom con pointer events sobre un handle en la esquina, no se usa una lib adicional.

---

## R4 — Estrategia de invalidación del caché

**Decisión** (Clarify Q5 + FR-011):
- Cada `WidgetCacheEntry` guarda en payload `connection_id` y `data_schema_hash`.
- Al arrancar el pipeline generador, antes de consultar el caché, se computa el hash actual del schema de la conexión activa (`hashlib.sha256(json.dumps(schema, sort_keys=True))`).
- Las entradas cuyo payload no matchee `connection_id` O cuyo `data_schema_hash` difiera del actual se filtran en la query de Qdrant (payload filter compuesto).
- Cuando el usuario elimina una conexión, un hook async marca `invalidated_at=now()` en todas las entradas con ese `connection_id` (soft delete; ayuda a analytics posteriores).
- Widgets abiertos en un dashboard NO consultan el caché — re-ejecutan su query directamente.

**Rationale**: evita leer schema nuevo y servir código viejo que rompería al ejecutarse.

**Alternativas descartadas**: TTL fijo (arbitrario y borra cosas útiles), re-embedding periódico (costo sin beneficio claro).

---

## R5 — UX de la sugerencia de reuso (Clarify Q2)

**Decisión**:
- El backend devuelve en la respuesta del endpoint `/chat` un nuevo payload `cache_suggestion` cuando aplica: `{widget_id, display_name, widget_type, score, preview_thumbnail_url}`.
- El frontend renderiza `CacheReuseSuggestion.tsx` como una tarjeta dentro del flujo del chat, sobre la burbuja de respuesta de Joi.
- Dos acciones: `onReuse()` llama a `/widget-cache/{id}/reuse` (POST) que incrementa `hit_count`, re-ejecuta la query de datos y devuelve el widget rehidratado; `onGenerate()` vuelve a invocar `/chat` con un flag `skip_cache=true`.

**Rationale**: permanece dentro de la conversación (no abre modales), el usuario decide con preview visible.

---

## R6 — Identificación de intención "recuperar widget guardado" desde el chat (US4)

**Decisión**:
- Extender el triage determinístico existente con patrones nuevos: `r"muéstra(me|le)?|abre|trae|enseña(me)?"` + referencia a nombre.
- Si el triage detecta la intención, ejecutar una búsqueda **por texto exacto y fuzzy (Levenshtein)** sobre `SavedWidget.display_name` en la DB secundaria **antes** de la búsqueda vectorial.
- Si hay un único match claro (>=0.8 fuzzy) → render directo; múltiples → Joi responde con lista de candidatos.

**Rationale**: no queremos confundir "muéstrame ventas Q1" (recuperación) con "dame un gráfico de ventas Q1" (generación). Mantener la decisión determinística por coherencia con ADL-009.

**Alternativas**: usar el mismo vector search. Descartada porque mezcla dos intenciones semánticas distintas.

---

## R7 — Modelo de datos compartido vs. split de widget

**Decisión**: Extender `backend/app/models/widget.py` con:
- `is_saved: bool = False`
- `display_name: Optional[str] = None`
- `saved_at: Optional[datetime] = None`

No se crea un modelo `SavedWidget` aparte; la entidad `SavedWidget` en el spec es **conceptual**, mapea a `Widget` con `is_saved=True`.

**Rationale**: evita la dualidad widget efímero/persistente en el código. Un único modelo, un único repositorio, flag booleano.

**Consecuencia para FR-013/015**: queries de colecciones hacen `WHERE is_saved = TRUE`.

---

## Referencias cruzadas

- ADL-005 (`ReadOnlySqlGuard`) sigue vigente; los dashboards NO bypassan el guard al re-ejecutar queries.
- ADL-009 (generate-then-execute) sin cambios; el caché intercepta ANTES, no dentro del pipeline existente.
- ADL-010 (RAG diferido) queda **supersedida parcialmente**; el nuevo ADL-023 lo documenta al cerrar tasks.
- ADL-014 (session_id localStorage contract) es la base de la visibilidad por sesión confirmada en Clarify Q4.
