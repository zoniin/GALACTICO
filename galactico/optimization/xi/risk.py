"""Declared-risk selection over the shared resampled worlds: TAIL(k of B), WORST_WORLD, REGRET.

Claim: on the snapshot's shared resampled worlds, an XI that the declared rule over the
per-world loss selects, the rule's optimum, which players are in every and in some XI the rule
selects, and, for the XI shown, the worlds that decide its value. The loss of an XI in a world
is the pair (largest shortfall, summed shortfall) of BALANCE, compared lexicographically.
Non-claim: stability against resampling of the historical matches; not robustness to
opponents, absences or form, and not a forecast. Another XI the rule selects has the same
optimum and can have other tail or binding worlds. No chance, share or average over worlds is
computed. UNKNOWN, NOT_RUN and a FEASIBLE incumbent are never a selection, an optimum, a
necessity or an absence.

Worlds (OR-XI-SPEC 1.4). A world replaces every candidate's whole vector, never merges it; a
player absent from a world has no value there. A world is set aside, as the shipped bootstrap
sets it aside, when a player who is not excluded has no value in it for a requirement in force
at a slot he is eligible for. On the worlds kept every admissible key is measured, so all of
them share one set of XIs; this module checks that and raises if it fails. ``k`` and ``B`` are
never recomputed on the worlds kept.

Arithmetic (1.2). Shortfalls are ``SHORTFALL_POLICY``, ``solve_xi``'s own ``_q`` integers, so
with one world each rule returns BALANCE's pair there. Inside the model a pair ``(M, T)`` is the
integer ``BIG * M + T`` with ``BIG = 2 |U| T_bound + 1``, larger than any summed shortfall
over ``|U|`` worlds and than twice any one, so a sum of ``k`` encodings and a difference of two
order as the pairs do (5.1). That integer is a search device: it lives in ``_encoding_base``,
the overflow guard, the model builders and one Python equality check, and is never a field, a
provenance value, a log record or a message. Every variable that holds one is split as
``BIG * a + b`` with ``a`` in ``[0, M_bound]`` and ``b`` in ``[0, BIG - 1]``, so no domain is
wider than ``BIG``; and a request whose model could pass ``2**53`` is refused before any solve.

How a rule is solved (5.6). The per-world shortfalls are a linear epigraph over the kernel's
background, never ``add_max_equality``. TAIL minimises ``k * eta + sum_w max(0, E^w - eta)``,
whose minimum over ``eta`` is the sum of the ``k`` largest ``E^w``; REGRET first takes each
world's least pair from ``kernel.value`` and minimises the largest ``E^w - E*^w``. Only an
OPTIMAL selection is reported; its XI is re-evaluated in Python and its objective recomputed
from those integers must equal ``solver.value`` of the objective. The level set is the model
with the objective held at that optimum, and each player's opposite solve, as
``kernel.membership`` makes it, decides whether he is in some or in every XI of it.
"""

from __future__ import annotations

import math
import time
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from ortools.sat.python import cp_model

from ..squad.kernel import (
    KERNEL_VERSION,
    PER_SOLVE_DETERMINISTIC_LIMIT,
    SHORTFALL_POLICY,
    KernelValue,
    Lineup,
    ShortfallKernel,
    fingerprint,
    scrub_lineage,
    source_fingerprints,
)
from .ceilings import UNFIELDABLE_PROVED
from .domain import FORMATIONS, Candidate, Formation, Slot, TacticalRequirement
from .solver import QUANTIZATION, _applies, _eligible, _fingerprint, _q
from .tradeoffs import MAX_MAGNITUDE

if TYPE_CHECKING:
    from ..squad.kernel import _Background

__all__ = [
    "COMPARISON",
    "DISCARD_REASON",
    "EXACT_OBJECTIVE_LIMIT",
    "LINEUP_ERROR",
    "PLAYER_ERROR",
    "RISK_GROWTH",
    "RISK_HARD",
    "RISK_NON_CLAIM",
    "RISK_NOT_EVALUABLE",
    "RISK_OVERFLOW",
    "RISK_REGRET",
    "RISK_TAIL",
    "RISK_VERSION",
    "RISK_WORST",
    "RULES",
    "RULE_ERROR",
    "SELECTION_DETERMINISTIC_LIMIT",
    "TAIL_COUNT_ERROR",
    "TAIL_MENU",
    "UNFIELDABLE_PROVED",
    "WORLDS_ERROR",
    "DiscardedWorld",
    "LossPair",
    "MembershipBlock",
    "MembershipRow",
    "RiskCertificate",
    "RiskSelection",
    "SolveRecord",
    "TailSums",
    "WorldLoss",
    "declared_risk_selection",
    "minimax_regret_selection",
    "tail_selection",
    "world_losses",
    "worst_world_selection",
]

RISK_VERSION = "declared-risk-lexicographic-v1"
RULES = ("WORST_WORLD", "TAIL", "MINIMAX_REGRET")  # the fixed order of the page
# TAIL only; WORST_WORLD is k = 1. The E-13 draft's counts (config.json:13-16), enforced by the
# API; the module accepts any k from 1 to the world count.
TAIL_MENU: Mapping[int, tuple[int, ...]] = MappingProxyType({12: (2, 3, 6), 40: (4, 10, 20)})
SELECTION_DETERMINISTIC_LIMIT = 40.0
EXACT_OBJECTIVE_LIMIT = 2**53
COMPARISON = "largest shortfall first, then summed shortfall"
DISCARD_REASON = "missing shared-world exposure"  # the shipped string, solver.py:562

