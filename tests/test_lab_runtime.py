"""How a new request runs, tested without a corpus.

Each test targets one rule a router would otherwise restate: which failure is
which status, who owns a budget, what may be cached, that two identical requests
compute once, that a response naming another provider or carrying a rating key
does not leave the server.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import threading
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from galactico.api import decision_lab, runtime
from galactico.domain import verdicts
from galactico.validation.digests import lf_sha256_text


def _envelope(**extra) -> dict:
    return {"value": 1, "completeness": "COMPLETE",
            "provenance": {"providers": ["pappalardo"]}, **extra}


# ---------------------------------------------------------------- error mapping

@pytest.mark.parametrize(("raised", "status", "detail"), [
    (FileNotFoundError("competition=Spain/actions.parquet"), 503, "historical corpus unavailable"),
    (ValueError("unknown lock id 99"), 422, "unknown lock id 99"),
    (runtime.LongJobsBusy(), 429, "two long computations are already running"),
])
def test_lab_errors_maps_each_failure_to_its_status(raised, status, detail):
    with pytest.raises(HTTPException) as caught, runtime.lab_errors():
        raise raised
    assert (caught.value.status_code, caught.value.detail) == (status, detail)
    assert caught.value.__cause__ is raised


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
