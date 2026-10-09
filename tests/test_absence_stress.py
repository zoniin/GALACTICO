"""Absence stress against an enumeration that shares nothing with it.

The oracle is typed from the problem statement: every removal set, every permutation of the
remaining players over the slots, eligibility and missing values checked inline, shortfall
integers by exact ``Fraction`` half-even. It imports the domain dataclasses only. The fault
injection (a solver that reports a chosen status) is the shipped device of the kernel tests
and is not part of the oracle.
"""

from __future__ import annotations

import itertools
import json
import random
import time
from dataclasses import asdict, replace
from fractions import Fraction

import pytest
from ortools.sat.python import cp_model

import galactico.optimization.squad.kernel as engine
import galactico.optimization.squad.stress as stress_module
from galactico.optimization.squad.stress import absence_stress
from galactico.optimization.xi.domain import Candidate, Formation, Slot, TacticalRequirement

# ---------------------------------------------------------------------------- oracle


def exact(value, normalizer, scale):
    return round(Fraction(value) / Fraction(normalizer) * scale)


def live(requirements):
    return [r for r in requirements if r.status == "active" and r.evidence_class != "UNAVAILABLE"]


def touches(requirement, slot):
    return not requirement.slot_ids or slot.slot_id in requirement.slot_ids


def fits(player, slot, requirements):
    return (
        player.minutes > 0
        and player.position in slot.allowed_positions
        and (player.eligible_slots is None or slot.slot_id in player.eligible_slots)
        and all(player.values.get(r.metric) is not None for r in requirements if touches(r, slot))
    )


def shortfall(xi, slots, requirements, scale):
    short = [
        max(0, exact(r.minimum, r.normalizer, scale) - sum(
            exact(p.values[r.metric], r.normalizer, scale)
            for p, s in zip(xi, slots, strict=True) if touches(r, s)))
        for r in requirements
    ]
    return (max(short, default=0), sum(short))


def brute(players, requirements, formation, scale, gone=(), locked=()):
    """Least (maximum, total) over every XI without ``gone`` that fields ``locked``, or None."""
    requirements = live(requirements)
    pool = [p for p in players if p.player_id not in gone]
    best = None
    for xi in itertools.permutations(pool, len(formation.slots)):
        if not set(locked) <= {p.player_id for p in xi}:
            continue
        if not all(fits(p, s, requirements) for p, s in zip(xi, formation.slots, strict=True)):
            continue
        value = shortfall(xi, formation.slots, requirements, scale)
        best = value if best is None or value < best else best
    return best


def slot_walk(players, requirements, formation, scale, gone=(), locked=()):
    """The same minimum by walking the slots; used where permutations are too many."""
    requirements = live(requirements)
    slots = formation.slots
    targets = [exact(r.minimum, r.normalizer, scale) for r in requirements]
    options = [
        [
            (p.player_id, [
                exact(p.values[r.metric], r.normalizer, scale) if touches(r, slot) else 0
                for r in requirements])
            for p in players
            if p.player_id not in gone and fits(p, slot, requirements)
        ]
        for slot in slots
    ]
    best = None
    needed = set(locked)
    used: set[int] = set()

    def walk(index, sums):
        nonlocal best
        if index == len(slots):
            if needed <= used:
                short = [max(0, t - s) for t, s in zip(targets, sums, strict=True)]
                value = (max(short, default=0), sum(short))
                best = value if best is None or value < best else best
            return
        for pid, row in options[index]:
            if pid not in used:
                used.add(pid)
                walk(index + 1, [a + b for a, b in zip(sums, row, strict=True)])
                used.remove(pid)

    walk(0, [0] * len(requirements))
    return best


def truth_table(players, requirements, formation, scale, removable, k, *, excluded=(),
                locked=(), solve=brute):
    return {
        absent: solve(players, requirements, formation, scale,
                      gone=(*excluded, *absent), locked=locked)
        for size in range(1, k + 1)
        for absent in itertools.combinations(sorted(removable), size)
    }


def cores_of(table, size):
    """Second pass: sets with no value whose every subset one smaller has one."""
    found = set()
    for absent, value in table.items():
        if len(absent) != size or value is not None:
            continue
        if size == 1 or all(
            table[smaller] is not None for smaller in itertools.combinations(absent, size - 1)
        ):
            found.add(absent)
    return found


def far():
    return 600.0


