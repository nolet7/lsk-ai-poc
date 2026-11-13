"""
FILE PURPOSE: Analyst Agent

This file analyzes enterprise evidence retrieved by the Researcher Agent.
It detects platform themes, calculates business priority, and stores a
structured analysis for the Writer Agent.

Flow:
Researcher -> Analyst -> Writer
"""

# Import the MCP-style business scoring function.
from mcp_tools.tools import calculate_business_score


def analyst_agent(state: dict) -> dict:
    """Analyze retrieved enterprise evidence and calculate priority."""

    # Read the list of enterprise source records from shared state.
    context = state["research_context"]

    # Join all returned source text into one lowercase string.
    # Lowercase makes the keyword checks case-insensitive.
    combined_context = " ".join(
        item.get("text", "") for item in context
    ).lower()

    # Start each scoring category at a neutral baseline value.
    risk = 5
    urgency = 5
    impact = 5

    # Increase risk when governance is mentioned.
    if "governance" in combined_context:
        risk += 2

    # Increase urgency when monitoring is mentioned.
    if "monitoring" in combined_context:
        urgency += 1

    # Increase impact when human approval is mentioned.
    if "human approval" in combined_context:
        impact += 2

    # Calculate the overall business priority score.
    # min(..., 10) prevents any input from exceeding the expected maximum.
    score = calculate_business_score(
        impact=min(impact, 10),
        urgency=min(urgency, 10),
        risk=min(risk, 10),
    )

    # Save the structured analysis for the Writer Agent.
    state["analysis"] = {
        # Store the score returned by the MCP scoring tool.
        "priority_score": score,

        # Detect major platform themes in the enterprise context.
        "key_themes": extract_themes(combined_context),

        # Record how many enterprise sources were used.
        "source_count": len(context),
    }

    # Return the updated workflow state.
    return state


def extract_themes(text: str) -> list[str]:
    """Detect high-level AI platform themes using keyword matching."""

    # Create a list for all detected themes.
    themes: list[str] = []

    # Map each business theme to related keywords.
    theme_map = {
        "Governance": ["governance", "policy", "approval"],
        "Monitoring": ["monitoring", "observability", "metrics"],
        "RAG": ["retrieval", "rag", "context"],
        "Security": ["access control", "audit", "security"],
        "Deployment": ["deployment", "production"],
    }

    # Check every theme and its related keywords.
    for theme, keywords in theme_map.items():

        # Add the theme when any associated keyword appears in the text.
        if any(keyword in text for keyword in keywords):
            themes.append(theme)

    # Return all detected themes.
    return themes
