"""Bounded in-memory upstream cache with per-key refresh and dated stale results."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from time import monotonic
from typing import Any

import httpx


class FeedError(Exception):
    """An upstream failure safe to report without exposing a credential or payload."""


@dataclass(frozen=True)
class Snapshot:
    rows: list[dict[str, Any]]
    checked: str
    warning: str | None = None


class FeedCache:
    def __init__(self, limit: int = 128, *, max_retry: int = 30) -> None:
        self._entries: OrderedDict[str, tuple[float, Snapshot | None, str | None, int]]
        self._entries = OrderedDict()
        self._max_retry = max_retry
        self._locks = [asyncio.Lock() for _ in range(16)]
        self._limit = limit

    async def get(self, key: str, ttl: int, fetch: Callable[[], Awaitable[list]]) -> Snapshot:
        async with self._locks[hash(key) % len(self._locks)]:
            expires, previous, error, retry = self._entries.get(key, (0, None, None, 30))
            if expires <= monotonic():
                try:
                    previous = Snapshot(await fetch(), datetime.now(UTC).isoformat())
                    error = None
                except (httpx.HTTPError, ValueError, FeedError) as exc:
                    error = str(exc) if isinstance(exc, FeedError) else "Feed unavailable."
                self._entries[key] = (monotonic() + (retry if error else ttl), previous, error,
                                      min(2 * retry, self._max_retry) if error else 30)
                if len(self._entries) > self._limit:
                    self._entries.popitem(last=False)
            self._entries.move_to_end(key)
            if previous is None:
                raise FeedError(error or "Feed unavailable.")
            return replace(previous, warning=error)
