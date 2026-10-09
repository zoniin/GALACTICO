"""The role brief: what an addition at one slot must supply. Arithmetic on declared minima.

Claim: for a chosen slot, the complete set of minimal requirement-value rows such that a player
added at that slot makes every declared minimum reachable if, and only if, his rates meet at
least one row on every listed requirement. When a candidate universe is given, the number of its
players admissible at the slot who do, each decided by its own exact solve with him placed
there. The result always says whether the squad reaches the minima with no addition at all.

Non-claim: a row is arithmetic on the declared minima and this squad's prior rates. It does not
say a player meeting it would reproduce those rates here, it names no role and it orders no
player. "Not reachable" refers to the conservative integer model. UNKNOWN, a deadline or a row
limit is never evidence that no further row exists.

How the rows are reached. The residual problem is the kernel's own background with the slot
vacant: the other slots, the squad, the declared exclusions and locks. Every number is in the
hard-constraint arithmetic of the solve the brief explains (floor each coefficient, ceil each
target; ``kernel.HARD_POLICY``), never the half-even shortfall integers:

    supply_r(x) = sum of floor coefficients of x over the slots where r applies
    need_r(x)   = max(0, ceil_target_r - supply_r(x))     r applies to the slot (a dimension)
    admissible:   supply_r(x) >= ceil_target_r             r does not apply to the slot

The rows are the Pareto-minimal ``need(x)`` over admissible residual lineups. They are found by
repeated lexicographic minimisation over "not weakly above any row found so far"; each such
minimum is minimal among all need vectors, so rows stay certified when the search stops early,
and an infeasible region proves there is no further row. No summed objective exists anywhere:
the dimension order is an enumeration device, not a preference.

"Meets" is defined by the solve, not by the rows: a candidate meets the brief at the slot if and
only if ``ShortfallKernel(squad + candidate).satisfiable(pinned={candidate: slot})`` is
SATISFIABLE. For a complete brief and non-negative rates the row test (``meets_row``) is
equivalent; the count reports whether the two agreed and is always taken from the solves.
"""

from __future__ import annotations

import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from ..xi.domain import FORMATIONS, Candidate, Formation, Slot, TacticalRequirement
from ..xi.solver import QUANTIZATION, _applies, _eligible
from .kernel import (
    HARD_POLICY,
    KERNEL_VERSION,
    PER_SOLVE_DETERMINISTIC_LIMIT,
    ShortfallKernel,
    _at_least,
    _Run,
    compose_evidence,
    fingerprint,
    scrub_lineage,
    source_fingerprints,
)

__all__ = [
    "BRIEF_VERSION",
    "INCOMPLETE_WARNING",
    "MAX_BRIEF_ROWS",
    "BriefCertificate",
    "BriefCount",
    "BriefRow",
    "RoleBrief",
    "meets_row",
    "role_brief",
]

BRIEF_VERSION = "residual-minimal-need-brief-v1"
MAX_BRIEF_ROWS = 64
INCOMPLETE_WARNING = (
    "The brief is incomplete: {n} minimal rows were found before the limit. "
    "A player who meets none of them may still meet a row that was not found."
)

_SOURCES = ("brief.py", "kernel.py", "../xi/domain.py", "../xi/tradeoffs.py")
_WITNESS = ("OPTIMAL", "FEASIBLE")
_NON_CLAIM = (
    "A row is arithmetic on your minima and this squad's prior rates. It does not say a player "
    "meeting it would reproduce those rates here, and it names no role."
)
_WITHOUT_ADDITION = {
    "SATISFIABLE": "already reachable",
    "NOT_SATISFIABLE": "not reachable",
    "UNFIELDABLE": "not reachable (no XI can be fielded)",
    "UNKNOWN": "undetermined (the solve did not finish)",
    "MODEL_INVALID": "undetermined (the solver rejected the model)",
}

