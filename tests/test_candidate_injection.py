"""Candidate injection against an enumeration that shares nothing with it or with the kernel.

The oracle is typed from the problem statement: ``itertools.permutations`` over the squad and
over the squad plus the candidate, integers by exact ``Fraction`` half-even, least-shortfall
XIs as explicit lists, membership by ``any`` / ``all``, the forced value by filtering to the
XIs with the candidate at the slot. It imports only the domain dataclasses.
"""

from __future__ import annotations

import dataclasses
import itertools
import math
import random
from dataclasses import asdict, replace
from fractions import Fraction

import pytest
from ortools.sat.python import cp_model

from galactico.optimization.squad import kernel as engine
from galactico.optimization.transfers import injection
from galactico.optimization.transfers.injection import (
    OUTCOME_GROUPS,
    SATURATED_WARNING,
    inject_candidates,
    injection_detail,
)
from galactico.optimization.xi.domain import Candidate, Formation, Slot, TacticalRequirement
from galactico.optimization.xi.solver import candidate_injection

# --------------------------------------------------------------------------- oracle


def active_of(requirements):
    return sorted(
        (r for r in requirements if r.status == "active" and r.evidence_class != "UNAVAILABLE"),
        key=lambda r: r.requirement_id,
    )


def applies(requirement, slot_id):
    return not requirement.slot_ids or slot_id in requirement.slot_ids


def enumerate_xis(players, requirements, formation, scale, excluded=(), locked=(), values=None):
    """Every admissible XI as ({slot: player}, shortfall integers by requirement id)."""
    active = active_of(requirements)
    vector = {p.player_id: (values or {}).get(p.player_id, p.values) for p in players}
    usable = [p for p in players if p.player_id not in excluded and p.minutes > 0]
    rows = []
    for combo in itertools.permutations(usable, len(formation.slots)):
        if not set(locked) <= {p.player_id for p in combo}:
            continue
        admitted = all(
            p.position in slot.allowed_positions
            and (p.eligible_slots is None or slot.slot_id in p.eligible_slots)
            and all(
                vector[p.player_id].get(r.metric) is not None
                for r in active
                if applies(r, slot.slot_id)
            )
            for p, slot in zip(combo, formation.slots, strict=True)
        )
        if not admitted:
            continue
        shortfalls = []
        for r in active:
            achieved = sum(
                round(Fraction(vector[p.player_id][r.metric]) / Fraction(r.normalizer) * scale)
                for p, slot in zip(combo, formation.slots, strict=True)
                if applies(r, slot.slot_id)
            )
            target = round(Fraction(r.minimum) / Fraction(r.normalizer) * scale)
            shortfalls.append(max(0, target - achieved))
        lineup = {slot.slot_id: p.player_id for p, slot in zip(combo, formation.slots, strict=True)}
        rows.append((lineup, tuple(shortfalls)))
    return rows


def least(rows):
    """(least (maximum, sum), the XIs attaining it); (None, []) when there is no XI."""
    if not rows:
        return None, []
    pair = min((max(s, default=0), sum(s)) for _, s in rows)
    return pair, [row for row in rows if (max(row[1], default=0), sum(row[1])) == pair]


def above(pair):
    """No XI compares above every pair."""
    return (1,) if pair is None else (0, *pair)


def truth(squad, candidate, requirements, formation, scale, slot_id, **declared):
    base, base_best = least(enumerate_xis(squad, requirements, formation, scale, **declared))
    together = enumerate_xis([*squad, candidate], requirements, formation, scale, **declared)
    after, after_best = least(together)
    cid = candidate.player_id
    forced, forced_best = least([row for row in together if row[0].get(slot_id) == cid])
    return {
        "base": base,
        "after": after,
        "forced": forced,
        "possible": any(cid in row[0].values() for row in after_best),
        "necessary": bool(after_best) and all(cid in row[0].values() for row in after_best),
        "base_best": base_best,
        "after_best": after_best,
        "forced_best": forced_best,
    }


def expected_outcome(candidate, requirements, formation, slot_id, fact):
    slot = next(s for s in formation.slots if s.slot_id == slot_id)
    placeable = (
        candidate.minutes > 0
        and candidate.position in slot.allowed_positions
        and all(
            candidate.values.get(r.metric) is not None
            for r in active_of(requirements)
            if applies(r, slot_id)
        )
    )
    if not placeable:
        return "NOT_EVALUABLE"
    if fact["base"] is None:
        return "MAKES_FIELDABLE" if fact["after"] is not None else "UNCHANGED"
    if fact["after"] == fact["base"]:
        return "UNCHANGED"
    return "REMOVES_SHORTFALL" if fact["after"] == (0, 0) else "LOWERS_SHORTFALL"


def members(best, ids):
    return {
        pid: (any(pid in row[0].values() for row in best),
              bool(best) and all(pid in row[0].values() for row in best))
        for pid in ids
    }


def near_half_integer(vectors, requirements, scale) -> bool:
    """The only place the shipped float expression and exact half-even can differ."""
    for r in active_of(requirements):
        numbers = [r.minimum] + [v[r.metric] for v in vectors if v.get(r.metric) is not None]
        for number in numbers:
            exact = Fraction(number) / Fraction(r.normalizer) * scale
            if abs(exact - math.floor(exact) - Fraction(1, 2)) < Fraction(1, 10**9):
                return True
    return False


# ------------------------------------------------------------------------ generator

SHAPE = Formation(
    "tiny",
    (
        Slot("a", "Back", ("D",), 0.2, 0.7),
        Slot("b", "Middle", ("M", "F"), 0.5, 0.5),
        Slot("c", "Front", ("F",), 0.8, 0.2),
    ),
)
METRICS = ("m0", "m1")


