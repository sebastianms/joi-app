type RenderMode = "shadcn" | "bootstrap" | "heroui" | "design_system_disabled";

function safeGet(key: string): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(key);
}

function safeSet(key: string, value: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, value);
}

function safeRemove(key: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(key);
}

export const joiStorage = {
  sessionId: {
    get: (): string | null => safeGet("joi_session_id"),
    set: (id: string): void => safeSet("joi_session_id", id),
    clear: (): void => safeRemove("joi_session_id"),
  },

  onboarding: {
    isCompleted: (): boolean => safeGet("joi_onboarding_completed") === "true",
    markCompleted: (): void => safeSet("joi_onboarding_completed", "true"),
    reset: (): void => safeRemove("joi_onboarding_completed"),
  },

  renderMode: {
    get: (): RenderMode | null => safeGet("joi_render_mode") as RenderMode | null,
    set: (mode: RenderMode): void => safeSet("joi_render_mode", mode),
    clear: (): void => safeRemove("joi_render_mode"),
  },
} as const;
