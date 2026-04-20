# Mission: Joi-App (Generación Dinámica de UI con IA)

## Overview & Motivation
Joi-App es una plataforma avanzada capaz de generar interfaces de usuario (UI) dinámicas y bajo demanda mediante el uso de Inteligencia Artificial Generativa. Inspirada en Joi de Blade Runner 2049, la aplicación interpreta datos y contratos para renderizar widgets en tiempo real, manteniendo independencia de proveedores tecnológicos y protegiendo la integridad de las fuentes de datos.

## Core Workflow
1. **Configuración Inicial:** El usuario conecta sus fuentes de datos (SQL o JSON), selecciona el framework base de UI y opcionalmente carga un Design System.
2. **Interacción:** El usuario conversa en un panel izquierdo (Chat) solicitando visualizar datos.
3. **Generación:** El sistema extrae la data, un agente determina el widget óptimo, y otro genera el código.
4. **Renderizado:** El widget se renderiza dinámicamente en el panel derecho (Lienzo/Canvas).
5. **Gestión:** El usuario guarda widgets en colecciones y arma Dashboards personalizados.

## Scope (MVP vs. Deferred)
**MVP Scope:**
- Soporte para PostgreSQL, MySQL, SQLite y JSON.
- Panel dual (chat / canvas).
- Generación de widgets bajo demanda en tiempo real.
- Sistema multi-agente (Agente de Datos y Agente de Arquitectura/Generación consolidado).
- Persistencia de dashboards y configuración en DB secundaria aislada.
- Aislamiento de escritura (solo lectura en DB original).
- Multitenancy por sesión.

**Deferred Scope:**
- Edición colaborativa en tiempo real.
- Autenticación empresarial compleja (SSO, LDAP).

## Success Metrics
- **Agnosticismo:** Capacidad de cambiar el proveedor de LLM o RAG sin alterar el código núcleo.
- **Latencia:** Tiempo de respuesta desde el prompt hasta el renderizado del widget minimizado.
- **Seguridad y Aislamiento:** Cero modificaciones no deseadas a las bases de datos de origen (100% lectura segura).
- **Fidelidad Visual:** Los widgets generados deben alinearse al sistema de diseño pre-cargado.
