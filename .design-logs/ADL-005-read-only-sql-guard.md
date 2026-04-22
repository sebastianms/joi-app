# ADL-005: Defensa Read-Only en Dos Capas para SQL Generado por LLM

**Fecha:** 2026-04-22
**Estado:** Activo
**Área:** Seguridad
**Autor:** AI Session

---

## Contexto

La Feature 003 (Data Agent) introduce un pipeline Text-to-SQL basado en Vanna + LiteLLM: el LLM genera SQL a partir de prompts en lenguaje natural y un `SqlRunner` lo ejecuta contra fuentes PostgreSQL, MySQL o SQLite del usuario. Esto abre un vector de ataque clásico ("Excessive Agency", OWASP LLM06): un prompt malicioso — directo o vía prompt injection — puede inducir al modelo a generar `DELETE`, `DROP`, `UPDATE` u otras sentencias mutantes.

El `mission.md` exige explícitamente dos invariantes no negociables:

- **"100% lectura segura"**: ninguna fuente del usuario debe ser modificada por el agente.
- **"Cero modificaciones no deseadas"** como Success Metric medible.

Una única capa de defensa es insuficiente: confiar solo en credenciales read-only asume que el usuario configuró correctamente la base de datos; confiar solo en un validador de tokens asume que el validador cubre todos los vectores futuros (nuevas keywords por engine, multi-statement, pragmas). Se necesita **defense in depth**.

---

## Decisión

Se implementa una arquitectura de **dos capas independientes** de defensa read-only:

