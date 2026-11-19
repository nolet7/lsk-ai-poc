"""P28-18 operator approval/evidence preflight. Offline, read-only, no AWS calls.

An approval *record* is not cryptographic proof or an authorization decision.
Human change-management approval, AWS IAM/SSM controls, and Linux gates must
be enforced independently before an operator runs any command on a host.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

_SHA = re.compile(r"[0-9a-f]{40}\Z")
_ACCOUNT = re.compile(r"[0-9]{12}\Z")
_INSTANCE = re.compile(r"i-[0-9a-f]{8,17}\Z")
_REGION = re.compile(r"[a-z]{2}-[a-z]+-\d\Z")
_CHANGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,79}\Z")

class PreflightRejected(ValueError):
    """Missing, expired or unsafe operator-supplied deployment attestation."""


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise PreflightRejected("Expected ISO-8601 UTC timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PreflightRejected("Invalid approval timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset().total_seconds() != 0:
        raise PreflightRejected("Approval timestamp must be UTC")
    return dt.astimezone(timezone.utc)


def verify_record(record: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, str]:
    """Validate a narrow human attestation and return only non-secret fields.

    Intentionally never checks an AWS host, signature or actual ticket: these
    require separately implemented organization trust and IAM boundaries.
    """
    fields = {"change_id", "operator", "approved_revision", "account_id", "region",
              "instance_id", "approved_at", "expires_at", "mode", "operator_confirmed"}
    if not isinstance(record, Mapping) or set(record) != fields:
        raise PreflightRejected("Approval record has missing or unexpected fields")
    for k, pattern in (("change_id", _CHANGE), ("operator", _CHANGE),
                       ("approved_revision", _SHA), ("account_id", _ACCOUNT),
                       ("region", _REGION), ("instance_id", _INSTANCE)):
        if not isinstance(record[k], str) or not pattern.fullmatch(record[k]):
            raise PreflightRejected(f"Invalid {k}")
    if record["mode"] != "diagnostic-only" or record["operator_confirmed"] is not True:
        raise PreflightRejected("Explicit diagnostic-only operator attestation required")
    issued, expiry = _time(record["approved_at"]), _time(record["expires_at"])
    current = now if now is not None else datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise PreflightRejected("Current timestamp must include timezone")
    current = current.astimezone(timezone.utc)
    if not (issued <= current < expiry and 0 < (expiry - issued).total_seconds() <= 86400):
        raise PreflightRejected("Approval is premature, expired or exceeds 24 hours")
    return {k: record[k] for k in ("change_id", "operator", "approved_revision",
                                     "account_id", "region", "instance_id", "mode")}


def inspect_checkout(checkout: Path, revision: str) -> dict[str, str]:
    """Read-only checkout presence checks, NOT a git/signature trust check."""
    if not _SHA.fullmatch(revision):
        raise PreflightRejected("Revision must be a full lowercase Git SHA")
    checkout = Path(checkout)
    expected = ("phase28/release_manager.py", "phase28/ec2_rollout.py",
                "phase28/container_entry.py", "requirements-p28-13.txt",
                "deploy/aws/phase28_ec2/run-current.sh",
                "deploy/aws/phase28_ec2/prepare-venv.sh")
    if checkout.is_symlink() or any(not (checkout / file).is_file() or
                                    (checkout / file).is_symlink() for file in expected):
        raise PreflightRejected("Required reviewed checkout files missing or linked")
    return {"checkout": str(checkout), "checked_files": str(len(expected))}


def write_evidence(directory: Path, approved: Mapping[str, str], *, now: datetime | None = None) -> Path:
    """Create an exclusive local metadata receipt; no secrets or token contents."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise PreflightRejected("Evidence directory must pre-exist and not be symlinked")
    instant = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    event = {"schema": "phase28-p18-preflight-v1", "kind": "offline-operator-attestation",
             "record": dict(approved), "evaluated_at": instant.isoformat(),
             "status": "record-validated-not-host-authorized"}
    body = (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode()
    digest = hashlib.sha256(body).hexdigest()
    destination = directory / f"p28-preflight-{digest[:20]}.json"
    try:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as file:
            file.write(body)
    except FileExistsError as exc:
        raise PreflightRejected("Evidence receipt already exists") from exc
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Phase 28 change record validator; NOT AWS authorization")
    parser.add_argument("--approval-file", required=True, type=Path)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.approval_file.is_symlink() or args.approval_file.stat().st_size > 8192:
            raise PreflightRejected("Untrusted approval file")
        record = json.loads(args.approval_file.read_text(encoding="utf-8"))
        approved = verify_record(record)
        inspect_checkout(args.checkout, approved["approved_revision"])
        receipt = write_evidence(args.evidence_dir, approved)
    except (PreflightRejected, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Preflight rejected: {exc}\n")
    print(f"Offline record validated; host authorization STILL REQUIRED. Receipt: {receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
