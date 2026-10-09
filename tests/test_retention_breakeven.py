"""The break-even carry-over fraction against a 21-step enumeration typed from the definition.

For every grid step the oracle scales the candidate with ``Fraction``, enumerates
``itertools.permutations`` of the squad plus the scaled candidate, forms the baseline and forced
optima as integer pairs by exact half-even (and ``Fraction`` floor/ceil feasibility for the hard
conclusion), and evaluates the predicate as the table states it. It imports only the domain
dataclasses: nothing from the retention module, the injection module or the kernel.
"""

from __future__ import annotations

import inspect
import itertools
import math
import random
import re
from dataclasses import asdict, replace
from fractions import Fraction

import pytest
from ortools.sat.python import cp_model

from galactico.optimization.snapshots import SnapshotMetric
from galactico.optimization.squad import kernel as engine
from galactico.optimization.transfers import retention
from galactico.optimization.transfers.injection import inject_candidates
from galactico.optimization.transfers.retention import (
    CONCLUSIONS,
    DEFAULT_CONCLUSION,
    MONOTONE_CONCLUSIONS,
    break_even_retention,
    scaled_candidate,
)
from galactico.optimization.xi.domain import Candidate, Formation, Slot, TacticalRequirement

# --------------------------------------------------------------------------- oracle


def applies(requirement, slot_id):
    return not requirement.slot_ids or slot_id in requirement.slot_ids


def enumerate_xis(players, requirements, formation, scale, excluded=()):
    """Every admissible XI as (player ids, half-even shortfalls, whether the exact floors hold)."""
    active = sorted(
        (r for r in requirements if r.status == "active" and r.evidence_class != "UNAVAILABLE"),
        key=lambda r: r.requirement_id,
    )
    usable = [p for p in players if p.player_id not in excluded and p.minutes > 0]
    rows = []
    for combo in itertools.permutations(usable, len(formation.slots)):
        seats = list(zip(combo, formation.slots, strict=True))
        if not all(
            p.position in slot.allowed_positions
            and (p.eligible_slots is None or slot.slot_id in p.eligible_slots)
            and all(p.values.get(r.metric) is not None for r in active if applies(r, slot.slot_id))
            for p, slot in seats
        ):
            continue
        shortfalls, floors = [], True
        for r in active:
            parts = [
                Fraction(p.values[r.metric]) / Fraction(r.normalizer) * scale
                for p, slot in seats
                if applies(r, slot.slot_id)
            ]
            target = Fraction(r.minimum) / Fraction(r.normalizer) * scale
            shortfalls.append(max(0, round(target) - sum(round(part) for part in parts)))
            floors &= sum(math.floor(part) for part in parts) >= math.ceil(target)
        rows.append(({p.player_id for p in combo}, tuple(shortfalls), floors))
    return rows


def least(rows):
    return min(((max(s, default=0), sum(s)) for _, s, _ in rows), default=None)


def above(pair):
    """No XI compares above every pair."""
    return (1,) if pair is None else (0, *pair)


def scaled_by(candidate, step, scaled):
    return replace(candidate, values={
        metric: value if value is None or metric not in scaled
        else float(Fraction(value) * Fraction(step, 20))
        for metric, value in candidate.values.items()
    })


def grid(candidate, squad, requirements, formation, scale, scaled, excluded=()):
    """({conclusion: holds at each of the 21 steps}, the forced pair per step, the baseline)."""
    base = least(enumerate_xis(squad, requirements, formation, scale, excluded))
    holds = {conclusion: [] for conclusion in CONCLUSIONS}
    forced_pairs = []
    for step in range(21):
        player = scaled_by(candidate, step, scaled)
        with_him = [row for row in enumerate_xis([*squad, player], requirements, formation, scale,
                                                 excluded) if candidate.player_id in row[0]]
        forced = least(with_him)
        forced_pairs.append(forced)
        # The lexicographic optimum of the squad plus him, whose sum the alternative reads.
        after = min(base, forced, key=above)
        holds["MINIMA_SATISFIABLE"].append(any(floors for _, _, floors in with_him))
        holds["SHORTFALL_VECTOR_LOWER"].append(above(forced) < above(base))
        holds["POSSIBLE_MEMBER"].append(forced is not None and above(forced) <= above(base))
        holds["REMOVES_SHORTFALL"].append(forced == (0, 0) and base != (0, 0))
        holds["TOTAL_SHORTFALL_LOWER"].append(
            forced is not None if base is None else after[1] < base[1])
    return holds, forced_pairs, base


