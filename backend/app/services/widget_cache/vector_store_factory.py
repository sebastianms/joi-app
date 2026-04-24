from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.embeddings import Embeddings

from app.core.config import settings
from app.services.security.encryption import decrypt

if TYPE_CHECKING:
    from langchain_core.vectorstores import VectorStore
    from app.models.vector_store_config import VectorStoreConfigORM

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "widget_cache"


def validate_vector_store(provider: str, connection_params: dict) -> None:
    """Ping the vector store with a dummy similarity search.

    Raises RuntimeError with a human-readable message if the provider is
    unavailable or the required extra is not installed.
    """
    import json

    from app.models.vector_store_config import VectorStoreProvider
    from app.services.embeddings.litellm_embeddings import LiteLLMEmbeddings

    dummy_embeddings = LiteLLMEmbeddings()
    params_json = json.dumps(connection_params)

    try:
        vs = build_vector_store_from_params(provider, params_json, dummy_embeddings)
        vs.similarity_search("joi-validate-ping", k=1)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Connection test failed: {exc}") from exc


def build_vector_store_from_params(
    provider: str, params_json: str, embeddings: Embeddings
) -> "VectorStore":
    """Build a VectorStore directly from provider name + raw params JSON (no ORM)."""
    if provider == "qdrant":
        return _build_qdrant_byo(params_json, embeddings)
    if provider == "chroma":
        return _build_chroma(params_json, embeddings)
    if provider == "pinecone":
        return _build_pinecone(params_json, embeddings)
    if provider == "weaviate":
        return _build_weaviate(params_json, embeddings)
    if provider == "pgvector":
        return _build_pgvector(params_json, embeddings)
    raise RuntimeError(f"Unsupported vector store provider: {provider}")


def build_vector_store(
    config: "VectorStoreConfigORM | None",
    embeddings: Embeddings,
) -> "VectorStore":
    """Return a LangChain VectorStore for the active provider.

    If config is None or marks is_default, uses the internal Qdrant instance.
    BYO providers decrypt their connection params and import lazily so that
    optional extras (langchain-chroma, etc.) are not required unless used.
    """
    if config is None or config.is_default:
        return _build_qdrant_default(embeddings)

    provider = config.provider
    params_json = decrypt(config.connection_params_encrypted)

    if provider == "qdrant":
        return _build_qdrant_byo(params_json, embeddings)
    if provider == "chroma":
        return _build_chroma(params_json, embeddings)
    if provider == "pinecone":
        return _build_pinecone(params_json, embeddings)
    if provider == "weaviate":
        return _build_weaviate(params_json, embeddings)
    if provider == "pgvector":
        return _build_pgvector(params_json, embeddings)

    raise ValueError(f"Unsupported vector store provider: {provider}")


def _build_qdrant_default(embeddings: Embeddings) -> "VectorStore":
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient

    client = QdrantClient(url=settings.QDRANT_URL)
    return QdrantVectorStore(
        client=client,
        collection_name=_COLLECTION_NAME,
        embedding=embeddings,
    )


def _build_qdrant_byo(params_json: str, embeddings: Embeddings) -> "VectorStore":
    import json

    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient

    params = json.loads(params_json)
    client = QdrantClient(**params)
    return QdrantVectorStore(
        client=client,
        collection_name=_COLLECTION_NAME,
        embedding=embeddings,
    )


def _build_chroma(params_json: str, embeddings: Embeddings) -> "VectorStore":
    import json

    try:
        from langchain_chroma import Chroma
    except ImportError as exc:
        raise RuntimeError(
            "langchain-chroma is not installed. Run: pip install langchain-chroma"
        ) from exc

    params = json.loads(params_json)
    return Chroma(collection_name=_COLLECTION_NAME, embedding_function=embeddings, **params)


def _build_pinecone(params_json: str, embeddings: Embeddings) -> "VectorStore":
    import json

    try:
        from langchain_pinecone import PineconeVectorStore
    except ImportError as exc:
        raise RuntimeError(
            "langchain-pinecone is not installed. Run: pip install langchain-pinecone"
        ) from exc

    params = json.loads(params_json)
    index_name = params.pop("index_name", _COLLECTION_NAME)
    return PineconeVectorStore(index_name=index_name, embedding=embeddings, **params)


def _build_weaviate(params_json: str, embeddings: Embeddings) -> "VectorStore":
    import json

    try:
        import weaviate
        from langchain_weaviate import WeaviateVectorStore
    except ImportError as exc:
        raise RuntimeError(
            "langchain-weaviate is not installed. Run: pip install langchain-weaviate"
        ) from exc

    params = json.loads(params_json)
    client = weaviate.connect_to_custom(**params)
    return WeaviateVectorStore(
        client=client,
        index_name=_COLLECTION_NAME,
        text_key="prompt_text",
        embedding=embeddings,
    )


def _build_pgvector(params_json: str, embeddings: Embeddings) -> "VectorStore":
    import json

    try:
        from langchain_postgres import PGVector
    except ImportError as exc:
        raise RuntimeError(
            "langchain-postgres is not installed. Run: pip install langchain-postgres"
        ) from exc

    params = json.loads(params_json)
    connection = params.pop("connection_string")
    return PGVector(
        connection=connection,
        collection_name=_COLLECTION_NAME,
        embeddings=embeddings,
        **params,
    )
