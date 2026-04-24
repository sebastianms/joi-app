# Quickstart: Feature 005 — Escenarios de validación E2E

> Cada escenario verifica end-to-end una user story. Ejecutar tras `Implement` completo. Precondición común: backend + frontend + Qdrant corriendo vía `docker compose up`, un `UserSession` con al menos una conexión de datos activa.

---

## Escenario 1 — Guardar un widget en varias colecciones (US1 + US2, Q3 N:M)

1. Genera un widget con un prompt válido (p.ej. "ventas por mes 2025").
2. Click en "Guardar" sobre el widget.
3. En el diálogo, teclea "Ventas 2025" como nombre y selecciona dos colecciones: "Anual" (nueva, créala inline) y "Comercial".
4. Confirma.
5. Navega a `/collections`. Deben aparecer "Anual" y "Comercial", cada una listando el widget "Ventas 2025" con el mismo `widget_id`.
6. Entra a "Comercial" y **elimina** la colección. Verifica que "Anual" sigue listando el mismo widget y que el widget continúa accesible desde `/widgets?is_saved=true`.

**Esperado**: el registro en `collection_widgets` correspondiente a "Comercial" es borrado por CASCADE; el widget permanece.

---

## Escenario 2 — Dashboard con layout persistente (US3, FR-005/FR-006)

1. Con al menos 3 widgets guardados, crea un dashboard llamado "Resumen".
2. Arrastra los 3 widgets desde la sidebar de colecciones al grid.
3. Reordena: lleva uno a la esquina inferior derecha; redimensiona otro a `6×4`.
4. Refresca la página.
5. Los tres widgets deben aparecer exactamente en la misma posición y tamaño.
6. Elimina un item del dashboard. Verifica que el widget sigue existiendo en su colección.

**Esperado**: `PATCH /api/dashboards/{id}/layout` persistió las celdas; al cargar, `GET /api/dashboards/{id}` restaura el layout.

---

## Escenario 3 — Recuperar widget por nombre desde el chat (US4)

1. Con un widget guardado "Churn mensual 2025" en cualquier colección.
2. En una **nueva conversación** escribe: "muéstrame Churn mensual 2025".
3. El canvas debe renderizar el widget guardado sin invocar al Agente Generador.
4. El `WidgetGenerationTrace` indica claramente "recuperado desde biblioteca" (no "caché").

**Esperado**: triage determinístico detecta la intención; no hay llamada al LLM de generación. Si cambiás el prompt por "Churn" (ambiguo con otro widget "Churn por región"), Joi responde listando candidatos.

---

## Escenario 4 — RAG cache hit con Qdrant default (US5, Clarify Q2)

1. Con Qdrant default (sin BYO config).
2. Genera widget A con prompt "ingresos mensuales por región en 2025".
3. Sin cambiar la conexión ni los datos, escribe un prompt semánticamente similar: "revenue por región durante 2025".
4. Joi responde con tarjeta `CacheReuseSuggestion` mostrando preview de A, score ≥ 0.85, y dos botones.
5. Presiona "Usar este widget". Verifica en el trace que no hubo llamada al Agente Generador, y que la data se re-ejecutó contra la conexión.
6. Incrementa `hit_count` a 1 en `widget_cache_entries`.
7. Repite el prompt similar, pero esta vez presiona "Generar uno nuevo". Verifica que se generó widget B distinto, y que se registró un nuevo `WidgetCacheEntry` para B.

**Esperado**: el endpoint `/api/chat` devuelve `cache_suggestion` sin generar; al reusar, llama internamente a `POST /widget-cache/{id}/reuse`; al rechazar, re-invoca `/chat` con `skip_cache=true`.

---

## Escenario 5 — BYO vector store (Pinecone) (FR-017 a FR-019)

1. Con la app corriendo y Qdrant default activo, abrir Setup Wizard → paso "Vector store (opcional)".
2. Elegir provider `pinecone`, completar api_key, index_name, environment.
3. Presionar "Validar". Debe volver `valid: true`.
4. Presionar "Guardar". La config queda persistida cifrada.
5. Verificar `GET /api/vector-store/config` devuelve `{ provider: "pinecone", is_default: false }` sin credenciales visibles.
6. Genera un widget nuevo. En el trace aparece `vector_store: pinecone`.
7. Escribe un prompt similar a uno previo del default-Qdrant. Verifica que el match **no se encuentra** porque el caché previo vivía en Qdrant, y el pipeline genera uno nuevo que se indexa en Pinecone.
8. Volver a Setup → "Usar Qdrant por defecto". Al borrar la config, el caché local queda huérfano (documentado, no se migra).

**Esperado**: el factory despacha a `langchain_pinecone.PineconeVectorStore`; ningún import directo de `qdrant-client` se ejecuta en este flujo.

---

## Escenario 6 — Fallback con vector store caído (FR-013)

1. Detener el contenedor Qdrant: `docker compose stop qdrant`.
2. Observar que `GET /api/vector-store/health` responde `healthy: false`.
3. Generar un widget nuevo. El pipeline procede normal, sin sugerencia de caché y sin indexado (se registra warning en logs).
4. Arrancar Qdrant: `docker compose start qdrant`.
5. Re-generar un widget similar. El sistema vuelve a indexar (pero el widget del paso 3 no está, porque no se cacheó).

**Esperado**: cero errores 500 al usuario; degradación silenciosa.

---

## Escenario 7 — Invalidación del caché por cambio de schema (FR-011, Clarify Q5)

1. Generar widget "ventas por región" sobre una tabla `sales(region, total)`.
2. Alterar la conexión (a través de un mock controlado de test, no SQL directo) para que el schema incluya una nueva columna; esto cambia `data_schema_hash`.
3. Repetir el prompt "ventas por región".
4. El caché no devuelve el widget previo porque el filtro `data_schema_hash` falla. Se genera uno nuevo y se indexa con el hash nuevo.

**Esperado**: se crean dos `widget_cache_entries` para el mismo prompt, una por hash.

---

## Escenario 8 — Dashboard abierto con conexión faltante (Clarify Q5)

1. Dashboard "Resumen" con 3 widgets de la conexión `conn-A`.
2. Eliminar `conn-A`.
3. Abrir `/dashboards/{id}`.
4. Los 3 widgets muestran estado de error localizado con botón "Reintentar"; el dashboard no crashea; los `WidgetCacheEntry` vinculados a `conn-A` pasan a `invalidated_at != NULL`.

**Esperado**: integridad del dashboard intacta; hit_count del caché no aumenta; UI comunica claramente que los datos no están disponibles.

---

## Pruebas automatizadas esperadas al cerrar Tasks

- Backend: unit tests del factory de provider (mocks por branch), cache_service (índice + búsqueda + invalidación), repositorios CRUD.
- Backend: integration tests con Qdrant embebido en container (testcontainers-python) para dos escenarios clave (hit y miss).
- Frontend: tests de componentes (`DashboardGrid`, `CacheReuseSuggestion`, `SaveWidgetDialog` con multi-select).
- E2E Playwright: al menos escenarios 1, 2, 4 y 6 automatizados (los demás pueden ser manuales en el MVP).
