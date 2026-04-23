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
      className="flex flex-col items-center justify-center gap-2 p-6 text-center"
    >
      <p className="text-sm font-medium text-destructive">
        No se pudo renderizar el widget
      </p>
      <p className="max-w-xs text-xs text-muted-foreground">{error.message}</p>
    </div>
  );
}