# The served sentences (OR-XI-SPEC 7.7). The labels are formatted here with B and k; the router
# adds E-13's suffix to the envelope claim and never to these.
RISK_WORST = (
    "Worst world of {B}, the extreme of the tail rule for these {B} worlds (a tail of one "
    "world): an XI whose single highest-loss resampled world is least, comparing the largest "
    "shortfall first and then the summed shortfall."
)
RISK_TAIL = (
    "Tail {k} of {B}: an XI whose {k} highest-loss resampled worlds have the least summed loss, "
    "comparing summed largest shortfalls first and then summed shortfalls."
)
RISK_REGRET = (
    "Least largest regret over {B} worlds: in each resampled world an XI's largest and summed "
    "shortfalls are set against the least pair any XI reaches there, and an XI whose largest "
    "gap is least is chosen."
)
RISK_NON_CLAIM = (
    "Stability against resampling of the historical matches; not robustness to opponents, "
    "absences or form, and not a forecast."
)
# The certificate's growth sentence (O8), WORST_WORLD and TAIL, formatted with B and |U|.
RISK_GROWTH = (
    "A worst case or a tail sum over resampled worlds can only grow as worlds are added. This "
    "request draws {B} worlds, of which {U} could be used."
)
RISK_HARD = "Declared-risk rules compare shortfalls; a hard minimum is a Satisfy question."
RISK_OVERFLOW = "The declared minima are too large for the exact integer model of this rule."
RISK_NOT_EVALUABLE = (
    "No world, or fewer worlds than the tail count, could be used, so this rule was not "
    "evaluated."
)
# Refusals of malformed declarations. Each is a fixed sentence and names no value.
RULE_ERROR = "The risk rule must be WORST_WORLD, TAIL or MINIMAX_REGRET."
TAIL_COUNT_ERROR = (
    "The tail count must be an integer from 1 to the world count; WORST_WORLD takes 1 or none "
    "and MINIMAX_REGRET none."
)
WORLDS_ERROR = (
    "Worlds must be a non-empty mapping of integer world ids, as many as the world count, to "
    "value tables keyed by integer player ids, each value finite and bounded by 1e12 or None; "
    "the world seed must be an integer, the bootstrap version a string, and analyze_ties a "
    "boolean."
)
PLAYER_ERROR = "A locked or excluded player is not a candidate."
LINEUP_ERROR = (
    "The lineup is not an XI of the used worlds under the declared locks and exclusions."
)

_SOURCES = ("risk.py", "../squad/kernel.py", "solver.py", "tradeoffs.py", "domain.py")
_STATUS = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.UNKNOWN: "UNKNOWN",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
}
_WITNESS = ("OPTIMAL", "FEASIBLE")

_Vectors = dict[int, dict[str, float | None]]
_Tables = dict[str, tuple[dict[tuple[int, str], int], int]]


@dataclass(frozen=True)
class LossPair:
    maximum_shortfall: int  # M, integer units of 1 / quantization (normalised)
    total_shortfall: int  # T


@dataclass(frozen=True)
class TailSums:
    """The tail rule's optimum; not a LossPair: a sum of maxima is not a maximum."""

    summed_maximum_shortfall: int  # Σ M over the tail
    summed_total_shortfall: int  # Σ T over the tail


@dataclass(frozen=True)
class WorldLoss:
    world_id: int
    selected: LossPair  # the XI shown, in this world
    world_least: LossPair | None  # MINIMAX_REGRET: the certified least pair of this world


@dataclass(frozen=True)
class DiscardedWorld:
    world_id: int
    reason: str  # "missing shared-world exposure"


@dataclass(frozen=True)
class SolveRecord:
    # WORLD_LEAST: one record per kernel stage kernel.value ran for that world, from its
    # stage_statuses (Z, S1, S2 as run), and one NOT_RUN record for a call that ran no solve
    # (a deadline passed); never the value status CERTIFIED
    purpose: str  # WORLD_LEAST | SELECTION | MEMBERSHIP
    world_id: int | None
    player_id: int | None
    status: str  # a 1.5 status; no objective value and no bound: those are encodings


@dataclass(frozen=True)
class MembershipRow:
    player_id: int
    possible: bool | None  # in some XI of the rule's level set
    necessary: bool | None  # in every XI of it


@dataclass(frozen=True)
class MembershipBlock:
    rows: tuple[MembershipRow, ...]  # player_id ascending; () when no selection exists
    # EXACT (also when vacuous) | LIMIT_REACHED | DEADLINE | MODEL_INVALID (1.5);
    # NOT_REQUESTED with analyze_ties=False (never served, 5.6 step 7)
    completeness: str


@dataclass(frozen=True)
class RiskCertificate:
    rule: str
    tail_count: int | None
    world_count: int  # B, as requested
    used_world_ids: tuple[int, ...]
    discarded_worlds: tuple[DiscardedWorld, ...]
    discarded_world_count: int
    undecided_world_ids: tuple[int, ...]  # REGRET only
    world_fingerprint: str
    world_seed: int
    solver_seed: int
    bootstrap_version: str
    quantization: int
    shortfall_policy: str  # kernel.SHORTFALL_POLICY
    comparison: str  # "largest shortfall first, then summed shortfall"
    selection_deterministic_limit: float
    world_least_deterministic_limit: float  # kernel.PER_SOLVE_DETERMINISTIC_LIMIT
    solves: int  # every CP-SAT call, kernel.value's stages included
    records: tuple[SolveRecord, ...]  # in call order; their statuses are the page's "statuses"
    # WORST_WORLD and TAIL: RISK_GROWTH formatted with B and |U| (O8: the certificate says that
    # a worst case grows with B and records B); None for MINIMAX_REGRET
    growth: str | None
    completeness: str  # EXACT | LIMIT_REACHED | DEADLINE | MODEL_INVALID (1.5)
    stopped_by: str | None  # DETERMINISTIC_LIMIT | WALL_CLOCK; None when nothing is undecided


