# Research: Feature 003 — Data Agent

**Date**: 2026-04-21
**Status**: Completed

Este documento consolida las investigaciones y trade-offs que dan forma al `plan.md`. Cada sección sigue el formato SDD: **Decision**, **Rationale**, **Alternatives Considered**.

---

## R1. Framework Text-to-SQL: Vanna-AI 2.0

**Decision**: Adoptar Vanna 2.0+ como framework base para el pipeline SQL del Data Agent.

**Rationale**:
- Soporte nativo para las tres fuentes SQL del MVP mediante integraciones oficiales: `PostgresRunner`, `MysqlRunner`, `SqliteRunner`. Cubre 3 de las 4 fuentes sin código propio.
- Arquitectura `Agent` + `ToolRegistry` + `AgentMemory` calza directamente con dos requisitos de la constitución: multi-agente (tech-stack.md) y RAG como memoria (mission.md).
- `LlmService` es un abstracto pluggable — permite inyectar LiteLLM como backend único (ver R2) sin acoplar el framework a un proveedor.
- `AgentMemory` integrado resuelve el requisito de FR-012 a FR-014 (memoria activable por sesión con aislamiento) sin necesidad de montar un vector store externo en la primera iteración.
- Calidad de docs y ejemplos consultados vía ctx7 (Source Reputation: Medium-High, Benchmark Score: 83–88).

**Alternatives Considered**:

| Alternativa | Razón de descarte |
|---|---|
| **LangChain SQL Agent** (`create_sql_agent`) | Mencionado en tech-stack.md original, pero menos opinionado en memoria RAG y routing. Requeriría más código propio para alcanzar paridad con Vanna en aislamiento multitenant. |
| **LlamaIndex NLSQLTableQueryEngine** | Fuerte en indexación, pero su modelo mental está orientado a document retrieval más que a agentes conversacionales con tool use. |
| **Implementación desde cero sobre LiteLLM + SQLAlchemy** | Máxima flexibilidad y cero dependencias, pero reinventa validación de schemas, few-shot prompting, memoria, sanitización. No justificado para MVP. |

**Caveat**: Vanna no soporta JSON nativamente (no hay `JsonRunner` oficial). Ver R3.

---

## R2. Gateway LLM Unificado: LiteLLM

**Decision**: Usar LiteLLM como gateway único de proveedores LLM. Se implementa un adapter `LiteLLMService(vanna.core.llm.base.LlmService)` que envuelve a LiteLLM y sirve tanto al pipeline SQL (Vanna) como al pipeline JSON y al chat simple (`LLMGateway` existente).

**Rationale**:
- `mission.md` lista "Agnosticismo de proveedor LLM" como una de 4 Success Metrics duras. LiteLLM resuelve esto con una API única OpenAI-compatible sobre 100+ proveedores (Anthropic, OpenAI, Gemini, Ollama, Bedrock, Azure, Vertex, etc.).
- Routing nativo por modelo + fallbacks → materializa la decisión "SQL potente / JSON liviano" (FR-016) sin introducir dos servicios separados.
- Un único punto de configuración de credenciales → consistente con el setup por variables de entorno.
- El `LLMGateway` actual (`EchoLLMGateway`) se reemplaza por una implementación real basada en el mismo cliente LiteLLM, eliminando el stub.

**Alternatives Considered**:

| Alternativa | Razón de descarte |
|---|---|
| **Adapters oficiales de Vanna por proveedor** (`AnthropicLlmService`, `OpenAiLlmService`, etc.) | Más simple a corto plazo pero rompe agnosticismo: cada proveedor es un adapter distinto, router manual, dos sets de credenciales si se usa más de uno. |
| **LangChain LLM abstractions** | Adecuado pero menos uniforme en tool use y menos proveedores soportados que LiteLLM. No aporta ventaja adicional sobre LiteLLM aquí. |
| **SDK directo de un solo proveedor (p.ej. `anthropic`)** | Viola explícitamente el pilar de agnosticismo. Descartado. |

**Verificación técnica pendiente en Implement**: confirmar que LiteLLM soporta tool calling + streaming en los proveedores objetivo (Anthropic, OpenAI). Si hay gaps puntuales, el adapter los cubre explícitamente.

---

## R3. Pipeline JSON: adapter dedicado, no `JsonRunner` custom sobre Vanna

