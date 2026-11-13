"""
FILE PURPOSE: Writer Agent

This file converts the question, plan, enterprise context, and analysis into
a structured Markdown report.

Flow:
Analyst -> Writer -> Reviewer
"""


def writer_agent(state: dict) -> dict:
    """Generate the draft and final Markdown report."""

    # Read the user's question from shared state.
    question = state["question"]

    # Read the ordered plan created by the Planner Agent.
    plan = state["plan"]

    # Read the evidence returned by the Researcher Agent.
    context = state["research_context"]

    # Read the scoring and themes created by the Analyst Agent.
    analysis = state["analysis"]

    # Start the Markdown report with the title and question.
    report = f"""# Production AI Platform Report

## Question

{question}

## Execution Plan

"""

    # Add every plan step as a Markdown bullet.
    for step in plan:
        report += f"- {step}\n"

    # Add the enterprise context section heading.
    report += """

## Retrieved Enterprise Context

"""

    # Add every enterprise source to the report.
    for item in context:

        # Read the source name safely.
        source_name = item.get("source", "Unknown source")

        # Read the source content safely.
        source_text = item.get("text", "No source text was returned.")

        # Format the source as a Markdown subsection.
        report += f"""
### Source: {source_name}

{source_text}
"""

    # Read the nested result returned by the scoring tool.
    priority_result = analysis.get("priority_score", {})

    # Extract the numeric priority score or use a fallback.
    priority_score = priority_result.get(
        "priority_score",
        "Not available",
    )

    # Read the list of themes detected by the Analyst Agent.
    key_themes = analysis.get("key_themes", [])

    # Convert the themes into readable comma-separated text.
    theme_text = (
        ", ".join(key_themes)
        if key_themes
        else "No key themes detected"
    )

    # Add analysis, recommendations, and conclusion sections.
    report += f"""

## Analysis

- Source Count: {analysis.get("source_count", 0)}
- Key Themes: {theme_text}
- Priority Score: {priority_score}

## Recommendations

1. Use RAG for grounded enterprise responses.
2. Use multi-agent orchestration for complex workflows.
3. Add evaluation before release.
4. Add monitoring for reliability and cost tracking.
5. Require human approval for high-risk actions.

## Conclusion

This platform demonstrates a production-style AI architecture combining agents, RAG, MCP-style tools, evaluation, monitoring, API serving, and local report generation.
"""

    # Store the report as the draft reviewed by the Reviewer Agent.
    state["draft_report"] = report

    # Populate final_report so the Save Report Agent receives report content.
    # The original code did not populate this field.
    state["final_report"] = report

    # Return the updated state to the Reviewer Agent.
    return state
