"""Unit tests for vector_store_factory — T106."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import json
import pytest

from app.services.widget_cache.vector_store_factory import build_vector_store, build_vector_store_from_params


class _FakeEmbeddings:
    def embed_documents(self, texts):
        return [[0.1] * 3 for _ in texts]

    def embed_query(self, text):
        return [0.1] * 3


_EMBEDDINGS = _FakeEmbeddings()


def _make_config(provider: str, is_default: bool = False, params: dict | None = None):
    config = MagicMock()
    config.provider = provider
    config.is_default = is_default
    config.connection_params_encrypted = b"encrypted"
    return config, json.dumps(params or {})


def test_build_default_uses_qdrant_when_config_is_none():
    """None config triggers the default Qdrant path."""
    with patch("app.services.widget_cache.vector_store_factory._build_qdrant_default") as mock:
        mock.return_value = MagicMock()
        build_vector_store(None, _EMBEDDINGS)
        mock.assert_called_once_with(_EMBEDDINGS)


def test_build_default_uses_qdrant_when_is_default():
    """is_default=True on config also triggers the default Qdrant path."""
    config, _ = _make_config("qdrant", is_default=True)
    with patch("app.services.widget_cache.vector_store_factory._build_qdrant_default") as mock:
        mock.return_value = MagicMock()
        build_vector_store(config, _EMBEDDINGS)
        mock.assert_called_once_with(_EMBEDDINGS)


def test_build_qdrant_byo():
    """BYO Qdrant config routes to _build_qdrant_byo."""
    params_json = json.dumps({"url": "http://remote:6333"})
    with (
        patch("app.services.widget_cache.vector_store_factory.decrypt", return_value=params_json),
        patch("app.services.widget_cache.vector_store_factory._build_qdrant_byo") as mock,
    ):
        mock.return_value = MagicMock()
        config, _ = _make_config("qdrant")
        build_vector_store(config, _EMBEDDINGS)
        mock.assert_called_once_with(params_json, _EMBEDDINGS)


def test_build_chroma_raises_if_not_installed():
    """Chroma provider raises RuntimeError when langchain-chroma is missing."""
    with pytest.raises(RuntimeError, match="langchain-chroma"):
        with patch.dict("sys.modules", {"langchain_chroma": None}):
            build_vector_store_from_params("chroma", json.dumps({}), _EMBEDDINGS)


def test_build_pinecone_raises_if_not_installed():
    """Pinecone provider raises RuntimeError when langchain-pinecone is missing."""
    with pytest.raises(RuntimeError, match="langchain-pinecone"):
        with patch.dict("sys.modules", {"langchain_pinecone": None}):
            build_vector_store_from_params("pinecone", json.dumps({"api_key": "k"}), _EMBEDDINGS)


def test_unsupported_provider_raises():
    """Unknown provider raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Unsupported"):
        build_vector_store_from_params("unknown_db", json.dumps({}), _EMBEDDINGS)
