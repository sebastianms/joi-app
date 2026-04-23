// Widget runtime entry point.
// Runs inside the sandboxed iframe. Receives widget:init from the host app,
// dispatches to the registered renderer for spec.widget_type, and emits
// widget:ready / widget:error / widget:resize back to the host.

import { createRoot, type Root } from "react-dom/client";
import type { WidgetSpec } from "@/types/widget";
import { findMissingBindings } from "./bindings-validator";
import {
  isWidgetInitMessage,
  makeErrorMessage,
  makeReadyMessage,
  makeResizeMessage,
} from "./protocol";
import { getRenderer } from "./registry";

// Register built-in renderers by side-effect import. Each file calls
// registerRenderer() at module load.
import "./renderers";

interface RuntimeState {
  initialized: boolean;
  root: Root | null;
  extractionId: string | null;
  lastHeight: number;
}

const RESIZE_MIN_DELTA_PX = 4;

function createState(): RuntimeState {
  return { initialized: false, root: null, extractionId: null, lastHeight: 0 };
}

function postToHost(message: unknown): void {
  window.parent.postMessage(message, "*");
}

function observeResize(state: RuntimeState, container: HTMLElement): void {
  const observer = new ResizeObserver(() => {
    const height = Math.ceil(container.getBoundingClientRect().height);
    if (!state.extractionId) return;
    if (Math.abs(height - state.lastHeight) < RESIZE_MIN_DELTA_PX) return;
    state.lastHeight = height;
    postToHost(makeResizeMessage(state.extractionId, height));
  });
  observer.observe(container);
}

function renderWidget(
  state: RuntimeState,
  container: HTMLElement,
  spec: WidgetSpec,
  rows: Array<Record<string, unknown>>,
): void {
  const Renderer = getRenderer(spec.widget_type);
  if (!Renderer) {
    postToHost(
      makeErrorMessage(
        spec.extraction_id,
        "SPEC_INVALID",
        `No renderer registered for widget_type=${spec.widget_type}`,
      ),
    );
    return;
  }

  const missing = findMissingBindings(spec);
  if (missing.length > 0) {
    postToHost(
      makeErrorMessage(
        spec.extraction_id,
        "SPEC_INVALID",
        `${spec.widget_type} requires bindings [${missing.join(", ")}].`,
      ),
    );
    return;
  }

  const startedAt = performance.now();
  if (!state.root) {
    state.root = createRoot(container);
    observeResize(state, container);
  }
  state.root.render(<Renderer spec={spec} rows={rows} />);

  // React commits are synchronous from our perspective; queueMicrotask lets
  // the DOM settle one frame before we announce readiness.
  queueMicrotask(() => {
    const bootstrapMs = Math.round(performance.now() - startedAt);
    postToHost(makeReadyMessage(spec.extraction_id, bootstrapMs));
  });
}

function handleInit(state: RuntimeState, data: unknown): void {
  if (!isWidgetInitMessage(data)) {
    return; // silently ignore non-conforming messages per protocol spec
  }

  const container = document.getElementById("root");
  if (!container) {
    postToHost(
      makeErrorMessage(
        data.widget_spec.extraction_id,
        "RUNTIME_ERROR",
        "iframe document missing #root container",
      ),
    );
    return;
  }

  try {
    state.extractionId = data.widget_spec.extraction_id;
    renderWidget(state, container, data.widget_spec, data.data_rows);
    state.initialized = true;
  } catch (err) {
    postToHost(
      makeErrorMessage(
        data.widget_spec.extraction_id,
        "RUNTIME_ERROR",
        err instanceof Error ? err.message : String(err),
      ),
    );
  }
}

export function bootstrap(): void {
  const state = createState();
  window.addEventListener("message", (event: MessageEvent) => {
    handleInit(state, event.data);
  });
  window.addEventListener("error", (event: ErrorEvent) => {
    if (!state.extractionId) return;
    postToHost(
      makeErrorMessage(state.extractionId, "RUNTIME_ERROR", event.message),
    );
  });
}

bootstrap();
