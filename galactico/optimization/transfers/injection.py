"""Exact candidate injection: what the declared model says when one player is added at one slot.

Claim: "With {candidate} placed at {slot}, the least declared shortfall is {z_c}; without him it
is {z_0}. In the squad plus him he is in every / in some / in no least-shortfall XI." Each side
is a certified value of the squad kernel, never a representative XI.

Non-claim: this is arithmetic on rates recorded at another club; whether they repeat after a
move has not been established. It is not a transfer value or a forecast, and the list is not an
order of merit. N players were screened: reading off the most favourable of many noisy
estimates overstates it, and no correction is applied.

How one forced solve gives the injected optimum. The XIs of the squad plus c are the disjoint
union of the squad's XIs and the XIs with c at s. With z_0 the squad's least shortfall and z_c
the least shortfall with c forced in (both lexicographic: maximum, then total; no XI compares
above every pair):

    least shortfall of the squad plus c = lexmin(z_0, z_c)
    c is in some least-shortfall XI   iff  z_c <= z_0
    c is in every least-shortfall XI  iff  z_c <  z_0

So an addition never raises the maximum component. The total at the lexicographic optimum can
move either way: a lower maximum can come with a higher total. With no XI at all, with or
without him, he is in none.

Ordering (ROOT 2.5 H8/H35). Rows are grouped by an exact categorical outcome of the injected
solve (``OUTCOME_GROUPS``, a fixed declared sequence), then listed inside a group by ONE
declared key, named in the response as ``order_key``. Equal keys are one tie group, listed by
player id. No key is derived from a solve, a membership, a world count or more than one
requirement, and no position number is emitted anywhere.

``injection_detail`` answers "who is no longer in any least-shortfall XI" on the injected
problem itself: the squad plus him is solved for its own level and membership is proved on
that level set. Nothing is read off two representative XIs.
"""

from __future__ import annotations

import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path

from ...domain.precision import format_plain
from ..reference import PERCENTILE_RULE, _nearest_order_statistic
from ..squad.kernel import (
    KERNEL_VERSION,
    PER_SOLVE_DETERMINISTIC_LIMIT,
    QUANTIZATION,
    SHORTFALL_POLICY,
    KernelValue,
    Membership,
    ShortfallKernel,
    compose_evidence,
    fingerprint,
    scrub_lineage,
    source_fingerprints,
)
from ..xi.domain import FORMATIONS, Candidate, Formation, TacticalRequirement
from ..xi.solver import _applies, _eligible

__all__ = [
    "INJECTION_VERSION",
    "ORDER_KEYS",
    "OUTCOME_GROUPS",
    "OUTCOME_STATEMENTS",
    "REFERENCE_PLAYER_ID",
    "SATURATED_WARNING",
    "BulkInjectionResult",
    "InclusionFacts",
    "InjectionCertificate",
    "InjectionDetail",
    "InjectionRow",
    "OrderingStatement",
    "OutcomeGroup",
    "RequirementRange",
    "TieGroup",
    "WorldCounts",
    "forced_inclusion_value",
    "has_measured_variable",
    "inclusion_facts",
    "inject_candidates",
    "injection_detail",
    "selection_statement",
]

INJECTION_VERSION = "forced-inclusion-injection-v1"
ORDER_KEYS = ("NAME", "PLAYER_ID", "MINUTES", "AGE", "REQUIREMENT_VALUE")
# The provider's "no player" id: the pool-median reference is a synthetic candidate, not a player.
REFERENCE_PLAYER_ID = 0
REFERENCE_NAME = "Pool median (not a player)"
# Fixed declared sequence of categorical outcomes; each is an exact fact about two certified values.
OUTCOME_GROUPS = (
    "REMOVES_SHORTFALL",
    "LOWERS_SHORTFALL",
    "MAKES_FIELDABLE",
    "UNCHANGED",
    "NOT_EVALUABLE",
    "UNDETERMINED",
)
OUTCOME_STATEMENTS: Mapping[str, str] = {
    "REMOVES_SHORTFALL": (
        "With him available the least declared shortfall is zero; without him it is not."
    ),
    "LOWERS_SHORTFALL": (
        "With him available the least declared shortfall (largest, then sum) is lower and "
        "still above zero. The sum alone can be higher."
    ),
    "MAKES_FIELDABLE": (
        "Without an addition no XI can be fielded under the declared exclusions and locks; "
        "with him at this slot one can."
    ),
    "UNCHANGED": (
        "The least declared shortfall is the same with and without him, or no XI can be "
        "fielded either way."
    ),
    "NOT_EVALUABLE": (
        "He cannot be placed at this slot in the model: the slot does not admit his provider "
        "position, or a rate an active requirement needs there is unavailable."
    ),
    "UNDETERMINED": "The solve was not certified in time. Nothing is implied.",
}
SATURATED_WARNING = (
    "The declared minima are already reachable without an addition. No candidate can lower a "
    "shortfall of zero. Declare a departure, raise a minimum or take a league percentile first."
)
"""Its last sentence names the three ways Transfer Lab offers to declare a shortfall, in the
words of its leads (``api.transfer_lab.DEFICIENCY_LEADS``; equal by test)."""
UNFIELDABLE_WARNING = (
    "The squad has no fieldable XI under the declared exclusions and locks without an addition "
    "at this or another slot."
)
_SELECTION_CAUTION = (
    "reading off the most favourable of many noisy estimates overstates it, and no correction "
    "is applied."
)
SELECTION_STATEMENT = "{n} players were screened: " + _SELECTION_CAUTION
"""For any number of screened players but one; ``selection_statement`` agrees in number."""
NON_CLAIM = (
    "This is arithmetic on rates recorded at another club; whether they repeat after a move "
    "has not been established. It is not a transfer value and not a forecast."
)
CARRY_OVER = "other club, untested"
# The shipped XI sentence says "not probability of football superiority". The page copy guard
# admits a named denial only, so the same statement is worded as one here.
WORLD_INTERPRETATION = "Conditional algorithm stability across resampled matches; not a probability"
SAME_NAMESPACE = "Squad and candidate values in a world come from one resample of the same matches."
# Which resample each side was drawn in is a field (``WorldCounts.namespace``,
# ``candidate_namespace``) and the result's provenance. A sentence carries no identifier.
OTHER_NAMESPACE = (
    "The candidate's values come from a separate resample of other matches; a world pairs two "
    "independent draws."
)
_HOLE = "missing shared-world exposure"
_PROVEN = ("CERTIFIED", "UNFIELDABLE")
_KEY_WORDS = {"NAME": "name", "PLAYER_ID": "player id", "MINUTES": "minutes", "AGE": "age"}
_SOURCES = ("injection.py", "../squad/kernel.py", "../xi/domain.py")

