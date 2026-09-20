"""Independent exhaustive oracle for explicit-floor progression exploration.

No solver helper enters the oracle: it checks every ordered assignment, exact
input-number fractions, conservative floors and nearest-even objective directly.
The historical smoke case tests this declared accounting model, not causal value.
"""

from dataclasses import asdict, replace
from fractions import Fraction
from itertools import permutations
from math import ceil, floor
from random import Random

import pytest

from galactico.optimization.xi import Candidate, Formation, Slot, TacticalRequirement
from galactico.optimization.xi.tradeoffs import maximize_requirement


def shape():
    return Formation(
        "three-slots",
        tuple(Slot(key, key, ("MF",), 0.5, 0.5) for key in ("anchor", "left", "right")),
    )


def finite_oracle(players, requirements, formation, *, scale, locked=(), excluded=()):
    """Return the exact integer optimum and all ordered optimum assignments."""
    active = [r for r in requirements if r.status == "active" and r.evidence_class != "UNAVAILABLE"]
    target = next(r for r in active if r.requirement_id == "progression")
    optimum, winners = None, set()
    for assignment in permutations(players, len(formation.slots)):
        ids = tuple(p.player_id for p in assignment)
        if not set(locked) <= set(ids) or set(excluded) & set(ids):
            continue
        pairs = tuple(zip(assignment, formation.slots, strict=True))
        if any(
            player.minutes <= 0
            or player.position not in slot.allowed_positions
            or (player.eligible_slots is not None and slot.slot_id not in player.eligible_slots)
            for player, slot in pairs
        ):
            continue
        valid = True
        for requirement in active:
            relevant = [
                player
                for player, slot in pairs
                if not requirement.slot_ids or slot.slot_id in requirement.slot_ids
            ]
            if any(player.values.get(requirement.metric) is None for player in relevant):
                valid = False
                break
            # Fractions are independently formed from the exact supplied values,
            # not from the result of an already-rounded float division.
            achieved = sum(
                floor(
                    Fraction(player.values[requirement.metric])
                    / Fraction(requirement.normalizer)
                    * scale
                )
                for player in relevant
            )
            minimum = ceil(Fraction(requirement.minimum) / Fraction(requirement.normalizer) * scale)
            if achieved < minimum:
                valid = False
                break
        if not valid:
            continue
        value = sum(
            round(Fraction(player.values[target.metric]) / Fraction(target.normalizer) * scale)
            for player, slot in pairs
            if not target.slot_ids or slot.slot_id in target.slot_ids
        )
        if optimum is None or value > optimum:
            optimum, winners = value, {ids}
        elif value == optimum:
            winners.add(ids)
    return optimum, winners


def assert_matches_oracle(result, expected, winners):
    objective = asdict(result)["objective"]
    if expected is None:
        assert result.solution_status == "INFEASIBLE"
        assert result.assignments == ()
        assert objective["certification"] == "NO_SOLUTION"
        return
    assert result.solution_status == "OPTIMAL"
    assert objective["integer_value"] == expected
    assert objective["integer_upper_bound"] == expected
    assert objective["certification"] == "QUANTIZED_OPTIMAL"
    chosen = tuple(a.player_id for a in result.assignments)
    assert chosen in winners
    assert len(chosen) == len(set(chosen))
    # All active floors are hard even when their input .hard flag was False.
    assert all(r.hard for r in result.requirements if r.achieved is not None)
    assert all(r.achieved >= r.minimum for r in result.requirements if r.achieved is not None)


def test_random_small_instances_match_every_assignment_oracle():
    rng = Random(20260918)
    observed_statuses = set()
    formation = shape()
    for iteration in range(36):
        scale = rng.choice((3, 8, 100_000))
        players = []
        for pid in range(6):
            eligible = tuple(slot.slot_id for slot in formation.slots if rng.random() > 0.15)
            values = {
                "p": rng.randrange(0, 17) / 4,
                "l": None if rng.random() < 0.10 else rng.randrange(0, 13) / 4,
                "r": None if rng.random() < 0.10 else rng.randrange(0, 13) / 4,
            }
            players.append(Candidate(pid, str(pid), "MF", values, eligible_slots=eligible))
        requirements = [
            TacticalRequirement("progression", "Progression", "p", 0, rng.choice((0.5, 1, 1.5, 3))),
            TacticalRequirement(
                "left",
                "Left origins",
                "l",
                rng.choice((0, 1, 3, 8)),
                rng.choice((0.5, 1, 3)),
                slot_ids=("left",),
            ),
            TacticalRequirement(
                "right",
                "Right origins",
                "r",
                rng.choice((0, 1, 3, 8)),
                rng.choice((0.5, 1, 3)),
                slot_ids=("right",),
            ),
            TacticalRequirement(
                "unknown",
                "Unknown",
                "absent",
                1000,
                1,
                evidence_class="UNAVAILABLE",
                status="unavailable",
            ),
        ]
        locked = (rng.randrange(6),) if iteration % 3 == 0 else ()
        excluded = (rng.randrange(6),) if iteration % 5 == 0 else ()
        expected, winners = finite_oracle(
            players, requirements, formation, scale=scale, locked=locked, excluded=excluded
        )
        result = maximize_requirement(
            players, requirements, formation, quantization=scale, locked=locked, excluded=excluded
        )
        assert_matches_oracle(result, expected, winners)
        observed_statuses.add(result.solution_status)
    assert observed_statuses == {"OPTIMAL", "INFEASIBLE"}


