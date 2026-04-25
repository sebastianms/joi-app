"use client";

import { useEffect, useRef } from "react";

interface LayoutTabsProps {
  active: "chat" | "canvas";
  onTabChange: (tab: "chat" | "canvas") => void;
  chatSlot: React.ReactNode;
  canvasSlot: React.ReactNode;
}

export function LayoutTabs({ active, onTabChange, chatSlot, canvasSlot }: LayoutTabsProps) {
  const tablistRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = tablistRef.current;
    if (!el) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") onTabChange("chat");
      if (e.key === "ArrowRight") onTabChange("canvas");
    };
    el.addEventListener("keydown", handler);
    return () => el.removeEventListener("keydown", handler);
  }, [onTabChange]);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Tab bar */}
      <div
        ref={tablistRef}
        role="tablist"
        className="flex border-b border-[color:var(--joi-border)] px-4 flex-shrink-0"
      >
        {(["chat", "canvas"] as const).map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={active === tab}
            data-role={`layout-tab-${tab}`}
            onClick={() => onTabChange(tab)}
            className={`px-4 py-2.5 text-[13px] font-medium border-b-2 -mb-px transition-colors capitalize
              ${active === tab
                ? "text-[color:var(--joi-accent)] border-[color:var(--joi-accent)]"
                : "text-[color:var(--joi-muted)] border-transparent hover:text-[color:var(--joi-text)]"
              }`}
          >
            {tab === "chat" ? "Chat" : "Canvas"}
          </button>
        ))}
      </div>

      {/* Panels — both mounted, inactive hidden to preserve state */}
      <div
        role="tabpanel"
        hidden={active !== "chat"}
        className="flex-1 min-h-0 flex flex-col"
        data-role="chat-panel"
      >
        {chatSlot}
      </div>
      <div
        role="tabpanel"
        hidden={active !== "canvas"}
        className="flex-1 min-h-0 flex flex-col"
        data-role="canvas-panel"
      >
        {canvasSlot}
      </div>
    </div>
  );
}
