from __future__ import annotations

import asyncio
import json

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.integration_redis]


@pytest.mark.asyncio
async def test_redis_connection_ping(redis_client) -> None:
    result = await redis_client.ping()
    assert result is True


@pytest.mark.asyncio
async def test_redis_set_and_get(redis_client) -> None:
    await redis_client.set("test:key:string", "hello-integration")
    val = await redis_client.get("test:key:string")
    assert val == "hello-integration"


@pytest.mark.asyncio
async def test_redis_setex_with_ttl(redis_client) -> None:
    await redis_client.setex("test:key:ttl", 60, "ephemeral")
    val = await redis_client.get("test:key:ttl")
    assert val == "ephemeral"

    ttl = await redis_client.ttl("test:key:ttl")
    assert ttl > 0
    assert ttl <= 60


@pytest.mark.asyncio
async def test_redis_delete_key(redis_client) -> None:
    await redis_client.set("test:key:del", "to-delete")
    await redis_client.delete("test:key:del")
    val = await redis_client.get("test:key:del")
    assert val is None


@pytest.mark.asyncio
async def test_redis_cache_pattern(redis_client) -> None:
    key = "test:cache:results:job-42"
    value = '{"species":"Penicillium commune","score":0.95}'
    await redis_client.set(key, value, ex=300)

    cached = await redis_client.get(key)
    assert cached == value
    assert json.loads(cached)["score"] == 0.95


@pytest.mark.asyncio
async def test_redis_pubsub(redis_client) -> None:
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("test:channel:integration")

    received: list[dict] = []

    async def _listen():
        async for message in pubsub.listen():
            if message["type"] == "message":
                received.append(message)
                await pubsub.unsubscribe("test:channel:integration")
                break

    listener_task = asyncio.create_task(_listen())
    await asyncio.sleep(0.05)

    msg_data = '{"event":"segmentation_complete","image_id":"img-1"}'
    await redis_client.publish("test:channel:integration", msg_data)

    try:
        await asyncio.wait_for(listener_task, timeout=3)
    except TimeoutError:
        await pubsub.unsubscribe("test:channel:integration")

    assert len(received) == 1
    assert received[0]["data"] == msg_data