def check_against(result, table, players, requirements, formation, baseline, *, excluded=()):
    """A1-A3 and the counts, for a run that finished."""
    assert result.certificate.completeness == "EXACT"
    assert [row.player_ids for row in result.table] == list(table)  # (size, ids) order
    for row in result.table:
        value = table[row.player_ids]
        assert row.integer_vector == value, row
        assert row.status == ("UNFIELDABLE" if value is None else "SHORTFALL_CERTIFIED")
        assert (row.resolution, row.inherited_from is None) in {
            ("SOLVED", True), ("INHERITED_VALUE", False), ("INHERITED_UNFIELDABLE", False)}
    requirements = live(requirements)
    for level in result.levels:
        sized = {a: v for a, v in table.items() if len(a) == level.k}
        fielded = [v for v in sized.values() if v is not None]
        assert level.set_count == len(sized) and level.unknown_count == 0
        assert level.certified_count == len(fielded)
        assert level.unfieldable_count == len(sized) - len(fielded)
        assert level.positive_change_count == sum(v > baseline for v in fielded)
        worst = max(fielded, default=None)
        assert level.worst_integer == worst == level.certified_lower_bound_integer
        assert {frozenset(s) for s in level.worst_sets} == {
            frozenset(a) for a, v in sized.items() if worst is not None and v == worst}
        assert list(level.worst_sets) == sorted(level.worst_sets)
        assert {c.player_ids for c in level.minimal_unfieldable} == cores_of(table, level.k)
        for core in level.minimal_unfieldable:
            # The stated reason is checked by counting, with the oracle's own eligibility.
            group = [s for s in formation.slots if s.slot_id in core.blocking_slot_ids]
            remaining = {
                p.player_id for p in players for s in group
                if fits(p, s, requirements) and p.player_id not in {*excluded, *core.player_ids}}
            assert core.cause == "SLOT_COVER" and len(group) == len(core.blocking_slot_ids)
            assert set(core.remaining_ids) == remaining and len(remaining) < len(group)


# ------------------------------------------------------------------------- generator

SLOTS = tuple(Slot(f"s{i}", f"Slot {i}", ("X",), 0.5, 0.5) for i in range(3))
SHAPE = Formation("three", SLOTS)


def near_half(value, normalizer, scale):
    part = Fraction(value) / Fraction(normalizer) * scale % 1
    return abs(part - Fraction(1, 2)) < Fraction(1, 10**9)


def instance(rng, number):
    while True:
        scale = rng.choice((3, 8, 100_000))
        twin = number % 2 == 0  # s0 and s1 admit the same players
        players = []
        for pid in range(1, rng.choice((6, 7)) + 1):
            keep = [rng.random() >= 0.25 for _ in SLOTS]
            if twin:
                keep[1] = keep[0]
            values = {"m": round(rng.uniform(0.0, 2.0), 3), "n": round(rng.uniform(0.0, 2.0), 3)}
            if rng.random() < 0.15:
                values[rng.choice(("m", "n"))] = None
            players.append(Candidate(pid, f"Name {pid}", "X", values, minutes=90,
                                     eligible_slots=tuple(
                                         s.slot_id for s, kept in zip(SLOTS, keep, strict=True)
                                         if kept)))
        requirements = [
            TacticalRequirement("need_m", "M", "m", round(rng.uniform(1.0, 5.0), 3),
                                round(rng.uniform(1.0, 4.0), 3)),
            TacticalRequirement("need_n", "N", "n", round(rng.uniform(0.5, 4.0), 3),
                                round(rng.uniform(1.0, 4.0), 3),
                                slot_ids=("s0", "s1") if twin else ("s0", "s2")),
        ]
        numbers = [(r.minimum, r.normalizer) for r in requirements]
        numbers += [(p.values[r.metric], r.normalizer) for p in players for r in requirements
                    if p.values[r.metric] is not None]
        if not any(near_half(v, n, scale) for v, n in numbers):
            return players, requirements, scale


