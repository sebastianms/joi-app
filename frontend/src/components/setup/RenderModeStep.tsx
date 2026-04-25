"use client";

import type { RenderMode } from "@/hooks/useRenderMode";
import { RenderModePreview } from "./RenderModePreview";

interface RenderModeStepProps {
  value: RenderMode;
  onChange: (mode: RenderMode) => void;
  isSaving?: boolean;
  error?: string | null;
}

const MODES: { id: RenderMode; label: string; description: string }[] = [
  {
    id: "shadcn",
    label: "shadcn/ui",
    description: "Componentes accesibles sobre Radix, estilo minimalista.",
  },
  {
    id: "bootstrap",
    label: "Bootstrap 5",
    description: "Grid responsive y clases utilitarias ampliamente conocidas.",
  },
  {
    id: "heroui",
    label: "HeroUI",
    description: "Componentes modernos con animaciones Framer Motion.",
  },
  {
    id: "design_system_disabled",
    label: "Sin framework",
    description: "HTML y CSS plano, sin dependencias de UI.",
  },
];

export function RenderModeStep({ value, onChange, isSaving, error }: RenderModeStepProps) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-semibold text-[color:var(--joi-text)]">
          Framework de widgets
        </h3>
        <p className="text-xs text-[color:var(--joi-muted)] mt-1">
          Elige la librería UI que Joi usará al generar visualizaciones.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {MODES.map(({ id, label, description }) => {
          const selected = value === id;
          return (
            <button
              key={id}
              data-role={`render-mode-option-${id}`}
              onClick={() => onChange(id)}
              disabled={isSaving}
              className={`text-left rounded-xl p-3 border transition-all
                ${selected
                  ? "border-[color:var(--joi-accent)] bg-[color:var(--joi-accent)]/5 shadow-[0_0_0_1px_var(--joi-accent)]"
                  : "border-[color:var(--joi-border)] bg-[color:var(--joi-surface-elevated)] hover:border-[color:var(--joi-accent)]/40"
                }
                disabled:opacity-50`}
            >
              <RenderModePreview mode={id} />
              <div className="mt-2">
                <div
                  className={`text-xs font-semibold ${selected ? "text-[color:var(--joi-accent)]" : "text-[color:var(--joi-text)]"}`}
                >
                  {label}
                </div>
                <div className="text-[10px] text-[color:var(--joi-muted)] mt-0.5 leading-snug">
                  {description}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {isSaving && (
        <p className="text-xs text-[color:var(--joi-muted)]">Guardando…</p>
      )}
      {error && (
        <p className="text-xs text-[color:var(--joi-accent-warm)]">{error}</p>
      )}
    </div>
  );
}
