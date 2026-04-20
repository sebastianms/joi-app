# Feature Specification: Setup Wizard & Data Connectors

**Feature Branch**: `[001-setup-wizard]`
**Created**: 2026-04-20
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conexión a Base de Datos (Priority: P1)
El usuario ingresa a la plataforma por primera vez y necesita conectar una base de datos relacional para que Joi-App pueda consultar la información a graficar. El sistema le pide credenciales y prueba la conexión, guardándola de forma segura si es exitosa.

**Why this priority**: Sin fuentes de datos, la plataforma no puede generar visualizaciones útiles.
**Independent Test**: Proveer credenciales de una base de datos SQLite o PostgreSQL mock y verificar que el sistema reporte conexión exitosa y logre hacer introspección del esquema.
**Acceptance Scenarios**:
1. **Given** el formulario de conexión vacío, **When** el usuario ingresa credenciales válidas y hace click en "Conectar", **Then** el sistema muestra un mensaje de éxito y guarda el perfil de conexión.
2. **Given** el formulario de conexión, **When** el usuario ingresa credenciales inválidas, **Then** el sistema muestra un mensaje de error claro y no guarda la conexión.

---

### User Story 2 - Carga de Archivos de Datos Estructurados (Priority: P1)
El usuario prefiere subir un archivo JSON con datos estáticos en lugar de conectar una base de datos en vivo. El sistema procesa el archivo, valida su estructura y lo deja disponible como fuente de datos para el agente.

**Why this priority**: Provee una alternativa rápida y sin requerir conocimientos de base de datos para los usuarios que desean probar la app inmediatamente.
**Independent Test**: Subir un archivo JSON válido y confirmar que el sistema lo lista en las fuentes de datos activas.
**Acceptance Scenarios**:
1. **Given** el área de "Dropzone" de archivos, **When** el usuario arrastra un JSON válido, **Then** el sistema extrae el esquema, notifica el éxito y lo registra como fuente activa.

---



### Edge Cases
- ¿Qué ocurre si la conexión a la base de datos se pierde temporalmente durante la configuración?
- ¿Qué ocurre si un usuario intenta subir un archivo JSON superior al límite de 10MB? (El sistema debe rechazarlo con un mensaje de error claro).

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: El sistema MUST permitir la configuración y conexión hacia bases de datos PostgreSQL, MySQL y SQLite.
- **FR-002**: El sistema MUST proveer una funcionalidad de carga de archivos (Upload) restringida a archivos JSON, imponiendo un límite estricto de 10 MB por archivo.
- **FR-003**: El sistema MUST almacenar las conexiones de forma persistente en el estado de la aplicación, asociadas a la sesión actual (Multitenancy).

- **FR-005**: El sistema MUST ejecutar un test de conexión de solo lectura a la base de datos antes de confirmar su guardado.

### Key Entities
- **DataSourceConnection**: Representa una conexión configurada a una base de datos externa o archivo, incluyendo el string de conexión (o path), tipo (SQL, JSON) y estado.


## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: Un usuario nuevo debe poder completar el wizard y establecer al menos una conexión exitosa en menos de 2 minutos.
- **SC-002**: La validación de la conexión a la base de datos (FR-005) debe responder en menos de 5 segundos.

## Assumptions
- Asumimos que los archivos JSON subidos tienen un formato tabular o estructural predecible (lista de objetos u objeto con listas).
- Asumimos que el usuario proveerá credenciales de una base de datos a la cual el servidor tiene acceso por red.

## Clarifications
### Session 2026-04-20
- **Límite de JSON:** Se acordó establecer un límite estricto de 10 MB para la carga de archivos JSON durante el MVP, priorizando la estabilidad y postergando el procesamiento de lectura por streaming (chunking) para fases posteriores.
- **Design System Excluido:** Se decidió dejar la funcionalidad de carga y parsing de Design Systems (PDF/TXT) **fuera del MVP**. El agente arquitecto utilizará por defecto Tailwind CSS + shadcn/ui sin reglas visuales adicionales.
