"""The declared planning problem, tested without a corpus.

``planning`` has no router, so one probe route here follows the handler skeleton the two lab
routers follow: resolve the scenario, declare the problem, build the envelope, finalize. Each
test targets one rule both routers would otherwise restate. One test asks the nine real POST
routes, with every place for a request held, and builds nothing. The three slow tests read
structure on the real corpus: who is in the flagship evidence set, where each league's
season ends, and that no key of any reply of any planning route holds a part the boundary
refuses.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from collections import Counter
from contextlib import ExitStack
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from typing import get_args

import pytest
from fastapi import APIRouter

from galactico.api import planning, runtime, shell
from galactico.api.decision_lab import DecisionRoute
from galactico.domain import thesis, verdicts
from galactico.domain.precision import format_plain
from galactico.domain.provenance import EvidenceClass
from galactico.optimization import historical, reference, snapshots
from galactico.optimization.squad import kernel
from galactico.optimization.transfers import universe as universe_module
from galactico.optimization.xi import tradeoffs
from galactico.optimization.xi.domain import FORMATIONS
from galactico.storage import public

CLAIM = "For this squad and the minima you declared: who is eligible where."
NON_CLAIM = "No player is judged here."
SIDES = ["left_pass_origins", "right_pass_origins"]
LABELS = {metric.metric_id: metric.label for metric in snapshots.SHIPPED_METRICS}
SEEN: list[planning.DeclaredProblem] = []


class Ask(planning.PlanningInputs):
    """A planning question with no field of its own."""


router = APIRouter(route_class=DecisionRoute)


@router.post("/probe")
def probe(request: Ask):
    scenario = planning.resolve_or_404(request.scenario_id)
    with runtime.lab_errors():
        problem = planning.declare(scenario, request)
        SEEN.append(problem)
        budget = runtime.budget_for("squad.depth")
        payload = planning.envelope(
            problem, route="squad.depth", claim=CLAIM, non_claim=NON_CLAIM,
            budget=budget.report("EXACT"),
        )
        return runtime.respond(runtime.finalize(payload))


def _team_snapshot(synthetic, *, team_id=675, manual=True) -> snapshots.TeamSnapshot:
    version = historical.ELIGIBILITY_VERSION if manual else snapshots.PROVIDER_POSITION_VERSION
    return snapshots.TeamSnapshot(
        kind="DATE", team_id=team_id, competition="Spain", match_id=None,
        cutoff="2018-05-21T00:00:00", cutoff_date="2018-05-21", label="synthetic",
        candidates=tuple(synthetic.candidates),
        omitted=(
            dict(player_id=91, name="Zed", position="MF", minutes=400, role_rules=("cm",),
                 reason="below 900 prior minutes"),
            dict(player_id=90, name="abel", position="DF", minutes=120, role_rules=("cb",),
                 reason="below 900 prior minutes"),
        ),
        requirement_minima=dict(synthetic.requirement_minima),
        worlds={}, world_scheme="LEAGUE_MATCHES", world_namespace="",
        prior_starters=(), prior_minutes={},
        eligibility=snapshots.ELIGIBILITY_RULESETS[version],
        metrics=snapshots.SHIPPED_METRICS, facts={},
        provenance={**synthetic.provenance, "providers": ["pappalardo"], "provider": "pappalardo",
                    "gate_statement": snapshots.GATE_STATEMENT, "training_match_count": 380},
    )


def _league_reference(scenario_id, experimental_opt_in=False) -> reference.LeagueReference:
    ids = ["progression", *(SIDES if experimental_opt_in else [])]
    percentiles = {10: 9.0, 25: 10.0, 50: 11.0, 75: 13.5, 90: 15.0}
    return reference.LeagueReference(
        competition="Spain", cutoff_date="2018-05-21", population="ALL_TEAMS",
        subject_team_id=675,
        distributions={
            rid: reference.ReferenceDistribution(
                metric=rid, label=LABELS[rid], n_units=760, n_teams=20, units_per_team=(38, 38),
                percentiles=percentiles, minimum=5.0, maximum=20.0, evidence_class="ESTIMATED",
                subject_n_units=38, subject_club_median=12.0, subject_units_at_or_below=None,
            )
            for rid in ids
        },
        skipped_not_ten_outfield=0, skipped_non_finite=0, evidence_class="ESTIMATED",
        provenance={"input_fingerprint": "f" * 64, "providers": ["pappalardo"]},
    )


def _no_corpus(*_args, **_kwargs):
    raise FileNotFoundError("competition=Spain/matches.parquet")


@pytest.fixture
def snap(synthetic_snapshot):
    return _team_snapshot(synthetic_snapshot)


@pytest.fixture
def client(lab_client, snap):
    SEEN.clear()
    return lab_client(router, patches={
        "galactico.api.planning.planning_snapshot": lambda scenario_id, worlds=0: snap,
        "galactico.api.planning.reference": _league_reference,
        "galactico.api.planning.league_clubs": _no_corpus,
    })


# ------------------------------------------------------------------ module contracts

def test_import_reads_no_data_and_loads_no_solver():
    code = (
        "import sys, galactico.api.planning as p;"
        "bad = [m for m in sys.modules if m.startswith('ortools') or m in ("
        "'galactico.optimization.snapshots', 'galactico.optimization.reference',"
        "'galactico.optimization.squad.kernel', 'galactico.storage.public')];"
        "assert not bad, bad;"
        "assert p.planning_snapshot.cache_info().currsize == 0"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_restated_constants_equal_the_objects_they_restate():
    assert planning.EXPERIMENTAL_OPT_IN_ERROR == snapshots.EXPERIMENTAL_OPT_IN_ERROR
    assert tuple(planning.LEAGUE_LABELS) == universe_module.LEAGUES == get_args(planning.League)
    # One league, one name: the label a planning page prints is the one the pool's sentences use.
    assert dict(planning.LEAGUE_LABELS) == dict(universe_module.LEAGUE_LABELS)
    assert set(planning.SEASON_END_CUTOFFS) == set(planning.LEAGUE_LABELS)
    assert tuple(FORMATIONS) == planning.FORMATION_IDS
    assert get_args(planning.PresetId) == tuple(planning.PRESETS)
    assert planning.FLAGSHIP.team_id == historical.TEAM_ID
    assert planning.WORLDS_ERROR == "bootstrap worlds must be one of 0, 12, 40"
    assert snapshots.ruleset_for(675, "Spain").kind == "MANUAL_DECLARED"
    # Every token a rule set can carry has its words, and every source its origin.
    rulesets = snapshots.ELIGIBILITY_RULESETS.values()
    assert set(planning.ELIGIBILITY_KIND_LABELS) == {rules.kind for rules in rulesets}
    assert set(planning.REVIEW_STATUS_LABELS) == {rules.review_status for rules in rulesets}
    assert tuple(planning.ORIGIN_LABELS) == tuple(s for s, _ in planning.MINIMUM_SOURCES) \
        == get_args(planning.RequirementDeclaration.model_fields["source"].annotation)


def test_catalogue_is_corpus_free_passes_the_copy_guard_and_claims_no_test(
        monkeypatch, thesis_guard):
    monkeypatch.setattr(planning, "league_clubs", _no_corpus)
    monkeypatch.setattr(planning, "planning_snapshot", _no_corpus)
    catalogue = planning.catalogue()
    thesis_guard(catalogue)
    assert shell.scan_labels(catalogue) == []
    assert catalogue["scenarios"] == [dict(
        scenario_id="madrid-planning-2018-05-21", kind="PLANNING", competition="Spain",
        competition_label="La Liga", team_id=675, team_name="Real Madrid",
        cutoff="2018-05-21", season="2017/18",
        label="Real Madrid · end of the 2017/18 league season",
    )]
    assert catalogue["percentile_menu"] == list(reference.PERCENTILE_MENU)
    assert catalogue["worlds_menu"] == [0, 12, 40]

    departure = next(p for p in catalogue["presets"] if p["id"] == "exclude-3322")
    assert departure["sets"] == {"excludes": [3322], "requirements": []}
    assert departure["scenario_ids"] == ["madrid-planning-2018-05-21"]
    assert departure["label"] == "Exclude Cristiano Ronaldo"  # named after what it sets
    assert "public record outside this corpus" in departure["description"]
    assert "your declaration" in departure["description"]
    assert [p["id"] for p in catalogue["presets"] if p["needs_experimental_opt_in"]] \
        == ["side-origins-league-p75"]
    # One requirement has one name on a page: a preset names what it sets by that label, and
    # the requirement id is not a second name for it.
    for preset in catalogue["presets"]:
        if preset["kind"] != "MINIMA":
            continue
        sets = [LABELS[row["requirement_id"]] for row in preset["sets"]["requirements"]]
        assert preset["label"].startswith(f"{' and '.join(sets)}: "), preset["label"]
        assert "progression" not in preset["label"].lower()
    assert catalogue["presets"][1]["label"] == (
        "Positive completed-pass xT per 90: minimum at the median of this club's own "
        "starting-XI sums")
    for phrase in catalogue["identity_policy"]["phrases"]:
        assert "progression" not in phrase["sentence"].lower(), phrase["sentence"]
        preset = planning.PRESETS.get(phrase["preset_id"])
        for rid, _source, _percentile in (preset.minima if preset else ()):
            assert LABELS[rid] in phrase["sentence"]

    by_id = {row["requirement_id"]: row for row in catalogue["requirements"]}
    assert [rid for rid, row in by_id.items() if row.get("declared_by_default")] == ["progression"]
    assert [rid for rid, row in by_id.items() if row.get("needs_experimental_opt_in")] == SIDES
    assert by_id["chance_creation"]["status"] == "UNMEASURED"
    assert [item["item_id"] for item in catalogue["not_measured"]] == [
        *(item.item_id for item in shell.NOT_MEASURED),
        "off_ball", "shots", "chance_creation_requirement", "carry_over", "league_strength",
        "results",
    ]
    # The copy is the branch that is true while nothing is registered. When a protocol is
    # frozen this fails, and the shots and carry-over sentences must be rewritten with it.
    assert verdicts.VERDICTS == {}
    assert (catalogue["verdicts"], catalogue["research_statement"]) \
        == ([], planning.NOT_TESTED_STATEMENT)
    # Every hole of the scope banner is a field of a scenario.
    assert "{" not in catalogue["scope"].format(**catalogue["scenarios"][0])
    # Every phrase that sets something names a preset that exists; a refusal names none.
    for phrase in catalogue["identity_policy"]["phrases"]:
        assert (phrase["preset_id"] in planning.PRESETS) == (phrase["state"] != "NOT_TRANSLATED")


def test_scenarios_have_one_id_each_and_unknown_ids_are_unknown(monkeypatch):
    monkeypatch.setattr(planning, "league_clubs", _no_corpus)
    assert planning.resolve_scenario("madrid-planning-2018-05-21") is planning.FLAGSHIP
    # Madrid's club spelling is the flagship problem, not a second cache entry.
    assert planning.resolve_scenario("spain-675-planning-2018-05-21") is planning.FLAGSHIP
    for unknown in ("madrid-2018-05-06", "spain-676-planning-2018-01-01",
                    "portugal-9-planning-2018-05-21", "spain-0676-planning-2018-05-21", ""):
        with pytest.raises(KeyError):
            planning.resolve_scenario(unknown)

    getafe = dict(scenario_id="spain-676-planning-2018-05-21", competition="Spain",
                  competition_label="La Liga", team_id=676, team_name="Getafe",
                  cutoff="2018-05-21")
    monkeypatch.setattr(planning, "league_clubs", lambda competition: (getafe,))
    scenario = planning.resolve_scenario("spain-676-planning-2018-05-21")
    assert (scenario.team_id, scenario.team_name, scenario.cutoff, scenario.kind) \
        == (676, "Getafe", "2018-05-21", "PLANNING")
    with pytest.raises(KeyError):
        planning.resolve_scenario("spain-677-planning-2018-05-21")


def test_the_club_list_covers_the_leagues_that_are_ingested_and_fails_only_with_none(
        monkeypatch):
    # Spain alone is a supported state (fetch --only Spain): its clubs are still listed.
    def only_spain(competition):
        if competition != "Spain":
            raise FileNotFoundError(f"competition={competition}/matches.parquet")
        return ({"scenario_id": "spain-676-planning-2018-05-21", "competition": "Spain",
                 "team_id": 676, "team_name": "Getafe"},)

    monkeypatch.setattr(planning, "league_clubs", only_spain)
    assert [(row["competition"], row["team_id"]) for row in planning.clubs()] == [("Spain", 676)]
    # Asking for one league that is absent is still an error, not an empty list.
    with pytest.raises(FileNotFoundError):
        planning.clubs("England")
    monkeypatch.setattr(planning, "league_clubs", _no_corpus)
    with pytest.raises(FileNotFoundError):
        planning.clubs()


def test_loaders_hand_the_scenario_to_the_tools_and_refuse_an_off_menu_world_count(monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(snapshots, "load_team_snapshot", lambda **kw: seen.append(kw) or "SNAP")
    monkeypatch.setattr(universe_module, "load_universe", lambda **kw: seen.append(kw) or "POOL")
    monkeypatch.setattr(reference, "load_league_reference",
                        lambda **kw: seen.append(kw) or "REF")
    for loader in (planning.planning_snapshot, planning.reference, planning.universe):
        loader.cache_clear()
    try:
        flagship = planning.DEFAULT_PLANNING_SCENARIO
        assert planning.planning_snapshot(flagship, 12) == "SNAP"
        assert seen.pop() == dict(competition="Spain", team_id=675, cutoff="2018-05-21",
                                  eligibility_version=None, worlds=12,
                                  world_scheme="LEAGUE_MATCHES")
        for off_menu in (7, 200, True, 12.0):
            with pytest.raises(ValueError, match="bootstrap worlds must be one of 0, 12, 40"):
                planning.planning_snapshot(flagship, off_menu)
        with pytest.raises(KeyError):
            planning.planning_snapshot("madrid-2018-05-06", 0)

        leagues = planning.canonical_leagues(planning.FLAGSHIP, ["France", "England"])
        assert leagues == ("England", "France")
        assert planning.universe(flagship, leagues, 12) == "POOL"
        assert seen.pop() == dict(snapshot="SNAP", include_leagues=("England", "France"))
        for refused in (["Spain"], ["England", "England"], ["Portugal"]):
            with pytest.raises(ValueError):
                planning.canonical_leagues(planning.FLAGSHIP, refused)

        assert planning.reference(flagship, True) == "REF"
        assert seen.pop() == dict(competition="Spain", cutoff="2018-05-21", subject_team_id=675,
                                  population="ALL_TEAMS", experimental_opt_in=True)
    finally:
        for loader in (planning.planning_snapshot, planning.reference, planning.universe):
            loader.cache_clear()


# --------------------------------------------------------------------- the build gate

def _waiting(loader: str, args: tuple) -> int:
    """Callers of one loader with one argument list that are in the gate now."""
    return sum(flight.waiters for key, flight in planning._BUILDS._flights.items()
               if (key.loader, key.args) == (loader, args))


def _until(condition) -> None:
    """Wait for a state another thread is about to reach. No outcome depends on how long."""
    deadline = time.monotonic() + 10
    while not condition():
        assert time.monotonic() < deadline
        time.sleep(0.001)


def test_one_build_per_key_two_builds_at_once_and_a_built_key_waits_for_nobody(monkeypatch):
    flagship = planning.DEFAULT_PLANNING_SCENARIO
    started = {worlds: threading.Event() for worlds in (0, 12, 40)}
    release = threading.Event()
    builds: list[int] = []

    def load(**kw):
        builds.append(kw["worlds"])
        started[kw["worlds"]].set()
        if kw["worlds"] != 40:
            assert release.wait(10)
        return f"SNAP-{kw['worlds']}"

    monkeypatch.setattr(snapshots, "load_team_snapshot", load)
    monkeypatch.setattr(reference, "load_league_reference",
                        lambda **kw: builds.append(-1) or "REF")
    monkeypatch.setattr(runtime, "LONG_JOB_WAIT_SECONDS", 0.01)
    loaders = (planning.planning_snapshot, planning.reference, planning.universe)
    for loader in loaders:
        loader.cache_clear()
    got: dict[int, list] = {0: [], 12: []}

    def ask(worlds: int) -> None:
        got[worlds].append(planning.planning_snapshot(flagship, worlds))

    threads = [threading.Thread(target=ask, args=(worlds,)) for worlds in (0, 0, 0, 12)]
    try:
        built = planning.planning_snapshot(flagship, 40)
        assert (built, builds) == ("SNAP-40", [40])
        assert planning.planning_snapshot.cache_info().currsize == 1

        threads[0].start()
        assert started[0].wait(10)
        for thread in threads[1:3]:
            thread.start()
        # Non-vacuity: both later callers of the key are waiting on the first one's build.
        _until(lambda: _waiting("planning_snapshot", (flagship, 0)) == 3)
        threads[3].start()
        assert started[12].wait(10)
        assert builds == [40, 0, 12]            # two builds are running; one key, one build

        # A key that is already built is served at once, with both places taken.
        assert planning.planning_snapshot(flagship, 40) is built
        # A third build has no place: the gate is one for the three loaders together.
        with pytest.raises(runtime.LongJobsBusy):
            planning.reference(flagship, False)
        assert builds == [40, 0, 12]
        release.set()
        for thread in threads:
            thread.join(10)
        # The waiters received the first caller's object. Nothing was built a second time.
        assert len(got[0]) == 3 and all(snap is got[0][0] for snap in got[0])
        assert (got[0][0], got[12]) == ("SNAP-0", ["SNAP-12"])
        assert builds == [40, 0, 12] and planning._BUILDS._flights == {}
        # Both places came back.
        assert planning.reference(flagship, False) == "REF" and builds[-1] == -1
    finally:
        release.set()
        for loader in loaders:
            loader.cache_clear()


def test_a_failed_build_keeps_nothing_and_a_build_inside_a_build_takes_one_place(monkeypatch):
    flagship = planning.DEFAULT_PLANNING_SCENARIO
    state = {"corpus": False}
    seen: list[str] = []

    def load(**kw):
        seen.append("snapshot")
        if not state["corpus"]:
            raise FileNotFoundError("competition=Spain/actions.parquet")
        return "SNAP"

    monkeypatch.setattr(snapshots, "load_team_snapshot", load)
    monkeypatch.setattr(universe_module, "load_universe",
                        lambda **kw: seen.append("universe") or ("POOL", kw["snapshot"]))
    monkeypatch.setattr(runtime, "LONG_JOB_WAIT_SECONDS", 0.01)
    loaders = (planning.planning_snapshot, planning.reference, planning.universe)
    for loader in loaders:
        loader.cache_clear()
    gate = planning._BUILDS
    try:
        for _ in range(2):  # a failure is not remembered, and it gives its place back
            with pytest.raises(FileNotFoundError):
                planning.planning_snapshot(flagship, 0)
        assert seen == ["snapshot", "snapshot"] and gate._flights == {}
        assert planning.planning_snapshot.cache_info().currsize == 0
        state["corpus"] = True
        # One place left: the pool's build takes it, and the snapshot it needs is built
        # inside that place. Asking for a second one would wait on itself.
        assert gate._places.acquire(blocking=False)
        try:
            assert planning.universe(flagship, (), 0) == ("POOL", "SNAP")
            assert seen[2:] == ["snapshot", "universe"]
        finally:
            gate._places.release()
        assert planning.planning_snapshot(flagship, 0) == "SNAP" and len(seen) == 4
    finally:
        for loader in loaders:
            loader.cache_clear()


# ------------------------------------------------------------ what a cache key is made of

def _corpus(root, leagues) -> None:
    for name in ("players", "teams"):
        (root / f"{name}.parquet").write_bytes(b"not parquet: a token opens no file")
    for league in leagues:
        (root / f"competition={league}").mkdir()
        for name in ("actions", "matches", "lineups"):
            (root / f"competition={league}" / f"{name}.parquet").write_bytes(b"x" * 10)


def test_corpus_token_reads_sizes_and_times_of_the_leagues_involved_and_opens_nothing(
        tmp_path, monkeypatch):
    monkeypatch.setattr(public, "PUBLIC", tmp_path)
    _corpus(tmp_path, ("Spain", "England"))
    token = planning.corpus_token(planning.FLAGSHIP, ())
    assert len(token) == 64 and token == planning.corpus_token(planning.FLAGSHIP)
    both = planning.corpus_token(planning.FLAGSHIP, ("England",))
    assert both != token
    # One identity per set of leagues, however it is spelt; the club's own league is always in.
    assert both == planning.corpus_token(planning.FLAGSHIP, ["England", "Spain", "England"])

    spain, england = (tmp_path / f"competition={league}" / "actions.parquet"
                      for league in ("Spain", "England"))
    info = spain.stat()
    later = (info.st_atime_ns, info.st_mtime_ns + 2_000_000_000)
    os.utime(spain, ns=later)
    moved = planning.corpus_token(planning.FLAGSHIP)
    assert moved != token                                     # same size, another time
    spain.write_bytes(b"x" * 11)
    os.utime(spain, ns=later)
    grown = planning.corpus_token(planning.FLAGSHIP)
    assert grown != moved                                     # same time, another size
    england.write_bytes(b"y" * 99)
    assert planning.corpus_token(planning.FLAGSHIP) == grown  # a league the request does not read
    assert planning.corpus_token(planning.FLAGSHIP, ("England",)) != both
    (tmp_path / "teams.parquet").write_bytes(b"z")
    assert planning.corpus_token(planning.FLAGSHIP) != grown

    with pytest.raises(FileNotFoundError):
        planning.corpus_token(planning.FLAGSHIP, ("Italy",))
    england.unlink()
    with pytest.raises(FileNotFoundError):
        planning.corpus_token(planning.FLAGSHIP, ("England",))


def _counting_tools(monkeypatch) -> Counter:
    """The three tool loaders replaced by ones that count and return ``(name, nth build)``."""
    built: Counter = Counter()

    def tool(name: str):
        def load(**_kw):
            built[name] += 1
            return (name, built[name])
        return load

    monkeypatch.setattr(snapshots, "load_team_snapshot", tool("snapshot"))
    monkeypatch.setattr(reference, "load_league_reference", tool("reference"))
    monkeypatch.setattr(universe_module, "load_universe", tool("universe"))
    return built


def _rewritten(path, size: int) -> None:
    """Another file under the same name: another size, and a later modification time."""
    before = path.stat().st_mtime_ns if path.exists() else time.time_ns()
    path.write_bytes(b"y" * size)
    os.utime(path, ns=(before, before + 5_000_000_000))


def test_a_corpus_file_that_changes_is_rebuilt_and_builds_of_the_old_file_are_dropped(
        tmp_path, monkeypatch):
    # The token moved the result-cache key and not the build's: a reply that missed was
    # computed again from the snapshot built from the old file, under the new token (BD7).
    monkeypatch.setattr(public, "PUBLIC", tmp_path)
    _corpus(tmp_path, tuple(planning.LEAGUE_LABELS))
    built = _counting_tools(monkeypatch)
    loaders = (planning.planning_snapshot, planning.reference, planning.universe)
    for loader in loaders:
        loader.cache_clear()
    flagship = planning.DEFAULT_PLANNING_SCENARIO
    everywhere = tuple(planning.LEAGUE_LABELS)
    spain = tmp_path / "competition=Spain" / "actions.parquet"
    try:
        token = planning.corpus_token(planning.FLAGSHIP)
        pool_token = planning.corpus_token(planning.FLAGSHIP, everywhere)
        squads = [planning.planning_snapshot(flagship, worlds) for worlds in (0, 12, 40)]
        league = planning.reference(flagship, False)
        pool = planning.universe(flagship, (), 0)
        assert built == {"snapshot": 3, "reference": 1, "universe": 1}
        # Unchanged files: every one is served as built.
        assert planning.planning_snapshot(flagship, 12) is squads[1]
        assert planning.reference(flagship, False) is league
        assert planning.universe(flagship, (), 0) is pool
        assert built == {"snapshot": 3, "reference": 1, "universe": 1}

        # Another league's file. The squad and its league reference read nothing of it and
        # are not rebuilt; the pool reads the tables of every league and is.
        _rewritten(tmp_path / "competition=England" / "lineups.parquet", 23)
        assert planning.corpus_token(planning.FLAGSHIP) == token
        assert planning.corpus_token(planning.FLAGSHIP, everywhere) != pool_token
        assert planning.planning_snapshot(flagship, 0) is squads[0]
        assert planning.reference(flagship, False) is league
        assert planning.universe(flagship, (), 0) == ("universe", 2)
        assert built == {"snapshot": 3, "reference": 1, "universe": 2}

        # The club's own league. Each loader reads the new file the next time it is asked,
        # and what it built from the old one is dropped, not kept beside the new build.
        _rewritten(spain, 31)
        assert planning.corpus_token(planning.FLAGSHIP) != token
        assert planning.planning_snapshot(flagship, 0) == ("snapshot", 4)
        assert planning.planning_snapshot.cache_info().currsize == 1  # worlds 12 and 40 went
        assert planning.reference(flagship, False) == ("reference", 2)
        assert planning.universe(flagship, (), 0) == ("universe", 3)
        assert [loader.cache_info().currsize for loader in loaders] == [1, 1, 1]
        assert planning.planning_snapshot(flagship, 12) == ("snapshot", 5)
        assert planning.planning_snapshot(flagship, 0) == ("snapshot", 4)   # still built once
        # The same bytes written back are a later file: the token is not a content hash.
        _rewritten(spain, 31)
        assert planning.planning_snapshot(flagship, 0) == ("snapshot", 6)
        assert planning.planning_snapshot.cache_info().currsize == 1
        assert planning._BUILDS._flights == {}
    finally:
        for loader in loaders:
            loader.cache_clear()


def test_a_build_answers_to_the_files_of_its_own_league_and_an_absent_file_is_a_state(
        tmp_path, monkeypatch):
    monkeypatch.setattr(public, "PUBLIC", tmp_path)
    built = _counting_tools(monkeypatch)
    english = "england-1609-planning-2018-05-14"
    monkeypatch.setattr(planning, "league_clubs", lambda competition: (dict(
        scenario_id=english, competition="England", competition_label="Premier League",
        team_id=1609, team_name="Arsenal", cutoff="2018-05-14"),))
    loaders = (planning.planning_snapshot, planning.reference, planning.universe)
    for loader in loaders:
        loader.cache_clear()
    flagship = planning.DEFAULT_PLANNING_SCENARIO
    try:
        # No corpus file at all (the state of a checkout without data): a token cannot be
        # taken, and a build is still one build per key.
        with pytest.raises(FileNotFoundError):
            planning.corpus_token(planning.FLAGSHIP)
        madrid = planning.planning_snapshot(flagship, 0)
        assert planning.planning_snapshot(flagship, 0) is madrid and built["snapshot"] == 1
        # The files arrive under the running process: that is a change, and it is read.
        _corpus(tmp_path, ("Spain", "England"))
        madrid = planning.planning_snapshot(flagship, 0)
        arsenal = planning.planning_snapshot(english, 0)
        assert (madrid, arsenal, built["snapshot"]) == (("snapshot", 2), ("snapshot", 3), 3)
        # A Spanish file changes: the English club's squad is neither rebuilt nor dropped.
        _rewritten(tmp_path / "competition=Spain" / "matches.parquet", 17)
        assert planning.planning_snapshot(flagship, 0) == ("snapshot", 4)
        assert planning.planning_snapshot(english, 0) is arsenal
        assert planning.planning_snapshot.cache_info().currsize == 2
        # The player table is one file for every league: both squads read it.
        _rewritten(tmp_path / "players.parquet", 5)
        assert planning.planning_snapshot(english, 0) == ("snapshot", 5)
        assert planning.planning_snapshot(flagship, 0) == ("snapshot", 6)
        assert planning.planning_snapshot.cache_info().currsize == 2
        # An id that names no league is unknown before anything is read or built.
        with pytest.raises(KeyError):
            planning.planning_snapshot("madrid-2018-05-06", 0)
        assert built["snapshot"] == 6
    finally:
        for loader in loaders:
            loader.cache_clear()


class Pooled(planning.PlanningInputs):
    """A planning question that names other leagues, as a pool question does."""

    include_leagues: list[planning.League] = []


def test_the_request_is_keyed_as_resolved_and_not_as_spelt():
    def key(**sent) -> tuple[str, ...]:
        request = Pooled(**sent)
        scenario = planning.resolve_scenario(request.scenario_id)
        return runtime.cache_key("squad.depth", planning.canonical_request(scenario, request), "t")

    high = {"requirement_id": "progression", "source": "EXPLICIT", "value": 4.0}
    side = {"requirement_id": "left_pass_origins", "source": "CLUB_MEDIAN"}
    declared = dict(excludes=[3322, 8278], locks=[7, 6], include_leagues=["Italy", "England"],
                    presets=["progression-league-p75", "exclude-3322"], requirements=[side, high])
    base = key(**declared)
    assert base == key(
        excludes=[8278, 3322, 3322], locks=[6, 7, 7], include_leagues=["England", "Italy"],
        presets=["exclude-3322", "progression-league-p75"], requirements=[high, side])
    # Madrid's club spelling is the flagship problem.
    assert base == key(**declared, scenario_id="spain-675-planning-2018-05-21")
    assert key() == key(scenario_id="spain-675-planning-2018-05-21", formation="4-3-3")
    canonical = planning.canonical_request(planning.FLAGSHIP, Pooled(
        scenario_id="spain-675-planning-2018-05-21", excludes=[9, 3, 9], requirements=[side, high]))
    assert canonical["scenario_id"] == planning.DEFAULT_PLANNING_SCENARIO
    assert canonical["excludes"] == [3, 9]
    assert [row["requirement_id"] for row in canonical["requirements"]] \
        == ["left_pass_origins", "progression"]
    different = {
        base,
        key(**{**declared, "excludes": [3322]}),
        key(**{**declared, "requirements": [side, {**high, "value": 4.5}]}),
        key(**declared, formation="4-3-1-2"),
    }
    assert len(different) == 4
    # A preset and the same exclusion by hand are different declarations, so different keys.
    assert key(presets=["exclude-3322"]) != key(excludes=[3322])
    # A name the declaration refuses when it is repeated is not folded into the accepted one:
    # the repeat is a 422, and it must not be answered from the other's stored reply.
    assert key(presets=["exclude-3322"] * 2) != key(presets=["exclude-3322"])
    assert key(include_leagues=["Italy", "Italy"]) != key(include_leagues=["Italy"])
    assert key(requirements=[high, high]) != key(requirements=[high])


def test_a_preset_and_the_same_declaration_by_hand_are_one_problem_under_two_keys(client):
    # "One accepted problem, one key" was the docstring's claim and is false (BD3). Both
    # facts are pinned here so that neither can change unnoticed: the two requests resolve to
    # one problem, with one input fingerprint, and they are keyed apart.
    def asked(**sent) -> tuple[tuple[str, ...], str, dict]:
        request = Ask(**sent)
        scenario = planning.resolve_scenario(request.scenario_id)
        key = runtime.cache_key("squad.depth", planning.canonical_request(scenario, request), "t")
        reply = client.post("/probe", json=sent)
        assert reply.status_code == 200, reply.text
        body = reply.json()
        return key, body["provenance"]["input_fingerprint"], body["inputs"]

    p75 = {"requirement_id": "progression", "source": "LEAGUE_PERCENTILE", "percentile": 75}
    for preset, by_hand in (
        ({"presets": ["exclude-3322"]}, {"excludes": [3322]}),
        ({"presets": ["progression-league-p75"]}, {"requirements": [p75]}),
    ):
        alone = asked(**preset)
        both = asked(**preset, **by_hand)
        assert alone[1] == both[1] and alone[2] == both[2]   # one resolved problem
        assert alone[0] != both[0]                           # two keys
        # Opposite case: the by-hand declaration without the preset is another problem,
        # with its own fingerprint as well as its own key.
        hand = asked(**by_hand)
        assert hand[1] != alone[1] and len({alone[0], both[0], hand[0]}) == 3


# ------------------------------------------------- the bound, on the real POST routes

POSTS = {
    "/api/squad/snapshot": {},
    "/api/squad/reference": {},
    "/api/squad/depth": {},
    "/api/squad/stress": {},
    "/api/squad/brief": {"slot_id": "st"},
    "/api/transfer/universe": {"slot_id": "st"},
    "/api/transfer/injection": {"slot_id": "st"},
    "/api/transfer/injection/detail": {"slot_id": "st", "player_id": 7},
    "/api/transfer/retention": {"slot_id": "st", "player_id": 7},
}
"""Every planning POST route, with the least a request of it must state."""


def test_every_planning_post_route_is_refused_at_once_when_sixteen_requests_are_in_progress(
        lab_client, monkeypatch):
    # The bound is taken in the one step all nine handlers share. A route that built or
    # declared anything before that step would wait for a build with every place held.
    from galactico.api import squad_lab, transfer_lab

    def built(*_args, **_kwargs):
        raise AssertionError("a request reached a build")

    patches = {
        "galactico.api.planning.planning_snapshot": built,
        "galactico.api.planning.reference": built,
        "galactico.api.planning.universe": built,
        "galactico.api.planning.league_clubs": _no_corpus,
        "galactico.api.planning.corpus_token": lambda scenario, leagues=(): "token",
    }
    served = {}
    for router in (squad_lab.router, transfer_lab.router):
        client = lab_client(router, patches=patches)
        served.update({route.path: client for route in router.routes if "POST" in route.methods})
    assert set(served) == set(POSTS)                 # a new POST route must be asked here too
    monkeypatch.setattr(runtime, "_IN_FLIGHT", runtime._Places(runtime.IN_FLIGHT_LIMIT))
    with ExitStack() as held:
        for _ in range(runtime.IN_FLIGHT_LIMIT):
            held.enter_context(runtime.admission())
        for path, body in POSTS.items():
            asked = time.perf_counter()
            reply = served[path].post(path, json=body)
            assert time.perf_counter() - asked < 0.5, path
            assert (reply.status_code, reply.json(), reply.headers["Retry-After"]) \
                == (429, {"detail": "16 requests are already in progress"}, "5"), path
        # A request the route refuses on its own account is still that refusal.
        unknown = served["/api/squad/depth"].post("/api/squad/depth", json={"scenario_id": "x"})
        assert (unknown.status_code, unknown.json()["detail"]) == (404, "unknown planning scenario")
        assert runtime.in_flight() == runtime.IN_FLIGHT_LIMIT
    assert runtime.in_flight() == 0
    # Non-vacuity: with a place free the same requests go on to the build.
    for path, body in POSTS.items():
        with pytest.raises(AssertionError, match="a request reached a build"):
            served[path].post(path, json=body)
        assert runtime.in_flight() == 0, path


# ----------------------------------------------------------------- the handler shape

ENVELOPE_KEYS = {
    "scenario_id", "scenario", "inputs", "eligibility", "omitted_candidates", "gate_statement",
    "requirement_scope", "claim", "non_claim", "evidence", "experimental_inputs", "declared",
    "ledger", "warnings", "budget", "not_measured", "not_measured_closing",
    "research_statement", "provenance",
}


def test_default_problem_is_progression_only_and_says_what_it_is_conditional_on(
        client, monkeypatch, thesis_guard):
    # A problem that names no league percentile must not build a league reference.
    monkeypatch.setattr(planning, "reference", _no_corpus)
    response = client.post("/probe", json={})
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == ENVELOPE_KEYS
    thesis_guard(body)
    assert shell.scan_labels(body) == []
    assert body["provenance"]["providers"] == ["pappalardo"]
    assert len(body["provenance"]["input_fingerprint"]) == 64
    assert (body["claim"], body["non_claim"]) == (CLAIM, NON_CLAIM)
    assert body["scenario"]["cutoff"] == "2018-05-21"
    assert body["eligibility"]["kind"] == "MANUAL_DECLARED"
    assert body["gate_statement"] == snapshots.GATE_STATEMENT
    # Canonical order: name ignoring case, then id. Each omission carries its reason.
    assert [(p["name"], p["reason"]) for p in body["omitted_candidates"]] == [
        ("abel", "below 900 prior minutes"), ("Zed", "below 900 prior minutes")]

    rows = {row["requirement_id"]: row for row in body["inputs"]["requirements"]}
    progression = rows["progression"]
    assert (progression["declared"], progression["source"], progression["origin"],
            progression["minimum"], progression["normalizer"], progression["stated"]) \
        == (True, "CLUB_MEDIAN", "POLICY", 12.0, 12.0, False)
    assert [rows[side]["status"] for side in SIDES] == ["EXPERIMENTAL_NOT_OPTED_IN"] * 2
    # Where the minimum came from, in words. An origin is not evidence: it carries no class,
    # and the only class on the row is the requirement's own.
    assert progression["origin_label"] == "Shipped default"
    assert all(row["origin_label"] is None for rid, row in rows.items() if rid != "progression")
    for row in rows.values():
        assert {key for key in row if "origin" in key} <= {"origin", "origin_label"}
        assert {key for key in row if "class" in key} <= {"evidence_class",
                                                          "legacy_evidence_class"}
    assert all(rows[rid]["status"] == "UNMEASURED"
               for rid in ("chance_creation", "rest_defense", "goalkeeping"))

    # The solve inputs are snapshot_inputs' own, and the class is the kernel's own.
    problem = SEEN[-1]
    assert [r.requirement_id for r in problem.requirements if r.active] == ["progression"]
    assert problem.minimums == {"progression": 12.0}
    assert body["evidence"]["class"] == "HEURISTIC" \
        == kernel.compose_evidence(problem.requirements)["composed"]
    assert body["experimental_inputs"] == [] and body["warnings"] == []
    assert LABELS["progression"] in body["evidence"]["binding"]

    # Declared inputs carry an origin and no class; computed rows carry a class and a stage.
    # The request stated no minimum, so no minimum is among the declared rows: the shipped
    # default is a computed row, with the origin the requirement row gives it.
    assert [row["key"] for row in body["declared"]] == ["declared-scenario", "declared-template"]
    assert all(row["origin"] == "DECLARED" and "evidence" not in row for row in body["declared"])
    assert [(row["row_id"], row["stage"]) for row in body["ledger"]] == [
        ("eligibility-rules", "AUDIT"), ("gate-minutes", "AUDIT"), ("rates-progression", "AUDIT"),
        ("minimum-progression", "REQUIREMENTS")]
    default = body["ledger"][3]
    assert (default["origin"], default["origin_label"]) \
        == (progression["origin"], progression["origin_label"]) == ("POLICY", "Shipped default")
    assert all("origin" not in row for row in body["ledger"][:3])
    assert body["ledger"][1]["value_text"] \
        == "12 in the evidence set; 2 omitted (2 below 900 prior minutes)"
    # A value cell names the rule set's kind and status in words; the tokens are the fields.
    assert body["ledger"][0]["value_text"] \
        == f"{historical.ELIGIBILITY_VERSION} (manual rules, declared by hand)"
    assert body["ledger"][2]["evidence"]["class"] == "ESTIMATED"

    # Nothing was tested, and nothing says otherwise.
    shown = [row["verdict"] for row in body["ledger"] if row["verdict"]]
    assert shown and all(v["basis"] == "NOT_REGISTERED" and v["may_gate"] is False
                         and v["badge"] == "RECORD ONLY · NOT TESTED" for v in shown)
    assert body["provenance"]["verdicts"] == []
    assert body["research_statement"] == planning.NOT_TESTED_STATEMENT


def _keys(node, found: set[str]) -> set[str]:
    """Every key of a JSON-like value, at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            _keys(value, found)
    elif isinstance(node, list):
        for value in node:
            _keys(value, found)
    return found


