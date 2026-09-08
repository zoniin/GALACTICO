"""Exact assignment under explicit, quantized tactical requirements.

BALANCE lexicographically minimizes maximum then total normalized shortfall.
SATISFY treats each active requirement as hard. Normalizers and the lexicographic
order are declared preferences, not scientifically identified utility weights.
Optimality refers only to this finite, quantized model. Equally optimal player
sets are interrogated separately so a deterministic tie cannot create a core.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, replace
from importlib.metadata import version

from ortools.sat.python import cp_model

from .domain import (
    FORMATIONS,
    Assignment,
    Candidate,
    Formation,
    RequirementAssessment,
    SelectionFrequency,
    TacticalRequirement,
    XIResult,
)

SOLVER_VERSION = "explicit-requirements-cpsat-v1"
QUANTIZATION = 100_000


def _eligible(player: Candidate, slot) -> bool:
    return (
        player.minutes > 0
        and player.position in slot.allowed_positions
        and (player.eligible_slots is None or slot.slot_id in player.eligible_slots)
    )


def _applies(requirement: TacticalRequirement, slot_id: str) -> bool:
    return not requirement.slot_ids or slot_id in requirement.slot_ids


def _q(value: float, normalizer: float, scale: int) -> int:
    # Python's half-even rule is part of the reproducible numerical policy.
    return int(round(value / normalizer * scale))


def _fingerprint(payload) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _status(status: int) -> str:
    return {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.UNKNOWN: "UNKNOWN",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
    }.get(status, "UNKNOWN")


def _solver(deadline: float, seed: int) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(0.001, deadline - time.monotonic())
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    return solver


def solve_xi(
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    locked: Sequence[int] = (),
    excluded: Sequence[int] = (),
    mode: str = "BALANCE",
    seed: int = 20260906,
    time_limit: float = 15.0,
    quantization: int = QUANTIZATION,
    analyze_ties: bool = True,
    provenance: Mapping | None = None,
    worlds: Mapping[int, Mapping[int, Mapping[str, float | None]]] | None = None,
) -> XIResult:
    """Solve one policy, optionally repeat it in coherent externally built worlds.

    ``locked`` requires inclusion somewhere eligible; it never bypasses eligibility.
    An unknown active measurement forbids the corresponding assignment explicitly.
    Inactive requirements remain UNMEASURED and contribute no numerical constraint.
    """
    deadline = time.monotonic() + time_limit
    formation = FORMATIONS[formation] if isinstance(formation, str) else formation
    candidates = tuple(sorted(candidates, key=lambda p: p.player_id))
    requirements = tuple(sorted(requirements, key=lambda r: r.requirement_id))
    locked, excluded = tuple(sorted(set(locked))), tuple(sorted(set(excluded)))
    ids = [p.player_id for p in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate player IDs must be unique")
    if len(requirements) != len({r.requirement_id for r in requirements}):
        raise ValueError("requirement IDs must be unique")
    if not isinstance(quantization, int) or quantization < 1 or quantization > 10**9:
        raise ValueError("quantization must be an integer between 1 and 1e9")
    if not math.isfinite(time_limit) or time_limit <= 0:
        raise ValueError("time limit must be finite and positive")
    if mode not in {"BALANCE", "SATISFY"}:
        raise ValueError("mode must be BALANCE or SATISFY")
    slots = {s.slot_id: s for s in formation.slots}
    for requirement in requirements:
        if set(requirement.slot_ids) - slots.keys():
            raise ValueError(f"{requirement.requirement_id}: unknown requirement slot")
    unknown = (set(locked) | set(excluded)) - set(ids)
    if unknown:
        raise ValueError(f"unknown locked/excluded player IDs: {sorted(unknown)}")

    metadata = dict(provenance or {})
    metadata.update(
        {
            "solver_version": SOLVER_VERSION,
            "solver_package_version": version("ortools"),
            "quantization": quantization,
            "rounding": "half-even after division by declared normalizer",
            "normalized_aggregation_error_bound": (len(slots) + 1) / (2 * quantization),
            "requirement_version": _fingerprint([asdict(r) for r in requirements]),
            "tactical_requirement_inputs": [asdict(r) for r in requirements],
            "formation_version": _fingerprint(asdict(formation)),
            "seed": seed,
            "mode": mode,
            "decision_claim": "Feasible XIs favored under explicit tactical requirements",
            "objective_policy": "minimize maximum normalized shortfall, then total shortfall",
            "tie_policy": "Deterministic solver representative; no football preference among ties",
            "input_fingerprint": _fingerprint(
                {
                    "candidates": [asdict(p) for p in candidates],
                    "requirements": [asdict(r) for r in requirements],
                    "formation": asdict(formation),
                    "locked": locked,
                    "excluded": excluded,
                    "quantization": quantization,
                    "mode": mode,
                }
            ),
        }
    )
    warnings = [
        "Optimal means optimal for the quantized requirement model, not the best football XI.",
        "Summed historical player rates assume those rates persist when selected together.",
        "Slot assignment within equivalent eligible roles is administrative, not learned role fit.",
        "Equivalent XIs may exist; representative selection frequency alone is not a stable core.",
    ]
    reasons = []
    if set(locked) & set(excluded):
        reasons.append("A player cannot be both locked and excluded.")
    active = [r for r in requirements if r.active]
    model = cp_model.CpModel()
    variables = {}
    missing = []
    for slot in formation.slots:
        for player in candidates:
            if player.player_id in excluded or not _eligible(player, slot):
                continue
            absent = [
                r.metric
                for r in active
                if _applies(r, slot.slot_id) and player.values.get(r.metric) is None
            ]
            if absent:
                missing.append(
                    {
                        "player_id": player.player_id,
                        "slot_id": slot.slot_id,
                        "metrics": sorted(set(absent)),
                    }
                )
                continue
            variables[player.player_id, slot.slot_id] = model.new_bool_var(
                f"p{player.player_id}_{slot.slot_id}"
            )
        choices = [v for (pid, sid), v in variables.items() if sid == slot.slot_id]
        if not choices:
            reasons.append(f"No eligible measured candidate for {slot.label} ({slot.slot_id}).")
        model.add(sum(choices) == 1)
    # Equivalent slots have identical eligibility and requirement incidence.
    # Canonical ordering removes permutations without changing feasible player sets.
    signatures = {}
    for slot in formation.slots:
        signature = (
            tuple(pid for pid in ids if (pid, slot.slot_id) in variables),
            tuple(r.requirement_id for r in active if _applies(r, slot.slot_id)),
        )
        if signature in signatures:
            previous = signatures[signature]
            model.add(
                sum(pid * variables[pid, previous] for pid in signature[0])
                <= sum(pid * variables[pid, slot.slot_id] for pid in signature[0])
            )
        signatures[signature] = slot.slot_id
    selected = {}
    for player in candidates:
        choices = [v for (pid, _), v in variables.items() if pid == player.player_id]
        selected[player.player_id] = sum(choices)
        model.add(sum(choices) <= 1)
        if player.player_id in locked:
            model.add(sum(choices) == 1)
    if set(locked) & set(excluded):
        model.add(False)
    metadata["unavailable_assignments"] = missing
    if missing:
        warnings.append(
            "Assignments with missing active measurements were excluded; no zero imputation."
        )

    deficits = []
    expressions = {}
    bounds = []
    for requirement in active:
        terms = []
        lower = 0
        for player in candidates:
            for slot in formation.slots:
                variable = variables.get((player.player_id, slot.slot_id))
                if variable is None or not _applies(requirement, slot.slot_id):
                    continue
                coefficient = _q(
                    player.values[requirement.metric], requirement.normalizer, quantization
                )
                if abs(coefficient) > 10**12:
                    raise ValueError("normalized requirement coefficient is too large")
                terms.append(coefficient * variable)
                lower += min(0, coefficient)
        target = _q(requirement.minimum, requirement.normalizer, quantization)
        expression = sum(terms)
        expressions[requirement.requirement_id] = (expression, target)
        if requirement.hard or mode == "SATISFY":
            model.add(expression >= target)
        upper = max(0, target - lower)
        deficit = model.new_int_var(0, upper, f"deficit_{requirement.requirement_id}")
        model.add_max_equality(deficit, [0, target - expression])
        deficits.append(deficit)
        bounds.append(upper)
    max_deficit = model.new_int_var(0, max(bounds, default=0), "max_deficit")
    model.add_max_equality(max_deficit, deficits or [0])
    total_deficit = sum(deficits)
    model.minimize(max_deficit)
    first = _solver(deadline, seed)
    first_status = first.solve(model)
    status = first_status
    solution = first
    stages = [
        {
            "stage": "maximum_shortfall",
            "status": _status(first_status),
            "objective": first.objective_value
            if first_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
            else None,
            "bound": first.best_objective_bound,
        }
    ]
    if first_status == cp_model.OPTIMAL:
        model.add(max_deficit == first.value(max_deficit))
        model.minimize(total_deficit)
        second = _solver(deadline, seed)
        second_status = second.solve(model)
        stages.append(
            {
                "stage": "total_shortfall",
                "status": _status(second_status),
                "objective": second.objective_value
                if second_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
                else None,
                "bound": second.best_objective_bound,
            }
        )
        if second_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status, solution = second_status, second
        else:
            # A proven first objective and a timed-out second stage only certify
            # a feasible lexicographic solution. Never fix an unproven optimum.
            status = cp_model.FEASIBLE
    metadata["solver_stages"] = stages
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if not reasons and status == cp_model.INFEASIBLE:
            reasons.append("No XI satisfies the combined eligibility, locks and hard requirements.")
        metadata["infeasibility_explanation"] = "Diagnostic reasons; not a minimal conflicting set"
        return XIResult(
            formation.formation_id,
            (),
            tuple(
                RequirementAssessment(
                    r.requirement_id,
                    r.label,
                    r.metric,
                    r.evidence_class,
                    "NOT_EVALUATED" if r.active else "UNMEASURED",
                    r.minimum,
                    None,
                    None,
                    None,
                    r.active and (r.hard or mode == "SATISFY"),
                    r.source,
                )
                for r in requirements
            ),
            _status(status),
            (),
            locked,
            excluded,
            provenance=metadata,
            warnings=tuple(warnings),
            infeasibility_reasons=tuple(reasons),
        )

    chosen = {(pid, sid) for (pid, sid), var in variables.items() if solution.value(var)}
    assignments = []
    by_id = {p.player_id: p for p in candidates}
    for slot in formation.slots:
        pid = next(pid for pid, sid in chosen if sid == slot.slot_id)
        player = by_id[pid]
        contributions = {
            r.requirement_id: float(player.values[r.metric])
            for r in active
            if _applies(r, slot.slot_id)
        }
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
                contributions,
            )
        )
    assessments = []
    for requirement in requirements:
        if not requirement.active:
            achieved = deficit = normalized = None
            label = "UNMEASURED"
        else:
            achieved = sum(
                a.contributions.get(requirement.requirement_id, 0.0) for a in assignments
            )
            deficit = max(0.0, requirement.minimum - achieved)
            normalized = deficit / requirement.normalizer
            # Status is based on raw values, not rounded solver coefficients.
            label = "COVERED" if deficit <= 1e-12 else "DEFICIT"
        assessments.append(
            RequirementAssessment(
                requirement.requirement_id,
                requirement.label,
                requirement.metric,
                requirement.evidence_class,
                label,
                requirement.minimum,
                achieved,
                deficit,
                normalized,
                requirement.active and (requirement.hard or mode == "SATISFY"),
                requirement.source,
            )
        )
    objective = (
        solution.value(max_deficit) / quantization,
        solution.value(total_deficit) / quantization,
    )
    equivalents = {}
    if status == cp_model.OPTIMAL and analyze_ties:
        model.add(total_deficit == solution.value(total_deficit))
        model.clear_objective()
        for player in candidates:
            pid = player.player_id
            in_xi = any(chosen_pid == pid for chosen_pid, _ in chosen)
            opposite = model.clone()
            opposite.add(selected[pid] == (0 if in_xi else 1))
            tie_solver = _solver(deadline, seed)
            tie_status = tie_solver.solve(opposite)
            witness = tie_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
            ruled_out = tie_status == cp_model.INFEASIBLE
            equivalents[pid] = {
                "necessary": (False if witness else True if ruled_out else None)
                if in_xi
                else False,
                "possible": True if in_xi else (True if witness else False if ruled_out else None),
            }
    metadata["tie_analysis_complete"] = bool(equivalents) and all(
        value is not None for row in equivalents.values() for value in row.values()
    )
    metadata["elapsed_seconds"] = time_limit - max(0, deadline - time.monotonic())
    if any(r.hard and r.deficit and r.deficit > 0 for r in assessments):
        warnings.append(
            "A raw hard threshold differs within quantization tolerance; inspect raw deficit."
        )
    result = XIResult(
        formation.formation_id,
        tuple(assignments),
        tuple(assessments),
        _status(status),
        objective,
        locked,
        excluded,
        equivalent_players=equivalents,
        provenance=metadata,
        warnings=tuple(warnings),
    )
    if worlds:
        return bootstrap_selection(
            result,
            candidates,
            requirements,
            formation,
            worlds=worlds,
            locked=locked,
            excluded=excluded,
            mode=mode,
            seed=seed,
            time_limit=time_limit,
            quantization=quantization,
        )
    return result


def bootstrap_selection(
    base: XIResult,
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation,
    *,
    worlds: Mapping[int, Mapping[int, Mapping[str, float | None]]],
    **solve_options,
) -> XIResult:
    """Selection stability across shared worlds; tie-aware necessity/possibility.

    Worlds are created from a shared match draw upstream, not independently from
    stored per-player quantiles. Every world's ID and content enter provenance.
    """
    formation = FORMATIONS[formation] if isinstance(formation, str) else formation
    active = [r for r in requirements if r.active]
    excluded = set(solve_options.get("excluded", ()))
    counts = {p.player_id: [0, 0, 0] for p in candidates}
    slot_counts = {p.player_id: {} for p in candidates}
    used, discarded, incomplete = [], [], []
    for world_id in sorted(worlds):
        world = worlds[world_id]
        valid = True
        changed = []
        for player in candidates:
            values = dict(world.get(player.player_id, {}))
            needed = {
                r.metric
                for r in active
                for slot in formation.slots
                if player.player_id not in excluded
                and _eligible(player, slot)
                and _applies(r, slot.slot_id)
            }
            if any(values.get(metric) is None for metric in needed):
                valid = False
            changed.append(replace(player, values=values))
        if not valid:
            discarded.append({"world_id": world_id, "reason": "missing shared-world exposure"})
            continue
        solved = solve_xi(changed, requirements, formation, analyze_ties=True, **solve_options)
        if solved.solution_status != "OPTIMAL" or not solved.provenance["tie_analysis_complete"]:
            incomplete.append({"world_id": world_id, "status": solved.solution_status})
            continue
        used.append(world_id)
        for assignment in solved.assignments:
            counts[assignment.player_id][0] += 1
            slots = slot_counts[assignment.player_id]
            slots[assignment.slot_id] = slots.get(assignment.slot_id, 0) + 1
        for pid, row in solved.equivalent_players.items():
            counts[pid][1] += int(row["necessary"])
            counts[pid][2] += int(row["possible"])
    denominator = len(used)
    frequencies = []
    if denominator:
        for player in sorted(candidates, key=lambda p: p.player_id):
            representative, necessary, possible = (
                n / denominator for n in counts[player.player_id]
            )
            label = (
                "USER LOCK"
                if player.player_id in solve_options.get("locked", ())
                else "CORE"
                if necessary >= 0.90
                else "FAVORED"
                if necessary >= 0.70
                else "FRINGE"
                if possible < 0.30
                else "CONTESTED"
            )
            frequencies.append(
                SelectionFrequency(
                    player.player_id,
                    player.name,
                    representative,
                    necessary,
                    possible,
                    label,
                    {slot: n / denominator for slot, n in slot_counts[player.player_id].items()},
                )
            )
    metadata = dict(base.provenance)
    metadata.update(
        {
            "bootstrap_world_fingerprint": _fingerprint(worlds),
            "bootstrap_requested_worlds": len(worlds),
            "bootstrap_used_worlds": used,
            "bootstrap_discarded_worlds": discarded,
            "bootstrap_incomplete_worlds": incomplete,
            "bootstrap_interpretation": (
                "Conditional algorithm stability, not probability of football superiority"
            ),
            "core_threshold_policy": (
                "CORE: necessary in >=90%; FAVORED >=70%; FRINGE possible <30%"
            ),
            "frequency_interval": (
                "Necessary-to-possible range across equally optimal XIs in each shared world"
            ),
        }
    )
    warnings = list(base.warnings)
    if discarded or incomplete:
        warnings.append(
            "Frequencies condition on certified feasible worlds; exclusions are recorded."
        )
    if not denominator:
        warnings.append("No fully certified bootstrap worlds; selection frequencies unavailable.")
    return replace(
        base,
        selection_frequencies=tuple(frequencies),
        provenance=metadata,
        warnings=tuple(warnings),
    )


def removal_sensitivity(
    base: XIResult,
    candidates: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    *,
    player_ids: Sequence[int] | None = None,
    **solve_options,
) -> dict[int, dict]:
    """Model sensitivity to excluding a player; not causal player importance."""
    output = {}
    old_ids = {a.player_id for a in base.assignments}
    for pid in sorted(player_ids if player_ids is not None else old_ids):
        options = dict(solve_options)
        inherited = dict(base.provenance)
        # A re-solve retains its evidence lineage, not the previous solve's
        # certification or resampling results. solve_xi records fresh hashes,
        # stages and bounds, including for infeasible removals.
        for key in tuple(inherited):
            if key in {
                "solver_stages",
                "elapsed_seconds",
                "tie_analysis_complete",
                "infeasibility_explanation",
            } or (key.startswith("bootstrap_") and key != "bootstrap_version"):
                inherited.pop(key)
        inherited.update(options.get("provenance") or {})
        inherited["sensitivity_baseline_fingerprint"] = base.provenance.get("input_fingerprint")
        options["provenance"] = inherited
        options["locked"] = tuple(p for p in base.locked if p != pid)
        options["excluded"] = tuple(sorted(set(base.excluded) | {pid}))
        options["analyze_ties"] = False
        result = solve_xi(candidates, requirements, base.formation, **options)
        new_ids = {a.player_id for a in result.assignments}
        output[pid] = {
            "solution_status": result.solution_status,
            "objective_vector": result.objective_vector,
            "objective_change": tuple(
                b - a for a, b in zip(base.objective_vector, result.objective_vector, strict=False)
            ),
            "in": sorted(new_ids - old_ids),
            "out": sorted(old_ids - new_ids),
            "requirements": [asdict(r) for r in result.requirements],
            "provenance": dict(result.provenance),
            "infeasibility_reasons": list(result.infeasibility_reasons),
            "claim": "Sensitivity of this requirement model to excluding the player",
        }
    return output


def candidate_injection(
    candidate: Candidate,
    squad: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    **solve_options,
) -> dict:
    """Transfer foundation: compare the same policy before/after candidate entry."""
    if candidate.player_id in {p.player_id for p in squad}:
        raise ValueError("injected candidate must have a new player ID")
    before = solve_xi(squad, requirements, formation, **solve_options)
    after = solve_xi([*squad, candidate], requirements, formation, **solve_options)
    return {
        "before": asdict(before),
        "after": asdict(after),
        "objective_change": tuple(
            b - a for a, b in zip(before.objective_vector, after.objective_vector, strict=False)
        ),
        "claim": "Marginal modeled requirement change; not transfer value or causal improvement",
    }
