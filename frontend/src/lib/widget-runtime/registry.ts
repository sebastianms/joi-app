// Renderer registry — each WidgetType gets a React component registered here.
// Renderers are added in T121–T128; entry.tsx reads this registry to dispatch.

import type { ComponentType } from "react";
import type { WidgetSpec, WidgetType } from "@/types/widget";

export interface RendererProps {
  spec: WidgetSpec;
  rows: Array<Record<string, unknown>>;
}

export type WidgetRenderer = ComponentType<RendererProps>;

const registry = new Map<WidgetType, WidgetRenderer>();

export function registerRenderer(type: WidgetType, renderer: WidgetRenderer): void {
  registry.set(type, renderer);
}

export function getRenderer(type: WidgetType): WidgetRenderer | undefined {
  return registry.get(type);
}

export function listRegisteredTypes(): WidgetType[] {
  return Array.from(registry.keys());
}
