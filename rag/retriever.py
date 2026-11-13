"""
FILE PURPOSE: Enterprise Semantic Retriever for RAG

This file searches the ChromaDB vector collection built by `rag/ingest.py`.

It performs the following tasks:

1. Converts a user query into an embedding with the shared model.
2. Verifies that the index exists and is not empty.
3. Retrieves the most similar document chunks.
4. Returns text, source metadata, chunk IDs, and distances to the Researcher Agent.

Application flow:

User question
    -> Researcher Agent
    -> search_enterprise_knowledge()
    -> retrieve_context()
    -> Query embedding
    -> ChromaDB similarity search
    -> Enterprise context returned to agents
"""

# Import the project settings for default result counts.
from config import settings

# Import the shared embedding and vector store helpers.
from rag import store
from rag.store import IndexNotReadyError


def retrieve_context(
    query: str,
    top_k: int | None = None,
) -> list[dict]:
    """
    Retrieve the most relevant enterprise document chunks.

    Args:
        query:
            User's business or technical question.

        top_k:
            Maximum number of similar chunks to return. Defaults to
            settings.top_k.

    Returns:
        A list of dictionaries containing:
        - id: stored chunk identifier
        - text: retrieved chunk content
        - source: original document filename
        - distance: vector distance, where lower means more similar

    Raises:
        ValueError: if the query is empty or top_k is not positive.
        IndexNotReadyError: if the index is missing or empty.
    """

    # Reject empty queries before generating an embedding.
    if not query.strip():
        raise ValueError("query cannot be empty.")

    # Resolve and validate the number of results requested.
    limit = settings.top_k if top_k is None else top_k
    if limit <= 0:
        raise ValueError("top_k must be greater than zero.")

    # Open the existing collection; this raises if the index was never built.
    collection = store.get_collection(create=False)

    # An empty index is an ingestion problem, so report it instead of returning nothing.
    total = collection.count()
    if total == 0:
        raise IndexNotReadyError(
            "Knowledge index is empty. Run `python -m rag.ingest` first."
        )

    # Search for no more results than the index holds.
    results = collection.query(
        query_embeddings=store.embed([query]),
        n_results=min(limit, total),
        include=["documents", "metadatas", "distances"],
    )

    # Create the normalized context records from the first (and only) query.
    contexts: list[dict] = []
    for doc_id, text, metadata, distance in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        strict=True,
    ):
        contexts.append({
            "id": doc_id,
            "text": text,
            "source": (metadata or {}).get("source", "Unknown source"),
            "distance": round(float(distance), 4),
        })

    # Return the normalized retrieval results.
    return contexts