Worlds = Mapping[int, Mapping[int, Mapping[str, float | None]]]
Pair = tuple[int, int]


@dataclass(frozen=True)
class InclusionFacts:
    """What two certified values prove about the squad plus one candidate."""

    resolved: bool
    with_candidate: Pair | None  # least shortfall of the squad plus him; None when no XI exists
    possible: bool | None
    necessary: bool | None
    shortcut: str  # NONE | ZERO_WITNESS | SATURATED_BASELINE


@dataclass(frozen=True)
class WorldCounts:
    """Counts over shared worlds. Divided by nothing: "{forced_lower} of {used}".

    Every requested world is in exactly one of four places: one of the three compared cells
    (an XI was certified both without him and with him at the slot), ``no_xi`` (it is proved
    that no XI exists on one side or on both), ``discarded`` (no joint exposure) or
    ``incomplete`` (a solve was not decided). A proved absence of an XI is a finding about
    that world and is never filed with the worlds nothing was decided about.
    """

    namespace: str  # the resample the squad's values were drawn in
    candidate_namespace: str  # the resample his values were drawn in; another league's differs
    namespace_statement: str
    requested: int
    used: int  # worlds in the three cells below
    forced_lower: int  # worlds with z_c < z_0: in every least-shortfall XI there
    forced_equal: int  # z_c == z_0: in some
    forced_higher: int  # z_c > z_0: in none
    # {"world_id", "baseline_status", "forced_status"}, each CERTIFIED or UNFIELDABLE and at
    # least one UNFIELDABLE. By the theorem of the module docstring he is in every XI of such
    # a world when only the baseline is UNFIELDABLE, and in none otherwise.
    no_xi: tuple[dict, ...]
    discarded: tuple[dict, ...]  # {"world_id", "reason"}
    incomplete: tuple[dict, ...]  # {"world_id", "status"}: UNKNOWN or MODEL_INVALID
    interpretation: str


@dataclass(frozen=True)
class InjectionRow:
    player_id: int
    name: str
    slot_id: str
    outcome: str  # one of OUTCOME_GROUPS
    resolution: str  # SOLVED | NO_MEASURED_ADMISSIBLE_SLOT | UNCERTIFIED
    shortcut: str  # NONE | NO_VARIABLE | ZERO_WITNESS | SATURATED_BASELINE
    forced_status: str  # CERTIFIED | UNFIELDABLE | UNKNOWN | MODEL_INVALID | NOT_RUN
    forced_inclusion_integer: Pair | None  # (maximum, sum) in units of 1 / quantization
    forced_inclusion_objective: tuple[float, float] | None
    forced_inclusion_change: tuple[float, float] | None  # z_c - z_0, signed, per component
    with_candidate_integer: Pair | None
    with_candidate_objective: tuple[float, float] | None
    membership: str  # NECESSARY | POSSIBLE | NOT_POSSIBLE | UNDETERMINED
    possible: bool | None
    necessary: bool | None
    requirement_values: Mapping[str, float | None]  # his raw rates by requirement: a vector
    world_counts: WorldCounts | None
    order_key_value: str | int | float | None
    input_fingerprint: str


@dataclass(frozen=True)
class TieGroup:
    """Rows of one outcome group whose declared key is equal; listed by player id."""

    order_key_value: str | int | float | None
    player_ids: tuple[int, ...]


@dataclass(frozen=True)
class OutcomeGroup:
    outcome: str
    statement: str
    count: int
    tie_groups: tuple[TieGroup, ...]


@dataclass(frozen=True)
class OrderingStatement:
    order_key: str
    requirement_id: str | None
    descending: bool
    grouped_by: str
    statement: str


@dataclass(frozen=True)
class InjectionCertificate:
    baseline_status: str
    baseline_integer: Pair | None
    solves: int  # CP-SAT calls of the shortfall values (baseline, forced, worlds)
    shortcut_counts: Mapping[str, int]
    completeness: str  # EXACT | DEADLINE | MODEL_INVALID
    elapsed_seconds: float
    time_limit_seconds: float
    per_solve_deterministic_limit: float
    quantization: int
    shortfall_policy: str


@dataclass(frozen=True)
class BulkInjectionResult:
    formation: str
    slot_id: str
    baseline_objective: tuple[float, float] | None
    baseline_lineup: tuple[tuple[str, int], ...]  # one representative; ties exist
    rows: tuple[InjectionRow, ...]  # outcome group, then the declared key, then player id
    groups: tuple[OutcomeGroup, ...]  # non-empty groups in OUTCOME_GROUPS sequence
    pool_median_reference: InjectionRow | None  # a synthetic candidate; not a player
    order_key: str
    ordering: OrderingStatement
    screened_count: int
    selection_statement: str
    membership_counts: Mapping[str, int]
    certificate: InjectionCertificate
    evidence: dict
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    warnings: tuple[str, ...]
    claim: str
    non_claim: str
    provenance: dict


@dataclass(frozen=True)
class RequirementRange:
    """Shortfall of one requirement over every XI of a level set, in declared units."""

    requirement_id: str
    least_shortfall: float | None  # over the least-shortfall XIs with him forced in
    greatest_shortfall: float | None
    baseline_least: float | None  # the same range over the squad's own least-shortfall XIs
    baseline_greatest: float | None


@dataclass(frozen=True)
class InjectionDetail:
    row: InjectionRow
    requirement_ranges: tuple[RequirementRange, ...]
    squad_membership_baseline: Mapping[int, Membership]  # least-shortfall XIs of the squad
    squad_membership_with_candidate: Mapping[int, Membership]  # of the squad plus him
    squad_membership_forced: Mapping[int, Membership]  # of the XIs with him forced in
    no_longer_possible_ids: tuple[int, ...]  # in some least-shortfall XI before, in none after
    no_longer_necessary_ids: tuple[int, ...]  # in every least-shortfall XI before, not after
    forced_lineup: tuple[tuple[str, int], ...]  # one representative of the forced level set
    tie_statement: str
    level_set_queries: int  # membership and range questions put to the kernel
    certificate: InjectionCertificate
    evidence: dict
    warnings: tuple[str, ...]
    claim: str
    non_claim: str
    provenance: dict


# ------------------------------------------------------------------ the definition


def _pair(value: KernelValue | None) -> Pair | None:
    if value is None or value.status != "CERTIFIED":
        return None
    return (value.maximum, value.total)


