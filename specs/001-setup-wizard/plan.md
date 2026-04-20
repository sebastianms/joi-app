# Implementation Plan: Setup Wizard

**Branch**: `[001-setup-wizard]` | **Date**: 2026-04-20

## Summary
Implementar el módulo inicial "Setup Wizard" de Joi-App. Este módulo dotará al usuario de las interfaces (Frontend) y los endpoints (Backend) necesarios para configurar orígenes de datos, ya sea mediante credenciales SQL o archivos JSON estáticos (con límite de 10MB). Esto habilitará el contexto de datos para los agentes en fases posteriores.

## Technical Context
**Language/Version**: Python 3.11+ (Backend) / TypeScript + Next.js (Frontend)
**Primary Dependencies**: 
- *Frontend*: Next.js, Tailwind CSS, shadcn/ui.
- *Backend*: FastAPI (recomendado para APIs rápidas de Python), SQLAlchemy.
**Storage**: SQLite local (BD secundaria de estado y persistencia de configuración).
**Testing**: pytest + pytest-asyncio (Backend), Playwright (Frontend e2e)
**Target Platform**: Linux server
**Project Type**: web-service + SPA

## Quality Standards
Todo el código generado en este proyecto DEBE cumplir con los siguientes estándares, sin excepción:

- **Clean Code**: Nombres descriptivos e intent-revealing. Funciones con una sola responsabilidad y máx. 3 argumentos. Sin comentarios redundantes. Aplicar DRY activamente.
- **SOLID**:
  - **SRP**: Cada clase/módulo tiene una única razón para cambiar.
  - **OCP**: Los servicios deben ser extensibles sin modificar código existente (ej. soporte para nuevas DBs sin tocar `ConnectionTesterService`).
  - **DIP**: Las capas superiores (endpoints) dependen de abstracciones (interfaces/protocolos), no de implementaciones concretas.
- **Tests**:
  - **Unitarios (pytest)**: Cada servicio y repositorio backend DEBE tener tests unitarios escritos antes o junto al código (TDD). Se usan mocks para aislar dependencias externas.
  - **Integración (pytest + TestClient)**: Cada endpoint debe tener cobertura de integración: happy path + casos de error.
  - **End-to-End (Playwright)**: Cada User Story completa debe tener un test e2e que ejerza el flujo completo desde la interfaz de usuario hasta la respuesta del backend.
  - **Coverage mínimo**: 80% en servicios y endpoints del backend.

## Constitution Check
- **Alineamiento Misión**: Sí. Se protege la integridad mediante conexiones explícitas "Read-Only".
- **Alineamiento Tech-Stack**: Sí. Se emplea Python, Next.js y SQLite.
- Se ha diferido la carga del Design System al no ser fundamental para el MVP.

## Project Structure
- `backend/`
  - `app/api/endpoints/connections.py`
  - `app/services/connection_tester.py`
  - `app/models/connection.py`
- `frontend/`
  - `src/app/setup/page.tsx`
  - `src/components/setup/sql-form.tsx`
  - `src/components/setup/json-dropzone.tsx`

## Complexity Tracking
> Sin violaciones ni trackings de complejidad extraordinarios en este plan.
