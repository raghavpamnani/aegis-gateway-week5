import hashlib
import json
import struct
import time

from aegis.retrieval import cosine


class ResponseCache:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings
        self.redis = None
        self.ready = False
        self.index = None
        if settings.redis_url:
            from redis.asyncio import Redis

            self.redis = Redis.from_url(settings.redis_url, socket_timeout=2, socket_connect_timeout=2)

    @staticmethod
    def scope(identity, corpus, hits, model, embed_model):
        return hashlib.sha256(
            json.dumps(
                [
                    identity,
                    corpus,
                    sorted(h["id"] for h in hits),
                    model,
                    embed_model,
                    "prompt-v1",
                    "temp-0",
                    "policy-v1",
                ]
            ).encode()
        ).hexdigest()

    async def setup(self, dim):
        if not self.redis or self.ready:
            return
        from redis.exceptions import ResponseError

        self.index = f"aegis-cache-{dim}"
        try:
            await self.redis.execute_command(
                "FT.CREATE",
                self.index,
                "ON",
                "HASH",
                "PREFIX",
                1,
                f"aegis:cache:{dim}:",
                "SCHEMA",
                "scope",
                "TAG",
                "vector",
                "VECTOR",
                "FLAT",
                6,
                "TYPE",
                "FLOAT32",
                "DIM",
                dim,
                "DISTANCE_METRIC",
                "COSINE",
            )
        except ResponseError as exc:
            if "Index already exists" not in str(exc):
                raise
        self.ready = True

    async def get(self, scope, vector):
        if self.redis:
            await self.setup(len(vector))
            result = await self.redis.execute_command(
                "FT.SEARCH",
                self.index,
                f"(@scope:{{{scope}}})=>[KNN 1 @vector $v AS distance]",
                "PARAMS",
                2,
                "v",
                struct.pack(f"<{len(vector)}f", *vector),
                "SORTBY",
                "distance",
                "RETURN",
                3,
                "distance",
                "payload",
                "expires",
                "DIALECT",
                2,
            )
            if result[0]:
                values = dict(zip(result[2][::2], result[2][1::2], strict=True))
                similarity = 1 - float(values[b"distance"])
                if float(values[b"expires"]) > time.time() and similarity > self.settings.cache_threshold:
                    return json.loads(values[b"payload"]), similarity
            return None
        best = None
        for row in self.store.cache_get(scope):
            sim = cosine(vector, json.loads(row["vector"]))
            if sim > self.settings.cache_threshold and (best is None or sim > best[1]):
                best = (json.loads(row["payload"]), sim)
        return best

    async def put(self, scope, vector, payload):
        key = hashlib.sha256((scope + json.dumps(vector)).encode()).hexdigest()
        if self.redis:
            await self.setup(len(vector))
            name = f"aegis:cache:{len(vector)}:" + key
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.hset(
                    name,
                    mapping={
                        "scope": scope,
                        "vector": struct.pack(f"<{len(vector)}f", *vector),
                        "payload": json.dumps(payload),
                        "expires": time.time() + self.settings.cache_ttl,
                    },
                )
                pipe.expire(name, self.settings.cache_ttl)
                await pipe.execute()
        else:
            self.store.cache_put(key, scope, vector, payload, self.settings.cache_ttl)

    async def close(self):
        if self.redis:
            await self.redis.aclose()
