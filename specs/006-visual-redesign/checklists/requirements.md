# Checklist de Calidad — Feature 006 (Visual Redesign & UX Polish)

> Validación del spec.md tras integrar Clarify. Marcar `[x]` al confirmar cada ítem.

## Trazabilidad

- [x] Cada User Story (US1–US6) tiene título, prioridad y criterios de aceptación.
- [x] Las decisiones D1–D5 están ancladas a una US o a una restricción no-funcional concreta.
- [x] Las respuestas de Clarify quedan ancladas a la US/métrica que modifican.

## Testabilidad

- [x] Métricas de éxito son verificables (Lighthouse, bundle size, 22 E2E preservados).
- [x] El breakpoint responsive (Q2) es medible con Playwright variando viewport.
- [x] El trigger del wizard (Q3) es testeable limpiando localStorage y recargando.

## No contaminación con HOW

- [x] El spec habla de estilos y comportamiento, no de rutas de archivo finales.
- [x] Los tokens CSS propuestos (D4) viven en Decisiones; los archivos concretos se definen en plan.md.

## Completitud

- [x] Alcance explícito (qué NO entra) está documentado.
- [x] Referencias visuales (Blade Runner 2049, Linear, Vercel) ancladas.
- [x] Clarify integrado.

## Coherencia

- [x] Consistente con `specs/mission.md` (identidad Joi como diferenciador).
- [x] El alcance de US6 (incluyendo T129–T131 y T501–T507 del backlog de Feature 004) cierra el diferido de ADL-022.
- [x] Feature 006 arranca después de cerrar Feature 005 (dashboards) — el roadmap lo refleja.

## Ambigüedad controlada

- [x] Cero marcadores `[NEEDS CLARIFICATION]` tras la sesión de Clarify 2026-04-24.
