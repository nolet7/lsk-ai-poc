"""P28-08: replace the legacy skipped adapter test with offline Converse checks."""
import unittest
from unittest.mock import Mock
from phase28.config import AISettings
from phase28.bedrock_client import BedrockInferenceClient, InferenceDisabledError, InferenceResponseError


def reply(text="Approved source response", input_tokens=5, output_tokens=3):
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "usage": {"inputTokens": input_tokens, "outputTokens": output_tokens},
        "stopReason": "end_turn",
    }


class AdapterTasks(unittest.TestCase):
    def setUp(self):
        self.settings = AISettings(live_inference=True, live_inference_ack=True)
        self.runtime = Mock()
        self.runtime.converse.return_value = reply()

    def test_mocked_bedrock_response(self):
        result = BedrockInferenceClient(self.settings, runtime_client=self.runtime).infer("Status?")
        self.assertEqual(result.text, "Approved source response")
        self.assertEqual((result.input_tokens, result.output_tokens), (5, 3))
        self.runtime.converse.assert_called_once()
        kwargs = self.runtime.converse.call_args.kwargs
        self.assertEqual(kwargs["modelId"], self.settings.model_id)
        self.assertEqual(kwargs["inferenceConfig"]["maxTokens"], self.settings.max_output_tokens)

    def test_disabled_blocks_mock_runtime(self):
        client = BedrockInferenceClient(AISettings(), runtime_client=self.runtime)
        with self.assertRaises(InferenceDisabledError):
            client.infer("Status?")
        self.runtime.converse.assert_not_called()

    def test_throttling_error_propagates(self):
        self.runtime.converse.side_effect = RuntimeError("simulated throttle")
        with self.assertRaises(RuntimeError):
            BedrockInferenceClient(self.settings, runtime_client=self.runtime).infer("Status?")

    def test_timeout_propagates(self):
        self.runtime.converse.side_effect = TimeoutError("simulated timeout")
        with self.assertRaises(TimeoutError):
            BedrockInferenceClient(self.settings, runtime_client=self.runtime).infer("Status?")

    def test_malformed_response_fails_closed(self):
        self.runtime.converse.return_value = {"usage": {"inputTokens": 2}}
        with self.assertRaises(InferenceResponseError):
            BedrockInferenceClient(self.settings, runtime_client=self.runtime).infer("Status?")


if __name__ == "__main__":
    unittest.main()
