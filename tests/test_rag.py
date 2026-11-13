"""
FILE PURPOSE: Unit Tests for Chunking, Ingestion, and Retrieval

These tests cover the RAG layer with the deterministic fake embedder from
conftest.py. They check incremental ingestion, re-indexing after edits and
model changes, and the explicit error raised when the index is missing.
"""

# Import pytest for assertions on exceptions.
import pytest

# Import the project settings so tests can change the embedding model.
from config import settings

# Import the modules under test.
from rag.ingest import chunk_text, ingest_documents
from rag.retriever import retrieve_context
from rag.store import IndexNotReadyError, get_collection


def test_chunk_text_splits_on_word_boundaries():
    # Words are grouped into chunks of at most the requested size.
    assert chunk_text("a b c d e", chunk_size=2) == ["a b", "c d", "e"]


def test_chunk_text_rejects_non_positive_size():
    # A chunk size of zero would loop forever or produce nothing, so it is refused.
    with pytest.raises(ValueError):
        chunk_text("a b c", chunk_size=0)


def test_ingest_indexes_every_document_first_time(ingested_index):
    assert ingested_index["documents_found"] == 3
    assert ingested_index["documents_updated"] == 3
    assert ingested_index["total_chunks"] == 3


def test_ingest_skips_unchanged_documents(ingested_index):
    # A second run over identical files re-embeds nothing.
    second = ingest_documents()

    assert second["documents_updated"] == 0
    assert second["documents_unchanged"] == 3
    assert second["total_chunks"] == ingested_index["total_chunks"]


def test_ingest_reindexes_only_changed_document(ingested_index):
    # Editing one file re-embeds that file and leaves the others untouched.
    target = settings.docs_dir / "rag_best_practices.txt"
    target.write_text(target.read_text(encoding="utf-8") + "\nNew guidance.", encoding="utf-8")

    result = ingest_documents()

    assert result["documents_updated"] == 1
    assert result["documents_unchanged"] == 2


def test_ingest_removes_deleted_document(ingested_index):
    # Deleting a file removes its chunks so retrieval cannot cite a missing source.
    (settings.docs_dir / "ai_governance_policy.txt").unlink()

    result = ingest_documents()

    assert result["documents_removed"] == 1
    assert result["total_chunks"] == 2


def test_ingest_rebuilds_index_when_embedding_model_changes(ingested_index, monkeypatch):
    # Vectors from different models are not comparable, so the index is rebuilt.
    monkeypatch.setattr(settings, "embedding_model", "another-model")

    result = ingest_documents()

    assert result["documents_updated"] == 3
    assert get_collection(create=False).metadata["embedding_model"] == "another-model"


def test_retriever_fails_clearly_when_index_is_missing():
    # Querying before ingestion must raise the readiness error, not return an empty list.
    with pytest.raises(IndexNotReadyError):
        retrieve_context("anything")


def test_retriever_rejects_blank_query(ingested_index):
    with pytest.raises(ValueError):
        retrieve_context("   ")


def test_retriever_rejects_zero_top_k(ingested_index):
    # Zero must be refused rather than silently replaced by the default.
    with pytest.raises(ValueError):
        retrieve_context("human approval", top_k=0)


def test_retriever_returns_sources_with_distances(ingested_index):
    results = retrieve_context("human approval for high-risk AI decisions", top_k=2)

    assert len(results) == 2
    assert {"id", "text", "source", "distance"} <= set(results[0])
    assert results[0]["source"] == "ai_governance_policy.txt"
