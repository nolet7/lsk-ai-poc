# Production AI Platform: Proof of Concept

A multi-agent retrieval-augmented (RAG) workflow that turns a question into an
approved, saved business report. It is packaged as a FastAPI service with
health and readiness probes, API-key authentication, Prometheus metrics,
alerting rules, a retrieval-quality gate, a container image, and CI.

> **Status: proof of concept.** The agents are deterministic Python. No LLM is
> called yet. Integrating one is the main next step (see [Roadmap](#roadmap)).

---

## Architecture

```text
POST /run (X-API-Key)
     |
     v
Planner -> Researcher --(ChromaDB similarity search)--> enterprise chunks
     |
     v
Analyst --> weighted priority score (40% impact, 40% urgency, 20% risk)
     |
     v
Writer --> Markdown report
     |
     v
Reviewer --+-- approved --------------------------> Save Report --> END
           |
           +-- rejected, retries left --> Writer
           |
           +-- rejected, no retries left --> END (nothing saved)
```

| Layer | Location | Responsibility |
|---|---|---|
| API | `app/` | Validation, auth, readiness, response contract |
| Orchestration | `agents/graph.py` | LangGraph state machine with a bounded review loop |
| Agents | `agents/*.py` | Planner, Researcher, Analyst, Writer, Reviewer, Save Report |
| Tools | `mcp_tools/tools.py` | Retrieval, scoring, and report persistence |
| RAG | `rag/` | Incremental ingestion, shared embedder and store, retrieval |
| Quality | `evaluation/` | Per-run output checks and the offline retrieval gate |
| Observability | `monitoring/` | HTTP metrics plus workflow, agent, and index metrics |
| Settings | `config.py` | All tunables, read from `PLATFORM_*` environment variables |

---

## Quickstart (local, without Docker)

Requires Python 3.11. CPU-only PyTorch keeps the install small.

```bash
python -m venv venv
venv\Scripts\activate            # Windows; use `source venv/bin/activate` elsewhere
pip install -r requirements-dev.txt --extra-index-url https://download.pytorch.org/whl/cpu

cp .env.example .env             # optional; defaults work for local development

python -m rag.ingest             # build the knowledge index (run once, and after editing data/docs)
uvicorn app.main:app --port 8000 # start the API (single worker)
```

Check it is working:

```bash
curl http://127.0.0.1:8000/ready
curl -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{"question": "How should we productionize enterprise RAG?"}'
```

Interactive API docs: <http://127.0.0.1:8000/docs>

The CLI runs the whole pipeline without the server:

```bash
python run_demo.py
```

## Quickstart (Docker Compose)

```bash
docker compose up --build
```

This starts three services in order:

1. `ingest` builds the index into the `chroma-data` volume and exits.
2. `api` starts on <http://localhost:8000> once the index is built and `/health` passes.
3. `prometheus` scrapes `api:8000/metrics` and evaluates the alerting rules, on <http://localhost:9090>.

To require an API key, set `PLATFORM_API_KEY` in your shell or in `.env`.

---

## Configuration

Every setting is read from the environment, with the `PLATFORM_` prefix, or from `.env`.

| Variable | Default | Purpose |
|---|---|---|
| `PLATFORM_API_KEY` | unset | Shared key required in `X-API-Key` for `POST /run`. Unset or blank disables auth. |
| `PLATFORM_LOG_LEVEL` | `INFO` | Application log level |
| `PLATFORM_DOCS_DIR` | `data/docs` | Folder of `.txt` documents to index |
| `PLATFORM_CHROMA_DIR` | `data/chroma_db` | Persistent vector index location |
| `PLATFORM_OUTPUT_DIR` | `data/outputs` | Where approved reports are written |
| `PLATFORM_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding model. Changing it rebuilds the index on the next ingest. |
| `PLATFORM_CHUNK_WORDS` | `500` | Words per chunk. Changing it re-indexes every document. |
| `PLATFORM_TOP_K` | `4` | Chunks returned per question |
| `PLATFORM_MAX_REVIEW_ATTEMPTS` | `2` | Writer→Reviewer cycles before a run stops without saving |
| `PLATFORM_QUESTION_MAX_LENGTH` | `2000` | Longest accepted question, in characters |
| `PLATFORM_WARMUP_MODEL` | `true` | Load the embedding model at API startup |

---

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/` | no | Service name and version |
| GET | `/health` | no | Liveness. The process is up. |
| GET | `/ready` | no | Readiness. The index exists, is non-empty, and matches the configured model. Returns 503 otherwise. |
| POST | `/run` | key if configured | Run the workflow for one question |
| GET | `/metrics` | no | Prometheus metrics. Restrict this at the network layer. |
| GET | `/docs` | no | OpenAPI and Swagger UI |

### `POST /run`

Request:

```json
{ "question": "How should an enterprise deploy governed AI agents?" }
```

Response (approved):

```json
{
  "run_id": "fb9d7db2d51f416d90b1d43a40dcd8c9",
  "status": "approved",
  "question": "How should an enterprise deploy governed AI agents?",
  "plan": ["Understand the user question", "..."],
  "analysis": { "priority_score": { "priority_score": 6.6 }, "key_themes": ["Governance"], "source_count": 3 },
  "review_attempts": 1,
  "review_notes": "Approved. Report passed all required section and length checks.",
  "final_report": "# Production AI Platform Report\n\n...",
  "report_filename": "production_ai_platform_report_20261113_102820_a889007e.md",
  "evaluation": { "scores": { "has_sources": 1, "has_recommendations": 1, "has_review": 1, "length_score": 1 },
                  "total_score": 4, "max_score": 4, "percentage": 100.0, "passed": true }
}
```

A rejected run returns HTTP 200 with `"status": "rejected"`, `"final_report": null`, and
`"report_filename": null`. Rejected drafts are never exposed or saved. Review notes explain why.

| Status | Meaning |
|---|---|
| 200 | The workflow finished. Read `status`. |
| 401 | `PLATFORM_API_KEY` is set and the `X-API-Key` header is missing or wrong. |
| 422 | The question is empty, whitespace-only, or longer than `PLATFORM_QUESTION_MAX_LENGTH`. |
| 503 | The knowledge index is missing or empty. Run `python -m rag.ingest`. |

Every response carries an `X-Request-ID` header. Send your own to correlate logs.

---

## Operations

### Ingestion

`python -m rag.ingest` is an explicit job, not part of API startup, so the API never
writes to the index while serving traffic. It is incremental:

- Unchanged files are skipped, using a content fingerprint.
- Changed files have their chunks replaced.
- Deleted files have their chunks removed.
- A different embedding model triggers a full rebuild.

Run it after editing `data/docs/`. Its output reports the counts:

```text
{'documents_found': 3, 'documents_updated': 0, 'documents_unchanged': 3, 'documents_removed': 0, 'total_chunks': 3}
```

### Retrieval quality gate

```bash
python -m rag.ingest
python -m evaluation.run_eval --min-hit-rate 0.75
```

`evaluation/golden_set.jsonl` holds labelled questions. The gate measures hit@1, the
share of questions whose top result comes from the expected document, and MRR. It
exits with status 1 below the threshold. CI runs it on every change. The sample corpus has
only three documents, so treat this as a regression tripwire, not a quality benchmark. Add
labelled questions from your real corpus before relying on it.

### Metrics

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `http_requests_total`, `http_request_duration_seconds` | counter, histogram | handler, method, status | HTTP traffic and latency (from the instrumentator) |
| `platform_workflow_runs_total` | counter | outcome: approved, rejected, error | Workflow outcomes |
| `platform_agent_duration_seconds` | histogram | agent | Time spent in each agent |
| `platform_retrieved_sources` | histogram | none | Chunks returned per run |
| `platform_review_rejections_total` | counter | none | Reviewer rejections |
| `platform_evaluation_percentage` | histogram | none | Output evaluation score per run |
| `platform_index_chunks` | gauge | none | Chunks in the index |

Labels are deliberately low-cardinality. Questions, run IDs, and file names never appear in labels.

### Alerts

Defined in `prometheus/alerts.yml`:

| Alert | Fires when | Severity |
|---|---|---|
| `AIPlatformDown` | Prometheus cannot scrape the API for 2 min | critical |
| `AIPlatformIndexEmpty` | `platform_index_chunks` is 0 for 5 min | critical |
| `AIPlatformHighErrorRate` | More than 5% of requests are 5xx for 10 min | warning |
| `AIPlatformRunLatencyHigh` | p95 latency of `POST /run` exceeds 10 s for 10 min | warning |
| `AIPlatformReviewRejectionsHigh` | More than 20% of runs are rejected for 30 min | warning |

### Runbook: API is down

1. `docker compose ps` and `docker compose logs api --tail 200`.
2. If the logs show a model download error, confirm the image was built with network access. The model is baked in at build time.
3. Restart with `docker compose restart api`.

### Logs and correlation

Each request logs one `request` line with its `request_id`, method, path, and status.
A `run completed` line links that `request_id` to the workflow's `run_id`. A failed
workflow logs `workflow failed run_id=...` with the traceback. Unexpected errors log
`unhandled error request_id=...`. The client receives the same ID in the `X-Request-ID`
response header, so a user report can be traced to its log lines.

### Runbook: high error rate

1. 503 responses from `/run` mean the index is missing or empty. Check `AIPlatformIndexEmpty` and run ingestion. `/ready` is excluded from this alert.
2. 500 responses are bugs. Take the `X-Request-ID` from the client, search the logs for it, and read the `unhandled error` or `workflow failed` traceback.

### Runbook: slow runs

Find the slow stage first:

```promql
histogram_quantile(0.95, sum by (le, agent) (rate(platform_agent_duration_seconds_bucket[10m])))
```

Only `researcher` does real work: it embeds the question and queries ChromaDB. The
other agents are plain Python and should take milliseconds. If `researcher` is slow,
check CPU limits on the container and confirm `PLATFORM_WARMUP_MODEL=true` so the model
is not loaded on the first request.

### Runbook: rejections rising

Open the `review_notes` of recent rejected runs. A rise usually means the document set changed and a required section cannot be produced. Review the Writer and the report contract before changing thresholds.

### Runbook: index empty

Run `python -m rag.ingest` against the same `PLATFORM_CHROMA_DIR` the API uses. In Compose, `docker compose up ingest` does this.

---

## Development

```bash
ruff check .                          # lint
pytest                                # unit and API tests: fake embedder, no model download
HF_HUB_OFFLINE=1 pytest -m integration  # real model and temporary index
```

| Test file | Covers |
|---|---|
| `tests/test_rag.py` | Chunking, incremental ingestion, re-index on change, model change, retrieval errors |
| `tests/test_agents.py` | Scoring validation, report persistence, analyst, reviewer, retry router |
| `tests/test_workflow.py` | Full workflow: approval, saving, retry cap, missing index |
| `tests/test_api.py` | Readiness gating, validation, auth, rejected-report contract, metrics |
| `tests/test_integration.py` | Real embedder ranking and the golden-set threshold |

Tests never touch `data/`. `tests/conftest.py` copies the corpus and redirects all storage to temporary directories.

### CI

`.github/workflows/ci.yml` runs on every pull request and every push to `main`:

1. **lint-and-test**: `ruff check`, then `pytest`.
2. **retrieval-gate**: integration tests, ingestion, and `run_eval` with the real model.
3. **docker**: builds the image and checks `GET /health` on a running container.

---

## Project layout

```text
.
├── app/                 FastAPI app, schemas, API key auth
├── agents/              LangGraph workflow and the six agents
├── mcp_tools/           Retrieval, scoring, and report-saving tools
├── rag/                 Shared embedder/store, ingestion, retrieval
├── evaluation/          Output evaluator, golden set, retrieval gate
├── monitoring/          Prometheus metrics and per-agent timing
├── prometheus/          Scrape config and alerting rules
├── data/docs/           Sample enterprise documents (input)
├── tests/               Unit, API, workflow, and integration tests
├── config.py            Settings from PLATFORM_* variables
├── Dockerfile           Non-root image with CPU torch and the model baked in
├── docker-compose.yml   ingest → api → prometheus
├── requirements.txt     Pinned runtime lock (resolves for Linux and Windows)
├── requirements-dev.txt Adds pytest and ruff
└── pyproject.toml       Project metadata, dependency floors, and tool config
```

Generated state (`data/chroma_db/`, `data/outputs/`) is not committed.

---

## Known limitations

- **No LLM.** The Writer fills a template and the Analyst scores with keyword rules. Retrying
  a rejected draft therefore produces the same draft. The retry cap prevents an endless loop, but
  retries will not help until the Writer can change its output.
- **Single worker, local vector store.** ChromaDB runs in-process as a local file. Scale by
  running more containers only after moving to a shared vector database.
- **Authentication is one shared key.** There are no per-user identities, quotas, or rate limits.
- **`/metrics` and `/ready` are unauthenticated.** Expose them only to your monitoring network.
- **Small evaluation set.** The golden set has eight questions over three documents.
- **Full-index fingerprint scan on ingest.** Ingestion reads every chunk's metadata to find
  what changed. This is fine for thousands of chunks; a larger corpus needs a manifest table.
- **Reports are local files.** Mount a volume, or replace `save_report_file` with object storage.

## Roadmap

1. Add an LLM behind a provider interface in `agents/writer.py`. Keep the deterministic writer
   as the offline fallback and as the test double.
2. Make the Reviewer check grounding: every recommendation should cite retrieved chunks.
3. Grow the golden set from real questions and add answer-level evaluation.
4. Move the index to a shared vector database before running more than one replica.
5. Add per-user authentication, rate limits, and token and cost metrics.
