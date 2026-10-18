"""The least and the largest sum of each requirement in force over the declared XIs, bracketed.

Claim: for each requirement in force, two intervals over the XIs that the eligibility rules,
missing measurements, locks, exclusions and declared hard floors allow (each floor compared
conservatively): the largest sum any of these XIs reaches lies in the first, the least in the
second. One end of each interval is the exact sum of one XI the search found; the other, where
the search settled it, is a bound the solver proved and no such XI passes. Non-claim: the XI
found need not reach the extreme sum itself, each range is taken for one requirement alone
(two minima reachable one at a time say nothing about reaching both), with floors every bound
speaks of the conservative inner set only, and a sum is arithmetic on prior per-90 rates, not a
forecast. UNKNOWN, NOT_RUN and a FEASIBLE incumbent are never a bound or an absence.

Arithmetic (OR-XI-SPEC 1.2; no third policy). The searched sum is ``OBJECTIVE_POLICY``, the
shipped maximiser's objective: ``O_r(x)`` adds each rate rounded half-even on its exact fraction
to ``1 / q`` of the normaliser. Every XI then has ``|S_r(x) - (n_r / q) O_r(x)| <= e_r`` with
``e_r = a_r n_r / (2q)``, so the solver's integer optimum ``I`` widened by ``e_r`` bounds every
exact sum ``S_r``. A declared floor is ``HARD_POLICY`` (floor each rate, ceil the floor): an XI
that meets it in integers meets the raw floor exactly, and one that meets the raw floor with
less than ``(a_r + 1) n_r / q`` to spare can be left out of every range.

How the ends are reached. The kernel's background with the floors added, then for each
requirement in id order one solve maximising ``O_r`` and one minimising it, with nothing else
in the objective. The first INFEASIBLE solve proves the inner set empty and ends the tool;
with floors one more solve of the background says whether the floors are the cause. Every
witness is re-evaluated without the solver, and its integer is read with ``solver.value``,
never from ``objective_value``.
"""

from __future__ import annotations

import math
import time
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path

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
from .domain import FORMATIONS, Candidate, Formation, TacticalRequirement
from .solver import QUANTIZATION, _applies
from .tradeoffs import (
    MAX_EXPRESSION_MAGNITUDE,
    MAX_MAGNITUDE,
    OBJECTIVE_POLICY,
    _finite,
    _scaled,
)

__all__ = [
    "CEILING_CLAIM",
    "CEILING_EMPTY",
    "CEILING_NON_CLAIM",
    "CEILING_NOT_DECIDED",
    "CEILING_PARTIAL_CLAIM",
    "CEILING_REFUSED",
    "CEILING_VERSION",
    "DIRECTIONS",
    "FLOORS_CONSERVATIVE",
    "FLOOR_REQUIREMENT_ERROR",
    "HARD_REQUIREMENT_ERROR",
    "NO_REQUIREMENT_ERROR",
    "UNFIELDABLE_PROVED",
    "CeilingCertificate",
    "CeilingResult",
    "RequirementRange",
    "SumEnd",
    "requirement_ranges",
]

CEILING_VERSION = "requirement-sum-range-v1"
DIRECTIONS = ("LARGEST", "LEAST")

