// generated from specs/004-widget-generation/contracts/postmessage-protocol.schema.json

import type { WidgetSpec } from "./widget";

// App → iframe
export interface WidgetInitMessage {
  type: "widget:init";
  protocol_version: "v1";
  widget_spec: WidgetSpec;
  data: {
    columns: Array<{ name: string; type: string }>;
    rows: Array<Record<string, unknown>>;
  };
}

// iframe → App
export interface WidgetReadyMessage {
  type: "widget:ready";
  widget_id: string;
  render_ms: number;
}

export interface WidgetErrorMessage {
  type: "widget:error";
  widget_id: string;
  code: string;
  message: string;
}

export interface WidgetResizeMessage {
  type: "widget:resize";
  widget_id: string;
  height: number;
}

export type IframeToAppMessage =
  | WidgetReadyMessage
  | WidgetErrorMessage
  | WidgetResizeMessage;

export type AppToIframeMessage = WidgetInitMessage;
