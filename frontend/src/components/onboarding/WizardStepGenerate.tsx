interface WizardStepGenerateProps {
  onComplete: () => void;
  onBack: () => void;
}

export function WizardStepGenerate({ onComplete, onBack }: WizardStepGenerateProps) {
  return (
    <>
      <div className="text-3xl mb-4" aria-hidden="true">✦</div>
      <h2 className="text-xl font-bold tracking-tight mb-3 text-[color:var(--joi-text)]">
        Joi genera tu visualización
      </h2>
      <p className="text-sm text-[color:var(--joi-muted)] leading-relaxed mb-4">
        En segundos tendrás un gráfico interactivo listo para explorar, guardar o añadir a un dashboard.
      </p>

      {/* Static widget preview */}
      <div
        className="rounded-lg border border-[color:var(--joi-border)]
          bg-[color:var(--joi-bg)] p-4 mb-8"
        aria-hidden="true"
      >
        <div className="text-xs text-[color:var(--joi-muted)] mb-3 uppercase tracking-wider">
          Ventas por mes — preview
        </div>
        <div className="flex items-end gap-1.5 h-16">
          {[62, 48, 71, 55, 80, 67, 91, 78, 59, 85, 72, 74].map((v, i) => (
            <div
              key={i}
              className="flex-1 rounded-sm"
              style={{
                height: `${(v / 91) * 100}%`,
                background: `linear-gradient(to top, rgba(0,212,255,0.25), rgba(0,212,255,0.85))`,
              }}
            />
          ))}
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-[color:var(--joi-muted)]">Ene</span>
          <span className="text-[10px] text-[color:var(--joi-accent)]">Jul ▲</span>
          <span className="text-[10px] text-[color:var(--joi-muted)]">Dic</span>
        </div>
      </div>

      <div className="flex justify-between items-center">
        <button
          onClick={onBack}
          className="text-xs text-[color:var(--joi-muted)] hover:text-[color:var(--joi-text)] transition-colors px-2 py-1"
        >
          ← Atrás
        </button>
        <button
          onClick={onComplete}
          className="px-4 py-2 rounded text-sm font-semibold
            bg-[color:var(--joi-accent)] text-black
            hover:opacity-90 transition-opacity"
        >
          Empezar
        </button>
      </div>
    </>
  );
}
