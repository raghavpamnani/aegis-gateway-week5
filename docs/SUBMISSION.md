# Demonstration and submission

## Two-minute walkthrough

**0:00-0:20 — User problem.** “An AI support service must respond even when a model provider fails, and we need evidence for every decision. Aegis Gateway makes the request path inspectable.” Show the live profile badge and fictional support workflow.

**0:20-1:20 — Working system and recovery.** Ask the standard refund FAQ, show retrieved documents and streamed text. Repeat to show the cache. Select the labelled primary timeout, run again, and show retry plus fallback. Open the exact request trace. If a full local Langfuse deployment has been verified, show the same trace there; otherwise do not imply it exists. Briefly show interrupted streaming produces an explicit partial failure.

**1:20-2:00 — Architecture and evidence.** Explain admission → hybrid retrieval → scoped cache → bounded routing → streaming → ledger/OTel. Show the small controlled benchmark and its sample count. State that shared local routes prove routing mechanics, and distinguish prepared integration profiles from verified deployments.

Never record the login key, provider secrets, private shell history or `.env`. Preload the model and embedding cache. Use a separate prepared request for each fault scenario and avoid including slow setup/downloads in the recording.

## Final delivery checklist

- [x] Modular implementation and setup guide.
- [x] Pydantic request/document schemas and architecture diagram.
- [x] Real local inference path, visible simulation profile and failure controls.
- [x] Async SSE, hybrid retrieval, scoped cache and request evidence.
- [x] Tests, reproducible evaluation scripts and recorded results.
- [x] Docker, Langfuse, Redis, proxy and GPU serving configuration prepared.
- [ ] Run Docker/Redis, self-hosted Langfuse, LiteLLM and vLLM on suitable infrastructure; save actual evidence.
- [ ] Obtain and record independent peer audit.
- [x] Public repository created after source/secret review: https://github.com/raghavpamnani/aegis-gateway-week5
- [ ] Record the actual two-minute video and add its accessible link.
- [ ] Submit repository link through the official Week 5 form from the kickoff PDF.

Do not mark the capstone fully submission-ready until the outstanding runtime checks and human deliverables are complete. The repository is published. No video has been recorded and no assignment form has been submitted.
