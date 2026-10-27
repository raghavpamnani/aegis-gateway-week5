import asyncio
import hashlib
import re
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass

from tenacity import RetryCallState, Retrying, wait_random_exponential

from aegis.cache import ResponseCache
from aegis.providers import ProviderError, Providers
from aegis.retrieval import Embeddings, Investigator
from aegis.store import Store
from aegis.telemetry import Telemetry, mark_error


@dataclass
class Breaker:
    failures: int = 0
    opened: float = 0
    probing: bool = False

    def enter(self, now, cooldown):
        if not self.opened:
            return True
        if now - self.opened < cooldown or self.probing:
            return False
        self.probing = True
        return True

    def fail(self, now, threshold):
        self.failures += 1
        if self.probing or self.failures >= threshold:
            self.opened = now
        self.probing = False

    def success(self):
        self.failures, self.opened, self.probing = 0, 0, False


class AdmissionError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class Engine:
    def __init__(self, settings, embeddings=None):
        self.s = settings
        self.store = Store(settings.home)
        self.retriever = Investigator(embeddings or Embeddings(settings.embed_model))
        self.providers = Providers(settings)
        self.cache = ResponseCache(self.store, settings)
        self.telemetry = Telemetry()
        self.breakers = defaultdict(Breaker)
        self.rates = defaultdict(deque)
        self.active = 0

    def admit(self, identity, req):
        now = time.monotonic()
        rates = self.rates[identity]
        while rates and rates[0] <= now - 60:
            rates.popleft()
        if len(rates) >= self.s.rpm:
            raise AdmissionError(429, "Gateway request quota exceeded; retry after 60 seconds")
        if self.active >= self.s.concurrency:
            raise AdmissionError(429, "Gateway concurrency limit reached")
        rid = uuid.uuid4().hex
        # Conservative UTF-8 byte bound over the bounded question+context+system prompt.
        # Paid rates are operator configured; no external pricing claims.
        max_input = len(req.question.encode()) + sum(len(d.body.encode()) for d in self.retriever.docs) + 4096
        reserve = (max_input * self.s.input_per_million + self.s.max_tokens * self.s.output_per_million) / 1e6
        reserve *= 2 * (self.s.retries + 1)
        if not self.store.reserve(rid, reserve, self.s.budget):
            raise AdmissionError(402, "Configured lab budget exhausted")
        rates.append(now)
        self.active += 1
        return rid

    async def events(self, rid, identity, req):
        start = time.monotonic()
        run = {
            "id": rid,
            "started": time.time(),
            "status": "running",
            "mode": self.s.mode,
            "scenario": req.scenario,
            "baseline": req.baseline,
            "identity": identity,
            "question_hash": hashlib.sha256(req.question.encode()).hexdigest(),
            "attempts": [],
            "stages": [],
            "cache": "bypass",
            "tokens": None,
            "estimated_cost": 0.0,
            "ttft_ms": None,
            "trace_id": None,
            "citations_valid": False,
            "usage_status": "not_called",
            "same_endpoint": self.s.primary_url == self.s.secondary_url,
        }
        run["pricing"] = {
            "input_per_million": self.s.input_per_million,
            "output_per_million": self.s.output_per_million,
            "basis": "operator-configured API rates; excludes local infrastructure",
        }
        emitted = False
        answer = ""
        usage = None
        had_call = False
        cost = 0.0
        try:
            with self.telemetry.span(
                "investigation",
                **{
                    "aegis.request_id": rid,
                    "aegis.profile": self.s.mode,
                    "aegis.scenario": req.scenario,
                    "deployment.environment.name": "local-lab",
                    "user.id": identity,
                    "aegis.prompt_version": "v1",
                },
            ) as root:
                run["trace_id"] = self.telemetry.trace_id(root)
                yield {
                    "type": "start",
                    "data": {
                        "id": rid,
                        "mode": self.s.mode,
                        "scenario": req.scenario,
                        "trace_id": run["trace_id"],
                    },
                }
                try:
                    async with asyncio.timeout(self.s.deadline):
                        yield {
                            "type": "stage",
                            "data": {
                                "name": "Hybrid retrieval",
                                "detail": "Loading local embeddings if cold; retrieving source evidence",
                            },
                        }
                        with self.telemetry.span("hybrid_retrieval"):
                            state = await self.retriever.run(req.question)
                        run["stages"] = state["stages"]
                        run["sources"] = [
                            {k: h[k] for k in ("id", "title", "version", "cosine", "bm25")}
                            for h in state["hits"]
                        ]
                        yield {
                            "type": "sources",
                            "data": {"sources": run["sources"], "route": state["route"]},
                        }
                        scope = self.cache.scope(
                            identity,
                            self.retriever.version,
                            state["hits"],
                            [self.s.mode, self.s.primary_model, self.s.secondary_model],
                            self.s.embed_model,
                        )
                        eligible = (
                            req.cache and state["eligible"] and req.scenario == "healthy" and not req.baseline
                        )
                        hit = None
                        if eligible:
                            with self.telemetry.span("semantic_cache.lookup"):
                                try:
                                    hit = await self.cache.get(scope, state["vector"])
                                    run["cache"] = "miss"
                                except Exception:
                                    run["cache"] = "unavailable"
                        if hit:
                            cached, sim = hit
                            answer = cached["answer"]
                            run.update(cache="hit", cache_similarity=round(sim, 5), citations_valid=True)
                            run["ttft_ms"] = (time.monotonic() - start) * 1000
                            yield {
                                "type": "cache",
                                "data": {
                                    "status": "hit",
                                    "similarity": sim,
                                    "backend": "redis" if self.cache.redis else "sqlite-local",
                                },
                            }
                            yield {"type": "token", "data": {"text": answer}}
                        else:
                            yield {"type": "cache", "data": {"status": run["cache"]}}
                            names = (
                                ["primary"]
                                if req.baseline or self.s.mode == "proxy"
                                else ["primary", "secondary"]
                            )
                            complete = False
                            for name in names:
                                breaker = self.breakers[(name, req.scenario)]
                                if (
                                    not req.baseline
                                    and self.s.mode != "proxy"
                                    and not breaker.enter(time.monotonic(), self.s.breaker_cooldown)
                                ):
                                    yield {
                                        "type": "routing",
                                        "data": {"provider": name, "status": "circuit_open"},
                                    }
                                    continue
                                attempts = 1 if req.baseline or self.s.mode == "proxy" else self.s.retries + 1
                                for attempt in range(attempts):
                                    current = {"provider": name, "number": attempt + 1, "status": "running"}
                                    run["attempts"].append(current)
                                    yield {"type": "routing", "data": current.copy()}
                                    attempt_start = time.monotonic()
                                    had_call = True
                                    try:
                                        model = (
                                            self.s.primary_model
                                            if name == "primary"
                                            else self.s.secondary_model
                                        )
                                        with self.telemetry.span(
                                            "model.attempt",
                                            **{
                                                "gen_ai.request.model": model,
                                                "aegis.provider": name,
                                                "aegis.attempt": attempt + 1,
                                                "langfuse.observation.type": "generation",
                                            },
                                        ) as span:
                                            async for chunk in self.providers.stream(
                                                name, req.question, state["hits"], req.scenario, attempt
                                            ):
                                                if "usage" in chunk:
                                                    usage = chunk["usage"]
                                                    if usage:
                                                        span.set_attribute(
                                                            "gen_ai.usage.input_tokens",
                                                            usage.get("prompt_tokens", 0),
                                                        )
                                                        span.set_attribute(
                                                            "gen_ai.usage.output_tokens",
                                                            usage.get("completion_tokens", 0),
                                                        )
                                                if "proxy_metadata" in chunk:
                                                    run["proxy_metadata"] = chunk["proxy_metadata"]
                                                if chunk.get("token"):
                                                    emitted = True
                                                    if run["ttft_ms"] is None:
                                                        run["ttft_ms"] = (time.monotonic() - start) * 1000
                                                    answer += chunk["token"]
                                                    yield {"type": "token", "data": {"text": chunk["token"]}}
                                            if not answer.strip():
                                                raise ProviderError("Empty model response")
                                            span.set_attribute("aegis.output_chars", len(answer))
                                        current["status"] = "success"
                                        breaker.success()
                                        complete = True
                                    except ProviderError as exc:
                                        current.update(status="error", error=str(exc))
                                        if exc.retryable and self.s.mode != "proxy":
                                            breaker.fail(time.monotonic(), self.s.breaker_threshold)
                                        else:
                                            breaker.probing = False
                                        if emitted or not exc.retryable:
                                            raise
                                        if attempt + 1 < attempts:
                                            retry = RetryCallState(Retrying(), None, (), {})
                                            retry.attempt_number = attempt + 1
                                            delay = max(
                                                exc.retry_after,
                                                wait_random_exponential(multiplier=0.15, max=1)(retry),
                                            )
                                            yield {
                                                "type": "retry",
                                                "data": {"provider": name, "delay_ms": round(delay * 1000)},
                                            }
                                            await asyncio.sleep(delay)
                                    finally:
                                        current["duration_ms"] = round(
                                            (time.monotonic() - attempt_start) * 1000, 2
                                        )
                                        if current["status"] == "running":
                                            current["status"] = "interrupted"
                                        # Cancelled half-open probe must not leave breaker locked.
                                        breaker.probing = False
                                    if complete:
                                        break
                                if complete:
                                    break
                            if not complete:
                                raise ProviderError("All permitted providers unavailable")
                            cited = set(re.findall(r"\[([A-Z]+-\d{3})\]", answer))
                            allowed = {h["id"] for h in state["hits"]}
                            run["citations_valid"] = bool(cited) and cited <= allowed
                            run["stages"] += ["generate", "citation_check"]
                            # Citation presence is structural, not proof of entailment.
                            if eligible and run["citations_valid"] and run["cache"] != "unavailable":
                                try:
                                    await self.cache.put(scope, state["vector"], {"answer": answer})
                                except Exception:
                                    run["cache_write"] = "unavailable"
                        run["status"] = "success" if run["citations_valid"] else "needs_review"
                except asyncio.CancelledError:
                    run["status"] = "cancelled"
                    raise
                except Exception as exc:
                    run["status"] = "partial_error" if emitted else "error"
                    message = (
                        str(exc)
                        if isinstance(exc, ProviderError)
                        else (
                            "End-to-end deadline exceeded"
                            if isinstance(exc, TimeoutError)
                            else "Request failed; inspect server configuration"
                        )
                    )
                    mark_error(root, message)
                    run["error"] = message
                    yield {"type": "error", "data": {"message": message, "partial": emitted}}
        finally:
            if run["status"] == "running":
                run["status"] = "cancelled"
            if usage:
                run["tokens"] = {
                    "input": usage.get("prompt_tokens", 0),
                    "output": usage.get("completion_tokens", 0),
                }
                cost = (
                    run["tokens"]["input"] * self.s.input_per_million
                    + run["tokens"]["output"] * self.s.output_per_million
                ) / 1e6
                run["usage_status"] = "provider_reported_final_attempt"
            elif had_call:
                run["usage_status"] = "simulated_no_tokens" if self.s.mode == "simulated" else "unknown"
            run["estimated_cost"] = cost
            run["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
            uncertain = (
                self.s.mode != "simulated"
                and had_call
                and (not usage or any(a["status"] != "success" for a in run["attempts"]))
            )
            run["budget_reservation_retained"] = uncertain
            self.store.finish(run, cost, uncertain)
            self.active -= 1
        yield {"type": "done", "data": run}

    async def close(self):
        await self.providers.close()
        await self.cache.close()
        await asyncio.to_thread(self.telemetry.close)
