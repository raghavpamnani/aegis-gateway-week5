# Integration profiles and verification

These profiles are explicit. The lightweight profile does not substitute for real Redis, Langfuse, LiteLLM or vLLM verification.

## Local Ollama (verified on the prepared Mac)

Install Ollama from its official distribution if absent. Start a project-local model directory:

```sh
bash scripts/serve_local_model.sh
# In a second terminal, only if the model is absent:
OLLAMA_HOST=http://127.0.0.1:11435 ollama pull qwen3:1.7b
AEGIS_MODE=live bash scripts/run.sh
```

The prepared model directory references pre-existing cached model blobs and has its own manifest directory. Earlier-week source folders are untouched. The server is configured to disable Ollama cloud inference. Fresh clones do not contain model weights.

## Docker app and Redis Search (prepared, not locally run)

```sh
docker compose up --build -d app
# Privately read the operator key from the app volume:
docker compose exec app cat .runtime/admin.key
```

The Redis 8 image provides Search/vector commands; no public Redis port is exposed beyond localhost. To test the actual backend from the host:

```sh
docker compose up -d cache
AEGIS_TEST_REDIS_URL=redis://127.0.0.1:6380/0 .venv/bin/python -m pytest -q tests/test_integrations.py
AEGIS_REDIS_URL=redis://127.0.0.1:6380/0 bash scripts/run.sh
```

Redis failure degrades to an explicit cache-unavailable outcome and provider inference; it does not silently claim a Redis hit. Embedding downloads happen on the first Docker request unless the named model volume is already warm. Allow network access for initial setup. Persisted application data includes the operator key, so protect the volume.

## Self-hosted Langfuse (prepared, server ingestion not verified)

The official Compose stack includes more than a single web container. The current vendor VM guide recommends 4 cores/16 GiB for its VM example; resource feasibility must be checked rather than promising the full stack fits an 8 GB Mac.

```sh
.venv/bin/python scripts/prepare_langfuse.py
# Review .runtime/langfuse/UPSTREAM.txt and generated configuration.
docker compose --env-file .runtime/langfuse/.env -f .runtime/langfuse/compose.yaml up -d
```

The preparation script records the upstream commit and restricts published ports to localhost. It creates random private deployment credentials without overwriting an existing secret file. Inspect upstream changes before using a newly fetched version. The underlying image tags follow the upstream major release and are not digest-locked.

Read the local login email/password from `.runtime/langfuse/.env` privately. Add the three values in `.runtime/langfuse/app.env` to the application's private `.env`, then restart. Docker app connections need `LANGFUSE_BASE_URL=http://host.docker.internal:3000`. Confirm the installed SDK/server compatibility using the official guide; the validated SDK is captured in `requirements.lock`.

The app uses the official Langfuse SDK on its existing OpenTelemetry provider when keys are configured. Local spans are filtered for export by this application's provider; prompts, response bodies and credentials are not attached. The SDK path is tested with an in-memory exporter. This proves SDK instrumentation, not server ingestion. To validate the server, run a request, then find its trace ID in Langfuse and inspect the nested model-attempt spans. Do not mark this integration verified until that succeeds.

Alternatively configure an OTLP HTTP endpoint using `AEGIS_OTLP_ENDPOINT` and comma-separated `AEGIS_OTLP_HEADERS`. For Langfuse v4 direct OTLP, the official API reference requires Basic authentication and `x-langfuse-ingestion-version=4`. SDK mode is preferred; do not enable both exporters for the same destination.

## LiteLLM Proxy (native verified; Docker profile not locally run)

The native proxy was tested at version 1.106.4 with a closed-port primary and a real Ollama secondary; see `evidence/proxy-evaluation.json`. To reproduce without Docker:

```sh
python3 -m venv .runtime/proxy-venv
.runtime/proxy-venv/bin/python -m pip install -r config/proxy-requirements.lock
.venv/bin/python scripts/run_proxy.py --fail-primary
# In a second terminal:
HF_HOME="$PWD/.runtime/huggingface" .venv/bin/python scripts/verify_proxy.py
```

The native launcher creates its private key in `.runtime/proxy.key`. Omit `--fail-primary` for the healthy configuration. This check uses an actual unreachable HTTP endpoint, not the app's fault shortcut.

For the Docker profile, generate a private random `LITELLM_MASTER_KEY` in `.env`; never use a published default. The image tag `main-stable` is a moving vendor tag; resolve and record an image digest for reproducible deployment before submission.

```sh
docker compose --profile proxy up -d proxy
AEGIS_MODE=proxy AEGIS_PRIMARY_URL=http://127.0.0.1:4000/v1 \
AEGIS_PRIMARY_MODEL=support-primary AEGIS_PRIMARY_KEY="$LITELLM_MASTER_KEY" bash scripts/run.sh
```

Set/export the key in the shell privately before the command. Edit `config/litellm.yaml` to configure actual independent endpoints. The sample routes share one local model and prove only routing configuration. Proxy mode deliberately disables app-owned retries, fallback and circuits. App fault-scenario controls are disabled in this mode; use an upstream HTTP fault service for a true proxy-failover test. Current prepared fault controls run at the app adapter boundary, not as a separate HTTP fault server.

## vLLM GPU (prepared, unavailable on this Mac)

On a supported Linux NVIDIA host with Docker GPU support:

```sh
docker compose --profile gpu up -d vllm
AEGIS_MODE=live AEGIS_PRIMARY_URL=http://127.0.0.1:8000/v1 \
AEGIS_PRIMARY_MODEL=support-local bash scripts/run.sh
```

The profile uses a small open model and a pinned vLLM release tag. Check current device/driver compatibility and model access before launching. A successful `/v1/models` response alone is insufficient: generate and stream a real response. Record version, GPU, configuration and request evidence. Ollama is an accessible local development backend, not proof of vLLM deployment.

## Official references

- [Langfuse Compose](https://langfuse.com/self-hosting/deployment/docker-compose)
- [Langfuse SDK compatibility](https://langfuse.com/docs/observability/sdk/overview)
- [Langfuse API authentication and ingestion](https://api.reference.langfuse.com/)
- [LiteLLM configuration](https://docs.litellm.ai/docs/proxy/config_settings)
- [Redis vector fields](https://redis.io/docs/latest/interact/search-and-query/advanced-concepts/vectors/)
- [vLLM hardware installation](https://docs.vllm.ai/en/stable/getting_started/installation/)
