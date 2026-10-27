"""Exercise Aegis through a real running native LiteLLM proxy."""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aegis.config import Settings
from aegis.engine import Engine
from aegis.models import Investigation


async def main():
    engine = Engine(
        Settings(
            home=Path(".runtime/proxy-check-" + str(time.time_ns())),
            mode="proxy",
            primary_url="http://127.0.0.1:4000/v1",
            primary_model="support-primary",
            primary_key=Path(".runtime/proxy.key").read_text().strip(),
            deadline=120,
            timeout=90,
        )
    )
    request = Investigation(question="What is the standard refund policy?", cache=False)
    rid = engine.admit("proxy-validation", request)
    answer = ""
    try:
        async for event in engine.events(rid, "proxy-validation", request):
            if event["type"] == "token":
                answer += event["data"]["text"]
            if event["type"] == "done":
                result = event["data"]
        config = Path(".runtime/native-proxy.yaml").read_text()
        report = {
            "primary_closed_port_fault": "127.0.0.1:1/v1" in config,
            "limits": "Native LiteLLM proxy smoke check, not Docker image validation. Secondary uses local Ollama.",
            "run": result,
            "answer": answer,
        }
        Path("evidence/proxy-evaluation.json").write_text(json.dumps(report, indent=2))
        print("Proxy outcome:", result["status"], "source IDs:", result["citations_valid"])
        if result["status"] != "success":
            raise SystemExit("Proxy integration did not pass")
    finally:
        await engine.close()


asyncio.run(main())
