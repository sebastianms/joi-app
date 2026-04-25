"use client";

import { useEffect, useState } from "react";

type LayoutMode = "dual" | "tabs";

const DUAL_PANEL_QUERY = "(min-width: 768px)";

export function useLayoutMode(): LayoutMode {
  const [mode, setMode] = useState<LayoutMode>("dual");

  useEffect(() => {
    const mql = window.matchMedia(DUAL_PANEL_QUERY);
    setMode(mql.matches ? "dual" : "tabs");

    const handler = (e: MediaQueryListEvent) => setMode(e.matches ? "dual" : "tabs");
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return mode;
}