**Decision**: Implementar un `JsonAgentAdapter` independiente del agente de Vanna. Carga el archivo JSON ya registrado, usa un LLM liviano (vía LiteLLM) para mapear el prompt a una expresión de acceso estructurada (JSONPath o filtro declarativo), ejecuta la expresión en memoria y emite el mismo `data_extraction.v1` que el pipeline SQL.

**Rationale** (alineado con decisión de Clarify Session 2026-04-21):
- Vanna no tiene `JsonRunner` oficial. Escribir uno implica elegir entre (a) cargar el JSON a SQLite en memoria y tratarlo como SQL (overkill para archivos ≤10MB con schema plano) o (b) implementar el runner desde cero, lo que ya es un pipeline separado pero forzado dentro del framework.
- Un pipeline dedicado es más simple, más barato (modelo liviano), más rápido (sin carga a SQLite intermedio) y más transparente en observabilidad (el trace muestra JSONPath, no SQL inventado).
- Ambos pipelines convergen en el mismo contrato de salida → el chat y Feature 004 no perciben la diferencia.

**Alternatives Considered**:

| Alternativa | Razón de descarte |
|---|---|
| **`JsonRunner` custom dentro de Vanna (cargar JSON → SQLite in-memory)** | Fuerza el uso del mismo modelo potente para una tarea trivial. Más latencia y costo. Gana uniformidad a cambio de eficiencia. |
| **Pipeline unificado con override de modelo por `source_type`** | Complejidad híbrida, dos lógicas mezcladas en el mismo código. Mantiene la carga JSON→SQLite innecesaria. |
| **Sin LLM para JSON, solo JSONPath manual** | No cubre prompts en lenguaje natural. El usuario tendría que conocer JSONPath. Rompe la experiencia de chat. |

**Trade-off aceptado**: dos pipelines para mantener. Se compensa con responsabilidades claramente delimitadas y tests aislados por pipeline.

---

## R4. Defensa Read-Only en Dos Capas

**Decision**: La garantía de "solo lectura" se implementa en **dos capas independientes** (defense in depth):

1. **Capa 1 — Credenciales**: las cadenas de conexión persistidas en `data_source_connections` deben usar usuarios de BD con privilegios de solo lectura (responsabilidad del usuario en el Setup Wizard, validada en tiempo de conexión cuando sea posible). Esta capa es externa al Data Agent.
2. **Capa 2 — Validador pre-ejecución** (`ReadOnlySqlGuard`): componente interno que, antes de entregar cualquier SQL generado al runner de Vanna, rechaza la consulta si contiene tokens prohibidos o estructuras de mutación.

Tokens/patrones prohibidos (lista inicial, ampliable): `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`, `REPLACE`, `MERGE`, `CALL`, `EXEC`, `EXECUTE`, `LOCK`, `UNLOCK`, `RENAME`, `COMMENT ON`, `VACUUM`, `COPY ... TO`, pragmas de escritura de SQLite (`PRAGMA writable_schema`).

Para JSON: el pipeline es intrínsecamente read-only (expresiones de acceso no pueden mutar el archivo cargado en memoria). No requiere validador adicional, pero SÍ debe escribir en el trace una marca explícita `read_only: true` para uniformidad del contrato.

**Rationale**:
- `mission.md` exige "100% lectura segura" y "Cero modificaciones no deseadas" como Success Metric. Una sola capa no basta: una credencial mal configurada por el usuario podría dejar escritura abierta, y un SQL con CTE anidadas podría evadir regex simples.
- La defensa en profundidad es estándar en sistemas de agentes Text-to-SQL (OWASP LLM Top 10: "Excessive Agency" — LLM06).
- El costo de implementación es bajo (~100 LoC para el guard + tests).

**Alternatives Considered**:

| Alternativa | Razón de descarte |
|---|---|
| **Solo credenciales read-only** | Depende 100% de que el usuario configure bien. Si configura superuser (p.ej. en desarrollo), el agente podría destruir datos. |
| **Solo validador de tokens** | No defiende contra casos donde el validador falle (actualización de tokens por cambio de DB engine). Además, la capa de credenciales es "gratis" si se usa. |
| **Parseo AST completo del SQL** (p.ej. `sqlparse` + AST walker) | Más robusto que regex, pero overkill para MVP. Token matching cubre el 95% de los vectores con 10× menos código. Se puede escalar a AST en una iteración futura si se detectan evasiones. |
| **Whitelist de sentencias (`SELECT`, `WITH ... SELECT`, `SHOW`, `EXPLAIN`)** | Más restrictivo que blacklist. Se complementa: la implementación de referencia combinará ambas (whitelist de la sentencia inicial + blacklist de tokens peligrosos). |

