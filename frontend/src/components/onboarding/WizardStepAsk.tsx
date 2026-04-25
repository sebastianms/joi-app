interface WizardStepAskProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export function WizardStepAsk({ onNext, onBack, onSkip }: WizardStepAskProps) {
  return (
    <>
      <div className="text-3xl mb-4" aria-hidden="true">💬</div>
      <h2 className="text-xl font-bold tracking-tight mb-3 text-[color:var(--joi-text)]">
        Pregunta por tus datos
      </h2>
      <p className="text-sm text-[color:var(--joi-muted)] leading-relaxed mb-4">
        Escribe en lenguaje natural lo que quieres ver. Joi entiende preguntas como:
      </p>
      <div
        className="rounded-lg border border-[color:var(--joi-border)]
          bg-black/20 px-4 py-3 font-mono text-sm mb-8
          text-[color:var(--joi-accent)]"
      >
        &ldquo;ventas por mes en 2025&rdquo;
      </div>
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <button
            onClick={onBack}
            className="text-xs text-[color:var(--joi-muted)] hover:text-[color:var(--joi-text)] transition-colors px-2 py-1"
          >
            ← Atrás
          </button>
          <button
            onClick={onSkip}
            className="text-xs text-[color:var(--joi-muted)] hover:text-[color:var(--joi-text)] transition-colors px-2 py-1"
          >
            Omitir
          </button>
        </div>
        <button
          onClick={onNext}
          className="px-4 py-2 rounded text-sm font-semibold
            bg-[color:var(--joi-accent)] text-black
            hover:opacity-90 transition-opacity"
        >
          Entendido →
        </button>
      </div>
    </>
  );
}
