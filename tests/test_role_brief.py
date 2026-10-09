"""The role brief against an oracle written from the problem statement.

The oracle enumerates player permutations with ``itertools`` and forms every integer with
``fractions.Fraction`` floor and ceil. It imports the domain dataclasses only: no helper of
``squad.brief``, ``squad.kernel``, ``xi.solver`` or ``xi.tradeoffs``. The solver side is Boolean
assignment variables with linear constraints, so the two share no model and no rounding helper.
"""

from __future__ import annotations

import itertools
import math
import random
import re
from dataclasses import asdict, replace
from fractions import Fraction
from types import SimpleNamespace

import pytest
from ortools.sat.python import cp_model

from galactico.optimization.squad import brief as module
from galactico.optimization.squad import kernel as engine
from galactico.optimization.squad.brief import (
    INCOMPLETE_WARNING,
    BriefRow,
    meets_row,
    role_brief,
)
from galactico.optimization.xi.domain import Candidate, Formation, Slot, TacticalRequirement

TERMINAL = {"NO_NEED", "BRIEF", "NOT_ADDRESSABLE_AT_SLOT", "RESIDUAL_UNFIELDABLE"}


# --------------------------------------------------------------------------- oracle


def applies(requirement, slot_id):
    return not requirement.slot_ids or slot_id in requirement.slot_ids


def can_play(player, slot, active):
    if player.minutes <= 0 or player.position not in slot.allowed_positions:
        return False
    if player.eligible_slots is not None and slot.slot_id not in player.eligible_slots:
        return False
    return all(
        player.values.get(r.metric) is not None for r in active if applies(r, slot.slot_id)
    )


def unit(value, requirement, scale):
    return math.floor(Fraction(value) / Fraction(requirement.normalizer) * scale)


def goal(requirement, scale):
    return math.ceil(Fraction(requirement.minimum) / Fraction(requirement.normalizer) * scale)


def lineups(players, slots, active, locked, excluded):
    if set(locked) & set(excluded):
        return
    pool = [p for p in players if p.player_id not in excluded]
    for chosen in itertools.permutations(pool, len(slots)):
        if set(locked) <= {p.player_id for p in chosen} and all(
            can_play(p, s, active) for p, s in zip(chosen, slots, strict=True)
        ):
            yield chosen


def supply(chosen, slots, requirement, scale):
    return sum(
        unit(p.values[requirement.metric], requirement, scale)
        for p, s in zip(chosen, slots, strict=True)
        if applies(requirement, s.slot_id)
    )


def minimal(vectors):
    return {
        a
        for a in vectors
        if not any(b != a and all(x <= y for x, y in zip(b, a, strict=True)) for b in vectors)
    }


def oracle_brief(players, requirements, formation, slot_id, scale, locked=(), excluded=()):
    active = sorted((r for r in requirements if r.active), key=lambda r: r.requirement_id)
    dims = [r for r in active if applies(r, slot_id)]
    fixed = [r for r in active if not applies(r, slot_id)]
    rest = [s for s in formation.slots if s.slot_id != slot_id]
    fieldable, needs = False, set()
    for chosen in lineups(players, rest, active, locked, excluded):
        fieldable = True
        if all(supply(chosen, rest, r, scale) >= goal(r, scale) for r in fixed):
            needs.add(
                tuple(max(0, goal(r, scale) - supply(chosen, rest, r, scale)) for r in dims)
            )
    rows = minimal(needs)
    if not fieldable:
        return "RESIDUAL_UNFIELDABLE", rows
    if not needs:
        return "NOT_ADDRESSABLE_AT_SLOT", rows
    return ("NO_NEED" if rows == {(0,) * len(dims)} else "BRIEF"), rows


def oracle_satisfiable(players, requirements, formation, scale, locked=(), excluded=()):
    active = [r for r in requirements if r.active]
    fieldable = False
    for chosen in lineups(players, formation.slots, active, locked, excluded):
        fieldable = True
        if all(supply(chosen, formation.slots, r, scale) >= goal(r, scale) for r in active):
            return "SATISFIABLE"
    return "NOT_SATISFIABLE" if fieldable else "UNFIELDABLE"


def oracle_meets(players, addition, requirements, formation, slot_id, scale, locked, excluded):
    """Full enumeration with the addition fixed at the slot, in conservative integers."""
    active = [r for r in requirements if r.active]
    slot = next(s for s in formation.slots if s.slot_id == slot_id)
    rest = [s for s in formation.slots if s.slot_id != slot_id]
    if not can_play(addition, slot, active):
        return False
    for chosen in lineups(players, rest, active, locked, excluded):
        if all(
            supply((*chosen, addition), (*rest, slot), r, scale) >= goal(r, scale)
            for r in active
        ):
            return True
    return False


# ------------------------------------------------------------------------ generator


def draw(rng: random.Random, number: int):
    slot_count = rng.choice((3, 4))
    allowed = (("A",), ("A", "B"), ("B",), ("A", "B"))
    slots = tuple(
        Slot(f"s{i}", f"Slot {i}", allowed[i], 0.2 * i, 0.5) for i in range(slot_count)
    )
    formation = Formation("toy", slots)
    slot_id = rng.choice(slots).slot_id
    others = [s.slot_id for s in slots if s.slot_id != slot_id]
    metrics = ("m0", "m1", "m2")[: rng.choice((2, 3))]
    scale = rng.choice((3, 8, 100_000))
    regime = rng.choice(("low", "middle", "middle", "high"))
    factor = {"low": (0.2, 0.5), "middle": (0.8, 1.3), "high": (1.3, 1.9)}[regime]
    requirements = []
    for i, metric in enumerate(metrics):
        if i == 0 and number % 3 == 0:  # one requirement that does not count the brief slot
            slot_ids = tuple(rng.sample(others, rng.randint(1, len(others))))
        else:
            chosen = [sid for sid in others if rng.random() < 0.6]
            slot_ids = () if len(chosen) == len(others) else (slot_id, *chosen)
        counted = len(slot_ids) or slot_count
        requirements.append(
            TacticalRequirement(
                f"need_{metric}", metric.upper(), metric,
                0.5 * counted * rng.uniform(*factor), rng.choice((0.5, 1.0, 2.0)),
                slot_ids, "MEASURED",
            )
        )
    players = []
    for pid in range(1, 7):
        eligible = None
        if rng.random() < 0.5:
            eligible = tuple(s.slot_id for s in slots if rng.random() < 0.8)
        values = {m: None if rng.random() < 0.06 else rng.uniform(0.0, 1.0) for m in metrics}
        players.append(Candidate(pid, f"P{pid}", rng.choice("AB"), values, 1000, eligible))
    locked = (rng.randint(1, 6),) if number % 5 == 0 else ()
    excluded = (rng.choice([p for p in range(1, 7) if p not in locked]),) if number % 4 == 0 else ()
    members = tuple(
        SimpleNamespace(
            player_id=100 + k, name=f"U{k}", provider_position=rng.choice("AB"), minutes=900 + k,
            values={m: None if rng.random() < 0.1 else rng.uniform(0.0, 1.4) for m in metrics},
        )
        for k in range(8)
    )
    universe = SimpleNamespace(
        candidates=members, provenance={"input_fingerprint": f"synthetic-{number}"}
    )
    return players, requirements, formation, slot_id, scale, locked, excluded, universe


def vectors(result):
    return {row.need_integer for row in result.rows}