def draw(rng: random.Random, number: int):
    scale = rng.choice((3, 8, 100_000))
    saturated = number % 3 == 0
    unfieldable = number % 6 == 1  # the pool slot has no squad player
    slot_id = "c" if unfieldable or rng.random() < 0.7 else "b"
    requirements = []
    for metric in METRICS:
        incidence = tuple(s for s in "abc" if rng.random() < 0.7) or (slot_id,)
        level = rng.uniform(0.0, 0.3) if saturated else rng.uniform(0.5, 1.1)
        requirements.append(
            TacticalRequirement(
                f"need_{metric}", metric, metric, level * len(incidence),
                rng.choice((1.0, rng.uniform(0.3, 2.0))), incidence,
                rng.choice(("MEASURED", "HEURISTIC")),
            )
        )

    def vector(ceiling=1.0, holes=0.0):
        return {m: None if rng.random() < holes else rng.uniform(0.0, ceiling) for m in METRICS}

    positions = ["D", "D", "M", "M", "F", "F"][: rng.randint(5, 6)]
    if unfieldable:
        positions = [p if p != "F" else "M" for p in positions]
    squad = [
        Candidate(pid, f"q{pid}", position, vector(holes=0.05), 900)
        for pid, position in zip(rng.sample(range(1, 50), len(positions)), positions, strict=True)
    ]
    pool = []
    for pid in (101, 102, 103, 104):
        position = "F" if slot_id == "c" else rng.choice(("M", "F"))
        values = vector(rng.choice((0.0, 0.4, 1.4)), holes=0.08)
        if pid == 104 and rng.random() < 0.3:
            position = "D"  # not admitted at the pool slot
        if pid == 103 and rng.random() < 0.4:
            values = dict(rng.choice(squad).values)  # equal to a squad player: ties
        pool.append(Candidate(pid, f"c{pid}", position, values, 900, (slot_id,)))
    ids = [p.player_id for p in squad]
    declared = {
        "excluded": (rng.choice(ids),) if number % 3 == 2 else (),
        "locked": (rng.choice(ids),) if number % 5 == 4 else (),
    }
    if set(declared["excluded"]) & set(declared["locked"]):
        declared["locked"] = ()
    worlds = None
    if number % 4 == 0:  # ten instances carry three shared worlds with one planted hole
        squad_worlds = {w: {p.player_id: vector(holes=0.0) for p in squad} for w in range(3)}
        pool_worlds = {w: {p.player_id: vector(1.4) for p in pool} for w in range(3)}
        if number % 8 == 0:
            del pool_worlds[1][101]
        else:
            holder = next(p for p in squad if p.player_id not in declared["excluded"])
            squad_worlds[2][holder.player_id] = dict.fromkeys(METRICS)
        worlds = (squad_worlds, pool_worlds)
    rng.shuffle(squad)
    rng.shuffle(pool)
    return squad, pool, requirements, scale, slot_id, declared, worlds


def instances(count=40, seed=20261015):
    rng = random.Random(seed)
    for number in range(count):
        while True:
            built = draw(rng, number)
            squad, pool, requirements, scale, _, _, worlds = built
            vectors = [p.values for p in (*squad, *pool)]
            for table in worlds or ():
                vectors += [v for world in table.values() for v in world.values()]
            if not near_half_integer(vectors, requirements, scale):
                break
        yield number, built


def facts_of(row):
    """What must not depend on the pool, its order or the ordering."""
    return replace(row, order_key_value=None)


# ----------------------------------------------------- J1, J3, J4, J5, worlds


def test_rows_equal_the_enumeration_on_seeded_instances():
    seen = {"membership": set(), "shortcut": set(), "outcome": set(), "leading": set(),
            "sum_at_optimum": set(), "discarded": 0, "used": 0, "cells": set()}
    for number, (squad, pool, requirements, scale, slot_id, declared, worlds) in instances():
        options = dict(slot_id=slot_id, quantization=scale, **declared)
        if worlds:
            options.update(squad_worlds=worlds[0], pool_worlds=worlds[1], world_namespace="test")
        result = inject_candidates(pool, squad, requirements, SHAPE, **options)
        plain = inject_candidates(pool, squad, requirements, SHAPE, _shortcuts=False, **options)
        rows = {row.player_id: row for row in result.rows}
        assert sorted(rows) == [101, 102, 103, 104] and result.screened_count == 4, number
        assert result.certificate.completeness == "EXACT", number
        by_plain = {row.player_id: row for row in plain.rows}
        for candidate in pool:
            row, cid = rows[candidate.player_id], candidate.player_id
            fact = truth(squad, candidate, requirements, SHAPE, scale, slot_id, **declared)
            assert result.certificate.baseline_integer == fact["base"], number
            assert row.with_candidate_integer == fact["after"], (number, cid)
            assert (row.possible, row.necessary) == (
                fact["possible"], fact["necessary"]), (number, cid)
            assert row.outcome == expected_outcome(candidate, requirements, SHAPE, slot_id, fact)
            if row.resolution == "SOLVED":
                assert row.forced_inclusion_integer == fact["forced"], (number, cid)
                assert row.forced_status == (
                    "UNFIELDABLE" if fact["forced"] is None else "CERTIFIED"), (number, cid)
            else:  # no variable at the slot: nothing was solved, and nothing could be
                assert (row.resolution, row.shortcut, row.forced_status) == (
                    "NO_MEASURED_ADMISSIBLE_SLOT", "NO_VARIABLE", "NOT_RUN")
                assert fact["forced"] is None
                assert by_plain[cid].forced_status == "UNFIELDABLE"
            # J3: the path through the kernel states the same facts as the shortcut.
            for name in ("outcome", "with_candidate_integer", "possible", "necessary",
                         "membership"):
                assert getattr(by_plain[cid], name) == getattr(row, name), (number, cid, name)
            # J4, and the direction rule: the leading component never rises with an addition.
            assert above(fact["after"]) <= above(fact["base"])
            assert above(fact["forced"]) >= above(fact["after"])
            if fact["base"] and fact["after"]:
                assert row.with_candidate_integer[0] <= fact["base"][0]
                seen["leading"].add(row.with_candidate_integer[0] < fact["base"][0])
                if row.necessary:
                    seen["sum_at_optimum"].add(
                        (row.with_candidate_integer[1] > fact["base"][1])
                        - (row.with_candidate_integer[1] < fact["base"][1]))
            if row.forced_inclusion_change is not None:
                change = tuple(round(v * scale) for v in row.forced_inclusion_change)
                assert change == tuple(
                    f - b for f, b in zip(fact["forced"], fact["base"], strict=True))
                seen["cells"].add((change > (0, 0)) - (change < (0, 0)))
            else:
                assert fact["forced"] is None or fact["base"] is None
            seen["membership"].add(row.membership)
            seen["shortcut"].add(row.shortcut)
            seen["outcome"].add(row.outcome)
            if worlds and row.resolution == "SOLVED":
                expected = {"lower": 0, "equal": 0, "higher": 0, "discarded": [], "incomplete": []}
                for world_id in sorted(worlds[0]):
                    squad_values = worlds[0][world_id]
                    own = worlds[1][world_id].get(cid)
                    hole = own is None or any(
                        own.get(r.metric) is None
                        for r in active_of(requirements) if applies(r, slot_id))
                    for player in squad:
                        if player.player_id in declared["excluded"]:
                            continue
                        needed = {
                            r.metric for r in active_of(requirements) for slot in SHAPE.slots
                            if player.position in slot.allowed_positions
                            and applies(r, slot.slot_id)
                        }
                        hole |= any(squad_values[player.player_id].get(m) is None for m in needed)
                    if hole:
                        expected["discarded"].append(world_id)
                        continue
                    there = truth(squad, candidate, requirements, SHAPE, scale, slot_id,
                                  values={**squad_values, cid: own}, **declared)
                    if there["base"] is None or there["forced"] is None:
                        expected["incomplete"].append(world_id)
                        continue
                    cell = "lower" if there["forced"] < there["base"] else (
                        "equal" if there["forced"] == there["base"] else "higher")
                    expected[cell] += 1
                counts = row.world_counts
                assert (counts.forced_lower, counts.forced_equal, counts.forced_higher) == (
                    expected["lower"], expected["equal"], expected["higher"]), (number, cid)
                assert [d["world_id"] for d in counts.discarded] == expected["discarded"]
                assert [d["world_id"] for d in counts.incomplete] == expected["incomplete"]
                assert counts.requested == 3 and counts.namespace == "test"
                assert counts.used == sum(expected[k] for k in ("lower", "equal", "higher"))
                seen["discarded"] += len(counts.discarded)
                seen["used"] += counts.used
            else:
                assert row.world_counts is None or row.resolution != "SOLVED"
        # J5: a row's facts do not depend on who else was screened, the pool order or the key.
        if number % 4 == 1:
            alone = inject_candidates(list(reversed(pool))[:2], squad, requirements, SHAPE,
                                      order_by="PLAYER_ID", descending=True, **options)
            for row in alone.rows:
                assert facts_of(row) == facts_of(rows[row.player_id]), number
    assert seen["membership"] == {"NECESSARY", "POSSIBLE", "NOT_POSSIBLE"}
    assert seen["shortcut"] == {"NONE", "NO_VARIABLE", "ZERO_WITNESS", "SATURATED_BASELINE"}
    assert seen["outcome"] == set(OUTCOME_GROUPS) - {"UNDETERMINED"}
    assert seen["cells"] == {-1, 0, 1}  # a forced inclusion lowers, keeps and raises the value
    assert seen["leading"] == {True, False}
    assert seen["sum_at_optimum"] >= {-1}  # the rising sum is the hand-built instance below
    assert seen["discarded"] > 0 and seen["used"] > 0


