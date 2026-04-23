// generated from specs/004-widget-generation/contracts/api-spec.json (render-mode profile)

export type RenderMode = "ui_framework" | "free_code" | "design_system";

export type UILibrary = "shadcn" | "bootstrap" | "heroui";

export interface RenderModeProfile {
  session_id: string;
  mode: RenderMode;
  ui_library?: UILibrary;
}

export interface RenderModeUpdateRequest {
  mode: "ui_framework" | "free_code";
  ui_library?: UILibrary;
}
