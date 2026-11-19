"""P28-10: no boto3 import, AWS credentials, sockets, or live inference."""
import unittest
from unittest.mock import Mock

from phase28.aws_security import (
    RuntimeApproval, RuntimeApprovalRequired, build_invoke_policy,
    create_runtime_client, foundation_model_arn,
)
from phase28.config import AISettings


class TestAwsSecurity(unittest.TestCase):
    def setUp(self):
        self.cfg = AISettings(live_inference=True, live_inference_ack=True,
                              timeout_seconds=15)
        self.client_factory = Mock(return_value=object())
        self.config_factory = Mock(return_value=object())
        self.approval = RuntimeApproval(True, self.cfg.aws_region, self.cfg.model_id)

    def make(self, **kwargs):
        args = dict(approval=self.approval, client_factory=self.client_factory,
                    config_factory=self.config_factory)
        args.update(kwargs)
        return create_runtime_client(self.cfg, **args)

    def test_default_configuration_blocks_before_factory(self):
        with self.assertRaises(RuntimeApprovalRequired):
            create_runtime_client(AISettings(), approval=self.approval,
                                  client_factory=self.client_factory,
                                  config_factory=self.config_factory)
        self.client_factory.assert_not_called()

    def test_approval_required(self):
        with self.assertRaises(RuntimeApprovalRequired):
            self.make(approval=None)
        self.client_factory.assert_not_called()

    def test_wrong_approval_model_blocks(self):
        with self.assertRaises(RuntimeApprovalRequired):
            self.make(approval=RuntimeApproval(True, self.cfg.aws_region, "different"))
        self.client_factory.assert_not_called()

    def test_missing_sdk_injection_blocks(self):
        with self.assertRaises(RuntimeApprovalRequired):
            self.make(client_factory=None)
        self.config_factory.assert_not_called()

    def test_sdk_factory_disables_all_automatic_retries(self):
        obj = self.make()
        self.assertIsNotNone(obj)
        self.config_factory.assert_called_once_with(
            connect_timeout=5, read_timeout=15,
            retries={"mode": "standard", "total_max_attempts": 1})
        self.client_factory.assert_called_once()
        args, kwargs = self.client_factory.call_args
        self.assertEqual(args, ("bedrock-runtime",))
        self.assertEqual(kwargs["region_name"], self.cfg.aws_region)

    def test_policy_scoped_to_exact_model_and_endpoint(self):
        policy = build_invoke_policy(
            region="us-east-1", model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            vpce_id="vpce-0123456789abcdef0")
        stmt = policy["Statement"][0]
        self.assertEqual(stmt["Action"], ["bedrock:InvokeModel"])
        self.assertEqual(stmt["Resource"], [
            "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"])
        self.assertEqual(stmt["Condition"]["StringEquals"]["aws:SourceVpce"],
                         "vpce-0123456789abcdef0")
        self.assertNotIn("*", str(stmt))

    def test_policy_rejects_wildcard_or_inference_profile(self):
        for model in ("*", "arn:aws:bedrock:us-east-1:123:inference-profile/foo", "a/b"):
            with self.subTest(model=model), self.assertRaises(ValueError):
                foundation_model_arn("us-east-1", model)

    def test_policy_rejects_wildcard_endpoint(self):
        for vpce in ("*", "", "vpce-123", "vpce-01234567*"):
            with self.subTest(vpce=vpce), self.assertRaises(ValueError):
                build_invoke_policy(region="us-east-1", model_id="model-id", vpce_id=vpce)

    def test_policy_rejects_invalid_region(self):
        with self.assertRaises(ValueError):
            foundation_model_arn("*", "model-id")


if __name__ == "__main__":
    unittest.main()
