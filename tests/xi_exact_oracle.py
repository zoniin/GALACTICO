"""Brute-force oracle for the four exact XI tools: listing and exact fractions, nothing else.

Claim: on a declared problem small enough to list (three to five slots, five to eight
candidates), every XI, every assignment and every world loss that OR-XI-SPEC sections 1 to 5
define, found by enumerating them and comparing exact integers and ``Fraction`` sums: the least
and largest requirement sums of CEILING, the satisfiable sets, deletion filter and restore tests
of CONFLICT, the nondominated integer vectors of FRONTIER, and the optima, level sets, tails,
binding worlds and membership of the risk rules. Each definition is written from the text of
those sections, not from the code it checks, by an author who builds none of the four tools.

Non-claim: a test instrument, not a tool. It answers nothing at real size, certifies nothing a
reader is shown, and its seeded instances are arithmetic on drawn numbers, not football data.
It imports ``itertools``, ``math``, ``fractions`` and ``collections`` and nothing from
``galactico``; candidates, requirements and slots are read by attribute, so the domain
dataclasses and the records below are interchangeable inputs. It forms no encoding of a loss:
pairs are compared as tuples. pytest does not collect it (no ``test_`` name).

Representation. An XI is a ``Lineup``, ``((slot_id, player_id), ...)`` in formation order, the
form the tools return, so a tool's lineup can be passed back in. A CONFLICT assignment is a
``ConflictLineup`` whose empty slots hold ``None``. A value table maps a player id to his metric
values; a player missing from it has every metric ``None``. Worlds map a world id to such a
table. Declarations (locks, exclusions, floors, dimensions, worlds, mode) are passed to every
function explicitly; an ``Instance`` carries the ones its generator drew so a test can pass them
on. Records are typed ``namedtuple`` subclasses: the four permitted modules hold no dataclass.

Arithmetic (section 1.2). ``objective`` is OBJECTIVE_POLICY, ``floor_coef`` and ``ceil_target``
are HARD_POLICY, and ``half_even`` stands in for SHORTFALL_POLICY's ``_q``: exact ``Fraction``
half-even, equal to ``_q`` only where the float division is exact. The generator therefore
draws dyadic numbers for the risk and ``explain_solve`` instances and checks the written-out
float rule against ``half_even`` on every coefficient and target it draws.
"""

from __future__ import annotations

import itertools
import math
from collections import namedtuple
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from fractions import Fraction

__all__ = [
    "ARITHMETICS",
    "DECIMAL_NORMALIZERS",
    "DISCARD_REASON",
    "DYADIC_NORMALIZERS",
    "EXACT_OBJECTIVE_LIMIT",
    "HARD_FLOOR_CONSERVATIVE",
    "KINDS",
    "MODES",
    "POSITIONS",
    "QUANTIZATIONS",
    "SOLVE_HALF_EVEN",
    "CeilingTruth",
    "ConflictLineup",
    "ConflictModel",
    "DomainInputs",
    "FilterRow",
    "FilterTruth",
    "FrontierTruth",
    "Instance",
    "Lineup",
    "OracleCandidate",
    "OracleRequirement",
    "OracleSlot",
    "Pair",
    "RangeTruth",
    "RiskTruth",
    "Satisfiability",
    "SeededInstances",
    "Vectors",
    "Worlds",
    "balance_optimum",
    "binding_of",
    "ceil_target",
    "ceilings",
    "conflict_model",
    "deletion_filter",
    "dominates",
    "domain_inputs",
    "exact_sum",
    "floor_coef",
    "frontier",
    "half_even",
    "instances",
    "loss_pair",
    "membership",
    "minimal_conflicting_sets",
    "nondominated",
    "objective",
    "options",
    "point_loss",
    "point_sums",
    "point_vectors",
    "regret_of",
    "regret_optimum",
    "restores_alone",
    "satisfiable",
    "t_bound",
    "tail_of",
    "tail_optimum",
    "tail_sum_of",
    "used_worlds",
    "world_pairs",
    "world_vector",
    "world_vectors",
    "xis",
]

Lineup = tuple[tuple[str, int], ...]
ConflictLineup = tuple[tuple[str, int | None], ...]
Vectors = Mapping[int, Mapping[str, float | None]]
Worlds = Mapping[int, Mapping[int, Mapping[str, float | None]]]
Pair = tuple[int, int]

POSITIONS = ("DF", "MF", "FW")
QUANTIZATIONS = (100, 1000, 100_000)
DYADIC_NORMALIZERS = (0.5, 1.0, 2.0, 4.0)
DECIMAL_NORMALIZERS = (0.3, 0.7, 1.0, 1.5, 2.5)
KINDS = ("CEILING", "FRONTIER", "CONFLICT_FLOORS", "CONFLICT_SOLVE", "RISK")
SOLVE_HALF_EVEN = "SOLVE_HALF_EVEN"
HARD_FLOOR_CONSERVATIVE = "HARD_FLOOR_CONSERVATIVE"
ARITHMETICS = (SOLVE_HALF_EVEN, HARD_FLOOR_CONSERVATIVE)
MODES = ("BALANCE", "SATISFY")
DISCARD_REASON = "missing shared-world exposure"
EXACT_OBJECTIVE_LIMIT = 2**53


# --------------------------------------------------------------------------- records


class OracleSlot(
    namedtuple("OracleSlot", "slot_id allowed_positions label x y", defaults=("", 0.5, 0.5))
):
    """A formation slot; its field names are ``xi.domain.Slot``'s keyword arguments."""

    __slots__ = ()
    slot_id: str
    allowed_positions: tuple[str, ...]
    label: str
    x: float
    y: float


class OracleCandidate(
    namedtuple(
        "OracleCandidate",
        "player_id position values minutes eligible_slots name",
        defaults=(1, None, ""),
    )
):
    """A candidate; its field names are ``xi.domain.Candidate``'s keyword arguments."""

    __slots__ = ()
    player_id: int
    position: str
    values: Mapping[str, float | None]
    minutes: int
    eligible_slots: tuple[str, ...] | None
    name: str


class OracleRequirement(
    namedtuple(
        "OracleRequirement",
        "requirement_id metric minimum normalizer slot_ids hard label",
        defaults=((), False, ""),
    )
):
    """A requirement in force; its field names are ``TacticalRequirement``'s keyword arguments."""

    __slots__ = ()
    requirement_id: str
    metric: str
    minimum: float
    normalizer: float
    slot_ids: tuple[str, ...]
    hard: bool
    label: str


class Instance(
    namedtuple(
        "Instance",
        "slots candidates requirements quantization kind seed formation_id "
        "locked excluded floors dimensions worlds mode",
        defaults=("HAND", None, "oracle", (), (), None, (), None, None),
    )
):
    """One declared problem: the structure, and the declarations its generator drew.

    ``requirements`` are the requirements in force (section 1.3); a requirement whose
    ``active`` attribute is false is ignored, as the tools ignore it. ``floors`` is a mapping
    (CEILING, FRONTIER, CONFLICT_FLOORS; ``None`` on a CONFLICT_FLOORS instance means every
    requirement at its minimum), ``dimensions`` holds a seeded ordered sample of two and one of
    three requirement ids (FRONTIER), ``worlds`` the world tables (RISK) and ``mode`` the
    decision rule ``explain_solve`` explains (CONFLICT_SOLVE).
    """

    __slots__ = ()
    slots: tuple[OracleSlot, ...]
    candidates: tuple[OracleCandidate, ...]
    requirements: tuple[OracleRequirement, ...]
    quantization: int
    kind: str
    seed: int | None
    formation_id: str
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    floors: Mapping[str, float] | None
    dimensions: tuple[tuple[str, ...], ...]
    worlds: Worlds | None
    mode: str | None


