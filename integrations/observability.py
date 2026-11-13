"""Low-cardinality, privacy-conscious FastAPI Prometheus instrumentation.

Only route templates, methods, status classes and durations are recorded.
No prompts, record IDs, API keys, actor headers or model outputs are logged.
"""
import time
import os
import secrets
from fastapi import Response, Header, HTTPException
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

HTTP_REQUESTS = Counter(
    "lsk_gateway_requests_total", "Gateway requests", ["method","route","status"]
)
HTTP_DURATION = Histogram(
    "lsk_gateway_request_duration_seconds", "Gateway request duration",
    ["method","route"], buckets=(0.01,0.025,0.05,0.1,0.25,0.5,1,2.5,5,10,30)
)
MODEL_CALLS = Counter(
    "lsk_bedrock_calls_total", "Bedrock calls by result", ["result"]
)

def instrument(app):
    @app.middleware("http")
    async def collect_metrics(request, call_next):
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            template = getattr(route, "path", None) or "unmatched"
            if template != "/internal/metrics":
                HTTP_REQUESTS.labels(request.method, template, str(status)).inc()
                HTTP_DURATION.labels(request.method, template).observe(time.perf_counter()-started)

    @app.get("/internal/metrics", include_in_schema=False)
    def metrics(x_metrics_key: str | None = Header(default=None)):
        # Scrape locally with a dedicated key outside POC; never use the gateway key.
        stage = os.getenv("LSK_STAGE", "poc").lower()
        if stage in ("pilot", "production"):
            expected = os.getenv("METRICS_API_KEY", "")
            if not expected:
                raise HTTPException(status_code=503, detail="Metrics access not configured")
            if not x_metrics_key or not secrets.compare_digest(expected, x_metrics_key):
                raise HTTPException(status_code=401, detail="Metrics credentials required")
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