def test_no_key_of_the_catalogue_or_of_an_envelope_holds_a_part_the_boundary_refuses(client):
    # The boundary refuses a key by its parts as well as whole (BD5). What every planning
    # reply is built on must hold none of them, in any state of the declarations.
    entered = {"requirement_id": "left_pass_origins", "source": "EXPLICIT", "value": 9.25}
    sent = [{}, {"presets": ["exclude-3322"], "locks": [7]}, {"formation": "4-3-1-2"},
            {"presets": ["progression-league-p75"]},
            {"experimental_opt_in": True, "requirements": [entered]},
            {"experimental_opt_in": True, "presets": ["side-origins-league-p75"]}]
    bodies = [planning.catalogue(), *(client.post("/probe", json=body).json() for body in sent)]
    seen: set[str] = set()
    for body in bodies:
        assert "detail" not in body
        assert thesis.banned_key_paths(body, parts=thesis.BANNED_KEY_PARTS) == []
        _keys(body, seen)
    # Non-vacuity: the walk read real keys at every depth, provenance included, and it finds
    # a part where one is planted.
    assert len(seen) > 120 and {"origin_label", "input_fingerprint", "dataset_hash"} <= seen
    planted = bodies[1]
    planted["provenance"]["snapshot"]["squad_ranking"] = 1
    planted["ledger"][0]["evidence"]["inputs"][0]["merit"] = 1
    assert thesis.banned_key_paths(planted, parts=thesis.BANNED_KEY_PARTS) == [
        "ledger[0].evidence.inputs[0].merit", "provenance.snapshot.squad_ranking"]
    assert thesis.banned_key_paths(planted) == []  # the whole-key rule alone sees neither


