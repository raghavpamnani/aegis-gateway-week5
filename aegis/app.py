import asyncio
import hmac
import json
import os
import secrets
import statistics
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from aegis.config import Settings
from aegis.engine import AdmissionError, Engine
from aegis.models import Investigation
from aegis.safety import check_question


class Login(BaseModel):
    key: str = Field(min_length=16, max_length=256)


def create_app(settings=None, engine=None):
    settings = settings or Settings()
    engine = engine or Engine(settings)
    key_path = settings.home / "admin.key"
    if settings.admin_key:
        key = settings.admin_key
    elif key_path.exists():
        key = key_path.read_text().strip()
    else:
        key = secrets.token_urlsafe(32)
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as file:
            file.write(key)
    sessions = {}
    login_attempts = []

    @asynccontextmanager
    async def lifespan(app):
        yield
        await engine.close()

    app = FastAPI(title="Aegis Gateway", version="0.1.0", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    app.state.engine = engine

    @app.middleware("http")
    async def boundaries(request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return Response("Cross-origin writes are disabled", status_code=403)
            # Reject oversized bodies before FastAPI JSON parsing.
            try:
                if int(request.headers.get("content-length", "0")) > 8192:
                    return Response("Request too large", status_code=413)
            except ValueError:
                return Response("Invalid length", status_code=400)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
        )
        return response

    def auth(request: Request):
        bearer = request.headers.get("authorization", "").removeprefix("Bearer ")
        session = request.cookies.get("aegis_session", "")
        if bearer and hmac.compare_digest(bearer, key):
            return "local-operator"
        if sessions.get(session, 0) > time.time():
            return "local-operator"
        raise HTTPException(401, "Sign in using the local operator key")

    @app.post("/api/session")
    def login(body: Login, response: Response):
        now = time.time()
        login_attempts[:] = [t for t in login_attempts if t > now - 60]
        if len(login_attempts) >= 5:
            raise HTTPException(429, "Too many login attempts; wait one minute")
        login_attempts.append(now)
        if not hmac.compare_digest(body.key, key):
            raise HTTPException(401, "Invalid operator key")
        # One local operator; bound session storage.
        sessions.clear()
        token = secrets.token_urlsafe(32)
        sessions[token] = now + 8 * 3600
        response.set_cookie("aegis_session", token, httponly=True, samesite="strict", max_age=8 * 3600)
        return {"ok": True}

    @app.delete("/api/session")
    def logout(request: Request, response: Response, identity=Depends(auth)):
        sessions.pop(request.cookies.get("aegis_session", ""), None)
        response.delete_cookie("aegis_session")
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"status": "alive", "service": "aegis-gateway"}

    @app.get("/api/overview")
    def overview(identity=Depends(auth)):
        runs = engine.store.runs()
        good = [r for r in runs if r["status"] == "success"]
        latencies = sorted(r["latency_ms"] for r in runs)
        return {
            "mode": settings.mode,
            "runs": runs,
            "count": len(runs),
            "success_rate": len(good) / len(runs) if runs else None,
            "p95_ms": latencies[max(0, int(len(latencies) * 0.95 + 0.999) - 1)] if latencies else None,
            "ttft_ms": statistics.median([r["ttft_ms"] for r in runs if r["ttft_ms"] is not None])
            if any(r["ttft_ms"] is not None for r in runs)
            else None,
            "estimated_cost": sum(r["estimated_cost"] for r in runs),
            "budget": engine.store.budget_state(),
            "budget_limit": settings.budget,
            "cache_backend": "redis" if engine.cache.redis else "sqlite-local",
            "embedding_model": settings.embed_model,
            "trace_export": "configured; verify ingestion"
            if engine.telemetry.export_enabled
            else "local ledger only",
            "primary": settings.primary_model,
            "secondary": settings.secondary_model,
            "same_endpoint": settings.primary_url == settings.secondary_url,
            "window": "most recent 100 persisted requests, all profiles/scenarios",
        }

    @app.get("/api/documents")
    def documents(identity=Depends(auth)):
        return {
            "version": engine.retriever.version,
            "documents": [d.model_dump() for d in engine.retriever.docs],
        }

    @app.get("/api/runs/{rid}")
    def run_detail(rid: str, identity=Depends(auth)):
        run = next((r for r in engine.store.runs(1000) if r["id"] == rid), None)
        if not run:
            raise HTTPException(404, "Request not found in local history")
        return run

    @app.post("/api/investigate")
    async def investigate(body: Investigation, identity=Depends(auth)):
        reason = check_question(body.question)
        if reason:
            raise HTTPException(422, reason)
        if settings.mode == "proxy" and body.scenario != "healthy":
            raise HTTPException(
                422, "Proxy fault scenarios use the upstream lab service; select healthy here"
            )
        try:
            rid = engine.admit(identity, body)
        except AdmissionError as exc:
            raise HTTPException(exc.status, exc.message) from exc

        queue = asyncio.Queue(maxsize=64)

        async def produce():
            iterator = engine.events(rid, identity, body)
            try:
                async for event in iterator:
                    await queue.put(event)
            finally:
                await iterator.aclose()
                # Do not deadlock cancellation trying to enqueue sentinel into a full queue.
                if not asyncio.current_task().cancelling():
                    await queue.put(None)

        task = asyncio.create_task(produce())

        async def stream():
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=5)
                    except TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    if event is None:
                        break
                    yield "event: " + event["type"] + "\ndata: " + json.dumps(event["data"]) + "\n\n"
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

        class ManagedResponse(StreamingResponse):
            async def __call__(self, scope, receive, send):
                try:
                    await super().__call__(scope, receive, send)
                finally:
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)

        # Ensure producer has entered its cleanup scope even if response delivery is interrupted.
        await asyncio.sleep(0)
        return ManagedResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                "X-Request-ID": rid,
            },
        )

    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    return app
