"""TASK P28-05/06/07: actor ACL, no-evidence abstention, read-only guarantee, audit safety."""
import unittest

class ServiceTasks(unittest.TestCase):
    @unittest.skip("TASK P28-06: mock dependencies, assert deny-before-retrieve")
    def test_unauthorized_domain_does_not_retrieve(self):
        pass
    @unittest.skip("TASK P28-07: preserve existing gateway API contracts")
    def test_retrieval_only_does_not_call_model(self):
        pass
