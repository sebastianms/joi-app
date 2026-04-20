# ADL-003: Almacenamiento Local de Estado con SQLite y Gestión de Rutas

**Fecha:** 2026-04-20
**Estado:** Activo
**Área:** Base de Datos
**Autor:** AI Session

---

## Contexto
El sistema requiere una base de datos secundaria para almacenar el estado de las conexiones, sesiones de usuario y metadatos del sistema, independiente de las bases de datos externas que el usuario conecte para consulta.

---

## Decisión
Usar **SQLite** (vía SQLAlchemy + `aiosqlite`) almacenada en la raíz del proyecto (`./joi.db`) en lugar de directorios protegidos por el sistema o carpetas de datos montadas por Docker con permisos de root.

---

## Justificación
Durante el desarrollo se identificó que carpetas como `backend/data/` estaban protegidas por permisos de root (creadas por Docker Compose), impidiendo que el proceso `uvicorn` ejecutado por el usuario local escribiera en la base de datos. Mover la DB a la raíz del proyecto garantiza que el usuario tenga permisos de escritura y simplifica el despliegue local.

---

## Consecuencias

### ✅ Positivas
- Persistencia inmediata sin necesidad de configurar un motor de base de datos pesado (Postgres/MySQL) para el estado interno.
- Facilidad de backup y portabilidad (archivo único).
- Evita errores de `OperationalError: attempt to write a readonly database`.

### ⚠️ Trade-offs aceptados
- SQLite no es ideal para alta concurrencia, pero es suficiente para el manejo de sesiones de usuario del MVP.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| PostgreSQL (Internal) | Requiere levantar un contenedor adicional y configuración de red/permisos más compleja para un MVP. |
| Redis | No provee persistencia relacional estructurada de forma tan nativa como SQLite para metadatos complejos. |

---

## Decisiones Relacionadas
- ADL-001: Arquitectura de Conectores de Datos Multitenant.

---

## Notas para el AI (Memoria Técnica)
- La base de datos de estado se encuentra en `backend/joi.db`.
- Siempre usar el driver `aiosqlite` para mantener la asincronía de FastAPI.