**Implementación de referencia**: whitelist primer token + blacklist de tokens sensibles en el resto. Si cualquiera falla → rechazo con trace `security_rejection=true`.

---

## R5. Memoria RAG: AgentMemory de Vanna + Aislamiento por Sesión

**Decision**: Usar `AgentMemory` integrado de Vanna como capa de memoria. La selección del vector store concreto (Chroma local, FAISS, etc.) se toma en esta fase y queda documentada en ADL-005 (ver R7). Cada `session_id` es un namespace aislado dentro del vector store. El flag `rag_enabled` por `UserSession` gobierna si se lee/escribe en esa colección.

**Rationale**:
- Vanna ya provee `AgentMemory` con soporte de namespaces. Evita implementar serialización + vector store + recuperación desde cero.
- Un namespace por `session_id` garantiza aislamiento multitenant (FR-013, SC-007). La fuga entre sesiones sería un bug de configuración del namespace, no un issue de diseño.
- El flag se resuelve en el `DataAgentService` (fachada): si `rag_enabled=false`, el agente corre con `agent_memory=None` o equivalente "memoria vacía".

**Alternatives Considered**:

| Alternativa | Razón de descarte |
|---|---|
| **Vector store externo compartido con partición por metadata filter** | Funciona, pero depende de que los filtros se apliquen en todas las queries; un bug hace fuga. Namespaces son un contrato más fuerte. |
| **Implementar memoria ad-hoc (lista en memoria)** | No reutiliza el contexto en la misma sesión tras reinicio del backend. Menos valor. Pero es el fallback razonable si el vector store falla. |
| **Deferir RAG a Phase 6** (como dice el roadmap original) | El usuario decidió en Clarify que se integra en Feature 003 como módulo transversal activable. Descartado. |

---

## R6. Vector Store: Chroma Local Embebido

**Decision**: Chroma local (persistencia en disco dentro del proyecto, aislado del `joi_app.db` relacional) como vector store por defecto para `AgentMemory`.

**Rationale**:
- Alineado con la filosofía "SQLite local" de ADL-003: cero dependencias externas, archivo local del proyecto, backup trivial.
- Chroma es el vector store más mencionado en docs de LangChain/LlamaIndex/Vanna → alta probabilidad de integración fluida.
- Modo embebido (sin servidor) evita un contenedor adicional en `docker-compose.yml`.
- Persistencia en disco → la memoria sobrevive reinicios del backend (importante para que SC-006 sea verificable).

**Alternatives Considered**:

| Alternativa | Razón de descarte |
|---|---|
| **FAISS in-memory** | Muy rápido, pero no persiste. Habría que serializar a disco manualmente. |
| **Qdrant local (en contenedor)** | Excelente producto, pero requiere servicio aparte. Sobrecarga operativa injustificada para MVP. |
| **In-memory LangChain VectorStore** | Solo para pruebas. No persistente. Útil para unit tests, no para producción. |
| **PostgreSQL + pgvector** | Fuerte opción empresarial, pero exige una PG separada. Fuera de scope del MVP. |

**Plan de uso**:
- Directorio: `./backend/chroma_data/` (añadir al `.gitignore`).
- Colección por sesión: `session_{session_id}`.
- Purga manual como follow-up: política de retención de sesiones no activas (no es requisito de MVP).

---

## R7. ADL-005: Documentación Arquitectónica Consolidada

**Decision**: Emitir un único **ADL-005** que consolide las 4 decisiones técnicas introducidas en Feature 003:

1. Adopción de Vanna-AI como motor Text-to-SQL.
2. LiteLLM como gateway LLM único.
3. Dos pipelines separados (SQL vs JSON) con routing de modelos por propósito.
4. RAG activable por sesión con Chroma local como vector store.

**Rationale**:
- Las 4 decisiones son interdependientes (Vanna necesita un LLM; LiteLLM lo provee; los dos pipelines comparten el mismo LLM gateway; el RAG es parte del pipeline SQL). Un solo ADL es más coherente que 4 ADLs fragmentados.
- La convención del proyecto (ver ADL-001 a ADL-004) es agrupar por "área de decisión", no por fecha.
- Un solo documento facilita lectura futura y posibles revisiones (si se cambia LiteLLM por X, el ADL-005 se marca como Superseded por ADL-00Y).

