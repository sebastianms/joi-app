"use client";

import { useCallback, useEffect, useState } from "react";
import { joiStorage } from "@/lib/storage/joi-storage";

interface OnboardingWizardControls {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  complete: () => void;
}

// Captured at module-load time — before any component (including useChat)
// has a chance to create a new session ID in localStorage.
// "true" means the user already had a session before this page load.
const _hadSessionOnLoad =
  typeof window !== "undefined" && !!window.localStorage.getItem("joi_session_id");

export function useOnboardingWizard(): OnboardingWizardControls {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Show wizard only on genuine first visits (no prior session) and
    // only while the user hasn't completed it yet.
    const isFirstVisit = !_hadSessionOnLoad;
    if (isFirstVisit && !joiStorage.onboarding.isCompleted()) {
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
