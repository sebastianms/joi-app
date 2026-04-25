"use client";

import { Sparkles, RefreshCw } from "lucide-react";
import type { CacheSuggestion } from "@/hooks/use-chat";
import { useWidgetCacheSuggestion } from "@/hooks/useWidgetCacheSuggestion";

interface CacheReuseSuggestionProps {
  suggestion: CacheSuggestion;
  sessionId: string;
  originalPrompt: string;
  onGenerateNew: (prompt: string) => void;
}

export function CacheReuseSuggestion({
  suggestion,
  sessionId,
  originalPrompt,
  onGenerateNew,
}: CacheReuseSuggestionProps) {
  const { isReusing, reuseError, reuseCache } = useWidgetCacheSuggestion();
  const scorePercent = Math.round(suggestion.score * 100);

  return (
    <div
      className="mt-2 rounded-lg border border-[color:var(--joi-accent)]/20
        bg-[color:var(--joi-accent)]/5 p-3 text-xs"
      data-role="cache-reuse-suggestion"
    >
      <div className="mb-2 flex items-center gap-1.5 text-[color:var(--joi-accent)]">
        <Sparkles className="h-3.5 w-3.5 shrink-0" />
        <span className="font-medium">
          Widget similar encontrado ({scorePercent}% coincidencia)
        </span>
      </div>

      <p className="mb-1 text-[color:var(--joi-muted)]">
        Tipo: <span className="font-medium text-[color:var(--joi-text)]">{suggestion.widget_type}</span>
      </p>
      <p className="mb-3 truncate text-[color:var(--joi-muted)] italic">
        &ldquo;{suggestion.prompt_text}&rdquo;
      </p>

      {reuseError && (
        <p className="mb-2 text-[color:var(--joi-accent-warm)]">{reuseError}</p>
      )}

      <div className="flex gap-2">
        <button
          className="flex-1 rounded px-2 py-1.5 font-semibold
            bg-[color:var(--joi-accent)] text-black
            hover:opacity-90 disabled:opacity-50 transition-opacity"
          disabled={isReusing}
          onClick={() => void reuseCache(suggestion.cache_entry_id, sessionId)}
          data-role="cache-reuse-button"
        >
          {isReusing ? "Aplicando…" : "Usar este widget"}
        </button>
        <button
          className="flex items-center gap-1 rounded border border-[color:var(--joi-border)]
            px-2 py-1.5 font-medium text-[color:var(--joi-muted)]
            hover:border-[color:var(--joi-accent)] hover:text-[color:var(--joi-accent)]
            disabled:opacity-50 transition-colors"
          disabled={isReusing}
          onClick={() => onGenerateNew(originalPrompt)}
          data-role="cache-skip-button"
        >
          <RefreshCw className="h-3 w-3" />
          Generar uno nuevo
        </button>
      </div>
    </div>
  );
}
