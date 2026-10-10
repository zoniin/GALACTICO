"""How every new request runs: errors, budgets, the result cache, the boundary check.

Claim: a new lab endpoint maps its failures to one set of status codes, gives its
tools at most a server-owned wall-clock budget, computes an identical in-flight
request once, lets at most sixteen requests past the cache lookup and refuses the
next one at once, runs at most two long computations at a time, and returns a
response whose provenance names the hosted providers, none of whose keys is a
banned key or holds a banned key part, and none of whose strings outside
provenance carries a banned word outside a named denial. Each rule has one home,
here, so five routers cannot hold five versions of it.

What a budget is: wall-clock seconds for the whole request, checked between
solves. It starts when the handler starts, so reading the corpus, waiting for a
place and waiting for an identical request in flight are inside it; none of them
is interrupted by it, so a request can last its budget plus one build, or as long
as the request it waits for. It is not the per-solve deterministic limit a tool
records in its certificate. A request that reaches its budget is a 200 that says
what was not evaluated; it is never called complete and never cached.

What the sixteen places are: a bound on worker threads, not on time. A request
whose reply is in memory takes none. Any other planning POST takes one where it
enters ``ResultCache.get_or_compute`` and keeps it until it returns or raises;
with all sixteen held the next is a 429 at once, with ``Retry-After``. A GET
route, a page and a static file never ask for one. Without the bound, forty
requests waiting on one computation held every worker thread, and a stored reply
and a static file waited with them.

What ``finalize`` checks: the provider set, every key (thirteen whole keys and
eight parts of a key, ``domain.thesis``) and the words of every string value
outside a provenance subtree (``domain.labels``), in a computed reply and in one
read from the result store. An error body does not pass through it. It is a guard
on the envelope, not evidence about the numbers inside it. A violation is a fault
of the server and is a 500: ``BoundaryViolation`` passes through ``lab_errors``
untouched, although it is a ``ValueError``.

Non-claim: no copy, no markup, no football definition (those are ``api/shell.py``
and the labs). ``KeyError`` is not mapped: a missing key inside a tool is an
internal fault, and reporting it as "unknown scenario" would blame the client. A
handler resolves its scenario first and raises its own 404.

The MATCH scenario bridge returns the same cached snapshot XI Lab solves on, so
a new endpoint and ``/api/xi/solve`` share ``dataset_hash`` and fingerprints.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Collection, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError

from ..domain import labels, thesis, verdicts
from . import decision_lab
from .decision_lab import DecisionRoute

__all__ = [
    "RUNTIME_VERSION",
    "HOSTED_PROVIDERS",
    "WORLD_MENU",
    "PRECOMPUTED_WORLDS",
    "COMPLETE_TOKENS",
    "BUDGETS",
    "LONG_ROUTES",
    "LONG_JOB_LIMIT",
    "LONG_JOB_WAIT_SECONDS",
    "MIN_REMAINING_SECONDS",
    "IN_FLIGHT_LIMIT",
    "IN_FLIGHT_BUSY",
    "RETRY_AFTER_SECONDS",
    "RESULT_STORE_DIR",
    "RESULT_STORE_ENV",
    "LongJobsBusy",
    "TooManyRequests",
    "BoundaryViolation",
    "Budget",
    "ResultCache",
    "RESULTS",
    "budget_for",
    "is_complete",
    "dumps",
    "source_fingerprint",
    "cache_key",
    "match_scenario",
    "match_snapshot",
    "lab_errors",
    "long_job",
    "admission",
    "in_flight",
    "finalize",
    "respond",
    "router",
]

RUNTIME_VERSION = "lab-runtime-v1"
HOSTED_PROVIDERS: tuple[str, ...] = ("pappalardo",)
WORLD_MENU: tuple[int, ...] = (12, 40)
"""World counts a request may name. 0 is the point estimate only."""
PRECOMPUTED_WORLDS: tuple[int, ...] = (200,)
"""Served from the result store only, never computed inside a request."""
COMPLETE_TOKENS: tuple[str, ...] = ("EXACT", "COMPLETE")
"""The completeness values a cached response may carry. ``TIME_LIMIT`` is not one."""

CORPUS_UNAVAILABLE = "historical corpus unavailable"
LONG_JOBS_BUSY = "two long computations are already running"
PRECOMPUTED_ONLY = "this world count is served from precomputed results only"

_PACKAGE = Path(__file__).resolve().parents[1]
RESULT_STORE_ENV = "GALACTICO_RESULT_STORE"
RESULT_STORE_DIR: Path = _PACKAGE.parent / "data" / "public" / "derived" / "results"


class LongJobsBusy(RuntimeError):
    """Both long-computation places are taken and none came free in time."""


class BoundaryViolation(ValueError):
    """A response the server built must not leave it. Always a 500, never a 422."""


BUDGETS: Mapping[str, float] = MappingProxyType({
    # XI additions (ARCH-SPEC 5.6).
    "xi.ceilings": 10.0,
    "xi.conflict": 15.0,
    "xi.frontier": 30.0,
    "xi.risk.tail": 60.0,
    "xi.risk.regret": 150.0,
    "xi.split-sample": 60.0,
    # Squad and transfer routes (OR-SQUAD-SPEC 11.4; its time_budget_seconds defaults).
    "squad.depth": 20.0,
    "squad.stress": 30.0,
    "squad.brief": 20.0,
    "transfer.injection": 45.0,
    "transfer.injection.detail": 30.0,
    "transfer.retention": 20.0,
})
"""Route name -> wall-clock seconds. Server-owned: a client may ask for less, never more."""

LONG_ROUTES: frozenset[str] = frozenset({"xi.risk.regret", "squad.stress", "transfer.injection"})
"""Routes that enumerate (every absence set, every candidate, every world optimum)."""

LONG_JOB_LIMIT = 2
LONG_JOB_WAIT_SECONDS = 5.0
_LONG_JOBS = threading.BoundedSemaphore(LONG_JOB_LIMIT)

MIN_REMAINING_SECONDS = 0.001
"""What a spent budget still hands a tool. Every squad and transfer tool refuses a time
limit that is not positive with a ``ValueError``, which ``lab_errors`` would report as
a 422. With this the tool starts, finds its deadline passed and answers ``DEADLINE``."""

IN_FLIGHT_LIMIT = 16
"""Most requests that may be past the cache lookup at once: computing, waiting for a place
or a build, or waiting for an identical request in flight. The seventeenth is refused at
once. Handlers and file reads run in the thread pool of the ASGI stack, 40 threads by
default, and a request that waits holds one. The bound is well below 40, so the planning
routes alone cannot hold every thread: whatever these sixteen wait for, a stored reply, a
catalogue, a page and a static file still find one."""
IN_FLIGHT_BUSY = f"{IN_FLIGHT_LIMIT} requests are already in progress"
RETRY_AFTER_SECONDS = 5
"""The ``Retry-After`` of every 429. ``LONG_JOB_WAIT_SECONDS``, rounded: the longest this
server itself waits for a place. A hint to the client, not a promise that a place is free."""


class TooManyRequests(RuntimeError):
    """Every place for a request past the cache lookup is taken. Refused at once: no wait."""

    def __init__(self, message: str = IN_FLIGHT_BUSY) -> None:
        super().__init__(message)


class _Places:
    """A fixed number of places, each taken or refused at once. Nothing waits here."""

    def __init__(self, limit: int) -> None:
        if type(limit) is not int or limit < 1:
            raise ValueError("a set of places holds at least one")
        self.limit = limit
        self._held = 0
        self._guard = threading.Lock()

    @property
    def held(self) -> int:
        return self._held

    def take(self) -> bool:
        with self._guard:
            if self._held >= self.limit:
                return False
            self._held += 1
            return True

    def give_back(self) -> None:
        with self._guard:
            if self._held <= 0:
                # More returns than takes would let a seventeenth request in later.
                raise RuntimeError("a place was given back that nobody held")
            self._held -= 1


_IN_FLIGHT = _Places(IN_FLIGHT_LIMIT)


def in_flight() -> int:
    """How many of the ``IN_FLIGHT_LIMIT`` places are held now."""
    return _IN_FLIGHT.held


@contextmanager
def admission() -> Iterator[None]:
    """Hold one of the ``IN_FLIGHT_LIMIT`` places for the block, or raise at once.

    ``TooManyRequests`` (a 429 with ``Retry-After`` inside ``lab_errors``) when every place
    is held. It never waits. The place goes back on every way out of the block: a return,
    a refusal, an error. The one caller is ``ResultCache.get_or_compute``, which every
    planning POST handler passes through; see there for what is and is not counted.
    """
    places = _IN_FLIGHT  # read once: the place goes back to the set it was taken from
    if not places.take():
        raise TooManyRequests()
    try:
        yield
    finally:
        places.give_back()


@dataclass
class Budget:
    """Wall-clock seconds one request may spend, counted from ``started``."""

    seconds: float
    # Read through the module at each start, so a test can move the clock under a request.
    started: float = field(default_factory=lambda: time.monotonic())

    def __post_init__(self) -> None:
        if isinstance(self.seconds, bool) or not isinstance(self.seconds, (int, float)) \
                or not math.isfinite(self.seconds) or self.seconds <= 0:
            raise ValueError("a budget is a positive, finite number of seconds")

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def remaining(self) -> float:
        """Seconds left, to pass to a tool as its total time limit. Never zero.

        A spent budget returns ``MIN_REMAINING_SECONDS``, not 0: the tool then reports
        what it could not evaluate, where a zero would be refused as a bad argument.
        Ask ``expired()`` whether the budget is spent; never test this against zero.
        """
        return max(MIN_REMAINING_SECONDS, self.seconds - self.elapsed())

    def expired(self) -> bool:
        return self.elapsed() >= self.seconds

    def report(self, completeness: str) -> dict[str, object]:
        """What the envelope says about time. ``completeness`` is the tool's own token."""
        return {
            "budget_seconds": float(self.seconds),
            "elapsed_seconds": round(self.elapsed(), 3),
            "completeness": completeness,
        }


