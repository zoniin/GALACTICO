#!/usr/bin/env python
"""Time the declared-risk solves XI Lab's risk routes would make, at 12 worlds and at 40.

    python scripts/time_xi_risk.py                         # every scenario and formation
    python scripts/time_xi_risk.py --worlds 40 --opt-in off --formations 4-3-3
    python scripts/time_xi_risk.py --budget-seconds 900    # not the router's budget

Why (ROOT-DECISIONS 2.7 X5; OR-XI-SPEC 7.1, 11 item 15 and 14): the 40-world declared-risk
option ships only after its TAIL, WORST_WORLD and REGRET selection and membership solves are
timed on the corpus, and the change that adds 40 worlds to the menu records the run times and
the peak memory. This harness is that measurement and nothing else.

What it runs. For each scenario of ``decision_lab.SCENARIOS``, each world count (12, the
reference; 40, on the menu since its timing on the corpus, run 39163120253), each formation the
request model accepts (``4-3-3`` and ``4-3-1-2``: 40 worlds is offered for both), without and
with the experimental opt-in, and each entry of the router's own menu
(``xi_extensions._rule_options``: ``WORST_WORLD`` at 1, ``TAIL`` at each count of
``TAIL_MENU[B]``, ``MINIMAX_REGRET``), it makes the call the router makes: the route's budget
is ``runtime.budget_for(route)``; then, inside
``runtime.long_job(route)``, ``xi_extensions._risk`` (which declares the problem and calls the
tool with the deadline the router passes) and ``runtime.finalize``, the body of ``_answer``'s
``compute`` without the result cache. The snapshot is the router's loader's,
``xi_extensions._match_snapshot(scenario_id, B)``. The tool call is timed by a wrapper around
the three tool functions of ``optimization.xi.risk`` that ``_risk`` looks up, so the arguments
are the router's own. Every request is validated by the request model, as the router validates
it: both world counts are in ``OFFERED_WORLDS`` since X5 was met, and a tail count off
``TAIL_MENU`` is refused with the router's own sentence.

Cold and warm calls. In the router the budget starts in ``_answer``, before the snapshot is
built, so the first request of a scenario at B on an empty cache leaves the tool the route's
budget less the build. The first timed entry of each scenario and world count is therefore
made cold first (``start`` cold): the loader's cache is cleared, the budget starts, and the
snapshot is built inside it, inside the long job, as ``compute`` builds it; ``snap_s`` is that
build and ``route_s`` the whole request. Then every entry, that one again included, is made
warm (``start`` warm), on the snapshot now built, the budget starting just before ``_risk``, as
on a request whose snapshot is in the cache. Which figures ADR-0030 records: the run time of
each call and of its solves from the warm rows (``tool_s``, the selection and membership wall
and deterministic seconds); from each cold row, whether the first request of that scenario at
that world count is answered within the route's budget once the build is paid (its
``completeness``, and ``route_s`` against ``budget_s``); and the peak memory, the process peak
on the closing line (the largest per-call peak, the cold calls' builds included), with one
router snapshot built at a time: the loader is cleared before each cold call, while the
router keeps up to four.

What it prints, and nothing else (OR-XI-SPEC 7.1 and 1.6: no lineup, pair or selection is
printed or kept, so the timing adds no prior exposure for E-13): per call, the status, the
completeness and what stopped it, the membership block's completeness, the selection solve's
status, the solves (all, and per purpose: selection, membership, world least; and the calls the
deadline skipped), the wall seconds (the cold call's snapshot build; the tool call; the route
from its budget's start to the end of finalize; the selection and the membership solves, summed
and the largest single solve), their deterministic seconds (summed and the largest), the solves
whose deterministic time reached the selection limit, the budget, the resident memory before
the call and its peak during it, the worlds used and discarded, and for a call that raised (the
router would answer it with an error) the name of the tool's sentence it carried, or the
exception's class, never its message. Never a player id or name, a lineup, a loss or a
frequency. Departure from 7.1's "per solve", stated in the output for ADR-0030: the membership
solves are summarised, not listed one by one (their statuses in candidate order would say who
is in every XI, 1.6); the membership completeness, the summed and largest seconds and the count
at the limit stand for them. Each call's result and envelope are dropped once these fields are
read. The run goes on after a failing call and exits 1 when any call raised or had its envelope
refused by ``finalize`` (the router answers both with an error).

Peak memory is ``VmHWM``, reset before each call through ``/proc/self/clear_refs`` where Linux
allows it (scope ``call``); elsewhere the process's high-water mark so far (scope
``process``). The process peak is the largest of the per-call peaks.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

WORLD_COUNTS: tuple[int, ...] = (12, 40)
RULE_NAMES: tuple[str, ...] = ("WORST_WORLD", "TAIL", "MINIMAX_REGRET")
TOOLS: dict[str, str] = {"WORST_WORLD": "worst_world_selection", "TAIL": "tail_selection",
                         "MINIMAX_REGRET": "minimax_regret_selection"}
SCOPED: tuple[str, ...] = ("SELECTION", "MEMBERSHIP")  # the calls whose times the tool records
MEGABYTE = 1024 * 1024


# ------------------------------------------------------------------------------- memory


def _status_kilobytes(field: str) -> int | None:
    try:
        with open("/proc/self/status", encoding="ascii") as status:
            for line in status:
                if line.startswith(field + ":"):
                    return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def current_rss_bytes() -> int | None:
    found = _status_kilobytes("VmRSS")
    return None if found is None else found * 1024


def peak_rss_bytes() -> int | None:
    """The resident high-water mark: ``VmHWM`` on Linux, ``ru_maxrss`` elsewhere."""
    found = _status_kilobytes("VmHWM")
    if found is not None:
        return found * 1024
    try:
        import resource
    except ImportError:
        return None
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return peak if sys.platform == "darwin" else peak * 1024


def reset_peak() -> bool:
    """Set ``VmHWM`` to the current RSS (Linux, ``clear_refs`` value 5); False where refused."""
    try:
        with open("/proc/self/clear_refs", "w", encoding="ascii") as handle:
            handle.write("5")
    except OSError:
        return False
    return True


def _megabytes(size: int | None) -> str:
    return "n/a" if size is None else f"{size / MEGABYTE:.0f}"


# ------------------------------------------------------------------------------ the menu


@dataclass(frozen=True)
class Entry:
    """One menu entry of the router at one world count, and the route that serves it."""

    route: str  # xi.risk.tail | xi.risk.regret
    rule: str
    tail_count: int | None  # as the request carries it: None for WORST_WORLD and REGRET


def menu(world_count: int) -> tuple[Entry, ...]:
    """The entries ``xi_extensions._rule_options`` offers at ``world_count``, in its order."""
    from galactico.api import xi_extensions

    entries = []
    for option in xi_extensions._rule_options(world_count):
        rule = option["rule"]
        if rule == "MINIMAX_REGRET":
            entries.append(Entry("xi.risk.regret", rule, None))
        elif rule == "WORST_WORLD":
            entries.append(Entry("xi.risk.tail", rule, None))
        else:
            entries.append(Entry("xi.risk.tail", rule, int(option["tail_count"])))
    return tuple(entries)


def request_for(entry: Entry, *, scenario_id: str, world_count: int, formation: str,
                opt_in: bool) -> Any:
    """The request body the router would receive for ``entry``, validated by the request
    model as the router validates it (a world count off ``OFFERED_WORLDS`` or a tail count off
    ``TAIL_MENU[world_count]`` is refused there).
    """
    from galactico.api import xi_extensions as x

    body: dict[str, Any] = {"scenario_id": scenario_id, "formation": formation,
                            "experimental_opt_in": opt_in, "bootstrap_worlds": world_count}
    model: Any = x.RiskRegretRequest
    if entry.route == "xi.risk.tail":
        model = x.RiskTailRequest
        body["rule"] = entry.rule
        if entry.tail_count is not None:
            body["tail_count"] = entry.tail_count
    return model.model_validate(body)


# --------------------------------------------------------------------------- the timing


@dataclass(frozen=True)
class TimingRow:
    """Everything this harness prints about one call. No field holds a player, a lineup, a
    loss or a frequency; a test pins the field names."""

    scenario_id: str
    world_count: int
    formation: str
    start: str  # cold: the snapshot built inside the budget | warm: the snapshot already built
    rule: str
    tail_count: int | None  # the result's k: 1 for WORST_WORLD, None for REGRET
    opt_in: bool
    status: str
    completeness: str
    stopped_by: str | None
    membership_completeness: str
    selection_status: str | None  # the selection solve's CP-SAT status; None when not called
    solves: int
    selection_solves: int
    membership_solves: int
    world_least_solves: int
    not_run: int
    snapshot_seconds: float | None  # the cold call's snapshot build; None when warm
    tool_seconds: float
    route_seconds: float  # from the budget's start to the end of finalize
    selection_wall_seconds: float
    membership_wall_seconds: float
    selection_max_wall_seconds: float  # the largest single solve
    membership_max_wall_seconds: float
    selection_deterministic_seconds: float
    membership_deterministic_seconds: float
    selection_max_deterministic_seconds: float
    membership_max_deterministic_seconds: float
    selection_at_limit: int  # solves whose deterministic time reached the selection limit
    membership_at_limit: int
    budget_seconds: float
    rss_before_bytes: int | None
    peak_rss_bytes: int | None
    rss_scope: str  # call | process
    used_worlds: int
    discarded_worlds: int
    finalized: bool
    # A call that raised, as the router would answer it with an error: the name of the risk
    # module's sentence the exception carries, else its class; never the message itself.
    error: str | None = None


@contextlib.contextmanager
def tool_probe(module: Any) -> Iterator[list[tuple[Any, float]]]:
    """Wrap the three tool functions of ``module``; each call appends (result, seconds)."""
    calls: list[tuple[Any, float]] = []
    originals = {name: getattr(module, name) for name in TOOLS.values()}

    def timed(function: Callable[..., Any]) -> Callable[..., Any]:
        def call(*args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter()
            result = function(*args, **kwargs)
            calls.append((result, time.perf_counter() - started))
            return result
        return call

    for name, function in originals.items():
        setattr(module, name, timed(function))
    try:
        yield calls
    finally:
        for name, function in originals.items():
            setattr(module, name, function)


@dataclass(frozen=True)
class SolveTimes:
    """The solves of one purpose, summarised: no time in call order leaves this harness."""

    solves: int
    wall: float  # summed seconds
    deterministic: float
    largest_wall: float  # the largest single solve; 0 without a solve
    largest_deterministic: float
    at_limit: int  # recorded deterministic time at or above the certificate's selection limit


def _solve_times(result: Any) -> dict[str, SolveTimes]:
    """The selection and the membership calls' times, per purpose.

    The tool records a wall and a deterministic time for each call it makes itself, in call
    order: the records whose purpose is SELECTION or MEMBERSHIP and that were run. Both purposes
    run under ``certificate.selection_deterministic_limit``.
    """
    records = [r for r in result.certificate.records
               if r.purpose in SCOPED and r.status != "NOT_RUN"]
    walls = [float(wall) for wall in result.provenance.get("risk_solve_wall_times", ())]
    spent = [float(row["deterministic_time"])
             for row in result.provenance.get("risk_solve_deterministic_times", ())]
    if not len(records) == len(walls) == len(spent):
        raise RuntimeError("the tool's recorded times do not line up with its solve records")
    limit = float(result.certificate.selection_deterministic_limit)
    out = {}
    for purpose in SCOPED:
        picked = [i for i, record in enumerate(records) if record.purpose == purpose]
        wall = [walls[i] for i in picked]
        deterministic = [spent[i] for i in picked]
        out[purpose] = SolveTimes(
            solves=len(picked), wall=sum(wall), deterministic=sum(deterministic),
            largest_wall=max(wall, default=0.0),
            largest_deterministic=max(deterministic, default=0.0),
            at_limit=sum(1 for value in deterministic if value >= limit))
    return out


def error_name(error: BaseException, module: Any) -> str:
    """The name of the string constant of ``module`` that is the error's text, else its class."""
    text = str(error)
    for name in getattr(module, "__all__", ()):
        if text and getattr(module, name, None) == text:
            return name
    return type(error).__name__


