# ASR Group Commercial AI Enablement — FDE POC

**Independent portfolio simulation only. Not affiliated with, approved by, or deployed for ASR Group.**
**All sample customer records, invoices, amounts, campaigns, outcomes and business hypotheses are fictional.**

## Actual business context

ASR Group markets cane-sugar and specialty sweetener products for grocery, foodservice and industrial customers. Its public brand portfolio includes Domino, C&H, Florida Crystals, Redpath and Tate & Lyle. This POC is about **commercial workflows**: customer account teams, distributor/foodservice relationships, consumer brand marketing and commercial finance—NOT manufacturing equipment or factory reliability.

Sources:
- https://www.asr-group.com/about-us
- https://www.asr-group.com/our-brands
- https://www.asrgroup-professional.com/about-us

## Fictional CTO directive

> As the fictional executive sponsor, commission a repeatable governed AI enablement platform for sales, customer-facing service, marketing and invoice review. Demonstrate grounded answers from existing systems, model-selected tools, safe handoffs and measurable evaluation. Never give the AI power to approve adjustments or execute payments. Establish POC evidence before considering a pilot.

## Workflows and systems

| Team | Actual AI job | Truth source | Controlled action |
|---|---|---|---|
| Sales / account management | Prepare account briefs, identify follow-ups and risks | Synthetic sales CRM-style API | Create pending account-note proposal |
| Marketing | Explain brand campaign performance, suggest experiments | Synthetic campaign API + deterministic CTR and CPA | Create pending campaign-note proposal |
| Finance | Explain invoice-vs-PO-vs-receipt discrepancies | Synthetic three-way match service | Create pending exception review proposal; no payments |

All three business services are standalone repos and can operate without the AI gateway. Their domain calculations remain deterministic and the legacy standalone insight API supports optional OpenAI-compatible inference.

## Current implementation

```text
Employee via private gateway (:8090)
  POST /v1/agent/run
          |
          v
 LangGraph state machine (bounded 3 tool rounds)
          |
          v
 AWS Bedrock Converse / Claude-compatible model (real inference, if enabled)
          |
          v
 Model selects allow-listed tool:
  - list_records(domain)
  - get_insight(domain, record_id)
  - propose_change(domain, record_id, text, reason) [opt-in only]
          |
          v
 Gateway async HTTPX service calls
     |             |             |
 Sales :8101   Marketing :8102   Finance :8103
          |
          v
 Tool facts + trace -> Bedrock -> grounded response
          |
    Independent reviewer approves/rejects outside the model
```

**Enforcement:** The LLM has no credentials to business systems. It calls gateway-mediated Python functions; domain and record-ID validation are enforced in Python. The model cannot directly call reviewer decision endpoints, change finance ledgers or execute payments. `allow_proposals=false` is the default, and even enabled proposals require an independent review. Service headers remain demo-only and spoofable; no production use.

The old `POST /run` report graph is retained as a separate legacy deterministic example; **it is not this new AI agent**.

## EC2 Ubuntu setup without Docker

Requirements: AWS EC2 instance and secured SSH tunnel, Python 3.12, outbound HTTPS, permission to invoke an available model through Bedrock (prefer an **EC2 instance profile** with least-privilege Bedrock permissions; never copy CLI keys to the server). Select an available, supported Bedrock Claude model or inference profile ID in the intended region. Model IDs, region availability and billing vary; no hardcoded assumption about access.

Clone `lsk-ai-poc` on its `poc` branch then run `bash scripts/clone_business_apps.sh`. **Recommended:** copy `.env.business.example` to `.env.business`, set distinct random gateway and business API keys, set `BEDROCK_MODEL_ID` in your shell, then run `bash scripts/start_asr_services.sh` from the central project root. That script creates a separate Python environment and starts all four services on localhost without Docker. Check `.run-asr/*.log`, and stop using `bash scripts/stop_asr_services.sh`. If you already have SQLite files from previous test runs, updating seed JSON does not overwrite those existing records. For manual setup, use a virtual environment:

```bash
python3 -m venv ~/lsk-venv
source ~/lsk-venv/bin/activate
pip install "fastapi>=0.115,<1" "uvicorn>=0.30,<1" "httpx>=0.27,<1" "boto3>=1.35,<2" "langgraph>=1,<2"
```

Start each business service from its **own directory** (in separate terminals or managed systemd services), passing a common strong `DEMO_API_KEY`, port and `APP_DOMAIN`:

```bash
cd ~/lsk-ai-poc/external/lsk-sales-account
DEMO_API_KEY="$DEMO_API_KEY" APP_DOMAIN=sales ~/lsk-venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8101
# Repeat from .../lsk-marketing, APP_DOMAIN=marketing, port 8102
# Repeat from .../lsk-finance, APP_DOMAIN=finance, port 8103
```

From the central repo root start the gateway:

```bash
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID='YOUR_ENABLED_MODEL_OR_INFERENCE_PROFILE_ID'
export GATEWAY_API_KEY='YOUR_PRIVATE_GATEWAY_KEY'
export DEMO_API_KEY='YOUR_PRIVATE_SERVICE_KEY'
python -m uvicorn integrations.gateway:app --host 127.0.0.1 --port 8090
```

Test synthetic data through the gateway (run on server or via SSH port forward):

```bash
curl -H "X-API-Key: $GATEWAY_API_KEY" -H "X-Actor: demo.sales" http://127.0.0.1:8090/v1/apps
curl -X POST http://127.0.0.1:8090/v1/agent/run \
 -H "X-API-Key: $GATEWAY_API_KEY" -H "X-Actor: demo.sales" \
 -H "Content-Type: application/json" \
 -d '{"question":"List the synthetic sales accounts and summarize their commercial follow-up risks."}'
curl -X POST http://127.0.0.1:8090/v1/agent/run \
 -H "X-API-Key: $GATEWAY_API_KEY" -H "X-Actor: demo.finance" \
 -H "Content-Type: application/json" \
 -d '{"question":"Explain invoice inv-1002 and the amount mismatch, without changing any records."}'
```

`allow_proposals` is intentionally omitted (defaults to false). To permit proposal creation in a **separate explicit workflow**, provide `"allow_proposals":true` in the request body. Still no approval or automatic record mutation.

## Tests and limitations

```bash
python -m unittest discover -s tests -p 'test_asr_agent.py' -v
python -m unittest discover -s tests -p 'test_gateway_agent.py' -v
```

Model inference requires valid runtime IAM permissions and enabled access in the actual AWS account. Unit tests mock the model and upstream APIs; they are not live AWS integration tests. The agent is bounded by a maximum of three tool rounds, but does not yet implement per-user/per-record authorization, hard token-budget controls, event telemetry or rigorous grounding evaluations. Do not claim deployments, real customer adoption, measured time savings or actual ASR business integrations.
