# Security and failure audit

Scope: single authenticated localhost operator with fictional data. This is a developer self-audit, not an independent peer audit or penetration test.

| Concern | Implemented control | Remaining limit |
| --- | --- | --- |
| Unauthorized access | Random private operator key, bounded login attempts, HttpOnly SameSite session | Single role; no organization identity or revocation workflow |
| Cross-site requests / DNS rebinding | Same-origin writes, TrustedHost, no permissive CORS | HTTPS/reverse-proxy deployment needs its own review |
| Secret disclosure | Server-side provider keys; no prompt/output capture in ledger/OTel | Cached answers contain text; local operator/filesystem is trusted |
| Prompt injection | Untrusted-evidence instructions, no action tools, simple input/ingestion quarantine | Regex checks are incomplete; model can still make unsupported claims |
| Invalid citations | Retrieved-ID check, review status, no cache write | Does not check factual entailment |
| Semantic cache leakage | Identity/model/corpus/prompt/source-set scope; conservative eligibility; TTL | Heuristics and high cosine similarity are not general correctness guarantees |
| Retry amplification | One owner per profile, transient classification, attempt/deadline bounds | Proxy internals require their own telemetry |
| Mixed-model output | Fallback only before first content token | Partial answers remain visible and explicitly flagged |
| Thundering herd | Concurrency gate and circuit breaker | Process-local; one worker only |
| Budget races | SQLite atomic reservation and conservative hold for unknown usage | Operator rates need maintenance; not a provider invoice reconciliation tool |
| Slow consumers / cancellation | Bounded queue, heartbeat and producer cancellation | Bytes/tokens already sent cannot be revoked |
| Telemetry outage | Bounded SDK/exporter queues and timeouts | No real Langfuse server outage test on this machine |
| Container privileges | Non-root app container, localhost published ports | Container runtime/image execution still unverified locally |

## Review checklist

- [x] Typed request/document boundaries reject unknown fields and invalid values.
- [x] Provider errors distinguish retryable and permanent failures.
- [x] No hidden scripted fallback in live mode.
- [x] Interrupted streams do not route to a second model.
- [x] Cancellation releases the active request slot and persists an outcome.
- [x] Concurrent paid reservations cannot exceed the configured ledger budget in the tested race.
- [x] Unknown usage retains its reservation across process restart.
- [x] Missing/invalid source citations require review and do not enter response cache.
- [x] Browser text rendering uses textContent rather than rendering model HTML.
- [x] Known instruction-override input is rejected; this is a narrow smoke check only.
- [ ] Independent peer review by another person.
- [ ] Real Redis, self-hosted Langfuse, proxy and vLLM runtime verification.
- [ ] Multi-user/distributed deployment, penetration test and load test.

Do not publish `.runtime/`, `.env`, `.venv`, model weights or operator credentials. Evidence JSON contains only fictional prompts/responses. Review any new evidence before publishing.
