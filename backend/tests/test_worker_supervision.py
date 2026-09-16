"""El mantenimiento debe propagar fallos para que Docker reinicie el worker."""

import pytest

from app import worker


class _Unused:
    pass


async def test_maintenance_propagates_heartbeat_failure(monkeypatch):
    async def no_wait(_seconds):
        return None

    async def failed_heartbeat():
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr(worker.asyncio, "sleep", no_wait)
    monkeypatch.setattr(worker, "write_worker_heartbeat", failed_heartbeat)

    with pytest.raises(ConnectionError, match="redis unavailable"):
        await worker._maintenance(_Unused(), _Unused(), _Unused())
