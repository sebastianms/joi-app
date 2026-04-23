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
