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
- [ ] Módulo de selección de framework UI y carga de Design System (Diferido - Ver Spec 001).

## Phase 4: Chat Engine & Hybrid Triage (Shippable Slice 2) [DONE]
- [x] Implementación del sistema de chat interactivo.
- [x] Construcción del motor de Triage (Enfoque determinístico — regex/keywords).
- [x] Ruteo de intenciones simples vs complejas.
- [ ] Capa probabilística (LLM classifier) — diferida a Feature 003.

## Phase 5: Multi-Agent Pipeline & Rendering Canvas (Shippable Slice 3)
- Desarrollo del Agente de Datos (Text-to-SQL y Extracción a JSON).
- Desarrollo del Agente Arquitecto/Generador para la creación de código del widget.
- Motor de sanitización e inyección dinámica del widget en el Canvas derecho.

## Phase 6: Dashboards, Collections & RAG Cache (Shippable Slice 4)
- Funcionalidad para etiquetar y guardar widgets en colecciones.
- Implementación de Dashboards personalizados reordenables.
- Integración final del sistema RAG como memoria caché de widgets.
