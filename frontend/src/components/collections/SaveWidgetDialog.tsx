"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Collection } from "@/hooks/use-collections";

interface SaveWidgetDialogProps {
  open: boolean;
  collections: Collection[];
  onClose: () => void;
  onSave: (displayName: string, collectionIds: string[]) => Promise<void>;
  onCreateCollection: (name: string) => Promise<Collection | null>;
}

export function SaveWidgetDialog({
  open,
  collections,
  onClose,
  onSave,
  onCreateCollection,
}: SaveWidgetDialogProps) {
  const [displayName, setDisplayName] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [newCollectionName, setNewCollectionName] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setDisplayName("");
      setSelectedIds(new Set());
      setNewCollectionName("");
      setError(null);
      setTimeout(() => firstInputRef.current?.focus(), 50);
    }
  }, [open]);

  if (!open) return null;

  function toggleCollection(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function handleCreateCollection() {
    const name = newCollectionName.trim();
    if (!name) return;
    const created = await onCreateCollection(name);
    if (created) {
      setNewCollectionName("");
      setSelectedIds((prev) => new Set([...prev, created.id]));
    }
  }

  async function handleSave() {
    if (!displayName.trim()) {
      setError("El nombre es obligatorio");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await onSave(displayName.trim(), Array.from(selectedIds));
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar el widget");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-label="Guardar widget"
      data-role="save-widget-dialog"
    >
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-semibold text-foreground">Guardar widget</h2>

        <div className="mb-4 flex flex-col gap-1">
          <Label htmlFor="display-name">Nombre del widget</Label>
          <Input
            id="display-name"
            ref={firstInputRef}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="ej. Ventas por región Q1"
            maxLength={120}
          />
        </div>

        <div className="mb-4 flex flex-col gap-2">
          <Label>Colecciones</Label>
          {collections.length === 0 ? (
            <p className="text-sm text-muted-foreground">No hay colecciones. Crea una abajo.</p>
          ) : (
            <ul className="max-h-40 overflow-y-auto rounded-md border border-input p-2" data-role="collection-checkbox-list">
              {collections.map((c) => (
                <li key={c.id} className="flex items-center gap-2 py-1" data-collection-name={c.name}>
                  <input
                    type="checkbox"
                    id={`col-${c.id}`}
                    checked={selectedIds.has(c.id)}
                    onChange={() => toggleCollection(c.id)}
                    className="h-4 w-4 accent-primary"
                  />
                  <label htmlFor={`col-${c.id}`} className="cursor-pointer text-sm text-foreground">
                    {c.name}
                  </label>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="mb-4 flex gap-2">
          <Input
            value={newCollectionName}
            onChange={(e) => setNewCollectionName(e.target.value)}
            placeholder="Nueva colección…"
            maxLength={120}
            onKeyDown={(e) => e.key === "Enter" && handleCreateCollection()}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleCreateCollection}
            disabled={!newCollectionName.trim()}
          >
            Crear
          </Button>
        </div>

        {error && <p className="mb-3 text-sm text-destructive">{error}</p>}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isSaving}>
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            disabled={isSaving || !displayName.trim()}
          >
            {isSaving ? "Guardando…" : "Guardar"}
          </Button>
        </div>
      </div>
    </div>
  );
}
