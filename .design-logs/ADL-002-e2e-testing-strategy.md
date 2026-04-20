# ADL-002: Estrategia de Testing E2E y Resolución de Hidratación

**Fecha:** 2026-04-20
**Estado:** Activo
**Área:** Frontend / QA
**Autor:** AI Session

---

## Contexto
Durante la implementación del Setup Wizard, se detectaron fallos en los tests E2E donde los formularios realizaban recargas de página (GET) en lugar de envíos asíncronos (AJAX), rompiendo la experiencia SPA y dificultando la detección de alertas en Playwright.

---

## Decisión
1. Adoptar **Playwright** como estándar para pruebas E2E integradas en el repositorio.
2. Forzar la hidratación completa del lado del cliente usando la directiva `"use client"` en la página raíz y habilitando `allowedDevOrigins: ["127.0.0.1"]` en `next.config.ts`.
3. Estandarizar la comunicación frontend-backend usando `127.0.0.1` para evitar discrepancias de resolución entre IPv4/IPv6.

---

## Justificación
Next.js 15+ tiene políticas de seguridad estrictas que bloquean el Hot Module Replacement (HMR) y la hidratación si el origen detectado no coincide con el configurado (específicamente cuando se accede vía IP). Sin esto, los `event handlers` de React no se adjuntan, resultando en formularios HTML nativos con comportamiento por defecto.

---

## Consecuencias

### ✅ Positivas
- Suite de tests E2E robusta que valida flujos críticos de éxito y error.
- Garantía de que la interactividad de la UI funciona correctamente en entornos de desarrollo locales.

### ⚠️ Trade-offs aceptados
- Se tuvo que simplificar el componente `Form` de shadcn en algunos casos para asegurar que `e.preventDefault()` fuera llamado de forma infalible antes de cualquier validación asíncrona.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Cypress | Playwright ofrece mejor integración con el ecosistema de CI/CD y soporte superior para múltiples navegadores en entornos Linux. |
| Deshabilitar SSR | Perderíamos los beneficios de performance y SEO de Next.js. |

---

## Decisiones Relacionadas
- ADL-001: Arquitectura de Conectores de Datos Multitenant.

---

## Notas para el AI (Memoria Técnica)
- No remover `allowedDevOrigins` de `next.config.ts` mientras se use `127.0.0.1` para tests.
- Asegurar que cualquier nuevo formulario use explícitamente `e.preventDefault()` o esté correctamente envuelto en un Client Component hidratado.
