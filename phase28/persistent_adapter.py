"""P28-09: single-host, offline Bedrock execution guarded by a SQLite quota ledger.

No AWS client is constructed. The injected BedrockInferenceClient MUST use a
mock runtime in this lab. This is NOT a production or distributed quota guard.
"""
from __future__ import annotations

from collections.abc import Callable

from phase28.bedrock_client import (
    BedrockInferenceClient, InferenceDisabledError, InferenceResult,
)
from phase28.budget import BudgetExceededError
from phase28.config import AISettings
from phase28.persistent_budget import PersistentInferenceBudget


class PersistentBudgetedBedrockAdapter:
    """Persist a worst-case reservation before an injected Converse call.

    For a provider exception or invalid model identity, the entire reserved
    cost remains charged. If reported usage exceeds its reserved upper bound,
    the reservation remains pending for explicit operator reconciliation.

    An externally supplied conservative token bound is required. No character-
    based estimate is safe for live AWS calls; no retries are performed here.
    """

    def __init__(
        self,
        settings: AISettings,
        client: BedrockInferenceClient,
        budget: PersistentInferenceBudget,
        *,
        estimate_input_tokens: Callable[[str], int],
    ) -> None:
        if not isinstance(settings, AISettings):
            raise TypeError("settings must be AISettings")
        if not isinstance(client, BedrockInferenceClient):
            raise TypeError("client must be BedrockInferenceClient")
        if not isinstance(budget, PersistentInferenceBudget):
            raise TypeError("budget must be PersistentInferenceBudget")
        if not callable(estimate_input_tokens):
            raise TypeError("estimate_input_tokens must be callable")
        if client.settings is not settings or budget._settings is not settings:
            raise ValueError("Client, ledger and adapter must share identical settings")
        self.settings = settings
        self._client = client
        self._budget = budget
        self._estimate_input_tokens = estimate_input_tokens

    def infer(self, prompt: str) -> InferenceResult:
        if not (self.settings.live_inference and self.settings.live_inference_ack):
            raise InferenceDisabledError("Inference requires two explicit opt-ins")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be nonempty")
        estimate = self._estimate_input_tokens(prompt)
        if type(estimate) is not int or estimate < 1:
            raise ValueError("Token bound must be a positive integer")

        # Transaction is committed before the first call to the runtime.
        reservation = self._budget.reserve(estimate, self.settings.max_output_tokens)
        try:
            result = self._client.infer(prompt)
        except BaseException:
            # Provider outcome is unknown. Retain the full charge, including on
            # interruption; never automatically retry an ambiguous attempt.
            self._budget.settle(reservation, success=False)
            raise

        # Do not refund if a provider returns a different model identity.
        if not isinstance(result, InferenceResult) or result.model_id != reservation.model_id:
            self._budget.settle(reservation, success=False)
            raise ValueError("Invalid or mismatched model result")

        # Over-budget provider usage is deliberately NOT settled; the existing
        # persistent ledger leaves it pending for manual reconciliation.
        self._budget.settle(
            reservation, success=True,
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        )
        return result
