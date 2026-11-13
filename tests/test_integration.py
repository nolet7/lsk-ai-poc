"""
FILE PURPOSE: Integration Tests with the Real Embedding Model

These tests load the real sentence-transformers model and a temporary
ChromaDB index. They verify what unit tests cannot: that ingestion and
retrieval agree on the embedding model, and that retrieval ranks the expected
documents first.

Run them explicitly, since they need the model weights:

    pytest -m integration

Set HF_HUB_OFFLINE=1 to use a locally cached model without network access.
"""

# Import pytest for the integration marker.
import pytest

# Import the evaluation helpers and golden set used by the CI retrieval gate.
from evaluation.run_eval import DEFAULT_GOLDEN_SET, evaluate_retrieval, load_golden_set
from rag.ingest import ingest_documents
from rag.retriever import retrieve_context


pytestmark = pytest.mark.integration


def test_real_model_indexes_and_retrieves_governance_document():
    # Index the temporary copy of the corpus with the real embedder.
    ingest_documents()

    # The governance question should surface the governance document first.
    results = retrieve_context("Who approves high-risk AI decisions?", top_k=2)

    assert results[0]["source"] == "ai_governance_policy.txt"


def test_retrieval_meets_golden_set_threshold():
    # The same check that CI runs through evaluation/run_eval.py.
    ingest_documents()

    report = evaluate_retrieval(load_golden_set(DEFAULT_GOLDEN_SET), top_k=4)

    assert report["hit_at_1"] >= 0.75, report
