"""The football-data.org request budget (season/budget.py, PLAN 4 D1-A; PLATFORM 3.4, 3.7).

Every test runs on an injected clock, and an injected ``httpx.MockTransport`` stands in for
the provider: nothing here reaches the network.
"""

from __future__ import annotations

import asyncio
import re
from time import monotonic

import httpx
import pytest

from galactico.domain.labels import scan_labels
from galactico.match_centre.feed import FeedCache, FeedError, Snapshot
from galactico.match_centre.season.budget import (
    DEFERRED_LINE,
    MAX_WAIT,
    RESERVES,
    Budget,
    Deferred,
    RequestBudget,
)


class Clock:
    """A clock that only moves when told to, or when the budget sleeps on it."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def budget(clock: Clock, **kwargs) -> Budget:
    return Budget(clock=clock, sleep=clock.sleep, **kwargs)


def spend(b: Budget, priority: int) -> int:
    """How many requests of this class the budget grants before it defers one."""
    async def run() -> int:
        granted = 0
        while True:
            try:
                await b.acquire(priority)
            except Deferred:
                return granted
            granted += 1
    return asyncio.run(run())


def test_each_class_spends_only_while_more_than_its_reserve_is_left():
    assert RESERVES == {0: 0, 1: 2, 2: 4, 3: 6}
    clock = Clock()
    b = budget(clock)
    assert b.tokens == 10
    assert spend(b, 3) == 4 and b.tokens == 6      # speculative stops at six left
    assert spend(b, 2) == 2 and b.tokens == 4      # warming at four
    assert spend(b, 1) == 2 and b.tokens == 2      # a reader's cold resource at two
    assert spend(b, 0) == 2 and b.tokens == 0      # the live overlay spends the last
    assert spend(b, 0) == 0
    # The window refills sixty seconds after its first request; no deferral slept.
    assert clock.slept == []
    clock.now += 60
    assert b.tokens == 10 and spend(b, 1) == 8


def test_a_deferred_request_makes_no_request():
    """The client acquires before each call; when the budget defers, the provider is never
    asked."""
    clock = Clock()
    b = budget(clock)
    asked: list[httpx.Request] = []

    def provider(request: httpx.Request) -> httpx.Response:
        asked.append(request)
        return httpx.Response(200, json={"matches": []},
                              headers={"X-Requests-Available-Minute": "9",
                                       "X-RequestCounter-Reset": "50"})

    async def call(client: httpx.AsyncClient, priority: int) -> httpx.Response:
        await b.acquire(priority)
        reply = await client.get("/v4/matches")
        b.observe(reply.headers, reply.status_code)
        return reply

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider),
                                     base_url="https://upstream.invalid") as client:
            await call(client, 1)
            assert len(asked) == 1 and b.tokens == 7   # 9 available, less the reserve of 2
            b.block_until(clock.now + 30)
            with pytest.raises(Deferred) as deferred:
                await call(client, 0)
            assert deferred.value.reason == "blocked" and len(asked) == 1
            clock.now += 31
            await call(client, 2)
            assert len(asked) == 2

    asyncio.run(run())


def test_headers_lower_the_tokens_and_never_raise_them():
    clock = Clock()
    b = budget(clock)
    b.observe({"X-Requests-Available-Minute": "5", "X-RequestCounter-Reset": "30"}, 200)
    assert b.tokens == 3
    b.observe({"x-requests-available-minute": "9"}, 200)       # any letter case; never up
    assert b.tokens == 3
    b.observe(httpx.Headers({"X-REQUESTS-AVAILABLE-MINUTE": "2"}), 200)
    assert b.tokens == 0
    b.observe({"X-Requests-Available-Minute": "many", "X-RequestCounter-Reset": ""}, 200)
    assert b.tokens == 0
    # The reset header says when the window refills: thirty seconds after the first reply.
    clock.now += 29.9
    assert b.tokens == 0
    clock.now += 0.1
    assert b.tokens == 10


def test_a_reply_without_a_reset_still_refills_within_a_minute():
    clock = Clock()
    b = budget(clock)
    b.observe({"X-Requests-Available-Minute": "3"}, 200)
    assert b.tokens == 1
    clock.now += 60
    assert b.tokens == 10


def test_a_429_blocks_every_class_until_the_reset_plus_a_second():
    clock = Clock()
    b = budget(clock)
    b.observe({"X-Requests-Available-Minute": "0", "X-RequestCounter-Reset": "4"}, 429)
    assert b.tokens == 0 and b.blocked_until == clock.now + 5
    for priority in (0, 1, 2, 3):
        assert spend(b, priority) == 0
    clock.now += 4.5                       # the counter has reset; the block has not ended
    assert spend(b, 0) == 0
    clock.now += 0.5
    assert b.blocked_until is None and spend(b, 1) == 8
    # A 429 that does not say when the counter resets blocks for a whole window.
    later = budget(Clock())
    later.observe({}, 429)
    assert later.blocked_until == later._clock() + 61


def test_a_request_waits_at_most_three_hundred_milliseconds_in_all():
    assert MAX_WAIT == 0.3
    clock = Clock()
    b = budget(clock)
    b.block_until(clock.now + 0.2)
    asyncio.run(b.acquire(1))                      # a short block is waited out
    assert clock.slept == [pytest.approx(0.2)]

    clock.slept.clear()
    b.block_until(clock.now + 0.31)
    with pytest.raises(Deferred, match=re.escape(DEFERRED_LINE)):
        asyncio.run(b.acquire(0))
    assert clock.slept == []                       # it did not start a wait it cannot finish

    # Two short waits that add up to more than the limit: the second is not started.
    clock.now += 1
    drained = budget(clock, per_minute=3, reserve=1)
    asyncio.run(drained.acquire(0))        # the window opens; the two left are a reader's reserve
    clock.now += 59.65                     # so it refills in 0.35 s
    drained.block_until(clock.now + 0.2)
    clock.slept.clear()
    with pytest.raises(Deferred) as deferred:
        asyncio.run(drained.acquire(1))
    assert clock.slept == [pytest.approx(0.2)] and deferred.value.reason == "minute"


def test_on_the_real_clock_a_deferral_is_immediate_and_a_short_wait_is_short():
    """The exact bound is held on the injected clock above; here, on the real one, with room
    for a loaded machine."""
    async def timed(b: Budget, priority: int) -> float:
        started = monotonic()
        try:
            await b.acquire(priority)
        finally:
            elapsed = monotonic() - started
        return elapsed

    b = Budget()
    b.block_until(monotonic() + 5)
    started = monotonic()
    with pytest.raises(Deferred):
        asyncio.run(timed(b, 0))
    assert monotonic() - started < 1.0

    b = Budget()
    b.block_until(monotonic() + 0.05)
    assert 0.04 <= asyncio.run(timed(b, 1)) < 1.0


def test_a_clock_that_stands_still_cannot_make_a_request_wait_forever():
    asked: list[float] = []

    async def sleep(seconds: float) -> None:
        asked.append(seconds)

    b = Budget(clock=lambda: 100.0, sleep=sleep)
    b.block_until(100.2)
    with pytest.raises(Deferred):
        asyncio.run(b.acquire(0))
    assert asked == [pytest.approx(0.2)]


def test_a_deferral_says_when_the_request_could_be_made():
    """For the caller's backoff: the minute's budget and a block name the wait; a view's own
    cap names none, since another view may make the request at once."""
    clock = Clock()
    b = budget(clock)
    b.observe({"X-Requests-Available-Minute": "0", "X-RequestCounter-Reset": "4"}, 429)
    with pytest.raises(Deferred) as blocked:
        asyncio.run(b.acquire(0))
    assert (blocked.value.reason, blocked.value.retry_after) == ("blocked", pytest.approx(5))
    clock.now += 5
    b.observe({"X-Requests-Available-Minute": "2", "X-RequestCounter-Reset": "20"}, 200)
    with pytest.raises(Deferred) as minute:
        asyncio.run(b.acquire(1))
    assert (minute.value.reason, minute.value.retry_after) == ("minute", pytest.approx(20))

    async def capped():
        with RequestBudget(0, clock=clock):
            await b.acquire(0)

    with pytest.raises(Deferred) as view:
        asyncio.run(capped())
    assert (view.value.reason, view.value.retry_after) == ("view", 0)


def test_a_deferral_is_a_feed_error_with_a_line_a_reader_may_see():
    error = Deferred("minute")
    assert isinstance(error, FeedError) and str(error) == DEFERRED_LINE
    assert scan_labels([DEFERRED_LINE]) == []
    words = set(re.findall(r"[a-z]+", DEFERRED_LINE.lower()))
    assert not words & {"key", "token", "tokens", "plan", "quota", "limit", "budget"}


def test_feed_cache_serves_the_last_rows_when_the_budget_defers():
    clock = Clock()
    b = budget(clock, per_minute=3, reserve=1)

    async def fetch():
        await b.acquire(1)
        return [{"id": 1}]

    async def run():
        cache = FeedCache()
        first = await cache.get("standings/PD", 0, fetch)
        stale = await cache.get("standings/PD", 0, fetch)
        assert stale.rows == first.rows and stale.checked == first.checked
        assert stale.warning == DEFERRED_LINE
        with pytest.raises(FeedError, match=re.escape(DEFERRED_LINE)):
            await cache.get("scorers/PD", 0, fetch)

    asyncio.run(run())


def test_a_view_makes_at_most_its_cap_and_is_partial_past_it():
    clock = Clock()
    b = budget(clock)

    async def run():
        assert RequestBudget.current() is None
        with RequestBudget(2, clock=clock) as view:
            assert RequestBudget.current() is view
            await b.acquire(1)
            await b.acquire(1)
            with pytest.raises(Deferred) as deferred:
                await b.acquire(0)
            assert deferred.value.reason == "view"
            assert (view.spent, view.deferred, view.partial) == (2, 1, True)
        assert RequestBudget.current() is None
        assert b.tokens == 8                       # the refused request spent nothing

    asyncio.run(run())


def test_tasks_a_view_starts_share_its_cap():
    clock = Clock()
    b = budget(clock)

    async def one() -> bool:
        try:
            await b.acquire(1)
        except Deferred:
            return False
        return True

    async def run():
        with RequestBudget(2, clock=clock) as view:
            granted = await asyncio.gather(*(one() for _ in range(5)))
        assert sorted(granted) == [False, False, False, True, True]
        assert (view.spent, view.deferred) == (2, 3)

    asyncio.run(run())


def test_a_view_past_its_deadline_makes_no_request():
    clock = Clock()
    b = budget(clock)

    async def run():
        with RequestBudget(5, deadline=3.0, clock=clock) as view:
            await b.acquire(1)
            clock.now += 3.0
            with pytest.raises(Deferred) as deferred:
                await b.acquire(1)
            assert deferred.value.reason == "deadline"
            assert (view.spent, view.partial) == (1, True)

    asyncio.run(run())


def test_a_request_the_minute_refuses_is_not_charged_to_the_view():
    clock = Clock()
    b = budget(clock)
    b.observe({"X-Requests-Available-Minute": "3", "X-RequestCounter-Reset": "40"}, 200)

    async def run():
        with RequestBudget(5, clock=clock) as view:
            with pytest.raises(Deferred) as deferred:
                await b.acquire(1)          # one left, and a reader's class keeps two
            assert deferred.value.reason == "minute"
            assert (view.spent, view.deferred) == (0, 1)
            await b.acquire(0)
            assert view.spent == 1

    asyncio.run(run())


def test_a_view_does_not_wait_past_its_deadline():
    clock = Clock()
    b = budget(clock)

    async def run():
        with RequestBudget(5, deadline=3.0, clock=clock):
            clock.now += 2.9                        # 0.1 s left: a 0.2 s wait is not begun
            b.block_until(clock.now + 0.2)
            with pytest.raises(Deferred):
                await b.acquire(0)
        assert clock.slept == []

    asyncio.run(run())


@pytest.mark.parametrize("priority", [-1, 4, True, "1", 1.5])
def test_a_priority_is_one_of_four_classes(priority):
    with pytest.raises(ValueError, match="priority"):
        asyncio.run(Budget().acquire(priority))


def test_a_budget_and_a_view_are_made_with_sense():
    for per_minute, reserve in ((0, 0), (10, 10), (10, -1)):
        with pytest.raises(ValueError):
            Budget(per_minute=per_minute, reserve=reserve)
    with pytest.raises(ValueError):
        RequestBudget(-1)
    assert Budget().per_minute == 10 and Budget().reserve == 2
    assert RequestBudget(2).deadline == 3.0


def test_snapshots_are_untouched_by_the_budget():
    """The budget gates requests; it never edits what a fetch returned."""
    clock = Clock()
    b = budget(clock)
    snap = Snapshot([{"id": 1}], "2026-11-27T10:00:00+00:00")

    async def fetch():
        await b.acquire(1)
        return snap

    async def run():
        assert (await FeedCache().get("k", 60, fetch)) == snap

    asyncio.run(run())