@dataclass(frozen=True)
class RiskSelection:
    rule: str  # WORST_WORLD | TAIL | MINIMAX_REGRET
    tail_count: int | None  # k; 1 for WORST_WORLD; None for MINIMAX_REGRET
    status: str  # CERTIFIED | UNFIELDABLE | NOT_EVALUABLE | UNKNOWN | MODEL_INVALID
    lineup: Lineup  # the XI shown; () unless CERTIFIED
    world_losses: tuple[WorldLoss, ...]  # every used world, ascending id; () unless CERTIFIED
    tail_world_ids: tuple[int, ...]  # for the XI shown, in the key order of 5.2
    tail_boundary_ties: tuple[int, ...]  # for the XI shown, ascending world id
    tail_sum: TailSums | None  # the rule's optimum (TAIL, WORST_WORLD)
    binding_world_ids: tuple[int, ...]  # for the XI shown (MINIMAX_REGRET), ascending world id
    point_loss: LossPair | None
    # requirement_id ascending; None where the lineup uses a key whose point value is None;
    # never printed as floats: the router adds exact texts (7.5)
    point_sums: tuple[tuple[str, float | None], ...]
    membership: MembershipBlock
    certificate: RiskCertificate
    # the rule's bare 7.7 label formatted with B and k; the router adds E-13's suffix (5.7)
    claim: str
    non_claim: str  # RISK_NON_CLAIM, word for word
    reasons: tuple[str, ...]
    provenance: dict


def _solver(deadline: float, seed: int) -> cp_model.CpSolver:
    """The selection and membership solver: kernel._solver's settings, the selection limit.

    One search setting is added. With the default search, ortools 9.15.6755 left the TAIL
    selection of a three-slot, five-candidate oracle instance at q = 100000 (seed 29, k = 3)
    FEASIBLE at its 40 deterministic seconds: the encodings reach 1e13, and the LP bound of the
    single worker did not close the gap. Probing the objective's lower bound proved every
    seeded selection with at most 0.5 deterministic seconds. It changes the search, never the
    model, the optimum or what a status certifies, and with one worker it is deterministic.
    """
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    solver.parameters.max_deterministic_time = SELECTION_DETERMINISTIC_LIMIT
    solver.parameters.max_time_in_seconds = max(0.001, deadline - time.monotonic())
    solver.parameters.use_objective_lb_search = True
    return solver


def _encoding_base(used: int, total_bound: int) -> int:
    """BIG of 5.1: above ``used`` summed totals and above twice one (X3). Never served."""
    return 2 * used * total_bound + 1


class _Calls:
    """Every CP-SAT call of one rule in call order, ``kernel.value``'s stages included (1.5).

    ``stops[i]`` is ``None`` for a decided call, ``MODEL_INVALID`` for a refused one, and
    ``LIMIT_REACHED`` or ``DEADLINE`` for an undecided one. ``LIMIT_REACHED`` only for a call
    this module made whose deterministic time reached its limit while the wall clock still had
    time left; a stage inside ``kernel.value`` exposes no solver and is ``DEADLINE``, as is a
    call the deadline skipped (``NOT_RUN``).
    """

    def __init__(self, deadline: float, seed: int) -> None:
        self.deadline, self.seed = deadline, seed
        self.records: list[SolveRecord] = []
        self.stops: list[str | None] = []
        self.solves = 0
        self.deterministic_times: list[dict] = []
        self.wall_times: list[float] = []

    def _add(self, record: SolveRecord, stop: str | None) -> None:
        self.records.append(record)
        self.stops.append(stop)

    def skip(self, purpose: str, *, world_id: int | None = None) -> None:
        self._add(SolveRecord(purpose, world_id, None, "NOT_RUN"), "DEADLINE")

    def solve(
        self, model: cp_model.CpModel, purpose: str, *, player_id: int | None = None,
        optimum: bool,
    ) -> tuple[str, cp_model.CpSolver | None]:
        """One call of ``_solver``; ``optimum`` makes a FEASIBLE incumbent undecided."""
        if time.monotonic() >= self.deadline:
            self._add(SolveRecord(purpose, None, player_id, "NOT_RUN"), "DEADLINE")
            return "NOT_RUN", None
        solver = _solver(self.deadline, self.seed)
        name = _STATUS.get(solver.solve(model), "UNKNOWN")
        within = time.monotonic() < self.deadline
        spent = float(solver.deterministic_time)
        self.solves += 1
        # CP-SAT's float sum can differ by one ulp between identical solves (ortools 9.15), so
        # the record keeps ten significant digits; the limit test reads ``spent``.
        recorded = float(f"{spent:.10g}")
        self.deterministic_times.append({"status": name, "deterministic_time": recorded})
        self.wall_times.append(float(solver.wall_time))
        if name == "MODEL_INVALID":
            stop = "MODEL_INVALID"
        elif name == "UNKNOWN" or (optimum and name == "FEASIBLE"):
            limited = spent >= SELECTION_DETERMINISTIC_LIMIT and within
            stop = "LIMIT_REACHED" if limited else "DEADLINE"
        else:
            stop = None
        self._add(SolveRecord(purpose, None, player_id, name), stop)
        return name, solver

    def world_least(self, world_id: int, value: KernelValue) -> None:
        """The records of one ``kernel.value`` call: its stages as run, then a stage skipped."""
        self.solves += value.solves
        stages = value.stage_statuses
        for index, name in enumerate(stages):
            undecided = name == "UNKNOWN" or (name == "FEASIBLE" and index > 0)
            last = index == len(stages) - 1
            if name == "MODEL_INVALID":
                stop = "MODEL_INVALID"
            elif last and value.status == "UNKNOWN" and undecided:
                stop = "DEADLINE"
            else:
                stop = None
            self._add(SolveRecord("WORLD_LEAST", world_id, None, name), stop)
        # UNKNOWN whose last stage was decided: the deadline skipped the next stage (or every
        # stage) inside kernel.value, a call not made.
        if value.status == "UNKNOWN" and (not stages or self.stops[-1] is None):
            self.skip("WORLD_LEAST", world_id=world_id)

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