def expected(holds):
    if not any(holds):
        return "NEVER_HOLDS", None
    first = holds.index(True)
    return ("HOLDS_AT_ZERO" if first == 0 else "BREAK_EVEN_FOUND"), first


def additive(*names):
    return [SnapshotMetric(name, name, "SPEC_PER_90", True, None, True, "HEURISTIC", "test")
            for name in names]


def near_half_integer(vectors, requirements, scale) -> bool:
    for r in requirements:
        numbers = [r.minimum] + [v[r.metric] for v in vectors if v.get(r.metric) is not None]
        for number in numbers:
            exact = Fraction(number) / Fraction(r.normalizer) * scale
            if abs(exact - math.floor(exact) - Fraction(1, 2)) < Fraction(1, 10**9):
                return True
    return False


# ----------------------------------------------- instance H: the first test (spec 9.6)

PAIR = Formation("pair", (Slot("s1", "One", ("X",), 0.3, 0.5), Slot("s2", "Two", ("X",), 0.7, 0.5)))
BOTH = additive("r1", "r2")


def instance_h():
    requirements = [TacticalRequirement("r1", "r1", "r1", 1.0, 1.0),
                    TacticalRequirement("r2", "r2", "r2", 1.0, 1.0)]
    squad = [Candidate(1, "A", "X", {"r1": 0.05, "r2": 0.30}, 900, ("s1",)),
             Candidate(2, "B1", "X", {"r1": 0.00, "r2": 0.80}, 900, ("s2",)),
             Candidate(3, "B3", "X", {"r1": 0.60, "r2": 0.70}, 900, ("s2",))]
    candidate = Candidate(9, "C", "X", {"r1": 1.00, "r2": 0.00}, 900, ("s1",))
    return candidate, squad, requirements


def solve_h(**options):
    candidate, squad, requirements = instance_h()
    return break_even_retention(candidate, squad, requirements, PAIR, slot_id="s1",
                                metrics=BOTH, quantization=100, **options)


def test_instance_h_the_default_is_lexicographic_and_the_total_alternative_is_not_monotone():
    # ROOT 2.6 D1: the default conclusion is the lexicographic one, monotone by theorem.
    default = inspect.signature(break_even_retention).parameters["conclusion"].default
    assert default == DEFAULT_CONCLUSION == CONCLUSIONS[0] == "SHORTFALL_VECTOR_LOWER"
    assert DEFAULT_CONCLUSION in MONOTONE_CONCLUSIONS
    assert "TOTAL_SHORTFALL_LOWER" in CONCLUSIONS and "TOTAL_SHORTFALL_LOWER" not in (
        MONOTONE_CONCLUSIONS)

    vector = solve_h()
    assert vector.conclusion == "SHORTFALL_VECTOR_LOWER" and vector.label == (
        "Break-even carry-over fraction")
    assert vector.certificate.baseline_integer == (35, 35) and vector.baseline_objective == (
        0.35, 0.35)
    assert (vector.status, vector.break_even_step, vector.break_even) == (
        "BREAK_EVEN_FOUND", 2, 0.10)
    assert (vector.certificate.scan, vector.certificate.monotone_by_theorem,
            vector.certificate.monotone_observed) == ("BISECTION", True, None)
    fails, holds = vector.bracket
    assert (fails.step, fails.holds, holds.step, holds.holds) == (1, False, 2, True)
    assert holds.forced_inclusion_integer == (30, 60)  # (0.30, 0.60) < (0.35, 0.35)
    assert vector.warnings == () and vector.certificate.completeness == "EXACT"
    assert vector.claim == (
        '"The least declared shortfall (maximum, then total) is strictly lower with him '
        "available\" holds if at least 10% of C's recorded r1, r2 carry over, and fails at 5%. "
        "Both sides were solved exactly.")

    total = solve_h(conclusion="TOTAL_SHORTFALL_LOWER")
    # By hand: holds at steps 8-14 (C with B3, sum 0.30), fails at 15-17 (C with B1 has the
    # lower maximum 0.25, 0.20, 0.20 and the sums 0.45, 0.40, 0.35), holds again at 18-20.
    assert total.holds_above == (8, 9, 10, 11, 12, 13, 14, 18, 19, 20)
    assert (total.status, total.break_even) == ("BREAK_EVEN_FOUND", 0.40)
    assert (total.certificate.scan, total.certificate.monotone_by_theorem,
            total.certificate.monotone_observed) == ("FULL", False, False)
    assert total.certificate.evaluated_steps == tuple(range(21))
    by_step = {point.step: point.forced_inclusion_integer for point in total.profile}
    assert (by_step[14], by_step[15], by_step[16], by_step[17], by_step[18]) == (
        (30, 30), (25, 45), (20, 40), (20, 35), (20, 30))
    assert total.warnings == (
        retention.NON_MONOTONE_WARNING,
        "This conclusion does not hold at every retention above the break-even: it fails again "
        "at 0.75, 0.80, 0.85. Read the profile, not the single number.",
    )
    assert "it does not hold at every one above" in total.claim
    # AUTO never bisects the non-monotone conclusion, and the oracle agrees with both.
    candidate, squad, requirements = instance_h()
    holds, _, base = grid(candidate, squad, requirements, PAIR, 100, ("r1", "r2"))
    assert base == (35, 35)
    for result in (vector, total):
        assert (result.status, result.break_even_step) == expected(holds[result.conclusion])
    assert [p.holds for p in total.profile] == holds["TOTAL_SHORTFALL_LOWER"]
    full = solve_h(scan="FULL")
    assert full.holds_above == tuple(range(2, 21)) and full.certificate.monotone_observed is True
    assert (full.status, full.break_even_step, full.bracket) == (
        vector.status, vector.break_even_step, vector.bracket)


