"""
FILE PURPOSE: Workflow Tests

These tests run the full LangGraph workflow against a temporary index and
verify the outcomes that matter to operators: approved reports are saved,
rejected drafts are never saved, and the retry loop always terminates.
"""

# Import Path to compare the saved report location.
from pathlib import Path

# Import pytest for assertions on exceptions.
import pytest

# Import the workflow under test and the settings that control the retry cap.
from agents.graph import run_platform
from config import settings

# Import the readiness exception raised when no index exists.
from rag.store import IndexNotReadyError


def test_approved_run_saves_report(ingested_index):
    result = run_platform("How should an enterprise deploy governed AI agents?")

    assert result["status"] == "approved"
    assert result["approved"] is True
    assert "## Recommendations" in result["final_report"]

    saved = list(settings.output_dir.glob("*.md"))
    assert saved == [Path(result["report_path"])]


def test_run_ids_are_unique(ingested_index):
    first = run_platform("question one")
    second = run_platform("question two")

    assert first["run_id"] != second["run_id"]


def test_rejected_run_stops_after_retry_budget_and_saves_nothing(ingested_index, reject_all_reviews):
    result = run_platform("Will this be rejected?")

    # The writer and reviewer ran exactly as many times as the budget allows.
    assert result["status"] == "rejected"
    assert result["review_attempts"] == settings.max_review_attempts
    assert result["report_path"] == ""
    assert not settings.output_dir.exists() or list(settings.output_dir.glob("*.md")) == []


def test_workflow_fails_when_index_is_missing():
    # Without an index the researcher cannot run, and the error must propagate.
    with pytest.raises(IndexNotReadyError):
        run_platform("anything")
