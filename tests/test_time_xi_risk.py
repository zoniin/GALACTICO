"""The declared-risk timing harness (``scripts/time_xi_risk.py``), on a synthetic snapshot.

Claim: the harness times the calls XI Lab's risk routes make: the router's own menu at each
world count (WORST_WORLD at 1, TAIL at ``TAIL_MENU[B]``, MINIMAX_REGRET), the router's own
``_risk`` on the snapshot of the router's loader, under the route's budget, with the tool
called once with the router's arguments; by default every shipped scenario, 12 and 40 worlds,
without and with the experimental opt-in. What it prints is pinned to statuses, completeness,
solves, seconds, memory and world counts: no player id, no player name and no loss value of
any result reaches its output.

Non-claim: no corpus is read; the snapshot is patched into the router's loader as in
``tests/test_xi_extensions_api.py``. Nothing here says how long the corpus solves take; the
root runs the harness in the ``root-checks`` workflow.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from galactico.api import decision_lab, runtime
from galactico.api import xi_extensions as x
from galactico.optimization.xi import risk

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "time_xi_risk.py"
METRICS = ("progression", "left_pass_origins", "right_pass_origins")
SCENARIO = "madrid-2018-05-06"

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
def snapshots(monkeypatch) -> dict[int, SimpleNamespace]:
    made = {12: make_snapshot(12), 40: make_snapshot(40)}
    asked: list[tuple[str, int]] = []

    def loader(scenario_id: str, worlds: int) -> SimpleNamespace:
        asked.append((scenario_id, worlds))
        return made[worlds]

    monkeypatch.setattr("galactico.api.xi_extensions._match_snapshot", loader)
    made["asked"] = asked
    return made


@pytest.fixture
def recorded(monkeypatch) -> list[tuple[str, dict, object]]:
    """Every tool call the router makes: (tool name, keyword arguments, result)."""
    calls: list[tuple[str, dict, object]] = []
    for name in ("worst_world_selection", "tail_selection", "minimax_regret_selection"):
        original = getattr(risk, name)

        def record(*args, _name=name, _original=original, **kwargs):
            result = _original(*args, **kwargs)
            calls.append((_name, kwargs, result))
            return result

        monkeypatch.setattr(risk, name, record)
    return calls


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
        seen.append((scenario_id, world_count, opt_in, entry.rule, entry.tail_count,
                     formation, budget_seconds))
        return blank

    monkeypatch.setattr(harness, "time_entry", fake)
    monkeypatch.setattr(harness, "format_row", lambda row, widths=None: "row")
    assert harness.main([]) == 0
    expected = [
        (scenario, worlds, opt_in, entry.rule, entry.tail_count, "4-3-3", None)
        for scenario in decision_lab.SCENARIOS for worlds in (12, 40)
        for opt_in in (False, True) for entry in harness.menu(worlds)
    ]
    assert seen == expected and len(seen) == 40
    assert snapshots["asked"] == [(s, w) for s in decision_lab.SCENARIOS for w in (12, 40)]


# ----------------------------------------------------------------------------- the calls


def test_each_call_is_the_routers_call_under_the_route_budget(harness, snapshots,
                                                             recorded) -> None:
    worst, tail, regret = harness.menu(40)[0], harness.menu(40)[3], harness.menu(40)[-1]
    rows = [harness.time_entry(snapshots[40], entry, scenario_id=SCENARIO, world_count=40,
                               formation="4-3-3", opt_in=False) for entry in (worst, tail, regret)]
    assert [name for name, _, _ in recorded] == ["worst_world_selection", "tail_selection",
                                                 "minimax_regret_selection"]
    for name, kwargs, _ in recorded:
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
    assert rows[-1].world_least_solves > 0 and rows[0].world_least_solves == 0


def test_a_budget_override_replaces_the_routes(harness, snapshots, recorded) -> None:
    row = harness.time_entry(snapshots[12], harness.menu(12)[0], scenario_id=SCENARIO,
                             world_count=12, formation="4-3-3", opt_in=True,
                             budget_seconds=900.0)
    assert row.budget_seconds == 900.0 and row.opt_in is True


def test_a_refused_finalize_is_printed_not_raised(harness, snapshots, monkeypatch) -> None:
    def refuse(payload, **kwargs):
        raise runtime.BoundaryViolation("planted")

    monkeypatch.setattr(runtime, "finalize", refuse)
    row = harness.time_entry(snapshots[12], harness.menu(12)[0], scenario_id=SCENARIO,
                             world_count=12, formation="4-3-3", opt_in=False)
    assert row.finalized is False
    assert row.error is None
    assert harness.format_row(row).split()[-2:] == ["REFUSED", "-"]


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
        "scenario_id", "world_count", "rule", "tail_count", "opt_in", "status", "completeness",
        "stopped_by", "membership_completeness", "selection_status", "solves",
        "selection_solves", "membership_solves", "world_least_solves", "not_run",
        "tool_seconds", "route_seconds", "selection_wall_seconds", "membership_wall_seconds",
        "selection_deterministic_seconds", "membership_deterministic_seconds",
        "budget_seconds", "rss_before_bytes", "peak_rss_bytes", "rss_scope", "used_worlds",
        "discarded_worlds", "finalized", "error",
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
    assert len(recorded) == 2 * 4  # at each world count, three tail entries and REGRET
    results = [result for _, _, result in recorded]
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
    assert len(rows) == 8
    assert all(len(line.split()) == len(harness.HEADER) for line in rows)
    assert "EXACT: 8 of 8; finalize refused: 0; errors: 0" in out


def test_a_call_that_raises_is_recorded_by_name_and_the_run_goes_on(harness, snapshots,
                                                                   monkeypatch,
                                                                   capsys) -> None:
    def refuse(*args, **kwargs):
        raise ValueError(risk.RISK_OVERFLOW)

    monkeypatch.setattr(risk, "tail_selection", refuse)
    assert harness.main(["--scenarios", SCENARIO, "--worlds", "40", "--opt-in", "off"]) == 1
    out = capsys.readouterr().out
    rows = [line.split() for line in out.splitlines() if line.lstrip().startswith(SCENARIO)]
    assert [(row[2], row[5], row[-1]) for row in rows] == [
        ("WORST_WORLD", "CERTIFIED", "-"), ("TAIL", "ERROR", "RISK_OVERFLOW"),
        ("TAIL", "ERROR", "RISK_OVERFLOW"), ("TAIL", "ERROR", "RISK_OVERFLOW"),
        ("MINIMAX_REGRET", "CERTIFIED", "-")]
    assert risk.RISK_OVERFLOW not in out
    assert "errors: 3" in out
    assert harness.error_name(KeyError("970101"), risk) == "KeyError"