def check_witnesses(result, players, requirements, formation, scale, locked, excluded):
    """B3, in the test's own exact arithmetic."""
    by_id = {p.player_id: p for p in players}
    reqs = {r.requirement_id: r for r in requirements}
    active = [r for r in requirements if r.active]
    rest = [s for s in formation.slots if s.slot_id != result.slot_id]
    for row in result.rows:
        assert row.certification == "MINIMAL_CERTIFIED"
        assert [sid for sid, _ in row.residual_lineup] == [s.slot_id for s in rest]
        chosen = [by_id[pid] for _, pid in row.residual_lineup]
        assert len({p.player_id for p in chosen}) == len(chosen)
        assert set(locked) <= {p.player_id for p in chosen}
        assert not {p.player_id for p in chosen} & set(excluded)
        assert all(can_play(p, s, active) for p, s in zip(chosen, rest, strict=True))

        def raw(requirement, chosen=chosen):
            return sum(
                (Fraction(p.values[requirement.metric])
                 for p, s in zip(chosen, rest, strict=True) if applies(requirement, s.slot_id)),
                Fraction(),
            )

        for k, rid in enumerate(result.dimensions):
            r = reqs[rid]
            threshold = Fraction(row.need_integer[k], scale) * Fraction(r.normalizer)
            assert raw(r) + threshold >= Fraction(r.minimum)
            assert row.residual_supply[k] == float(raw(r))
            # The printed need is sufficient and is the least float that is.
            assert Fraction(row.need[k]) >= threshold
            assert row.need[k] == 0.0 or Fraction(math.nextafter(row.need[k], 0.0)) < threshold
        for rid in result.fixed_floor_requirements:
            assert raw(reqs[rid]) >= Fraction(reqs[rid].minimum)


# ------------------------------------------------------------------ B1-B4, B7 seeded


def test_brief_equals_the_oracle_on_seeded_instances():
    rng = random.Random(20261013)
    statuses, baselines, widest = set(), set(), 0
    mixed = satisfiable_with_rows = unmeasured_addition = reversed_order = 0
    for number in range(120):
        players, requirements, formation, slot_id, scale, locked, excluded, universe = draw(
            rng, number)
        result = role_brief(players, requirements, formation, slot_id=slot_id, locked=locked,
                            excluded=excluded, universe=universe, quantization=scale)
        status, rows = oracle_brief(
            players, requirements, formation, slot_id, scale, locked, excluded)
        context = (number, slot_id, scale)
        assert result.status == status, context
        assert vectors(result) == rows and len(result.rows) == len(rows), context
        assert [r.need_integer for r in result.rows] == sorted(rows), context
        assert result.squad_satisfiable_without_addition == oracle_satisfiable(
            players, requirements, formation, scale, locked, excluded), context
        certificate = result.certificate
        assert certificate.completeness == "COMPLETE" and certificate.rows == len(rows)
        assert certificate.pairwise_incomparable and certificate.witnesses_verified
        assert certificate.final_region_status in ("INFEASIBLE", "INFEASIBLE_BY_CONSTRUCTION")
        assert (certificate.quantization, certificate.hard_policy) == (scale, engine.HARD_POLICY)
        check_witnesses(result, players, requirements, formation, scale, locked, excluded)

        # B4: the count is the solves, the solves are the oracle, and the row test agrees.
        slot = next(s for s in formation.slots if s.slot_id == slot_id)
        additions = [
            Candidate(u.player_id, u.name, u.provider_position, u.values, u.minutes, (slot_id,))
            for u in universe.candidates if u.provider_position in slot.allowed_positions
        ]
        truth = {
            a.player_id: oracle_meets(
                players, a, requirements, formation, slot_id, scale, locked, excluded)
            for a in additions
        }
        count = result.count
        assert count.method == "INJECTED_SATISFY_SOLVE" and count.admissible == len(additions)
        assert count.meeting_ids == tuple(sorted(pid for pid, met in truth.items() if met))
        assert (count.meeting, count.not_meeting, count.undetermined) == (
            sum(truth.values()), len(truth) - sum(truth.values()), 0), context
        assert count.row_test_agrees is True, context
        for a in additions:
            by_rows = any(
                meets_row(a.values, row, requirements, result.dimensions, scale)
                for row in result.rows)
            assert by_rows == truth[a.player_id], (context, a.player_id)
        # B7: with nothing needed, every admissible addition that is measured meets.
        if status == "NO_NEED":
            measured = [a for a in additions if can_play(a, slot, requirements)]
            assert count.meeting == len(measured)
            unmeasured_addition += len(measured) < len(additions)
        assert result.provenance["universe_fingerprint"] == f"synthetic-{number}"
        assert result.provenance["screened_count"] == len(additions)

        # B2: neither input order is part of the answer or of its fingerprint.
        if number % 4 == 1:
            shuffled, reordered = players[:], requirements[:]
            rng.shuffle(shuffled)
            reordered.reverse()
            again = role_brief(shuffled, reordered, formation, slot_id=slot_id, locked=locked,
                               excluded=excluded, universe=universe, quantization=scale)
            assert (again.status, vectors(again), again.count) == (
                result.status, rows, result.count)
            assert again.provenance["input_fingerprint"] == result.provenance["input_fingerprint"]
            # Renaming the requirements reverses the order the dimensions are minimised in:
            # the same rows come back, so that order is a device and not a preference.
            ordered = sorted(requirements, key=lambda r: r.requirement_id)
            flipped = role_brief(
                players,
                [replace(r, requirement_id=f"{9 - i}{r.requirement_id}")
                 for i, r in enumerate(ordered)],
                formation, slot_id=slot_id, locked=locked, excluded=excluded, quantization=scale)
            assert [d[1:] for d in flipped.dimensions] == list(result.dimensions)[::-1]
            assert {v[::-1] for v in vectors(flipped)} == rows, context
            reversed_order += len(rows) > 1 and len(result.dimensions) > 1

        statuses.add(status)
        baselines.add(result.squad_satisfiable_without_addition)
        widest = max(widest, len(rows))
        mixed += 0 < sum(truth.values()) < len(truth)
        satisfiable_with_rows += (
            status == "BRIEF" and result.squad_satisfiable_without_addition == "SATISFIABLE")
    # Non-vacuity: every outcome and its opposite occurred.
    assert statuses == TERMINAL
    assert baselines == {"SATISFIABLE", "NOT_SATISFIABLE", "UNFIELDABLE"}
    assert widest >= 3 and mixed >= 5 and satisfiable_with_rows >= 1 and unmeasured_addition >= 1
    assert reversed_order >= 3


