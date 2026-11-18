"""Task P28-01 configuration tests. Run: python -m unittest discover -s phase28/tests"""
import unittest
from dataclasses import fields
from phase28.config import AISettings, load_settings


class TestAISettings(unittest.TestCase):
    def test_defaults_are_safe(self):
        settings = load_settings({})
        self.assertEqual(settings.environment, "poc")
        self.assertFalse(settings.live_inference)
        self.assertFalse(settings.live_inference_ack)

    def test_invalid_region(self):
        for region in ("", "us-east", "invalid", "us_east_1"):
            with self.subTest(region=region), self.assertRaises(ValueError):
                load_settings({"AI_AWS_REGION": region})

    def test_invalid_model(self):
        for model in ("", "bad model", "https://example.com"):
            with self.subTest(model=model), self.assertRaises(ValueError):
                load_settings({"AI_MODEL_ID": model})

    def test_invalid_environment(self):
        with self.assertRaises(ValueError):
            load_settings({"AI_ENVIRONMENT": "dev"})

    def test_poc_budget(self):
        for key, value in (("AI_MAX_INPUT_TOKENS", "4097"),
                           ("AI_MAX_OUTPUT_TOKENS", "1025"),
                           ("AI_MAX_REQUESTS_PER_MINUTE", "11"),
                           ("AI_MAX_DAILY_REQUESTS", "201")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                load_settings({key: value})

    def test_invalid_inference_limits(self):
        for key, value in (("AI_MAX_INPUT_TOKENS", "0"),
                           ("AI_TEMPERATURE", "1.5"),
                           ("AI_TIMEOUT_SECONDS", "0"),
                           ("AI_MAX_DAILY_REQUESTS", "abc")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                load_settings({key: value})

    def test_live_inference_requires_two_explicit_flags(self):
        with self.assertRaises(ValueError):
            load_settings({"AI_LIVE_INFERENCE": "true"})
        settings = load_settings({"AI_LIVE_INFERENCE": "true", "AI_LIVE_INFERENCE_ACK": "true"})
        self.assertTrue(settings.live_inference)

    def test_bad_boolean_rejected(self):
        with self.assertRaises(ValueError):
            load_settings({"AI_LIVE_INFERENCE": "maybe"})

    def test_credentials_never_enter_settings(self):
        settings = load_settings({"AWS_ACCESS_KEY_ID": "secret", "AWS_SECRET_ACCESS_KEY": "secret"})
        self.assertFalse(any("credential" in f.name or "secret" in f.name or "access_key" in f.name for f in fields(settings)))
        self.assertNotIn("secret", repr(settings))

    def test_immutable(self):
        settings = load_settings({})
        with self.assertRaises(AttributeError):
            settings.live_inference = True


if __name__ == "__main__":
    unittest.main()
