# ADL-008: Pipeline SQL como Generate → Guard → Execute (no `vanna.Agent` loop)

**Fecha:** 2026-04-22
**Estado:** Subsumido por ADL-009 (pipeline lineal se mantiene; executor pasa de Runners Vanna a SQLAlchemy)
**Área:** Arquitectura
**Autor:** AI Session

---

## Contexto

El plan original de T019 (ver `specs/003-data-agent/tasks.md`) instruye instanciar un `vanna.Agent` con `LiteLLMVannaService` + un `SqlRunner` (`PostgresRunner`/`MysqlRunner`/`SqliteRunner`) y usarlo para generar y ejecutar SQL.

Al adoptar `vanna==2.0.2` (ver ADL-006 y commit del upgrade), se constata que la API pública de `vanna.Agent` es **agéntica**, no "text-to-SQL directo":

- `Agent.__init__` requiere `llm_service`, `tool_registry`, `user_resolver`, `agent_memory` y `conversation_store`.
- La única API pública relevante es `Agent.send_message(...)`, que corre un **loop de tool-calling**. No existe un `generate_sql(question) -> str` directo.
- La herramienta que ejecuta SQL (`vanna.tools.RunSqlTool`) corre el SQL **dentro** del loop del agente. El guard `ReadOnlySqlGuard` (ADL-005) no tiene un punto de intercepción limpio entre "SQL generado por el LLM" y "SQL ejecutado por el runner".
- El loop controla además memoria, auditoría y UI features — overhead que el Data Agent no necesita en su primera versión.

Además, el contrato `DataExtraction` (T009) exige control granular sobre:
- Timeout configurable (`QUERY_TIMEOUT_SECONDS`).
- Truncado a `MAX_ROWS_PER_EXTRACTION` con flag `truncated`.
- Mapeo fino de excepciones a `ErrorCode`.
- `query_plan.expression` con el SQL exacto, incluso cuando el guard lo rechaza.

---

## Decisión

`SqlAgentAdapter` (T019) implementa el pipeline como **tres pasos explícitos** bajo su propio control, sin instanciar `vanna.Agent`:

1. **Generate** — llamar directamente a `LiteLLMVannaService.send_request(LlmRequest(...))` con un prompt NL→SQL enriquecido con schema y dialecto. El resultado es un string SQL.
2. **Guard** — pasar el SQL por `ReadOnlySqlGuard.validate(...)` (ADL-005). Si rechaza, emitir `DataExtraction(status="error", error.code="SECURITY_REJECTION", query_plan.expression=<sql rechazada>)` y detener.
3. **Execute** — ejecutar con un `SqlRunner` de `vanna.integrations.{postgres,mysql,sqlite}` **solo para la fase de ejecución**, envuelto en un timeout asíncrono y con truncado a `MAX_ROWS_PER_EXTRACTION`.

Los `*Runner` de Vanna se mantienen como dependencia: proveen abstracción de driver (DSN parsing, ejecución a DataFrame) sin imponer el loop agéntico.

---

## Justificación

- **Guard-in-the-middle es un invariante de seguridad** (ADL-005). Si el SQL se ejecuta dentro de un tool del `Agent`, el guard queda fuera del flujo natural y hay que interceptar vía middleware — más frágil que una llamada secuencial.
- **Control de timeout/truncado** se implementa trivialmente con `asyncio.wait_for` + slicing del DataFrame. Dentro del loop del `Agent` habría que implementarlo como middleware/hook, sumando complejidad sin beneficio.
- **Observabilidad**: el trace `AgentTrace` (T010) requiere el SQL exacto, filas preview y pipeline. El pipeline de 3 pasos expone esos datos directamente; el loop del `Agent` los esconde tras su abstracción de tools.
- **Testabilidad**: T020 puede mockear `LiteLLMVannaService.send_request` y el `SqlRunner` individualmente. Con `Agent`, habría que mockear el loop entero o usar fakes complejos.
- **Reutilizar runners oficiales** evita mantener parsing de DSN por dialecto y ejecución a pandas. Mantenemos la dependencia de Vanna sin aceptar toda su arquitectura.
- **Superficie mínima**: el `Agent` introduce conceptos (user resolver, access groups, UI features, audit config) que no aplican al MVP single-user local de joi-app.