# The served claims (OR-XI-SPEC 7.7). The reply's state selects one (2.2, "Claim by state").
CEILING_CLAIM = (
    "For each requirement in force, two intervals over the XIs that the eligibility rules, "
    "missing measurements, locks, exclusions and declared hard floors allow, each floor "
    "compared conservatively: the largest sum any of these XIs reaches lies in the first, the "
    "least in the second. One end of each interval is the exact sum of one XI the search found, "
    "printed rounded outward to four decimals; that XI need not reach the largest or the least "
    "sum itself. The other end is a bound no such XI passes: the search adds each prior per-90 "
    "rate rounded half-even to 1/100000 of the club median, and the bound is the limit the "
    "search proved on that rounded sum, widened by its rounding allowance and printed rounded "
    "outward."
)
CEILING_PARTIAL_CLAIM = (
    "For each requirement in force, the largest and the least sum over the XIs that the "
    "eligibility rules, missing measurements, locks, exclusions and declared hard floors "
    "allow, each floor compared conservatively, are bracketed only on the sides the search "
    "settled. Where a cell shows a sum, it is the exact sum of one XI the search found, printed "
    "rounded outward to four decimals; that XI need not reach the largest or the least sum "
    "itself. Where a cell shows a bound, no such XI passes it: the search adds each prior "
    "per-90 rate rounded half-even to 1/100000 of the club median, and the bound is the limit "
    "the search proved on that rounded sum, widened by its rounding allowance and printed "
    "rounded outward. A cell marked not certified implies nothing."
)
CEILING_NOT_DECIDED = (
    "Whether any XI that the eligibility rules, missing measurements, locks, exclusions and "
    "declared hard floors allow exists was not decided within the search limits. No range is "
    "implied."
)
CEILING_EMPTY = (
    "No XI that the eligibility rules, missing measurements, locks, exclusions and declared "
    "hard floors allow exists, each floor compared conservatively, so there is no range to "
    "report."
)
CEILING_REFUSED = (
    "The solver refused the model, so no range is reported. No value is implied."
)
CEILING_NON_CLAIM = (
    "Each range is taken for one requirement alone, over the XIs the eligibility rules, missing "
    "measurements, locks, exclusions and declared hard floors allow, each floor compared "
    "conservatively: reaching two minima at once is a different question. A sum is arithmetic "
    "on prior rates, not a forecast of what an XI would produce."
)
# Defined once here; frontier.py and risk.py re-export them (7.7).
UNFIELDABLE_PROVED = (
    "No XI satisfies the combined eligibility rules, missing measurements, locks and "
    "exclusions."
)
FLOORS_CONSERVATIVE = (
    "No XI meets the declared floors in the conservative comparison: each rate rounded down "
    "and each floor rounded up to 1/100000 of the club median, so an XI that meets a floor with "
    "less than that unit times one more than the number of places counted to spare can be "
    "excluded."
)
# Refusals. Each names no value; conflict.explain_floors raises the hard one too (3.1).
NO_REQUIREMENT_ERROR = "At least one requirement must be in force: with none there is no sum."
HARD_REQUIREMENT_ERROR = (
    "A requirement in force is marked hard; a hard minimum is declared here as a floor."
)
FLOOR_REQUIREMENT_ERROR = "A floor names a requirement that is not in force."

_SOURCES = ("ceilings.py", "../squad/kernel.py", "solver.py", "tradeoffs.py", "domain.py")
_WITNESS = ("OPTIMAL", "FEASIBLE")


@dataclass(frozen=True)
class SumEnd:
    """One end of one requirement's range: the solve that settles it, its witness, its bound."""

    direction: str  # LARGEST | LEAST
    solver_status: str  # status of the one solve of this end, or NOT_RUN
    certification: str  # QUANTIZED_OPTIMAL | FEASIBLE_NOT_PROVEN | NO_SOLUTION
    # O_r of the witness recomputed in Python, OBJECTIVE_POLICY units of n_r / q
    integer_value: int | None
    # I± when QUANTIZED_OPTIMAL; the solver's bound when FEASIBLE_NOT_PROVEN, None when that
    # bound is not finite
    integer_bound: int | None
    attained: float | None  # S_r(witness), the float nearest the exact sum (never printed)
    # (n_r / q) * integer_bound ± e_r, rounded outward with math.nextafter; None with the bound
    raw_bound: float | None
    lineup: Lineup  # the witness, (slot_id, player_id) in formation order; () when none


