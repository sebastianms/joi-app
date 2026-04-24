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
    <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs dark:border-amber-800 dark:bg-amber-950">
      <div className="mb-2 flex items-center gap-1.5 text-amber-700 dark:text-amber-300">
        <Sparkles className="h-3.5 w-3.5 shrink-0" />
        <span className="font-medium">
          Widget similar encontrado ({scorePercent}% coincidencia)
        </span>
      </div>

      <p className="mb-1 text-muted-foreground">
        Tipo: <span className="font-medium">{suggestion.widget_type}</span>
      </p>
      <p className="mb-3 truncate text-muted-foreground italic">
        &ldquo;{suggestion.prompt_text}&rdquo;
      </p>

      {reuseError && (
        <p className="mb-2 text-red-600 dark:text-red-400">{reuseError}</p>
      )}

      <div className="flex gap-2">
        <button
          className="flex-1 rounded bg-amber-600 px-2 py-1.5 font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          disabled={isReusing}
          onClick={() => void reuseCache(suggestion.cache_entry_id, sessionId)}
          data-role="cache-reuse-button"
        >
          {isReusing ? "Aplicando…" : "Usar este widget"}
        </button>
        <button
          className="flex items-center gap-1 rounded border border-border px-2 py-1.5 font-medium text-foreground transition-colors hover:bg-muted disabled:opacity-50"
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
