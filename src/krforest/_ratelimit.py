"""비동기 HTTP 호출 속도 제한 도우미."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class AsyncTokenBucket:
    """초당 호출 수를 제한하는 간단한 비동기 토큰 버킷."""

    max_rps: float = 5.0
    capacity: float | None = None
    _tokens: float = field(init=False)
    _updated_at: float = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self) -> None:
        if self.max_rps <= 0:
            raise ValueError("max_rps must be greater than 0")
        self.capacity = self.capacity or self.max_rps
        self._tokens = self.capacity
        self._updated_at = time.monotonic()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                wait_for = (1 - self._tokens) / self.max_rps
            await asyncio.sleep(wait_for)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._updated_at
        self._updated_at = now
        assert self.capacity is not None
        self._tokens = min(self.capacity, self._tokens + elapsed * self.max_rps)
