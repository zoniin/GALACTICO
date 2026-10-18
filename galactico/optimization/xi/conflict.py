"""A certified minimal set of declarations that cannot all hold together, when no XI exists.

Claim: when the declared model has no XI, a set of the reader's declarations (slot coverage,
exclusions, requirement floors, locks) that no assignment meets, such that leaving out any one
member lets the others in the set hold together when every declaration outside the set is also
set aside. Each member that is said to be needed carries the assignment that shows it, and each
member carries a separate restore test: with every other declaration kept, does dropping this
one alone leave an XI. Non-claim: the set is one such set, found in a declared order; it is not
chosen to be the smallest by count, and when more than one exists another order can return
another. Dropping a member from everything declared may still leave no XI. Eligibility, the
minutes gate and missing measurements are part of the model and are never offered for removal,
and nothing was relaxed in the solve this explains. UNKNOWN and NOT_RUN are never evidence that
a member is needed or that a set is satisfiable.

Arithmetic, named by the function (OR-XI-SPEC 1.2, X2). ``explain_solve`` explains XI Lab's own
solve in its arithmetic: every requirement that is hard, or every one under Satisfy, is a floor
at its minimum, compared as ``solve_xi`` compares it (``_q`` coefficients and target, half-even
after a float division). ``explain_floors`` explains a hard-floor query in the conservative
arithmetic of ``kernel.satisfiable`` (floor each rate, ceil each floor). Half-even infeasibility
implies conservative infeasibility, not the converse, so each reply names its arithmetic.

The model (3.2). One Boolean per admissible key, the keys built with exclusions *not* applied
(an exclusion is a declaration here), at most one player per slot and one slot per player as
the background, and one Boolean ``a_c`` per declaration enforcing it. A test of a set ``T``
fixes ``a_c`` to whether ``c`` is in ``T``. The deletion filter (3.3): the whole set is tested
first; then each declaration in the deletion order is dropped from the current set if the rest
is still infeasible, and kept with a witness otherwise. The current set is never satisfiable,
the last test that dropped a member proved the final set, and each kept member's witness meets
the final set without it, so every proper subset is satisfiable. A refused or undecided filter
test keeps its member, unproved. A restore test then solves everything declared but one member.
"""

from __future__ import annotations

import math
import time
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from ortools.sat.python import cp_model

from ..squad.kernel import (
    HARD_POLICY,
    KERNEL_VERSION,
    PER_SOLVE_DETERMINISTIC_LIMIT,
    SHORTFALL_POLICY,
    Lineup,
    ShortfallKernel,
    fingerprint,
    scrub_lineage,
    source_fingerprints,
)
from .ceilings import _Calls, _refuse_hard, _validated_floors
from .domain import FORMATIONS, Candidate, Formation, Slot, TacticalRequirement
from .solver import QUANTIZATION, _applies, _q
from .tradeoffs import MAX_EXPRESSION_MAGNITUDE, MAX_MAGNITUDE, _scaled

__all__ = [
    "ARITHMETICS",
    "CONFLICT_CLAIM",
    "CONFLICT_FEASIBLE",
    "CONFLICT_MODEL_INVALID",
    "CONFLICT_NON_CLAIM",
    "CONFLICT_NOT_DECIDED",
    "CONFLICT_NOT_PROVEN_CLAIM",
    "CONFLICT_VERSION",
    "DELETION_ORDER",
    "FAMILIES",
    "MODE_ERROR",
    "ConflictCertificate",
    "ConflictLineup",
    "Declaration",
    "DeletionTest",
    "MinimalConflict",
    "RestoreTest",
    "explain_floors",
    "explain_solve",
]

CONFLICT_VERSION = "deletion-filter-conflict-v1"
FAMILIES = ("SLOT_COVERAGE", "EXCLUSION", "REQUIREMENT_FLOOR", "LOCK")  # the deletion order
ARITHMETICS = ("SOLVE_HALF_EVEN", "HARD_FLOOR_CONSERVATIVE")  # explain_solve, explain_floors
DELETION_ORDER = (
    "slot coverage in formation order, then exclusions, requirement floors "
    "and locks, each by ascending id"
)
ConflictLineup = tuple[tuple[str, int | None], ...]  # None: the slot is empty

