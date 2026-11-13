"""
FILE PURPOSE: LangGraph Orchestration

This file connects all agents into one executable multi-agent workflow.
It defines shared state, registers workflow nodes, creates edges, routes
review decisions, compiles the graph, and runs the platform.

Workflow:
Planner -> Researcher -> Analyst -> Writer -> Reviewer
                                           | approved -> Save Report -> END
                                           | rejected -> Writer
"""

# Import types used to describe the shared workflow state.
from typing import TypedDict, List, Dict, Any

# Import the LangGraph builder and END marker.
from langgraph.graph import StateGraph, END

# Import each specialized agent.
from agents.planner import planner_agent
from agents.researcher import researcher_agent
from agents.analyst import analyst_agent
from agents.writer import writer_agent
from agents.reviewer import reviewer_agent
from agents.save_report import save_report_agent


class PlatformState(TypedDict):
    """Shared data passed between every workflow agent."""

    # Original business or technical question.
    question: str

    # Ordered plan created by the Planner Agent.
    plan: List[str]

    # Enterprise records returned by the Researcher Agent.
    research_context: List[Dict[str, Any]]

    # Priority score and themes created by the Analyst Agent.
    analysis: Dict[str, Any]

    # Markdown report before quality approval.
    draft_report: str

    # Feedback created by the Reviewer Agent.
    review_notes: str

    # Approved Markdown report.
    final_report: str

    # Local path returned by the save tool.
    report_path: str

    # Approval decision used for graph routing.
    approved: bool


def review_router(state: PlatformState) -> str:
    """Route the report according to the review decision."""

    # Send an approved report to the saving node.
    if state["approved"]:
        return "save_report"

    # Send a rejected report back to the Writer Agent.
    return "writer"


def build_platform_graph():
    """Build and compile the Production AI Platform workflow."""

    # Create a LangGraph workflow that uses PlatformState.
    graph = StateGraph(PlatformState)

    # Register every agent as a graph node.
    graph.add_node("planner", planner_agent)
    graph.add_node("researcher", researcher_agent)
    graph.add_node("analyst", analyst_agent)
    graph.add_node("writer", writer_agent)
    graph.add_node("reviewer", reviewer_agent)
    graph.add_node("save_report", save_report_agent)

    # Make the Planner Agent the first workflow node.
    graph.set_entry_point("planner")

    # Connect the normal forward-processing path.
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "analyst")
    graph.add_edge("analyst", "writer")
    graph.add_edge("writer", "reviewer")

    # Add conditional routing after report review.
    graph.add_conditional_edges(
        "reviewer",
        review_router,
        {
            # Approved reports move to persistence.
            "save_report": "save_report",

            # Rejected reports return to the writer.
            "writer": "writer",
        },
    )

    # End the workflow after the report has been saved.
    graph.add_edge("save_report", END)

    # Compile and return the executable graph.
    return graph.compile()


def run_platform(question: str) -> PlatformState:
    """Run the complete multi-agent workflow for one question."""

    # Build the executable application.
    app = build_platform_graph()

    # Initialize every field required by PlatformState.
    initial_state: PlatformState = {
        # Store the submitted user question.
        "question": question,

        # The Planner Agent will populate this field.
        "plan": [],

        # The Researcher Agent will populate this field.
        "research_context": [],

        # The Analyst Agent will populate this field.
        "analysis": {},

        # The Writer Agent will populate this field.
        "draft_report": "",

        # The Reviewer Agent will populate this field.
        "review_notes": "",

        # The Writer or Reviewer will populate this field.
        "final_report": "",

        # The Save Report Agent will populate this field.
        "report_path": "",

        # Reports start unapproved.
        "approved": False,
    }

    # Execute the graph and return the completed workflow state.
    return app.invoke(initial_state)
