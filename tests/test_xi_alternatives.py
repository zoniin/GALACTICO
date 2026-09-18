"""Diverse optimal witnesses checked against independent finite enumeration."""

from itertools import combinations, permutations

import pytest
from ortools.sat.python import cp_model

from galactico.optimization.xi import Candidate, Formation, Slot, TacticalRequirement, solve_xi
from galactico.optimization.xi import solver as engine


def shape(n=2):
    return Formation("tiny", tuple(Slot(str(i), str(i), ("MF",), .5, .5) for i in range(n)))


def roster(n=8):
    return [Candidate(i, str(i), "MF", {"p": 1.0}) for i in range(1, n + 1)]


def player_set(result):
    return frozenset(a.player_id for a in result.assignments)


def brute_force(players, requirements, formation, scale=100_000, locked=(), excluded=()):
    """No solver helpers: enumerate assignments, eligibility and integer losses."""
    best, winners = None, set()
    for assigned in permutations(players, len(formation.slots)):
        ids = frozenset(p.player_id for p in assigned)
        if not set(locked) <= ids or set(excluded) & ids:
            continue
        if any(
            p.minutes <= 0 or p.position not in s.allowed_positions
            or (p.eligible_slots is not None and s.slot_id not in p.eligible_slots)
            for p, s in zip(assigned, formation.slots, strict=True)
        ):
            continue
        losses, valid = [], True
        for requirement in requirements:
            if not requirement.active:
                continue
            relevant = [p for p, s in zip(assigned, formation.slots, strict=True)
                        if not requirement.slot_ids or s.slot_id in requirement.slot_ids]
            if any(p.values.get(requirement.metric) is None for p in relevant):
                valid = False
                break
            actual = sum(round(p.values[requirement.metric] / requirement.normalizer * scale)
                         for p in relevant)
            target = round(requirement.minimum / requirement.normalizer * scale)
            loss = max(0, target - actual)
            if requirement.hard and loss:
                valid = False
            losses.append(loss)
        if not valid:
            continue
        objective = (max(losses, default=0) / scale, sum(losses) / scale)
        if best is None or objective < best:
            best, winners = objective, {ids}
        elif objective == best:
            winners.add(ids)
    return best, winners


def test_pairwise_diverse_witnesses_match_brute_force_and_exhaustion_is_conditional():
    players = roster(8)
    requirements = [TacticalRequirement("p", "p", "p", 3, 3)]
    expected, winners = brute_force(players, requirements, shape())
    result = solve_xi(players, requirements, shape(), alternative_count=5)
    assert result.objective_vector == expected
    assert len(result.alternatives) == 3
    assert result.provenance["alternative_search"]["status"] == "EXHAUSTED"
    sets = [player_set(r) for r in (result, *result.alternatives)]
    for candidate in (result, *result.alternatives):
        assert candidate.objective_vector == expected
        assert player_set(candidate) in winners
        assert len(candidate.assignments) == len(player_set(candidate)) == 2
        assert candidate.requirements[0].achieved == 2
    for a, b in combinations(sets, 2):
        assert len(a - b) >= 2
    # Remaining optima exist, but none passes all sequential diversity cuts.
    assert winners - set(sets)
    assert not any(all(len(other - chosen) >= 2 for chosen in sets) for other in winners)
    for alternative in result.alternatives:
        assert alternative.player_changes == 2
        assert set(alternative.incoming_player_ids) == player_set(alternative) - sets[0]
        assert set(alternative.outgoing_player_ids) == sets[0] - player_set(alternative)
        assert alternative.provenance["objective_certification"] == "BASELINE_OPTIMAL"
        assert alternative.provenance["parent_input_fingerprint"] == (
            result.provenance["input_fingerprint"]
        )
    # The exploration cuts must never turn tied players into a stable core.
    assert all(v == {"necessary": False, "possible": True}
               for v in result.equivalent_players.values())


