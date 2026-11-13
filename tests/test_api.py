"""
FILE PURPOSE: API Contract Tests

These tests drive the FastAPI application through TestClient with a temporary
index and the fake embedder. They cover readiness gating, request validation,
API key enforcement, the rejected-report contract, and metric exposure.
"""

# Import pytest and SecretStr to configure authentication per test.
import pytest
from pydantic import SecretStr

# Import the test client that runs the ASGI app in-process.
from fastapi.testclient import TestClient

# Import the application and settings under test.
from app.main import app
from config import settings


@pytest.fixture
def client():
    """Start the application lifespan and yield a client for the duration of a test."""

    with TestClient(app) as test_client:
        yield test_client


def test_root_and_health_report_liveness(client):
    assert client.get("/").json()["version"] == settings.app_version
    assert client.get("/health").json() == {"status": "ok"}


def test_ready_is_503_until_index_is_built(client):
    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_ready_is_200_after_ingestion(client, ingested_index):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["chunks"] == 3


def test_ready_reports_model_mismatch(client, ingested_index, monkeypatch):
    # An index built with another model must not serve questions.
    monkeypatch.setattr(settings, "embedding_model", "different-model")

    response = client.get("/ready")

    assert response.status_code == 503
    assert "Re-run ingestion" in response.json()["reason"]


def test_run_returns_approved_report_without_server_paths(client, ingested_index):
    response = client.post(
        "/run",
        json={"question": "  How should we govern AI systems?  "},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "approved"
    assert body["question"] == "How should we govern AI systems?"
    assert body["evaluation"]["passed"] is True
    assert body["report_filename"].endswith(".md")
    assert body["final_report"].startswith("# Production AI Platform Report")
    assert "report_path" not in body
    assert "X-Request-ID" in response.headers


def test_run_returns_503_when_index_is_missing(client):
    response = client.post("/run", json={"question": "anything"})

    assert response.status_code == 503
    assert "Run `python -m rag.ingest`" in response.json()["detail"]


@pytest.mark.parametrize("question", ["", "   ", "x" * (settings.question_max_length + 1)])
def test_run_rejects_blank_or_oversized_questions(client, question):
    response = client.post("/run", json={"question": question})

    assert response.status_code == 422


def test_run_requires_api_key_when_configured(client, ingested_index, monkeypatch):
    monkeypatch.setattr(settings, "api_key", SecretStr("s3cret"))
    payload = {"question": "How should we govern AI systems?"}

    assert client.post("/run", json=payload).status_code == 401
    assert client.post("/run", json=payload, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/run", json=payload, headers={"X-API-Key": "s3cret"}).status_code == 200


def test_rejected_run_never_exposes_draft(client, ingested_index, reject_all_reviews):
    response = client.post("/run", json={"question": "How should we govern AI systems?"})
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "rejected"
    assert body["final_report"] is None
    assert body["report_filename"] is None
    assert body["review_attempts"] == settings.max_review_attempts


def test_metrics_endpoint_exposes_business_series(client, ingested_index):
    client.post("/run", json={"question": "How should we govern AI systems?"})

    metrics = client.get("/metrics").text

    assert 'platform_workflow_runs_total{outcome="approved"}' in metrics
    assert 'platform_agent_duration_seconds_count{agent="writer"}' in metrics
    assert "http_requests_total" in metrics


def test_request_id_is_echoed_when_supplied(client):
    response = client.get("/health", headers={"X-Request-ID": "trace-123"})

    assert response.headers["X-Request-ID"] == "trace-123"


def test_unhandled_error_returns_500_with_request_id(monkeypatch, ingested_index):
    # An unexpected failure must return a generic 500 that still carries the request ID.
    import app.main as main_module

    def explode(question):
        raise RuntimeError("boom")

    monkeypatch.setattr(main_module, "run_platform", explode)

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/run",
            json={"question": "How should we govern AI systems?"},
            headers={"X-Request-ID": "trace-500"},
        )

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error."}
    assert response.headers["X-Request-ID"] == "trace-500"
    assert "boom" not in response.text
