import type { ReactNode } from "react";
import Link from "next/link";

interface SetupShellProps {
  children: ReactNode;
}

export function SetupShell({ children }: SetupShellProps) {
  return (
    <div
      className="flex flex-col min-h-screen"
      style={{ background: "var(--joi-bg)", color: "var(--joi-text)" }}
    >
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-4
          border-b border-[color:var(--joi-border)]
          bg-[color:var(--joi-surface)]/60 backdrop-blur-md"
      >
        <div className="flex items-center gap-3">
          <div
            className="w-7 h-7 rounded flex items-center justify-center text-black text-sm font-bold"
            style={{ background: "var(--joi-accent)" }}
          >
            J
          </div>
          <span className="text-sm font-semibold tracking-wide text-[color:var(--joi-text)]">
            JOI.APP
          </span>
          <span className="text-xs text-[color:var(--joi-muted)] ml-1">/ Configuración</span>
        </div>
        <Link
          href="/"
          className="text-xs text-[color:var(--joi-muted)] hover:text-[color:var(--joi-text)] transition-colors"
        >
          ← Volver al chat
        </Link>
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center py-12 px-6">
        <div className="w-full max-w-2xl">
          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight text-[color:var(--joi-text)]">
              Configura tu fuente de datos
            </h1>
            <p className="text-sm text-[color:var(--joi-muted)] mt-2 leading-relaxed">
              Joi necesita acceso a tus datos para generar visualizaciones. Conecta una base de datos
              SQL, sube un archivo JSON o configura el vector store.
            </p>
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
