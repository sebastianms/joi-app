# Tech Stack & Architecture: Joi-App

## System Design & Component Architecture
Joi-App utiliza una arquitectura basada en un **Sistema Multi-Agente** acoplado a un entorno de renderizado de UI dinámico.
- **Capa de Interfaz (Frontend):** Panel dual responsivo (Chat a la izquierda, Canvas a la derecha).
- **Orquestador de Agentes:** Enruta y coordina el flujo de los prompts hacia los agentes especializados.
- **Agente de Datos (Agente 1):** Conecta con fuentes de datos (DB o APIs), formula consultas de lectura y entrega la información bajo un contrato JSON estricto.
- **Agente de Arquitectura y Generación (Consolidado):** Analiza el Design System y los datos para seleccionar el widget más adecuado y genera el código final simultáneamente, reduciendo la latencia de llamadas al LLM.
- **Capa de Memoria (RAG):** *Diferida post-MVP* — ver ADL-010. El MVP no incluye memoria vectorial; se re-evaluará al retomar US5 de Feature 003.

## Technology Stack & Configuration
- **Frontend / UI Render Engine:** Next.js (React), que permite la ejecución e inyección segura de código UI en tiempo de ejecución.
- **Framework de Componentes Base:** Tailwind CSS + shadcn/ui por su alta compatibilidad con el contexto de LLMs sin requerir un RAG extenso.
- **Backend / IA Logic:** Python con FastAPI. Llamadas al LLM centralizadas en un gateway `litellm_client` (LiteLLM) — ver ADL-006 (parcialmente superseded) y ADL-009.
- **Modelos de Lenguaje (LLMs):** Agnóstico vía LiteLLM (Soporte para OpenAI, Anthropic Claude, Google Gemini). Routing por `Purpose` (`sql` / `json` / `chat`) con modelos independientes por propósito.
- **Pipeline Text-to-SQL:** Sin framework externo. `SqlAgentAdapter` orquesta `generate (LiteLLM) → guard (ReadOnlySqlGuard, ADL-005) → execute (SQLAlchemy)` — ver ADL-009.

## Data Layer & Persistence
- **Fuentes de Datos de Origen (Solo Lectura):** PostgreSQL, MySQL, SQLite, Archivos JSON.
- **Base de Datos Secundaria (Estado de App):** SQLite, encargado de almacenar metadatos, configuración de conexiones, colecciones de widgets y definiciones de Dashboards.
- **Vector Store (RAG):** *Diferido post-MVP* — ver ADL-010. Cuando US5 se reactive, el stack se re-decide; la investigación en `specs/003-data-agent/research.md` queda como insumo.

## Processing Pipelines
1. **Triage Híbrido:** Primera capa determinística (regex de intención y palabras clave de acción) apoyada por el historial de sesión corto, sirviendo como un filtro eficiente antes de recurrir al procesamiento completo vía LLM.
2. **Extracción (Data Agent):** SQL Query Generation seguro (Read-only) -> Ejecución -> Validación contra Schema JSON.
3. **Diseño (Arquitecto Agent):** JSON Estructurado + Directivas de Diseño -> Selección de Componente.
4. **Generación (Generator Agent):** Componente -> Código UI -> Sanitización.
5. **Caching:** Almacenar metadatos del widget generado exitosamente en el RAG.
