"""
FILE PURPOSE: Unit Tests for Tools and Individual Agents

These tests exercise the MCP-style tools and the Analyst, Reviewer, and
routing logic in isolation, without running the full workflow.
"""

# Import Path to check where saved reports land.
from pathlib import Path

# Import pytest for assertions on rejected inputs.
import pytest

# Import the tools and agents under test.
from agents.analyst import analyst_agent
from agents.graph import review_router
from agents.reviewer import reviewer_agent
from config import settings
from mcp_tools.tools import calculate_business_score, save_report_file


# A report that contains every required section and passes the length check.
COMPLETE_REPORT = "# Production AI Platform Report\n\n" + "\n\n".join(
    [
        "## Question\n\nHow do we deploy AI safely?",
        "## Execution Plan\n\n- Plan",
        "## Retrieved Enterprise Context\n\n" + "Context sentence. " * 20,
        "## Analysis\n\n- Priority Score: 6.6",
        "## Recommendations\n\n1. Use RAG.",
        "## Conclusion\n\nDone.",
    ]
)


def test_business_score_applies_weights():
    # Impact 40%, urgency 40%, risk 20%.
    result = calculate_business_score(impact=10, urgency=5, risk=0)

    assert result["priority_score"] == 6.0


@pytest.mark.parametrize("bad_value", [True, 1.5, "7", -1, 11])
def test_business_score_rejects_invalid_inputs(bad_value):
    # Booleans, floats, strings, and out-of-range integers are all refused.
    with pytest.raises((TypeError, ValueError)):
        calculate_business_score(impact=bad_value, urgency=5, risk=5)


def test_save_report_writes_unique_files_inside_output_dir():
    # Two saves with the same title in the same second must not overwrite each other.
    first = save_report_file("Quarterly / Risk Report!", "# Report\n\nBody")
    second = save_report_file("Quarterly / Risk Report!", "# Report\n\nBody")

    first_path, second_path = Path(first["path"]), Path(second["path"])

    assert first_path != second_path
    assert first_path.parent == settings.output_dir
    assert first_path.read_text(encoding="utf-8") == "# Report\n\nBody"
    assert first_path.name.startswith("quarterly_risk_report_")


def test_save_report_rejects_empty_input():
    with pytest.raises(ValueError):
        save_report_file("   ", "content")
    with pytest.raises(ValueError):
        save_report_file("Title", "   ")


def test_analyst_scores_governance_monitoring_and_approval_terms():
    # The keyword rules raise risk by 2, urgency by 1, and impact by 2 from a baseline of 5.
    state = {
        "research_context": [
            {"text": "Governance requires monitoring and human approval."},
        ],
    }

    result = analyst_agent(state)["analysis"]

    assert result["priority_score"]["priority_score"] == 6.6
    assert "Governance" in result["key_themes"]
    assert "Monitoring" in result["key_themes"]
    assert result["source_count"] == 1


def test_reviewer_approves_complete_report():
    state = {"draft_report": COMPLETE_REPORT, "review_attempts": 0}

    result = reviewer_agent(state)

    assert result["approved"] is True
    assert result["final_report"] == COMPLETE_REPORT
    assert result["review_attempts"] == 1


def test_reviewer_rejects_report_with_missing_section():
    state = {"draft_report": COMPLETE_REPORT.replace("## Conclusion", "## Closing"), "review_attempts": 0}

    result = reviewer_agent(state)

    assert result["approved"] is False
    assert "Missing section: Conclusion" in result["review_notes"]


def test_review_router_sends_approved_reports_to_save():
    state = {"approved": True, "review_attempts": 1}

    assert review_router(state) == "save_report"


def test_review_router_retries_while_attempts_remain():
    state = {"approved": False, "review_attempts": settings.max_review_attempts - 1}

    assert review_router(state) == "writer"


def test_review_router_stops_when_retry_budget_is_spent():
    state = {"approved": False, "review_attempts": settings.max_review_attempts}

    assert review_router(state) == "end"
