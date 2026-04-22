# ADL-007: Chroma Local como Memoria RAG con Aislamiento por Sesión

**Fecha:** 2026-04-22
**Estado:** Activo
**Área:** Arquitectura
**Autor:** AI Session

---

## Contexto

La Feature 003 incluye una User Story (US5, P2) que exige memoria RAG activable por sesión: con `rag_enabled=true`, las consultas posteriores se benefician del contexto de las anteriores (schema aprendido, ejemplos few-shot, queries exitosas). Requisitos duros:

- **FR-013 / SC-007**: aislamiento multitenant. Datos de la sesión A nunca deben ser accesibles desde la sesión B.
- **Flag por sesión**: el usuario puede desactivar RAG, y en ese caso el agente debe correr sin leer ni escribir en la memoria.
- **Sin servicios externos**: el `tech-stack.md` prefiere evitar dependencias de red para el MVP (usuarios en desktop/local).

Vanna ya provee `AgentMemory` como abstracción. Falta decidir (a) el vector store concreto y (b) el mecanismo de aislamiento.

---

## Decisión

Se usa **Chroma en modo local** (persistencia en `backend/chroma_data/`) como vector store backing de `vanna.AgentMemory`, con **una colección por sesión**: `session_{session_id}`. El módulo `backend/app/services/rag_memory.py` (T041) expone:

```python
def build_agent_memory(session_id: str, enabled: bool) -> vanna.AgentMemory | None
```

- Si `enabled=False` → retorna `None` (o un `NullAgentMemory` equivalente); el `vanna.Agent` corre sin memoria.
- Si `enabled=True` → abre cliente Chroma apuntando a `./backend/chroma_data/`, obtiene la colección `session_{session_id}` y la envuelve en `AgentMemory`.

El flag `rag_enabled` vive en `UserSession` (SQLAlchemy, ADL-003). El `DataAgentService` (T021) lo lee vía `UserSessionRepository` y lo pasa a `SqlAgentAdapter.extract()`, que a su vez lo propaga a `build_agent_memory`.

Directrices adicionales:

- `backend/chroma_data/` está en `.gitignore` (T001, T055): es estado local, no versionado.
- Un endpoint admin opcional (`PATCH /api/sessions/{session_id}`, T045) permite alternar el flag sin UI.
- El aislamiento es por **namespace de colección**, no por filtros de metadata: un bug en el nombre de colección sería detectable en tests, mientras que un filter-miss sería silencioso.

---

## Justificación

- **Chroma local** evita servicios externos y es zero-config para el usuario: el archivo persiste junto al backend.
- **Una colección por `session_id`** es el mecanismo de aislamiento más fuerte disponible en Chroma: dos colecciones son físicamente disjuntas. Una fuga cross-session requeriría un bug explícito en el nombre, no un filter-miss.
- **Vanna `AgentMemory`** resuelve serialización, embedding y retrieval; implementarlo ad-hoc sería semanas de trabajo.
- El flag vive en `UserSession` (no en el body del request) porque es estado persistente entre mensajes; poner el flag en el request sería propenso a errores del cliente.
- El endpoint admin es **opcional** porque la UI no lo expone en MVP; los tests pueden setear el valor directamente en DB o vía API.

---

## Consecuencias

### ✅ Positivas

- Aislamiento fuerte entre sesiones garantizado por el diseño (cubre SC-007 y FR-013).
- Zero-config para el usuario: no requiere levantar un vector store externo.
- El flag `rag_enabled` permite al usuario optar out explícitamente, útil para privacidad o debugging.
- Los tests de aislamiento (T043) son simples: escribir en sesión A, consultar desde sesión B, assert que no retorna resultados.
- Si Chroma falla, el fallback es `rag_enabled=false`: el agente sigue funcionando sin memoria.

### ⚠️ Trade-offs aceptados

