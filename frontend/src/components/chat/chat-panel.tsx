"use client";

import { AlertCircle } from "lucide-react";
import { useChat } from "@/hooks/use-chat";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { MessageInput } from "./message-input";
import { MessageList } from "./message-list";

interface ChatPanelProps {
  title?: string;
}

export function ChatPanel({ title = "Joi Chat" }: ChatPanelProps) {
  const { messages, isSending, error, sendMessage } = useChat();

  return (
    <section
      className="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm"
      aria-label="Panel de chat"
    >
      <header className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      </header>

      <MessageList messages={messages} isTyping={isSending} />

      {error && (
        <Alert variant="destructive" className="mx-3 mb-2">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <MessageInput
        onSend={(content) => {
          void sendMessage(content);
        }}
        disabled={isSending}
      />
    </section>
  );
}
