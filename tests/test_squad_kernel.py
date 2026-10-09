"""The squad kernel against an oracle that shares nothing with it or with solve_xi.

The oracle is written from the problem statement: `itertools.product` over the per-slot lists
of admissible players, integers formed with exact `Fraction` half-even (shortfalls) and exact
`Fraction` floor/ceil (hard floors). It imports only the domain dataclasses. `solve_xi` is used
as a second, differential reference and never by the oracle.
"""

from __future__ import annotations

import itertools
import math
import random
import re
import time
from dataclasses import asdict, replace
from fractions import Fraction
from pathlib import Path

import pytest
from ortools.sat.python import cp_model

from galactico.domain.provenance import EvidenceClass
from galactico.optimization.squad import kernel as engine
from galactico.optimization.squad.kernel import (
    KernelValue,
    Membership,
    ShortfallKernel,
    compose_evidence,
    fingerprint,
    scrub_lineage,
    source_fingerprints,
)
from galactico.optimization.xi.domain import Candidate, Formation, Slot, TacticalRequirement
from galactico.optimization.xi.solver import solve_xi

BANNED_KEYS = {"rating", "score", "rank", "overall", "index", "grade", "quality", "fit_score"}


def far() -> float:
    return time.monotonic() + 600.0


# --------------------------------------------------------------------------- oracle


def oracle(
    candidates,
    requirements,
    formation,
    *,
    scale,
    excluded=(),
    locked=(),
    pinned=None,
    vacant=(),
    values=None,
):
    """Every admissible assignment with its integers; no helper from the code under test."""
    pinned, values = dict(pinned or {}), dict(values or {})
    slots = [slot for slot in formation.slots if slot.slot_id not in vacant]
    active = sorted(
        (r for r in requirements if r.status == "active" and r.evidence_class != "UNAVAILABLE"),
        key=lambda r: r.requirement_id,
    )
    vector = {p.player_id: values.get(p.player_id, p.values) for p in candidates}

    def applies(requirement, slot_id):
        return not requirement.slot_ids or slot_id in requirement.slot_ids

    options = []
    for slot in slots:
        row = []
        for player in candidates:
            pid = player.player_id
            if pid in excluded or player.minutes <= 0:
                continue
            if player.position not in slot.allowed_positions:
                continue
            if player.eligible_slots is not None and slot.slot_id not in player.eligible_slots:
                continue
            if pid in pinned and pinned[pid] != slot.slot_id:
                continue
            if any(
                vector[pid].get(r.metric) is None for r in active if applies(r, slot.slot_id)
            ):
                continue
            row.append(pid)
        options.append(row)
    required = set(locked) | set(pinned)
    contradiction = bool(set(locked) & set(excluded))
    scaled: dict[tuple[int, str], Fraction] = {}

    def exact(pid, requirement):
        key = (pid, requirement.requirement_id)
        if key not in scaled:
            scaled[key] = (
                Fraction(vector[pid][requirement.metric]) / Fraction(requirement.normalizer) * scale
            )
        return scaled[key]

    targets = {
        r.requirement_id: Fraction(r.minimum) / Fraction(r.normalizer) * scale for r in active
    }
    rows = []
    for combo in itertools.product(*options):
        chosen = set(combo)
        if contradiction or len(chosen) != len(combo) or not required <= chosen:
            continue
        shortfalls, floors_hold = [], True
        for requirement in active:
            parts = [
                exact(pid, requirement)
                for pid, slot in zip(combo, slots, strict=True)
                if applies(requirement, slot.slot_id)
            ]
            target = targets[requirement.requirement_id]
            shortfalls.append(max(0, round(target) - sum(round(part) for part in parts)))
            floors_hold &= sum(math.floor(part) for part in parts) >= math.ceil(target)
        lineup = tuple((slot.slot_id, pid) for slot, pid in zip(slots, combo, strict=True))
        rows.append((lineup, tuple(shortfalls), floors_hold))
    admissible = {slot.slot_id: row for slot, row in zip(slots, options, strict=True)}
    if not rows:
        return {"value": None, "floor": "UNFIELDABLE", "feasible": 0, "admissible": admissible}
    best = min((max(s, default=0), sum(s)) for _, s, _ in rows)
    optimal = [row for row in rows if (max(row[1], default=0), sum(row[1])) == best]
    return {
        "value": best,
        "feasible": len(rows),
        "admissible": admissible,
        "optimal_lineups": {lineup for lineup, _, _ in optimal},
        "optimal_sets": [{pid for _, pid in lineup} for lineup, _, _ in optimal],
        "ranges": {
            r.requirement_id: (
                min(s[i] for _, s, _ in optimal),
                max(s[i] for _, s, _ in optimal),
            )
            for i, r in enumerate(active)
        },
        "floor": "SATISFIABLE" if any(ok for _, _, ok in rows) else "NOT_SATISFIABLE",
        "satisfying_lineups": {lineup for lineup, _, ok in rows if ok},
    }


def near_half_integer(candidates, requirements, scale, values=None) -> bool:
    """The only place the shipped float expression and exact half-even can differ."""
    vectors = [p.values for p in candidates] + list((values or {}).values())
    for requirement in requirements:
        numbers = [requirement.minimum]
        numbers += [v[requirement.metric] for v in vectors if v.get(requirement.metric) is not None]
        for number in numbers:
            exact = Fraction(number) / Fraction(requirement.normalizer) * scale
            if abs(exact - math.floor(exact) - Fraction(1, 2)) < Fraction(1, 10**9):
                return True
    return False


# ------------------------------------------------------------------------ generator


