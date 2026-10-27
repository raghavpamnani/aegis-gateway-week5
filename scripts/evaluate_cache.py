"""Small reviewed semantic-cache acceptance set using the actual embedding model."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aegis.config import Settings
from aegis.retrieval import Embeddings, Investigator, cosine


async def main():
    settings = Settings()
    investigator = Investigator(Embeddings(settings.embed_model))
    base = "What is the standard refund policy?"
    reference = await investigator.run(base)
    # Acceptance labels are manually authored against the supplied synthetic policies.
    cases = [
        (base, True),
        ("What's the standard refund policy?", True),
        ("What is the standard refund policy for subscriptions?", True),
        ("What is the enterprise refund policy?", False),
        ("What is not refundable under the standard refund policy?", False),
        ("Can my account receive a refund today?", False),
        ("What is the standard refund policy after 30 days?", False),
        ("What is the standard refund policy for renewals?", False),
        ("What is the account recovery policy?", False),
    ]
    rows = []
    for question, equivalent in cases:
        state = await investigator.run(question)
        sim = cosine(reference["vector"], state["vector"])
        scope_same = sorted(h["id"] for h in reference["hits"]) == sorted(h["id"] for h in state["hits"])
        accepted = state["eligible"] and scope_same and sim > settings.cache_threshold
        rows.append(
            {
                "question": question,
                "equivalent": equivalent,
                "similarity": sim,
                "eligible": state["eligible"],
                "same_source_scope": scope_same,
                "accepted": accepted,
            }
        )
    accepted = [r for r in rows if r["accepted"]]
    report = {
        "embedding_model": settings.embed_model,
        "threshold": settings.cache_threshold,
        "n": len(rows),
        "accepted": len(accepted),
        "false_hits": sum(not r["equivalent"] for r in accepted),
        "false_misses": sum(r["equivalent"] and not r["accepted"] for r in rows),
        "limits": "Small manually authored set. Does not establish general semantic cache safety.",
        "cases": rows,
    }
    Path("evidence/cache-evaluation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, indent=2))


asyncio.run(main())
