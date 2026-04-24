"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import type { AgentTrace, DataExtraction } from "@/types/extraction";
import type { WidgetSpec } from "@/types/widget";
import { getSessionId } from "@/lib/session";

export type ChatRole = "user" | "assistant";
export type IntentType = "simple" | "complex";

export interface WidgetSummary {
  id: string;
  display_name: string;
}

export interface CacheSuggestion {
  cache_entry_id: string;
  score: number;
  widget_type: string;
  prompt_text: string;
  widget_spec?: WidgetSpec;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  intentType?: IntentType;
  extraction?: DataExtraction;
  trace?: AgentTrace;
  widgetSpec?: WidgetSpec;
  recoveredWidget?: WidgetSummary;
  candidates?: WidgetSummary[];
  cacheSuggestion?: CacheSuggestion;
  originalPrompt?: string;
}

interface ChatResponsePayload {
  response: string;
  intent_type: IntentType;
  extraction?: DataExtraction;
  trace?: AgentTrace;
  widget_spec?: WidgetSpec;
  recovered_widget?: WidgetSummary;
  candidates?: WidgetSummary[];
  cache_suggestion?: CacheSuggestion;
}

export interface UseChatResult {
  messages: ChatMessage[];
  isSending: boolean;
  error: string | null;
  sendMessage: (content: string, options?: { skipCache?: boolean }) => Promise<void>;
  sessionId: string;
}

const DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

const generateId = () => crypto.randomUUID();

export function useChat(): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId] = useState<string>(getSessionId);
  const sessionIdRef = useRef<string>(sessionId);

  const apiUrl = useMemo(
    () => process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL,
    []
  );

  const sendMessage = useCallback(
    async (content: string, options?: { skipCache?: boolean }): Promise<void> => {
      const trimmed = content.trim();
      if (trimmed.length === 0 || isSending) {
        return;
      }

      const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        content: trimmed,
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsSending(true);
      setError(null);

      try {
        const response = await fetch(`${apiUrl}/chat/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionIdRef.current,
            message: trimmed,
            skip_cache: options?.skipCache ?? false,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || "Failed to send message");
        }

        const data: ChatResponsePayload = await response.json();
        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: "assistant",
          content: data.response,
          intentType: data.intent_type,
          extraction: data.extraction,
          trace: data.trace,
          widgetSpec: data.widget_spec,
          recoveredWidget: data.recovered_widget,
          candidates: data.candidates,
          cacheSuggestion: data.cache_suggestion,
          originalPrompt: data.cache_suggestion ? trimmed : undefined,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
      } finally {
        setIsSending(false);
      }
    },
    [apiUrl, isSending]
  );

  return { messages, isSending, error, sendMessage, sessionId };
}
