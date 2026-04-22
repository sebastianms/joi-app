"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import type { AgentTrace, DataExtraction } from "@/types/extraction";

export type ChatRole = "user" | "assistant";
export type IntentType = "simple" | "complex";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  intentType?: IntentType;
  extraction?: DataExtraction;
  trace?: AgentTrace;
}

interface ChatResponsePayload {
  response: string;
  intent_type: IntentType;
  extraction?: DataExtraction;
  trace?: AgentTrace;
}

interface UseChatResult {
  messages: ChatMessage[];
  isSending: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  sessionId: string;
}

const DEFAULT_API_URL = "http://127.0.0.1:8000/api";

function generateId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function useChat(): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId] = useState<string>(() => {
    if (typeof window !== "undefined") {
      const existing = localStorage.getItem("joi_session_id");
      if (existing) return existing;
      const id = generateId();
      localStorage.setItem("joi_session_id", id);
      return id;
    }
    return generateId();
  });
  const sessionIdRef = useRef<string>(sessionId);

  const apiUrl = useMemo(
    () => process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL,
    []
  );

  const sendMessage = useCallback(
    async (content: string): Promise<void> => {
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
