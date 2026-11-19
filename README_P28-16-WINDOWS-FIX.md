# P28-16 Windows test compatibility correction

The EC2 release manager uses Linux POSIX symbolic links and atomic `os.replace` operations. Seven filesystem integration tests require symlink creation; Windows normally raises `WinError 1314` without special privileges. **Do not change the release manager to use Windows junctions or run an elevated shell just for these tests.**

This hotfix changes **only** `phase28/tests/test_release_manager.py`. On native Windows those seven tests report `skipped` (not passed); the three independent tests execute. On Linux (including GitHub Actions ubuntu-latest) all ten tests execute against real symlinks and must pass.

From repository root, after extraction:

```bash
python -m unittest discover -s phase28/tests -p 'test_release_manager.py' -v
python -m unittest discover -s phase28/tests -v
git diff --check
```

Expected on Windows: 10 release tests, 7 skipped, 3 passed. Overall 159 discovered tests, 7 skipped, 152 passed. **Verify the GitHub Actions Linux run is green with all 159 passing before merging or deploying.**

This does not validate the release manager on EC2, systemd recovery, or actual rollback operations. Live model inference stays disabled.
