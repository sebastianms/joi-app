"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { joiStorage } from "@/lib/storage/joi-storage";
import { useEffect, useState } from "react";

interface AppHeaderProps {
  onOpenOnboarding?: () => void;
}

const NAV_LINK_BASE = "px-3 py-1.5 text-[13px] font-medium rounded transition-colors";
const NAV_LINK_ACTIVE = "text-[color:var(--joi-accent)] bg-[color:var(--joi-accent)]/10";
const NAV_LINK_IDLE = "text-[color:var(--joi-muted)] hover:text-[color:var(--joi-text)] hover:bg-white/5";

function navClass(active: boolean) {
  return `${NAV_LINK_BASE} ${active ? NAV_LINK_ACTIVE : NAV_LINK_IDLE}`;
}

export function AppHeader({ onOpenOnboarding }: AppHeaderProps) {
  const pathname = usePathname();
  const [shortSession, setShortSession] = useState<string | null>(null);

  useEffect(() => {
    const sid = joiStorage.sessionId.get();
    if (sid) setShortSession(sid.slice(0, 4));
  }, []);

  return (
    <header
      className="flex items-center justify-between px-5 h-[52px] flex-shrink-0
        bg-[color:var(--joi-surface)]/60 backdrop-blur-md
        border-b border-[color:var(--joi-border)]"
    >
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2.5 group">
        <div
          className="w-7 h-7 rounded-md flex items-center justify-center
            bg-[color:var(--joi-accent)] text-black text-[13px] font-bold leading-none
            group-hover:opacity-80 transition-opacity"
        >
          J
        </div>
        <span className="text-[15px] font-semibold tracking-[0.12em] text-[color:var(--joi-text)] group-hover:text-[color:var(--joi-accent)] transition-colors">
          JOI<span className="text-[color:var(--joi-accent)]">.</span>APP
        </span>
      </Link>

      {/* Nav */}
      <nav className="flex items-center gap-2">
        {shortSession && (
          <span
            className="text-[11px] text-[color:var(--joi-muted)] px-2 py-0.5
              border border-[color:var(--joi-border)] rounded"
          >
            sesión · {shortSession}
          </span>
        )}
        <Link href="/" className={navClass(pathname === "/")}>
          Chat
        </Link>
        <Link href="/dashboards" className={navClass(pathname.startsWith("/dashboards"))}>
          Dashboards
        </Link>
        <Link href="/collections" className={navClass(pathname.startsWith("/collections"))}>
          Colecciones
        </Link>
        <button
          onClick={onOpenOnboarding}
          className="px-3 py-1.5 text-[13px] font-medium text-[color:var(--joi-muted)]
            rounded border border-[color:var(--joi-border)]
            hover:border-[color:var(--joi-accent)] hover:text-[color:var(--joi-accent)]
            transition-colors"
        >
          ¿Cómo funciona?
        </button>
        <Link
          href="/setup"
          className={`${navClass(pathname.startsWith("/setup"))} border border-[color:var(--joi-border)] ${pathname.startsWith("/setup") ? "border-[color:var(--joi-accent)]" : "hover:border-[color:var(--joi-accent)]"}`}
        >
          Configurar
        </Link>
      </nav>
    </header>
  );
}
