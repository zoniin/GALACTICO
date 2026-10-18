"""The declared-risk timing harness (``scripts/time_xi_risk.py``), on a synthetic snapshot.

Claim: the harness times the calls XI Lab's risk routes make: the router's own menu at each
world count (WORST_WORLD at 1, TAIL at ``TAIL_MENU[B]``, MINIMAX_REGRET), the router's own
``_risk`` on the snapshot of the router's loader, inside the route's long job, with the tool
called once with the router's arguments and the route's deadline; by default every shipped
scenario, 12 and 40 worlds, both formations, without and with the experimental opt-in, the
first entry of each scenario and world count made cold (the snapshot built inside the budget)
before it is made warm. The measured fields hold what they name: the tool call's seconds, the
peak memory during the call, the per-purpose sums and maxima of the tool's recorded solve
times. A call whose envelope ``finalize`` refuses makes the run exit 1. What it prints is
pinned to statuses, completeness, solves, seconds, memory and world counts: no player id, no
player name and no loss value of any result reaches its output.

Non-claim: no corpus is read; the snapshot is patched into the router's loader as in
``tests/test_xi_extensions_api.py``. Nothing here says how long the corpus solves take; the
root runs the harness in the ``root-checks`` workflow.
"""

from __future__ import annotations

import contextlib
import dataclasses
import importlib.util
import re
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import NamedTuple

import pytest

from galactico.api import decision_lab, runtime
from galactico.api import xi_extensions as x
from galactico.optimization.xi import risk

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "time_xi_risk.py"
METRICS = ("progression", "left_pass_origins", "right_pass_origins")
SCENARIO = "madrid-2018-05-06"
FORMATIONS = ("4-3-3", "4-3-1-2")
MEGABYTE = 1024 * 1024

# Fourteen candidates with ids and names nothing else in the output could print.
ROWS = (
    (970101, "GK", ("gk",), (None, None, None)),
    (970102, "DF", ("lb",), (0.8, 1.5, 0.3)),
    (970103, "DF", ("cb",), (0.9, 0.6, 0.6)),
    (970104, "DF", ("cb",), (0.7, 0.5, 0.8)),
    (970105, "DF", ("rb",), (0.8, 0.3, 1.4)),
    (970110, "DF", ("cb", "lb"), (1.1, 0.9, 0.4)),
    (970106, "MF", ("dm",), (1.0, 1.0, 1.0)),
    (970107, "MF", ("cm",), (1.6, 0.4, 0.9)),
    (970108, "MF", ("cm",), (0.4, 1.6, 0.9)),
    (970109, "MF", ("cm", "dm"), (1.2, 0.9, 1.1)),
    (973322, "FW", ("lw", "st"), (1.3, 1.2, 0.2)),
    (973321, "FW", ("st",), (0.9, 0.7, 0.7)),
    (978278, "FW", ("rw", "st"), (1.1, 0.3, 1.3)),
    (973563, "MF", ("am", "cm"), (0.9, 1.3, 1.0)),
)
NAMES = {pid: f"Quillfeather{pid}" for pid, *_ in ROWS}


def make_snapshot(worlds: int) -> SimpleNamespace:
    """The shape ``historical.load_snapshot`` returns, with ``worlds`` resampled vectors."""
    candidates = [
        {"player_id": pid, "name": NAMES[pid], "position": position, "role_rules": roles,
         "minutes": 1500, "values": dict(zip(METRICS, values, strict=True))}
        for pid, position, roles, values in ROWS
    ]
    table = {
        world: {
            c["player_id"]: {
                m: None if v is None
                else round(v * (1 + 0.04 * (((world * 5 + c["player_id"] * 3) % 7) - 3)), 6)
                for m, v in c["values"].items()
            }
            for c in candidates
        }
        for world in range(worlds)
    }
    return SimpleNamespace(
        match_id=2565907, cutoff="2018-05-06T00:00:00", label="synthetic",
        candidates=candidates, omitted=[], requirement_minima=dict.fromkeys(METRICS, 10.0),
        worlds=table, prior_starters=(), prior_minutes={},
        provenance={"dataset_hash": "synthetic", "provider": "pappalardo", "seed": 20260906,
                    "bootstrap_version": "synthetic-bootstrap-v1", "bootstrap_worlds": worlds},
    )