def _xi_sums(problem, requirement_id) -> list[Fraction]:
    """The sum of every XI the declarations allow, by depth-first enumeration in exact fractions.

    It shares no code with the tool: no solver, no quantisation, no kernel.
    """
    slots = FORMATIONS[problem.formation].slots
    active = [r for r in problem.requirements if r.active]
    target = next(r for r in active if r.requirement_id == requirement_id)
    sums: list[Fraction] = []

    def applies(requirement, slot_id) -> bool:
        return not requirement.slot_ids or slot_id in requirement.slot_ids

    def place(index: int, used: frozenset, total: Fraction) -> None:
        if index == len(slots):
            if set(problem.locks) <= used:
                sums.append(total)
            return
        slot = slots[index]
        for player in problem.candidates:
            if player.player_id in used or player.player_id in problem.excludes:
                continue
            if player.position not in slot.allowed_positions:
                continue
            if player.eligible_slots is not None and slot.slot_id not in player.eligible_slots:
                continue
            if any(applies(r, slot.slot_id) and player.values.get(r.metric) is None
                   for r in active):
                continue  # no measurement where one is needed: not placed, never zero
            counts = applies(target, slot.slot_id)
            gain = Fraction(player.values[target.metric]) if counts else Fraction()
            place(index + 1, used | {player.player_id}, total + gain)

    place(0, frozenset(), Fraction())
    return sums


