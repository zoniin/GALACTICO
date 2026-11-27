"""Tier four, the store shared across instances (season/store.py, PLAN 4 D1-A; PLATFORM 3.1).

Off Vercel, and always under pytest, the store is a no-op and the app behaves exactly as it
does with tier three alone. The Runtime Cache store is exercised against an in-memory stand-in
for the optional package; nothing here reaches the network.
"""

from __future__ import annotations

import ast
import asyncio
import base64
import json
import math
import os
import sys
import types
import zlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from galactico.match_centre.feed import FeedCache, Snapshot
from galactico.match_centre.season import store as t4
from galactico.match_centre.season.store import (
    MAX_BYTES,
    MAX_TTL,
    MemoryStore,
    NoStore,
    RuntimeStore,
    SharedStore,
    age,
    decode,
    encode,
)

CHECKED = "2026-11-20T08:00:00+00:00"
SNAP = Snapshot([{"id": 1, "home": "A FC", "away": "Norte CF", "result": None}], CHECKED,
                warning="not kept")
ON_VERCEL = {"VERCEL": "1", "SEASON_RUNTIME_CACHE": "1"}


class Clock:
    def __init__(self) -> None:
        self.now = 50.0

    def __call__(self) -> float:
        return self.now


class FakeRuntimeCache:
    """What ``vercel.functions.get_cache(sync=False)`` returns, held in a dict: values are
    JSON, as the real cache stores them."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.options: dict[str, dict] = {}
        self.expired: list[str] = []
        self.fail = False

    async def get(self, key):
        if self.fail:
            raise RuntimeError("cache down")
        return json.loads(self.values[key]) if key in self.values else None

    async def set(self, key, value, options=None):
        if self.fail:
            raise RuntimeError("cache down")
        self.values[key] = json.dumps(value)
        self.options[key] = options or {}

    async def expire_tag(self, tag):
        if self.fail:
            raise RuntimeError("cache down")
        self.expired.append(tag)


def run(coroutine):
    return asyncio.run(coroutine)


# --- the no-op fallback ------------------------------------------------------------

def test_no_store_keeps_nothing_and_never_fails():
    store = NoStore()
    run(store.set("fd:/v4/competitions", SNAP, 60, ("fd",)))
    assert run(store.get("fd:/v4/competitions")) is None
    assert run(store.purge("fd")) is None


def test_under_pytest_the_store_is_always_the_no_op(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("SEASON_RUNTIME_CACHE", "1")
    assert os.environ.get("PYTEST_CURRENT_TEST")
    assert isinstance(SharedStore.from_environment(), NoStore)


@pytest.mark.parametrize("environ", [
    {}, {"VERCEL": "1"}, {"SEASON_RUNTIME_CACHE": "1"},
    {"VERCEL": "1", "SEASON_RUNTIME_CACHE": "0"}, {"VERCEL": "", "SEASON_RUNTIME_CACHE": "1"},
])
def test_off_vercel_or_without_the_switch_the_store_is_the_no_op(environ, monkeypatch):
    monkeypatch.setitem(sys.modules, "vercel.functions", _fake_package(FakeRuntimeCache()))
    assert isinstance(SharedStore.from_environment(environ), NoStore)


def test_without_the_optional_package_the_store_is_the_no_op(monkeypatch):
    monkeypatch.setitem(sys.modules, "vercel", None)        # import vercel... fails
    monkeypatch.setitem(sys.modules, "vercel.functions", None)
    assert isinstance(SharedStore.from_environment(ON_VERCEL), NoStore)


def _fake_package(cache: FakeRuntimeCache, calls: list | None = None) -> types.ModuleType:
    module = types.ModuleType("vercel.functions")

    def get_cache(**kwargs):
        if calls is not None:
            calls.append(kwargs)
        return cache

    module.get_cache = get_cache
    return module


def test_on_vercel_with_the_switch_and_the_package_it_is_the_runtime_cache(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setitem(sys.modules, "vercel", types.ModuleType("vercel"))
    monkeypatch.setitem(sys.modules, "vercel.functions", _fake_package(FakeRuntimeCache(), calls))
    store = SharedStore.from_environment(ON_VERCEL)
    assert isinstance(store, RuntimeStore)
    (kwargs,) = calls
    assert kwargs["sync"] is False and kwargs["key_hash_function"]("a/b?c") == "a/b?c"


def test_the_smaller_cache_package_is_enough(monkeypatch):
    """``vercel-cache`` alone holds the same ``get_cache`` as the full package."""
    cache = FakeRuntimeCache()
    module = _fake_package(cache)
    module.__name__ = "vercel.cache"
    monkeypatch.setitem(sys.modules, "vercel", types.ModuleType("vercel"))
    monkeypatch.setitem(sys.modules, "vercel.functions", None)
    monkeypatch.setitem(sys.modules, "vercel.cache", module)
    store = SharedStore.from_environment(ON_VERCEL)
    assert isinstance(store, RuntimeStore)
    run(store.set("fd:a", SNAP, 60))
    assert run(store.get("fd:a")).rows == SNAP.rows and len(cache.values) == 1


def test_a_package_that_will_not_start_is_the_no_op(monkeypatch):
    module = types.ModuleType("vercel.functions")

    def get_cache(**kwargs):
        raise RuntimeError("no runtime context")

    module.get_cache = get_cache
    monkeypatch.setitem(sys.modules, "vercel", types.ModuleType("vercel"))
    monkeypatch.setitem(sys.modules, "vercel.functions", module)
    assert isinstance(SharedStore.from_environment(ON_VERCEL), NoStore)


# --- the stored form -----------------------------------------------------------------

def test_a_value_is_zlib_json_of_the_rows_and_their_time():
    blob = encode(SNAP)
    assert json.loads(zlib.decompress(blob)) == {"rows": SNAP.rows, "checked": CHECKED}
    back = decode(blob)
    assert (back.rows, back.checked, back.warning) == (SNAP.rows, CHECKED, None)
    assert back.rows[0]["result"] is None                      # missing stays missing
    for garbage in (b"", b"not zlib", zlib.compress(b"[1, 2]"), zlib.compress(b'{"rows": 1}')):
        with pytest.raises(ValueError):
            decode(garbage)


def test_age_reads_the_checked_time_and_never_calls_a_bad_stamp_fresh():
    now = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
    assert age(SNAP, now=now) == 3600
    assert age(Snapshot([], "2026-11-20T08:00:00"), now=now) == math.inf
    assert age(Snapshot([], "yesterday"), now=now) == math.inf


# --- the memory store (tests) --------------------------------------------------------

def test_the_memory_store_keeps_the_rows_and_their_time_until_the_ttl():
    clock = Clock()
    store = MemoryStore(clock=clock)
    run(store.set("fd:standings/PD", SNAP, 60, ("fd",)))
    back = run(store.get("fd:standings/PD"))
    assert (back.rows, back.checked, back.warning) == (SNAP.rows, CHECKED, None)
    clock.now += 59.9
    assert run(store.get("fd:standings/PD")) is not None
    clock.now += 0.1
    assert run(store.get("fd:standings/PD")) is None and len(store) == 0


def test_no_entry_outlives_seven_days():
    assert MAX_TTL == 7 * 86400
    clock = Clock()
    store = MemoryStore(clock=clock)
    run(store.set("fd:teams/PD", SNAP, 30 * 86400, ("fd",)))
    clock.now += MAX_TTL - 1
    assert run(store.get("fd:teams/PD")) is not None
    clock.now += 1
    assert run(store.get("fd:teams/PD")) is None


def test_purge_drops_every_entry_with_the_tag_and_only_those():
    store = MemoryStore(clock=Clock())
    run(store.set("fd:a", SNAP, 60, ("fd",)))
    run(store.set("fd:b", SNAP, 60, ("fd", "comp-PD")))
    run(store.set("wp:c", SNAP, 60, ("wp",)))
    run(store.purge("fd"))
    assert [run(store.get(k)) is None for k in ("fd:a", "fd:b", "wp:c")] == [True, True, False]


def test_what_cannot_be_stored_is_not_stored():
    """Larger than 2 MB compressed, not JSON, or no lifetime: refused, and read as a miss."""
    assert MAX_BYTES == 2 * 1024 * 1024
    store = MemoryStore(clock=Clock())
    noise = base64.b64encode(os.urandom(2 * MAX_BYTES)).decode("ascii")
    run(store.set("big", Snapshot([{"blob": noise}], CHECKED), 60))
    run(store.set("set", Snapshot([{"ids": {1, 2}}], CHECKED), 60))
    run(store.set("nan", Snapshot([{"x": math.nan}], CHECKED), 60))
    run(store.set("now", SNAP, 0))
    assert store.refused == ["big", "set", "nan", "now"] and len(store) == 0
    assert all(run(store.get(k)) is None for k in store.refused)


# --- the runtime cache store ---------------------------------------------------------

def test_the_runtime_store_round_trips_under_a_hashed_name():
    cache = FakeRuntimeCache()
    store = RuntimeStore(cache)
    key = "fd:/v4/competitions/PD/matches?season=2026"
    run(store.set(key, SNAP, 6 * 3600, ("fd",)))
    (name,) = cache.values
    assert name.startswith(t4.KEY_PREFIX) and set(name[len(t4.KEY_PREFIX):]) <= set(
        "0123456789abcdef")
    assert cache.options[name] == {"ttl": 6 * 3600, "tags": ["fd"]}
    stored = json.loads(cache.values[name])
    assert stored["key"] == key and decode(base64.b64decode(stored["value"])).rows == SNAP.rows
    back = run(store.get(key))
    assert (back.rows, back.checked, back.warning) == (SNAP.rows, CHECKED, None)
    run(store.purge("fd"))
    assert cache.expired == ["fd"]


def test_the_runtime_store_clamps_the_lifetime_and_refuses_what_is_too_large(monkeypatch):
    cache = FakeRuntimeCache()
    store = RuntimeStore(cache)
    run(store.set("week", SNAP, 30 * 86400))
    assert next(iter(cache.options.values()))["ttl"] == MAX_TTL
    run(store.set("now", SNAP, 0))
    monkeypatch.setattr(t4, "MAX_BYTES", 16)
    run(store.set("big", SNAP, 60))
    run(store.set("set", Snapshot([{"ids": {1}}], CHECKED), 60))
    assert len(cache.values) == 1


def test_the_runtime_store_reads_only_what_it_wrote_for_that_key():
    cache = FakeRuntimeCache()
    store = RuntimeStore(cache)
    run(store.set("fd:a", SNAP, 60))
    (name,) = cache.values
    # Another key's value under this name, and values that are not this store's, are misses.
    cache.values[name] = json.dumps({"key": "fd:b", "value": json.loads(cache.values[name])[
        "value"]})
    assert run(store.get("fd:a")) is None
    for value in ("just text", {"key": "fd:a", "value": "%%%"}, {"key": "fd:a"}, [1, 2]):
        cache.values[name] = json.dumps(value)
        assert run(store.get("fd:a")) is None


def test_a_runtime_cache_failure_never_reaches_a_reader():
    cache = FakeRuntimeCache()
    store = RuntimeStore(cache)
    run(store.set("fd:a", SNAP, 60))
    cache.fail = True
    assert run(store.get("fd:a")) is None
    run(store.set("fd:b", SNAP, 60))
    run(store.purge("fd"))


# --- with tier three ----------------------------------------------------------------

def test_rows_read_back_from_the_store_keep_the_time_they_were_read_upstream():
    """The point of FeedCache keeping a returned snapshot's ``checked``: a cold instance that
    finds the rows in tier four does not call them fresh."""
    shared = MemoryStore(clock=Clock())
    upstream: list[int] = []

    async def fetch_through(store):
        found = await store.get("fd:standings/PD")
        if found is not None:
            return found
        upstream.append(1)
        snap = Snapshot([{"id": 1}], CHECKED)
        await store.set("fd:standings/PD", snap, 7 * 86400, ("fd",))
        return snap

    async def go():
        warm = await FeedCache().get("fd:standings/PD", 60, lambda: fetch_through(shared))
        cold = await FeedCache().get("fd:standings/PD", 60, lambda: fetch_through(shared))
        assert warm.checked == cold.checked == CHECKED and len(upstream) == 1
        # With the no-op store every instance goes upstream, as tier three alone does.
        nothing = NoStore()
        await FeedCache().get("k", 60, lambda: fetch_through(nothing))
        await FeedCache().get("k", 60, lambda: fetch_through(nothing))
        assert len(upstream) == 3

    run(go())


# --- what the hosted modules import (PLAN 3.1) --------------------------------------

SEASON = Path(__file__).resolve().parents[1] / "galactico" / "match_centre" / "season"


@pytest.mark.parametrize("name", ["budget.py", "store.py"])
def test_the_plumbing_imports_only_the_standard_library_and_the_feed(name):
    """Hosted-safe: no galactico.domain, api or optimization, and no third-party package at
    import time. The one optional package is imported where the Runtime Cache store is made,
    and its absence is the no-op store."""
    tree = ast.parse((SEASON / name).read_text(encoding="utf-8"))
    top, inner = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = {(0, alias.name) for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            names = {(node.level, node.module or "")}
        else:
            continue
        (top if node in tree.body else inner).update(names)
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    assert {(level, module) for level, module in top
            if level or module.split(".")[0] not in stdlib} == {(2, "feed")}
    assert inner == ({(0, "vercel.functions"), (0, "vercel.cache")} if name == "store.py"
                     else set())