def has_measured_variable(
    candidate: Candidate,
    requirements: Sequence[TacticalRequirement],
    formation: Formation,
    slot_id: str,
    values: Mapping[str, float | None] | None = None,
) -> bool:
    """Whether the model can place him at the slot at all (the kernel's variable rule).

    False when the slot does not admit his position or minutes, or a rate an active
    requirement needs at that slot is unavailable. Nothing is imputed.
    """
    slot = next(s for s in formation.slots if s.slot_id == slot_id)
    vector = candidate.values if values is None else values
    return _eligible(candidate, slot) and all(
        vector.get(r.metric) is not None for r in requirements if r.active and _applies(r, slot_id)
    )


def forced_inclusion_value(
    candidate: Candidate,
    squad: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    slot_id: str,
    locked: Sequence[int] = (),
    excluded: Sequence[int] = (),
    seed: int = 20260906,
    quantization: int = QUANTIZATION,
    deadline: float,
) -> KernelValue:
    """z_c: the least declared shortfall over the XIs that have the candidate at the slot."""
    kernel = ShortfallKernel(
        [*squad, candidate], requirements, formation, quantization=quantization, seed=seed
    )
    return kernel.value(
        excluded=excluded, locked=locked, pinned={candidate.player_id: slot_id}, deadline=deadline
    )


def inclusion_facts(baseline: KernelValue, forced: KernelValue) -> InclusionFacts:
    """The theorem of the module docstring, applied to two kernel values.

    An undecided forced value still proves "in no least-shortfall XI" in one case: the
    baseline is (0, 0) and the zero-shortfall solve with him forced in was INFEASIBLE.
    Nothing else is concluded from an undecided value.
    """
    undetermined = InclusionFacts(False, None, None, None, "NONE")
    if baseline.status not in _PROVEN:
        return undetermined
    base, own = _pair(baseline), _pair(forced)
    saturated = base == (0, 0) and forced.stage_statuses[:1] == ("INFEASIBLE",)
    if forced.status == "CERTIFIED":
        shortcut = (
            "ZERO_WITNESS" if own == (0, 0) else "SATURATED_BASELINE" if saturated else "NONE"
        )
        if base is None:
            return InclusionFacts(True, own, True, True, shortcut)
        return InclusionFacts(True, min(base, own), own <= base, own < base, shortcut)
    if forced.status == "UNFIELDABLE":
        return InclusionFacts(True, base, False, False, "NONE")
    if saturated:
        return InclusionFacts(True, base, False, False, "SATURATED_BASELINE")
    return undetermined


# ---------------------------------------------------------------------- validation


@dataclass(frozen=True)
class _Problem:
    squad: tuple[Candidate, ...]
    requirements: tuple[TacticalRequirement, ...]
    formation: Formation
    slot_id: str
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    seed: int
    quantization: int
    time_limit: float
    kernel: ShortfallKernel

    @property
    def declared(self) -> dict:
        return {"excluded": self.excluded, "locked": self.locked}

    def injected(self, candidate: Candidate) -> ShortfallKernel:
        return ShortfallKernel(
            [*self.squad, candidate],
            self.requirements,
            self.formation,
            quantization=self.quantization,
            seed=self.seed,
        )

    def forced(self, kernel: ShortfallKernel, candidate: Candidate, deadline: float, values=None):
        return kernel.value(
            **self.declared,
            pinned={candidate.player_id: self.slot_id},
            values=values,
            deadline=deadline,
        )


def _problem(squad, requirements, formation, slot_id, locked, excluded, seed, quantization,
             time_limit) -> _Problem:
    squad, requirements = tuple(squad), tuple(requirements)
    kernel = ShortfallKernel(squad, requirements, formation, quantization=quantization, seed=seed)
    shape = FORMATIONS[formation] if isinstance(formation, str) else formation
    if slot_id not in {slot.slot_id for slot in shape.slots}:
        raise ValueError(f"unknown slot for this formation: {slot_id}")
    if (
        isinstance(time_limit, bool)
        or not isinstance(time_limit, (int, float))
        or not math.isfinite(time_limit)
        or time_limit <= 0
    ):
        raise ValueError("time_limit must be a positive number of seconds")
    known = {player.player_id for player in squad}
    if REFERENCE_PLAYER_ID in known:
        raise ValueError("player id 0 is reserved for the pool-median reference")
    for name, ids in (("locked", locked), ("excluded", excluded)):
        ids = tuple(ids)
        if any(type(pid) is not int for pid in ids) or set(ids) - known:
            raise ValueError(f"{name} must name squad players; a pool candidate cannot be {name}")
    return _Problem(
        squad, requirements, shape, slot_id, tuple(sorted(set(locked))),
        tuple(sorted(set(excluded))), seed, quantization, float(time_limit), kernel,
    )


def _slot_label(problem: _Problem) -> str:
    """The declared slot as a person reads it. Ids stay in fields; sentences use the label."""
    return next(s.label for s in problem.formation.slots if s.slot_id == problem.slot_id)


def _pool(pool: Sequence[Candidate], problem: _Problem) -> tuple[Candidate, ...]:
    pool = tuple(pool)
    ids = [candidate.player_id for candidate in pool]
    if any(type(pid) is not int for pid in ids) or len(ids) != len(set(ids)):
        raise ValueError("pool player IDs must be unique integers")
    if set(ids) & {player.player_id for player in problem.squad}:
        raise ValueError("an injected candidate must have a player ID that is not in the squad")
    if REFERENCE_PLAYER_ID in ids:
        raise ValueError("player id 0 is reserved for the pool-median reference")
    for candidate in pool:
        slots = candidate.eligible_slots
        if slots is None or tuple(slots) != (problem.slot_id,):
            raise ValueError(
                f"candidate {candidate.player_id} must be restricted to the declared slot "
                f"{problem.slot_id}"
            )
    return tuple(sorted(pool, key=lambda candidate: candidate.player_id))