def _largest_sum(problem, requirement_id) -> Fraction | None:
    sums = _xi_sums(problem, requirement_id)
    return max(sums) if sums else None


def _set_rates(snap, rates: dict[int, float], metric: str = "progression") -> None:
    for candidate in snap.candidates:
        if candidate["player_id"] in rates:
            candidate["values"][metric] = rates[candidate["player_id"]]


ATTAINED_SENTENCE = (
    "One XI of the gated squad under these declarations sums to {reached} on {label}, and none "
    "sums to more than {ceiling}. The first number is the sum of one XI the solver found, with "
    "every minimum set aside; another XI can sum to more. The second is a ceiling no XI "
    "exceeds: the solver's optimum plus its rounding allowance. The shortfall model rounds "
    "each player's rate and the minimum to 1/100000 of the club median, so a minimum entered "
    "between these two numbers, or under the first by less than that allowance, can be "
    "answered with a shortfall or with none. Under these declarations and this role-slot "
    "template, no XI of the gated squad reaches a minimum above {ceiling}."
)


def test_attained_is_the_largest_sum_where_no_rounding_can_hide_another_xi(client, snap):
    # Rates in sixteenths, all different: every sum is exact and no two XIs are a rounding
    # step apart, so here the XI the tool found must be the enumeration's largest. That is a
    # property of these rates. The two tests below use rates where it does not hold.
    _set_rates(snap, {2: 0.5, 3: 1.25, 4: 0.75, 5: 1.0, 6: 1.5, 7: 2.0, 8: 0.25,
                      3322: 1.75, 3321: 2.5, 8278: 0.375, 3563: 2.25})
    largest = {}
    for name, body in (("default", {}), ("without 3563", {"excludes": [3563]}),
                       ("8 fielded", {"locks": [8]}), ("diamond", {"formation": "4-3-1-2"})):
        assert client.post("/probe", json=body).status_code == 200
        problem = SEEN[-1]
        (row,) = planning.attained(problem, time_limit=10.0)
        expected = _largest_sum(problem, "progression")
        assert (row["requirement_id"], row["status"]) == ("progression", "CERTIFIED"), name
        assert row["label"] == LABELS["progression"]
        assert row["reached"] == float(expected), name
        # No XI sums to more than the ceiling, and the ceiling is within two rounding
        # allowances of the largest sum: one the solver's rounding, one added on top of it.
        slack = 2 * Fraction(row["allowance"]) + Fraction(1, 10**9)
        assert expected <= Fraction(row["ceiling"]) <= expected + slack
        # The printed numbers are rounded away from the claim: down for one, up for the other.
        assert float(row["reached_text"]) <= row["reached"]
        assert float(row["ceiling_text"]) >= row["ceiling"]
        # Scoped to what was solved: the gated squad, these declarations, this template. No
        # remedy is named. It says what each number is, and what the shortfall model does
        # with a minimum near them.
        assert row["statement"] == ATTAINED_SENTENCE.format(
            reached=row["reached_text"], ceiling=row["ceiling_text"],
            label=LABELS["progression"]) == planning.ATTAINED_CERTIFIED.format(
            reached=row["reached_text"], ceiling=row["ceiling_text"], label=row["label"])
        assert "addition" not in row["statement"] and "largest" not in row["statement"]
        assert shell.scan_labels(row) == []
        # The scale the sentence names is the shortfall model's own, and the query's. The
        # allowance it names is half a unit of that scale for each of the ten outfield slots,
        # a unit being 1/100000 of the club median (12 in this squad), rounded outward.
        assert f"1/{kernel.QUANTIZATION} of the club median" in row["statement"]
        assert row["quantization"] == kernel.QUANTIZATION == 100_000
        assert row["allowance"] == math.nextafter(
            float(Fraction(10, 2 * kernel.QUANTIZATION) * 12), math.inf)
        largest[name] = expected
    # The declarations are in the answer: a departure and a forced inclusion both lower it.
    assert largest["default"] > largest["without 3563"]
    assert largest["default"] > largest["8 fielded"]

    # With the opt-in, one row per requirement in force, each its own maximisation.
    assert client.post("/probe", json={"experimental_opt_in": True}).status_code == 200
    problem = SEEN[-1]
    rows = planning.attained(problem, time_limit=10.0)
    assert [row["requirement_id"] for row in rows] == ["progression", *SIDES]
    for row in rows:
        assert row["reached"] == float(_largest_sum(problem, row["requirement_id"]))


