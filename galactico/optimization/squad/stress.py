"""Exact k-absence stress of one XI model. A declared scenario, never a likelihood.

Claim: "If {players} are unavailable, the least declared shortfall this model can reach rises
from {baseline} to {value}. Over all {n} sets of {k} players this is the largest rise among sets
that still leave a fieldable XI; {u} sets leave none. Every set was solved to proof or inherited
from one that was."

Non-claim: "Unavailability is a scenario you chose. No likelihood of injury or suspension is
estimated, and a player whose absence changes nothing here may matter for everything this model
does not measure." When a set leaves no fieldable XI, one warning says that such sets reflect
the evidence gate and the eligibility rules, not the real squad.

Every set of 1..k removable players is enumerated. A set's value is the kernel's least
(maximum, total) shortfall with those players excluded as well, in the shipped half-even
integers, or the separate outcome UNFIELDABLE, which is never encoded as a large number.
Levels are reported separately because "exactly j" and "at most j" differ once unfieldable
sets exist: a single absence can cost more than every pair that still leaves an XI.

A set is not solved when a subset already settles it. The locks are the same for every set
(a locked player is never removable), so removing more players only shrinks the set of XIs:
an unfieldable subset makes the set unfieldable, and a subset whose certified XI avoids the
extra players gives the set that same value. Both rules are proofs, and a test re-solves every
inherited set directly.

A set that leaves no XI is a core when no proper non-empty subset does. Each core is explained
without the solver by a group of slots with fewer remaining players than slots, which anyone
can check by counting. Such a group always exists: the squad without absences fields every
locked player, an absence removes no locked player, and a cover of every slot and a placement
of every locked player can always be combined into one XI (Mendelsohn-Dulmage). So the locks
are never the cause of a core, and a core without a short slot group is raised as an error.

Worst sets keep every tie and are listed in player_id order, which is not an order of merit.
Nothing here uses a resampled world.
"""

from __future__ import annotations

import itertools
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

from ...domain.precision import format_plain
from ..xi.domain import FORMATIONS, Candidate, Formation, TacticalRequirement
from ..xi.solver import QUANTIZATION, _applies, _eligible
from .kernel import (
    KERNEL_VERSION,
    SHORTFALL_POLICY,
    KernelValue,
    ShortfallKernel,
    compose_evidence,
    fingerprint,
    scrub_lineage,
    source_fingerprints,
)

__all__ = [
    "ABSENCE_POLICY",
    "LOCK_POLICY",
    "MAX_ABSENCE_SETS",
    "NO_XI_BY_PROOF",
    "STRESS_CLAIM",
    "STRESS_NON_CLAIM",
    "STRESS_VERSION",
    "AbsenceSetValue",
    "AbsenceStressResult",
    "StressCertificate",
    "StressLevel",
    "UnfieldableCore",
    "absence_stress",
    "why_no_xi",
]

STRESS_VERSION = "exhaustive-k-absence-stress-v1"
LOCK_POLICY = "LOCKS_NOT_REMOVABLE"
MAX_ABSENCE_SETS = 5000
ABSENCE_POLICY = "Declared scenario; no absence likelihood is estimated"
STRESS_CLAIM = (
    "If {players} are unavailable, the least declared shortfall this model can reach rises "
    "from {baseline} to {value}. Over all {n} sets of {k} players this is the largest rise "
    "among sets that still leave a fieldable XI; {u} sets leave none. Every set was solved to "
    "proof or inherited from one that was."
)
STRESS_NON_CLAIM = (
    "Unavailability is a scenario you chose. No likelihood of injury or suspension is "
    "estimated, and a player whose absence changes nothing here may matter for everything this "
    "model does not measure."
)
_COMPLETE = (
    "Every inclusion-minimal set of at most {k} player{s} whose absence leaves no fieldable XI "
    "is listed. Larger ones were not searched."
)
# When locks or a declared ``removable`` list keep some players out of the enumeration, the
# sets that contain them were never formed and nothing is said about them.
_COMPLETE_AMONG = (
    "Every inclusion-minimal set of at most {k} of the {n} removable player{s} whose absence "
    "leaves no fieldable XI is listed. Sets with any other player, and larger sets, were not "
    "searched."
)
_DEADLINE = (
    "{n} absence set{s} not resolved within {t} s. The largest certified rise is a lower "
    "bound on the worst case, and more sets may leave no fieldable XI. Unknown is not evidence "
    "either way."
)
NO_XI_BY_PROOF = (
    "No XI satisfies the eligibility rules, the measurements, the exclusions and the locks "
    "together."
)
_SOURCES = ("stress.py", "kernel.py", "../xi/domain.py")

