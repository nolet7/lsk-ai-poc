"""Phase 28: fail-closed Bedrock Converse inference adapter.

The injected runtime is intended for offline tests only. Real AWS inference is
intentionally blocked until a tested, shared quota/usage limiter is integrated.
No AWS credentials are read, stored, or passed by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phase28.config import AISettings


class InferenceDisabledError(RuntimeError):
    """Inference is not authorized or real-call safeguards are missing."""


class InferenceResponseError(RuntimeError):
    """The model's response cannot be safely interpreted."""


@dataclass(frozen=True, slots=True)
class InferenceResult:
    text: str
    model_id: str
    input_tokens: int
    output_tokens: int
    stop_reason: str


class BedrockInferenceClient:
    """Offline-testable Bedrock adapter with explicit authorization checks.

    Production calls are NOT enabled by injecting an AWS client: callers must
    integrate rate, daily-use, token-budget and cost controls first, then
    implement a separately reviewed production pathway.
    """

    def __init__(
        self, settings: AISettings, runtime_client: Any | None = None
    ) -> None:
        if not isinstance(settings, AISettings):
            raise TypeError("settings must be an AISettings instance")
        self.settings = settings
        self._runtime_client = runtime_client

    def infer(self, prompt: str) -> InferenceResult:
        """Send one text prompt via an injected Converse-compatible test double.

        This method does not create a boto3 client or access AWS credentials.
        Configuration caps are not runtime budget enforcement.
        """
        if not (self.settings.live_inference and self.settings.live_inference_ack):
            raise InferenceDisabledError("Inference requires two explicit opt-ins")

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a nonempty string")

        if self._runtime_client is None:
            raise InferenceDisabledError(
                "Real AWS inference is blocked until runtime budget controls are implemented"
            )

        response = self._runtime_client.converse(
            modelId=self.settings.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={
                "maxTokens": self.settings.max_output_tokens,
                "temperature": self.settings.temperature,
            },
        )
        return self._parse_response(response)

    def _parse_response(self, response: Any) -> InferenceResult:
        """Validate nested Converse response without including raw data in errors."""
        try:
            if not isinstance(response, dict):
                raise ValueError
            output = response["output"]
            message = output["message"]
            content = message["content"]
            usage = response["usage"]
            reason = response["stopReason"]
            if (
                not isinstance(output, dict)
                or not isinstance(message, dict)
                or not isinstance(content, list)
                or not content
                or not isinstance(usage, dict)
                or not isinstance(reason, str)
                or not reason
            ):
                raise ValueError
            texts = []
            for block in content:
                if not isinstance(block, dict) or not isinstance(block.get("text"), str):
                    raise ValueError
                texts.append(block["text"])
            text = "".join(texts)
            input_tokens = usage["inputTokens"]
            output_tokens = usage["outputTokens"]
            if (
                not text.strip()
                or type(input_tokens) is not int
                or type(output_tokens) is not int
                or input_tokens < 0
                or output_tokens < 0
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError) as exc:
            raise InferenceResponseError("Invalid Bedrock Converse response") from exc

        return InferenceResult(
            text=text,
            model_id=self.settings.model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason=reason,
        )