def test_stress_equals_the_enumeration_on_seeded_instances():
    rng = random.Random(20261012)
    seen = {key: 0 for key in (
        "certified_pairs", "unfieldable_pairs", "tied_worst", "inherited_value",
        "inherited_unfieldable", "worst_above", "worst_equal", "cores", "locked_cores", "k3")}
    for number in range(40):
        players, requirements, scale = instance(rng, number)
        ids = [p.player_id for p in players]
        base = brute(players, requirements, SHAPE, scale)
        locked = ()
        if number % 4 == 0 and base is not None:
            # A lock the squad can honour: someone who is in at least one XI.
            fielded = [pid for pid in ids
                       if brute(players, requirements, SHAPE, scale, locked=(pid,)) is not None]
            locked = (rng.choice(fielded),)
            base = brute(players, requirements, SHAPE, scale, locked=locked)
        k = 3 if number % 4 == 1 else 2
        removable = [pid for pid in ids if pid not in locked]
        result = absence_stress(players, requirements, SHAPE, k=k, allow_k3=k == 3,
                                locked=locked, quantization=scale, time_limit=far())
        if base is None:
            assert result.certificate.baseline_status == "UNFIELDABLE" and result.levels == ()
            assert result.table == () and result.single_absences == ()
            continue
        table = truth_table(players, requirements, SHAPE, scale, removable, k, locked=locked)
        assert result.certificate.baseline_integer == base
        assert result.certificate.removable_ids == tuple(removable)
        check_against(result, table, players, requirements, SHAPE, base)
        assert [row.player_ids for row in result.single_absences] == [(p,) for p in removable]
        # A4: an inherited answer is the answer of a direct solve.
        direct = absence_stress(players, requirements, SHAPE, k=k, allow_k3=k == 3,
                                locked=locked, quantization=scale, time_limit=far(),
                                _inherit=False)
        assert {row.resolution for row in direct.table} == {"SOLVED"}
        assert [(r.player_ids, r.status, r.integer_vector) for r in direct.table] == [
            (r.player_ids, r.status, r.integer_vector) for r in result.table]
        # A6: the order of the inputs is not an input.
        shuffled = absence_stress(rng.sample(players, len(players)), requirements[::-1], SHAPE,
                                  k=k, allow_k3=k == 3, locked=locked, quantization=scale,
                                  time_limit=far())
        assert shuffled.table == result.table and shuffled.levels == result.levels
        assert shuffled.provenance["input_fingerprint"] == result.provenance["input_fingerprint"]

        pairs = result.levels[1]
        seen["certified_pairs"] += pairs.certified_count > 0
        seen["unfieldable_pairs"] += pairs.unfieldable_count > 0
        seen["tied_worst"] += any(len(level.worst_sets) > 1 and level.worst_integer > base
                                  for level in result.levels)
        seen["inherited_value"] += result.certificate.sets_inherited_value > 0
        seen["inherited_unfieldable"] += result.certificate.sets_inherited_unfieldable > 0
        seen["worst_above"] += any(level.worst_integer is not None and level.worst_integer > base
                                   for level in result.levels)
        seen["worst_equal"] += any(level.worst_integer == base for level in result.levels)
        cores = sum(len(level.minimal_unfieldable) for level in result.levels)
        seen["cores"] += cores > 0
        seen["locked_cores"] += bool(locked) and cores > 0
        seen["k3"] += k == 3
        # The second oracle, used on the real squad, agrees with the first on every set here.
        assert all(slot_walk(players, requirements, SHAPE, scale, gone=absent, locked=locked)
                   == value for absent, value in table.items())
    # Non-vacuity: the interesting outcome and its opposite both occurred.
    assert all(seen.values()), seen


# ------------------------------------------------------------------ hand-built cases


def squad(rows):
    return [Candidate(pid, f"P{pid}", "X", {"m": value}, minutes=90, eligible_slots=slots)
            for pid, slots, value in rows]


TWO = Formation("two", SLOTS[:2])
NEED = [TacticalRequirement("need_m", "M", "m", 10.0, 10.0)]


def test_two_disjoint_pairs_tie_for_the_worst_and_both_are_returned():
    players = squad([(1, ("s0",), 5.0), (2, ("s0",), 5.0), (6, ("s0",), 1.0),
                     (3, ("s1",), 5.0), (4, ("s1",), 5.0), (5, ("s1",), 1.0)])
    result = absence_stress(players, NEED, TWO, k=3, allow_k3=True, quantization=100)
    table = truth_table(players, NEED, TWO, 100, range(1, 7), 3)
    check_against(result, table, players, NEED, TWO, (0, 0))
    singles, pairs, triples = result.levels
    assert singles.worst_integer == (0, 0) and len(singles.worst_sets) == 6
    assert singles.positive_change_count == 0 and "No set among the 6 sets" in singles.claim
    # A whole number is printed as one, the way the injection sentences print a pair.
    assert "raises the least declared shortfall above (maximum 0, total 0); 0 sets" in (
        singles.claim)
    assert "rises from (maximum 0, total 0) to (maximum 0.4, total 0.4)." in pairs.claim
    assert pairs.worst_integer == (40, 40) and pairs.worst_sets == ((1, 2), (3, 4))
    assert pairs.worst_objective == (0.4, 0.4) and pairs.unfieldable_count == 0
    assert "any one of these 2 sets" in pairs.claim and "P1 and P2; P3 and P4" in pairs.claim
    assert [(c.player_ids, c.blocking_slot_ids, c.remaining_ids)
            for c in triples.minimal_unfieldable] == [
        ((1, 2, 6), ("s0",), ()), ((3, 4, 5), ("s1",), ())]
    row = {r.player_ids: r for r in result.table}
    assert row[(1, 2)].change_from_baseline == (0.4, 0.4)
    assert result.claim == triples.claim and result.completeness_statement.startswith(
        "Every inclusion-minimal set of at most 3 players")
    # Said once, in the fuller wording, and only when such a set exists.
    said = [text for text in (result.non_claim, *result.warnings, result.completeness_statement)
            if "no fieldable XI reflect the evidence gate" in text]
    assert said == [
        "Sets that leave no fieldable XI reflect the evidence gate and the eligibility rules, "
        "not the real squad; the omitted players are listed beside this result."]
    assert said[0] in result.warnings
    assert result.non_claim.endswith("everything this model does not measure.")