def test_attained_brackets_the_largest_sum_when_the_rates_are_not_exact(client, snap):
    # Decimal rates: no sum is exact in binary, and XIs lie within a rounding step of one
    # another, so the first number need not be the largest sum. What must hold is the
    # bracket, against an enumeration that shares nothing with the tool.
    draw = random.Random(20261009)
    outfield = [c["player_id"] for c in snap.candidates if c["position"] != "GK"]
    cases = needs_allowance = inexact = below_exact = 0
    for _ in range(12):
        rates = {pid: round(draw.uniform(0.05, 3.0), draw.choice((3, 4, 5, 6)))
                 for pid in outfield}
        inexact += sum(Fraction(rate).denominator > 2**20 for rate in rates.values())
        _set_rates(snap, rates)
        for body in ({}, {"formation": "4-3-1-2"}, {"excludes": [3563]}, {"locks": [8]}):
            assert client.post("/probe", json=body).status_code == 200
            problem = SEEN[-1]
            (row,) = planning.attained(problem, time_limit=10.0)
            assert row["status"] == "CERTIFIED"
            sums = _xi_sums(problem, "progression")
            largest = max(sums)
            # The first number is the sum of one XI: the float nearest that XI's exact sum.
            assert row["reached"] in {float(total) for total in sums}
            # The bracket, on the numbers and on what is printed of them.
            assert row["reached"] <= float(largest) and largest <= Fraction(row["ceiling"])
            first, second = Fraction(row["reached_text"]), Fraction(row["ceiling_text"])
            assert first <= largest <= second
            # Each printed number is rounded away from its claim, and by less than one unit
            # of the fourth decimal. The first is the exact sum of an XI, rounded down: the
            # float in ``reached`` can lie a hair under a sum that is a whole fourth decimal.
            found = [total for total in sums if float(total) == row["reached"]]
            assert any(math.floor(total * 10**4) == first * 10**4 for total in found)
            below_exact += any(Fraction(row["reached"]) < first <= total for total in found)
            assert float(row["reached_text"]) <= row["reached"]
            ceiling = Fraction(row["ceiling"])
            assert ceiling <= second < ceiling + Fraction(1, 10**4)
            assert second - first <= 2 * Fraction(row["allowance"]) + Fraction(2, 10**4) \
                + Fraction(1, 10**9)
            cases += 1
            # The largest sum is above the solver's optimum over rounded rates: without the
            # allowance the second number would be exceeded by an XI.
            needs_allowance += largest > Fraction(row["ceiling"]) - Fraction(row["allowance"])
    # Non-vacuity: the rates are not binary fractions, the allowance was needed, and a sum
    # that is a whole fourth decimal above its own float did occur.
    assert cases == 48 and inexact > 100 and needs_allowance >= 10 and below_exact >= 1


def test_the_first_number_is_one_xi_the_solver_found_and_another_can_sum_to_more(client, snap):
    # Two midfielders whose rates are the same whole number of units of the shortfall scale
    # and differ below it, a unit being 1/100000 of the club median (12 in this squad). The
    # solver sees one model whichever of the two has the larger rate, so it leaves the same
    # player out both times: in one of the two squads the XI it found is not the largest sum.
    unit = Fraction(12) / 100_000
    near = (float(unit * Fraction("100.4")), float(unit * Fraction("100.3")))
    assert [round(Fraction(rate) / unit) for rate in near] == [100, 100] and near[0] > near[1]
    others = {2: 0.31, 3: 0.47, 4: 0.53, 5: 0.29, 6: 0.61, 3563: 1.9,
              3322: 0.71, 3321: 0.83, 8278: 0.37}
    found = []
    for seven, eight in (near, near[::-1]):
        _set_rates(snap, {**others, 7: seven, 8: eight})
        assert client.post("/probe", json={}).status_code == 200
        problem = SEEN[-1]
        (row,) = planning.attained(problem, time_limit=10.0)
        sums = _xi_sums(problem, "progression")
        largest = max(sums)
        assert row["reached"] in {float(total) for total in sums}
        assert Fraction(row["reached_text"]) <= largest <= Fraction(row["ceiling_text"])
        found.append((row["reached"] == float(largest), float(largest) - row["reached"]))
    assert sorted(is_largest for is_largest, _ in found) == [False, True]
    short = max(gap for _, gap in found)
    assert 0 < short < float(unit)  # by less than one unit: the rounding hid it


def test_the_shortfall_model_answers_a_minimum_near_the_two_numbers_either_way(client, snap):
    # What the sentence says of the shortfall model, shown on the model itself. Every rate is
    # a whole number of units plus one fixed fraction of a unit, a unit being 1/100000 of the
    # club median, so the ten outfield rates of an XI all round the same way.
    unit = Fraction(12) / 100_000
    whole = {2: 2000, 3: 3000, 4: 3500, 5: 2500, 6: 4000, 7: 9000, 8: 5000, 3563: 9500,
             3322: 6000, 3321: 7000, 8278: 6500}

    def squad(fraction: str) -> None:
        _set_rates(snap, {pid: float((units + Fraction(fraction)) * unit)
                          for pid, units in whole.items()})

    def shortfall(minimum: Fraction | float) -> tuple[float, float]:
        assert client.post("/probe", json=_entered(float(minimum))).status_code == 200
        problem = SEEN[-1]
        value = kernel.ShortfallKernel(
            problem.candidates, problem.requirements, problem.formation,
        ).value(excluded=problem.excludes, locked=problem.locks,
                deadline=time.monotonic() + 30)
        assert value.status == "CERTIFIED"
        return value.objective_vector

    def numbers() -> tuple[Fraction, Fraction, Fraction, Fraction]:
        assert client.post("/probe", json={}).status_code == 200
        problem = SEEN[-1]
        (row,) = planning.attained(problem, time_limit=10.0)
        largest = max(_xi_sums(problem, "progression"))
        assert row["reached"] == float(largest)      # one XI is far ahead: no tie to hide
        return (Fraction(row["reached_text"]), Fraction(row["ceiling_text"]), largest,
                Fraction(row["allowance"]))

    # Rounded down: each rate loses 0.4 of a unit, so an XI's rounded sum is four units less
    # than its sum.
    squad("0.4")
    first, second, largest, allowance = numbers()
    assert first <= largest <= second
    # An XI sums to at least the first number, and the model certifies a shortfall at it,
    assert shortfall(first)[0] > 0
    # and at a minimum under the first number by less than the allowance.
    step = Fraction(1, 10_000)
    assert step < allowance and shortfall(first - step)[0] > 0
    # A minimum more than the allowance under it is answered with none.
    assert shortfall(first - allowance - step) == (0.0, 0.0)

    # Rounded up: each rate gains 0.4 of a unit. A minimum that no XI's sum reaches, between
    # the two printed numbers, is answered with none.
    squad("0.6")
    first, second, largest, allowance = numbers()
    above = largest + 2 * unit
    assert first <= largest < above < second
    assert shortfall(above) == (0.0, 0.0)
    # Above the second number the model and the sums agree: no XI reaches it.
    assert shortfall(second + step)[0] > 0


def test_attained_states_no_number_when_no_xi_exists_or_the_solve_was_not_decided(
        client, monkeypatch):
    # Both right-sided defenders' only cover gone: no XI, so no sum. Not a zero.
    assert client.post("/probe", json={"excludes": [5]}).status_code == 200
    (row,) = planning.attained(SEEN[-1], time_limit=10.0)
    assert _largest_sum(SEEN[-1], "progression") is None
    assert (row["status"], row["reached"], row["ceiling"]) == ("UNFIELDABLE", None, None)
    assert row["reached_text"] is None and "No XI can be fielded" in row["statement"]

    # A spent clock: the tool returns no incumbent, and that is not a finding. The solve's
    # own clock is moved a second at every reading, so no machine is fast enough to finish.
    assert client.post("/probe", json={}).status_code == 200
    ticks = iter(range(10**6))
    monkeypatch.setattr(tradeoffs, "time", SimpleNamespace(monotonic=lambda: float(next(ticks))))
    (late,) = planning.attained(SEEN[-1], time_limit=1e-9)
    assert (late["status"], late["reached"], late["ceiling"]) == ("NOT_CERTIFIED", None, None)
    assert late["statement"] == (
        f"Neither a sum of {LABELS['progression']} nor a ceiling for it was certified within "
        "the time limit. No value is implied.")
    assert shell.scan_labels(late) == []