def test_tighter_floors_cannot_improve_same_quantized_objective():
    formation = shape()
    players = [
        Candidate(i, str(i), "MF", {"p": p, "side": side})
        for i, (p, side) in enumerate(((9, 0), (8, 0), (7, 1), (5, 2), (3, 3), (1, 4)))
    ]
    previous = None
    saw_strict_decrease = False
    infeasible_seen = False
    for minimum in (0, 1, 2, 3, 4, 5):
        requirements = [
            TacticalRequirement("progression", "Progression", "p", 0, 3),
            TacticalRequirement("side", "Side", "side", minimum, 1, slot_ids=("left",)),
        ]
        expected, winners = finite_oracle(players, requirements, formation, scale=100)
        result = maximize_requirement(players, requirements, formation, quantization=100)
        assert_matches_oracle(result, expected, winners)
        if expected is None:
            infeasible_seen = True
        else:
            assert not infeasible_seen
            if previous is not None:
                assert expected <= previous
                saw_strict_decrease |= expected < previous
            previous = expected
    assert saw_strict_decrease and infeasible_seen


def test_target_slot_incidence_preserves_relevant_missingness_and_lock_cascade():
    formation = shape()
    players = [
        Candidate(
            1, "anchor without target", "MF", {"p": None, "origin": 0}, eligible_slots=("anchor",)
        ),
        Candidate(2, "flexible", "MF", {"p": 4, "origin": 1}, eligible_slots=("left", "right")),
        Candidate(3, "left specialist", "MF", {"p": 3, "origin": 1}, eligible_slots=("left",)),
        Candidate(4, "right lock", "MF", {"p": 1, "origin": 1}, eligible_slots=("right",)),
        Candidate(
            5,
            "missing relevant target",
            "MF",
            {"p": None, "origin": 100},
            eligible_slots=("left", "right"),
        ),
        Candidate(6, "ineligible keeper superstar", "GK", {"p": 100, "origin": 100}),
        Candidate(7, "no appearances", "MF", {"p": 100, "origin": 100}, minutes=0),
    ]
    requirements = [
        TacticalRequirement("progression", "Progression", "p", 0, 1, slot_ids=("left", "right")),
        TacticalRequirement("origins", "Origins", "origin", 1, 1),
    ]
    initial = maximize_requirement(players, requirements, formation)
    assert {a.slot_id: a.player_id for a in initial.assignments} == {
        "anchor": 1,
        "left": 3,
        "right": 2,
    }
    expected, winners = finite_oracle(players, requirements, formation, scale=100_000, locked=(4,))
    locked = maximize_requirement(players, requirements, formation, locked=(4,))
    assert_matches_oracle(locked, expected, winners)
    assert {a.slot_id: a.player_id for a in locked.assignments} == {
        "anchor": 1,
        "left": 2,
        "right": 4,
    }
    reverse = maximize_requirement(players[::-1], requirements[::-1], formation, locked=(4,))
    assert reverse.assignments == locked.assignments
    assert reverse.provenance["input_fingerprint"] == locked.provenance["input_fingerprint"]
    assert initial.provenance["input_fingerprint"] != locked.provenance["input_fingerprint"]


def test_primary_optimum_certificate_is_not_a_pareto_certificate():
    formation = Formation("single", (Slot("only", "Only", ("MF",), 0.5, 0.5),))
    players = [
        Candidate(1, "less origin activity", "MF", {"p": 1, "origin": 1}),
        Candidate(2, "more origin activity", "MF", {"p": 1, "origin": 2}),
    ]
    requirements = [
        TacticalRequirement("progression", "Progression", "p", 0, 1),
        TacticalRequirement("origin", "Origins", "origin", 0, 1),
    ]
    expected, winners = finite_oracle(players, requirements, formation, scale=100_000)
    # The declared optimum set legitimately includes a point dominated in the
    # second descriptor. Style being larger is not itself football improvement.
    assert winners == {(1,), (2,)}
    result = maximize_requirement(players, requirements, formation)
    assert_matches_oracle(result, expected, winners)
    assert asdict(result)["objective"]["certification"] == "QUANTIZED_OPTIMAL"
    assert "pareto_optimal" not in asdict(result)
    assert not hasattr(result, "selection_frequencies")


