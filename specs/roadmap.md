# Roadmap: Joi-App

## Phase 1: Setup & Constitution [DONE]
- [x] Inicializar repositorio y estructura de directorios.
- [x] Establecer definiciones tecnológicas faltantes y resolver `[NEEDS CLARIFICATION]`.
- [x] Consolidar la documentación SDD de Constitución.

## Phase 2: Foundational Elements [DONE]
- [x] Configuración del esqueleto Frontend (Dual Panel UI).
- [x] Implementación de la capa de acceso a base de datos segura (Read-only).
- [x] Implementación de la base de datos secundaria para almacenamiento de estado.
- [x] Configuración de la capa de abstracción para Modelos LLM (FastAPI structure).

## Phase 3: Setup Wizard & Data Connectors [DONE]
- [x] UI y lógica para el asistente de configuración.
- [x] Conectores de base de datos (PostgreSQL, MySQL, SQLite, JSON) interactivos.
- [ ] Módulo de selección de framework UI y carga de Design System — diferido a Phase 7 US6.

## Phase 4: Chat Engine & Hybrid Triage (Shippable Slice 2) [DONE]
- [x] Implementación del sistema de chat interactivo.
- [x] Construcción del motor de Triage (Enfoque determinístico — regex/keywords).
- [x] Ruteo de intenciones simples vs complejas.
- [ ] Capa probabilística (LLM classifier) — diferida a Feature 003.

## Phase 5: Multi-Agent Pipeline & Rendering Canvas (Shippable Slice 3) [DONE]
- [x] Desarrollo del Agente de Datos (Text-to-SQL y Extracción a JSON) — Feature 003 (US1–US4). Pipelines SQL y JSON operativos con guard read-only, manejo de errores graceful y Agent Trace en el chat.
- [x] Desarrollo del Agente Arquitecto/Generador para la creación de código del widget — Feature 004 (US1–US2). Selector determinístico (R1), generador LLM, fallback tabular, preferencia explícita del usuario con triage extendido.
- [x] Motor de sanitización e inyección dinámica del widget en el Canvas derecho — Feature 004 (US3–US4). iframe sandbox CSP (R4), protocolo postMessage, timeout 4s, fallback universal, error banner con continuidad de sesión. Polish pendiente (T901–T910).

## Phase 6: Dashboards, Collections & RAG Cache (Shippable Slice 4) — Feature 005
Carpeta: [specs/005-dashboards-collections/](005-dashboards-collections/). US1–US5 implementadas (2026-04-24); Polish en curso.
- [x] Funcionalidad para etiquetar y guardar widgets en colecciones (US1–US2, relación widget ↔ colección N:M).
- [x] Implementación de Dashboards personalizados reordenables con grid drag-and-drop (US3).
- [x] Recuperación de widgets guardados desde el chat por nombre (US4).
- [x] Integración del sistema RAG como memoria caché de widgets (US5) — activada sobre LangChain + Qdrant default (Docker) + BYO vector store opcional (Chroma/Pinecone/Weaviate/PGVector). Supersedencia parcial de ADL-010 documentada en [ADL-023](../.design-logs/ADL-023-rag-langchain-byo-vector-store.md).

## Phase 7: Visual Redesign & UX Polish — Feature 006
Carpeta: [specs/006-visual-redesign/](006-visual-redesign/). Spec, Clarify, Plan y Tasks listos (2026-04-24). Incluye cierre del backlog diferido de Feature 004 (T129–T131 adaptadores UI; T501–T507 render-mode selector) — supersede ADL-022 al completar Implement.
- [ ] Identidad visual Blade Runner 2049: paleta dark-first, tokens CSS, glow/glass acotado (US1).
- [ ] Layout dual rediseñado: header, separador de panels, responsive mobile (US2).
- [ ] Componentes de chat rediseñados: burbujas, AgentTrace, WidgetGenerationTrace (US3).
- [ ] Canvas con estados visuales ricos: idle, generating, bootstrapping, error (US4).
- [ ] Onboarding wizard de primera vez: modal 3 pasos, activación automática (US5).
- [ ] Setup page rediseñada con la identidad visual de la app (US6).
  - Incluye selector de render-mode (shadcn/bootstrap/heroui + Design System deshabilitado) — Feature 004 T501–T507 diferidas.
  - Incluye implementación de adaptadores UI para el runtime del widget (T129–T131) y cobertura de Escenarios 6–7 y 11–12 del quickstart de Feature 004 (T307, T507).

> **Nota (actualizada 2026-04-24)**: La infraestructura RAG se **activó en Feature 005 (Phase 6)** como caché semántico de widgets. ADL-010 queda parcialmente superseded por [ADL-023](../.design-logs/ADL-023-rag-langchain-byo-vector-store.md): LangChain como capa de abstracción, Qdrant default (Docker), BYO vector store opcional (Chroma/Pinecone/Weaviate/PGVector), embeddings `text-embedding-3-small` vía LiteLLM controlados por Joi.
