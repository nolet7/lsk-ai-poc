# LSK Enterprise AI Enablement — Controlled Pilot Scaffold

> **NOT AN APPROVED PILOT DEPLOYMENT.** LSK-inspired commercial portfolio simulation with synthetic records only. No verified corporate identity, actual user pilot, or production business integration exists. Review [release gates](docs/RELEASE_AUDIT.md) and [commercial AI implementation](docs/ASR_COMMERCIAL_AI.md). The Bedrock/LangGraph agent is available for **read-only evaluation** when model access is configured; demo writes/review endpoints are disabled. Pilot promotion requires verified OIDC/RBAC, evaluation outcomes and business signoff.


## Integrated business applications (Sales · Marketing · Finance)

Three standalone [GitHub applications](docs/INTEGRATION.md) now connect through a common asynchronous enterprise gateway:

| Application | Repository | Employee portal |
|---|---|---|
| Sales Account Intelligence | [lsk-sales-account](https://github.com/nolet7/lsk-sales-account) | http://localhost:8101/portal |
| Marketing Intelligence | [lsk-marketing](https://github.com/nolet7/lsk-marketing) | http://localhost:8102/portal |
| Finance Invoice Review | [lsk-finance](https://github.com/nolet7/lsk-finance) | http://localhost:8103/portal |

From this repository root, run `bash scripts/clone_business_apps.sh`, copy `.env.business.example` to `.env.business`, set separate strong demo keys, and run `docker compose --env-file .env.business -f compose.business.yml up --build`. Visit http://localhost:8090 for the hub.

See [integration architecture and API contract](docs/INTEGRATION.md) and [async agent tool adapters](docs/AGENT_CONNECTORS.md).

**Portfolio POC only:** Synthetic records, demo shared API keys, spoofable reviewer-role headers and local storage. These integrations have not completed production security, identity, deployment, or business-adoption gates.

---


## Purpose

This project demonstrates a multi-agent enterprise AI workflow built with
LangGraph and MCP-style tools. It turns a user question into an approved,
saved business report.

## Workflow

```text
User Question
     |
     v
Planner
     |
     v
Researcher ----> Enterprise Knowledge Search
     |
     v
Analyst -------> Business Priority Score
     |
     v
Writer
     |
     v
Reviewer
  | approved                 | rejected
  v                          |
Save Report <----------------+
     |
     v
END
```

## Files

### `graph.py`

The main orchestration file. It defines shared state, registers all agents,
connects the workflow, routes reviewer decisions, and runs the graph.

### `agents/planner.py`

Creates the ordered execution plan.

### `agents/researcher.py`

Searches enterprise knowledge using `search_enterprise_knowledge()`.

### `agents/analyst.py`

Detects business and platform themes and calls
`calculate_business_score()`.

### `agents/writer.py`

Creates the structured Markdown report.

### `agents/reviewer.py`

Checks required sections and report length, then approves or rejects the
report.

### `agents/save_report.py`

Saves the approved report with `save_report_file()`.

## Required MCP tool functions

The project expects `mcp_tools/tools.py` to provide:

```python
search_enterprise_knowledge(question)
calculate_business_score(impact, urgency, risk)
save_report_file(title, content)
```

## Dependency

```bash
pip install langgraph
```

## Example

```python
from graph import run_platform

result = run_platform(
    "How should we build a production enterprise RAG platform?"
)

print(result["approved"])
print(result["review_notes"])
print(result["report_path"])
```

## Corrections included

Two execution problems in the original files were corrected:

1. `reviewer_agent()` now returns the updated state.
2. `writer_agent()` populates `final_report` before the save step.

## Current limitation

When a report is rejected, the graph routes it back to the Writer Agent, but
the Writer Agent does not yet use `review_notes` to revise specific problems.
A retry counter should also be added before production use.

## FastAPI application layer

The updated package also includes:

```text
app/
├── __init__.py
├── main.py
└── schemas.py
```

### `app/main.py`

Creates the FastAPI service, registers monitoring, loads RAG documents at
startup, runs the LangGraph workflow through `POST /run`, evaluates the output,
and exposes root and health endpoints.

### `app/schemas.py`

Defines the Pydantic request and response contracts used for validation,
OpenAPI documentation, and consistent client integration.

### Run the API

```bash
uvicorn app.main:app --reload
```

### Example request

```bash
curl -X POST "http://127.0.0.1:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"question":"How should we productionize enterprise RAG?"}'
```

### Available endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Confirms the platform is running |
| POST | `/run` | Executes the multi-agent workflow |
| GET | `/health` | Basic API liveness check |

The API expects the additional project modules referenced by `app/main.py`:
`evaluation.evaluator`, `monitoring.metrics`, and `rag.ingest`.

## Output evaluation layer

The project now includes:

```text
evaluation/
├── __init__.py
└── evaluator.py
```

### `evaluation/evaluator.py`

Performs deterministic post-workflow quality checks. It verifies that
enterprise sources were retrieved, recommendations exist, reviewer feedback
was produced, and the report is sufficiently detailed.

The evaluator returns:

```json
{
  "scores": {
    "has_sources": 1,
    "has_recommendations": 1,
    "has_review": 1,
    "length_score": 1
  },
  "total_score": 4,
  "max_score": 4,
  "percentage": 100.0,
  "passed": true
}
```

### Evaluation correction

The original evaluator checked whether the words `Reviewer Notes` appeared
inside `final_report`. Reviewer feedback is actually stored in the separate
`review_notes` state field, so the updated evaluator checks that field directly.

## MCP-style tools layer

The project now includes:

```text
mcp_tools/
├── __init__.py
└── tools.py
```

### `mcp_tools/tools.py`

Provides the reusable functions called by the multi-agent workflow:

- `search_enterprise_knowledge(query)` calls the RAG retriever.
- `calculate_business_score(impact, urgency, risk)` calculates a weighted
  priority score using 40% impact, 40% urgency, and 20% risk.
- `save_report_file(title, content)` saves an approved Markdown report under
  `data/outputs/`.

### Validation and safety improvements

The commented version also:

- Validates business-score values as integers between 0 and 10.
- Rejects empty report titles and content.
- Normalizes filenames using cross-platform-safe characters.
- Adds a fallback filename when normalization removes the complete title.
- Uses timestamps to reduce report filename collisions.

## Prometheus monitoring layer

The project now includes:

```text
monitoring/
├── __init__.py
└── metrics.py
```

### `monitoring/metrics.py`

Configures Prometheus-compatible HTTP metrics for the FastAPI application using
`prometheus-fastapi-instrumentator`.

The application calls:

```python
setup_metrics(app)
```

during FastAPI initialization. The function:

1. Creates an `Instrumentator`.
2. Instruments the FastAPI application.
3. Exposes the collected metrics through the application.

### Install the dependency

```bash
pip install prometheus-fastapi-instrumentator
```

### Prometheus configuration example

```yaml
scrape_configs:
  - job_name: production-ai-platform
    metrics_path: /metrics
    static_configs:
      - targets:
          - production-ai-platform:8000
```

### Operational use

The collected HTTP metrics can support:

- API request-rate dashboards
- Response-status monitoring
- Request-latency analysis
- Availability alerts
- Error-rate alerts
- SLO and error-budget reporting

The current file configures standard HTTP instrumentation. Business metrics
such as agent execution duration, retrieval failures, evaluation scores,
token usage, and report approvals should be added separately.

## RAG ingestion and retrieval layer

The project now includes:

```text
rag/
├── __init__.py
├── ingest.py
└── retriever.py
```

### `rag/ingest.py`

Loads `.txt` files from `data/docs`, splits them into 500-word chunks, creates
embeddings with `all-MiniLM-L6-v2`, and upserts the chunks into the persistent
ChromaDB collection named `enterprise_knowledge`.

### `rag/retriever.py`

Embeds a user question with the same sentence-transformer model, queries
ChromaDB for the most similar chunks, and returns normalized records containing
the chunk ID, source filename, and retrieved text.

### Install dependencies

```bash
pip install chromadb sentence-transformers
```

### Expected data structure

```text
data/
├── docs/
│   ├── governance.txt
│   ├── architecture.txt
│   └── operations.txt
├── chroma_db/
└── outputs/
```

### Manual ingestion

```bash
python -m rag.ingest
```

### Retrieval example

```python
from rag.retriever import retrieve_context

results = retrieve_context(
    "How should human approval be added to production AI workflows?",
    top_k=4,
)

for item in results:
    print(item["source"])
    print(item["text"])
```

### Important design notes

- Ingestion and retrieval must use the same embedding model.
- The current chunking strategy uses fixed word counts and no overlap.
- Only `.txt` files are ingested.
- The embedding model is loaded when each module is imported.
- ChromaDB is configured as a local persistent vector database.
- Production systems should add document-version tracking, deletion handling,
  access controls, retrieval evaluation, source citations, and readiness checks.

## Command-line end-to-end demo

The project now includes:

```text
run_demo.py
```

### What `run_demo.py` does

The demo runner executes the full platform without starting FastAPI:

```text
Enterprise documents
    -> RAG ingestion
    -> LangGraph agents
    -> Report review
    -> Report persistence
    -> Output evaluation
    -> Terminal summary
```

### Run the demo

From the project root:

```bash
python run_demo.py
```

### Expected prerequisites

Before running the demo:

1. Add `.txt` documents under `data/docs/`.
2. Install the project dependencies.
3. Ensure ChromaDB can write to `data/chroma_db/`.
4. Ensure the report process can write to `data/outputs/`.

### Example terminal flow

```text
Ingesting documents...
Ingestion result: {'documents_indexed': 6}

Running production AI platform...

Evaluating output...

Production AI Platform Complete
-------------------------------
Question: How should an enterprise deploy governed AI agents...
Report saved to: data/outputs/production_ai_platform_report_....md
Review notes: Approved. Report is complete and portfolio-ready.
Evaluation: {...}
```

### Why this file is useful

`run_demo.py` is the simplest way to verify that the following pieces work
together:

- SentenceTransformer embeddings
- ChromaDB persistence
- Enterprise retrieval
- LangGraph agent orchestration
- Business scoring
- Markdown report generation
- Reviewer approval
- Output evaluation
- Report file persistence