def budget_for(route: str, requested: float | None = None) -> Budget:
    """The budget of ``route``, lowered to ``requested`` when the client asked for less.

    ``BUDGETS[route]`` is the ceiling: a request cannot raise it. An unknown route
    is a ``KeyError`` (an internal fault), not a default.
    """
    ceiling = BUDGETS[route]
    if requested is None:
        return Budget(ceiling)
    return Budget(min(Budget(requested).seconds, ceiling))


def is_complete(payload: object) -> bool:
    """Whether every ``completeness`` field of a payload is EXACT or COMPLETE.

    A payload with no such field is not complete: nothing in it says so, and a
    response that is merely silent about a deadline must not be cached as final.
    """
    seen: list[object] = []

    def walk(node: object) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                if key == "completeness":
                    seen.append(value)
                else:
                    walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(payload)
    return bool(seen) and all(isinstance(v, str) and v in COMPLETE_TOKENS for v in seen)


def dumps(payload: dict) -> bytes:
    """The one serialisation of a response: strict JSON, UTF-8, no NaN, no infinity.

    A NaN, an infinity or a value ``json`` cannot encode (a NumPy integer, a
    dataclass) raises ``BoundaryViolation``. Missing is ``None``, never NaN.
    """
    try:
        return json.dumps(payload, allow_nan=False, ensure_ascii=False).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise BoundaryViolation(f"response is not strict JSON: {exc}") from exc


