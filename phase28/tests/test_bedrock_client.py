"""P28-02 acceptance tests. Expected to fail until TODOs are implemented."""
import unittest
from unittest.mock import Mock

from phase28.config import AISettings
from phase28.bedrock_client import (
    BedrockInferenceClient,
    InferenceDisabledError,
    InferenceResponseError,
)


class TestBedrockInferenceClient(unittest.TestCase):
    def test_defaults_fail_closed_without_calling_client(self):
        fake = Mock()
        client = BedrockInferenceClient(AISettings(), runtime_client=fake)
        with self.assertRaises(InferenceDisabledError):
            client.infer("Hello")
        fake.converse.assert_not_called()

    def test_single_flag_cannot_enable_inference(self):
        fake = Mock()
        cfg = AISettings(live_inference_ack=True, live_inference=False)
        with self.assertRaises(InferenceDisabledError):
            BedrockInferenceClient(cfg, runtime_client=fake).infer("Hello")
        fake.converse.assert_not_called()

    def test_empty_prompt_rejected_without_calling_client(self):
        fake = Mock()
        cfg = AISettings(live_inference=True, live_inference_ack=True)
        with self.assertRaises(ValueError):
            BedrockInferenceClient(cfg, runtime_client=fake).infer("   ")
        fake.converse.assert_not_called()

    def test_converse_request_and_response(self):
        fake = Mock()
        fake.converse.return_value = {
            "output": {"message": {"content": [{"text": "Hello!"}]}},
            "usage": {"inputTokens": 4, "outputTokens": 3},
            "stopReason": "end_turn",
        }
        cfg = AISettings(live_inference=True, live_inference_ack=True)
        result = BedrockInferenceClient(cfg, runtime_client=fake).infer("Hello")
        fake.converse.assert_called_once_with(
            modelId=cfg.model_id,
            messages=[{"role": "user", "content": [{"text": "Hello"}]}],
            inferenceConfig={"maxTokens": cfg.max_output_tokens, "temperature": cfg.temperature},
        )
        self.assertEqual(result.text, "Hello!")
        self.assertEqual(result.model_id, cfg.model_id)
        self.assertEqual(result.input_tokens, 4)
        self.assertEqual(result.output_tokens, 3)

    def test_malformed_response_rejected(self):
        fake = Mock()
        fake.converse.return_value = {"output": {}, "usage": {}}
        cfg = AISettings(live_inference=True, live_inference_ack=True)
        with self.assertRaises(InferenceResponseError):
            BedrockInferenceClient(cfg, runtime_client=fake).infer("Hello")


if __name__ == "__main__":
    unittest.main()
