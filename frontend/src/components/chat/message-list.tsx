"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import type { ChatMessage, WidgetSummary } from "@/hooks/use-chat";
import { AgentTraceBlock } from "./agent-trace-block";

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

const ROUTE_RE = /(\/\w+)/g;
const IS_ROUTE = /^\/\w+$/;

function renderWithLinks(text: string) {
  const parts = text.split(ROUTE_RE);
  return parts.map((part, i) =>
    IS_ROUTE.test(part) ? (
      <Link key={i} href={part} className="underline hover:opacity-80">
        {part}
      </Link>
    ) : (
      part
    )
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
        {isUser ? message.content : renderWithLinks(message.content)}
        {!isUser && message.trace && (
          <AgentTraceBlock
            trace={message.trace}
            extraction={message.extraction}
          />
        )}
        {!isUser && message.recoveredWidget && (
          <RecoveredWidgetCard widget={message.recoveredWidget} />
        )}
        {!isUser && message.candidates && message.candidates.length > 0 && (
          <CandidateList candidates={message.candidates} />
        )}
      </div>
    </div>
  );
}

function RecoveredWidgetCard({ widget }: { widget: WidgetSummary }) {
  return (
    <div className="mt-2 flex items-center gap-2 rounded border border-border bg-background px-3 py-2 text-xs">
      <span className="flex-1 truncate font-medium">{widget.display_name}</span>
      <Link
        href={`/?recovered_widget=${widget.id}`}
        className="text-primary underline hover:opacity-80 shrink-0"
      >
        Abrir
      </Link>
    </div>
  );
}

function CandidateList({ candidates }: { candidates: WidgetSummary[] }) {
  return (
    <div className="mt-2 flex flex-col gap-1">
      {candidates.map((w) => (
        <div
          key={w.id}
          className="flex items-center gap-2 rounded border border-border bg-background px-3 py-1.5 text-xs"
        >
          <span className="flex-1 truncate">{w.display_name}</span>
          <Link
            href={`/?recovered_widget=${w.id}`}
            className="text-primary underline hover:opacity-80 shrink-0"
          >
            Abrir
          </Link>
        </div>
      ))}
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