# ------------------------------------------------------------- T1, T2, T4, T5


def draw(rng: random.Random, number: int):
    scale = rng.choice((8, 100, 100_000))
    slots = [Slot("a", "A", ("P",), 0.2, 0.5), Slot("b", "B", ("P", "Q"), 0.5, 0.5)]
    if rng.random() < 0.5:
        slots.append(Slot("c", "C", ("Q",), 0.8, 0.5))
    formation = Formation(f"tiny-{number}", tuple(slots))
    slot_ids = [slot.slot_id for slot in slots]
    positive = number % 3 != 0
    requirements = []
    for metric in ("m0", "m1"):
        incidence = tuple(s for s in slot_ids if rng.random() < 0.7) or (rng.choice(slot_ids),)
        level = rng.uniform(0.6, 1.2) if positive else rng.uniform(0.0, 0.3)
        requirements.append(TacticalRequirement(
            f"need_{metric}", metric, metric, level * len(incidence),
            rng.choice((1.0, rng.uniform(0.3, 2.0))), incidence))
    positions = "PPQQ" + rng.choice("PQ")
    squad = [
        Candidate(pid, f"q{pid}", position, {m: rng.uniform(0.0, 1.0) for m in ("m0", "m1")}, 900)
        for pid, position in zip(rng.sample(range(1, 40), 5), positions, strict=True)
    ]
    # In half of the positive instances the declared deficiency is a departure.
    excluded = ()
    if positive and number % 2:
        excluded = (max(squad, key=lambda p: p.values["m0"]).player_id,)
    slot = rng.choice(slots)
    if number % 10 == 7:  # a slot nobody in the squad can fill: the baseline has no XI
        excluded = tuple(p.player_id for p in squad if p.position == "P")
        slot = slots[0]
    candidate = Candidate(
        77, "cand", rng.choice(slot.allowed_positions),
        {m: rng.choice((0.0, rng.uniform(0.5, 1.8), rng.uniform(0.5, 1.8))) for m in ("m0", "m1")},
        900, (slot.slot_id,),
    )
    scaled = rng.choice(((), ("m0",), ("m1",), ("m0", "m1"), ("m0", "m1"), ("m0", "m1")))
    rng.shuffle(squad)
    return candidate, squad, requirements, formation, scale, slot.slot_id, scaled, excluded


def instances(count=30, seed=20261016):
    rng = random.Random(seed)
    for number in range(count):
        while True:
            built = draw(rng, number)
            candidate, squad, requirements, _, scale, _, scaled, _ = built
            vectors = [p.values for p in squad]
            vectors += [scaled_by(candidate, step, scaled).values for step in range(21)]
            if not near_half_integer(vectors, requirements, scale):
                break
        yield number, built