def draw(rng: random.Random, number: int):
    slots = [
        Slot("s0", "Twin one", ("A",), 0.2, 0.5),
        Slot("s1", "Twin two", ("A",), 0.4, 0.5),
        Slot("s2", "Other", ("B",), 0.6, 0.5),
    ]
    if rng.random() < 0.5:
        slots.append(Slot("s3", "Either", ("A", "B"), 0.8, 0.5))
    formation = Formation(f"tiny-{number}", tuple(slots))
    slot_ids = [slot.slot_id for slot in slots]
    twins = rng.random() < 0.7  # keep s0 and s1 interchangeable in most instances
    scale = rng.choice((3, 8, 100_000))
    metrics = [f"m{i}" for i in range(rng.choice((2, 3)))]
    requirements = []
    for metric in metrics:
        if rng.random() < 0.4:
            incidence = ()
        else:
            incidence = tuple(s for s in slot_ids if rng.random() < 0.6) or (rng.choice(slot_ids),)
            if twins and ("s0" in incidence) != ("s1" in incidence):
                incidence = tuple(sorted({*incidence, "s0", "s1"}))
        applicable = len(incidence) or len(slot_ids)
        requirements.append(
            TacticalRequirement(
                requirement_id=f"need_{metric}",
                label=metric,
                metric=metric,
                minimum=rng.uniform(0.1, 1.0) * applicable,
                normalizer=rng.choice((1.0, rng.uniform(0.3, 2.0))),
                slot_ids=incidence,
                evidence_class=rng.choice(("MEASURED", "HEURISTIC", "RESEARCH")),
            )
        )
    if rng.random() < 0.3:  # an inactive requirement contributes nothing, even where unmeasured
        requirements.append(
            TacticalRequirement("idle", "idle", "idle", 5.0, 1.0, (), "UNAVAILABLE", False,
                                "unavailable")
        )

    def vector():
        return {m: None if rng.random() < 0.10 else rng.uniform(-0.2, 1.5) for m in metrics}

    candidates = []
    for order, pid in enumerate(rng.sample(range(1, 60), rng.randint(5, 7))):
        if rng.random() < 0.5:
            eligible = None
        else:
            kept = {s: rng.random() >= 0.20 for s in slot_ids}
            if twins:
                kept["s1"] = kept["s0"]
            eligible = tuple(s for s in slot_ids if kept[s])
        candidates.append(
            Candidate(
                pid,
                f"p{pid}",
                "B" if order == 0 else "A" if order < 4 else rng.choice(("A", "B")),
                vector(),
                0 if rng.random() < 0.05 else 900,
                eligible,
            )
        )
    ids = [p.player_id for p in candidates]
    declared = {
        "locked": (rng.choice(ids),) if number % 3 == 0 else (),
        "excluded": (rng.choice(ids),) if number % 4 == 0 else (),
        "pinned": {rng.choice(ids): rng.choice(slot_ids)} if number % 5 == 0 else None,
        "vacant": (rng.choice(slot_ids),) if number % 6 == 0 else (),
        "values": {pid: vector() for pid in rng.sample(ids, 2)} if number % 7 == 0 else None,
    }
    rng.shuffle(candidates)
    rng.shuffle(requirements)
    return candidates, requirements, formation, scale, declared


def instances(count=60, seed=20261009):
    rng = random.Random(seed)
    for number in range(count):
        while True:
            built = draw(rng, number)
            if not near_half_integer(built[0], built[1], built[3], built[4]["values"]):
                break
        yield number, built


def reference(candidates, requirements, formation, scale, declared):
    """solve_xi on the same declaration; a pin is a lock restricted to one eligible slot."""
    players = []
    for player in candidates:
        if declared["values"] and player.player_id in declared["values"]:
            player = replace(player, values=declared["values"][player.player_id])
        slot_id = (declared["pinned"] or {}).get(player.player_id)
        if slot_id is not None:
            allowed = player.eligible_slots is None or slot_id in player.eligible_slots
            player = replace(player, eligible_slots=(slot_id,) if allowed else ())
        players.append(player)
    result = solve_xi(
        players,
        requirements,
        formation,
        locked=tuple({*declared["locked"], *(declared["pinned"] or {})}),
        excluded=declared["excluded"],
        quantization=scale,
        analyze_ties=False,
    )
    if result.solution_status == "INFEASIBLE":
        return None
    assert result.solution_status == "OPTIMAL"
    return tuple(round(v * scale) for v in result.objective_vector)


def twin_pair_is_live(requirements, truth) -> bool:
    """Whether s0 and s1 are interchangeable (same admissible players, at least two, and the
    same requirement incidence) in a fieldable instance, read from the problem statement."""
    admissible = truth["admissible"]
    if truth["value"] is None or not {"s0", "s1"} <= admissible.keys():
        return False
    same_incidence = all(
        not r.slot_ids or ("s0" in r.slot_ids) == ("s1" in r.slot_ids)
        for r in requirements
        if r.status == "active" and r.evidence_class != "UNAVAILABLE"
    )
    return same_incidence and admissible["s0"] == admissible["s1"] and len(admissible["s0"]) >= 2


# ----------------------------------------------------------------- K1-K5, K7, K8


