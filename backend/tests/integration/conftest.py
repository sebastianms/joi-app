"""Integration-test-scoped fixtures.

Isolates the chat pipeline from any real vector store running on localhost:
- `CacheService.search` → returns [] (cache miss every call)
- `CacheService.index` → no-op

Without this, a running Qdrant (e.g. from dev-e2e.sh) can return cache hits
for tests that expect the generation path, turning `widget_spec` into None.
"""

from __future__ import annotations

import pytest

from app.services.widget_cache.cache_service import CacheService


@pytest.fixture(autouse=True)
def _disable_widget_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _empty_search(*_args, **_kwargs):
        return []

    async def _noop_index(*_args, **_kwargs):
        return None

    async def _noop_invalidate(*_args, **_kwargs):
        return None

    monkeypatch.setattr(CacheService, "search", _empty_search)
    monkeypatch.setattr(CacheService, "index", _noop_index)
    monkeypatch.setattr(CacheService, "invalidate_by_connection", _noop_invalidate)
