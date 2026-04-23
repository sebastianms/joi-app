# ADL-022: RenderModeProfile y Setup Wizard — Modelo de Datos Implementado, UI Diferida

**Fecha:** 2026-04-23
**Estado:** Activo — UI/endpoints diferidos a Feature 005 US6
**Área:** Arquitectura / Backend / Frontend
**Autor:** AI Session

---

## Contexto

Feature 004 planificó un Step 2 en el Setup Wizard donde el usuario elige la librería UI para sus widgets (shadcn, Bootstrap, HeroUI, o Design System "próximamente"). Esta elección se persiste en `render_mode_profiles` ligada al `session_id` y se consulta en cada generación de widget.

El diseño original incluía:
- Modelo de datos `RenderModeProfile` + ORM + repositorio (T010–T012)
- Endpoints `GET/PUT /api/render-mode/profile` (T501–T503)
- Componente `render-mode-step.tsx` en el wizard (T504–T505)
- Tests E2E del wizard (T506)
- Cobertura manual Escenarios 11–12 (T507)

Durante la implementación, T010–T012 se completaron (modelo, ORM, repositorio) porque son prerequisito de la lógica de generación. Sin embargo, los endpoints y la UI se diferieron al descubrir que:

1. Los adaptadores de librería (T129–T131) — los wrappers de Card/Table/etc. dentro del iframe — solo tienen sentido en modo `free_code`, que no está activo en el MVP.
2. En modo `ui_framework`, el runtime bundle usa Recharts directamente sin pasar por adaptadores de librería.
3. La selección visual de framework pertenece naturalmente a la **identidad visual de la app** (Feature 005), no al flujo de datos.

---

## Decisión (R7 — parcialmente implementado)

### Qué está implementado

- `RenderModeProfile` Pydantic + `RenderModeProfileORM` SQLAlchemy en `backend/app/models/render_mode.py`
- Tabla `render_mode_profiles` creada en `main.lifespan()` junto a las demás
- `RenderModeRepository.get_or_create(session_id)` con default `ui_framework` + `shadcn`
- Default lazy: si la sesión no tiene perfil, se usa el default en `chat_manager.py` sin consulta DB

### Qué está diferido a Feature 005 US6

- `GET/PUT /api/render-mode/profile` (T501–T503)
- `render-mode-step.tsx` en el wizard (T504–T505)
- Adaptadores de librería en el bundle del iframe (T129–T131)
- Tests E2E del wizard + Escenarios 11–12 del quickstart de Feature 004 (T506–T507)

**Condición de activación**: cuando Feature 005 US6 rediseñe el Setup Wizard con la identidad visual de la app, ese es el momento natural para incorporar el selector de framework, ya que implica cambios estructurales al wizard de todos modos.

---

## Consecuencias

### ✅ Positivas
- El modelo de datos ya existe — Feature 005 solo necesita conectar la UI y los endpoints.
- No hay migración de schema al activar la UI: la tabla ya está creada y el default lazy funciona.
- El chat_manager.py ya consulta el perfil de render en cada request — el default shadcn fluye correctamente.

### ⚠️ Trade-offs aceptados
- Hasta Feature 005, todos los usuarios usan shadcn/ui sin posibilidad de cambiar. Esto es aceptable para el MVP.
- Los adaptadores bootstrap/heroui no tienen cobertura de tests hasta que se activen.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|---|---|
| Implementar UI ahora sin Feature 005 | Crearía un Setup Wizard inconsistente visualmente (viejo diseño + nuevo step) |
| No implementar el modelo de datos hasta Feature 005 | El chat_manager necesita el default lazy en cada request — mejor tenerlo ya |

---

## Decisiones Relacionadas
- ADL-019: Arquitectura del agente generador (modos de render)
- ADL-020: Canvas iframe sandbox (adaptadores de librería viven en el bundle)

---

## Notas para el AI (Memoria Técnica)
- `RenderModeRepository` en `backend/app/repositories/render_mode_repository.py` ya está implementado. No reimplementes ni dupliques.
- Al implementar los endpoints en Feature 005, registrar el router en `backend/app/api/router.py`.
- `design_system` como modo de render está **permanentemente deshabilitado en el MVP**. El validador Pydantic en `render_mode.py` lo rechaza. No lo habilites sin una decisión explícita.
- Los adaptadores (T129–T131) van en `frontend/src/lib/widget-runtime/adapters/`. El directorio no existe aún.