def test_kernel_equals_the_oracle_and_solve_xi_on_seeded_instances():
    seen = {"status": set(), "floor": set(), "zero": 0, "positive": 0, "gap": 0, "twins": 0,
            "removal_unfieldable": 0, "removal_raises": 0, "necessary": 0, "impossible": 0,
            "differential": 0, "compared": 0}
    for number, (candidates, requirements, formation, scale, declared) in instances():
        tag = f"instance {number}"
        kernel = ShortfallKernel(candidates, requirements, formation, quantization=scale)
        truth = oracle(candidates, requirements, formation, scale=scale, **declared)
        value = kernel.value(**declared, deadline=far())
        floor = kernel.satisfiable(**declared, deadline=far())
        seen["status"].add(value.status)
        seen["floor"].add(floor.status)
        seen["twins"] += twin_pair_is_live(requirements, truth)
        seen["compared"] += 1

        # K1: the lexicographic optimum and a witness inside the optimal set.
        if truth["value"] is None:
            assert (value.status, value.maximum, value.total, value.lineup) == (
                "UNFIELDABLE", None, None, ()), tag
            assert value.objective_vector is None
        else:
            assert value.status == "CERTIFIED", tag
            assert (value.maximum, value.total) == truth["value"], tag
            assert value.lineup in truth["optimal_lineups"], tag
            assert value.objective_vector == (value.maximum / scale, value.total / scale)
            seen["zero" if truth["value"] == (0, 0) else "positive"] += 1
        assert value.solves == len(value.stage_statuses) <= 3

        # K4: the conservative floor statement, and raw minima met exactly by its witness.
        assert floor.status == truth["floor"], tag
        assert floor.solves <= 2
        if floor.status == "SATISFIABLE":
            assert floor.lineup in truth["satisfying_lineups"], tag
            vector = {p.player_id: (declared["values"] or {}).get(p.player_id, p.values)
                      for p in candidates}
            by_id = {r.requirement_id: r for r in requirements}
            for rid, raw in floor.raw_sums:
                requirement = by_id[rid]
                total = sum(
                    (Fraction(vector[pid][requirement.metric]) for sid, pid in floor.lineup
                     if not requirement.slot_ids or sid in requirement.slot_ids),
                    Fraction(),
                )
                assert total >= Fraction(requirement.minimum), tag
                assert raw == float(total), tag
        else:
            assert floor.lineup == () and floor.raw_sums == ()
        if truth["value"] == (0, 0) and floor.status == "NOT_SATISFIABLE":
            seen["gap"] += 1

        # K2: the shipped solver returns the same integers (vacancy is outside its interface).
        if not declared["vacant"]:
            assert reference(candidates, requirements, formation, scale, declared) == (
                truth["value"]), tag
            seen["differential"] += 1

        # K5: input order changes neither a value nor the contract hash.
        mirrored = ShortfallKernel(candidates[::-1], requirements[::-1], formation,
                                   quantization=scale)
        again = mirrored.value(**declared, deadline=far())
        assert (again.status, again.maximum, again.total) == (
            value.status, value.maximum, value.total), tag
        assert mirrored.satisfiable(**declared, deadline=far()).status == floor.status, tag
        assert fingerprint(mirrored.input_contract) == fingerprint(kernel.input_contract)

        # K7: a whole-vector replacement equals a kernel built on the replaced candidates.
        if declared["values"]:
            fresh = ShortfallKernel(
                [replace(p, values=declared["values"].get(p.player_id, p.values))
                 for p in candidates],
                requirements, formation, quantization=scale,
            )
            plain = {**declared, "values": None}
            rebuilt = fresh.value(**plain, deadline=far())
            assert (rebuilt.status, rebuilt.maximum, rebuilt.total) == (
                value.status, value.maximum, value.total), tag
            assert fresh.satisfiable(**plain, deadline=far()).status == floor.status, tag

        # K3 and the per-requirement ranges over the optimal level set.
        level_args = {k: v for k, v in declared.items() if k != "vacant"}
        ids = [p.player_id for p in candidates]
        if value.status == "CERTIFIED" and declared["vacant"]:
            with pytest.raises(ValueError, match="does not belong"):
                kernel.membership(value, ids, **level_args, deadline=far())
        elif value.status == "CERTIFIED":
            membership = kernel.membership(value, ids, **level_args, deadline=far())
            assert list(membership) == sorted(ids)
            for pid, fact in membership.items():
                possible = any(pid in chosen for chosen in truth["optimal_sets"])
                necessary = all(pid in chosen for chosen in truth["optimal_sets"])
                assert fact == Membership(possible, necessary), (tag, pid)
                seen["necessary"] += necessary
                seen["impossible"] += not possible
            ranges = kernel.shortfall_ranges(value, **level_args, deadline=far())
            assert ranges == truth["ranges"], tag

        # Baseline plus every single-player removal: kernel == oracle == solve_xi, and K8.
        for pid in sorted(ids):
            if pid in declared["excluded"]:
                continue
            without = {**declared, "excluded": (*declared["excluded"], pid)}
            removed = kernel.value(**without, deadline=far())
            expected = oracle(candidates, requirements, formation, scale=scale, **without)["value"]
            if expected is None:
                assert removed.status == "UNFIELDABLE", (tag, pid)
                seen["removal_unfieldable"] += 1
            else:
                assert removed.status == "CERTIFIED", (tag, pid)
                assert (removed.maximum, removed.total) == expected, (tag, pid)
                # K8: an exclusion never lowers the value; UNFIELDABLE is absorbing.
                assert value.status == "CERTIFIED", (tag, pid)
                assert expected >= (value.maximum, value.total), (tag, pid)
                seen["removal_raises"] += expected > (value.maximum, value.total)
            if not declared["vacant"]:
                assert reference(candidates, requirements, formation, scale, without) == (
                    expected), (tag, pid)
                seen["differential"] += 1
            seen["compared"] += 1

    # Non-vacuity: each interesting outcome and its opposite occurred.
    assert {"CERTIFIED", "UNFIELDABLE"} <= seen["status"]
    assert {"SATISFIABLE", "NOT_SATISFIABLE", "UNFIELDABLE"} <= seen["floor"]
    assert seen["zero"] >= 5 and seen["positive"] >= 5
    assert seen["gap"] >= 1  # zero shortfall yet not satisfiable in the conservative model
    assert seen["twins"] >= 5  # the symmetry ordering was live on real ties
    assert seen["removal_unfieldable"] >= 5 and seen["removal_raises"] >= 5
    assert seen["necessary"] >= 5 and seen["impossible"] >= 5
    assert seen["differential"] >= 200 and seen["compared"] >= 300
    print({k: sorted(v) if isinstance(v, set) else v for k, v in seen.items()})


