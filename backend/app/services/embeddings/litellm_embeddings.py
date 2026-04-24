from __future__ import annotations

import functools
import hashlib
import math
import re
from typing import Any

import litellm
from langchain_core.embeddings import Embeddings

from app.core.config import settings

_MOCK_DIM = 1536  # match text-embedding-3-small


def _mock_embed(text: str) -> tuple[float, ...]:
    """Deterministic bag-of-words embedding for E2E / offline mode.

    Shared tokens produce highly similar cosine-space vectors — enough to
    exercise the cache hit threshold (0.85) with semantically close prompts.
    """
    vec = [0.0] * _MOCK_DIM
    tokens = re.findall(r"\w+", text.lower())
    for tok in tokens:
        bucket = int(hashlib.md5(tok.encode()).hexdigest(), 16) % _MOCK_DIM
        vec[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return tuple(vec)


class LiteLLMEmbeddings(Embeddings):
    """LangChain Embeddings adapter that routes through the LiteLLM gateway.

    Using LiteLLM keeps embedding calls under the same API-key management and
    provider abstraction as LLM completions (see ADL-006). When
    `MOCK_LLM_RESPONSES=true` is set, embeddings are produced deterministically
    in-process so E2E suites never hit the network.
    """

    def __init__(self, model: str | None = None) -> None:
        self._model = model or settings.EMBEDDING_MODEL

    @functools.lru_cache(maxsize=256)  # per-process in-memory cache
    def _embed_cached(self, text: str) -> tuple[float, ...]:
        if settings.MOCK_LLM_RESPONSES:
            return _mock_embed(text)
        response: Any = litellm.embedding(model=self._model, input=[text])
        return tuple(response.data[0].embedding)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(self._embed_cached(t)) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return list(self._embed_cached(text))
