"use client";

import Link from "next/link";
import { joiStorage } from "@/lib/storage/joi-storage";
import { useEffect, useState } from "react";

interface AppHeaderProps {
  onOpenOnboarding?: () => void;
}

export function AppHeader({ onOpenOnboarding }: AppHeaderProps) {
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
        <Link
          href="/"
          className="px-3 py-1.5 text-[13px] font-medium text-[color:var(--joi-muted)]
            rounded hover:text-[color:var(--joi-text)] hover:bg-white/5 transition-colors"
        >
          Chat
        </Link>
        <Link
          href="/dashboards"
          className="px-3 py-1.5 text-[13px] font-medium text-[color:var(--joi-muted)]
            rounded hover:text-[color:var(--joi-text)] hover:bg-white/5 transition-colors"
        >
          Dashboards
        </Link>
        <Link
          href="/collections"
          className="px-3 py-1.5 text-[13px] font-medium text-[color:var(--joi-muted)]
            rounded hover:text-[color:var(--joi-text)] hover:bg-white/5 transition-colors"
        >
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
          className="px-3 py-1.5 text-[13px] font-medium text-[color:var(--joi-muted)]
            rounded border border-[color:var(--joi-border)]
            hover:border-[color:var(--joi-accent)] hover:text-[color:var(--joi-accent)]
            transition-colors"
        >
          Configurar
        </Link>
      </nav>
    </header>
  );
}