# ----------------------------------------------------------------- J8: detail


def test_detail_equals_the_enumeration_and_names_who_is_no_longer_possible():
    seen = {"gone": 0, "nobody": 0, "ranges": 0, "wide": 0}
    # Hand-built: two equally least XIs that split the same shortfall differently between the
    # requirements, so a range is wider than a point and one representative would mislead.
    both = ("b", "c")
    split = (
        [Candidate(1, "d", "D", {"m0": 0.0, "m1": 0.0}, 900),
         Candidate(2, "left", "M", {"m0": 0.5, "m1": 0.3}, 900),
         Candidate(3, "right", "M", {"m0": 0.3, "m1": 0.5}, 900),
         Candidate(4, "f", "F", {"m0": 0.2, "m1": 0.2}, 900)],
        [Candidate(101, "same", "F", {"m0": 0.2, "m1": 0.2}, 900, ("c",)),
         Candidate(102, "more", "F", {"m0": 0.4, "m1": 0.2}, 900, ("c",))],
        [TacticalRequirement("need_m0", "m0", "m0", 1.0, 1.0, both),
         TacticalRequirement("need_m1", "m1", "m1", 1.0, 1.0, both)],
        100, "c", {"excluded": (), "locked": ()}, None,
    )
    for number, (squad, pool, requirements, scale, slot_id, declared, _) in (
            *instances(count=24), ("split", split)):
        ids = sorted(p.player_id for p in squad)
        rids = [r.requirement_id for r in active_of(requirements)]
        for candidate in sorted(pool, key=lambda c: c.player_id)[:2]:
            fact = truth(squad, candidate, requirements, SHAPE, scale, slot_id, **declared)
            detail = injection_detail(candidate, squad, requirements, SHAPE, slot_id=slot_id,
                                      quantization=scale, **declared)
            where = (number, candidate.player_id)
            assert detail.certificate.completeness == "EXACT", where
            assert (detail.row.possible, detail.row.necessary) == (
                fact["possible"], fact["necessary"]), where

            def table(found):
                return {pid: (m.possible, m.necessary) for pid, m in found.items()}

            before = members(fact["base_best"], ids) if fact["base"] else {}
            after = members(fact["after_best"], ids) if fact["after"] else {}
            inside = members(fact["forced_best"], ids) if fact["forced"] else {}
            assert table(detail.squad_membership_baseline) == before, where
            assert table(detail.squad_membership_with_candidate) == after, where
            assert table(detail.squad_membership_forced) == inside, where
            gone = tuple(pid for pid in ids
                         if before and after and before[pid][0] and not after[pid][0])
            assert detail.no_longer_possible_ids == gone, where
            assert detail.no_longer_necessary_ids == tuple(
                pid for pid in ids if before and after and before[pid][1] and not after[pid][1])
            # A player leaves the least-shortfall XIs only for a candidate who is in all of them.
            assert not gone or fact["necessary"]
            if fact["base"] and fact["after"]:
                seen["gone" if gone else "nobody"] += 1
                assert ("forced out" in detail.tie_statement) == (not gone), where
            for index, rid in enumerate(rids):
                found = next(r for r in detail.requirement_ranges if r.requirement_id == rid)
                for best, low, high in ((fact["forced_best"], found.least_shortfall,
                                         found.greatest_shortfall),
                                        (fact["base_best"], found.baseline_least,
                                         found.baseline_greatest)):
                    if not best:
                        assert low is None and high is None, where
                        continue
                    column = [row[1][index] for row in best]
                    assert (round(low * scale), round(high * scale)) == (min(column), max(column))
                    seen["ranges"] += 1
                    seen["wide"] += min(column) != max(column)
            if fact["forced"]:
                assert dict(detail.forced_lineup) in [row[0] for row in fact["forced_best"]]
    assert seen["gone"] > 0 and seen["nobody"] > 0 and seen["ranges"] > 0 and seen["wide"] > 0


# --------------------------------------------------------- hand-built boundary cases

PAIR = Formation("pair", (Slot("s1", "One", ("X",), 0.3, 0.5), Slot("s2", "Two", ("X",), 0.7, 0.5)))


def one_need(minimum=1.0):
    return [TacticalRequirement("need", "need", "r", minimum, 1.0)]


def pair_squad():
    return [Candidate(1, "Ann", "X", {"r": 0.3}, 900, ("s1",)),
            Candidate(2, "Bo", "X", {"r": 0.4}, 900, ("s2",))]


def newcomer(value, pid=9, name="New"):
    return Candidate(pid, name, "X", {"r": value}, 900, ("s1",))


def only_row(candidate, squad, requirements, formation=PAIR, **options):
    result = inject_candidates([candidate], squad, requirements, formation, slot_id="s1",
                               quantization=100, **options)
    (row,) = result.rows
    return row, result


def detail_of(candidate, squad, requirements):
    return injection_detail(candidate, squad, requirements, PAIR, slot_id="s1", quantization=100)


