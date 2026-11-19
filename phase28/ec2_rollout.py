"""P28-17: Linux-only, explicit migration from legacy diagnostic layout.

No AWS calls, network access, package installation or service manipulation here.
Operator supplies a stopped service, known-good staged release, and callbacks.
The legacy directory remains available as a recovery backup.
"""
from __future__ import annotations
import os
from pathlib import Path
from phase28.release_manager import ReleaseError, _check_release, _release_path, _switch


def migrate_legacy(root: Path, revision: str, *, restart, probe) -> Path:
    """Convert a legacy `current/` directory to a release link, with restoration.

    Linux only. Must be called under the same exclusive deployment lock as
    phase28.release_manager.main(), with service stopped and no concurrent deploy.
    `restart` and `probe` must raise if the diagnostic service is unhealthy.
    """
    if os.name != "posix":
        raise ReleaseError("Migration requires Linux POSIX filesystem semantics")
    root = Path(root)
    current = root / "current"
    target = _release_path(root, revision)
    backup = root / "legacy-current-backup"
    if current.is_symlink() or not current.is_dir():
        raise ReleaseError("Expected an existing legacy current directory")
    if backup.exists() or backup.is_symlink():
        raise ReleaseError("Backup already present; manual review required")
    _check_release(target)
    if not (root / "venvs" / revision / "bin" / "python").is_file():
        raise ReleaseError("Matching per-release virtualenv is not prepared")
    # Validate before touching the legacy directory; never silently discard it.
    os.replace(current, backup)
    try:
        _switch(root, target)
        restart()
        probe()
    except BaseException as primary:
        try:
            if current.is_symlink():
                current.unlink()
            if current.exists():
                raise ReleaseError("Unexpected current path during recovery")
            os.replace(backup, current)
            restart()
            probe()
        except BaseException as recovery:
            raise ReleaseError("Migration and recovery failed; manual intervention required") from recovery
        raise ReleaseError("Migration failed; legacy directory restored") from primary
    return backup