def summarise(result: Any, *, scenario_id: str, world_count: int, formation: str, start: str,
              opt_in: bool, snapshot_seconds: float | None, tool_seconds: float,
              route_seconds: float, budget_seconds: float, rss_before: int | None,
              peak_rss: int | None, rss_scope: str, finalized: bool,
              error: str | None = None) -> TimingRow:
    """The printable fields of one call, read from the tool's result and nothing else."""
    certificate = result.certificate
    records = certificate.records
    times = _solve_times(result)
    selection, membership = times["SELECTION"], times["MEMBERSHIP"]
    statuses = [r.status for r in records if r.purpose == "SELECTION"]
    return TimingRow(
        scenario_id=scenario_id,
        world_count=world_count,
        formation=formation,
        start=start,
        rule=result.rule,
        tail_count=result.tail_count,
        opt_in=opt_in,
        status=result.status,
        completeness=certificate.completeness,
        stopped_by=certificate.stopped_by,
        membership_completeness=result.membership.completeness,
        selection_status=statuses[-1] if statuses else None,
        solves=certificate.solves,
        selection_solves=selection.solves,
        membership_solves=membership.solves,
        world_least_solves=sum(1 for r in records
                               if r.purpose == "WORLD_LEAST" and r.status != "NOT_RUN"),
        not_run=sum(1 for r in records if r.status == "NOT_RUN"),
        snapshot_seconds=snapshot_seconds,
        tool_seconds=tool_seconds,
        route_seconds=route_seconds,
        selection_wall_seconds=selection.wall,
        membership_wall_seconds=membership.wall,
        selection_max_wall_seconds=selection.largest_wall,
        membership_max_wall_seconds=membership.largest_wall,
        selection_deterministic_seconds=selection.deterministic,
        membership_deterministic_seconds=membership.deterministic,
        selection_max_deterministic_seconds=selection.largest_deterministic,
        membership_max_deterministic_seconds=membership.largest_deterministic,
        selection_at_limit=selection.at_limit,
        membership_at_limit=membership.at_limit,
        budget_seconds=budget_seconds,
        rss_before_bytes=rss_before,
        peak_rss_bytes=peak_rss,
        rss_scope=rss_scope,
        used_worlds=len(certificate.used_world_ids),
        discarded_worlds=certificate.discarded_world_count,
        finalized=finalized,
        error=error,
    )


