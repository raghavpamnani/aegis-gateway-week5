"""Day 21 isolated teaching example. Do not stack with proxy-owned retries."""

import asyncio

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    stop=stop_after_attempt(2),
    wait=wait_random_exponential(multiplier=0.2, max=2),
    reraise=True,
)
async def primary(client, url, payload):
    response = await client.post(url, json=payload)
    if response.status_code == 429:
        # Demonstrates retry classification; full gateway also handles Retry-After.
        raise httpx.TimeoutException("Transient upstream quota", request=response.request)
    response.raise_for_status()
    return response.json()


async def inference(primary_url, secondary_url, payload):
    async with httpx.AsyncClient(timeout=10) as client:
        async with asyncio.timeout(30):
            try:
                return await primary(client, primary_url, payload)
            except (httpx.TimeoutException, httpx.NetworkError):
                response = await client.post(secondary_url, json=payload)
                response.raise_for_status()
                return response.json()