# ------------------------------------------------------------------ hand-built cases


def one_slot(value=0.2951, minimum=0.2959):
    formation = Formation("one", (Slot("a", "Only", ("A",), 0.5, 0.5),))
    players = [Candidate(1, "one", "A", {"m": value}, 900)]
    requirements = [TacticalRequirement("need", "need", "m", minimum, 1.0)]
    return players, requirements, formation


def pair():
    """Two slots, three players; the best XI is short on one requirement (40, 40 at scale 100)."""
    formation = Formation(
        "pair", (Slot("a", "A", ("A",), 0.3, 0.5), Slot("b", "B", ("B",), 0.7, 0.5))
    )
    players = [
        Candidate(1, "one", "A", {"m": 0.30, "n": 0.50}, 900),
        Candidate(2, "two", "A", {"m": 0.10, "n": 0.90}, 900),
        Candidate(3, "three", "B", {"m": 0.30, "n": 0.20}, 900),
    ]
    requirements = [
        TacticalRequirement("need_m", "m", "m", 1.0, 1.0),
        TacticalRequirement("need_n", "n", "n", 0.6, 1.0),
    ]
    return players, requirements, formation


def one_player_for_two_slots():
    """Each slot has an admissible player, yet no XI exists: only a proof finds it."""
    players, requirements, formation = pair()
    either = tuple(replace(slot, allowed_positions=("A", "B")) for slot in formation.slots)
    return ShortfallKernel(players[:1], requirements, Formation("wide", either), quantization=100)


def test_half_even_zero_shortfall_can_be_not_satisfiable_under_the_conservative_floor():
    # 29.51 and 29.59 both round to 30 (no shortfall); floor 29 is below ceil 30 (no floor).
    players, requirements, formation = one_slot()
    kernel = ShortfallKernel(players, requirements, formation, quantization=100)
    value = kernel.value(deadline=far())
    assert (value.status, value.maximum, value.total) == ("CERTIFIED", 0, 0)
    assert value.lineup == (("a", 1),) and value.stage_statuses == ("OPTIMAL",)
    floor = kernel.satisfiable(deadline=far())
    assert (floor.status, floor.solves) == ("NOT_SATISFIABLE", 2)
    truth = oracle(players, requirements, formation, scale=100)
    assert truth["value"] == (0, 0) and truth["floor"] == "NOT_SATISFIABLE"
    # Conservative means conservative: a raw minimum that IS met (0.2959 >= 0.2951) is still
    # excluded at this scale (floor 29 < ceil 30), and admitted once the scale separates them.
    coarse = ShortfallKernel(*one_slot(0.2959, 0.2951), quantization=100)
    assert coarse.satisfiable(deadline=far()).status == "NOT_SATISFIABLE"
    fine = ShortfallKernel(*one_slot(0.2959, 0.2951), quantization=100_000)
    met = fine.satisfiable(deadline=far())
    assert (met.status, met.lineup, met.raw_sums, met.solves) == (
        "SATISFIABLE", (("a", 1),), (("need", 0.2959),), 1)


def test_equally_least_xis_keep_their_different_requirement_shortfalls_visible():
    # Two XIs tie at (2, 3) with the shortfall on opposite requirements: a range, not a point.
    formation = Formation("one", (Slot("a", "Only", ("A",), 0.5, 0.5),))
    players = [
        Candidate(1, "one", "A", {"m": 0.8, "n": 0.9}, 900),
        Candidate(2, "two", "A", {"m": 0.9, "n": 0.8}, 900),
        Candidate(3, "three", "A", {"m": 0.1, "n": 0.1}, 900),
    ]
    requirements = [
        TacticalRequirement("need_m", "m", "m", 1.0, 1.0),
        TacticalRequirement("need_n", "n", "n", 1.0, 1.0),
    ]
    kernel = ShortfallKernel(players, requirements, formation, quantization=10)
    truth = oracle(players, requirements, formation, scale=10)
    level = kernel.value(deadline=far())
    assert (level.maximum, level.total) == truth["value"] == (2, 3)
    ranges = kernel.shortfall_ranges(level, deadline=far())
    assert ranges == truth["ranges"] == {"need_m": (1, 2), "need_n": (1, 2)}
    assert kernel.membership(level, [1, 2, 3], deadline=far()) == {
        1: Membership(True, False), 2: Membership(True, False), 3: Membership(False, False)}