def test_levels_are_separate_when_every_larger_set_leaves_no_xi():
    # One player covers both slots; without him the two specialists are both needed. So a
    # single absence has a positive value and no pair leaves an XI: "exactly one" is not
    # bounded by "exactly two". k equals the number of removable players.
    players = squad([(1, ("s0", "s1"), 9.0), (2, ("s0",), 2.0), (3, ("s1",), 3.0)])
    result = absence_stress(players, NEED, TWO, k=3, allow_k3=True, quantization=100)
    table = truth_table(players, NEED, TWO, 100, (1, 2, 3), 3)
    check_against(result, table, players, NEED, TWO, (0, 0))
    singles, pairs, triples = result.levels
    assert singles.worst_integer == (50, 50) and singles.worst_sets == ((1,),)
    assert singles.claim.startswith("If P1 is unavailable, the least declared shortfall")
    assert pairs.worst_integer is None and pairs.worst_sets == () and pairs.certified_count == 0
    assert pairs.certified_lower_bound is None and pairs.completeness == "EXACT"
    assert {c.player_ids for c in pairs.minimal_unfieldable} == {(1, 2), (1, 3), (2, 3)}
    assert pairs.claim.startswith("All 3 sets of 2 players leave no fieldable XI")
    assert triples.unfieldable_count == 1 and triples.minimal_unfieldable == ()
    assert triples.claim.startswith("The 1 set of 3 players leaves no fieldable XI in this model.")
    last = result.table[-1]
    assert (last.player_ids, last.resolution, last.inherited_from) == (
        (1, 2, 3), "INHERITED_UNFIELDABLE", (2, 3))
    assert result.certificate.sets_inherited_unfieldable == 1


def test_a_locked_player_is_not_removable_and_locks_never_explain_a_core():
    players = squad([(1, ("s0",), 1.0), (2, ("s0", "s1"), 9.0), (3, ("s1",), 5.0),
                     (4, ("s1",), 4.0)])
    result = absence_stress(players, NEED, TWO, k=3, allow_k3=True, locked=(1,), quantization=100)
    assert result.certificate.removable_ids == (2, 3, 4) and result.locked == (1,)
    assert result.certificate.lock_policy == "LOCKS_NOT_REMOVABLE"
    table = truth_table(players, NEED, TWO, 100, (2, 3, 4), 3, locked=(1,))
    # The lock binds: the squad's least shortfall is that of P1 with P2, not of P2 with P3.
    assert result.certificate.baseline_integer == (0, 0) == brute(players, NEED, TWO, 100,
                                                                    locked=(1,))
    check_against(result, table, players, NEED, TWO, (0, 0))
    assert table[(2,)] == (40, 40) and brute(players, NEED, TWO, 100, gone=(2,)) == (40, 40)
    assert [c.player_ids for c in result.levels[2].minimal_unfieldable] == [(2, 3, 4)]
    for refused in (dict(removable=(1, 2)), dict(lock_policy="RELEASE_LOCK"),
                    dict(removable=(2, 2)), dict(locked=(9,)), dict(excluded=("3",))):
        with pytest.raises(ValueError):
            absence_stress(players, NEED, TWO, **{"locked": (1,), "quantization": 100,
                                                  **refused})
    narrowed = absence_stress(players, NEED, TWO, k=2, locked=(1,), removable=(4, 3),
                              excluded=(2,), quantization=100)
    assert narrowed.certificate.removable_ids == (3, 4) and narrowed.excluded == (2,)
    check_against(narrowed, truth_table(players, NEED, TWO, 100, (3, 4), 2, excluded=(2,),
                                        locked=(1,)),
                  players, NEED, TWO, brute(players, NEED, TWO, 100, gone=(2,), locked=(1,)),
                  excluded=(2,))


