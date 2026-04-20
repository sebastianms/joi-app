# ADL-001: Arquitectura de Conectores de Datos Multitenant (SQL/JSON)

**Fecha:** 2026-04-20
**Estado:** Activo
**Área:** Arquitectura
**Autor:** AI Session

---

## Contexto
Joi-App requiere una fase inicial de configuración donde los usuarios conecten sus fuentes de datos (SQL o JSON) para habilitar la generación de UI dinámica. Se necesitaba una arquitectura que soportara múltiples tipos de fuentes, validación inmediata y persistencia asociada a una sesión de usuario (multitenancy).

---

## Decisión
Implementar un sistema de conectores desacoplados usando el patrón de **Servicios de Dominio (SRP)** en el backend y una interfaz de **Asistente (Wizard)** en el frontend basada en pestañas (Tabs). Se priorizó el soporte para SQLite, PostgreSQL, MySQL y archivos JSON estáticos (<10MB).

---

## Justificación
El uso de servicios especializados (`ConnectionTesterService`, `JsonFileService`) permite escalar el soporte a nuevos tipos de datos sin modificar la lógica de persistencia. El Wizard en el frontend simplifica el onboarding del usuario, permitiendo una transición suave entre fuentes en vivo y archivos estáticos.

---

## Consecuencias

### ✅ Positivas
- Código altamente modular y testeable (91% coverage).
- Validación temprana de credenciales y esquemas.
- Separación clara entre el almacenamiento físico (archivos) y el registro lógico (DB).

### ⚠️ Trade-offs aceptados
- Los archivos JSON se guardan en el sistema de archivos local del servidor en lugar de un bucket S3 (simplificación para MVP).
- El límite de 10MB es estricto y no soporta streaming por ahora.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Guardar JSON en BLOB de DB | Impacto en performance y dificultad para procesamiento futuro con agentes. |
| Configuración vía YAML/CLI | Demasiado compleja para el usuario objetivo (orientado a UI dinámica). |

---

## Decisiones Relacionadas
- ADL-003: Almacenamiento Local de Estado con SQLite.

---

## Notas para el AI (Memoria Técnica)
- Mantener siempre la validación de solo lectura en los conectores SQL para seguridad.
- No modificar el límite de 10MB sin actualizar la lógica de validación tanto en el frontend como en el backend.
