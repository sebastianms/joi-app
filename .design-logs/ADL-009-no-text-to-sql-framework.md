# ADL-009: Sin Framework Text-to-SQL — LiteLLM Directo + SQLAlchemy

**Fecha:** 2026-04-22
**Estado:** Activo
**Área:** Arquitectura
**Autor:** AI Session

---

## Contexto

ADL-006 adoptó **Vanna** como framework Text-to-SQL del Data Agent y **LiteLLM** como gateway al proveedor LLM. Al implementar T018–T019 sobre `vanna==2.0.2` se descubre que:

1. **Vanna 2.x es agéntico, no "NL→SQL directo"**. `Agent.send_message()` corre un loop de tool-calling; no expone `generate_sql(question) -> str`. ADL-008 ya documentó esto y propuso un pipeline lineal `generate → guard → execute`.
2. **Los Runners SQL de Vanna (`SqliteRunner`, `PostgresRunner`, `MySQLRunner`)** requieren un `ToolContext` con `User`, `AgentMemory`, `conversation_id` y `request_id`. Instanciarlos fuera del `Agent` obliga a fabricar dependencias agénticas sintéticas.
3. **El único aporte real de Vanna en el MVP sería `AgentMemory` (RAG)** — pero US5/T042 (la User Story que habilita RAG) se difiere post-MVP (ver ADL-010).
4. Sin RAG y sin Agent, `LiteLLMVannaService` (T018) queda como un **wrapper para satisfacer un ABC (`vanna.core.llm.LlmService`) que nadie consume**. Aporta solo indirección.

Paralelamente, `tech-stack.md` aún menciona **LangChain** como backend framework — pero LangChain nunca se instaló en `backend/requirements.txt` ni se importa en el código. Es deuda documental de la decisión original de Feature 003 (registrada en `research.md`, consolidada en ADL-006).

---

## Decisión

Se **elimina Vanna** del stack del Data Agent. El pipeline queda:

1. **Gateway LLM**: `litellm_client` (singleton, ADL-006). Este punto **se mantiene intacto**: todas las llamadas LLM siguen pasando por `get_client()` / `chat_completion()` / `acompletion()` con routing por `Purpose` (`sql` / `json` / `chat`).

2. **Generación NL→SQL**: `SqlAgentAdapter.extract(...)` construye un prompt (system + user + schema) y llama a `litellm_client.acompletion(messages, purpose="sql")` directamente. No hay capa intermedia tipo `LiteLLMVannaService` ni `vanna.Agent`.

3. **Validación**: el SQL generado pasa por `ReadOnlySqlGuard` (ADL-005) antes de ejecutarse.

4. **Ejecución**: se usa **SQLAlchemy** (ya es dependencia del proyecto, ya la usa `connection_tester.py`). El adapter abre una conexión al DSN de `DataSourceConnection`, ejecuta con `asyncio.wait_for(to_thread(execute))` para respetar `QUERY_TIMEOUT_SECONDS`, trunca a `MAX_ROWS_PER_EXTRACTION`, y construye un `DataExtraction`.

5. **Prompt engineering**: construido ad-hoc en el adapter a partir del schema de la conexión y del `DataSourceType`. No se adopta ningún `SystemPromptBuilder` externo.

**Invariante ADL-006 se preserva**: toda llamada al LLM sigue pasando por `litellm_client`. Lo que se elimina es la capa Vanna, no el gateway LiteLLM.

---

## Justificación

- **`LiteLLMVannaService` solo existía para satisfacer un ABC de Vanna** (`LlmService.send_request`). Sin el `Agent` como consumidor, el ABC es puro overhead. Eliminarlo reduce ~130 líneas y dos capas de serialización (`LlmMessage` ↔ dict OpenAI ↔ litellm).
- **`SqlRunner` de Vanna es inusable fuera del `Agent`** por el acoplamiento a `ToolContext`. SQLAlchemy provee la abstracción equivalente (DSN parsing, ejecución) sin ese acoplamiento.
- **Guard-in-the-middle** (ADL-005) queda natural en el pipeline lineal: es una línea entre `generate` y `execute`. Con `Agent` requería middleware.
- **Control granular de timeout, truncado y mapeo de errores** — requerimientos del contrato `DataExtraction` (T009) y del error-mapping (T037) — es trivial en SQLAlchemy, artificial dentro del loop agéntico.
- **Reducción de dependencias transitivas**: Vanna arrastra `pandas`, `plotly`, `tabulate`, integraciones de múltiples DBs que no usamos. Removerlo baja tamaño del entorno virtual y superficie de conflictos (precedente: chromadb/fastapi en commit `39ebcd7`).
- **Prompt engineering ad-hoc es suficiente para MVP**: el prompt de NL→SQL con schema + dialecto es directo. Si crece, se factoriza en un helper propio, no se importa un framework.
- **LangChain nunca estuvo**: `tech-stack.md` menciona LangChain como plan original, pero `backend/requirements.txt` no lo tiene ni nunca lo tuvo. Esta ADL aprovecha para **saldar esa deuda documental** actualizando `tech-stack.md` al stack real.
- **Reversibilidad**: si en US5 se necesita RAG y la opción resulta ser Vanna + `AgentMemory`, re-introducirlo es un cambio localizado en `SqlAgentAdapter` (ver ADL-010).

