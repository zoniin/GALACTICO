"""FeedCache, the in-process cache every upstream client shares (tier three).

Three changes in wave D1, all additive. D1-A (PLAN 4): a fetch that returns a ``Snapshot``
keeps its ``checked`` time, and each key has its own lock in place of sixteen shared shards.
The D1 root step (request D1-A R1): a ``Deferred`` from the season budget made no request,
so it holds the key for its ``retry_after`` and does not back off as an upstream failure
does. The cache's other behaviour is pinned in tests/test_match_centre.py and is unchanged.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from galactico.match_centre import feed as feed_module
from galactico.match_centre.feed import FeedCache, FeedError, Snapshot
from galactico.match_centre.season.budget import DEFERRED_LINE, Deferred

EARLIER = "2026-11-20T08:00:00+00:00"


def test_fifty_concurrent_gets_of_one_key_fetch_once():
    calls = 0

    async def load():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return [{"id": 1}]

    async def run():
        cache = FeedCache()
        snaps = await asyncio.gather(*(cache.get("day", 60, load) for _ in range(50)))
        assert calls == 1
        assert all(snap == snaps[0] and snap.rows == [{"id": 1}] for snap in snaps)
        # The lock table holds only keys in flight; all fifty callers have left.
        assert len(cache._locks) == 0

    asyncio.run(run())


def _colliding_key(key: str) -> str:
    """A second key that fell into the first one's shard under the sixteen-shard scheme."""
    return next(f"other-{n}" for n in range(10_000) if hash(f"other-{n}") % 16 == hash(key) % 16)


def test_two_keys_do_not_wait_for_each_other():
    """A slow season download must not hold up a standings read whose key once hashed to
    the same shard."""
    slow_key = "matches/PD/2026"
    fast_key = _colliding_key(slow_key)

    async def run():
        gate = asyncio.Event()
        started = asyncio.Event()

        async def slow():
            started.set()
            await gate.wait()
            return [{"slow": True}]

        async def fast():
            return [{"fast": True}]

        cache = FeedCache()
        pending = asyncio.create_task(cache.get(slow_key, 60, slow))
        await started.wait()
        assert len(cache._locks) == 1
        done = await asyncio.wait_for(cache.get(fast_key, 60, fast), timeout=1)
        assert done.rows == [{"fast": True}] and not pending.done()
        gate.set()
        assert (await pending).rows == [{"slow": True}]
        assert len(cache._locks) == 0

    asyncio.run(run())


def test_the_same_key_still_waits_for_the_fetch_in_flight():
    async def run():
        gate, calls = asyncio.Event(), []

        async def load():
            calls.append(1)
            await gate.wait()
            return [{"id": len(calls)}]

        cache = FeedCache()
        first = asyncio.create_task(cache.get("day", 60, load))
        second = asyncio.create_task(cache.get("day", 60, load))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not second.done() and len(cache._locks) == 1
        gate.set()
        assert (await first) == (await second) and len(calls) == 1

    asyncio.run(run())


def test_checked_is_the_time_the_rows_were_read():
    """Rows another tier held keep the time they were read upstream (R8: a page says how
    current its data is). Rows fetched now are stamped now, as before."""
    stored = Snapshot([{"id": 7}], EARLIER, warning="ignored")
    attempts = 0

    async def from_store():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return stored
        raise FeedError("Feed unavailable.")

    async def fresh():
        return [{"id": 8}]

    async def run():
        cache = FeedCache()
        snap = await cache.get("standings/PD", 0, from_store)
        assert (snap.rows, snap.checked, snap.warning) == ([{"id": 7}], EARLIER, None)
        # A failed refresh serves the same rows with the same honest time, and says so.
        stale = await cache.get("standings/PD", 0, from_store)
        assert (stale.rows, stale.checked) == ([{"id": 7}], EARLIER)
        assert stale.warning == "Feed unavailable."

        before = datetime.now(UTC)
        now = await cache.get("scorers/PD", 60, fresh)
        stamped = datetime.fromisoformat(now.checked)
        assert before <= stamped <= datetime.now(UTC) and stamped.tzinfo is not None

    asyncio.run(run())