Lineup = tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class BriefRow:
    """One minimal need vector, aligned with ``RoleBrief.dimensions``."""

    need_integer: tuple[int, ...]  # conservative integer units of 1 / quantization
    need: tuple[float, ...]  # original units; the least float not below the exact threshold
    residual_supply: tuple[float, ...]  # exact raw sums of the witness over the other slots
    residual_lineup: Lineup  # one witness for the other slots; not the only one
    certification: str  # MINIMAL_CERTIFIED


@dataclass(frozen=True)
class BriefCount:
    """How many universe players admissible at the slot meet the brief, by exact solves."""

    admissible: int  # universe players the slot's eligibility rule admits
    meeting: int | None  # None unless every candidate was resolved
    not_meeting: int
    undetermined: int
    meeting_ids: tuple[int, ...]  # ordered by player_id; a set, not an order of merit
    method: str  # INJECTED_SATISFY_SOLVE
    row_test_agrees: bool | None  # None if the brief is incomplete or a candidate is unresolved


@dataclass(frozen=True)
class BriefCertificate:
    rows: int
    pairwise_incomparable: bool  # checked without a solver
    witnesses_verified: bool  # exact integer and Fraction re-evaluation of every row
    # INFEASIBLE: solver proof that no further row exists. INFEASIBLE_BY_CONSTRUCTION: no
    # solve was needed (a zero row bounds every need vector; no dimension; a kernel reason).
    # OPTIMAL: a further row exists (row limit). NOT_RUN, UNKNOWN, FEASIBLE: no proof.
    final_region_status: str
    solves: int  # CP-SAT calls of the enumeration
    completeness: str  # COMPLETE | LIMIT_REACHED | DEADLINE
    quantization: int
    hard_policy: str


@dataclass(frozen=True)
class RoleBrief:
    formation: str
    slot_id: str
    slot_label: str
    dimensions: tuple[str, ...]  # active requirement ids applying to the slot, sorted
    fixed_floor_requirements: tuple[str, ...]  # active requirements that do not apply to it
    # NO_NEED | BRIEF | NOT_ADDRESSABLE_AT_SLOT | RESIDUAL_UNFIELDABLE | INCOMPLETE | MODEL_INVALID
    status: str
    rows: tuple[BriefRow, ...]  # sorted by need_integer: the enumeration order, nothing else
    squad_satisfiable_without_addition: str  # SATISFIABLE | NOT_SATISFIABLE | UNFIELDABLE | UNKNOWN
    count: BriefCount | None  # None when no universe was given
    certificate: BriefCertificate
    evidence: dict
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    warnings: tuple[str, ...]
    claim: str
    provenance: dict


@dataclass
class _Enumeration:
    status: str
    completeness: str
    final_region_status: str
    rows: list[tuple[tuple[int, ...], Lineup]]
    solves: int
    reasons: tuple[str, ...] = ()


def meets_row(
    values: Mapping[str, float | None],
    row: BriefRow,
    requirements: Sequence[TacticalRequirement],
    dimensions: Sequence[str],
    quantization: int,
) -> bool:
    """Exact rational test: ``Fraction(value) >= need_integer * normalizer / quantization``
    on every dimension, which is ``floor_coefficient(value) >= need_integer``.

    An unmeasured value meets nothing. The test is sufficient for any rates; it is also
    necessary only for a complete brief and non-negative rates.
    """
    by_id = {r.requirement_id: r for r in requirements}
    dimensions = tuple(dimensions)
    if len(dimensions) != len(row.need_integer):
        raise ValueError("the row and the dimensions have different lengths")
    for requirement_id, need in zip(dimensions, row.need_integer, strict=True):
        requirement = by_id[requirement_id]
        value = values.get(requirement.metric)
        if value is None:
            return False
        if Fraction(value) * quantization < Fraction(need) * Fraction(requirement.normalizer):
            return False
    return True


def _pairwise_incomparable(vectors: Sequence[tuple[int, ...]]) -> bool:
    """No vector is weakly above another (which also rules out duplicates)."""
    return not any(
        i != j and all(a <= b for a, b in zip(low, high, strict=True))
        for i, low in enumerate(vectors)
        for j, high in enumerate(vectors)
    )