# The served claims (OR-XI-SPEC 7.7). The status selects one (3.4, "Status rules").
CONFLICT_CLAIM = (
    "These declarations cannot all hold together. Leave out any one of them and the others in "
    "this set can hold together, with every declaration outside the set also set aside. That "
    "check leaves out the other declarations: dropping one of these alone may still leave no "
    "XI, and each one says whether it does. This is one such set: when more than one exists, "
    "checking in another order can return another, and this one was not chosen to be the "
    "smallest by count."
)
CONFLICT_NOT_PROVEN_CLAIM = (
    "These declarations cannot all hold together. For a member shown with an assignment, "
    "leaving it out lets the others in this set hold together, with every declaration outside "
    "the set also set aside; for at least one member that was not decided within the search "
    "limits, or the solver refused the check, so this set may not be minimal. Dropping one of "
    "these alone, with the other declarations kept, may still leave no XI, and each one says "
    "whether it does."
)
CONFLICT_NOT_DECIDED = (
    "Whether these declarations can all hold together was not decided within the search "
    "limits. No set is implied."
)
CONFLICT_MODEL_INVALID = (
    "The solver refused the model of these declarations, so whether they can all hold "
    "together was not decided. No set is implied."
)
CONFLICT_FEASIBLE = (
    "Every declaration holds in at least one XI, so there is nothing to explain; one such XI "
    "is shown."
)
CONFLICT_NON_CLAIM = (
    "Eligibility rules, the minutes gate and missing measurements are part of the model and "
    "are never offered for removal. Nothing was relaxed in the solve this explains."
)
MODE_ERROR = "mode must be BALANCE or SATISFY"  # solve_xi's own sentence (solver.py:118-119)

_SOURCES = (
    "conflict.py", "ceilings.py", "../squad/kernel.py", "solver.py", "tradeoffs.py", "domain.py"
)
_WITNESS = ("OPTIMAL", "FEASIBLE")
_PREFIX = {
    "SLOT_COVERAGE": "slot",
    "EXCLUSION": "exclusion",
    "REQUIREMENT_FLOOR": "floor",
    "LOCK": "lock",
}


@dataclass(frozen=True)
class Declaration:
    constraint_id: str  # slot:lb | exclusion:3322 | floor:progression | lock:3563
    family: str
    subject: str  # slot_id, player_id as text, or requirement_id
    raw_floor: float | None  # floors only: the floor as declared
    integer_target: int | None  # floors only: t in the named arithmetic


@dataclass(frozen=True)
class DeletionTest:
    constraint_id: str
    status: str  # status of the test, or NOT_RUN
    # DROPPED | KEPT_WITNESS | KEPT_UNDECIDED | KEPT_REFUSED (status MODEL_INVALID) | NOT_RUN
    outcome: str
    # KEPT_WITNESS only: an assignment meeting final − {c}; () otherwise (the two lists below
    # too). Not an XI: slots may be empty and a player whose exclusion lies outside
    # final − {c} may appear
    witness: ConflictLineup
    witness_excluded_players: tuple[int, ...]  # excluded players the witness uses
    witness_missing_locked_players: tuple[int, ...]  # locked players the witness leaves out


@dataclass(frozen=True)
class RestoreTest:
    constraint_id: str  # a member of the final set
    status: str  # status of the test of all − {c}; NOT_RUN; or NOT_APPLICABLE (slot coverage)
    # True: an XI meets every other declaration; False: none does; None: not decided or not
    # applicable
    restores_alone: bool | None
    witness: Lineup  # True only: that XI; () otherwise