def _ordering(order_by, order_requirement_id, descending, ages, requirements) -> OrderingStatement:
    if order_by not in ORDER_KEYS:
        raise ValueError(
            f"order_by must be one of {ORDER_KEYS}; a key derived from a solve, a membership, "
            "a world count or several requirements would order players by merit"
        )
    if type(descending) is not bool:
        raise ValueError("descending is true or false")
    active = {r.requirement_id for r in requirements if r.active}
    if order_by == "REQUIREMENT_VALUE":
        if order_requirement_id not in active:
            raise ValueError(
                "REQUIREMENT_VALUE needs order_requirement_id naming ONE active requirement"
            )
    elif order_requirement_id is not None:
        raise ValueError("order_requirement_id is only read with order_by=REQUIREMENT_VALUE")
    if order_by == "AGE" and ages is None:
        raise ValueError("order_by=AGE needs the ages mapping")
    words = _KEY_WORDS.get(order_by, f"recorded {order_requirement_id} rate")
    return OrderingStatement(
        order_key=order_by,
        requirement_id=order_requirement_id,
        descending=descending,
        grouped_by="outcome",
        statement=(
            "Grouped by the exact outcome of the injected solve, then ordered by "
            f"{words}{', descending,' if descending else ''} inside each group. This is not an "
            f"order of merit. Rows with the same {words} are tied and listed by player id."
        ),
    )


def _key_value(candidate: Candidate, ordering: OrderingStatement, ages, requirements):
    if ordering.order_key == "NAME":
        return candidate.name.casefold()
    if ordering.order_key == "PLAYER_ID":
        return candidate.player_id
    if ordering.order_key == "MINUTES":
        return candidate.minutes
    if ordering.order_key == "AGE":
        return ages.get(candidate.player_id)
    metric = next(r.metric for r in requirements if r.requirement_id == ordering.requirement_id)
    return candidate.values.get(metric)


def _canonical(candidate: Candidate) -> dict:
    return {
        "player_id": candidate.player_id,
        "name": candidate.name,
        "position": candidate.position,
        "values": {key: candidate.values[key] for key in sorted(candidate.values)},
        "minutes": candidate.minutes,
        "eligible_slots": list(candidate.eligible_slots or ()),
    }


def _canonical_worlds(worlds: Mapping | None) -> dict | None:
    if worlds is None:
        return None
    return {
        str(world_id): {
            str(pid): {key: vector[key] for key in sorted(vector)}
            for pid, vector in worlds[world_id].items()
        }
        for world_id in worlds
    }


# -------------------------------------------------------------------------- worlds


class _SharedWorlds:
    """Squad and pool values per shared world; the baseline value of a world is solved once."""

    def __init__(self, problem: _Problem, squad_worlds: Worlds, pool_worlds: Worlds,
                 namespace: str, pool_namespaces: Mapping[int, str] | None = None) -> None:
        self.pool_namespaces = dict(pool_namespaces or {})
        for name in (namespace, *self.pool_namespaces.values()):
            if not isinstance(name, str) or not name:
                raise ValueError("worlds need the world_namespace they were drawn in")
        if set(pool_worlds) - set(squad_worlds):
            raise ValueError("pool_worlds names a world the squad has no values for")
        self.problem, self.squad, self.pool = problem, squad_worlds, pool_worlds
        self.namespace = namespace
        self.ids = sorted(squad_worlds)
        self.solves = 0
        self.invalid = False
        self._baselines: dict[int, KernelValue | None] = {}
        active = [r for r in problem.requirements if r.active]
        excluded = set(problem.excluded)
        # Per player: the metrics he needs in a world (solver.py:549-564).
        self._needed = {
            player.player_id: {
                r.metric
                for r in active
                for slot in problem.formation.slots
                if _eligible(player, slot) and _applies(r, slot.slot_id)
            }
            for player in problem.squad
            if player.player_id not in excluded
        }

    def namespace_of(self, player_id: int) -> str:
        """The resample a candidate's values were drawn in; the squad's unless declared."""
        return self.pool_namespaces.get(player_id, self.namespace)

    def own(self, player_id: int) -> dict:
        """One candidate's world inputs, canonical: his namespace and his vector per world."""
        found = {world_id: self.pool.get(world_id, {}).get(player_id) for world_id in self.ids}
        return {
            "namespace": self.namespace_of(player_id),
            "values": {
                str(world_id): None if vector is None else dict(vector)
                for world_id, vector in found.items()
            },
        }

    def squad_vectors(self, world_id: int) -> dict[int, Mapping[str, float | None]]:
        world = self.squad[world_id]
        return {p.player_id: world[p.player_id] for p in self.problem.squad if p.player_id in world}

    def baseline(self, world_id: int, deadline: float) -> KernelValue | None:
        """The squad's value in one world; None when a squad player has a hole there."""
        if world_id not in self._baselines:
            world = self.squad[world_id]
            exposed = all(
                all(dict(world.get(pid, {})).get(metric) is not None for metric in needed)
                for pid, needed in self._needed.items()
            )
            value = None
            if exposed:
                value = self.problem.kernel.value(
                    **self.problem.declared, values=self.squad_vectors(world_id), deadline=deadline
                )
                self.solves += value.solves
            self._baselines[world_id] = value
        return self._baselines[world_id]

    def counts(self, candidate: Candidate, kernel: ShortfallKernel, deadline: float) -> WorldCounts:
        problem, pid = self.problem, candidate.player_id
        cells = {"lower": 0, "equal": 0, "higher": 0}
        discarded, incomplete, no_xi = [], [], []
        for world_id in self.ids:
            base = self.baseline(world_id, deadline)
            vector = self.pool.get(world_id, {}).get(pid)
            if (
                base is None
                or vector is None
                or not has_measured_variable(
                    candidate, problem.requirements, problem.formation, problem.slot_id, vector
                )
            ):
                discarded.append({"world_id": world_id, "reason": _HOLE})
                continue
            forced = problem.forced(
                kernel, candidate, deadline, {**self.squad_vectors(world_id), pid: vector}
            )
            self.solves += forced.solves
            statuses = (base.status, forced.status)
            # Either side undecided: the world is open, whatever the other side proved.
            undecided = next((status for status in statuses if status not in _PROVEN), None)
            if undecided is not None:
                self.invalid |= "MODEL_INVALID" in statuses
                incomplete.append({"world_id": world_id, "status": undecided})
                continue
            if "UNFIELDABLE" in statuses:
                no_xi.append({"world_id": world_id, "baseline_status": base.status,
                              "forced_status": forced.status})
                continue
            own, squad = _pair(forced), _pair(base)
            cells["lower" if own < squad else "equal" if own == squad else "higher"] += 1
        own_namespace = self.namespace_of(pid)
        return WorldCounts(
            namespace=self.namespace,
            candidate_namespace=own_namespace,
            namespace_statement=(
                SAME_NAMESPACE if own_namespace == self.namespace else OTHER_NAMESPACE
            ),
            requested=len(self.ids),
            used=sum(cells.values()),
            forced_lower=cells["lower"],
            forced_equal=cells["equal"],
            forced_higher=cells["higher"],
            no_xi=tuple(no_xi),
            discarded=tuple(discarded),
            incomplete=tuple(incomplete),
            interpretation=WORLD_INTERPRETATION,
        )


