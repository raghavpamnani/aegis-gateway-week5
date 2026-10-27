import asyncio
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph

from aegis.models import Document


def terms(text):
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


class Embeddings:
    """Lazy local sentence-transformer. No lexical fallback passed off as embeddings."""

    def __init__(self, model):
        self.name = model
        self.model = None
        self.lock = asyncio.Lock()

    async def encode(self, texts):
        async with self.lock:
            if self.model is None:

                def load_model():
                    from sentence_transformers import SentenceTransformer

                    return SentenceTransformer(self.name, device="cpu")

                self.model = await asyncio.to_thread(load_model)
            result = await asyncio.to_thread(self.model.encode, texts, normalize_embeddings=True)
            return result.tolist()


class State(TypedDict, total=False):
    question: str
    vector: list[float]
    hits: list[dict]
    route: str
    eligible: bool
    stages: list[str]


class Investigator:
    def __init__(self, embeddings, path=None):
        self.embeddings = embeddings
        path = path or Path(__file__).resolve().parents[1] / "data/corpus.json"
        self.docs = [Document.model_validate(d) for d in json.loads(path.read_text())]
        self.version = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        self.vectors = None
        self.lock = asyncio.Lock()
        graph = StateGraph(State)
        graph.add_node("classify", self.classify)
        graph.add_node("hybrid_retrieve", self.retrieve)
        graph.add_node("policy_gate", self.policy_gate)
        graph.set_entry_point("classify")
        graph.add_edge("classify", "hybrid_retrieve")
        graph.add_edge("hybrid_retrieve", "policy_gate")
        graph.add_edge("policy_gate", END)
        self.graph = graph.compile()

    def classify(self, state):
        # Deterministic routing, not falsely presented as model agent planning.
        runbook = any(t in state["question"].lower() for t in ["504", "429", "timeout", "incident"])
        return {"route": "incident" if runbook else "policy", "stages": ["classify"]}

    async def retrieve(self, state):
        async with self.lock:
            if self.vectors is None:
                self.vectors = await self.embeddings.encode([d.title + " " + d.body for d in self.docs])
        vector = (await self.embeddings.encode([state["question"]]))[0]
        q = terms(state["question"])
        tokens = [terms(d.title + " " + d.body) for d in self.docs]
        avg = sum(map(len, tokens)) / len(tokens)
        lexical = []
        for tok in tokens:
            counts = Counter(tok)
            score = 0.0
            for t in set(q):
                df = sum(t in other for other in tokens)
                idf = math.log(1 + (len(tokens) - df + 0.5) / (df + 0.5))
                freq = counts[t]
                score += idf * freq * 2.2 / (freq + 1.2 * (0.25 + 0.75 * len(tok) / avg))
            lexical.append(score)
        semantic = [cosine(vector, v) for v in self.vectors]
        bm = sorted(range(len(tokens)), key=lambda i: lexical[i], reverse=True)
        vm = sorted(range(len(tokens)), key=lambda i: semantic[i], reverse=True)
        fused = sorted(
            range(len(tokens)),
            key=lambda i: 1 / (60 + bm.index(i) + 1) + 1 / (60 + vm.index(i) + 1),
            reverse=True,
        )
        hits = [
            {**self.docs[i].model_dump(), "cosine": round(semantic[i], 4), "bm25": round(lexical[i], 4)}
            for i in fused[:3]
        ]
        return {"vector": vector, "hits": hits, "stages": state["stages"] + ["hybrid_retrieve"]}

    def policy_gate(self, state):
        q = state["question"].lower()
        # Reviewed, static FAQ families only; investigations bypass response cache.
        eligible = state["route"] == "policy" and not re.search(
            r"\b(my|our|account|today|now|customer|not|never)\b|\d|@|https?://", q
        )
        eligible = eligible and state["hits"][0]["cacheable"] and state["hits"][0]["cosine"] > 0.3
        return {"eligible": bool(eligible), "stages": state["stages"] + ["policy_gate"]}

    async def run(self, question):
        return await self.graph.ainvoke({"question": question})