@dataclass(frozen=True)
class ConflictCertificate:
    arithmetic: str
    rounding_policy: str  # kernel.SHORTFALL_POLICY or kernel.HARD_POLICY
    quantization: int
    initial_status: str  # the test of every declaration (s0)
    final_set_proof_solve: int | None  # index in statuses of the solve proving the final set
    # members_with_witness + members_undecided + members_refused == len(conflict)
    members_with_witness: int  # KEPT_WITNESS
    members_undecided: int  # KEPT_UNDECIDED and NOT_RUN
    members_refused: int  # KEPT_REFUSED
    witnesses_verified: bool
    solves: int  # CP-SAT calls actually made
    # s0, then one per filter test in deletion order, then one per restore test that is not
    # NOT_APPLICABLE, in call order; NOT_RUN for a test the deadline skipped
    statuses: tuple[str, ...]
    per_solve_deterministic_limit: float
    deletion_order: str
    completeness: str  # EXACT | LIMIT_REACHED | DEADLINE | MODEL_INVALID
    stopped_by: str | None


@dataclass(frozen=True)
class MinimalConflict:
    # MINIMAL_CERTIFIED | NOT_PROVEN_MINIMAL | MODEL_FEASIBLE | UNDECIDED | MODEL_INVALID
    status: str
    requirements_in_force: tuple[str, ...]  # R, requirement_id ascending
    declarations: tuple[Declaration, ...]  # all of them, deletion order
    conflict: tuple[str, ...]  # constraint ids of the set, deletion order; () unless certified
    tests: tuple[DeletionTest, ...]  # filter rows, deletion order; () unless the filter ran
    restore_tests: tuple[RestoreTest, ...]  # one per member of the set, deletion order
    feasible_witness: Lineup  # MODEL_FEASIBLE: an XI meeting every declaration
    certificate: ConflictCertificate
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    claim: str  # the constant the status selects, word for word
    non_claim: str  # CONFLICT_NON_CLAIM, word for word
    provenance: dict


@dataclass(frozen=True)
class _Floor:
    requirement: TacticalRequirement
    value: float  # φ_r, as declared
    coefficients: dict[tuple[int, str], int]  # over keys at the slots where r applies
    target: int


