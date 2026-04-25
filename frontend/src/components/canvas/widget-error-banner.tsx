"use client";

import type { CanvasError } from "@/types/widget";

interface WidgetErrorBannerProps {
  error: CanvasError;
}

export function WidgetErrorBanner({ error }: WidgetErrorBannerProps) {
  return (
    <div
      role="alert"
      data-role="widget-error"
      className="flex flex-col items-center justify-center gap-4 p-8 text-center"
    >
      <div
        className="flex h-12 w-12 items-center justify-center rounded-full
          bg-[color:var(--joi-accent-warm)]/10
          border border-[color:var(--joi-accent-warm)]/30
          text-xl"
        aria-hidden="true"
      >
        ⚠
      </div>
      <div className="space-y-1.5">
        <p className="text-sm font-semibold text-[color:var(--joi-text)]">
          No se pudo renderizar el widget
        </p>
        <p className="max-w-xs text-xs text-[color:var(--joi-muted)] leading-relaxed">
          {error.message}
        </p>
      </div>
    </div>
  );
}