def test_brief_equals_the_oracle_where_the_first_generator_never_goes():
    """Hard flags, a minimum at or below zero, a requirement that counts the brief slot alone,
    a player with no minutes, one integer unit per whole normalizer, a negative rate on a
    requirement that does not count the slot, a player both locked and excluded, and a row
    limit below and at the true number of rows."""
    rng = random.Random(20261014)
    statuses, features = set(), dict.fromkeys(
        ("hard", "nonpositive_minimum", "slot_alone", "no_minutes", "unit_scale",
         "negative_fixed_rate", "locked_and_excluded", "row_limit", "ties"), 0)
    for number in range(90):
        slots = tuple(
            Slot(f"s{i}", f"Slot {i}", (("A",), ("A", "B"), ("B",), ("A", "B"))[i], 0.2 * i, 0.5)
            for i in range(rng.choice((2, 3, 4))))
        formation = Formation("toy", slots)
        slot_id = rng.choice(slots).slot_id
        others = [s.slot_id for s in slots if s.slot_id != slot_id]
        metrics = ("m0", "m1", "m2")[: rng.choice((2, 3))]
        scale = rng.choice((1, 2, 8, 100_000))
        eighths = number % 2 == 0  # values on a grid: equal sums and exact boundaries occur
        requirements = []
        for metric in metrics:
            kind = rng.random()
            if kind < 0.25:
                slot_ids = tuple(rng.sample(others, rng.randint(1, len(others))))
            elif kind < 0.4:
                slot_ids = (slot_id,)
            else:
                slot_ids = (slot_id, *(sid for sid in others if rng.random() < 0.6))
                slot_ids = () if len(slot_ids) == len(slots) else slot_ids
            factor = rng.choice(((0.2, 0.5), (0.7, 1.2), (0.7, 1.2), (1.2, 1.8), (-0.5, 0.0)))
            minimum = 0.5 * (len(slot_ids) or len(slots)) * rng.uniform(*factor)
            requirements.append(TacticalRequirement(
                f"need_{metric}", metric.upper(), metric,
                round(minimum * 8) / 8 if eighths else minimum,
                rng.choice((0.5, 1.0, 2.0) if eighths else (0.3, 1.0, 3.7)),
                slot_ids, "MEASURED", hard=rng.random() < 0.3))
        dimension_metrics = {r.metric for r in requirements if applies(r, slot_id)}
        players = []
        for pid in range(1, 7):
            eligible = None
            if rng.random() < 0.5:
                eligible = tuple(s.slot_id for s in slots if rng.random() < 0.75)
            values = {}
            for metric in metrics:
                value = rng.randint(0, 8) / 8 if eighths else rng.uniform(0.0, 1.0)
                if metric not in dimension_metrics and rng.random() < 0.25:
                    value = -value
                values[metric] = None if rng.random() < 0.05 else value
            players.append(Candidate(pid, f"P{pid}", rng.choice("AB"), values,
                                     0 if rng.random() < 0.05 else 1000, eligible))
        locked = tuple(rng.sample(range(1, 7), rng.choice((0, 0, 0, 1, 2))))
        excluded = tuple(rng.sample(range(1, 7), rng.choice((0, 0, 1, 2))))
        universe = [
            Candidate(100 + k, f"U{k}", rng.choice(slot_of.allowed_positions),
                      {m: rng.randint(0, 10) / 8 if eighths else rng.uniform(0.0, 1.4)
                       for m in metrics}, 900 + k, (slot_id,))
            for slot_of in (next(s for s in slots if s.slot_id == slot_id),) for k in range(6)
        ]

        def run(players=players, requirements=requirements, formation=formation,
                slot_id=slot_id, locked=locked, excluded=excluded, scale=scale, **kwargs):
            return role_brief(players, requirements, formation, slot_id=slot_id, locked=locked,
                              excluded=excluded, quantization=scale, **kwargs)

        result = run(universe=universe)
        status, rows = oracle_brief(
            players, requirements, formation, slot_id, scale, locked, excluded)
        context = (number, slot_id, scale)
        assert (result.status, vectors(result)) == (status, rows), context
        assert result.certificate.completeness == "COMPLETE", context
        assert result.squad_satisfiable_without_addition == oracle_satisfiable(
            players, requirements, formation, scale, locked, excluded), context
        check_witnesses(result, players, requirements, formation, scale, locked, excluded)
        truth = {
            a.player_id: oracle_meets(
                players, a, requirements, formation, slot_id, scale, locked, excluded)
            for a in universe
        }
        assert result.count.meeting_ids == tuple(sorted(p for p, met in truth.items() if met))
        assert result.count.row_test_agrees is True, context
        if len(rows) >= 2:
            # Below the true number of rows the brief says so; at it, completeness is proven.
            short = run(max_rows=len(rows) - 1)
            assert (short.status, short.certificate.completeness) == (
                "INCOMPLETE", "LIMIT_REACHED"), context
            assert len(short.rows) == len(rows) - 1 and vectors(short) < rows, context
            assert (run(max_rows=len(rows)).status, vectors(run(max_rows=len(rows)))) == (
                "BRIEF", rows), context
            features["row_limit"] += 1
        statuses.add(status)
        dimensions = [r for r in requirements if applies(r, slot_id)]
        features["hard"] += status == "BRIEF" and any(r.hard for r in dimensions)
        features["nonpositive_minimum"] += bool(rows) and any(r.minimum <= 0 for r in dimensions)
        features["slot_alone"] += bool(rows) and any(r.slot_ids == (slot_id,) for r in dimensions)
        features["no_minutes"] += any(p.minutes == 0 for p in players)
        features["unit_scale"] += scale == 1 and status == "BRIEF"
        features["negative_fixed_rate"] += status != "RESIDUAL_UNFIELDABLE" and any(
            (p.values[r.metric] or 0) < 0 for p in players for r in requirements)
        features["locked_and_excluded"] += bool(set(locked) & set(excluded))
        features["ties"] += eighths and status == "BRIEF" and 0 < sum(truth.values()) < 6
    assert statuses == TERMINAL
    assert all(seen >= 2 for seen in features.values()), features


# ------------------------------------------------------------------- hand-built cases


def toy(*slot_ids, keeper=False):
    slots = tuple(Slot(sid, f"Slot {sid}", ("P",), 0.5, 0.5) for sid in slot_ids)
    if keeper:
        slots = (Slot("g", "Keeper", ("G",), 0.5, 0.9), *slots)
    return Formation("toy", slots)


def man(pid, eligible=None, position="P", **values):
    return Candidate(pid, f"P{pid}", position, values, 1000, eligible)


def need(metric, minimum, slots=(), normalizer=1.0):
    return TacticalRequirement(
        f"need_{metric}", metric.upper(), metric, minimum, normalizer, slots, "MEASURED")


def two_rows():
    """Slot x beside slot y. Two players can only play y and are opposite on a and b; the one
    player who can play x plays nowhere else, so vacating x removes him (the Madrid lb shape).
    Dyadic values: every floor coefficient at scale 100 is exact."""
    squad = [man(1, ("y",), a=0.75, b=0.25), man(2, ("y",), a=0.25, b=0.75),
             man(3, ("x",), a=0.875, b=0.875)]
    return squad, [need("a", 1.0), need("b", 1.0)], toy("x", "y")


