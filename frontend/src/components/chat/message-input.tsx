"use client";

import { useState, type FormEvent, type KeyboardEvent } from "react";
import { SendHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

const DEFAULT_PLACEHOLDER = "Escribe un mensaje...";

export function MessageInput({
  onSend,
  disabled = false,
  placeholder = DEFAULT_PLACEHOLDER,
}: MessageInputProps) {
  const [draft, setDraft] = useState("");

  function submit() {
    const trimmed = draft.trim();
    if (trimmed.length === 0 || disabled) {
      return;
    }
    onSend(trimmed);
    setDraft("");
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 border-t border-border bg-background p-3"
      aria-label="Enviar mensaje"
    >
      <Input
        name="message"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        aria-label="Mensaje"
      />
      <Button
        type="submit"
        size="icon"
        disabled={disabled || draft.trim().length === 0}
        aria-label="Enviar"
      >
        <SendHorizontal />
      </Button>
    </form>
  );
}
