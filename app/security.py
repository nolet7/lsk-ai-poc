"""
FILE PURPOSE: API Key Authentication

This file protects workflow endpoints with a shared API key.

When PLATFORM_API_KEY is unset, the check is skipped so local development
works without configuration. Any shared or deployed environment must set it.

Clients send the key in the X-API-Key header. The comparison uses
secrets.compare_digest to avoid leaking the key through response timing.
"""

# Import secrets for a constant-time string comparison.
import secrets

# Import FastAPI helpers for reading headers and returning HTTP errors.
from fastapi import Header, HTTPException, status

# Import the project settings that hold the configured key.
from config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """
    Reject requests whose X-API-Key header does not match the configured key.

    Args:
        x_api_key:
            Value of the X-API-Key request header, if provided.

    Raises:
        HTTPException: 401 when a key is configured and the header is missing or wrong.
    """

    # Skip authentication when no key is configured.
    if settings.api_key is None:
        return

    # Compare in constant time against the configured secret.
    expected = settings.api_key.get_secret_value()
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
