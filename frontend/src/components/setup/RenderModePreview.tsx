import type { RenderMode } from "@/hooks/useRenderMode";

interface RenderModePreviewProps {
  mode: RenderMode;
}

const PREVIEW_CONTENT: Record<RenderMode, { badge: string; bars: string[]; btn: string }> = {
  shadcn: {
    badge: "bg-zinc-800 text-zinc-300",
    bars: ["bg-blue-500", "bg-blue-400", "bg-blue-600"],
    btn: "bg-zinc-800 text-zinc-200 border border-zinc-700",
  },
  bootstrap: {
    badge: "bg-[#0d6efd] text-white",
    bars: ["bg-[#0d6efd]", "bg-[#6ea8fe]", "bg-[#0a58ca]"],
    btn: "bg-[#0d6efd] text-white",
  },
  heroui: {
    badge: "bg-violet-600 text-white",
    bars: ["bg-violet-500", "bg-violet-400", "bg-violet-700"],
    btn: "bg-violet-600 text-white",
  },
  design_system_disabled: {
    badge: "bg-[color:var(--joi-border)] text-[color:var(--joi-muted)]",
    bars: ["bg-[color:var(--joi-muted)]/40", "bg-[color:var(--joi-muted)]/30", "bg-[color:var(--joi-muted)]/50"],
    btn: "bg-[color:var(--joi-surface-elevated)] text-[color:var(--joi-muted)] border border-[color:var(--joi-border)]",
  },
};

export function RenderModePreview({ mode }: RenderModePreviewProps) {
  const p = PREVIEW_CONTENT[mode];
  return (
    <div
      aria-hidden="true"
      className="rounded bg-black/30 p-2 flex flex-col gap-1.5"
    >
      <div className={`text-[9px] font-mono px-1.5 py-0.5 rounded self-start ${p.badge}`}>
        {mode === "design_system_disabled" ? "plain" : mode}
      </div>
      <div className="flex items-end gap-0.5 h-6">
        {p.bars.map((cls, i) => (
          <div
            key={i}
            className={`flex-1 rounded-sm ${cls}`}
            style={{ height: `${(i + 1) * 33}%` }}
          />
        ))}
        <div className={`flex-1 rounded-sm ${p.bars[1]}`} style={{ height: "55%" }} />
      </div>
      <div className={`text-[9px] px-1.5 py-0.5 rounded self-start ${p.btn}`}>Button</div>
    </div>
  );
}
