"""
FILE PURPOSE: Enterprise Document Ingestion for RAG

This file prepares enterprise text documents for semantic search. It runs as
an explicit job (`python -m rag.ingest`), not inside the API process.

It performs the following tasks:

1. Finds `.txt` files under the configured documents directory.
2. Fingerprints each file so unchanged documents are skipped.
3. Splits changed documents into word-based chunks.
4. Creates embeddings in batches with the shared embedding model.
5. Replaces the chunks of changed documents and removes deleted documents.
6. Rebuilds the whole index when the embedding model has changed.

Application flow:

Enterprise text files
    -> load_documents()
    -> _sync_index()
    -> store.embed() in batches
    -> ChromaDB collection (read by the retriever)
"""

# Import hashlib to fingerprint document content for incremental ingestion.
import hashlib

# Import the project settings.
from config import settings

# Import the shared embedding and vector store helpers.
from rag import store


def chunk_text(
    text: str,
    chunk_size: int | None = None,
) -> list[str]:
    """
    Split text into fixed-size word chunks.

    Args:
        text:
            Complete source document text.

        chunk_size:
            Maximum number of words in each chunk. Defaults to
            settings.chunk_words.

    Returns:
        A list of text chunks.

    Note:
        This implementation does not add overlap between chunks.
    """

    # Use the configured chunk size only when the caller does not provide one.
    size = settings.chunk_words if chunk_size is None else chunk_size

    # Reject invalid chunk sizes before processing the text.
    if size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    # Split the document into individual words.
    words = text.split()

    # Join each slice of words back into one chunk.
    return [
        " ".join(words[index:index + size])
        for index in range(0, len(words), size)
    ]


def load_documents() -> list[dict]:
    """
    Load, fingerprint, and chunk every enterprise text file.

    Returns:
        A list with one dictionary per non-empty document:
        - source: original filename
        - fingerprint: hash of the file content and chunking settings
        - chunks: list of text chunks
    """

    # Create the list of documents that contain indexable text.
    documents: list[dict] = []

    # Visit files in a stable order so ingestion output is reproducible.
    for path in sorted(settings.docs_dir.glob("*.txt")):

        # Read the raw bytes so the fingerprint covers every byte of the file.
        raw = path.read_bytes()

        # Include the chunk size so changing it triggers re-indexing.
        fingerprint = hashlib.sha256(
            f"chunk_words={settings.chunk_words}\n".encode("utf-8") + raw
        ).hexdigest()

        # Decode the text and split it into chunks.
        chunks = chunk_text(raw.decode("utf-8"))

        # Skip empty documents because they have nothing to retrieve.
        if chunks:
            documents.append({
                "source": path.name,
                "fingerprint": fingerprint,
                "chunks": chunks,
            })

    # Return every indexable document.
    return documents


def _indexed_fingerprints(collection) -> dict[str, str]:
    """Map each indexed source filename to the fingerprint it was indexed with."""

    # Read only metadata; the stored text and vectors are not needed here.
    existing = collection.get(include=["metadatas"])

    # Build the source-to-fingerprint map from the chunk metadata.
    return {
        metadata["source"]: metadata["fingerprint"]
        for metadata in existing["metadatas"]
    }


def _index_document(collection, document: dict) -> None:
    """Embed and upsert every chunk of one document in batches."""

    # Walk the chunks in embedding-batch-sized slices.
    chunks = document["chunks"]
    batch_size = settings.embedding_batch_size

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]

        # Create one stable ID per chunk so re-runs overwrite rather than duplicate.
        ids = [
            f"{document['source']}::{start + offset}"
            for offset in range(len(batch))
        ]

        # Upsert the chunk text, its vector, and its source metadata together.
        collection.upsert(
            ids=ids,
            documents=batch,
            embeddings=store.embed(batch),
            metadatas=[
                {
                    "source": document["source"],
                    "fingerprint": document["fingerprint"],
                }
                for _ in batch
            ],
        )


def ingest_documents() -> dict[str, int]:
    """
    Synchronize the ChromaDB index with the documents on disk.

    Only documents whose fingerprint changed are re-embedded. Documents that
    were deleted from disk are removed from the index. If the index was built
    with a different embedding model, it is rebuilt from scratch because
    vectors from different models cannot be compared.

    Returns:
        Counts describing what changed during this run.
    """

    # Load the current documents from disk.
    documents = load_documents()

    # Rebuild the index when it was created with a different embedding model.
    existing = store.get_collection(create=True)
    if existing.count() and (existing.metadata or {}).get("embedding_model") != settings.embedding_model:
        store.reset_collection()
        existing = store.get_collection(create=True)

    # Read which documents and fingerprints are already indexed.
    indexed = _indexed_fingerprints(existing)

    # Remove chunks for documents that no longer exist on disk.
    on_disk = {document["source"] for document in documents}
    removed = sorted(set(indexed) - on_disk)
    for source in removed:
        existing.delete(where={"source": source})

    # Re-embed only documents that are new or whose content changed.
    changed = [
        document for document in documents
        if indexed.get(document["source"]) != document["fingerprint"]
    ]
    for document in changed:

        # Drop stale chunks first, because a shorter document leaves old chunk IDs behind.
        if document["source"] in indexed:
            existing.delete(where={"source": document["source"]})

        _index_document(existing, document)

    # Return a summary for logs, the CLI, and the readiness check.
    return {
        "documents_found": len(documents),
        "documents_updated": len(changed),
        "documents_unchanged": len(documents) - len(changed),
        "documents_removed": len(removed),
        "total_chunks": existing.count(),
    }


# Run ingestion only when this file is executed directly.
# Importing this module from the API or tests does not trigger ingestion.
if __name__ == "__main__":

    # Print the synchronization summary.
    print(ingest_documents())