def test_two_incomparable_rows_a_candidate_on_a_row_and_one_unit_below_it():
    squad, requirements, formation = two_rows()
    on_first = man(11, ("x",), a=0.25, b=0.75)
    on_second = man(12, ("x",), a=0.75, b=0.25)
    one_unit_below = man(13, ("x",), a=0.25 - 2**-10, b=0.75)  # floor coefficient 24, not 25
    between = man(14, ("x",), a=0.5, b=0.5)
    universe = [between, one_unit_below, on_second, on_first]
    result = role_brief(squad, requirements, formation, slot_id="x", universe=universe,
                        quantization=100)
    assert result.status == "BRIEF" and result.dimensions == ("need_a", "need_b")
    assert [row.need_integer for row in result.rows] == [(25, 75), (75, 25)]
    assert [row.need for row in result.rows] == [(0.25, 0.75), (0.75, 0.25)]
    assert [row.residual_lineup for row in result.rows] == [(("y", 1),), (("y", 2),)]
    assert [row.residual_supply for row in result.rows] == [(0.75, 0.25), (0.25, 0.75)]
    # The squad reaches the minima as it is, and the brief is non-zero all the same.
    assert result.squad_satisfiable_without_addition == "SATISFIABLE"
    assert any("non-zero all the same" in text for text in result.warnings)
    assert "already reachable without any addition" in result.claim
    assert "meet at least one of these 2 rows" in result.claim
    count = result.count
    assert (count.admissible, count.meeting, count.not_meeting, count.undetermined) == (4, 2, 2, 0)
    assert count.meeting_ids == (11, 12) and count.row_test_agrees is True
    assert "2 of the 4 gated players admissible at Slot x in the declared universe make " in (
        result.claim)
    assert result.certificate.final_region_status == "INFEASIBLE"
    assert result.certificate.solves == result.provenance["brief_solver_calls"]["enumeration"] == 5

    # B5. Delete a row: the candidate sitting exactly on it meets by the solve and by no
    # remaining row. Add a dominated row: the incomparability check sees it.
    for kept, sitting in ((result.rows[1:], on_first), (result.rows[:1], on_second)):
        assert sitting.player_id in count.meeting_ids
        assert not any(
            meets_row(sitting.values, row, requirements, result.dimensions, 100) for row in kept)
    assert module._pairwise_incomparable([(25, 75), (75, 25)])
    assert not module._pairwise_incomparable([(25, 75), (75, 25), (80, 80)])
    assert not module._pairwise_incomparable([(25, 75), (25, 75)])

    # A candidate universe object gives the same count; a keeper in it is not admissible at x.
    members = [*((c, "P") for c in universe), (man(15, a=2.0, b=2.0), "G")]
    pool = SimpleNamespace(
        candidates=tuple(
            SimpleNamespace(player_id=c.player_id, name=c.name, provider_position=position,
                            values=c.values, minutes=c.minutes)
            for c, position in members),
        provenance={"input_fingerprint": "pool"})
    pooled = role_brief(squad, requirements, formation, slot_id="x", universe=pool,
                        quantization=100)
    assert pooled.count == count and pooled.provenance["universe_fingerprint"] == "pool"
    assert pooled.provenance["input_fingerprint"] != result.provenance["input_fingerprint"]
    # The adapter is the transfer universe's own rule: same players, same injectable objects.
    from galactico.optimization.transfers.universe import admissible_at, as_injectable

    adapted, _ = module._injectables(pool, formation.slots[0], frozenset(), ("a", "b"))
    assert adapted == sorted(
        (as_injectable(u, "x") for u in admissible_at(pool, formation, "x")),
        key=lambda c: c.player_id)
    assert [c.player_id for c in adapted] == [11, 12, 13, 14]
    with pytest.raises(ValueError, match="provider_position"):
        role_brief(squad, requirements, formation, slot_id="x", quantization=100,
                   universe=SimpleNamespace(candidates=(dict(player_id=11),), provenance={}))

    # (6) max_rows = 1: one certified row, a further one proven to exist, the count still exact.
    limited = role_brief(squad, requirements, formation, slot_id="x", universe=universe,
                         quantization=100, max_rows=1)
    assert (limited.status, limited.certificate.completeness) == ("INCOMPLETE", "LIMIT_REACHED")
    assert limited.certificate.final_region_status == "OPTIMAL"
    assert [row.need_integer for row in limited.rows] == [(25, 75)]
    assert limited.warnings[-1] == INCOMPLETE_WARNING.format(n=1)
    assert (limited.count.meeting, limited.count.meeting_ids) == (2, (11, 12))
    assert limited.count.row_test_agrees is None
    assert "other rows may exist" in limited.claim
    assert "For Slot x: 1 minimal row was found before the limit." in limited.claim
    # A limit equal to the number of rows is not a limit: completeness is still proven.
    exact = role_brief(squad, requirements, formation, slot_id="x", quantization=100, max_rows=2)
    assert (exact.status, exact.certificate.completeness, exact.count) == (
        "BRIEF", "COMPLETE", None)
    assert "universe_fingerprint" not in exact.provenance


def test_the_brief_agrees_with_the_conservative_solve_where_float_arithmetic_would_not():
    third = 1 / 3
    assert third + third + third >= 1.0  # float arithmetic accepts the boundary
    squad = [man(1, ("y",), a=third), man(2, ("z",), a=third)]
    requirements, formation = [need("a", 1.0)], toy("x", "y", "z")
    plain = role_brief(squad, requirements, formation, slot_id="x", quantization=100_000)
    (row,) = plain.rows
    assert row.need_integer == (33334,)  # 100000 - 2 * floor(33333.33)
    assert Fraction(row.need[0]) >= Fraction(33334, 100_000) > Fraction(third)
    universe = [man(11, ("x",), a=third), man(12, ("x",), a=row.need[0])]
    result = role_brief(squad, requirements, formation, slot_id="x", universe=universe,
                        quantization=100_000)
    # The third third does not meet; the printed threshold itself does.
    assert result.count.meeting_ids == (12,) and result.count.row_test_agrees is True
    assert result.squad_satisfiable_without_addition == "UNFIELDABLE"
    assert "not reachable (no XI can be fielded)" in result.claim


def test_a_slot_no_requirement_counts_and_squads_that_cannot_fill_the_other_slots():
    squad = [man(1, position="G", a=0.0), man(2, a=0.5), man(3, a=0.5)]
    formation = toy("x", "y", keeper=True)
    keeper = [man(11, ("g",), position="G")]  # unmeasured on a: no requirement counts g
    met = role_brief(squad, [need("a", 1.0, ("x", "y"))], formation, slot_id="g",
                     universe=keeper, quantization=100)
    assert (met.status, met.dimensions, met.fixed_floor_requirements) == (
        "NO_NEED", (), ("need_a",))
    (row,) = met.rows
    assert (row.need_integer, row.need, row.residual_supply) == ((), (), ())
    assert sorted(pid for _, pid in row.residual_lineup) == [2, 3]
    assert met.count.meeting == met.count.admissible == 1 and met.count.row_test_agrees is True
    assert met.certificate.completeness == "COMPLETE"
    unmet = role_brief(squad, [need("a", 1.5, ("x", "y"))], formation, slot_id="g",
                       universe=keeper, quantization=100)
    assert (unmet.status, unmet.rows, unmet.certificate.completeness) == (
        "NOT_ADDRESSABLE_AT_SLOT", (), "COMPLETE")
    assert (unmet.count.meeting, unmet.count.not_meeting, unmet.count.row_test_agrees) == (
        0, 1, True)
    assert unmet.squad_satisfiable_without_addition == "NOT_SATISFIABLE"
    assert "A does not count this slot and the other slots cannot reach it." in unmet.claim

    # (5) The only player for x is the only player for y: the squad cannot field an XI, an
    # addition at x can, and the row is what the other slot leaves open.
    lone = role_brief([man(1, a=0.75)], [need("a", 1.0)], toy("x", "y"), slot_id="x",
                      quantization=100)
    assert (lone.status, lone.squad_satisfiable_without_addition) == ("BRIEF", "UNFIELDABLE")
    assert [r.need_integer for r in lone.rows] == [(25,)]
    assert "meet this row on every listed requirement" in lone.claim
    # One player for two other slots is a solver proof; an empty slot is a kernel reason.
    hall = role_brief([man(1, a=0.75), man(2, ("x",), a=0.75)], [need("a", 1.0)],
                      toy("x", "y", "z"), slot_id="x", quantization=100)
    assert (hall.status, hall.rows, hall.certificate.final_region_status) == (
        "RESIDUAL_UNFIELDABLE", (), "INFEASIBLE")
    assert hall.certificate.solves == 1 and hall.warnings == ()
    empty = role_brief([man(2, ("x",), a=0.75)], [need("a", 1.0)], toy("x", "y"), slot_id="x",
                       quantization=100)
    assert (empty.status, empty.certificate.final_region_status, empty.certificate.solves) == (
        "RESIDUAL_UNFIELDABLE", "INFEASIBLE_BY_CONSTRUCTION", 0)
    assert empty.warnings == ("No eligible measured candidate for Slot y (y).",)
    assert "one addition at this slot does not make an XI fieldable" in empty.claim