def test_break_even_equals_the_21_step_enumeration_for_every_conclusion():
    seen = {conclusion: set() for conclusion in CONCLUSIONS}
    interior = unfieldable = empty_scaling = compared = 0
    for number, (candidate, squad, requirements, formation, scale, slot_id, scaled, excluded) in (
            instances()):
        options = dict(slot_id=slot_id, scaled_metrics=scaled, metrics=additive("m0", "m1"),
                       excluded=excluded, quantization=scale)
        plain = inject_candidates([candidate], squad, requirements, formation, slot_id=slot_id,
                                  excluded=excluded, quantization=scale).rows[0]
        # Every conclusion is checked against the enumeration. The full scan is mandatory for
        # the non-monotone one and is compared with the bisection for one monotone conclusion
        # per instance, in rotation.
        rotating = sorted(MONOTONE_CONCLUSIONS)[number % 4]
        table, forced_pairs, base = grid(candidate, squad, requirements, formation, scale, scaled,
                                         excluded)
        for conclusion in CONCLUSIONS:
            where, holds = (number, conclusion), table[conclusion]
            if conclusion in MONOTONE_CONCLUSIONS:
                auto = break_even_retention(candidate, squad, requirements, formation,
                                            conclusion=conclusion, **options)
                # T1 through the bisection
                assert (auto.status, auto.break_even_step) == expected(holds), where
                assert auto.certificate.scan in ("BISECTION", "NONE"), where
                seen[conclusion].add(auto.status)
                if auto.status == "BREAK_EVEN_FOUND":
                    # T4
                    fails, found = auto.bracket
                    assert (fails.step + 1, fails.holds, found.holds) == (found.step, False, True)
                    assert len(auto.certificate.evaluated_steps) <= 7, where
                    interior += 1
                if conclusion != rotating:
                    continue
            full = break_even_retention(candidate, squad, requirements, formation,
                                        conclusion=conclusion, scan="FULL", **options)
            # T1 through the full scan
            assert (full.status, full.break_even_step) == expected(holds), where
            assert full.certificate.completeness == "EXACT", where
            assert full.scaled_metrics == tuple(scaled), where
            seen[conclusion].add(full.status)
            if full.certificate.scan == "FULL":
                assert [p.holds for p in full.profile] == holds, where
                assert full.holds_above == tuple(i for i, h in enumerate(holds) if h), where
                if conclusion != "MINIMA_SATISFIABLE":
                    assert [p.forced_inclusion_integer for p in full.profile] == forced_pairs
                    # T3: the unscaled candidate is the plain injection row.
                    top = full.profile[20]
                    assert top.forced_inclusion_objective == plain.forced_inclusion_objective
                    assert top.with_candidate_objective == plain.with_candidate_objective, where
                    assert full.baseline_unfieldable == (base is None), where
                    unfieldable += base is None
                if conclusion in MONOTONE_CONCLUSIONS:
                    # T5: the theorem, checked on the solved profile.
                    assert full.certificate.monotone_by_theorem, where
                    keys = [above(pair) for pair in forced_pairs]
                    assert keys == sorted(keys, reverse=True), where
                    assert full.certificate.monotone_observed in (True, None), where
                    assert holds == sorted(holds), where
            else:  # decided without a candidate solve: it must be true at no grid value
                assert full.reason == "SATURATED_BASELINE" and not any(holds), where
                assert full.profile == () and base == (0, 0), where
            if not scaled:  # T6: nothing is scaled, so nothing can change along the grid
                assert full.status in ("HOLDS_AT_ZERO", "NEVER_HOLDS"), where
                empty_scaling += 1
            if conclusion in MONOTONE_CONCLUSIONS:
                # T2
                assert (auto.status, auto.break_even_step, auto.reason) == (
                    full.status, full.break_even_step, full.reason), where
                assert auto.bracket == full.bracket, where
                assert auto.certificate.solves <= full.certificate.solves, where
                compared += 1
    full_sets = [c for c, statuses in seen.items()
                 if statuses >= {"BREAK_EVEN_FOUND", "HOLDS_AT_ZERO", "NEVER_HOLDS"}]
    assert len(full_sets) >= 2, seen
    assert interior >= 10 and unfieldable > 0 and empty_scaling > 0 and compared == 30


# ------------------------------------------------------- hand-built boundary cases

ONE = Formation("one", (Slot("s", "Only", ("X",), 0.5, 0.5),))
NEED = [TacticalRequirement("need", "need", "r", 1.0, 1.0)]
INCUMBENT = [Candidate(1, "Inc", "X", {"r": 0.5}, 900)]