def _outward(need: int, normalizer: float, quantization: int) -> float:
    """The least float not below ``need * normalizer / quantization``: meeting the printed
    threshold is sufficient. Zero stays zero."""
    exact = Fraction(need, quantization) * Fraction(normalizer)
    shown = float(exact)
    return math.nextafter(shown, math.inf) if Fraction(shown) < exact else shown


def _canonical(candidate: Candidate) -> dict:
    return {
        "player_id": candidate.player_id,
        "name": candidate.name,
        "position": candidate.position,
        "values": {key: candidate.values[key] for key in sorted(candidate.values)},
        "minutes": candidate.minutes,
        "eligible_slots": None
        if candidate.eligible_slots is None
        else list(candidate.eligible_slots),
    }


def _injectables(
    universe: Any, slot: Slot, squad_ids: frozenset[int], metrics: Sequence[str]
) -> tuple[list[Candidate], str | None]:
    """The universe players the slot admits, each restricted to the slot, in player_id order.

    Two shapes are accepted. A candidate universe (the object of ``transfers.universe``:
    ``candidates`` carrying ``provider_position``, and ``provenance``): each member is
    restricted to the slot and kept when the solver's own eligibility rule admits him there,
    so the count's ``admissible`` cannot disagree with the injected solve. Or a sequence of
    ``Candidate`` already restricted to the slot, where an inadmissible one is an error.
    """
    recorded = None
    if hasattr(universe, "candidates") and hasattr(universe, "provenance"):
        recorded = dict(universe.provenance or {}).get("input_fingerprint")
        if not all(hasattr(member, "provider_position") for member in universe.candidates):
            raise ValueError("a candidate universe lists players with a provider_position")
        members = [
            Candidate(
                player_id=member.player_id,
                name=member.name,
                position=member.provider_position,
                values=member.values,
                minutes=member.minutes,
                eligible_slots=(slot.slot_id,),
            )
            for member in universe.candidates
        ]
        members = [member for member in members if _eligible(member, slot)]
    else:
        members = list(universe)
        for member in members:
            if not isinstance(member, Candidate):
                raise ValueError("a universe is a candidate universe or a sequence of Candidate")
            if member.eligible_slots != (slot.slot_id,):
                raise ValueError(
                    f"universe candidate {member.player_id} is not restricted to {slot.slot_id}"
                )
            if not _eligible(member, slot):
                raise ValueError(
                    f"universe candidate {member.player_id} is not admissible at {slot.slot_id}"
                )
    ids = [member.player_id for member in members]
    if any(type(pid) is not int for pid in ids) or len(ids) != len(set(ids)):
        raise ValueError("universe player IDs must be unique integers")
    collisions = sorted(set(ids) & squad_ids)
    if collisions:
        raise ValueError(f"universe player IDs collide with squad player IDs: {collisions}")
    for member in members:
        _non_negative(member, metrics)
    members.sort(key=lambda member: member.player_id)
    listed = fingerprint([_canonical(member) for member in members])
    return members, recorded if isinstance(recorded, str) else listed


def _non_negative(candidate: Candidate, metrics: Sequence[str]) -> None:
    for metric in metrics:
        value = candidate.values.get(metric)
        if value is not None and value < 0:
            raise ValueError(
                f"player {candidate.player_id} has a negative {metric}: "
                "the brief quantifies over additions with non-negative rates"
            )


