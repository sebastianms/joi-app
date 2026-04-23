# ADL-019: Arquitectura del Agente Generador de Widgets — Modos de Render, Manifests y Routing LLM

**Fecha:** 2026-04-23
**Estado:** Activo
**Área:** Arquitectura / Backend / LLM
**Autor:** AI Session

---

## Contexto

La Feature 004 introduce un Agente Generador que convierte una `DataExtraction` en un `WidgetSpec` renderizable. Este agente necesita resolver tres decisiones estructurales:

1. **Modos de render**: ¿qué tipo de output produce el LLM — componente de una librería UI, o código libre?
2. **Inyección del catálogo de componentes**: ¿cómo sabe el LLM qué componentes puede usar de la librería activa?
3. **Routing del modelo LLM**: ¿usamos el mismo modelo para widgets que para SQL/chat, o uno separado?

Estas tres decisiones están acopladas: el routing afecta costos, los modos de render afectan el prompt, y la estrategia de manifest afecta tanto el tamaño como la cacheabilidad del prompt.

---

## Decisión

### Modos de render (R2)

`RenderModeProfile` soporta dos modos activos en el MVP:

- `ui_framework` (default): el agente genera una `WidgetSpec` con bindings declarativos (`x`, `y`, `label`, `value`, etc.) que el runtime del iframe renderiza usando componentes del catálogo cerrado. No hay código libre — el LLM solo elige tipo + bindings + opciones visuales.
- `free_code`: el agente emite código HTML/CSS/JS libre que el iframe ejecuta directamente. Mayor flexibilidad, mayor riesgo de calidad inconsistente. **No activo en el MVP** — la infraestructura (adaptadores de librería, endpoints, Setup Wizard step) está diferida a Feature 005 US6.

El tercer modo, `design_system`, está inhabilitado permanentemente en la UI del MVP (badge "próximamente").

El default lazy es `ui_framework` + `shadcn`. Cualquier sesión sin perfil heredará este default sin migración.

### Inyección del catálogo de componentes — manifests estáticos (R3)

Para cada librería soportada (`shadcn`, `bootstrap`, `heroui`) se mantiene en el repositorio un "component manifest" estático:

```
backend/app/services/widget/manifests/shadcn.md
backend/app/services/widget/manifests/bootstrap.md
backend/app/services/widget/manifests/heroui.md
```

Cada manifest es ≤ 2KB y lista los componentes relevantes para visualizaciones + restricciones de uso + ejemplos mínimos. El `PromptBuilder` (T104) ensambla:

```
system_prompt_base + manifest_librería_activa + widget_type_target + descripción_datos
```

El prefijo `system_prompt_base + manifest` es estable entre requests de la misma librería → el proveedor LLM activa **prompt caching** automáticamente (Anthropic, OpenAI reciente), amortizando el costo de tokens del manifest.

No se usa RAG ni vector store para los manifests: el volumen es fijo y pequeño, y agregar Chroma solo para esto sería overkill (coherente con ADL-010).

### Routing del modelo LLM (R6)

Se agrega `Purpose="widget"` al `LiteLLMClient` existente (Feature 003), independiente de `sql`, `json` y `chat`. El modelo se configura vía env var `LLM_MODEL_WIDGET`. El operador puede apuntar a un modelo optimizado para generación de código (e.g. Claude Sonnet, GPT-4.1) sin afectar el routing SQL/chat.

---

## Consecuencias

### ✅ Positivas
- Modo `ui_framework` con bindings declarativos es determinístico y testeable — el LLM no genera código que se ejecuta.
- Manifests en repo = auditables, versionables, sin infra adicional.
- Prompt caching reduce costos de tokens en producción.
- Routing independiente por propósito permite ajuste de modelo sin regresiones.

### ⚠️ Trade-offs aceptados
- `free_code` diferido implica que los adaptadores de librería (T129–T131) no tienen consumidor hasta Feature 005.
- Los manifests son estáticos — cuando una librería actualice sus APIs, hay que actualizarlos manualmente.
- `ui_framework` limita al catálogo cerrado de 8 tipos; visualizaciones fuera del catálogo requieren `free_code`.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|---|---|
| Modo único de código libre | Calidad inconsistente, mayor superficie de prompt injection |
| RAG sobre catálogo de componentes | Volumen insuficiente para justificar vector store; Chroma ya existe pero para otro propósito |
| Mismo modelo LLM para todos los propósitos | Acopla decisiones operativas no relacionadas |
| Fine-tuning por librería | Complejidad operativa masiva, fuera de scope MVP |

---

## Decisiones Relacionadas
- ADL-010: RAG diferido post-MVP (coherente con manifests estáticos)
- ADL-016: Identidad del WidgetSpec controlada por el backend
- ADL-020: Canvas iframe sandbox (superficie de aislamiento)
- ADL-022: RenderModeProfile & Setup Wizard (destino de T501–T507)

---

## Notas para el AI (Memoria Técnica)
- En modo `ui_framework`, el LLM **solo produce bindings declarativos** — nunca código ejecutable. No sugieras agregar campos `code` al prompt para este modo.
- Los manifests en `backend/app/services/widget/manifests/` son la fuente de verdad del catálogo de componentes. Si se actualiza una librería, actualizar el manifest correspondiente.
- `Purpose="widget"` en `litellm_client.py` es el único punto de entrada al LLM para generación de widgets. No invoques `litellm` directamente desde el generator.
- `free_code` no está activo. No implementes lógica que lo active sin pasar por Feature 005 US6.