Pair = tuple[int, int]
Ids = tuple[int, ...]


def why_no_xi(value: KernelValue) -> str:
    """Why a squad with nobody placed has no XI, in a sentence a person reads.

    A reason the kernel reached by counting names a slot or a player and is passed on. When
    no count shows it and a solve proved it, the kernel's own sentence lists every
    declaration a call can make, placements ("pins") among them. The squad's value places
    nobody, so the sentence here names what was declared and nothing else.
    """
    return NO_XI_BY_PROOF if value.solves else " ".join(value.reasons)


@dataclass(frozen=True)
class AbsenceSetValue:
    """The least declared shortfall without one set of players, or that no XI is left."""

    player_ids: Ids
    status: str  # SHORTFALL_CERTIFIED | UNFIELDABLE | UNKNOWN
    integer_vector: Pair | None  # (maximum, total) in units of 1 / quantization
    objective_vector: tuple[float, float] | None
    change_from_baseline: tuple[float, float] | None  # componentwise; the pair is compared
    # lexicographically, so the second component can fall while the first rises
    resolution: str  # SOLVED | INHERITED_VALUE | INHERITED_UNFIELDABLE | NOT_REACHED | UNDECIDED
    inherited_from: Ids | None  # the subset whose proof covers this set


@dataclass(frozen=True)
class UnfieldableCore:
    """A set that leaves no XI and has no proper subset that does, with a countable reason."""

    player_ids: Ids
    cause: str  # SLOT_COVER, always (see the module docstring)
    blocking_slot_ids: tuple[str, ...]  # fewer remaining players than these slots
    remaining_ids: Ids  # the players still available to that slot group


@dataclass(frozen=True)
class StressLevel:
    """All sets of exactly ``k`` removable players."""

    k: int
    set_count: int
    certified_count: int
    unfieldable_count: int  # proven; "at least" when completeness is DEADLINE
    unknown_count: int
    positive_change_count: int  # certified sets whose value is above the baseline
    worst_integer: Pair | None  # None unless unknown_count == 0 and certified_count > 0
    worst_objective: tuple[float, float] | None
    worst_sets: tuple[Ids, ...]  # every tie, in player_id order; () when worst_integer is None
    certified_lower_bound_integer: Pair | None  # largest certified value, at any completeness
    certified_lower_bound: tuple[float, float] | None
    minimal_unfieldable: tuple[UnfieldableCore, ...]  # proven cores of size exactly k, sorted
    completeness: str  # EXACT | DEADLINE
    claim: str


@dataclass(frozen=True)
class StressCertificate:
    baseline_status: str
    baseline_integer: Pair | None
    removable_ids: Ids
    lock_policy: str
    solves: int
    sets_solved: int
    sets_inherited_value: int
    sets_inherited_unfieldable: int
    completeness: str  # EXACT | DEADLINE | MODEL_INVALID
    elapsed_seconds: float
    quantization: int
    shortfall_policy: str
    time_limit: float
    per_solve_deterministic_limit: float


@dataclass(frozen=True)
class AbsenceStressResult:
    formation: str
    k: int
    baseline_objective: tuple[float, float] | None
    levels: tuple[StressLevel, ...]  # k = 1 .. requested k; () without a certified baseline
    single_absences: tuple[AbsenceSetValue, ...]  # level 1 in full, ordered by player_id
    table: tuple[AbsenceSetValue, ...]  # every set, ordered by (size, ids); () unless asked
    omitted: tuple[dict, ...]  # passed through from the caller; shown beside every number
    certificate: StressCertificate
    evidence: dict
    locked: Ids
    excluded: Ids
    warnings: tuple[str, ...]
    claim: str  # the claim of the requested level
    non_claim: str
    completeness_statement: str | None  # None unless every level is EXACT
    provenance: dict


@dataclass(frozen=True)
class _Entry:
    status: str
    integers: Pair | None
    lineup_ids: frozenset[int]
    resolution: str
    inherited_from: Ids | None
    solves: int = 0
    model_invalid: bool = False


