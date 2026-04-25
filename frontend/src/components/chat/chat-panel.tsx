"use client";

import { AlertCircle } from "lucide-react";
import type { UseChatResult } from "@/hooks/use-chat";
import { MessageInput } from "./message-input";
import { MessageList } from "./message-list";

interface ChatPanelProps {
  chat: UseChatResult;
}

export function ChatPanel({ chat }: ChatPanelProps) {
  const { messages, isSending, error, sendMessage, sessionId } = chat;

  return (
    <section
      className="flex h-full flex-col overflow-hidden
        bg-[color:var(--joi-surface)]/60 backdrop-blur-md"
      aria-label="Panel de chat"
    >
      <header
        className="border-b border-[color:var(--joi-border)] px-4 py-3 flex items-center gap-2 flex-shrink-0"
      >
        <div
          className="w-1.5 h-1.5 rounded-full bg-[color:var(--joi-success)]"
          aria-hidden="true"
        />
        <h2
          className="text-[11px] font-semibold tracking-[0.1em] uppercase
            text-[color:var(--joi-muted)]"
        >
          JOI · AGENTE
        </h2>
        <span className="ml-auto text-[11px] text-[color:var(--joi-muted)]">listo</span>
      </header>

      <MessageList
        messages={messages}
        isTyping={isSending}
        sessionId={sessionId}
        onSendMessage={sendMessage}
      />

      {error && (
        <div
          className="mx-3 mb-2 flex items-start gap-2 rounded-md
            border border-[color:var(--joi-accent-warm)]/30
            bg-[color:var(--joi-accent-warm)]/10 px-3 py-2 text-xs
            text-[color:var(--joi-accent-warm)]"
        >
          <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <MessageInput
        onSend={(content) => { void sendMessage(content); }}
        disabled={isSending}
      />
    </section>
  );
}