def test_a_squad_with_no_xi_is_reported_before_any_absence_and_inputs_are_validated():
    players = squad([(1, ("s0",), 5.0), (2, ("s0",), 5.0), (3, ("s1",), 5.0)])
    both = absence_stress(players, NEED, TWO, k=1, locked=(3,), excluded=(3,), quantization=100)
    empty = absence_stress(players, NEED, TWO, k=1, excluded=(3,), quantization=100)
    for result in (both, empty):
        assert result.certificate.baseline_status == "UNFIELDABLE"
        assert result.levels == () and result.table == () and result.baseline_objective is None
        assert result.completeness_statement is None
        assert "no fieldable XI in this model before any absence" in result.warnings[0]
        assert result.claim == "No XI can be fielded in this model before any absence."
    hard = [replace(NEED[0], hard=True)]
    many = squad([(pid, ("s0", "s1"), 1.0) for pid in range(1, 41)])
    for arguments, message in (
        ((players, NEED, TWO, dict(k=0)), "k must be 1, 2 or 3"),
        ((players, NEED, TWO, dict(k=True)), "k must be 1, 2 or 3"),
        ((players, NEED, TWO, dict(k=3)), "k = 3 must be requested explicitly"),
        ((players, NEED, TWO, dict(k=2, excluded=(1, 2))), "k exceeds"),
        ((players, hard, TWO, dict(k=1)), "soft"),
        ((many, NEED, TWO, dict(k=3, allow_k3=True)), "too many absence sets"),
        ((players, NEED, TWO, dict(k=1, time_limit=0)), "time_limit"),
        ((players, NEED, "5-5-5", dict(k=1)), "unknown formation"),
    ):
        with pytest.raises(ValueError, match=message):
            absence_stress(*arguments[:3], **arguments[3])


def test_a_narrowed_enumeration_does_not_claim_the_sets_it_never_formed():
    # P1 and P2 are the only players of s0, so their pair leaves no XI. A caller who narrows
    # the removable players (or locks one of the two) never forms that pair: "every minimal
    # set is listed" would then be a claim about sets nobody enumerated.
    players = squad([(1, ("s0",), 5.0), (2, ("s0",), 5.0), (3, ("s1",), 5.0),
                     (4, ("s1",), 5.0), (5, ("s1",), 5.0)])
    full = absence_stress(players, NEED, TWO, k=2, quantization=100)
    assert [c.player_ids for c in full.levels[1].minimal_unfieldable] == [(1, 2)]
    assert full.completeness_statement == (
        "Every inclusion-minimal set of at most 2 players whose absence leaves no fieldable XI "
        "is listed. Larger ones were not searched.")
    assert "removable" not in full.claim
    # The sentence agrees in number with k and with the removable count.
    assert absence_stress(players, NEED, TWO, k=1, quantization=100).completeness_statement == (
        "Every inclusion-minimal set of at most 1 player whose absence leaves no fieldable XI "
        "is listed. Larger ones were not searched.")
    assert absence_stress(
        players, NEED, TWO, k=1, quantization=100, removable=(3,)
    ).completeness_statement == (
        "Every inclusion-minimal set of at most 1 of the 1 removable player whose absence "
        "leaves no fieldable XI is listed. Sets with any other player, and larger sets, were "
        "not searched.")
    for narrowing in (dict(removable=(3, 4)), dict(locked=(1,))):
        result = absence_stress(players, NEED, TWO, k=2, quantization=100, **narrowing)
        count = len(result.certificate.removable_ids)
        assert count < 5 and result.certificate.completeness == "EXACT"
        assert not any(level.minimal_unfieldable for level in result.levels)
        assert result.completeness_statement == (
            f"Every inclusion-minimal set of at most 2 of the {count} removable players whose "
            "absence leaves no fieldable XI is listed. Sets with any other player, and larger "
            "sets, were not searched.")
        assert all(f"drawn from the {count} removable players" in level.claim
                   for level in result.levels)


# --------------------------------------------------------- undecided is never a proof


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


def undecided_instance():
    rng = random.Random(7)
    for number in itertools.count():
        players, requirements, scale = instance(rng, number)
        ids = [p.player_id for p in players]
        table = truth_table(players, requirements, SHAPE, scale, ids, 2)
        base = brute(players, requirements, SHAPE, scale)
        values = [v for v in table.values() if v is not None]
        if base is not None and None in table.values() and values and max(values) > base:
            return players, requirements, scale, table, base


