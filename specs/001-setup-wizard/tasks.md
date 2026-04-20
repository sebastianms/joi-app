# Tasks: Setup Wizard

> **Restricciones de Calidad (OBLIGATORIO en cada tarea)**
> - **Clean Code**: Nombres descriptivos, funciones con responsabilidad única (SRP), sin comentarios redundantes, máx. 3 argumentos por función.
> - **SOLID**: SRP (una razón para cambiar), OCP (abierto a extensión), DIP (depender de abstracciones). Usar interfaces/protocolos en Python, props tipadas en TypeScript.
> - **Tests**: Cada fase de backend DEBE ir acompañada de **tests unitarios** (pytest) antes o junto con la implementación (TDD). Cada feature completa requiere un **test e2e** con Playwright (frontend → backend).

---

## Phase 1: Setup
- [x] T001 [P] Inicializar repositorio frontend con Next.js, Tailwind CSS y configurar shadcn/ui en `frontend/`
- [x] T002 [P] Inicializar repositorio backend con FastAPI, estructura de carpetas limpia y dependencias en `backend/`
- [x] T003 Configurar base de datos secundaria (SQLite) y motor SQLAlchemy con session factory en `backend/app/db/session.py`
- [x] T004 Configurar entornos de test: `pytest` + `pytest-asyncio` en `backend/`, `Playwright` en `frontend/`

## Phase 2: Foundational
- [x] T005 Definir protocolo/interfaz abstracta `DataSourceRepository` (DIP) en `backend/app/repositories/base.py`
- [x] T006 Implementar el modelo ORM `DataSourceConnection` en `backend/app/models/connection.py`
- [x] T007 Implementar repositorio concreto `SQLiteConnectionRepository` en `backend/app/repositories/connection_repository.py`
- [x] T008 Configurar CORS en FastAPI para el origen del frontend Next.js
- [x] T009 [P] Escribir tests unitarios para el repositorio y el modelo ORM en `backend/tests/unit/test_connection_repository.py`

## Phase 3: Containerization
- [x] T010 [P] Crear `Dockerfile` y `.dockerignore` optimizado para el Backend (FastAPI).
- [x] T011 [P] Crear `Dockerfile` y `.dockerignore` optimizado para el Frontend (Next.js standalone).
- [x] T012 [P] Configurar `docker-compose.yml` en la raíz para orquestar ambos servicios y actualizar `README.md`.

## Phase 4: User Story 1 (SQL Connections)
- [x] T013 [US1] Implementar servicio `ConnectionTesterService` (SRP) en `backend/app/services/connection_tester.py`
  - Lógica de test de conexión read-only agnóstica al tipo de DB (OCP)
- [x] T014 [US1] Escribir tests unitarios para `ConnectionTesterService` con mocks de DB en `backend/tests/unit/test_connection_tester.py`
- [x] T015 [US1] Crear endpoint POST `/api/connections/sql` con validación Pydantic en `backend/app/api/endpoints/connections.py`
- [x] T016 [US1] Escribir test de integración del endpoint en `backend/tests/integration/test_connections_endpoint.py`
- [x] T017 [US1] Crear componente `SQLConnectionForm` (props tipadas, un solo propósito) en `frontend/src/components/setup/sql-form.tsx`
- [x] T018 [US1] Integrar el formulario en la vista principal del wizard en `frontend/src/app/setup/page.tsx`
- [x] T019 [US1] Escribir test e2e del flujo completo "conexión SQL exitosa" en `frontend/e2e/setup-sql.spec.ts`

## Phase 5: User Story 2 (JSON Upload)
- [x] T020: Implementar servicio `JsonFileService` (SRP) para parsing, validación de esquema y almacenamiento seguro en `backend/app/services/json_handler.py`
- [x] T021: Crear endpoint `POST /api/connections/json` en `backend/app/api/endpoints/connections.py`
- [x] T022: Crear componente `JSONUploadForm.tsx` con feedback de carga en `frontend/src/components/setup/json-form.tsx`
- [x] T023: Escribir test e2e del flujo completo "subida de JSON válido" y "rechazo de archivo grande" en `frontend/e2e/setup-json.spec.ts`

## Phase 5: Polish
- [x] T024 Revisar coverage total de tests en backend (`pytest --cov`) y asegurar mínimo 80% en servicios y endpoints
- [x] T025 Realizar auditoría de Clean Code con el skill Deckard y corregir deudas técnicas menores
- [x] T026 Verificar persistencia de ambas fuentes de datos en la base de datos de auditoría
- [x] T027 Consolidar branch y documentar en `walkthrough.md`
