"""
FILE PURPOSE: Planner Agent

This file creates the ordered execution plan for the multi-agent AI platform.
It is the first agent in the workflow.

Flow:
User question -> Planner -> Researcher
"""


def planner_agent(state: dict) -> dict:
    """Create the workflow plan and add it to the shared state."""

    # Read the user's original question from the shared LangGraph state.
    question = state["question"]

    # Store the ordered tasks that all later agents will follow.
    state["plan"] = [
        # Understand what the user is asking.
        "Understand the user question",

        # Find enterprise information related to the question.
        "Retrieve relevant enterprise knowledge",

        # Analyze business risks, priorities, and actions.
        "Analyze risks, actions, and recommendations",

        # Create a structured report from the collected information.
        "Generate a structured business report",

        # Validate the report before it is accepted.
        "Review the report for quality",

        # Save the approved final report.
        "Save the final report",
    ]

    # Keep the question available for future question-specific planning logic.
    _ = question

    # Return the updated state to the next LangGraph node.
    return state
