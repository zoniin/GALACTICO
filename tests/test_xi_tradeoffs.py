"""Contract and certificate guards for the separate explicit-floor solver."""

from dataclasses import asdict, replace
from fractions import Fraction

import pytest
from ortools.sat.python import cp_model

from galactico.optimization.xi import (
    Candidate,
    Formation,
    Slot,
    TacticalRequirement,
    maximize_requirement,
    tradeoffs,
)


@pytest.fixture
def case():
    formation = Formation("one", (Slot("only", "Only", ("MF",), 0.5, 0.5),))
    candidates = [Candidate(1, "one", "MF", {"p": 2.5}), Candidate(2, "two", "MF", {"p": 3.5})]
    requirements = [TacticalRequirement("progression", "Progression", "p", 0, 1)]
    return candidates, requirements, formation


@pytest.mark.parametrize(
    "options",
    [
        {"quantization": True},
        {"quantization": 0},
        {"quantization": 10**9 + 1},
        {"quantization": 1.5},
        {"time_limit": 0},
        {"time_limit": float("nan")},
        {"time_limit": float("inf")},
        {"time_limit": True},
        {"seed": True},
        {"seed": -1},
        {"seed": 2**31},
        {"seed": 1.5},
        {"locked": [99]},
        {"excluded": [99]},
        {"locked": [True]},
        {"target_requirement_id": "unknown"},
    ],
)
def test_invalid_parameters_raise_instead_of_silently_changing_policy(case, options):
    with pytest.raises(ValueError):
        maximize_requirement(*case, **options)


def test_unknown_formation_and_requirement_slot_and_duplicate_ids_raise(case):
    players, requirements, formation = case
    with pytest.raises(ValueError, match="unknown formation"):
        maximize_requirement(players, requirements, "unknown")
    with pytest.raises(ValueError, match="unique"):
        maximize_requirement(players + players, requirements, formation)
    with pytest.raises(ValueError, match="unique"):
        maximize_requirement(players, requirements * 2, formation)
    with pytest.raises(ValueError, match="unknown requirement slot"):
        maximize_requirement(
            players, [replace(requirements[0], slot_ids=("elsewhere",))], formation
        )
    with pytest.raises(ValueError, match="active"):
        maximize_requirement(players, [replace(requirements[0], status="research")], formation)


@pytest.mark.parametrize("value,normalizer", [(1e13, 1), (1e12, 1e-10), (1, 1e-300)])
def test_large_raw_or_normalized_coefficients_fail_cleanly(case, value, normalizer):
    players, requirements, formation = case
    players = [replace(players[0], values={"p": value})]
    requirements = [replace(requirements[0], normalizer=normalizer)]
    with pytest.raises(ValueError):
        maximize_requirement(players, requirements, formation)


def test_half_even_objective_is_exact_and_distinct_from_conservative_floor(case):
    result = maximize_requirement(*case, quantization=1)
    assert result.objective.integer_value == 4  # round(3.5), not floor(3.5)
    assert result.objective.integer_upper_bound == 4
    assert result.objective.achieved == 3.5
    assert result.objective.quantized_value == 4
    floor = result.provenance["floor_certificates"]["progression"]
    assert floor["integer_achieved"] == 3
    assert result.objective.raw_rounding_error_bound >= 0.5


def test_decoded_certificate_uses_original_units_and_raw_error_bound(case):
    players, requirements, formation = case
    requirements = [replace(requirements[0], normalizer=3)]
    result = maximize_requirement(players, requirements, formation, quantization=7)
    objective = result.objective
    assert objective.quantized_value == float(Fraction(objective.integer_value, 7) * 3)
    assert abs(objective.achieved - objective.quantized_value) <= objective.raw_rounding_error_bound
    assert objective.raw_rounding_error_bound >= float(Fraction(3, 14))


def test_all_active_floors_are_hard_and_unmeasured_remains_unmeasured(case):
    players, requirements, formation = case
    requirements += [
        TacticalRequirement(
            "unseen", "Unseen", "absent", 100, 1, status="unavailable", evidence_class="UNAVAILABLE"
        )
    ]
    result = maximize_requirement(players, requirements, formation)
    measured, unseen = result.requirements
    assert measured.hard and measured.status == "COVERED"
    assert unseen.status == "UNMEASURED" and not unseen.hard and unseen.achieved is None
    impossible = maximize_requirement(players, [replace(requirements[0], minimum=4)], formation)
    assert impossible.solution_status == "INFEASIBLE"
    assert impossible.objective.certification == "NO_SOLUTION"
    assert impossible.requirements[0].hard
    assert impossible.requirements[0].status == "NOT_EVALUATED"
    assert "conservative" in " ".join(impossible.infeasibility_reasons)