def solve_one(value, conclusion=DEFAULT_CONCLUSION, squad=INCUMBENT, **options):
    candidate = Candidate(9, "New", "X", {"r": value}, 900, ("s",))
    result = break_even_retention(candidate, squad, NEED, ONE, slot_id="s", conclusion=conclusion,
                                  metrics=additive("r"), quantization=8, **options)
    holds, _, _ = grid(candidate, squad, NEED, ONE, 8, ("r",), options.get("excluded", ()))
    assert (result.status, result.break_even_step) == expected(holds[conclusion]), (
        value, conclusion)
    return result


def test_boundary_cases_one_quantum_step_twenty_never_and_an_empty_slot():
    # One quantum at scale 8: the incumbent rounds to 4 of 8; the candidate reaches 4 at step 9
    # (in some least-shortfall XI) and 5 at step 12 (in every one).
    lower = solve_one(1.0)
    assert (lower.status, lower.break_even) == ("BREAK_EVEN_FOUND", 0.60)
    assert [p.forced_inclusion_integer for p in lower.bracket] == [(4, 4), (3, 3)]
    assert solve_one(1.0, "POSSIBLE_MEMBER").break_even_step == 9
    # Exactly at the last step, and never.
    last = solve_one(0.575)
    assert (last.break_even_step, last.bracket[0].step, last.bracket[1].step) == (20, 19, 20)
    never = solve_one(0.3)
    assert (never.status, never.break_even, never.reason) == ("NEVER_HOLDS", None, None)
    assert never.certificate.evaluated_steps == (20,) and never.bracket[1] is None
    assert never.bracket[0].holds is False and "does not hold even if 100%" in never.claim
    # The two policies answer different questions: half-even reaches the minimum at step 19,
    # the conservative floor only when the full rate carries over.
    assert solve_one(1.0, "REMOVES_SHORTFALL").break_even_step == 19
    hard = solve_one(1.0, "MINIMA_SATISFIABLE")
    assert (hard.break_even_step, hard.certificate.baseline_status) == (20, "NOT_RUN")
    assert hard.bracket[0].forced_status == "NOT_SATISFIABLE"
    assert hard.bracket[1].forced_status == "SATISFIABLE"
    # The sentence names the slot by its label ("Only"), not by its id ("s").
    assert hard.conclusion_sentence == "Every declared minimum is reachable with him at Only"
    # An empty slot: any admissible body makes the XI fieldable, at zero carry-over.
    empty = solve_one(1.0, excluded=(1,))
    assert (empty.status, empty.break_even, empty.baseline_unfieldable) == (
        "HOLDS_AT_ZERO", 0.0, True)
    assert empty.bracket[0] is None and empty.baseline_objective is None
    assert "holds even if none of New's recorded r carries over (0%)" in empty.claim
    # ... but "falls to zero" still needs a shortfall of zero, not merely an XI.
    assert solve_one(1.0, "REMOVES_SHORTFALL", excluded=(1,)).break_even_step == 19
    # Saturated baseline and an unplaceable candidate: decided without a candidate solve.
    strong = [Candidate(1, "Inc", "X", {"r": 1.0}, 900)]
    saturated = solve_one(1.0, squad=strong)
    assert (saturated.status, saturated.reason, saturated.profile) == (
        "NEVER_HOLDS", "SATURATED_BASELINE", ())
    assert saturated.certificate.scan == "NONE" and saturated.certificate.solves == 1
    assert solve_one(1.0, "POSSIBLE_MEMBER", squad=strong).break_even_step == 19
    unplaced = break_even_retention(Candidate(9, "New", "X", {"r": None}, 900, ("s",)), INCUMBENT,
                                    NEED, ONE, slot_id="s", metrics=additive("r"), quantization=8)
    assert (unplaced.status, unplaced.reason) == ("NEVER_HOLDS", "NO_MEASURED_ADMISSIBLE_SLOT")
    assert unplaced.claim.endswith("the model cannot place New at Only.")


def test_a_negative_rate_voids_the_theorem_and_forces_the_full_scan():
    """A bisection would read "fails at 100%" as never; the conclusion holds at 0% to 35%."""
    squad = [Candidate(1, "Inc", "X", {"r": -0.2}, 900)]
    result = solve_one(-0.5, squad=squad)
    assert (result.status, result.holds_above) == ("HOLDS_AT_ZERO", tuple(range(8)))
    assert (result.certificate.scan, result.certificate.monotone_by_theorem,
            result.certificate.monotone_observed) == ("FULL", False, False)
    assert result.warnings[0] == retention.NEGATIVE_RATE_WARNING
    assert "it fails again at 0.40, 0.45" in result.warnings[1]