@dataclass(frozen=True)
class RequirementRange:
    """Both ends of one requirement in force, and the two facts about its declared minimum.

    No evidence field: the router composes the class per range. ``minimum`` is the main
    solve's minimum from the requirements as passed, never a floor, and is only compared.
    """

    requirement_id: str
    label: str
    metric: str
    applicable_slots: int  # a_r
    normalizer: float
    minimum: float  # m_r from the unmodified requirements, compared only
    raw_rounding_error_bound: float  # e_r, math.nextafter outward
    largest: SumEnd
    least: SumEnd
    minimum_reached_by_some_xi: bool | None
    minimum_reached_witness: str | None  # LARGEST | LEAST: the end whose witness decided True
    minimum_reached_reason: str | None  # None | ALLOWANCE | NOT_CERTIFIED, read off LARGEST
    minimum_missed_by_some_xi: bool | None
    minimum_missed_witness: str | None
    minimum_missed_reason: str | None  # as above, read off LEAST


@dataclass(frozen=True)
class CeilingCertificate:
    # FIELDABLE | UNFIELDABLE | NOT_SATISFIABLE | FLOORS_UNMET | UNKNOWN | MODEL_INVALID
    feasible_set: str
    solves: int  # CP-SAT calls actually made
    # one entry per end or cause solve reached, in call order: its status, or NOT_RUN; ends
    # after a proof that ends the tool have none; () for UNFIELDABLE by construction
    statuses: tuple[str, ...]
    completeness: str  # EXACT | LIMIT_REACHED | DEADLINE | MODEL_INVALID
    stopped_by: str | None  # DETERMINISTIC_LIMIT | WALL_CLOCK; None when nothing is undecided
    quantization: int
    objective_policy: str
    hard_policy: str
    per_solve_deterministic_limit: float
    witnesses_verified: bool  # every witness re-evaluated without the solver


@dataclass(frozen=True)
class CeilingResult:
    formation: str
    # requirement_id ascending; () for UNFIELDABLE by construction and whenever a proof or a
    # refusal ended the tool
    ranges: tuple[RequirementRange, ...]
    floors: tuple[tuple[str, float], ...]  # (requirement_id, φ_r) ascending; () when none
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    certificate: CeilingCertificate
    claim: str  # the constant the state selects, word for word
    non_claim: str  # CEILING_NON_CLAIM, word for word
    # served: the kernel's reasons by construction, or UNFIELDABLE_PROVED on a proved-empty
    # model whose kernel recorded none
    reasons: tuple[str, ...]
    provenance: dict


class _Calls:
    """The CP-SAT calls of one tool call, in order, each with how it ended (OR-XI-SPEC 1.5).

    ``stops[i]`` is ``None`` for a decided call, ``MODEL_INVALID`` for a refused one, and
    ``LIMIT_REACHED`` or ``DEADLINE`` for an undecided one: ``LIMIT_REACHED`` only when its
    deterministic time reached the limit while the wall clock still had time left, so that
    stop does not depend on load. A call the deadline skipped is ``NOT_RUN`` and ``DEADLINE``.
    """

    def __init__(self, deadline: float, seed: int) -> None:
        self._run = _Run(deadline, seed)
        self._deadline = deadline
        self.statuses: list[str] = []
        self.stops: list[str | None] = []
        self.deterministic_times: list[dict] = []
        self.wall_times: list[float] = []

    @property
    def solves(self) -> int:
        return len(self._run.statuses)

    def skip(self) -> None:
        self.statuses.append("NOT_RUN")
        self.stops.append("DEADLINE")

    def solve(
        self, model: cp_model.CpModel, *, optimum: bool
    ) -> tuple[str, cp_model.CpSolver | None]:
        """One call through ``kernel._Run``; ``optimum`` makes a FEASIBLE incumbent undecided."""
        name, solver = self._run.solve(model)
        if solver is None:  # the deadline passed before the call (kernel.py:197-200)
            self.skip()
            return "NOT_RUN", None
        within = time.monotonic() < self._deadline
        spent = float(solver.deterministic_time)
        self.deterministic_times.append({"status": name, "deterministic_time": spent})
        self.wall_times.append(float(solver.wall_time))
        self.statuses.append(name)
        if name == "MODEL_INVALID":
            self.stops.append("MODEL_INVALID")
        elif name == "UNKNOWN" or (optimum and name == "FEASIBLE"):
            limited = spent >= PER_SOLVE_DETERMINISTIC_LIMIT and within
            self.stops.append("LIMIT_REACHED" if limited else "DEADLINE")
        else:
            self.stops.append(None)
        return name, solver

    def tokens(self, start: int = 0) -> tuple[str, str | None]:
        """(completeness, stopped_by) over the calls from ``start``, those no proof superseded."""
        stops = self.stops[start:]
        if "MODEL_INVALID" in stops:
            completeness = "MODEL_INVALID"
        elif "DEADLINE" in stops:
            completeness = "DEADLINE"
        elif "LIMIT_REACHED" in stops:
            completeness = "LIMIT_REACHED"
        else:
            completeness = "EXACT"
        # A load-dependent stop wins, so a reply is never called load-independent wrongly.
        stopped_by = (
            "WALL_CLOCK"
            if "DEADLINE" in stops
            else "DETERMINISTIC_LIMIT"
            if "LIMIT_REACHED" in stops
            else None
        )
        return completeness, stopped_by


