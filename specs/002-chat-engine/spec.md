# Feature Specification: Chat Engine & Hybrid Triage

**Feature Branch**: `002-chat-engine`
**Created**: 2026-04-21
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conversación Interactiva Base (Priority: P1)
El usuario interactúa con la aplicación mediante un chat conversacional para solicitar información o visualizaciones de sus datos. El sistema mantiene el contexto de la conversación (historial corto) para permitir preguntas de seguimiento.

**Why this priority**: Es la interfaz principal de la aplicación; sin el chat, el usuario no puede solicitar widgets ni interactuar con sus datos.
**Independent Test**: Enviar un mensaje de texto simple y verificar que el sistema responde de forma coherente manteniendo el contexto del mensaje anterior.
**Acceptance Scenarios**:
1. **Given** un panel de chat vacío, **When** el usuario escribe y envía un saludo o pregunta genérica, **Then** el sistema muestra el mensaje enviado y retorna una respuesta de texto del asistente.
2. **Given** una conversación existente, **When** el usuario hace una pregunta que depende de la respuesta anterior, **Then** el sistema responde considerando el contexto previo.

### User Story 2 - Triage de Intenciones Simples vs Complejas (Priority: P1)
El sistema analiza el mensaje del usuario de manera eficiente para determinar si es una charla casual (intención simple) o una solicitud que requiere acceso a datos/generación de UI (intención compleja). Las intenciones simples se procesan rápidamente sin activar pipelines complejos, reduciendo latencia y costos.

**Why this priority**: Optimiza el rendimiento, latencia y costos al evitar llamadas innecesarias al motor completo de IA para preguntas triviales.
**Independent Test**: Enviar múltiples mensajes (unos conversacionales y otros pidiendo gráficos de datos) y verificar que el tiempo de respuesta y la ruta de procesamiento difieren correspondientemente.
**Acceptance Scenarios**:
1. **Given** el panel de chat activo, **When** el usuario envía un mensaje conversacional (ej. "hola", "gracias"), **Then** el sistema clasifica la intención como simple y devuelve una respuesta inmediata de texto.
2. **Given** el panel de chat activo, **When** el usuario solicita visualizar datos (ej. "muéstrame las ventas por mes"), **Then** el sistema clasifica la intención como compleja y activa el flujo de generación de UI.

### Edge Cases
- What happens when el usuario envía un mensaje extremadamente largo?
- How does system handle cuando el motor de triage falla al clasificar la intención de manera segura? (Default: debe caer a un fallback o pedir aclaración).
- What happens when la conexión a internet fluctúa durante el envío del mensaje?

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: El sistema MUST permitir al usuario escribir mensajes de texto y enviarlos mediante un botón o la tecla Enter.
- **FR-002**: El sistema MUST mostrar un historial visual de la conversación actual (mensajes del usuario y del asistente) en el panel izquierdo.
- **FR-003**: El sistema MUST implementar un motor de triage que evalúe cada mensaje nuevo y lo etiquete para definir su flujo de procesamiento. La capa inicial determinística utilizará Coincidencia de Patrones (Regex / Palabras Clave) para garantizar latencia mínima en intenciones simples.
- **FR-004**: El sistema MUST mantener en memoria el historial corto de la sesión actual para proveer contexto en las interacciones continuas.
- **FR-005**: El sistema MUST mostrar un indicador visual (ej. typing indicator o skeleton) mientras se procesa la respuesta.

### Key Entities
- **Message**: Representa una unidad de comunicación (texto, rol del emisor, timestamp).
- **SessionContext**: Agrupa el historial de mensajes de la sesión actual.
- **TriageResult**: Resultado de la evaluación inicial (intención, nivel de confianza, ruta asignada).

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: Los usuarios experimentan un tiempo de respuesta menor a 500ms para interacciones clasificadas como intenciones "simples".
- **SC-002**: El motor de triage clasifica correctamente el 95% de los mensajes de prueba (simples vs complejos) sin falsos positivos que bloqueen peticiones de datos.
- **SC-003**: El panel de chat maneja de forma fluida historiales de hasta 100 mensajes sin degradación perceptible (stutter) en el scroll.

## Assumptions
- Los mensajes estarán limitados a texto plano en esta fase (sin soporte para subida de imágenes en el chat).
- El historial corto en memoria es efímero y desaparece al recargar la página, a menos que se guarde explícitamente en el futuro.

## Clarifications

### Session 2026-04-21
- **Q**: ¿Cómo deberíamos implementar la capa determinística inicial antes de derivar la consulta al LLM?
- **A**: Se utilizará Coincidencia de Patrones (Regex / Palabras Clave) por su velocidad y simplicidad para cumplir con el tiempo de respuesta esperado (SC-001).
