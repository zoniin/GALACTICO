"""Exact shortfall and satisfiability values of one XI model. Nothing here is a football claim.

Claim: for a declared candidate set, formation and requirements, the least declared shortfall
(maximum, then total) and the satisfiability of the declared minima, each with its proof status.
Non-claim: no value here estimates what a team would produce, and UNKNOWN is never evidence
that an XI does not exist. Shortfalls use the shipped half-even integers of solve_xi; hard
statements use the conservative floor/ceil integers of the hard-floor query. No third policy.

How a shortfall value is reached (three bounded solves, no ``add_max_equality``):

    Z   feasibility  background and f_r(x) >= T_r for every r         witness => (0, 0)
    S1  minimise z   background and z >= T_r - f_r(x), z in [1, U]
    S2  minimise sum d_r   background and d_r >= T_r - f_r(x), d_r in [0, z*]

Zero bounds both components below, so a Z witness certifies (0, 0). If Z is infeasible every
XI has a maximum of at least 1, so ``z >= 1`` loses nothing; U bounds every attainable
shortfall, so an infeasible S1 means no XI exists at all. ``d_r <= z*`` keeps S2 inside the
stage-one level set. The pair therefore equals solve_xi's (max_deficit, total_deficit).

Statuses. ``UNFIELDABLE`` is a statement about the gated integer model: no assignment fills
every slot under eligibility, measurement, exclusions, locks and pins. It is reported either
from a solver proof or from a reason that is a proof by construction (an empty slot, a player
both locked and excluded, a lock or pin with no admissible assignment). A deadline that has
already passed always answers ``UNKNOWN`` without a solve, even when such a reason exists.
A FEASIBLE incumbent of an optimisation stage is not a value and is reported ``UNKNOWN``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from importlib.metadata import version
from pathlib import Path

from ortools.sat.python import cp_model

from ...domain.provenance import EvidenceClass
from ..xi.domain import FORMATIONS, Candidate, Formation, Slot, TacticalRequirement
from ..xi.solver import QUANTIZATION, _applies, _eligible, _q
from ..xi.tradeoffs import (
    FLOOR_POLICY,
    MAX_EXPRESSION_MAGNITUDE,
    MAX_MAGNITUDE,
    _finite,
    _scaled,
)

__all__ = [
    "HARD_POLICY",
    "KERNEL_VERSION",
    "MAX_EXPRESSION_MAGNITUDE",
    "MAX_MAGNITUDE",
    "PER_SOLVE_DETERMINISTIC_LIMIT",
    "QUANTIZATION",
    "SHORTFALL_POLICY",
    "FloorValue",
    "KernelValue",
    "Membership",
    "ShortfallKernel",
    "compose_evidence",
    "fingerprint",
    "scrub_lineage",
    "source_fingerprints",
]

KERNEL_VERSION = "linear-epigraph-shortfall-kernel-v1"
SHORTFALL_POLICY = "half-even after float division by the declared normalizer (xi.solver._q)"
HARD_POLICY = FLOOR_POLICY
# CP-SAT deterministic time: the binding per-solve limit, so a status does not depend on load.
PER_SOLVE_DETERMINISTIC_LIMIT = 10.0

_PACKAGE_PARENT = Path(__file__).resolve().parents[3]
_SOURCES = ("kernel.py", "../xi/solver.py", "../xi/tradeoffs.py", "../xi/domain.py")
_STATUS = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.UNKNOWN: "UNKNOWN",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
}
_WITNESS = ("OPTIMAL", "FEASIBLE")
# XI's legacy strings on the domain ladder (ROOT 2.5 O13). UNAVAILABLE is not a class.
_LADDER = {
    "MEASURED": EvidenceClass.ESTIMATED,
    "HEURISTIC": EvidenceClass.HEURISTIC,
    "RESEARCH": EvidenceClass.EXPERIMENTAL,
}
# The local ``prior_certificate_keys`` of xi/tradeoffs.py, which cannot be imported. A test
# reads that source and asserts the two sets are the same object in content.
_PRIOR_CERTIFICATE_KEYS = frozenset(
    {
        "mode",
        "objective_vector",
        "objective_certificate",
        "objective_policy",
        "alternative_search",
        "equivalent_players",
        "selection_frequencies",
        "normalized_aggregation_error_bound",
        "rounding",
        "elapsed_seconds",
        "floor_certificates",
        "floor_conservatism_bounds",
        "input_contract",
        "infeasibility_explanation",
        "unavailable_assignments",
    }
)
_CERTIFICATE_PREFIXES = (
    "solver_",
    "tie_",
    "stress_",
    "brief_",
    "depth_",
    "injection_",
    "retention_",
    "frontier_",
    "risk_",
    "conflict_",
    "ceiling_",
)

Lineup = tuple[tuple[str, int], ...]
_Key = tuple[int, str]
_Tables = dict[str, tuple[dict[_Key, int], int]]


@dataclass(frozen=True)
class KernelValue:
    """Least declared shortfall of one model, in integer units of 1 / quantization."""

    status: str  # CERTIFIED | UNFIELDABLE | UNKNOWN | MODEL_INVALID
    maximum: int | None  # None unless CERTIFIED
    total: int | None
    lineup: Lineup  # (slot_id, player_id) witness in formation order; () unless CERTIFIED
    stage_statuses: tuple[str, ...]  # CP-SAT status names of Z, S1, S2 as run
    solves: int
    reasons: tuple[str, ...] = ()  # diagnostic only
    quantization: int = QUANTIZATION  # the scale the two integers are expressed in
    # sha256 of the model and the declarations a CERTIFIED value was computed under; "" otherwise
    computed_under: str = ""

    @property
    def objective_vector(self) -> tuple[float, float] | None:
        """(maximum / quantization, total / quantization); None unless CERTIFIED."""
        if self.status != "CERTIFIED" or self.maximum is None or self.total is None:
            return None
        return (self.maximum / self.quantization, self.total / self.quantization)


@dataclass(frozen=True)
class FloorValue:
    """Whether every active minimum can be met at once, in the conservative integer model."""

    status: str  # SATISFIABLE | NOT_SATISFIABLE | UNFIELDABLE | UNKNOWN | MODEL_INVALID
    lineup: Lineup
    raw_sums: tuple[tuple[str, float], ...]  # (requirement_id, exact witness sum as float)
    solves: int


@dataclass(frozen=True)
class Membership:
    """Whether a player is in some / in every XI of the certified least-shortfall level set."""

    possible: bool | None
    necessary: bool | None


@dataclass
class _Background:
    """The assignment constraints of one evaluation; ``model`` is None when reasons prove
    that no assignment exists."""

    model: cp_model.CpModel | None
    variables: dict[_Key, cp_model.IntVar]
    slots: tuple[Slot, ...]
    vectors: dict[int, Mapping[str, float | None]]
    locked: frozenset[int]
    pinned: dict[int, str]
    reasons: tuple[str, ...]
    declared: dict  # canonical, JSON-safe; a replacement equal to the own vector is no change


class _Run:
    """Solver accounting for one method call."""

    def __init__(self, deadline: float, seed: int) -> None:
        self.deadline, self.seed = deadline, seed
        self.statuses: list[str] = []

    def solve(self, model: cp_model.CpModel) -> tuple[str, cp_model.CpSolver | None]:
        # A passed deadline is UNKNOWN without a solver call (tradeoffs.py:332-334).
        if time.monotonic() >= self.deadline:
            return "UNKNOWN", None
        solver = _solver(self.deadline, self.seed)
        name = _STATUS.get(solver.solve(model), "UNKNOWN")
        self.statuses.append(name)
        return name, solver


def _solver(deadline: float, seed: int) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    solver.parameters.max_deterministic_time = PER_SOLVE_DETERMINISTIC_LIMIT
    solver.parameters.max_time_in_seconds = max(0.001, deadline - time.monotonic())
    return solver


def fingerprint(payload) -> str:
    """sha256 of the canonical JSON of ``payload`` (sorted keys, compact, no NaN)."""
    try:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("provenance and inputs must be finite JSON-serializable values") from exc
    return hashlib.sha256(serialized.encode()).hexdigest()


def source_fingerprints(*module_files: str) -> dict[str, str]:
    """LF-normalised sha256 of each source file, keyed by its path below the repository root.

    A file outside the repository is keyed by its base name.
    """
    hashes = {}
    for module_file in module_files:
        path = Path(module_file).resolve()
        try:
            key = path.relative_to(_PACKAGE_PARENT).as_posix()
        except ValueError:
            key = path.name
        hashes[key] = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return dict(sorted(hashes.items()))


def scrub_lineage(provenance: Mapping | None) -> dict:
    """Keep data lineage, drop every prior certification.

    A re-solve inherits where its numbers came from, never an earlier solve's status, bounds,
    tie analysis or resampling results. ``bootstrap_version`` is lineage and is kept.
    """
    kept = {}
    for key, value in dict(provenance or {}).items():
        if isinstance(key, str) and (
            key in _PRIOR_CERTIFICATE_KEYS
            or key.startswith(_CERTIFICATE_PREFIXES)
            or (key.startswith("bootstrap_") and key != "bootstrap_version")
        ):
            continue
        kept[key] = value
    return kept


def compose_evidence(
    requirements: Sequence[TacticalRequirement], *extra: EvidenceClass
) -> dict:
    """Evidence classes of a number built from these requirements under an eligibility policy.

    Only active requirements contribute: an inactive one supplies no number. Eligibility is a
    declared policy (HEURISTIC), so the composed class is never stronger than HEURISTIC.
    ``declared_inputs`` is returned empty for the caller to fill: a declared input is not
    evidence and is never coerced into a class.
    """
    for item in extra:
        if not isinstance(item, EvidenceClass):
            raise ValueError("extra evidence must be EvidenceClass members")
    per_requirement = {
        r.requirement_id: _LADDER[r.evidence_class]
        for r in sorted(requirements, key=lambda r: r.requirement_id)
        if r.active
    }
    composed = max([*per_requirement.values(), EvidenceClass.HEURISTIC, *extra])
    return {
        "per_requirement": {rid: cls.name for rid, cls in per_requirement.items()},
        "eligibility": EvidenceClass.HEURISTIC.name,
        "composed": EvidenceClass(composed).name,
        "declared_inputs": [],
    }


def _at_least(model: cp_model.CpModel, expression, lower: int) -> None:
    if isinstance(expression, int):
        if expression < lower:
            model.add_bool_or([])
        return
    model.add(expression >= lower)


class ShortfallKernel:
    """One declared XI model; every method evaluates it under per-call declarations.

    ``excluded``, ``locked``, ``pinned``, ``vacant`` and ``values`` never change the kernel:
    each call builds its own model, so calls are independent and order-free.
    """

    def __init__(
        self,
        candidates: Sequence[Candidate],
        requirements: Sequence[TacticalRequirement],
        formation: str | Formation = "4-3-3",
        *,
        quantization: int = QUANTIZATION,
        seed: int = 20260906,
    ) -> None:
        if type(seed) is not int or not 0 <= seed < 2**31:
            raise ValueError("seed must be an integer between 0 and 2**31 - 1")
        if type(quantization) is not int or not 1 <= quantization <= 10**9:
            raise ValueError("quantization must be an integer between 1 and 1e9")
        if isinstance(formation, str):
            if formation not in FORMATIONS:
                raise ValueError(f"unknown formation: {formation}")
            formation = FORMATIONS[formation]
        if not isinstance(formation, Formation):
            raise ValueError("formation must be a known name or Formation")
        slot_ids = [slot.slot_id for slot in formation.slots]
        if not slot_ids or len(slot_ids) != len(set(slot_ids)):
            raise ValueError("formation slots must be nonempty and unique")
        for slot in formation.slots:
            _finite(slot.x, "slot x")
            _finite(slot.y, "slot y")
        candidates = tuple(candidates)
        ids = [player.player_id for player in candidates]
        if any(type(pid) is not int for pid in ids) or len(ids) != len(set(ids)):
            raise ValueError("candidate player IDs must be unique integers")
        candidates = tuple(sorted(candidates, key=lambda player: player.player_id))
        requirements = tuple(sorted(requirements, key=lambda r: r.requirement_id))
        if len(requirements) != len({r.requirement_id for r in requirements}):
            raise ValueError("requirement IDs must be unique")
        for player in candidates:
            if type(player.minutes) is not int or player.minutes < 0:
                raise ValueError("candidate minutes must be a nonnegative integer")
            for metric, value in player.values.items():
                if value is not None:
                    _finite(value, f"candidate metric {metric}")
        for requirement in requirements:
            _finite(requirement.minimum, "requirement minimum")
            _finite(requirement.normalizer, "requirement normalizer", positive=True)
            if set(requirement.slot_ids) - set(slot_ids):
                raise ValueError(f"{requirement.requirement_id}: unknown requirement slot")
            if len(requirement.slot_ids) != len(set(requirement.slot_ids)):
                raise ValueError("requirement slots must be unique")
        self._candidates = candidates
        self._requirements = requirements
        self._active = tuple(r for r in requirements if r.active)
        self._formation = formation
        self._slot_ids = frozenset(slot_ids)
        self._ids = tuple(sorted(ids))
        self._known = frozenset(ids)
        self._quantization = quantization
        self._seed = seed
        self._contract: dict | None = None
        self._model_hash: str | None = None

    # ------------------------------------------------------------------ inputs

    def _model(self) -> dict:
        """The declared model alone, canonical: what a value is a value of."""
        return {
            "candidates": [
                {
                    "player_id": p.player_id,
                    "name": p.name,
                    "position": p.position,
                    "values": {k: p.values[k] for k in sorted(p.values)},
                    "minutes": p.minutes,
                    "eligible_slots": None
                    if p.eligible_slots is None
                    else list(p.eligible_slots),
                }
                for p in self._candidates
            ],
            "requirements": [
                {
                    "requirement_id": r.requirement_id,
                    "label": r.label,
                    "metric": r.metric,
                    "minimum": r.minimum,
                    "normalizer": r.normalizer,
                    "slot_ids": list(r.slot_ids),
                    "evidence_class": r.evidence_class,
                    "hard": r.hard,
                    "status": r.status,
                    "source": r.source,
                }
                for r in self._requirements
            ],
            "formation": {
                "formation_id": self._formation.formation_id,
                "slots": [
                    {
                        "slot_id": s.slot_id,
                        "label": s.label,
                        "allowed_positions": list(s.allowed_positions),
                        "x": s.x,
                        "y": s.y,
                    }
                    for s in self._formation.slots
                ],
            },
            "quantization": self._quantization,
        }

    @property
    def input_contract(self) -> dict:
        """Canonical, JSON-safe statement of the model; independent of input order.

        Per-call declarations (exclusions, locks, pins, vacancies, value replacements) are not
        part of it: the caller hashes them beside it.
        """
        if self._contract is None:
            here = Path(__file__)
            self._contract = {
                "kernel_version": KERNEL_VERSION,
                **self._model(),
                "seed": self._seed,
                "shortfall_rounding": SHORTFALL_POLICY,
                "hard_rounding": HARD_POLICY,
                "per_solve_deterministic_limit": PER_SOLVE_DETERMINISTIC_LIMIT,
                "wall_clock_limit": "max(0.001, deadline - now) seconds per solve",
                "source_fingerprints": source_fingerprints(
                    *(str(here.parent / name) for name in _SOURCES)
                ),
                "solver_package_version": version("ortools"),
            }
        return copy.deepcopy(self._contract)

    def _player_ids(self, ids: Collection[int], name: str) -> frozenset[int]:
        ids = tuple(ids)
        if any(type(pid) is not int for pid in ids):
            raise ValueError(f"{name} player IDs must be integers")
        unknown = set(ids) - self._known
        if unknown:
            raise ValueError(f"unknown {name} player IDs: {sorted(unknown)}")
        return frozenset(ids)

    @staticmethod
    def _deadline(deadline: float) -> float:
        if (
            isinstance(deadline, bool)
            or not isinstance(deadline, (int, float))
            or math.isnan(deadline)
        ):
            raise ValueError("deadline must be a time.monotonic() value")
        return deadline

    def _background(
        self,
        excluded: Collection[int],
        locked: Collection[int],
        pinned: Mapping[int, str] | None,
        vacant: Collection[str],
        values: Mapping[int, Mapping[str, float | None]] | None,
    ) -> _Background:
        excluded_ids = self._player_ids(excluded, "excluded")
        locked_ids = self._player_ids(locked, "locked")
        pins = dict(pinned or {})
        self._player_ids(pins, "pinned")
        if set(pins.values()) - self._slot_ids:
            raise ValueError("pinned slots must be slots of the formation")
        vacant_ids = frozenset(vacant)
        if vacant_ids - self._slot_ids:
            raise ValueError("vacant slots must be slots of the formation")
        # Whole-vector replacement, never a merge (solver.py:550). A player absent from
        # ``values`` keeps his own vector; ids outside this model are not about it.
        vectors: dict[int, Mapping[str, float | None]] = {}
        replaced: dict[str, dict] = {}
        for player in self._candidates:
            if values is not None and player.player_id in values:
                vector = dict(values[player.player_id])
                for metric, value in vector.items():
                    if value is not None:
                        _finite(value, f"candidate metric {metric}")
                vectors[player.player_id] = vector
                if vector != dict(player.values):
                    replaced[str(player.player_id)] = vector
            else:
                vectors[player.player_id] = player.values

        reasons = []
        if locked_ids & excluded_ids:
            reasons.append("A player cannot be both locked and excluded.")
        slots = tuple(s for s in self._formation.slots if s.slot_id not in vacant_ids)
        model = cp_model.CpModel()
        variables: dict[_Key, cp_model.IntVar] = {}
        by_slot: dict[str, list[int]] = {}
        by_player: dict[int, list[cp_model.IntVar]] = {pid: [] for pid in self._ids}
        for slot in slots:
            sid = slot.slot_id
            applicable = [r.metric for r in self._active if _applies(r, sid)]
            eligible = []
            for player in self._candidates:
                pid = player.player_id
                if pid in excluded_ids or not _eligible(player, slot):
                    continue
                if pid in pins and pins[pid] != sid:
                    continue
                # An unknown active measurement forbids the assignment; nothing is imputed.
                if any(vectors[pid].get(metric) is None for metric in applicable):
                    continue
                variable = model.new_bool_var(f"p{pid}_{sid}")
                variables[pid, sid] = variable
                by_player[pid].append(variable)
                eligible.append(pid)
            by_slot[sid] = eligible
            if eligible:
                model.add(sum(variables[pid, sid] for pid in eligible) == 1)
            else:
                reasons.append(f"No eligible measured candidate for {slot.label} ({sid}).")
        for pid in self._ids:
            choices = by_player[pid]
            required = pid in locked_ids or pid in pins
            if pid in pins and not choices:
                reasons.append(
                    f"Pinned player {pid} has no admissible assignment at {pins[pid]}."
                )
            elif required and not choices:
                reasons.append(f"Locked player {pid} has no admissible assignment.")
            elif choices:
                model.add(sum(choices) == 1 if required else sum(choices) <= 1)
        if not reasons:
            # Slots with the same admissible players and the same requirement incidence are
            # interchangeable. Ordering them by ordinal (1..n in player_id order, not raw ids)
            # removes permutations without changing the feasible player sets.
            signatures: dict[tuple, str] = {}
            for slot in slots:
                sid = slot.slot_id
                members = tuple(by_slot[sid])
                signature = (
                    members,
                    tuple(r.requirement_id for r in self._active if _applies(r, sid)),
                )
                previous = signatures.get(signature)
                if previous is not None:
                    model.add(
                        sum(n * variables[pid, previous] for n, pid in enumerate(members, 1))
                        <= sum(n * variables[pid, sid] for n, pid in enumerate(members, 1))
                    )
                signatures[signature] = sid
        return _Background(
            None if reasons else model,
            variables,
            slots,
            vectors,
            locked_ids,
            pins,
            tuple(reasons),
            {
                "excluded": sorted(excluded_ids),
                "locked": sorted(locked_ids),
                "pinned": [[pid, pins[pid]] for pid in sorted(pins)],
                "vacant": sorted(vacant_ids),
                "values": replaced,
            },
        )

    def _computed_under(self, background: _Background) -> str:
        """Hash of this model and one call's declarations: what a level is a level of."""
        if self._model_hash is None:
            self._model_hash = fingerprint(self._model())
        return fingerprint({"model": self._model_hash, "declared": background.declared})

    def _tables(self, background: _Background, *, conservative: bool) -> _Tables:
        """Integer coefficients and target of every active requirement under one named policy.

        ``conservative=False``: SHORTFALL_POLICY. ``conservative=True``: HARD_POLICY (floor each
        coefficient, ceil the target). A coefficient belongs to (player, requirement); the slot
        only decides whether it is counted.
        """
        scale = self._quantization

        def half_even(value: float, normalizer: float) -> int:
            try:
                return _q(value, normalizer, scale)
            except OverflowError as exc:  # the float quotient is infinite
                raise ValueError("normalized requirement coefficient is too large") from exc

        tables: _Tables = {}
        for requirement in self._active:
            per_player: dict[int, int] = {}
            coefficients: dict[_Key, int] = {}
            for key in background.variables:
                pid, sid = key
                if not _applies(requirement, sid):
                    continue
                if pid not in per_player:
                    value = background.vectors[pid][requirement.metric]
                    coefficient = (
                        math.floor(_scaled(value, requirement.normalizer, scale))
                        if conservative
                        else half_even(value, requirement.normalizer)
                    )
                    if abs(coefficient) > MAX_MAGNITUDE:
                        raise ValueError("normalized requirement coefficient is too large")
                    per_player[pid] = coefficient
                coefficients[key] = per_player[pid]
            target = (
                math.ceil(_scaled(requirement.minimum, requirement.normalizer, scale))
                if conservative
                else half_even(requirement.minimum, requirement.normalizer)
            )
            if abs(target) > MAX_MAGNITUDE:
                raise ValueError("normalized requirement minimum is too large")
            if sum(abs(c) for c in coefficients.values()) >= MAX_EXPRESSION_MAGNITUDE:
                raise ValueError("normalized requirement expression is too large")
            tables[requirement.requirement_id] = (coefficients, target)
        return tables

    @staticmethod
    def _expression(background: _Background, coefficients: Mapping[_Key, int]):
        if not coefficients:
            return 0
        keys = list(coefficients)
        return cp_model.LinearExpr.weighted_sum(
            [background.variables[key] for key in keys], [coefficients[key] for key in keys]
        )

    @staticmethod
    def _witness(background: _Background, solver: cp_model.CpSolver) -> Lineup:
        chosen = {
            sid: pid
            for (pid, sid), variable in background.variables.items()
            if solver.value(variable)
        }
        return tuple((slot.slot_id, chosen[slot.slot_id]) for slot in background.slots)

    @staticmethod
    def _admissible(background: _Background, lineup: Lineup) -> bool:
        """Whether a lineup is an assignment of this background, checked without the solver."""
        players = [pid for _, pid in lineup]
        return (
            [sid for sid, _ in lineup] == [slot.slot_id for slot in background.slots]
            and len(players) == len(set(players))
            and all((pid, sid) in background.variables for sid, pid in lineup)
            and background.locked <= set(players)
            and all((sid, pid) in lineup for pid, sid in background.pinned.items())
        )

    @staticmethod
    def _shortfalls(tables: _Tables, lineup: Lineup) -> dict[str, int]:
        """Integer shortfall of each requirement for a lineup, in pure Python."""
        return {
            rid: max(0, target - sum(coefficients.get((pid, sid), 0) for sid, pid in lineup))
            for rid, (coefficients, target) in tables.items()
        }

    # ------------------------------------------------------------------ values

    def value(
        self,
        *,
        excluded: Collection[int] = (),
        locked: Collection[int] = (),
        pinned: Mapping[int, str] | None = None,
        vacant: Collection[str] = (),
        values: Mapping[int, Mapping[str, float | None]] | None = None,
        deadline: float,
    ) -> KernelValue:
        """Least (maximum, total) shortfall under SHORTFALL_POLICY, with its proof status."""
        deadline = self._deadline(deadline)
        if any(r.hard for r in self._active):
            raise ValueError(
                "shortfall values treat every active requirement as soft; "
                "use satisfiable() for hard statements"
            )
        background = self._background(excluded, locked, pinned, vacant, values)
        tables = self._tables(background, conservative=False) if background.model else {}
        run = _Run(deadline, self._seed)

        def result(status, maximum=None, total=None, lineup=(), extra=()):
            return KernelValue(
                status,
                maximum,
                total,
                lineup,
                tuple(run.statuses),
                len(run.statuses),
                (*background.reasons, *extra),
                self._quantization,
                self._computed_under(background) if status == "CERTIFIED" else "",
            )

        def certified(solver, maximum, total):
            lineup = self._witness(background, solver)
            found = self._shortfalls(tables, lineup)
            if (
                not self._admissible(background, lineup)
                or max(found.values(), default=0) != maximum
                or sum(found.values()) != total
            ):
                raise RuntimeError("shortfall certificate failed its integer re-evaluation")
            return result("CERTIFIED", maximum, total, lineup)

        def unproven(name, stage):
            if name == "MODEL_INVALID":
                return result("MODEL_INVALID", extra=(f"{stage} was rejected by the solver.",))
            return result("UNKNOWN", extra=(f"{stage} was not decided ({name}).",))

        if time.monotonic() >= deadline:
            return result("UNKNOWN", extra=("Deadline reached before any solve.",))
        if background.model is None:
            return result("UNFIELDABLE")

        expressions = {
            rid: (self._expression(background, coefficients), target)
            for rid, (coefficients, target) in tables.items()
        }
        zero = background.model.clone()
        for expression, target in expressions.values():
            _at_least(zero, expression, target)
        name, solver = run.solve(zero)
        if name in _WITNESS:
            return certified(solver, 0, 0)
        if name != "INFEASIBLE":
            return unproven(name, "The zero-shortfall feasibility solve")

        upper = max(
            [1]
            + [
                target - sum(min(0, c) for c in coefficients.values())
                for coefficients, target in tables.values()
            ]
        )
        first = background.model.clone()
        level = first.new_int_var(1, upper, "maximum_shortfall")
        for expression, target in expressions.values():
            first.add(level + expression >= target)
        first.minimize(level)
        name, solver = run.solve(first)
        if name == "INFEASIBLE":
            return result(
                "UNFIELDABLE",
                extra=("No XI satisfies the combined eligibility, measurement, locks and pins.",),
            )
        if name != "OPTIMAL":
            return unproven(name, "The maximum-shortfall solve")
        maximum = solver.value(level)

        second = background.model.clone()
        deficits = []
        for index, (expression, target) in enumerate(expressions.values()):
            deficit = second.new_int_var(0, maximum, f"shortfall_{index}")
            second.add(deficit + expression >= target)
            deficits.append(deficit)
        second.minimize(sum(deficits))
        name, solver = run.solve(second)
        if name != "OPTIMAL":
            return unproven(name, "The total-shortfall solve")
        return certified(solver, maximum, sum(solver.value(d) for d in deficits))

    def satisfiable(
        self,
        *,
        excluded: Collection[int] = (),
        locked: Collection[int] = (),
        pinned: Mapping[int, str] | None = None,
        vacant: Collection[str] = (),
        values: Mapping[int, Mapping[str, float | None]] | None = None,
        deadline: float,
    ) -> FloorValue:
        """Whether every active minimum holds at once under HARD_POLICY.

        ``SATISFIABLE`` returns an XI whose exact raw sums meet the raw minima. ``NOT_SATISFIABLE``
        refers to the conservative integer model: an XI that meets a raw minimum exactly on the
        boundary can be excluded by it.
        """
        deadline = self._deadline(deadline)
        background = self._background(excluded, locked, pinned, vacant, values)
        tables = self._tables(background, conservative=True) if background.model else {}
        run = _Run(deadline, self._seed)

        def result(status, lineup=(), raw_sums=()):
            return FloorValue(status, lineup, raw_sums, len(run.statuses))

        if time.monotonic() >= deadline:
            return result("UNKNOWN")
        if background.model is None:
            return result("UNFIELDABLE")
        floors = background.model.clone()
        for coefficients, target in tables.values():
            _at_least(floors, self._expression(background, coefficients), target)
        name, solver = run.solve(floors)
        if name in _WITNESS:
            lineup = self._witness(background, solver)
            if not self._admissible(background, lineup):
                raise RuntimeError("conservative floor certificate returned an inadmissible XI")
            raw_sums = []
            for requirement in self._active:
                exact = sum(
                    (
                        Fraction(background.vectors[pid][requirement.metric])
                        for sid, pid in lineup
                        if _applies(requirement, sid)
                    ),
                    Fraction(),
                )
                # Exact sums satisfy the raw floor by construction, without tolerance.
                if exact < Fraction(requirement.minimum):
                    raise RuntimeError("conservative floor certificate failed its raw-value check")
                raw_sums.append((requirement.requirement_id, float(exact)))
            return result("SATISFIABLE", lineup, tuple(raw_sums))
        if name == "MODEL_INVALID":
            return result("MODEL_INVALID")
        if name != "INFEASIBLE":
            return result("UNKNOWN")
        # The floors are infeasible. Whether any XI exists at all is a separate proof.
        name, _ = run.solve(background.model)
        if name == "INFEASIBLE":
            return result("UNFIELDABLE")
        if name in _WITNESS:
            return result("NOT_SATISFIABLE")
        return result("MODEL_INVALID" if name == "MODEL_INVALID" else "UNKNOWN")

    # --------------------------------------------------------------- level set

    def _level_set(
        self,
        level: KernelValue,
        excluded: Collection[int],
        locked: Collection[int],
        pinned: Mapping[int, str] | None,
        values: Mapping[int, Mapping[str, float | None]] | None,
        *,
        exact: bool,
    ) -> tuple[_Background, cp_model.CpModel, dict[str, cp_model.IntVar]]:
        """Background restricted to the XIs attaining ``level``.

        The level must be a CERTIFIED value of this model under the same declarations. Two
        checks, no solve: the record of what the level was computed under must equal this
        call's (the witness of a tighter declaration is still an XI of a looser one, where it
        need not be least), and its witness is re-evaluated here. A mismatch is an error,
        never a silent answer about a different model. A level built by hand carries no
        record; for it only the witness is checked and that it is least is the caller's
        claim. With ``exact`` every shortfall variable is pinned to
        ``max(0, T_r - f_r)`` by one Boolean and two reified constraints (no big-M).
        """
        if not isinstance(level, KernelValue) or level.status != "CERTIFIED":
            raise ValueError("a level set requires a CERTIFIED KernelValue")
        if level.quantization != self._quantization:
            raise ValueError("the level was computed at a different quantization")
        background = self._background(excluded, locked, pinned, (), values)
        tables = self._tables(background, conservative=False) if background.model else {}
        found = self._shortfalls(tables, level.lineup)
        if (
            background.model is None
            or (level.computed_under and level.computed_under != self._computed_under(background))
            or not self._admissible(background, level.lineup)
            or max(found.values(), default=0) != level.maximum
            or sum(found.values()) != level.total
        ):
            raise ValueError("the level does not belong to this model and these declarations")
        model = background.model.clone()
        deficits = {}
        for index, (rid, (coefficients, target)) in enumerate(tables.items()):
            expression = self._expression(background, coefficients)
            deficit = model.new_int_var(0, level.maximum, f"shortfall_{index}")
            model.add(deficit + expression >= target)
            if exact:
                covered = model.new_bool_var(f"covered_{index}")
                model.add(deficit == 0).only_enforce_if(covered)
                model.add(deficit + expression <= target).only_enforce_if(covered.negated())
            deficits[rid] = deficit
        if deficits:
            model.add(sum(deficits.values()) == level.total)
        return background, model, deficits

    def membership(
        self,
        level: KernelValue,
        player_ids: Collection[int],
        *,
        excluded: Collection[int] = (),
        locked: Collection[int] = (),
        pinned: Mapping[int, str] | None = None,
        values: Mapping[int, Mapping[str, float | None]] | None = None,
        deadline: float,
    ) -> dict[int, Membership]:
        """For each player: in some least-shortfall XI (possible), in every one (necessary).

        INFEASIBLE is the only source of ``necessary=True`` and of ``possible=False``; an
        undecided solve leaves the fact ``None``. A player with no admissible assignment is
        ``possible=False`` by construction, without a solve.
        """
        deadline = self._deadline(deadline)
        requested = sorted(self._player_ids(player_ids, "requested"))
        background, model, _ = self._level_set(level, excluded, locked, pinned, values, exact=False)
        run = _Run(deadline, self._seed)
        in_level = {pid for _, pid in level.lineup}
        output = {}
        for pid in requested:
            choices = [v for (owner, _), v in background.variables.items() if owner == pid]
            if not choices:
                output[pid] = Membership(False, False)
                continue
            opposite = model.clone()
            opposite.add(sum(choices) == (0 if pid in in_level else 1))
            name, _ = run.solve(opposite)
            witness, ruled_out = name in _WITNESS, name == "INFEASIBLE"
            if pid in in_level:
                output[pid] = Membership(True, False if witness else True if ruled_out else None)
            else:
                output[pid] = Membership(True if witness else False if ruled_out else None, False)
        return output

    def shortfall_ranges(
        self,
        level: KernelValue,
        *,
        excluded: Collection[int] = (),
        locked: Collection[int] = (),
        pinned: Mapping[int, str] | None = None,
        values: Mapping[int, Mapping[str, float | None]] | None = None,
        deadline: float,
    ) -> dict[str, tuple[int, int] | None]:
        """(least, greatest) integer shortfall of each active requirement over the level set.

        ``None`` for a requirement whose two solves were not both OPTIMAL.
        """
        deadline = self._deadline(deadline)
        _, model, deficits = self._level_set(level, excluded, locked, pinned, values, exact=True)
        run = _Run(deadline, self._seed)
        output: dict[str, tuple[int, int] | None] = {}
        for rid, deficit in deficits.items():
            bounds = []
            for maximise in (False, True):
                directed = model.clone()
                if maximise:
                    directed.maximize(deficit)
                else:
                    directed.minimize(deficit)
                name, solver = run.solve(directed)
                if name != "OPTIMAL":
                    break
                bounds.append(solver.value(deficit))
            output[rid] = (bounds[0], bounds[1]) if len(bounds) == 2 else None
        return output
