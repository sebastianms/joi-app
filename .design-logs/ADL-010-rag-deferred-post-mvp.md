# ADL-010: RAG Diferido Post-MVP (US5 fuera de la primera release)

**Fecha:** 2026-04-22
**Estado:** Activo
**Área:** Arquitectura
**Autor:** AI Session

---

## Contexto

La Feature 003 incluye **US5** (P2) — memoria RAG activable por sesión: con `rag_enabled=true`, las consultas siguientes reutilizan contexto previo (schema aprendido, ejemplos Q→SQL exitosos). ADL-007 especificó Chroma local como vector store con una colección por sesión.

Al revisar el estado del proyecto:

1. `backend/requirements.txt` tiene `chromadb==1.0.21`, pero **ningún código del backend lo importa**. Es deuda de la decisión original.
2. ADL-007 está acoplada a Vanna (`vanna.AgentMemory`). Con ADL-009 Vanna sale del stack, así que ADL-007 tampoco es implementable tal como está escrita.
3. El `roadmap.md` define US1–US4 como **MVP shippable sin RAG**. US5 fue pensada como su propio shippable slice (P2, explícitamente después del MVP).
4. Durante la conversación de diseño se cuestiona si RAG es necesario en esta etapa; el usuario deja explícito que *"no está seguro de querer Chroma todavía"*.

---

## Decisión

**US5 y todas sus tareas (T034–T045 en `specs/003-data-agent/tasks.md`) se difieren post-MVP**. En concreto:

- Se marcan como `[-] DEFERRED` (no `[ ]` pendiente) en `tasks.md` para que quede claro que no están simplemente sin hacer, sino **fuera del alcance** de la primera release.
- `chromadb==1.0.21` se **retira** de `backend/requirements.txt` para no cargar 200MB+ de dependencia muerta. Se re-evalúa cuando US5 se reactive.
- El campo `UserSession.rag_enabled` (T007) **se mantiene** en el modelo: es barato, forward-compatible y permite que US5 se active sin migración futura. Su valor por defecto es `false` y **no se consulta en ningún pipeline activo** del MVP.
- ADL-007 queda como **"Archivado — pendiente de re-evaluación"**: no se borra (la investigación sigue siendo útil), pero deja de ser una decisión activa del proyecto.

**Cuando US5 se reactive**, la decisión sobre vector store (Chroma, FAISS, Qdrant, algo local nuevo) se re-toma con el contexto de ese momento. ADL-007 queda como insumo, no como decisión vigente.

---

## Justificación

- **Roadmap explícito**: `specs/roadmap.md` lista US5 como shippable slice posterior al MVP. Diferirlo respeta la estructura SDD original del proyecto.
- **Costo real de mantener RAG "encendido pero sin usar"**: `chromadb` como dep tiene precedente de conflicto (commit `39ebcd7` con FastAPI). Mantenerlo en requirements por si acaso solo acumula riesgo.
- **Decisión técnica desactualizada**: ADL-007 asume `vanna.AgentMemory`. Con ADL-009 (Vanna fuera), reimplementar RAG requiere decisión nueva. Diferir permite tomarla con más información.
- **MVP sigue siendo útil sin RAG**: la experiencia de US1–US4 es "hazme una pregunta, te devuelvo SQL + resultados". El valor del RAG es "preguntas siguientes reutilizan contexto" — un *nice-to-have*, no el core loop.
- **Privacidad por defecto**: el MVP sin RAG no persiste embeddings de queries del usuario. Un default más seguro. US5 introduce persistencia; merece una decisión consciente en su momento.
- **Flexibilidad futura**: la investigación en `research.md` ya cubre Chroma, FAISS, Pinecone. Si US5 regresa, la comparativa está hecha — solo falta elegir.

---

## Consecuencias

### ✅ Positivas

