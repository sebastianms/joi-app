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
  // Tracks the last spec for which widget:init was actually sent, so we can
  // send it when the bundle loads after the spec has already arrived.
  const initSentForSpecRef = useRef<string | null>(null);

  const setStage = useCallback((stage: CanvasLoadingStage, error: CanvasError | null = null) => {
    setState((prev) => ({ ...prev, loading_stage: stage, last_error: error }));
  }, []);

  const clearTimer = useCallback(() => {
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const sendInit = useCallback(
    (spec: WidgetSpec) => {
      const iframeWindow = frameRef.current?.contentWindow;
      if (!iframeWindow) return;
      initSentForSpecRef.current = spec.widget_id;
      iframeWindow.postMessage(buildInitMessage(spec, dataRows), "*");
      clearTimer();
      timeoutRef.current = window.setTimeout(() => {
        setStage("error", {
          code: "RENDER_TIMEOUT",
          message: `El widget no respondió en ${BOOTSTRAP_TIMEOUT_MS / 1000}s.`,
        });
      }, BOOTSTRAP_TIMEOUT_MS);
    },
    [dataRows, clearTimer, setStage],
  );

  // Effect A: react to spec changes.
  // When spec changes we update canvas state and, if the bundle is already
  // loaded, send widget:init immediately. If the bundle isn't ready yet we
  // keep loading_stage="bootstrapping" and wait for Effect B to fire.
  // Bundle load errors (RENDER_ERROR with no bundleCode) are preserved so
  // the error panel remains visible even after a new spec arrives.
  useEffect(() => {
    const specId = widgetSpec?.widget_id ?? null;
    if (specId === lastSpecIdRef.current) return;
    lastSpecIdRef.current = specId;
    clearTimer();
    setState((prev) => {
      const bundleFailedPreviously =
        prev.last_error?.code === "RENDER_ERROR" && !bundleCode;
      return {
        ...prev,
        previous_widget_spec: prev.current_widget_spec,
        current_widget_spec: widgetSpec,
        // Keep error visible if the bundle never loaded; otherwise start bootstrapping.
        loading_stage: bundleFailedPreviously ? "error" : widgetSpec ? "bootstrapping" : "idle",
        last_error: bundleFailedPreviously ? prev.last_error : null,
      };
    });

    if (!widgetSpec || !bundleCode) return;
    sendInit(widgetSpec);
  }, [widgetSpec, bundleCode, sendInit, clearTimer]);

  // Effect B: react to bundle becoming available.
  // If the spec arrived before the bundle, init hasn't been sent yet.
  // Fire it now so the widget can bootstrap without requiring another spec change.
  useEffect(() => {
    if (!bundleCode || !widgetSpec) return;
    if (initSentForSpecRef.current === widgetSpec.widget_id) return;
    sendInit(widgetSpec);
  }, [bundleCode, widgetSpec, sendInit]);

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