def _lf_digest(data: bytes) -> str:
    # The rule of galactico.validation.digests (CRLF read as LF, nothing else), restated
    # because product code may not import a validation module. Equal by test.
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


@lru_cache(maxsize=1)
def source_fingerprint() -> str:
    """Digest of every optimisation and API source file, read once per process.

    A stored result is keyed on it, so a code change makes every stored file
    unreachable and a stale result cannot be served. Read on first use of the
    store, not at import: with the store off no source file is read.
    """
    files = sorted(
        [*(_PACKAGE / "optimization").rglob("*.py"), *(_PACKAGE / "api").glob("*.py")],
        key=lambda path: path.relative_to(_PACKAGE).as_posix(),
    )
    return _lf_digest(b"".join(path.read_bytes().replace(b"\r\n", b"\n") for path in files))


def _env_store_dir() -> Path | None:
    return RESULT_STORE_DIR if os.environ.get(RESULT_STORE_ENV) == "1" else None


@dataclass
class _Flight:
    lock: threading.Lock = field(default_factory=threading.Lock)
    waiters: int = 0


class ResultCache:
    """Serialised complete responses, least recently used first out, computed once per key.

    ``get_or_compute`` looks in memory, then in the result store when one is
    enabled, then computes. Two identical requests in flight compute once: the
    second waits on the first's lock and is served its bytes. ``store(payload)``
    decides whether a computed payload is kept; a payload that is not kept is
    returned to its caller and computed again for the next one.

    A reply found in memory is returned at once and is not counted. Everything after
    that lookup happens inside one of the ``IN_FLIGHT_LIMIT`` places (``admission``).

    The store directory is read, never written, by this class.
    """

    def __init__(self, max_entries: int = 64, max_bytes: int = 32 * 1024 * 1024, *,
                 store_dir: Path | None = None) -> None:
        if max_entries < 1 or max_bytes < 1:
            raise ValueError("a result cache holds at least one entry and one byte")
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self.store_dir = store_dir if store_dir is not None else _env_store_dir()
        self._entries: OrderedDict[tuple[str, ...], bytes] = OrderedDict()
        self._bytes = 0
        self._guard = threading.Lock()
        self._flights: dict[tuple[str, ...], _Flight] = {}

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def stored_bytes(self) -> int:
        return self._bytes

    def store_path(self, key: tuple[str, ...]) -> Path | None:
        """Where the precomputed result of ``key`` lives; ``None`` when the store is off."""
        if self.store_dir is None:
            return None
        name = json.dumps([list(key), source_fingerprint()], separators=(",", ":"))
        return self.store_dir / f"{hashlib.sha256(name.encode('utf-8')).hexdigest()}.json"

    def get_or_compute(self, key: tuple[str, ...], compute: Callable[[], dict], *,
                       store: Callable[[dict], bool],
                       precomputed_only: bool = False) -> tuple[bytes, bool]:
        """``(bytes, hit)``. ``hit`` is true when ``compute`` did not run for this caller.

        ``precomputed_only`` is for a world count in ``PRECOMPUTED_WORLDS``: with
        no stored result it raises ``ValueError`` (a 422) instead of computing.

        A key that is in memory is returned at once: it takes no place and waits for
        nobody. Any other request must hold one of the ``IN_FLIGHT_LIMIT`` places from
        here until it returns or raises, and when every place is held it raises
        ``TooManyRequests`` at once, having computed nothing and joined no flight. What
        holds a place: a computation, with the builds and long-computation places it
        waits for inside ``compute``; a read of the result store; and a request that
        waits for an identical request in flight. That last wait has no time limit of
        its own. The request holds its place, and its worker thread, until the request
        ahead of it returns or fails, and if that one fails it computes in its turn.
        A failure is not shared: behind a request refused for want of a long-computation
        place, each identical request asks for a place in its own turn and can be
        refused ``LONG_JOB_WAIT_SECONDS`` after the one before it. Sixteen places bound
        how many threads can be waiting like that; they do not shorten the wait.
        """
        key = tuple(key)
        with self._guard:
            data = self._hit(key)
        if data is not None:
            return data, True
        with admission():
            with self._guard:
                flight = self._flights.setdefault(key, _Flight())
                flight.waiters += 1
            try:
                with flight.lock:
                    # Stored by the request ahead of this one, or since the first look.
                    with self._guard:
                        data = self._hit(key)
                    if data is None:
                        data = self._from_store(key)
                        if data is not None:
                            with self._guard:
                                self._put(key, data)
                    if data is not None:
                        return data, True
                    if precomputed_only:
                        raise ValueError(PRECOMPUTED_ONLY)
                    payload = compute()
                    data = dumps(payload)
                    if store(payload):
                        with self._guard:
                            self._put(key, data)
                    return data, False
            finally:
                with self._guard:
                    flight.waiters -= 1
                    if flight.waiters == 0 and self._flights.get(key) is flight:
                        del self._flights[key]

    def _hit(self, key: tuple[str, ...]) -> bytes | None:
        data = self._entries.get(key)
        if data is not None:
            self._entries.move_to_end(key)
        return data

    def _put(self, key: tuple[str, ...], data: bytes) -> None:
        if len(data) > self.max_bytes:
            return  # larger than the whole cache: returned to its caller, kept by nobody
        previous = self._entries.pop(key, None)
        if previous is not None:
            self._bytes -= len(previous)
        self._entries[key] = data
        self._bytes += len(data)
        while len(self._entries) > self.max_entries or self._bytes > self.max_bytes:
            _, evicted = self._entries.popitem(last=False)
            self._bytes -= len(evicted)

    def _from_store(self, key: tuple[str, ...]) -> bytes | None:
        path = self.store_path(key)
        if path is None or not path.is_file():
            return None
        data = path.read_bytes()
        try:
            payload = json.loads(data)
        except ValueError as exc:
            raise BoundaryViolation(f"stored result {path.name} is not JSON") from exc
        if not is_complete(payload):
            raise BoundaryViolation(f"stored result {path.name} is not a complete response")
        # A stored file leaves the server like a computed reply, so it passes the same
        # check: providers, keys and the words of its strings. The store has no route to
        # ask for exempt key paths, and no caller of ``finalize`` passes any.
        finalize(payload)
        return data