- `backend/requirements.txt` queda con deps **realmente usadas**: sin Vanna, sin Chroma, sin LangChain. Entorno virtual más liviano.
- `SqlAgentAdapter` no necesita ramificar por `rag_enabled`: en MVP siempre es *sin memoria*.
- Se elimina una fuente de complejidad accidental en US1 (el flag existía pero no hacía nada hasta US5).
- Cuando US5 se reactive, la decisión de vector store es local a US5 — no arrastra deuda de decisiones viejas.
- El MVP puede shippear sin esperar integración de RAG ni resolución de conflictos de dependencia.

### ⚠️ Trade-offs aceptados

- **El MVP no aprende entre consultas**: cada query va al LLM sin memoria de las anteriores. Aceptable: la docs es clara, el usuario entiende que RAG llega en una release posterior.
- **`UserSession.rag_enabled` queda como "campo fantasma"**: existe en DB pero no se lee. Riesgo: alguien asume que funciona y reporta un bug. Mitigación: el endpoint admin para togglearlo (T045) se difiere junto con US5, y la UI del MVP no lo expone.
- **ADL-007 queda como documento no canónico**: puede confundir a nuevos contribuyentes. Mitigación: su header se marca como "Archivado".
- **Reactivar US5 requiere nueva ADL** (no solo "des-archivar" ADL-007): el stack se re-decide. Costo: una ADL más. Beneficio: decisión acorde al contexto del momento.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| **Implementar RAG ahora con Chroma directo (sin Vanna)** | Extiende alcance del MVP sin necesidad clara del usuario. RAG requiere también definir estrategia de embeddings, costos, UI — demasiado para incluir en US1–US4. |
| **Implementar RAG ahora con LangChain + Chroma** | LangChain no está instalado; adoptarlo ahora es decisión nueva. Además no resuelve el problema real: sigue siendo fuera de alcance. |
| **Dejar `chromadb` en requirements "por si acaso"** | Dep de ~200MB + precedente de conflictos. Sin consumidor, es puro riesgo sin retorno. |
| **Eliminar `rag_enabled` del modelo `UserSession`** | Borrar el campo hoy, re-agregarlo en US5 = migración innecesaria. Mantenerlo es forward-compatible a costo ~cero. |
| **Marcar tareas como `[ ]` simple en tasks.md** | Ambiguo: parece trabajo pendiente de US1–US4, no diferido. `[-] DEFERRED` es explícito. |

---

## Decisiones Relacionadas

- **ADL-006** — LiteLLM + Vanna Stack: parcialmente superseded por ADL-009; la parte RAG se suspende por esta ADL.
- **ADL-007** — Chroma RAG con aislamiento por sesión: **archivado** por esta ADL. Pendiente de re-evaluación cuando US5 regrese.
- **ADL-009** — Sin framework Text-to-SQL: esta ADL es su complemento — al quitar Vanna, RAG pierde su vehículo natural y se difiere.
- **`specs/roadmap.md`** — US5 como shippable slice post-MVP: esta ADL lo hace explícito.

---

## Notas para el AI (Memoria Técnica)

- **No** implementar RAG, vector stores ni `AgentMemory` en el MVP. Si un nuevo prompt lo sugiere, referir esta ADL y posponer.
- **No** leer `UserSession.rag_enabled` en ningún pipeline activo (SQL, JSON, chat). Es un campo reservado para US5.
- **No** mencionar "memoria de sesión" o "few-shot learning" en UI del MVP: podría prometer algo que no existe.
- **Sí** mantener `UserSession.rag_enabled` como campo con default `false`: forward-compatible, barato.
- **Sí** mantener ADL-007 en el repo como referencia histórica, con header de "Archivado".
- Si US5 regresa (usuario, roadmap update, o feedback de MVP), **no reactivar ADL-007 directamente**: escribir una ADL nueva que re-decida el stack RAG con la información del momento.
- El campo `rag_enabled` en el request body del chat **no debe existir**: si llega del cliente, ignorarlo silenciosamente. ADL-007 ya establecía que el flag vive en `UserSession`; esta ADL lo mantiene.
- `chromadb` queda fuera de `requirements.txt`. Si alguien lo agrega en un PR, pedir justificación y una ADL que reactive US5.
