"""The football-data.org request budget: one limiter per process, and a cap per page view.

The free plan allows 10 requests a minute per key, and every consumer of the key spends the
same minute: other instances, preview deployments, local development, the smoke probe. So
the limiter believes the reply headers over its own count (PLATFORM 3.4):

- ``X-Requests-Available-Minute`` lowers the tokens left, less ``reserve`` kept for the
  other consumers, and never raises them;
- ``X-RequestCounter-Reset`` says when the window refills;
- a 429 blocks every request until the reset, plus one second.

Each request has a priority. A class spends only while more than its reserve is left
(``RESERVES``): the live overlay (P0) can spend the last request, a reader's cold resource
(P1) stops at two, scheduled warming (P2) at four and speculative search fill (P3) at six.

A reader's request never waits more than ``MAX_WAIT`` for a request to become available. It
raises ``Deferred`` instead, and makes no request: the view serves what is cached, or a
partial page, and says when it updates.

``RequestBudget`` is the cap of one page view (PLAN 3.6): at most ``max_calls`` upstream
requests and a deadline. A route opens one around the view (``with RequestBudget(2):``); it
lives in a context variable, so ``Budget.acquire`` charges whichever view is current, and
tasks the view starts share it. The client calls ``Budget.acquire`` before each upstream
request and nothing else: acquire checks and charges the view's cap too.

Claim: with headers, the process never spends more than the server says is left, less the
reserve, beyond the requests already in flight. Non-claim: instances do not coordinate
except through those headers; the per-instance count before the first reply is a guess.
"""

from __future__ import annotations

import asyncio
import contextvars
import math
import threading
from collections.abc import Awaitable, Callable, Mapping
from time import monotonic
from typing import Literal

from ..feed import FeedError

__all__ = ["Budget", "Deferred", "Priority", "RequestBudget", "RESERVES", "MAX_WAIT"]

Priority = Literal[0, 1, 2, 3]

RESERVES: dict[int, int] = {0: 0, 1: 2, 2: 4, 3: 6}
"""Priority class -> it spends only while more than this many requests are left."""

MAX_WAIT = 0.3
"""Seconds a request may wait for the budget, in total, before it is deferred."""

WINDOW = 60.0
"""The provider's counter window, in seconds, used until a reply states its reset."""

BLOCK_MARGIN = 1.0
"""Seconds added to a 429's reset before the next request."""

BLOCK_WITHOUT_RESET = 60.0
"""How long a 429 blocks when its reply does not say when the counter resets."""

DEFERRED_LINE = "Part of this page is still loading. Reload in a minute to see the rest."
"""What a reader may be shown for a deferred request. It names no key, plan or quota."""

_AVAILABLE = "x-requests-available-minute"
_RESET = "x-requestcounter-reset"


class Deferred(FeedError):
    """No request was made: the minute's budget, the view's cap or its deadline was reached.

    ``str()`` is the reader's line (``FeedCache`` serves it as the stale result's warning);
    ``reason`` is one word for logs and tests: "minute", "blocked", "view" or "deadline".
    ``retry_after`` is how many seconds until this process could make the request: 0 when
    only this view's cap or deadline refused it, since another view may make it at once.
    """

    def __init__(self, reason: str, retry_after: float = 0.0) -> None:
        super().__init__(DEFERRED_LINE)
        self.reason = reason
        self.retry_after = retry_after


_CURRENT: contextvars.ContextVar[RequestBudget | None] = contextvars.ContextVar(
    "season_request_budget", default=None)


class RequestBudget:
    """The upstream requests one page view may make: at most ``max_calls``, before ``deadline``
    seconds have passed since it was opened.

    ``spent`` counts the requests charged, and ``deferred`` the requests refused while it was
    current, whatever refused them. A view with ``partial`` set renders what it has, says so,
    and gets the degraded CDN lifetime.
    """

    def __init__(self, max_calls: int, deadline: float = 3.0, *,
                 clock: Callable[[], float] = monotonic) -> None:
        if max_calls < 0 or deadline < 0:
            raise ValueError("a request budget needs a cap and a deadline of at least zero")
        self.max_calls = max_calls
        self.deadline = deadline
        self._clock = clock
        self._opened = clock()
        self.spent = 0
        self.deferred = 0
        self._tokens: list[contextvars.Token] = []

    @property
    def partial(self) -> bool:
        return self.deferred > 0

    def time_left(self) -> float:
        return max(0.0, self.deadline - (self._clock() - self._opened))

    def charge(self) -> None:
        """Count one upstream request against this view, or raise ``Deferred`` (and count the
        refusal) when the view may not make another."""
        if self.spent >= self.max_calls:
            self.deferred += 1
            raise Deferred("view")
        if self.time_left() <= 0:
            self.deferred += 1
            raise Deferred("deadline")
        self.spent += 1

    def _refund(self) -> None:
        """A charged request that was then deferred by the minute's budget."""
        self.spent -= 1
        self.deferred += 1

    def __enter__(self) -> RequestBudget:
        self._tokens.append(_CURRENT.set(self))
        return self

    def __exit__(self, *exc: object) -> None:
        _CURRENT.reset(self._tokens.pop())

    @staticmethod
    def current() -> RequestBudget | None:
        """The view budget of the running request, or ``None`` outside one."""
        return _CURRENT.get()