def _validated_floors(
    active: Sequence[TacticalRequirement], floors: Mapping[str, float] | None
) -> dict[str, float]:
    """The declared floors by requirement id, ascending; refused without naming a value."""
    if floors is None:
        return {}
    if not isinstance(floors, Mapping):
        raise ValueError("floors must map requirement ids to numbers")
    known = {r.requirement_id for r in active}
    if set(floors) - known:
        raise ValueError(FLOOR_REQUIREMENT_ERROR)
    for value in floors.values():
        _finite(value, "a floor")
    return {rid: floors[rid] for rid in sorted(floors)}


def _refuse_hard(active: Sequence[TacticalRequirement]) -> None:
    # As kernel.value refuses one (kernel.py:670-674): a flag that would be ignored is refused.
    if any(r.hard for r in active):
        raise ValueError(HARD_REQUIREMENT_ERROR)


def _exact_sum(lineup, requirement: TacticalRequirement, vectors) -> Fraction:
    return sum(
        (Fraction(vectors[pid][requirement.metric]) for sid, pid in lineup
         if pid is not None and _applies(requirement, sid)),
        Fraction(),
    )


def _objective_coefficients(
    background, requirement: TacticalRequirement, quantization: int
) -> dict[tuple[int, str], int]:
    """OBJECTIVE_POLICY coefficients over the background's keys, as tradeoffs.py:299-312."""
    per_player: dict[int, int] = {}
    coefficients = {}
    for key in background.variables:
        pid, sid = key
        if not _applies(requirement, sid):
            continue
        if pid not in per_player:
            value = background.vectors[pid][requirement.metric]
            per_player[pid] = round(_scaled(value, requirement.normalizer, quantization))
            if abs(per_player[pid]) > MAX_MAGNITUDE:
                raise ValueError("normalized requirement coefficient is too large")
        coefficients[key] = per_player[pid]
    if sum(abs(c) for c in coefficients.values()) >= MAX_EXPRESSION_MAGNITUDE:
        raise ValueError("normalized objective expression is too large")
    return coefficients


def _raw(integer: int, applicable: int, normalizer: float, quantization: int, sign: int):
    """``(n / q) * integer + sign * e``, exact."""
    return Fraction(normalizer) * (2 * integer + sign * applicable) / (2 * quantization)


def _no_solution(direction: str, status: str) -> SumEnd:
    return SumEnd(direction, status, "NO_SOLUTION", None, None, None, None, ())


