"""비동기 HTTP 호출 속도 제한 도우미."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class AsyncTokenBucket:
    """초당 호출 수를 제한하는 간단한 비동기 토큰 버킷."""

    max_rps: float = 5.0
    capacity: float | None = None
    _tokens: float = field(init=False)
    _updated_at: float = field(init=False)
    _waiters: deque[asyncio.Future[None]] = field(default_factory=deque, init=False)
    _timer_handle: asyncio.TimerHandle | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.max_rps <= 0:
            raise ValueError("max_rps must be greater than 0")
        self.capacity = self.capacity or self.max_rps
        self._tokens = self.capacity
        self._updated_at = time.monotonic()

    async def acquire(self) -> None:
        self._refill()
        if not self._waiters and self._tokens >= 1:
            self._tokens -= 1
            return
        fut: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self._waiters.append(fut)
        self._schedule()
        try:
            await fut
        except asyncio.CancelledError:
            try:
                self._waiters.remove(fut)
            except ValueError:
                pass
            raise

    def _schedule(self) -> None:
        if self._timer_handle is not None:
            return
        while self._waiters:
            self._refill()
            if self._tokens < 1:
                wait_for = (1 - self._tokens) / self.max_rps
                self._timer_handle = asyncio.get_running_loop().call_later(
                    wait_for, self._on_timer
                )
                return
            self._tokens -= 1
            self._waiters.popleft().set_result(None)

    def _on_timer(self) -> None:
        self._timer_handle = None
        self._schedule()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._updated_at
        self._updated_at = now
        assert self.capacity is not None
        self._tokens = min(self.capacity, self._tokens + elapsed * self.max_rps)