class SeededInstances(
    namedtuple("SeededInstances", "ceiling frontier conflict_floors conflict_solve risk")
):
    """The five instances of one seed, one per kind, each from its own stream."""

    __slots__ = ()
    ceiling: Instance
    frontier: Instance
    conflict_floors: Instance
    conflict_solve: Instance
    risk: Instance


class DomainInputs(namedtuple("DomainInputs", "candidates requirements formation")):
    """An instance rebuilt with the domain classes a test passes in."""

    __slots__ = ()
    candidates: tuple[object, ...]
    requirements: tuple[object, ...]
    formation: object


class RangeTruth(
    namedtuple(
        "RangeTruth",
        "requirement_id applicable_slots allowance minimum largest_integer least_integer "
        "largest_sum least_sum sums minimum_reached minimum_missed",
    )
):
    """Section 2.1 for one requirement over the inner set: ``I+``, ``I-``, ``R+``, ``R-``.

    ``allowance`` is ``e_r = a_r * n_r / (2q)`` and ``sums`` every ``S_r`` (ascending, one per
    XI of the inner set), all exact. ``minimum_reached`` is ``R+ >= m_r`` and
    ``minimum_missed`` is ``R- < m_r``, with ``m_r`` the requirement's own minimum.
    """

    __slots__ = ()
    requirement_id: str
    applicable_slots: int
    allowance: Fraction
    minimum: Fraction
    largest_integer: int
    least_integer: int
    largest_sum: Fraction
    least_sum: Fraction
    sums: tuple[Fraction, ...]
    minimum_reached: bool
    minimum_missed: bool


class CeilingTruth(namedtuple("CeilingTruth", "state xi_count feasible_count feasible ranges")):
    """The inner set of 2.1 and its ranges.

    ``state`` is ``FIELDABLE`` (the inner set holds an XI), ``UNFIELDABLE`` (no XI at all) or
    ``NOT_SATISFIABLE`` (XIs exist and none meets the floors). ``xi_count`` counts every XI,
    ``feasible`` lists the inner set and ``ranges`` is empty when it is.
    """

    __slots__ = ()
    state: str
    xi_count: int
    feasible_count: int
    feasible: tuple[Lineup, ...]
    ranges: tuple[RangeTruth, ...]


class FrontierTruth(
    namedtuple(
        "FrontierTruth", "state dimensions points vectors vector_of raw_of raw_nondominated"
    )
):
    """Section 4.1: every integer vector ``V(x)`` of the inner set and the nondominated ones.

    ``points`` and ``vectors`` are lexicographic-descending in the declared order;
    ``vector_of`` and ``raw_of`` map each XI of the inner set to ``V(x)`` and to its exact sums;
    ``raw_nondominated`` holds the XIs whose exact sums no other XI's dominate. ``state`` is
    read as CEILING's: ``FIELDABLE`` here is the tool's ``FRONTIER``.
    """

    __slots__ = ()
    state: str
    dimensions: tuple[str, ...]
    points: tuple[tuple[int, ...], ...]
    vectors: tuple[tuple[int, ...], ...]
    vector_of: Mapping[Lineup, tuple[int, ...]]
    raw_of: Mapping[Lineup, tuple[Fraction, ...]]
    raw_nondominated: frozenset[Lineup]

    def witnesses(self, point: tuple[int, ...]) -> tuple[Lineup, ...]:
        """Every XI of the inner set whose integer vector is ``point``."""
        return tuple(x for x, vector in self.vector_of.items() if vector == point)


class ConflictModel(
    namedtuple(
        "ConflictModel",
        "arithmetic slot_ids options coefficients applicable targets locked excluded "
        "declarations",
    )
):
    """The declarations of section 3.1 in one arithmetic, over keys that ignore exclusions.

    ``options`` lists per slot the players with an admissible key; ``coefficients`` maps a
    floored requirement id to ``{(slot_index, player_id): c}`` and ``targets`` to its ``t``;
    ``applicable`` holds the slot indexes where it applies; ``declarations`` is every
    constraint id in the deletion order of 3.1.
    """

    __slots__ = ()
    arithmetic: str
    slot_ids: tuple[str, ...]
    options: tuple[tuple[int, ...], ...]
    coefficients: Mapping[str, Mapping[tuple[int, int], int]]
    applicable: Mapping[str, tuple[int, ...]]
    targets: Mapping[str, int]
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    declarations: tuple[str, ...]


class Satisfiability(namedtuple("Satisfiability", "satisfiable witness nodes")):
    """One backtracking test: the answer, the first assignment found, the nodes visited."""

    __slots__ = ()
    satisfiable: bool
    witness: ConflictLineup | None
    nodes: int


class FilterRow(namedtuple("FilterRow", "constraint_id outcome witness")):
    """One filter test of 3.3: ``DROPPED``, or ``KEPT_WITNESS`` with an assignment."""

    __slots__ = ()
    constraint_id: str
    outcome: str
    witness: ConflictLineup | None


class FilterTruth(namedtuple("FilterTruth", "status conflict rows initial_witness nodes")):
    """The deletion filter of 3.3 in a given order.

    ``status`` is ``MODEL_FEASIBLE`` (``initial_witness`` is an XI meeting every
    declaration; no row) or ``MINIMAL_CERTIFIED`` (``conflict`` in the given order, one row per
    declaration). ``nodes`` holds the node count of every test, the initial one first.
    """

    __slots__ = ()
    status: str
    conflict: tuple[str, ...]
    rows: tuple[FilterRow, ...]
    initial_witness: ConflictLineup | None
    nodes: tuple[int, ...]


class RiskTruth(
    namedtuple(
        "RiskTruth",
        "status used_world_ids discarded_world_ids optimum level_set player_sets membership "
        "world_least",
    )
):
    """A risk rule's answer: ``CERTIFIED``, ``UNFIELDABLE`` or ``NOT_EVALUABLE``.

    ``optimum`` is the tail rule's ``(sum of M, sum of T)`` or the regret rule's largest
    ``(M - M*, T - T*)``; ``level_set`` every XI attaining it and ``player_sets`` their player
    sets; ``membership`` one ``(player_id, possible, necessary)`` per candidate, id ascending;
    ``world_least`` the regret rule's ``(world_id, (M*, T*))`` per used world. Each is empty
    (``optimum`` ``None``) unless the rule is ``CERTIFIED``.
    """

    __slots__ = ()
    status: str
    used_world_ids: tuple[int, ...]
    discarded_world_ids: tuple[int, ...]
    optimum: Pair | None
    level_set: tuple[Lineup, ...]
    player_sets: frozenset[frozenset[int]]
    membership: tuple[tuple[int, bool, bool], ...]
    world_least: tuple[tuple[int, Pair], ...]


