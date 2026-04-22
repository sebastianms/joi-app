# ADL-006: Adopción de LiteLLM + Vanna como Stack del Data Agent

**Fecha:** 2026-04-22
**Estado:** Activo
**Área:** Arquitectura
**Autor:** AI Session

---

## Contexto

La Feature 003 introduce el Data Agent: un componente que transforma prompts en lenguaje natural en extracciones estructuradas (`DataExtraction`) contra fuentes SQL y JSON. El diseño debe cumplir dos restricciones cruzadas del `mission.md` y `tech-stack.md`:

1. **Agnosticismo de proveedor LLM**: el usuario puede haber configurado Anthropic, OpenAI o Gemini (ver `.env.example` ampliado en T004). El pipeline no debe acoplarse a un SDK específico.
2. **Pipeline Text-to-SQL robusto**: generar SQL válido requiere más que un prompt plano — se necesita context passing de schema, ejemplos few-shot y memoria de la sesión (R5 de research.md).

Hasta Feature 002 existía solo `EchoLLMGateway` (placeholder). Para Feature 003 se debe decidir (a) el gateway LLM agnóstico y (b) el framework Text-to-SQL.

---

## Decisión

Se adoptan **dos librerías complementarias** con responsabilidades bien separadas:

1. **LiteLLM** como gateway unificado al proveedor LLM. Un singleton en `backend/app/services/litellm_client.py` (T014) que:
   - Configura providers a partir de env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`).
   - Rutea llamadas por `purpose: Literal["sql", "json", "chat"]`, permitiendo modelos distintos por propósito (`LLM_MODEL_SQL`, `LLM_MODEL_JSON`).
   - Reemplaza `EchoLLMGateway` por `LiteLLMGateway` (T015) preservando la interfaz `LLMGateway` para no romper `ChatManagerService`.

2. **Vanna** como framework Text-to-SQL. Se adapta al gateway LiteLLM mediante `LiteLLMVannaService` (T018) que hereda de `vanna.core.llm.base.LlmService` y delega en el cliente LiteLLM. El `SqlAgentAdapter` (T019) instancia un `vanna.Agent` con:
   - `LiteLLMVannaService` como LLM backend.
   - `SqlRunner` apropiado por `source_type` (`PostgresRunner`/`MysqlRunner`/`SqliteRunner`).
   - `AgentMemory` basada en Chroma con aislamiento por `session_id` (ver ADL-007).

Para JSON se usa LiteLLM directamente con `purpose="json"` (T026): el modelo genera un JSONPath que se ejecuta con `jsonpath-ng`. No se usa Vanna para JSON porque no aplica.

**Invariante de arquitectura**: toda llamada al LLM pasa por el cliente singleton de `litellm_client.py`. Llamadas directas a `litellm.completion` o a SDKs de proveedor son anti-pattern (T056 grep-ea esto en la auditoría final).

---

## Justificación

- **LiteLLM** ya es la solución de facto para agnosticismo de proveedor en Python: API unificada estilo OpenAI, soporte de routing, caching y observabilidad. Implementar un gateway propio duplicaría esfuerzo sin aportar valor.
- **Vanna** provee Text-to-SQL con context passing, few-shot examples y `AgentMemory` (RAG) de forma integrada. Implementarlo from scratch toma semanas; Vanna lo resuelve en horas.
- Separar gateway (LiteLLM) de framework de agente (Vanna) permite:
  - Reemplazar Vanna en el futuro sin cambiar el gateway.
  - Reemplazar el proveedor LLM sin tocar Vanna (solo cambia `LiteLLMVannaService`).
  - Usar el mismo gateway para el pipeline JSON sin depender de Vanna.
- El routing por `purpose` permite optimizar costos: un modelo pequeño para clasificación/JSON y uno más capaz para SQL.
- La interfaz `LLMGateway` preexistente (Feature 002) se preserva: el `ChatManagerService` no cambia su contrato, solo la implementación concreta inyectada.

---

## Consecuencias

### ✅ Positivas

- Dos pipelines (SQL, JSON) reutilizan el mismo gateway; un único punto de configuración de credenciales.
- Agnosticismo real de proveedor: cambiar de Anthropic a OpenAI requiere solo env vars.
- Vanna trae `AgentMemory` integrada, que habilita R5 (RAG por sesión) con mínimo código propio (ver ADL-007).
- Tests unitarios mockean `litellm.completion` en un solo punto (`test_litellm_gateway.py`, T016) en lugar de mockear cada SDK.
- Observabilidad centralizada: logs, latencias y costos se pueden medir en el singleton.

### ⚠️ Trade-offs aceptados

- **Dependencia transitiva grande**: LiteLLM importa SDKs de múltiples proveedores. Impacta el tamaño del entorno virtual y tiempo de cold start. Aceptable para un backend server; revisar si se empaqueta para desktop.
- **Vanna como dependencia viva**: Vanna evoluciona rápido; cambios breaking en `LlmService` obligarían a actualizar `LiteLLMVannaService`. Mitigado fijando versiones en `requirements.txt`.
- **Routing por `purpose` es implícito**: el caller debe recordar pasar `purpose`. Mitigable con un linter simple o un wrapper por propósito si se vuelve error-prone.
- **Conflicto de versiones ya incidente**: `chromadb` (dependencia de la memoria de Vanna) forzó bump a `1.0.21` para compatibilizar con FastAPI (commit `39ebcd7`). Esperable que surjan más conflictos similares.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| **Integrar SDK de Anthropic/OpenAI directamente** | Acopla el agente a un proveedor. Cambiar requiere refactor en todos los puntos de llamada. |
| **Implementar gateway propio sobre httpx** | Duplica trabajo ya resuelto por LiteLLM (streaming, retries, response normalization, rate limiting). |
| **Vanna con su default LLM (OpenAI)** | Rompe el agnosticismo de proveedor. Obliga al usuario a tener OpenAI key aunque quiera usar Anthropic. |
| **Reemplazar Vanna por prompt plano + parsing manual** | Pierde context passing y few-shot; la calidad del SQL generado cae significativamente. |
| **LangChain SQL Agent** | Más complejo y opinionated; abstracción más pesada. Vanna es más específico a Text-to-SQL con menos código. |
| **Cliente por proveedor en paralelo (factory)** | Reinventa LiteLLM. Factible pero con ~10× más código para features básicas (streaming, routing). |

---

## Decisiones Relacionadas

- **ADL-005** — ReadOnlySqlGuard: consume el SQL generado por Vanna antes de ejecutarlo.
- **ADL-007** — Chroma RAG Memory: complementa este stack con la capa de memoria de Vanna.
- **research.md R1, R2, R6** (Feature 003): consolidado aquí.
- **tech-stack.md** — Backend: registra LiteLLM y Vanna como dependencias oficiales del Data Agent.

---

## Notas para el AI (Memoria Técnica)

- **Nunca** importar `anthropic`, `openai` o `google.generativeai` directamente en el código del Data Agent. Toda llamada LLM pasa por `litellm_client.get_client()` o por Vanna vía `LiteLLMVannaService`.
- **Nunca** llamar `litellm.completion(...)` directamente fuera de `litellm_client.py`: eso evade el routing por `purpose` y la configuración centralizada. T056 grep-ea este anti-pattern.
- **Nunca** instanciar un `vanna.Agent` sin pasar `LiteLLMVannaService` como LLM: el default de Vanna usa OpenAI y rompería el agnosticismo.
- La interfaz `LLMGateway` existe desde Feature 002 y **debe preservarse**. Cambios en su firma rompen `ChatManagerService`.
- Si un nuevo pipeline necesita un LLM, agregar un `purpose` nuevo (`"embedding"`, `"classify"`, etc.) en lugar de importar LiteLLM directamente.
- Si Vanna introduce un breaking change, actualizar `LiteLLMVannaService` es el único punto de adaptación; no propagar el cambio a `SqlAgentAdapter`.
- Las env vars `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` son **todas opcionales**: el usuario configura las que use. El gateway debe tolerar ausencia de keys no usadas.
