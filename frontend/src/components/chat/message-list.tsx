"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/hooks/use-chat";

interface MessageListProps {
  messages: ChatMessage[];
  isTyping?: boolean;
  emptyLabel?: string;
}

const DEFAULT_EMPTY_LABEL =
  "Inicia la conversación enviando un mensaje abajo.";

export function MessageList({
  messages,
  isTyping = false,
  emptyLabel = DEFAULT_EMPTY_LABEL,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isTyping]);

  if (messages.length === 0 && !isTyping) {
    return (
      <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
        {emptyLabel}
      </div>
    );
  }

  return (
    <div
      className="flex flex-1 flex-col gap-3 overflow-y-auto p-4"
      role="log"
      aria-live="polite"
    >
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {isTyping && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[80%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm shadow-sm",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground"
        )}
        data-role={message.role}
      >
        {message.content}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div
      className="flex justify-start"
      aria-label="Asistente escribiendo"
      role="status"
    >
      <div className="flex gap-1 rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground shadow-sm">
        <span className="h-2 w-2 animate-bounce rounded-full bg-current [animation-delay:-0.3s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-current [animation-delay:-0.15s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-current" />
      </div>
    </div>
  );
}
