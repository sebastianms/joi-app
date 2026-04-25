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
    // Show on every visit until the user explicitly completes the wizard.
    // Note: useChat creates the session ID synchronously before this effect runs,
    // so checking sessionId === null would always be false.
    if (!joiStorage.onboarding.isCompleted()) {
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
