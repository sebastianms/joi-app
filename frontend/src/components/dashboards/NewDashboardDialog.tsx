"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface NewDashboardDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (name: string) => Promise<boolean>;
}

export function NewDashboardDialog({ open, onClose, onCreate }: NewDashboardDialogProps) {
  const [name, setName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setName("");
      setError(null);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    setError(null);
    const ok = await onCreate(name.trim());
    setIsSubmitting(false);
    if (ok) {
      onClose();
    } else {
      setError("Ya existe un dashboard con ese nombre.");
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-dashboard-title"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      data-role="new-dashboard-dialog"
    >
      <div className="bg-background rounded-lg shadow-lg w-full max-w-sm p-6">
        <h2 id="new-dashboard-title" className="text-base font-semibold mb-4">
          Nuevo dashboard
        </h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <Input
            ref={inputRef}
            placeholder="Nombre del dashboard"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={120}
          />
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting || !name.trim()}>
              Crear
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