def _enumerate(
    kernel: ShortfallKernel,
    slot_id: str,
    dimensions: Sequence[TacticalRequirement],
    fixed: Sequence[TacticalRequirement],
    locked: Sequence[int],
    excluded: Sequence[int],
    max_rows: int,
    deadline: float,
    seed: int,
) -> _Enumeration:
    """Section 6.5: the minimal need vectors of the residual problem, each with a witness."""
    background = kernel._background(excluded, locked, None, (slot_id,), None)
    run = _Run(deadline, seed)
    rows: list[tuple[tuple[int, ...], Lineup]] = []

    def done(status: str, completeness: str, final: str) -> _Enumeration:
        return _Enumeration(
            status, completeness, final, rows, len(run.statuses), background.reasons
        )

    def undecided(name: str) -> _Enumeration:
        if name == "MODEL_INVALID":
            return done("MODEL_INVALID", "DEADLINE", name)
        return done("INCOMPLETE", "DEADLINE", name)

    # A passed deadline answers nothing, even where a reason is a proof by construction.
    if time.monotonic() >= deadline:
        return done("INCOMPLETE", "DEADLINE", "NOT_RUN")
    if background.model is None:
        return done("RESIDUAL_UNFIELDABLE", "COMPLETE", "INFEASIBLE_BY_CONSTRUCTION")

    tables = kernel._tables(background, conservative=True)
    region = background.model.clone()
    for requirement in fixed:
        coefficients, target = tables[requirement.requirement_id]
        _at_least(region, kernel._expression(background, coefficients), target)

    def no_admissible_lineup() -> _Enumeration:
        """The region is empty before any row: which of the two negative statements holds."""
        if not fixed:  # the region is the background itself
            return done("RESIDUAL_UNFIELDABLE", "COMPLETE", "INFEASIBLE")
        name, _ = run.solve(background.model)
        if name == "INFEASIBLE":
            return done("RESIDUAL_UNFIELDABLE", "COMPLETE", "INFEASIBLE")
        if name in _WITNESS:
            return done("NOT_ADDRESSABLE_AT_SLOT", "COMPLETE", "INFEASIBLE")
        return undecided(name)

    def verified(vector: tuple[int, ...], solver) -> Lineup:
        lineup = kernel._witness(background, solver)
        if not kernel._admissible(background, lineup):
            raise RuntimeError("brief row returned an inadmissible residual lineup")
        found = []
        for requirement in (*dimensions, *fixed):
            coefficients, target = tables[requirement.requirement_id]
            supply = sum(coefficients.get((pid, sid), 0) for sid, pid in lineup)
            raw = sum(
                (
                    Fraction(background.vectors[pid][requirement.metric])
                    for sid, pid in lineup
                    if _applies(requirement, sid)
                ),
                Fraction(),
            )
            need = max(0, target - supply)
            if requirement in dimensions:
                found.append(need)
            # Raw supply plus the exact rational need reaches the raw minimum, no tolerance.
            exact = Fraction(need, kernel._quantization) * Fraction(requirement.normalizer)
            if (requirement not in dimensions and need) or raw + exact < Fraction(
                requirement.minimum
            ):
                raise RuntimeError("brief row failed its exact re-evaluation")
        if tuple(found) != vector:
            raise RuntimeError("brief row failed its exact re-evaluation")
        return lineup

    if not dimensions:
        # No declared requirement counts this slot: the only need vector is the empty one.
        name, solver = run.solve(region)
        if name == "INFEASIBLE":
            return no_admissible_lineup()
        if name not in _WITNESS:
            return undecided(name)
        rows.append(((), verified((), solver)))
        return done("NO_NEED", "COMPLETE", "INFEASIBLE_BY_CONSTRUCTION")

    needs = []
    for position, requirement in enumerate(dimensions):
        coefficients, target = tables[requirement.requirement_id]
        need = region.new_int_var(0, max(0, target), f"need_{position}")
        region.add(need + kernel._expression(background, coefficients) >= target)
        needs.append(need)

    while True:
        work = region.clone()
        vector: list[int] = []
        solver = None
        for position, need in enumerate(needs):
            work.minimize(need)
            name, solver = run.solve(work)
            if position == 0 and name == "INFEASIBLE":
                if not rows:
                    return no_admissible_lineup()
                return done("BRIEF", "COMPLETE", "INFEASIBLE")
            if position == 0 and name == "OPTIMAL" and len(rows) >= max_rows:
                # A further row exists and is not computed: the limit is a declared input.
                return done("INCOMPLETE", "LIMIT_REACHED", "OPTIMAL")
            if name == "INFEASIBLE":
                raise RuntimeError("brief enumeration lost a feasible lexicographic level")
            if name != "OPTIMAL":  # a FEASIBLE incumbent is not a minimum
                return undecided(name)
            vector.append(solver.value(need))
            work.add(need == vector[-1])
        row = tuple(vector)
        rows.append((row, verified(row, solver)))
        if not any(row):
            # Every need vector is weakly above zero: complete by construction.
            return done("NO_NEED", "COMPLETE", "INFEASIBLE_BY_CONSTRUCTION")
        # Leave the up-set of this row: strictly below it on at least one dimension.
        below = []
        for position, (need, value) in enumerate(zip(needs, row, strict=True)):
            if value >= 1:
                literal = region.new_bool_var(f"below_{len(rows)}_{position}")
                region.add(need <= value - 1).only_enforce_if(literal)
                below.append(literal)
        region.add_bool_or(below)


