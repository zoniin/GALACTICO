"""Nondominated rounded sums of two or three declared requirements, one XI each, proved complete.
Not a ranking and not a forecast: no point is preferred, and a sum is arithmetic on prior rates.

Claim: for the declared requirements, in the declared order, every vector of their sums in the
shipped rounding (``OBJECTIVE_POLICY`` integers, ``round(Fraction(v) / Fraction(n) * q)``) that
some XI reaches and that no XI's vector matches or exceeds on every declared requirement while
exceeding it on one, each with one XI that reaches it. A ``COMPLETE`` list carries the proof that
none is missing: a final solve of the region left after the cuts is INFEASIBLE. The XIs are those
of the kernel's background (eligibility, the measurement rule over every requirement in force,
locks, exclusions) that meet the declared hard floors, compared conservatively (``HARD_POLICY``).

Non-claim: the certified object is the integer vector, not the witness's raw sums. Two XIs with
different raw sums can share a vector, and an XI whose raw sums no other XI's exceed can be
exceeded after rounding, within ``a_r * n_r / q`` per requirement. With floors, an XI that meets a
raw floor with less than ``(a_r + 1) * n_r / q`` to spare lies outside the region and can lie
above every listed point. Nothing is said about a requirement that was not declared. UNKNOWN,
NOT_RUN, a deterministic limit, a deadline or the point limit is never evidence that no further
point exists, and a list cut by one of them never reads as complete.

How the points are reached (OR-XI-SPEC 4.2), every solve through ``kernel._Run``:

    R_0      background, then each declared floor in ascending id
    stage i  maximise V_i over R_k with V_j = v_j for j < i   OPTIMAL only; v_i = solver.value
    record   v = (v_1, ..., v_d) and the stage-d XI, re-evaluated without the solver
    R_k+1    R_k and OR_i (V_i >= v_i + 1)                       leave the down-set of v
    stop     stage 1 INFEASIBLE, or the limit check INFEASIBLE   no point is missing

Each recorded vector is nondominated when it is recorded: a vector above it would lie in R_k and
be lexicographically above the maximum. So a list cut by a limit or a deadline stays true and is
the lexicographic-largest prefix of the frontier in the declared order. With ``max_points`` listed,
one solve of R_k with no objective decides whether another point exists. No summed or weighted
objective exists anywhere: the dimension order is an enumeration device, not a preference.
"""

from __future__ import annotations

import math
import time
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING

from ortools.sat.python import cp_model

from ..squad.kernel import (
    HARD_POLICY,
    KERNEL_VERSION,
    PER_SOLVE_DETERMINISTIC_LIMIT,
    Lineup,
    ShortfallKernel,
    _at_least,
    _Run,
    fingerprint,
    scrub_lineage,
    source_fingerprints,
)
from .ceilings import FLOORS_CONSERVATIVE, UNFIELDABLE_PROVED
from .domain import FORMATIONS, Candidate, Formation, TacticalRequirement
from .solver import QUANTIZATION, _applies
from .tradeoffs import (
    MAX_EXPRESSION_MAGNITUDE,
    MAX_MAGNITUDE,
    OBJECTIVE_POLICY,
    _finite,
    _scaled,
)

if TYPE_CHECKING:
    from ..squad.kernel import _Background

__all__ = [
    "DIMENSION_COUNTS",
    "FLOORS_CONSERVATIVE",
    "FRONTIER_CLAIM",
    "FRONTIER_NON_CLAIM",
    "FRONTIER_VERSION",
    "MAX_FRONTIER_POINTS",
    "POINT_ORDER",
    "UNFIELDABLE_PROVED",
    "Frontier",
    "FrontierCertificate",
    "FrontierPoint",
    "nondominated_sums",
]

