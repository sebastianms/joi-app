// Canvas orchestration hook (T133, FR-008/FR-008a/FR-008b).
//
// Responsibility: mantener CanvasState, cargar el bundle del runtime una
// sola vez, enviar widget:init al iframe tras su load, escuchar los
// mensajes ready/error/resize y aplicar el timeout de 4s de bootstrap.
//
// El hook NO fetchea la spec: la recibe como prop (viene del backend via
// useChat). El "generating" del enum pertenece al consumidor (canvas-panel)
// y se infiere de isSending del chat; aquí cubrimos desde "bootstrapping".

"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type {
  CanvasError,
  CanvasLoadingStage,
  CanvasState,
  WidgetSpec,
} from "@/types/widget";
import {
  PROTOCOL_VERSION,
  type WidgetInitMessage,
} from "@/types/postmessage";
import {
  isWidgetErrorMessage,
  isWidgetReadyMessage,
  isWidgetResizeMessage,
} from "@/lib/widget-runtime/protocol";
import type { WidgetFrameHandle } from "@/components/canvas/widget-frame";

const BUNDLE_URL = "/widget-runtime.bundle.js";
const BOOTSTRAP_TIMEOUT_MS = 4000;
const DEFAULT_FRAME_HEIGHT = 320;
const MAX_FRAME_HEIGHT = 2000;

interface UseCanvasInput {
  sessionId: string;
  widgetSpec: WidgetSpec | null;
  dataRows: Array<Record<string, unknown>>;
}

interface UseCanvasResult {
  state: CanvasState;
  bundleCode: string | null;
  frameHeight: number;
  frameRef: React.RefObject<WidgetFrameHandle | null>;
  handleFrameLoad: () => void;
}

let bundlePromise: Promise<string> | null = null;

function loadBundle(): Promise<string> {
  if (!bundlePromise) {
    bundlePromise = fetch(BUNDLE_URL).then((res) => {
      if (!res.ok) {
        throw new Error(`Bundle HTTP ${res.status}`);
      }
      return res.text();
    });
  }
  return bundlePromise;
}

function initialState(sessionId: string): CanvasState {
  return {
    session_id: sessionId,
    current_widget_spec: null,
    loading_stage: "idle",
    last_error: null,
    previous_widget_spec: null,
  };
}

function buildInitMessage(
  spec: WidgetSpec,
  dataRows: Array<Record<string, unknown>>,
): WidgetInitMessage {
  return {
    type: "widget:init",
    protocol_version: PROTOCOL_VERSION,
    widget_spec: spec,
    data_rows: dataRows,
  };
}

export function useCanvas(input: UseCanvasInput): UseCanvasResult {
  const { sessionId, widgetSpec, dataRows } = input;

  const [state, setState] = useState<CanvasState>(() => initialState(sessionId));
  const [bundleCode, setBundleCode] = useState<string | null>(null);
  const [frameHeight, setFrameHeight] = useState<number>(DEFAULT_FRAME_HEIGHT);
  const frameRef = useRef<WidgetFrameHandle | null>(null);
  const timeoutRef = useRef<number | null>(null);
  const lastSpecIdRef = useRef<string | null>(null);

  const setStage = useCallback((stage: CanvasLoadingStage, error: CanvasError | null = null) => {
    setState((prev) => ({ ...prev, loading_stage: stage, last_error: error }));
  }, []);

  const clearTimer = useCallback(() => {
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    const specId = widgetSpec?.widget_id ?? null;
    if (specId === lastSpecIdRef.current) return;
    lastSpecIdRef.current = specId;
    clearTimer();
    setState((prev) => ({
      ...prev,
      previous_widget_spec: prev.current_widget_spec,
      current_widget_spec: widgetSpec,
      loading_stage: widgetSpec ? "bootstrapping" : "idle",
      last_error: null,
    }));

    if (!widgetSpec) return;
    // Post widget:init whenever the spec changes. The iframe doesn't reload
    // between specs (srcdoc is stable) so we cannot rely on onLoad alone.
    const iframeWindow = frameRef.current?.contentWindow;
    if (!iframeWindow) return;
    iframeWindow.postMessage(buildInitMessage(widgetSpec, dataRows), "*");
    timeoutRef.current = window.setTimeout(() => {
      setStage("error", {
        code: "RENDER_TIMEOUT",
        message: `El widget no respondió en ${BOOTSTRAP_TIMEOUT_MS / 1000}s.`,
      });
    }, BOOTSTRAP_TIMEOUT_MS);
  }, [widgetSpec, dataRows, clearTimer, setStage]);

  useEffect(() => {
    loadBundle()
      .then(setBundleCode)
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "unknown";
        setStage("error", { code: "RENDER_ERROR", message: `No se pudo cargar el runtime: ${message}` });
      });
  }, [setStage]);

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      // With sandbox="allow-scripts" (no allow-same-origin) the browser assigns
      // an opaque origin, so source-identity checks are unreliable. Message shape
      // validation via the protocol guards is sufficient — non-conforming messages
      // are silently ignored by the validators.
      const data = event.data;
      if (isWidgetReadyMessage(data)) {
        clearTimer();
        setStage("ready");
        return;
      }
      if (isWidgetErrorMessage(data)) {
        clearTimer();
        setStage("error", { code: "RENDER_ERROR", message: data.message });
        return;
      }
      if (isWidgetResizeMessage(data)) {
        setFrameHeight(Math.min(data.height, MAX_FRAME_HEIGHT));
        return;
      }
    }
    window.addEventListener("message", onMessage);
    return () => {
      window.removeEventListener("message", onMessage);
    };
  }, [clearTimer, setStage]);

  useEffect(() => () => clearTimer(), [clearTimer]);

  const handleFrameLoad = useCallback(() => {
    const spec = widgetSpec;
    const iframeWindow = frameRef.current?.contentWindow;
    if (!spec || !iframeWindow) return;
    iframeWindow.postMessage(buildInitMessage(spec, dataRows), "*");

    clearTimer();
    timeoutRef.current = window.setTimeout(() => {
      setStage("error", {
        code: "RENDER_TIMEOUT",
        message: `El widget no respondió en ${BOOTSTRAP_TIMEOUT_MS / 1000}s.`,
      });
    }, BOOTSTRAP_TIMEOUT_MS);
  }, [widgetSpec, dataRows, clearTimer, setStage]);

  return useMemo(
    () => ({ state, bundleCode, frameHeight, frameRef, handleFrameLoad }),
    [state, bundleCode, frameHeight, handleFrameLoad],
  );
}
