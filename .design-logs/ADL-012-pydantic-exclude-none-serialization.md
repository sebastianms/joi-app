# ADL-012: response_model_exclude_none=True como Convención de Serialización Pydantic/JSON Schema

**Fecha:** 2026-04-22
**Estado:** Activo
**Área:** Backend
**Autor:** AI Session

---

## Contexto

El contrato `data_extraction.v1` se define en `specs/003-data-agent/contracts/data-extraction-v1.schema.json` usando JSON Schema draft-07. En ese schema, los campos opcionales se modelan como propiedades **ausentes del objeto** (no están en `required`). El schema nunca usa `"type": ["object", "null"]` ni `"nullable": true` para campos opcionales — la ausencia del campo es el mecanismo de opcionalidad.

Pydantic v2, por defecto, serializa los campos con valor `None` como `"field": null` en el JSON. Por ejemplo, `QueryPlan(parameters=None)` produce `{"parameters": null}`, no `{}`.

Esto crea una **impedancia semántica**: el validador `jsonschema` ve `"parameters": null` y falla con `"None is not of type 'object'"` porque el schema define `parameters` como `type: object` (optativo por ausencia, no nullable por tipo).

El error fue detectado en el test `test_chat_complex_intent_returns_contract_compliant_extraction` (T024), donde `jsonschema.validate(instance=extraction, schema=extraction_schema)` rechazaba la respuesta con un error aparentemente misterioso hasta trazar la causa a la serialización Pydantic.

---

## Decisión

Todos los endpoints FastAPI que sirven modelos del contrato `data_extraction.v1` (o cualquier contrato basado en JSON Schema con opcionalidad-por-ausencia) deben usar:

```python
@router.post(
    "/messages",
    response_model=ChatResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
```

`response_model_exclude_none=True` instruye a FastAPI/Pydantic a omitir del JSON de respuesta todos los campos cuyo valor es `None`, en lugar de serializarlos como `null`. Esto alinea la salida del endpoint con la semántica del JSON Schema.

---

## Justificación

- **Corrección del contrato**: el JSON Schema del contrato usa opcionalidad-por-ausencia. `null` y `ausente` son semánticamente distintos en JSON Schema; el schema de `data_extraction.v1` solo permite ausencia.
- **Validación runtime**: `test_chat_with_data_agent.py` usa `jsonschema.validate(...)` contra el schema en disco. Sin `exclude_none`, el test falla con errores crípticos de tipo en campos opcionales.
- **Consistencia**: el frontend TypeScript (`frontend/src/types/extraction.ts`) modela los campos opcionales como `field?: Type` (undefined), no como `field: Type | null`. La serialización sin `null` coincide con la expectativa del consumidor TypeScript.
- **Convención uniforme**: usar `exclude_none=True` en todos los endpoints del contrato evita casos inconsistentes (algunos endpoints con `null`, otros sin él) que romperían los consumidores que asumen opcionalidad-por-ausencia.

---

## Consecuencias

### ✅ Positivas

- `jsonschema.validate()` en tests de contrato pasa sin modificar el schema ni el modelo Pydantic.
- La respuesta JSON es más compacta (no incluye claves `null` irrelevantes).
- El frontend TypeScript no necesita manejar `null` explícito en campos opcionales del contrato.

### ⚠️ Trade-offs aceptados

- **Distinción `None` vs ausente se pierde en la respuesta**: si algún consumidor necesita saber que un campo estaba presente pero valía `None` (distinción semántica nula-vs-ausente), no podrá. Para este contrato, esa distinción no existe — los campos opcionales son simplemente opcionales.
- **Los tests de respuesta deben usar `"field" not in data`** en lugar de `data["field"] is None` para verificar la ausencia de campos opcionales. Esto fue actualizado en `test_chat_endpoint.py`.
- **Solo aplica a la serialización HTTP**: internamente en Python, los campos con `None` siguen siendo `None` en los objetos Pydantic. Solo el JSON serializado los omite.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| **Modificar el JSON Schema para permitir `null`** (`"type": ["object", "null"]`) | El schema define el contrato público del sistema. Permitir `null` ampliaría la superficie del contrato innecesariamente y divergiría de la semántica de opcionalidad-por-ausencia establecida. |
| **Usar `Optional[X] = None` con un custom serializer que emita `null`** | Requiere escribir serializers custom por campo o por modelo. Complejidad innecesaria cuando `exclude_none=True` resuelve el caso general. |
| **Hacer los campos no-opcionales en el modelo Pydantic** | Requeriría asignar valores dummy para campos que semánticamente no aplican. Peor legibilidad y peor semántica en el modelo. |
| **Dejar el comportamiento por defecto y adaptar los tests** | Los tests dejarían de validar contra el schema en disco, perdiendo el valor de la validación de contrato runtime. |

---

## Decisiones Relacionadas

- **ADL-001** — Data Connectors Architecture: define el contrato `data_extraction.v1` como la estructura de intercambio entre backend y frontend.
- **T009 / T025** — `DataExtraction` y `AgentTrace` models: estos son los modelos afectados directamente por esta decisión.

---

## Notas para el AI (Memoria Técnica)

- **Siempre** agregar `response_model_exclude_none=True` a cualquier endpoint que sirva modelos del contrato `data_extraction.v1` o contratos derivados.
- Si se agrega un nuevo endpoint que retorne `ChatResponse` o subcomponentes del contrato, verificar que tenga `response_model_exclude_none=True`.
- Los tests de integración que verifican la ausencia de campos opcionales deben usar `assert "field_name" not in data`, **no** `assert data["field_name"] is None`.
- Esta convención aplica solo a la serialización HTTP (FastAPI). En el código Python, `None` sigue siendo el valor de campo no-asignado en los modelos.
- Si en el futuro un campo realmente necesita distinguir entre "ausente" y "nulo explícito", se debe modelar con un tipo `Optional[X]` en Pydantic **y** actualizar el JSON Schema para permitir `null` explícitamente, luego revisar si `exclude_none=True` sigue siendo apropiado para ese campo.
