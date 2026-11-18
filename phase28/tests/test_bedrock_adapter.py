"""TASK P28-04: mock Bedrock Converse; cover success, throttle, timeout, malformed reply."""
import unittest

class AdapterTasks(unittest.TestCase):
    @unittest.skip("TASK P28-04: use injected mock, never AWS network in CI")
    def test_mocked_bedrock_response(self):
        pass
