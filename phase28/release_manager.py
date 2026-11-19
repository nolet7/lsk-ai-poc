"""P28-16: Dockerless, diagnostic-only, single-instance release switching.

No AWS calls, network access, package installation or inference. The operator
prepares approved releases separately. Activation is serialized with flock.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

_RELEASE = re.compile(r"^[0-9a-f]{7,40}$")


class ReleaseError(RuntimeError):
    pass


def _valid_release(release_id: str) -> str:
    if not isinstance(release_id, str) or not _RELEASE.fullmatch(release_id):
        raise ReleaseError("Release ID must be a 7-40 character lowercase Git SHA")
    return release_id


def _release_path(root: Path, release_id: str) -> Path:
    return root / "releases" / _valid_release(release_id)


def _check_release(directory: Path) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise ReleaseError("Approved release directory missing")
    if not (directory / "phase28/container_entry.py").is_file() or not (directory / "phase28/__init__.py").is_file():
        raise ReleaseError("Release is missing diagnostic application")
    if not (directory / "requirements-p28-13.txt").is_file():
        raise ReleaseError("Release is missing dependency manifest")
    for p in directory.rglob("*"):
        if p.is_symlink():
            raise ReleaseError("Release cannot contain symlinks")


def _current(root: Path) -> Path | None:
    current = root / "current"
    if not current.is_symlink():
        if current.exists():
            raise ReleaseError("Existing non-symlink current directory: migrate manually")
        return None
    # No traversal and no symlink chain: target must be exactly releases/<sha>
    target = os.readlink(current)
    if not re.fullmatch(r"releases/[0-9a-f]{7,40}", target):
        raise ReleaseError("Untrusted current link")
    selected = root / target
    _check_release(selected)
    return selected


def stage(root: Path, checkout: Path, release_id: str) -> Path:
    """Stage reviewed sources; caller must independently verify revision/signature.

    No pip invocation. Only .py files from phase28 and a requirements manifest
    are copied; tests excluded. Reject symlinks and filesystem escape.
    """
    root = Path(root)
    checkout = Path(checkout)
    destination = _release_path(root, release_id)
    if destination.exists() or destination.is_symlink():
        raise ReleaseError("Release already exists: immutable releases only")
    source = checkout / "phase28"
    requirements = checkout / "requirements-p28-13.txt"
    if source.is_symlink() or not source.is_dir() or requirements.is_symlink() or not requirements.is_file():
        raise ReleaseError("Checkout is incomplete")
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ReleaseError("Source contains symlink")
    files = [p for p in source.rglob("*.py") if "tests" not in p.relative_to(source).parts]
    if not files:
        raise ReleaseError("Source missing or contains symlink")
    (root / "releases").mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".staging-", dir=root / "releases"))
    try:
        for src in files:
            rel = src.relative_to(source)
            out = tmp / "phase28" / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out)
        shutil.copyfile(requirements, tmp / "requirements-p28-13.txt")
        _check_release(tmp)
        for p in tmp.rglob("*"):
            p.chmod(0o755 if p.is_dir() else 0o644)
        tmp.chmod(0o755)
        os.replace(tmp, destination)
        return destination
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


def _switch(root: Path, release: Path) -> None:
    target = f"releases/{release.name}"
    link = root / f".current-next-{os.getpid()}"
    if link.exists() or link.is_symlink():
        raise ReleaseError("Temporary release link already present")
    try:
        link.symlink_to(target)
        os.replace(link, root / "current")
    finally:
        if link.is_symlink():
            link.unlink()


def activate(root: Path, release_id: str, *, restart, probe) -> str:
    """Atomic symlink switch, restart, health check; restore on failure.

    restart() must restart systemd and raise on failure.
    probe() must verify /health/live==200, /health/ready==503,
    and business endpoint unavailable. A failed new release triggers rollback.
    This isn't distributed/transactional: a power cut during restart requires
    operator reconciliation; never delete prior releases automatically.
    """
    root = Path(root)
    destination = _release_path(root, release_id)
    _check_release(destination)
    previous = _current(root)
    if previous == destination:
        raise ReleaseError("Release is already active")
    _switch(root, destination)
    try:
        restart()
        probe()
    except BaseException as primary:
        try:
            if previous is None:
                (root / "current").unlink()
            else:
                _switch(root, previous)
            restart()
            if previous is not None:
                probe()
        except BaseException as rollback_failure:
            raise ReleaseError("Activation failed; automatic recovery failed; manual intervention required") from rollback_failure
        raise ReleaseError("Activation failed; previous release restored") from primary
    return destination.name


def _checked(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, timeout=30)


def _diagnostic_probe() -> None:
    from urllib.error import HTTPError, URLError
    from urllib.request import urlopen, Request
    from time import sleep

    base = "http://127.0.0.1:18080"
    for attempt in range(15):
        try:
            with urlopen(base + "/health/live", timeout=2) as resp:
                if resp.status != 200:
                    raise ReleaseError("Liveness must be HTTP 200")
            for path, method in (("/health/ready", "GET"), ("/v1/business/questions", "POST")):
                try:
                    request = Request(base + path, data=b"{}" if method == "POST" else None, method=method)
                    urlopen(request, timeout=2)
                except HTTPError as e:
                    if e.code not in (403, 503):
                        raise ReleaseError("Diagnostic endpoint did not fail closed") from e
                else:
                    raise ReleaseError("Diagnostic endpoint became available")
            return
        except (URLError, TimeoutError):
            if attempt == 14:
                raise ReleaseError("Diagnostic endpoint unavailable")
            sleep(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="LSK Phase28 diagnostic-only release manager")
    parser.add_argument("command", choices=("stage", "activate", "rollback", "status"))
    parser.add_argument("--root", type=Path, default=Path("/opt/lsk-phase28"))
    parser.add_argument("--revision")
    parser.add_argument("--checkout", type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Run only as root on the approved EC2 host")
    args.root.mkdir(parents=True, exist_ok=True)
    import fcntl  # Linux-only: import lazily so offline Windows tests work.
    with (args.root / ".release-lock").open("a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        if args.command == "status":
            p = _current(args.root)
            print(p.name if p else "none")
        elif args.command == "stage":
            if not args.checkout or not args.revision:
                parser.error("stage requires --checkout and --revision")
            # Git must be clean and exactly the approved commit.
            revision = _valid_release(args.revision)
            actual = subprocess.run(["git", "-C", str(args.checkout), "rev-parse", "HEAD"],
                                    check=True, capture_output=True, text=True, timeout=10).stdout.strip()
            dirty = subprocess.run(["git", "-C", str(args.checkout), "status", "--porcelain", "--untracked-files=normal"],
                                   check=True, capture_output=True, text=True, timeout=10).stdout.strip()
            if len(revision) != 40 or actual != revision or dirty:
                raise ReleaseError("Checkout must match a full approved SHA and be clean")
            print(stage(args.root, args.checkout, revision))
        elif args.command == "activate":
            if not args.revision:
                parser.error("activate requires --revision")
            print(activate(args.root, args.revision,
                           restart=lambda: _checked(["systemctl", "restart", "lsk-phase28.service"]),
                           probe=_diagnostic_probe))
        else:
            if not args.revision:
                parser.error("rollback requires an explicitly approved previous --revision")
            print(activate(args.root, args.revision,
                           restart=lambda: _checked(["systemctl", "restart", "lsk-phase28.service"]),
                           probe=_diagnostic_probe))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