def _shared_worlds(problem, squad_worlds, pool_worlds, namespace, pool_namespaces=None
                   ) -> _SharedWorlds | None:
    if (squad_worlds is None) != (pool_worlds is None):
        raise ValueError("squad worlds and candidate worlds are given together or not at all")
    if squad_worlds is None:
        if pool_namespaces:
            raise ValueError("a candidate world namespace was declared without worlds")
        return None
    return _SharedWorlds(problem, squad_worlds, pool_worlds, namespace, pool_namespaces)


# ---------------------------------------------------------------------------- rows


@dataclass
class _Evaluation:
    row: InjectionRow
    forced: KernelValue | None
    kernel: ShortfallKernel | None
    solves: int


def _outcome(baseline: KernelValue, facts: InclusionFacts) -> str:
    if not facts.resolved:
        return "UNDETERMINED"
    if baseline.status == "UNFIELDABLE":
        return "MAKES_FIELDABLE" if facts.necessary else "UNCHANGED"
    if not facts.necessary:
        return "UNCHANGED"
    return "REMOVES_SHORTFALL" if facts.with_candidate == (0, 0) else "LOWERS_SHORTFALL"


def _evaluate(problem: _Problem, candidate: Candidate, baseline: KernelValue, deadline: float,
              worlds: _SharedWorlds | None, key_value, parent: str, shortcuts: bool
              ) -> _Evaluation:
    scale = problem.quantization
    variable = has_measured_variable(
        candidate, problem.requirements, problem.formation, problem.slot_id
    )
    forced, kernel, counts, solves = None, None, None, 0
    if variable or not shortcuts:
        kernel = problem.injected(candidate)
        # A baseline that is not proven decides nothing; no forced solve is spent on it.
        if baseline.status in _PROVEN:
            forced = problem.forced(kernel, candidate, deadline)
            solves = forced.solves
    base = _pair(baseline)
    if not variable:
        if forced is not None and forced.status == "CERTIFIED":
            raise RuntimeError("a candidate with no variable at the slot was given a value")
        facts = InclusionFacts(True, base, False, False, "NO_VARIABLE")
        resolution, outcome = "NO_MEASURED_ADMISSIBLE_SLOT", "NOT_EVALUABLE"
    else:
        facts = (
            inclusion_facts(baseline, forced)
            if forced is not None
            else InclusionFacts(False, None, None, None, "NONE")
        )
        resolution = "SOLVED" if facts.resolved else "UNCERTIFIED"
        outcome = _outcome(baseline, facts)
        if worlds is not None:
            counts = worlds.counts(candidate, kernel, deadline)
    own = _pair(forced)
    after = facts.with_candidate
    membership = (
        "UNDETERMINED" if facts.possible is None
        else "NECESSARY" if facts.necessary
        else "POSSIBLE" if facts.possible
        else "NOT_POSSIBLE"
    )
    row = InjectionRow(
        player_id=candidate.player_id,
        name=candidate.name,
        slot_id=problem.slot_id,
        outcome=outcome,
        resolution=resolution,
        shortcut=facts.shortcut,
        forced_status="NOT_RUN" if forced is None else forced.status,
        forced_inclusion_integer=own,
        forced_inclusion_objective=None if own is None else (own[0] / scale, own[1] / scale),
        forced_inclusion_change=(
            None if own is None or base is None
            else ((own[0] - base[0]) / scale, (own[1] - base[1]) / scale)
        ),
        with_candidate_integer=after,
        with_candidate_objective=None if after is None else (after[0] / scale, after[1] / scale),
        membership=membership,
        possible=facts.possible,
        necessary=facts.necessary,
        requirement_values={
            r.requirement_id: candidate.values.get(r.metric)
            for r in sorted(problem.requirements, key=lambda r: r.requirement_id)
            if r.active
        },
        world_counts=counts,
        order_key_value=key_value,
        # His own world values are inputs of his world counts; nobody else's are.
        input_fingerprint=fingerprint({
            "parent": parent,
            "candidate": _canonical(candidate),
            "candidate_worlds": None if worlds is None else worlds.own(candidate.player_id),
        }),
    )
    return _Evaluation(row, forced, kernel, solves)


def _value_left_open(row: InjectionRow) -> bool:
    """A forced value the solve did not certify, even when membership was proved without it."""
    return row.resolution == "UNCERTIFIED" or row.forced_status == "UNKNOWN"


def _pool_median(pool: Sequence[Candidate], problem: _Problem) -> Candidate | None:
    """A synthetic candidate at the pool's per-metric median (nearest order statistic)."""
    if not pool:
        return None
    slot = next(s for s in problem.formation.slots if s.slot_id == problem.slot_id)
    values: dict[str, float | None] = {}
    for metric in sorted({r.metric for r in problem.requirements if r.active}):
        present = sorted(
            c.values[metric] for c in pool if c.values.get(metric) is not None
        )
        values[metric] = _nearest_order_statistic(present, 50) if present else None
    return Candidate(
        REFERENCE_PLAYER_ID,
        REFERENCE_NAME,
        slot.allowed_positions[0],
        values,
        _nearest_order_statistic(sorted(c.minutes for c in pool), 50),
        (problem.slot_id,),
    )


def _grouped(rows: Sequence[InjectionRow], descending: bool
             ) -> tuple[tuple[InjectionRow, ...], tuple[OutcomeGroup, ...]]:
    ordered: list[InjectionRow] = []
    groups = []
    for outcome in OUTCOME_GROUPS:
        members = sorted((r for r in rows if r.outcome == outcome), key=lambda r: r.player_id)
        if not members:
            continue
        # A stable sort keeps player-id order inside equal keys; an unavailable key goes last.
        keyed = sorted(
            (r for r in members if r.order_key_value is not None),
            key=lambda r: r.order_key_value,
            reverse=descending,
        )
        ties = [
            TieGroup(value, tuple(sorted(r.player_id for r in group)))
            for value, group in groupby(keyed, key=lambda r: r.order_key_value)
        ]
        by_id = {r.player_id: r for r in members}
        missing = [r.player_id for r in members if r.order_key_value is None]
        if missing:
            ties.append(TieGroup(None, tuple(missing)))
        ordered += [by_id[pid] for tie in ties for pid in tie.player_ids]
        groups.append(OutcomeGroup(outcome, OUTCOME_STATEMENTS[outcome], len(members), tuple(ties)))
    return tuple(ordered), tuple(groups)