def test_raising_the_minima_never_shrinks_a_need():
    squad = [man(1, a=0.75, c=0.5), man(2, a=0.25, c=1.0), man(3, a=0.5, c=0.25),
             man(4, a=1.0, c=0.125)]
    formation = toy("x", "y", "z")
    base = [need("a", 1.0), need("c", 0.5, ("y", "z"))]
    seen, previous, strict = [], None, False
    for multiplier in (0.5, 1.0, 1.5, 2.0, 2.5, 4.0):
        requirements = [replace(r, minimum=r.minimum * multiplier) for r in base]
        result = role_brief(squad, requirements, formation, slot_id="x", quantization=100)
        status, rows = oracle_brief(squad, requirements, formation, "x", 100)
        assert (result.status, vectors(result)) == (status, rows)
        seen.append(result.status)
        if previous is not None and rows:
            assert all(
                any(all(o <= n for o, n in zip(old, new, strict=True)) for old in previous)
                for new in rows)
            strict = strict or rows != previous
        previous = rows or previous
    order = ["NO_NEED", "BRIEF", "NOT_ADDRESSABLE_AT_SLOT"]
    assert strict and seen == sorted(seen, key=order.index) and set(seen) == set(order)


# -------------------------------------------------------- B8: deadlines and UNKNOWN


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


def undecided_cases():
    squad, requirements, formation = two_rows()
    universe = [man(11, ("x",), a=0.25, b=0.75), man(14, ("x",), a=0.5, b=0.5)]
    yield squad, requirements, formation, "x", universe
    # NOT_ADDRESSABLE_AT_SLOT, then a solver-proven RESIDUAL_UNFIELDABLE.
    yield ([man(1, position="G", a=0.0), man(2, a=0.5), man(3, a=0.5)],
           [need("a", 1.5, ("x", "y"))], toy("x", "y", keeper=True), "g",
           [man(11, ("g",), position="G")])
    yield ([man(1, a=0.75), man(2, ("x",), a=0.75)], [need("a", 1.0)], toy("x", "y", "z"), "x",
           [man(11, ("x",), a=1.0)])


@pytest.mark.parametrize("forced", [cp_model.UNKNOWN, cp_model.MODEL_INVALID])
def test_an_undecided_solve_never_becomes_a_complete_brief_or_a_negative_statement(
        monkeypatch, forced):
    phases, truths = set(), set()
    name = "UNKNOWN" if forced == cp_model.UNKNOWN else "MODEL_INVALID"
    for squad, requirements, formation, slot_id, universe in undecided_cases():
        def run(squad=squad, requirements=requirements, formation=formation, slot_id=slot_id,
                universe=universe):
            return role_brief(squad, requirements, formation, slot_id=slot_id,
                              universe=universe, quantization=100)

        truth = run()
        truths.add(truth.status)
        calls = truth.provenance["brief_solver_calls"]
        first, second = calls["squad_without_addition"], calls["enumeration"]
        assert truth.count.undetermined == 0
        for on_call in range(1, first + second + calls["count"] + 1):
            with monkeypatch.context() as patch:
                override_status(patch, on_call, forced)
                result = run()
            if on_call <= first:
                phases.add("squad")
                assert result.squad_satisfiable_without_addition == name
                # Part of the answer is unknown, so the certificate may not read COMPLETE:
                # a result that does is what the API cache keeps.
                assert result.certificate.completeness == "DEADLINE"
            elif on_call <= first + second:
                phases.add("enumeration")
                assert result.status == (
                    "INCOMPLETE" if forced == cp_model.UNKNOWN else "MODEL_INVALID"), on_call
                assert result.certificate.completeness == "DEADLINE"
                assert result.certificate.final_region_status == name
                assert vectors(result) <= vectors(truth)  # rows found are still minimal rows
                assert result.count.row_test_agrees is None
                assert result.count.meeting_ids == truth.count.meeting_ids  # from the solves
            else:
                phases.add("count")
                assert (result.status, vectors(result)) == (truth.status, vectors(truth))
                assert result.count.meeting is None and result.count.undetermined == 1
                assert result.count.row_test_agrees is None
                assert "no count is stated" in result.claim
                assert result.certificate.completeness == "DEADLINE"
    assert phases == {"squad", "enumeration", "count"}
    assert truths == {"BRIEF", "NOT_ADDRESSABLE_AT_SLOT", "RESIDUAL_UNFIELDABLE"}


def test_a_passed_deadline_states_nothing_and_calls_no_solver(monkeypatch):
    squad, requirements, formation = two_rows()
    universe = [man(11, ("x",), a=0.25, b=0.75)]
    calls = override_status(monkeypatch, 0, cp_model.UNKNOWN)
    # Even a residual that is unfieldable by construction is not reported once time is up.
    for people in (squad, [man(2, ("x",), a=0.75, b=0.75)]):
        clock = iter([0.0])  # the deadline is taken at 0.0; every later reading is past it
        with monkeypatch.context() as patch:
            patch.setattr(module.time, "monotonic", lambda clock=clock: next(clock, 10.0**6))
            result = role_brief(people, requirements, formation, slot_id="x", universe=universe,
                                quantization=100, time_limit=5.0)
        assert (result.status, result.rows) == ("INCOMPLETE", ())
        assert result.certificate.completeness == "DEADLINE"
        assert result.certificate.final_region_status == "NOT_RUN"
        assert result.squad_satisfiable_without_addition == "UNKNOWN"
        assert (result.count.meeting, result.count.undetermined) == (None, 1)
        assert INCOMPLETE_WARNING.format(n=0) in result.warnings
    assert calls == []


def test_a_deadline_at_any_clock_reading_leaves_only_what_was_proven(monkeypatch):
    """The clock passes the deadline at its n-th reading, for every n up to a finished run:
    between solves of the enumeration and between candidates of the count."""
    squad = [man(1, ("y",), a=0.75, b=0.25), man(2, ("y",), a=0.25, b=0.75),
             man(4, ("y",), a=0.5, b=0.5), man(3, ("x",), a=0.875, b=0.875)]
    requirements, formation = [need("a", 1.0), need("b", 1.0)], toy("x", "y")
    universe = [man(11, ("x",), a=0.25, b=0.75), man(14, ("x",), a=0.5, b=0.5),
                man(15, ("x",), a=0.125, b=0.125)]

    def run():
        return role_brief(squad, requirements, formation, slot_id="x", universe=universe,
                          quantization=100, time_limit=5.0)

    truth = run()
    assert [row.need_integer for row in truth.rows] == [(25, 75), (50, 50), (75, 25)]
    assert truth.count.meeting_ids == (11, 14)
    some_rows = some_candidates = finished = 0
    for readings in range(1, 200):
        clock = iter([0.0] * readings)
        with monkeypatch.context() as patch:
            patch.setattr(module.time, "monotonic", lambda clock=clock: next(clock, 10.0**6))
            result = run()
        count, certificate = result.count, result.certificate
        assert vectors(result) <= vectors(truth)  # every row shown is a true minimal row
        undecided = (count.undetermined > 0
                     or result.squad_satisfiable_without_addition == "UNKNOWN")
        if certificate.completeness == "COMPLETE":
            # COMPLETE is a statement about the whole answer: rows, squad and count.
            assert (result.status, vectors(result)) == (truth.status, vectors(truth))
            assert certificate.final_region_status == "INFEASIBLE"
            assert not undecided
        elif result.status == "INCOMPLETE":
            assert certificate.completeness == "DEADLINE"
            assert certificate.final_region_status in ("NOT_RUN", "UNKNOWN")
            assert count.row_test_agrees is None
            assert INCOMPLETE_WARNING.format(n=len(result.rows)) in result.warnings
        else:
            # The rows were all found and proven; the deadline fell in the squad solve or
            # in the count, and the certificate says so instead of reading COMPLETE.
            assert certificate.completeness == "DEADLINE" and undecided
            assert vectors(result) == vectors(truth)
            assert certificate.final_region_status == "INFEASIBLE"
        assert result.squad_satisfiable_without_addition in ("UNKNOWN", "SATISFIABLE")
        # The count never guesses: a candidate is met, not met, or left undetermined.
        assert set(count.meeting_ids) <= set(truth.count.meeting_ids)
        assert count.not_meeting <= truth.count.not_meeting
        assert len(count.meeting_ids) + count.not_meeting + count.undetermined == 3
        assert (count.meeting is None) == (count.undetermined > 0)
        some_rows += 0 < len(result.rows) < 3
        some_candidates += 0 < count.undetermined < 3
        if result == truth:
            finished = readings
            break
    assert finished and some_rows >= 1 and some_candidates >= 1


