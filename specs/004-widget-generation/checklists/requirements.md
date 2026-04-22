# Checklist: Calidad del Spec — Feature 004 (Widget Generation & Canvas Rendering)

Validación de la especificación antes de pasar a Clarify / Plan. Marcar cada ítem como `[x]` solo tras verificar contra `spec.md`.

## Agnosticismo tecnológico (QUÉ, no CÓMO)

- [x] El spec NO menciona frameworks de UI específicos (React, Vue, Svelte, etc.).
- [x] El spec NO menciona mecanismos concretos de aislamiento (iframe, Shadow DOM, CSP) fuera de los pendientes de Clarify.
- [x] El spec NO menciona proveedores de LLM concretos (OpenAI, Anthropic, Gemini).
- [x] El spec NO menciona librerías de gráficos (D3, Chart.js, Recharts, etc.).
- [x] Todos los tipos de visualización se describen por rol ("tabla", "gráfico de barras") y no por componente.

## User stories

- [x] Cada user story tiene prioridad (P1/P2) justificada.
- [x] Cada user story tiene **Independent Test** que permite validarla aisladamente.
- [x] Cada user story tiene al menos 2 Acceptance Scenarios en formato Given/When/Then.
- [x] Las P1 son suficientes para entregar valor tangible (MVP de la feature).
- [x] Las P2 mejoran la experiencia pero no bloquean el MVP.

## Requisitos funcionales

- [x] Cada FR es **testable** y **no ambiguo**.
- [x] Cada FR se traza a al menos una user story o edge case.
- [x] Ningún FR prescribe implementación (stack, clases, archivos).
- [x] Los contratos (`widget_spec.v1`) se describen por rol, no por schema concreto.

## Criterios de éxito

- [x] Todos los SC son **medibles** (incluyen umbral numérico o condición verificable).
- [x] Todos los SC son **agnósticos de tecnología** (no mencionan stack).
- [x] Todos los SC son **user-focused** (expresan valor al usuario, no métrica interna).
- [x] Existen SC tanto para el flujo principal (US1) como para la seguridad/aislamiento (US3).

## Marcadores de clarificación

- [x] El spec contiene como máximo 3 `[NEEDS CLARIFICATION]` inline (conteo actual: 1 — en FR-006).
- [x] Los pendientes de decisión mayor se agrupan en una sección "Pendientes para la fase Clarify" al final del spec.
- [x] Ningún pendiente crítico queda silenciado como suposición.

## Trazabilidad con la constitución

- [x] La feature se declara como cumplimiento del bloque pendiente de la Fase 5 del [roadmap.md](../../roadmap.md).
- [x] Los SC de aislamiento (SC-003, SC-004) trazan a la Success Metric "Cero modificaciones no deseadas" del [mission.md](../../mission.md).
- [x] El spec respeta el invariante de agnosticismo (no fija stack).
- [x] El spec reutiliza el Agent Trace introducido en Feature 003 en lugar de crear una observabilidad paralela.

## Out of scope y dependencias

- [x] El spec delimita explícitamente lo que NO cubre (colecciones, dashboards, RAG, persistencia).
- [x] Las dependencias con Features 001/002/003 están declaradas.
- [x] Las asunciones razonables están documentadas.

## Lista de revisión final (bloqueantes)

- [ ] Pendiente: validar user stories con el usuario antes de entrar a Clarify.
- [ ] Pendiente: elegir las 5 preguntas de Clarify priorizadas sobre la sección "Pendientes para la fase Clarify".
- [ ] Pendiente: tras Clarify, recorrer FRs afectados y actualizar sin dejar texto contradictorio.