def _whole(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


class Budget:
    """The process's limiter for one key: ``per_minute`` requests a window, corrected by the
    reply headers, less ``reserve`` kept for the key's other consumers."""

    def __init__(self, per_minute: int = 10, reserve: int = 2,
                 clock: Callable[[], float] = monotonic, *,
                 sleep: Callable[[float], Awaitable[object]] = asyncio.sleep,
                 max_wait: float = MAX_WAIT) -> None:
        if per_minute < 1 or not 0 <= reserve < per_minute:
            raise ValueError("a budget needs at least one request a minute and a smaller reserve")
        self.per_minute = per_minute
        self.reserve = reserve
        self.max_wait = max_wait
        self._clock = clock
        self._sleep = sleep
        self._tokens = per_minute
        self._refill_at: float | None = None
        self._blocked_until = -math.inf
        self._lock = threading.Lock()

    # -- state, as of now

    def _refresh(self, now: float) -> None:
        if self._refill_at is not None and now >= self._refill_at:
            self._tokens = self.per_minute
            self._refill_at = None

    @property
    def tokens(self) -> int:
        """Requests left in this window, as this process knows them."""
        with self._lock:
            self._refresh(self._clock())
            return self._tokens

    @property
    def blocked_until(self) -> float | None:
        """The clock time before which no request is made, if one is set and still ahead."""
        with self._lock:
            ahead = self._blocked_until > self._clock()
            return self._blocked_until if ahead else None

    def _take(self, priority: int, now: float) -> float | None:
        """Take one request now (``None``), or say how many seconds until one could be had."""
        self._refresh(now)
        if now < self._blocked_until:
            return self._blocked_until - now
        if self._tokens > RESERVES[priority]:
            self._tokens -= 1
            if self._refill_at is None:
                self._refill_at = now + WINDOW
            return None
        return (self._refill_at - now) if self._refill_at is not None else WINDOW

    # -- the three calls the client makes

    async def acquire(self, priority: Priority) -> None:
        """Wait at most ``max_wait`` for one request of class ``priority``, then return; or
        raise ``Deferred`` having made none. Charges the current view's ``RequestBudget``."""
        if priority not in RESERVES or isinstance(priority, bool):
            raise ValueError(f"{priority!r} is not a priority class (0 to 3)")
        view = RequestBudget.current()
        if view is not None:
            view.charge()
        try:
            await self._wait_for(priority, view)
        except Deferred:
            if view is not None:
                view._refund()
            raise

    async def _wait_for(self, priority: int, view: RequestBudget | None) -> None:
        limit = self.max_wait if view is None else min(self.max_wait, view.time_left())
        started, slept = self._clock(), 0.0
        while True:
            with self._lock:
                now = self._clock()
                wait = self._take(priority, now)
                blocked = now < self._blocked_until
            if wait is None:
                return
            # The waits so far (as the clock measured them, or as asked if the clock says less)
            # and this one: a wait that would end past the limit is not begun.
            if max(now - started, slept) + wait > limit:
                raise Deferred("blocked" if blocked else "minute", retry_after=wait)
            await self._sleep(wait)
            slept += wait

    def observe(self, headers: Mapping[str, str], status: int) -> None:
        """Read a reply's rate headers (any letter case) and status."""
        fields = {str(name).lower(): value for name, value in headers.items()}
        available = _whole(fields.get(_AVAILABLE))
        reset = _whole(fields.get(_RESET))
        if reset is not None and reset < 0:
            reset = None
        with self._lock:
            now = self._clock()
            self._refresh(now)
            if status == 429:
                wait = float(reset) if reset is not None else BLOCK_WITHOUT_RESET
                self._tokens = 0
                self._refill_at = now + wait
                self._blocked_until = max(self._blocked_until, now + wait + BLOCK_MARGIN)
                return
            if available is not None:
                self._tokens = max(0, min(self._tokens, available - self.reserve))
            if reset is not None:
                self._refill_at = now + reset
            elif self._tokens < self.per_minute and self._refill_at is None:
                self._refill_at = now + WINDOW

    def block_until(self, t: float) -> None:
        """Make no request before clock time ``t`` (a later block already set stands)."""
        with self._lock:
            self._blocked_until = max(self._blocked_until, t)