@pytest.mark.parametrize("status", [cp_model.UNKNOWN, cp_model.MODEL_INVALID])
def test_no_incumbent_is_not_infeasibility(case, monkeypatch, status):
    monkeypatch.setattr(cp_model.CpSolver, "solve", lambda *_: status)
    result = maximize_requirement(*case)
    assert result.solution_status in {"UNKNOWN", "MODEL_INVALID"}
    assert not result.assignments
    assert not result.infeasibility_reasons
    assert result.objective.certification == "NO_SOLUTION"
    assert result.objective.integer_value is None
    assert result.objective.integer_upper_bound is None
    assert "does not establish infeasibility" in " ".join(result.warnings)


def test_deadline_before_solve_returns_unknown_not_infeasible(case, monkeypatch):
    clock = iter((0, 2))
    monkeypatch.setattr(tradeoffs.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(cp_model.CpSolver, "solve", lambda *_: pytest.fail("deadline exceeded"))
    result = maximize_requirement(*case, time_limit=1)
    assert result.solution_status == "UNKNOWN"
    assert result.infeasibility_reasons == ()


def test_feasible_has_upper_bound_but_never_optimal_certificate(case, monkeypatch):
    original = cp_model.CpSolver

    class UnprovenSolver:
        def __init__(self):
            self.inner = original()
            self.parameters = self.inner.parameters

        def solve(self, model):
            self.inner.solve(model)
            return cp_model.FEASIBLE

        def value(self, variable):
            return self.inner.value(variable)

        @property
        def best_objective_bound(self):
            return self.inner.best_objective_bound + 2.25

    monkeypatch.setattr(cp_model, "CpSolver", UnprovenSolver)
    result = maximize_requirement(*case, quantization=1)
    assert result.solution_status == "FEASIBLE"
    assert result.objective.certification == "FEASIBLE_NOT_PROVEN"
    assert result.objective.integer_value == 4
    assert result.objective.integer_upper_bound == 7  # outward, not nearest or downward


def test_fresh_provenance_retains_sources_not_old_solve_certificates(case):
    source = {
        "dataset_hash": "data",
        "cutoff": "2018-05-06",
        "bootstrap_version": "shared-v1",
        "bootstrap_worlds": 12,
        "bootstrap_used_worlds": [1],
        "bootstrap_world_fingerprint": "old-world",
        "solver_stages": [{"status": "OPTIMAL"}],
        "solver_version": "old",
        "input_fingerprint": "old-input",
        "mode": "BALANCE",
        "tie_analysis_complete": True,
        "alternative_search": {"status": "EXHAUSTED"},
        "objective_vector": [0, 0],
    }
    result = maximize_requirement(*case, provenance=source)
    metadata = result.provenance
    assert metadata["dataset_hash"] == "data" and metadata["cutoff"] == "2018-05-06"
    assert metadata["bootstrap_version"] == "shared-v1"
    assert metadata["solver_version"] != "old"
    assert metadata["input_fingerprint"] != "old-input"
    assert metadata["input_contract"]["source_provenance"] == source
    for key in (
        "bootstrap_worlds",
        "bootstrap_used_worlds",
        "bootstrap_world_fingerprint",
        "solver_stages",
        "mode",
        "tie_analysis_complete",
        "alternative_search",
        "objective_vector",
    ):
        assert key not in metadata
    for key in ("objective_vector", "selection_frequencies", "alternatives"):
        assert key not in asdict(result)


def test_policy_source_seed_and_quantization_all_invalidate_identity(case, monkeypatch):
    baseline = maximize_requirement(*case)
    fingerprints = {baseline.provenance["input_fingerprint"]}
    for options in (
        {"seed": 9},
        {"quantization": 1000},
        {"provenance": {"dataset_hash": "new"}},
        {"locked": (1,)},
        {"excluded": (1,)},
        {"time_limit": 10},
    ):
        fingerprints.add(maximize_requirement(*case, **options).provenance["input_fingerprint"])
    monkeypatch.setattr(tradeoffs, "_source_fingerprints", lambda: {"tradeoffs.py": "changed"})
    fingerprints.add(maximize_requirement(*case).provenance["input_fingerprint"])
    assert len(fingerprints) == 8
