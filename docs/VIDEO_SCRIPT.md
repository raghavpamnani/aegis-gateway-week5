# Aegis Gateway — two-minute video script

Target: approximately 250 spoken words, with 20 seconds for the problem, 60 seconds for the working system and recovery, and 40 seconds for architecture and evidence. Rehearse once and adjust your speaking pace; timestamps are recording targets, not measured durations.

## Before recording

1. Start Ollama and the app using the README. Open http://127.0.0.1:8050 and sign in before recording. Verify the badge says **LIVE INFERENCE**.
2. In Investigation lab, select **Healthy · no injected fault**, enable the FAQ cache and run **What is the standard refund policy?** once. Wait for SUCCESS. This warms embeddings/model and seeds the eligible FAQ cache. If the first response says `needs_review`, do not record a successful-answer claim; inspect it first.
3. Uncheck **Allow cache for eligible static FAQs** for the first recorded request, so viewers see actual generation rather than a cached response. Leave baseline unchecked.
4. Prepare browser tabs for the application, GitHub architecture document, and validation report. Use the real project documents, not the AI-generated concept image.
5. Use a desktop-sized browser at a readable zoom. Close unrelated tabs and notifications. Keep the operator key, `.env`, and any credential terminal off screen.
6. Rehearse the workflow. Cold startup can take tens of seconds; warm it before recording. If a request still exceeds its time slot, use a clearly labelled cut such as “Generation wait shortened,” while preserving the before/after outcome. Do not disguise edited footage as a latency benchmark.

## Timed script and screen actions

### 0:00–0:20 — Introduce the problem

**Screen:** Overview, with LIVE INFERENCE visible. Move to Investigation lab as you finish.

**Say:**

> Hi, I’m Rahul. This is Aegis Gateway, my Week Five capstone. AI support applications need more than good answers: they must handle model failures and explain what happened. Aegis makes that request path visible through a fictional support workflow.

### 0:20–0:40 — Show the working application

**Screen:** With Healthy selected and cache unchecked, run **What is the standard refund policy?** Point to streaming text, `[POL-001]`, and the retrieved evidence cards. Wait for the final outcome before describing success.

**Say:**

> I’ll ask about the standard refund policy. The application combines keyword and vector retrieval, then streams a response from a real local model. These document IDs connect the answer to retrieved evidence. The interface also records the request’s timing and outcome.

### 0:40–1:00 — Demonstrate failure recovery

**Screen:** Select **Primary timeout → fallback** and run the same question. Point to primary attempt, retry, secondary route, and SUCCESS in the timeline. This control injects a fault; it does not cause a real provider outage.

**Say:**

> Now I’m injecting a primary-model timeout. This is a controlled failure simulation. The gateway applies a bounded retry, then switches to the secondary route and completes the response. Both local routes share one endpoint, so this demonstrates routing mechanics, not independent-provider availability.

### 1:00–1:20 — Show cache and inspectability

**Screen:** Restore Healthy, enable cache, and repeat the exact FAQ. Show `Cache hit`. Open Request traces and select the **live / timeout** request with three attempts, rather than the newer cache-hit request. Show attempt outcomes and durations.

**Say:**

> Repeating an eligible FAQ can reuse a cached answer. This local profile uses SQLite with real embeddings. In the trace explorer, I can inspect the earlier failed attempts and successful fallback. Citation checks validate source IDs; they do not prove every generated claim.

### 1:20–1:40 — Explain architecture

**Screen:** Open `docs/ARCHITECTURE.md` on GitHub and show the rendered Mermaid diagram. Point along admission → retrieval → cache → routing → streaming → ledger and telemetry.

**Say:**

> FastAPI provides typed request boundaries. LangGraph coordinates retrieval and policy checks. The gateway controls admission, retries, circuits and streaming, while OpenTelemetry captures execution spans. Interrupted streams end explicitly, instead of silently mixing another model’s answer into an unfinished response.

### 1:40–2:00 — Present evidence and scope

**Screen:** Open `docs/VALIDATION.md`, showing automated checks and native proxy evidence. Briefly show the public repository name. Finish on the app or repository.

**Say:**

> Validation includes twenty-one passing local tests and an actual LiteLLM proxy fallback from an unreachable primary to Ollama. Redis, self-hosted Langfuse and GPU vLLM configurations are prepared, with deployment checks still outstanding. Aegis demonstrates reliability through recorded behavior, with its limits stated clearly.

## Narration-only copy

Hi, I’m Rahul. This is Aegis Gateway, my Week Five capstone. AI support applications need more than good answers: they must handle model failures and explain what happened. Aegis makes that request path visible through a fictional support workflow.

I’ll ask about the standard refund policy. The application combines keyword and vector retrieval, then streams a response from a real local model. These document IDs connect the answer to retrieved evidence. The interface also records the request’s timing and outcome.

Now I’m injecting a primary-model timeout. This is a controlled failure simulation. The gateway applies a bounded retry, then switches to the secondary route and completes the response. Both local routes share one endpoint, so this demonstrates routing mechanics, not independent-provider availability.

Repeating an eligible FAQ can reuse a cached answer. This local profile uses SQLite with real embeddings. In the trace explorer, I can inspect the earlier failed attempts and successful fallback. Citation checks validate source IDs; they do not prove every generated claim.

FastAPI provides typed request boundaries. LangGraph coordinates retrieval and policy checks. The gateway controls admission, retries, circuits and streaming, while OpenTelemetry captures execution spans. Interrupted streams end explicitly, instead of silently mixing another model’s answer into an unfinished response.

Validation includes twenty-one passing local tests and an actual LiteLLM proxy fallback from an unreachable primary to Ollama. Redis, self-hosted Langfuse and GPU vLLM configurations are prepared, with deployment checks still outstanding. Aegis demonstrates reliability through recorded behavior, with its limits stated clearly.

## If an expected result does not appear

- **No cache hit:** ensure Healthy is selected, the cache box is checked, baseline is off, and the exact seeded FAQ is used. Do not call a miss a hit.
- **Circuit open instead of retry:** a recent rehearsal may have opened the scenario circuit. Wait at least 20 seconds before retrying the timeout demonstration.
- **Live model unavailable:** start Ollama and confirm the model is installed. Do not switch to scripted mode while describing the output as real inference.
- **Langfuse:** do not show a fictitious server dashboard. The official SDK was tested using a test exporter; real self-hosted ingestion remains pending.
- **Latency:** the dashboard includes cold-start and retrieval time. Do not claim millisecond responses or a production SLA from these small local demonstrations.

Optional extra footage, outside the two-minute submission: show the interrupted-stream error, knowledge library, or the native LiteLLM proxy evidence. Keep these out of the main cut if they prevent completion within two minutes.
