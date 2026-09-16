"""Tests del heartbeat que Docker/Coolify usa para supervisar el worker."""

import fakeredis.aioredis

from app.core import worker_health


async def test_worker_heartbeat_becomes_healthy(monkeypatch):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(worker_health, "get_redis", lambda: redis)
    await worker_health.write_worker_heartbeat()
    assert await worker_health.worker_is_healthy() is True


async def test_missing_worker_heartbeat_is_unhealthy(monkeypatch):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(worker_health, "get_redis", lambda: redis)
    assert await worker_health.worker_is_healthy() is False


async def test_malformed_worker_heartbeat_is_unhealthy(monkeypatch):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await redis.set(worker_health.WORKER_HEARTBEAT_KEY, "not-a-number")
    monkeypatch.setattr(worker_health, "get_redis", lambda: redis)
    assert await worker_health.worker_is_healthy() is False


async def test_expired_worker_heartbeat_is_unhealthy(monkeypatch):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await redis.set(worker_health.WORKER_HEARTBEAT_KEY, "100")
    monkeypatch.setattr(worker_health, "get_redis", lambda: redis)
    monkeypatch.setattr(worker_health.time, "time", lambda: 1000)
    assert await worker_health.worker_is_healthy() is False