# --------------------------------------------------------------------------- declarations


@dataclass(frozen=True)
class _Declared:
    """The checked declarations every function of this module reads."""

    candidates: tuple[Candidate, ...]  # player_id ascending
    active: tuple[TacticalRequirement, ...]  # the requirements in force, id ascending
    shape: Formation
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    worlds: dict[int, dict[int, dict[str, float | None]]]  # a plain copy, world id ascending


def _declared(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation,
    worlds: Mapping[int, Mapping[int, Mapping[str, float | None]]],
    locked: Collection[int],
    excluded: Collection[int],
    quantization: int,
    seed: int,
) -> tuple[ShortfallKernel, _Declared]:
    """The kernel (its constructor checks the model) and the declarations, every check made."""
    candidates, requirements = tuple(candidates), tuple(requirements)
    kernel = ShortfallKernel(candidates, requirements, formation, quantization=quantization,
                             seed=seed)
    shape = FORMATIONS[formation] if isinstance(formation, str) else formation
    roster = tuple(sorted(candidates, key=lambda p: p.player_id))
    known = {p.player_id for p in roster}

    def ids(chosen: Collection[int]) -> tuple[int, ...]:
        chosen = tuple(chosen)
        if any(type(pid) is not int for pid in chosen) or not set(chosen) <= known:
            raise ValueError(PLAYER_ERROR)
        return tuple(sorted(set(chosen)))

    if not isinstance(worlds, Mapping):
        raise ValueError(WORLDS_ERROR)
    plain: dict[int, dict[int, dict[str, float | None]]] = {}
    for world_id in worlds:
        world = worlds[world_id]
        if type(world_id) is not int or not isinstance(world, Mapping):
            raise ValueError(WORLDS_ERROR)
        table: dict[int, dict[str, float | None]] = {}
        for pid, vector in world.items():
            if type(pid) is not int or not isinstance(vector, Mapping):
                raise ValueError(WORLDS_ERROR)
            for metric, value in vector.items():
                if not isinstance(metric, str) or not (value is None or _bounded(value)):
                    raise ValueError(WORLDS_ERROR)
            table[pid] = dict(vector)
        plain[world_id] = table
    active = tuple(sorted((r for r in requirements if r.active), key=lambda r: r.requirement_id))
    return kernel, _Declared(
        roster, active, shape, ids(locked), ids(excluded), dict(sorted(plain.items()))
    )


def _bounded(value) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and abs(value) <= MAX_MAGNITUDE
    )


def _discard(declared: _Declared) -> tuple[tuple[int, ...], tuple[DiscardedWorld, ...]]:
    """The discard rule of 1.4, the shipped bootstrap's (solver.py:549-564)."""
    needed: dict[int, set[str]] = {}
    for player in declared.candidates:
        if player.player_id in declared.excluded:
            continue
        metrics = {
            r.metric
            for slot in declared.shape.slots
            if _eligible(player, slot)
            for r in declared.active
            if _applies(r, slot.slot_id)
        }
        if metrics:
            needed[player.player_id] = metrics
    used, discarded = [], []
    for world_id, world in declared.worlds.items():
        hole = any(
            world.get(pid, {}).get(metric) is None
            for pid, metrics in needed.items()
            for metric in metrics
        )
        if hole:
            discarded.append(DiscardedWorld(world_id, DISCARD_REASON))
        else:
            used.append(world_id)
    return tuple(used), tuple(discarded)


def _vectors(declared: _Declared, world_id: int) -> _Vectors:
    """V^w: one whole replaced vector for every candidate; absent means every metric None."""
    world = declared.worlds[world_id]
    return {p.player_id: dict(world.get(p.player_id, {})) for p in declared.candidates}


def _pair(shortfalls: Mapping[str, int]) -> LossPair:
    return LossPair(max(shortfalls.values(), default=0), sum(shortfalls.values()))