1. **Capa 1 — Credenciales (responsabilidad del usuario)**: la cadena de conexión persistida en `data_source_connections` debe usar un usuario de BD con privilegios de solo lectura. Validada en el Setup Wizard cuando el engine lo permite.
2. **Capa 2 — `ReadOnlySqlGuard` (responsabilidad del agente)**: validador pre-ejecución en `backend/app/services/read_only_sql_guard.py` que rechaza cualquier SQL generado por el LLM antes de entregarlo al runner. Implementa:
   - **Whitelist del primer token significativo**: solo `SELECT`, `WITH`, `SHOW`, `EXPLAIN`, `PRAGMA` (este último con sub-validación).
   - **Blacklist de keywords**: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`, `REPLACE`, `MERGE`, `CALL`, `EXEC`, `EXECUTE`, `LOCK`, `UNLOCK`, `RENAME`, `VACUUM`, `ATTACH`, `DETACH`, `REINDEX`, `ANALYZE`.
   - **Frases prohibidas**: `COMMENT ON`, `COPY`.
   - **PRAGMA sanitizado**: rechaza pragmas de escritura (`writable_schema`, `journal_mode`, `foreign_keys`, `synchronous`, `locking_mode`, `secure_delete`) y cualquier PRAGMA con asignación `=`.
   - **Multi-statement bloqueado**: tokenización con `sqlparse`; más de una sentencia ejecutable → rechazo.
   - **SQL vacío o solo comentarios**: rechazado.

Cuando el guard rechaza, el `SqlAgentAdapter` emite `DataExtraction(status="error", error.code="SECURITY_REJECTION", query_plan.expression=<sql rechazada>)` y el `AgentTrace` marca `security_rejection=true` para que el frontend muestre el badge correspondiente.

Para el pipeline JSON no se requiere guard: es intrínsecamente read-only (JSONPath sobre contenido cargado en memoria no puede mutar el archivo origen). Se documenta como tal en el trace.

---

## Justificación

- El `mission.md` no permite una sola capa: una credencial mal configurada (p.ej. superuser en desarrollo) podría dejar escritura abierta, y un SQL con CTE anidadas podría evadir un validador de credenciales solo.
- Defense in depth es estándar en sistemas de agentes Text-to-SQL (OWASP LLM06: "Excessive Agency").
- La whitelist del primer token es más restrictiva que una blacklist pura: cualquier nueva sentencia mutante que aparezca en un engine futuro queda bloqueada por defecto (fail-closed).
- `sqlparse` permite detectar multi-statement de forma robusta sin requerir un parser AST completo (overkill para MVP; token matching cubre ~95% de vectores con ~10× menos código).
- El costo de implementación es bajo (~190 LoC + tests) y el guard queda como punto único auditable (SRP estricto).

---

## Consecuencias

### ✅ Positivas

- Cumple los Success Metrics de `mission.md` ("100% lectura segura", "Cero modificaciones no deseadas").
- Fail-closed: cualquier keyword desconocida al primer token se rechaza por defecto.
- Observabilidad: cada rechazo se refleja en el `AgentTrace` con `security_rejection=true`, visible al usuario.
- Auditable: toda ejecución de SQL pasa por un único punto (`ReadOnlySqlGuard.validate`), lo que facilita grep y revisiones de seguridad (ver T056).
- Aislado del resto del sistema: el guard no conoce Vanna ni LiteLLM; puede reutilizarse en futuros pipelines SQL.

### ⚠️ Trade-offs aceptados

- **Falsos positivos posibles**: la whitelist estricta puede rechazar sentencias legítimas raras (`VALUES`, `TABLE` como sentencia top-level en PostgreSQL, `DESCRIBE` en MySQL). Estas se pueden habilitar caso por caso si surgen; por ahora se prefiere rechazar a permitir.
- **Mantenimiento por engine**: nuevas keywords peligrosas por engine (ej. MySQL `HANDLER`, PostgreSQL `LISTEN/NOTIFY`) requieren actualizar las constantes. Aceptable dado que los engines soportados están fijados.
- **No es un parser AST**: un atacante suficientemente sofisticado podría construir SQL semánticamente mutante que evada el token matching (ej. funciones definidas por el usuario que muten en side-effects). Mitigado por la Capa 1 (credenciales read-only) y aceptable para MVP; escalable a AST walker si se detectan evasiones.
- **PRAGMA conservador**: se rechaza cualquier `PRAGMA name=value`, aunque algunos pragmas de solo lectura aceptan `=` en su sintaxis. Preferimos rechazar a permitir.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| **Solo credenciales read-only** | Depende 100% de que el usuario configure bien la BD. En desarrollo es común usar superusers; el agente podría destruir datos. |
| **Solo validador de tokens** | No cubre el caso de credenciales mal configuradas. Además, la capa de credenciales es "gratis" (no cuesta implementación, solo documentación). |
| **Parseo AST completo con walker** | Más robusto que token matching, pero overkill para MVP. Token matching cubre ~95% de vectores con mucho menos código. Escalable si se detectan evasiones. |
| **Solo blacklist de keywords** | No es fail-closed: cualquier keyword mutante nueva (por versión de engine) pasaría hasta que se agregue a la lista. La whitelist del primer token es más segura por defecto. |
| **Confiar en el LLM para no generar SQL mutante** | Los LLMs son probabilísticos; un prompt injection puede cambiar su comportamiento. Política: **nunca** confiar en la salida del LLM para decisiones de seguridad. |

---

## Decisiones Relacionadas

- **ADL-001** — Data Connectors Architecture: define las fuentes soportadas (PostgreSQL, MySQL, SQLite, JSON) que consume este guard.
- **ADL-003** — Local State Storage: el campo `rag_enabled` vive en `UserSession`, ortogonal a esta decisión pero parte del mismo pipeline.
- **research.md R4** (Feature 003): consolidado aquí; esta ADL es el registro canónico.

---

## Notas para el AI (Memoria Técnica)

- **Nunca** ejecutar SQL generado por un LLM sin pasar por `ReadOnlySqlGuard.validate()`. Es un anti-pattern explícito que T056 grep-ea en la auditoría final.
- **Nunca** reemplazar la whitelist del primer token por una blacklist "equivalente": la whitelist es intencional y fail-closed.
- **Nunca** eliminar la validación de multi-statement: es el vector más común de bypass (`SELECT 1; DELETE FROM t`).
- Si un usuario reporta un falso positivo (SQL legítimo rechazado), **no** relajar el guard globalmente; agregar el caso específico con tests que cubran el vector de ataque original.
- Si se detecta una evasión real (SQL mutante que pasa el guard), escalar a parser AST en lugar de agregar más keywords a la blacklist.
- El guard **no** conoce el engine de destino (PostgreSQL/MySQL/SQLite): es intencional. Mantenerlo engine-agnostic preserva la simplicidad. Las keywords peligrosas por engine específico se agregan a la blacklist común.
- El pipeline JSON **no** pasa por este guard y **no** debe hacerlo: es read-only por construcción. Si en el futuro se agrega un pipeline que mute JSON en memoria, requiere su propio guard documentado en un ADL nuevo.
