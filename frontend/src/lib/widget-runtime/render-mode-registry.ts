// Maps render-mode names to their UI adapter.
// entry.tsx reads this registry to set the active adapter before bootstrapping.

import { ShadcnAdapter, type Adapter } from "./adapters/shadcn";
import { BootstrapAdapter } from "./adapters/bootstrap";
import { HeroUIAdapter } from "./adapters/heroui";

export type { Adapter };

export type RenderModeName = "shadcn" | "bootstrap" | "heroui" | "design_system_disabled";

const REGISTRY: Record<RenderModeName, Adapter> = {
  shadcn: ShadcnAdapter,
  bootstrap: BootstrapAdapter,
  heroui: HeroUIAdapter,
  design_system_disabled: ShadcnAdapter, // plain HTML — falls back to shadcn primitives
};

let _active: Adapter = ShadcnAdapter;

export function setActiveAdapter(mode: RenderModeName): void {
  _active = REGISTRY[mode] ?? ShadcnAdapter;
}

export function getActiveAdapter(): Adapter {
  return _active;
}