RESULTS = ResultCache()


def cache_key(route: str, request: BaseModel | Mapping[str, object],
              dataset_hash: str) -> tuple[str, ...]:
    """Route, dataset and the canonical request. Tool versions are in the payload's provenance.

    ``request`` is a model, keyed as it was sent, or a mapping a router has already resolved
    (``planning.canonical_request``), keyed as it is. ``dataset_hash`` is any identity of the
    data the request reads: a dataset hash, or ``planning.corpus_token``.
    """
    body = request.model_dump(mode="json") if isinstance(request, BaseModel) else dict(request)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return (route, dataset_hash, hashlib.sha256(canonical.encode("utf-8")).hexdigest())


def match_scenario(scenario_id: str) -> dict:
    """The ``decision_lab.SCENARIOS`` entry itself. ``KeyError`` for anything else."""
    return decision_lab.SCENARIOS[scenario_id]


def match_snapshot(scenario_id: str, worlds: int):
    """The cached snapshot XI Lab solves on, for a MATCH scenario and a menu world count."""
    if isinstance(worlds, bool) or not isinstance(worlds, int) \
            or (worlds != 0 and worlds not in WORLD_MENU):
        menu = ", ".join(str(count) for count in (0, *WORLD_MENU))
        raise ValueError(f"bootstrap worlds must be one of {menu}")
    return decision_lab.snapshot(match_scenario(scenario_id)["match_id"], worlds)


