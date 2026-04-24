# Contract: localStorage Keys

> Namespace: `joi_*`. Ningún componente lee/escribe fuera de estos helpers.

---

## Helper ubicación

Centralizar en `frontend/src/lib/storage/joi-storage.ts`. Ningún componente usa `localStorage` directamente.

---

## Keys

### `joi_session_id`

- **Tipo**: `string` (UUID v4).
- **Escribe**: `SessionBootstrap` al recibir la primera respuesta del backend (ADL-014).
- **Lee**: hooks de sesión, `useOnboardingWizard` (para detectar primera visita).
- **Invariante**: una sola sesión por tab; nunca se sobrescribe mientras exista. Sólo se borra manualmente desde devtools.

### `joi_onboarding_completed`

- **Tipo**: `"true"` o ausente (nada más).
- **Escribe**: `OnboardingWizard.onComplete` al terminar los 3 pasos o presionar "Omitir".
- **Lee**: `useOnboardingWizard` al montar.
- **Invariante**: nunca se escribe `"false"`; eliminar la key es la forma de "resetear".

### `joi_render_mode`

- **Tipo**: `"shadcn" | "bootstrap" | "heroui" | "design_system_disabled"`.
- **Escribe**: `useRenderMode.setMode` tras PUT exitoso al backend.
- **Lee**: runtime del widget (lectura sincrónica al bootstrap para evitar flash).
- **Invariante**: el backend es fuente de verdad. Si hay diff con backend, backend gana; el cliente se sobrescribe.

---

## Seguridad

- localStorage es accesible por cualquier script de la origin. Ninguna de estas keys contiene información sensible (session_id es opaco y se valida en backend).
- Se prohíbe guardar en `joi_*` cualquier credencial, API key, o dato del usuario (p.ej. URLs de conexión de datos).

---

## Testing

- Un test E2E dedicado borra las 3 keys, recarga, y verifica que el wizard aparece + la sesión se re-crea + el render-mode vuelve a default.
