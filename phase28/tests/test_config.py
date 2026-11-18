"""TASK P28-01: replace skips with tests for valid config, missing model, invalid limits, region."""
import unittest

class ConfigTasks(unittest.TestCase):
    @unittest.skip("TASK P28-01: implement and assert fail-closed configuration")
    def test_missing_model_disables_live_inference(self):
        pass
