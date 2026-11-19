"""P28-14 fail-closed container entry point.

The real gateway requires trusted OIDC JWKS, storage ACL and audit wiring.
Without them, serve only diagnostics and refuse business requests. This is
NOT the public read-only application endpoint.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException


def create_diagnostic_app() -> FastAPI:
    app = FastAPI(title="LSK Phase28 Deployment Diagnostics", docs_url=None,
                  redoc_url=None, openapi_url=None)

    @app.get("/health/live", include_in_schema=False)
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready", include_in_schema=False)
    async def ready() -> None:
        raise HTTPException(status_code=503, detail="Gateway dependencies not configured")

    @app.post("/v1/business/questions", include_in_schema=False)
    async def business_disabled() -> None:
        raise HTTPException(status_code=503, detail="Gateway unavailable")

    return app


app = create_diagnostic_app()