---

## Consecuencias

### ✅ Positivas

- Guard y timeout viven en el path crítico sin middleware extra.
- `SqlAgentAdapter` es fácil de testear con mocks discretos.
- `AgentTrace` se construye con datos disponibles localmente — no hay que extraerlos del estado del loop.
- Si el MVP crece y necesita tool-calling (p. ej. consultas multi-paso), podemos introducir `Agent` como **capa adicional** sin refactor del adapter.
- Mantenemos ADL-006 intacto: toda llamada al LLM sigue pasando por `litellm_client` vía `LiteLLMVannaService`.

### ⚠️ Trade-offs aceptados

- **No aprovechamos el tool-calling automático de Vanna** (function calling, multi-turn tool use). El adapter queda como un pipeline lineal. Si en US2+ se requiere, habrá que decidir si migrar al `Agent` o extender el adapter.
- **`AgentMemory` de Vanna (RAG, ADL-007) requiere integración manual**: no viene "gratis" al usar `Agent`. T042 cablea memoria al prompt del adapter explícitamente.
- **Desvío literal del plan** (`tasks.md` dice *"Instancia `vanna.Agent`…"*). Esta ADL es la justificación del desvío. El plan queda vigente en intención (usar Vanna para SQL), no en letra (instanciar `Agent`).

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| **`vanna.Agent` literal con `RunSqlTool`** | El guard no tiene intercepción limpia; timeout/truncado requieren middleware. Overhead de user resolver, access groups, UI features sin uso. |
| **`vanna.Agent` con `RunSqlTool` custom que llame al guard** | Introduce un tool que delega en el guard — indirección sin beneficio; complica tests y trace. |
| **Remplazar `SqlRunner` por SQLAlchemy directo** | Tendríamos que mantener parsing de DSN por dialecto y ejecución a DataFrame manualmente. Reinventa lo que Vanna ya resuelve. |
| **Llamar a `litellm_client.acompletion` directamente desde el adapter** | Rompería la simetría con T018 (ya hay `LiteLLMVannaService`); el servicio permite evolucionar a `Agent` después sin tocar el adapter. |

---

## Decisiones Relacionadas

- **ADL-005** — ReadOnlySqlGuard: es el eslabón intermedio del pipeline de 3 pasos.
- **ADL-006** — LiteLLM + Vanna stack: esta ADL es una **enmienda** a la nota "instanciar `vanna.Agent`" en ADL-006. Mantiene el invariante de routing por `litellm_client` intacto.
- **ADL-007** — Chroma RAG Memory: su integración (T042) debe hacerse vía prompt enrichment, no vía `Agent.agent_memory`.

---

## Notas para el AI (Memoria Técnica)

- **No** instanciar `vanna.Agent` en el Data Agent. Si un caso de uso futuro lo justifica, requiere nueva ADL que explique por qué el pipeline lineal es insuficiente.
- **Sí** usar `vanna.integrations.{postgres,mysql,sqlite}.{Postgres,Mysql,Sqlite}Runner` para ejecutar SQL validado. No reimplementar DSN parsing por dialecto.
- **Sí** llamar a `LiteLLMVannaService.send_request(...)` directamente desde `SqlAgentAdapter` para generar SQL. Es el punto de integración con LiteLLM; el servicio existe precisamente para esto.
- El pipeline canónico del adapter es: `generate (LLM)` → `validate (guard)` → `execute (runner) con timeout + truncado` → `build DataExtraction`. Los tres pasos viven en un método `extract` del adapter.
- Cuando se integre RAG (T042), el contexto de memoria se inyecta en el prompt del paso `generate`, **no** mediante `Agent.agent_memory`.
- Si Vanna 2.1+ introduce un helper `generate_sql_only(question) -> str` sin agent loop, se puede adoptar para simplificar el paso `generate` — seguirá sin requerir `Agent`.
