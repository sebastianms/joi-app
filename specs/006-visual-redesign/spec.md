# Spec: Feature 006 — Visual Redesign & UX Polish

**Fase**: Phase 7 — Visual Identity & UX  
**Prioridad**: P2 (post Feature 004)  
**Stack**: shadcn/ui + Tailwind CSS v4 (sin dependencias nuevas)  
**Alcance**: Rediseño parcial — identidad visual, layout, componentes clave, onboarding wizard

---

## Contexto

La app funciona correctamente pero la UI es utilitaria y genérica. El nombre **Joi-App** es una referencia directa a *Joi* de Blade Runner 2049 — una IA holográfica, etérea, con presencia visual fuerte pero no invasiva. La estética debe evocar ese universo: oscuro, atmosférico, con acentos de luz fría/cálida, tipografía precisa.

Actualmente:
- Paleta: blanco/zinc genérico de Next.js scaffold.
- Layout: grid básico sin jerarquía visual clara.
- Chat: burbujas planas sin personalidad.
- Canvas: panel vacío sin estado inicial atractivo.
- Setup: formulario funcional pero frío.
- No hay onboarding — el usuario llega a una pantalla en blanco sin saber qué hacer.

---

## User Stories

### US1 — Identidad visual Blade Runner (P1)
**Como** usuario que abre la app por primera vez,  
**quiero** percibir una estética consistente y atmosférica,  
**para** sentir que estoy usando algo especial, no un CRUD genérico.

**Criterios de aceptación:**
- Paleta dark-first con fondo casi negro (`#0a0d12`), acentos en cyan/azul eléctrico (`#00d4ff`) y ámbar cálido (`#f5a623`) para estados de alerta/truncación.
- Tipografía: Geist Sans ya presente — reforzar con pesos y tracking deliberados. Títulos con `letter-spacing` amplio.
- Superficies con sutil efecto glass (backdrop-blur + border semitransparente) en panels, no en todo.
- Glow suave en elementos interactivos (input activo, botón primario).
- Sin gradientes recargados — atmósfera lograda con opacidad y blur, no con colores.

### US2 — Layout dual rediseñado (P1)
**Como** usuario trabajando con datos,  
**quiero** un layout que comunique claramente el propósito de cada panel,  
**para** no perderme entre el chat y el canvas.

**Criterios de aceptación:**
- Header rediseñado: logo/nombre con identidad, navegación mínima, indicador de sesión.
- Panel izquierdo (Chat): header del panel con nombre del agente ("Joi"), indicador de estado (pensando / listo).
- Panel derecho (Canvas): título dinámico del widget activo, indicador de fuente de datos conectada.
- Separador visual entre paneles con profundidad (no solo un borde).
- Responsive: en mobile, tabs para alternar entre chat y canvas (no stack vertical).

### US3 — Componentes de chat rediseñados (P1)
**Como** usuario leyendo respuestas del agente,  
**quiero** una distinción visual clara entre mis mensajes y los del agente,  
**para** poder seguir la conversación fácilmente.

**Criterios de aceptación:**
- Burbujas de usuario: alineadas a la derecha, fondo de acento cyan muy sutil, texto claro.
- Burbujas del agente: sin burbuja contenedora — texto directo con avatar/icono de "Joi" a la izquierda.
- `AgentTrace`: colapsado por defecto con icono de terminal, expandido muestra código con syntax highlight mínimo (no dependencia externa — solo colores CSS para keywords SQL).
- `WidgetGenerationTrace`: badge de status con color semántico (verde/ámbar/rojo) y animación de pulso mientras genera.
- Typing indicator: tres puntos con animación que evoca "procesando" más que "escribiendo".

### US4 — Canvas con estados visuales ricos (P1)
**Como** usuario esperando un widget,  
**quiero** feedback visual atractivo durante la carga,  
**para** no ver una pantalla en blanco.

**Criterios de aceptación:**
- Estado idle: ilustración o patrón sutil (grid de puntos con opacidad baja) + texto de invitación.
- Estado generating: animación de "construcción" — líneas que aparecen progresivamente, no un spinner genérico.
- Estado bootstrapping: overlay con progreso sobre el iframe.
- Estado error: icono y mensaje con tono de alerta, no rojo alarma.
- Transiciones suaves entre estados (200ms ease).

### US5 — Onboarding wizard de primera vez (P2)
**Como** usuario nuevo que abre la app por primera vez,  
**quiero** una guía rápida de 3 pasos que me explique qué puedo hacer,  
**para** llegar al primer widget sin necesitar documentación externa.

**Criterios de aceptación:**
- Se activa automáticamente si no hay `joi_session_id` en localStorage (primera visita).
- 3 pasos en modal/overlay:
  1. **"Conecta tus datos"** — explica que necesitas una fuente SQL o JSON, botón "Ir a configurar".
  2. **"Pregunta por tus datos"** — muestra un ejemplo de prompt, botón "Entendido".
  3. **"Joi genera tu visualización"** — preview estático de un widget, botón "Empezar".
- Puede saltarse con "Omitir".
- No bloquea la app si se omite o se cierra.
- Se puede reabrir desde el header ("¿Cómo funciona?").

### US6 — Setup page rediseñada (P2)
**Como** usuario configurando una fuente de datos,  
**quiero** una página de setup con la misma identidad visual que el resto,  
**para** no sentir que salí de la app.

**Criterios de aceptación:**
- Mismo fondo oscuro y estética que la app principal.
- Formularios con inputs estilizados (borde sutil, focus con glow).
- Feedback de conexión exitosa con animación (check + color verde).
- Feedback de error con mensaje claro y acción sugerida.
- Título y descripción con la voz de Joi ("Conecta tu fuente de datos. Haré el resto.").

