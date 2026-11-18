
"""Fail-closed AWS Bedrock configuration for Phase 28."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
import re


_REGION = re.compile(
    r"^(?:us|eu|ap|sa|ca|me|af|il)-(?:[a-z]+-)+[1-9][0-9]*$"
)
_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,255}$")

_TRUE = {"true", "1", "yes"}
_FALSE = {"false", "0", "no"}


def _boolean(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in _TRUE:
        return True
    if normalized in _FALSE:
        return False
    raise ValueError(f"{name} must be an explicit boolean")


def _integer(
    value: str, name: str, minimum: int, maximum: int
) -> int:
    try:
        result = int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if not minimum <= result <= maximum:
        raise ValueError(
            f"{name} must be between {minimum} and {maximum}"
        )
    return result


@dataclass(frozen=True, slots=True)
class AISettings:
    aws_region: str = "us-east-1"
    model_id: str = "anthropic.claude-3-5-haiku-20241022-v1:0"
    environment: str = "poc"
    live_inference: bool = False
    max_input_tokens: int = 2048
    max_output_tokens: int = 512
    temperature: float = 0.0
    timeout_seconds: int = 15
    max_requests_per_minute: int = 5
    max_daily_requests: int = 100
    live_inference_ack: bool = False

    def __post_init__(self) -> None:
        if not _REGION.fullmatch(self.aws_region):
            raise ValueError("Invalid AWS region format")

        if (
            not _MODEL.fullmatch(self.model_id)
            or self.model_id.startswith(
                ("arn:", "http:", "https:")
            )
        ):
            raise ValueError("Invalid Bedrock model identifier")

        if self.environment not in {
            "poc", "pilot", "production"
        }:
            raise ValueError(
                "environment must be poc, pilot, or production"
            )

        for name in (
            "live_inference", "live_inference_ack"
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")

        limits = (
            ("max_input_tokens", 1, 8192),
            ("max_output_tokens", 1, 2048),
            ("timeout_seconds", 1, 120),
            ("max_requests_per_minute", 1, 60),
            ("max_daily_requests", 1, 10000),
        )

        for name, minimum, maximum in limits:
            value = getattr(self, name)
            if (
                type(value) is not int
                or not minimum <= value <= maximum
            ):
                raise ValueError(
                    f"{name} must be between "
                    f"{minimum} and {maximum}"
                )

        if (
            isinstance(self.temperature, bool)
            or not isinstance(
                self.temperature, (int, float)
            )
            or not 0 <= self.temperature <= 1
        ):
            raise ValueError(
                "temperature must be between 0 and 1"
            )

        if self.environment == "poc":
            if (
                self.max_input_tokens > 4096
                or self.max_output_tokens > 1024
            ):
                raise ValueError("POC token limits exceeded")

            if (
                self.max_requests_per_minute > 10
                or self.max_daily_requests > 200
            ):
                raise ValueError("POC request budget exceeded")

        if self.live_inference and not self.live_inference_ack:
            raise ValueError(
                "Live inference requires explicit "
                "AI_LIVE_INFERENCE_ACK=true"
            )


def load_settings(
    environ: Mapping[str, str] | None = None,
) -> AISettings:
    """Load validated non-secret configuration.

    When environ is provided, use it exclusively.
    No AWS calls or credential loading occur here.
    """
    source = os.environ if environ is None else environ
    defaults = AISettings()

    def get(name: str, default: object) -> str:
        return source.get(name, str(default))

    return AISettings(
        aws_region=get(
            "AI_AWS_REGION", defaults.aws_region
        ),
        model_id=get(
            "AI_MODEL_ID", defaults.model_id
        ),
        environment=get(
            "AI_ENVIRONMENT", defaults.environment
        ),
        live_inference=_boolean(
            get("AI_LIVE_INFERENCE", "false"),
            "AI_LIVE_INFERENCE",
        ),
        max_input_tokens=_integer(
            get(
                "AI_MAX_INPUT_TOKENS",
                defaults.max_input_tokens,
            ),
            "AI_MAX_INPUT_TOKENS", 1, 8192,
        ),
        max_output_tokens=_integer(
            get(
                "AI_MAX_OUTPUT_TOKENS",
                defaults.max_output_tokens,
            ),
            "AI_MAX_OUTPUT_TOKENS", 1, 2048,
        ),
        temperature=float(
            get("AI_TEMPERATURE", defaults.temperature)
        ),
        timeout_seconds=_integer(
            get(
                "AI_TIMEOUT_SECONDS",
                defaults.timeout_seconds,
            ),
            "AI_TIMEOUT_SECONDS", 1, 120,
        ),
        max_requests_per_minute=_integer(
            get(
                "AI_MAX_REQUESTS_PER_MINUTE",
                defaults.max_requests_per_minute,
            ),
            "AI_MAX_REQUESTS_PER_MINUTE", 1, 60,
        ),
        max_daily_requests=_integer(
            get(
                "AI_MAX_DAILY_REQUESTS",
                defaults.max_daily_requests,
            ),
            "AI_MAX_DAILY_REQUESTS", 1, 10000,
        ),
        live_inference_ack=_boolean(
            get("AI_LIVE_INFERENCE_ACK", "false"),
            "AI_LIVE_INFERENCE_ACK",
        ),
    )