def test_a_cancelled_or_failing_caller_leaves_no_lock_behind():
    async def run():
        gate = asyncio.Event()

        async def held():
            await gate.wait()
            return [{"id": 1}]

        async def broken():
            raise FeedError("Feed unavailable.")

        cache = FeedCache()
        holder = asyncio.create_task(cache.get("a", 60, held))
        await asyncio.sleep(0)
        waiter = asyncio.create_task(cache.get("a", 60, held))
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        gate.set()
        await holder
        with pytest.raises(FeedError, match="unavailable"):
            await cache.get("b", 60, broken)
        assert len(cache._locks) == 0

    asyncio.run(run())


def test_the_entry_limit_and_the_lru_order_are_unchanged():
    async def load():
        return [{"id": 1}]

    async def run():
        cache = FeedCache(limit=2)
        for key in ("a", "b"):
            await cache.get(key, 60, load)
        await cache.get("a", 60, load)          # a is now the most recent
        await cache.get("c", 60, load)          # b, the least recent, leaves
        assert list(cache._entries) == ["a", "c"]

    asyncio.run(run())


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_a_deferral_by_the_view_cap_is_retried_at_once(monkeypatch):
    """A view that reached its own cap made no request and nothing failed: the next view
    may fetch at once, and the third call returns fresh rows."""
    clock = _Clock()
    monkeypatch.setattr(feed_module, "monotonic", clock)
    outcomes = [[{"id": 1}], Deferred("view"), Deferred("view"), [{"id": 2}]]
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        outcome = outcomes[calls - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def run():
        cache = FeedCache(max_retry=300)
        first = await cache.get("standings/PD", 0, fetch)
        assert first.rows == [{"id": 1}] and first.warning is None
        for expected_calls in (2, 3):
            stale = await cache.get("standings/PD", 0, fetch)
            assert calls == expected_calls
            assert (stale.rows, stale.checked, stale.warning) == (
                first.rows, first.checked, DEFERRED_LINE)
        fresh = await cache.get("standings/PD", 60, fetch)
        assert calls == 4 and fresh.rows == [{"id": 2}] and fresh.warning is None
        # The failure backoff was never started: an upstream failure now waits 30 s.
        assert cache._entries["standings/PD"][3] == 30

    asyncio.run(run())


def test_a_deferral_by_the_minute_holds_for_its_retry_after_and_does_not_double(monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(feed_module, "monotonic", clock)
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        if calls == 1:
            return [{"id": 1}]
        raise Deferred("minute", retry_after=20)

    async def run():
        cache = FeedCache(max_retry=300)
        await cache.get("scorers/PD", 0, fetch)
        for _ in range(3):
            stale = await cache.get("scorers/PD", 0, fetch)
            assert stale.rows == [{"id": 1}] and stale.warning == DEFERRED_LINE
            held_calls = calls
            clock.now += 19.9                        # still held: no new attempt
            await cache.get("scorers/PD", 0, fetch)
            assert calls == held_calls
            clock.now += 0.2                         # 20 s, not 30, and never 60
        assert cache._entries["scorers/PD"][3] == 30

    asyncio.run(run())


def test_an_upstream_failure_still_backs_off_and_doubles(monkeypatch):
    """The unchanged path, beside the deferral: 30 s, then 60 s."""
    clock = _Clock()
    monkeypatch.setattr(feed_module, "monotonic", clock)
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        if calls == 1:
            return [{"id": 1}]
        raise FeedError("Feed unavailable.")

    async def run():
        cache = FeedCache(max_retry=300)
        await cache.get("day", 0, fetch)
        await cache.get("day", 0, fetch)             # fails: held 30 s
        clock.now += 29
        await cache.get("day", 0, fetch)
        assert calls == 2
        clock.now += 2
        await cache.get("day", 0, fetch)             # fails again: held 60 s
        assert calls == 3
        clock.now += 59
        await cache.get("day", 0, fetch)
        assert calls == 3

    asyncio.run(run())
