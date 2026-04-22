# ADL-015: MOCK_LLM_RESPONSES como modo determinístico para tests E2E

**Fecha:** 2026-04-22
**Estado:** Activo
**Área:** Backend
**Autor:** AI Session

---

## Contexto
El Data Agent depende de un LLM real (vía LiteLLM) para traducir preguntas en español a SQL. Este paso introduce no-determinismo inherente: el SQL generado varía entre corridas, el LLM a veces "adapta" prompts malformados (generando SQL válido contra columnas inexistentes en vez de fallar), y la latencia y costo por llamada hacen inviable ejecutar la suite E2E frecuentemente.

Durante el cierre de Feature 003 confirmamos que varios escenarios del quickstart (por ejemplo, el Esc 6 `QUERY_SYNTAX`) no son reproducibles contra el LLM real porque éste "corrige" el input, y que ejecutar E2E contra el modelo real cuesta minutos y API credits por corrida.

---

## Decisión
El backend expone la env var `MOCK_LLM_RESPONSES`. Cuando su valor es `true`, el cliente LiteLLM se reemplaza por respuestas *canned* deterministas cubriendo los caminos felices y los errores estructurados del Data Agent. La suite Playwright arranca el backend con `./dev.sh MOCK_LLM_RESPONSES=true` y, con eso, los 5 tests pasan de forma determinista en ~3 segundos.

---

## Justificación
- **Determinismo real**: las respuestas canned garantizan que cada test ejecute exactamente el mismo camino, eliminando flakes por variación del LLM.
- **Ejercita el stack completo**: a diferencia de mockear en el frontend, el mock vive dentro del backend (`app/services/litellm_client.py`), por lo que Playwright → Next → FastAPI → agente se recorre igual que en producción, sólo con el LLM reemplazado.
- **Coste cero**: no consume créditos de API ni requiere red, lo que permite correr E2E en cada push.
- **Establece patrón**: cualquier feature futura que integre un LLM debe soportar el mismo flag, manteniendo consistencia en la estrategia de testing.

---

## Consecuencias

### ✅ Positivas
- Suite E2E pasa de lenta/frágil a rápida y reproducible (`5 passed, 1 skipped (2.9s)`).
- Los escenarios de error estructurado del contrato del agente quedan cubiertos por E2E sin depender del LLM.
- Onboarding de nuevos devs no requiere credenciales del proveedor LLM para correr E2E localmente.

### ⚠️ Trade-offs aceptados
- Los mocks pueden divergir del comportamiento real del LLM con el tiempo — requieren mantenimiento cuando cambia el contrato del agente.
- Escenarios que dependen de la adaptabilidad real del LLM (ej. `QUERY_SYNTAX` del Esc 6, o evaluar la calidad del SQL generado) **no** se cubren con E2E; quedan delegados a tests unitarios o a validación manual.
- La flag es un path adicional en código productivo; hay que asegurarse de que nunca quede activa en deploys reales (validar en config de entorno).

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Grabar/reproducir tipo VCR (cassettes en disco) | Añade estado en el repo, sufre drift cuando cambia el prompt, y el match de requests con prompts largos es frágil. |
| Mock en el frontend con `page.route()` | No ejercita el camino real del backend; un bug en el pipeline del agente pasaría los E2E. |
| Sólo tests unitarios del agente | Perdemos cobertura del flujo completo Playwright → Next → FastAPI → agente → DB, que es donde aparecen regresiones de integración. |
| Proveedor LLM local (ej. Ollama) en CI | Complejidad operacional alta, sigue siendo no-determinista, y los tiempos de cold-start son prohibitivos. |
| Usar el LLM real con seed/temperature=0 | LiteLLM no garantiza determinismo estricto entre proveedores, y sigue costando créditos y latencia. |

---

## Decisiones Relacionadas
- ADL-002 (E2E Testing Strategy) — esta decisión concreta el mecanismo para hacer los E2E viables contra un agente LLM.
- ADL-006 (LiteLLM + Vanna Stack) — el mock se inyecta en la capa LiteLLM, respetando la abstracción ya elegida.
- ADL-013 (Data Agent Architecture) — los caminos de error canned reflejan el contrato estructurado del agente.

---

## Notas para el AI (Memoria Técnica)
- Cuando se agregue una nueva feature que integre un LLM, **extender** el mismo mecanismo `MOCK_LLM_RESPONSES` con nuevas respuestas canned. No introducir flags paralelas por feature.
- Si un test E2E depende de la adaptabilidad real del LLM (validar calidad del SQL generado, tolerancia a prompts ambiguos, etc.), **no** forzarlo en la suite E2E — moverlo a unit/integration tests del agente o a validación manual.
- **Nunca** activar `MOCK_LLM_RESPONSES=true` en entornos productivos. Si se agrega un nuevo entorno, incluir una validación que rechace la flag fuera de dev/test.
- Los mocks viven en `backend/app/services/litellm_client.py`; mantenerlos en sincronía con el contrato real del agente cuando cambien formatos de respuesta o códigos de error.
