"""
FILE PURPOSE: FastAPI Request and Response Schemas

This file defines the Pydantic models used by the Production AI Platform API.

Pydantic models provide:
1. Request-body validation, including whitespace stripping and length limits.
2. Clear Python types.
3. Automatic OpenAPI schema generation.
4. Interactive Swagger documentation.
5. A stable response contract that the route is checked against.
"""

# Import typing helpers for the constrained question type and status values.
from typing import Annotated, Any, Literal

# Import Pydantic models, field helpers, and string constraints.
from pydantic import BaseModel, Field, StringConstraints

# Import the project settings for the maximum question length.
from config import settings


# A question that is stripped of surrounding whitespace, non-empty, and length-limited.
Question = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=settings.question_max_length,
    ),
]


class PlatformRequest(BaseModel):
    """
    Validate the JSON body submitted to POST /run.

    Example:
        {
            "question": "How should we deploy a governed RAG platform?"
        }
    """

    # Store the business or technical question submitted by the API client.
    # Whitespace-only questions are rejected after stripping.
    question: Question = Field(
        ...,
        description="Business or technical question for the AI platform.",
        examples=[
            "How should we productionize an enterprise RAG platform?"
        ],
    )


class EvaluationResult(BaseModel):
    """Deterministic quality checks performed on a completed run."""

    # Individual binary checks: 1 passed, 0 failed.
    scores: dict[str, int]

    # Number of checks that passed.
    total_score: int

    # Number of checks performed.
    max_score: int

    # Pass rate as a percentage.
    percentage: float

    # True when enough checks passed for the run to be considered healthy.
    passed: bool


class PlatformResponse(BaseModel):
    """
    Describe the response returned after the workflow completes.

    Note:
        final_report is returned only for approved runs. Rejected drafts are
        never exposed to clients, and report_filename is null for them.
    """

    # Identifier for this run, also written to the server logs.
    run_id: str

    # Final outcome of the quality gate.
    status: Literal["approved", "rejected"]

    # Echo of the normalized question processed by the workflow.
    question: str

    # Ordered execution plan created by the Planner Agent.
    plan: list[str]

    # Priority score, source count, and themes from the Analyst Agent.
    analysis: dict[str, Any]

    # Number of Reviewer evaluations performed before the outcome was reached.
    review_attempts: int

    # Reviewer feedback for this run.
    review_notes: str

    # Approved Markdown report, or null when the run was rejected.
    final_report: str | None

    # Filename of the saved report on the server, or null when not saved.
    report_filename: str | None

    # Output-quality evaluation for this run.
    evaluation: EvaluationResult