def test_declarations_that_cannot_be_met_are_unfieldable_with_a_reason_and_never_relaxed():
    players, requirements, formation = pair()
    kernel = ShortfallKernel(players, requirements, formation, quantization=100)
    base = kernel.value(deadline=far())
    assert (base.status, base.maximum, base.total) == ("CERTIFIED", 40, 40)
    assert base.stage_statuses == ("INFEASIBLE", "OPTIMAL", "OPTIMAL") and base.solves == 3
    cases = [
        (dict(locked=(1,), excluded=(1,)), "both locked and excluded"),
        (dict(excluded=(3,)), "No eligible measured candidate for B (b)."),
        (dict(pinned={3: "a"}), "Pinned player 3 has no admissible assignment at a."),
        (dict(pinned={1: "a"}, vacant=("a",)), "Pinned player 1"),
        (dict(locked=(3,), values={3: {"m": None, "n": 0.2}}), "No eligible measured"),
    ]
    for declared, reason in cases:
        value = kernel.value(**declared, deadline=far())
        assert (value.status, value.lineup, value.solves) == ("UNFIELDABLE", (), 0), declared
        assert any(reason in text for text in value.reasons), (declared, value.reasons)
        assert kernel.satisfiable(**declared, deadline=far()).status == "UNFIELDABLE"
        assert oracle(players, requirements, formation, scale=100, **declared)["value"] is None
    # Unfieldable by counting, with every slot individually coverable: only a proof finds it.
    hall = one_player_for_two_slots()
    value = hall.value(deadline=far())
    assert (value.status, value.stage_statuses) == ("UNFIELDABLE", ("INFEASIBLE", "INFEASIBLE"))
    assert hall.satisfiable(deadline=far()).status == "UNFIELDABLE"
    # A pin is honoured, a vacancy removes the slot and its incidence, and nothing is mutated.
    pinned = kernel.value(pinned={2: "a"}, deadline=far())
    assert pinned.lineup == (("a", 2), ("b", 3)) and (pinned.maximum, pinned.total) == (60, 60)
    vacant = kernel.value(vacant=("b",), deadline=far())
    assert vacant.lineup == (("a", 1),) and (vacant.maximum, vacant.total) == (70, 80)
    # A requirement whose every slot is vacant keeps its whole minimum as shortfall.
    narrow = [replace(requirements[0], slot_ids=("b",)), requirements[1]]
    emptied = ShortfallKernel(players, narrow, formation, quantization=100)
    assert oracle(players, narrow, formation, scale=100, vacant=("b",))["value"] == (100, 100)
    lone = emptied.value(vacant=("b",), deadline=far())
    assert (lone.status, lone.maximum, lone.total, lone.lineup) == (
        "CERTIFIED", 100, 100, (("a", 2),))
    assert emptied.satisfiable(vacant=("b",), deadline=far()).status == "NOT_SATISFIABLE"
    after = kernel.value(deadline=far())
    assert (after.maximum, after.total, after.lineup) == (base.maximum, base.total, base.lineup)


def test_invalid_inputs_are_errors_before_any_solve(monkeypatch):
    players, requirements, formation = pair()
    calls = []
    monkeypatch.setattr(engine, "_solver", lambda *a: calls.append(a))
    kernel = ShortfallKernel(players, requirements, formation, quantization=100)
    bad_calls = [
        dict(excluded=(99,)),
        dict(locked=("1",)),
        dict(pinned={99: "a"}),
        dict(pinned={1: "zz"}),
        dict(vacant=("zz",)),
        dict(values={1: {"m": float("nan"), "n": 0.1}}),
        dict(values={1: {"m": 1e13, "n": 0.1}}),
    ]
    for declared in bad_calls:
        with pytest.raises(ValueError):
            kernel.value(**declared, deadline=far())
        with pytest.raises(ValueError):
            kernel.satisfiable(**declared, deadline=far())
    with pytest.raises(ValueError):
        kernel.value(deadline=float("nan"))
    hard = [replace(requirements[0], hard=True), requirements[1]]
    strict = ShortfallKernel(players, hard, formation, quantization=100)
    with pytest.raises(ValueError, match="use satisfiable"):
        strict.value(deadline=far())
    for arguments in (
        dict(quantization=0),
        dict(quantization=1.0),
        dict(seed=-1),
        dict(formation="5-5-5"),
        dict(candidates=[*players, players[0]]),
        dict(requirements=[*requirements, requirements[0]]),
        dict(requirements=[replace(requirements[0], slot_ids=("zz",))]),
    ):
        merged = dict(candidates=players, requirements=requirements, formation=formation,
                      quantization=100) | arguments
        with pytest.raises(ValueError):
            ShortfallKernel(merged.pop("candidates"), merged.pop("requirements"), **merged)
    # A normaliser so small that the float quotient overflows is an input error like any other.
    tiny = ShortfallKernel(players, [replace(requirements[0], normalizer=1e-320)], formation)
    for method in (tiny.value, tiny.satisfiable):
        with pytest.raises(ValueError, match="too large"):
            method(deadline=far())
    assert calls == []
    # A level that is not a certified value of the same declarations is refused, not answered.
    monkeypatch.undo()
    level = kernel.value(deadline=far())
    with pytest.raises(ValueError, match="does not belong"):
        kernel.membership(level, [1], excluded=(1,), deadline=far())
    with pytest.raises(ValueError, match="does not belong"):
        kernel.shortfall_ranges(replace(level, total=level.total + 1), deadline=far())
    with pytest.raises(ValueError, match="CERTIFIED"):
        kernel.membership(kernel.value(excluded=(3,), deadline=far()), [1], deadline=far())
    with pytest.raises(ValueError, match="different quantization"):
        ShortfallKernel(players, requirements, formation).membership(level, [1], deadline=far())


def test_a_level_is_refused_under_looser_declarations_or_another_model():
    """The forgotten argument is the dangerous one: the witness of a tighter declaration is
    still an XI of the looser model, so only the record of what it was computed under tells."""
    players, requirements, formation = pair()
    kernel = ShortfallKernel(players, requirements, formation, quantization=100)
    assert oracle(players, requirements, formation, scale=100)["value"] == (40, 40)
    tighter = {
        "locked": dict(locked=(2,)),
        "pinned": dict(pinned={2: "a"}),
        "excluded": dict(excluded=(1,)),
        "values": dict(values={1: {"m": 0.0, "n": 0.0}}),
    }
    for name, declared in tighter.items():
        level = kernel.value(**declared, deadline=far())
        truth = oracle(players, requirements, formation, scale=100, **declared)
        assert (level.status, (level.maximum, level.total)) == ("CERTIFIED", truth["value"]), name
        assert truth["value"] == (60, 60) and level.lineup == (("a", 2), ("b", 3)), name
        # Not the least shortfall of the model without the declaration: refused, by both.
        with pytest.raises(ValueError, match="does not belong"):
            kernel.membership(level, [1, 2, 3], deadline=far())
        with pytest.raises(ValueError, match="does not belong"):
            kernel.shortfall_ranges(level, deadline=far())
        facts = kernel.membership(level, [1, 2, 3], **declared, deadline=far())
        assert facts == {
            pid: Membership(any(pid in s for s in truth["optimal_sets"]),
                            all(pid in s for s in truth["optimal_sets"]))
            for pid in (1, 2, 3)
        }, name
        assert kernel.shortfall_ranges(level, **declared, deadline=far()) == truth["ranges"], name
    # The level of a squad is not a level of that squad with one more player in it.
    smaller = ShortfallKernel(players[1:], requirements, formation, quantization=100)
    with pytest.raises(ValueError, match="does not belong"):
        kernel.membership(smaller.value(deadline=far()), [1], deadline=far())
    # Other spellings of the same declarations are the same declarations.
    level = kernel.value(locked=(2,), values={99: {"m": 1.0}}, deadline=far())
    again = kernel.membership(level, [2], locked=[2, 2], values={1: players[0].values},
                              deadline=far())
    assert again == {2: Membership(True, True)}
    mirrored = ShortfallKernel(players[::-1], requirements[::-1], formation, quantization=100)
    assert mirrored.membership(level, [2], locked=(2,), deadline=far()) == again