def _claim(
    slot: Slot,
    status: str,
    rows: int,
    fixed: Sequence[str],
    without_addition: str,
    count: BriefCount | None,
    quantization: int,
) -> str:
    where = f"{slot.label} ({slot.slot_id})"
    if status == "BRIEF" and rows == 1:
        head = (
            f"For {where}: a player added there makes every declared minimum reachable if, "
            "and only if, his rates meet this row on every listed requirement. It is the only "
            "minimal row."
        )
    elif status == "BRIEF":
        head = (
            f"For {where}: a player added there makes every declared minimum reachable if, "
            f"and only if, his rates meet at least one of these {rows} rows on every listed "
            "requirement. The rows are all the minimal ones."
        )
    elif status == "NO_NEED":
        head = (
            f"For {where}: the other slots reach every declared minimum without counting this "
            "one, so any addition placed there with measured, non-negative rates leaves every "
            "declared minimum reachable."
        )
    elif status == "NOT_ADDRESSABLE_AT_SLOT":
        head = (
            f"For {where}: no addition at this slot can make the declared minima reachable. "
            f"{', '.join(fixed)} do not count this slot and the other slots cannot reach them."
        )
    elif status == "RESIDUAL_UNFIELDABLE":
        head = (
            f"For {where}: the other slots cannot be filled from this squad under the declared "
            "exclusions and locks; one addition at this slot does not make an XI fieldable."
        )
    elif status == "INCOMPLETE":
        head = (
            f"For {where}: {rows} minimal rows were found before the limit. A player added "
            "there whose rates meet one of them on every listed requirement makes every "
            "declared minimum reachable; other rows may exist, so meeting none of them "
            "decides nothing."
        )
    else:
        head = f"For {where}: the solver rejected the model; no statement is made."
    counted = ""
    if count is not None and count.meeting is not None:
        counted = (
            f" {count.meeting} of the {count.admissible} gated players admissible at "
            f"{slot.slot_id} in the declared universe make every declared minimum reachable, "
            "each confirmed by an exact solve with him placed there."
        )
    elif count is not None:
        counted = (
            f" {count.undetermined} of the {count.admissible} gated players admissible at "
            f"{slot.slot_id} in the declared universe were not resolved before the deadline; "
            "no count is stated."
        )
    return (
        f"{head}{counted} {_NON_CLAIM} With the squad as it is, the minima are "
        f"{_WITHOUT_ADDITION[without_addition]} without any addition. Every statement refers "
        f"to the conservative integer model at quantization {quantization}."
    )


