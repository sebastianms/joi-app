"""LiteLLM gateway singleton.

Every LLM call in the Data Agent must flow through this module. Importing
`anthropic`, `openai`, or `google.generativeai` directly — or calling
`litellm.completion` outside this file — bypasses routing by purpose and the
centralized credential configuration (see ADL-006).
"""

from __future__ import annotations

import os
from threading import Lock
from typing import Any, Literal

import litellm

from app.core.config import settings

Purpose = Literal["sql", "json", "chat"]

ChatMessage = dict[str, str]


class LiteLLMConfigurationError(RuntimeError):
    """Raised when no provider credentials are configured."""


class LiteLLMClient:
    """Thin wrapper around `litellm.completion` with routing by purpose."""

    def __init__(
        self,
        *,
        model_sql: str,
        model_json: str,
        model_chat: str,
    ) -> None:
        self._models: dict[Purpose, str] = {
            "sql": model_sql,
            "json": model_json,
            "chat": model_chat,
        }

    def model_for(self, purpose: Purpose) -> str:
        return self._models[purpose]

    def chat_completion(
        self,
        messages: list[ChatMessage],
        *,
        purpose: Purpose,
        **kwargs: Any,
    ) -> str:
        model = self.model_for(purpose)
        response = litellm.completion(model=model, messages=messages, **kwargs)
        return response["choices"][0]["message"]["content"]

    async def acompletion(
        self,
        messages: list[ChatMessage],
        *,
        purpose: Purpose,
        **kwargs: Any,
    ) -> Any:
        model = self.model_for(purpose)
        return await litellm.acompletion(model=model, messages=messages, **kwargs)


_client: LiteLLMClient | None = None
_lock = Lock()


def _apply_provider_env() -> None:
    if settings.ANTHROPIC_API_KEY:
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY)
    if settings.OPENAI_API_KEY:
        os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    if settings.GEMINI_API_KEY:
        os.environ.setdefault("GEMINI_API_KEY", settings.GEMINI_API_KEY)


def _has_any_provider_configured() -> bool:
    return any(
        [
            settings.ANTHROPIC_API_KEY,
            settings.OPENAI_API_KEY,
            settings.GEMINI_API_KEY,
            os.environ.get("ANTHROPIC_API_KEY"),
            os.environ.get("OPENAI_API_KEY"),
            os.environ.get("GEMINI_API_KEY"),
        ]
    )


def get_client() -> LiteLLMClient:
    global _client
    if _client is not None:
        return _client
    with _lock:
        if _client is not None:
            return _client
        if not _has_any_provider_configured():
            raise LiteLLMConfigurationError(
                "No LLM provider credentials configured. Set ANTHROPIC_API_KEY, "
                "OPENAI_API_KEY, or GEMINI_API_KEY in the environment."
            )
        _apply_provider_env()
        _client = LiteLLMClient(
            model_sql=settings.LLM_MODEL_SQL,
            model_json=settings.LLM_MODEL_JSON,
            model_chat=settings.LLM_MODEL_CHAT,
        )
        return _client


def chat_completion(
    messages: list[ChatMessage],
    *,
    purpose: Purpose,
    **kwargs: Any,
) -> str:
    return get_client().chat_completion(messages, purpose=purpose, **kwargs)


async def acompletion(
    messages: list[ChatMessage],
    *,
    purpose: Purpose,
    **kwargs: Any,
) -> Any:
    return await get_client().acompletion(messages, purpose=purpose, **kwargs)


def reset_client_for_tests() -> None:
    global _client
    with _lock:
        _client = None
