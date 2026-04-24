from __future__ import annotations

import functools
from typing import Any

import litellm
from langchain_core.embeddings import Embeddings

from app.core.config import settings


class LiteLLMEmbeddings(Embeddings):
    """LangChain Embeddings adapter that routes through the LiteLLM gateway.

    Using LiteLLM keeps embedding calls under the same API-key management and
    provider abstraction as LLM completions (see ADL-006).
    """

    def __init__(self, model: str | None = None) -> None:
        self._model = model or settings.EMBEDDING_MODEL

    @functools.lru_cache(maxsize=256)  # per-process in-memory cache
    def _embed_cached(self, text: str) -> tuple[float, ...]:
        response: Any = litellm.embedding(model=self._model, input=[text])
        return tuple(response.data[0].embedding)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(self._embed_cached(t)) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return list(self._embed_cached(text))
