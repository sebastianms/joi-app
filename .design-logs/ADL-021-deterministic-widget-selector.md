# ADL-021: Selector Determinístico de Tipo de Widget

**Fecha:** 2026-04-23
**Estado:** Activo
**Área:** Arquitectura / Backend
**Autor:** AI Session

---

## Contexto

El Agente Arquitecto necesita decidir qué tipo de widget generar a partir de una `DataExtraction`. Esta decisión ocurre antes de invocar el LLM y determina qué prompt ensambla el `PromptBuilder`. Un error aquí tiene consecuencias visibles: el LLM intenta generar un heatmap a partir de datos KPI, o un gráfico de líneas a partir de texto no ordenado.

La decisión central de diseño es: ¿quién elige el tipo — el LLM o una heurística determinística?

---

## Decisión (R1)

El tipo de widget se elige mediante **reglas determinísticas** sobre la forma de la `DataExtraction` (columnas, tipos, cardinalidad, `row_count`). El LLM no participa en esta selección.

### Catálogo de 8 tipos

| Tipo | Aplicabilidad mínima |
|---|---|
| `table` | Siempre aplicable (fallback universal) |
| `bar_chart` | ≥1 categórica (2–50 valores únicos) + ≥1 numérica |
| `line_chart` | ≥1 temporal o numérica ordenable + ≥1 numérica, ≤500 filas |
| `pie_chart` | 1 categórica (2–10 valores únicos) + 1 numérica positiva |
| `kpi` | `row_count == 1` + 1 columna numérica |
| `scatter_plot` | ≥2 numéricas sin categóricas, ≤2000 filas |
| `heatmap` | 2 categóricas (2–30 valores únicos cada una) + 1 numérica |
| `area_chart` | ≥1 temporal + ≥1 numérica |

### Orden de prioridad del selector

1. `row_count == 0` → estado vacío (no widget, no LLM)
2. `row_count == 1` + 1 numérica → `kpi`
3. 1 temporal + ≥1 numérica + ≤500 filas → `line_chart`
4. 2 categóricas pequeñas + 1 numérica → `heatmap`
5. 1 categórica pequeña + 1 numérica → `bar_chart`
6. ≥2 numéricas sin categóricas → `scatter_plot`
7. Fallback → `table`

### Extensión para preferencia del usuario (R10)

El `TriageEngine` incluye un segundo pass que busca patrones regex en el mensaje del usuario cuando el intent ya es `complex` o hay una extracción previa en sesión. Si matchea un tipo, emite `preferred_widget_type` en el `TriageResult`. El arquitecto aplica `check_applicability` antes de honrar la preferencia; si el tipo es incompatible con los datos, devuelve un mensaje explicativo y mantiene el widget anterior.

---

## Consecuencias

### ✅ Positivas
- Latencia cero para la selección: no hay llamada LLM extra.
- Completamente testeable y auditable (T108, T109).
- Coherente con la filosofía determinística del guard SQL (ADL-005) y el triage (Feature 002).

### ⚠️ Trade-offs aceptados
- El selector no aprende de feedback — si los usuarios consistentemente prefieren `bar_chart` sobre `line_chart` para ciertos datos, el selector no se adapta.
- La detección de cardinalidad depende de `DataExtraction.rows` (muestra); con datos truncados puede ser imprecisa.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|---|---|
| Decisión del LLM | No determinístico, latencia mayor, no auditable |
| Híbrido heurística + LLM | Doble camino, doble métricas; reactivable post-MVP si SC-007 no se cumple |

---

## Decisiones Relacionadas
- ADL-019: Arquitectura del agente generador
- ADL-016: Identidad del WidgetSpec controlada por el backend

---

## Notas para el AI (Memoria Técnica)
- El selector vive en `backend/app/services/widget/type_selector.py`. Las reglas de aplicabilidad por tipo viven en `backend/app/services/widget/applicability.py`.
- `table` es el fallback universal — nunca puede fallar. Si agregas un nuevo tipo al catálogo, agrégalo también a `REQUIRED_BINDINGS` en `bindings_validator.py` y su mirror en `frontend/src/lib/widget-runtime/bindings-validator.ts`.
- Las reglas de preferencia regex de R10 están en `backend/app/services/triage_engine.py`. Editar en pares con los tests en `test_triage_widget_preference.py`.
- No muevas la lógica de selección al LLM sin una discusión explícita — es una decisión de arquitectura con impacto en latencia y determinismo.
