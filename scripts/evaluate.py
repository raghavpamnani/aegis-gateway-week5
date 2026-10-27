"""Reproducible lab cases; fault injection is synthetic, inference profile is explicit."""

import argparse
import asyncio
import json
import platform
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aegis.config import Settings
from aegis.engine import Engine
from aegis.models import Investigation


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    profile = "live" if args.live else "simulated"
    settings = Settings(
        home=Path(".runtime/evaluation-" + str(time.time_ns())),
        mode=profile,
        deadline=120,
        timeout=60,
        rpm=100,
    )
    engine = Engine(settings)
    results = []
    # Warm local embedding model before timed requests.
    await engine.retriever.run("What is the standard refund policy?")
    scenarios = ["healthy", "timeout", "rate_limit", "outage", "midstream"]
    try:
        for baseline in [True, False]:
            for scenario in scenarios:
                req = Investigation(
                    question="What is the standard refund policy?",
                    scenario=scenario,
                    baseline=baseline,
                    cache=False,
                )
                rid = engine.admit("benchmark", req)
                final = None
                answer = ""
                async for event in engine.events(rid, "benchmark", req):
                    if event["type"] == "token":
                        answer += event["data"]["text"]
                    if event["type"] == "done":
                        final = event["data"]
                # Synthetic corpus/output only; safe to include in benchmark evidence.
                results.append({**final, "answer": answer})
                print(profile, "baseline" if baseline else "gateway", scenario, final["status"], flush=True)
        # Cache comparisons are separate from resilience comparisons.
        for question in [
            "What is the standard refund policy?",
            "What is the standard refund policy?",
            "What is the standard refund policy for subscriptions?",
            "Which subscriptions are not refundable?",
        ]:
            req = Investigation(question=question)
            rid = engine.admit("cache-benchmark", req)
            async for event in engine.events(rid, "cache-benchmark", req):
                if event["type"] == "done":
                    results.append({**event["data"], "case_question": question})
    finally:
        await engine.close()
    groups = {}
    for baseline in [True, False]:
        group = [r for r in results[:10] if r["baseline"] == baseline]
        groups["baseline" if baseline else "gateway"] = {
            "n": len(group),
            "successes": sum(r["status"] == "success" for r in group),
            "median_ms": statistics.median(r["latency_ms"] for r in group),
            "attempts": sum(len(r["attempts"]) for r in group),
        }
    report = {
        "profile": profile,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "corpus": engine.retriever.version,
        "embedding": settings.embed_model,
        "model": settings.primary_model,
        "concurrency": 1,
        "warmup": "one retrieval, model may be cold",
        "retries": settings.retries,
        "timeout_seconds": settings.timeout,
        "deadline_seconds": settings.deadline,
        "limits": "Small scripted fault matrix, not production availability or model accuracy. Retry jitter is random. "
        "Both local model routes share one endpoint; independence is not demonstrated.",
        "summary": groups,
        "runs": results,
    }
    Path("evidence").mkdir(exist_ok=True)
    target = Path("evidence") / (profile + "-evaluation.json")
    target.write_text(json.dumps(report, indent=2))
    print("Saved", target)


if __name__ == "__main__":
    asyncio.run(main())
