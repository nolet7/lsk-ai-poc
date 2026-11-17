# TASK 09D — LLM serving gateway, governance and AI evaluation

**Gated after Task 05 service IAM and before model-using traffic.** Target specification, not implemented.

## Requirements
1. Create `services/model-gateway/` with a bounded Bedrock Converse interface. Pin approved model or inference profile ID by environment; verify regional support, rights, pricing, model context window and data handling before deployment.
2. Define tasks and candidate models: classification/summarization vs grounded finance explanation; compare approved Amazon Nova/Anthropic Claude or other accessible Bedrock families. Don't fabricate currently available IDs or prices. Use embeddings through an independent versioned client.
3. Implement routing policy with latency, quality and budget thresholds; controlled fallback must **never** circumvent data policy or treat a heuristic response as an LLM result. Preserve explicit 503/abstain semantics when unavailable.
4. Create prompt registry with prompt ID/version, reviewer, test dataset, tool schema/version, model compatibility, rollout percentages and rollback; keep unsafe prompt instructions outside user/tool/doc text.
5. Guard against malicious inputs and untrusted tool results with authorization **before model**, schemas, bounded tool args, Bedrock Guardrails where suitable, output validation and redaction. Guardrails do not replace IAM or ACL.
6. Meter tokens, provider failures, retry latency and estimated spend per tenant/workload; implement quotas, timeouts, concurrency limits, circuit breakers, rate limiting and cache policy only for safe non-sensitive content.
7. Maintain golden evaluation data for finance arithmetic (from deterministic API), factual grounding, citation accuracy, tool-use correctness, negative permission cases, prompt injection, PII leakage, cost and p95 latency.
8. Implement CI quality gates: preflight synthetic tests on every PR, optional approved live Bedrock benchmark in nonprod (controlled spend), prompt/model A/B testing, canary and rollback on regression. Use Bedrock RAG/model evaluation where suitable.
9. Record inference metadata and traces without unapproved prompts or PII; ensure logs, retention and cross-account access are controlled.

## Evidence
- Explicit model version with real invoice-evidence read-only response and source IDs
- Model-unavailable returns transparent error; deterministic service continues to work
- Prompt injection and unauthorized tool attempts blocked; no model-initiated mutation
- Golden dataset baseline + predeclared quality thresholds and failed-regression release
- Token count, latency, cost per task and model fallback/no-fallback decision recorded

**No auto-training from user prompts or customer documents without signed governance approval.**
