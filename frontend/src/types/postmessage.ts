// generated from specs/004-widget-generation/contracts/postmessage-protocol.schema.json

import type { WidgetSpec } from "./widget";

export const PROTOCOL_VERSION = "v1" as const;

export interface WidgetThemeTokens {
  [token: string]: unknown;
}

// App → iframe
export interface WidgetInitMessage {
  type: "widget:init";
  protocol_version: typeof PROTOCOL_VERSION;
  widget_spec: WidgetSpec;
  data_rows: Array<Record<string, unknown>>;
  theme?: WidgetThemeTokens;
}

// iframe → App
export interface WidgetReadyMessage {
  type: "widget:ready";
  protocol_version: typeof PROTOCOL_VERSION;
  extraction_id: string;
  bootstrap_ms?: number;
}

export type WidgetMessageErrorCode =
  | "SPEC_INVALID"
  | "RUNTIME_ERROR"
  | "DATA_MISMATCH"
  | "UNKNOWN";

export interface WidgetErrorMessage {
  type: "widget:error";
  protocol_version: typeof PROTOCOL_VERSION;
  extraction_id: string;
  code: WidgetMessageErrorCode;
  message: string;
}

export interface WidgetResizeMessage {
  type: "widget:resize";
  protocol_version: typeof PROTOCOL_VERSION;
  extraction_id: string;
  height: number;
}

export type IframeToAppMessage =
  | WidgetReadyMessage
  | WidgetErrorMessage
  | WidgetResizeMessage;

export type AppToIframeMessage = WidgetInitMessage;
