# TASK 09C — Enterprise RAG and document intelligence

**Gated after Task 08 managed storage and Task 05 identity.** Target specification, not implemented.

## Required pipeline
1. Create approved source registry and S3 versioned raw/quarantine/processed locations with KMS encryption, retention, data ownership, source version and provenance. Never use production customer documents in a synthetic lab.
2. Implement upload/connector ingest: malware scanning, type and length limits, parsing and OCR only where necessary, PII classification, document owner/tenant/security tags and record-level ACL metadata. Require approval before documents become searchable.
3. Generate stable chunk IDs and checksums; tune overlaps and preserve source file/page/chunk. Use approved Bedrock embedding model pinned to ID/version and confirm dimension/pgvector index compatibility.
4. Index in Aurora pgvector **if** validated engine/version/extensions and measured performance; otherwise benchmark OpenSearch and/or Bedrock Knowledge Bases and record ADR. Protect indexes with DB-level tenant partition/RLS where appropriate.
5. Query path: signed user context -> policy decision -> tenant/domain/document ACL prefilter in query -> hybrid lexical/vector (if supported) -> optional reranking -> postfilter defense -> sourced evidence -> model gateway. Do not rely on prompt-only tenant filtering or only filter after retrieving unauthorized text.
6. Test entitlement revocation, deleted documents, updates/reembedding, expired metadata, document injection, irrelevant evidence, empty result, cross-tenant vectors and audit.
7. Add evaluation corpus with at least approved positive/negative retrieval examples. Measure precision@k, recall@k, MRR/nDCG as appropriate, citation exactness, abstention, groundedness, ingest failure and index freshness; establish targets from baseline.

## Evidence
- S3 source/version -> ingestion job -> vector ID -> cited answer trace
- Denied retrieval of other tenant and restricted documents (including direct vector API)
- Revoke/delete changes reflected within approved freshness SLA
- Index rebuild from versioned S3 and embedding migration plan
- Relevance evaluation with measured baseline, latency and cost

**Do not use generated text as the authoritative source of pricing, inventory or invoice calculations.**
