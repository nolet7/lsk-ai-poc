"""
FILE PURPOSE: Shared Embedding and Vector Store Access

This file owns the expensive, shared resources used by both ingestion and
retrieval:

1. The sentence-transformers embedding model, loaded lazily and cached.
2. The persistent ChromaDB client, cached per storage path.
3. The enterprise knowledge collection, with an explicit error when it is
   missing rather than silently creating an empty index.

Keeping these in one place means the model is loaded once per process, and
unit tests can replace `embed()` without importing torch.

Application flow:

ingest.py  -> store.embed() + store.get_collection(create=True)
retriever.py -> store.embed() + store.get_collection(create=False)
"""

# Import lru_cache so each heavyweight resource is created once per process.
from functools import lru_cache

# Import ChromaDB for persistent local vector storage.
import chromadb

# Import the NotFoundError raised when the collection has not been created yet.
from chromadb.errors import NotFoundError

# Import the project settings.
from config import settings


class IndexNotReadyError(RuntimeError):
    """Raised when the vector index is missing or empty and cannot serve queries."""


@lru_cache(maxsize=1)
def get_embedder():
    """Load the sentence-transformers model once and reuse it for every call."""

    # Import here so importing this module does not pull in torch.
    from sentence_transformers import SentenceTransformer

    # Load the configured embedding model.
    return SentenceTransformer(settings.embedding_model)


def embed(texts: list[str]) -> list[list[float]]:
    """
    Convert texts into dense vectors.

    Args:
        texts:
            One or more strings to encode.

    Returns:
        One embedding vector per input string, as plain Python lists.
    """

    # Encode in batches and return native Python lists for ChromaDB.
    return get_embedder().encode(
        texts,
        batch_size=settings.embedding_batch_size,
        show_progress_bar=False,
    ).tolist()


@lru_cache(maxsize=4)
def _client(path: str):
    """Create one persistent ChromaDB client per storage path."""

    # Open or create the persistent database at the given path.
    return chromadb.PersistentClient(path=path)


def get_client():
    """Return the persistent ChromaDB client for the configured path."""

    # Resolve the configured path as a string for the cache key.
    return _client(str(settings.chroma_dir))


def get_collection(create: bool):
    """
    Return the enterprise knowledge collection.

    Args:
        create:
            When True, create the collection if it does not exist. When False,
            raise IndexNotReadyError if it is missing.

    Returns:
        The ChromaDB collection holding the enterprise knowledge chunks.
    """

    # Read the shared client for the configured storage path.
    client = get_client()

    # Create the collection during ingestion, recording which model built it.
    if create:
        return client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"embedding_model": settings.embedding_model},
        )

    # Otherwise require an existing collection so queries never run against nothing.
    try:
        return client.get_collection(name=settings.collection_name)
    except NotFoundError as exc:
        raise IndexNotReadyError(
            "Knowledge index does not exist. Run `python -m rag.ingest` first."
        ) from exc


def reset_collection() -> None:
    """Delete the enterprise knowledge collection so it can be rebuilt."""

    # Remove the collection if it exists; ignore the case where it does not.
    try:
        get_client().delete_collection(name=settings.collection_name)
    except NotFoundError:
        pass
