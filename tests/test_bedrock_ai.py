import asyncio
import os
import unittest
from unittest.mock import patch
from integrations.bedrock_ai import analyze_with_bedrock, ModelUnavailable

EVIDENCE={"summary":"Three-way match failed","signals":{"matched":False,"invoice_po_delta":120}}

class BedrockAnalysisTests(unittest.TestCase):
    def test_requires_model_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ModelUnavailable):
                asyncio.run(analyze_with_bedrock("finance","inv-1","Why?", EVIDENCE))

    def test_uses_model_and_preserves_evidence(self):
        seen={}
        def fake(model, system, user):
            seen.update({"model":model,"system":system,"user":user})
            return {"output":{"message":{"content":[{"text":"Mismatch is 120; obtain review."}]}}}
        with patch.dict(os.environ, {"BEDROCK_MODEL_ID":"test-model"}, clear=True):
            result=asyncio.run(analyze_with_bedrock("finance","inv-1","Explain mismatch",EVIDENCE,invoke=fake))
        self.assertEqual(result["mode"],"bedrock-llm")
        self.assertEqual(result["evidence"]["signals"]["invoice_po_delta"],120)
        self.assertEqual(result["actions_taken"],[])
        self.assertIn("Explain mismatch",seen["user"])

    def test_invalid_response_fails_closed(self):
        with patch.dict(os.environ, {"BEDROCK_MODEL_ID":"test-model"}, clear=True):
            with self.assertRaises(ModelUnavailable):
                asyncio.run(analyze_with_bedrock("sales","s1","Summarize",EVIDENCE,invoke=lambda *args: {}))