# ------------------------------------------------------------- inputs, guard, hashes


def test_invalid_inputs_are_errors_before_any_solve(monkeypatch):
    squad, requirements, formation = two_rows()
    calls = override_status(monkeypatch, 0, cp_model.UNKNOWN)

    def refuse(match, squad=squad, slot_id="x", quantization=100, **kwargs):
        with pytest.raises(ValueError, match=match):
            role_brief(squad, requirements, formation, slot_id=slot_id,
                       quantization=quantization, **kwargs)

    refuse("unknown slot", slot_id="w")
    refuse("collide with squad player IDs", universe=[man(3, ("x",), a=1.0, b=1.0)])
    refuse("not restricted to x", universe=[man(11, a=1.0, b=1.0)])
    refuse("not restricted to x", universe=[man(11, ("x", "y"), a=1.0, b=1.0)])
    refuse("not admissible at x", universe=[man(11, ("x",), position="G", a=1.0, b=1.0)])
    refuse("unique integers", universe=[man(11, ("x",), a=1.0, b=1.0)] * 2)
    refuse("non-negative rates", universe=[man(11, ("x",), a=-0.1, b=1.0)])
    refuse("non-negative rates", squad=[*squad, man(4, a=0.5, b=-0.5)])
    refuse("sequence of Candidate", universe=[dict(player_id=11)])
    for limit in (0, 257, 2.0, True):
        refuse("max_rows", max_rows=limit)
    for limit in (0, -1.0, math.inf, math.nan, True, "1"):
        refuse("time_limit", time_limit=limit)
    refuse("unknown locked player IDs", locked=(99,))
    refuse("unknown excluded player IDs", excluded=(99,))
    refuse("quantization", quantization=0)
    assert calls == []
    # A negative rate on a metric that is not a dimension of the slot is not the brief's concern.
    wide = [need("a", 1.0), need("c", -10.0, ("y",))]
    extra = [man(1, ("y",), a=0.75, c=-5.0), man(3, ("x",), a=0.875)]
    assert role_brief(extra, wide, formation, slot_id="x", quantization=100).status == "BRIEF"
    with pytest.raises(ValueError, match="different lengths"):
        meets_row({"a": 1.0}, BriefRow((1, 1), (0.1, 0.1), (0.0, 0.0), (), "MINIMAL_CERTIFIED"),
                  requirements, ("need_a",), 100)


def test_result_carries_no_merit_key_and_its_fingerprint_follows_the_decision_inputs(
        thesis_guard):
    squad, requirements, formation = two_rows()
    universe = [man(12, ("x",), a=0.75, b=0.25), man(11, ("x",), a=0.25, b=0.75)]
    lineage = {"dataset_hash": "abc", "providers": ["pappalardo"], "solver_status": "OPTIMAL",
               "brief_version": "an earlier brief", "objective_vector": [0, 0]}

    def run(**changes):
        arguments = dict(slot_id="x", universe=universe, quantization=100, provenance=lineage,
                         locked=(1,), excluded=())
        arguments.update(changes)
        people = arguments.pop("squad", squad)
        return role_brief(people, arguments.pop("requirements", requirements), formation,
                          **arguments)

    result = run()
    thesis_guard(asdict(result))
    record = result.provenance
    assert record["dataset_hash"] == "abc" and record["providers"] == ["pappalardo"]
    assert "solver_status" not in record and "objective_vector" not in record
    assert record["brief_version"] == module.BRIEF_VERSION
    assert record["kernel_version"] == engine.KERNEL_VERSION
    assert record["hard_policy"] == engine.HARD_POLICY and record["quantization"] == 100
    assert (result.locked, result.excluded) == ((1,), ())
    # The lock leaves one residual lineup, so one row; ids come back in player_id order.
    assert [row.need_integer for row in result.rows] == [(25, 75)]
    assert result.count.meeting_ids == (11,) and result.count.not_meeting == 1
    assert result.evidence["composed"] == "HEURISTIC"
    assert result.evidence["per_requirement"] == {"need_a": "ESTIMATED", "need_b": "ESTIMATED"}
    assert result.evidence["declared_inputs"] == [
        "formation", "requirement minima", "slot", "locks", "candidate universe"]
    # A locked player who can play only the brief slot leaves the other slots unfillable.
    stuck = run(locked=(3,))
    assert (stuck.status, stuck.count.meeting) == ("RESIDUAL_UNFIELDABLE", 0)
    assert stuck.warnings == ("Locked player 3 has no admissible assignment.",)

    same = run(squad=squad[::-1], requirements=requirements[::-1], universe=universe[::-1])
    assert same.provenance["input_fingerprint"] == record["input_fingerprint"]
    changed = [
        stuck, run(locked=()), run(excluded=(2,)), run(max_rows=3), run(seed=7),
        run(time_limit=29.0), run(universe=universe[:1]), run(universe=None),
        run(provenance={**lineage, "dataset_hash": "abd"}),
        run(requirements=[replace(requirements[0], minimum=1.25), requirements[1]]),
        run(squad=[replace(squad[0], values={"a": 0.5, "b": 0.25}), *squad[1:]]),
        run(slot_id="y", universe=None),
        run(quantization=1000),
    ]
    prints = {r.provenance["input_fingerprint"] for r in changed} | {record["input_fingerprint"]}
    assert len(prints) == len(changed) + 1
    # An inactive requirement is neither a dimension nor a fixed floor.
    research = replace(requirements[1], status="research")
    partial = run(requirements=[requirements[0], research], locked=())
    assert partial.dimensions == ("need_a",) and partial.fixed_floor_requirements == ()
    assert set(partial.evidence["per_requirement"]) == {"need_a"}


