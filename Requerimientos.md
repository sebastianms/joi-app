# **Documento Maestro de Requerimientos: Plataforma de Generación Dinámica de UI con IA**

**Versión:** 9.0 (Consolidada)  
**Fecha:** 20 de abril de 2026

## **1\. Resumen Ejecutivo**

Este documento detalla los requerimientos para una aplicación avanzada capaz de generar interfaces de usuario (UI) dinámicas y bajo demanda mediante el uso de Inteligencia Artificial Generativa. El sistema se basa en una arquitectura de agentes que interpretan datos y contratos para renderizar **widgets** en tiempo real, manteniendo una total independencia de proveedores tecnológicos (agnóstico) y protegiendo la integridad de las fuentes de datos originales. La App se llama Joi-App (En referencia a Joi de Blade Runner 2049\)

## **2\. Casos de Uso y Flujo del Usuario**

### **2.1. Configuración Inicial (Setup Wizard)**

La aplicación comienza con un proceso de configuración técnica obligatoria:

* **Conexión de Datos:** El usuario debe configurar el acceso a sus fuentes de información. Soporte para:  
  * Bases de Datos Relacionales: PostgreSQL, MySQL y SQLite (ingreso de credenciales).  
  * Archivos Estructurados: Carga de archivos JSON.  
* **Selección de Framework de UI:** Elección de la librería base para los componentes (ej. shadcn/ui, Bootstrap o Ant Design).  
* **Personalización Estética (Design System):** Opción de cargar archivos (ej. PDF) que contengan el sistema de diseño de la empresa para que la IA alinee el estilo visual de los widgets generados.

### **2.2. Interacción Principal y Renderizado**

* **Interfaz Dual:**  
  * **Panel Izquierdo (Chat):** Interfaz de conversación donde el agente inicia con un "¿Qué quieres hacer hoy?".  
  * **Panel Derecho (Lienzo/Canvas):** Espacio en blanco donde se renderizan los widgets de forma dinámica.  
* **Generación Bajo Demanda:** El usuario solicita datos (ej. "Muestra las ventas del último trimestre"). El sistema extrae la data, elige el mejor widget y lo posiciona en el lienzo derecho.

### **2.3. Gestión de Contenidos**

* **Colecciones:** Capacidad de guardar widgets específicos, asignándoles nombres y etiquetas (tags) para categorizarlos.  
* **Dashboards Personalizados:** Sección para importar widgets guardados previamente y organizarlos en un tablero de control a medida.

## **3\. Arquitectura Técnica y de Agentes**

### **3.1. Sistema Multi-Agente**

| Agente | Responsabilidad   |
| :---- | :---- |
| **Agente de Datos (Agente 1\)** | Conecta con APIs o DBs, extrae la información y la entrega en formato estructurado bajo un contrato JSON. |
| **Agente Arquitecto (Agente 2\)** | Analiza la data y el Design System cargado para decidir cuál es el widget más eficiente para la visualización. |
| **Agente Generador (Agente 3/2)** | Escribe el código final (HTML, JavaScript, CSS) basado en el framework seleccionado (shadcn, bootstrap, etc.). |

### **3.2. Estrategia de IA y Optimización**

* **Agnosticismo Total:** Capa de abstracción para intercambiar LLMs (GPT, Claude, Gemini) y proveedores de RAG sin alterar el núcleo.  
* **Optimización Híbrida:** Prioridad absoluta a enfoques **determinísticos** (Regex, lógica de código) para detectar intenciones simples antes de recurrir al procesamiento probabilístico del LLM.  
* **RAG como Caché:** El RAG no guarda definiciones del framework, sino que actúa como caché de **widgets ya creados** y data obtenida, acelerando respuestas futuras.

## **4\. Manejo de Persistencia y Seguridad**

* **Aislamiento de Escritura:** El sistema nunca modifica la base de datos de origen. Posee una base de datos secundaria para guardar "capas" de información nueva (ej. columnas adicionales o archivos nuevos) relacionada con la original.  
* **Privacidad (Multitenancy):** Validación estricta por sesión. Cada usuario tiene su propio entorno aislado; es imposible acceder a los widgets o datos de otros usuarios.

## **5\. Preguntas abiertas**

1. **Eficiencia:** ¿Es posible consolidar al Agente Arquitecto y Generador en uno solo para reducir latencia?  
2. **Triage:** ¿Cómo estructurar el agente ligero de triage para que identifique mediante código si el usuario desea *consultar* o *modificar* datos?  
3. **Componentes:** ¿Qué librería (ej. Tailwind CSS \+ shadcn) facilita que el LLM trabaje con ella mediante contexto de texto en lugar de RAG pesado?  
4. **Almacenamiento:** ¿Es más conveniente persistir la configuración de los Dashboards en la DB SQL secundaria o como metadatos en el RAG?