@pytest.mark.parametrize("forced", [cp_model.UNKNOWN, cp_model.MODEL_INVALID])
def test_a_forced_undecided_solve_withholds_the_worst_case_and_proves_nothing(monkeypatch, forced):
    players, requirements, scale, table, base = undecided_instance()
    full = absence_stress(players, requirements, SHAPE, k=2, quantization=scale)
    assert full.certificate.completeness == "EXACT"
    total_calls = full.certificate.solves
    hit_levels = set()
    for on_call in range(1, total_calls + 1):
        with monkeypatch.context() as patch:
            override_status(patch, on_call, forced)
            result = absence_stress(players, requirements, SHAPE, k=2, quantization=scale)
        expected = "MODEL_INVALID" if forced == cp_model.MODEL_INVALID else "DEADLINE"
        assert result.certificate.completeness == expected, on_call
        assert result.completeness_statement is None
        if result.certificate.baseline_status != "CERTIFIED":
            assert result.levels == () and result.certificate.baseline_integer is None
            assert result.warnings and result.claim.startswith("Nothing is claimed")
            continue
        unknown = [row for row in result.table if row.status == "UNKNOWN"]
        assert [row.resolution for row in unknown] == ["UNDECIDED"], on_call
        for row in result.table:
            if row.status != "UNKNOWN":
                # Whatever was reported as decided is true, the unfieldable sets included.
                assert row.integer_vector == table[row.player_ids], (on_call, row)
                assert (row.status == "UNFIELDABLE") == (table[row.player_ids] is None)
        for level in result.levels:
            if level.unknown_count:
                hit_levels.add(level.k)
                assert level.completeness == "DEADLINE"
                assert level.worst_integer is None and level.worst_sets == ()
                assert level.worst_objective is None and "no worst case is stated" in level.claim
                assert level.unknown_count == 1 and level.claim.startswith("1 of the ")
                assert " was not resolved, so no worst case is stated." in level.claim
                truly_worst = max(v for a, v in table.items()
                                  if len(a) == level.k and v is not None)
                # A8: what was certified bounds the true worst case from below.
                assert (level.certified_lower_bound_integer is None
                        or level.certified_lower_bound_integer <= truly_worst)
                # A core is listed only when every subset is proven to leave an XI.
                assert {c.player_ids for c in level.minimal_unfieldable} <= cores_of(
                    table, level.k)
            else:
                assert level.completeness == "EXACT"
        assert any(w.startswith("1 absence set was not resolved within 60 s.")
                   for w in result.warnings)
    assert hit_levels == {1, 2}


def test_a_passed_deadline_leaves_sets_not_reached_and_a_valid_lower_bound(monkeypatch):
    players, requirements, scale, table, base = undecided_instance()
    reached = set()
    for ticks in (1, 4, 9, 14, 20, 30):
        with monkeypatch.context() as patch:
            clock = itertools.count()
            patch.setattr(stress_module.time, "monotonic",
                          lambda clock=clock, ticks=ticks: 0.0 if next(clock) < ticks else 1e9)
            result = absence_stress(players, requirements, SHAPE, k=2, quantization=scale,
                                    time_limit=5.0)
        if result.certificate.baseline_status != "CERTIFIED":
            assert result.certificate.baseline_status == "UNKNOWN" and result.levels == ()
            assert result.certificate.completeness == "DEADLINE"
            assert result.claim.startswith("Nothing is claimed")
            reached.add("no baseline")
            continue
        late = [row for row in result.table if row.status == "UNKNOWN"]
        assert late and {row.resolution for row in late} <= {"NOT_REACHED", "UNDECIDED"}
        reached.add("partial")
        assert result.certificate.completeness == "DEADLINE"
        for row in result.table:
            if row.status != "UNKNOWN":
                assert row.integer_vector == table[row.player_ids]
                assert (row.status == "UNFIELDABLE") == (table[row.player_ids] is None)
        for level in result.levels:
            if level.unknown_count:
                assert level.worst_sets == () and level.worst_integer is None
                bound = level.certified_lower_bound_integer
                assert bound is None or bound <= max(
                    v for a, v in table.items() if len(a) == level.k and v is not None)
        unresolved = "1 absence set was" if len(late) == 1 else f"{len(late)} absence sets were"
        assert any(w.startswith(f"{unresolved} not resolved within 5 s") for w in result.warnings)
    assert reached == {"no baseline", "partial"}


# -------------------------------------------------------- shipped code, guard, hashes


def test_single_absences_equal_the_shipped_removal_sensitivity():
    from galactico.optimization.xi.solver import removal_sensitivity, solve_xi

    rng = random.Random(20261012)
    compared = unfieldable = 0
    for number in range(8):
        players, requirements, scale = instance(rng, number)
        base = solve_xi(players, requirements, SHAPE, quantization=scale, analyze_ties=False)
        if base.solution_status != "OPTIMAL":
            continue
        ids = [p.player_id for p in players]
        shipped = removal_sensitivity(base, players, requirements, player_ids=ids)
        result = absence_stress(players, requirements, SHAPE, k=1, quantization=scale)
        for row in result.single_absences:
            (pid,) = row.player_ids
            if shipped[pid]["solution_status"] == "INFEASIBLE":
                assert row.status == "UNFIELDABLE"
                unfieldable += 1
            else:
                assert shipped[pid]["solution_status"] == "OPTIMAL"
                assert row.integer_vector == tuple(
                    round(v * scale) for v in shipped[pid]["objective_vector"])
                compared += 1
    assert compared >= 20 and unfieldable >= 1


