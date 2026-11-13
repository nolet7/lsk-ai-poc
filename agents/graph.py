"""
FILE PURPOSE: LangGraph Orchestration

This file connects all agents into one executable multi-agent workflow.
It defines shared state, registers workflow nodes, creates edges, routes
review decisions with a retry cap, compiles the graph once, and runs it.

Workflow:
Planner -> Researcher -> Analyst -> Writer -> Reviewer
                                           | approved -> Save Report -> END
                                           | rejected, attempts left -> Writer
                                           | rejected, no attempts left -> END
"""

# Import functools to compile the graph once per process.
from functools import lru_cache

# Import logging for workflow lifecycle events.
import logging

# Import uuid to give every run a unique identifier.
import uuid

# Import types used to describe the shared workflow state.
from typing import TypedDict, List, Dict, Any

# Import the LangGraph builder and END marker.
from langgraph.graph import StateGraph, END

# Import the project settings for the review retry cap.
from config import settings

# Import each specialized agent.
from agents.planner import planner_agent
from agents.researcher import researcher_agent
from agents.analyst import analyst_agent
from agents.writer import writer_agent
from agents.reviewer import reviewer_agent
from agents.save_report import save_report_agent

# Import the metrics helpers for per-agent timing and run outcomes.
from monitoring.metrics import WORKFLOW_RUNS, timed_agent

# Create the module logger for workflow lifecycle events.
logger = logging.getLogger(__name__)


class PlatformState(TypedDict):
    """Shared data passed between every workflow agent."""

    # Unique identifier for this workflow run, used in logs and API responses.
    run_id: str

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

    # Number of times the Reviewer Agent has evaluated a draft.
    review_attempts: int

    # Approved Markdown report.
    final_report: str

    # Local path returned by the save tool.
    report_path: str

    # Approval decision used for graph routing.
    approved: bool

    # Final outcome: pending, approved, or rejected.
    status: str


def review_router(state: PlatformState) -> str:
    """Route the report according to the review decision and retry budget."""

    # Send an approved report to the saving node.
    if state["approved"]:
        return "save_report"

    # Give the Writer another attempt while the retry budget lasts.
    if state["review_attempts"] < settings.max_review_attempts:
        return "writer"

    # Stop the workflow without saving once the retry budget is exhausted.
    return "end"


@lru_cache(maxsize=1)
def build_platform_graph():
    """Build and compile the Production AI Platform workflow once per process."""

    # Create a LangGraph workflow that uses PlatformState.
    graph = StateGraph(PlatformState)

    # Register every agent as a timed graph node.
    graph.add_node("planner", timed_agent("planner")(planner_agent))
    graph.add_node("researcher", timed_agent("researcher")(researcher_agent))
    graph.add_node("analyst", timed_agent("analyst")(analyst_agent))
    graph.add_node("writer", timed_agent("writer")(writer_agent))
    graph.add_node("reviewer", timed_agent("reviewer")(reviewer_agent))
    graph.add_node("save_report", timed_agent("save_report")(save_report_agent))

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

            # Rejected reports return to the writer while attempts remain.
            "writer": "writer",

            # Rejected reports with no attempts left end without saving.
            "end": END,
        },
    )

    # End the workflow after the report has been saved.
    graph.add_edge("save_report", END)

    # Compile and return the executable graph.
    return graph.compile()


def run_platform(question: str) -> PlatformState:
    """
    Run the complete multi-agent workflow for one question.

    Args:
        question:
            Business or technical question to answer.

    Returns:
        The completed workflow state, including run_id and status.

    Raises:
        Any exception raised by an agent, such as IndexNotReadyError when the
        knowledge index is missing. The outcome is counted before re-raising.
    """

    # Build the executable application; this is cached after the first call.
    app = build_platform_graph()

    # Initialize every field required by PlatformState.
    run_id = uuid.uuid4().hex
    initial_state: PlatformState = {
        "run_id": run_id,
        "question": question,
        "plan": [],
        "research_context": [],
        "analysis": {},
        "draft_report": "",
        "review_notes": "",
        "review_attempts": 0,
        "final_report": "",
        "report_path": "",
        "approved": False,
        "status": "pending",
    }

    # Execute the graph, counting failures so they show up in dashboards.
    try:
        result = app.invoke(initial_state)
    except Exception:
        WORKFLOW_RUNS.labels(outcome="error").inc()
        logger.exception("workflow failed run_id=%s", run_id)
        raise

    # Record the final decision on the state and in metrics.
    result["status"] = "approved" if result["approved"] else "rejected"
    WORKFLOW_RUNS.labels(outcome=result["status"]).inc()
    logger.info(
        "workflow finished run_id=%s status=%s review_attempts=%d",
        result["run_id"],
        result["status"],
        result["review_attempts"],
    )

    # Return the completed workflow state.
    return result