def _facts(
    requirement: TacticalRequirement,
    applicable: int,
    quantization: int,
    ends: Mapping[str, SumEnd],
    sums: Mapping[str, Fraction],
) -> tuple:
    """The two facts of OR-XI-SPEC 2.1 about ``m_r``, each with its witness or its reason.

    True is read off a returned witness (both ends' witnesses can decide either fact), False
    off a proved bound, and ``None`` only when neither decides it. The reason names the end
    whose bound would have decided False: ALLOWANCE only when that end is QUANTIZED_OPTIMAL,
    where the minimum lies inside its rounding band; NOT_CERTIFIED otherwise.
    """
    minimum = Fraction(requirement.minimum)
    normalizer = requirement.normalizer

    def fact(order, end, holds, refutes):
        for name in order:
            if name in sums and holds(sums[name]):
                return True, name, None
        if end.integer_bound is not None and refutes(end.integer_bound):
            return False, None, None
        reason = "ALLOWANCE" if end.certification == "QUANTIZED_OPTIMAL" else "NOT_CERTIFIED"
        return None, None, reason

    reached = fact(
        ("LARGEST", "LEAST"),
        ends["LARGEST"],
        lambda s: s >= minimum,
        lambda bound: _raw(bound, applicable, normalizer, quantization, 1) < minimum,
    )
    missed = fact(
        ("LEAST", "LARGEST"),
        ends["LEAST"],
        lambda s: s < minimum,
        lambda bound: _raw(bound, applicable, normalizer, quantization, -1) >= minimum,
    )
    return (*reached, *missed)