def failed_row(entry: Entry, *, scenario_id: str, world_count: int, formation: str,
               start: str, opt_in: bool, snapshot_seconds: float | None,
               route_seconds: float, budget_seconds: float, rss_before: int | None,
               peak_rss: int | None, rss_scope: str, error: str) -> TimingRow:
    """A call that raised before the tool returned: its time to the error and nothing else."""
    return TimingRow(
        scenario_id=scenario_id, world_count=world_count, formation=formation, start=start,
        rule=entry.rule, tail_count=1 if entry.rule == "WORST_WORLD" else entry.tail_count,
        opt_in=opt_in, status="ERROR", completeness="-", stopped_by=None,
        membership_completeness="-", selection_status=None, solves=0, selection_solves=0,
        membership_solves=0, world_least_solves=0, not_run=0,
        snapshot_seconds=snapshot_seconds, tool_seconds=route_seconds,
        route_seconds=route_seconds, selection_wall_seconds=0.0, membership_wall_seconds=0.0,
        selection_max_wall_seconds=0.0, membership_max_wall_seconds=0.0,
        selection_deterministic_seconds=0.0, membership_deterministic_seconds=0.0,
        selection_max_deterministic_seconds=0.0, membership_max_deterministic_seconds=0.0,
        selection_at_limit=0, membership_at_limit=0,
        budget_seconds=budget_seconds, rss_before_bytes=rss_before, peak_rss_bytes=peak_rss,
        rss_scope=rss_scope, used_worlds=0, discarded_worlds=0, finalized=False, error=error,
    )


