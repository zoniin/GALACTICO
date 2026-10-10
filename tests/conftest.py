"""Shared fixtures. Fixtures only: nothing autouse, no collection hooks, no plugins.

Claim: a test that asks for the corpus, the tag sidecar or the profile bundle
through a fixture here is skipped, never errored, when the thing is absent (the
CI check job has no data). A test that asks for none of them is untouched: this
file changes no outcome of the suite that existed before it.

Non-claim: the corpus fixtures check presence, not content. Every test that uses
``corpus_root``, ``spain_frames``, ``spain_sidecar_root`` or ``profile_bundle``
must also be marked ``@pytest.mark.slow``; nothing here enforces that.

Each path fixture is one line over a plain function that takes the path, so the
skip behaviour is tested by calling the function on an empty directory instead of
by re-pointing a session fixture.
"""

from __future__ import annotations

import contextlib
import importlib
import json
from collections.abc import Callable, Collection, Iterator, Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    import pandas as pd
    from fastapi.testclient import TestClient

ROOT: Path = Path(__file__).resolve().parents[1]
try:
    from galactico.storage.public import PUBLIC
except ImportError:  # the loader is a sibling package of this build; the path is the fact
    PUBLIC = ROOT / "data/public/parquet/pappalardo"
BUNDLE: Path = ROOT / "data/public/profiles/Spain_2017-18.json"
SIDECAR_ROOT: Path = ROOT / "data/public/sidecar/pappalardo/v1"

SPAIN_FILES: Mapping[str, str] = {
    "actions": "competition=Spain/actions.parquet",
    "matches": "competition=Spain/matches.parquet",
    "lineups": "competition=Spain/lineups.parquet",
    "players": "players.parquet",
}
_LEAGUE_FILES: tuple[str, ...] = ("actions.parquet", "matches.parquet", "lineups.parquet")
_RUNTIME = "galactico.api.runtime"


def _need(path: Path, reason: str) -> Path:
    if not path.exists():
        pytest.skip(reason)
    return path


def _corpus_root(public: Path) -> Path:
    for relative in SPAIN_FILES.values():
        _need(public / relative, "public historical corpus not downloaded")
    return public


def _spain_frames(public: Path) -> dict[str, pd.DataFrame]:
    import pandas as pd

    _corpus_root(public)
    return {name: pd.read_parquet(public / relative) for name, relative in SPAIN_FILES.items()}


def _league_available(public: Path) -> Callable[[str], None]:
    def check(competition: str) -> None:
        for name in _LEAGUE_FILES:
            _need(public / f"competition={competition}" / name, f"{competition} not downloaded")

    return check


def _sidecar_root(sidecar: Path) -> Path:
    # The manifest is written last, so it is what says a build finished.
    _need(sidecar / "Spain" / "MANIFEST.json", "tag sidecar not built")
    return sidecar


def _profile_bundle(bundle: Path) -> dict:
    return json.loads(_need(bundle, "profile artifacts not built").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def corpus_root() -> Path:
    return _corpus_root(PUBLIC)


@pytest.fixture(scope="session")
def spain_frames(corpus_root: Path) -> dict[str, pd.DataFrame]:
    """The kwargs ``build_snapshot(**frames, ...)`` takes, read once. Copy before poisoning."""
    return _spain_frames(corpus_root)


@pytest.fixture(scope="session")
def league_available() -> Callable[[str], None]:
    return _league_available(PUBLIC)


@pytest.fixture(scope="session")
def spain_sidecar_root(corpus_root: Path) -> Path:
    return _sidecar_root(SIDECAR_ROOT)


@pytest.fixture(scope="session")
def profile_bundle() -> dict:
    return _profile_bundle(BUNDLE)


@pytest.fixture
def thesis_guard() -> Callable[..., None]:
    """``thesis_guard(payload, allow=())``: no banned key anywhere, and strict JSON."""
    from galactico.domain.thesis import banned_key_paths

    def guard(payload: Any, allow: Collection[str] = ()) -> None:
        found = banned_key_paths(payload, allow=allow)
        assert found == [], f"banned keys in payload: {found}"
        json.dumps(payload, allow_nan=False)  # NaN and Infinity are not JSON; raises ValueError

    return guard


@pytest.fixture
def lab_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., TestClient]]:
    """``lab_client(router, patches={"pkg.mod.name": value})`` on a bare app with that router.

    When ``galactico.api.runtime`` exists its ``RESULTS`` is replaced by a fresh
    ``ResultCache`` so no response leaks between tests. Until it exists, nothing is
    replaced, because there is nothing to leak through.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    with contextlib.ExitStack() as stack:

        def make(router: Any, patches: Mapping[str, Any] | None = None) -> TestClient:
            for dotted, value in (patches or {}).items():
                monkeypatch.setattr(dotted, value)
            try:
                runtime = importlib.import_module(_RUNTIME)
            except ModuleNotFoundError as error:
                if error.name != _RUNTIME:
                    raise  # the module exists and one of its own imports is broken
            else:
                monkeypatch.setattr(runtime, "RESULTS", runtime.ResultCache())
            app = FastAPI()
            app.include_router(router)
            return stack.enter_context(TestClient(app))

        yield make


@pytest.fixture
def synthetic_snapshot() -> SimpleNamespace:
    """The 12-candidate shape of ``test_decision_api.py``, with four worlds and one hole.

    It carries no event frames, so the frame-level traps (a null ``success``, a
    ``player_id`` of 0, a non-pass type) cannot occur here. The provider's ``MD``
    code can: candidates 6, 7, 8 and 3563 are ``MD`` in ``players`` and arrive as
    ``MF``, the mapping the snapshot builder has already applied. The keeper has no
    measured left pass-origin value: it is ``None`` in the point values and in every
    world, never zero.
    """
    metrics = ("progression", "left_pass_origins", "right_pass_origins")

    def player(pid: int, position: str, roles: list[str]) -> dict:
        return {
            "player_id": pid,
            "name": f"P{pid}",
            "position": position,
            "role_rules": roles,
            "minutes": 1000,
            "values": dict.fromkeys(metrics, 1.0),
        }

    candidates = [
        player(1, "GK", ["gk"]),
        player(2, "DF", ["lb"]),
        player(3, "DF", ["cb"]),
        player(4, "DF", ["cb"]),
        player(5, "DF", ["rb"]),
        player(6, "MF", ["dm"]),
        player(7, "MF", ["cm"]),
        player(8, "MF", ["cm"]),
        player(3322, "FW", ["lw", "st"]),
        player(3321, "FW", ["st"]),
        player(8278, "FW", ["rw", "st"]),
        player(3563, "MF", ["am", "cm"]),
    ]
    candidates[0]["values"]["left_pass_origins"] = None
    worlds = {
        world: {
            candidate["player_id"]: {
                metric: None if value is None else round(value + 0.05 * (world - 1.5), 6)
                for metric, value in candidate["values"].items()
            }
            for candidate in candidates
        }
        for world in range(4)
    }
    return SimpleNamespace(
        match_id=2565907,
        candidates=candidates,
        requirement_minima=dict.fromkeys(metrics, 12.0),
        worlds=worlds,
        provenance={"dataset_hash": "synthetic", "dataset_manifest": "synthetic-no-corpus"},
        omitted=[],
    )
