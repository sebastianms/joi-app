"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Collection } from "@/hooks/use-collections";

interface CollectionListProps {
  collections: Collection[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onRename: (id: string, name: string) => Promise<boolean>;
  onDelete: (id: string) => Promise<boolean>;
  onCreate: (name: string) => Promise<boolean>;
}

export function CollectionList({
  collections,
  selectedId,
  onSelect,
  onRename,
  onDelete,
  onCreate,
}: CollectionListProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function startEdit(collection: Collection) {
    setEditingId(collection.id);
    setEditName(collection.name);
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  async function submitRename(id: string) {
    if (!editName.trim()) return;
    setIsSubmitting(true);
    const ok = await onRename(id, editName.trim());
    setIsSubmitting(false);
    if (ok) setEditingId(null);
  }

  async function submitCreate() {
    if (!newName.trim()) return;
    setIsSubmitting(true);
    const ok = await onCreate(newName.trim());
    setIsSubmitting(false);
    if (ok) {
      setNewName("");
      setShowCreate(false);
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-foreground">Colecciones</h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowCreate(true)}
          aria-label="Nueva colección"
        >
          +
        </Button>
      </div>

      {showCreate && (
        <form
          className="flex gap-1 mb-2"
          onSubmit={(e) => {
            e.preventDefault();
            submitCreate();
          }}
        >
          <Input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Nombre de colección"
            className="h-7 text-xs"
          />
          <Button type="submit" size="sm" disabled={isSubmitting || !newName.trim()}>
            Crear
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setShowCreate(false);
              setNewName("");
            }}
          >
            ✕
          </Button>
        </form>
      )}

      {collections.length === 0 && !showCreate && (
        <p className="text-xs text-muted-foreground py-2">No hay colecciones.</p>
      )}

      {collections.map((col) => (
        <div
          key={col.id}
          data-role="collection-item"
          data-collection-name={col.name}
          className={`group flex items-center gap-1 rounded px-2 py-1 cursor-pointer text-sm ${
            selectedId === col.id
              ? "bg-accent text-accent-foreground"
              : "hover:bg-accent/50"
          }`}
          onClick={() => editingId !== col.id && onSelect(col.id)}
        >
          {editingId === col.id ? (
            <form
              className="flex flex-1 gap-1"
              onSubmit={(e) => {
                e.preventDefault();
                submitRename(col.id);
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <Input
                ref={inputRef}
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="h-6 text-xs flex-1"
              />
              <Button type="submit" size="sm" className="h-6 px-2 text-xs" disabled={isSubmitting}>
                ✓
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setEditingId(null)}
              >
                ✕
              </Button>
            </form>
          ) : (
            <>
              <span className="flex-1 truncate">{col.name}</span>
              <button
                className="hidden group-hover:inline text-muted-foreground hover:text-foreground text-xs px-1"
                onClick={(e) => {
                  e.stopPropagation();
                  startEdit(col);
                }}
                aria-label={`Renombrar ${col.name}`}
              >
                ✎
              </button>
              <button
                className="hidden group-hover:inline text-muted-foreground hover:text-destructive text-xs px-1"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(col.id);
                }}
                aria-label={`Eliminar ${col.name}`}
              >
                ✕
              </button>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
