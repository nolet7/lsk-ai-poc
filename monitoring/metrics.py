"""
FILE PURPOSE: Prometheus Metrics for the Production AI Platform

This file exposes two layers of metrics:

1. HTTP metrics from prometheus-fastapi-instrumentator: request rate, status
   codes, and latency per route.
2. Business metrics for the AI workflow: workflow outcomes, per-agent
   duration, retrieval breadth, review rejections, evaluation scores, and
   index size.

Label values are kept low-cardinality. Labels never contain user questions,
run IDs, or document names, because each distinct value creates a new time
series in Prometheus.

Application flow:

app/main.py
    -> setup_metrics(app)          HTTP metrics + /metrics endpoint
agents/graph.py
    -> timed_agent("name")         per-agent duration
agents/reviewer.py
    -> REVIEW_REJECTIONS.inc()     quality-gate rejections
app/main.py, agents/graph.py
    -> WORKFLOW_RUNS, RETRIEVED_SOURCES, EVALUATION_PERCENTAGE, INDEX_CHUNKS
"""

# Import functools so the timing decorator keeps each agent's name and docstring.
import functools

# Import perf_counter for high-resolution duration measurement.
from time import perf_counter

# Import the Prometheus metric types used for business instrumentation.
from prometheus_client import Counter, Gauge, Histogram

# Import FastAPI for the application type annotation.
from fastapi import FastAPI

# Import the third-party helper that instruments FastAPI for Prometheus.
from prometheus_fastapi_instrumentator import Instrumentator


# Count completed workflow runs by outcome: approved, rejected, or error.
WORKFLOW_RUNS = Counter(
    "platform_workflow_runs",
    "Completed multi-agent workflow runs, labelled by outcome.",
    ["outcome"],
)

# Measure how long each agent node takes to run.
AGENT_DURATION = Histogram(
    "platform_agent_duration_seconds",
    "Execution time of each workflow agent.",
    ["agent"],
)

# Record how many enterprise sources each research step returned.
RETRIEVED_SOURCES = Histogram(
    "platform_retrieved_sources",
    "Number of enterprise chunks returned by retrieval per run.",
    buckets=[0, 1, 2, 3, 4, 5, 6, 8, 10, 20],
)

# Count reviewer rejections; a sustained rise means reports are failing quality checks.
REVIEW_REJECTIONS = Counter(
    "platform_review_rejections",
    "Reports rejected by the Reviewer Agent.",
)

# Record the output-evaluation percentage for each completed run.
EVALUATION_PERCENTAGE = Histogram(
    "platform_evaluation_percentage",
    "Output evaluation score as a percentage per run.",
    buckets=[25, 50, 75, 100],
)

# Track how many chunks the knowledge index currently holds.
INDEX_CHUNKS = Gauge(
    "platform_index_chunks",
    "Number of chunks in the enterprise knowledge index.",
)


def timed_agent(name: str):
    """
    Wrap a workflow node so its execution time is recorded.

    Args:
        name:
            Low-cardinality agent label, such as "planner" or "writer".

    Returns:
        A decorator that wraps the node function.
    """

    def decorator(node):

        # Preserve the wrapped function's name and docstring.
        @functools.wraps(node)
        def wrapper(state: dict) -> dict:

            # Start timing before the agent runs.
            start = perf_counter()
            try:
                return node(state)
            finally:
                # Record the duration even when the agent raises an error.
                AGENT_DURATION.labels(agent=name).observe(perf_counter() - start)

        return wrapper

    return decorator


def setup_metrics(app: FastAPI) -> None:
    """
    Add Prometheus instrumentation to a FastAPI application.

    Args:
        app:
            The FastAPI application that should be monitored.

    Returns:
        None. The supplied FastAPI application is configured in place.

    Called by:
        app/main.py
    """

    # Create the Prometheus instrumentation manager.
    instrumentator = Instrumentator(
        excluded_handlers=["/metrics"],
    )

    # Attach HTTP instrumentation to the FastAPI application.
    instrumentator.instrument(app)

    # Expose the collected metrics at GET /metrics for Prometheus to scrape.
    instrumentator.expose(app)
