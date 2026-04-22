# ADL-013: Arquitectura del Data Agent — Consolidación MVP

**Fecha:** 2026-04-22
**Estado:** Activo
**Área:** Arquitectura
**Autor:** AI Session

---

## Contexto

Feature 003 introduce el Data Agent: el componente que toma un prompt en lenguaje natural, lo convierte en una consulta sobre la fuente de datos activa (SQL o JSON), ejecuta la consulta de forma segura y devuelve un `DataExtraction` conforme al contrato `data_extraction.v1`. La arquitectura atravesó varias iteraciones durante el diseño (R1–R6 de `research.md`, ADL-006 a ADL-010) antes de llegar a la forma implementada. Este ADL consolida las decisiones que quedan activas en el MVP.

---

## Decisión

El Data Agent del MVP implementa un **pipeline lineal de tres pasos** sin framework Text-to-SQL externo:

```
generate (LiteLLM, purpose="sql"|"json")
    → validate (ReadOnlySqlGuard — solo SQL)
        → execute (SQLAlchemy con timeout / jsonpath-ng)
            → DataExtraction (contrato v1)
```

Los dos pipelines (SQL y JSON) son adapters independientes con responsabilidades claramente delimitadas, orquestados por `DataAgentService` (fachada). El `ChatManagerService` recibe `DataAgentService` por parámetro en `handle()` — no por constructor — para resolver la tensión entre el ciclo de vida singleton del manager y el ciclo de vida per-request de la sesión de base de datos.

---

## Justificación

### R1 + ADL-009 — Sin framework Text-to-SQL
Vanna (R1) y LangChain se descartaron: el primero acopla la generación SQL a un loop agéntico que impide control granular de timeout, truncado y mapeo de errores; el segundo nunca se instaló. `LiteLLM + SQLAlchemy` entrega el mismo resultado con 0 dependencias adicionales y pipeline inspectable.

### R2 — LiteLLM como gateway único
Toda llamada al LLM pasa por `litellm_client.acompletion(messages, purpose=...)`. El routing por `purpose` (`sql` / `json` / `chat`) permite asignar modelos distintos por tarea sin cambiar el código de los adapters.

### R3 — Pipeline JSON dedicado
Vanna no tiene `JsonRunner` oficial. `JsonAgentAdapter` carga el archivo, usa un LLM liviano para obtener una expresión JSONPath y la ejecuta con `jsonpath-ng`. Emite el mismo contrato `data_extraction.v1` que el pipeline SQL, haciendo la diferencia transparente para el chat y Feature 004.

### R4 — Defensa read-only en dos capas
1. Credenciales de solo lectura en la fuente (responsabilidad del usuario en el Setup Wizard).
2. `ReadOnlySqlGuard` (ADL-005): whitelist del primer token + blacklist de tokens de mutación, ejecutado antes de cada `execute()`. Si rechaza, `query_plan.expression` contiene el SQL rechazado para auditoría.

### R6 + ADL-010 — RAG diferido post-MVP
US5 (memoria RAG activable por sesión) queda fuera del alcance del MVP. El campo `UserSession.rag_enabled` se mantiene en el modelo como forward-compat, pero ningún pipeline activo lo consulta. El vector store y el stack RAG se deciden cuando US5 se reactive.

---

## Consecuencias

### ✅ Positivas
- Pipeline lineal: cada paso es unitariamente testeable con mocks discretos.
- Un solo gateway LLM: cambiar de proveedor es una variable de entorno, no código.
- Aislamiento de pipelines: SQL y JSON evolucionan independientemente; Feature 004 (visualización) consume el contrato sin conocer el pipeline.
- Superficie de dependencias mínima: sin Vanna, sin LangChain, sin Chroma en el MVP.

### ⚠️ Trade-offs aceptados
- Prompt NL→SQL mantenido ad-hoc: iteraciones de prompt son responsabilidad del equipo, no de un framework. Aceptable para MVP.
- Dos pipelines distintos: si la lógica común crece, habrá presión a extraer una clase base. Actualmente no hay duplicación significativa.
- Sin few-shot memory (RAG): la calidad del SQL depende solo del prompt estático + schema. US5 lo resolverá.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Vanna 2.x con Agent loop | Loop agéntico impide control granular; US5 (la única razón de Vanna) se difiere. ADL-009. |
| LangChain `create_sql_agent` | Nunca instalado; mismo problema de loop agéntico. ADL-009. |
| Cargar JSON a SQLite in-memory | Overkill para archivos ≤10MB; usa el modelo SQL potente para tarea trivial. R3. |
| Chroma + Vanna AgentMemory para MVP | RAG útil pero no crítico para US1–US4; añade dependencia pesada. ADL-010. |

---

## Decisiones Relacionadas

- **ADL-005** — ReadOnlySqlGuard: la capa 2 del sistema de defensa read-only.
- **ADL-006** — LiteLLM stack: invariante del gateway único (la parte de Vanna quedó superseded por ADL-009).
- **ADL-009** — Sin framework Text-to-SQL: decisión operativa que dio forma a esta arquitectura.
- **ADL-010** — RAG diferido post-MVP: consecuencia directa del descarte de Vanna.
- **ADL-011** — DI por parámetro en `handle()`: resuelve la tensión singleton vs. per-request del DataAgentService.
- **ADL-012** — `response_model_exclude_none=True`: serialización Pydantic alineada con JSON Schema opcionales.

---

## Notas para el AI (Memoria Técnica)

- El único punto de llamada al LLM es `litellm_client.acompletion(messages, purpose=...)`. No importar ni llamar a `litellm` directamente en adapters. T056 audita esto.
- Todo SQL generado pasa por `ReadOnlySqlGuard.validate(sql)` antes de ejecutarse. No existe camino de ejecución SQL que saltee el guard.
- `DataAgentService` se inyecta por parámetro en `ChatManagerService.handle(request, data_agent)`, no por constructor. Razón: el manager es singleton (preserva historial en memoria); el data agent puede tener dependencias per-request. ADL-011.
- `UserSession.rag_enabled` existe en el modelo pero **no se consulta en ningún pipeline activo**. No agregues lógica de RAG sin reactivar US5 mediante una nueva ADL.
- Si US5 se activa: el punto de integración del RAG es `SqlAgentAdapter._generate_sql(...)` — inyectar few-shot examples en el prompt antes de la llamada a LiteLLM. No reintroducir `vanna.Agent`.
- Los errores de los adapters se mapean a `ErrorCode` en `_classify_sqlalchemy_error` (SQL) y en el bloque try/except de `JsonAgentAdapter`. El `ChatManagerService` garantiza HTTP 200 incluso en error; la excepción va en `extraction.error`.