def test_boundary_cases_state_the_exact_category_and_the_signed_change():
    squad = pair_squad()
    # (1) identical to the incumbent: in some least-shortfall XI, not in all, nobody forced out.
    row, result = only_row(newcomer(0.3), squad, one_need())
    assert (row.membership, row.outcome, row.forced_inclusion_change) == (
        "POSSIBLE", "UNCHANGED", (0.0, 0.0))
    assert result.baseline_objective == (0.3, 0.3) and row.with_candidate_objective == (0.3, 0.3)
    detail = detail_of(newcomer(0.3), squad, one_need())
    assert detail.no_longer_possible_ids == () and detail.no_longer_necessary_ids == (1,)
    assert detail.tie_statement == (
        "No squad player is forced out: every player who is in a least-shortfall XI without "
        "New is still in one with him available.")
    # (2) one quantum above the incumbent: in every least-shortfall XI; the incumbent in none.
    row, _ = only_row(newcomer(0.31), squad, one_need())
    assert (row.membership, row.outcome, row.forced_inclusion_integer) == (
        "NECESSARY", "LOWERS_SHORTFALL", (29, 29))
    assert row.forced_inclusion_change == (-0.01, -0.01)
    detail = detail_of(newcomer(0.31), squad, one_need())
    assert detail.no_longer_possible_ids == (1,)
    assert detail.tie_statement == (
        "With New available, these players are in a least-shortfall XI without him and in "
        "none with him: Ann.")
    assert detail.claim == (
        "With New placed at s1, the least declared shortfall is (maximum 0.29, sum 0.29); "
        "without him it is (maximum 0.3, sum 0.3). In the squad plus him he is in every "
        "least-shortfall XI.")
    # (3) an unavailable rate on an applicable requirement: not placed, not imputed, no solve.
    row, result = only_row(newcomer(None), squad, one_need())
    assert (row.outcome, row.resolution, row.shortcut, row.forced_status, row.membership) == (
        "NOT_EVALUABLE", "NO_MEASURED_ADMISSIBLE_SLOT", "NO_VARIABLE", "NOT_RUN", "NOT_POSSIBLE")
    assert row.with_candidate_objective == (0.3, 0.3) and row.forced_inclusion_objective is None
    assert result.pool_median_reference.outcome == "NOT_EVALUABLE"  # no available rate to take
    # (4) saturated baseline: an invented player is POSSIBLE by a zero witness and displaces no one.
    row, result = only_row(newcomer(0.9), squad, one_need(0.5))
    assert (row.membership, row.outcome, row.shortcut) == ("POSSIBLE", "UNCHANGED", "ZERO_WITNESS")
    assert result.baseline_objective == (0.0, 0.0) and result.warnings == (SATURATED_WARNING,)
    detail = detail_of(newcomer(0.9), squad, one_need(0.5))
    assert detail.no_longer_possible_ids == () and "forced out" in detail.tie_statement
    # ... and one who cannot reach zero is in none, decided by the first stage alone.
    row, _ = only_row(newcomer(0.05), squad, one_need(0.5))
    assert (row.membership, row.shortcut, row.forced_inclusion_change) == (
        "NOT_POSSIBLE", "SATURATED_BASELINE", (0.05, 0.05))
    # (5) forced inclusion raises the shortfall: in no least-shortfall XI, value unchanged.
    row, _ = only_row(newcomer(0.1), squad, one_need())
    assert (row.membership, row.outcome, row.forced_inclusion_change) == (
        "NOT_POSSIBLE", "UNCHANGED", (0.2, 0.2))
    assert (row.with_candidate_objective, row.forced_inclusion_objective) == (
        (0.3, 0.3), (0.5, 0.5))
    detail = detail_of(newcomer(0.1), squad, one_need())
    assert detail.tie_statement == (
        "No squad player is forced out: New is in no least-shortfall XI, so the least-shortfall "
        "XIs are the same with and without him.")
    # The declared shortfall is removed, and an empty slot is made fieldable.
    row, _ = only_row(newcomer(0.8), squad, one_need())
    assert (row.outcome, row.shortcut, row.membership) == (
        "REMOVES_SHORTFALL", "ZERO_WITNESS", "NECESSARY")
    row, result = only_row(newcomer(0.2), squad, one_need(), excluded=(1,))
    assert (row.outcome, row.membership, row.forced_inclusion_change) == (
        "MAKES_FIELDABLE", "NECESSARY", None)
    assert result.baseline_objective is None and result.certificate.baseline_status == "UNFIELDABLE"
    assert result.warnings == (injection.UNFIELDABLE_WARNING,)
    row, _ = only_row(newcomer(None), squad, one_need(), excluded=(1,))
    assert (row.outcome, row.possible, row.necessary, row.with_candidate_objective) == (
        "NOT_EVALUABLE", False, False, None)


def instance_h():
    requirements = [TacticalRequirement("r1", "r1", "r1", 1.0, 1.0),
                    TacticalRequirement("r2", "r2", "r2", 1.0, 1.0)]
    squad = [Candidate(1, "A", "X", {"r1": 0.05, "r2": 0.30}, 900, ("s1",)),
             Candidate(2, "B1", "X", {"r1": 0.00, "r2": 0.80}, 900, ("s2",)),
             Candidate(3, "B3", "X", {"r1": 0.60, "r2": 0.70}, 900, ("s2",))]
    return squad, requirements


def test_a_lower_maximum_can_come_with_a_higher_sum_and_the_row_says_both():
    """(6) Critic C2: the leading component never rises; the sum at the optimum can."""
    squad, requirements = instance_h()
    strong = Candidate(9, "C", "X", {"r1": 1.0, "r2": 0.0}, 900, ("s1",))
    partial = Candidate(8, "C80", "X", {"r1": 0.8, "r2": 0.0}, 900, ("s1",))
    result = inject_candidates([strong, partial], squad, requirements, PAIR, slot_id="s1",
                               quantization=100)
    rows = {row.player_id: row for row in result.rows}
    assert result.certificate.baseline_integer == (35, 35)
    assert rows[9].with_candidate_integer == (20, 20) and rows[9].forced_inclusion_change == (
        -0.15, -0.15)
    assert rows[8].with_candidate_integer == (20, 40)  # maximum 35 -> 20, sum 35 -> 40
    assert rows[8].forced_inclusion_change == (-0.15, 0.05)
    assert {row.membership for row in rows.values()} == {"NECESSARY"}
    assert {row.outcome for row in rows.values()} == {"LOWERS_SHORTFALL"}
    for candidate in (strong, partial):
        fact = truth(squad, candidate, requirements, PAIR, 100, "s1")
        assert rows[candidate.player_id].with_candidate_integer == fact["after"]
    assert "The total alone can be higher" in result.groups[0].statement


