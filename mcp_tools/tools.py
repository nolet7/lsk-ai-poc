"""
FILE PURPOSE: MCP-Style Tools for the Production AI Platform

This file contains reusable tool functions called by the platform's agents.

It provides three capabilities:

1. Enterprise knowledge retrieval
   - Calls the RAG retriever to find context related to a user question.

2. Business-priority scoring
   - Combines impact, urgency, and risk into a weighted score.

3. Report persistence
   - Saves approved Markdown reports to a timestamped file.

Agent usage:

Researcher Agent
    -> search_enterprise_knowledge()

Analyst Agent
    -> calculate_business_score()

Save Report Agent
    -> save_report_file()
"""

# Import datetime so report filenames can include the current date and time.
from datetime import datetime

# Import regular expressions for safe report filename normalization.
import re

# Import uuid so concurrent runs in the same second never overwrite each other.
import uuid

# Import the project settings for the report output directory.
from config import settings

# Import the RAG retrieval function used to search enterprise knowledge.
from rag.retriever import retrieve_context


def search_enterprise_knowledge(query: str) -> list[dict]:
    """
    Retrieve enterprise context related to a user question.

    Args:
        query:
            Business or technical question submitted to the platform.

    Returns:
        A list of source dictionaries returned by the RAG retriever.

    Used by:
        Researcher Agent
    """

    # Pass the user's question to the RAG retrieval layer.
    return retrieve_context(query)


def calculate_business_score(
    impact: int,
    urgency: int,
    risk: int,
) -> dict[str, int | float]:
    """
    Calculate a weighted business-priority score.

    Weighting:
        Impact: 40%
        Urgency: 40%
        Risk: 20%

    Args:
        impact:
            Estimated business impact, typically on a 1-to-10 scale.

        urgency:
            Estimated time sensitivity, typically on a 1-to-10 scale.

        risk:
            Estimated operational or governance risk, typically on a
            1-to-10 scale.

    Returns:
        The original dimensions and the calculated priority score.

    Used by:
        Analyst Agent
    """

    # Validate the score inputs before performing the weighted calculation.
    for name, value in {
        "impact": impact,
        "urgency": urgency,
        "risk": risk,
    }.items():

        # Reject Boolean values because bool is technically a subclass of int.
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer.")

        # Enforce the scoring range expected by the Analyst Agent.
        if not 0 <= value <= 10:
            raise ValueError(f"{name} must be between 0 and 10.")

    # Calculate the weighted priority score.
    score = (
        (impact * 0.4)
        + (urgency * 0.4)
        + (risk * 0.2)
    )

    # Return both the source inputs and rounded calculated score.
    return {
        "impact": impact,
        "urgency": urgency,
        "risk": risk,
        "priority_score": round(score, 2),
    }


def save_report_file(title: str, content: str) -> dict[str, str]:
    """
    Save an approved Markdown report to the local output directory.

    Args:
        title:
            Human-readable report title used to create the filename.

        content:
            Complete Markdown report content.

    Returns:
        A dictionary containing the saved report path.

    Used by:
        Save Report Agent
    """

    # Reject empty titles because they produce unclear filenames.
    if not title.strip():
        raise ValueError("Report title cannot be empty.")

    # Reject empty report content to prevent saving unusable files.
    if not content.strip():
        raise ValueError("Report content cannot be empty.")

    # Create the output directory and any missing parent directories.
    settings.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Normalize the title for safe cross-platform filenames:
    # 1. Convert to lowercase.
    # 2. Replace unsupported characters with underscores.
    # 3. Remove leading and trailing underscores.
    # 4. Limit the filename component to 50 characters.
    safe_title = re.sub(
        r"[^a-z0-9_-]+",
        "_",
        title.lower(),
    ).strip("_")[:50]

    # Use a fallback when normalization removes every title character.
    if not safe_title:
        safe_title = "production_ai_platform_report"

    # Create a timestamp so reports sort chronologically.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Add a short random suffix so two saves in the same second never collide.
    suffix = uuid.uuid4().hex[:8]

    # Build the final Markdown file path.
    path = settings.output_dir / f"{safe_title}_{timestamp}_{suffix}.md"

    # Write the report using UTF-8 so international text is preserved.
    path.write_text(
        content,
        encoding="utf-8",
    )

    # Return the saved location to the Save Report Agent.
    return {
        "path": str(path)
    }