def test_each_rounding_policy_is_applied_to_its_own_quantity_where_float_and_exact_differ():
    # 0.005 * 100 and 0.015 * 100 are 0.5 and 1.5 in floating point (half-even: 0 and 2) but
    # just above 0.5 and just below 1.5 exactly (1 and 1). Shortfalls follow the shipped float
    # expression, so they equal solve_xi and not the exact oracle.
    players, requirements, formation = one_slot(0.005, 0.015)
    kernel = ShortfallKernel(players, requirements, formation, quantization=100)
    value = kernel.value(deadline=far())
    shipped = solve_xi(players, requirements, formation, quantization=100, analyze_ties=False)
    assert (value.maximum, value.total) == (2, 2)
    assert tuple(round(v * 100) for v in shipped.objective_vector) == (2, 2)
    assert oracle(players, requirements, formation, scale=100)["value"] == (0, 0)
    # 0.15 * 100 is 15.0 in floating point and just below 15 exactly. Hard statements use the
    # exact fractions: floor 14 against ceil 15, although the float product would say 15 >= 15.
    players, requirements, formation = one_slot(0.15, 0.15)
    kernel = ShortfallKernel(players, requirements, formation, quantization=100)
    assert 0.15 * 100 == 15.0 and Fraction(0.15) * 100 < 15
    assert oracle(players, requirements, formation, scale=100)["floor"] == "NOT_SATISFIABLE"
    assert kernel.satisfiable(deadline=far()).status == "NOT_SATISFIABLE"
    assert (kernel.value(deadline=far()).maximum, kernel.value(deadline=far()).total) == (0, 0)


# --------------------------------------------------------------------------- K6


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


def test_a_passed_deadline_is_unknown_with_no_solver_call(monkeypatch):
    players, requirements, formation = pair()
    kernel = ShortfallKernel(players, requirements, formation, quantization=100)
    level = kernel.value(deadline=far())
    calls = override_status(monkeypatch, 0, cp_model.UNKNOWN)
    late = time.monotonic() - 1.0
    value = kernel.value(deadline=late)
    assert (value.status, value.maximum, value.total, value.lineup, value.solves) == (
        "UNKNOWN", None, None, (), 0)
    assert value.stage_statuses == () and value.objective_vector is None
    floor = kernel.satisfiable(deadline=late)
    assert (floor.status, floor.lineup, floor.solves) == ("UNKNOWN", (), 0)
    # Even a declaration that is unfieldable by construction answers UNKNOWN once time is up.
    assert kernel.value(excluded=(3,), deadline=late).status == "UNKNOWN"
    assert kernel.membership(level, [1, 2, 3], deadline=late) == {
        1: Membership(True, None), 2: Membership(None, False), 3: Membership(True, None)}
    assert kernel.shortfall_ranges(level, deadline=late) == {"need_m": None, "need_n": None}
    assert calls == []
    # The shipped device: the clock passes the deadline after the first solve.
    clock = iter([0.0, 0.0, 0.0, 5.0, 5.0, 5.0])
    monkeypatch.setattr(engine.time, "monotonic", lambda: next(clock, 5.0))
    timed = kernel.value(deadline=1.0)
    assert (timed.status, timed.stage_statuses, timed.solves) == ("UNKNOWN", ("INFEASIBLE",), 1)
    assert len(calls) == 1


@pytest.mark.parametrize("forced,expected", [(cp_model.UNKNOWN, "UNKNOWN"),
                                             (cp_model.MODEL_INVALID, "MODEL_INVALID"),
                                             (cp_model.FEASIBLE, "UNKNOWN")])
def test_an_undecided_solve_never_becomes_a_value_or_a_proof_of_absence(
        monkeypatch, forced, expected):
    players, requirements, formation = pair()
    kernel = ShortfallKernel(players, requirements, formation, quantization=100)
    hall = one_player_for_two_slots()
    level = kernel.value(deadline=far())
    assert kernel.satisfiable(deadline=far()).status == "NOT_SATISFIABLE"
    # FEASIBLE at the feasibility stages is a real witness claim, so it is forced only where
    # an incumbent is "not a value": the two optimisation stages.
    stages = (2, 3) if forced == cp_model.FEASIBLE else (1, 2, 3)
    for on_call in stages:
        with monkeypatch.context() as patch:
            override_status(patch, on_call, forced)
            value = kernel.value(deadline=far())
            assert (value.status, value.maximum, value.total, value.lineup) == (
                expected, None, None, ()), on_call
            assert value.solves == on_call and value.reasons
    if forced == cp_model.FEASIBLE:
        return
    for on_call in (1, 2):
        for undecided in (kernel.satisfiable, hall.value, hall.satisfiable):
            with monkeypatch.context() as patch:
                override_status(patch, on_call, forced)
                assert undecided(deadline=far()).status == expected, (on_call, undecided)
    with monkeypatch.context() as patch:
        override_status(patch, 1, forced)
        facts = kernel.membership(level, [1, 2, 3], deadline=far())
        # Player 1 is in the witness and his opposite solve was undecided: necessity unknown.
        assert facts[1] == Membership(True, None)
        assert facts[2] == Membership(False, False) and facts[3] == Membership(True, True)
    with monkeypatch.context() as patch:
        override_status(patch, 2, forced)
        assert kernel.shortfall_ranges(level, deadline=far()) == {"need_m": None, "need_n": (0, 0)}


