# Validation evidence

Local validation date: 27 October 2026. Test results and JSON artifacts describe executed checks, not intended behavior. No cloud API calls or production traffic were used.

The browser screenshot `evidence/dashboard-live.png` shows the final live-model request recovering from an injected primary timeout, with retrieved source IDs and the request timeline. Cold embedding startup is included in its displayed latency.

## What ran

- Python 3.12, macOS Apple Silicon; actual Ollama `qwen3:1.7b` inference.
- Real `all-MiniLM-L6-v2` sentence embeddings, BM25/reciprocal-rank hybrid retrieval and LangGraph state execution.
- SQLite semantic response caching with actual embeddings, namespace separation and TTL.
- Async SSE through the real HTTP API and browser, including a live-model answer with source IDs.
- Automated failure-path/API checks and official Langfuse SDK nested-span export to an in-memory exporter.
- Actual native LiteLLM 1.106.4 proxy: primary pointed to a closed localhost port, secondary routed to Ollama; streamed response succeeded. Returned proxy metadata reported one fallback.

## Controlled reliability matrix

Artifacts: [simulated evaluation](../evidence/simulated-evaluation.json), [live evaluation](../evidence/live-evaluation.json).

| Scenario | Primary-only baseline | Gateway |
| --- | --- | --- |
| Healthy | Success | Success |
| Injected primary timeout | Error | Success through secondary |
| Injected primary HTTP 429 | Error | Success through secondary |
| All providers unavailable | Error | Explicit error |
| Interrupted response | Partial error | Partial error; no fallback merge |

Each profile has five baseline and five gateway cases. Baseline completed 1/5; gateway completed 3/5. This is a deliberately adversarial scripted scenario set, not a measured production success rate. The app adapter injects these faults; it does not reproduce a real provider outage. Both local model routes otherwise share an endpoint. Failure latency medians mix successful generations with fast failures and must not be used to claim speed improvements.

The live model returned provider usage and source-ID-valid responses for the successful reliability cases. This is not a broad answer-quality evaluation; source-ID validity is not factual entailment. Per-request response text in the artifact is fictional and reviewable.

## Real proxy failover

[Proxy evidence](../evidence/proxy-evaluation.json) records an actual request through native LiteLLM with a closed-port primary. The response headers report `x-litellm-attempted-fallbacks: 1` and the final response passed the source-ID check. This verifies the native proxy path and fallback, not its Docker image or independent cloud providers. Versions are captured in `config/proxy-requirements.lock`.

## Cache acceptance set

[Cache evidence](../evidence/cache-evaluation.json): nine manually reviewed questions, two accepted matches (including an equivalent contraction paraphrase), zero false hits and one false miss among the positive examples at cosine > 0.94. Negation, personalization, numeric constraints and different intent are represented. This small set supports the conservative example configuration only, not general semantic-cache correctness. Cache latency includes embedding work; no sub-10ms guarantee is claimed.

## Automated checks

See `evidence/checks.txt` for the final recorded run. Coverage includes primary recovery, all-provider failure, midstream failure, permanent authentication error, end-to-end deadline, cancellation cleanup, half-open circuits, rate/concurrency and budget admission, concurrent reservation race, unknown usage retention, restart persistence, cache expiry/isolation, invalid citation handling, proxy retry ownership, HTTP auth/CSRF/host rejection, schema validation, actual SSE framing/parser behavior and official Langfuse SDK trace parentage.

The Redis integration check is skipped unless a real Redis Search URL is supplied. A skipped test is not a passing integration test.

## Not yet verified

- Real Redis Search instance and Docker image execution.
- Actual self-hosted Langfuse server ingestion and UI trace visibility.
- GPU vLLM inference.
- Fresh-clone Docker startup, remote deployment, multi-user isolation and sustained load.
- Independent peer audit, video recording and form submission.

The CI workflow runs on repository pushes; inspect its GitHub Actions result separately from the recorded local results. Runtime-dependent checks need suitable infrastructure before final submission.