def role_brief(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    slot_id: str,
    locked: Sequence[int] = (),
    excluded: Sequence[int] = (),
    universe: Any = None,
    max_rows: int = MAX_BRIEF_ROWS,
    seed: int = 20260906,
    time_limit: float = 30.0,
    quantization: int = QUANTIZATION,
    provenance: Mapping | None = None,
) -> RoleBrief:
    """The minimal need rows of one slot, and optionally how many universe players meet them.

    ``universe`` is ``None`` (no count), a candidate universe object, or a sequence of
    ``Candidate`` already restricted to ``slot_id``. Every active requirement is a hard
    conservative floor here whatever its ``hard`` flag, as in ``ShortfallKernel.satisfiable``.
    One deadline covers the squad-without-addition solve, the enumeration and the count.
    """
    kernel = ShortfallKernel(
        candidates, requirements, formation, quantization=quantization, seed=seed
    )
    shape = FORMATIONS[formation] if isinstance(formation, str) else formation
    slot = next((s for s in shape.slots if s.slot_id == slot_id), None)
    if slot is None:
        raise ValueError(f"unknown slot for {shape.formation_id}: {slot_id}")
    if type(max_rows) is not int or not 1 <= max_rows <= 256:
        raise ValueError("max_rows must be an integer between 1 and 256")
    if (
        isinstance(time_limit, bool)
        or not isinstance(time_limit, (int, float))
        or not math.isfinite(time_limit)
        or time_limit <= 0
    ):
        raise ValueError("time_limit must be a positive number of seconds")
    squad = sorted(candidates, key=lambda player: player.player_id)
    active = sorted((r for r in requirements if r.active), key=lambda r: r.requirement_id)
    dimensions = tuple(r for r in active if _applies(r, slot_id))
    fixed = tuple(r for r in active if not _applies(r, slot_id))
    dimension_ids = tuple(r.requirement_id for r in dimensions)
    fixed_ids = tuple(r.requirement_id for r in fixed)
    metrics = sorted({r.metric for r in dimensions})
    for player in squad:
        _non_negative(player, metrics)
    injectables: list[Candidate] | None = None
    universe_fingerprint = None
    if universe is not None:
        injectables, universe_fingerprint = _injectables(
            universe, slot, frozenset(player.player_id for player in squad), metrics
        )
    # Validates the declarations before any solve; the same call builds the residual model.
    kernel._background(excluded, locked, None, (slot_id,), None)
    locked_ids, excluded_ids = tuple(sorted(set(locked))), tuple(sorted(set(excluded)))
    contract = {
        "version": BRIEF_VERSION,
        "kernel": kernel.input_contract,
        "slot_id": slot_id,
        "locked": list(locked_ids),
        "excluded": list(excluded_ids),
        "max_rows": max_rows,
        "seed": seed,
        "time_limit": time_limit,
        "quantization": quantization,
        "hard_policy": HARD_POLICY,
        "universe": None
        if injectables is None
        else [_canonical(member) for member in injectables],
        "universe_fingerprint": universe_fingerprint,
        "source_fingerprints": source_fingerprints(
            *(str(Path(__file__).parent / name) for name in _SOURCES)
        ),
        "source_provenance": dict(provenance or {}),
    }
    input_fingerprint = fingerprint(contract)

    deadline = time.monotonic() + time_limit
    baseline = kernel.satisfiable(excluded=excluded, locked=locked, deadline=deadline)
    found = _enumerate(
        kernel, slot_id, dimensions, fixed, locked, excluded, max_rows, deadline, seed
    )
    status = "MODEL_INVALID" if baseline.status == "MODEL_INVALID" else found.status
    found.rows.sort()
    vectors = [vector for vector, _ in found.rows]
    if not _pairwise_incomparable(vectors):
        raise RuntimeError("brief rows are not pairwise incomparable")
    rows = tuple(
        BriefRow(
            need_integer=vector,
            need=tuple(
                _outward(need, requirement.normalizer, quantization)
                for need, requirement in zip(vector, dimensions, strict=True)
            ),
            residual_supply=tuple(
                float(
                    sum(
                        (
                            Fraction(player.values[requirement.metric])
                            for sid, pid in lineup
                            for player in squad
                            if player.player_id == pid and _applies(requirement, sid)
                        ),
                        Fraction(),
                    )
                )
                for requirement in dimensions
            ),
            residual_lineup=lineup,
            certification="MINIMAL_CERTIFIED",
        )
        for vector, lineup in found.rows
    )
    complete = found.completeness == "COMPLETE" and status != "MODEL_INVALID"

    count = None
    count_solves = 0
    if injectables is not None:
        meeting: list[int] = []
        not_meeting = undetermined = 0
        agrees = True
        for member in injectables:
            injected = ShortfallKernel(
                [*squad, member], requirements, formation, quantization=quantization, seed=seed
            ).satisfiable(
                pinned={member.player_id: slot_id},
                excluded=excluded,
                locked=locked,
                deadline=deadline,
            )
            count_solves += injected.solves
            if injected.status in ("UNKNOWN", "MODEL_INVALID"):
                undetermined += 1
                continue
            met = injected.status == "SATISFIABLE"
            if met:
                meeting.append(member.player_id)
            else:
                not_meeting += 1
            by_rows = any(
                meets_row(member.values, row, requirements, dimension_ids, quantization)
                for row in rows
            )
            agrees = agrees and by_rows == met
        count = BriefCount(
            admissible=len(injectables),
            meeting=None if undetermined else len(meeting),
            not_meeting=not_meeting,
            undetermined=undetermined,
            meeting_ids=tuple(meeting),
            method="INJECTED_SATISFY_SOLVE",
            row_test_agrees=agrees if complete and not undetermined else None,
        )

    # The certificate covers the whole answer, not the row enumeration alone. An undecided
    # squad-without-addition solve or an undecided count solve leaves part of it unknown,
    # and a result that reads COMPLETE is what a cache keeps.
    completeness = found.completeness
    if completeness == "COMPLETE" and (
        baseline.status in ("UNKNOWN", "MODEL_INVALID")
        or (count is not None and count.undetermined)
    ):
        completeness = "DEADLINE"

    warnings = list(found.reasons)
    if status == "INCOMPLETE":
        warnings.append(INCOMPLETE_WARNING.format(n=len(rows)))
    if status == "BRIEF" and baseline.status == "SATISFIABLE":
        warnings.append(
            "With the squad as it is the minima are reachable, and the brief at "
            f"{slot_id} is non-zero all the same: the rows describe an addition who takes this "
            "slot, so whoever fills it now must play elsewhere or not at all."
        )
    if count is not None and count.row_test_agrees is False:
        warnings.append(
            "The row test and the exact solves disagree for at least one candidate; "
            "the count is taken from the solves."
        )

    evidence = compose_evidence(requirements)
    evidence["declared_inputs"] = [
        "formation",
        "requirement minima",
        "slot",
        *(["locks"] if locked_ids else []),
        *(["exclusions"] if excluded_ids else []),
        *(["candidate universe"] if injectables is not None else []),
    ]
    lineage = scrub_lineage(provenance)
    # A screening belongs to the call that ran it: an earlier result's is not inherited.
    lineage.pop("universe_fingerprint", None)
    lineage.pop("screened_count", None)
    record = {
        **lineage,
        "brief_version": BRIEF_VERSION,
        "kernel_version": KERNEL_VERSION,
        "hard_policy": HARD_POLICY,
        "quantization": quantization,
        "brief_solver_calls": {
            "squad_without_addition": baseline.solves,
            "enumeration": found.solves,
            "count": count_solves,
        },
        "per_solve_deterministic_limit": PER_SOLVE_DETERMINISTIC_LIMIT,
        "time_limit_seconds": time_limit,
        "input_fingerprint": input_fingerprint,
    }
    if injectables is not None:
        record["universe_fingerprint"] = universe_fingerprint
        record["screened_count"] = len(injectables)
    return RoleBrief(
        formation=shape.formation_id,
        slot_id=slot_id,
        slot_label=slot.label,
        dimensions=dimension_ids,
        fixed_floor_requirements=fixed_ids,
        status=status,
        rows=rows,
        squad_satisfiable_without_addition=baseline.status,
        count=count,
        certificate=BriefCertificate(
            rows=len(rows),
            pairwise_incomparable=True,
            witnesses_verified=True,
            final_region_status=found.final_region_status,
            solves=found.solves,
            completeness=completeness,
            quantization=quantization,
            hard_policy=HARD_POLICY,
        ),
        evidence=evidence,
        locked=locked_ids,
        excluded=excluded_ids,
        warnings=tuple(warnings),
        claim=_claim(
            slot, status, len(rows), fixed_ids, baseline.status, count, quantization
        ),
        provenance=record,
    )