def time_entry(snap: Any | None, entry: Entry, *, scenario_id: str, world_count: int,
               formation: str, opt_in: bool, budget_seconds: float | None = None) -> TimingRow:
    """One call as the router makes it, timed; only its ``TimingRow`` leaves this function.

    ``snap`` None makes the call cold: the router's loader's cache is cleared, and the snapshot
    is built inside the budget and the long job, as ``_answer``'s ``compute`` builds it on a
    request whose snapshot is not in the cache. Otherwise the call is warm, on ``snap``.

    A call that raises in the route is recorded (``TimingRow.error``) and the run goes on: the
    router would answer it with an error, which is itself what the measurement has to show. A
    snapshot build that raises stops the run.
    """
    from galactico.api import runtime
    from galactico.api import xi_extensions as x
    from galactico.optimization.xi import risk

    request = request_for(entry, scenario_id=scenario_id, world_count=world_count,
                          formation=formation, opt_in=opt_in)
    cold = snap is None
    if cold:
        x._match_snapshot.cache_clear()  # every built snapshot dropped: this build is the first
    scope = "call" if reset_peak() else "process"
    before = current_rss_bytes()
    budget = (runtime.budget_for(entry.route) if budget_seconds is None
              else runtime.Budget(budget_seconds))
    finalized, failure, snapshot_seconds = True, None, None
    with tool_probe(risk) as calls, runtime.long_job(entry.route):
        started = time.perf_counter()
        if cold:
            snap = x._match_snapshot(scenario_id, world_count)
            snapshot_seconds = time.perf_counter() - started
        try:
            envelope = x._risk(snap, request, budget, entry.rule, entry.tail_count)
        except Exception as error:  # recorded by name; the router answers it as an error
            failure, finalized = error_name(error, risk), False
        else:
            try:
                runtime.finalize(envelope)
            except runtime.BoundaryViolation:
                finalized = False
            del envelope
        route_seconds = time.perf_counter() - started
    del snap
    peak = peak_rss_bytes()
    common = {"scenario_id": scenario_id, "world_count": world_count, "formation": formation,
              "start": "cold" if cold else "warm", "opt_in": opt_in,
              "snapshot_seconds": snapshot_seconds, "route_seconds": route_seconds,
              "budget_seconds": float(budget.seconds), "rss_before": before, "peak_rss": peak,
              "rss_scope": scope}
    if len(calls) > 1:
        raise RuntimeError(f"the route called the tool {len(calls)} times, not once")
    if not calls:
        if failure is None:
            raise RuntimeError("the route returned without calling the tool")
        return failed_row(entry, error=failure, **common)
    result, tool_seconds = calls.pop()
    return summarise(result, tool_seconds=tool_seconds, finalized=finalized, error=failure,
                     **common)


