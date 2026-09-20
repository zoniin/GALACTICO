"""An explicit-floor accounting experiment, separate from the BALANCE solver.

Every active requirement is a hard floor. The selected descriptor alone is
maximized. Neither an optimum nor a sequence of floor edits identifies a best
football XI, predicted team production, or a complete Pareto frontier.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from fractions import Fraction
from importlib.metadata import version
from pathlib import Path

from ortools.sat.python import cp_model

from .domain import (
    FORMATIONS,
    Assignment,
    Candidate,
    Formation,
    RequirementAssessment,
    RequirementObjectiveCertificate,
    RequirementTradeoffResult,
    TacticalRequirement,
)

TRADEOFF_VERSION = "explicit-floor-single-descriptor-v1"
MAX_MAGNITUDE = 10**12
MAX_EXPRESSION_MAGNITUDE = 2**50
FLOOR_POLICY = "floor each exact input-number fraction; ceil the exact minimum fraction"
OBJECTIVE_POLICY = "nearest half-even of each exact input-number fraction"


def _fingerprint(payload) -> str:
    try:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("provenance and inputs must be finite JSON-serializable values") from exc
    return hashlib.sha256(serialized.encode()).hexdigest()


def _applies(requirement: TacticalRequirement, slot_id: str) -> bool:
    return not requirement.slot_ids or slot_id in requirement.slot_ids


def _scaled(value: float, normalizer: float, scale: int) -> Fraction:
    # Do not divide floating values before converting to exact fractions.
    return Fraction(value) / Fraction(normalizer) * scale


def _finite(value, name: str, *, positive: bool = False) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or abs(value) > MAX_MAGNITUDE
        or (positive and value <= 0)
    ):
        kind = "positive" if positive else "numeric"
        raise ValueError(f"{name} must be finite, bounded by 1e12 and {kind}")


def _source_fingerprints() -> dict[str, str]:
    return {
        filename: hashlib.sha256(
            Path(__file__).with_name(filename).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for filename in ("tradeoffs.py", "domain.py")
    }


def maximize_requirement(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    target_requirement_id: str = "progression",
    locked: Sequence[int] = (),
    excluded: Sequence[int] = (),
    seed: int = 20260906,
    time_limit: float = 15.0,
    quantization: int = 100_000,
    provenance: Mapping | None = None,
) -> RequirementTradeoffResult:
    """Maximize one historical descriptor under conservative explicit floors.

    The integer floor model is an inner approximation: all returned XIs meet
    raw floors, but a raw-boundary-feasible XI can be excluded by quantization.
    Missing active values forbid only assignments to which they apply.
    """
    started = time.monotonic()
    _finite(time_limit, "time limit", positive=True)
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
    candidates = tuple(sorted(candidates, key=lambda player: player.player_id))
    requirements = tuple(sorted(requirements, key=lambda requirement: requirement.requirement_id))
    ids = [player.player_id for player in candidates]
    if any(type(pid) is not int for pid in ids) or len(ids) != len(set(ids)):
        raise ValueError("candidate player IDs must be unique integers")
    if len(requirements) != len({requirement.requirement_id for requirement in requirements}):
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
    if any(type(pid) is not int for pid in (*locked, *excluded)):
        raise ValueError("locked/excluded player IDs must be integers")
    locked, excluded = tuple(sorted(set(locked))), tuple(sorted(set(excluded)))
    unknown = (set(locked) | set(excluded)) - set(ids)
    if unknown:
        raise ValueError(f"unknown locked/excluded player IDs: {sorted(unknown)}")
    active = tuple(requirement for requirement in requirements if requirement.active)
    target = next((r for r in active if r.requirement_id == target_requirement_id), None)
    if target is None:
        raise ValueError("target requirement must name an active requirement")
    applicable_count = sum(_applies(target, sid) for sid in slot_ids)
    raw_error = float(Fraction(applicable_count, 2 * quantization) * Fraction(target.normalizer))
    # Round outward so serialization cannot understate the exact error bound.
    raw_error = math.nextafter(raw_error, math.inf)
    source = dict(provenance or {})
    policy = {
        "version": TRADEOFF_VERSION,
        "candidates": [asdict(player) for player in candidates],
        "requirements": [asdict(requirement) for requirement in requirements],
        "formation": asdict(formation),
        "locked": locked,
        "excluded": excluded,
        "target_requirement_id": target_requirement_id,
        "seed": seed,
        "time_limit": time_limit,
        "quantization": quantization,
        "floor_rounding": FLOOR_POLICY,
        "objective_rounding": OBJECTIVE_POLICY,
        "all_active_floors_hard": True,
        "source_fingerprints": _source_fingerprints(),
        "source_provenance": source,
        "solver_package_version": version("ortools"),
    }
    # Retain data lineage, never a prior solve's certification or world results.
    # The full caller payload is hashed and retained above as source-only input.
    prior_certificate_keys = {
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
    metadata = {
        key: value
        for key, value in source.items()
        if key not in prior_certificate_keys
        and not key.startswith(("solver_", "tie_"))
        and not (key.startswith("bootstrap_") and key != "bootstrap_version")
    }
    metadata.update(
        {
            "solver_version": TRADEOFF_VERSION,
            "solver_package_version": policy["solver_package_version"],
            "input_fingerprint": _fingerprint(policy),
            "input_contract": policy,
            "source_fingerprints": policy["source_fingerprints"],
            "tactical_requirement_inputs": policy["requirements"],
            "requirement_version": _fingerprint(policy["requirements"]),
            "formation_inputs": policy["formation"],
            "formation_version": _fingerprint(policy["formation"]),
            "seed": seed,
            "quantization": quantization,
            "floor_rounding": FLOOR_POLICY,
            "objective_rounding": OBJECTIVE_POLICY,
            "decision_claim": (
                "Maximize one declared historical descriptor subject to explicit hard floors"
            ),
            "tie_policy": (
                "Deterministic representative; no secondary objective or football preference"
            ),
            "floor_conservatism_bounds": {
                r.requirement_id: {
                    "raw_strict_upper_bound": math.nextafter(
                        float(
                            Fraction(sum(_applies(r, sid) for sid in slot_ids) + 1, quantization)
                            * Fraction(r.normalizer)
                        ),
                        math.inf,
                    ),
                    "interpretation": (
                        "Conservative floor slack is strictly below this bound; "
                        "raw-boundary feasible XIs can be excluded"
                    ),
                }
                for r in active
            },
        }
    )
    warnings = [
        "This maximizes the declared historical descriptor, "
        "not football quality or predicted team output.",
        "Summing historical player rates assumes persistence together; "
        "this is an accounting model, not a forecast.",
        "All active minima are hard floors, including requirements marked soft in BALANCE.",
        "Conservative quantization can exclude raw-boundary-feasible XIs; "
        "optimality applies to this finite inner approximation.",
        "Equal target values have no secondary preference; "
        "this is not a Pareto-optimality or full-frontier certificate.",
        "Slot assignments are administrative eligibility choices, not learned role fit.",
    ]
    model = cp_model.CpModel()
    variables = {}
    missing = []
    reasons = []
    for slot in formation.slots:
        for player in candidates:
            if (
                player.player_id in excluded
                or player.minutes <= 0
                or player.position not in slot.allowed_positions
                or (player.eligible_slots is not None and slot.slot_id not in player.eligible_slots)
            ):
                continue
            absent = sorted(
                {
                    r.metric
                    for r in active
                    if _applies(r, slot.slot_id) and player.values.get(r.metric) is None
                }
            )
            if absent:
                missing.append(
                    {"player_id": player.player_id, "slot_id": slot.slot_id, "metrics": absent}
                )
                continue
            variables[player.player_id, slot.slot_id] = model.new_bool_var(
                f"p{player.player_id}_{slot.slot_id}"
            )
        choices = [var for (_, sid), var in variables.items() if sid == slot.slot_id]
        model.add(sum(choices) == 1)
        if not choices:
            reasons.append(f"No eligible measured candidate for {slot.label} ({slot.slot_id}).")
    for player in candidates:
        choices = [var for (pid, _), var in variables.items() if pid == player.player_id]
        model.add(sum(choices) <= 1)
        if player.player_id in locked:
            model.add(sum(choices) == 1)
    if set(locked) & set(excluded):
        model.add(False)
        reasons.append("A player cannot be both locked and excluded.")
    metadata["unavailable_assignments"] = missing
    if missing:
        warnings.append(
            "Assignments with missing active measurements were excluded; no zero imputation."
        )
    by_id = {player.player_id: player for player in candidates}
    objective_coefficients = {}
    floor_certificates = {}
    for requirement in active:
        coefficients = {}
        for key in variables:
            pid, sid = key
            if not _applies(requirement, sid):
                continue
            scaled = _scaled(
                by_id[pid].values[requirement.metric], requirement.normalizer, quantization
            )
            coefficient = math.floor(scaled)
            if abs(coefficient) > MAX_MAGNITUDE:
                raise ValueError("normalized requirement coefficient is too large")
            coefficients[key] = coefficient
            if requirement is target:
                objective_coefficients[key] = round(scaled)
        minimum = math.ceil(_scaled(requirement.minimum, requirement.normalizer, quantization))
        if abs(minimum) > MAX_MAGNITUDE:
            raise ValueError("normalized requirement minimum is too large")
        if sum(abs(c) for c in coefficients.values()) >= MAX_EXPRESSION_MAGNITUDE:
            raise ValueError("normalized requirement expression is too large")
        model.add(
            sum(coefficient * variables[key] for key, coefficient in coefficients.items())
            >= minimum
        )
        floor_certificates[requirement.requirement_id] = {
            "integer_minimum": minimum,
            "integer_achieved": None,
            "quantization": quantization,
            "normalizer": requirement.normalizer,
        }
    if sum(abs(c) for c in objective_coefficients.values()) >= MAX_EXPRESSION_MAGNITUDE:
        raise ValueError("normalized objective expression is too large")
    objective_expression = sum(
        coefficient * variables[key] for key, coefficient in objective_coefficients.items()
    )
    model.maximize(objective_expression)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    remaining = started + time_limit - time.monotonic()
    if remaining <= 0:
        status = cp_model.UNKNOWN
    else:
        solver.parameters.max_time_in_seconds = remaining
        status = solver.solve(model)
    status_label = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.UNKNOWN: "UNKNOWN",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
    }.get(status, "UNKNOWN")
    has_solution = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assignments = []
    chosen = set()
    if has_solution:
        chosen = {key for key, variable in variables.items() if solver.value(variable)}
        for slot in formation.slots:
            pid = next(pid for pid, sid in chosen if sid == slot.slot_id)
            player = by_id[pid]
            assignments.append(
                Assignment(
                    slot.slot_id,
                    slot.label,
                    pid,
                    player.name,
                    player.position,
                    slot.x,
                    slot.y,
                    pid in locked,
                    {
                        r.requirement_id: float(player.values[r.metric])
                        for r in active
                        if _applies(r, slot.slot_id)
                    },
                )
            )
    assessments = []
    for requirement in requirements:
        achieved = None
        if has_solution and requirement.active:
            exact = sum(
                (
                    Fraction(by_id[pid].values[requirement.metric])
                    for pid, sid in chosen
                    if _applies(requirement, sid)
                ),
                Fraction(),
            )
            achieved = float(exact)
            # Exact sums satisfy the raw floor by construction, without tolerance.
            if exact < Fraction(requirement.minimum):
                raise RuntimeError("conservative floor certificate failed its raw-value check")
            floor_certificates[requirement.requirement_id]["integer_achieved"] = sum(
                math.floor(
                    _scaled(
                        by_id[pid].values[requirement.metric], requirement.normalizer, quantization
                    )
                )
                for pid, sid in chosen
                if _applies(requirement, sid)
            )
        assessments.append(
            RequirementAssessment(
                requirement.requirement_id,
                requirement.label,
                requirement.metric,
                requirement.evidence_class,
                "UNMEASURED"
                if not requirement.active
                else "COVERED"
                if has_solution
                else "NOT_EVALUATED",
                requirement.minimum,
                achieved,
                0.0 if achieved is not None else None,
                0.0 if achieved is not None else None,
                requirement.active,
                requirement.source,
            )
        )
    integer_value = (
        sum(objective_coefficients.get(key, 0) for key in chosen) if has_solution else None
    )
    integer_bound = None
    if status == cp_model.OPTIMAL:
        integer_bound = integer_value
    elif status == cp_model.FEASIBLE:
        integer_bound = max(integer_value, math.ceil(solver.best_objective_bound))

    def decode(integer):
        return (
            None
            if integer is None
            else float(Fraction(integer, quantization) * Fraction(target.normalizer))
        )

    certificate = RequirementObjectiveCertificate(
        target.requirement_id,
        target.label,
        target.metric,
        "MAXIMIZE",
        next(a.achieved for a in assessments if a.requirement_id == target.requirement_id),
        decode(integer_value),
        decode(integer_bound),
        "QUANTIZED_OPTIMAL"
        if status == cp_model.OPTIMAL
        else "FEASIBLE_NOT_PROVEN"
        if has_solution
        else "NO_SOLUTION",
        raw_error,
        integer_value,
        integer_bound,
        quantization,
    )
    metadata["floor_certificates"] = floor_certificates
    metadata["objective_certificate"] = asdict(certificate)
    metadata["solver_status"] = status_label
    metadata["infeasibility_explanation"] = "Diagnostic reasons; not a minimal conflicting set"
    if not has_solution:
        if status == cp_model.INFEASIBLE and not reasons:
            reasons.append(
                "No XI satisfies the conservative integer model of the combined "
                "eligibility, locks and hard floors."
            )
        if status != cp_model.INFEASIBLE:
            # A deadline/model failure is not proof that this policy is impossible.
            reasons = []
            warnings.append("No incumbent was returned; this does not establish infeasibility.")
    return RequirementTradeoffResult(
        formation.formation_id,
        tuple(assignments),
        tuple(assessments),
        status_label,
        certificate,
        locked,
        excluded,
        tuple(warnings),
        tuple(reasons),
        metadata,
    )