class _Model:
    """The CP-SAT model of 3.2 and the checks every witness passes without the solver."""

    def __init__(
        self,
        slots: Sequence[Slot],
        keys: Sequence[tuple[int, str]],
        vectors: Mapping[int, Mapping[str, float | None]],
        declarations: Sequence[Declaration],
        floors: Mapping[str, _Floor],
        conservative: bool,
    ) -> None:
        self.slots = tuple(slots)
        self.keys = frozenset(keys)
        self.vectors = vectors
        self.floors = floors
        self.conservative = conservative
        self.model = cp_model.CpModel()
        self.variables = {key: self.model.new_bool_var(f"p{key[0]}_{key[1]}") for key in keys}
        by_slot: dict[str, list[cp_model.IntVar]] = {slot.slot_id: [] for slot in self.slots}
        by_player: dict[int, list[cp_model.IntVar]] = {}
        for (pid, sid), variable in self.variables.items():
            by_slot[sid].append(variable)
            by_player.setdefault(pid, []).append(variable)
        # The background, never deleted: one player per slot, one slot per player.
        for group in (*by_slot.values(), *by_player.values()):
            if len(group) > 1:
                self.model.add(sum(group) <= 1)
        self.active: dict[str, cp_model.IntVar] = {}
        for index, declaration in enumerate(declarations):
            literal = self.model.new_bool_var(f"declared_{index}")
            self.active[declaration.constraint_id] = literal
            family, subject = declaration.family, declaration.subject
            if family == "SLOT_COVERAGE":
                terms, lower, upper = by_slot[subject], 1, None
            elif family == "EXCLUSION":
                terms, lower, upper = by_player.get(int(subject), []), None, 0
            elif family == "LOCK":
                terms, lower, upper = by_player.get(int(subject), []), 1, None
            else:
                floor = floors[subject]
                terms = [
                    coefficient * self.variables[key]
                    for key, coefficient in floor.coefficients.items()
                ]
                lower, upper = floor.target, None
            if not terms:
                # A constant expression is decided here, the rule of kernel._at_least.
                holds = (lower is None or lower <= 0) and (upper is None or upper >= 0)
                if not holds:
                    self.model.add_bool_or([literal.negated()])
                continue
            expression = sum(terms)
            if lower is not None:
                self.model.add(expression >= lower).only_enforce_if(literal)
            else:
                self.model.add(expression <= upper).only_enforce_if(literal)

    def test(self, tested: Collection[str]) -> cp_model.CpModel:
        """A clone with ``a_c`` fixed to whether ``c`` is tested; no objective."""
        clone = self.model.clone()
        for constraint_id, literal in self.active.items():
            clone.add(literal == int(constraint_id in tested))
        return clone

    def assignment(self, solver: cp_model.CpSolver) -> ConflictLineup:
        chosen = {sid: pid for (pid, sid), var in self.variables.items() if solver.value(var)}
        return tuple((slot.slot_id, chosen.get(slot.slot_id)) for slot in self.slots)

    def holds(self, assignment: ConflictLineup, tested: Collection[str]) -> bool:
        """Every declaration of ``tested`` holds for ``assignment``, checked from scratch."""
        if [sid for sid, _ in assignment] != [slot.slot_id for slot in self.slots]:
            return False
        placed = [pid for _, pid in assignment if pid is not None]
        if len(placed) != len(set(placed)):
            return False
        if any(pid is not None and (pid, sid) not in self.keys for sid, pid in assignment):
            return False
        for constraint_id in tested:
            prefix, subject = constraint_id.split(":", 1)
            if prefix == "slot" and dict(assignment)[subject] is None:
                return False
            if prefix == "exclusion" and int(subject) in placed:
                return False
            if prefix == "lock" and int(subject) not in placed:
                return False
            if prefix == "floor":
                floor = self.floors[subject]
                held = sum(floor.coefficients.get((pid, sid), 0) for sid, pid in assignment)
                if held < floor.target:
                    return False
                if self.conservative:
                    # The conservative integers imply the raw floor exactly, no tolerance.
                    exact = sum(
                        (Fraction(self.vectors[pid][floor.requirement.metric])
                         for sid, pid in assignment
                         if pid is not None and _applies(floor.requirement, sid)),
                        Fraction(),
                    )
                    if exact < Fraction(floor.value):
                        return False
        return True


def _floor(
    requirement: TacticalRequirement,
    value: float,
    keys: Sequence[tuple[int, str]],
    vectors: Mapping[int, Mapping[str, float | None]],
    quantization: int,
    conservative: bool,
) -> _Floor:
    """One floor's coefficients and target in the named arithmetic, with the checks of
    ``kernel._tables`` on every coefficient, the target and the expression."""

    def integer(number: float, *, target: bool) -> int:
        if conservative:
            scaled = _scaled(number, requirement.normalizer, quantization)
            return math.ceil(scaled) if target else math.floor(scaled)
        try:
            return _q(number, requirement.normalizer, quantization)
        except OverflowError as exc:  # the float quotient is infinite
            what = "minimum" if target else "coefficient"
            raise ValueError(f"normalized requirement {what} is too large") from exc

    per_player: dict[int, int] = {}
    coefficients = {}
    for pid, sid in keys:
        if not _applies(requirement, sid):
            continue
        if pid not in per_player:
            per_player[pid] = integer(vectors[pid][requirement.metric], target=False)
            if abs(per_player[pid]) > MAX_MAGNITUDE:
                raise ValueError("normalized requirement coefficient is too large")
        coefficients[pid, sid] = per_player[pid]
    target = integer(value, target=True)
    if abs(target) > MAX_MAGNITUDE:
        raise ValueError("normalized requirement minimum is too large")
    if sum(abs(c) for c in coefficients.values()) >= MAX_EXPRESSION_MAGNITUDE:
        raise ValueError("normalized requirement expression is too large")
    return _Floor(requirement, value, coefficients, target)


