# ADL-024: PostgreSQL en producción y Alembic para migraciones de schema

**Fecha:** 2026-04-27
**Estado:** Activo
**Área:** Base de Datos — Infraestructura
**Autor:** AI Session (post-Feature 006)

---

## Contexto

Hasta ahora la app usaba **SQLite** en todos los entornos (desarrollo y Docker), con `Base.metadata.create_all` al arrancar para crear las tablas. Este enfoque es suficiente para un MVP pero tiene dos problemas al pasar a producción:

1. **SQLite no es apto para producción**: no soporta concurrencia real, no tiene roles/permisos, y el archivo crece de forma incontrolada.
2. **`create_all` no gestiona cambios de schema**: crea tablas inexistentes pero no modifica ni migra tablas ya existentes. Cualquier `ALTER TABLE` requeriría intervención manual o perder datos.

Se decidió preparar el stack para producción añadiendo PostgreSQL como base de datos de producción y Alembic como gestor de migraciones versionadas.

---

## Decisión

- **PostgreSQL 16 Alpine** se añade como servicio en `docker-compose.yml`, con healthcheck y volumen persistente.
- **Alembic** gestiona el schema en entornos PostgreSQL; `create_all` se mantiene solo para SQLite en desarrollo local.
- El backend detecta el tipo de base de datos al arrancar: si `DATABASE_URL` empieza por `postgresql`, corre `alembic upgrade head`; si no, usa `create_all`.
- La migración inicial (`62c36cb03062`) documenta el schema completo de las 10 tablas existentes.

---

## Justificación

- **PostgreSQL** es el estándar de facto para aplicaciones web en producción: concurrencia, ACID, índices parciales, JSON nativo, roles y permisos.
- **Alembic** es el ORM de migraciones nativo de SQLAlchemy — mismo ecosistema, sin dependencias nuevas significativas.
- Mantener **SQLite + `create_all` en dev** preserva el arranque rápido sin Docker para desarrollo diario. Un developer puede clonar y correr `./dev.sh` sin necesitar Postgres.
- La detección por prefijo de URL (`postgresql` vs `sqlite`) es simple y explícita, sin flags de entorno adicionales.

---

## Consecuencias

### ✅ Positivas
- Schema versionado: cada cambio de modelo genera un archivo de migración revisable y reversible.
- `docker compose up --build` levanta un entorno de producción real con Postgres desde cero.
- `alembic downgrade -1` permite revertir migraciones problemáticas sin pérdida de datos.
- El schema queda documentado en `alembic/versions/` como fuente de verdad versionada en git.

### ⚠️ Trade-offs aceptados
- Los developers deben generar y commitear una migración por cada cambio de modelo ORM. Olvidarlo causa divergencia entre modelos y schema en producción.
- Las bases de datos SQLite existentes en desarrollo no tienen la tabla `alembic_version`. Si se quiere usar Alembic también en dev, hay que stampear con `alembic stamp head` tras la primera vez.
- El primer `docker compose up` tarda más porque descarga la imagen `postgres:16-alpine`.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| SQLite en producción | No soporta concurrencia real; inadecuado para múltiples usuarios simultáneos |
| Mantener solo `create_all` sin Alembic | Cualquier cambio de schema en producción requeriría intervención manual o recrear la DB |
| Usar Alembic también en SQLite (desarrollo) | Añade fricción al onboarding; los devs necesitarían correr `alembic upgrade head` en lugar de simplemente `./dev.sh` |
| MySQL / MariaDB | PostgreSQL ofrece mejor soporte de tipos avanzados (JSONB, arrays) y es el preferido del ecosistema Python/SQLAlchemy |

---

## Decisiones Relacionadas
- ADL-001: define la arquitectura de conectores de datos (SQLAlchemy como capa de acceso).
- ADL-023: RAG Cache usa Qdrant (también en Docker Compose) — mismo patrón de servicio con healthcheck.

---

## Notas para el AI (Memoria Técnica)
- **Todo cambio a un modelo ORM en `backend/app/models/` requiere una migración Alembic**. No es suficiente con modificar el modelo — hay que correr `alembic revision --autogenerate -m "descripcion"` y commitear el archivo generado en `alembic/versions/`.
- La credencial de Postgres en Docker Compose es `joi:joi@postgres:5432/joi` (usuario, password, host, db). Es intencional para desarrollo/staging; en producción real debe venir de un secret manager.
- El `DATABASE_URL` en `docker-compose.yml` override al del `.env` local — no confundir los dos entornos.
- No sugieras volver a `create_all` como estrategia global. La separación dev/prod es intencional.