# --------------------------------------------------------------------------- core


def _in_force(instance: Instance) -> tuple[OracleRequirement, ...]:
    active = (r for r in instance.requirements if getattr(r, "active", True))
    return tuple(sorted(active, key=lambda r: r.requirement_id))


def _candidates(instance: Instance) -> tuple[OracleCandidate, ...]:
    return tuple(sorted(instance.candidates, key=lambda c: c.player_id))


def _eligible(candidate: OracleCandidate, slot: OracleSlot) -> bool:
    return (
        candidate.minutes > 0
        and candidate.position in slot.allowed_positions
        and (candidate.eligible_slots is None or slot.slot_id in candidate.eligible_slots)
    )


def _applies(requirement: OracleRequirement, slot_id: str) -> bool:
    return not requirement.slot_ids or slot_id in requirement.slot_ids


def _player_ids(instance: Instance, ids: Iterable[int]) -> frozenset[int]:
    chosen = frozenset(ids)
    if not chosen <= {c.player_id for c in instance.candidates}:
        raise ValueError("a lock or an exclusion names a player who is not a candidate")
    return chosen


def point_vectors(instance: Instance) -> dict[int, Mapping[str, float | None]]:
    """The candidates' own value tables, by player id."""
    return {c.player_id: c.values for c in instance.candidates}


def options(
    instance: Instance,
    *,
    vectors: Vectors,
    excluded: Collection[int],
    keys_ignore_exclusions: bool = False,
) -> tuple[tuple[int, ...], ...]:
    """Per slot, in formation order, the players with an admissible key (1.1), id ascending.

    A key is admissible when the player is eligible at the slot and every requirement in
    force that applies there is measured in his table. Excluded players are left out unless
    ``keys_ignore_exclusions`` (CONFLICT, where an exclusion is a declaration).
    """
    left_out = frozenset() if keys_ignore_exclusions else _player_ids(instance, excluded)
    requirements = _in_force(instance)
    rows = []
    for slot in instance.slots:
        metrics = [r.metric for r in requirements if _applies(r, slot.slot_id)]
        rows.append(
            tuple(
                c.player_id
                for c in _candidates(instance)
                if c.player_id not in left_out
                and _eligible(c, slot)
                and all(vectors.get(c.player_id, {}).get(m) is not None for m in metrics)
            )
        )
    return tuple(rows)


def xis(
    instance: Instance, *, locked: Collection[int], excluded: Collection[int], vectors: Vectors
) -> tuple[Lineup, ...]:
    """Every XI: ``itertools.product`` over the options, injective, locks in, exclusions out."""
    required = _player_ids(instance, locked)
    slot_ids = tuple(s.slot_id for s in instance.slots)
    found = []
    for players in itertools.product(*options(instance, vectors=vectors, excluded=excluded)):
        chosen = set(players)
        if len(chosen) == len(players) and required <= chosen:
            found.append(tuple(zip(slot_ids, players, strict=True)))
    return tuple(found)


# Each rule is a pure function of (value, normalizer, q) over few distinct draws; remembering
# its integers keeps the enumerations fast without a second definition of any of them.
_ROUNDED: dict[tuple[str, float, float, int], int] = {}


def _rounded(rule: str, value: float, normalizer: float, quantization: int) -> int:
    key = (rule, value, normalizer, quantization)
    if key not in _ROUNDED:
        exact = Fraction(value) / Fraction(normalizer) * quantization
        if rule == "floor":
            _ROUNDED[key] = math.floor(exact)
        elif rule == "ceil":
            _ROUNDED[key] = math.ceil(exact)
        else:
            _ROUNDED[key] = round(exact)
    return _ROUNDED[key]


def objective(v: float, n: float, q: int) -> int:
    """OBJECTIVE_POLICY: ``round(Fraction(v) / Fraction(n) * q)``, half-even on the exact value."""
    return _rounded("half-even", v, n, q)


def floor_coef(v: float, n: float, q: int) -> int:
    """HARD_POLICY coefficient: the floor of the exact scaled value."""
    return _rounded("floor", v, n, q)


def ceil_target(m: float, n: float, q: int) -> int:
    """HARD_POLICY target: the ceiling of the exact scaled minimum."""
    return _rounded("ceil", m, n, q)


def half_even(v: float, n: float, q: int) -> int:
    """The shortfall rule as exact half-even (ROOT 2.6 D8); equal to ``_q`` on dyadic draws."""
    return _rounded("half-even", v, n, q)


def exact_sum(x: ConflictLineup, r: OracleRequirement, vectors: Vectors) -> Fraction:
    """``S_r(x)``: the exact sum of ``r``'s metric over the filled slots where ``r`` applies."""
    total = Fraction(0)
    for slot_id, player in x:
        if player is None or not _applies(r, slot_id):
            continue
        value = vectors.get(player, {}).get(r.metric)
        if value is None:
            raise ValueError("the lineup uses a key whose metric is not measured")
        total += Fraction(value)
    return total


def world_vector(
    instance: Instance, world: Mapping[int, Mapping[str, float | None]], p: int
) -> dict[str, float | None]:
    """``dict(world.get(p, {}))``: whole-vector replacement; an absent player has no value."""
    return dict(world.get(p, {}))


def world_vectors(
    instance: Instance, world: Mapping[int, Mapping[str, float | None]]
) -> dict[int, dict[str, float | None]]:
    """The complete world table of 1.4: one replaced vector for every candidate."""
    return {c.player_id: world_vector(instance, world, c.player_id) for c in instance.candidates}