def _tail(pairs: Mapping[int, LossPair], k: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """The tail by the key of 5.2 (M descending, T descending, world id ascending), cut at
    ``k``, and the worlds outside it with the same pair as its last member, ascending."""
    ordered = sorted(
        pairs, key=lambda w: (-pairs[w].maximum_shortfall, -pairs[w].total_shortfall, w)
    )
    last = pairs[ordered[k - 1]]
    return tuple(ordered[:k]), tuple(sorted(w for w in ordered[k:] if pairs[w] == last))


# --------------------------------------------------------------------------- the rules


def _declared_risk(
    rule: str,
    tail_count: int | None,
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation,
    *,
    worlds: Mapping[int, Mapping[int, Mapping[str, float | None]]],
    world_count: int,
    world_seed: int,
    bootstrap_version: str,
    locked: Collection[int],
    excluded: Collection[int],
    seed: int,
    quantization: int,
    analyze_ties: bool,
    deadline: float,
    provenance: Mapping | None,
) -> RiskSelection:
    """One rule, OR-XI-SPEC 5.6 steps 1 to 7. ``tail_count`` is ``None`` for REGRET."""
    kernel, declared = _declared(
        candidates, requirements, formation, worlds, locked, excluded, quantization, seed
    )
    deadline = ShortfallKernel._deadline(deadline)
    if any(r.hard for r in declared.active):
        raise ValueError(RISK_HARD)
    if type(world_count) is not int or world_count < 1 or world_count != len(declared.worlds):
        raise ValueError(WORLDS_ERROR)
    regret = tail_count is None
    if not regret and (type(tail_count) is not int or not 1 <= tail_count <= world_count):
        raise ValueError(TAIL_COUNT_ERROR)
    if (
        type(world_seed) is not int
        or not isinstance(bootstrap_version, str)
        or type(analyze_ties) is not bool
    ):
        raise ValueError(WORLDS_ERROR)

    # Step 1: the discard rule, before anything is built. k and B are never recomputed.
    used, discarded = _discard(declared)
    sources = source_fingerprints(*(str(Path(__file__).parent / name) for name in _SOURCES))
    world_fingerprint = _fingerprint(declared.worlds)  # every world, discarded ones included
    contract = {
        "version": RISK_VERSION,
        "kernel": kernel.input_contract,
        "rule": rule,
        "tail_count": tail_count,
        "world_count": world_count,
        "world_seed": world_seed,
        "bootstrap_version": bootstrap_version,
        "world_fingerprint": world_fingerprint,
        "locked": list(declared.locked),
        "excluded": list(declared.excluded),
        "analyze_ties": analyze_ties,
        "shortfall_policy": SHORTFALL_POLICY,
        "comparison": COMPARISON,
        "selection_deterministic_limit": SELECTION_DETERMINISTIC_LIMIT,
        "source_fingerprints": sources,
    }
    calls = _Calls(deadline, seed)
    if rule == "MINIMAX_REGRET":
        claim = RISK_REGRET.format(B=world_count)
    elif rule == "WORST_WORLD":
        claim = RISK_WORST.format(B=world_count)
    else:
        claim = RISK_TAIL.format(B=world_count, k=tail_count)

    def finish(
        status: str,
        tokens: tuple[str, str | None],
        *,
        reasons: tuple[str, ...] = (),
        undecided: tuple[int, ...] = (),
        membership: MembershipBlock | None = None,
        lineup: Lineup = (),
        losses: tuple[WorldLoss, ...] = (),
        tail: tuple[tuple[int, ...], tuple[int, ...]] = ((), ()),
        tail_sum: TailSums | None = None,
        binding: tuple[int, ...] = (),
        point_loss: LossPair | None = None,
        point_sums: tuple[tuple[str, float | None], ...] = (),
    ) -> RiskSelection:
        completeness, stopped_by = tokens
        if not analyze_ties:
            membership = MembershipBlock((), "NOT_REQUESTED")
        elif membership is None:
            # No selection: vacuous and EXACT when none can exist, else the selection's tokens.
            proved = status in ("UNFIELDABLE", "NOT_EVALUABLE")
            membership = MembershipBlock((), "EXACT" if proved else completeness)
        record = {
            **scrub_lineage(provenance),
            "risk_version": RISK_VERSION,
            "kernel_version": KERNEL_VERSION,
            "shortfall_policy": SHORTFALL_POLICY,
            "quantization": quantization,
            "selection_deterministic_limit": SELECTION_DETERMINISTIC_LIMIT,
            "per_solve_deterministic_limit": PER_SOLVE_DETERMINISTIC_LIMIT,
            "input_contract": contract,
            "input_fingerprint": fingerprint({"version": RISK_VERSION, "contract": contract}),
            "source_fingerprints": sources,
            # Times are not encodings and enter no hash (1.5); wall times are diagnostic only.
            # Only the calls this module makes: kernel.value exposes no solver.
            "risk_solve_deterministic_times": list(calls.deterministic_times),
            "risk_solve_wall_times": list(calls.wall_times),
        }
        certificate = RiskCertificate(
            rule=rule,
            tail_count=tail_count,
            world_count=world_count,
            used_world_ids=used,
            discarded_worlds=discarded,
            discarded_world_count=len(discarded),
            undecided_world_ids=undecided,
            world_fingerprint=world_fingerprint,
            world_seed=world_seed,
            solver_seed=seed,
            bootstrap_version=bootstrap_version,
            quantization=quantization,
            shortfall_policy=SHORTFALL_POLICY,
            comparison=COMPARISON,
            selection_deterministic_limit=SELECTION_DETERMINISTIC_LIMIT,
            world_least_deterministic_limit=PER_SOLVE_DETERMINISTIC_LIMIT,
            solves=calls.solves,
            records=tuple(calls.records),
            growth=None if regret else RISK_GROWTH.format(B=world_count, U=len(used)),
            completeness=completeness,
            stopped_by=stopped_by,
        )
        return RiskSelection(
            rule=rule,
            tail_count=tail_count,
            status=status,
            lineup=lineup,
            world_losses=losses,
            tail_world_ids=tail[0],
            tail_boundary_ties=tail[1],
            tail_sum=tail_sum,
            binding_world_ids=binding,
            point_loss=point_loss,
            point_sums=point_sums,
            membership=membership,
            certificate=certificate,
            claim=claim,
            non_claim=RISK_NON_CLAIM,
            reasons=reasons,
            provenance=record,
        )

    exact = ("EXACT", None)
    if not used or (not regret and len(used) < tail_count):
        return finish("NOT_EVALUABLE", exact, reasons=(RISK_NOT_EVALUABLE,))

    # Step 2: the backgrounds and the tables of every used world, then the guard. Only β is
    # solved; each β_w serves its keys and its tables.
    vectors = {w: _vectors(declared, w) for w in used}
    background = kernel._background(declared.excluded, declared.locked, None, (), vectors[used[0]])
    tables: dict[int, _Tables] = {}
    for w in used:
        own = (
            background
            if w == used[0]
            else kernel._background(declared.excluded, declared.locked, None, (), vectors[w])
        )
        if own.variables.keys() != background.variables.keys():
            raise RuntimeError("two used worlds admit different keys (the lemma of 1.4)")
        tables[w] = kernel._tables(own, conservative=False)
    point = kernel._background(declared.excluded, declared.locked, None, (), None)
    point_tables = kernel._tables(point, conservative=False)
    # U^w_r = max(0, t_r - L^w_r), L^w_r the sum of the negative coefficients over the keys.
    deficit_bounds = {
        w: [
            max(0, target - sum(min(0, c) for c in coefficients.values()))
            for coefficients, target in tables[w].values()
        ]
        for w in used
    }
    total_bound = max(sum(row) for row in deficit_bounds.values())
    largest_bound = max(max(row, default=0) for row in deficit_bounds.values())
    terms = 3 if regret else tail_count + len(used) + 2
    if terms * _encoding_base(len(used), total_bound) * (largest_bound + 1) >= (
        EXACT_OBJECTIVE_LIMIT
    ):
        raise ValueError(RISK_OVERFLOW)
    if time.monotonic() >= deadline:  # as the kernel: no solve, even where a reason exists
        if regret:
            for w in used:
                calls.skip("WORLD_LEAST", world_id=w)
        else:
            calls.skip("SELECTION")
        return finish("UNKNOWN", calls.tokens(), undecided=used if regret else ())
    if background.model is None:
        return finish("UNFIELDABLE", exact, reasons=background.reasons)

    least: dict[int, KernelValue] = {}
    if regret:
        # Step 5, first part: BALANCE's certified least pair in every used world.
        for w in used:
            least[w] = kernel.value(
                excluded=declared.excluded, locked=declared.locked, values=vectors[w],
                deadline=deadline,
            )
            calls.world_least(w, least[w])
        outcomes = {value.status for value in least.values()}
        if "UNFIELDABLE" in outcomes:
            if "CERTIFIED" in outcomes:
                raise RuntimeError("a world proved empty beside another world's verified XI")
            # The proof supersedes every other world's undecided or refused least (1.5).
            return finish("UNFIELDABLE", exact, reasons=background.reasons or (UNFIELDABLE_PROVED,))
        if "MODEL_INVALID" in outcomes:
            return finish("MODEL_INVALID", calls.tokens())
        undecided = tuple(w for w in used if least[w].status != "CERTIFIED")
        if undecided:
            return finish("UNKNOWN", calls.tokens(), undecided=undecided)

    selected = _select(
        kernel, background, used, tables, deficit_bounds, total_bound, largest_bound,
        tail_count, least, calls,
    )
    if selected.status == "UNFIELDABLE":
        return finish("UNFIELDABLE", exact, reasons=background.reasons or (UNFIELDABLE_PROVED,))
    if selected.status != "CERTIFIED":
        return finish(selected.status, calls.tokens())

    lineup = selected.lineup
    pairs = selected.pairs
    losses = tuple(
        WorldLoss(w, pairs[w], LossPair(least[w].maximum, least[w].total) if regret else None)
        for w in used
    )
    membership = None
    if analyze_ties:
        start = len(calls.stops)
        rows = _membership(declared, background, lineup, selected.level, calls)
        membership = MembershipBlock(rows, calls.tokens(start)[0])
    if regret:
        gaps = {
            w: (
                pairs[w].maximum_shortfall - least[w].maximum,
                pairs[w].total_shortfall - least[w].total,
            )
            for w in used
        }
        top = max(gaps.values())
        tail, tail_sum = ((), ()), None
        binding = tuple(w for w in used if gaps[w] == top)
    else:
        tail = _tail(pairs, tail_count)
        tail_sum = TailSums(
            sum(pairs[w].maximum_shortfall for w in tail[0]),
            sum(pairs[w].total_shortfall for w in tail[0]),
        )
        binding = ()
    return finish(
        "CERTIFIED",
        calls.tokens(),
        membership=membership,
        lineup=lineup,
        losses=losses,
        tail=tail,
        tail_sum=tail_sum,
        binding=binding,
        point_loss=(
            _pair(kernel._shortfalls(point_tables, lineup))
            if all((pid, sid) in point.variables for sid, pid in lineup)
            else None
        ),
        point_sums=_point_sums(declared, lineup),
    )


@dataclass(frozen=True)
class _Selected:
    status: str  # CERTIFIED | UNFIELDABLE | UNKNOWN | MODEL_INVALID
    lineup: Lineup
    pairs: dict[int, LossPair]
    level: cp_model.CpModel | None  # the model of the rule's level set, no objective


def _select(
    kernel: ShortfallKernel,
    background: _Background,
    used: tuple[int, ...],
    tables: Mapping[int, _Tables],
    deficit_bounds: Mapping[int, list[int]],
    total_bound: int,
    largest_bound: int,
    tail_count: int | None,
    least: Mapping[int, KernelValue],
    calls: _Calls,
) -> _Selected:
    """Steps 3, 4 or 5, and 6: the epigraph, the rule's objective, the selection solve and its
    re-evaluation. ``big`` and every encoding stay local to this function."""
    big = _encoding_base(len(used), total_bound)
    model = background.model.clone()
    largest, summed = {}, {}
    for w in used:
        # Step 3: d_r >= t_r - f_r(x), M^w >= d_r, T^w = sum_r d_r; a linear epigraph.
        largest[w] = model.new_int_var(0, largest_bound, f"largest_{w}")
        shortfalls = []
        for index, (coefficients, target) in enumerate(tables[w].values()):
            shortfall = model.new_int_var(0, deficit_bounds[w][index], f"shortfall_{w}_{index}")
            model.add(shortfall + kernel._expression(background, coefficients) >= target)
            model.add(largest[w] >= shortfall)
            shortfalls.append(shortfall)
        summed[w] = sum(shortfalls)
    if tail_count is not None:
        # Step 4: Φ = k eta + sum_w u_w with u_w >= E^w - eta, eta and u_w split (5.1).
        level_high = model.new_int_var(0, largest_bound, "tail_level_high")
        level_low = model.new_int_var(0, big - 1, "tail_level_low")
        excess = []
        for w in used:
            over_high = model.new_int_var(0, largest_bound, f"tail_excess_high_{w}")
            over_low = model.new_int_var(0, big - 1, f"tail_excess_low_{w}")
            model.add(
                big * over_high + over_low
                >= big * (largest[w] - level_high) + (summed[w] - level_low)
            )
            excess.append(big * over_high + over_low)
        objective = tail_count * (big * level_high + level_low) + sum(excess)
    else:
        # Step 5: rho >= E^w - E*^w for every used world, rho split (5.1).
        gap_high = model.new_int_var(0, largest_bound, "regret_high")
        gap_low = model.new_int_var(0, big - 1, "regret_low")
        for w in used:
            reference = big * least[w].maximum + least[w].total
            model.add(big * gap_high + gap_low >= big * largest[w] + summed[w] - reference)
        objective = big * gap_high + gap_low

    # Step 6: only OPTIMAL is a selection; INFEASIBLE proves that no XI exists.
    selection = model.clone()
    selection.minimize(objective)
    name, solver = calls.solve(selection, "SELECTION", optimum=True)
    if name == "INFEASIBLE":
        if tail_count is None:
            raise RuntimeError("an INFEASIBLE selection contradicts a verified world optimum")
        return _Selected("UNFIELDABLE", (), {}, None)
    if name == "MODEL_INVALID":
        return _Selected("MODEL_INVALID", (), {}, None)
    if name != "OPTIMAL":
        return _Selected("UNKNOWN", (), {}, None)
    lineup = kernel._witness(background, solver)
    if not kernel._admissible(background, lineup):
        raise RuntimeError("the selected lineup is not an XI of the declared model")
    pairs = {w: _pair(kernel._shortfalls(tables[w], lineup)) for w in used}
    encoded = {w: big * pairs[w].maximum_shortfall + pairs[w].total_shortfall for w in used}
    if tail_count is not None:
        optimum = sum(sorted(encoded.values(), reverse=True)[:tail_count])
    else:
        optimum = max(encoded[w] - big * least[w].maximum - least[w].total for w in used)
    # The one Python equality check: an exact int of the expression the solve optimised;
    # objective_value is never read.
    if optimum != solver.value(objective):
        raise RuntimeError("the selection failed its integer re-evaluation")
    # Step 7's model: with the split variables free, exactly the XIs whose objective is the
    # optimum.
    level = model.clone()
    level.add(objective <= optimum)
    return _Selected("CERTIFIED", lineup, pairs, level)


def _membership(
    declared: _Declared,
    background: _Background,
    lineup: Lineup,
    level: cp_model.CpModel,
    calls: _Calls,
) -> tuple[MembershipRow, ...]:
    """Step 7: the opposite solve of kernel.membership for each candidate, id ascending.

    INFEASIBLE is the only source of ``necessary=True`` and of ``possible=False``; an undecided
    or refused solve leaves ``None``. Excluded players and players with no admissible key are
    ``(False, False)``, locked players ``(True, True)``, without a solve.
    """
    chosen = {pid for _, pid in lineup}
    rows = []
    for player in declared.candidates:
        pid = player.player_id
        choices = [v for (owner, _), v in background.variables.items() if owner == pid]
        if not choices:
            rows.append(MembershipRow(pid, False, False))
            continue
        if pid in declared.locked:
            rows.append(MembershipRow(pid, True, True))
            continue
        opposite = level.clone()
        opposite.add(sum(choices) == (0 if pid in chosen else 1))
        name, _ = calls.solve(opposite, "MEMBERSHIP", player_id=pid, optimum=False)
        witness, ruled_out = name in _WITNESS, name == "INFEASIBLE"
        decided = False if witness else True if ruled_out else None
        if pid in chosen:
            rows.append(MembershipRow(pid, True, decided))
        else:
            rows.append(MembershipRow(pid, None if decided is None else not decided, False))
    return tuple(rows)


def _point_sums(
    declared: _Declared, lineup: Lineup
) -> tuple[tuple[str, float | None], ...]:
    """Each exact S_r at the point values as the nearest float, or None where a key the
    lineup uses for r has no point value."""
    own = {p.player_id: p.values for p in declared.candidates}
    rows = []
    for r in declared.active:
        values = [own[pid].get(r.metric) for sid, pid in lineup if _applies(r, sid)]
        if any(value is None for value in values):
            rows.append((r.requirement_id, None))
        else:
            rows.append((r.requirement_id, float(sum(map(Fraction, values), Fraction()))))
    return tuple(rows)


# --------------------------------------------------------------------------- public


def tail_selection(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    worlds: Mapping[int, Mapping[int, Mapping[str, float | None]]],
    world_count: int,
    tail_count: int,
    world_seed: int,
    bootstrap_version: str,
    locked: Collection[int] = (),
    excluded: Collection[int] = (),
    seed: int = 20260906,
    quantization: int = QUANTIZATION,
    analyze_ties: bool = True,
    deadline: float,
    provenance: Mapping | None = None,
) -> RiskSelection:
    """TAIL(k of B): an XI whose ``k`` highest-loss used worlds have the least summed loss.

    ``world_count`` must equal ``len(worlds)``; ``tail_count`` lies in ``1..world_count`` (the
    menu is the API's). ``world_seed`` and ``bootstrap_version`` are copied into the
    certificate. ``deadline`` is a ``time.monotonic()`` value. Every refusal is raised before
    the deadline is read or a solve is made.
    """
    return _declared_risk(
        "TAIL", tail_count, candidates, requirements, formation, worlds=worlds,
        world_count=world_count, world_seed=world_seed, bootstrap_version=bootstrap_version,
        locked=locked, excluded=excluded, seed=seed, quantization=quantization,
        analyze_ties=analyze_ties, deadline=deadline, provenance=provenance,
    )


def worst_world_selection(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    worlds: Mapping[int, Mapping[int, Mapping[str, float | None]]],
    world_count: int,
    world_seed: int,
    bootstrap_version: str,
    locked: Collection[int] = (),
    excluded: Collection[int] = (),
    seed: int = 20260906,
    quantization: int = QUANTIZATION,
    analyze_ties: bool = True,
    deadline: float,
    provenance: Mapping | None = None,
) -> RiskSelection:
    """WORST_WORLD: TAIL with ``k = 1``, labelled as the extreme of the tail family for ``B``."""
    return _declared_risk(
        "WORST_WORLD", 1, candidates, requirements, formation, worlds=worlds,
        world_count=world_count, world_seed=world_seed, bootstrap_version=bootstrap_version,
        locked=locked, excluded=excluded, seed=seed, quantization=quantization,
        analyze_ties=analyze_ties, deadline=deadline, provenance=provenance,
    )


def minimax_regret_selection(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    worlds: Mapping[int, Mapping[int, Mapping[str, float | None]]],
    world_count: int,
    world_seed: int,
    bootstrap_version: str,
    locked: Collection[int] = (),
    excluded: Collection[int] = (),
    seed: int = 20260906,
    quantization: int = QUANTIZATION,
    analyze_ties: bool = True,
    deadline: float,
    provenance: Mapping | None = None,
) -> RiskSelection:
    """MINIMAX_REGRET: an XI whose largest gap to each used world's least pair is least.

    Each world's least pair is ``kernel.value`` on that world (BALANCE, ADR-0020). A world
    whose least is not certified is never set aside: the rule is then UNKNOWN.
    """
    return _declared_risk(
        "MINIMAX_REGRET", None, candidates, requirements, formation, worlds=worlds,
        world_count=world_count, world_seed=world_seed, bootstrap_version=bootstrap_version,
        locked=locked, excluded=excluded, seed=seed, quantization=quantization,
        analyze_ties=analyze_ties, deadline=deadline, provenance=provenance,
    )


def declared_risk_selection(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    rule: str,
    tail_count: int | None = None,
    **options,
) -> RiskSelection:
    """One of ``RULES`` by name. WORST_WORLD accepts ``tail_count`` None or 1, TAIL requires
    one, MINIMAX_REGRET accepts only None; ``options`` are the rule function's keywords."""
    if rule == "WORST_WORLD":
        if tail_count is not None and (type(tail_count) is not int or tail_count != 1):
            raise ValueError(TAIL_COUNT_ERROR)
        return worst_world_selection(candidates, requirements, formation, **options)
    if rule == "TAIL":
        if tail_count is None:
            raise ValueError(TAIL_COUNT_ERROR)
        return tail_selection(candidates, requirements, formation, tail_count=tail_count,
                              **options)
    if rule == "MINIMAX_REGRET":
        if tail_count is not None:
            raise ValueError(TAIL_COUNT_ERROR)
        return minimax_regret_selection(candidates, requirements, formation, **options)
    raise ValueError(RULE_ERROR)


def world_losses(
    lineup: Lineup,
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation,
    *,
    worlds: Mapping[int, Mapping[int, Mapping[str, float | None]]],
    locked: Collection[int] = (),
    excluded: Collection[int] = (),
    quantization: int = QUANTIZATION,
) -> tuple[WorldLoss, ...]:
    """The pair of ``lineup`` in every used world, ascending, in pure Python (no solver).

    An independent re-evaluation: the discard rule of 1.4 applied to ``worlds``, then ``_q``
    shortfalls summed from each world's vectors, ``world_least`` ``None``. ``lineup`` must be
    an XI of the used worlds under ``locked`` and ``excluded`` (with no used world, under the
    candidates' own vectors); anything else is ``ValueError(LINEUP_ERROR)``.
    """
    _, declared = _declared(
        candidates, requirements, formation, worlds, locked, excluded, quantization, 20260906
    )
    used, _ = _discard(declared)
    if used:
        tables = [_vectors(declared, w) for w in used]
    else:
        tables = [{p.player_id: dict(p.values) for p in declared.candidates}]
    if not _is_xi(lineup, declared, tables):
        raise ValueError(LINEUP_ERROR)
    rows = []
    for w, vectors in zip(used, tables[: len(used)], strict=True):
        shortfalls = {}
        for r in declared.active:
            supply = sum(
                _half_even(vectors[pid][r.metric], r.normalizer, quantization)
                for sid, pid in lineup
                if _applies(r, sid)
            )
            target = _half_even(r.minimum, r.normalizer, quantization)
            shortfalls[r.requirement_id] = max(0, target - supply)
        rows.append(WorldLoss(w, _pair(shortfalls), None))
    return tuple(rows)


def _half_even(value: float, normalizer: float, quantization: int) -> int:
    try:
        return _q(value, normalizer, quantization)
    except OverflowError as exc:  # the float quotient is infinite, as kernel._tables maps it
        raise ValueError("normalized requirement coefficient is too large") from exc


def _is_xi(lineup, declared: _Declared, tables: Sequence[_Vectors]) -> bool:
    """Every slot filled once in formation order, every pair an admissible key under each
    table, every locked player in, no excluded one: checked without a solver."""
    slots: dict[str, Slot] = {slot.slot_id: slot for slot in declared.shape.slots}
    by_id = {p.player_id: p for p in declared.candidates}
    try:
        pairs = [(sid, pid) for sid, pid in lineup]
    except (TypeError, ValueError):
        return False
    players = [pid for _, pid in pairs]
    if [sid for sid, _ in pairs] != list(slots) or len(set(players)) != len(players):
        return False
    for sid, pid in pairs:
        if type(pid) is not int or pid not in by_id or pid in declared.excluded:
            return False
        if not _eligible(by_id[pid], slots[sid]):
            return False
        for vectors in tables:
            if any(
                vectors[pid].get(r.metric) is None
                for r in declared.active
                if _applies(r, sid)
            ):
                return False
    return set(declared.locked) <= set(players)
