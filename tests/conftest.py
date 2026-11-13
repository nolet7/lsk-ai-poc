"""
FILE PURPOSE: Shared Test Fixtures

This file isolates every test from the real data directories and, by default,
from the real embedding model.

Isolation:
- Documents are copied into a temporary directory, so tests can add, change,
  or delete files freely.
- ChromaDB and report output use temporary directories.
- The embedding model is replaced by a deterministic bag-of-words embedder,
  so unit and API tests run in seconds without downloading anything.

Tests marked `integration` keep the real embedder and must be run explicitly
with `pytest -m integration`.
"""

# Import hashlib for a deterministic, process-independent token hash.
import hashlib

# Import math and re for the fake embedder.
import math
import re

# Import shutil to copy the sample documents into a temporary directory.
import shutil

# Import pytest for fixtures and markers.
import pytest

# Import the project settings and the modules whose state must be reset between tests.
from config import PROJECT_ROOT, settings
from agents import graph as graph_module
from rag import store


# Width of the fake embedding vectors.
FAKE_DIM = 64


def fake_embed(texts: list[str]) -> list[list[float]]:
    """Embed each text as a normalized bag-of-words vector over hashed tokens."""

    vectors: list[list[float]] = []
    for text in texts:

        # Count hashed tokens into fixed buckets.
        vector = [0.0] * FAKE_DIM
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            bucket = hashlib.md5(token.encode("utf-8")).digest()[0] % FAKE_DIM
            vector[bucket] += 1.0

        # Normalize so longer texts do not dominate.
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        vectors.append([value / norm for value in vector])

    return vectors


def _reset_caches() -> None:
    """Clear process-level caches so each test builds its own resources."""

    store._client.cache_clear()
    graph_module.build_platform_graph.cache_clear()


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch, request):
    """Point all storage at temporary directories and disable optional startup work."""

    # Copy the sample corpus so tests can modify it without touching the repository.
    docs_dir = tmp_path / "docs"
    shutil.copytree(PROJECT_ROOT / "data" / "docs", docs_dir)

    # Redirect every storage location into the temporary directory.
    monkeypatch.setattr(settings, "docs_dir", docs_dir)
    monkeypatch.setattr(settings, "chroma_dir", tmp_path / "chroma")
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    # Keep the API unauthenticated and skip model warm-up unless a test opts in.
    monkeypatch.setattr(settings, "api_key", None)
    monkeypatch.setattr(settings, "warmup_model", False)

    # Replace the embedder unless the test explicitly needs the real model.
    if request.node.get_closest_marker("integration") is None:
        monkeypatch.setattr(store, "embed", fake_embed)

    # Start and finish each test with fresh caches.
    _reset_caches()
    yield
    _reset_caches()


@pytest.fixture
def ingested_index():
    """Build the knowledge index from the temporary corpus and return the ingestion summary."""

    # Import here so the fixture resolves the module after the isolated settings are applied.
    from rag.ingest import ingest_documents

    return ingest_documents()


@pytest.fixture
def reject_all_reviews(monkeypatch):
    """Replace the Reviewer Agent with one that always rejects the draft."""

    def always_reject(state: dict) -> dict:
        state["review_attempts"] = state.get("review_attempts", 0) + 1
        state["approved"] = False
        state["review_notes"] = "Forced rejection for testing."
        return state

    monkeypatch.setattr(graph_module, "reviewer_agent", always_reject)
    graph_module.build_platform_graph.cache_clear()