FRONTIER_VERSION = "lexicographic-cut-frontier-v1"
# Mirrors brief.MAX_BRIEF_ROWS; derived from no data (OR-XI-SPEC 1.6).
MAX_FRONTIER_POINTS = 64
DIMENSION_COUNTS = (2, 3)
# One constant, true in every state: a cut list is a prefix in the declared order. "May": a list
# stopped by a deadline can hold every point.
POINT_ORDER = (
    "lexicographic, descending, in the order in which the requirements were declared; when the "
    "list is complete, reversing a two-requirement declaration reverses it; when it is not "
    "complete, the points listed are the first ones in that order, and declaring the "
    "requirements in another order may list other points"
)
# Served word for word on every status. It states no completeness: the router's status
# sentence does, from the certificate (OR-XI-SPEC 7.5, 7.7).
FRONTIER_CLAIM = (
    "Each point listed is a combination of rounded sums of the declared requirements that some XI "
    "reaches and that no XI's rounded sums match or exceed on all of them while exceeding it on "
    "one, shown with one XI that reaches it. Whether the list holds every such combination is "
    "stated with it. The XIs are those the eligibility rules, missing measurements of any "
    "requirement in force, locks, exclusions and declared hard floors allow, each floor compared "
    "conservatively. A rounded sum adds each prior per-90 rate as a multiple of the club median, "
    "rounded half-even to 1/100000, and is printed exactly. Beside each point, the sums of one XI "
    "reaching it before rounding, in the same unit and rounded down; they differ from the point "
    "by no more than the allowance shown."
)
FRONTIER_NON_CLAIM = (
    "Not a ranking: no point is preferred, and the list follows the order in which you declared "
    "the requirements. A point says nothing about requirements you did not declare, and a sum is "
    "arithmetic on prior rates, not a forecast."
)

_SOURCES = ("frontier.py", "../squad/kernel.py", "solver.py", "tradeoffs.py", "domain.py")
_WITNESS = ("OPTIMAL", "FEASIBLE")

_Key = tuple[int, str]


@dataclass(frozen=True)
class FrontierPoint:
    integer_sums: tuple[int, ...]  # V(witness), aligned with the dimensions: THE POINT
    quantized_sums: tuple[float, ...]  # integer_sums[i] * n_i / q, nearest float (never printed)
    raw_sums: tuple[float, ...]  # S_{r_i}(witness), nearest float of the exact sum (never printed)
    lineup: Lineup  # one XI reaching the point; not the only one
    stage_statuses: tuple[str, ...]  # the d stage statuses, all OPTIMAL


@dataclass(frozen=True)
class FrontierCertificate:
    points: int
    pairwise_nondominated: bool  # checked without a solver
    witnesses_verified: bool
    # INFEASIBLE: proof that no point is missing. INFEASIBLE_BY_CONSTRUCTION: a kernel reason.
    # OPTIMAL or FEASIBLE with stopped_by POINT_LIMIT: the limit check found an XI, so another
    # point exists. Otherwise the status of the solve that stopped the search (a stage, or the
    # limit check: FEASIBLE, UNKNOWN, NOT_RUN, MODEL_INVALID): no proof.
    final_region_status: str
    solves: int  # CP-SAT calls actually made
    statuses: tuple[str, ...]  # every call in call order, NOT_RUN for one the deadline skipped
    # COMPLETE (also for a proved empty set) | LIMIT_REACHED | DEADLINE | MODEL_INVALID;
    # FLOORS_UNMET takes that of its undecided cause solve
    completeness: str
    # POINT_LIMIT | DETERMINISTIC_LIMIT | WALL_CLOCK; None when no call is undecided and no
    # limit cut the list
    stopped_by: str | None
    quantization: int
    objective_policy: str
    hard_policy: str
    per_solve_deterministic_limit: float
    raw_rounding_error_bounds: tuple[float, ...]  # e_{r_i} = a_r * n_r / (2q), outward
    max_points: int