def test_only_declared_additive_requirement_rates_are_scaled_and_the_rest_is_held():
    candidate, squad, requirements = instance_h()
    # T6: his only non-zero rate is held, so the grid changes nothing.
    held = break_even_retention(candidate, squad, requirements, PAIR, slot_id="s1", metrics=BOTH,
                                scaled_metrics=("r2",), quantization=100, scan="FULL")
    nothing = break_even_retention(candidate, squad, requirements, PAIR, slot_id="s1",
                                   metrics=BOTH, scaled_metrics=(), quantization=100, scan="FULL")
    for result in (held, nothing):
        assert (result.status, result.holds_above) == ("HOLDS_AT_ZERO", tuple(range(21)))
        assert len({p.forced_inclusion_integer for p in result.profile}) == 1
    assert (held.scaled_metrics, held.unscaled_metrics) == (("r2",), ("r1",))
    assert held.scaling_statements == (
        "Scaled by the carry-over fraction: r2.", "Held at the recorded value: r1.")
    assert nothing.scaling_statements == (
        "Scaled by the carry-over fraction: none.", "Held at the recorded value: r1, r2.")
    # A requirement metric nobody declared an additive rate is never scaled: not by default,
    # not on request.
    undeclared = break_even_retention(candidate, squad, requirements, PAIR, slot_id="s1",
                                      quantization=100)
    assert (undeclared.scaled_metrics, undeclared.unscaled_metrics) == ((), ("r1", "r2"))
    assert undeclared.status == "HOLDS_AT_ZERO"
    shipped = [TacticalRequirement("progression", "p", "progression", 1.0, 1.0)]
    players = [Candidate(1, "A", "X", {"progression": 0.2}, 900)]
    new = Candidate(9, "C", "X", {"progression": 0.9}, 900, ("s",))
    assert break_even_retention(new, players, shipped, ONE, slot_id="s").scaled_metrics == (
        "progression",)
    # Step 20 is the recorded value bit for bit; a hole stays a hole.
    odd = Candidate(9, "C", "X", {"a": 0.1 + 0.2, "b": None, "c": 0.7}, 900, ("s",))
    assert scaled_candidate(odd, 20, ("a", "b")).values == odd.values
    assert scaled_candidate(odd, 5, ("a", "b")).values == {
        "a": float(Fraction(0.1 + 0.2) / 4), "b": None, "c": 0.7}
    refusals = [
        dict(scaled_metrics=("r3",)), dict(scaled_metrics=("r1",), metrics=additive("r2")),
        dict(conclusion="BEST"), dict(scan="BISECTION"), dict(slot_id="s2"), dict(time_limit=-1),
    ]
    for options in refusals:
        with pytest.raises(ValueError):
            break_even_retention(candidate, squad, requirements, PAIR,
                                 **{"slot_id": "s1", "metrics": BOTH, **options})
    with pytest.raises(ValueError):
        break_even_retention(replace(candidate, player_id=1), squad, requirements, PAIR,
                             slot_id="s1", metrics=BOTH)
    with pytest.raises(ValueError):
        scaled_candidate(odd, 21, ("a",))


# ------------------------------------------------------------------- T7: deadlines


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


def test_an_undecided_solve_is_never_read_as_fails_and_never_yields_a_break_even(monkeypatch):
    exact = solve_h()
    assert exact.certificate.solves == 21  # baseline 3, then six grid values of three solves
    # Bisection: whichever solve is left undecided, no value is implied.
    for on_call in range(1, 22):
        with monkeypatch.context() as patch:
            override_status(patch, on_call, cp_model.UNKNOWN)
            result = solve_h()
        assert (result.status, result.break_even, result.break_even_step) == (
            "UNDETERMINED", None, None), on_call
        assert result.bracket == (None, None) and result.certificate.completeness == "DEADLINE"
        assert result.warnings == (
            "The break-even was not determined within 30 s. No value is implied.",)
        assert result.claim.endswith("No value is implied.")
        # The baseline's own three solves come first; after them exactly one step is open.
        assert sum(p.holds is None for p in result.profile) == (on_call > 3), on_call
    # Full scan: an undecided step below the first holding step leaves the break-even open ...
    with monkeypatch.context() as patch:
        override_status(patch, 4, cp_model.UNKNOWN)
        result = solve_h(conclusion="TOTAL_SHORTFALL_LOWER")
    assert (result.status, result.break_even, result.profile[0].holds) == (
        "UNDETERMINED", None, None)
    # ... and one above it leaves the break-even proved and the monotonicity unobserved.
    with monkeypatch.context() as patch:
        override_status(patch, 3 + 3 * 20 + 1, cp_model.UNKNOWN)
        result = solve_h(conclusion="TOTAL_SHORTFALL_LOWER")
    assert (result.status, result.break_even_step, result.profile[20].holds) == (
        "BREAK_EVEN_FOUND", 8, None)
    assert result.certificate.monotone_observed is None
    assert result.certificate.completeness == "DEADLINE"
    # No time left after the first clock reading: nothing is solved.
    calls = override_status(monkeypatch, 0, cp_model.UNKNOWN)
    clock = iter([0.0])
    monkeypatch.setattr(retention.time, "monotonic", lambda: next(clock, 5.0))
    result = solve_h(time_limit=1.0)
    assert calls == [] and result.certificate.solves == 0
    assert (result.status, result.certificate.baseline_status, result.profile) == (
        "UNDETERMINED", "UNKNOWN", ())


