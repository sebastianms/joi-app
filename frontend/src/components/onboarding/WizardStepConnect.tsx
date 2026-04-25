import Link from "next/link";

interface WizardStepConnectProps {
  onNext: () => void;
  onSkip: () => void;
}

export function WizardStepConnect({ onNext, onSkip }: WizardStepConnectProps) {
  return (
    <>
      <div className="text-3xl mb-4" aria-hidden="true">⚡</div>
      <h2 className="text-xl font-bold tracking-tight mb-3 text-[color:var(--joi-text)]">
        Conecta tus datos
      </h2>
      <p className="text-sm text-[color:var(--joi-muted)] leading-relaxed mb-8">
        Joi necesita una fuente de datos para trabajar — una base de datos SQL o un archivo JSON.
        Configura tu primera fuente y estarás listo.
      </p>
      <div className="flex justify-between items-center">
        <button
          onClick={onSkip}
          className="text-xs text-[color:var(--joi-muted)] hover:text-[color:var(--joi-text)] transition-colors px-2 py-1"
        >
          Omitir
        </button>
        <div className="flex items-center gap-2">
          <Link
            href="/setup"
            className="text-xs text-[color:var(--joi-muted)] hover:text-[color:var(--joi-accent)] transition-colors px-2 py-1"
          >
            Ir a configurar
          </Link>
          <button
            onClick={onNext}
            className="px-4 py-2 rounded text-sm font-semibold
              bg-[color:var(--joi-accent)] text-black
              hover:opacity-90 transition-opacity"
          >
            Siguiente →
          </button>
        </div>
      </div>
    </>
  );
}
