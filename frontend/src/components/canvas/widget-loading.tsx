import type { CanvasLoadingStage } from "@/types/widget";

interface WidgetLoadingProps {
  stage: Extract<CanvasLoadingStage, "generating" | "bootstrapping">;
}

export function WidgetLoading({ stage }: WidgetLoadingProps) {
  if (stage === "generating") {
    return (
      <div
        className="flex h-full flex-col items-center justify-center gap-6 p-8"
        role="status"
        aria-live="polite"
        aria-label="Construyendo widget"
        data-role="widget-loading"
        data-stage={stage}
      >
        <div className="flex flex-col gap-1.5 w-64">
          {[1, 0.7, 0.85, 0.5, 0.9, 0.4].map((w, i) => (
            <div
              key={i}
              className="h-0.5 rounded-full bg-[color:var(--joi-accent)] origin-left"
              style={{
                width: `${w * 100}%`,
                animation: `construct-lines 2s ${i * 150}ms ease-in-out infinite`,
              }}
            />
          ))}
        </div>
        <div className="flex items-center gap-2 text-[13px] text-[color:var(--joi-muted)] tracking-wide">
          <span
            className="w-1.5 h-1.5 rounded-full bg-[color:var(--joi-accent)]"
            style={{ animation: "pulse-accent 1.5s infinite" }}
          />
          Construyendo widget
        </div>
      </div>
    );
  }

  return (
    <div
      className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-3
        bg-[color:var(--joi-bg)]/80 backdrop-blur-sm rounded-lg"
      role="status"
      aria-live="polite"
      aria-label="Renderizando widget"
      data-role="widget-loading"
      data-stage={stage}
    >
      <div className="flex gap-1">
        {[0, 200, 400].map((d) => (
          <span
            key={d}
            className="w-1.5 h-1.5 rounded-full bg-[color:var(--joi-accent)]"
            style={{ animation: `typing-bounce 1.4s ${d}ms infinite` }}
          />
        ))}
      </div>
      <p className="text-xs text-[color:var(--joi-muted)] tracking-wider">Renderizando…</p>
    </div>
  );
}
