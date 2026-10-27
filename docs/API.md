# API usage

The service binds to `127.0.0.1:8050`. Read `.runtime/admin.key` privately and set `AEGIS_KEY` in your shell without recording its value. Every `/api` endpoint except session login requires the bearer key or an existing local session cookie.

```sh
curl --no-buffer http://127.0.0.1:8050/api/investigate \
  -H "Authorization: Bearer $AEGIS_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is the standard refund policy?","scenario":"timeout","cache":false,"baseline":false}'
```

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Process liveness only; not model/backend readiness |
| `POST /api/session` | Exchange local operator key for HttpOnly session cookie |
| `DELETE /api/session` | Sign out current browser session |
| `GET /api/overview` | Most recent 100 records and aggregated metrics |
| `GET /api/documents` | Validated fictional corpus and version fingerprint |
| `GET /api/runs/{id}` | Select request evidence from recent local history |
| `POST /api/investigate` | Validated support question; async SSE response |

Stream events: `start`, `stage`, `sources`, `cache`, `routing`, `retry`, `token`, `error`, `done`. Each named event has one JSON `data` object. Five-second comment heartbeats keep an idle retrieval/model request visible. SSE event data and source scores are not HTML.

Use `AbortController.abort()` to stop a browser request. After the stream starts, inspect `error` and final `done.status`; an HTTP 200 stream can end in `partial_error`. Do not treat HTTP status alone as successful generation. Pre-admission errors use 401 (authentication), 402 (configured lab budget), 422 (invalid request) and 429 (rate/concurrency).

Interactive schema is available at `/docs`. Typed source contracts are in `aegis/models.py`; graph and persisted-record schemas are described in `ARCHITECTURE.md`. No endpoint accepts provider URLs, upstream credentials or caller-selected identity from an investigation request.
