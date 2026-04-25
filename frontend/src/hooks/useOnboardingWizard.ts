"use client";

import { useCallback, useEffect, useState } from "react";
import { joiStorage } from "@/lib/storage/joi-storage";

interface OnboardingWizardControls {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  complete: () => void;
}

export function useOnboardingWizard(): OnboardingWizardControls {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Auto-open only on first visit (no session id yet) and not already completed.
    const isFirstVisit = joiStorage.sessionId.get() === null;
    const alreadyCompleted = joiStorage.onboarding.isCompleted();
    if (isFirstVisit && !alreadyCompleted) {
      setIsOpen(true);
    }
  }, []);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);

  const complete = useCallback(() => {
    joiStorage.onboarding.markCompleted();
    setIsOpen(false);
  }, []);

  return { isOpen, open, close, complete };
}