# ------------------------------------------------------------------ J6: ordering


def ordering_case():
    squad = pair_squad()
    pool = [newcomer(0.9, 21, "Dee"), newcomer(0.31, 22, "abe"), newcomer(0.1, 23, "Cy"),
            newcomer(0.35, 24, "Bea"), newcomer(0.1, 25, "cy"), newcomer(None, 26, "Aa"),
            newcomer(0.05, 27, "Zed")]
    return pool, squad, one_need()


def test_rows_are_grouped_by_outcome_then_by_the_one_declared_key_with_ties_kept():
    pool, squad, requirements = ordering_case()
    result = inject_candidates(pool, squad, requirements, PAIR, slot_id="s1", quantization=100)
    assert (result.order_key, result.ordering.order_key, result.ordering.grouped_by) == (
        "NAME", "NAME", "outcome")
    # Outcome groups in the declared sequence; inside a group names, never the solved value.
    assert [(g.outcome, g.count) for g in result.groups] == [
        ("REMOVES_SHORTFALL", 1), ("LOWERS_SHORTFALL", 2), ("UNCHANGED", 3), ("NOT_EVALUABLE", 1)]
    assert [row.player_id for row in result.rows] == [21, 22, 24, 23, 25, 27, 26]
    lowers = [row for row in result.rows if row.outcome == "LOWERS_SHORTFALL"]
    assert [row.name for row in lowers] == ["abe", "Bea"]
    # ... although the solved values run the other way: the order is not an order of merit.
    assert [row.forced_inclusion_integer for row in lowers] == [(29, 29), (25, 25)]
    unchanged = next(g for g in result.groups if g.outcome == "UNCHANGED")
    assert [(t.order_key_value, t.player_ids) for t in unchanged.tie_groups] == [
        ("cy", (23, 25)), ("zed", (27,))]
    assert result.ordering.statement == (
        "Grouped by the exact outcome of the injected solve, then ordered by name inside each "
        "group. This is not an order of merit. Rows with the same name are tied and listed by "
        "player id.")
    assert result.selection_statement.startswith("7 players were screened")
    assert result.selection_statement in result.non_claim
    assert result.provenance["selection_statement"] == result.selection_statement
    assert result.membership_counts == {
        "NECESSARY": 3, "POSSIBLE": 0, "NOT_POSSIBLE": 4, "UNDETERMINED": 0}
    # The pool-median reference: nearest order statistic of the six available rates, not a player.
    reference = result.pool_median_reference
    assert (reference.player_id, reference.name) == (0, "Pool median (not a player)")
    assert reference.requirement_values == {"need": 0.1} and reference.outcome == "UNCHANGED"
    assert 0 not in {row.player_id for row in result.rows}

    by_value = inject_candidates(pool, squad, requirements, PAIR, slot_id="s1", quantization=100,
                                 order_by="REQUIREMENT_VALUE", order_requirement_id="need",
                                 descending=True)
    unchanged = next(g for g in by_value.groups if g.outcome == "UNCHANGED")
    assert [(t.order_key_value, t.player_ids) for t in unchanged.tie_groups] == [
        (0.1, (23, 25)), (0.05, (27,))]
    assert by_value.ordering.statement == (
        "Grouped by the exact outcome of the injected solve, then ordered by recorded need rate, "
        "descending, inside each group. This is not an order of merit. Rows with the same "
        "recorded need rate are tied and listed by player id.")
    by_age = inject_candidates(pool, squad, requirements, PAIR, slot_id="s1", quantization=100,
                               order_by="AGE", ages={23: 30, 25: None, 27: 24})
    unchanged = next(g for g in by_age.groups if g.outcome == "UNCHANGED")
    assert [(t.order_key_value, t.player_ids) for t in unchanged.tie_groups] == [
        (24, (27,)), (30, (23,)), (None, (25,))]  # an unavailable key is last, never zero
    # Row facts are the same under every key; only the key value and the position change.
    assert {r.player_id: facts_of(r) for r in by_age.rows} == {
        r.player_id: facts_of(r) for r in result.rows}
    for rows in (result.rows, by_value.rows, by_age.rows):
        groups = [OUTCOME_GROUPS.index(row.outcome) for row in rows]
        assert groups == sorted(groups)
    # No position number anywhere: a tie is a set of ids, an order is a sequence.
    fields = {f.name for cls in (injection.InjectionRow, injection.TieGroup, injection.OutcomeGroup,
                                 injection.BulkInjectionResult, injection.OrderingStatement)
              for f in dataclasses.fields(cls)}
    assert fields.isdisjoint({"tie_group", "position", "ordinal", "place", "number", "order"})


@pytest.mark.parametrize("options", [
    {"order_by": "FORCED_INCLUSION_OBJECTIVE"},
    {"order_by": "MEMBERSHIP"},
    {"order_by": "WORLD_COUNT"},
    {"order_by": "REQUIREMENT_VALUE"},
    {"order_by": "REQUIREMENT_VALUE", "order_requirement_id": "absent"},
    {"order_by": "NAME", "order_requirement_id": "need"},
    {"order_by": "AGE"},
    {"descending": 1},
    {"locked": (21,)},
    {"excluded": (21,)},
    {"slot_id": "nowhere"},
    {"time_limit": 0},
    {"squad_worlds": {0: {}}},
    {"squad_worlds": {0: {}}, "pool_worlds": {0: {}}},
    {"squad_worlds": {0: {}}, "pool_worlds": {1: {}}, "world_namespace": "n"},
    {"quantization": 0},
])
def test_undeclared_keys_and_inconsistent_declarations_are_refused(options):
    pool, squad, requirements = ordering_case()
    with pytest.raises(ValueError):
        inject_candidates(pool, squad, requirements, PAIR,
                          **{"slot_id": "s1", "quantization": 100, **options})


def test_pool_identity_rules_are_refused_before_any_solve():
    pool, squad, requirements = ordering_case()
    for bad in ([newcomer(0.2, 1)], [newcomer(0.2, 21), newcomer(0.3, 21)], [newcomer(0.2, 0)],
                [replace(newcomer(0.2), eligible_slots=None)],
                [replace(newcomer(0.2), eligible_slots=("s2",))]):
        with pytest.raises(ValueError):
            inject_candidates(bad, squad, requirements, PAIR, slot_id="s1")
    hard = [replace(requirements[0], hard=True)]
    with pytest.raises(ValueError):
        inject_candidates(pool, squad, hard, PAIR, slot_id="s1")
    empty = inject_candidates([], squad, requirements, PAIR, slot_id="s1", quantization=100)
    assert empty.rows == () and empty.pool_median_reference is None and empty.screened_count == 0


# ------------------------------------------------------------ J7: one world


