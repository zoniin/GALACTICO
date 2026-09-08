"""Exact finite enumeration is the oracle; it does not call solver internals."""

from itertools import permutations

import numpy as np
import pytest

from galactico.optimization.xi import (
    FORMATIONS,
    Candidate,
    Formation,
    Slot,
    TacticalRequirement,
    removal_sensitivity,
    solve_xi,
)


def formation(n=2):
    return Formation("tiny", tuple(Slot(str(i), str(i), ("MF",), 0.5, 0.5) for i in range(n)))


def test_removal_keeps_hard_policy_seed_scale_and_template_without_fake_swaps():
    players = [Candidate(i, str(i), "MF", {"p": value}) for i, value in ((1, 2), (2, 1), (3, 0))]
    requirements = [TacticalRequirement("p", "Progression", "p", 3, 3)]
    base = solve_xi(players, requirements, formation(), mode="SATISFY", seed=17, quantization=10)
    assert base.solution_status == "OPTIMAL"
    removed = removal_sensitivity(base, players, requirements, player_ids=[1])[1]
    assert removed["solution_status"] == "INFEASIBLE"
    assert removed["comparison_available"] is False
    assert removed["in"] == removed["out"] == []
    assert removed["provenance"]["mode"] == "SATISFY"
    assert removed["provenance"]["seed"] == 17
    assert removed["provenance"]["quantization"] == 10
    assert removed["provenance"]["formation_inputs"] == base.provenance["formation_inputs"]


def oracle(players, requirements, shape, scale=100_000, locked=(), excluded=()):
    best, winners = None, []
    for assignment in permutations(players, len(shape.slots)):
        ids = {p.player_id for p in assignment}
        if not set(locked) <= ids or set(excluded) & ids:
            continue
        if any(
            p.minutes <= 0
            or p.position not in s.allowed_positions
            or (p.eligible_slots is not None and s.slot_id not in p.eligible_slots)
            for p, s in zip(assignment, shape.slots, strict=True)
        ):
            continue
        deficits, valid = [], True
        for r in requirements:
            if not r.active:
                continue
            participants = [
                p
                for p, s in zip(assignment, shape.slots, strict=True)
                if not r.slot_ids or s.slot_id in r.slot_ids
            ]
            if any(p.values.get(r.metric) is None for p in participants):
                valid = False
                break
            shortfall = max(
                0,
                round(r.minimum / r.normalizer * scale)
                - sum(round(p.values[r.metric] / r.normalizer * scale) for p in participants),
            )
            if r.hard and shortfall:
                valid = False
            deficits.append(shortfall)
        if not valid:
            continue
        objective = (max(deficits, default=0) / scale, sum(deficits) / scale)
        if best is None or objective < best:
            best, winners = objective, [ids]
        elif objective == best:
            winners.append(ids)
    return best, winners


def test_random_tiny_instances_match_exhaustive_oracle():
    rng = np.random.default_rng(130)
    for _ in range(20):
        players = [
            Candidate(i, str(i), "MF", dict(zip(("p", "w"), rng.uniform(0, 2, 2), strict=True)))
            for i in range(5)
        ]
        requirements = [TacticalRequirement(k, k, k, 3.5, n) for k, n in (("p", 3.5), ("w", 2.0))]
        shape = formation(3)
        expected, winners = oracle(players, requirements, shape)
        result = solve_xi(players, requirements, shape)
        assert result.solution_status == "OPTIMAL"
        assert result.objective_vector == expected
        assert {a.player_id for a in result.assignments} in winners
        for pid, membership in result.equivalent_players.items():
            assert membership["possible"] == any(pid in xi for xi in winners)
            assert membership["necessary"] == all(pid in xi for xi in winners)


def test_tied_representative_never_becomes_a_fake_core():
    players = [Candidate(i, str(i), "MF", {"p": 1.0}) for i in range(3)]
    requirement = [TacticalRequirement("p", "p", "p", 1.0, 1.0)]
    worlds = {w: {i: {"p": 1.0 + w} for i in range(3)} for w in range(3)}
    result = solve_xi(players, requirement, formation(), worlds=worlds)
    assert sum(f.selection_frequency for f in result.selection_frequencies) == 2
    assert all(f.necessary_frequency == 0 for f in result.selection_frequencies)
    assert all(f.possible_frequency == 1 for f in result.selection_frequencies)
    assert all(f.label == "CONTESTED" for f in result.selection_frequencies)


