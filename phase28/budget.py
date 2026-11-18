"""P28-03: offline, single-process inference budget guard.

This is a teaching/reference guard, not a production distributed quota service.
It performs no AWS calls and never loads credentials. Caller must reserve BEFORE
inference and settle after receiving validated usage; on ambiguous failure,
retain the full reservation rather than assuming the provider did not bill.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from threading import RLock
from time import monotonic
from typing import Callable
from uuid import uuid4

from phase28.config import AISettings


class BudgetExceededError(RuntimeError):
    """An inference request would exceed configured safety limits."""


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Explicit USD rates per 1 million tokens; no guessed cloud pricing."""

    input_per_million_usd: Decimal
    output_per_million_usd: Decimal

    def __post_init__(self) -> None:
        for rate in (self.input_per_million_usd, self.output_per_million_usd):
            if not isinstance(rate, Decimal) or not rate.is_finite() or rate < 0:
                raise ValueError("Pricing must be finite, nonnegative Decimal rates")

    def estimate(self, input_tokens: int, output_tokens: int) -> Decimal:
        for number in (input_tokens, output_tokens):
            if type(number) is not int or number < 0:
                raise ValueError("Token counts must be nonnegative integers")
        return (
            self.input_per_million_usd * input_tokens
            + self.output_per_million_usd * output_tokens
        ) / Decimal(1_000_000)


@dataclass(frozen=True, slots=True)
class Reservation:
    reservation_id: str
    model_id: str
    reserved_input_tokens: int
    reserved_output_tokens: int
    reserved_usd: Decimal


@dataclass(frozen=True, slots=True)
class BudgetSnapshot:
    daily_requests: int
    committed_and_reserved_usd: Decimal
    pending_reservations: int


class InMemoryInferenceBudget:
    """Atomic local quota reservation; not safe across processes or restarts.

    This guard reserves worst-case tokens and USD BEFORE sending a request.
    For a network timeout or unknown completion, call settle(..., success=False)
    to keep the full reservation charged; this is intentionally conservative.
    """

    def __init__(
        self,
        settings: AISettings,
        pricing: ModelPricing,
        max_daily_usd: Decimal,
        *,
        clock: Callable[[], float] = monotonic,
        utcnow: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if not isinstance(settings, AISettings):
            raise TypeError("settings must be AISettings")
        if not isinstance(pricing, ModelPricing):
            raise TypeError("pricing must be ModelPricing")
        if not isinstance(max_daily_usd, Decimal) or not max_daily_usd.is_finite() or max_daily_usd <= 0:
            raise ValueError("max_daily_usd must be a positive finite Decimal")
        self._settings = settings
        self._pricing = pricing
        self._cap = max_daily_usd
        self._clock = clock
        self._utcnow = utcnow
        self._lock = RLock()
        self._minute = deque()
        self._day = None
        self._requests_today = 0
        self._daily_usd = Decimal(0)
        self._pending: dict[str, Reservation] = {}

    def _refresh_day(self) -> None:
        now = self._utcnow()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("utcnow must return an aware datetime")
        today = now.astimezone(timezone.utc).date()
        if self._day is None:
            self._day = today
        elif today != self._day:
            # Do not silently drop unresolved costs spanning the date boundary.
            if self._pending:
                raise BudgetExceededError("Pending reservations must be settled before UTC day rollover")
            self._day = today
            self._requests_today = 0
            self._daily_usd = Decimal(0)

    def reserve(self, input_tokens: int, output_tokens: int) -> Reservation:
        """Reserve budget BEFORE sending to a model; fail closed on any limit."""
        if type(input_tokens) is not int or input_tokens < 1:
            raise ValueError("input_tokens must be a positive integer")
        if type(output_tokens) is not int or output_tokens < 1:
            raise ValueError("output_tokens must be a positive integer")
        if input_tokens > self._settings.max_input_tokens or output_tokens > self._settings.max_output_tokens:
            raise BudgetExceededError("Per-request token limit exceeded")
        estimate = self._pricing.estimate(input_tokens, output_tokens)
        with self._lock:
            self._refresh_day()
            now = self._clock()
            while self._minute and self._minute[0] <= now - 60:
                self._minute.popleft()
            if len(self._minute) >= self._settings.max_requests_per_minute:
                raise BudgetExceededError("Per-minute request limit exceeded")
            if self._requests_today >= self._settings.max_daily_requests:
                raise BudgetExceededError("Daily request limit exceeded")
            if self._daily_usd + estimate > self._cap:
                raise BudgetExceededError("Daily USD budget exceeded")
            reservation = Reservation(str(uuid4()), self._settings.model_id, input_tokens, output_tokens, estimate)
            self._minute.append(now)
            self._requests_today += 1
            self._daily_usd += estimate
            self._pending[reservation.reservation_id] = reservation
            return reservation

    def settle(self, reservation: Reservation, *, input_tokens: int | None = None,
               output_tokens: int | None = None, success: bool = False) -> Decimal:
        """Charge actual usage on success; otherwise retain worst-case charge.

        'success' means a validated provider response with reliable usage. It
        does not mean the application liked the model's answer.
        """
        if not isinstance(reservation, Reservation):
            raise TypeError("reservation must be Reservation")
        with self._lock:
            stored = self._pending.get(reservation.reservation_id)
            if stored is None or stored != reservation:
                raise ValueError("Unknown or already settled reservation")
            if success:
                if type(input_tokens) is not int or type(output_tokens) is not int:
                    raise ValueError("Successful settlement requires integer token counts")
                if not (0 <= input_tokens <= reservation.reserved_input_tokens and
                        0 <= output_tokens <= reservation.reserved_output_tokens):
                    raise BudgetExceededError("Actual usage exceeds reservation; manual review required")
                actual = self._pricing.estimate(input_tokens, output_tokens)
                self._daily_usd -= reservation.reserved_usd - actual
                charged = actual
            else:
                charged = reservation.reserved_usd
            del self._pending[reservation.reservation_id]
            return charged

    def snapshot(self) -> BudgetSnapshot:
        with self._lock:
            self._refresh_day()
            return BudgetSnapshot(self._requests_today, self._daily_usd, len(self._pending))
