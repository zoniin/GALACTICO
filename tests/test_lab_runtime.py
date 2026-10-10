"""How a new request runs, tested without a corpus.

Each test targets one rule a router would otherwise restate: which failure is
which status, who owns a budget, what may be cached, that two identical requests
compute once, that sixteen requests are past the cache lookup at once and the
next is refused without waiting, that a response naming another provider or
carrying a rating key does not leave the server, computed or read from the store.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import threading
import time
from contextlib import ExitStack
from pathlib import Path

import anyio
import anyio.to_thread
import numpy as np
import pytest
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from galactico.api import decision_lab, runtime
from galactico.domain import labels, thesis, verdicts
from galactico.validation.digests import lf_sha256_text


def _envelope(**extra) -> dict:
    return {"value": 1, "completeness": "COMPLETE",
            "provenance": {"providers": ["pappalardo"]}, **extra}


# ---------------------------------------------------------------- error mapping

@pytest.mark.parametrize(("raised", "status", "detail"), [
    (FileNotFoundError("competition=Spain/actions.parquet"), 503, "historical corpus unavailable"),
    (ValueError("unknown lock id 99"), 422, "unknown lock id 99"),
    (runtime.LongJobsBusy(), 429, "two long computations are already running"),
    (runtime.TooManyRequests(), 429, "16 requests are already in progress"),
])
def test_lab_errors_maps_each_failure_to_its_status(raised, status, detail):
    with pytest.raises(HTTPException) as caught, runtime.lab_errors():
        raise raised
    assert (caught.value.status_code, caught.value.detail) == (status, detail)
    assert caught.value.__cause__ is raised
    # A refusal for want of a place says when to ask again. No other failure does.
    assert caught.value.headers == ({"Retry-After": "5"} if status == 429 else None)


def test_a_damaged_or_unreadable_corpus_file_is_a_503_and_never_a_library_sentence(tmp_path):
    import pandas as pd

    damaged = tmp_path / "actions.parquet"
    damaged.write_bytes(b"not parquet at all")
    # Non-vacuity: what a loader raises on such a file is a ValueError carrying Arrow's text.
    with pytest.raises(ValueError, match="Parquet") as arrow:
        pd.read_parquet(damaged)
    assert type(arrow.value).__module__.startswith("pyarrow")
    for raised in (arrow.value, PermissionError(13, "Permission denied", str(damaged)),
                   OSError("the device is not ready")):
        with pytest.raises(HTTPException) as caught, runtime.lab_errors():
            raise raised
        assert (caught.value.status_code, caught.value.detail) \
            == (503, "historical corpus unavailable")
        assert caught.value.__cause__ is raised
    # Opposite case: a refusal this repository wrote is still a 422 with its own sentence.
    with pytest.raises(HTTPException) as caught, runtime.lab_errors():
        runtime.Budget(0)
    assert (caught.value.status_code, caught.value.detail) \
        == (422, "a budget is a positive, finite number of seconds")


def test_lab_errors_leaves_internal_faults_and_handler_statuses_alone():
    # A missing key inside a tool is a 500, whatever not_found says.
    with pytest.raises(KeyError), runtime.lab_errors(not_found="unknown squad scenario"):
        raise KeyError("progression")
    with pytest.raises(HTTPException) as caught, runtime.lab_errors():
        raise HTTPException(404, "unknown squad scenario")
    assert caught.value.status_code == 404
    # A boundary violation is a ValueError and still not a 422.
    assert issubclass(runtime.BoundaryViolation, ValueError)
    with pytest.raises(runtime.BoundaryViolation), runtime.lab_errors():
        runtime.finalize({"value": 1})
    with pytest.raises(runtime.BoundaryViolation), runtime.lab_errors():
        runtime.respond({"value": float("nan")})
    with runtime.lab_errors():
        pass


def test_a_model_rejected_inside_the_block_is_a_422_that_echoes_no_value():
    # A pydantic ValidationError is a ValueError whose text embeds the rejected input.
    class Reference(BaseModel):
        model_config = ConfigDict(extra="forbid")
        team_id: int

    secret = "675; DROP TABLE players"
    with pytest.raises(HTTPException) as caught, runtime.lab_errors():
        Reference(team_id=secret)
    assert caught.value.status_code == 422
    assert caught.value.detail == [{
        "loc": ("team_id",), "type": "int_parsing",
        "msg": "Input should be a valid integer, unable to parse string as an integer",
    }]
    assert secret not in json.dumps(caught.value.detail)
    assert secret in str(caught.value.__cause__)        # non-vacuity: str(exc) would echo it


# ---------------------------------------------------------------- budgets

def test_budget_table_is_server_owned_and_pinned():
    assert dict(runtime.BUDGETS) == {
        "xi.ceilings": 10.0, "xi.conflict": 15.0, "xi.frontier": 30.0,
        "xi.risk.tail": 60.0, "xi.risk.regret": 150.0, "xi.split-sample": 60.0,
        "squad.depth": 20.0, "squad.stress": 30.0, "squad.brief": 20.0,
        "transfer.injection": 45.0, "transfer.injection.detail": 30.0,
        "transfer.retention": 20.0,
    }
    assert frozenset({"xi.risk.regret", "squad.stress", "transfer.injection"}) \
        == runtime.LONG_ROUTES <= set(runtime.BUDGETS)
    assert not [name for name in runtime.BUDGETS if name.startswith(("opponent", "desk"))]
    with pytest.raises(TypeError):
        runtime.BUDGETS["squad.depth"] = 600.0  # type: ignore[index]


def test_a_client_may_lower_a_budget_and_never_raise_it():
    assert runtime.budget_for("squad.stress").seconds == 30.0
    assert runtime.budget_for("squad.stress", 5).seconds == 5
    assert runtime.budget_for("squad.stress", 120).seconds == 30.0
    with pytest.raises(KeyError):
        runtime.budget_for("squad.audit")
    for bad in (0, -1, float("inf"), float("nan"), True):
        with pytest.raises(ValueError):
            runtime.budget_for("squad.stress", bad)


def test_budget_counts_wall_clock_from_its_start():
    fresh = runtime.Budget(10.0, started=time.monotonic() - 3.0)
    assert 6.5 < fresh.remaining() <= 7.0 and not fresh.expired()
    spent = runtime.Budget(1.0, started=time.monotonic() - 2.0)
    assert spent.remaining() == runtime.MIN_REMAINING_SECONDS and spent.expired()
    report = spent.report("TIME_LIMIT")
    assert set(report) == {"budget_seconds", "elapsed_seconds", "completeness"}
    assert report["budget_seconds"] == 1.0 and report["completeness"] == "TIME_LIMIT"
    assert report["elapsed_seconds"] == round(report["elapsed_seconds"], 3) >= 2.0
    assert not runtime.is_complete(report)
    assert runtime.is_complete(fresh.report("COMPLETE"))


def test_a_spent_budget_reaches_a_tool_as_a_passed_deadline_not_a_refused_argument():
    # The seam with the squad and transfer tools. Each refuses a time limit that is not
    # positive with a ValueError, and lab_errors reports a ValueError as a 422: a budget
    # spent while the inputs were built would blame the client for the server's clock.
    from galactico.optimization.squad.depth import squad_depth

    refusal = "time_limit must be a positive number of seconds"
    with pytest.raises(ValueError, match=refusal):      # non-vacuity: the refusal exists
        squad_depth(None, time_limit=0.0)
    spent = runtime.Budget(1.0, started=time.monotonic() - 2.0)
    assert spent.expired() and 0 < spent.remaining() <= 0.001
    # What a spent budget hands over passes that check; the call fails later, on the
    # snapshot this test does not build.
    with pytest.raises((AttributeError, TypeError)):
        squad_depth(None, time_limit=spent.remaining())


# ---------------------------------------------------------------- completeness

@pytest.mark.parametrize(("payload", "complete"), [
    ({"completeness": "COMPLETE"}, True),
    ({"completeness": "EXACT", "rows": [{"completeness": "COMPLETE"}]}, True),
    ({"completeness": "COMPLETE", "rows": [{"certificate": {"completeness": "TIME_LIMIT"}}]},
     False),
    ({"completeness": "DEADLINE"}, False),
    ({"completeness": None}, False),
    ({"value": 1}, False),             # silent about completeness is not complete
])
def test_only_a_payload_that_says_it_is_complete_everywhere_is_cacheable(payload, complete):
    assert runtime.is_complete(payload) is complete


# ---------------------------------------------------------------- result cache

def test_result_cache_serves_stored_bytes_and_computes_once():
    cache = runtime.ResultCache()
    assert (cache.max_entries, cache.max_bytes, cache.store_dir) == (64, 32 * 1024 * 1024, None)
    calls = []

    def compute() -> dict:
        calls.append(1)
        return _envelope(label="Atlético")

    first, hit_first = cache.get_or_compute(("r", "h", "q"), compute, store=runtime.is_complete)
    second, hit_second = cache.get_or_compute(("r", "h", "q"), compute, store=runtime.is_complete)
    assert (hit_first, hit_second, len(calls)) == (False, True, 1)
    assert first == second == runtime.dumps(_envelope(label="Atlético"))
    assert "Atlético".encode() in first        # UTF-8, not \u escapes
    assert json.loads(first)["label"] == "Atlético"


def test_an_incomplete_payload_is_returned_and_not_stored():
    cache = runtime.ResultCache()
    calls = []

    def compute() -> dict:
        calls.append(1)
        return _envelope(completeness="TIME_LIMIT", not_evaluated=7)

    for _ in range(2):
        data, hit = cache.get_or_compute(("k",), compute, store=runtime.is_complete)
        assert hit is False and json.loads(data)["not_evaluated"] == 7
    assert len(calls) == 2 and len(cache) == 0


def test_result_cache_evicts_least_recently_used_by_entries_and_by_bytes():
    def fill(cache: runtime.ResultCache, name: str, size: int = 1) -> bool:
        return cache.get_or_compute(
            (name,), lambda: {"pad": "x" * size, "completeness": "EXACT"},
            store=runtime.is_complete)[1]

    by_entries = runtime.ResultCache(max_entries=2)
    assert [fill(by_entries, n) for n in ("a", "b", "a", "c")] == [False, False, True, False]
    assert fill(by_entries, "a") is True       # touched, so "b" was the one evicted
    assert fill(by_entries, "b") is False and len(by_entries) == 2

    one = len(runtime.dumps({"pad": "x" * 100, "completeness": "EXACT"}))
    by_bytes = runtime.ResultCache(max_bytes=2 * one)
    assert [fill(by_bytes, n, 100) for n in ("a", "b", "c")] == [False, False, False]
    assert by_bytes.stored_bytes == 2 * one and len(by_bytes) == 2
    assert fill(by_bytes, "a", 100) is False   # evicted to make room for "c"
    assert fill(by_bytes, "huge", 1000) is False and fill(by_bytes, "huge", 1000) is False
    assert by_bytes.stored_bytes <= by_bytes.max_bytes


def test_identical_in_flight_requests_compute_once_and_distinct_ones_do_not_wait():
    cache = runtime.ResultCache()
    started, release = threading.Event(), threading.Event()
    calls, results = [], []

    def slow() -> dict:
        calls.append(1)
        started.set()
        assert release.wait(10)
        return _envelope()

    def request() -> None:
        results.append(cache.get_or_compute(("same",), slow, store=runtime.is_complete))

    threads = [threading.Thread(target=request) for _ in range(6)]
    threads[0].start()
    assert started.wait(10)
    for thread in threads[1:]:
        thread.start()
    # Non-vacuity: all six are in flight on the one key before the first may finish.
    deadline = time.monotonic() + 10
    while cache._flights[("same",)].waiters < 6:
        assert time.monotonic() < deadline
        time.sleep(0.001)
    # A different key is not behind the same lock: it completes while "same" is in flight.
    other = cache.get_or_compute(("other",), _envelope, store=runtime.is_complete)
    assert other[1] is False
    release.set()
    for thread in threads:
        thread.join(10)
    assert len(calls) == 1 and len(results) == 6
    assert sorted(hit for _, hit in results) == [False, True, True, True, True, True]
    assert len({data for data, _ in results}) == 1
    assert cache._flights == {}


def test_a_failed_computation_stores_nothing_and_releases_its_key():
    cache = runtime.ResultCache()

    def broken() -> dict:
        raise ValueError("unknown lock id 99")

    with pytest.raises(ValueError):
        cache.get_or_compute(("k",), broken, store=runtime.is_complete)
    assert cache._flights == {} and len(cache) == 0
    assert cache.get_or_compute(("k",), _envelope, store=runtime.is_complete)[1] is False
    with pytest.raises(runtime.BoundaryViolation):
        cache.get_or_compute(("nan",), lambda: _envelope(value=float("nan")),
                             store=runtime.is_complete)
    assert len(cache) == 1


def test_cache_key_is_route_dataset_and_canonical_request():
    class Query(BaseModel):
        model_config = ConfigDict(extra="forbid")
        scenario_id: str = "madrid-planning-2018-05-21"
        locks: list[int] = []
        k: int = 2

    request = Query(locks=[3, 1])
    canonical = '{"k":2,"locks":[3,1],"scenario_id":"madrid-planning-2018-05-21"}'
    assert runtime.cache_key("squad.stress", request, "abc") == (
        "squad.stress", "abc", hashlib.sha256(canonical.encode()).hexdigest())
    same = Query(k=2, scenario_id="madrid-planning-2018-05-21", locks=[3, 1])
    assert runtime.cache_key("squad.stress", same, "abc") == runtime.cache_key(
        "squad.stress", request, "abc")
    keys = {
        runtime.cache_key("squad.stress", request, "abc"),
        runtime.cache_key("squad.depth", request, "abc"),
        runtime.cache_key("squad.stress", request, "abd"),
        runtime.cache_key("squad.stress", Query(locks=[1, 3]), "abc"),
        runtime.cache_key("squad.stress", Query(locks=[3, 1], k=1), "abc"),
    }
    assert len(keys) == 5
    # A mapping is keyed as the model that dumps to it, so a router can key a request as it
    # resolved it and not as it was spelt.
    resolved = {"locks": [3, 1], "scenario_id": "madrid-planning-2018-05-21", "k": 2}
    assert runtime.cache_key("squad.stress", resolved, "abc") == runtime.cache_key(
        "squad.stress", request, "abc")
    assert runtime.cache_key("squad.stress", {**resolved, "locks": [1, 3]}, "abc") \
        == runtime.cache_key("squad.stress", Query(locks=[1, 3]), "abc")


# ---------------------------------------------------------------- precomputed results

def test_result_store_is_off_by_default_and_serves_only_complete_results(tmp_path, monkeypatch):
    assert runtime.RESULTS.store_dir is None and runtime.ResultCache().store_path(("k",)) is None
    monkeypatch.setenv(runtime.RESULT_STORE_ENV, "1")
    assert runtime.ResultCache().store_dir == runtime.RESULT_STORE_DIR
    monkeypatch.delenv(runtime.RESULT_STORE_ENV)

    monkeypatch.setattr(runtime, "source_fingerprint", lambda: "f" * 64)
    cache = runtime.ResultCache(store_dir=tmp_path)
    key = ("xi.risk.tail", "abc", "q")

    def never() -> dict:
        raise AssertionError("a precomputed result must not be computed in a request")

    with pytest.raises(ValueError, match="served from precomputed results only"):
        cache.get_or_compute(key, never, store=runtime.is_complete, precomputed_only=True)

    stored = runtime.dumps(_envelope(worlds=200))
    cache.store_path(key).write_bytes(stored)
    assert cache.get_or_compute(key, never, store=runtime.is_complete,
                                precomputed_only=True) == (stored, True)

    # A code change moves the fingerprint: the stored file is unreachable, not stale.
    written = cache.store_path(key)
    monkeypatch.setattr(runtime, "source_fingerprint", lambda: "0" * 64)
    moved = runtime.ResultCache(store_dir=tmp_path)
    assert moved.store_path(key) != written and written.is_file()
    with pytest.raises(ValueError, match="precomputed"):
        moved.get_or_compute(key, never, store=runtime.is_complete, precomputed_only=True)

    for bad in (_envelope(completeness="TIME_LIMIT"),
                {"completeness": "COMPLETE", "provenance": {"providers": ["statsbomb"]}}):
        moved.store_path(key).write_bytes(runtime.dumps(bad))
        with pytest.raises(runtime.BoundaryViolation):
            moved.get_or_compute(key, never, store=runtime.is_complete)
    assert list(tmp_path.iterdir()) and len(moved) == 0


@pytest.mark.parametrize(("planted", "refusal", "named"), [
    ({"players": [{"name": "A", "rating": 9.1}]}, "banned keys", "players[0].rating"),
    ({"players": [{"name": "A", "squad_merit": 1}]}, "banned keys", "players[0].squad_merit"),
    ({"claim": "The best eleven, ranked by the model."}, "served labels", "claim: best"),
])
def test_a_stored_result_passes_the_boundary_check_like_a_computed_one(
        planted, refusal, named, tmp_path, monkeypatch):
    # The store read completeness and providers only, so a stored file would have left the
    # server with a key or a word no computed reply may carry (BD6). The store is off unless
    # it is switched on, and here it is switched on the way a deployment switches it on.
    monkeypatch.setenv(runtime.RESULT_STORE_ENV, "1")
    monkeypatch.setattr(runtime, "RESULT_STORE_DIR", tmp_path)
    monkeypatch.setattr(runtime, "source_fingerprint", lambda: "f" * 64)
    cache = runtime.ResultCache()
    assert cache.store_dir == tmp_path
    key = ("squad.depth", "abc", "q")
    stored = _envelope(**planted)
    # Non-vacuity: the file is one the two older checks pass, and finalize refuses it computed.
    assert runtime.is_complete(stored)
    runtime._require_hosted_providers(stored)
    with pytest.raises(runtime.BoundaryViolation, match=refusal):
        runtime.finalize(stored)
    cache.store_path(key).write_bytes(runtime.dumps(stored))

    def never() -> dict:
        raise AssertionError("a stored result is read, not computed")

    for _ in range(2):  # refused each time: nothing of it is kept in memory
        with pytest.raises(runtime.BoundaryViolation, match=refusal) as caught:
            cache.get_or_compute(key, never, store=runtime.is_complete)
        assert named in str(caught.value)
    assert len(cache) == 0 and cache._flights == {}
    # Opposite case: the same file without the fault is served as stored.
    clean = runtime.dumps(_envelope(players=[{"name": "A"}], claim="It is not a forecast."))
    cache.store_path(key).write_bytes(clean)
    assert cache.get_or_compute(key, never, store=runtime.is_complete) == (clean, True)


def test_source_fingerprint_is_the_lf_digest_of_the_served_code():
    assert runtime._lf_digest(b"a\r\nb\rc\n") == lf_sha256_text("a\nb\rc\n")
    package = Path(runtime.__file__).resolve().parents[1]
    files = sorted([*(package / "optimization").rglob("*.py"), *(package / "api").glob("*.py")],
                   key=lambda path: path.relative_to(package).as_posix())
    assert Path(runtime.__file__).resolve() in files and len(files) > 5
    expected = hashlib.sha256(
        b"".join(path.read_bytes().replace(b"\r\n", b"\n") for path in files)).hexdigest()
    runtime.source_fingerprint.cache_clear()
    assert runtime.source_fingerprint() == expected


# ---------------------------------------------------------------- long jobs

def test_at_most_two_long_computations_run_and_a_place_is_always_returned(monkeypatch):
    monkeypatch.setattr(runtime, "_LONG_JOBS", threading.BoundedSemaphore(runtime.LONG_JOB_LIMIT))
    monkeypatch.setattr(runtime, "LONG_JOB_WAIT_SECONDS", 0.02)
    assert runtime.LONG_JOB_LIMIT == 2
    with runtime.long_job("squad.stress"), runtime.long_job("transfer.injection"):
        with pytest.raises(runtime.LongJobsBusy), runtime.long_job("xi.risk.regret"):
            raise AssertionError("a third long computation started")
        with runtime.long_job("squad.depth"):      # a short route does not need a place
            pass
    with pytest.raises(RuntimeError, match="tool fault"), runtime.long_job("squad.stress"):
        raise RuntimeError("tool fault")
    with runtime.long_job("squad.stress"), runtime.long_job("squad.stress"):
        pass                                        # both places came back
    with pytest.raises(KeyError), runtime.long_job("squad.stres"):
        raise AssertionError("a misspelt route skipped the limit")


# ---------------------------------------------------------------- places past the cache

@pytest.fixture
def places(monkeypatch):
    """A fresh set of places, so a test neither inherits a held place nor leaves one."""
    fresh = runtime._Places(runtime.IN_FLIGHT_LIMIT)
    monkeypatch.setattr(runtime, "_IN_FLIGHT", fresh)
    return fresh


def _until(condition) -> None:
    """Wait for a state another thread is about to reach. No outcome depends on how long."""
    deadline = time.monotonic() + 10
    while not condition():
        assert time.monotonic() < deadline
        time.sleep(0.001)


def test_sixteen_requests_are_past_the_cache_lookup_and_the_seventeenth_is_refused_at_once(
        places):
    # The audit's burst: forty-five requests on one cold key took every worker thread, and a
    # stored reply, a page and a static file then waited for that one computation (BD1). With
    # sixteen places, sixteen requests are in and the next is refused without waiting.
    assert runtime.IN_FLIGHT_LIMIT == 16 == places.limit
    assert runtime.IN_FLIGHT_BUSY == "16 requests are already in progress"

    async def worker_threads() -> float:
        return anyio.to_thread.current_default_thread_limiter().total_tokens

    # The pool every handler and file read runs in. The bound has to stay well inside it.
    assert anyio.run(worker_threads) == 40 >= 2 * runtime.IN_FLIGHT_LIMIT
    cache = runtime.ResultCache()
    stored, _ = cache.get_or_compute(("stored",), _envelope, store=runtime.is_complete)
    assert runtime.in_flight() == 0
    started, release = threading.Semaphore(0), threading.Event()
    results: list = []

    def slow() -> dict:
        started.release()
        assert release.wait(20)
        return _envelope()

    def request(name: str) -> None:
        results.append(cache.get_or_compute((name,), slow, store=runtime.is_complete))

    # Twelve different requests and four on one key: three of those wait for the fourth.
    names = [f"k{i}" for i in range(12)] + ["same"] * 4
    threads = [threading.Thread(target=request, args=(name,)) for name in names]
    try:
        for thread in threads:
            thread.start()
        for _ in range(13):                       # thirteen computations are running
            assert started.acquire(timeout=10)
        _until(lambda: getattr(cache._flights.get(("same",)), "waiters", 0) == 4)
        # A request that waits for an identical one holds a place while it waits.
        assert runtime.in_flight() == 16

        def never() -> dict:
            raise AssertionError("a refused request must not compute")

        for key in (("seventeenth",), ("same",), ("k0",)):  # a new one, and two that would wait
            asked = time.perf_counter()
            with pytest.raises(runtime.TooManyRequests) as caught:
                cache.get_or_compute(key, never, store=runtime.is_complete)
            assert time.perf_counter() - asked < 0.5
            assert str(caught.value) == "16 requests are already in progress"
        # A refusal takes no place and joins no flight; a stored reply needs no place.
        assert runtime.in_flight() == 16 and cache._flights[("same",)].waiters == 4
        asked = time.perf_counter()
        assert cache.get_or_compute(("stored",), never, store=runtime.is_complete) \
            == (stored, True)
        assert time.perf_counter() - asked < 0.5
    finally:
        release.set()
        for thread in threads:
            thread.join(20)
    assert len(results) == 16 and sorted(hit for _, hit in results) == [False] * 13 + [True] * 3
    assert runtime.in_flight() == 0 and cache._flights == {}
    # Every place came back: the request that was refused is now answered.
    assert cache.get_or_compute(("seventeenth",), _envelope, store=runtime.is_complete)[1] is False


def test_a_place_is_given_back_on_every_way_out_and_none_leaks_over_two_hundred_requests(
        places, monkeypatch):
    monkeypatch.setattr(runtime, "_LONG_JOBS", threading.BoundedSemaphore(runtime.LONG_JOB_LIMIT))
    monkeypatch.setattr(runtime, "LONG_JOB_WAIT_SECONDS", 0.001)
    cache = runtime.ResultCache()
    held: list[int] = []

    def reply() -> dict:
        held.append(runtime.in_flight())           # non-vacuity: a computation holds a place
        return _envelope()

    def partial() -> dict:
        return _envelope(completeness="TIME_LIMIT")

    def refused() -> dict:
        raise ValueError("unknown lock id 99")

    def absent() -> dict:
        raise FileNotFoundError("competition=Spain/actions.parquet")

    def fault() -> dict:
        raise KeyError("progression")

    def not_json() -> dict:
        return _envelope(value=float("nan"))

    def banned() -> dict:
        return runtime.finalize(_envelope(rating=7.1))

    def long_place() -> dict:
        with runtime.long_job("squad.stress"):     # both places are held by the test
            raise AssertionError("a third long computation started")

    ways = [(reply, None), (partial, None), (refused, ValueError), (absent, FileNotFoundError),
            (fault, KeyError), (not_json, runtime.BoundaryViolation),
            (banned, runtime.BoundaryViolation), (long_place, runtime.LongJobsBusy)]
    seen = set()
    with runtime.long_job("squad.stress"), runtime.long_job("transfer.injection"):
        for number in range(200):
            compute, raised = ways[number % len(ways)]
            key = (compute.__name__, str(number % 24))  # some keys repeat: stored replies too
            if raised is None:
                _, hit = cache.get_or_compute(key, compute, store=runtime.is_complete)
                seen.add((compute.__name__, hit))
            else:
                with pytest.raises(raised):
                    cache.get_or_compute(key, compute, store=runtime.is_complete)
            assert runtime.in_flight() == 0, (number, compute.__name__)
        with pytest.raises(ValueError, match="precomputed"):
            cache.get_or_compute(("p",), reply, store=runtime.is_complete, precomputed_only=True)
        assert runtime.in_flight() == 0
    assert held and set(held) == {1}
    assert seen == {("reply", False), ("reply", True), ("partial", False)}
    # Nothing leaked and nothing was given back twice: exactly sixteen places can be taken.
    assert [places.take() for _ in range(17)] == [True] * 16 + [False]
    assert places.held == 16
    for _ in range(16):
        places.give_back()
    assert places.held == 0
    with pytest.raises(RuntimeError, match="nobody held"):
        places.give_back()
    assert places.held == 0                       # the count never goes below zero


def test_the_refusal_is_a_429_with_retry_after_and_stored_replies_and_get_routes_are_served(
        lab_client, places):
    calls: list[str] = []
    catalogue = lab_client(runtime.router)
    client = lab_client(_skeleton(calls))
    first = client.post("/api/squad/stress", json={})
    assert (first.status_code, first.headers["X-Galactico-Cache"]) == (200, "miss")
    assert runtime.RETRY_AFTER_SECONDS == 5
    with ExitStack() as stack:
        for _ in range(runtime.IN_FLIGHT_LIMIT):
            stack.enter_context(runtime.admission())
        asked = time.perf_counter()
        busy = client.post("/api/squad/stress", json={"mode": "TIME_LIMIT"})
        assert time.perf_counter() - asked < 0.5
        assert (busy.status_code, busy.json()) \
            == (429, {"detail": "16 requests are already in progress"})
        assert busy.headers["Retry-After"] == "5"
        assert calls == ["COMPLETE"]               # the refused request computed nothing
        # A stored reply never takes a place, so it is served with every place held.
        again = client.post("/api/squad/stress", json={})
        assert (again.status_code, again.headers["X-Galactico-Cache"]) == (200, "hit")
        assert again.content == first.content
        # Nor does a request that is refused before the cache, or a GET route.
        assert client.post("/api/squad/stress", json={"scenario_id": "x"}).status_code == 404
        assert client.post("/api/squad/stress", json={"worlds": 200}).status_code == 422
        assert catalogue.get("/api/evidence/verdicts").status_code == 200
        assert runtime.in_flight() == runtime.IN_FLIGHT_LIMIT
    assert runtime.in_flight() == 0
    served = client.post("/api/squad/stress", json={"mode": "TIME_LIMIT"})
    assert (served.status_code, served.headers["X-Galactico-Cache"]) == (200, "miss")
    # The other refusal for want of a place tells the client when to ask again, too.
    busy = client.post("/api/squad/stress", json={"mode": "BUSY"})
    assert (busy.status_code, busy.json(), busy.headers["Retry-After"]) \
        == (429, {"detail": "two long computations are already running"}, "5")
    assert runtime.in_flight() == 0


# ---------------------------------------------------------------- boundary check

def test_finalize_returns_the_payload_unchanged_when_it_may_leave():
    payload = _envelope(teams=[{"home_score": 2, "score": 2}], score_research={"status": "NONE"})
    with pytest.raises(runtime.BoundaryViolation, match=r"teams\[0\]\.score"):
        runtime.finalize(payload)
    before = json.dumps(payload, sort_keys=True)
    assert runtime.finalize(payload, allow_keys=("teams[].score",)) is payload
    assert json.dumps(payload, sort_keys=True) == before


@pytest.mark.parametrize("provenance", [
    None,
    {},
    {"providers": []},
    {"providers": ["pappalardo", "statsbomb"]},
    {"providers": ["statsbomb"]},
    {"providers": ["pappalardo", "pappalardo"]},
    {"providers": "pappalardo"},
    {"providers": None},
])
def test_finalize_refuses_any_provider_set_but_the_hosted_one(provenance):
    payload = {"value": 1} if provenance is None else {"value": 1, "provenance": provenance}
    with pytest.raises(runtime.BoundaryViolation, match="providers"):
        runtime.finalize(payload)


@pytest.mark.parametrize("inner", [
    {"universe": {"provenance": {"providers": ["pappalardo", "statsbomb"]}}},
    {"rows": [{"lineage": {"provider": "statsbomb"}}]},
    {"rows": [{"provenance": {"providers": []}}]},
    {"reference": {"provider": None}},
])
def test_no_lineage_below_the_envelope_names_another_provider(inner, tmp_path, monkeypatch):
    # The envelope's own provider list is not the only one a response carries: a universe,
    # a reference or a row brings its lineage with it.
    payload = _envelope(**inner)
    with pytest.raises(runtime.BoundaryViolation, match="provider"):
        runtime.finalize(payload)
    nested = _envelope(universe={"provenance": {"providers": ("pappalardo",),
                                                "provider": "pappalardo"}},
                       rows=[{"provider_position": "MF"}])
    assert runtime.finalize(nested) is nested
    # The result store reads with the same rule.
    monkeypatch.setattr(runtime, "source_fingerprint", lambda: "f" * 64)
    cache = runtime.ResultCache(store_dir=tmp_path)
    cache.store_path(("k",)).write_bytes(runtime.dumps(payload))
    with pytest.raises(runtime.BoundaryViolation, match="provider"):
        cache.get_or_compute(("k",), _envelope, store=runtime.is_complete)


@pytest.mark.parametrize("payload", [
    {"rows": [{"player": {"rating": 7.1}}]},
    {"candidates": [{"fit_score": 0.9}]},
    {"overallRating": 80},
    {"worlds": [{"index": 3}]},
    {"shortfall": {"total": 0.4}},
])
def test_finalize_refuses_a_rating_key_at_any_depth(payload):
    assert runtime.HOSTED_PROVIDERS == ("pappalardo",)
    with pytest.raises(runtime.BoundaryViolation, match="banned keys"):
        runtime.finalize({**payload, "provenance": {"providers": ["pappalardo"]}})


@pytest.mark.parametrize("key", [
    "ratings", "merit", "overall_score", "rank_overall", "xi_rating", "rating_value", "ranks",
    "ranked_first", "squad_ranking", "playerMerit", "Overall-Score",
])
def test_finalize_refuses_a_key_one_of_whose_parts_reads_as_a_rating(key):
    # The thirteen whole keys were the whole rule, and the boundary check passed each of
    # these (BD5). No reply held one; the check is what would not have stopped it.
    payload = _envelope(players=[{"name": "A", key: 9.1}])
    with pytest.raises(runtime.BoundaryViolation, match="banned keys") as caught:
        runtime.finalize(payload)
    assert f"players[0].{key}" in str(caught.value)
    # A path is still what exempts a key, never a word.
    assert runtime.finalize(payload, allow_keys=(f"players[].{key}",)) is payload


def test_finalize_names_exactly_the_parts_it_refuses_and_passes_the_near_words():
    refused = sorted(thesis.BANNED_KEY_PARTS)
    assert refused == ["merit", "overall", "rank", "ranked", "ranking", "ranks", "rating",
                       "ratings"]
    # "score", "tier", "fit" and "best" are not on the list: a scoreline beside its side, the
    # data tier of a verdict and a count keep their keys. The label guard does not read keys
    # here, so this payload answers to the key walker alone.
    served = _envelope(
        home_score=2, score_research={"status": "NONE"}, total_completed_passes=412,
        rows=[{"tier": "PUBLIC", "fit": None, "best_xi": False, "player_score": None,
               "tolerated_loss": 0.4, "rate_assumption": "as recorded", "outranking": 1}],
    )
    assert runtime.finalize(served) is served


@pytest.mark.parametrize(("planted", "path", "word"), [
    ({"claim": "The best eleven of this squad."}, "claim", "best"),
    ({"rows": [{"note": {"text": "Ranked by the model, nothing more."}}]},
     "rows[0].note.text", "ranked"),
    ({"warnings": ["Clean.", "A FORECAST of his rates."]}, "warnings[1]", "forecast"),
])
def test_finalize_refuses_a_banned_word_in_a_served_label_at_any_depth(planted, path, word):
    # The copy guard used to run only in the tests of the replies they requested (M-06).
    with pytest.raises(runtime.BoundaryViolation, match="served labels") as caught:
        runtime.finalize(_envelope(**planted))
    message = str(caught.value)
    assert f"{path}: {word}" in message
    # It names the path and the word, never the sentence around it.
    assert "eleven" not in message and "nothing more" not in message and "rates" not in message


def test_the_label_guard_at_the_boundary_reads_values_and_leaves_keys_to_the_key_walker():
    # A named denial passes; lineage under provenance is not a label; an exempted key is
    # judged once, by the key walker's own exemption, and not a second time as a label.
    payload = _envelope(
        non_claim="It is not a forecast, and there is no overall rating.",
        teams=[{"home_score": 2, "score": 2}],
        universe={"provenance": {"providers": ["pappalardo"], "tie_policy": "best bound"}},
    )
    assert runtime.finalize(payload, allow_keys=("teams[].score",)) is payload
    assert labels.scan_labels({"score": "fine", "label": "top"}, keys=False) == ["label: top"]
    assert labels.scan_labels({"score": "fine", "label": "top"}) == ["score: score", "label: top"]


def test_respond_is_strict_json_and_names_the_cache_outcome():
    response = runtime.respond({"club": "Atlético", "value": None, "share": 0.25})
    assert response.media_type == "application/json"
    assert response.headers["X-Galactico-Cache"] == "miss"
    assert response.body == '{"club": "Atlético", "value": null, "share": 0.25}'.encode()
    cached = runtime.respond(b'{"a": 1}', cache_hit=True)
    assert cached.body == b'{"a": 1}' and cached.headers["X-Galactico-Cache"] == "hit"
    for value in (float("nan"), float("inf"), -float("inf"), np.int64(3), np.float32(1.5),
                  np.bool_(True), np.float64("nan"), {1, 2}):
        with pytest.raises(runtime.BoundaryViolation, match="strict JSON"):
            runtime.respond({"value": value})


# ---------------------------------------------------------------- MATCH scenario bridge

def test_match_scenarios_are_the_shipped_registry_entries():
    assert set(decision_lab.SCENARIOS) == {"madrid-2018-05-06", "madrid-2018-04-08"}
    for scenario_id, entry in decision_lab.SCENARIOS.items():
        assert runtime.match_scenario(scenario_id) is entry
    with pytest.raises(KeyError):
        runtime.match_scenario("madrid-planning-2018-05-21")


def test_match_snapshot_is_the_object_xi_lab_solves_on(monkeypatch):
    calls = []
    snap = object()

    def spy(match_id, worlds):
        calls.append((match_id, worlds))
        return snap

    monkeypatch.setattr(decision_lab, "snapshot", spy)
    assert runtime.WORLD_MENU == (12, 40) and runtime.PRECOMPUTED_WORLDS == (200,)
    for worlds in (0, 12, 40):
        assert runtime.match_snapshot("madrid-2018-05-06", worlds) is snap
    assert calls == [(2565907, 0), (2565907, 12), (2565907, 40)]
    for worlds in (7, 200, -12, True, 12.0, "12", None):
        with pytest.raises(ValueError) as caught:
            runtime.match_snapshot("madrid-2018-05-06", worlds)
        assert str(caught.value) == "bootstrap worlds must be one of 0, 12, 40"
    with pytest.raises(KeyError):
        runtime.match_snapshot("madrid-planning-2018-05-21", 0)
    assert len(calls) == 3


# ---------------------------------------------------------------- HTTP

def test_verdicts_endpoint_serves_the_registry(lab_client, thesis_guard, monkeypatch):
    client = lab_client(runtime.router)
    response = client.get("/api/evidence/verdicts")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert body == {
        "verdicts": [],                                  # the registry ships empty
        "order": "experiment_id, subject_id ascending",
        "claim": "Registered protocols and their recorded verdicts. "
                 "A verdict labels a quantity; it is not a property of a player.",
        "provenance": {"providers": ["pappalardo"]},
    }
    thesis_guard(body)
    assert runtime.finalize(body) is body      # the boundary check of every other new response
    assert [route.path for route in runtime.router.routes] == ["/api/evidence/verdicts"]

    listed = [verdicts.as_payload(verdicts.verdict_for("E-10", "x"))]
    monkeypatch.setattr(verdicts, "all_payloads", lambda: listed)
    assert client.get("/api/evidence/verdicts").json()["verdicts"] == listed
    # It is finalized, so a listing that named another provider would not leave the server.
    monkeypatch.setattr(verdicts, "all_payloads", lambda: [{"provider": "statsbomb"}])
    with pytest.raises(runtime.BoundaryViolation, match="provider"):
        client.get("/api/evidence/verdicts")


class _Query(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = "madrid-planning-2018-05-21"
    mode: str = "COMPLETE"


def _skeleton(calls: list[str]) -> APIRouter:
    """The handler shape ARCH-SPEC 5.2 gives every new POST endpoint."""
    router = APIRouter(route_class=decision_lab.DecisionRoute)

    @router.post("/api/squad/stress")
    def stress(request: _Query):
        if request.scenario_id != "madrid-planning-2018-05-21":
            raise HTTPException(404, "unknown squad scenario")
        with runtime.lab_errors():
            key = runtime.cache_key("squad.stress", request, "synthetic")

            def compute() -> dict:
                with runtime.long_job("squad.stress"):
                    budget = runtime.budget_for("squad.stress")
                    calls.append(request.mode)
                    if request.mode == "NO_CORPUS":
                        raise FileNotFoundError("competition=Spain")
                    if request.mode == "BAD_LOCK":
                        raise ValueError("unknown lock id 99")
                    if request.mode == "BUSY":
                        raise runtime.LongJobsBusy()
                    providers = ["statsbomb"] if request.mode == "LEAK" else ["pappalardo"]
                    return runtime.finalize({
                        "levels": [], "budget": budget.report(
                            "TIME_LIMIT" if request.mode == "TIME_LIMIT" else "COMPLETE"),
                        "provenance": {"providers": providers},
                    })

            data, hit = runtime.RESULTS.get_or_compute(key, compute, store=runtime.is_complete)
            return runtime.respond(data, cache_hit=hit)

    return router


def test_the_handler_skeleton_end_to_end(lab_client, thesis_guard):
    calls: list[str] = []
    before = runtime.RESULTS
    client = lab_client(_skeleton(calls))
    assert runtime.RESULTS is not before and len(runtime.RESULTS) == 0

    first = client.post("/api/squad/stress", json={})
    second = client.post("/api/squad/stress", json={})
    assert (first.status_code, first.headers["X-Galactico-Cache"]) == (200, "miss")
    assert (second.status_code, second.headers["X-Galactico-Cache"]) == (200, "hit")
    assert first.content == second.content and calls == ["COMPLETE"]
    thesis_guard(first.json())
    assert first.json()["budget"]["budget_seconds"] == 30.0

    for _ in range(2):
        limited = client.post("/api/squad/stress", json={"mode": "TIME_LIMIT"})
        assert limited.headers["X-Galactico-Cache"] == "miss"
        assert limited.json()["budget"]["completeness"] == "TIME_LIMIT"
    assert calls.count("TIME_LIMIT") == 2

    for mode, status, detail in [
        ("NO_CORPUS", 503, "historical corpus unavailable"),
        ("BAD_LOCK", 422, "unknown lock id 99"),
        ("BUSY", 429, "two long computations are already running"),
    ]:
        failed = client.post("/api/squad/stress", json={"mode": mode})
        assert (failed.status_code, failed.json()) == (status, {"detail": detail})
    assert client.post("/api/squad/stress", json={"scenario_id": "x"}).status_code == 404
    assert client.post("/api/squad/stress", json={"worlds": 200}).status_code == 422

    # A response that names another provider never leaves: a server fault, not a 422.
    with pytest.raises(runtime.BoundaryViolation, match="providers"):
        client.post("/api/squad/stress", json={"mode": "LEAK"})
    assert len(runtime.RESULTS) == 1
    # Every failure gave its long-computation place back.
    with runtime.long_job("squad.stress"), runtime.long_job("squad.stress"):
        pass


# ---------------------------------------------------------------- module boundary

def test_runtime_imports_no_shell_planning_sidecar_or_research():
    source = Path(runtime.__file__).read_text(encoding="utf-8")
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            names |= {f"{node.module or ''}.{alias.name}" for alias in node.names}
    banned = r"shell|planning|sidecar|validation|experiments|match_lab|statsbomb"
    assert not [name for name in names if re.search(banned, name)]
    assert runtime.router.route_class is decision_lab.DecisionRoute
    assert runtime.RUNTIME_VERSION == "lab-runtime-v1"
