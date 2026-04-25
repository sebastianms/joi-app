"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import type { ChatMessage, UseChatResult, WidgetSummary } from "@/hooks/use-chat";
import { AgentTraceBlock } from "./agent-trace-block";
import { CacheReuseSuggestion } from "./CacheReuseSuggestion";

interface MessageListProps {
  messages: ChatMessage[];
  isTyping?: boolean;
  emptyLabel?: string;
  sessionId?: string;
  onSendMessage?: UseChatResult["sendMessage"];
}

const DEFAULT_EMPTY_LABEL = "Inicia la conversación enviando un mensaje abajo.";

export function MessageList({
  messages,
  isTyping = false,
  emptyLabel = DEFAULT_EMPTY_LABEL,
  sessionId,
  onSendMessage,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isTyping]);

  if (messages.length === 0 && !isTyping) {
    return (
      <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-[color:var(--joi-muted)]">
        {emptyLabel}
      </div>
    );
  }

  return (
    <div
      className="flex flex-1 flex-col gap-4 overflow-y-auto p-4
        [scrollbar-width:thin] [scrollbar-color:var(--joi-border)_transparent]"
      role="log"
      aria-live="polite"
    >
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          sessionId={sessionId}
          onSendMessage={onSendMessage}
        />
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

function MessageBubble({
  message,
  sessionId,
  onSendMessage,
}: {
  message: ChatMessage;
  sessionId?: string;
  onSendMessage?: UseChatResult["sendMessage"];
}) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[75%] whitespace-pre-wrap rounded-xl rounded-br-sm
            px-3.5 py-2.5 text-sm leading-relaxed
            bg-[color:var(--joi-accent)]/10 border border-[color:var(--joi-accent)]/20
            text-[color:var(--joi-text)]"
          data-role="user"
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2.5 items-start" data-role="assistant">
      {/* Avatar */}
      <div
        className="w-6 h-6 rounded-full flex-shrink-0 mt-0.5
          flex items-center justify-center
          bg-[color:var(--joi-accent)] text-black text-[10px] font-bold"
      >
        J
      </div>

      {/* Content — no bubble, text directo */}
      <div className="flex-1 min-w-0">
        <p className="text-sm leading-relaxed text-[color:var(--joi-text)] whitespace-pre-wrap">
          {renderWithLinks(message.content)}
        </p>

        {message.trace && (
          <AgentTraceBlock
            trace={message.trace}
            extraction={message.extraction}
          />
        )}
        {message.recoveredWidget && (
          <RecoveredWidgetCard widget={message.recoveredWidget} />
        )}
        {message.candidates && message.candidates.length > 0 && (
          <CandidateList candidates={message.candidates} />
        )}
        {message.cacheSuggestion && sessionId && onSendMessage && (
          <CacheReuseSuggestion
            suggestion={message.cacheSuggestion}
            sessionId={sessionId}
            originalPrompt={message.originalPrompt ?? ""}
            onGenerateNew={(prompt) =>
              void onSendMessage(prompt, { skipCache: true })
            }
          />
        )}
      </div>
    </div>
  );
}

function RecoveredWidgetCard({ widget }: { widget: WidgetSummary }) {
  return (
    <div
      className="mt-2 flex items-center gap-2 rounded-md
        border border-[color:var(--joi-border)]
        bg-[color:var(--joi-surface)] px-3 py-2 text-xs"
    >
      <span className="flex-1 truncate font-medium text-[color:var(--joi-text)]">
        {widget.display_name}
      </span>
      <Link
        href={`/?recovered_widget=${widget.id}`}
        className="text-[color:var(--joi-accent)] hover:opacity-80 shrink-0 transition-opacity"
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
          className="flex items-center gap-2 rounded-md
            border border-[color:var(--joi-border)]
            bg-[color:var(--joi-surface)] px-3 py-1.5 text-xs"
        >
          <span className="flex-1 truncate text-[color:var(--joi-text)]">{w.display_name}</span>
          <Link
            href={`/?recovered_widget=${w.id}`}
            className="text-[color:var(--joi-accent)] hover:opacity-80 shrink-0 transition-opacity"
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
      className="flex items-center gap-1.5 py-1"
      aria-label="Asistente procesando"
      role="status"
    >
      {[0, 200, 400].map((delay) => (
        <span
          key={delay}
          className="block w-1.5 h-1.5 rounded-full bg-[color:var(--joi-accent)]"
          style={{ animation: `typing-bounce 1.4s ${delay}ms infinite` }}
        />
      ))}
    </div>
  );
}
