"""P28-05: SQLite-backed OFFLINE quota ledger for a single-host lab.

No AWS SDK, credentials, model calls, or automatic retry behavior.
SQLite WAL is not suitable for a distributed multi-host Kubernetes quota service.
Use PostgreSQL/Redis with tested transactions for that deployment model.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from phase28.budget import BudgetExceededError, ModelPricing
from phase28.config import AISettings


@dataclass(frozen=True, slots=True)
class LedgerReservation:
    reservation_id: str
    model_id: str
    input_limit: int
    output_limit: int
    reserved_usd: Decimal


@dataclass(frozen=True, slots=True)
class LedgerSnapshot:
    daily_requests: int
    charged_and_reserved_usd: Decimal
    pending: int


class PersistentInferenceBudget:
    """Transactional quota ledger shared by processes on ONE local machine.

    Every reserve and settle uses BEGIN IMMEDIATE to serialize writers.
    Pending requests retain their worst-case reservation across restarts.
    The service rejects day rollover if any earlier request remains pending.
    """

    def __init__(
        self,
        database_path: str | Path,
        settings: AISettings,
        pricing: ModelPricing,
        max_daily_usd: Decimal,
    ) -> None:
        if not isinstance(settings, AISettings):
            raise TypeError("settings must be AISettings")
        if not isinstance(pricing, ModelPricing):
            raise TypeError("pricing must be ModelPricing")
        if (not isinstance(max_daily_usd, Decimal) or
                not max_daily_usd.is_finite() or max_daily_usd <= 0):
            raise ValueError("max_daily_usd must be positive finite Decimal")
        path = Path(database_path)
        if str(path) == ':memory:' or not path.parent.is_dir():
            raise ValueError("database must be an existing local directory path")
        self._path = path
        self._settings = settings
        self._pricing = pricing
        self._cap = max_daily_usd
        conn = self._connect()
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY,
                day TEXT NOT NULL,
                created REAL NOT NULL,
                model TEXT NOT NULL,
                input_limit INTEGER NOT NULL,
                output_limit INTEGER NOT NULL,
                reserved_usd TEXT NOT NULL,
                charged_usd TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending','settled','unknown'))
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS requests_day_idx ON requests(day)")
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), timeout=5, isolation_level=None)
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @staticmethod
    def _now() -> tuple[str, float]:
        return datetime.now(timezone.utc).date().isoformat(), time.time()

    @staticmethod
    def _total(rows: list[tuple[str]]) -> Decimal:
        return sum((Decimal(value) for (value,) in rows), Decimal(0))

    def reserve(self, input_tokens: int, output_tokens: int) -> LedgerReservation:
        if type(input_tokens) is not int or not 1 <= input_tokens <= self._settings.max_input_tokens:
            raise BudgetExceededError("Invalid or excessive input token reservation")
        if type(output_tokens) is not int or not 1 <= output_tokens <= self._settings.max_output_tokens:
            raise BudgetExceededError("Invalid or excessive output token reservation")
        estimate = self._pricing.estimate(input_tokens, output_tokens)
        day, now = self._now()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM requests WHERE day != ? AND status = 'pending' LIMIT 1", (day,)).fetchone():
                raise BudgetExceededError("Previous-day pending request requires reconciliation")
            if conn.execute("SELECT 1 FROM requests WHERE day > ? LIMIT 1", (day,)).fetchone():
                raise BudgetExceededError("System date moved backwards")
            today_count = conn.execute("SELECT COUNT(*) FROM requests WHERE day = ?", (day,)).fetchone()[0]
            minute_count = conn.execute("SELECT COUNT(*) FROM requests WHERE created > ?", (now - 60,)).fetchone()[0]
            spent = self._total(conn.execute("SELECT charged_usd FROM requests WHERE day = ?", (day,)).fetchall())
            if today_count >= self._settings.max_daily_requests:
                raise BudgetExceededError("Daily request limit exceeded")
            if minute_count >= self._settings.max_requests_per_minute:
                raise BudgetExceededError("Rolling minute request limit exceeded")
            if spent + estimate > self._cap:
                raise BudgetExceededError("Daily USD cap exceeded")
            rid = str(uuid4())
            conn.execute("""INSERT INTO requests
                (id, day, created, model, input_limit, output_limit,
                 reserved_usd, charged_usd, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
                (rid, day, now, self._settings.model_id, input_tokens,
                 output_tokens, str(estimate), str(estimate)))
            conn.commit()
            return LedgerReservation(rid, self._settings.model_id, input_tokens, output_tokens, estimate)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def settle(self, reservation: LedgerReservation, *, success: bool = False,
               input_tokens: int | None = None, output_tokens: int | None = None) -> Decimal:
        if not isinstance(reservation, LedgerReservation):
            raise TypeError("Expected LedgerReservation")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""SELECT model, input_limit, output_limit,
                reserved_usd, status FROM requests WHERE id = ?""",
                (reservation.reservation_id,)).fetchone()
            if row is None or row != (reservation.model_id, reservation.input_limit,
                                     reservation.output_limit, str(reservation.reserved_usd), 'pending'):
                raise ValueError("Unknown, forged, or already settled reservation")
            if success:
                if (type(input_tokens) is not int or type(output_tokens) is not int or
                    not 0 <= input_tokens <= reservation.input_limit or
                    not 0 <= output_tokens <= reservation.output_limit):
                    raise BudgetExceededError("Usage exceeds reservation; manual reconciliation needed")
                charged = self._pricing.estimate(input_tokens, output_tokens)
                status = 'settled'
            else:
                charged = reservation.reserved_usd
                status = 'unknown'
            conn.execute("UPDATE requests SET charged_usd = ?, status = ? WHERE id = ?",
                         (str(charged), status, reservation.reservation_id))
            conn.commit()
            return charged
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def snapshot(self) -> LedgerSnapshot:
        day, _ = self._now()
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            count = conn.execute("SELECT COUNT(*) FROM requests WHERE day = ?", (day,)).fetchone()[0]
            spent = self._total(conn.execute("SELECT charged_usd FROM requests WHERE day = ?", (day,)).fetchall())
            pending = conn.execute("SELECT COUNT(*) FROM requests WHERE status = 'pending'").fetchone()[0]
            conn.commit()
            return LedgerSnapshot(count, spent, pending)
        finally:
            conn.close()