def test_result_carries_no_merit_key_no_world_and_a_fingerprint_of_every_decision_input(
        thesis_guard):
    players = squad([(1, ("s0",), 5.0), (2, ("s0",), 5.0), (6, ("s0",), 1.0),
                     (3, ("s1",), 5.0), (4, ("s1",), 5.0), (5, ("s1",), 1.0)])
    lineage = {"dataset_hash": "synthetic", "solver_stages": ["old"], "stress_version": "old",
               "bootstrap_worlds": 4, "bootstrap_version": "b1", "objective_vector": [1, 2]}
    omitted = [{"player_id": 9, "name": "Below", "minutes": 10,
                "reason": "below 900 prior minutes"}]

    def run(**changes):
        arguments = dict(k=2, quantization=100, provenance=lineage, omitted=omitted)
        arguments.update(changes)
        return absence_stress(arguments.pop("players", players),
                              arguments.pop("requirements", NEED), TWO, **arguments)

    result = run()
    payload = asdict(result)
    thesis_guard(payload)
    text = json.dumps(payload)
    assert "likelihood" in result.non_claim and "probab" not in text.lower()
    assert not any("world" in key for key in payload if key != "provenance")
    assert not any("world" in key for row in (payload["levels"][0], payload["certificate"],
                                             payload["table"][0], payload["evidence"])
                   for key in row)
    assert result.omitted == tuple(omitted)
    provenance = result.provenance
    assert provenance["stress_version"] == "exhaustive-k-absence-stress-v1"
    assert provenance["dataset_hash"] == "synthetic" and provenance["bootstrap_version"] == "b1"
    assert not {"solver_stages", "bootstrap_worlds", "objective_vector"} & set(provenance)
    assert provenance["absence_policy"] == "Declared scenario; no absence likelihood is estimated"
    assert result.evidence["composed"] == "HEURISTIC"
    assert result.evidence["binding"] == ["need_m", "eligibility"]
    assert {row["name"] for row in result.evidence["declared_inputs"]} >= {
        "k", "locked", "excluded", "removable"}
    experimental = run(requirements=[replace(NEED[0], evidence_class="RESEARCH")])
    assert experimental.evidence["composed"] == "EXPERIMENTAL"
    assert experimental.evidence["binding"] == ["need_m"]
    hashes = {run(**change).provenance["input_fingerprint"] for change in (
        dict(k=1), dict(excluded=(6,)), dict(locked=(6,)), dict(removable=(1, 2, 3)),
        dict(time_limit=30.0), dict(include_table=False), dict(quantization=1000),
        dict(seed=5), dict(requirements=[replace(NEED[0], minimum=9.0)]),
        dict(provenance={"dataset_hash": "other"}),
        dict(players=[replace(players[0], values={"m": 4.0}), *players[1:]]))}
    assert len(hashes) == 11 and provenance["input_fingerprint"] not in hashes
    assert run(players=players[::-1]).provenance["input_fingerprint"] == provenance[
        "input_fingerprint"]
    assert run(include_table=False).table == () and len(
        run(include_table=False).single_absences) == 6
    # Level one is listed by player_id, which no number in the rows follows.
    assert [row.player_ids[0] for row in result.single_absences] == [1, 2, 3, 4, 5, 6]


# -------------------------------------------------------------------- real scenario

MADRID = 675
MATCH = 2565907
# Spec section 10.3, measured there by a slot enumeration; integers in units of 1e-5.
PINNED = {
    "4-3-3": {
        "levels": [(16, 0, 2, (12709, 19483), [(3310,)]),
                   (120, 17, 30, (32389, 32389), [(4498, 4501)]),
                   (560, 212, 157, (45235, 45235), [(4498, 4501, 8287)])],
        "singles": {3310: (12709, 19483), 4501: (9300, 9300)},
        "pair_cores": {
            (3304, 3306), (3304, 3309), (3304, 3310), (3304, 4501), (3306, 3309), (3306, 3310),
            (3306, 4501), (3309, 3310), (3309, 4501), (3310, 4501), (3563, 8287), (3563, 14723),
            (3563, 40756), (3785, 3915), (8287, 14723), (8287, 40756), (14723, 40756)},
        "triple_cores": {(3321, 3322, 8278), (4498, 8278, 288091)},
    },
    "4-3-1-2": {
        "levels": [(16, 0, 5, (32389, 32389), [(4501,)]),
                   (120, 24, 52, (45235, 45235), [(4501, 8287)]),
                   (560, 294, 186, (51071, 52821), [(4501, 8278, 8287)])],
        "singles": {3309: (331, 331), 3310: (12709, 19483), 3563: (2176, 2176),
                    4501: (32389, 32389), 8287: (918, 918)},
        "pair_cores": 24,
        "triple_cores": set(),
    },
}


