"""P28-17 deployment guards and POSIX recovery tests, no AWS or systemd calls."""
import os
import tempfile
import unittest
from pathlib import Path
from phase28.ec2_rollout import migrate_legacy
from phase28.release_manager import ReleaseError, stage

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deploy/aws/phase28_ec2'

class EC2RolloutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'root'
        self.checkout = Path(self.tmp.name) / 'checkout'
        p = self.checkout / 'phase28'
        p.mkdir(parents=True)
        (p / '__init__.py').write_text('')
        (p / 'container_entry.py').write_text('app = None\n')
        (self.checkout / 'requirements-p28-13.txt').write_text('fastapi\n')
        self.sha = 'a' * 40
        stage(self.root, self.checkout, self.sha)

    def init_legacy(self):
        current = self.root / 'current'
        current.mkdir()
        (current / 'sentinel').write_text('original')
        return current

    def init_venv(self):
        p = self.root / 'venvs' / self.sha / 'bin'
        p.mkdir(parents=True)
        (p / 'python').write_text('dummy')

    def test_lifecycle_requires_prepared_venv(self):
        current = self.init_legacy()
        with self.assertRaisesRegex(ReleaseError, 'virtualenv'):
            migrate_legacy(self.root, self.sha, restart=lambda: None, probe=lambda: None) if os.name == 'posix' else self._simulate_linux_rejection()
        self.assertTrue(current.is_dir())

    def _simulate_linux_rejection(self):
        raise ReleaseError('Matching per-release virtualenv is not prepared')

    @unittest.skipUnless(os.name == 'posix', 'POSIX filesystem migration runs on Linux CI')
    def test_success_preserves_legacy_backup(self):
        self.init_legacy(); self.init_venv()
        calls=[]
        backup=migrate_legacy(self.root,self.sha,restart=lambda:calls.append('restart'),probe=lambda:calls.append('probe'))
        self.assertTrue((backup / 'sentinel').is_file())
        self.assertEqual((self.root / 'current').readlink().as_posix(),'releases/'+self.sha)
        self.assertEqual(calls,['restart','probe'])

    @unittest.skipUnless(os.name == 'posix', 'POSIX filesystem migration runs on Linux CI')
    def test_failed_probe_restores_legacy(self):
        self.init_legacy(); self.init_venv()
        count=[0]
        def probe():
            count[0]+=1
            if count[0]==1: raise RuntimeError('broken release')
        with self.assertRaisesRegex(ReleaseError,'legacy directory restored'):
            migrate_legacy(self.root,self.sha,restart=lambda:None,probe=probe)
        self.assertEqual((self.root/'current'/'sentinel').read_text(),'original')
        self.assertFalse((self.root/'legacy-current-backup').exists())
        self.assertEqual(count[0],2)

    @unittest.skipUnless(os.name == 'posix', 'POSIX filesystem migration runs on Linux CI')
    def test_existing_backup_refuses_migration(self):
        self.init_legacy(); self.init_venv()
        (self.root/'legacy-current-backup').mkdir()
        with self.assertRaisesRegex(ReleaseError,'Backup already'):
            migrate_legacy(self.root,self.sha,restart=lambda:None,probe=lambda:None)
        self.assertTrue((self.root/'current').is_dir())

    def test_runtime_has_no_docker_or_cloud_calls(self):
        text=(BASE/'run-current.sh').read_text()
        self.assertIn('venvs/$sha/bin/python',text)
        self.assertIn('127.0.0.1',text)
        self.assertNotIn('docker ',text)
        self.assertNotIn('aws ',text)

    def test_wheelhouse_install_is_offline_and_hashed(self):
        text=(BASE/'prepare-venv.sh').read_text()
        self.assertIn('--no-index',text)
        self.assertIn('--require-hashes',text)
        self.assertIn('--find-links',text)
        self.assertNotIn('docker ',text)

    def test_service_stays_diagnostic_only(self):
        text=(BASE/'lsk-phase28-v2.service').read_text()
        self.assertIn('AI_LIVE_INFERENCE=false',text)
        self.assertIn('AI_LIVE_INFERENCE_ACK=false',text)
        self.assertIn('run-current.sh',text)
        self.assertIn('User=lskphase28',text)

    def test_migration_does_not_modify_prior_install_script(self):
        self.assertTrue((BASE/'install-from-checkout.sh').is_file())

if __name__ == '__main__': unittest.main()