def _ids(values: Sequence[int], known: frozenset[int], name: str) -> Ids:
    values = tuple(values)
    if any(type(pid) is not int for pid in values):
        raise ValueError(f"{name} player IDs must be integers")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} player IDs must be unique")
    unknown = set(values) - known
    if unknown:
        raise ValueError(f"unknown {name} player IDs: {sorted(unknown)}")
    return tuple(sorted(values))


def _floats(integers: Pair | None, quantization: int) -> tuple[float, float] | None:
    return None if integers is None else (integers[0] / quantization, integers[1] / quantization)


def _from_kernel(value: KernelValue) -> _Entry:
    if value.status == "CERTIFIED":
        return _Entry(
            "SHORTFALL_CERTIFIED",
            (value.maximum, value.total),
            frozenset(pid for _, pid in value.lineup),
            "SOLVED",
            None,
            value.solves,
        )
    if value.status == "UNFIELDABLE":
        return _Entry("UNFIELDABLE", None, frozenset(), "SOLVED", None, value.solves)
    # Undecided is never a value and never a proof that no XI exists.
    return _Entry(
        "UNKNOWN",
        None,
        frozenset(),
        "UNDECIDED" if value.solves else "NOT_REACHED",
        None,
        value.solves,
        value.status == "MODEL_INVALID",
    )


def _phrase(integers: Pair, quantization: int) -> str:
    """A certified pair as every sentence of the labs prints one: written out, never rounded
    a second time and never in exponent notation."""
    maximum, total = _floats(integers, quantization)
    return f"(largest {format_plain(maximum)}, sum {format_plain(total)})"


def _listed(names: Sequence[str]) -> str:
    """Names as a list in a sentence: "A", "A and B", "A, B and C"."""
    *first, last = names
    return f"{', '.join(first)} and {last}" if first else last


def _level_claim(
    level_k: int,
    count: int,
    unfieldable: int,
    unknown: int,
    worst: Pair | None,
    worst_sets: Sequence[Ids],
    baseline: Pair,
    names: Mapping[int, str],
    quantization: int,
    scope: str = "",
) -> str:
    """The claim of one level in words. Each branch says only what was proven."""
    sets = (
        f"{count} set{'s' if count != 1 else ''} of {level_k} player{'s' * (level_k != 1)}"
        f"{scope}"
    )
    proof = "Every set was solved to proof or inherited from one that was."
    none_left = (
        f"{unfieldable} set{' leaves' if unfieldable == 1 else 's leave'} no fieldable XI"
    )
    if unknown:
        return (
            f"{unknown} of the {sets} {'was' if unknown == 1 else 'were'} not resolved, so no "
            "worst case is stated. "
            f"At least {unfieldable} leave{'s' if unfieldable == 1 else ''} no fieldable XI."
        )
    if worst is None:
        every = f"The {sets} leaves" if count == 1 else f"All {sets} leave"
        return f"{every} no fieldable XI in this model. {proof}"
    if worst == baseline:
        return (
            f"No set among the {sets} that still leaves a fieldable XI raises the least declared "
            f"shortfall above {_phrase(baseline, quantization)}; {none_left}. {proof}"
        )
    listed = [_listed([names[pid] for pid in ids]) for ids in worst_sets]
    if len(listed) == 1:
        subject = f"If {listed[0]} {'is' if level_k == 1 else 'are'} unavailable"
    else:
        subject = f"If any one of these {len(listed)} sets is unavailable ({'; '.join(listed)})"
    return (
        f"{subject}, the least declared shortfall this model can reach rises from "
        f"{_phrase(baseline, quantization)} to {_phrase(worst, quantization)}. Over all {sets} "
        f"this is the largest rise among sets that still leave a fieldable XI; {none_left}. "
        f"{proof}"
    )