# ------------------------------------------------------- guard, provenance, hashes


def test_results_carry_no_merit_key_no_prior_certificate_and_a_canonical_fingerprint(thesis_guard):
    candidate, squad, requirements = instance_h()
    lineage = {"dataset_hash": "abc", "providers": ["pappalardo"], "objective_vector": [0, 0],
               "retention_break_even": 0.1, "bootstrap_worlds": 40}

    def solve(squad=squad, **changed):
        return break_even_retention(candidate, squad, requirements, PAIR, **{
            "slot_id": "s1", "metrics": BOTH, "quantization": 100, "provenance": lineage,
            **changed})

    result = solve()
    thesis_guard(asdict(result))
    provenance = result.provenance
    assert provenance["providers"] == ["pappalardo"] and provenance["dataset_hash"] == "abc"
    assert not {"objective_vector", "retention_break_even", "bootstrap_worlds"} & set(provenance)
    assert provenance["grid"] == "0.00 to 1.00 in steps of 0.05"
    assert provenance["carry_over"] == (
        "No carry-over function is applied. Retention is a scenario, not an estimate.")
    assert result.evidence["composed"] == "HEURISTIC"
    declared = {entry["input"]: entry["value"] for entry in result.evidence["declared_inputs"]}
    assert declared["conclusion"] == "SHORTFALL_VECTOR_LOWER" and declared["scaled_metrics"] == [
        "r1", "r2"]
    assert "not a forecast" in result.non_claim
    assert (result.certificate.shortfall_policy, result.certificate.hard_policy) == (
        engine.SHORTFALL_POLICY, engine.HARD_POLICY)
    same = solve(squad=list(reversed(squad)))
    assert same.provenance["input_fingerprint"] == provenance["input_fingerprint"]
    changed = [solve(conclusion="POSSIBLE_MEMBER"), solve(scaled_metrics=("r1",)),
               solve(scan="FULL"), solve(excluded=(2,)), solve(quantization=1000)]
    prints = {r.provenance["input_fingerprint"] for r in changed}
    assert len(prints) == len(changed) and provenance["input_fingerprint"] not in prints


# --------------------------------- review: no sentence says more than the solves it stands on


def test_no_sentence_says_every_grid_value_was_solved_unless_every_one_was(monkeypatch):
    # Complete full scan: the sentences are entitled to it (the positive case).
    whole = solve_h(conclusion="TOTAL_SHORTFALL_LOWER")
    assert whole.warnings[0] == retention.NON_MONOTONE_WARNING
    assert "Every grid value was solved" in whole.warnings[0]
    assert "Every grid value was solved exactly; it does not hold at every one above." in (
        whole.claim)
    # One grid value above the break-even left undecided: the break-even stands, the rest is open.
    with monkeypatch.context() as patch:
        override_status(patch, 3 + 3 * 20 + 1, cp_model.UNKNOWN)
        cut = solve_h(conclusion="TOTAL_SHORTFALL_LOWER")
    assert (cut.status, cut.break_even_step, cut.certificate.monotone_observed) == (
        "BREAK_EVEN_FOUND", 8, None)
    assert cut.profile[20].holds is None and cut.certificate.completeness == "DEADLINE"
    for sentence in (cut.claim, *cut.warnings):
        assert "Every grid value was solved" not in sentence, sentence
    assert "does not hold at every one above" not in cut.claim
    assert cut.claim.endswith(
        "it fails at 35%. Not every grid value above it was solved; whether it holds at every "
        "one above is not established.")
    assert cut.warnings == (
        "The total at the least-shortfall optimum can rise when the maximum falls, so this "
        "conclusion can fail again above its break-even. Not every grid value was solved.",)
    # Decided without any candidate solve: nothing on the grid was solved, and nothing says so.
    strong = [Candidate(1, "Inc", "X", {"r": 1.0}, 900)]
    saturated = solve_one(1.0, "TOTAL_SHORTFALL_LOWER", squad=strong)
    assert (saturated.status, saturated.reason, saturated.certificate.scan,
            saturated.profile) == ("NEVER_HOLDS", "SATURATED_BASELINE", "NONE", ())
    assert all("grid value was solved" not in warning for warning in saturated.warnings)
    negative = solve_one(-0.5, squad=strong)
    assert (negative.reason, negative.certificate.scan) == ("SATURATED_BASELINE", "NONE")
    assert all("grid value was solved" not in warning for warning in negative.warnings)