# ------------------------------------------------------------------------------- output

HEADER: tuple[str, ...] = (
    "scenario", "B", "formation", "start", "rule", "k", "opt_in", "status", "completeness",
    "stopped_by", "membership", "selection", "solves", "sel", "mem", "wl", "not_run", "snap_s",
    "tool_s", "route_s", "sel_wall_s", "mem_wall_s", "sel_max_wall_s", "mem_max_wall_s",
    "sel_det_s", "mem_det_s", "sel_max_det_s", "mem_max_det_s", "sel_at_limit", "mem_at_limit",
    "budget_s", "rss_before_mb", "peak_rss_mb", "rss_scope", "used", "discarded", "finalize",
    "error",
)


def _cells(row: TimingRow) -> tuple[str, ...]:
    def seconds(value: float | None) -> str:
        return "-" if value is None else f"{value:.3f}"

    return (
        row.scenario_id, str(row.world_count), row.formation, row.start, row.rule,
        "-" if row.tail_count is None else str(row.tail_count),
        "on" if row.opt_in else "off", row.status, row.completeness, row.stopped_by or "-",
        row.membership_completeness, row.selection_status or "-", str(row.solves),
        str(row.selection_solves), str(row.membership_solves), str(row.world_least_solves),
        str(row.not_run), seconds(row.snapshot_seconds), seconds(row.tool_seconds),
        seconds(row.route_seconds), seconds(row.selection_wall_seconds),
        seconds(row.membership_wall_seconds), seconds(row.selection_max_wall_seconds),
        seconds(row.membership_max_wall_seconds), seconds(row.selection_deterministic_seconds),
        seconds(row.membership_deterministic_seconds),
        seconds(row.selection_max_deterministic_seconds),
        seconds(row.membership_max_deterministic_seconds), str(row.selection_at_limit),
        str(row.membership_at_limit), f"{row.budget_seconds:g}",
        _megabytes(row.rss_before_bytes), _megabytes(row.peak_rss_bytes), row.rss_scope,
        str(row.used_worlds), str(row.discarded_worlds),
        "-" if row.error is not None and not row.finalized
        else "ok" if row.finalized else "REFUSED",
        row.error or "-",
    )


def format_row(row: TimingRow, widths: Sequence[int] | None = None) -> str:
    cells = _cells(row)
    if widths is None:
        return " ".join(cells)
    return " ".join(cell.rjust(width) for cell, width in zip(cells, widths, strict=True))


def header_widths() -> tuple[int, ...]:
    """Fixed widths, so each row prints as it is measured and lines up with the header."""
    floor = {"scenario": 17, "B": 2, "rule": 14, "k": 2, "status": 13, "completeness": 13,
             "stopped_by": 19, "membership": 13, "selection": 13, "snap_s": 9, "tool_s": 9,
             "route_s": 9, "sel_wall_s": 10, "mem_wall_s": 10, "sel_det_s": 9, "mem_det_s": 9,
             "error": 16}
    return tuple(max(len(name), floor.get(name, 0)) for name in HEADER)


def process_peak(rows: Sequence[TimingRow]) -> int | None:
    """The process's peak resident memory over the run: the largest per-call peak."""
    peaks = [row.peak_rss_bytes for row in rows if row.peak_rss_bytes is not None]
    return max(peaks, default=None)