def absence_stress(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    k: int = 2,
    allow_k3: bool = False,
    removable: Sequence[int] | None = None,
    locked: Sequence[int] = (),
    excluded: Sequence[int] = (),
    lock_policy: str = LOCK_POLICY,
    include_table: bool = True,
    omitted: Sequence[Mapping] = (),
    seed: int = 20260906,
    time_limit: float = 60.0,
    quantization: int = QUANTIZATION,
    provenance: Mapping | None = None,
    _inherit: bool = True,
) -> AbsenceStressResult:
    """Every set of 1..k absences, each certified, inherited from a proof, or UNKNOWN.

    ``excluded`` are declared departures and apply to every set. ``locked`` players must be
    fielded and are never removable. ``removable`` narrows the players whose absence is
    enumerated; the default is every candidate that is neither excluded nor locked.
    ``k = 3`` needs ``allow_k3=True``. ``_inherit=False`` solves every set directly (tests).
    """
    started = time.monotonic()
    if type(k) is not int or k not in (1, 2, 3):
        raise ValueError("k must be 1, 2 or 3")
    if type(allow_k3) is not bool or type(include_table) is not bool:
        raise ValueError("allow_k3 and include_table are true or false")
    if k == 3 and not allow_k3:
        raise ValueError("k = 3 must be requested explicitly")
    if lock_policy != LOCK_POLICY:
        raise ValueError(
            f"lock_policy must be {LOCK_POLICY}: a locked player is not removable in a stress test"
        )
    if (
        isinstance(time_limit, bool)
        or not isinstance(time_limit, (int, float))
        or not math.isfinite(time_limit)
        or time_limit <= 0
    ):
        raise ValueError("time_limit must be a positive number of seconds")
    kernel = ShortfallKernel(candidates, requirements, formation, quantization=quantization,
                             seed=seed)
    shape = FORMATIONS[formation] if isinstance(formation, str) else formation
    players = sorted(candidates, key=lambda player: player.player_id)
    active = [r for r in sorted(requirements, key=lambda r: r.requirement_id) if r.active]
    if any(r.hard for r in active):
        raise ValueError(
            "shortfall values treat every active requirement as soft; "
            "use satisfiable() for hard statements"
        )
    names = {player.player_id: player.name for player in players}
    known = frozenset(names)
    excluded_ids = _ids(excluded, known, "excluded")
    locked_ids = _ids(locked, known, "locked")
    pool = tuple(pid for pid in sorted(known) if pid not in excluded_ids and pid not in locked_ids)
    if removable is not None:
        chosen = _ids(removable, known, "removable")
        if set(chosen) - set(pool):
            raise ValueError("removable players must be candidates neither excluded nor locked")
        pool = chosen
    if k > len(pool):
        raise ValueError("k exceeds the number of removable players")
    if math.comb(len(pool), k) > MAX_ABSENCE_SETS:
        raise ValueError("too many absence sets for exhaustive certification")
    # Locks or a declared ``removable`` list leave some remaining players out of every set.
    narrowed = len(pool) < len(known) - len(excluded_ids)
    scope = (
        f" drawn from the {len(pool)} removable player{'s' * (len(pool) != 1)}" if narrowed else ""
    )
    omitted_rows = tuple(dict(row) for row in omitted)
    contract = kernel.input_contract
    here = Path(__file__).parent
    solver_package_version = version("ortools")
    input_fingerprint = fingerprint(
        {
            "version": STRESS_VERSION,
            "input_contract": contract,
            "k": k,
            "allow_k3": allow_k3,
            "removable": None if removable is None else list(pool),
            "locked": list(locked_ids),
            "excluded": list(excluded_ids),
            "lock_policy": lock_policy,
            "include_table": include_table,
            "seed": seed,
            "time_limit": time_limit,
            "quantization": quantization,
            "shortfall_policy": SHORTFALL_POLICY,
            "source_fingerprints": source_fingerprints(*(str(here / name) for name in _SOURCES)),
            "source_provenance": dict(provenance or {}),
            "solver_package_version": solver_package_version,
        }
    )

    deadline = started + time_limit
    base = kernel.value(excluded=excluded_ids, locked=locked_ids, deadline=deadline)
    baseline = (base.maximum, base.total) if base.status == "CERTIFIED" else None
    table: dict[Ids, _Entry] = {}
    warnings: list[str] = []
    if baseline is not None:
        table[()] = _from_kernel(base)
        for size in range(1, k + 1):
            for absent in itertools.combinations(pool, size):
                # Every set has the same locks, so each subset one player smaller is a parent:
                # its XIs include this set's XIs.
                parents = [
                    tuple(pid for pid in absent if pid != dropped) for dropped in absent
                ] if _inherit else []
                entry = None
                for parent in parents:
                    if table[parent].status == "UNFIELDABLE":
                        entry = _Entry("UNFIELDABLE", None, frozenset(), "INHERITED_UNFIELDABLE",
                                       parent)
                        break
                if entry is None:
                    for parent in parents:
                        known_parent = table[parent]
                        if (
                            known_parent.status == "SHORTFALL_CERTIFIED"
                            and not set(absent) & known_parent.lineup_ids
                        ):
                            # The parent's certified XI is still an XI here, and no XI here
                            # can do better than the parent's least value.
                            entry = _Entry("SHORTFALL_CERTIFIED", known_parent.integers,
                                           known_parent.lineup_ids, "INHERITED_VALUE", parent)
                            break
                if entry is None:
                    if time.monotonic() >= deadline:
                        entry = _Entry("UNKNOWN", None, frozenset(), "NOT_REACHED", None)
                    else:
                        entry = _from_kernel(
                            kernel.value(
                                excluded=(*excluded_ids, *absent),
                                locked=locked_ids,
                                deadline=deadline,
                            )
                        )
                table[absent] = entry

    def public(ids: Ids) -> AbsenceSetValue:
        entry = table[ids]
        change = None
        if entry.integers is not None:
            change = (
                (entry.integers[0] - baseline[0]) / quantization,
                (entry.integers[1] - baseline[1]) / quantization,
            )
        return AbsenceSetValue(
            ids,
            entry.status,
            entry.integers,
            _floats(entry.integers, quantization),
            change,
            entry.resolution,
            entry.inherited_from,
        )

    # Who can fill which slot once the declared departures are gone: the kernel's own rule.
    cover = {
        slot.slot_id: frozenset(
            player.player_id
            for player in players
            if player.player_id not in excluded_ids
            and _eligible(player, slot)
            and all(
                player.values.get(r.metric) is not None
                for r in active
                if _applies(r, slot.slot_id)
            )
        )
        for slot in shape.slots
    }
    slot_ids = [slot.slot_id for slot in shape.slots]

    def core(ids: Ids) -> UnfieldableCore:
        gone = set(ids)
        for size in range(1, len(slot_ids) + 1):
            for group in itertools.combinations(slot_ids, size):
                remaining = set().union(*(cover[sid] for sid in group)) - gone
                if len(remaining) < size:
                    return UnfieldableCore(ids, "SLOT_COVER", group, tuple(sorted(remaining)))
        raise RuntimeError("an unfieldable set has no slot group short of players")

    levels = []
    for size in range(1, k + 1) if baseline is not None else ():
        sets = [ids for ids in table if len(ids) == size]
        certified = [ids for ids in sets if table[ids].status == "SHORTFALL_CERTIFIED"]
        unfieldable = [ids for ids in sets if table[ids].status == "UNFIELDABLE"]
        unknown = len(sets) - len(certified) - len(unfieldable)
        bound = max((table[ids].integers for ids in certified), default=None)
        worst = bound if not unknown else None
        worst_sets = (
            tuple(ids for ids in certified if table[ids].integers == worst)
            if worst is not None
            else ()
        )
        cores = tuple(
            core(ids)
            for ids in unfieldable
            # A core needs every proper non-empty subset proven to leave an XI.
            if all(
                table[subset].status == "SHORTFALL_CERTIFIED"
                for smaller in range(1, size)
                for subset in itertools.combinations(ids, smaller)
            )
        )
        levels.append(
            StressLevel(
                k=size,
                set_count=len(sets),
                certified_count=len(certified),
                unfieldable_count=len(unfieldable),
                unknown_count=unknown,
                positive_change_count=sum(table[ids].integers > baseline for ids in certified),
                worst_integer=worst,
                worst_objective=_floats(worst, quantization),
                worst_sets=worst_sets,
                certified_lower_bound_integer=bound,
                certified_lower_bound=_floats(bound, quantization),
                minimal_unfieldable=cores,
                completeness="DEADLINE" if unknown else "EXACT",
                claim=_level_claim(size, len(sets), len(unfieldable), unknown, worst, worst_sets,
                                   baseline, names, quantization, scope),
            )
        )

    entries = [entry for ids, entry in table.items() if ids]
    unresolved = sum(entry.status == "UNKNOWN" for entry in entries)
    model_invalid = base.status == "MODEL_INVALID" or any(e.model_invalid for e in entries)
    elapsed = time.monotonic() - started
    if base.status == "UNFIELDABLE":
        warnings.append(
            "The squad has no fieldable XI in this model before any absence, so no absence set "
            "was evaluated. The slot depth of the squad explains why. " + why_no_xi(base)
        )
    elif base.status == "MODEL_INVALID":
        warnings.append(
            "The solver rejected the model of the squad without any absence, so no absence set "
            "was evaluated. Nothing is known either way."
        )
    elif baseline is None:
        warnings.append(
            "The squad without any absence was not decided within the time limit, so no absence "
            "set was evaluated. Unknown is not evidence either way."
        )
    if unresolved:
        warnings.append(
            _DEADLINE.format(
                n=unresolved, s=" was" if unresolved == 1 else "s were", t=f"{time_limit:g}"
            )
        )
    if model_invalid and baseline is not None:
        warnings.append(
            "The solver rejected a model; the affected sets are reported as not resolved."
        )
    if any(level.unfieldable_count for level in levels):
        causes = ("the evidence gate, the eligibility rules and the exclusions declared here"
                  if excluded_ids else "the evidence gate and the eligibility rules")
        warnings.append(
            f"Sets that leave no fieldable XI reflect {causes}, not the real squad; the "
            "omitted players are listed beside this result."
        )
    exact = baseline is not None and not unresolved and not model_invalid
    if base.status == "UNFIELDABLE":
        completeness = "EXACT"  # a proof: nothing was left to enumerate
    else:
        completeness = "MODEL_INVALID" if model_invalid else "EXACT" if exact else "DEADLINE"
    certificate = StressCertificate(
        baseline_status=base.status,
        baseline_integer=baseline,
        removable_ids=pool,
        lock_policy=lock_policy,
        solves=base.solves + sum(entry.solves for entry in entries),
        sets_solved=sum(entry.resolution == "SOLVED" for entry in entries),
        sets_inherited_value=sum(entry.resolution == "INHERITED_VALUE" for entry in entries),
        sets_inherited_unfieldable=sum(
            entry.resolution == "INHERITED_UNFIELDABLE" for entry in entries
        ),
        completeness=completeness,
        elapsed_seconds=elapsed,
        quantization=quantization,
        shortfall_policy=SHORTFALL_POLICY,
        time_limit=float(time_limit),
        per_solve_deterministic_limit=contract["per_solve_deterministic_limit"],
    )
    evidence = compose_evidence(requirements)
    evidence["binding"] = [
        *(rid for rid, name in evidence["per_requirement"].items() if name == evidence["composed"]),
        *(["eligibility"] if evidence["eligibility"] == evidence["composed"] else []),
    ]
    evidence["declared_inputs"] = [
        {"name": "k", "value": k},
        {"name": "allow_k3", "value": allow_k3},
        {"name": "removable", "value": None if removable is None else list(pool)},
        {"name": "locked", "value": list(locked_ids)},
        {"name": "excluded", "value": list(excluded_ids)},
        {"name": "lock_policy", "value": lock_policy},
        {"name": "minimums", "value": {r.requirement_id: r.minimum for r in active}},
    ]
    if levels:
        claim = levels[-1].claim
    elif base.status == "UNFIELDABLE":
        claim = "No XI can be fielded in this model before any absence."
    else:
        claim = "Nothing is claimed: the squad without any absence was not decided."
    return AbsenceStressResult(
        formation=shape.formation_id,
        k=k,
        baseline_objective=_floats(baseline, quantization),
        levels=tuple(levels),
        single_absences=tuple(public(ids) for ids in table if len(ids) == 1),
        table=tuple(public(ids) for ids in table if ids) if include_table else (),
        omitted=omitted_rows,
        certificate=certificate,
        evidence=evidence,
        locked=locked_ids,
        excluded=excluded_ids,
        warnings=tuple(warnings),
        claim=claim,
        non_claim=STRESS_NON_CLAIM,
        completeness_statement=(
            (_COMPLETE_AMONG if narrowed else _COMPLETE).format(
                k=k, n=len(pool), s="s" * ((len(pool) if narrowed else k) != 1)
            )
            if exact
            else None
        ),
        provenance={
            **scrub_lineage(provenance),
            "stress_version": STRESS_VERSION,
            "kernel_version": KERNEL_VERSION,
            "solver_package_version": solver_package_version,
            "decision_claim": STRESS_CLAIM,
            "absence_policy": ABSENCE_POLICY,
            "lock_policy": lock_policy,
            "shortfall_policy": SHORTFALL_POLICY,
            "quantization": quantization,
            "input_fingerprint": input_fingerprint,
        },
    )
