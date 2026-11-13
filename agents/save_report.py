"""
FILE PURPOSE: Save Report Agent

This file saves the approved report by calling an MCP-style file tool.
It records the returned report path in shared LangGraph state.

Flow:
Reviewer approval -> Save Report -> END
"""

# Import the MCP-style report persistence function.
from mcp_tools.tools import save_report_file


def save_report_agent(state: dict) -> dict:
    """Save the approved report and record its file path."""

    # Call the file-saving tool with the report title and approved content.
    result = save_report_file(
        title="Production AI Platform Report",
        content=state["final_report"],
    )

    # Store the generated report path in shared state.
    state["report_path"] = result["path"]

    # Return the completed workflow state.
    return state