def used_worlds(
    instance: Instance, worlds: Worlds, *, excluded: Collection[int]
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """The discard rule of 1.4: ``(used ascending, discarded ascending)``.

    A world is discarded when some player who is not excluded, at some slot where he is
    eligible, has no value in it for a requirement in force that applies there. Locks and the
    candidates' own tables play no part.
    """
    left_out = _player_ids(instance, excluded)
    requirements = _in_force(instance)
    used, discarded = [], []
    for world_id in sorted(worlds):
        world = worlds[world_id]
        hole = any(
            world_vector(instance, world, c.player_id).get(r.metric) is None
            for c in instance.candidates
            if c.player_id not in left_out
            for slot in instance.slots
            if _eligible(c, slot)
            for r in requirements
            if _applies(r, slot.slot_id)
        )
        (discarded if hole else used).append(world_id)
    return tuple(used), tuple(discarded)


def domain_inputs(
    instance: Instance,
    *,
    slot_type: Callable[..., object],
    formation_type: Callable[..., object],
    candidate_type: Callable[..., object],
    requirement_type: Callable[..., object],
) -> DomainInputs:
    """The instance rebuilt with the domain classes the caller passes (the oracle imports none).

    Candidates and requirements keep the instance's order, which the generator shuffles.
    """
    slots = tuple(slot_type(**s._asdict()) for s in instance.slots)
    candidates = tuple(
        candidate_type(**{**c._asdict(), "values": dict(c.values)}) for c in instance.candidates
    )
    requirements = tuple(requirement_type(**r._asdict()) for r in instance.requirements)
    return DomainInputs(candidates, requirements, formation_type(instance.formation_id, slots))


# --------------------------------------------------------------------------- CEILING


def _floored(
    instance: Instance, floors: Mapping[str, float] | None
) -> tuple[tuple[OracleRequirement, float], ...]:
    by_id = {r.requirement_id: r for r in _in_force(instance)}
    rows = []
    for requirement_id in sorted(floors or {}):
        if requirement_id not in by_id:
            raise ValueError("a floor names a requirement that is not in force")
        rows.append((by_id[requirement_id], floors[requirement_id]))
    return tuple(rows)


def _integer_sum(
    x: Lineup, r: OracleRequirement, vectors: Vectors, q: int, rule: Callable[..., int]
) -> int:
    return sum(rule(vectors[p][r.metric], r.normalizer, q) for s, p in x if _applies(r, s))


def _inner(
    instance: Instance,
    *,
    floors: Mapping[str, float] | None,
    locked: Collection[int],
    excluded: Collection[int],
) -> tuple[str, int, tuple[Lineup, ...]]:
    """The state, the count of every XI and the inner set of 2.1 (floors compared as HARD)."""
    vectors = point_vectors(instance)
    q = instance.quantization
    every = xis(instance, locked=locked, excluded=excluded, vectors=vectors)
    floored = _floored(instance, floors)
    inner = tuple(
        x
        for x in every
        if all(
            _integer_sum(x, r, vectors, q, floor_coef) >= ceil_target(phi, r.normalizer, q)
            for r, phi in floored
        )
    )
    state = "FIELDABLE" if inner else "NOT_SATISFIABLE" if every else "UNFIELDABLE"
    return state, len(every), inner


def ceilings(
    instance: Instance,
    *,
    floors: Mapping[str, float] | None,
    locked: Collection[int],
    excluded: Collection[int],
) -> CeilingTruth:
    """Per requirement in force, the least and largest ``O_r`` over the inner set, every ``S_r``."""
    state, count, inner = _inner(instance, floors=floors, locked=locked, excluded=excluded)
    vectors = point_vectors(instance)
    q = instance.quantization
    ranges = []
    for r in _in_force(instance):
        if not inner:
            break
        integers = [_integer_sum(x, r, vectors, q, objective) for x in inner]
        sums = sorted(exact_sum(x, r, vectors) for x in inner)
        applicable = sum(1 for s in instance.slots if _applies(r, s.slot_id))
        minimum = Fraction(r.minimum)
        ranges.append(
            RangeTruth(
                r.requirement_id,
                applicable,
                Fraction(applicable) * Fraction(r.normalizer) / (2 * q),
                minimum,
                max(integers),
                min(integers),
                sums[-1],
                sums[0],
                tuple(sums),
                sums[-1] >= minimum,
                sums[0] < minimum,
            )
        )
    return CeilingTruth(state, count, len(inner), inner, tuple(ranges))


# --------------------------------------------------------------------------- FRONTIER


def dominates(u: Sequence[Fraction | int], v: Sequence[Fraction | int]) -> bool:
    """``u >= v`` componentwise and ``u != v``."""
    return tuple(u) != tuple(v) and all(a >= b for a, b in zip(u, v, strict=True))


def nondominated(vectors: Iterable[tuple]) -> tuple[tuple, ...]:
    """The distinct vectors no other dominates, lexicographic-descending."""
    distinct = sorted(set(vectors), reverse=True)
    return tuple(v for v in distinct if not any(dominates(u, v) for u in distinct))


def frontier(
    instance: Instance,
    *,
    dimensions: Sequence[str],
    floors: Mapping[str, float] | None,
    locked: Collection[int],
    excluded: Collection[int],
) -> FrontierTruth:
    """The vectors ``V(x)`` over the inner set and their nondominated subset (4.1)."""
    by_id = {r.requirement_id: r for r in _in_force(instance)}
    declared = tuple(dimensions)
    if not declared or len(set(declared)) != len(declared) or not set(declared) <= set(by_id):
        raise ValueError("dimensions must be distinct requirements in force")
    state, _, inner = _inner(instance, floors=floors, locked=locked, excluded=excluded)
    vectors = point_vectors(instance)
    q = instance.quantization
    chosen = [by_id[d] for d in declared]
    vector_of = {x: tuple(_integer_sum(x, r, vectors, q, objective) for r in chosen) for x in inner}
    raw_of = {x: tuple(exact_sum(x, r, vectors) for r in chosen) for x in inner}
    raw_points = set(nondominated(raw_of.values()))
    return FrontierTruth(
        state,
        declared,
        nondominated(vector_of.values()),
        tuple(sorted(set(vector_of.values()), reverse=True)),
        vector_of,
        raw_of,
        frozenset(x for x in inner if raw_of[x] in raw_points),
    )


# --------------------------------------------------------------------------- CONFLICT


def conflict_model(
    instance: Instance,
    *,
    arithmetic: str,
    locked: Collection[int],
    excluded: Collection[int],
    floors: Mapping[str, float] | None = None,
    mode: str | None = None,
) -> ConflictModel:
    """The declarations of 3.1 in the named arithmetic (the table of 3.1).

    ``HARD_FLOOR_CONSERVATIVE`` (``explain_floors``): the given floors, or every requirement
    in force at its minimum when ``floors`` is ``None``; floor coefficients, ceiling targets.
    ``SOLVE_HALF_EVEN`` (``explain_solve``): every requirement that is hard, or every one in
    ``SATISFY`` mode, at its minimum; half-even coefficients and targets.
    """
    q = instance.quantization
    requirements = _in_force(instance)
    if arithmetic == HARD_FLOOR_CONSERVATIVE:
        if mode is not None:
            raise ValueError("a mode belongs to the half-even arithmetic")
        if floors is None:
            floored = tuple((r, r.minimum) for r in requirements)
        else:
            floored = _floored(instance, floors)
        coefficient, target = floor_coef, ceil_target
    elif arithmetic == SOLVE_HALF_EVEN:
        if floors is not None:
            raise ValueError("the half-even arithmetic takes its floors from the mode")
        if mode not in MODES:
            raise ValueError("mode must be BALANCE or SATISFY")
        floored = tuple(
            (r, r.minimum) for r in requirements if getattr(r, "hard", False) or mode == "SATISFY"
        )
        coefficient, target = half_even, half_even
    else:
        raise ValueError("unknown arithmetic")
    vectors = point_vectors(instance)
    keys = options(instance, vectors=vectors, excluded=(), keys_ignore_exclusions=True)
    slot_ids = tuple(s.slot_id for s in instance.slots)
    coefficients, applicable, targets = {}, {}, {}
    for r, phi in floored:
        where = tuple(i for i, slot_id in enumerate(slot_ids) if _applies(r, slot_id))
        applicable[r.requirement_id] = where
        coefficients[r.requirement_id] = {
            (i, p): coefficient(vectors[p][r.metric], r.normalizer, q)
            for i in where
            for p in keys[i]
        }
        targets[r.requirement_id] = target(phi, r.normalizer, q)
    locks = tuple(sorted(_player_ids(instance, locked)))
    exclusions = tuple(sorted(_player_ids(instance, excluded)))
    declarations = (
        tuple(f"slot:{s}" for s in slot_ids)
        + tuple(f"exclusion:{p}" for p in exclusions)
        + tuple(f"floor:{r.requirement_id}" for r, _ in floored)
        + tuple(f"lock:{p}" for p in locks)
    )
    return ConflictModel(
        arithmetic, slot_ids, keys, coefficients, applicable, targets, locks, exclusions,
        declarations,
    )


def _holds(model: ConflictModel, tested: frozenset[str], assignment: ConflictLineup) -> bool:
    """Every declaration of ``tested`` holds for ``assignment`` (checked from scratch)."""
    placed = [p for _, p in assignment if p is not None]
    if len(placed) != len(set(placed)):
        return False
    for i, (_, player) in enumerate(assignment):
        if player is not None and player not in model.options[i]:
            return False
    for declaration in tested:
        family, subject = declaration.split(":", 1)
        if family == "slot" and dict(assignment)[subject] is None:
            return False
        if family == "exclusion" and int(subject) in placed:
            return False
        if family == "lock" and int(subject) not in placed:
            return False
        if family == "floor":
            coefficients = model.coefficients[subject]
            total = sum(
                coefficients[(i, p)]
                for i, (_, p) in enumerate(assignment)
                if p is not None and i in model.applicable[subject]
            )
            if total < model.targets[subject]:
                return False
    return True


def satisfiable(
    declarations: Iterable[str], model: ConflictModel, *, node_limit: int | None = None
) -> Satisfiability:
    """Whether some assignment (1.1) meets the background and every declaration given (3.3).

    Depth-first over the slots in formation order: each slot takes an admissible unused
    player, or stays empty when its coverage is not declared. A branch is pruned when the slots
    left cannot hold the locked players still missing, or when a floor cannot be met even if
    every applicable slot left took its largest coefficient (0 for a slot that may stay
    empty); that bound ignores injectivity, so it never prunes a witness. The search stops at
    the first witness. Above ``node_limit`` nodes it raises ``RuntimeError``.
    """
    tested = frozenset(declarations)
    if not tested <= set(model.declarations):
        raise ValueError("a declaration is not one of the model's")
    count = len(model.slot_ids)
    covered = tuple(f"slot:{s}" in tested for s in model.slot_ids)
    banned = frozenset(p for p in model.excluded if f"exclusion:{p}" in tested)
    required = tuple(p for p in model.locked if f"lock:{p}" in tested)
    floors = tuple(r for r in sorted(model.targets) if f"floor:{r}" in tested)
    usable = tuple(tuple(p for p in row if p not in banned) for row in model.options)
    if any(covered[i] and not usable[i] for i in range(count)):
        return Satisfiability(False, None, 1)
    reach: dict[str, list[int]] = {}
    for r in floors:
        best = [0] * count
        for i in model.applicable[r]:
            values = [model.coefficients[r][(i, p)] for p in usable[i]]
            best[i] = max(values + ([] if covered[i] else [0]))
        reach[r] = [sum(best[i:]) for i in range(count + 1)]

    nodes = 0
    chosen: list[int | None] = []
    used: set[int] = set()
    totals = dict.fromkeys(floors, 0)

    def search(i: int) -> bool:
        nonlocal nodes
        nodes += 1
        if node_limit is not None and nodes > node_limit:
            raise RuntimeError("the backtracking search passed its node limit")
        if any(totals[r] + reach[r][i] < model.targets[r] for r in floors):
            return False
        missing = [p for p in required if p not in used]
        places = [{j for j in range(i, count) if p in usable[j]} for p in missing]
        if any(not slots for slots in places) or len(set().union(*places)) < len(missing):
            return False
        if i == count:
            return True
        for player in usable[i]:
            if player in used:
                continue
            chosen.append(player)
            used.add(player)
            gains = {
                r: model.coefficients[r][(i, player)] for r in floors if i in model.applicable[r]
            }
            for r, gain in gains.items():
                totals[r] += gain
            if search(i + 1):
                return True
            for r, gain in gains.items():
                totals[r] -= gain
            used.discard(player)
            chosen.pop()
        if not covered[i]:
            chosen.append(None)
            if search(i + 1):
                return True
            chosen.pop()
        return False

    if not search(0):
        return Satisfiability(False, None, nodes)
    witness = tuple(zip(model.slot_ids, chosen, strict=True))
    if not _holds(model, tested, witness):
        raise RuntimeError("the search returned an assignment that misses a declaration")
    return Satisfiability(True, witness, nodes)


def deletion_filter(
    order: Sequence[str], model: ConflictModel, *, node_limit: int | None = None
) -> FilterTruth:
    """The deletion filter of 3.3 in ``order``, which must hold every declaration once."""
    order = tuple(order)
    if len(set(order)) != len(order) or set(order) != set(model.declarations):
        raise ValueError("the order must hold every declaration of the model once")
    first = satisfiable(model.declarations, model, node_limit=node_limit)
    if first.satisfiable:
        return FilterTruth("MODEL_FEASIBLE", (), (), first.witness, (first.nodes,))
    current = set(order)
    rows, nodes = [], [first.nodes]
    for declaration in order:
        test = satisfiable(current - {declaration}, model, node_limit=node_limit)
        nodes.append(test.nodes)
        if test.satisfiable:
            rows.append(FilterRow(declaration, "KEPT_WITNESS", test.witness))
        else:
            current.discard(declaration)
            rows.append(FilterRow(declaration, "DROPPED", None))
    conflict = tuple(d for d in order if d in current)
    return FilterTruth("MINIMAL_CERTIFIED", conflict, tuple(rows), None, tuple(nodes))


def restores_alone(
    c: str, model: ConflictModel, *, node_limit: int | None = None
) -> bool | None:
    """The restore test of 3.3: whether every declaration but ``c`` holds together.

    ``None`` for slot coverage, where the test does not apply (an XI fills every slot).
    """
    if c not in model.declarations:
        raise ValueError("a declaration is not one of the model's")
    if c.startswith("slot:"):
        return None
    rest = [d for d in model.declarations if d != c]
    return satisfiable(rest, model, node_limit=node_limit).satisfiable


def minimal_conflicting_sets(model: ConflictModel) -> tuple[tuple[str, ...], ...]:
    """Every set that is not satisfiable while each of its proper subsets is, by size.

    Exponential in the number of declarations: for the small instances of the tests only.
    """
    known: dict[frozenset[str], bool] = {}

    def holds(subset: frozenset[str]) -> bool:
        if subset not in known:
            known[subset] = satisfiable(subset, model).satisfiable
        return known[subset]

    found = []
    for size in range(1, len(model.declarations) + 1):
        for combination in itertools.combinations(model.declarations, size):
            subset = frozenset(combination)
            if not holds(subset) and all(holds(subset - {d}) for d in subset):
                found.append(combination)
    return tuple(found)


# --------------------------------------------------------------------------- RISK


def loss_pair(instance: Instance, x: Lineup, vectors: Vectors) -> Pair | None:
    """``(M, T)`` of 5.1 for ``x`` under one value table; ``None`` if it uses an unmeasured key."""
    q = instance.quantization
    shortfalls = []
    for r in _in_force(instance):
        total = 0
        for slot_id, player in x:
            if player is None or not _applies(r, slot_id):
                continue
            value = vectors.get(player, {}).get(r.metric)
            if value is None:
                return None
            total += half_even(value, r.normalizer, q)
        shortfalls.append(max(0, half_even(r.minimum, r.normalizer, q) - total))
    return max(shortfalls, default=0), sum(shortfalls)


def point_loss(instance: Instance, x: Lineup) -> Pair | None:
    """``point_loss`` of 5.6: the pair at the candidates' own values, or ``None``."""
    return loss_pair(instance, x, point_vectors(instance))


def point_sums(instance: Instance, x: Lineup) -> tuple[tuple[str, Fraction | None], ...]:
    """``point_sums`` of 5.6: each exact ``S_r`` at the candidates' own values, or ``None``.

    ``None`` when ``r``'s metric is unmeasured at a key of the lineup where ``r`` applies: a
    value at a slot where ``r`` does not apply is not part of ``S_r``.
    """
    vectors = point_vectors(instance)
    rows = []
    for r in _in_force(instance):
        measured = all(
            vectors.get(p, {}).get(r.metric) is not None for s, p in x if _applies(r, s)
        )
        rows.append((r.requirement_id, exact_sum(x, r, vectors) if measured else None))
    return tuple(rows)


def world_pairs(
    instance: Instance, x: Lineup, *, worlds: Worlds, excluded: Collection[int]
) -> tuple[tuple[int, Pair], ...]:
    """``(world_id, (M^w, T^w))`` for every used world, ascending."""
    used, _ = used_worlds(instance, worlds, excluded=excluded)
    rows = []
    for world_id in used:
        pair = loss_pair(instance, x, world_vectors(instance, worlds[world_id]))
        if pair is None:
            raise ValueError("the lineup uses a key that a used world leaves unmeasured")
        rows.append((world_id, pair))
    return tuple(rows)


def _ordered(rows: Iterable[tuple[int, Pair]]) -> list[tuple[int, Pair]]:
    # The key of 5.2: M descending, then T descending, then world id ascending.
    return sorted(rows, key=lambda row: (-row[1][0], -row[1][1], row[0]))


def _tail_sum(rows: Iterable[tuple[int, Pair]], k: int) -> Pair:
    tail = _ordered(rows)[:k]
    return sum(pair[0] for _, pair in tail), sum(pair[1] for _, pair in tail)


def _risk_space(
    instance: Instance, worlds: Worlds, *, locked: Collection[int], excluded: Collection[int]
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[Lineup, ...]]:
    """Used and discarded worlds, and the XIs every used world shares (the lemma of 1.4)."""
    used, discarded = used_worlds(instance, worlds, excluded=excluded)
    if not used:
        return used, discarded, ()
    left_out = _player_ids(instance, excluded)
    eligible = tuple(
        tuple(
            c.player_id
            for c in _candidates(instance)
            if c.player_id not in left_out and _eligible(c, slot)
        )
        for slot in instance.slots
    )
    for world_id in used:
        table = world_vectors(instance, worlds[world_id])
        if options(instance, vectors=table, excluded=excluded) != eligible:
            raise RuntimeError("a used world leaves an eligible key unmeasured (lemma of 1.4)")
    table = world_vectors(instance, worlds[used[0]])
    return used, discarded, xis(instance, locked=locked, excluded=excluded, vectors=table)


def membership(
    instance: Instance, level_set: Iterable[Lineup]
) -> tuple[tuple[int, bool, bool], ...]:
    """``(player_id, possible, necessary)`` per candidate over a non-empty level set."""
    sets = [frozenset(p for _, p in x) for x in level_set]
    if not sets:
        raise ValueError("membership is read over a level set that holds an XI")
    return tuple(
        (c.player_id, any(c.player_id in s for s in sets), all(c.player_id in s for s in sets))
        for c in _candidates(instance)
    )


def _certified(
    instance: Instance,
    used: tuple[int, ...],
    discarded: tuple[int, ...],
    values: Mapping[Lineup, Pair],
    world_least: tuple[tuple[int, Pair], ...],
) -> RiskTruth:
    optimum = min(values.values())
    level = tuple(x for x, value in values.items() if value == optimum)
    return RiskTruth(
        "CERTIFIED",
        used,
        discarded,
        optimum,
        level,
        frozenset(frozenset(p for _, p in x) for x in level),
        membership(instance, level),
        world_least,
    )


def _terminal(status: str, used: tuple[int, ...], discarded: tuple[int, ...]) -> RiskTruth:
    return RiskTruth(status, used, discarded, None, (), frozenset(), (), ())


def tail_sum_of(
    instance: Instance, x: Lineup, k: int, *, worlds: Worlds, excluded: Collection[int]
) -> Pair:
    """``(sum of the k largest M, sum of T over the k lexicographically largest worlds)``."""
    rows = world_pairs(instance, x, worlds=worlds, excluded=excluded)
    if not 1 <= k <= len(rows):
        raise ValueError("k must lie between 1 and the number of used worlds")
    return _tail_sum(rows, k)


def tail_of(
    instance: Instance, x: Lineup, k: int, *, worlds: Worlds, excluded: Collection[int]
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """For ``x``: the tail (the key order of 5.2, cut at ``k``) and its boundary ties.

    The ties are the worlds outside the tail whose pair equals the last tail member's, in
    ascending world id.
    """
    rows = _ordered(world_pairs(instance, x, worlds=worlds, excluded=excluded))
    if not 1 <= k <= len(rows):
        raise ValueError("k must lie between 1 and the number of used worlds")
    last = rows[k - 1][1]
    ties = tuple(sorted(world_id for world_id, pair in rows[k:] if pair == last))
    return tuple(world_id for world_id, _ in rows[:k]), ties


def tail_optimum(
    instance: Instance,
    k: int,
    *,
    worlds: Worlds,
    locked: Collection[int],
    excluded: Collection[int],
) -> RiskTruth:
    """TAIL(k) of 5.2: the least ``(sum of the k largest M, sum of T over that tail)`` over 𝒳.

    ``NOT_EVALUABLE`` when no world, or fewer than ``k``, is used; then ``UNFIELDABLE`` when
    the used worlds share no XI.
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    used, discarded, space = _risk_space(instance, worlds, locked=locked, excluded=excluded)
    if len(used) < k:
        return _terminal("NOT_EVALUABLE", used, discarded)
    if not space:
        return _terminal("UNFIELDABLE", used, discarded)
    tables = {w: world_vectors(instance, worlds[w]) for w in used}
    values = {}
    for x in space:
        rows = [(w, loss_pair(instance, x, tables[w])) for w in used]
        values[x] = _tail_sum(rows, k)
    return _certified(instance, used, discarded, values, ())


def balance_optimum(
    instance: Instance, *, vectors: Vectors, locked: Collection[int], excluded: Collection[int]
) -> tuple[Pair | None, tuple[Lineup, ...]]:
    """BALANCE under one value table: the least ``(M, T)`` and every XI attaining it."""
    values = {
        x: loss_pair(instance, x, vectors)
        for x in xis(instance, locked=locked, excluded=excluded, vectors=vectors)
    }
    if not values:
        return None, ()
    least = min(values.values())
    return least, tuple(x for x, value in values.items() if value == least)


def _world_least(
    instance: Instance,
    used: tuple[int, ...],
    worlds: Worlds,
    *,
    locked: Collection[int],
    excluded: Collection[int],
) -> dict[int, Pair | None]:
    return {
        w: balance_optimum(
            instance,
            vectors=world_vectors(instance, worlds[w]),
            locked=locked,
            excluded=excluded,
        )[0]
        for w in used
    }


def _regret(rows: Iterable[tuple[int, Pair]], least: Mapping[int, Pair]) -> Pair:
    return max((pair[0] - least[w][0], pair[1] - least[w][1]) for w, pair in rows)


def regret_optimum(
    instance: Instance, *, worlds: Worlds, locked: Collection[int], excluded: Collection[int]
) -> RiskTruth:
    """MINIMAX_REGRET of 5.3: the least largest ``(M - M*, T - T*)`` over the used worlds.

    ``(M*, T*)`` is BALANCE's least pair in each world, found by its own enumeration.
    """
    used, discarded, space = _risk_space(instance, worlds, locked=locked, excluded=excluded)
    if not used:
        return _terminal("NOT_EVALUABLE", used, discarded)
    if not space:
        return _terminal("UNFIELDABLE", used, discarded)
    least = _world_least(instance, used, worlds, locked=locked, excluded=excluded)
    if any(pair is None for pair in least.values()):
        raise RuntimeError("a used world has no XI although the used worlds share one")
    tables = {w: world_vectors(instance, worlds[w]) for w in used}
    values = {
        x: _regret([(w, loss_pair(instance, x, tables[w])) for w in used], least) for x in space
    }
    return _certified(instance, used, discarded, values, tuple((w, least[w]) for w in used))


def regret_of(
    instance: Instance,
    x: Lineup,
    *,
    worlds: Worlds,
    locked: Collection[int],
    excluded: Collection[int],
) -> Pair:
    """The largest ``(M - M*, T - T*)`` of ``x`` over the used worlds (compared, never served)."""
    rows = world_pairs(instance, x, worlds=worlds, excluded=excluded)
    used = tuple(w for w, _ in rows)
    least = _world_least(instance, used, worlds, locked=locked, excluded=excluded)
    if not rows or any(pair is None for pair in least.values()):
        raise ValueError("a regret needs a used world and an XI")
    return _regret(rows, least)


def binding_of(
    instance: Instance,
    x: Lineup,
    *,
    worlds: Worlds,
    locked: Collection[int],
    excluded: Collection[int],
) -> tuple[int, ...]:
    """The binding worlds of ``x`` (5.3): those whose difference pair is the largest, ascending."""
    rows = world_pairs(instance, x, worlds=worlds, excluded=excluded)
    used = tuple(w for w, _ in rows)
    least = _world_least(instance, used, worlds, locked=locked, excluded=excluded)
    if not rows or any(pair is None for pair in least.values()):
        raise ValueError("binding worlds need a used world and an XI")
    top = _regret(rows, least)
    return tuple(
        w for w, pair in rows if (pair[0] - least[w][0], pair[1] - least[w][1]) == top
    )


def _deficit_bounds(
    instance: Instance, worlds: Worlds, *, excluded: Collection[int]
) -> dict[int, tuple[int, ...]]:
    """``U^w_r`` of 5.1 for every used world, requirement id ascending."""
    used, _ = used_worlds(instance, worlds, excluded=excluded)
    if not used:
        raise ValueError("the bounds of 5.1 are defined only when some world is used")
    q = instance.quantization
    bounds = {}
    for world_id in used:
        table = world_vectors(instance, worlds[world_id])
        keys = options(instance, vectors=table, excluded=excluded)
        row = []
        for r in _in_force(instance):
            lower = sum(
                min(0, half_even(table[p][r.metric], r.normalizer, q))
                for i, slot in enumerate(instance.slots)
                if _applies(r, slot.slot_id)
                for p in keys[i]
            )
            row.append(max(0, half_even(r.minimum, r.normalizer, q) - lower))
        bounds[world_id] = tuple(row)
    return bounds


def t_bound(instance: Instance, worlds: Worlds, *, excluded: Collection[int]) -> int:
    """``T_bound`` of 5.1: the largest ``sum_r U^w_r`` over the used worlds (0 with no ``R``)."""
    return max(sum(row) for row in _deficit_bounds(instance, worlds, excluded=excluded).values())


def _guard_admits(instance: Instance) -> bool:
    """Whether 5.1's overflow guard admits TAIL at every evaluable ``k`` and REGRET.

    The guard's own arithmetic on bounds; no loss is encoded. The worst evaluable ``k`` is the
    number of used worlds; with none used every rule is ``NOT_EVALUABLE`` before the guard.
    """
    worlds = instance.worlds or {}
    used, _ = used_worlds(instance, worlds, excluded=instance.excluded)
    if not used:
        return True
    bounds = _deficit_bounds(instance, worlds, excluded=instance.excluded)
    totals = max(sum(row) for row in bounds.values())
    largest = max(max(row, default=0) for row in bounds.values())
    cap = (2 * len(used) * totals + 1) * (largest + 1)
    return (2 * len(used) + 2) * cap < EXACT_OBJECTIVE_LIMIT and 3 * cap < EXACT_OBJECTIVE_LIMIT


# --------------------------------------------------------------------------- instances


_MASK = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C15


class _Stream:
    """SplitMix64: a fixed integer sequence per ``(seed, salt)``, the same on every platform."""

    __slots__ = ("_state",)

    def __init__(self, seed: int, salt: int) -> None:
        self._state = (seed * 0xD1B54A32D192ED03 + salt * _GOLDEN) & _MASK

    def _next(self) -> int:
        self._state = (self._state + _GOLDEN) & _MASK
        z = self._state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    def below(self, n: int) -> int:
        """An integer in ``[0, n)``, without modulo bias."""
        limit = (1 << 64) - (1 << 64) % n
        while True:
            value = self._next()
            if value < limit:
                return value % n

    def between(self, low: int, high: int) -> int:
        return low + self.below(high - low + 1)

    def chance(self, numerator: int, denominator: int) -> bool:
        return self.below(denominator) < numerator

    def order(self, count: int) -> list[int]:
        """A uniformly drawn permutation of ``range(count)``."""
        indexes = list(range(count))
        for i in range(count - 1, 0, -1):
            j = self.below(i + 1)
            indexes[i], indexes[j] = indexes[j], indexes[i]
        return indexes


def _positions(rng: _Stream) -> tuple[str, ...]:
    chosen = set(rng.order(len(POSITIONS))[: (1, 2, 2, 2, 3, 3)[rng.below(6)]])
    return tuple(position for i, position in enumerate(POSITIONS) if i in chosen)


def _scope(rng: _Stream, slot_ids: Sequence[str]) -> tuple[str, ...]:
    while True:
        chosen = tuple(slot_id for slot_id in slot_ids if rng.chance(1, 2))
        if chosen:
            return chosen


def _value(rng: _Stream, dyadic: bool, scale: int) -> float:
    if dyadic:
        return rng.between(-128, 256) / 64
    if rng.chance(1, 2):
        return rng.between(-200, 400) / (100 * scale)
    return rng.between(-2000, 4000) / (1000 * scale)


def _minimum(rng: _Stream, dyadic: bool, scale: int) -> float:
    return rng.between(0, 256) / 64 if dyadic else rng.between(0, 400) / (100 * scale)


def _check_half_even(instance: Instance) -> None:
    """Section 6: the float rule, written out, equals exact half-even on every draw."""
    q = instance.quantization
    for r in instance.requirements:
        drawn = [r.minimum] + [c.values.get(r.metric) for c in instance.candidates]
        for world in (instance.worlds or {}).values():
            drawn.extend(vector.get(r.metric) for vector in world.values())
        for v in drawn:
            if v is not None and int(round(v / r.normalizer * q)) != half_even(v, r.normalizer, q):
                raise AssertionError("a dyadic draw rounds differently in floating point")


def _draw(seed: int, kind: str) -> Instance:
    rng = _Stream(seed, KINDS.index(kind) + 1)
    dyadic = kind in ("CONFLICT_SOLVE", "RISK")
    # Decimal draws come at one of three magnitudes, so that q = 100 sometimes rounds coarsely
    # (ties of integer sums between XIs whose exact sums differ) and q = 100000 never does.
    scale = 1 if dyadic else (1, 10, 100)[rng.below(3)]
    slots = tuple(
        OracleSlot(f"s{i}", _positions(rng), f"Slot {i}") for i in range(1, rng.between(3, 5) + 1)
    )
    slot_ids = tuple(s.slot_id for s in slots)
    requirements = [
        OracleRequirement(
            f"r{i}",
            f"m{i}",
            _minimum(rng, dyadic, scale),
            (DYADIC_NORMALIZERS if dyadic else DECIMAL_NORMALIZERS)[rng.below(4 if dyadic else 5)],
            () if rng.chance(1, 2) else _scope(rng, slot_ids),
            kind == "CONFLICT_SOLVE" and rng.chance(1, 3),
            f"Requirement {i}",
        )
        for i in range(1, (3 if kind == "FRONTIER" else rng.between(1, 3)) + 1)
    ]
    metrics = [r.metric for r in requirements]
    ids = [range(1, 41)[i] for i in rng.order(40)[: rng.between(max(5, len(slots) + 2), 8)]]
    candidates = tuple(
        OracleCandidate(
            pid,
            POSITIONS[rng.below(len(POSITIONS))],
            {m: None if rng.chance(1, 12) else _value(rng, dyadic, scale) for m in metrics},
            0 if rng.chance(1, 10) else rng.between(90, 3000),
            None if rng.chance(4, 5) else tuple(s for s in slot_ids if rng.chance(2, 3)),
            f"Player {pid}",
        )
        for pid in ids
    )
    locks = rng.order(len(ids))[: (0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 2)[rng.below(12)]]
    locked = sorted(ids[i] for i in locks)
    excluded = {ids[i] for i in rng.order(len(ids))[: (0, 0, 0, 1, 1, 2)[rng.below(6)]]}
    if kind.startswith("CONFLICT") and locked and rng.chance(1, 4):
        excluded.add(locked[0])

    floors: dict[str, float] | None = None
    if kind in ("CEILING", "FRONTIER", "CONFLICT_FLOORS"):
        floors = {}
        for r in requirements:
            applicable = sum(1 for s in slot_ids if not r.slot_ids or s in r.slot_ids)
            if rng.chance(1, 2 if kind == "CONFLICT_FLOORS" else 3):
                floors[r.requirement_id] = rng.between(-100, 300 * applicable) / (100 * scale)
        if kind == "CONFLICT_FLOORS" and rng.chance(1, 4):
            floors = None
    dimensions: tuple[tuple[str, ...], ...] = ()
    if kind == "FRONTIER":
        names = [r.requirement_id for r in requirements]
        dimensions = (
            tuple(names[i] for i in rng.order(3)[:2]),
            tuple(names[i] for i in rng.order(3)),
        )
    worlds: dict[int, dict[int, dict[str, float | None]]] | None = None
    if kind == "RISK":
        worlds = {}
        for world_id in range(rng.between(1, 5)):
            world = {pid: {m: _value(rng, True, 1) for m in metrics} for pid in ids}
            for _ in range((0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 2)[rng.below(12)]):
                pid = ids[rng.below(len(ids))]
                if rng.chance(1, 2):
                    world.pop(pid, None)
                elif pid in world:
                    world[pid][metrics[rng.below(len(metrics))]] = None
            worlds[world_id] = world
    mode = None
    if kind == "CONFLICT_SOLVE":
        mode = "SATISFY" if rng.chance(2, 3) else "BALANCE"

    instance = Instance(
        slots,
        candidates,
        tuple(requirements[i] for i in rng.order(len(requirements))),
        QUANTIZATIONS[rng.below(3)],
        kind,
        seed,
        f"oracle-{kind.lower()}-{seed}",
        tuple(locked),
        tuple(sorted(excluded)),
        floors,
        dimensions,
        worlds,
        mode,
    )
    if kind == "RISK":
        # The generator rules of section 6 do not mention 5.1's overflow guard, which a drawn
        # instance at q = 100000 with negative rates can exceed. A coarser q is taken instead,
        # so every seeded instance is one the risk rules evaluate; q = 100 always passes.
        for q in sorted(QUANTIZATIONS, reverse=True):
            if q <= instance.quantization and _guard_admits(instance._replace(quantization=q)):
                instance = instance._replace(quantization=q)
                break
        else:
            raise AssertionError("no quantization passes the overflow guard")
    if dyadic:
        _check_half_even(instance)
    return instance


def instances(seed: int) -> SeededInstances:
    """The seeded instances of section 6, one per kind, each drawn from its own stream.

    Three to five slots with mixed allowed positions, five to eight candidates (some with
    ``eligible_slots``, some with zero minutes), one to three requirements (three for
    FRONTIER) with mixed ``slot_ids``, some ``None`` values, locks, exclusions and
    ``q`` in ``{100, 1000, 100000}``. CEILING, FRONTIER and CONFLICT_FLOORS draw decimal values
    of either sign, at one of three magnitudes per instance, with decimal normalisers;
    CONFLICT_SOLVE and RISK draw multiples of 1/64 in ``[-2, 4]``, minima in ``[0, 4]`` and
    normalisers in ``{0.5, 1, 2, 4}``, and every draw is checked against the float rule. RISK
    draws one to five worlds with holes and keeps its declarations inside 5.1's overflow guard
    at every evaluable ``k`` (a coarser ``q`` is taken where they would not be; on seeds 0 to
    119 none is). The draws hold for the declarations drawn: a test that changes them owns the
    consequence.
    """
    return SeededInstances(*(_draw(seed, kind) for kind in KINDS))
