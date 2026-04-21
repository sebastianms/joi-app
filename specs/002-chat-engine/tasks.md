# Tasks: Chat Engine & Hybrid Triage

> **Restricciones de Calidad (OBLIGATORIO en cada tarea)**
> - **Clean Code**: Nombres descriptivos, funciones con responsabilidad única (SRP), sin comentarios redundantes, máx. 3 argumentos por función.
> - **SOLID**: SRP (una razón para cambiar), OCP (abierto a extensión), DIP (depender de abstracciones). Usar interfaces/protocolos en Python, props tipadas en TypeScript.
> - **Tests**: Cada fase de backend DEBE ir acompañada de **tests unitarios** (pytest) antes o junto con la implementación (TDD). Cada feature completa requiere un **test e2e** con Playwright (frontend → backend).

---

## Phase 1: Foundational
- [x] T001 [P] Crear modelos Pydantic `Message`, `ChatRequest`, `ChatResponse` y `TriageResult` en `backend/app/models/chat.py`
- [x] T002 [P] Escribir tests unitarios iniciales para la inicialización y validación de modelos en `backend/tests/unit/test_chat_models.py`

## Phase 2: User Story 2 (Triage de Intenciones)
- [x] T003 [US2] Implementar servicio `TriageEngineService` (Regex/Keywords determinístico) en `backend/app/services/triage_engine.py`
- [x] T004 [US2] Escribir tests unitarios para `TriageEngineService` validando correctamente clasificaciones simples vs complejas en `backend/tests/unit/test_triage_engine.py`

## Phase 3: User Story 1 (Conversación Base - Backend)
- [x] T005 [US1] Implementar orquestador `ChatManagerService` integrando el motor de Triage en `backend/app/services/chat_manager.py`
- [x] T006 [US1] Crear endpoint POST `/api/chat/messages` consumiendo `ChatManagerService` en `backend/app/api/endpoints/chat.py`
- [x] T007 [US1] Escribir test de integración del endpoint en `backend/tests/integration/test_chat_endpoint.py`

## Phase 4: User Story 1 (Conversación Base - Frontend)
- [x] T008 [P] [US1] Crear custom hook `useChat` para gestionar el estado de los mensajes en memoria en `frontend/src/hooks/use-chat.ts`
- [x] T009 [P] [US1] Crear componente visual `MessageInput` (input de texto + botón enviar) en `frontend/src/components/chat/message-input.tsx`
- [x] T010 [P] [US1] Crear componente visual `MessageList` (renderizado del historial de chat) en `frontend/src/components/chat/message-list.tsx`
- [x] T011 [US1] Ensamblar el contenedor principal `ChatPanel` utilizando los componentes previos y el hook `useChat` en `frontend/src/components/chat/chat-panel.tsx`
- [x] T012 [US1] Integrar el `ChatPanel` en el layout principal del panel dual en `frontend/src/app/page.tsx` (o donde corresponda en la arquitectura actual)

## Phase 5: Polish
- [x] T013 Escribir test e2e validando el envío de un mensaje simple y su respuesta en `frontend/e2e/chat-basic.spec.ts`
- [x] T014 Validar métricas de Clean Code usando el skill Deckard y refactorizar si es necesario
- [x] T015 Documentar los cambios en el archivo `walkthrough.md` consolidando el completado de la Feature 002