# ----------------------------------------------------------- lineage, evidence, hashes


def test_scrub_lineage_keeps_data_lineage_and_drops_every_prior_certification():
    source = Path(engine.__file__).parents[1] / "xi" / "tradeoffs.py"
    block = re.search(r"prior_certificate_keys = \{(.*?)\}", source.read_text("utf-8"), re.S)
    assert set(re.findall(r'"([a-z_]+)"', block.group(1))) == set(engine._PRIOR_CERTIFICATE_KEYS)
    dropped = {
        **{key: 1 for key in engine._PRIOR_CERTIFICATE_KEYS},
        **{prefix + "x": 1 for prefix in engine._CERTIFICATE_PREFIXES},
        "bootstrap_used_worlds": [1],
    }
    kept = {"cutoff": "2018-05-06", "bootstrap_version": "v1", "providers": ["pappalardo"],
            "training_latest_date": "2018-05-05", "seed": 7, 3: "non-string key"}
    assert scrub_lineage({**dropped, **kept}) == kept
    assert scrub_lineage(None) == {}


def test_evidence_composes_to_the_weakest_class_and_is_never_stronger_than_eligibility():
    measured = TacticalRequirement("a", "a", "a", 1.0, 1.0, evidence_class="MEASURED")
    research = TacticalRequirement("b", "b", "b", 1.0, 1.0, evidence_class="RESEARCH")
    idle = TacticalRequirement("c", "c", "c", 1.0, 1.0, (), "RESEARCH", False, "research")
    assert compose_evidence([measured, idle]) == {
        "per_requirement": {"a": "ESTIMATED"},
        "eligibility": "HEURISTIC",
        "composed": "HEURISTIC",
        "declared_inputs": [],
    }
    both = compose_evidence([research, measured])
    assert both["per_requirement"] == {"a": "ESTIMATED", "b": "EXPERIMENTAL"}
    assert both["composed"] == "EXPERIMENTAL"
    assert compose_evidence([measured], EvidenceClass.DERIVED)["composed"] == "HEURISTIC"
    assert compose_evidence([], EvidenceClass.EXPERIMENTAL)["composed"] == "EXPERIMENTAL"
    with pytest.raises(ValueError):
        compose_evidence([measured], "HEURISTIC")


def test_contract_hashes_are_canonical_and_results_carry_no_merit_key(tmp_path):
    players, requirements, formation = pair()
    kernel = ShortfallKernel(players, requirements, formation, quantization=100)
    contract = kernel.input_contract
    assert fingerprint(contract) == fingerprint(kernel.input_contract)
    contract["quantization"] = 1  # a caller's copy cannot alter the kernel's contract
    assert kernel.input_contract["quantization"] == 100
    changed = [
        ShortfallKernel(players, requirements, formation, quantization=1000),
        ShortfallKernel(players, requirements, formation, quantization=100, seed=1),
        ShortfallKernel(players[:2], requirements, formation, quantization=100),
        ShortfallKernel(players, [replace(requirements[0], minimum=1.5), requirements[1]],
                        formation, quantization=100),
        ShortfallKernel([replace(players[0], values={"m": 0.31, "n": 0.5}), *players[1:]],
                        requirements, formation, quantization=100),
    ]
    hashes = {fingerprint(k.input_contract) for k in changed} | {fingerprint(kernel.input_contract)}
    assert len(hashes) == len(changed) + 1
    sources = kernel.input_contract["source_fingerprints"]
    assert set(sources) == {
        "galactico/optimization/squad/kernel.py",
        "galactico/optimization/xi/domain.py",
        "galactico/optimization/xi/solver.py",
        "galactico/optimization/xi/tradeoffs.py",
    }
    windows, unix = tmp_path / "crlf.py", tmp_path / "lf.py"
    windows.write_bytes(b"a = 1\r\nb = 2\r\n")
    unix.write_bytes(b"a = 1\nb = 2\n")
    assert source_fingerprints(str(windows))["crlf.py"] == source_fingerprints(str(unix))["lf.py"]
    assert fingerprint({"b": 1, "a": 2}) == fingerprint({"a": 2, "b": 1})
    with pytest.raises(ValueError):
        fingerprint({"a": float("nan")})
    value, floor = kernel.value(deadline=far()), kernel.satisfiable(deadline=far())
    for result in (value, floor, Membership(True, False)):
        assert not BANNED_KEYS & set(asdict(result))
    assert isinstance(value, KernelValue) and "encoded" not in asdict(value)


# ------------------------------------------------------------------- real scenario


def madrid(formation, worlds=0):
    from galactico.api.decision_lab import decision_inputs
    from galactico.optimization.historical import PUBLIC, load_snapshot

    required = [
        PUBLIC / "players.parquet",
        *[PUBLIC / "competition=Spain" / name
          for name in ("actions.parquet", "matches.parquet", "lineups.parquet")],
    ]
    if not all(path.exists() for path in required):
        pytest.skip("public historical corpus not downloaded")
    snapshot = load_snapshot(2565907, worlds=worlds)
    return (*decision_inputs(snapshot, formation), snapshot)


# Spec section 10.3, level 1 (integers in units of 1e-5); every other removal is (0, 0).
MADRID_REMOVALS = {
    "4-3-3": {3310: (12709, 19483), 4501: (9300, 9300)},
    "4-3-1-2": {3309: (331, 331), 3310: (12709, 19483), 3563: (2176, 2176),
                4501: (32389, 32389), 8287: (918, 918)},
}