def test_one_world_equal_to_the_point_values_lands_in_the_cell_the_point_solve_implies():
    pool, squad, requirements = ordering_case()
    squad_worlds = {7: {p.player_id: dict(p.values) for p in squad}}
    pool_worlds = {7: {p.player_id: dict(p.values) for p in pool}}
    result = inject_candidates(pool, squad, requirements, PAIR, slot_id="s1", quantization=100,
                               squad_worlds=squad_worlds, pool_worlds=pool_worlds,
                               world_namespace="point")
    cells = set()
    for row in result.rows:
        counts = row.world_counts
        if row.outcome == "NOT_EVALUABLE":
            assert counts is None
            continue
        cell = (counts.forced_lower, counts.forced_equal, counts.forced_higher)
        assert cell == (row.necessary, row.possible and not row.necessary, not row.possible)
        assert counts.used == 1 and counts.discarded == () and counts.incomplete == ()
        # Worded as a named denial, the only form the page copy guard admits.
        assert counts.interpretation == (
            "Conditional algorithm stability across resampled matches; not a probability")
        cells.add(cell)
    assert cells == {(1, 0, 0), (0, 0, 1)}
    assert result.pool_median_reference.world_counts is None


# ------------------------------------------------------- J2: the shipped function


def test_the_injected_optimum_and_membership_equal_the_shipped_candidate_injection():
    compared = 0
    for number, (squad, pool, requirements, scale, slot_id, declared, _) in instances(count=12):
        result = inject_candidates(pool, squad, requirements, SHAPE, slot_id=slot_id,
                                   quantization=scale, **declared)
        for row in result.rows[:2]:
            candidate = next(c for c in pool if c.player_id == row.player_id)
            shipped = candidate_injection(candidate, squad, requirements, SHAPE, quantization=scale,
                                          analyze_ties=True, **declared)["after"]
            if shipped["solution_status"] != "OPTIMAL":
                assert row.with_candidate_integer is None, number
                continue
            assert row.with_candidate_integer == tuple(
                round(v * scale) for v in shipped["objective_vector"]), number
            facts = shipped["equivalent_players"][row.player_id]
            assert (row.possible, row.necessary) == (facts["possible"], facts["necessary"]), number
            compared += 1
    assert compared >= 12


# ----------------------------------------------------------------- J10: deadlines


def override_status(monkeypatch, on_call, status):
    """The shipped device: the n-th solver call reports a chosen status."""
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


def test_an_undecided_solve_is_undetermined_and_never_not_possible(monkeypatch):
    squad = pair_squad()
    weak = newcomer(0.1)
    # Baseline: three solves. The candidate's forced value: calls four to six.
    for on_call in (4, 5, 6):
        with monkeypatch.context() as patch:
            override_status(patch, on_call, cp_model.UNKNOWN)
            row, result = only_row(weak, squad, one_need())
        assert (row.resolution, row.outcome, row.membership) == (
            "UNCERTIFIED", "UNDETERMINED", "UNDETERMINED"), on_call
        assert (row.possible, row.necessary, row.with_candidate_objective) == (None, None, None)
        assert result.certificate.completeness == "DEADLINE"
        assert result.membership_counts["UNDETERMINED"] == 1
        assert result.warnings == (
            "1 candidates were not resolved within 60 s. Undetermined is not 'not possible'.",)
    # An unproven baseline decides nothing for anyone who could be placed.
    with monkeypatch.context() as patch:
        override_status(patch, 2, cp_model.UNKNOWN)
        result = inject_candidates([weak, newcomer(None, 10, "Gap")], squad, one_need(), PAIR,
                                   slot_id="s1", quantization=100)
    assert result.certificate.baseline_status == "UNKNOWN" and result.baseline_objective is None
    assert [(r.player_id, r.outcome, r.forced_status) for r in result.rows] == [
        (10, "NOT_EVALUABLE", "NOT_RUN"), (9, "UNDETERMINED", "NOT_RUN")]
    assert "No candidate fact is implied." in result.warnings[0]
    # Saturated baseline (one solve). The zero-shortfall solve with him forced in is call two:
    # proved infeasible, it already shows he is in no least-shortfall XI, whatever follows.
    with monkeypatch.context() as patch:
        override_status(patch, 3, cp_model.UNKNOWN)
        row, result = only_row(newcomer(0.05), squad, one_need(0.5))
    assert (row.membership, row.shortcut, row.forced_status, row.forced_inclusion_objective) == (
        "NOT_POSSIBLE", "SATURATED_BASELINE", "UNKNOWN", None)
    assert row.with_candidate_objective == (0.0, 0.0) and row.outcome == "UNCHANGED"
    with monkeypatch.context() as patch:
        override_status(patch, 2, cp_model.UNKNOWN)
        row, _ = only_row(newcomer(0.05), squad, one_need(0.5))
    assert (row.membership, row.shortcut) == ("UNDETERMINED", "NONE")
    # No time left after the first clock reading: nothing is solved, nothing is concluded.
    calls = override_status(monkeypatch, 0, cp_model.UNKNOWN)
    clock = iter([0.0])
    monkeypatch.setattr(injection.time, "monotonic", lambda: next(clock, 5.0))
    row, result = only_row(weak, squad, one_need(), time_limit=1.0)
    assert calls == [] and result.certificate.solves == 0
    assert (row.outcome, result.certificate.completeness) == ("UNDETERMINED", "DEADLINE")
    clock = iter([0.0])
    detail = injection_detail(weak, squad, one_need(), PAIR, slot_id="s1", quantization=100,
                              time_limit=1.0)
    assert detail.no_longer_possible_ids == () and "stated only when" in detail.tie_statement
    assert detail.certificate.completeness == "DEADLINE" and calls == []


# ------------------------------------------------- J9, provenance, fingerprints


