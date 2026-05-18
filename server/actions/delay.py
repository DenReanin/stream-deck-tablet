"""Pausa entre acciones. Útil dentro de un 'sequence'."""
from __future__ import annotations

import asyncio


async def wait(params: dict) -> dict:
    ms = int(params.get("ms", 100))
    if ms < 0:
        raise ValueError("delay 'ms' must be >= 0")
    await asyncio.sleep(ms / 1000.0)
    return {"waited_ms": ms}