def test_eligibility_missing_values_and_no_appearances_are_hard():
    players = [
        Candidate(1, "a", "MF", {"p": 1}),
        Candidate(2, "b", "MF", {"p": 2}),
        Candidate(3, "keeper superstar", "GK", {"p": 1000}),
        Candidate(4, "never played", "MF", {"p": 1000}, minutes=0),
        Candidate(5, "missing", "MF", {"p": None}),
    ]
    r = [TacticalRequirement("p", "p", "p", 4, 4)]
    result = solve_xi(players, r, formation())
    assert {a.player_id for a in result.assignments} == {1, 2}
    assert result.requirements[0].status == "DEFICIT"
    assert solve_xi(players, r, formation(), locked=[3]).solution_status == "INFEASIBLE"
    assert solve_xi(players, r, formation(), mode="SATISFY").solution_status == "INFEASIBLE"
    assert (
        solve_xi(players, r, formation(), locked=[1], excluded=[1]).solution_status == "INFEASIBLE"
    )


def test_order_invariance_uniqueness_and_lock_cascade():
    players = [
        Candidate(1, "flexible", "MF", {"p": 4}, eligible_slots=("0", "1")),
        Candidate(2, "slot zero", "MF", {"p": 3}, eligible_slots=("0",)),
        Candidate(3, "slot one", "MF", {"p": 1}, eligible_slots=("1",)),
    ]
    req = [TacticalRequirement("p", "p", "p", 9, 9)]
    a = solve_xi(players, req, formation())
    b = solve_xi(players[::-1], req, formation())
    assert a.assignments == b.assignments
    assert len({p.player_id for p in a.assignments}) == 2
    locked = solve_xi(players, req, formation(), locked=[3])
    assert {p.slot_id: p.player_id for p in locked.assignments} == {"0": 1, "1": 3}
    assert a.provenance["input_fingerprint"] != locked.provenance["input_fingerprint"]


def test_missing_world_exposure_discards_whole_world():
    players = [Candidate(i, str(i), "MF", {"p": i}) for i in (1, 2, 3)]
    req = [TacticalRequirement("p", "p", "p", 6, 6)]
    worlds = {
        0: {i: {"p": i} for i in (1, 2, 3)},
        1: {i: {"p": None if i == 1 else i} for i in (1, 2, 3)},
    }
    result = solve_xi(players, req, formation(), worlds=worlds)
    assert result.provenance["bootstrap_used_worlds"] == [0]
    assert result.provenance["bootstrap_discarded_worlds"][0]["world_id"] == 1


def test_formations_are_eleven_slots_with_one_keeper():
    for f in FORMATIONS.values():
        assert len(f.slots) == 11
        assert sum(s.allowed_positions == ("GK",) for s in f.slots) == 1
    with pytest.raises(ValueError):
        solve_xi([Candidate(1, "a", "MF", {})] * 2, [], formation())


def test_impossible_requirement_is_preserved_and_never_silently_relaxed():
    players = [Candidate(i, str(i), "MF", {"p": 1}) for i in (1, 2, 3)]
    requirements = [
        TacticalRequirement("p", "Progression", "p", 3, 3),
        TacticalRequirement(
            "defense",
            "Defense",
            "defense",
            0,
            1,
            evidence_class="UNAVAILABLE",
            status="unavailable",
        ),
    ]
    soft = solve_xi(players, requirements, formation())
    assert soft.solution_status == "OPTIMAL"
    assessments = {r.requirement_id: r for r in soft.requirements}
    assert assessments["p"].minimum == 3
    assert assessments["p"].achieved == 2
    assert assessments["p"].deficit == 1
    assert assessments["p"].status == "DEFICIT"

    hard = solve_xi(players, requirements, formation(), mode="SATISFY")
    assert hard.solution_status == "INFEASIBLE"
    assert hard.assignments == ()
    assert hard.objective_vector == ()
    assessments = {r.requirement_id: r for r in hard.requirements}
    assert assessments["p"].minimum == 3
    assert assessments["p"].hard
    assert assessments["p"].status == "NOT_EVALUATED"
    assert assessments["p"].achieved is None
    assert assessments["p"].deficit is None
    assert assessments["p"].normalized_deficit is None
    assert assessments["defense"].status == "UNMEASURED"
