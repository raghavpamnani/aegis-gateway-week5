# Aegis Gateway

Public repository: https://github.com/raghavpamnani/aegis-gateway-week5

**AI reliability you can inspect.** A local AI gateway and support-investigation lab that makes retries, fallback, semantic caching, streaming, retrieval and trace provenance visible.

Ask about a fictional Northstar Cloud refund policy or PAY-504 incident. The application retrieves evidence using BM25 and real local sentence embeddings, executes a bounded LangGraph workflow, streams a cited response, and records the request outcome. Introduce a labelled primary timeout and watch the gateway recover through a secondary route.

## Run locally

Requires Python 3.12, initial internet access for dependencies and the ~90 MB embedding model, and several GB of disk for the Python runtime. All application source, configuration and evidence are in this Week 5 project.

```sh
bash scripts/setup.sh
bash scripts/run.sh
```

Open **http://127.0.0.1:8050**. Read the generated `.runtime/admin.key` privately and paste it into the local login form. Do not commit or record that key. API calls accept the same key as a bearer token. Authentication is for one local operator, not organization tenancy.

The default **SIMULATED MODEL / REAL PIPELINE** profile uses scripted model text with actual embeddings, retrieval, cache, retry/fallback and request records. It does not claim LLM generation or measured model tokens.

### Actual local LLM

Start Ollama on port 11435 and install `qwen3:1.7b`. The prepared Mac already has this model; `scripts/serve_local_model.sh` starts the installed runtime with the Week 5 model directory. A fresh checkout must install Ollama and pull the model first; see [integrations](docs/INTEGRATIONS.md).

```sh
# Terminal 1
bash scripts/serve_local_model.sh
# Terminal 2
AEGIS_MODE=live bash scripts/run.sh
```

Both default routes use the same local endpoint/model. This verifies routing mechanics and real inference, not independent provider fault tolerance. Configure separate server-side endpoints to demonstrate independent routes. The app never silently switches a failed live model to scripted text.

Local inference has no provider API charge; hardware and electricity are not free. Cost uses explicit operator-configured per-million-token rates. Unknown usage is recorded as unknown and retains the conservative budget reservation; it is never presented as measured zero usage.

## What to demonstrate

1. Run **Refund policy** with no faults: inspect retrieved sources and streamed answer.
2. Repeat the FAQ: an eligible completed response can hit the semantic cache.
3. Select **Primary timeout**: observe bounded retry, secondary routing and the persisted attempt durations.
4. Select **All providers unavailable**: observe an explicit error.
5. Select **Interrupted stream**: observe a partial error with no appended fallback answer.
6. Open **Request traces** and select the request. Inspect the source-ID check, model usage provenance and trace ID.

The source-ID check proves citations refer to retrieved IDs, not that every claim is supported. Responses without valid source IDs require review and are not cached. This fictional assistant cannot perform refunds or modify infrastructure.

## Verify

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check aegis scripts tests
HF_HOME="$PWD/.runtime/huggingface" .venv/bin/python scripts/evaluate.py
HF_HOME="$PWD/.runtime/huggingface" .venv/bin/python scripts/evaluate.py --live
HF_HOME="$PWD/.runtime/huggingface" .venv/bin/python scripts/evaluate_cache.py
```

The live evaluation needs Ollama. Use `HF_HUB_OFFLINE=1` after downloading embeddings. The Redis integration test skips unless `AEGIS_TEST_REDIS_URL` points to a real Redis Search server; a skip is not validation. See [validation evidence](docs/VALIDATION.md).

## Week 5 coverage

| Day | Implementation |
| --- | --- |
| 21 | Bounded retry/backoff, provider fallback, ingress request/concurrency limits, token/cost provenance; isolated tenacity example |
| 22 | OpenTelemetry spans, optional official Langfuse SDK integration, local inference; Langfuse and GPU vLLM deployment profiles |
| 23 | Real-embedding semantic response cache, optional Redis vector backend, circuit state machine; LiteLLM Proxy configuration |
| 24 | Async SSE, heartbeats, disconnect cancellation, bounded buffering; minimal streaming exercise |
| 25 | Validated document ingestion, hybrid retrieval, bounded orchestration and model reasoning, cited streaming, architecture, Docker and audit evidence |

The orchestration graph has deterministic classification/retrieval/policy nodes; model reasoning is confined to composing an evidence-grounded response. This is not an autonomous tool-selecting multi-agent system.

## Project layout

```text
aegis/       API, typed contracts, retrieval graph, gateway, cache, telemetry, dashboard
data/        Versioned fictional policies and runbooks
config/      LiteLLM routing configuration
scripts/     Setup, examples, ingestion and reproducible evaluations
tests/       Failure-path, API, budget, cache and SDK checks
docs/        Architecture, integrations, audit and demonstration
evidence/    Actual evaluation outputs; no credentials or private prompts
```

[API usage](docs/API.md) · [Architecture and state schemas](docs/ARCHITECTURE.md) · [Integration profiles](docs/INTEGRATIONS.md) · [Security and audit](docs/AUDIT.md) · [Validation](docs/VALIDATION.md) · [Video script](docs/VIDEO_SCRIPT.md) · [Demo and submission](docs/SUBMISSION.md)

## Current limits

Verified locally: actual embeddings, hybrid retrieval, LangGraph orchestration, Ollama inference, SQLite cache, gateway failure controls, SSE, browser workflow, OpenTelemetry and official Langfuse SDK export to a test exporter. Native LiteLLM proxy failover is also verified. Redis Search, a real self-hosted Langfuse server, Docker image execution and GPU vLLM are prepared integrations that still need runtime verification on suitable infrastructure. Do not claim complete curriculum deployment or production readiness until those checks pass.

The Docker/CI configurations are provided for that verification; they have not been run on this Mac. The full stack is heavier than this machine's lightweight profile. No cloud resources or paid APIs have been provisioned.

## References and attribution

Original capstone implementation, informed by [LiteLLM](https://github.com/BerriAI/litellm), [Portkey](https://github.com/Portkey-AI/gateway), [Langfuse](https://github.com/langfuse/langfuse), [Redis vector search](https://redis.io/docs/latest/interact/search-and-query/advanced-concepts/vectors/) and [vLLM](https://docs.vllm.ai/en/stable/getting_started/installation/). Upstream tools retain their own licenses. The visual concept in the parent `design/` folder is AI-generated concept art, not validation evidence.