def test_results_carry_no_merit_key_no_prior_certificate_and_a_canonical_fingerprint(thesis_guard):
    pool, squad, requirements = ordering_case()
    lineage = {"dataset_hash": "abc", "providers": ["pappalardo"], "universe_fingerprint": "u1",
               "objective_vector": [0.0, 0.0], "selection_frequencies": [], "bootstrap_worlds": 40,
               "solver_status": "OPTIMAL", "bootstrap_version": "v1"}
    options = dict(slot_id="s1", quantization=100, provenance=lineage)
    result = inject_candidates(pool, squad, requirements, PAIR, **options)
    detail = injection_detail(pool[0], squad, requirements, PAIR, **options)
    for payload in (asdict(result), asdict(detail)):
        thesis_guard(payload)
    for provenance in (result.provenance, detail.provenance):
        assert provenance["providers"] == ["pappalardo"] and provenance["dataset_hash"] == "abc"
        assert (provenance["universe_fingerprint"], provenance["bootstrap_version"]) == (
            "u1", "v1")
        assert not {"objective_vector", "selection_frequencies", "bootstrap_worlds",
                    "solver_status"} & set(provenance)
        assert provenance["carry_over"] == "other club, untested"
    assert result.evidence["composed"] == "HEURISTIC" and result.evidence["declared_inputs"]
    assert result.certificate.shortfall_policy == engine.SHORTFALL_POLICY

    def print_of(pool=pool, squad=squad, requirements=requirements, **changed):
        return inject_candidates(pool, squad, requirements, PAIR, **{**options, **changed})

    same = print_of(pool=list(reversed(pool)), squad=list(reversed(squad)))
    assert same.provenance["input_fingerprint"] == result.provenance["input_fingerprint"]
    assert [facts_of(r) for r in same.rows] == [facts_of(r) for r in result.rows]
    changed = [print_of(pool=pool[:-1]), print_of(excluded=(2,)), print_of(order_by="MINUTES"),
               print_of(quantization=1000), print_of(requirements=one_need(0.9)),
               print_of(provenance={**lineage, "dataset_hash": "other"})]
    prints = {r.provenance["input_fingerprint"] for r in changed}
    assert len(prints) == len(changed) and result.provenance["input_fingerprint"] not in prints
    # A row's identity ignores who else was screened and the ordering, not the declarations.
    row_print = {r.player_id: r.input_fingerprint for r in result.rows}
    assert {r.player_id: r.input_fingerprint for r in changed[0].rows}.items() <= row_print.items()
    assert {r.player_id: r.input_fingerprint for r in changed[2].rows} == row_print
    assert {r.player_id: r.input_fingerprint for r in changed[1].rows}[21] != row_print[21]


# ------------------------------------------------------------------- real scenario


@pytest.mark.slow
def test_madrid_default_scenario_is_saturated_and_a_declared_deficiency_is_not(corpus_root):
    from galactico.api.decision_lab import decision_inputs
    from galactico.optimization.historical import load_snapshot

    squad, requirements = decision_inputs(load_snapshot(2565907, worlds=0), "4-3-3")
    pool = [
        Candidate(900001, "Zero", "FW", dict.fromkeys(
            ("progression", "left_pass_origins", "right_pass_origins"), 0.0), 900, ("lw",)),
        Candidate(900002, "Copy", "FW", dict(next(p for p in squad if p.player_id == 3322).values),
                  2000, ("lw",)),
    ]
    result = inject_candidates(pool, squad, requirements, "4-3-3", slot_id="lw")
    # Spec 10.3: the default scenario's least shortfall is (0, 0); no addition can lower zero.
    assert result.certificate.baseline_integer == (0, 0) and result.warnings == (SATURATED_WARNING,)
    assert {row.outcome for row in result.rows} == {"UNCHANGED"}
    assert not {row.membership for row in result.rows} & {"NECESSARY", "UNDETERMINED"}
    assert result.certificate.completeness == "EXACT"
    for candidate in pool:
        shipped = candidate_injection(candidate, squad, requirements, "4-3-3")["after"]
        row = next(r for r in result.rows if r.player_id == candidate.player_id)
        facts = shipped["equivalent_players"][candidate.player_id]
        assert row.with_candidate_objective == tuple(shipped["objective_vector"]) == (0.0, 0.0)
        assert (row.possible, row.necessary) == (facts["possible"], facts["necessary"])
    # A declared deficiency: the two players whose single removal leaves a positive shortfall.
    short = inject_candidates(pool, squad, requirements, "4-3-3", slot_id="lw", excluded=(3310,))
    assert short.certificate.baseline_integer == (12709, 19483)
    for row in short.rows:
        assert row.with_candidate_integer <= (12709, 19483)
        assert row.with_candidate_integer[0] <= 12709


# ------------------------------------------- review: what a deadline leaves open stays open


def test_a_forced_value_the_deadline_cut_off_is_not_certified_as_complete(monkeypatch):
    """The first stage alone can prove "in no least-shortfall XI"; the value is still missing."""
    squad = pair_squad()
    with monkeypatch.context() as patch:
        override_status(patch, 3, cp_model.UNKNOWN)
        row, result = only_row(newcomer(0.05), squad, one_need(0.5))
    assert (row.membership, row.resolution, row.forced_status, row.forced_inclusion_integer) == (
        "NOT_POSSIBLE", "SOLVED", "UNKNOWN", None)
    assert result.certificate.completeness == "DEADLINE"
    assert result.warnings == (
        SATURATED_WARNING,
        "1 forced-inclusion values were not computed within 60 s. Whether those candidates are "
        "in a least-shortfall XI was still proved; no value is implied.",
    )
    with monkeypatch.context() as patch:
        override_status(patch, 3, cp_model.UNKNOWN)
        detail = detail_of(newcomer(0.05), squad, one_need(0.5))
    assert (detail.row.membership, detail.row.forced_status) == ("NOT_POSSIBLE", "UNKNOWN")
    assert detail.requirement_ranges[0].least_shortfall is None
    assert detail.certificate.completeness == "DEADLINE"
    assert detail.warnings[-1].startswith("Some facts were not resolved within 30 s.")
    # The pool-median reference is held to the same rule as a row.
    with monkeypatch.context() as patch:
        override_status(patch, 6, cp_model.UNKNOWN)
        row, result = only_row(newcomer(0.05), squad, one_need(0.5))
    assert (row.forced_status, result.pool_median_reference.forced_status) == (
        "CERTIFIED", "UNKNOWN")
    assert result.pool_median_reference.membership == "NOT_POSSIBLE"
    assert result.certificate.completeness == "DEADLINE"


def test_who_is_forced_out_is_read_off_proved_memberships_never_off_an_open_row(monkeypatch):
    """His forced value is undecided, yet the squad plus him was solved and he is in an XI."""
    squad = pair_squad()
    for on_call in (4, 5, 6):
        with monkeypatch.context() as patch:
            override_status(patch, on_call, cp_model.UNKNOWN)
            detail = detail_of(newcomer(0.3), squad, one_need())
        assert (detail.row.membership, detail.row.possible) == ("UNDETERMINED", None), on_call
        together = detail.squad_membership_with_candidate
        assert (together[1].possible, together[1].necessary) == (True, False), on_call
        assert detail.no_longer_possible_ids == ()
        assert "is in no least-shortfall XI" not in detail.tie_statement, on_call
        assert detail.tie_statement == (
            "No squad player is forced out: every player who is in a least-shortfall XI without "
            "New is still in one with him available.")
        assert detail.certificate.completeness == "DEADLINE"
        assert "of undetermined membership" in detail.claim