@pytest.fixture(scope="module")
def harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("time_xi_risk_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look the module up
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


@pytest.fixture
def snapshots(monkeypatch) -> dict:
    """The router's loader, patched: each ask is recorded (and, cleared, the asks before it);
    ``made["delay"]`` seconds pass in each build."""
    made: dict = {12: make_snapshot(12), 40: make_snapshot(40), "delay": 0.0}
    asked: list[tuple[str, int]] = []
    cleared: list[int] = []

    def loader(scenario_id: str, worlds: int) -> SimpleNamespace:
        asked.append((scenario_id, worlds))
        time.sleep(made["delay"])
        return made[worlds]

    loader.cache_clear = lambda: cleared.append(len(asked))
    monkeypatch.setattr("galactico.api.xi_extensions._match_snapshot", loader)
    made["asked"], made["cleared"] = asked, cleared
    return made


class Call(NamedTuple):
    name: str
    kwargs: dict
    result: object
    left: float  # the deadline the tool was given, less the clock when it was called


@pytest.fixture
def recorded(monkeypatch) -> list[Call]:
    """Every tool call the router makes, with the time its deadline left it."""
    calls: list[Call] = []
    for name in ("worst_world_selection", "tail_selection", "minimax_regret_selection"):
        original = getattr(risk, name)

        def record(*args, _name=name, _original=original, **kwargs):
            left = kwargs["deadline"] - time.monotonic()
            result = _original(*args, **kwargs)
            calls.append(Call(_name, kwargs, result, left))
            return result

        monkeypatch.setattr(risk, name, record)
    return calls


def column(harness, line: str, name: str) -> str:
    """One cell of a printed row (no cell holds a space)."""
    return line.split()[harness.HEADER.index(name)]


# ------------------------------------------------------------------------------- the menu


def test_the_menu_is_the_routers_at_each_world_count(harness) -> None:
    def entries(worlds):
        return [(e.route, e.rule, e.tail_count) for e in harness.menu(worlds)]

    assert entries(12) == [("xi.risk.tail", "WORST_WORLD", None), ("xi.risk.tail", "TAIL", 2),
                           ("xi.risk.tail", "TAIL", 3), ("xi.risk.tail", "TAIL", 6),
                           ("xi.risk.regret", "MINIMAX_REGRET", None)]
    assert entries(40) == [("xi.risk.tail", "WORST_WORLD", None), ("xi.risk.tail", "TAIL", 4),
                           ("xi.risk.tail", "TAIL", 10), ("xi.risk.tail", "TAIL", 20),
                           ("xi.risk.regret", "MINIMAX_REGRET", None)]
    assert [option["rule"] for option in x._rule_options(40)] == [e.rule for e in
                                                                 harness.menu(40)]
    assert x.TAIL_MENU == risk.TAIL_MENU and harness.WORLD_COUNTS == runtime.WORLD_MENU


def test_requests_at_12_are_validated_and_at_40_built_as_the_router_would(harness) -> None:
    tail, worst, regret = harness.menu(12)[1], harness.menu(12)[0], harness.menu(12)[-1]
    request = harness.request_for(tail, scenario_id=SCENARIO, world_count=12, formation="4-3-3",
                                  opt_in=True)
    assert isinstance(request, x.RiskTailRequest)
    assert (request.bootstrap_worlds, request.rule, request.tail_count,
            request.experimental_opt_in) == (12, "TAIL", 2, True)
    assert harness.request_for(worst, scenario_id=SCENARIO, world_count=12, formation="4-3-3",
                               opt_in=False).tail_count is None
    assert isinstance(harness.request_for(regret, scenario_id=SCENARIO, world_count=12,
                                          formation="4-3-3", opt_in=False),
                      x.RiskRegretRequest)
    forty = harness.request_for(harness.menu(40)[2], scenario_id=SCENARIO, world_count=40,
                                formation="4-3-3", opt_in=False)
    assert (forty.bootstrap_worlds, forty.rule, forty.tail_count) == (40, "TAIL", 10)
    assert (forty.locks, forty.excludes, forty.minimums) == ([], [], {})
    off_menu = harness.Entry("xi.risk.tail", "TAIL", 6)
    with pytest.raises(ValueError, match="not on the menu"):
        harness.request_for(off_menu, scenario_id=SCENARIO, world_count=40, formation="4-3-3",
                            opt_in=False)


def test_by_default_every_scenario_world_count_opt_in_and_entry_is_timed(harness, snapshots,
                                                                        monkeypatch,
                                                                        capsys) -> None:
    seen: list[tuple] = []
    row = harness.TimingRow(**{field.name: None for field in
                               dataclasses.fields(harness.TimingRow)})
    blank = dataclasses.replace(row, tail_count=None, opt_in=False, finalized=True,
                                completeness="EXACT")

    def fake(snap, entry, *, scenario_id, world_count, formation, opt_in, budget_seconds):
        if snap is not None:
            assert snap is snapshots[world_count]
        seen.append((scenario_id, world_count, "cold" if snap is None else "warm", formation,
                     opt_in, entry.rule, entry.tail_count, budget_seconds))
        return blank

    monkeypatch.setattr(harness, "time_entry", fake)
    monkeypatch.setattr(harness, "format_row", lambda row, widths=None: "row")
    assert harness.main([]) == 0
    assert tuple(x.XIDeclarations.model_fields["formation"].annotation.__args__) == FORMATIONS
    expected = []
    for scenario in decision_lab.SCENARIOS:
        for worlds in (12, 40):
            expected.append((scenario, worlds, "cold", "4-3-3", False, "WORST_WORLD", None,
                             None))
            expected += [(scenario, worlds, "warm", formation, opt_in, entry.rule,
                          entry.tail_count, None)
                         for formation in FORMATIONS for opt_in in (False, True)
                         for entry in harness.menu(worlds)]
    assert seen == expected and len(seen) == 2 * 2 * (1 + 2 * 2 * 5)
    # The cold call is faked here, so the loader is asked once per key: by main, for the warm
    # calls, after the cold call.
    assert snapshots["asked"] == [(s, w) for s in decision_lab.SCENARIOS for w in (12, 40)]


# ----------------------------------------------------------------------------- the calls


def test_each_call_is_the_routers_call_under_the_route_budget(harness, snapshots,
                                                             recorded) -> None:
    worst, tail, regret = harness.menu(40)[0], harness.menu(40)[3], harness.menu(40)[-1]
    rows = [harness.time_entry(snapshots[40], entry, scenario_id=SCENARIO, world_count=40,
                               formation="4-3-3", opt_in=False) for entry in (worst, tail, regret)]
    assert [call.name for call in recorded] == ["worst_world_selection", "tail_selection",
                                                "minimax_regret_selection"]
    for (name, kwargs, _, left), entry in zip(recorded, (worst, tail, regret), strict=True):
        # The route's deadline: its budget, started just before _risk on a warm call.
        assert runtime.BUDGETS[entry.route] - 5.0 < left <= runtime.BUDGETS[entry.route]
        assert kwargs["worlds"] is snapshots[40].worlds
        assert (kwargs["world_count"], kwargs["world_seed"], kwargs["bootstrap_version"],
                kwargs["analyze_ties"], kwargs["seed"]) == (
            40, 20260906, "synthetic-bootstrap-v1", True, decision_lab.SEED)
        assert kwargs.get("tail_count") == (20 if name == "tail_selection" else None)
    assert [row.budget_seconds for row in rows] == [runtime.BUDGETS["xi.risk.tail"]] * 2 + [
        runtime.BUDGETS["xi.risk.regret"]]
    assert [(row.rule, row.tail_count) for row in rows] == [("WORST_WORLD", 1), ("TAIL", 20),
                                                            ("MINIMAX_REGRET", None)]
    for row in rows:
        assert (row.status, row.completeness, row.used_worlds, row.discarded_worlds,
                row.finalized) == ("CERTIFIED", "EXACT", 40, 0, True)
        assert row.selection_solves == 1 and row.selection_status == "OPTIMAL"
        assert row.membership_solves == 14 and row.not_run == 0
        assert row.tool_seconds <= row.route_seconds
        assert (row.start, row.snapshot_seconds, row.formation) == ("warm", None, "4-3-3")
    assert rows[-1].world_least_solves > 0 and rows[0].world_least_solves == 0
    assert snapshots["asked"] == [] and snapshots["cleared"] == []  # warm: the snapshot given


def test_the_tool_runs_inside_the_routes_long_job(harness, snapshots, recorded,
                                                  monkeypatch) -> None:
    entered: list[str] = []
    held: list[str] = []
    real = runtime.long_job

    @contextlib.contextmanager
    def long_job(route):
        entered.append(route)
        with real(route):
            held.append(route)
            try:
                yield
            finally:
                held.pop()

    inside: list[tuple[str, ...]] = []
    for name in ("worst_world_selection", "minimax_regret_selection"):
        original = getattr(risk, name)

        def watch(*args, _original=original, **kwargs):
            inside.append(tuple(held))
            return _original(*args, **kwargs)

        monkeypatch.setattr(risk, name, watch)
    monkeypatch.setattr(runtime, "long_job", long_job)
    for entry in (harness.menu(12)[0], harness.menu(12)[-1]):
        harness.time_entry(snapshots[12], entry, scenario_id=SCENARIO, world_count=12,
                           formation="4-3-3", opt_in=False)
    assert entered == ["xi.risk.tail", "xi.risk.regret"]
    assert inside == [("xi.risk.tail",), ("xi.risk.regret",)]


def test_each_memory_reading_lands_in_its_own_field(harness, snapshots, monkeypatch) -> None:
    """The size before the call is VmRSS after the reset, the peak is the high-water mark read
    after it, and the scope says whether the reset took; readers faked, so nothing depends on
    what else the process frees."""
    readings = iter([100 * MEGABYTE])
    monkeypatch.setattr(harness, "current_rss_bytes", lambda: next(readings))
    monkeypatch.setattr(harness, "peak_rss_bytes", lambda: 300 * MEGABYTE)
    for took, scope in ((True, "call"), (False, "process")):
        readings = iter([100 * MEGABYTE])
        monkeypatch.setattr(harness, "reset_peak", lambda took=took: took)
        row = harness.time_entry(snapshots[12], harness.menu(12)[0], scenario_id=SCENARIO,
                                 world_count=12, formation="4-3-3", opt_in=False)
        assert (row.rss_before_bytes, row.peak_rss_bytes, row.rss_scope) == (
            100 * MEGABYTE, 300 * MEGABYTE, scope)


def test_the_measured_fields_hold_what_they_name(harness, snapshots, recorded,
                                                 monkeypatch) -> None:
    """A tool that sleeps and holds 64 MB: tool_s holds the call, the peak the memory, and the
    solve columns the sums and maxima of the tool's own recorded times."""
    original = risk.tail_selection
    held = []

    def heavy(*args, **kwargs):
        block = b"\x01" * (64 * MEGABYTE)  # every page written: resident
        held.append(harness.current_rss_bytes())
        time.sleep(0.3)
        del block
        return original(*args, **kwargs)

    monkeypatch.setattr(risk, "tail_selection", heavy)
    row = harness.time_entry(snapshots[40], harness.menu(40)[2], scenario_id=SCENARIO,
                             world_count=40, formation="4-3-3", opt_in=False)
    assert row.tool_seconds >= 0.3 and row.route_seconds >= row.tool_seconds
    if held[0] is not None:
        # The peak is the high-water mark since the call began, so at least the resident size
        # while the block was held. Not the size before the call plus the block: the process
        # can free memory between the reset and the allocation, and in CI it freed more than
        # the block (peak equal to the size before, to the byte). The kernel's resident
        # counters are approximate (per-CPU batches), and the high-water mark it records can
        # trail a direct VmRSS read by a few pages, hence 4 MB of slack against a 64 MB block.
        assert row.peak_rss_bytes >= held[0] - 4 * MEGABYTE
    (result,) = [call.result for call in recorded]
    run = [r for r in result.certificate.records
           if r.purpose in ("SELECTION", "MEMBERSHIP") and r.status != "NOT_RUN"]
    walls = result.provenance["risk_solve_wall_times"]
    spent = [t["deterministic_time"] for t in result.provenance["risk_solve_deterministic_times"]]
    for purpose, prefix in (("SELECTION", "selection"), ("MEMBERSHIP", "membership")):
        picked = [i for i, record in enumerate(run) if record.purpose == purpose]
        assert getattr(row, f"{prefix}_solves") == len(picked)
        assert getattr(row, f"{prefix}_wall_seconds") == pytest.approx(
            sum(walls[i] for i in picked))
        assert getattr(row, f"{prefix}_max_wall_seconds") == max(walls[i] for i in picked)
        assert getattr(row, f"{prefix}_deterministic_seconds") == pytest.approx(
            sum(spent[i] for i in picked))
        assert getattr(row, f"{prefix}_max_deterministic_seconds") == max(spent[i]
                                                                          for i in picked)
        assert getattr(row, f"{prefix}_at_limit") == 0
    assert row.membership_solves == 14 and row.membership_wall_seconds > \
        row.membership_max_wall_seconds


def test_the_process_peak_is_the_largest_per_call_peak(harness, snapshots, monkeypatch,
                                                      capsys) -> None:
    row = harness.TimingRow(**{field.name: None for field in
                               dataclasses.fields(harness.TimingRow)})
    peaks = iter([5, None, 9, 3, 4, 2])  # megabytes, in call order; the largest is not last

    def fake(snap, entry, **kwargs):
        peak = next(peaks)
        return dataclasses.replace(row, start="cold" if snap is None else "warm",
                                   finalized=True,
                                   peak_rss_bytes=None if peak is None else peak * MEGABYTE)

    monkeypatch.setattr(harness, "time_entry", fake)
    monkeypatch.setattr(harness, "format_row", lambda row, widths=None: "row")
    assert harness.main(["--scenarios", SCENARIO, "--worlds", "12", "--opt-in", "off",
                         "--formations", "4-3-3"]) == 0
    assert "calls: 6 (1 cold, 5 warm); process peak_rss_mb 9 (the largest per-call peak)" \
        in capsys.readouterr().out
    assert harness.process_peak([]) is None


def test_a_solve_at_the_deterministic_limit_is_counted(harness) -> None:
    records = (SimpleNamespace(purpose="SELECTION", status="FEASIBLE"),
               SimpleNamespace(purpose="MEMBERSHIP", status="OPTIMAL"),
               SimpleNamespace(purpose="WORLD_LEAST", status="OPTIMAL"),
               SimpleNamespace(purpose="MEMBERSHIP", status="NOT_RUN"),
               SimpleNamespace(purpose="MEMBERSHIP", status="UNKNOWN"))
    result = SimpleNamespace(
        certificate=SimpleNamespace(records=records, selection_deterministic_limit=40.0),
        provenance={"risk_solve_wall_times": [9.0, 0.5, 7.0],
                    "risk_solve_deterministic_times": [{"deterministic_time": 40.0},
                                                       {"deterministic_time": 0.25},
                                                       {"deterministic_time": 40.5}]})
    times = harness._solve_times(result)
    assert times["SELECTION"] == harness.SolveTimes(1, 9.0, 40.0, 9.0, 40.0, 1)
    assert times["MEMBERSHIP"] == harness.SolveTimes(2, 7.5, 40.75, 7.0, 40.5, 1)


def test_a_cold_call_builds_the_snapshot_inside_the_routes_budget(harness, snapshots,
                                                                  recorded) -> None:
    snapshots["delay"] = 0.5
    entry = harness.menu(40)[-1]
    row = harness.time_entry(None, entry, scenario_id=SCENARIO, world_count=40,
                             formation="4-3-3", opt_in=False)
    assert snapshots["cleared"] == [0] and snapshots["asked"] == [(SCENARIO, 40)]
    (call,) = recorded
    assert call.kwargs["worlds"] is snapshots[40].worlds
    budget = runtime.BUDGETS[entry.route]
    # The budget started before the build: the tool's deadline leaves it the budget less it.
    assert budget - 5.0 < call.left <= budget - 0.5
    assert (row.start, row.budget_seconds, row.completeness) == ("cold", budget, "EXACT")
    assert row.snapshot_seconds >= 0.5
    assert row.route_seconds >= row.snapshot_seconds + row.tool_seconds
    line = harness.format_row(row)
    assert (column(harness, line, "start"), column(harness, line, "snap_s")) == (
        "cold", f"{row.snapshot_seconds:.3f}")


def test_a_budget_override_replaces_the_routes(harness, snapshots, recorded) -> None:
    row = harness.time_entry(snapshots[12], harness.menu(12)[0], scenario_id=SCENARIO,
                             world_count=12, formation="4-3-3", opt_in=True,
                             budget_seconds=900.0)
    assert row.budget_seconds == 900.0 and row.opt_in is True
    assert 895.0 < recorded[0].left <= 900.0


def test_a_refused_finalize_is_printed_and_fails_the_run(harness, snapshots, monkeypatch,
                                                        capsys) -> None:
    def refuse(payload, **kwargs):
        raise runtime.BoundaryViolation("planted")

    monkeypatch.setattr(runtime, "finalize", refuse)
    row = harness.time_entry(snapshots[12], harness.menu(12)[0], scenario_id=SCENARIO,
                             world_count=12, formation="4-3-3", opt_in=False)
    assert row.finalized is False
    assert row.error is None
    assert harness.format_row(row).split()[-2:] == ["REFUSED", "-"]
    # The router answers a refused envelope with a 500: no request at that count is answered.
    assert harness.main(["--scenarios", SCENARIO, "--worlds", "12", "--opt-in", "off",
                         "--formations", "4-3-3", "--rules", "WORST_WORLD"]) == 1
    out = capsys.readouterr().out
    assert "finalize refused: 2; errors: 0" in out


def test_recorded_times_that_do_not_line_up_with_the_records_are_refused(harness) -> None:
    records = (SimpleNamespace(purpose="SELECTION", status="OPTIMAL"),
               SimpleNamespace(purpose="MEMBERSHIP", status="OPTIMAL"))
    result = SimpleNamespace(
        certificate=SimpleNamespace(records=records),
        provenance={"risk_solve_wall_times": [0.1],
                    "risk_solve_deterministic_times": [{"deterministic_time": 0.1}]})
    with pytest.raises(RuntimeError, match="line up"):
        harness._solve_times(result)


# --------------------------------------------------------------------------- the output


def test_the_printed_fields_are_statuses_counts_seconds_memory_and_worlds(harness) -> None:
    assert [field.name for field in dataclasses.fields(harness.TimingRow)] == [
        "scenario_id", "world_count", "formation", "start", "rule", "tail_count", "opt_in",
        "status", "completeness", "stopped_by", "membership_completeness", "selection_status",
        "solves", "selection_solves", "membership_solves", "world_least_solves", "not_run",
        "snapshot_seconds", "tool_seconds", "route_seconds", "selection_wall_seconds",
        "membership_wall_seconds", "selection_max_wall_seconds", "membership_max_wall_seconds",
        "selection_deterministic_seconds", "membership_deterministic_seconds",
        "selection_max_deterministic_seconds", "membership_max_deterministic_seconds",
        "selection_at_limit", "membership_at_limit", "budget_seconds", "rss_before_bytes",
        "peak_rss_bytes", "rss_scope", "used_worlds", "discarded_worlds", "finalized", "error",
    ]
    assert len(harness.HEADER) == len(dataclasses.fields(harness.TimingRow))
    words = {"player", "lineup", "loss", "pair", "frequency", "shortfall", "name", "tail_sum"}
    assert not {name for name in harness.HEADER
                for word in words if word in name.lower()}


def loss_texts(result) -> set[str]:
    """Every loss integer of a result with four or more digits, and its exact decimal text."""
    q = result.certificate.quantization
    values: list[int] = []
    pairs = [row.selected for row in result.world_losses]
    pairs += [row.world_least for row in result.world_losses if row.world_least is not None]
    if result.point_loss is not None:
        pairs.append(result.point_loss)
    for pair in pairs:
        values += [pair.maximum_shortfall, pair.total_shortfall]
    if result.tail_sum is not None:
        values += [result.tail_sum.summed_maximum_shortfall,
                   result.tail_sum.summed_total_shortfall]
    texts = set()
    for value in values:
        if abs(value) >= 1000:
            texts |= {str(value), x._units(value, q)}
    return texts


def test_the_output_holds_no_player_id_name_or_loss_value(harness, snapshots, recorded,
                                                         capsys) -> None:
    assert harness.main(["--scenarios", SCENARIO, "--worlds", "12", "40", "--rules",
                         "TAIL", "MINIMAX_REGRET", "--opt-in", "on"]) == 0
    out = capsys.readouterr().out
    # At each world count: the first TAIL entry cold, then for each formation three tail
    # entries and REGRET.
    assert len(recorded) == 2 * (1 + 2 * 4)
    assert snapshots["asked"] == [(SCENARIO, 12)] * 2 + [(SCENARIO, 40)] * 2
    assert snapshots["cleared"] == [0, 2]
    results = [call.result for call in recorded]
    assert all(result.status == "CERTIFIED" for result in results)
    lineup_ids = {pid for result in results for _, pid in result.lineup if pid is not None}
    assert lineup_ids, "the check would pass on no lineup"
    texts = set().union(*(loss_texts(result) for result in results))
    assert len(texts) >= 4, "the check would pass on no loss value"
    for pid, name in NAMES.items():
        assert not re.search(rf"(?<![\d.]){pid}(?![\d.])", out), pid
        assert name not in out
    for text in texts:
        assert not re.search(rf"(?<![\d.]){re.escape(text)}(?![\d.])", out), text
    rows = [line for line in out.splitlines() if line.lstrip().startswith(SCENARIO)]
    assert len(rows) == 18
    assert all(len(line.split()) == len(harness.HEADER) for line in rows)
    assert [column(harness, line, "start") for line in rows].count("cold") == 2
    assert {column(harness, line, "formation") for line in rows} == set(FORMATIONS)
    assert "EXACT: 18 of 18; finalize refused: 0; errors: 0" in out
    assert "calls: 18 (2 cold, 16 warm); process peak_rss_mb " in out
    assert "membership solves are summarised, not listed one by one" in out


def test_a_call_that_raises_is_recorded_by_name_and_the_run_goes_on(harness, snapshots,
                                                                   monkeypatch,
                                                                   capsys) -> None:
    def refuse(*args, **kwargs):
        raise ValueError(risk.RISK_OVERFLOW)

    monkeypatch.setattr(risk, "tail_selection", refuse)
    assert harness.main(["--scenarios", SCENARIO, "--worlds", "40", "--opt-in", "off",
                         "--formations", "4-3-3"]) == 1
    out = capsys.readouterr().out
    rows = [line for line in out.splitlines() if line.lstrip().startswith(SCENARIO)]
    assert [tuple(column(harness, line, name) for name in ("start", "rule", "status", "error"))
            for line in rows] == [
        ("cold", "WORST_WORLD", "CERTIFIED", "-"), ("warm", "WORST_WORLD", "CERTIFIED", "-"),
        ("warm", "TAIL", "ERROR", "RISK_OVERFLOW"), ("warm", "TAIL", "ERROR", "RISK_OVERFLOW"),
        ("warm", "TAIL", "ERROR", "RISK_OVERFLOW"), ("warm", "MINIMAX_REGRET", "CERTIFIED", "-")]
    assert risk.RISK_OVERFLOW not in out
    assert "errors: 3" in out
    assert harness.error_name(KeyError("970101"), risk) == "KeyError"