@pytest.mark.slow
@pytest.mark.parametrize("formation", ["4-3-3", "4-3-1-2"])
def test_madrid_baseline_and_every_single_removal_equal_solve_xi_and_the_oracle(formation):
    from galactico.optimization.xi.domain import FORMATIONS

    players, requirements, _ = madrid(formation)
    shape = FORMATIONS[formation]
    scale = 100_000
    kernel = ShortfallKernel(players, requirements, formation)
    ids = sorted(p.player_id for p in players)
    assert len(ids) == 16
    table = {}
    for removed in [(), *((pid,) for pid in ids)]:
        value = kernel.value(excluded=removed, deadline=far())
        truth = oracle(players, requirements, shape, scale=scale, excluded=removed)
        shipped = solve_xi(players, requirements, formation, excluded=removed, analyze_ties=False)
        assert shipped.solution_status == "OPTIMAL" and value.status == "CERTIFIED", removed
        integers = (value.maximum, value.total)
        assert integers == truth["value"], removed
        assert integers == tuple(round(v * scale) for v in shipped.objective_vector), removed
        assert value.lineup in truth["optimal_lineups"], removed
        floor = kernel.satisfiable(excluded=removed, deadline=far())
        assert floor.status == truth["floor"], removed
        table[removed] = integers
    assert table[()] == (0, 0)
    assert {r[0]: v for r, v in table.items() if r and v != (0, 0)} == MADRID_REMOVALS[formation]
    # Membership and ranges of the level set, baseline and the largest single removal.
    for removed in ((), (3310,)):
        level = kernel.value(excluded=removed, deadline=far())
        truth = oracle(players, requirements, shape, scale=scale, excluded=removed)
        facts = kernel.membership(level, ids, excluded=removed, deadline=far())
        assert facts == {
            pid: Membership(any(pid in s for s in truth["optimal_sets"]),
                            all(pid in s for s in truth["optimal_sets"]))
            for pid in ids
        }
        assert kernel.shortfall_ranges(level, excluded=removed, deadline=far()) == truth["ranges"]
    if formation == "4-3-3":
        baseline = oracle(players, requirements, shape, scale=scale)
        assert baseline["feasible"] == 5200  # ordered assignments, maps/xi-core.md 4(c)
        assert len({frozenset(s) for s in baseline["optimal_sets"]}) == 120
        assert kernel.satisfiable(deadline=far()).status == "SATISFIABLE"


@pytest.mark.slow
def test_madrid_shipped_float_rounding_equals_exact_half_even_including_worlds():
    """K9: the two readings of "half-even" coincide on every coefficient and target."""
    players, requirements, snapshot = madrid("4-3-3", worlds=40)
    active = [r for r in requirements if r.active]
    assert len(active) == 3 and len(snapshot.worlds) == 40
    vectors = [p.values for p in players]
    vectors += [vector for world in snapshot.worlds.values() for vector in world.values()]
    checked = 0
    for scale in (100, 1000, 100_000):
        for requirement in active:
            numbers = [requirement.minimum]
            numbers += [v[requirement.metric] for v in vectors
                        if v.get(requirement.metric) is not None]
            for number in numbers:
                exact = round(Fraction(number) / Fraction(requirement.normalizer) * scale)
                assert engine._q(number, requirement.normalizer, scale) == exact
                checked += 1
    assert checked >= 3 * 3 * (len(players) + 1)


# Spec section 10.3, level 2, 4-3-3: the pairs whose removal leaves no XI in the gated model.
MADRID_UNFIELDABLE_PAIRS = {
    (3304, 3306), (3304, 3309), (3304, 3310), (3304, 4501), (3306, 3309), (3306, 3310),
    (3306, 4501), (3309, 3310), (3309, 4501), (3310, 4501), (3563, 8287), (3563, 14723),
    (3563, 40756), (3785, 3915), (8287, 14723), (8287, 40756), (14723, 40756),
}


@pytest.mark.slow
def test_madrid_every_pair_removal_equals_the_oracle_and_solve_xi():
    from galactico.optimization.xi.domain import FORMATIONS

    players, requirements, _ = madrid("4-3-3")
    scale = 100_000
    kernel = ShortfallKernel(players, requirements, "4-3-3")
    ids = sorted(p.player_id for p in players)
    table = {}
    for removed in itertools.combinations(ids, 2):
        value = kernel.value(excluded=removed, deadline=far())
        truth = oracle(players, requirements, FORMATIONS["4-3-3"], scale=scale, excluded=removed)
        # The shipped solver on every pair: with the 17 sets of level 1, all 136 of spec 10.3.
        shipped = solve_xi(players, requirements, "4-3-3", excluded=removed, analyze_ties=False)
        if truth["value"] is None:
            assert (value.status, value.maximum, value.total) == ("UNFIELDABLE", None, None)
            assert shipped.solution_status == "INFEASIBLE", removed
        else:
            assert value.status == "CERTIFIED", removed
            assert (value.maximum, value.total) == truth["value"], removed
            assert value.lineup in truth["optimal_lineups"], removed
            assert shipped.solution_status == "OPTIMAL", removed
            assert tuple(round(v * scale) for v in shipped.objective_vector) == truth["value"]
        assert kernel.satisfiable(excluded=removed, deadline=far()).status == truth["floor"]
        table[removed] = truth["value"]
    assert len(table) == 120
    unfieldable = {removed for removed, value in table.items() if value is None}
    assert unfieldable == MADRID_UNFIELDABLE_PAIRS
    assert sum(value not in (None, (0, 0)) for value in table.values()) == 30
    worst = max(value for value in table.values() if value is not None)
    assert worst == (32389, 32389)
    assert [removed for removed, value in table.items() if value == worst] == [(4498, 4501)]
