"use client";

import { useEffect, useState } from "react";
import { WizardStepConnect } from "./WizardStepConnect";
import { WizardStepAsk } from "./WizardStepAsk";
import { WizardStepGenerate } from "./WizardStepGenerate";

interface OnboardingWizardProps {
  open: boolean;
  onClose: () => void;
  onComplete: () => void;
}

type Step = 0 | 1 | 2;

export function OnboardingWizard({ open, onClose, onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState<Step>(0);

  // Reset step when wizard reopens
  useEffect(() => {
    if (open) setStep(0);
  }, [open]);

  // ESC to close
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const next = () => setStep((s) => Math.min(s + 1, 2) as Step);
  const back = () => setStep((s) => Math.max(s - 1, 0) as Step);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center
        bg-black/70 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-title"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="w-full max-w-md mx-4 rounded-2xl p-8
          bg-[color:var(--joi-surface-elevated)]/90 backdrop-blur-xl
          border border-[color:var(--joi-border)]"
      >
        {/* Step dots */}
        <div className="flex gap-1.5 mb-8" aria-hidden="true">
          {([0, 1, 2] as Step[]).map((s) => (
            <div
              key={s}
              className={`w-1.5 h-1.5 rounded-full transition-all duration-200 ${
                s === step
                  ? "bg-[color:var(--joi-accent)] shadow-[0_0_0_3px_var(--joi-glow)]"
                  : s < step
                  ? "bg-[color:var(--joi-success)]"
                  : "bg-[color:var(--joi-border)]"
              }`}
            />
          ))}
        </div>

        {/* Hidden title for screen readers */}
        <span id="onboarding-title" className="sr-only">
          Bienvenido a Joi · paso {step + 1} de 3
        </span>

        {step === 0 && <WizardStepConnect onNext={next} onSkip={onComplete} />}
        {step === 1 && <WizardStepAsk onNext={next} onBack={back} onSkip={onComplete} />}
        {step === 2 && <WizardStepGenerate onComplete={onComplete} onBack={back} />}
      </div>
    </div>
  );
}