@dataclass(frozen=True)
class Frontier:
    formation: str
    dimensions: tuple[str, ...]  # as declared
    # FRONTIER | UNFIELDABLE | NOT_SATISFIABLE | FLOORS_UNMET | INCOMPLETE | MODEL_INVALID
    status: str
    points: tuple[FrontierPoint, ...]  # POINT_ORDER
    point_order: str
    floors: tuple[tuple[str, float], ...]  # (requirement_id, floor) ascending; () when none
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    certificate: FrontierCertificate
    claim: str  # FRONTIER_CLAIM, word for word, on every status; it states no completeness
    non_claim: str  # FRONTIER_NON_CLAIM, word for word
    reasons: tuple[str, ...]
    provenance: dict


class _Calls:
    """Every CP-SAT call of one enumeration, in call order, with the times of OR-XI-SPEC 1.5.

    A call the deadline skipped (``_Run.solve`` returns no solver) is ``NOT_RUN``, never
    ``UNKNOWN``, and has no time entry. Only the last call can be undecided or refused: the
    search stops at it.
    """

    def __init__(self, deadline: float, seed: int) -> None:
        self._run = _Run(deadline, seed)
        self._deadline = deadline
        self.statuses: list[str] = []
        self.deterministic_times: list[dict] = []
        self.wall_times: list[float] = []
        self._last_reached_limit = False

    def solve(self, model: cp_model.CpModel) -> tuple[str, cp_model.CpSolver | None]:
        name, solver = self._run.solve(model)
        returned = time.monotonic()
        if solver is None:
            self.statuses.append("NOT_RUN")
            self._last_reached_limit = False
            return "NOT_RUN", None
        spent = float(solver.deterministic_time)
        self.statuses.append(name)
        # CP-SAT's float sum can differ by one ulp between identical solves (ortools 9.15), so
        # the record keeps ten significant digits, which repeat; the limit test reads ``spent``.
        recorded = float(f"{spent:.10g}")
        self.deterministic_times.append({"status": name, "deterministic_time": recorded})
        self.wall_times.append(float(solver.wall_time))
        # Load-independent only when the deterministic limit stopped it before the wall clock.
        self._last_reached_limit = (
            spent >= PER_SOLVE_DETERMINISTIC_LIMIT and returned < self._deadline
        )
        return name, solver

    def stop(self) -> tuple[str, str | None]:
        """Completeness and ``stopped_by`` of the last call, which stopped the search."""
        if self.statuses[-1] == "MODEL_INVALID":
            return "MODEL_INVALID", None
        if self._last_reached_limit:
            return "LIMIT_REACHED", "DETERMINISTIC_LIMIT"
        return "DEADLINE", "WALL_CLOCK"


def _dimensions(
    dimensions: Sequence[str], in_force: Mapping[str, TacticalRequirement]
) -> tuple[str, ...]:
    declared = tuple(dimensions)
    if len(declared) not in DIMENSION_COUNTS:
        raise ValueError("a frontier is declared on two or three requirements")
    if any(not isinstance(rid, str) or rid not in in_force for rid in declared):
        raise ValueError("every frontier dimension must be a requirement in force")
    if len(set(declared)) != len(declared):
        raise ValueError("a requirement is declared twice as a frontier dimension")
    return declared


def _floors(
    floors: Mapping[str, float] | None, in_force: Mapping[str, TacticalRequirement]
) -> dict[str, float]:
    declared = dict(floors or {})
    if set(declared) - set(in_force):
        raise ValueError("a floor must name a requirement in force")
    checked = {}
    for requirement_id in sorted(declared):
        _finite(declared[requirement_id], "a floor")
        checked[requirement_id] = float(declared[requirement_id])  # exact: |floor| <= 1e12
    return checked


def _objective(
    background: _Background, requirement: TacticalRequirement, scale: int
) -> dict[_Key, int]:
    """OBJECTIVE_POLICY coefficients of one dimension, as tradeoffs.py:299-312 computes them."""
    coefficients: dict[_Key, int] = {}
    for key in background.variables:
        pid, sid = key
        if not _applies(requirement, sid):
            continue
        value = background.vectors[pid][requirement.metric]
        coefficient = round(_scaled(value, requirement.normalizer, scale))
        if abs(coefficient) > MAX_MAGNITUDE:
            raise ValueError("normalized objective coefficient is too large")
        coefficients[key] = coefficient
    if sum(abs(c) for c in coefficients.values()) >= MAX_EXPRESSION_MAGNITUDE:
        raise ValueError("normalized objective expression is too large")
    return coefficients


