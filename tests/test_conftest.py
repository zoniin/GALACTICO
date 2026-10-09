"""The shared fixtures skip when data is absent and guard what they say they guard."""

from __future__ import annotations

import inspect

import conftest
import pytest
from fastapi import APIRouter

SKIP = pytest.skip.Exception


@pytest.mark.parametrize(("call", "reason"), [
    (lambda root: conftest._corpus_root(root), "public historical corpus not downloaded"),
    (lambda root: conftest._spain_frames(root), "public historical corpus not downloaded"),
    (lambda root: conftest._league_available(root)("Italy"), "Italy not downloaded"),
    (lambda root: conftest._sidecar_root(root), "tag sidecar not built"),
    (lambda root: conftest._profile_bundle(root / "Spain_2017-18.json"),
     "profile artifacts not built"),
])
def test_an_empty_directory_skips_and_does_not_error(tmp_path, call, reason):
    with pytest.raises(SKIP, match=reason):
        call(tmp_path)


def test_a_partial_corpus_is_still_a_skip(tmp_path):
    directory = tmp_path / "competition=Spain"
    directory.mkdir()
    (directory / "actions.parquet").write_bytes(b"")
    with pytest.raises(SKIP):
        conftest._corpus_root(tmp_path)
    with pytest.raises(SKIP):
        conftest._league_available(tmp_path)("Spain")


def test_present_paths_are_returned_not_skipped(tmp_path):
    for relative in conftest.SPAIN_FILES.values():
        target = tmp_path / relative
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(b"")
    assert conftest._corpus_root(tmp_path) == tmp_path
    assert conftest._league_available(tmp_path)("Spain") is None
    bundle = tmp_path / "bundle.json"
    bundle.write_text('{"profiles": []}', encoding="utf-8")
    assert conftest._profile_bundle(bundle) == {"profiles": []}


def test_conftest_holds_fixtures_only():
    hooks = [name for name in vars(conftest) if name.startswith("pytest_")]
    assert hooks == []
    assert "autouse=True" not in inspect.getsource(conftest)


def test_thesis_guard(thesis_guard):
    thesis_guard({"home_score": 1, "score_research": {}})
    thesis_guard({"teams": [{"score": 2}]}, allow=("teams[].score",))
    with pytest.raises(AssertionError, match=r"a\[0\]\.Rating"):
        thesis_guard({"a": [{"Rating": 1}]})
    with pytest.raises(AssertionError):
        thesis_guard({"teams": [{"score": 2}]})
    with pytest.raises(ValueError):  # a clean key with a NaN is still not a servable payload
        thesis_guard({"value": float("nan")})


def test_lab_client_serves_one_router_with_patches_applied(lab_client):
    router = APIRouter()

    @router.get("/probe")
    def probe() -> dict:
        return {"separator": conftest.json.dumps([1, 2], separators=(",", ":"))}

    client = lab_client(router)
    assert client.get("/probe").json() == {"separator": "[1,2]"}
    assert client.get("/api/xi/scenarios").status_code == 404  # nothing but that router

    patched = lab_client(router, patches={"conftest.json.dumps": lambda *a, **k: "patched"})
    assert patched.get("/probe").json() == {"separator": "patched"}


def test_lab_client_patches_do_not_outlive_the_test():
    assert conftest.json.dumps([1]) == "[1]"


def test_synthetic_snapshot_shape(synthetic_snapshot, thesis_guard):
    snap = synthetic_snapshot
    ids = [candidate["player_id"] for candidate in snap.candidates]
    assert len(ids) == len(set(ids)) == 12
    assert sorted(snap.worlds) == [0, 1, 2, 3]
    assert all(sorted(world) == sorted(ids) for world in snap.worlds.values())
    holes = [(c["player_id"], metric) for c in snap.candidates
             for metric, value in c["values"].items() if value is None]
    assert holes == [(1, "left_pass_origins")]
    # A hole stays a hole in every world, and the worlds are not four copies of one.
    assert all(world[1]["left_pass_origins"] is None for world in snap.worlds.values())
    assert len({world[2]["progression"] for world in snap.worlds.values()}) == 4
    assert {c["position"] for c in snap.candidates} == {"GK", "DF", "MF", "FW"}
    assert snap.provenance["dataset_hash"] == "synthetic"
    assert snap.omitted == []
    thesis_guard(vars(snap) | {"worlds": {str(k): {str(p): v for p, v in w.items()}
                                          for k, w in snap.worlds.items()}})


@pytest.mark.slow
def test_spain_frames_are_the_build_snapshot_kwargs(spain_frames, league_available):
    league_available("Spain")
    assert sorted(spain_frames) == ["actions", "lineups", "matches", "players"]
    assert len(spain_frames["actions"]) == 628_659
    assert len(spain_frames["matches"]) == 380


@pytest.mark.slow
def test_sidecar_fixture_skips_until_the_sidecar_is_built(spain_sidecar_root):
    assert (spain_sidecar_root / "competition=Spain" / "events.parquet").is_file()
