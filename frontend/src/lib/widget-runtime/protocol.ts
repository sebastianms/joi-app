// Runtime-side validators for postMessage protocol v1.
// Kept intentionally small so the bundle stays under the 300KB budget (T132).

import {
  PROTOCOL_VERSION,
  type WidgetInitMessage,
  type WidgetErrorMessage,
  type WidgetMessageErrorCode,
  type WidgetReadyMessage,
  type WidgetResizeMessage,
} from "@/types/postmessage";

export function isWidgetInitMessage(raw: unknown): raw is WidgetInitMessage {
  if (!raw || typeof raw !== "object") return false;
  const msg = raw as Record<string, unknown>;
  return (
    msg.type === "widget:init" &&
    msg.protocol_version === PROTOCOL_VERSION &&
    typeof msg.widget_spec === "object" &&
    msg.widget_spec !== null &&
    Array.isArray(msg.data_rows)
  );
}

const ERROR_CODES: ReadonlySet<WidgetMessageErrorCode> = new Set([
  "SPEC_INVALID",
  "RUNTIME_ERROR",
  "DATA_MISMATCH",
  "UNKNOWN",
]);

export function isWidgetReadyMessage(raw: unknown): raw is WidgetReadyMessage {
  if (!raw || typeof raw !== "object") return false;
  const msg = raw as Record<string, unknown>;
  return (
    msg.type === "widget:ready" &&
    msg.protocol_version === PROTOCOL_VERSION &&
    typeof msg.extraction_id === "string"
  );
}

export function isWidgetErrorMessage(raw: unknown): raw is WidgetErrorMessage {
  if (!raw || typeof raw !== "object") return false;
  const msg = raw as Record<string, unknown>;
  return (
    msg.type === "widget:error" &&
    msg.protocol_version === PROTOCOL_VERSION &&
    typeof msg.extraction_id === "string" &&
    typeof msg.code === "string" &&
    ERROR_CODES.has(msg.code as WidgetMessageErrorCode) &&
    typeof msg.message === "string"
  );
}

export function isWidgetResizeMessage(raw: unknown): raw is WidgetResizeMessage {
  if (!raw || typeof raw !== "object") return false;
  const msg = raw as Record<string, unknown>;
  return (
    msg.type === "widget:resize" &&
    msg.protocol_version === PROTOCOL_VERSION &&
    typeof msg.extraction_id === "string" &&
    typeof msg.height === "number" &&
    Number.isFinite(msg.height)
  );
}

export function makeReadyMessage(
  extractionId: string,
  bootstrapMs: number,
): WidgetReadyMessage {
  return {
    type: "widget:ready",
    protocol_version: PROTOCOL_VERSION,
    extraction_id: extractionId,
    bootstrap_ms: bootstrapMs,
  };
}

export function makeErrorMessage(
  extractionId: string,
  code: WidgetMessageErrorCode,
  message: string,
): WidgetErrorMessage {
  return {
    type: "widget:error",
    protocol_version: PROTOCOL_VERSION,
    extraction_id: extractionId,
    code,
    message,
  };
}

export function makeResizeMessage(
  extractionId: string,
  height: number,
): WidgetResizeMessage {
  return {
    type: "widget:resize",
    protocol_version: PROTOCOL_VERSION,
    extraction_id: extractionId,
    height,
  };
}