def _pairwise_nondominated(vectors: Sequence[tuple[int, ...]]) -> bool:
    """No vector is weakly below another, which also rules out duplicates."""
    return not any(
        i != j and all(a <= b for a, b in zip(low, high, strict=True))
        for i, low in enumerate(vectors)
        for j, high in enumerate(vectors)
    )


def _leave_down_set(
    region: cp_model.CpModel,
    expressions: Sequence[cp_model.LinearExpr],
    vector: Sequence[int],
    index: int,
) -> None:
    """R_k+1 = R_k and OR_i (V_i >= v_i + 1): every later XI exceeds this point somewhere."""
    above = []
    for position, (expression, value) in enumerate(zip(expressions, vector, strict=True)):
        literal = region.new_bool_var(f"above_{index}_{position}")
        region.add(expression >= value + 1).only_enforce_if(literal)
        above.append(literal)
    region.add_bool_or(above)


def nondominated_sums(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    dimensions: Sequence[str],
    floors: Mapping[str, float] | None = None,
    locked: Collection[int] = (),
    excluded: Collection[int] = (),
    seed: int = 20260906,
    quantization: int = QUANTIZATION,
    max_points: int = MAX_FRONTIER_POINTS,
    deadline: float,
    provenance: Mapping | None = None,
) -> Frontier:
    """Every nondominated vector of the declared requirements' rounded sums, one XI each.

    ``dimensions`` has no default (O7): two or three distinct requirements in force, in the
    order the reader declared them. ``floors`` are hard and conservative; a requirement in
    force with ``hard=True`` is refused, because a flag this tool would ignore must not be
    accepted silently. Every ``ValueError`` is raised before any deadline or emptiness check.
    """
    requirements = tuple(requirements)
    in_force = {r.requirement_id: r for r in requirements if r.active}
    declared = _dimensions(dimensions, in_force)
    if type(max_points) is not int or not 1 <= max_points <= MAX_FRONTIER_POINTS:
        raise ValueError("the point limit must be an integer between 1 and 64")
    if any(r.hard for r in in_force.values()):
        raise ValueError(
            "a hard requirement is not accepted here: declare a hard minimum as a floor"
        )
    floor_values = _floors(floors, in_force)
    # Only the floored tables enter the model; _tables still checks every active minimum.
    floored = tuple(
        replace(r, minimum=floor_values[r.requirement_id])
        if r.requirement_id in floor_values
        else r
        for r in requirements
    )
    kernel = ShortfallKernel(candidates, floored, formation, quantization=quantization, seed=seed)
    deadline = kernel._deadline(deadline)
    shape = FORMATIONS[formation] if isinstance(formation, str) else formation
    dimension_rows = tuple(in_force[rid] for rid in declared)
    background = kernel._background(excluded, locked, None, (), None)
    # Tables and coefficients before any deadline or emptiness check: a ValueError never
    # depends on load or on the background (OR-XI-SPEC 2.3 step 1).
    hard = kernel._tables(background, conservative=True)
    coefficients = tuple(_objective(background, r, quantization) for r in dimension_rows)
    locked_ids = tuple(sorted(set(locked)))
    excluded_ids = tuple(sorted(set(excluded)))

    sources = source_fingerprints(*(str(Path(__file__).parent / name) for name in _SOURCES))
    # The kernel's contract plus the declarations (OR-XI-SPEC 10); never the deadline, never a
    # solve time. The dimension order is part of the answer and is kept.
    contract = {
        "version": FRONTIER_VERSION,
        "kernel": kernel.input_contract,
        "dimensions": list(declared),
        "floors": [[rid, value] for rid, value in floor_values.items()],
        "locked": list(locked_ids),
        "excluded": list(excluded_ids),
        "max_points": max_points,
        "objective_policy": OBJECTIVE_POLICY,
        "hard_policy": HARD_POLICY,
        "source_fingerprints": sources,
    }
    applicable = tuple(
        sum(1 for slot in shape.slots if _applies(r, slot.slot_id)) for r in dimension_rows
    )
    # e_r, rounded outward as tradeoffs.py:145-148 rounds it.
    allowances = tuple(
        math.nextafter(float(Fraction(count, 2 * quantization) * Fraction(r.normalizer)), math.inf)
        for count, r in zip(applicable, dimension_rows, strict=True)
    )
    calls = _Calls(deadline, seed)
    points: list[FrontierPoint] = []

    def vector_of(lineup: Lineup) -> tuple[int, ...]:
        # OBJECTIVE_POLICY recomputed from the lineup's values, without the coefficient tables.
        return tuple(
            sum(
                round(_scaled(background.vectors[pid][r.metric], r.normalizer, quantization))
                for sid, pid in lineup
                if _applies(r, sid)
            )
            for r in dimension_rows
        )

    def exact_sum(lineup: Lineup, requirement: TacticalRequirement) -> Fraction:
        return sum(
            (
                Fraction(background.vectors[pid][requirement.metric])
                for sid, pid in lineup
                if _applies(requirement, sid)
            ),
            Fraction(),
        )

    def verified(lineup: Lineup, vector: tuple[int, ...]) -> Lineup:
        if not kernel._admissible(background, lineup):
            raise RuntimeError("a frontier witness is not an XI of the declared model")
        for requirement_id in sorted(floor_values):
            table, target = hard[requirement_id]
            supply = sum(table.get((pid, sid), 0) for sid, pid in lineup)
            # Exact sums meet the raw floor by construction, without tolerance.
            raw = exact_sum(lineup, in_force[requirement_id])
            if supply < target or raw < Fraction(floor_values[requirement_id]):
                raise RuntimeError("a frontier witness failed its floor re-evaluation")
        if vector_of(lineup) != vector:
            raise RuntimeError("a frontier witness failed its integer re-evaluation")
        return lineup

    def point(vector: tuple[int, ...], lineup: Lineup, stages: tuple[str, ...]) -> FrontierPoint:
        return FrontierPoint(
            integer_sums=vector,
            quantized_sums=tuple(
                float(Fraction(value) * Fraction(r.normalizer) / quantization)
                for value, r in zip(vector, dimension_rows, strict=True)
            ),
            raw_sums=tuple(float(exact_sum(lineup, r)) for r in dimension_rows),
            lineup=lineup,
            stage_statuses=stages,
        )

    def finish(
        status: str,
        completeness: str,
        stopped_by: str | None,
        final: str,
        reasons: tuple[str, ...] = (),
    ) -> Frontier:
        vectors = [p.integer_sums for p in points]
        if not _pairwise_nondominated(vectors):
            raise RuntimeError("frontier points are not pairwise nondominated")
        record = {
            **scrub_lineage(provenance),
            "frontier_version": FRONTIER_VERSION,
            "kernel_version": KERNEL_VERSION,
            "objective_policy": OBJECTIVE_POLICY,
            "hard_policy": HARD_POLICY,
            "quantization": quantization,
            "per_solve_deterministic_limit": PER_SOLVE_DETERMINISTIC_LIMIT,
            "input_contract": contract,
            "input_fingerprint": fingerprint({"version": FRONTIER_VERSION, "contract": contract}),
            "source_fingerprints": sources,
            # Reproducible; the wall times below depend on load and are diagnostic only.
            "frontier_solve_deterministic_times": list(calls.deterministic_times),
            "frontier_solve_wall_times": list(calls.wall_times),
        }
        return Frontier(
            formation=shape.formation_id,
            dimensions=declared,
            status=status,
            points=tuple(points),
            point_order=POINT_ORDER,
            floors=tuple(floor_values.items()),
            locked=locked_ids,
            excluded=excluded_ids,
            certificate=FrontierCertificate(
                points=len(points),
                pairwise_nondominated=True,
                witnesses_verified=True,
                final_region_status=final,
                solves=len(calls.deterministic_times),
                statuses=tuple(calls.statuses),
                completeness=completeness,
                stopped_by=stopped_by,
                quantization=quantization,
                objective_policy=OBJECTIVE_POLICY,
                hard_policy=HARD_POLICY,
                per_solve_deterministic_limit=PER_SOLVE_DETERMINISTIC_LIMIT,
                raw_rounding_error_bounds=allowances,
                max_points=max_points,
            ),
            claim=FRONTIER_CLAIM,
            non_claim=FRONTIER_NON_CLAIM,
            reasons=reasons,
            provenance=record,
        )

    def stopped(final: str) -> Frontier:
        completeness, stopped_by = calls.stop()
        status = "MODEL_INVALID" if completeness == "MODEL_INVALID" else "INCOMPLETE"
        return finish(status, completeness, stopped_by, final)

    def empty() -> Frontier:
        """R_0 is proved empty: no point exists. Which of the two causes holds (4.2)."""
        proved = background.reasons or (UNFIELDABLE_PROVED,)
        if not floor_values:  # R_0 is the background itself
            return finish("UNFIELDABLE", "COMPLETE", None, "INFEASIBLE", proved)
        name, solver = calls.solve(background.model)
        if name == "INFEASIBLE":
            return finish("UNFIELDABLE", "COMPLETE", None, "INFEASIBLE", proved)
        if name in _WITNESS:
            if not kernel._admissible(background, kernel._witness(background, solver)):
                raise RuntimeError("the floor-free witness is not an XI of the declared model")
            return finish("NOT_SATISFIABLE", "COMPLETE", None, "INFEASIBLE")
        # The empty frontier is proved; whether an XI exists without the floors is not.
        completeness, stopped_by = calls.stop()
        status = "MODEL_INVALID" if completeness == "MODEL_INVALID" else "FLOORS_UNMET"
        return finish(status, completeness, stopped_by, "INFEASIBLE")

    # A passed deadline answers nothing, even where a reason is a proof by construction.
    if time.monotonic() >= deadline:
        calls.statuses.append("NOT_RUN")
        return finish("INCOMPLETE", "DEADLINE", "WALL_CLOCK", "NOT_RUN")
    if background.model is None:
        return finish(
            "UNFIELDABLE", "COMPLETE", None, "INFEASIBLE_BY_CONSTRUCTION", background.reasons
        )

    region = background.model.clone()
    for requirement_id in sorted(floor_values):
        table, target = hard[requirement_id]
        _at_least(region, kernel._expression(background, table), target)
    expressions = tuple(kernel._expression(background, c) for c in coefficients)

    while True:
        if len(points) == max_points:
            # The limit check: a feasibility solve of R_k, no objective. An XI of R_k proves a
            # further point; INFEASIBLE proves the list complete.
            name, _ = calls.solve(region)
            if name in _WITNESS:
                return finish("INCOMPLETE", "LIMIT_REACHED", "POINT_LIMIT", name)
            if name == "INFEASIBLE":
                return finish("FRONTIER", "COMPLETE", None, "INFEASIBLE")
            return stopped(name)
        work = region.clone()
        vector: list[int] = []
        stages: list[str] = []
        solver = None
        for stage, expression in enumerate(expressions):
            work.maximize(expression)
            name, solver = calls.solve(work)
            if name == "INFEASIBLE" and stage == 0:
                if not points:
                    return empty()
                return finish("FRONTIER", "COMPLETE", None, "INFEASIBLE")
            if name == "INFEASIBLE":
                raise RuntimeError("the frontier search lost a feasible lexicographic level")
            if name != "OPTIMAL":  # a FEASIBLE incumbent is not a maximum
                return stopped(name)
            vector.append(solver.value(expression))
            stages.append(name)
            work.add(expression == vector[-1])
        found = tuple(vector)
        lineup = verified(kernel._witness(background, solver), found)
        points.append(point(found, lineup, tuple(stages)))
        _leave_down_set(region, expressions, found, len(points))