# --------------------------------------------------------------------------------- main


def main(argv: Sequence[str] | None = None) -> int:
    from galactico.api import decision_lab
    from galactico.api import xi_extensions as x

    formations = list(x.XIDeclarations.model_fields["formation"].annotation.__args__)
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenarios", nargs="+", choices=sorted(decision_lab.SCENARIOS),
                        default=list(decision_lab.SCENARIOS))
    parser.add_argument("--worlds", nargs="+", type=int, choices=WORLD_COUNTS,
                        default=list(WORLD_COUNTS))
    parser.add_argument("--opt-in", choices=("both", "off", "on"), default="both")
    parser.add_argument("--rules", nargs="+", choices=RULE_NAMES, default=list(RULE_NAMES))
    parser.add_argument("--formations", nargs="+", choices=formations, default=formations,
                        help="default: every formation the request model accepts")
    parser.add_argument("--budget-seconds", type=float, default=None,
                        help="replace the route's budget (not what the router allows)")
    args = parser.parse_args(argv)
    opt_ins = {"both": (False, True), "off": (False,), "on": (True,)}[args.opt_in]

    print("XI declared-risk timing (ROOT-DECISIONS 2.7 X5; OR-XI-SPEC 7.1, 11 item 15). "
          "Printed: statuses, completeness, solves, seconds, memory and world counts only; no "
          "player, lineup, loss or frequency.")
    budget = ("each route's, runtime.budget_for" if args.budget_seconds is None
              else f"{args.budget_seconds:g} s, replacing each route's")
    tails = "; ".join(f"{b}: {list(k)}" for b, k in x.TAIL_MENU.items())
    print(f"offered world counts today: {list(x.OFFERED_WORLDS)}; tail menu {tails}; "
          f"formations {', '.join(args.formations)}; budget {budget}")
    print("Departure from OR-XI-SPEC 7.1 'per solve', for ADR-0030: the membership solves are "
          "summarised, not listed one by one (their statuses in candidate order would say who "
          "is in every XI, 1.6); the membership completeness, the summed and the largest "
          "single-solve wall and deterministic seconds and the solves at the deterministic "
          "limit stand for them. The selection solve's status is printed.")
    print("start: cold = the snapshot cache cleared and the snapshot built inside the route's "
          "budget, as the first request of a scenario at B; warm = the snapshot already built. "
          "Run times: the warm rows; the first request: the cold rows.")
    print("columns: sel, mem, wl = selection, membership and world-least solves run; not_run = "
          "calls the deadline skipped; snap_s = the cold call's snapshot build; tool_s = the "
          "tool call; route_s = from the budget's start to the end of finalize; sel/mem wall "
          "and det = summed solver wall and deterministic seconds, max = the largest single "
          "solve; at_limit = solves whose deterministic time reached the selection limit.",
          flush=True)

    rows: list[TimingRow] = []
    for scenario_id in args.scenarios:
        for world_count in args.worlds:
            timed = [(formation, opt_in, entry) for formation in args.formations
                     for opt_in in opt_ins for entry in menu(world_count)
                     if entry.rule in args.rules]
            if not timed:
                continue
            widths = header_widths()
            print(" ".join(name.rjust(width) for name, width in zip(HEADER, widths,
                                                                   strict=True)), flush=True)
            snap = None  # the first entry is made cold first: its call builds the snapshot
            for index, (formation, opt_in, entry) in enumerate([timed[0], *timed]):
                if index == 1:  # then warm, on the snapshot the cold call built, from the cache
                    snap = x._match_snapshot(scenario_id, world_count)
                row = time_entry(snap, entry, scenario_id=scenario_id,
                                 world_count=world_count, formation=formation, opt_in=opt_in,
                                 budget_seconds=args.budget_seconds)
                rows.append(row)
                print(format_row(row, widths), flush=True)
            del snap
    cold = sum(1 for row in rows if row.start == "cold")
    print(f"calls: {len(rows)} ({cold} cold, {len(rows) - cold} warm); process peak_rss_mb "
          f"{_megabytes(process_peak(rows))} (the largest per-call peak)")
    complete = sum(1 for row in rows if row.completeness == "EXACT")
    failed = sum(1 for row in rows if row.error is not None)
    refused = sum(1 for row in rows if not row.finalized and row.error is None)
    print(f"EXACT: {complete} of {len(rows)}; finalize refused: {refused}; errors: {failed}")
    return 1 if failed or refused else 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())