def explain_floors(
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
) -> MinimalConflict:
    """Explain a hard-floor query in the conservative arithmetic (``HARD_POLICY``).

    ``floors=None`` floors every requirement in force at its minimum, as
    ``kernel.satisfiable`` and ``maximize_requirement`` do; ``{}`` declares no floor. A
    requirement in force marked hard is refused, as the ceilings tool refuses it: floors are
    the only hard declarations here.
    """
    deadline = ShortfallKernel._deadline(deadline)
    requirements = tuple(requirements)
    active = sorted((r for r in requirements if r.active), key=lambda r: r.requirement_id)
    if floors is None:
        declared = {r.requirement_id: r.minimum for r in active}
    else:
        declared = _validated_floors(active, floors)
    _refuse_hard(active)
    return _explain(
        candidates, requirements, formation, active, declared, "HARD_FLOOR_CONSERVATIVE", None,
        locked, excluded, seed, quantization, deadline, provenance,
    )


def explain_solve(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    mode: str,
    locked: Collection[int] = (),
    excluded: Collection[int] = (),
    seed: int = 20260906,
    quantization: int = QUANTIZATION,
    deadline: float,
    provenance: Mapping | None = None,
) -> MinimalConflict:
    """Explain ``solve_xi(mode=mode)`` in its own half-even arithmetic (``SHORTFALL_POLICY``).

    The floors are the minima ``solve_xi`` enforces (solver.py:274-275): every requirement in
    force that is hard, and every one under ``SATISFY``. Under ``BALANCE`` with no hard
    requirement no floor is declared and only places, exclusions and locks are checked.
    """
    deadline = ShortfallKernel._deadline(deadline)
    if not isinstance(mode, str) or mode not in ("BALANCE", "SATISFY"):
        raise ValueError(MODE_ERROR)
    requirements = tuple(requirements)
    active = sorted((r for r in requirements if r.active), key=lambda r: r.requirement_id)
    declared = {
        r.requirement_id: r.minimum for r in active if r.hard or mode == "SATISFY"
    }
    return _explain(
        candidates, requirements, formation, active, declared, "SOLVE_HALF_EVEN", mode,
        locked, excluded, seed, quantization, deadline, provenance,
    )