def _certificate(problem: _Problem, baseline: KernelValue, rows: Sequence[InjectionRow],
                 solves: int, started: float, *, invalid: bool, incomplete: bool
                 ) -> InjectionCertificate:
    invalid = invalid or baseline.status == "MODEL_INVALID" or any(
        r.forced_status == "MODEL_INVALID" for r in rows
    )
    incomplete = incomplete or baseline.status not in _PROVEN or any(
        _value_left_open(r)
        # A world with no fieldable XI is a proved fact about that world and is counted in
        # ``no_xi``; ``incomplete`` holds only the worlds a solve left undecided.
        or bool(r.world_counts and r.world_counts.incomplete)
        for r in rows
    )
    counts = dict.fromkeys(("NONE", "NO_VARIABLE", "ZERO_WITNESS", "SATURATED_BASELINE"), 0)
    for row in rows:
        counts[row.shortcut] += 1
    return InjectionCertificate(
        baseline_status=baseline.status,
        baseline_integer=_pair(baseline),
        solves=solves,
        shortcut_counts=counts,
        completeness="MODEL_INVALID" if invalid else "DEADLINE" if incomplete else "EXACT",
        elapsed_seconds=time.monotonic() - started,
        time_limit_seconds=problem.time_limit,
        per_solve_deterministic_limit=PER_SOLVE_DETERMINISTIC_LIMIT,
        quantization=problem.quantization,
        shortfall_policy=SHORTFALL_POLICY,
    )


def _baseline_warnings(problem: _Problem, baseline: KernelValue) -> list[str]:
    if _pair(baseline) == (0, 0):
        return [SATURATED_WARNING]
    if baseline.status == "UNFIELDABLE":
        return [UNFIELDABLE_WARNING]
    if baseline.status != "CERTIFIED":
        return [
            f"The squad's own least shortfall was not certified within {problem.time_limit:g} s. "
            "No candidate fact is implied."
        ]
    return []


def selection_statement(screened: int) -> str:
    """The selection caution for a pool of this size, agreeing in number with it."""
    if screened == 1:
        return f"1 player was screened: {_SELECTION_CAUTION}"
    return SELECTION_STATEMENT.format(n=screened)


def _side(pair: Pair | None, status: str, scale: int, subject: str) -> str:
    """One side of a claim as a clause of its own, whatever was proved about that side.

    A certified pair is printed in declared units, written out: never rounded a second time
    and never in exponent notation. A proved absence of an XI is said as that, and never as
    the value of ``subject`` ("the least declared shortfall", or "it" once that was named).
    """
    if pair is not None:
        return (f"{subject} is (largest {format_plain(pair[0] / scale)}, "
                f"sum {format_plain(pair[1] / scale)})")
    if status == "UNFIELDABLE":
        return "no XI can be fielded"
    return f"{subject} is not determined"


def _parent_payload(problem: _Problem, squad_worlds, namespace: str, provenance) -> dict:
    here = Path(__file__).parent
    return {
        "version": INJECTION_VERSION,
        "kernel": problem.kernel.input_contract,
        "slot_id": problem.slot_id,
        "locked": list(problem.locked),
        "excluded": list(problem.excluded),
        "seed": problem.seed,
        "time_limit": problem.time_limit,
        "quantization": problem.quantization,
        "shortfall_policy": SHORTFALL_POLICY,
        "world_namespace": namespace,
        "squad_worlds": fingerprint(_canonical_worlds(squad_worlds)),
        "source_fingerprints": source_fingerprints(*(str(here / name) for name in _SOURCES)),
        "source_provenance": dict(provenance or {}),
    }


def _evidence(problem: _Problem, declared: Mapping[str, object]) -> dict:
    evidence = compose_evidence(problem.requirements)
    minima = {r.requirement_id: r.minimum for r in problem.requirements if r.active}
    evidence["declared_inputs"] = [
        {"input": name, "value": value}
        for name, value in {
            "formation": problem.formation.formation_id,
            "slot_id": problem.slot_id,
            "requirement_minima": minima,
            "excluded": list(problem.excluded),
            "locked": list(problem.locked),
            **declared,
        }.items()
    ]
    return evidence


# ----------------------------------------------------------------------------- bulk