def test_exact_number_quantization_does_not_round_intermediate_division():
    formation = Formation("single", (Slot("only", "Only", ("MF",), 0.5, 0.5),))
    players = [Candidate(1, "one unit", "MF", {"p": 1.0})]
    requirements = [TacticalRequirement("progression", "Progression", "p", 1.0, 49.0)]
    # Binary-float division followed by multiplication loses this exact unit:
    # 1.0 / 49.0 * 49 == 0.9999999999999999. The declared exact-input-number
    # policy must not introduce an artificial floor rejection at this boundary.
    expected, winners = finite_oracle(players, requirements, formation, scale=49)
    assert expected == 1
    result = maximize_requirement(players, requirements, formation, quantization=49)
    assert_matches_oracle(result, expected, winners)
    assert asdict(result)["objective"]["achieved"] == 1.0


def test_conservative_floor_can_reject_an_exact_raw_boundary_without_relaxation():
    formation = Formation("single", (Slot("only", "Only", ("MF",), 0.5, 0.5),))
    players = [Candidate(1, "boundary unit", "MF", {"p": 0.29})]
    requirements = [TacticalRequirement("progression", "Progression", "p", 0.29, 1)]
    # The *supplied* float .29 is strictly below 29/100. Its lower coefficient
    # is 28 and its upper floor is 29 even though .29 * 100 rounds to 29.0.
    # Conservative quantization can exclude raw-feasible points; no exact-real
    # infeasibility claim may be inferred from the model's certificate.
    assert Fraction(0.29) < Fraction(29, 100)
    expected, winners = finite_oracle(players, requirements, formation, scale=100)
    assert expected is None
    result = maximize_requirement(players, requirements, formation, quantization=100)
    assert_matches_oracle(result, expected, winners)


def test_equal_quantized_objectives_are_not_equal_raw_values_or_raw_optimality():
    formation = Formation("single", (Slot("only", "Only", ("MF",), 0.5, 0.5),))
    players = [
        Candidate(1, "lower raw", "MF", {"p": 1.26}),
        Candidate(2, "higher raw", "MF", {"p": 1.49}),
    ]
    requirements = [TacticalRequirement("progression", "Progression", "p", 0, 1)]
    expected, winners = finite_oracle(players, requirements, formation, scale=1)
    assert expected == 1 and winners == {(1,), (2,)}
    result = maximize_requirement(players, requirements, formation, quantization=1)
    assert_matches_oracle(result, expected, winners)
    objective = asdict(result)["objective"]
    assert objective["quantized_value"] == objective["quantized_upper_bound"] == 1
    assert objective["achieved"] in (1.26, 1.49)
    assert objective["achieved"] != objective["quantized_value"]


def test_actual_madrid_floor_tradeoff_is_an_accounting_smoke_not_a_quality_test():
    from galactico.api.decision_lab import decision_inputs
    from galactico.optimization.historical import PUBLIC, load_snapshot

    required_files = [
        PUBLIC / "players.parquet",
        *[
            PUBLIC / "competition=Spain" / name
            for name in ("actions.parquet", "matches.parquet", "lineups.parquet")
        ],
    ]
    if not all(path.exists() for path in required_files):
        pytest.skip("local legally hosted historical corpus unavailable")
    snapshot = load_snapshot(2565907, worlds=0)
    players, requirements = decision_inputs(snapshot, "4-3-3")
    results = []
    for multiplier in (1, 1.2, 1.3):
        policy = [
            replace(r, minimum=r.minimum * multiplier)
            if r.requirement_id in {"left_pass_origins", "right_pass_origins"}
            else r
            for r in requirements
        ]
        result = maximize_requirement(players, policy, provenance=snapshot.provenance)
        results.append(result)
        if result.assignments:
            assert len(result.assignments) == len({a.player_id for a in result.assignments}) == 11
            assert all(
                r.achieved >= r.minimum for r in result.requirements if r.achieved is not None
            )
            assert all(
                r.status == "UNMEASURED"
                for r in result.requirements
                if r.requirement_id in {"chance_creation", "rest_defense", "goalkeeping"}
            )
    assert [r.solution_status for r in results] == ["OPTIMAL", "OPTIMAL", "INFEASIBLE"]
    first, tighter = (asdict(r)["objective"] for r in results[:2])
    assert first["integer_value"] > tighter["integer_value"]
    assert first["achieved"] == pytest.approx(3.803025211830119)
    assert tighter["achieved"] == pytest.approx(3.7890563874213306)
    # Preserved evidence cutoff, not the evaluated match's events or outcome.
    assert results[0].provenance["cutoff"] == snapshot.provenance["cutoff"]
    assert results[0].provenance["training_latest_date"] < snapshot.provenance["cutoff"]
    assert not hasattr(results[0], "selection_frequencies")
