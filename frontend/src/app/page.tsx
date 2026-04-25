"use client";

import { useState } from "react";
import { ChatPanel } from "@/components/chat/chat-panel";
import { CanvasPanel } from "@/components/canvas/canvas-panel";
import { AppHeader } from "@/components/layout/AppHeader";
import { PanelSeparator } from "@/components/layout/PanelSeparator";
import { LayoutTabs } from "@/components/layout/LayoutTabs";
import { useLayoutMode } from "@/hooks/useLayoutMode";
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
  const layoutMode = useLayoutMode();
  const [activeTab, setActiveTab] = useState<"chat" | "canvas">("chat");
  const { widgetSpec, dataRows, extractionEmpty } = pickCanvasSource(chat.messages);

  const chatSlot = <ChatPanel chat={chat} />;
  const canvasSlot = (
    <CanvasPanel
      sessionId={chat.sessionId}
      widgetSpec={widgetSpec}
      dataRows={dataRows}
      isGenerating={chat.isSending && !widgetSpec}
      extractionEmpty={extractionEmpty}
    />
  );

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />

      {layoutMode === "dual" ? (
        <main className="flex flex-1 min-h-0 overflow-hidden">
          <div className="flex flex-col flex-1 min-h-0" data-role="chat-panel">
            {chatSlot}
          </div>
          <PanelSeparator />
          <div className="flex flex-col flex-1 min-h-0" data-role="canvas-panel">
            {canvasSlot}
          </div>
        </main>
      ) : (
        <main className="flex flex-1 min-h-0 overflow-hidden">
          <LayoutTabs
            active={activeTab}
            onTabChange={setActiveTab}
            chatSlot={chatSlot}
            canvasSlot={canvasSlot}
          />
        </main>
      )}
    </div>
  );
}