---

## Consecuencias

### ✅ Positivas

- Un solo punto de llamada LLM: `litellm_client`. Sin wrappers intermedios.
- `SqlAgentAdapter` es testeable con mocks discretos (`litellm.acompletion`, `sqlalchemy.create_engine`).
- Pipeline lineal de 3 pasos (generate → guard → execute) coincide 1:1 con la estructura del test plan (T020).
- `tech-stack.md` queda alineado con el código: sin menciones ficticias de LangChain/Vanna.
- Reducción de superficie de dependencias: se elimina `vanna` y su transitive closure.
- `LlmGateway` / `LiteLLMGateway` del chat (Feature 002) se preservan — no hay cambio en esa interfaz.

### ⚠️ Trade-offs aceptados

- **Perdemos few-shot examples automáticos** que Vanna proveía vía `AgentMemory`. Aceptable: US5 estaba marcado como shippable slice aparte; el MVP US1–US4 no depende de esto.
- **Perdemos abstracción multi-dialecto de Vanna**: el prompt debe conocer el dialecto (`POSTGRESQL`/`MYSQL`/`SQLITE`) y pasarlo explícito. Manejable con un branch por `source_type`.
- **Debemos mantener el prompt de NL→SQL** nosotros: cambios en comportamiento del LLM requieren iterar el prompt local. Aceptable — control directo.
- **ADL-006 queda parcialmente superseded**: la decisión "Vanna como framework Text-to-SQL" ya no aplica. Se marca ADL-006 como *Activo en parte* y esta ADL es la enmienda.
- **ADL-008 queda subsumido**: su propuesta de "pipeline lineal con runners de Vanna" se reemplaza por "pipeline lineal con SQLAlchemy". La decisión de fondo (no usar `Agent`) se mantiene.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| **Mantener Vanna solo por `LlmService` ABC** | El ABC no aporta nada: nadie más lo consume. Pura indirección. |
| **Vanna como generator (sin `Agent`) y SQLAlchemy como executor** | Vanna 2.x no expone un generator standalone; habría que re-implementar con `LlmService.send_request` directo — que es exactamente lo que hace esta ADL sin Vanna. |
| **Migrar a LangChain `create_sql_agent`** | LangChain nunca se instaló. Adoptarlo ahora es decisión nueva, no "reemplazo". Mismo problema que Vanna: loop agéntico difícil de controlar granularmente. |
| **Implementar un mini-framework Text-to-SQL propio** | Sobre-ingeniería para MVP. Un prompt + schema + dialecto alcanza. |
| **Usar `SqlRunner` de Vanna con `ToolContext` sintético** | Frankenstein: instanciar `User`, `AgentMemory` fake solo para ejecutar SQL. Peor que SQLAlchemy directo. |

---

## Decisiones Relacionadas

- **ADL-005** — ReadOnlySqlGuard: sigue siendo el eslabón intermedio del pipeline. Sin cambios.
- **ADL-006** — LiteLLM + Vanna Stack: **parcialmente superseded por esta ADL**. La parte de Vanna ya no aplica; la parte de LiteLLM (invariante de gateway único) se mantiene intacta.
- **ADL-007** — Chroma RAG: se difiere junto con US5 (ver ADL-010). Si se revive, se decidirá stack en ese momento.
- **ADL-008** — Pipeline lineal sin Agent: subsumido por esta ADL (se mantiene la idea, cambia el executor).
- **ADL-010** — RAG diferido post-MVP: consecuencia directa de esta decisión.

---

## Notas para el AI (Memoria Técnica)

- **No** importar `vanna` en ningún archivo del Data Agent. Si aparece, es un antipattern detectado en auditoría (T056).
- **No** reintroducir `LiteLLMVannaService`, `vanna.Agent`, ni `vanna.tools.RunSqlTool`. El pipeline es lineal.
- **Sí** llamar a `litellm_client.acompletion(messages, purpose="sql")` desde `SqlAgentAdapter` para generar SQL. Es el único punto de acceso al LLM.
- **Sí** usar SQLAlchemy (`create_engine` + `connect()` + `execute()`) para ejecutar SQL validado, con `asyncio.wait_for(to_thread(...))` para timeout. `connection_tester.py` es la referencia de patrón.
- El prompt NL→SQL debe incluir: dialecto explícito (`POSTGRESQL`/`MYSQL`/`SQLITE`), lista de tablas con columnas y tipos, y la instrucción de generar **solo** SELECT/WITH. Responsabilidad del adapter, no de un framework externo.
- Si US5 (RAG) se activa en el futuro, la integración va en el paso `generate` del adapter: inyectar few-shot examples en el prompt **antes** de llamar a `litellm.acompletion`. No introducir `Agent` solo para esto.
- Si en el futuro se migra a un framework (Vanna 3, LangChain, LlamaIndex), el punto de cambio es `SqlAgentAdapter._generate_sql(...)`. El resto del pipeline (guard, execute, truncate, error mapping) es reutilizable tal cual.
- `tech-stack.md` queda actualizado por esta ADL: la mención a LangChain se elimina; el stack real del backend es FastAPI + LiteLLM + SQLAlchemy + pydantic.