def inject_candidates(
    pool: Sequence[Candidate],
    squad: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    slot_id: str,
    locked: Sequence[int] = (),
    excluded: Sequence[int] = (),
    order_by: str = "NAME",
    order_requirement_id: str | None = None,
    descending: bool = False,
    ages: Mapping[int, int | None] | None = None,
    squad_worlds: Worlds | None = None,
    pool_worlds: Worlds | None = None,
    world_namespace: str = "",
    pool_world_namespaces: Mapping[int, str] | None = None,
    seed: int = 20260906,
    time_limit: float = 60.0,
    quantization: int = QUANTIZATION,
    provenance: Mapping | None = None,
    _shortcuts: bool = True,
) -> BulkInjectionResult:
    """One exact forced-inclusion solve per pool candidate, against one baseline.

    Every pool candidate is restricted to ``slot_id``. Rows come back grouped by outcome, then
    by the one declared key; a row's facts do not depend on who else was screened or on the
    ordering. A row that was not certified before the deadline is UNDETERMINED, never
    "not possible". ``world_namespace`` is the resample the squad's worlds were drawn in;
    ``pool_world_namespaces`` (player id -> namespace) names another one for a candidate whose
    worlds were drawn separately, as another league's are. ``_shortcuts`` is a test switch:
    off, a candidate with no variable at the slot is also put through the kernel.
    """
    started = time.monotonic()
    problem = _problem(
        squad, requirements, formation, slot_id, locked, excluded, seed, quantization, time_limit
    )
    pool = _pool(pool, problem)
    ordering = _ordering(order_by, order_requirement_id, descending, ages, problem.requirements)
    declared_namespaces = dict(pool_world_namespaces or {})
    worlds = _shared_worlds(
        problem, squad_worlds, pool_worlds, world_namespace,
        {c.player_id: declared_namespaces[c.player_id] for c in pool
         if c.player_id in declared_namespaces},
    )
    parent = _parent_payload(problem, squad_worlds, world_namespace, provenance)
    parent_hash = fingerprint(parent)
    deadline = started + problem.time_limit

    baseline = problem.kernel.value(**problem.declared, deadline=deadline)
    evaluations = [
        _evaluate(
            problem, candidate, baseline, deadline, worlds,
            _key_value(candidate, ordering, ages, problem.requirements), parent_hash, _shortcuts,
        )
        for candidate in pool
    ]
    median = _pool_median(pool, problem)
    reference = (
        None if median is None
        else _evaluate(problem, median, baseline, deadline, None, None, parent_hash, _shortcuts)
    )
    rows, groups = _grouped([e.row for e in evaluations], descending)
    solves = baseline.solves + sum(e.solves for e in evaluations)
    solves += (reference.solves if reference else 0) + (worlds.solves if worlds else 0)
    certificate = _certificate(
        problem, baseline, rows, solves, started,
        invalid=bool(worlds and worlds.invalid)
        or bool(reference and reference.row.forced_status == "MODEL_INVALID"),
        incomplete=bool(reference and _value_left_open(reference.row)),
    )
    membership_counts = dict.fromkeys(("NECESSARY", "POSSIBLE", "NOT_POSSIBLE", "UNDETERMINED"), 0)
    for row in rows:
        membership_counts[row.membership] += 1
    warnings = _baseline_warnings(problem, baseline)
    open_rows = membership_counts["UNDETERMINED"]
    if open_rows:
        warnings.append(
            f"{open_rows} candidate{' was' if open_rows == 1 else 's were'} not resolved within "
            f"{problem.time_limit:g} s. Undetermined is not 'not possible'."
        )
    cut_off = sum(row.resolution == "SOLVED" and _value_left_open(row) for row in rows)
    if cut_off:
        warnings.append(
            f"{cut_off} forced-inclusion value{' was' if cut_off == 1 else 's were'} not "
            f"computed within {problem.time_limit:g} s. Whether "
            f"{'that candidate is' if cut_off == 1 else 'those candidates are'} in a "
            "least-shortfall XI was still proved; no value is implied."
        )
    selection = selection_statement(len(pool))
    scale = problem.quantization
    base = _pair(baseline)
    pool_namespaces = (
        {} if worlds is None
        else {str(pid): name for pid, name in sorted(worlds.pool_namespaces.items())}
    )
    screened = (f"For each of {len(pool)} screened candidates" if len(pool) != 1
                else "For the 1 screened candidate")
    result_provenance = {
        **scrub_lineage(provenance),
        "injection_version": INJECTION_VERSION,
        "kernel_version": KERNEL_VERSION,
        "solver_package_version": parent["kernel"]["solver_package_version"],
        "world_namespace": world_namespace,
        # Candidates whose worlds were drawn in another resample than the squad's, by id.
        "pool_world_namespaces": pool_namespaces,
        "screened_count": len(pool),
        "selection_statement": selection,
        "order_key": ordering.order_key,
        "outcome_groups": list(OUTCOME_GROUPS),
        "pool_median_rule": (
            f"per requirement metric, the median of the pool's available values "
            f"({PERCENTILE_RULE}); a synthetic candidate with player id 0, not a player"
        ),
        "carry_over": CARRY_OVER,
        "input_fingerprint": fingerprint({
            **parent,
            "pool": [_canonical(candidate) for candidate in pool],
            "pool_worlds": fingerprint(_canonical_worlds(pool_worlds)),
            "pool_world_namespaces": pool_namespaces,
            "ordering": [ordering.order_key, ordering.requirement_id, ordering.descending],
            "ages": None if order_by != "AGE" else {str(k): ages[k] for k in sorted(ages)},
        }),
    }
    return BulkInjectionResult(
        formation=problem.formation.formation_id,
        slot_id=slot_id,
        baseline_objective=None if base is None else (base[0] / scale, base[1] / scale),
        baseline_lineup=baseline.lineup,
        rows=rows,
        groups=groups,
        pool_median_reference=None if reference is None else reference.row,
        order_key=ordering.order_key,
        ordering=ordering,
        screened_count=len(pool),
        selection_statement=selection,
        membership_counts=membership_counts,
        certificate=certificate,
        evidence=_evidence(problem, {
            "order_by": order_by,
            "order_requirement_id": order_requirement_id,
            "descending": descending,
        }),
        locked=problem.locked,
        excluded=problem.excluded,
        warnings=tuple(warnings),
        claim=(
            "Without an addition "
            f"{_side(base, baseline.status, scale, 'the least declared shortfall')}. "
            f"{screened} placed at {_slot_label(problem)}: the least declared shortfall with "
            "him forced into the XI, and whether he is in every, some or no least-shortfall "
            "XI of the squad plus him."
        ),
        non_claim=f"{NON_CLAIM} {ordering.statement} {selection}",
        provenance=result_provenance,
    )


# --------------------------------------------------------------------------- detail