def _retry_after() -> dict[str, str]:
    return {"Retry-After": str(RETRY_AFTER_SECONDS)}


@contextmanager
def lab_errors(*, not_found: str = "unknown scenario") -> Iterator[None]:
    """Map what a loader or a tool raises to the status a client should see.

    ``OSError`` (a file that is absent, ``FileNotFoundError``, or cannot be read) -> 503,
    ``ValueError`` -> 422 with the tool's own sentence, ``LongJobsBusy`` and
    ``TooManyRequests`` -> 429, each with its own sentence and a ``Retry-After`` header of
    ``RETRY_AFTER_SECONDS``.
    ``KeyError`` and ``BoundaryViolation`` pass through and are a 500. An
    ``HTTPException`` raised inside passes through too. A pydantic ``ValidationError``
    is a 422 that lists location, message and type and never the rejected value.

    One ``ValueError`` is not a refusal: the one Arrow raises on a file that is not the
    Parquet it is named as. That is the corpus, not the client, and is a 503 too; Arrow's
    sentence is not sent. A plain ``ValueError`` a library raises cannot be told from a
    tool's own by its type and is still a 422.

    ``not_found`` is accepted so the specified call shape works, and is not used:
    nothing raised in the block is turned into a 404. The handler raises its own,
    with its own detail, before the block or inside it.
    """
    try:
        yield
    except BoundaryViolation:
        raise
    except ValidationError as exc:
        # A ValueError whose text embeds the rejected input. Same shape as DecisionRoute.
        raise HTTPException(422, detail=[
            {key: error[key] for key in ("loc", "msg", "type") if key in error}
            for error in exc.errors()
        ]) from exc
    except LongJobsBusy as exc:
        raise HTTPException(429, LONG_JOBS_BUSY, headers=_retry_after()) from exc
    except TooManyRequests as exc:
        raise HTTPException(429, IN_FLIGHT_BUSY, headers=_retry_after()) from exc
    except OSError as exc:
        raise HTTPException(503, CORPUS_UNAVAILABLE) from exc
    except ValueError as exc:
        if type(exc).__module__.partition(".")[0] == "pyarrow":  # ArrowInvalid: a damaged file
            raise HTTPException(503, CORPUS_UNAVAILABLE) from exc
        raise HTTPException(422, str(exc)) from exc


@contextmanager
def long_job(route: str) -> Iterator[None]:
    """Hold one of the two long-computation places while a ``LONG_ROUTES`` route computes.

    Any other known route passes straight through. A route with no budget is a
    ``KeyError``: a misspelt name must not skip the limit.
    """
    if route not in BUDGETS:
        raise KeyError(route)
    if route not in LONG_ROUTES:
        yield
        return
    if not _LONG_JOBS.acquire(timeout=LONG_JOB_WAIT_SECONDS):
        raise LongJobsBusy(LONG_JOBS_BUSY)
    try:
        yield
    finally:
        _LONG_JOBS.release()