def test_a_screening_recorded_by_an_earlier_brief_is_not_inherited():
    squad, requirements, formation = two_rows()
    screened = role_brief(squad, requirements, formation, slot_id="x", quantization=100,
                          universe=[man(11, ("x",), a=0.25, b=0.75)])
    assert screened.provenance["screened_count"] == 1
    assert "universe_fingerprint" in screened.provenance
    # That record handed on as lineage: this call screened nobody and must not say it did.
    plain = role_brief(squad, requirements, formation, slot_id="x", quantization=100,
                       provenance=screened.provenance)
    assert plain.count is None
    assert "screened_count" not in plain.provenance
    assert "universe_fingerprint" not in plain.provenance
    # With a universe of its own the record is this call's, not the earlier one's.
    other = role_brief(squad, requirements, formation, slot_id="x", quantization=100,
                       provenance=screened.provenance,
                       universe=[man(11, ("x",), a=0.25, b=0.75), man(12, ("x",), a=0.5, b=0.5)])
    assert other.provenance["screened_count"] == 2
    assert other.provenance["universe_fingerprint"] != screened.provenance["universe_fingerprint"]


# ------------------------------------------------------------------- real scenario

OUTFIELD = ("lb", "lcb", "rcb", "rb", "dm", "lcm", "rcm", "lw", "st", "rw")
DIMENSIONS = ("left_pass_origins", "progression", "right_pass_origins")


@pytest.mark.slow
def test_madrid_briefs_equal_the_pinned_table(corpus_root):
    """Spec section 10.3: scenario madrid-2018-05-06, shipped minima, 4-3-3, integers in
    units of 1e-5, measured there by an independent slot-DFS enumeration."""
    from galactico.api.decision_lab import decision_inputs
    from galactico.optimization.historical import load_snapshot

    candidates, requirements = decision_inputs(load_snapshot(2565907, worlds=0), "4-3-3")

    def brief(slot_id, multiplier=1.0, **kwargs):
        scaled = [replace(r, minimum=r.minimum * multiplier) if r.active else r
                  for r in requirements]
        result = role_brief(candidates, scaled, "4-3-3", slot_id=slot_id, **kwargs)
        assert result.certificate.completeness == "COMPLETE"
        assert result.dimensions == (() if slot_id == "gk" else DIMENSIONS)
        return result

    def rows(result):
        return [row.need_integer for row in result.rows]

    default = {slot_id: brief(slot_id) for slot_id in ("gk", *OUTFIELD)}
    assert {b.squad_satisfiable_without_addition for b in default.values()} == {"SATISFIABLE"}
    assert (default["lb"].status, len(default["lb"].rows)) == ("BRIEF", 8)
    assert rows(default["lb"])[:3] == [
        (12902, 20022, 45335), (13520, 19655, 45489), (13576, 10532, 13278)]
    assert default["rb"].status == "BRIEF"
    assert rows(default["rb"]) == [(0, 0, 12181), (5110, 0, 9871), (31847, 9509, 9400)]
    for slot_id in ("lcb", "rcb", "dm", "lcm", "rcm", "lw", "st", "rw"):
        assert (default[slot_id].status, rows(default[slot_id])) == ("NO_NEED", [(0, 0, 0)])
    assert (default["gk"].status, rows(default["gk"])) == ("NO_NEED", [()])
    assert default["gk"].fixed_floor_requirements == DIMENSIONS
    assert default["lb"].evidence["composed"] == "EXPERIMENTAL"

    without = {slot_id: brief(slot_id, excluded=(3310,)) for slot_id in ("gk", *OUTFIELD)}
    assert {b.squad_satisfiable_without_addition for b in without.values()} == {
        "NOT_SATISFIABLE"}
    assert {slot_id: len(without[slot_id].rows) for slot_id in OUTFIELD} == dict(
        lb=8, lcb=6, rcb=6, rb=7, dm=5, lcm=5, rcm=5, lw=3, st=4, rw=3)
    assert {without[slot_id].status for slot_id in OUTFIELD} == {"BRIEF"}
    assert rows(without["dm"]) == [
        (16047, 11997, 3957), (16665, 11630, 4111), (20410, 6716, 0), (20892, 1942, 0),
        (34285, 1405, 0)]
    assert (without["gk"].status, without["gk"].rows) == ("NOT_ADDRESSABLE_AT_SLOT", ())

    for slot_id in ("gk", *OUTFIELD):
        both = brief(slot_id, excluded=(3310, 4501))
        assert both.squad_satisfiable_without_addition == "UNFIELDABLE"
        if slot_id in ("lb", "rb"):
            assert (both.status, len(both.rows)) == ("BRIEF", 7)
        else:
            assert (both.status, both.rows) == ("RESIDUAL_UNFIELDABLE", ())

    raised = brief("lcb", multiplier=1.25)
    assert (raised.status, len(raised.rows)) == ("BRIEF", 14)
    assert rows(raised)[:3] == [(0, 27676, 83219), (0, 28043, 83065), (326, 21444, 72529)]
    assert raised.certificate.solves == 43  # 3 dimensions x 14 rows + the empty region


def slot_search(players, requirements, formation, slot_id, scale, excluded=()):
    """Every need vector of the residual problem, by depth-first search over the other slots.

    The permutation oracle cannot reach eleven slots. Same exact arithmetic, formed here; no
    solver and no helper of the module under test.
    """
    active = sorted((r for r in requirements if r.active), key=lambda r: r.requirement_id)
    dims = [r for r in active if applies(r, slot_id)]
    fixed = [r for r in active if not applies(r, slot_id)]
    rest = [s for s in formation.slots if s.slot_id != slot_id]
    pool = [p for p in players if p.player_id not in excluded]
    options = [[p for p in pool if can_play(p, s, active)] for s in rest]
    floors = {
        (p.player_id, r.requirement_id): unit(p.values[r.metric], r, scale)
        for p in pool for r in active if p.values.get(r.metric) is not None
    }
    goals = {r.requirement_id: goal(r, scale) for r in active}
    sums = dict.fromkeys(goals, 0)
    used, needs, lineups_seen = set(), set(), [0]

    def walk(depth):
        if depth == len(rest):
            lineups_seen[0] += 1
            if all(sums[r.requirement_id] >= goals[r.requirement_id] for r in fixed):
                needs.add(tuple(
                    max(0, goals[r.requirement_id] - sums[r.requirement_id]) for r in dims))
            return
        counted = [r.requirement_id for r in active if applies(r, rest[depth].slot_id)]
        for player in options[depth]:
            if player.player_id in used:
                continue
            used.add(player.player_id)
            for rid in counted:
                sums[rid] += floors[player.player_id, rid]
            walk(depth + 1)
            for rid in counted:
                sums[rid] -= floors[player.player_id, rid]
            used.discard(player.player_id)

    walk(0)
    rows = minimal(needs)
    if not lineups_seen[0]:
        return "RESIDUAL_UNFIELDABLE", rows, needs, dims
    if not needs:
        return "NOT_ADDRESSABLE_AT_SLOT", rows, needs, dims
    return ("NO_NEED" if rows == {(0,) * len(dims)} else "BRIEF"), rows, needs, dims


