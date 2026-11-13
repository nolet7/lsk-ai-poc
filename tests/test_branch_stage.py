"""Branch marker is authoritative: direct uvicorn cannot downgrade identity controls."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from integrations.security import stage

MARKER=Path(__file__).resolve().parents[1]/"integrations"/"release-stage.env"

class StageMarkerTests(unittest.TestCase):
    def test_defaults_to_committed_release_stage(self):
        lines=MARKER.read_text(encoding="utf-8").splitlines()
        expected=next(x.split("=",1)[1] for x in lines if x.startswith("LSK_STAGE="))
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(stage(),expected)

    def test_environment_cannot_downgrade_to_other_stage(self):
        lines=MARKER.read_text(encoding="utf-8").splitlines()
        expected=next(x.split("=",1)[1] for x in lines if x.startswith("LSK_STAGE="))
        different=next(x for x in ("poc","pilot","production") if x != expected)
        with patch.dict(os.environ,{"LSK_STAGE":different},clear=True):
            with self.assertRaises(HTTPException) as exc:
                stage()
        self.assertEqual(exc.exception.status_code,503)