def requirement_ranges(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    floors: Mapping[str, float] | None = None,
    locked: Collection[int] = (),
    excluded: Collection[int] = (),
    seed: int = 20260906,
    quantization: int = QUANTIZATION,
    deadline: float,
    provenance: Mapping | None = None,
) -> CeilingResult:
    """Both ends of every requirement in force over the XIs the declarations allow.

    ``floors`` are hard floors in the conservative comparison, keyed by requirement id; every
    other minimum is only compared with the ends. ``deadline`` is a ``time.monotonic()``
    value. Every input check runs before the deadline is read or a solve is made, so a
    refusal depends neither on load nor on the background.
    """
    deadline = ShortfallKernel._deadline(deadline)
    requirements = tuple(requirements)
    active = sorted((r for r in requirements if r.active), key=lambda r: r.requirement_id)
    declared = _validated_floors(active, floors)
    if not active:
        raise ValueError(NO_REQUIREMENT_ERROR)
    _refuse_hard(active)
    # The model holds φ_r as the minimum of a floored requirement; the facts keep m_r.
    floored = tuple(
        replace(r, minimum=declared[r.requirement_id])
        if r.active and r.requirement_id in declared
        else r
        for r in requirements
    )
    kernel = ShortfallKernel(candidates, floored, formation, quantization=quantization, seed=seed)
    background = kernel._background(excluded, locked, None, (), None)
    locked_ids = tuple(sorted(set(locked)))
    excluded_ids = tuple(sorted(set(excluded)))
    # Step 1: both tables and their checks, whatever the clock and the background say.
    tables = kernel._tables(background, conservative=True)
    objectives = {
        r.requirement_id: _objective_coefficients(background, r, quantization) for r in active
    }
    shape = FORMATIONS[formation] if isinstance(formation, str) else formation
    applicable = {
        r.requirement_id: sum(_applies(r, slot.slot_id) for slot in shape.slots) for r in active
    }

    sources = source_fingerprints(*(str(Path(__file__).parent / name) for name in _SOURCES))
    contract = {
        "version": CEILING_VERSION,
        "kernel": kernel.input_contract,
        "floors": [[rid, value] for rid, value in declared.items()],
        "minima": {r.requirement_id: r.minimum for r in active},
        "locked": list(locked_ids),
        "excluded": list(excluded_ids),
        "objective_policy": OBJECTIVE_POLICY,
        "hard_policy": HARD_POLICY,
        "source_fingerprints": sources,
    }
    calls = _Calls(deadline, seed)

    def finish(feasible_set, ranges, tokens, reasons=()):
        completeness, stopped_by = tokens
        if feasible_set == "FIELDABLE":
            proved = all(
                end.integer_bound is not None
                for item in ranges
                for end in (item.largest, item.least)
            )
            claim = CEILING_CLAIM if proved else CEILING_PARTIAL_CLAIM
        elif feasible_set == "UNKNOWN":
            claim = CEILING_NOT_DECIDED
        elif feasible_set == "MODEL_INVALID":
            claim = CEILING_REFUSED
        else:
            claim = CEILING_EMPTY
        record = {
            **scrub_lineage(provenance),
            "ceiling_version": CEILING_VERSION,
            "kernel_version": KERNEL_VERSION,
            "objective_policy": OBJECTIVE_POLICY,
            "hard_policy": HARD_POLICY,
            "quantization": quantization,
            "per_solve_deterministic_limit": PER_SOLVE_DETERMINISTIC_LIMIT,
            "input_contract": contract,
            "input_fingerprint": fingerprint({"version": CEILING_VERSION, "contract": contract}),
            "source_fingerprints": sources,
            # Times are not encodings and enter no hash (1.5); wall times are diagnostic only.
            "ceiling_solve_deterministic_times": list(calls.deterministic_times),
            "ceiling_solve_wall_times": list(calls.wall_times),
        }
        return CeilingResult(
            formation=shape.formation_id,
            ranges=tuple(ranges),
            floors=tuple(declared.items()),
            locked=locked_ids,
            excluded=excluded_ids,
            certificate=CeilingCertificate(
                feasible_set=feasible_set,
                solves=calls.solves,
                statuses=tuple(calls.statuses),
                completeness=completeness,
                stopped_by=stopped_by,
                quantization=quantization,
                objective_policy=OBJECTIVE_POLICY,
                hard_policy=HARD_POLICY,
                per_solve_deterministic_limit=PER_SOLVE_DETERMINISTIC_LIMIT,
                witnesses_verified=True,
            ),
            claim=claim,
            non_claim=CEILING_NON_CLAIM,
            reasons=tuple(reasons),
            provenance=record,
        )

    def ranged(ends, sums):
        rows = []
        for r in active:
            rid = r.requirement_id
            pair = ends.get(rid, {})
            pair = {d: pair.get(d) or _no_solution(d, "NOT_RUN") for d in DIRECTIONS}
            # e_r as tradeoffs.py:145-148 computes it, rounded outward once.
            raw_error = float(
                Fraction(applicable[rid], 2 * quantization) * Fraction(r.normalizer)
            )
            facts = _facts(r, applicable[rid], quantization, pair, sums.get(rid, {}))
            rows.append(
                RequirementRange(
                    rid,
                    r.label,
                    r.metric,
                    applicable[rid],
                    r.normalizer,
                    r.minimum,
                    math.nextafter(raw_error, math.inf),
                    pair["LARGEST"],
                    pair["LEAST"],
                    *facts,
                )
            )
        return rows

    # Step 2. A passed deadline answers nothing, even where a reason is a proof by construction.
    if time.monotonic() >= deadline:
        for _ in range(2 * len(active)):
            calls.skip()
        return finish("UNKNOWN", ranged({}, {}), calls.tokens())
    if background.model is None:
        return finish("UNFIELDABLE", (), ("EXACT", None), background.reasons)

    # Step 3: the floors, in ascending id so that a reordered mapping builds the same model.
    region = background.model.clone()
    for rid in declared:
        coefficients, target = tables[rid]
        _at_least(region, kernel._expression(background, coefficients), target)

    by_id = {r.requirement_id: r for r in active}

    def verified(solver, r, expression) -> tuple[Lineup, int, Fraction]:
        lineup = kernel._witness(background, solver)
        if not kernel._admissible(background, lineup):
            raise RuntimeError("a range witness is not an XI of the declared model")
        for rid, floor in declared.items():
            coefficients, target = tables[rid]
            held = sum(coefficients.get((pid, sid), 0) for sid, pid in lineup)
            exact = _exact_sum(lineup, by_id[rid], background.vectors)
            # Exact sums meet the raw floor by construction, without tolerance.
            if held < target or exact < Fraction(floor):
                raise RuntimeError("a range witness failed its floor re-evaluation")
        value = sum(
            round(_scaled(background.vectors[pid][r.metric], r.normalizer, quantization))
            for sid, pid in lineup
            if _applies(r, sid)
        )
        # An exact int of the expression the solve optimised; objective_value is never read.
        if value != solver.value(expression):
            raise RuntimeError("a range witness failed its integer re-evaluation")
        return lineup, value, _exact_sum(lineup, r, background.vectors)

    ends: dict[str, dict[str, SumEnd]] = {}
    sums: dict[str, dict[str, Fraction]] = {}
    witnessed = False
    for r in active:
        rid = r.requirement_id
        expression = cp_model.LinearExpr.weighted_sum(
            [background.variables[key] for key in objectives[rid]], list(objectives[rid].values())
        )
        for direction in DIRECTIONS:
            work = region.clone()
            if direction == "LARGEST":
                work.maximize(expression)
            else:
                work.minimize(expression)
            name, solver = calls.solve(work, optimum=True)
            if name == "INFEASIBLE":
                if witnessed:
                    raise RuntimeError("an INFEASIBLE range solve contradicts a verified witness")
                return _empty(calls, background, declared, finish)
            if name == "MODEL_INVALID":
                return finish("MODEL_INVALID", (), calls.tokens())
            if name not in _WITNESS:
                ends.setdefault(rid, {})[direction] = _no_solution(direction, name)
                continue
            witnessed = True
            lineup, value, exact = verified(solver, r, expression)
            if name == "OPTIMAL":
                certification, bound = "QUANTIZED_OPTIMAL", value
            else:
                certification, proved = "FEASIBLE_NOT_PROVEN", solver.best_objective_bound
                if not math.isfinite(proved):
                    bound = None
                elif direction == "LARGEST":  # the shipped formula, tradeoffs.py:421
                    bound = max(value, math.ceil(proved))
                else:
                    bound = min(value, math.floor(proved))
            raw_bound = None
            if bound is not None:
                sign = 1 if direction == "LARGEST" else -1
                outward = math.inf if direction == "LARGEST" else -math.inf
                exact_bound = _raw(bound, applicable[rid], r.normalizer, quantization, sign)
                raw_bound = math.nextafter(float(exact_bound), outward)
            ends.setdefault(rid, {})[direction] = SumEnd(
                direction, name, certification, value, bound, float(exact), raw_bound, lineup
            )
            sums.setdefault(rid, {})[direction] = exact
    return finish("FIELDABLE" if witnessed else "UNKNOWN", ranged(ends, sums), calls.tokens())


def _empty(calls: _Calls, background, declared: Mapping[str, float], finish) -> CeilingResult:
    """Step 6: the inner set is proved empty; with floors, one solve decides the cause.

    The proof supersedes every call before it that was undecided (1.5), so only the calls
    after it count towards completeness: none, or the cause solve.
    """
    proved = ("EXACT", None)
    reasons = background.reasons or (UNFIELDABLE_PROVED,)
    if not declared:
        return finish("UNFIELDABLE", (), proved, reasons)
    start = len(calls.stops)
    name, solver = calls.solve(background.model, optimum=False)
    if name == "INFEASIBLE":
        return finish("UNFIELDABLE", (), proved, reasons)
    if name in _WITNESS:
        lineup = ShortfallKernel._witness(background, solver)
        if not ShortfallKernel._admissible(background, lineup):
            raise RuntimeError("the cause solve returned an assignment that is not an XI")
        return finish("NOT_SATISFIABLE", (), proved)
    if name == "MODEL_INVALID":
        return finish("MODEL_INVALID", (), calls.tokens(start))
    # No XI meets the floors (proved); whether one exists without them is not decided.
    return finish("FLOORS_UNMET", (), calls.tokens(start))
