"""
FILE PURPOSE: FastAPI Request and Response Schemas

This file defines Pydantic models used by the Production AI Platform API.

Pydantic models provide:
1. Request-body validation.
2. Clear Python types.
3. Automatic OpenAPI schema generation.
4. Interactive Swagger documentation.
5. Consistent API contracts between clients and the FastAPI service.
"""

# Import Pydantic's base class for typed validation models.
from pydantic import BaseModel, Field


class PlatformRequest(BaseModel):
    """
    Validate the JSON body submitted to POST /run.

    Example:
        {
            "question": "How should we deploy a governed RAG platform?"
        }
    """

    # Store the business or technical question submitted by the API client.
    # min_length prevents empty questions from reaching the agent workflow.
    question: str = Field(
        ...,
        min_length=1,
        description="Business or technical question for the AI platform.",
        examples=[
            "How should we productionize an enterprise RAG platform?"
        ],
    )


class PlatformResponse(BaseModel):
    """
    Describe the core response returned after the workflow completes.

    Note:
        The current FastAPI route returns additional fields such as plan,
        analysis, and review_notes. This schema captures the original core
        response fields and can be expanded or attached to the route with
        response_model=PlatformResponse.
    """

    # Echo the question processed by the workflow.
    question: str

    # Contain the approved Markdown report.
    final_report: str

    # Identify where the report was saved.
    report_path: str

    # Contain the result returned by the output evaluator.
    evaluation: dict