def _hosted(providers: object) -> bool:
    return isinstance(providers, (list, tuple)) \
        and all(isinstance(name, str) for name in providers) \
        and sorted(providers) == list(HOSTED_PROVIDERS)


def _require_hosted_providers(payload: object) -> None:
    provenance = payload.get("provenance") if isinstance(payload, Mapping) else None
    providers = provenance.get("providers") if isinstance(provenance, Mapping) else None
    if not _hosted(providers):
        raise BoundaryViolation(
            f"provenance.providers must be exactly {list(HOSTED_PROVIDERS)}; got {providers!r}"
        )

    # The envelope's list is not the only lineage in a response: a universe, a reference
    # or a row carries its own. None of it may name anyone else.
    def walk(node: object, path: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                here = f"{path}.{key}" if path else str(key)
                if (key == "providers" and not _hosted(value)) \
                        or (key == "provider" and value not in HOSTED_PROVIDERS):
                    raise BoundaryViolation(
                        f"{here} names a provider outside {list(HOSTED_PROVIDERS)}: {value!r}"
                    )
                walk(value, here)
        elif isinstance(node, (list, tuple)):
            for position, value in enumerate(node):
                walk(value, f"{path}[{position}]")

    walk(payload, "")


def finalize(payload: dict, *, allow_keys: Collection[str] = ()) -> dict:
    """The boundary check of every new response. Returns the same object, unchanged.

    (1) ``payload["provenance"]["providers"]`` is exactly the hosted provider set, and
    no ``providers`` or ``provider`` key at any depth names anyone else.
    (2) No key at any depth, provenance included, is refused by the key walker
    (``thesis.banned_key_paths``). Two things are refused, and nothing else. A key that is
    one of the thirteen ``thesis.BANNED_KEYS`` as a whole (``rating``, ``score``, ``rank``,
    ``fit_score`` and the like), whatever its case and separators. And a key one of whose
    parts is one of the eight ``thesis.BANNED_KEY_PARTS``: rating, ratings, rank, ranks,
    ranking, ranked, merit, overall. A part is what an underscore, a hyphen, whitespace or
    a change of case separates, so ``xi_rating``, ``overall_score`` and ``playerMerit`` are
    refused and ``outranking`` is not. ``score``, ``tier``, ``fit`` and ``best`` are not
    parts: ``home_score``, the data ``tier`` of a verdict and ``best_xi`` pass this check.
    So it is narrower than "no key reads like a rating": a key under another name passes.
    ``allow_keys`` names exempt paths in the walker's grammar; no route passes any.
    (3) No string value, at any depth outside a ``provenance`` subtree, contains a word the
    copy guard bans outside a named denial (``labels.scan_labels``). Keys are not read by
    the copy guard here, strings under provenance are not read, and an error body never
    comes this way.
    Any failure is a ``BoundaryViolation``, which names the path and the word and never
    the sentence around it.
    """
    _require_hosted_providers(payload)
    found = thesis.banned_key_paths(payload, parts=thesis.BANNED_KEY_PARTS, allow=allow_keys)
    if found:
        raise BoundaryViolation(f"banned keys in response: {found}")
    found_labels = labels.scan_labels(payload, keys=False)
    if found_labels:
        raise BoundaryViolation(f"banned words in served labels: {found_labels[:5]}")
    return payload


def respond(payload_or_bytes: dict | bytes, *, cache_hit: bool = False) -> Response:
    """A JSON response from a payload or from bytes the cache already serialised."""
    body = payload_or_bytes if isinstance(payload_or_bytes, bytes) else dumps(payload_or_bytes)
    return Response(
        content=body,
        media_type="application/json",
        headers={"X-Galactico-Cache": "hit" if cache_hit else "miss"},
    )


VERDICTS_ORDER = "experiment_id, subject_id ascending"
VERDICTS_CLAIM = (
    "Registered protocols and their recorded verdicts. "
    "A verdict labels a quantity; it is not a property of a player."
)

router = APIRouter(route_class=DecisionRoute)


@router.get("/api/evidence/verdicts")
def evidence_verdicts() -> Response:
    """Every registered verdict. Corpus-free: the registry is a module, not a data file."""
    payload = {
        "verdicts": verdicts.all_payloads(),
        "order": VERDICTS_ORDER,
        "claim": VERDICTS_CLAIM,
        "provenance": {"providers": list(HOSTED_PROVIDERS)},
    }
    return respond(finalize(payload))
