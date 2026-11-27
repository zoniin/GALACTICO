"""Bounded in-memory upstream cache with per-key refresh and dated stale results."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
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


class _KeyLocks:
    """One lock per key, held in the dict only while a caller is using it.

    Sixteen shared shards made a cold read of one resource wait behind an unrelated download
    whose key hashed to the same shard. Here two keys never share a lock, and the dict is
    bounded by the keys in flight: the last caller out removes its key's entry.
    """

    def __init__(self) -> None:
        self._held: dict[str, tuple[asyncio.Lock, int]] = {}

    def __len__(self) -> int:
        return len(self._held)

    @asynccontextmanager
    async def hold(self, key: str) -> AsyncIterator[None]:
        lock, users = self._held.get(key) or (asyncio.Lock(), 0)
        self._held[key] = (lock, users + 1)
        try:
            async with lock:
                yield
        finally:
            lock, users = self._held[key]
            if users == 1:
                del self._held[key]
            else:
                self._held[key] = (lock, users - 1)


class FeedCache:
    def __init__(self, limit: int = 128, *, max_retry: int = 30) -> None:
        self._entries: OrderedDict[str, tuple[float, Snapshot | None, str | None, int]]
        self._entries = OrderedDict()
        self._max_retry = max_retry
        self._locks = _KeyLocks()
        self._limit = limit

    async def get(self, key: str, ttl: int,
                  fetch: Callable[[], Awaitable[list | Snapshot]]) -> Snapshot:
        """The key's rows, refreshed by ``fetch`` once ``ttl`` seconds have passed.

        ``fetch`` returns the rows, or a ``Snapshot`` when it read them from a store that
        knows when they were checked: that ``checked`` is kept, so rows another tier held
        do not read as freshly fetched.

        A ``FeedError`` that carries ``retry_after`` (the season budget's ``Deferred``) says
        no request was made, so nothing failed upstream: the key is held for exactly that
        many seconds (0 refetches on the next call) and the failure backoff is not doubled.
        """
        async with self._locks.hold(key):
            expires, previous, error, retry = self._entries.get(key, (0, None, None, 30))
            if expires <= monotonic():
                hold: float | None = None
                try:
                    fetched = await fetch()
                    previous = (fetched if isinstance(fetched, Snapshot)
                                else Snapshot(fetched, datetime.now(UTC).isoformat()))
                    error = None
                except (httpx.HTTPError, ValueError, FeedError) as exc:
                    error = str(exc) if isinstance(exc, FeedError) else "Feed unavailable."
                    hold = getattr(exc, "retry_after", None)
                if hold is not None:
                    self._entries[key] = (monotonic() + max(0.0, float(hold)), previous, error,
                                          retry)
                else:
                    self._entries[key] = (monotonic() + (retry if error else ttl), previous,
                                          error, min(2 * retry, self._max_retry) if error else 30)
                if len(self._entries) > self._limit:
                    self._entries.popitem(last=False)
            self._entries.move_to_end(key)
            if previous is None:
                raise FeedError(error or "Feed unavailable.")
            return replace(previous, warning=error)
