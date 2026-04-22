# ADL-011: DataAgentService Inyectado por Parámetro en handle() — Tensión Singleton vs Per-Request

**Fecha:** 2026-04-22
**Estado:** Activo
**Área:** Arquitectura
**Autor:** AI Session

---

## Contexto

`ChatManagerService` debe ser un **singleton** a lo largo del ciclo de vida de la aplicación porque mantiene el historial de sesiones en memoria (`_sessions: dict[str, list[Message]]`). Si se instanciara por request, cada mensaje llegaría a una instancia sin memoria de las interacciones anteriores, rompiendo la continuidad de la conversación.

Al implementar T022, `ChatManagerService.handle()` necesita invocar `DataAgentService.extract(...)` para los intents complejos. Pero `DataAgentService` requiere un `SQLiteConnectionRepository` y un `UserSessionRepository`, ambos construidos sobre una `AsyncSession` de SQLAlchemy — que **debe ser per-request** (es el patrón de SQLAlchemy async: una sesión por transacción HTTP, nunca compartida entre requests).

Esto crea una tensión directa:

- `ChatManagerService` → singleton (necesita estado persistente entre requests).
- `DataAgentService` → per-request (necesita `AsyncSession` per-request).

Si `DataAgentService` se inyecta en el constructor de `ChatManagerService`, el singleton captura la sesión del primer request y la reutiliza para todos los siguientes, causando estado compartido entre transacciones — un bug de concurrencia grave con SQLAlchemy async.

---

## Decisión

`DataAgentService` **no se inyecta en el constructor** de `ChatManagerService`. En su lugar, se pasa como **parámetro del método `handle()`**:

```python
async def handle(self, request: ChatRequest, data_agent: DataAgentService) -> ChatResponse:
    ...
```

El endpoint FastAPI construye `DataAgentService` per-request vía `Depends(get_data_agent)` y lo pasa a `handle()` en cada invocación. `ChatManagerService` sigue siendo singleton sin capturar ninguna sesión de base de datos.

---

## Justificación

- **Correctitud transaccional**: cada request obtiene su propia `AsyncSession` limpia. No hay riesgo de estado compartido entre requests concurrentes.
- **Singleton preservado**: `ChatManagerService` mantiene `_sessions` en memoria de forma segura porque ya no tiene referencias a recursos per-request.
- **Sin complejidad extra**: el patrón es directo — el endpoint ya tiene acceso a `DataAgentService` vía `Depends`, basta con pasarlo como argumento. No requiere factories, proxies ni contextvars.
- **Testabilidad**: los tests de `ChatManagerService` instancian un `StubDataAgent` y lo pasan directamente a `handle()`, sin necesidad de parchear dependencias globales ni FastAPI.
- **Consistente con FastAPI idioms**: `Depends` gestiona el ciclo de vida de `DataAgentService` (incluyendo el commit/rollback de la sesión) de forma estándar.

---

## Consecuencias

### ✅ Positivas

- `ChatManagerService` es un POJO testeable: no tiene dependencias de base de datos en su constructor.
- El ciclo de vida de `AsyncSession` permanece bajo control de FastAPI / SQLAlchemy, no de la lógica de negocio.
- Agregar futuros servicios per-request (ej. un `AuditLogService`) sigue el mismo patrón sin refactor del singleton.

### ⚠️ Trade-offs aceptados

- La firma de `handle()` crece con cada servicio per-request nuevo que necesite el manager. Si el número de parámetros crece mucho, se puede agrupar en un objeto `RequestContext`, pero no se hace prematuramente.
- `ChatManagerService` no puede invocar `DataAgentService` de forma autónoma (ej. desde un task en background iniciado dentro del manager); necesitaría recibir el agente de algún caller. Aceptable para el MVP que es estrictamente request-response.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| **Inyectar `DataAgentService` en el constructor de `ChatManagerService`** | El singleton capturaría la `AsyncSession` del primer request. Corrupción de estado entre transacciones en concurrencia. |
| **Hacer `ChatManagerService` per-request también** | Rompe la continuidad del historial de sesiones (la razón de ser del singleton). |
| **Usar `contextvars.ContextVar` para propagar la sesión** | Añade complejidad implícita; los `ContextVar` en FastAPI tienen gotchas con middleware y background tasks. El patrón de parámetro explícito es más claro. |
| **Inyectar una factory `Callable[[], DataAgentService]` en el constructor** | Indirección sin beneficio: el singleton invocaría la factory en `handle()`, lo que es funcionalmente equivalente al parámetro, pero más opaco. |

---

## Decisiones Relacionadas

- **ADL-003** — Local State Storage: confirma que el historial de sesiones vive en memoria en el singleton. Esta ADL explica cómo coexistir con recursos per-request.
- **ADL-009** — Sin framework Text-to-SQL: `DataAgentService` orquesta `SqlAgentAdapter`, que a su vez usa `litellm_client` y SQLAlchemy per-request.

---

## Notas para el AI (Memoria Técnica)

- **No** mover `DataAgentService` al constructor de `ChatManagerService`. El historial de sesiones vive en el singleton; la sesión de base de datos no puede vivir ahí.
- **Sí** pasar `data_agent` como parámetro de `handle()`. Es el punto de integración correcto.
- Si en el futuro se necesita más de un servicio per-request en `handle()`, crear un `dataclass RequestContext` que los agrupe — no acumular parámetros indefinidamente.
- El patrón aplica a cualquier servicio que use `AsyncSession`: repositories, unit-of-work, etc. Nunca capturar una `AsyncSession` en un singleton.