def _explain(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation,
    active: Sequence[TacticalRequirement],
    declared: Mapping[str, float],
    arithmetic: str,
    mode: str | None,
    locked: Collection[int],
    excluded: Collection[int],
    seed: int,
    quantization: int,
    deadline: float,
    provenance: Mapping | None,
) -> MinimalConflict:
    # For validation and the input contract only; its background model is never solved,
    # since coverage and exclusions are fixed in it.
    kernel = ShortfallKernel(candidates, requirements, formation, quantization=quantization,
                             seed=seed)
    locked_ids = tuple(sorted(kernel._player_ids(locked, "locked")))
    excluded_ids = tuple(sorted(kernel._player_ids(excluded, "excluded")))
    shape = FORMATIONS[formation] if isinstance(formation, str) else formation
    # Admissible keys with exclusions not applied: eligibility, minutes and the measurement
    # rule over every requirement in force, in formation order, then player id.
    keys_of = kernel._background((), (), None, (), None)
    keys = list(keys_of.variables)
    conservative = arithmetic == "HARD_FLOOR_CONSERVATIVE"
    by_id = {r.requirement_id: r for r in active}
    floors = {
        rid: _floor(by_id[rid], value, keys, keys_of.vectors, quantization, conservative)
        for rid, value in sorted(declared.items())
    }
    declarations = (
        *(Declaration(f"slot:{s.slot_id}", "SLOT_COVERAGE", s.slot_id, None, None)
          for s in shape.slots),
        *(Declaration(f"exclusion:{pid}", "EXCLUSION", str(pid), None, None)
          for pid in excluded_ids),
        *(Declaration(f"floor:{rid}", "REQUIREMENT_FLOOR", rid, floor.value, floor.target)
          for rid, floor in floors.items()),
        *(Declaration(f"lock:{pid}", "LOCK", str(pid), None, None) for pid in locked_ids),
    )
    order = tuple(d.constraint_id for d in declarations)
    family = {d.constraint_id: d.family for d in declarations}
    model = _Model(shape.slots, keys, keys_of.vectors, declarations, floors, conservative)

    sources = source_fingerprints(*(str(Path(__file__).parent / name) for name in _SOURCES))
    rounding = HARD_POLICY if conservative else SHORTFALL_POLICY
    contract = {
        "version": CONFLICT_VERSION,
        "kernel": kernel.input_contract,
        "arithmetic": arithmetic,
        "rounding_policy": rounding,
        "mode": mode,
        "floors": [[rid, floor.value] for rid, floor in floors.items()],
        "locked": list(locked_ids),
        "excluded": list(excluded_ids),
        "deletion_order": DELETION_ORDER,
        "source_fingerprints": sources,
    }
    calls = _Calls(deadline, seed)

    def verified(solver, tested: Collection[str]) -> ConflictLineup:
        assignment = model.assignment(solver)
        if not model.holds(assignment, tested):
            raise RuntimeError("a conflict witness failed its re-evaluation without the solver")
        return assignment

    def finish(status, *, tests=(), restore=(), conflict=(), witness=(), proof=None,
               tokens=None):
        completeness, stopped_by = tokens if tokens is not None else calls.tokens()
        outcomes = {row.constraint_id: row.outcome for row in tests}
        members = [outcomes[c] for c in conflict]
        claim = {
            "MINIMAL_CERTIFIED": CONFLICT_CLAIM,
            "NOT_PROVEN_MINIMAL": CONFLICT_NOT_PROVEN_CLAIM,
            "MODEL_FEASIBLE": CONFLICT_FEASIBLE,
            "UNDECIDED": CONFLICT_NOT_DECIDED,
            "MODEL_INVALID": CONFLICT_MODEL_INVALID,
        }[status]
        record = {
            **scrub_lineage(provenance),
            "conflict_version": CONFLICT_VERSION,
            "kernel_version": KERNEL_VERSION,
            "arithmetic": arithmetic,
            "rounding_policy": rounding,
            "quantization": quantization,
            "per_solve_deterministic_limit": PER_SOLVE_DETERMINISTIC_LIMIT,
            "input_contract": contract,
            "input_fingerprint": fingerprint({"version": CONFLICT_VERSION, "contract": contract}),
            "source_fingerprints": sources,
            # Times are not encodings and enter no hash (1.5); wall times are diagnostic only.
            "conflict_solve_deterministic_times": list(calls.deterministic_times),
            "conflict_solve_wall_times": list(calls.wall_times),
        }
        return MinimalConflict(
            status=status,
            requirements_in_force=tuple(r.requirement_id for r in active),
            declarations=declarations,
            conflict=tuple(conflict),
            tests=tuple(tests),
            restore_tests=tuple(restore),
            feasible_witness=witness,
            certificate=ConflictCertificate(
                arithmetic=arithmetic,
                rounding_policy=rounding,
                quantization=quantization,
                initial_status=calls.statuses[0],
                final_set_proof_solve=proof,
                members_with_witness=members.count("KEPT_WITNESS"),
                members_undecided=members.count("KEPT_UNDECIDED") + members.count("NOT_RUN"),
                members_refused=members.count("KEPT_REFUSED"),
                witnesses_verified=True,
                solves=calls.solves,
                statuses=tuple(calls.statuses),
                per_solve_deterministic_limit=PER_SOLVE_DETERMINISTIC_LIMIT,
                deletion_order=DELETION_ORDER,
                completeness=completeness,
                stopped_by=stopped_by,
            ),
            locked=locked_ids,
            excluded=excluded_ids,
            claim=claim,
            non_claim=CONFLICT_NON_CLAIM,
            provenance=record,
        )

    # s0: every declaration. _Calls records a passed deadline as NOT_RUN without a call.
    name, solver = calls.solve(model.test(order), optimum=False)
    if name in _WITNESS:
        assignment = verified(solver, order)  # every slot covered: an XI
        return finish("MODEL_FEASIBLE", witness=tuple(assignment), tokens=("EXACT", None))
    if name == "MODEL_INVALID":
        return finish("MODEL_INVALID", tokens=("MODEL_INVALID", None))
    if name != "INFEASIBLE":
        return finish("UNDECIDED")

    current = set(order)
    proof = 0
    rows: dict[str, tuple[str, str, ConflictLineup | None]] = {}
    for position, constraint_id in enumerate(order):
        if time.monotonic() < deadline:
            name, solver = calls.solve(model.test(current - {constraint_id}), optimum=False)
        else:
            calls.skip()
            name, solver = "NOT_RUN", None
        if name == "NOT_RUN":
            # This declaration and every later one stay in the set, untested.
            rows[constraint_id] = ("NOT_RUN", "NOT_RUN", None)
            for later in order[position + 1:]:
                calls.skip()
                rows[later] = ("NOT_RUN", "NOT_RUN", None)
            break
        if name == "INFEASIBLE":
            current.discard(constraint_id)
            proof = len(calls.statuses) - 1
            rows[constraint_id] = (name, "DROPPED", None)
        elif name in _WITNESS:
            assignment = verified(solver, current - {constraint_id})
            rows[constraint_id] = (name, "KEPT_WITNESS", assignment)
        elif name == "MODEL_INVALID":
            rows[constraint_id] = (name, "KEPT_REFUSED", None)  # the filter continues
        else:
            rows[constraint_id] = (name, "KEPT_UNDECIDED", None)
    conflict = tuple(c for c in order if c in current)
    tests = []
    for constraint_id in order:
        status, outcome, assignment = rows[constraint_id]
        if assignment is None:
            tests.append(DeletionTest(constraint_id, status, outcome, (), (), ()))
            continue
        # Checked again against exactly final − {c}: what makes the member necessary.
        if not model.holds(assignment, current - {constraint_id}):
            raise RuntimeError("a conflict witness does not meet the final set without it")
        placed = {pid for _, pid in assignment if pid is not None}
        tests.append(
            DeletionTest(
                constraint_id,
                status,
                outcome,
                assignment,
                tuple(pid for pid in excluded_ids if pid in placed),
                tuple(pid for pid in locked_ids if pid not in placed),
            )
        )

    restore = []
    every = frozenset(order)
    for constraint_id in conflict:
        if family[constraint_id] == "SLOT_COVERAGE":  # an XI fills every slot
            restore.append(RestoreTest(constraint_id, "NOT_APPLICABLE", None, ()))
            continue
        if time.monotonic() < deadline:
            name, solver = calls.solve(model.test(every - {constraint_id}), optimum=False)
        else:
            calls.skip()
            name, solver = "NOT_RUN", None
        if name in _WITNESS:
            # It meets every declaration but c, slot coverage included: an XI without c.
            assignment = verified(solver, every - {constraint_id})
            lineup = tuple((sid, pid) for sid, pid in assignment)
            restore.append(RestoreTest(constraint_id, name, True, lineup))
        elif name == "INFEASIBLE":  # another conflict remains
            restore.append(RestoreTest(constraint_id, name, False, ()))
        else:  # UNKNOWN, NOT_RUN or MODEL_INVALID: the set and its status stand
            restore.append(RestoreTest(constraint_id, name, None, ()))
    outcomes = {rows[c][1] for c in conflict}
    status = "MINIMAL_CERTIFIED" if outcomes == {"KEPT_WITNESS"} else "NOT_PROVEN_MINIMAL"
    return finish(status, tests=tests, restore=restore, conflict=conflict, proof=proof)
