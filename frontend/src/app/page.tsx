"use client";

import Link from "next/link";
import { ChatPanel } from "@/components/chat/chat-panel";
import { CanvasPanel } from "@/components/canvas/canvas-panel";
import { useChat, type ChatMessage } from "@/hooks/use-chat";
import type { WidgetSpec } from "@/types/widget";

interface CanvasSource {
  widgetSpec: WidgetSpec | null;
  dataRows: Array<Record<string, unknown>>;
  extractionEmpty: boolean;
}

function pickCanvasSource(messages: ChatMessage[]): CanvasSource {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i];
    if (message.role !== "assistant") continue;
    if (message.widgetSpec) {
      return {
        widgetSpec: message.widgetSpec,
        dataRows: message.extraction?.rows ?? [],
        extractionEmpty: false,
      };
    }
    if (message.extraction) {
      return {
        widgetSpec: null,
        dataRows: message.extraction.rows,
        extractionEmpty:
          message.extraction.status === "success" &&
          message.extraction.row_count === 0,
      };
    }
  }
  return { widgetSpec: null, dataRows: [], extractionEmpty: false };
}

export default function Home() {
  const chat = useChat();
  const { widgetSpec, dataRows, extractionEmpty } = pickCanvasSource(chat.messages);

  return (
    <div className="flex min-h-screen flex-col bg-zinc-50 font-sans dark:bg-black">
      <header className="flex items-center justify-between border-b border-border bg-background px-6 py-3">
        <h1 className="text-lg font-semibold tracking-tight">Joi-App</h1>
        <Link
          href="/setup"
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          Configurar fuentes de datos
        </Link>
      </header>

      <main className="grid flex-1 grid-cols-1 gap-4 p-4 md:grid-cols-2">
        <div className="min-h-0">
          <ChatPanel chat={chat} />
        </div>
        <CanvasPanel
          sessionId={chat.sessionId}
          widgetSpec={widgetSpec}
          dataRows={dataRows}
          isGenerating={chat.isSending && !widgetSpec}
          extractionEmpty={extractionEmpty}
        />
      </main>
    </div>
  );
}