@pytest.fixture(scope="module")
def madrid_snapshots(corpus_root):
    from galactico.optimization.snapshots import load_team_snapshot

    return {
        "match": load_team_snapshot(competition="Spain", team_id=MADRID, match_id=MATCH,
                                    worlds=0),
        "planning": load_team_snapshot(competition="Spain", team_id=MADRID,
                                       cutoff="2018-05-21", worlds=0),
    }


@pytest.mark.slow
@pytest.mark.parametrize("formation", ["4-3-3", "4-3-1-2"])
def test_madrid_default_scenario_reproduces_the_pinned_tables(madrid_snapshots, formation):
    from galactico.optimization.snapshots import snapshot_inputs

    snapshot = madrid_snapshots["match"]
    # The pinned tables were measured with the shipped three requirements in force.
    players, requirements = snapshot_inputs(snapshot, formation, experimental_opt_in=True)
    started = time.perf_counter()
    result = absence_stress(players, requirements, formation, k=3, allow_k3=True,
                            omitted=snapshot.omitted, provenance=snapshot.provenance)
    assert time.perf_counter() - started < 60
    pinned = PINNED[formation]
    assert result.certificate.completeness == "EXACT" and result.baseline_objective == (0.0, 0.0)
    assert len(result.certificate.removable_ids) == 16 and len(result.omitted) == 7
    assert [(lv.set_count, lv.unfieldable_count, lv.positive_change_count, lv.worst_integer,
             list(lv.worst_sets)) for lv in result.levels] == pinned["levels"]
    assert {row.player_ids[0]: row.integer_vector for row in result.single_absences
            if row.integer_vector != (0, 0)} == pinned["singles"]
    pair_cores = {c.player_ids for c in result.levels[1].minimal_unfieldable}
    if isinstance(pinned["pair_cores"], int):
        assert len(pair_cores) == pinned["pair_cores"]
    else:
        assert pair_cores == pinned["pair_cores"]
    # Every unfieldable pair is its own core: no single absence leaves no XI.
    assert len(pair_cores) == result.levels[1].unfieldable_count
    assert {c.player_ids for c in result.levels[2].minimal_unfieldable} == pinned["triple_cores"]
    assert result.certificate.sets_inherited_unfieldable >= 210
    assert result.evidence["composed"] == "EXPERIMENTAL"
    assert result.provenance["providers"] == ["pappalardo"]


@pytest.mark.slow
@pytest.mark.parametrize("which,sets,unfieldable,positive", [
    ("match", (16, 120), (0, 17), (0, 1)),
    ("planning", (19, 171), (0, 6), (0, 0)),
])
def test_madrid_planning_scope_equals_a_slot_enumeration(madrid_snapshots, which, sets,
                                                         unfieldable, positive):
    from galactico.optimization.snapshots import snapshot_inputs
    from galactico.optimization.xi.domain import FORMATIONS

    snapshot = madrid_snapshots[which]
    # The planning default: progression only (ROOT 2.6 D4).
    players, requirements = snapshot_inputs(snapshot, "4-3-3")
    assert [r.requirement_id for r in requirements if r.active] == ["progression"]
    result = absence_stress(players, requirements, "4-3-3", k=2, omitted=snapshot.omitted,
                            provenance=snapshot.provenance)
    shape = FORMATIONS["4-3-3"]
    ids = [p.player_id for p in players]
    base = slot_walk(players, requirements, shape, 100_000)
    assert result.certificate.baseline_integer == base == (0, 0)
    table = truth_table(players, requirements, shape, 100_000, ids, 2, solve=slot_walk)
    check_against(result, table, players, requirements, shape, base)
    assert tuple(lv.set_count for lv in result.levels) == sets
    assert tuple(lv.unfieldable_count for lv in result.levels) == unfieldable
    assert tuple(lv.positive_change_count for lv in result.levels) == positive
    assert result.evidence["composed"] == "HEURISTIC"
    if which == "match":
        assert result.levels[1].worst_integer == (1277, 1277)
        assert result.levels[1].worst_sets == ((3310, 3563),)
