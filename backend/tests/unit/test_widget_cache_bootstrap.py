"""Unit tests for widget cache bootstrap."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.widget_cache.bootstrap import ensure_widget_cache_collection


async def test_bootstrap_creates_collection_when_missing():
    fake_client = MagicMock()
    fake_client.get_collections.return_value = MagicMock(collections=[])

    with patch("qdrant_client.QdrantClient", return_value=fake_client):
        await ensure_widget_cache_collection()

    fake_client.create_collection.assert_called_once()


async def test_bootstrap_skips_when_collection_exists():
    fake_collection = MagicMock()
    fake_collection.name = "widget_cache"

    fake_client = MagicMock()
    fake_client.get_collections.return_value = MagicMock(collections=[fake_collection])

    with patch("qdrant_client.QdrantClient", return_value=fake_client):
        await ensure_widget_cache_collection()

    fake_client.create_collection.assert_not_called()


async def test_bootstrap_swallows_qdrant_unavailable():
    """If Qdrant is unreachable, bootstrap logs and returns without raising."""
    with patch("qdrant_client.QdrantClient", side_effect=RuntimeError("unreachable")):
        # Must not raise
        await ensure_widget_cache_collection()
