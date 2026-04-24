# Checklist de Calidad — Feature 005 (Dashboards, Collections & RAG Cache)

> Validación de `spec.md` antes de avanzar a Phase 2 (Clarify). Marcar `[x]` cuando se confirme cada ítem.

## Trazabilidad

- [x] Cada User Story (US1–US5) declara valor al usuario y su priority.
- [x] Cada User Story tiene un Independent Test que puede ejecutarse de forma aislada.
- [x] Cada Functional Requirement (FR-001 a FR-015) se traza a al menos una User Story.
- [x] Cada Key Entity está referenciada por al menos un FR.

## Testabilidad

- [x] Los Acceptance Scenarios usan formato Given/When/Then de forma consistente.
- [x] Los Success Criteria incluyen métricas numéricas concretas (tiempo, porcentaje, factor).
- [x] Los Success Criteria son agnósticos de tecnología (sin mención a SQLite, `sqlite-vec`, FastAPI, etc.).
- [x] Las Measurable Outcomes son verificables sin conocer la implementación.

## No contaminación con HOW

- [x] El spec no menciona librerías concretas (las propuestas viven en Assumptions o se difieren al Plan).
- [x] No hay rutas de archivos del proyecto en el cuerpo normativo (solo en Assumptions si son contextuales).
- [x] El pipeline técnico del RAG se describe como comportamiento observable, no como secuencia de llamadas internas.

## Completitud

- [x] La sección Edge Cases cubre al menos 5 escenarios de borde reales.
- [x] La sección Alcance explícito enumera qué queda fuera del MVP de la feature.
- [x] La sección Assumptions documenta cada default asumido sin clarificar.
- [x] El campo `Status` está en `Draft` al crear el spec.

## Ambigüedad controlada

- [ ] Cantidad de marcadores `[NEEDS CLARIFICATION]` en el cuerpo del spec: **0** (las ambigüedades se levantan en Phase 2 como preguntas de Clarify, no como marcadores inline).
- [x] Las 5 preguntas de Clarify están preparadas en el plan (`plans/continuemos-planificando-lo-que-radiant-mountain.md`) y cada una referencia un FR/Edge case concreto.

## Coherencia con la constitución

- [x] El alcance respeta `specs/mission.md` (persistencia de dashboards ya listada como MVP scope).
- [x] La activación del RAG se documenta como supersedencia de ADL-010 en Assumptions.
- [x] `specs/tech-stack.md` será actualizado en Phase 3 (Plan) con la decisión del vector store.

---

## Próximo paso

Ejecutar Phase 2 (Clarify): plantear las 5 preguntas al usuario en orden, una por una, e integrar cada respuesta en una sección `## Clarifications` del spec + actualizar la sección del FR/US impactada.
