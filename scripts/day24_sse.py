"""Day 24 minimal simulated token exercise. Run with uvicorn scripts.day24_sse:app."""

import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


@app.get("/tokens")
async def tokens():
    async def generate():
        for token in "This is an explicitly simulated token stream.".split():
            await asyncio.sleep(0.1)
            yield "data: " + json.dumps({"text": token + " "}) + "\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
