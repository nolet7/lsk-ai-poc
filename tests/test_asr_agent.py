import asyncio
import os
import unittest
from unittest.mock import patch
from integrations.asr_agent import run_commercial_agent, AgentError

def first(messages, tools, system, model):
    return {"output":{"message":{"role":"assistant","content":[{"toolUse":{
        "toolUseId":"tool-1","name":"get_insight",
        "input":{"domain":"finance","record_id":"inv-1002"}}}]}}}

async def reply(messages, tools, system, model):
    if len(messages)==1:
        return first(messages,tools,system,model)
    assert messages[2]["content"][0]["toolResult"]["status"]=="success"
    return {"output":{"message":{"role":"assistant","content":[{"text":"Invoice inv-1002 differs by $1000; request human review."}]}}}

class Tests(unittest.TestCase):
    def test_real_model_tool_loop(self):
        calls=[]
        async def forward(domain,path,actor,method="GET",payload=None):
            calls.append((domain,path,actor,method))
            return {"summary":"Mismatch","signals":{"invoice_po_delta":1000}}
        with patch.dict(os.environ,{"BEDROCK_MODEL_ID":"fake-test-model"}):
            result=asyncio.run(run_commercial_agent("Explain invoice inv-1002","finance.employee",forward,converse=reply))
        self.assertEqual(result["mode"],"bedrock-langgraph")
        self.assertEqual(result["tool_rounds"],1)
        self.assertEqual(result["finish_reason"],"completed")
        self.assertEqual(calls,[("finance","/v1/records/inv-1002/insight","finance.employee","GET")])

    def test_proposal_not_exposed_unless_allowed(self):
        async def converse(messages,tools,system,model):
            assert "propose_change" not in [t["toolSpec"]["name"] for t in tools]
            return {"output":{"message":{"role":"assistant","content":[{"text":"No changes made."}]}}}
        async def no_call(*args): raise AssertionError("Should not call business tool")
        with patch.dict(os.environ,{"BEDROCK_MODEL_ID":"test"}):
            result=asyncio.run(run_commercial_agent("Review the account","employee",no_call,converse=converse))
        self.assertFalse(result["proposal_creation_enabled"])

    def test_requires_model(self):
        async def no_call(*args): return {}
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(AgentError):
                asyncio.run(run_commercial_agent("What happened?","employee",no_call))

    def test_model_cannot_force_proposal_without_permission(self):
        async def rogue(messages, tools, system, model):
            if len(messages)==1:
                return {"output":{"message":{"role":"assistant","content":[{"toolUse":{
                    "toolUseId":"rogue-1","name":"propose_change",
                    "input":{"domain":"finance","record_id":"inv-1002",
                             "text":"Approve payment","reason":"AI recommendation"}}}]}}}
            return {"output":{"message":{"role":"assistant","content":[{"text":"Not authorized to propose."}]}}}
        calls=[]
        async def forward(*args):
            calls.append(args)
            raise AssertionError("No unauthorized business API call permitted")
        with patch.dict(os.environ,{"BEDROCK_MODEL_ID":"test-model"}):
            result=asyncio.run(run_commercial_agent("Change invoice details","employee",forward,converse=rogue))
        self.assertEqual(calls,[])
        self.assertEqual(result["tool_trace"][0]["status"],"error")
        self.assertFalse(result["proposal_creation_enabled"])