def test_both_lexicographic_stages_are_preserved_and_unique_best_exhausts():
    players = [Candidate(1, "1", "MF", {"p": 2, "q": 0}),
               Candidate(2, "2", "MF", {"p": 0, "q": 2}),
               Candidate(3, "3", "MF", {"p": 0, "q": 1}),
               Candidate(4, "4", "MF", {"p": 0, "q": 0})]
    requirements = [TacticalRequirement("p", "p", "p", 5, 1),
                    TacticalRequirement("q", "q", "q", 5, 1)]
    objective, winners = brute_force(players, requirements, shape())
    result = solve_xi(players, requirements, shape(), alternative_count=5,
                      minimum_player_changes=1)
    assert objective == (3, 6)
    assert winners == {frozenset((1, 2))}
    assert result.objective_vector == objective
    assert result.alternatives == ()
    assert result.provenance["alternative_search"]["status"] == "EXHAUSTED"


def test_locks_exclusions_missing_measurements_and_eligibility_survive_exploration():
    players = roster(7) + [Candidate(8, "keeper", "GK", {"p": 100}),
                           Candidate(9, "missing", "MF", {"p": None}),
                           Candidate(10, "zero minutes", "MF", {"p": 100}, minutes=0)]
    # An exact integer normalizer keeps this eligibility test off a rounding boundary.
    requirements = [TacticalRequirement("p", "p", "p", 3, 1, hard=True)]
    expected, winners = brute_force(players, requirements, shape(3), locked=(1,), excluded=(7,))
    result = solve_xi(players, requirements, shape(3), locked=[1], excluded=[7],
                      alternative_count=5, minimum_player_changes=2)
    assert result.alternatives
    for candidate in (result, *result.alternatives):
        assert candidate.objective_vector == expected
        assert player_set(candidate) in winners
        assert 1 in player_set(candidate)
        assert not player_set(candidate) & {7, 8, 9, 10}
        assert candidate.requirements[0].hard
    impossible = solve_xi(players, requirements, shape(3), locked=[8], alternative_count=2)
    assert impossible.solution_status == "INFEASIBLE"
    assert impossible.alternatives == ()
    assert impossible.provenance["alternative_search"]["status"] == "UNCERTIFIED_BASELINE"


def test_same_maximum_but_worse_total_shortfall_is_not_an_equivalent_xi():
    players = [
        Candidate(1, "best", "MF", {"p": 2, "q": 3}),
        Candidate(2, "worse total", "MF", {"p": 2, "q": 2}),
    ]
    requirements = [
        TacticalRequirement("p", "p", "p", 5, 1),
        TacticalRequirement("q", "q", "q", 5, 1),
    ]
    # Both have maximum shortfall 3; only player 1 has total shortfall 5.
    expected, winners = brute_force(players, requirements, shape(1))
    result = solve_xi(players, requirements, shape(1), alternative_count=2,
                      minimum_player_changes=1)
    assert expected == (3, 5)
    assert winners == {frozenset([1])}
    assert result.objective_vector == expected
    assert result.alternatives == ()
    assert result.provenance["alternative_search"]["status"] == "EXHAUSTED"


def test_input_order_invariance_and_exploration_fingerprint_separation():
    players = roster()
    baseline = solve_xi(players, [], shape())
    one = solve_xi(players, [], shape(), alternative_count=1)
    reverse = solve_xi(players[::-1], [], shape(), alternative_count=1)
    more = solve_xi(players, [], shape(), alternative_count=2)
    assert baseline.assignments == one.assignments == reverse.assignments == more.assignments
    assert one.alternatives == reverse.alternatives
    assert one.provenance["alternative_search"]["status"] == "LIMIT_REACHED"
    assert baseline.provenance["alternative_search"]["status"] == "NOT_REQUESTED"
    assert baseline.provenance["input_fingerprint"] == one.provenance["input_fingerprint"]
    assert one.provenance["input_fingerprint"] == more.provenance["input_fingerprint"]
    assert one.provenance["alternative_search"]["exploration_fingerprint"] != (
        more.provenance["alternative_search"]["exploration_fingerprint"]
    )
    assert baseline.equivalent_players == more.equivalent_players


