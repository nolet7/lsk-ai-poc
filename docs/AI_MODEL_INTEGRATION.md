# AI model integration — real Bedrock inference (POC)

## What is and is not AI
- The old `POST /run` LangGraph report workflow is **deterministic** (except SentenceTransformer embeddings). It does not invoke a chat LLM.
- The standalone Sales, Marketing and Finance applications can optionally invoke an OpenAI-compatible chat model if `OPENAI_API_KEY` is configured **in each service's environment**; otherwise `mode=deterministic`.
- The new gateway endpoint `POST /v1/ai/analyze` optionally invokes **AWS Bedrock's Converse API**. It is explicit, read-only, and returns `mode=bedrock-llm` only after a model call succeeds.
- These features are not a production agent system: tool adapters are not part of the legacy LangGraph graph; no autonomous orchestration or verified user identity is implemented.

## Set up on an EC2 instance (without Docker)
Use an EC2 instance profile with narrowly scoped `bedrock:InvokeModel` access to the chosen foundation model or inference profile. The current IAM user may not have it. Confirm model availability, region, any provider onboarding requirements, and costs in the Bedrock console. **AWS credits may not cover all model usage.** No AWS access keys are required on EC2 with a configured role.

```bash
python -m pip install "fastapi>=0.115,<1" "httpx>=0.27,<1" "boto3>=1.35,<2" "uvicorn>=0.30,<1"
export GATEWAY_API_KEY='your-gateway-key'
export DEMO_API_KEY='your-service-key'
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID='YOUR_ENABLED_MODEL_OR_INFERENCE_PROFILE_ID'
python -m uvicorn integrations.gateway:app --host 127.0.0.1 --port 8090
```

Ensure all three upstream business services run locally on 8101, 8102, 8103 with matching `DEMO_API_KEY`. Never expose the demo API to the public internet or send genuine business records to the model. Restrict incoming SSH to your IP and use SSH port forwarding.

Test using a synthetic record ID returned by the service:

```bash
curl -H "X-API-Key: $GATEWAY_API_KEY" -H "X-Actor: demo.employee" \
  http://localhost:8090/v1/apps/finance/records

curl -X POST http://localhost:8090/v1/ai/analyze \
  -H "X-API-Key: $GATEWAY_API_KEY" -H "X-Actor: demo.employee" \
  -H "Content-Type: application/json" \
  -d '{"domain":"finance","record_id":"REPLACE_WITH_VALID_ID","question":"Explain the invoice mismatch and recommended next steps."}'
```

Response differentiates the actual model-generated `answer` from deterministic `evidence` and marks `actions_taken=[]`. Inference errors return HTTP 503; there is no fake model fallback.

## Operational gaps before a genuine pilot
Verified OIDC identity, per-record authorization, prompt injection tests, data classification and PII filtering, output grounding/evals, budgets/token-cost telemetry, structured model output, retries/timeouts/circuit breakers, traces and audit of model invocation, model version policy, user studies and security approval. Current implementation uses synchronous boto3 inside `asyncio.to_thread` for non-blocking FastAPI operation, not native async Bedrock I/O.
