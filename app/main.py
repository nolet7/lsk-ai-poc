"""
FILE PURPOSE: FastAPI Application Entry Point

This file exposes the Production AI Platform as an HTTP API.

It is responsible for:
1. Creating the FastAPI application.
2. Registering monitoring metrics.
3. Ingesting RAG documents when the application starts.
4. Accepting user questions through POST /run.
5. Running the LangGraph multi-agent workflow.
6. Evaluating the generated platform output.
7. Returning the report, analysis, review notes, and saved report path.
8. Providing root and health-check endpoints.

Request flow:
Client -> FastAPI -> PlatformRequest validation -> LangGraph workflow
       -> Output evaluation -> JSON response
"""

# Import FastAPI, which creates the web application and API routes.
from fastapi import FastAPI

# Import the request schema used to validate incoming POST /run payloads.
from app.schemas import PlatformRequest

# Import the function that runs the complete multi-agent LangGraph workflow.
from agents.graph import run_platform

# Import the evaluation function used to assess the completed workflow output.
from evaluation.evaluator import evaluate_output

# Import the monitoring setup function that registers application metrics.
from monitoring.metrics import setup_metrics

# Import the RAG ingestion function that loads enterprise documents.
from rag.ingest import ingest_documents


# Create the FastAPI application.
# The title appears in generated OpenAPI and Swagger documentation.
app = FastAPI(title="Production AI Platform")


# Register monitoring and metrics instrumentation with the FastAPI application.
# The exact metrics depend on monitoring.metrics.setup_metrics().
setup_metrics(app)


@app.on_event("startup")
def startup_event() -> None:
    """
    Ingest enterprise documents when the API process starts.

    This prepares the retrieval layer before users submit questions.
    """

    # Load or index the documents used by the RAG retrieval workflow.
    ingest_documents()


@app.get("/")
def home() -> dict[str, str]:
    """
    Return a basic message confirming that the API is running.

    Endpoint:
        GET /
    """

    # Return a small JSON response for users opening the root endpoint.
    return {
        "message": "Production AI Platform is running"
    }


@app.post("/run")
def run(request: PlatformRequest) -> dict:
    """
    Run the complete Production AI Platform for one user question.

    Endpoint:
        POST /run

    Request body example:
        {
            "question": "How should we productionize enterprise RAG?"
        }
    """

    # Send the validated question to the LangGraph multi-agent workflow.
    # The result contains the plan, analysis, report, review decision,
    # and location of the saved report.
    result = run_platform(request.question)

    # Evaluate the completed workflow output for quality or readiness.
    evaluation = evaluate_output(result)

    # Return the most useful workflow fields to the API client.
    return {
        # Echo the submitted question.
        "question": result["question"],

        # Return the ordered execution plan created by the Planner Agent.
        "plan": result["plan"],

        # Return scoring, source count, and detected themes.
        "analysis": result["analysis"],

        # Return the Reviewer Agent's approval or correction notes.
        "review_notes": result["review_notes"],

        # Return the approved Markdown report.
        "final_report": result["final_report"],

        # Return the location where the report was saved.
        "report_path": result["report_path"],

        # Return the separate output-quality evaluation.
        "evaluation": evaluation,
    }


@app.get("/health")
def health() -> dict[str, str]:
    """
    Return the API process health status.

    Endpoint:
        GET /health

    Note:
        This is a basic liveness check. It does not verify the health of the
        RAG index, MCP tools, LangGraph workflow, or external dependencies.
    """

    # Return HTTP 200 with a simple operational status.
    return {
        "status": "ok"
    }