**Ubicación**: `.design-logs/ADL-005-data-agent-architecture.md`. Se redacta en la fase Implement (antes de mergear Feature 003), siguiendo el formato de los ADLs existentes.

---

## R8. Extensión retrocompatible del `ChatResponse`

**Decision**: Extender `ChatResponse` agregando un campo opcional `extraction: DataExtraction | null` y un campo opcional `trace: AgentTrace | null`. El campo `response: str` existente se mantiene y puede contener el mensaje natural del agente (p.ej. "He encontrado 42 filas de ventas en tu región norte...").

**Rationale**:
- Los consumidores actuales del endpoint `/api/chat/messages` (Feature 002 frontend) siguen funcionando: no leen los nuevos campos.
- Los nuevos consumidores (Feature 003 frontend) leen `extraction` y `trace` cuando están presentes.
- Evita un endpoint nuevo (`/api/chat/extract` o similar) que duplicaría la lógica de triage y sesión.

**Alternatives Considered**:

| Alternativa | Razón de descarte |
|---|---|
| **Endpoint nuevo `/api/chat/extract`** | Duplica el flujo de sesión + triage. El triage ya decide si invocar al agente; mantener un solo endpoint es más simple. |
| **Respuesta polimórfica (`response` puede ser string o un objeto complejo)** | Rompe compatibilidad y dificulta tipado en TypeScript/Pydantic. |
| **Campo `metadata: dict` genérico** | Pierde tipado fuerte. Los nuevos campos merecen schema explícito. |

---

## R9. Persistencia de la Extracción: En Memoria, Adjunta a la Sesión

**Decision**: La `DataExtraction` se adjunta al historial del chat en memoria (dentro de un nuevo `Message` enriquecido o como un field del `Message` del asistente). Se recupera por `session_id` + identificador de extracción. No se persiste en el `joi_app.db`.

**Rationale**:
- Alineado con la decisión de Clarify: el trace vive en memoria.
- La extracción y su trace comparten ciclo de vida → persistirlos juntos o no persistirlos juntos.
- Feature 004 consumirá la extracción "en caliente" cuando renderice el widget; no necesita recuperarla tras reinicio del backend en esta iteración.
- Simplifica el modelo: sin tabla de extracciones, sin retención, sin migración.

**Alternatives Considered**:

| Alternativa | Razón de descarte |
|---|---|
| **Persistir extracciones en SQLite** | Auditoría, pero no hay requisito. Retención y privacidad como nuevos problemas. |
| **Guardar como archivo JSON en disco** | Ventaja cero sobre memoria; más I/O. |

---

## Resumen de Dependencias Técnicas a Instalar

Estas dependencias se añaden al `backend/requirements.txt` (o equivalente pyproject) en la fase Implement. Nombres finales a confirmar contra PyPI en Implement:

- `vanna` (framework Text-to-SQL)
- `litellm` (gateway LLM)
- `chromadb` (vector store embebido)
- `jsonpath-ng` (expresiones de acceso para el pipeline JSON)
- `sqlparse` (opcional, para mejorar el `ReadOnlySqlGuard` con tokenización robusta en vez de regex simple)

Los drivers de BD (`asyncpg`, `aiomysql`, `aiosqlite`) ya existen por Feature 001.

---

## Verificaciones Técnicas Diferidas a Implement

Riesgos conocidos que se resuelven con spikes cortos durante la implementación:

1. **LiteLLM + Vanna tool calling**: confirmar compatibilidad de `validate_tools` de Vanna con el formato de tool schema que LiteLLM propaga al proveedor subyacente. Riesgo: medio. Mitigación: adapter custom en `LiteLLMService` que traduzca si es necesario.
2. **Chroma async**: validar que el cliente async de Chroma no bloquee el event loop de FastAPI. Si hay issues, correr el vector store en thread pool vía `asyncio.to_thread`.
3. **Namespaces por sesión con garbage collection**: confirmar que Chroma no cree overhead excesivo con miles de colecciones pequeñas. Si es el caso, migrar a partición por metadata filter.
4. **Timeout propagación**: confirmar que SQLAlchemy/drivers respetan `statement_timeout` en los tres motores relacionales. Si PostgreSQL no lo hace por conexión, configurarlo por transacción.
