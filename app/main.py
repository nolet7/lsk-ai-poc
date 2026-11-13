"""
FILE PURPOSE: FastAPI Application Entry Point

This file exposes the Production AI Platform as an HTTP API.

It is responsible for:
1. Creating the FastAPI application with a lifespan that warms the model.
2. Registering HTTP and business metrics.
3. Accepting user questions through POST /run, protected by an API key.
4. Running the LangGraph multi-agent workflow and evaluating its output.
5. Reporting liveness (GET /health) and readiness (GET /ready).

Document ingestion is intentionally not run here. Build the index with
`python -m rag.ingest` before starting the API; /ready reports 503 until the
index exists and matches the configured embedding model.

Request flow:
Client -> FastAPI -> PlatformRequest validation -> API key check
       -> LangGraph workflow -> Output evaluation -> PlatformResponse
"""

# Import logging for application-level log configuration.
import logging

# Import asynccontextmanager to define the application lifespan.
from contextlib import asynccontextmanager

# Import uuid to give requests without an ID a correlation ID.
import uuid

# Import Path to expose only the report filename, not the server path.
from pathlib import Path

# Import FastAPI, request helpers, and the error type for HTTP failures.
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# Import the threadpool helper so the model loads without blocking the event loop.
from starlette.concurrency import run_in_threadpool

# Import the project settings.
from config import settings

# Import the API request and response contracts.
from app.schemas import PlatformRequest, PlatformResponse, EvaluationResult

# Import the API key dependency.
from app.security import require_api_key

# Import the function that runs the complete multi-agent LangGraph workflow.
from agents.graph import run_platform

# Import the evaluation function used to assess the completed workflow output.
from evaluation.evaluator import evaluate_output

# Import the metrics setup and business metric instruments.
from monitoring.metrics import (
    EVALUATION_PERCENTAGE,
    INDEX_CHUNKS,
    RETRIEVED_SOURCES,
    setup_metrics,
)

# Import the shared vector store helpers and the readiness exception.
from rag import store
from rag.store import IndexNotReadyError


# Configure logging once for the process; this is a no-op if already configured.
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# Create the module logger for request-level events.
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Prepare shared resources before the API starts serving requests.

    Loads the embedding model so the first request is fast, and seeds the
    index-size metric from the current collection.
    """

    # Load the embedding model in a worker thread so startup does not block the event loop.
    if settings.warmup_model:
        await run_in_threadpool(store.get_embedder)
        logger.info("embedding model loaded: %s", settings.embedding_model)

    # Seed the index-size gauge; an unbuilt index simply reports zero chunks.
    try:
        INDEX_CHUNKS.set(store.get_collection(create=False).count())
    except IndexNotReadyError:
        INDEX_CHUNKS.set(0)

    # Serve requests until shutdown.
    yield


# Create the FastAPI application.
# The title and version appear in generated OpenAPI and Swagger documentation.
app = FastAPI(
    title="Production AI Platform",
    version=settings.app_version,
    lifespan=lifespan,
)

# Register HTTP metrics and the /metrics endpoint.
setup_metrics(app)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    """
    Give every request an ID, log its outcome, and return the ID in a header.

    The ID is also available to routes as request.state.request_id. Unhandled
    exceptions are converted to a 500 here so the response still carries the
    ID an operator needs to find the traceback.
    """

    # Reuse the caller's request ID when present, capped to a safe length.
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)[:64]
    request.state.request_id = request_id

    # Process the request, converting unexpected failures into a logged 500.
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "unhandled error request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )
        response = JSONResponse(status_code=500, content={"detail": "Internal server error."})

    # Attach the identifier and log one access line per request.
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request request_id=%s method=%s path=%s status=%d",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


@app.get("/")
def home() -> dict[str, str]:
    """
    Return a basic message confirming that the API is running.

    Endpoint:
        GET /
    """

    # Return the service name and version for quick manual checks.
    return {
        "message": "Production AI Platform is running",
        "version": settings.app_version,
    }


@app.post(
    "/run",
    response_model=PlatformResponse,
    dependencies=[Depends(require_api_key)],
)
def run(request: PlatformRequest, http_request: Request) -> PlatformResponse:
    """
    Run the complete Production AI Platform for one user question.

    Endpoint:
        POST /run

    Responses:
        200: the workflow finished. Check `status` for approved or rejected.
        401: a key is configured and the X-API-Key header is missing or wrong.
        422: the question is empty, whitespace-only, or too long.
        503: the knowledge index is missing or empty.
    """

    # Run the workflow; the route is synchronous so FastAPI executes it in a threadpool.
    try:
        result = run_platform(request.question)
    except IndexNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Evaluate the completed output and record quality and breadth metrics.
    evaluation = evaluate_output(result)
    EVALUATION_PERCENTAGE.observe(evaluation["percentage"])
    RETRIEVED_SOURCES.observe(len(result["research_context"]))

    # Expose the report only when it passed the quality gate.
    approved = result["approved"]
    report_path = result["report_path"]

    # Link the HTTP request to the workflow run so operators can trace either one.
    logger.info(
        "run completed request_id=%s run_id=%s status=%s",
        http_request.state.request_id,
        result["run_id"],
        result["status"],
    )

    # Return the response contract, omitting unapproved content and server paths.
    return PlatformResponse(
        run_id=result["run_id"],
        status=result["status"],
        question=result["question"],
        plan=result["plan"],
        analysis=result["analysis"],
        review_attempts=result["review_attempts"],
        review_notes=result["review_notes"],
        final_report=result["final_report"] if approved else None,
        report_filename=Path(report_path).name if approved and report_path else None,
        evaluation=EvaluationResult(**evaluation),
    )


@app.get("/health")
def health() -> dict[str, str]:
    """
    Return the API process liveness status.

    Endpoint:
        GET /health

    Note:
        This only confirms the process is up. Use GET /ready to check whether
        the knowledge index is available to serve questions.
    """

    # Return HTTP 200 while the process is serving requests.
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """
    Report whether the knowledge index can serve questions.

    Endpoint:
        GET /ready

    Responses:
        200: the index exists, is non-empty, and was built with the configured model.
        503: the index is missing, empty, or built with a different model.
    """

    # Require an existing index; a missing one means ingestion has not run.
    try:
        collection = store.get_collection(create=False)
    except IndexNotReadyError as exc:
        return JSONResponse(status_code=503, content={"status": "not_ready", "reason": str(exc)})

    # Read the index size and the model that built it.
    chunks = collection.count()
    model = (collection.metadata or {}).get("embedding_model")

    # Refuse to serve when the index is empty or built with a different embedding model.
    if chunks == 0:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "Knowledge index is empty."},
        )
    if model != settings.embedding_model:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": (
                    f"Index was built with {model!r}; "
                    f"expected {settings.embedding_model!r}. Re-run ingestion."
                ),
            },
        )

    # Update the index-size gauge and report readiness.
    INDEX_CHUNKS.set(chunks)
    return {
        "status": "ready",
        "chunks": chunks,
        "embedding_model": model,
    }