# ------------------------------------------- a page prints these sentences: labels, not ids


def test_no_sentence_of_a_break_even_names_a_slot_a_requirement_or_a_metric_by_its_id():
    formation = Formation("pair", (Slot("zs1", "Near side", ("X",), 0.3, 0.5),
                                   Slot("zs2", "Far side", ("X",), 0.7, 0.5)))
    requirements = [TacticalRequirement("rq_one", "Alpha per 90", "mx_one", 1.0, 1.0),
                    TacticalRequirement("rq_two", "Beta per 90", "mx_two", 1.0, 1.0)]
    squad = [Candidate(1, "A", "X", {"mx_one": 0.05, "mx_two": 0.30}, 900, ("zs1",)),
             Candidate(2, "B1", "X", {"mx_one": 0.00, "mx_two": 0.80}, 900, ("zs2",)),
             Candidate(3, "B3", "X", {"mx_one": 0.60, "mx_two": 0.70}, 900, ("zs2",))]
    candidate = Candidate(9, "C", "X", {"mx_one": 1.00, "mx_two": 0.00}, 900, ("zs1",))
    labelled = [
        SnapshotMetric("mx_one", "Alpha per 90", "SPEC_PER_90", True, None, True, "HEURISTIC", "t"),
        SnapshotMetric("mx_two", "Beta per 90", "SPEC_PER_90", True, None, True, "HEURISTIC", "t"),
    ]

    def solve(**options):
        return break_even_retention(candidate, squad, requirements, formation, slot_id="zs1",
                                    metrics=labelled, quantization=100, **options)

    results = [solve(conclusion=conclusion) for conclusion in CONCLUSIONS]
    results += [solve(scaled_metrics=("mx_two",), scan="FULL"), solve(scaled_metrics=()),
                solve(excluded=(1,))]
    unplaced = replace(candidate, values={"mx_one": None, "mx_two": None})
    results.append(break_even_retention(unplaced, squad, requirements, formation, slot_id="zs1",
                                        metrics=labelled, quantization=100))
    assert {r.status for r in results} >= {"BREAK_EVEN_FOUND", "HOLDS_AT_ZERO", "NEVER_HOLDS"}
    for result in results:
        sentences = (result.claim, result.non_claim, result.conclusion_sentence, result.label,
                     *result.warnings, *result.scaling_statements)
        for token in ("zs1", "zs2", "rq_one", "rq_two", "mx_one", "mx_two"):
            for text in sentences:
                assert not re.search(
                    rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])", text), (token, text)
    assert results[0].scaling_statements == (
        "Scaled by the carry-over fraction: Alpha per 90, Beta per 90.",
        "Held at the recorded value: none.")
    assert "of C's recorded Alpha per 90, Beta per 90 carry over" in results[0].claim
    assert results[5].scaling_statements == (
        "Scaled by the carry-over fraction: Beta per 90.",
        "Held at the recorded value: Alpha per 90.")
    # The ids stay in the fields beside the sentences.
    assert (results[5].scaled_metrics, results[5].unscaled_metrics) == (("mx_two",), ("mx_one",))
    # A metric the caller gave no label is named by its id: there is nothing else to print.
    bare = [replace(metric, label="") for metric in labelled]
    assert break_even_retention(
        candidate, squad, requirements, formation, slot_id="zs1", metrics=bare, quantization=100
    ).scaling_statements[0] == "Scaled by the carry-over fraction: mx_one, mx_two."
