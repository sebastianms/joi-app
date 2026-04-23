# ADL-016: Identidad del WidgetSpec Controlada por el Backend — El LLM Nunca es Fuente de Verdad para IDs

**Fecha:** 2026-04-23
**Estado:** Activo
**Área:** Arquitectura / Seguridad de contrato
**Autor:** AI Session

---

## Contexto

El Agente Arquitecto/Generador (Feature 004, T105) invoca al LLM con el prompt ensamblado en T104 y espera recibir un objeto JSON conforme a `widget-spec-v1.schema.json`. La spec incluye varios campos de **identidad y contexto de render**:

- `extraction_id` — referencia al `DataExtraction` que alimenta el widget.
- `session_id` — sesión de chat.
- `render_mode` — `ui_framework` o `free_code` (define la superficie de aislamiento).
- `ui_library` — cuando `render_mode=ui_framework`, es obligatoria (`shadcn`, `bootstrap`, `heroui`).
- `selection_source` — `deterministic`, `user_preference` o `fallback`.
- `widget_type` — dictado por el selector determinístico (R1) o por la preferencia del usuario (R10).
- `truncation_badge` — deriva de `DataExtraction.truncated`.
- `data_reference.extraction_id` y `data_reference.row_count` — metadata de la extracción de origen.

Dos riesgos concretos emergieron durante la implementación:

1. **Desalineación de identidad**: el integration test T113 reveló que el LLM devolvía un `data_reference.extraction_id` distinto al del `extraction_id` top-level, porque el prompt le pasaba el valor pero el modelo lo reescribía al copiar la estructura. El widget terminaba referenciando un dataset fantasma y el frontend no podía inyectar las filas correctas por postMessage.

2. **Potencial bypass de aislamiento**: si el LLM decidiera emitir `render_mode=free_code` cuando el `RenderModeProfile` de la sesión dice `ui_framework`, el prompt-injection vía `user_intent` podría usarse para elegir el modo menos restrictivo. Análogo aplica a `ui_library`, donde un atacante podría pedir una librería no instalada.

Aceptar que el LLM es fuente de verdad para cualquiera de estos campos abre superficie para ambos riesgos.

---

## Decisión

El backend **sobrescribe incondicionalmente** los campos de identidad y contexto después de parsear la respuesta del LLM, usando `_override_spec_invariants` en [backend/app/services/widget/generator.py](../backend/app/services/widget/generator.py):

```python
def _override_spec_invariants(spec: WidgetSpec, request: GenerationRequest) -> WidgetSpec:
    data_reference = spec.data_reference.model_copy(
        update={
            "extraction_id": request.extraction.extraction_id,
            "row_count": request.extraction.row_count,
        }
    )
    return spec.model_copy(
        update={
            "extraction_id": request.extraction.extraction_id,
            "session_id": request.extraction.session_id,
            "render_mode": request.render_mode,
            "ui_library": request.ui_library if request.render_mode == WidgetRenderMode.UI_FRAMEWORK else None,
            "selection_source": SelectionSource.DETERMINISTIC,
            "widget_type": request.widget_type,
            "truncation_badge": request.extraction.truncated,
            "data_reference": data_reference,
        }
    )
```

El LLM **sí** puede decidir (y son sus únicas responsabilidades):

- `bindings` (mapping columnas → roles visuales como x/y/series/value/label).
- `visual_options` (title, subtitle, axis labels, format hints).
- `code` (`{html, css?, js?}` cuando `render_mode=free_code`).

Después del override, el `selection_source` final se decide en el `architect_service` (T106): el generator siempre setea `DETERMINISTIC` como valor provisorio, y el architect lo reemplaza por `USER_PREFERENCE` o `FALLBACK` según la rama ejecutada.

---

## Justificación

