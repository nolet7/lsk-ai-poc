"""
FILE PURPOSE: Enterprise Document Ingestion for RAG

This file prepares enterprise text documents for semantic search.

It performs the following tasks:

1. Finds `.txt` files under `data/docs`.
2. Splits each file into smaller word-based chunks.
3. Creates vector embeddings with SentenceTransformers.
4. Stores the chunks, embeddings, and source metadata in ChromaDB.
5. Supports direct command-line execution for manual ingestion.

Application flow:

Enterprise text files
    -> load_documents()
    -> chunk_text()
    -> SentenceTransformer embeddings
    -> ChromaDB persistent collection
    -> Retriever Agent can search indexed knowledge

This module is called by `app/main.py` during FastAPI startup.
"""

# Import Path for cross-platform file and directory handling.
from pathlib import Path

# Import ChromaDB for persistent local vector storage.
import chromadb

# Import SentenceTransformer for creating semantic embeddings.
from sentence_transformers import SentenceTransformer


# Define the directory containing enterprise source documents.
DOCS_DIR = Path("data/docs")

# Define where ChromaDB stores its persistent database files.
DB_PATH = "data/chroma_db"

# Define the collection used for enterprise knowledge vectors.
COLLECTION_NAME = "enterprise_knowledge"

# Define the embedding model used for both ingestion and retrieval.
# Using the same model in both modules keeps vectors compatible.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Load the sentence-transformer model once when this module is imported.
# This avoids reloading the model for every document chunk.
model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def chunk_text(
    text: str,
    chunk_size: int = 500,
) -> list[str]:
    """
    Split text into fixed-size word chunks.

    Args:
        text:
            Complete source document text.

        chunk_size:
            Maximum number of words in each chunk.

    Returns:
        A list of text chunks.

    Note:
        This implementation does not add overlap between chunks.
    """

    # Reject invalid chunk sizes before processing the text.
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    # Split the document into individual words.
    words = text.split()

    # Create a list that will hold the resulting text chunks.
    chunks: list[str] = []

    # Move through the word list in chunk_size increments.
    for index in range(0, len(words), chunk_size):

        # Join the current word range back into one text chunk.
        chunk = " ".join(
            words[index:index + chunk_size]
        )

        # Add only non-empty chunks to the result.
        if chunk:
            chunks.append(chunk)

    # Return all chunks generated from the source text.
    return chunks


def load_documents() -> list[dict[str, str]]:
    """
    Load and chunk all enterprise text files.

    Returns:
        A list of dictionaries containing:
        - id: unique chunk identifier
        - source: original filename
        - text: chunk content
    """

    # Create a list for every document chunk prepared for indexing.
    documents: list[dict[str, str]] = []

    # Search the configured document directory for text files.
    for path in DOCS_DIR.glob("*.txt"):

        # Read the complete file using UTF-8 encoding.
        text = path.read_text(encoding="utf-8")

        # Split the file into smaller chunks and enumerate them.
        for chunk_index, chunk in enumerate(chunk_text(text)):

            # Create one structured record for each document chunk.
            documents.append({
                # Combine the filename stem and chunk number for a stable ID.
                "id": f"{path.stem}-{chunk_index}",

                # Preserve the original filename as source metadata.
                "source": path.name,

                # Store the actual text that will be embedded and retrieved.
                "text": chunk,
            })

    # Return every prepared chunk from every source file.
    return documents


def ingest_documents() -> dict[str, int]:
    """
    Embed and index enterprise document chunks in ChromaDB.

    Returns:
        A dictionary containing the number of indexed chunks.
    """

    # Create or open the persistent local ChromaDB database.
    client = chromadb.PersistentClient(path=DB_PATH)

    # Create the enterprise collection when it does not already exist.
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME
    )

    # Load and chunk all configured enterprise documents.
    docs = load_documents()

    # Process each prepared document chunk.
    for doc in docs:

        # Convert the text chunk into a dense semantic vector.
        embedding = model.encode(
            doc["text"]
        ).tolist()

        # Insert or update the chunk in ChromaDB.
        # Upsert allows repeated ingestion without duplicate IDs.
        collection.upsert(
            # ChromaDB expects list values, even for one document.
            ids=[doc["id"]],

            # Store the source chunk text.
            documents=[doc["text"]],

            # Store the vector created by SentenceTransformers.
            embeddings=[embedding],

            # Store the original filename for source attribution.
            metadatas=[
                {
                    "source": doc["source"]
                }
            ],
        )

    # Return a small ingestion summary for logs or API startup diagnostics.
    return {
        "documents_indexed": len(docs)
    }


# Run ingestion only when this file is executed directly.
# Importing this module from FastAPI does not trigger this block.
if __name__ == "__main__":

    # Execute ingestion and print the number of indexed chunks.
    print(ingest_documents())
