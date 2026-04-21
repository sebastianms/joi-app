# Implementation Plan: Chat Engine & Hybrid Triage

**Branch**: `002-chat-engine` | **Date**: 2026-04-21

## Summary
Implementar el motor principal de chat de Joi-App. Este incluye la interfaz de usuario en el frontend para interacción conversacional y el motor de triage híbrido en el backend. El triage usa una capa determinística (Regex/Keywords) para procesar rápidamente intenciones simples (conversación básica), derivando intenciones complejas (consulta de datos) al flujo principal.

## Technical Context
**Language/Version**: Python 3.11+ / TypeScript (Next.js)
**Primary Dependencies**: FastAPI, LangChain, Tailwind CSS, shadcn/ui, lucide-react
**Storage**: En memoria (estado de sesión efímero)
**Testing**: pytest (backend), Playwright (frontend e2e)
**Project Type**: web-service (AI Agent)

## Constitution Check
- **Aligns with Tech-Stack**: Sí, se implementa la primera etapa del pipeline (Triage Híbrido determinístico) utilizando FastAPI y LangChain.
- **Aligns with Mission**: Sí, provee la interfaz conversacional esencial y cumple la métrica de baja latencia al no usar el LLM para consultas simples.

## Project Structure
### Backend (`backend/app/`)
- `api/endpoints/chat.py`: Nuevo endpoint WebSockets o POST para comunicación de chat.
- `services/chat_manager.py`: Gestión del estado de la sesión y orquestación del flujo.
- `services/triage_engine.py`: Motor determinístico de enrutamiento basado en regex.
- `models/chat.py`: Modelos Pydantic (`Message`, `TriageResult`).

### Frontend (`frontend/src/`)
- `components/chat/chat-panel.tsx`: Contenedor principal del chat.
- `components/chat/message-list.tsx`: Renderizado del historial de mensajes.
- `components/chat/message-input.tsx`: Campo de entrada y botón de envío.
- `hooks/use-chat.ts`: Hook de React para manejar el estado y la comunicación con el backend.

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| N/A | No hay violaciones. | N/A |