- **Chroma local no escala a multi-nodo**: si el backend pasa a varios workers o containers, requiere migrar a Chroma server o un vector store remoto. Aceptable para MVP (desktop/local).
- **Crecimiento del disco**: cada sesión deja documentos embeddings en `backend/chroma_data/`. No hay TTL automático; se puede saturar con sesiones largas o muchas sesiones. Mitigable con cleanup periódico (fuera de scope MVP).
- **Costo de embeddings**: cada escritura en `AgentMemory` genera un embedding (vía LiteLLM). Con `rag_enabled=true` todas las extracciones exitosas escriben; duplica llamadas al LLM. Aceptable dado que el usuario opta in.
- **`backend/chroma_data/` no versionado**: el estado no es reproducible entre equipos de desarrollo; intencional, pero requiere documentación en walkthrough para onboarding.
- **Conflicto de versiones ya incidente**: bump de `chromadb` a `1.0.21` para compatibilizar con FastAPI (commit `39ebcd7`). Esperar fricción similar en upgrades futuros.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| **Vector store compartido con filtros por metadata (`session_id`)** | Un filter-miss causa fuga cross-session silenciosa. Namespaces por colección son un contrato más fuerte. |
| **FAISS local** | No tiene persistencia nativa robusta ni abstracción de colecciones; requeriría más código para serialización y aislamiento. |
| **Pinecone / Weaviate / Qdrant Cloud** | Dependencia de red, costos por uso, configuración externa. Rompe la filosofía zero-config del MVP. |
| **Memoria en-RAM (diccionario en proceso)** | Se pierde al reiniciar el backend. Rompe la premisa de "la segunda consulta se beneficia de la primera" si hay restart. |
| **SQLite con pgvector-like extension** | Sin soporte nativo robusto de vectores en SQLite; obligaría a implementar kNN manual. Vanna tampoco lo soporta out-of-the-box. |
| **Flag `rag_enabled` en el request body** | Propenso a inconsistencias del cliente (olvidar pasarlo). El estado pertenece a `UserSession`. |

---

## Decisiones Relacionadas

- **ADL-003** — Local State Storage: `UserSession` SQLAlchemy vive en la misma DB secundaria que los connectors; el flag `rag_enabled` es un campo de ese modelo.
- **ADL-005** — ReadOnlySqlGuard: ortogonal; la memoria no afecta la validación de seguridad pero puede enriquecer el contexto del LLM antes de generar SQL.
- **ADL-006** — LiteLLM + Vanna Stack: este ADL depende de `vanna.AgentMemory` expuesto por el stack de ADL-006.
- **research.md R5, R7** (Feature 003): consolidado aquí.

---

## Notas para el AI (Memoria Técnica)

- **Nunca** implementar aislamiento cross-session con filtros de metadata sobre una colección compartida: usar una colección por `session_id`. Es un invariante de seguridad.
- **Nunca** leer el flag `rag_enabled` desde el body del request: viene de `UserSession` vía `UserSessionRepository`. El body es inseguro (cliente puede mentir).
- **Nunca** commitear `backend/chroma_data/`: está en `.gitignore` por diseño. Si aparece en `git status`, es un bug de configuración.
- El nombre de colección **debe** ser exactamente `session_{session_id}`. Cambiar el prefijo rompe el aislamiento retroactivo (las sesiones viejas quedan huérfanas) y requiere migración explícita.
- Si `rag_enabled=false`, **no** pasar una memoria vacía que igual lea de la colección: pasar `None` o `NullAgentMemory` para que Vanna no acceda al vector store en absoluto. Esto cubre el test de "no escritura" (T044).
- Si Chroma falla al inicializar (disco lleno, permisos), **no** propagar la excepción al usuario: degradar a `rag_enabled=false` para esa sesión y loggear. El agente debe seguir funcionando sin memoria.
- El endpoint admin `PATCH /api/sessions/{session_id}` es **opcional**: si se omite, los tests deben poder setear el flag directamente vía repositorio o DB. No bloquear la implementación por este endpoint.
- Si en el futuro se migra a Chroma server o vector store remoto, encapsular el cambio dentro de `build_agent_memory`: ningún caller debe cambiar.