- **Integridad de referencias**: el `data_reference.extraction_id` y el top-level `extraction_id` siempre apuntan al mismo `DataExtraction`. El frontend puede confiar en cualquiera de los dos para inyectar las filas por postMessage sin cross-check defensivo.
- **Aislamiento garantizado**: el `render_mode` viene del `RenderModeProfile` del servidor, no del LLM. El sandbox iframe (R4) siempre se aplica al modo correcto. Prompt injection vía `user_intent` no puede promover un widget a `free_code` si el perfil dice `ui_framework`.
- **Auditabilidad**: `selection_source` y `widget_type` los fija el código determinístico, trazables a reglas (R1, R10) o a excepciones (fallback). El LLM no puede autoatribuir un origen distinto.
- **Superficie del modelo acotada**: el prompt ya pide JSON; al limitar qué campos pesan, la probabilidad de `SPEC_INVALID` baja y el modelo se concentra en el trabajo semántico real (bindings + visual options).
- **Contrato verificable**: el integration test T113 valida contra `widget-spec-v1.schema.json` que el spec del response es coherente end-to-end, sin necesidad de hacer assertions defensivas en el frontend.

---

## Consecuencias

### ✅ Positivas

- El frontend confía en las IDs del spec sin validaciones cruzadas.
- El Setup Wizard (T501–T507) puede cambiar `ui_library` de forma transaccional: el próximo widget se rendea con la nueva librería sin que el modelo "recuerde" la anterior por training.
- Los tests de T111 documentan explícitamente qué campos sobrescribe el generator, haciendo la regla visible.
- Se reduce la dependencia del comportamiento del LLM: cambiar el modelo subyacente (R6) no introduce regresiones en identidad.

### ⚠️ Trade-offs aceptados

- Si el LLM produce bindings usando IDs inexistentes en el prompt (ej. inventa `widget_id`), el backend los sobrescribe silenciosamente — no hay señal al LLM de que "falló". Aceptable porque el LLM no debería producir esos IDs en primer lugar (el prompt no los pide).
- Añade dos llamadas a `model_copy(update=...)` por generación exitosa. Costo despreciable.
- Los tests tienen que saber qué campos se sobrescriben. Eso se mitiga con el test explícito `test_generate_overrides_identity_fields` en T111.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| **Validar que el LLM devuelva los IDs correctos y fallar si no coinciden** | Rompe el flujo por un comportamiento que no aporta valor — si el LLM los devolviera correctamente seguiríamos sobrescribiéndolos por defensa. Aceptar el parseo y sobrescribir es más simple. |
| **No pedir IDs en el prompt y hacer que el LLM devuelva solo `bindings` + `visual_options` + `code`** | El schema del contrato tiene campos `required` en el nivel top. El LLM debe producir JSON válido contra el schema. Pedir un objeto parcial y armar el resto en el backend es equivalente, pero menos parseable para el LLM (más errores `SPEC_INVALID`). |
| **Dejar que el LLM decida `render_mode` y validar post-hoc contra el `RenderModeProfile`** | Crea una ruta donde el widget válido contra el schema no es ejecutable con la política del sandbox. Prefiero un solo camino determinístico. |
| **Sobrescribir solo `extraction_id` y confiar en el resto** | No cubre el vector de `render_mode` ni el bug real de `data_reference.extraction_id` que T113 reveló. |

---

## Decisiones Relacionadas

- **ADL-005** — Read-Only SQL Guard: mismo principio (el guard reescribe/bloquea SQL del LLM). El LLM no es fuente de verdad para capacidades de ejecución.
- **ADL-006** — LiteLLM Gateway: único punto de llamada al LLM; hace posible centralizar el patrón de override aquí.
- **Research R4** — iframe sandbox: `render_mode` controla la superficie de ejecución, por eso NO puede venir del LLM.
- **Research R10** — Triage extendido: define cómo llega `preferred_widget_type` de forma determinística para US2.

---

## Notas para el AI (Memoria Técnica)

- **Nunca** remover el `_override_spec_invariants` del generator. El integration test T113 quebrará inmediatamente si el `data_reference.extraction_id` deja de coincidir.
- **Sí** añadir campos al override si el schema se extiende con nuevos campos de identidad o contexto de render.
- Los únicos campos que el LLM decide son `bindings`, `visual_options` y `code`. Si aparece otro campo "semántico" (ej. `color_palette`, `layout_hints`), evaluar si el backend lo controla o el LLM lo decide — la pregunta guía es: ¿afecta seguridad/aislamiento/identidad? Si sí, override.
- El `selection_source` se sobrescribe dos veces: primero a `DETERMINISTIC` en el generator, y después a su valor real (`USER_PREFERENCE`/`FALLBACK`) en el architect_service. Este "doble paso" es intencional: mantiene al generator ignorante del contexto de orquestación.