@pytest.mark.slow
def test_season_end_briefs_and_universe_counts_equal_a_slot_search(corpus_root, league_available):
    """The planning snapshot (cutoff 2018-05-21) with player 3322 excluded: status and rows of
    every slot, and who in the real same-league universe meets them. A candidate meets when
    his floor coefficients cover some need vector the search found: the definition itself,
    with no minimal row and no solve. The literals were measured by both computations."""
    from galactico.optimization import snapshots
    from galactico.optimization.transfers.universe import load_universe
    from galactico.optimization.xi.domain import FORMATIONS

    for league in ("Spain", "England", "Italy", "Germany", "France"):
        league_available(league)
    snap = snapshots.load_team_snapshot(
        competition="Spain", team_id=675, cutoff="2018-05-21", worlds=0)
    universe = load_universe(snapshot=snap)
    formation, scale, seen = FORMATIONS["4-3-3"], 100_000, {}
    # Without the opt-in only progression is in force; with it the two side descriptors too.
    for opt_in, counted in ((False, ("lw",)), (True, ("lb", "rb", "st"))):
        candidates, requirements = snapshots.snapshot_inputs(
            snap, "4-3-3", experimental_opt_in=opt_in)
        for slot in formation.slots:
            status, rows, needs, dims = slot_search(
                candidates, requirements, formation, slot.slot_id, scale, excluded=(3322,))
            result = role_brief(
                candidates, requirements, "4-3-3", slot_id=slot.slot_id, excluded=(3322,),
                universe=universe if slot.slot_id in counted else None,
                provenance=snap.provenance)
            context = (opt_in, slot.slot_id)
            assert (result.status, vectors(result)) == (status, rows), context
            assert result.dimensions == tuple(r.requirement_id for r in dims), context
            assert result.certificate.completeness == "COMPLETE", context
            assert result.squad_satisfiable_without_addition == "SATISFIABLE", context
            assert result.provenance["providers"] == ["pappalardo"]
            seen[context] = (status, len(rows))
            if slot.slot_id not in counted:
                assert result.count is None and "screened_count" not in result.provenance
                continue
            admissible = [
                u for u in universe.candidates if u.provider_position in slot.allowed_positions]
            meeting = tuple(
                u.player_id for u in admissible
                if all(u.values.get(r.metric) is not None for r in dims)
                and any(
                    all(unit(u.values[r.metric], r, scale) >= least
                        for r, least in zip(dims, vector, strict=True))
                    for vector in needs)
            )
            count = result.count
            assert (count.admissible, count.meeting_ids) == (len(admissible), meeting), context
            assert (count.meeting, count.undetermined) == (len(meeting), 0), context
            assert count.row_test_agrees is True, context
            assert result.provenance["screened_count"] == len(admissible)
            assert (result.provenance["universe_fingerprint"]
                    == universe.provenance["input_fingerprint"])
            seen[context] += (len(meeting), len(admissible))
    assert {found[0] for (opt_in, _), found in seen.items() if not opt_in} == {"NO_NEED"}
    assert seen[False, "lw"] == ("NO_NEED", 1, 176, 176)
    assert seen[True, "lb"] == ("BRIEF", 5, 28, 118)
    assert seen[True, "rb"] == ("BRIEF", 3, 35, 118)
    assert seen[True, "st"] == ("NO_NEED", 1, 58, 58)
    assert seen[True, "gk"] == ("NO_NEED", 1)
    assert {seen[True, sid] for sid in ("lcb", "rcb", "dm", "lcm", "rcm", "lw", "rw")} == {
        ("NO_NEED", 1)}


# ------------------------------------------- a page prints these sentences: labels, not ids


def whole_word(token, text):
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])", text)


def test_no_sentence_of_a_brief_names_a_slot_or_a_requirement_by_its_id():
    slots = (Slot("zq1", "Left post", ("P",), 0.3, 0.5),
             Slot("zq2", "Right post", ("P",), 0.7, 0.5),
             Slot("zq0", "Keeper", ("G",), 0.5, 0.9), Slot("zq3", "Far post", ("P",), 0.5, 0.1))
    formation = Formation("toy", slots[:3])
    posts = Formation("toy", slots[:2])
    three = Formation("toy", (*slots[:2], slots[3]))

    def wanted(metric, label, minimum, slot_ids=()):
        return TacticalRequirement(
            f"rq_{metric}", label, metric, minimum, 1.0, slot_ids, "MEASURED")

    both = [wanted("mxa", "Alpha per 90", 1.0), wanted("mxb", "Beta per 90", 1.0)]
    squad = [man(1, ("zq2",), mxa=0.75, mxb=0.25), man(2, ("zq2",), mxa=0.25, mxb=0.75),
             man(3, ("zq1",), mxa=0.875, mxb=0.875)]
    pool = [man(11, ("zq1",), mxa=0.25, mxb=0.75), man(13, ("zq1",), mxa=0.125, mxb=0.125)]
    with_keeper = [man(1, position="G", mxa=0.0), man(2, mxa=0.5), man(3, mxa=0.5)]
    keeper = [man(11, ("zq0",), position="G")]
    outfield = ("zq1", "zq2")
    results = [
        role_brief(squad, both, posts, slot_id="zq1", universe=pool, quantization=100),
        role_brief(squad, both, posts, slot_id="zq1", universe=pool, quantization=100,
                   max_rows=1),
        role_brief(with_keeper, [wanted("mxa", "Alpha per 90", 1.0, outfield)], formation,
                   slot_id="zq0", universe=keeper, quantization=100),
        role_brief(with_keeper, [wanted("mxa", "Alpha per 90", 1.5, outfield)], formation,
                   slot_id="zq0", universe=keeper, quantization=100),
        role_brief([man(1, mxa=0.75), man(2, ("zq1",), mxa=0.75)],
                   [wanted("mxa", "Alpha per 90", 1.0)], three, slot_id="zq1", quantization=100),
    ]
    assert [r.status for r in results] == [
        "BRIEF", "INCOMPLETE", "NO_NEED", "NOT_ADDRESSABLE_AT_SLOT", "RESIDUAL_UNFIELDABLE"]
    assert any("non-zero all the same" in text for text in results[0].warnings)
    sentences = [text for r in results for text in (r.claim, *r.warnings)]
    for token in ("zq0", "zq1", "zq2", "zq3", "rq_mxa", "rq_mxb", "mxa", "mxb"):
        for text in sentences:
            assert not whole_word(token, text), (token, text)
    assert results[0].claim.startswith("For Left post: a player added there makes")
    assert "Alpha per 90 does not count this slot" in results[3].claim


def test_brief_sentences_agree_in_number_with_their_counts():
    squad, requirements, formation = two_rows()
    on_first, below = man(11, ("x",), a=0.25, b=0.75), man(13, ("x",), a=0.125, b=0.125)
    one_of_two = role_brief(squad, requirements, formation, slot_id="x",
                            universe=[on_first, below], quantization=100)
    assert ("1 of the 2 gated players admissible at Slot x in the declared universe makes "
            "every declared minimum reachable") in one_of_two.claim
    alone = role_brief(squad, requirements, formation, slot_id="x", universe=[on_first],
                       quantization=100)
    assert "1 of the 1 gated player admissible at Slot x in the declared universe makes " in (
        alone.claim)
    neither = role_brief(squad, requirements, formation, slot_id="x", universe=[below],
                         quantization=100)
    assert "0 of the 1 gated player admissible at Slot x in the declared universe make " in (
        neither.claim)
    assert module._claim(
        formation.slots[0], "BRIEF", 2, (), "SATISFIABLE",
        module.BriefCount(3, None, 0, 1, (), "INJECTED_SATISFY_SOLVE", None), 100,
    ).count("1 of the 3 gated players admissible at Slot x in the declared universe was not "
            "resolved before the deadline") == 1
    assert "A, B do not count this slot and the other slots cannot reach them." in module._claim(
        formation.slots[0], "NOT_ADDRESSABLE_AT_SLOT", 0, ("A", "B"), "NOT_SATISFIABLE", None, 100)
    limited = role_brief(squad, requirements, formation, slot_id="x", quantization=100,
                         max_rows=1)
    assert limited.warnings[-1] == (
        "The brief is incomplete: the limit was reached with 1 of its minimal rows found. "
        "A player who meets none of them may still meet a row that was not found.")
