# ADL-004: Integración del Chat como Home Dual-Panel y Contrato con Backend

**Fecha:** 2026-04-21
**Estado:** Activo
**Área:** Frontend
**Autor:** AI Session

---

## Contexto
La Feature 002 (Chat Engine & Hybrid Triage) requiere que el chat sea la superficie principal de interacción con Joi-App, con el "Canvas" a la derecha reservado para los widgets que generará el pipeline multi-agente en la Feature 003. Antes de este slice, la ruta raíz (`/`) era el Setup Wizard de conectores de datos (Feature 001). También era necesario definir cómo el frontend gestionaría el estado de la conversación y cómo se comunicaría con el endpoint `POST /api/chat/messages` respetando la contractualidad Pydantic expuesta por el backend (campos `session_id`, `message`, respuesta con `response` e `intent_type`).

Restricciones relevantes:
- El backend mantiene el historial por `session_id` en memoria (ver `ChatManagerService`). El frontend debe generar y conservar un `session_id` estable durante la vida de la pestaña.
- El tech-stack (`specs/tech-stack.md`) exige un layout dual responsivo (Chat izquierda, Canvas derecha).
- La spec 002 declara el historial como efímero: no se requiere persistencia.
- Los componentes deben ser compatibles con React Server Components (Next.js 16) y Tailwind 4 + shadcn/ui.

---

## Decisión
1. La ruta raíz `/` pasa a ser el layout dual (Chat + Canvas placeholder). El Setup Wizard se reubica bajo `/setup`, accesible desde un enlace en el header del home.
2. El chat se estructura en cuatro piezas desacopladas:
   - **Hook `useChat`**: única fuente de verdad del estado del chat (mensajes, `isSending`, `error`, `sessionId`). Genera el `session_id` con `crypto.randomUUID` y lo persiste vía `useRef` durante la vida del componente (no sobrevive a refrescos, consistente con la spec).
   - **`MessageInput`**: componente puramente controlado, recibe `onSend` por prop.
   - **`MessageList`**: renderiza burbujas con roles ARIA (`log`, `aria-live`) y auto-scroll vía `scrollIntoView`.
   - **`ChatPanel`**: ensambla hook + list + input y expone alertas de error.
3. El contrato con el backend se encapsula exclusivamente dentro del hook: el resto de la UI no conoce fetch, URLs ni la forma del payload.

---

## Justificación
- **Separación hook / presentación**: aplica DIP — los componentes visuales son reemplazables y testables sin mockear fetch. El hook puede evolucionar a WebSockets o streaming sin afectar la UI.
- **`session_id` en `useRef`**: se evita regenerar el id en cada render y se alinea con la naturaleza efímera declarada en la spec sin introducir localStorage (que implicaría una decisión de privacidad/persistencia no discutida).
- **Home = chat**: refuerza la propuesta de valor de Joi-App (interfaz conversacional sobre datos). El Setup Wizard pasa a ser una configuración secundaria, no la primera pantalla.
- **ARIA y selectors accesibles**: habilitan tests e2e estables (`getByRole`, `getByLabel`) sin acoplarse a clases CSS, y mejoran accesibilidad para screen readers.
- **`data-role` en las burbujas**: gancho de testing estable e insensible a cambios de estilos.

---

## Consecuencias

### ✅ Positivas
- El chat queda como superficie principal, alineado con la misión del producto.
- Los cuatro componentes del frontend son unidades pequeñas, cada una con SRP, lo que facilita iteración visual sin regresiones lógicas.
- El hook `useChat` centraliza el transporte; migrar a streaming SSE o a WebSockets solo requiere modificar un archivo.
- Los tests e2e usan roles y labels, reduciendo su fragilidad frente a refactors visuales.

### ⚠️ Trade-offs aceptados
- El `session_id` se pierde al recargar la pestaña, por lo que el contexto conversacional también se pierde. Aceptable según la spec actual; la Feature 003+ probablemente necesite persistencia.
- El endpoint se consume con `fetch` + `JSON.stringify` manual, sin una capa de cliente generada (tRPC/OpenAPI). Suficiente mientras haya pocos endpoints; se revisará si el API crece.
- Los selectors por rol dependen de que los componentes mantengan atributos `aria-label` estables. Cambios accidentales en esos labels romperán los e2e.
- Al reubicar el setup a `/setup`, cualquier bookmark o link externo previo a `/` queda apuntando al chat, no al wizard.

---

## Alternativas Consideradas

| Alternativa | Razón de descarte |
|-------------|-------------------|
| Mantener setup wizard en `/` y agregar chat en `/chat` | Contradice la misión (el chat es la UX principal) y obliga al usuario a navegar para usar el producto. |
| Guardar `session_id` en `localStorage` | Introduce decisión de privacidad/persistencia no justificada por la spec actual, que declara el historial como efímero. |
| Colocar el estado del chat en un store global (Zustand/Redux) | Overkill: un único consumidor (`ChatPanel`) justifica un hook local. Se evaluará si aparecen múltiples consumidores. |
| Cliente tipado autogenerado (OpenAPI/tRPC) | Fricción de setup desproporcionada con un único endpoint; se puede migrar cuando la superficie del API crezca. |
| Usar un textarea con `shift+Enter` = nueva línea | Requiere un componente adicional de shadcn/ui no instalado; el input simple cubre el caso de uso inicial sin añadir dependencias. |

---

## Decisiones Relacionadas
- ADL-001 (Data Connectors Architecture): los conectores siguen disponibles bajo `/setup`, sin cambios en su lógica.
- ADL-002 (E2E Testing Strategy): se extiende la suite Playwright con `chat-basic.spec.ts` siguiendo el mismo patrón establecido.
- ADL-003 (Local State Storage): el estado del chat es intencionalmente volátil y no se integra con el almacenamiento local definido allí.

---

## Notas para el AI (Memoria Técnica)
- **No** muevas el fetch del chat a un componente visual; todo el transporte vive dentro de `useChat` (`frontend/src/hooks/use-chat.ts`).
- **No** regeneres el `session_id` en cada render: debe permanecer estable vía `useRef` durante la vida del componente.
- **No** persistas el historial en `localStorage`/IndexedDB sin actualizar este ADL y la spec 002. El diseño asume historial efímero.
- **No** cambies `aria-label="Mensaje"`, `aria-label="Enviar"`, `role="log"` ni `data-role` en las burbujas sin actualizar `frontend/e2e/chat-basic.spec.ts`: romperán los selectors.
- **No** vuelvas a montar el Setup Wizard en `/`. Debe vivir en `/setup` y seguir siendo accesible desde el link del header.
- Al añadir nuevos endpoints del chat (streaming, regenerate, etc.), extiende el hook `useChat`; no introduzcas un segundo cliente HTTP paralelo.
- Cuando la Feature 003 introduzca widgets, el panel derecho (`aria-label="Canvas de widgets"`) será el punto de inyección: conservar ese contenedor semántico.
