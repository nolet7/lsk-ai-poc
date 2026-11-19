"""Offline release failure injection: no systemd, NGINX, AWS, or Docker."""
import os
import tempfile
import unittest
from pathlib import Path

from phase28.release_manager import ReleaseError, _current, activate, stage


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.base = Path(t.name)
        self.root = self.base / "root"
        self.checkout = self.base / "checkout"
        (self.checkout / "phase28").mkdir(parents=True)
        (self.checkout / "phase28" / "__init__.py").write_text("")
        (self.checkout / "phase28" / "container_entry.py").write_text("app = None\n")
        (self.checkout / "requirements-p28-13.txt").write_text("fastapi\n")
        self.a = "a" * 40
        self.b = "b" * 40
        stage(self.root, self.checkout, self.a)
        stage(self.root, self.checkout, self.b)

    @unittest.skipIf(os.name == "nt", "Linux symlink behavior requires POSIX; verified in Linux CI")
    def test_success_switches_relative_atomic_link(self):
        calls = []
        activate(self.root, self.a, restart=lambda: calls.append("restart"), probe=lambda: calls.append("probe"))
        self.assertEqual(calls, ["restart", "probe"])
        self.assertEqual((self.root / "current").readlink().as_posix(), "releases/" + self.a)

    @unittest.skipIf(os.name == "nt", "Linux symlink behavior requires POSIX; verified in Linux CI")
    def test_probe_failure_rolls_back_and_probes_previous(self):
        activate(self.root, self.a, restart=lambda: None, probe=lambda: None)
        hits = []
        def probe():
            hits.append("probe")
            if hits.count("probe") == 1:
                raise TimeoutError()
        with self.assertRaisesRegex(ReleaseError, "previous release restored"):
            activate(self.root, self.b, restart=lambda: hits.append("restart"), probe=probe)
        self.assertEqual(_current(self.root).name, self.a)
        self.assertEqual(hits.count("restart"), 2)
        self.assertEqual(hits.count("probe"), 2)

    @unittest.skipIf(os.name == "nt", "Linux symlink behavior requires POSIX; verified in Linux CI")
    def test_failed_restart_rolls_back(self):
        activate(self.root, self.a, restart=lambda: None, probe=lambda: None)
        calls = []
        def restart():
            calls.append("restart")
            if len(calls) == 1:
                raise RuntimeError("systemd down")
        with self.assertRaises(ReleaseError):
            activate(self.root, self.b, restart=restart, probe=lambda: None)
        self.assertEqual(_current(self.root).name, self.a)

    @unittest.skipIf(os.name == "nt", "Linux symlink behavior requires POSIX; verified in Linux CI")
    def test_missing_previous_fails_closed_on_error(self):
        with self.assertRaises(ReleaseError):
            activate(self.root, self.a, restart=lambda: None, probe=lambda: (_ for _ in ()).throw(RuntimeError()))
        self.assertFalse((self.root / "current").exists())

    def test_invalid_release_id_never_changes_current(self):
        for value in ("../escape", "A" * 40, "123", "a" * 41):
            with self.subTest(value=value), self.assertRaises(ReleaseError):
                activate(self.root, value, restart=lambda: None, probe=lambda: None)

    def test_existing_release_immutable(self):
        with self.assertRaisesRegex(ReleaseError, "already exists"):
            stage(self.root, self.checkout, self.a)

    @unittest.skipIf(os.name == "nt", "Linux symlink behavior requires POSIX; verified in Linux CI")
    def test_symlink_source_rejected(self):
        (self.checkout / "phase28" / "evil.py").symlink_to(self.checkout / "requirements-p28-13.txt")
        with self.assertRaises(ReleaseError):
            stage(self.root, self.checkout, "c" * 40)

    @unittest.skipIf(os.name == "nt", "Linux symlink behavior requires POSIX; verified in Linux CI")
    def test_untrusted_current_link_rejected(self):
        (self.root / "current").symlink_to("/tmp/other")
        with self.assertRaisesRegex(ReleaseError, "Untrusted"):
            activate(self.root, self.b, restart=lambda: None, probe=lambda: None)

    @unittest.skipIf(os.name == "nt", "Linux symlink behavior requires POSIX; verified in Linux CI")
    def test_rollback_failure_explicit(self):
        activate(self.root, self.a, restart=lambda: None, probe=lambda: None)
        with self.assertRaisesRegex(ReleaseError, "manual intervention"):
            activate(self.root, self.b, restart=lambda: (_ for _ in ()).throw(RuntimeError()), probe=lambda: None)

    def test_source_tests_excluded(self):
        (self.checkout / "phase28" / "tests").mkdir()
        (self.checkout / "phase28" / "tests" / "test_demo.py").write_text("assert False")
        stage(self.root, self.checkout, "c" * 40)
        self.assertFalse((self.root / "releases" / ("c" * 40) / "phase28" / "tests").exists())

if __name__ == "__main__":
    unittest.main()