def injection_detail(
    candidate: Candidate,
    squad: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    slot_id: str,
    locked: Sequence[int] = (),
    excluded: Sequence[int] = (),
    squad_worlds: Worlds | None = None,
    candidate_worlds: Worlds | None = None,
    world_namespace: str = "",
    candidate_world_namespace: str | None = None,
    seed: int = 20260906,
    time_limit: float = 30.0,
    quantization: int = QUANTIZATION,
    provenance: Mapping | None = None,
) -> InjectionDetail:
    """One candidate in full: ranges, squad memberships and who is no longer possible.

    ``candidate_worlds`` has the shape of ``squad_worlds`` (world id, then player id);
    ``candidate_world_namespace`` names the resample they were drawn in when it is not the
    squad's ``world_namespace``. The squad plus him is solved for its own level; the theorem's
    value is checked against it and a disagreement raises. A membership the deadline left open
    stays ``None``.
    """
    started = time.monotonic()
    problem = _problem(
        squad, requirements, formation, slot_id, locked, excluded, seed, quantization, time_limit
    )
    (candidate,) = _pool([candidate], problem)
    worlds = _shared_worlds(
        problem, squad_worlds, candidate_worlds, world_namespace,
        None if candidate_world_namespace is None
        else {candidate.player_id: candidate_world_namespace},
    )
    parent = _parent_payload(problem, squad_worlds, world_namespace, provenance)
    deadline = started + problem.time_limit
    declared, pin = problem.declared, {candidate.player_id: slot_id}
    squad_ids = sorted(player.player_id for player in problem.squad)
    active = sorted(r.requirement_id for r in problem.requirements if r.active)

    baseline = problem.kernel.value(**declared, deadline=deadline)
    evaluation = _evaluate(
        problem, candidate, baseline, deadline, worlds, None, fingerprint(parent), True
    )
    row, forced = evaluation.row, evaluation.forced
    kernel = evaluation.kernel or problem.injected(candidate)
    solves = baseline.solves + evaluation.solves + (worlds.solves if worlds else 0)
    queries = 0

    before: dict[int, Membership] = {}
    base_ranges: dict = {}
    if baseline.status == "CERTIFIED":
        before = problem.kernel.membership(baseline, squad_ids, **declared, deadline=deadline)
        base_ranges = problem.kernel.shortfall_ranges(baseline, **declared, deadline=deadline)
        queries += len(squad_ids) + len(active)

    # The injected problem computes its own level: the kernel ties a level to its model.
    after = kernel.value(**declared, deadline=deadline)
    solves += after.solves
    together: dict[int, Membership] = {}
    comparable = baseline.status in _PROVEN and row.resolution != "UNCERTIFIED"
    if comparable and after.status in _PROVEN and _pair(after) != row.with_candidate_integer:
        raise RuntimeError("the injection theorem disagrees with the direct solve of the squad")
    if after.status == "CERTIFIED":
        together = kernel.membership(
            after, [*squad_ids, candidate.player_id], **declared, deadline=deadline
        )
        queries += len(squad_ids) + 1
        direct = together.pop(candidate.player_id)
        for proved, stated in ((direct.possible, row.possible), (direct.necessary, row.necessary)):
            if proved is not None and stated is not None and proved != stated:
                raise RuntimeError("the injection theorem disagrees with the proved membership")

    inside: dict[int, Membership] = {}
    forced_ranges: dict = {}
    if forced is not None and forced.status == "CERTIFIED":
        inside = kernel.membership(forced, squad_ids, **declared, pinned=pin, deadline=deadline)
        forced_ranges = kernel.shortfall_ranges(forced, **declared, pinned=pin, deadline=deadline)
        queries += len(squad_ids) + len(active)

    scale = problem.quantization

    def bound(ranges: Mapping, rid: str, position: int) -> float | None:
        found = ranges.get(rid)
        return None if found is None else found[position] / scale

    ranges = tuple(
        RequirementRange(
            rid, bound(forced_ranges, rid, 0), bound(forced_ranges, rid, 1),
            bound(base_ranges, rid, 0), bound(base_ranges, rid, 1),
        )
        for rid in active
    )
    gone = tuple(
        pid for pid in squad_ids
        if pid in before and pid in together
        and before[pid].possible is True and together[pid].possible is False
    )
    freed = tuple(
        pid for pid in squad_ids
        if pid in before and pid in together
        and before[pid].necessary is True and together[pid].necessary is False
    )
    open_facts = sum(
        fact.possible is None or fact.necessary is None
        for table in (before, together, inside)
        for fact in table.values()
    ) + sum(
        table.get(rid) is None for table in (base_ranges, forced_ranges) if table for rid in active
    )
    undecided = after.status not in _PROVEN or bool(open_facts)
    certificate = _certificate(
        problem, baseline, [row], solves, started,
        invalid=bool(worlds and worlds.invalid) or after.status == "MODEL_INVALID",
        incomplete=undecided,
    )
    warnings = _baseline_warnings(problem, baseline)
    if undecided or _value_left_open(row):
        warnings.append(
            f"Some facts were not resolved within {problem.time_limit:g} s. Undetermined is "
            "not 'not possible'."
        )
    names = {player.player_id: player.name for player in problem.squad}
    if undecided or baseline.status != "CERTIFIED" or after.status != "CERTIFIED":
        tie_statement = (
            "Who is no longer in any least-shortfall XI is stated only when the squad has a "
            "certified least shortfall both without and with the addition."
        )
    elif gone:
        tie_statement = (
            f"With {candidate.name} available, these players are in a least-shortfall XI "
            f"without him and in none with him: {', '.join(names[pid] for pid in gone)}."
        )
    elif row.possible is False:
        tie_statement = (
            f"No squad player is forced out: {candidate.name} is in no least-shortfall XI, so "
            "the least-shortfall XIs are the same with and without him."
        )
    else:
        # Proved by the two membership tables alone, whatever his own row could establish.
        tie_statement = (
            f"No squad player is forced out: every player who is in a least-shortfall XI "
            f"without {candidate.name} is still in one with him available."
        )
    base = _pair(baseline)
    membership_words = {
        "NECESSARY": "in every least-shortfall XI",
        "POSSIBLE": "in some least-shortfall XIs and not in all",
        "NOT_POSSIBLE": "in no least-shortfall XI",
        "UNDETERMINED": "of undetermined membership",
    }[row.membership]
    # Each side is a clause of its own. No solve was run for a candidate the model cannot
    # place: that is a proof, not a deadline. A side with no XI has no shortfall to name, so
    # "it" stands for the shortfall only when the clause before it named one.
    shortfall = "the least declared shortfall"
    no_xi_with_him = (row.resolution != "NO_MEASURED_ADMISSIBLE_SLOT"
                      and row.forced_inclusion_integer is None
                      and row.forced_status == "UNFIELDABLE")
    with_him = (
        f"{shortfall} is not defined (the model cannot place him at this slot)"
        if row.resolution == "NO_MEASURED_ADMISSIBLE_SLOT"
        else _side(row.forced_inclusion_integer, row.forced_status, scale, shortfall)
    )
    without_him = _side(base, baseline.status, scale, shortfall if no_xi_with_him else "it")
    if no_xi_with_him and base is None and baseline.status == "UNFIELDABLE":
        without_him += " either"
    return InjectionDetail(
        row=row,
        requirement_ranges=ranges,
        squad_membership_baseline=before,
        squad_membership_with_candidate=together,
        squad_membership_forced=inside,
        no_longer_possible_ids=gone,
        no_longer_necessary_ids=freed,
        forced_lineup=() if forced is None else forced.lineup,
        tie_statement=tie_statement,
        level_set_queries=queries,
        certificate=certificate,
        evidence=_evidence(problem, {"candidate_player_id": candidate.player_id}),
        warnings=tuple(warnings),
        claim=(
            f"With {candidate.name} placed at {_slot_label(problem)}, {with_him}; without him "
            f"{without_him}. In the squad plus him he is {membership_words}."
        ),
        non_claim=NON_CLAIM,
        provenance={
            **scrub_lineage(provenance),
            "injection_version": INJECTION_VERSION,
            "kernel_version": KERNEL_VERSION,
            "solver_package_version": parent["kernel"]["solver_package_version"],
            "world_namespace": world_namespace,
            # The resample his world values were drawn in; None when it is the squad's.
            "candidate_world_namespace": candidate_world_namespace,
            "carry_over": CARRY_OVER,
            "input_fingerprint": fingerprint({
                **parent,
                "candidate": _canonical(candidate),
                "candidate_worlds": fingerprint(_canonical_worlds(candidate_worlds)),
                "candidate_world_namespace": candidate_world_namespace,
            }),
        },
    )
