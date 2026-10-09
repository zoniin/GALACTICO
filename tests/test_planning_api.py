"""The declared planning problem, tested without a corpus.

``planning`` has no router, so one probe route here follows the handler skeleton the two lab
routers follow: resolve the scenario, declare the problem, build the envelope, finalize. Each
test targets one rule both routers would otherwise restate. The two slow tests read structure
on the real corpus: who is in the flagship evidence set, and where each league's season ends.
"""

from __future__ import annotations

import math
import os
import random
import subprocess
import sys
import threading
import time
from fractions import Fraction
from typing import get_args

import pytest
from fastapi import APIRouter

from galactico.api import planning, runtime, shell
from galactico.api.decision_lab import DecisionRoute
from galactico.domain import verdicts
from galactico.optimization import historical, reference, snapshots
from galactico.optimization.squad import kernel
from galactico.optimization.transfers import universe as universe_module
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

def _waiting(key) -> int:
    flight = planning._BUILDS._flights.get(key)
    return 0 if flight is None else flight.waiters


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
        _until(lambda: _waiting(("planning_snapshot", (flagship, 0), (str, int))) == 3)
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
    assert [row["key"] for row in body["declared"]] == [
        "declared-scenario", "declared-template", "declared-minimum-progression"]
    assert all(row["origin"] == "DECLARED" and "evidence" not in row for row in body["declared"])
    assert [row["row_id"] for row in body["ledger"]] == [
        "eligibility-rules", "gate-minutes", "rates-progression"]
    assert {row["stage"] for row in body["ledger"]} == {"AUDIT"}
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


def _largest_sum(problem, requirement_id) -> Fraction | None:
    """Every XI the declarations allow, by depth-first enumeration in exact fractions.

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
    return max(sums) if sums else None


def test_attained_is_the_largest_sum_over_every_fieldable_xi(client, snap):
    # Rates in sixteenths, all different: every sum is exact and no two XIs are a rounding
    # step apart, so the tool's XI must be the enumeration's.
    rates = {2: 0.5, 3: 1.25, 4: 0.75, 5: 1.0, 6: 1.5, 7: 2.0, 8: 0.25,
             3322: 1.75, 3321: 2.5, 8278: 0.375, 3563: 2.25}
    for candidate in snap.candidates:
        if candidate["player_id"] in rates:
            candidate["values"]["progression"] = rates[candidate["player_id"]]
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
        # No XI sums to more than the ceiling, and the ceiling is the rounding allowance away.
        slack = 2 * Fraction(row["allowance"]) + Fraction(1, 10**9)
        assert expected <= Fraction(row["ceiling"]) <= expected + slack
        # The printed numbers are rounded away from the claim: down for one, up for the other.
        assert float(row["reached_text"]) <= row["reached"]
        assert float(row["ceiling_text"]) >= row["ceiling"]
        # Scoped to what was solved: the gated squad, these declarations, this template. No
        # remedy is named.
        assert row["statement"] == (
            f"One XI of the gated squad under these declarations sums to {row['reached_text']} "
            f"on {LABELS['progression']}, and none sums to more than {row['ceiling_text']}: an "
            "exact maximisation with every minimum set aside, rounding allowance included. "
            "Under these declarations and this role-slot template, no XI of the gated squad "
            f"reaches a minimum above {row['ceiling_text']}.")
        assert "addition" not in row["statement"]
        assert shell.scan_labels(row) == []
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


def test_attained_states_no_number_when_no_xi_exists_or_the_solve_was_not_decided(
        client, monkeypatch):
    # Both right-sided defenders' only cover gone: no XI, so no sum. Not a zero.
    assert client.post("/probe", json={"excludes": [5]}).status_code == 200
    (row,) = planning.attained(SEEN[-1], time_limit=10.0)
    assert _largest_sum(SEEN[-1], "progression") is None
    assert (row["status"], row["reached"], row["ceiling"]) == ("UNFIELDABLE", None, None)
    assert row["reached_text"] is None and "No XI can be fielded" in row["statement"]

    # A spent clock: the tool returns no incumbent, and that is not a finding.
    assert client.post("/probe", json={}).status_code == 200
    (late,) = planning.attained(SEEN[-1], time_limit=1e-9)
    assert (late["status"], late["reached"], late["ceiling"]) == ("NOT_CERTIFIED", None, None)
    assert "not certified" in late["statement"] and "No value is implied" in late["statement"]
    assert shell.scan_labels(late) == []


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
    assert "declared-experimental-opt-in" in [row["key"] for row in body["declared"]]
    assert [row["evidence"]["class"] for row in body["ledger"][2:]] \
        == ["ESTIMATED", "EXPERIMENTAL", "EXPERIMENTAL"]


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
    assert declared["declared-minimum-progression"] == "0.000. Entered by you."
    # One declaration, one problem: zero by either sign has one fingerprint.
    assert body["provenance"]["input_fingerprint"] \
        == client.post("/probe", json=sent(0.0)).json()["provenance"]["input_fingerprint"]
    assert math.copysign(1.0, planning.RequirementDeclaration(
        requirement_id="progression", source="EXPLICIT", value=-0.0).value) == 1.0


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
