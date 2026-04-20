# Tech Stack & Architecture: Joi-App

## System Design & Component Architecture
Joi-App utiliza una arquitectura basada en un **Sistema Multi-Agente** acoplado a un entorno de renderizado de UI dinámico.
- **Capa de Interfaz (Frontend):** Panel dual responsivo (Chat a la izquierda, Canvas a la derecha).
- **Orquestador de Agentes:** Enruta y coordina el flujo de los prompts hacia los agentes especializados.
- **Agente de Datos (Agente 1):** Conecta con fuentes de datos (DB o APIs), formula consultas de lectura y entrega la información bajo un contrato JSON estricto.
- **Agente de Arquitectura y Generación (Consolidado):** Analiza el Design System y los datos para seleccionar el widget más adecuado y genera el código final simultáneamente, reduciendo la latencia de llamadas al LLM.
- **Capa de Memoria (RAG):** Actúa como caché rápida de widgets pre-generados y asociaciones exitosas de datos, acelerando consultas repetidas. No se utiliza para guardar documentación completa del framework.

## Technology Stack & Configuration
- **Frontend / UI Render Engine:** Next.js (React), que permite la ejecución e inyección segura de código UI en tiempo de ejecución.
- **Framework de Componentes Base:** Tailwind CSS + shadcn/ui por su alta compatibilidad con el contexto de LLMs sin requerir un RAG extenso.
- **Backend / IA Logic:** Python utilizando el framework LangChain.
- **Modelos de Lenguaje (LLMs):** Agnóstico (Soporte para OpenAI, Anthropic Claude, Google Gemini).

## Data Layer & Persistence
- **Fuentes de Datos de Origen (Solo Lectura):** PostgreSQL, MySQL, SQLite, Archivos JSON.
- **Base de Datos Secundaria (Estado de App):** SQLite, encargado de almacenar metadatos, configuración de conexiones, colecciones de widgets y definiciones de Dashboards.
- **Vector Store (RAG):** El almacenamiento vectorial integrado de LangChain (ej. Chroma local o memoria vector store base) para el almacenamiento y recuperación de contexto de widgets generados previamente.

## Processing Pipelines
1. **Triage Híbrido:** Primera capa determinística (regex de intención y palabras clave de acción) apoyada por el historial de sesión corto, sirviendo como un filtro eficiente antes de recurrir al procesamiento completo vía LLM.
2. **Extracción (Data Agent):** SQL Query Generation seguro (Read-only) -> Ejecución -> Validación contra Schema JSON.
3. **Diseño (Arquitecto Agent):** JSON Estructurado + Directivas de Diseño -> Selección de Componente.
4. **Generación (Generator Agent):** Componente -> Código UI -> Sanitización.
5. **Caching:** Almacenar metadatos del widget generado exitosamente en el RAG.
