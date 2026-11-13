"""
FILE PURPOSE: Researcher Agent

This file retrieves enterprise knowledge related to the user's question.
It calls an MCP-style search tool and stores the returned sources in the
shared LangGraph state.

Flow:
Planner -> Researcher -> Analyst
"""

# Import the enterprise-search function from the MCP tools layer.
from mcp_tools.tools import search_enterprise_knowledge


def researcher_agent(state: dict) -> dict:
    """Retrieve enterprise evidence for the current user question."""

    # Read the original question from shared workflow state.
    question = state["question"]

    # Search the enterprise knowledge source for relevant evidence.
    context = search_enterprise_knowledge(question)

    # Store the retrieved source records for the Analyst and Writer Agents.
    state["research_context"] = context

    # Return the updated state to LangGraph.
    return state