def test_a_world_that_was_not_decided_or_has_no_xi_is_counted_in_no_cell(monkeypatch):
    squad = pair_squad()
    worlds = dict(squad_worlds={0: {p.player_id: dict(p.values) for p in squad}},
                  pool_worlds={0: {9: {"r": 0.31}}}, world_namespace="n")
    # Point solves: baseline 1-3, forced 4-6. World 0: baseline 7-9, forced 10-12.
    for on_call in (8, 11):
        with monkeypatch.context() as patch:
            override_status(patch, on_call, cp_model.UNKNOWN)
            row, result = only_row(newcomer(0.31), squad, one_need(), **worlds)
        counts = row.world_counts
        assert row.membership == "NECESSARY", on_call  # the point solve is untouched
        assert (counts.used, counts.forced_lower, counts.forced_equal, counts.forced_higher) == (
            0, 0, 0, 0), on_call
        assert counts.incomplete == ({"world_id": 0, "status": "UNKNOWN"},), on_call
        assert result.certificate.completeness == "DEADLINE", on_call
    # No XI without him in that world: a proved fact, recorded, and in no cell either.
    row, result = only_row(newcomer(0.31), squad, one_need(), excluded=(1,), **worlds)
    counts = row.world_counts
    assert (row.outcome, counts.used, counts.requested) == ("MAKES_FIELDABLE", 0, 1)
    assert counts.incomplete == ({"world_id": 0, "status": "UNFIELDABLE"},)
    assert result.certificate.completeness == "EXACT"


# ----------------------------------- review: identity of a row, and numbers in sentences


def test_a_row_fingerprint_covers_his_own_world_values_and_nobody_elses():
    squad = pair_squad()
    squad_worlds = {0: {p.player_id: dict(p.values) for p in squad}}
    pool = [newcomer(0.31), newcomer(0.2, 10, "Other")]

    def rows(own, other, pool=pool):
        result = inject_candidates(
            pool, squad, one_need(), PAIR, slot_id="s1", quantization=100,
            squad_worlds=squad_worlds, pool_worlds={0: {9: {"r": own}, 10: {"r": other}}},
            world_namespace="n")
        return {row.player_id: row for row in result.rows}

    first, second, third = rows(0.31, 0.2), rows(0.01, 0.2), rows(0.31, 0.9)
    assert first[9].world_counts.forced_lower == 1 and second[9].world_counts.forced_higher == 1
    # Different inputs, different facts: the identity must differ too.
    assert first[9].input_fingerprint != second[9].input_fingerprint
    # ... and still ignores who else was screened and what their worlds were.
    assert first[9].input_fingerprint == third[9].input_fingerprint
    assert first[9].input_fingerprint == rows(0.31, 0.2, pool[:1])[9].input_fingerprint
    assert first[10].input_fingerprint == second[10].input_fingerprint
    without = inject_candidates(pool, squad, one_need(), PAIR, slot_id="s1", quantization=100)
    assert without.rows[0].world_counts is None


def test_world_counts_name_the_namespace_each_side_was_drawn_in():
    """The universe resamples leagues independently: one namespace string cannot label both."""
    squad = pair_squad()
    pool = [newcomer(0.31), newcomer(0.2, 10, "Abroad")]
    worlds = dict(squad_worlds={0: {p.player_id: dict(p.values) for p in squad}},
                  pool_worlds={0: {9: {"r": 0.31}, 10: {"r": 0.2}}}, world_namespace="home")
    options = dict(slot_id="s1", quantization=100, **worlds)
    mixed = inject_candidates(pool, squad, one_need(), PAIR, pool_world_namespaces={10: "away"},
                              **options)
    plain = inject_candidates(pool, squad, one_need(), PAIR, **options)
    rows = {row.player_id: row for row in mixed.rows}
    before = {row.player_id: row for row in plain.rows}
    home, away = rows[9].world_counts, rows[10].world_counts
    assert (home.namespace, home.candidate_namespace) == ("home", "home")
    assert (away.namespace, away.candidate_namespace) == ("home", "away")
    assert home.namespace_statement == (
        "Squad and candidate values in a world come from one resample of the same matches.")
    assert away.namespace_statement == (
        "The candidate's values come from a separate resample of other matches (namespace "
        "away); a world pairs two independent draws.")
    assert before[10].world_counts.candidate_namespace == "home"
    # The declaration is an input: it moves his identity and the result's, nobody else's.
    assert rows[10].input_fingerprint != before[10].input_fingerprint
    assert rows[9] == before[9]
    assert mixed.provenance["input_fingerprint"] != plain.provenance["input_fingerprint"]
    detail = injection_detail(pool[1], squad, one_need(), PAIR, time_limit=60.0,
                              candidate_world_namespace="away", squad_worlds=worlds["squad_worlds"],
                              candidate_worlds=worlds["pool_worlds"], world_namespace="home",
                              slot_id="s1", quantization=100)
    assert facts_of(detail.row) == facts_of(rows[10])
    for refused in ({"pool_world_namespaces": {10: ""}}, {"pool_world_namespaces": {10: 7}}):
        with pytest.raises(ValueError):
            inject_candidates(pool, squad, one_need(), PAIR, **options, **refused)
    with pytest.raises(ValueError):  # a namespace without worlds names nothing
        inject_candidates(pool, squad, one_need(), PAIR, slot_id="s1", quantization=100,
                          pool_world_namespaces={10: "away"})
    with pytest.raises(ValueError):
        injection_detail(pool[1], squad, one_need(), PAIR, slot_id="s1", quantization=100,
                         candidate_world_namespace="away")


def test_sentences_print_the_certified_integers_exactly_and_name_an_unplaceable_candidate():
    squad = [Candidate(1, "Ann", "X", {"r": 0.1234567}, 900, ("s1",)),
             Candidate(2, "Bo", "X", {"r": 0.4}, 900, ("s2",))]
    options = dict(slot_id="s1", quantization=10**7)
    result = inject_candidates([newcomer(0.1)], squad, one_need(), PAIR, **options)
    assert result.certificate.baseline_integer == (4765433, 4765433)
    assert "(maximum 0.4765433, sum 0.4765433)" in result.claim
    detail = injection_detail(newcomer(0.2234567), squad, one_need(), PAIR, **options)
    assert detail.row.forced_inclusion_integer == (3765433, 3765433)
    assert detail.claim.startswith(
        "With New placed at s1, the least declared shortfall is (maximum 0.3765433, sum "
        "0.3765433); without him it is (maximum 0.4765433, sum 0.4765433).")
    # A candidate the model cannot place has no forced value by proof, not by a deadline.
    detail = detail_of(newcomer(None), pair_squad(), one_need())
    assert (detail.row.outcome, detail.certificate.completeness, detail.warnings) == (
        "NOT_EVALUABLE", "EXACT", ())
    assert "not determined" not in detail.claim
    assert detail.claim == (
        "With New placed at s1, the least declared shortfall is not defined (the model cannot "
        "place him at this slot); without him it is (maximum 0.3, sum 0.3). In the squad plus "
        "him he is in no least-shortfall XI.")