def test_attained_works_to_one_deadline_and_hands_each_solve_what_is_left(client, monkeypatch):
    # Each solve was handed the whole of what was left when attained began, and the frozen
    # query starts its own clock per call: three requirements could spend three times the
    # budget and the reply still said EXACT (BD2).
    assert client.post("/probe", json={"experimental_opt_in": True}).status_code == 200
    problem = SEEN[-1]
    clock = [1000.0]
    monkeypatch.setattr(planning, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    solve = tradeoffs.maximize_requirement
    handed: list[tuple[str, float]] = []

    def slow(*args, **kwargs):
        handed.append((kwargs["target_requirement_id"], kwargs["time_limit"]))
        result = solve(*args, **kwargs)
        clock[0] += 1.5  # every solve takes a second and a half of the request's clock
        return result

    monkeypatch.setattr(tradeoffs, "maximize_requirement", slow)
    rows = planning.attained(problem, time_limit=4.0)
    assert [row["requirement_id"] for row in rows] == ["progression", *SIDES]
    assert handed == [("progression", 4.0), (SIDES[0], 2.5), (SIDES[1], 1.0)]
    # Non-vacuity: the solves themselves were decided, so only the handed limits differ.
    assert [row["status"] for row in rows] == ["CERTIFIED"] * 3

    # A deadline that passes between solves: the next solve is handed the least a tool
    # accepts, never zero and never a negative number, which the tool would refuse.
    handed.clear()
    planning.attained(problem, time_limit=2.0)
    assert handed == [("progression", 2.0), (SIDES[0], 0.5),
                      (SIDES[1], runtime.MIN_REMAINING_SECONDS)]
    assert 0 < runtime.MIN_REMAINING_SECONDS < 0.5


def test_the_departure_preset_is_a_declaration_with_its_sentence(client):
    plain = client.post("/probe", json={}).json()
    body = client.post("/probe", json={"presets": ["exclude-3322"]}).json()
    assert body["inputs"]["excludes"] == [3322] == list(SEEN[-1].excludes)
    declared = {row["key"]: row for row in body["declared"]}
    assert declared["declared-preset-exclude-3322"]["value_text"] == (
        "He left in July 2018. That is a public record outside this corpus, entered here as "
        "your declaration.")
    assert declared["declared-exclusion-3322"]["value_text"] == "P3322"
    # The preset and the same exclusion sent by hand are different declarations of one solve.
    by_hand = client.post("/probe", json={"excludes": [3322, 3322]}).json()
    assert by_hand["inputs"]["excludes"] == [3322]
    prints = {b["provenance"]["input_fingerprint"] for b in (plain, body, by_hand)}
    assert len(prints) == 3
    assert client.post("/probe", json={}).json()["provenance"]["input_fingerprint"] \
        == plain["provenance"]["input_fingerprint"]


def test_experimental_requirements_enter_only_through_the_declared_opt_in(client):
    side = {"requirement_id": "left_pass_origins", "source": "EXPLICIT", "value": 9.5}
    for refused in ({"requirements": [side]}, {"presets": ["side-origins-league-p75"]}):
        response = client.post("/probe", json=refused)
        assert (response.status_code, response.json()["detail"]) \
            == (422, "experimental requirements need experimental_opt_in")

    response = client.post("/probe", json={"experimental_opt_in": True, "requirements": [side]})
    assert response.status_code == 200, response.text
    body = response.json()
    assert shell.scan_labels(body) == []
    problem = SEEN[-1]
    assert [r.requirement_id for r in problem.requirements if r.active] \
        == ["progression", *SIDES]
    assert problem.minimums == {"progression": 12.0, "left_pass_origins": 9.5,
                                "right_pass_origins": 12.0}
    # The composed class and the inputs that bind it are always in the response.
    assert body["evidence"]["class"] == "EXPERIMENTAL" \
        == kernel.compose_evidence(problem.requirements)["composed"]
    assert body["evidence"]["binding"] == [LABELS[side] for side in SIDES]
    assert body["experimental_inputs"] == SIDES
    assert len(body["warnings"]) == 1 and "EXPERIMENTAL" in body["warnings"][0]
    rows = {row["requirement_id"]: row for row in body["inputs"]["requirements"]}
    assert (rows["left_pass_origins"]["origin"], rows["left_pass_origins"]["source_sentence"]) \
        == ("DECLARED", "Entered by you.")
    assert [rows[rid]["origin_label"] for rid in ("progression", *SIDES)] \
        == ["Shipped default", "Entered by you", "Shipped default"]
    # The class of a per-player rate, as the ledger gives it: the Player Lab estimate, or
    # experimental for a descriptor that is.
    by_metric = {metric.metric_id: metric for metric in problem.snapshot.metrics}
    assert [planning.rate_class(by_metric[rid]).name for rid in ("progression", *SIDES)] \
        == ["ESTIMATED", "EXPERIMENTAL", "EXPERIMENTAL"]
    assert rows["right_pass_origins"]["stated"] is False
    # The opt-in and the one entered minimum are declared rows. The two minima nobody
    # declared are not: each is a policy row, with the class of its requirement.
    assert [row["key"] for row in body["declared"]] == [
        "declared-scenario", "declared-template", "declared-experimental-opt-in",
        "declared-minimum-left_pass_origins"]
    assert [(row["row_id"], row["evidence"]["class"]) for row in body["ledger"]] == [
        ("eligibility-rules", "HEURISTIC"), ("gate-minutes", "DERIVED"),
        ("rates-progression", "ESTIMATED"), ("rates-left_pass_origins", "EXPERIMENTAL"),
        ("rates-right_pass_origins", "EXPERIMENTAL"), ("minimum-progression", "HEURISTIC"),
        ("minimum-right_pass_origins", "EXPERIMENTAL")]


def test_a_league_percentile_minimum_is_the_reference_value_and_names_its_sample(client):
    body = client.post("/probe", json={"presets": ["progression-league-p75"]}).json()
    row = next(r for r in body["inputs"]["requirements"] if r["requirement_id"] == "progression")
    assert (row["minimum"], row["normalizer"], row["source"], row["percentile"], row["origin"]) \
        == (13.5, 12.0, "LEAGUE_PERCENTILE", 75, "POLICY")
    assert row["origin_label"] == "League percentile you chose"
    assert row["source_sentence"] == (
        "Positive completed-pass xT per 90 minimum at the 75th percentile of La Liga starting-XI "
        "sums before 2018-05-21 (760 starting elevens of 20 clubs).")
    assert row["reference_fingerprint"] == "f" * 64
    # The percentile is the reader's choice, so the row is a declared one. Its number is
    # read off the league reference and is printed as the rounded figure it is.
    declared = {entry["key"]: entry for entry in body["declared"]}
    assert declared["declared-minimum-progression"]["value_text"] \
        == f"≈ 13.5000. {row['source_sentence']}"
    assert declared["declared-minimum-progression"]["origin"] == "DECLARED"
    assert "minimum-progression" not in {entry["row_id"] for entry in body["ledger"]}
    (requirement,) = [r for r in SEEN[-1].requirements if r.active]
    assert (requirement.minimum, requirement.normalizer) == (13.5, 12.0)
    hashes = {client.post("/probe", json=sent).json()["provenance"]["requirement_set_hash"]
              for sent in ({}, {"presets": ["progression-league-p75"]},
                           {"presets": ["progression-league-p90"]})}
    assert len(hashes) == 3
    # A page that resends what the preset set, with the preset still pressed, declares it once.
    resent = client.post("/probe", json={"presets": ["progression-league-p75"], "requirements": [
        {"requirement_id": "progression", "source": "LEAGUE_PERCENTILE", "percentile": 75}]})
    assert resent.status_code == 200
    assert resent.json()["provenance"]["requirement_set_hash"] \
        == body["provenance"]["requirement_set_hash"]


@pytest.mark.parametrize(("sent", "detail"), [
    ({"excludes": [999]}, "unknown excluded player IDs: [999]"),
    ({"locks": [91]}, "unknown locked player IDs: [91]"),  # omitted below the gate: no candidate
    ({"requirements": [{"requirement_id": "chance_creation", "source": "CLUB_MEDIAN"}]},
     "unknown requirement"),
    ({"requirements": [{"requirement_id": "progression", "source": "CLUB_MEDIAN"}],
      "presets": ["progression-league-p75"]}, "duplicate requirement declarations"),
    ({"requirements": [{"requirement_id": "progression", "source": "CLUB_MEDIAN"}] * 2},
     "duplicate requirement declarations"),
    ({"presets": ["progression-league-p75", "progression-league-p90"]},
     "duplicate requirement declarations"),
    # A contradiction is refused where it is declared, by hand or through a preset.
    ({"locks": [3322], "excludes": [7, 3322]}, "a player cannot be both locked and excluded"),
    ({"locks": [3322], "presets": ["exclude-3322"]},
     "a player cannot be both locked and excluded"),
])
def test_a_declaration_the_problem_cannot_hold_is_a_422_with_its_sentence(client, sent, detail):
    response = client.post("/probe", json=sent)
    assert (response.status_code, response.json()["detail"]) == (422, detail)


def test_a_club_with_no_prior_starting_eleven_is_refused_by_the_label_of_the_requirement(
        client, snap):
    del snap.requirement_minima["progression"]
    response = client.post("/probe", json={})
    assert (response.status_code, response.json()["detail"]) == (
        422, f"no prior starting eleven gives a {LABELS['progression']} minimum for this club")


@pytest.mark.parametrize("sent", [
    {"mode": "SATISFY"},
    {"bootstrap_worlds": 12},
    {"experimental_opt_in": 1},
    {"excludes": ["3322"]},
    {"presets": ["bbc"]},
    {"formation": "3-5-2"},
    {"requirements": [{"requirement_id": "progression", "source": "EXPLICIT"}]},
    {"requirements": [{"requirement_id": "progression", "source": "CLUB_MEDIAN", "value": 1.0}]},
    {"requirements": [{"requirement_id": "progression", "source": "LEAGUE_PERCENTILE",
                       "percentile": 60}]},
    # A menu value is an integer: a float that compares equal to one is not it.
    {"requirements": [{"requirement_id": "progression", "source": "LEAGUE_PERCENTILE",
                       "percentile": 75.0}]},
    # A JSON number too large for a float parses as infinity; it is refused, not echoed.
    '{"requirements": [{"requirement_id": "progression", "source": "EXPLICIT", "value": 1e400}]}',
])
def test_a_malformed_request_is_a_422_that_echoes_no_value(client, sent):
    response = client.post("/probe", **({"content": sent} if isinstance(sent, str)
                                        else {"json": sent}))
    assert response.status_code == 422
    assert all(set(error) <= {"loc", "msg", "type"} for error in response.json()["detail"])


def test_a_minimum_of_negative_zero_is_stored_and_printed_as_zero(client):
    def sent(value: float) -> dict:
        return {"requirements": [
            {"requirement_id": "progression", "source": "EXPLICIT", "value": value}]}

    body = client.post("/probe", json=sent(-0.0)).json()
    row = next(r for r in body["inputs"]["requirements"] if r["requirement_id"] == "progression")
    assert row["minimum"] == 0 and math.copysign(1.0, row["minimum"]) == 1.0
    declared = {r["key"]: r["value_text"] for r in body["declared"]}
    assert declared["declared-minimum-progression"] == "0. Entered by you."
    # One declaration, one problem: zero by either sign has one fingerprint.
    assert body["provenance"]["input_fingerprint"] \
        == client.post("/probe", json=sent(0.0)).json()["provenance"]["input_fingerprint"]
    assert math.copysign(1.0, planning.RequirementDeclaration(
        requirement_id="progression", source="EXPLICIT", value=-0.0).value) == 1.0


def _entered(value: float) -> dict:
    return {"requirements": [
        {"requirement_id": "progression", "source": "EXPLICIT", "value": value}]}


@pytest.mark.parametrize(("value", "printed"), [
    # The audit's values: three decimals recorded the first three as one number, 3.814, which
    # is on the other side of a certified boundary from two of them, and 2.0688 as 2.069.
    (3.8141, "3.8141"), (3.8143, "3.8143"), (3.81431, "3.81431"), (2.0688, "2.0688"),
    (12.5, "12.5"), (4.0, "4"), (1000.0, "1000"), (3.0062074447922993, "3.0062074447922993"),
    (0.00006, "0.00006"), (1e-07, "0.0000001"),          # never in exponent notation
])
def test_the_record_of_an_entered_minimum_is_the_number_entered(client, value, printed):
    body = client.post("/probe", json=_entered(value)).json()
    declared = {row["key"]: row for row in body["declared"]}
    record = declared["declared-minimum-progression"]
    assert record["value_text"] == f"{printed}. Entered by you."
    assert (record["label"], record["origin"], record["stage"]) \
        == (f"{LABELS['progression']} minimum", "DECLARED", "REQUIREMENTS")
    # The record reads back as the float that was sent, which is the float that was solved on.
    assert float(printed) == value == SEEN[-1].minimums["progression"] and printed == format_plain(
        value)
    assert "e" not in printed.lower() and "≈" not in record["value_text"]
    # An entered minimum is in the record once: no policy row repeats it among the computed.
    assert "minimum-progression" not in {row["row_id"] for row in body["ledger"]}


def test_two_entered_minima_are_two_records_however_close(client):
    values = (3.814, 3.8141, 3.8142, 3.8143, 3.81431, 3.8144)
    records = set()
    for value in values:
        body = client.post("/probe", json=_entered(value)).json()
        records.add({row["key"]: row["value_text"] for row in body["declared"]}[
            "declared-minimum-progression"])
    assert len(records) == len(values)


CLUB_MEDIAN = {"requirement_id": "progression", "source": "CLUB_MEDIAN"}


@pytest.mark.parametrize(("sent", "stated", "extra_declared"), [
    ({}, False, []),
    # What the pages send from the second request on: the default, restated by the page.
    ({"requirements": [CLUB_MEDIAN]}, True, []),
    # The preset is the reader's act and is recorded as that. The number is still the default.
    ({"presets": ["minima-club-median"]}, True, ["declared-preset-minima-club-median"]),
])
def test_the_shipped_default_is_a_policy_row_and_never_a_declared_one(
        client, sent, stated, extra_declared):
    body = client.post("/probe", json=sent).json()
    requirement = next(row for row in body["inputs"]["requirements"] if row["declared"])
    assert (requirement["stated"], requirement["source"], requirement["origin"],
            requirement["origin_label"]) == (stated, "CLUB_MEDIAN", "POLICY", "Shipped default")
    # Not among the declared rows, under any key.
    assert [row["key"] for row in body["declared"]] == [
        "declared-scenario", "declared-template", *extra_declared]
    assert {row["origin"] for row in body["declared"]} == {"DECLARED"}
    # Listed once, among the computed rows, with the origin the requirement row gives it and
    # that origin's served label where the page prints the rule of a row.
    (policy,) = [row for row in body["ledger"] if row["row_id"] == "minimum-progression"]
    assert policy == {
        "row_id": "minimum-progression",
        "quantity": f"{LABELS['progression']} minimum",
        "value_text": "≈ 12.0000",
        "sample": requirement["source_sentence"],
        "evidence": shell.evidence_payload(
            [(LABELS["progression"], EvidenceClass.HEURISTIC)]),
        "verdict": shell.verdict_payload("none", "minimum-progression"),
        "solver": "Shipped default",
        "stage": "REQUIREMENTS",
        "origin": "POLICY",
        "origin_label": "Shipped default",
    }
    assert policy["sample"] == (
        "Median of this club's starting-XI sums before 2018-05-21. The shipped default.")
    assert policy["verdict"]["badge"] == "RECORD ONLY · NOT TESTED"
    assert shell.scan_labels(body) == []


def test_a_default_is_printed_as_the_rounded_figure_it_is(client, snap):
    # 3.0062074447922993 is the flagship's median in the corpus; three decimals and no sign
    # printed it as if it were 3.006.
    snap.requirement_minima["progression"] = 3.0062074447922993
    body = client.post("/probe", json={}).json()
    (policy,) = [row for row in body["ledger"] if row["row_id"] == "minimum-progression"]
    assert policy["value_text"] == "≈ 3.0062"
    requirement = next(row for row in body["inputs"]["requirements"] if row["declared"])
    assert requirement["minimum"] == 3.0062074447922993    # the number itself is in the reply
    # Entered by the reader, the same number is a declared row and is printed whole.
    body = client.post("/probe", json=_entered(3.0062074447922993)).json()
    assert {row["key"]: row["value_text"] for row in body["declared"]}[
        "declared-minimum-progression"] == "3.0062074447922993. Entered by you."


def test_every_minimum_in_force_is_in_the_record_once_and_under_one_origin(client):
    entered = {"requirement_id": "left_pass_origins", "source": "EXPLICIT", "value": 9.25}
    chosen = {"requirement_id": "right_pass_origins", "source": "LEAGUE_PERCENTILE",
              "percentile": 90}
    for sent in ({}, {"experimental_opt_in": True},
                 {"experimental_opt_in": True, "requirements": [entered]},
                 {"experimental_opt_in": True, "requirements": [entered, chosen, CLUB_MEDIAN]},
                 {"experimental_opt_in": True, "presets": ["side-origins-league-p75"]}):
        reply = client.post("/probe", json=sent)
        assert reply.status_code == 200, reply.text
        body = reply.json()
        declared = {row["key"]: row for row in body["declared"]}
        computed = {row["row_id"]: row for row in body["ledger"]}
        in_force = [row for row in body["inputs"]["requirements"] if row["declared"]]
        assert in_force
        for row in in_force:
            rid = row["requirement_id"]
            by_reader = f"declared-minimum-{rid}" in declared
            by_policy = f"minimum-{rid}" in computed
            # Once, and on the side its source puts it: the shipped default is never the
            # reader's, and a number or a percentile the reader gave is never a default.
            assert (by_reader, by_policy) == (
                (False, True) if row["source"] == "CLUB_MEDIAN" else (True, False)), (sent, rid)
            if by_policy:
                assert (computed[f"minimum-{rid}"]["origin"],
                        computed[f"minimum-{rid}"]["origin_label"]) \
                    == (row["origin"], row["origin_label"]) == ("POLICY", "Shipped default")
            else:
                text = declared[f"declared-minimum-{rid}"]["value_text"]
                number = (format_plain(row["minimum"]) if row["source"] == "EXPLICIT"
                          else f"≈ {row['minimum']:.4f}")
                assert text == f"{number}. {row['source_sentence']}"


KIT = Path(__file__).resolve().parents[1] / "web" / "labs-shared.js"


@pytest.mark.skipif(shutil.which("node") is None or not KIT.exists(),
                    reason="node or the shared browser kit is absent")
def test_the_page_kit_prints_the_default_minimum_outside_declared_by_you(client, tmp_path):
    # The kit prints every declared row under "Declared by you" with one fixed mark. It was
    # sent the shipped default among them. Nothing of the kit is changed here: the reply is.
    replies = {
        "default": client.post("/probe", json={}).json(),
        "entered": client.post("/probe", json=_entered(3.8143)).json(),
    }
    program = tmp_path / "ledger.mjs"
    program.write_text(
        "globalThis.window = {};\n" + KIT.read_text(encoding="utf-8")
        + f"\nconst replies = {json.dumps(replies)};\n"
        "console.log(JSON.stringify(Object.fromEntries(Object.entries(replies).map("
        "([name, r]) => [name, window.Shell.ledger(r.declared, r.ledger)]))));\n",
        encoding="utf-8")
    done = subprocess.run([shutil.which("node"), str(program)], capture_output=True, text=True,
                          encoding="utf-8", timeout=60)
    assert done.returncode == 0, done.stderr[-1000:]
    drawn = json.loads(done.stdout)

    def tables(markup: str) -> tuple[str, str]:
        assert markup.index('id="ledger-declared"') < markup.index('id="evidence-ledger"')
        first, second = markup.split('id="evidence-ledger"')
        return first, second

    declared, computed = tables(drawn["default"])
    assert "<caption>Declared by you</caption>" in declared
    assert re.findall(r'<tr data-declared="([^"]*)">', declared) \
        == ["declared-scenario", "declared-template"]
    assert declared.count("[ DECLARED ]") == 2
    assert "minimum" not in declared and "Shipped default" not in declared
    row = re.search(r'<tr data-ledger="minimum-progression">(.*?)</tr>', computed).group(1)
    assert "≈ 12.0000" in row and "The shipped default." in row
    assert re.search(r'data-label="Solver or rule"><div class="cell">Shipped default</div>', row)
    assert "DECLARED" not in computed
    # Opposite case: a minimum the reader entered is drawn among the declared rows, whole.
    declared, computed = tables(drawn["entered"])
    assert re.findall(r'<tr data-declared="([^"]*)">', declared)[-1] \
        == "declared-minimum-progression"
    assert "3.8143. Entered by you." in declared and declared.count("[ DECLARED ]") == 3
    assert 'data-ledger="minimum-progression"' not in computed


def test_unknown_scenario_is_404_no_corpus_is_503_and_other_clubs_are_unreviewed(
        client, synthetic_snapshot, monkeypatch):
    for unknown in ("madrid-2018-05-06", "portugal-9-planning-2018-05-21"):
        response = client.post("/probe", json={"scenario_id": unknown})
        assert (response.status_code, response.json()["detail"]) \
            == (404, "unknown planning scenario")
    # Another club needs the match table to exist; without the corpus that is a 503.
    other = "spain-676-planning-2018-05-21"
    response = client.post("/probe", json={"scenario_id": other})
    assert (response.status_code, response.json()["detail"]) \
        == (503, "historical corpus unavailable")
    monkeypatch.setattr(planning, "planning_snapshot", _no_corpus)
    assert client.post("/probe", json={}).status_code == 503

    getafe = dict(scenario_id=other, competition="Spain", competition_label="La Liga",
                  team_id=676, team_name="Getafe", cutoff="2018-05-21")
    monkeypatch.setattr(planning, "league_clubs", lambda competition: (getafe,))
    monkeypatch.setattr(planning, "planning_snapshot", lambda scenario_id, worlds=0:
                        _team_snapshot(synthetic_snapshot, team_id=676, manual=False))
    body = client.post("/probe", json={"scenario_id": other}).json()
    assert (body["eligibility"]["kind"], body["eligibility"]["review_status"]) \
        == ("PROVIDER_POSITION", "UNREVIEWED")
    assert body["ledger"][0]["value_text"] \
        == f"{snapshots.PROVIDER_POSITION_VERSION} (provider positions, unreviewed)"
    assert "unreviewed" in body["eligibility"]["banner"]
    assert all(candidate.eligible_slots is None for candidate in SEEN[-1].candidates)
    # The departure preset is a fact about one club. It is not offered for another.
    response = client.post("/probe", json={"scenario_id": other, "presets": ["exclude-3322"]})
    assert (response.status_code, response.json()["detail"]) \
        == (422, "preset exclude-3322 is not offered for this scenario")


# ----------------------------------------------------------------------- order groups

OUTCOMES = (("GK", "Goalkeepers"), ("DF", "Defenders"), ("MF", "Midfielders"),
            ("FW", "Forwards"))


def _expected_groups(rows, value, descending):
    """From the statement: outcome sequence, then the key, no value last, ties by player id."""
    expected = []
    for token, _label in OUTCOMES:
        members = [row for row in rows if row["position"] == token]
        present = sorted({value(row) for row in members if value(row) is not None},
                         reverse=descending)
        ties = [sorted(row["player_id"] for row in members if value(row) == key)
                for key in present]
        absent = sorted(row["player_id"] for row in members if value(row) is None)
        if absent:
            ties.append(absent)
        if ties:
            expected.append((token, ties))
    return expected


def test_listings_group_by_outcome_then_one_declared_key_and_keep_ties(
        snap, monkeypatch, thesis_guard):
    monkeypatch.setattr(planning, "planning_snapshot", lambda scenario_id, worlds=0: snap)
    problem = planning.declare(planning.FLAGSHIP, planning.PlanningInputs())
    keys = planning.order_keys(problem)
    assert [key.order_key for key in keys] \
        == ["name", "minutes", "age", "requirement_value:progression"]
    readers = {
        "name": (lambda row: row["name"].casefold(), False),
        "minutes": (lambda row: row["minutes"], True),
        "age": (lambda row: row["age_years"], False),
        "requirement_value:progression": (lambda row: row["values"]["progression"], True),
    }
    sizes: set[int] = set()
    saw_absent = saw_missing_outcome = False
    for seed in range(40):
        draw = random.Random(seed)
        rows = [
            dict(player_id=pid, name=draw.choice(["Ana", "ana", "Bo", "Cy"]),
                 position=draw.choice(["GK", "DF", "MF", "FW"][: draw.randint(2, 4)]),
                 minutes=draw.choice([900, 1200, 2000]),
                 age_years=draw.choice([None, 21, 27]),
                 values={"progression": draw.choice([None, 0.5, 1.25, 1.25000001])})
            for pid in draw.sample(range(1, 60), draw.randint(1, 9))
        ]
        listing = planning.listings(rows, outcome_of=lambda row: row["position"],
                                    outcomes=OUTCOMES, keys=keys)
        thesis_guard(listing)
        assert listing["default"] == "name" and listing["tie_rule"] == planning.TIE_RULE
        for key in listing["keys"]:
            value, descending = readers[key["order_key"]]
            assert key["direction"] == ("DESCENDING" if descending else "ASCENDING")
            got = [(g["outcome"], [t["player_ids"] for t in g["tie_groups"]])
                   for g in key["groups"]]
            assert got == _expected_groups(rows, value, descending), (seed, key["order_key"])
            assert all(g["count"] == sum(len(t["player_ids"]) for t in g["tie_groups"])
                       for g in key["groups"])
            sizes |= {len(t["player_ids"]) for g in key["groups"] for t in g["tie_groups"]}
            saw_absent |= any(t["key_value"] is None for g in key["groups"]
                              for t in g["tie_groups"])
            # A band may print the key's number. It never prints a case-folded name.
            assert all((t["key_label"] is None)
                       == (t["key_value"] is None or key["order_key"] == "name")
                       for g in key["groups"] for t in g["tie_groups"])
            saw_missing_outcome |= len(key["groups"]) < len(OUTCOMES)
    # Non-vacuity: ties and singletons, an absent key and an empty outcome all occurred.
    assert 1 in sizes and max(sizes) >= 2 and saw_absent and saw_missing_outcome

    row = dict(player_id=1, name="Ana", position="MF", minutes=900, age_years=21,
               values={"progression": 1.0})
    merit = planning.OrderKey("shortfall_change", "x", True, lambda r: 0)
    for rows, outcomes, bad_keys in (
        ([row], OUTCOMES, (merit,)),               # a key derived from a solve
        ([row], OUTCOMES, (keys[0], keys[0])),     # one key twice
        ([row, row], OUTCOMES, keys),              # one player twice
        ([row], OUTCOMES[:1], keys),               # an outcome nobody declared
    ):
        with pytest.raises(ValueError):
            planning.listings(rows, outcome_of=lambda r: r["position"], outcomes=outcomes,
                              keys=bad_keys)


# ------------------------------------------------------------------- the real corpus

@pytest.mark.slow
def test_flagship_resolves_and_builds_on_the_real_corpus(corpus_root):
    planning.planning_snapshot.cache_clear()
    try:
        scenario = planning.resolve_scenario(planning.DEFAULT_PLANNING_SCENARIO)
        token = planning.corpus_token(scenario)
        assert len(token) == 64 and token == planning.corpus_token(scenario, ("Spain",))
        problem = planning.declare(scenario, planning.PlanningInputs(presets=["exclude-3322"]))
        snap = problem.snapshot
        assert (len(snap.candidates), len(snap.omitted)) == (19, 5)
        assert (snap.kind, snap.cutoff_date, snap.world_scheme) \
            == ("DATE", "2018-05-21", "LEAGUE_MATCHES")
        assert (snap.eligibility.kind, snap.eligibility.review_status) \
            == ("MANUAL_DECLARED", "DECLARED_BY_HAND")
        assert {player["reason"] for player in snap.omitted} == {"below 900 prior minutes"}
        # The preset's label names player 3322; the corpus must agree with the literal.
        assert snap.facts[3322].name == "Cristiano Ronaldo"
        assert problem.excludes == (3322,) and len(problem.candidates) == 19
        assert [r.requirement_id for r in problem.requirements if r.active] == ["progression"]
        payload = runtime.finalize(planning.envelope(
            problem, route="squad.depth", claim=CLAIM, non_claim=NON_CLAIM,
            budget=runtime.budget_for("squad.depth").report("EXACT"),
        ))
        runtime.dumps(payload)
        assert shell.scan_labels(payload) == []
        assert payload["provenance"]["providers"] == ["pappalardo"]
        assert len(payload["omitted_candidates"]) == 5
    finally:
        planning.planning_snapshot.cache_clear()


@pytest.mark.slow
def test_no_key_of_any_reply_of_any_planning_route_holds_a_part_the_boundary_refuses(
        corpus_root, monkeypatch):
    """Every JSON route of the three planning routers, on the real corpus, walked key by key.

    The boundary refuses a key one of whose parts is a listed word (BD5). This is the proof
    that no reply the routes build holds one: every route is asked, in the states that change
    the shape of a reply, and every key at every depth is read, provenance included.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from galactico.api import squad_lab, transfer_lab

    routers = (runtime.router, squad_lab.router, transfer_lab.router)
    served = {(method, route.path) for router in routers for route in router.routes
              for method in route.methods if route.path.startswith("/api/")}
    assert len(served) == 14
    app = FastAPI()
    for router in routers:
        app.include_router(router)
    monkeypatch.setattr(runtime, "RESULTS", runtime.ResultCache())
    loaders = (planning.planning_snapshot, planning.reference, planning.universe)
    for loader in loaders:
        loader.cache_clear()
    asked: set[tuple[str, str]] = set()
    seen: set[str] = set()

    def walk(client, path: str, body: dict | None = None) -> dict:
        reply = client.get(path) if body is None else client.post(path, json=body)
        assert reply.status_code == 200, (path, body, reply.text[:300])
        payload = reply.json()
        assert thesis.banned_key_paths(payload, parts=thesis.BANNED_KEY_PARTS) == [], path
        _keys(payload, seen)
        asked.add(("GET" if body is None else "POST", path))
        return payload

    departed = {"presets": ["exclude-3322"]}
    try:
        with TestClient(app) as client:
            for path in ("/api/evidence/verdicts", "/api/squad/scenarios", "/api/squad/clubs",
                         "/api/transfer/scenarios", "/api/transfer/clubs"):
                walk(client, path)
            walk(client, "/api/squad/snapshot", {})
            walk(client, "/api/squad/reference", {"presets": ["progression-league-p75"]})
            walk(client, "/api/squad/depth", departed)
            walk(client, "/api/squad/depth", {"formation": "4-3-1-2", "experimental_opt_in": True})
            walk(client, "/api/squad/stress", {**departed, "k": 1})
            pool = walk(client, "/api/transfer/universe", {**departed, "slot_id": "st"})
            # The default minimum is reached, so the reply says what the squad attains. A
            # minimum above that ceiling is a declared shortfall: the other shape of a reply.
            ceilings = [float(row["ceiling_text"]) for row in pool["deficiency"]["attained"]]
            assert len(ceilings) == 1
            short = {**departed, "slot_id": "st", "requirements": [
                {"requirement_id": "progression", "source": "EXPLICIT",
                 "value": ceilings[0] + 0.5}]}
            assert walk(client, "/api/transfer/universe", short)["deficiency"]["state"] \
                == "SHORTFALL"
            walk(client, "/api/squad/depth", {**departed, "requirements": short["requirements"]})
            walk(client, "/api/squad/brief", short)
            search = walk(client, "/api/transfer/injection", short)
            assert search["rows"]
            candidate = {**short, "player_id": search["rows"][0]["player_id"]}
            walk(client, "/api/transfer/injection/detail", {**candidate, "worlds": 0})
            walk(client, "/api/transfer/retention", candidate)
    finally:
        for loader in loaders:
            loader.cache_clear()
    assert asked == served
    # Non-vacuity: several hundred distinct keys were read.
    assert len(seen) > 300 and {"origin_label", "input_fingerprint", "tolerated_loss"} <= seen


@pytest.mark.slow
def test_every_league_cutoff_is_the_day_after_its_last_match(corpus_root, league_available):
    import pandas as pd

    from galactico.storage.public import load_public

    planning.league_clubs.cache_clear()
    try:
        for league, cutoff_date in planning.SEASON_END_CUTOFFS.items():
            league_available(league)
            last = pd.to_datetime(load_public(league, tables=("matches",)).matches.date).max()
            assert (last.normalize() + pd.Timedelta(days=1)).date().isoformat() == cutoff_date
        spain = planning.clubs("Spain")
        assert len(spain) == 20
        assert spain == sorted(spain, key=lambda c: (c["team_name"].casefold(), c["team_id"]))
        madrid = next(club for club in spain if club["team_id"] == 675)
        assert (madrid["scenario_id"], madrid["team_name"], madrid["eligibility_kind"]) \
            == (planning.DEFAULT_PLANNING_SCENARIO, planning.FLAGSHIP.team_name,
                "MANUAL_DECLARED")
        others = {club["eligibility_review_status"] for club in spain if club["team_id"] != 675}
        assert others == {"UNREVIEWED"}
        assert planning.resolve_scenario(spain[0]["scenario_id"]).team_id == spain[0]["team_id"]
    finally:
        planning.league_clubs.cache_clear()
