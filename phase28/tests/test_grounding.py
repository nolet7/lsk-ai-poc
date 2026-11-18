import unittest
from phase28.grounding import GroundingError, allowed_source_ids, validate_grounded_answer


class TestGrounding(unittest.TestCase):
    def setUp(self):
        self.evidence = {"sources": [{"id": "doc1"}, {"id": "doc2"}]}

    def test_authorized_citation(self):
        result = validate_grounded_answer("Fact", ["doc1"], self.evidence)
        self.assertEqual(result["cited_source_ids"], ["doc1"])

    def test_disallowed_citation_is_rejected(self):
        with self.assertRaises(GroundingError):
            validate_grounded_answer("Fact", ["other-tenant"], self.evidence)

    def test_duplicates_fail_closed(self):
        with self.assertRaises(GroundingError):
            allowed_source_ids({"sources": [{"id": "doc1"}, {"id": "doc1"}]})

    def test_no_evidence_is_not_grounded(self):
        with self.assertRaises(GroundingError):
            validate_grounded_answer("Guess", ["doc1"], {"sources": []})
