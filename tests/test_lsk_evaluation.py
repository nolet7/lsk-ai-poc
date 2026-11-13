import unittest
from scripts.evaluate_lsk import grade_case

class EvaluationTests(unittest.TestCase):
    def test_passes_verified_evidence(self):
        case={"id":"demo","required_record_ids":["inv-1002"],"forbidden_phrases":["paid"]}
        response={"answer":"Invoice inv-1002 has discrepancy and requires review.",
                  "finish_reason":"completed","proposal_creation_enabled":False,
                  "tool_trace":[{"tool":"get_insight","status":"success","record_id":"inv-1002"}]}
        self.assertTrue(grade_case(case,response,0.5)["passed"])
    def test_rejects_unverified_model_claim(self):
        case={"id":"demo","required_record_ids":["inv-1002"],"forbidden_phrases":[]}
        response={"answer":"Invoice inv-1002 has discrepancy.","finish_reason":"completed",
                  "proposal_creation_enabled":False,"tool_trace":[]}
        self.assertFalse(grade_case(case,response,0.5)["passed"])
    def test_detects_forbidden_claim(self):
        case={"id":"demo","required_record_ids":["inv-1002"],"forbidden_phrases":["invoice paid"]}
        response={"answer":"inv-1002 invoice paid","finish_reason":"completed",
                  "proposal_creation_enabled":False,
                  "tool_trace":[{"tool":"get_insight","status":"success","record_id":"inv-1002"}]}
        self.assertFalse(grade_case(case,response,1.0)["passed"])