def override_status(monkeypatch, on_call, status):
    original = engine._solver
    calls = []

    class Proxy:
        def __init__(self, actual, number):
            self.actual, self.number = actual, number

        def solve(self, model):
            actual_status = self.actual.solve(model)
            return status if self.number == on_call else actual_status

        def __getattr__(self, name):
            return getattr(self.actual, name)

    def factory(deadline, seed):
        calls.append(1)
        return Proxy(original(deadline, seed), len(calls))

    monkeypatch.setattr(engine, "_solver", factory)
    return calls


@pytest.mark.parametrize("witness_status,expected", [(cp_model.UNKNOWN, "TIME_LIMIT"),
                                                    (cp_model.MODEL_INVALID, "MODEL_INVALID")])
def test_unknown_and_invalid_search_never_claim_exhaustion(monkeypatch, witness_status, expected):
    override_status(monkeypatch, 3, witness_status)
    result = solve_xi(roster(), [], shape(), analyze_ties=False, alternative_count=2)
    assert result.solution_status == "OPTIMAL"
    assert not result.alternatives
    assert result.provenance["alternative_search"]["status"] == expected


def test_feasible_witness_is_valid_but_uncertified_baseline_is_not(monkeypatch):
    override_status(monkeypatch, 3, cp_model.FEASIBLE)
    result = solve_xi(roster(), [], shape(), analyze_ties=False, alternative_count=1)
    assert result.alternatives[0].solution_status == "FEASIBLE"
    assert result.alternatives[0].objective_vector == result.objective_vector
    monkeypatch.undo()
    calls = override_status(monkeypatch, 2, cp_model.FEASIBLE)
    result = solve_xi(roster(), [], shape(), analyze_ties=False, alternative_count=1)
    assert result.solution_status == "FEASIBLE"
    assert not result.alternatives
    assert len(calls) == 2
    assert result.provenance["alternative_search"]["status"] == "UNCERTIFIED_BASELINE"


def test_deadline_prevents_starting_exploration(monkeypatch):
    original = engine._solver
    clock = [0.0]
    calls = []

    class Proxy:
        def __init__(self, actual):
            self.actual = actual

        def solve(self, model):
            result = self.actual.solve(model)
            if len(calls) == 2:
                clock[0] = 100.0
            return result

        def __getattr__(self, name):
            return getattr(self.actual, name)

    def factory(deadline, seed):
        calls.append(1)
        return Proxy(original(deadline, seed))

    monkeypatch.setattr(engine.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(engine, "_solver", factory)
    result = solve_xi(roster(), [], shape(), analyze_ties=False, alternative_count=2)
    assert len(calls) == 2
    assert result.provenance["alternative_search"]["status"] == "TIME_LIMIT"
    assert not result.alternatives


def test_bootstrap_worlds_do_not_repeat_alternative_search(monkeypatch):
    original = engine.solve_xi
    requests = []

    def tracked(*args, **kwargs):
        requests.append(kwargs.get("alternative_count", 0))
        return original(*args, **kwargs)

    monkeypatch.setattr(engine, "solve_xi", tracked)
    result = original(roster(4), [], shape(), alternative_count=1,
                      worlds={0: {i: {} for i in range(1, 5)}})
    assert requests == [0]
    assert len(result.alternatives) == 1
    assert result.provenance["bootstrap_used_worlds"] == [0]


@pytest.mark.parametrize("options", [{"alternative_count": -1}, {"alternative_count": 6},
                                     {"alternative_count": True}, {"alternative_count": 1.5},
                                     {"minimum_player_changes": 0},
                                     {"minimum_player_changes": True},
                                     {"alternative_count": 1, "minimum_player_changes": 3}])
def test_invalid_search_policy_rejected(options):
    with pytest.raises(ValueError):
        solve_xi(roster(), [], shape(), **options)
