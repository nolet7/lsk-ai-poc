
"""P28-04: Offline Bedrock adapter with budget enforcement.

Uses the existing P28-02 inference client and P28-03 budget guard.
Does not create AWS clients or load credentials.

This is an in-process lab adapter, NOT a production quota boundary.
"""

from __future__ import annotations

from collections.abc import Callable

from phase28.bedrock_client import (
    BedrockInferenceClient,
    InferenceDisabledError,
    InferenceResult,
)
from phase28.budget import InMemoryInferenceBudget
from phase28.config import AISettings


class BudgetedBedrockAdapter:
    """Reserve resources before inference and reconcile after it.

    estimate_input_tokens must return a conservative upper bound
    on provider-billed input tokens, including any request overhead.
    Never use an unverified approximation for a live deployment.
    """

    def __init__(
        self,
        settings: AISettings,
        client: BedrockInferenceClient,
        budget: InMemoryInferenceBudget,
        *,
        estimate_input_tokens: Callable[[str], int],
    ) -> None:
        if not isinstance(settings, AISettings):
            raise TypeError("settings must be AISettings")

        if not isinstance(client, BedrockInferenceClient):
            raise TypeError(
                "client must be BedrockInferenceClient"
            )

        if not isinstance(budget, InMemoryInferenceBudget):
            raise TypeError(
                "budget must be InMemoryInferenceBudget"
            )

        if not callable(estimate_input_tokens):
            raise TypeError(
                "estimate_input_tokens must be callable"
            )

        # P28-03 does not yet expose a public settings property.
        # Require the exact same validated settings object so
        # configuration cannot diverge across these components.
        if (
            client.settings is not settings
            or budget._settings is not settings
        ):
            raise ValueError(
                "Client and budget must share AISettings"
            )

        self.settings = settings
        self._client = client
        self._budget = budget
        self._estimate_input_tokens = estimate_input_tokens

    def infer(self, prompt: str) -> InferenceResult:
        """Run a budget-controlled inference request."""

        # TASK P28-04.1: Fail closed before reserving budget.
        if not (
            self.settings.live_inference
            and self.settings.live_inference_ack
        ):
            raise InferenceDisabledError(
                "Inference requires explicit authorization"
            )

        # TASK P28-04.2: Validate the prompt.
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(
                "prompt must be a nonempty string"
            )

        # TASK P28-04.3: Obtain a conservative token bound.
        estimated_tokens = self._estimate_input_tokens(prompt)

        if (
            type(estimated_tokens) is not int
            or estimated_tokens < 1
        ):
            raise ValueError(
                "Token estimate must be a positive integer"
            )

        # TASK P28-04.4: Reserve before any inference.
        reservation = self._budget.reserve(
            input_tokens=estimated_tokens,
            output_tokens=self.settings.max_output_tokens,
        )

        try:
            # TASK P28-04.5: Execute the existing client.
            result = self._client.infer(prompt)

        except Exception:
            # Unknown outcomes must not release reserved cost.
            self._budget.settle(
                reservation,
                success=False,
            )
            raise

        # TASK P28-04.6: Validate provider accounting.
        # The client has already parsed the provider response.
        # Budget.settle also verifies usage bounds.
        if result.model_id != reservation.model_id:
            raise ValueError(
                "Response model differs from reserved model"
            )

        # TASK P28-04.7: Reconcile actual provider usage.
        self._budget.settle(
            reservation,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            success=True,
        )

        return result
