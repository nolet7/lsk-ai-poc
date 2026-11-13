"""
FILE PURPOSE: Enterprise Semantic Retriever for RAG

This file searches the ChromaDB vector collection created by `rag/ingest.py`.

It performs the following tasks:

1. Converts a user query into an embedding.
2. Searches the persistent enterprise knowledge collection.
3. Retrieves the most semantically similar document chunks.
4. Returns text, source metadata, and chunk IDs to the Researcher Agent.

Application flow:

User question
    -> Researcher Agent
    -> search_enterprise_knowledge()
    -> retrieve_context()
    -> Query embedding
    -> ChromaDB similarity search
    -> Enterprise context returned to agents
"""

# Import ChromaDB for persistent vector similarity search.
import chromadb

# Import SentenceTransformer for encoding user queries.
from sentence_transformers import SentenceTransformer


# Define the path containing the persistent ChromaDB database.
DB_PATH = "data/chroma_db"

# Define the collection populated by the ingestion module.
COLLECTION_NAME = "enterprise_knowledge"

# Use the same embedding model as the ingestion process.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Load the embedding model once when the module is imported.
model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def retrieve_context(
    query: str,
    top_k: int = 4,
) -> list[dict[str, str]]:
    """
    Retrieve the most relevant enterprise document chunks.

    Args:
        query:
            User's business or technical question.

        top_k:
            Maximum number of similar chunks to return.

    Returns:
        A list of dictionaries containing:
        - id: stored chunk identifier
        - text: retrieved chunk content
        - source: original document filename
    """

    # Reject empty queries before generating an embedding.
    if not query.strip():
        raise ValueError("query cannot be empty.")

    # Reject invalid result limits.
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    # Open the persistent ChromaDB database.
    client = chromadb.PersistentClient(path=DB_PATH)

    # Open or create the enterprise knowledge collection.
    # In production, an empty collection should usually be treated as an
    # ingestion/readiness problem rather than silently created.
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    # Convert the user's query into a semantic vector.
    query_embedding = model.encode(
        query
    ).tolist()

    # Search the vector collection for the closest document chunks.
    results = collection.query(
        # ChromaDB expects a list of query vectors.
        query_embeddings=[query_embedding],

        # Limit the number of returned matches.
        n_results=top_k,
    )

    # Create a list for normalized context records.
    contexts: list[dict[str, str]] = []

    # Safely read the first query's result arrays.
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    ids = results.get("ids", [[]])[0]

    # Combine text, metadata, and IDs returned at matching positions.
    for text, metadata, doc_id in zip(
        documents,
        metadatas,
        ids,
    ):

        # Add one structured context record for the Researcher Agent.
        contexts.append({
            # Preserve the ChromaDB chunk identifier.
            "id": doc_id,

            # Return the matching enterprise text.
            "text": text,

            # Return source attribution when available.
            "source": metadata.get(
                "source",
                "Unknown source",
            ),
        })

    # Return the normalized retrieval results.
    return contexts