---

## Decisiones de diseño

### D1 — Dark-first, no dark-mode toggle
La estética Blade Runner es inherentemente oscura. No implementamos toggle claro/oscuro — la app es dark-first. Simplifica la implementación y mantiene la identidad coherente.

### D2 — Sin librerías de animación externas
Framer Motion u otras no se introducen. Todas las animaciones son CSS (Tailwind `animate-*`, `transition-*`) o keyframes custom en `globals.css`. Mantiene el bundle pequeño.

### D3 — Glass morphism acotado
El efecto glass (`backdrop-blur` + `bg-white/5` + `border-white/10`) se aplica SOLO a: panels principales, modal de onboarding, header. No en botones, inputs ni componentes pequeños — evita el efecto "todo flota".

### D4 — Paleta de tokens CSS
Todos los colores se definen como CSS variables en `globals.css` y se referencian via Tailwind. Ningún color hardcodeado en componentes. Facilita ajustes futuros.

```css
/* Propuesta de tokens */
--joi-bg:          #0a0d12;   /* fondo base */
--joi-surface:     #111520;   /* superficie de panels */
--joi-border:      rgba(255,255,255,0.08);  /* bordes sutiles */
--joi-accent:      #00d4ff;   /* cyan eléctrico — acción primaria */
--joi-accent-warm: #f5a623;   /* ámbar — alertas, truncación */
--joi-text:        #e2e8f0;   /* texto principal */
--joi-muted:       #64748b;   /* texto secundario */
--joi-glow:        rgba(0,212,255,0.15);    /* glow del acento */
```

### D5 — Componentes existentes primero
Antes de crear componentes nuevos, se extienden los existentes con las clases de Tailwind nuevas. Solo se crean componentes nuevos para el onboarding wizard (US5) que no tiene equivalente.

---

## Alcance explícito (qué NO entra)

- No se rediseñan los renderers del widget (viven en el iframe sandboxed).
- No se cambia la estructura de rutas.
- No se introducen dependencias de UI adicionales (ni Framer Motion, ni Radix Dialog extra si ya existe, etc.).
- No se implementa modo claro.
- No se toca el CSS del widget-runtime bundle.

---

## Referencias visuales

- *Blade Runner 2049* — paleta de escenas con Joi: azul eléctrico sobre negro profundo, partículas, hologramas.
- [Linear](https://linear.app) — minimalismo funcional, dark UI con jerarquía clara.
- [Vercel Dashboard](https://vercel.com/dashboard) — surfaces con glass sutil, tipografía precisa.

---

## Métricas de éxito

- Lighthouse Accessibility ≥ 90 (los colores de contraste deben cumplir WCAG AA).
- Ninguna dependencia nueva en `package.json`.
- Bundle size del frontend no aumenta más de 10KB gzipped respecto al estado pre-006. Baseline = tamaño gzipped del build de `main` al 2026-04-24; verificación **manual** en el PR (sin Action dedicada).
- Los 22 tests E2E existentes siguen pasando sin modificación (los `data-role` y `aria-label` se preservan).

---

## Clarifications

### Session 2026-04-24

- **Q1 — Paleta CSS**: Los valores propuestos (bg #0a0d12, surface #111520, accent #00d4ff, warm #f5a623) NO se congelan al iniciar. Antes del Plan, se produce un **mockup visual** (screenshot/componente de referencia renderizado) con la paleta aplicada al layout dual y al chat. El usuario valida el mockup y recién ahí se emiten los tokens CSS definitivos en [frontend/src/app/globals.css](frontend/src/app/globals.css). La decisión sobre nombres de tokens (D4) sí queda como está en el spec.
- **Q2 — Breakpoint responsive**: En `< 768px` (breakpoint `md` de Tailwind) el layout cambia de dual-panel a **tabs** para alternar entre chat y canvas. En `≥ 768px` siempre dual-panel. Contratos: el componente raíz expone un hook `useLayoutMode()` que devuelve `"dual" | "tabs"`, y los tabs tienen `data-role="layout-tab-chat"` / `data-role="layout-tab-canvas"`.
- **Q3 — Trigger del onboarding wizard**: Se activa **solo** cuando `localStorage.getItem("joi_session_id") === null` (primera visita absoluta). Sessions existentes NO lo ven automáticamente. Botón "¿Cómo funciona?" del header lo reabre manualmente. La flag `onboarding_completed` del cliente se guarda también en `localStorage`, no en la DB (no se requiere columna en `UserSession`).
- **Q4 — Render-mode selector y adaptadores UI (T129–T131, T501–T507 de Feature 004)**: **Entran en el alcance de Feature 006 Visual Redesign**. US6 ahora incluye: (a) selector visual shadcn/bootstrap/heroui + Design System deshabilitado en el Setup redesignado, (b) implementación de adaptadores UI para el runtime del widget (T129–T131 Feature 004), (c) cobertura de Escenarios 6–7 y 11–12 del quickstart de Feature 004. El backlog diferido de 004 queda cerrado al completar esta feature. ADL-022 (render-mode-profile-deferred) pasa a "Superseded by Feature 006".
- **Q5 — Bundle size budget**: El baseline es el tamaño gzipped del build de `main` al **2026-04-24**. Se documenta el valor exacto en el Plan (tras correr `npm run build` sobre el HEAD actual). Verificación **manual** por el PR reviewer — no se añade GitHub Action dedicada. Si se excede +10KB, el PR se bloquea hasta optimización.
