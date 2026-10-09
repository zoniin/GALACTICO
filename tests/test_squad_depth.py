"""Slot depth against set comprehensions and enumerations typed from the definition.

The oracle recomputes every stage with list comprehensions over the snapshot's own records,
finds kappa by searching player subsets (the module takes a minimum over slot subsets: the two
share no arithmetic), and finds pinned values by enumerating XIs with exact ``Fraction``
half-even integers. Snapshots are built directly as ``TeamSnapshot`` objects; no corpus.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import asdict, replace
from fractions import Fraction

import pytest
from ortools.sat.python import cp_model

import galactico.optimization.squad.depth as depth_module
import galactico.optimization.squad.kernel as engine
from galactico.optimization.snapshots import (
    ELIGIBILITY_RULESETS,
    PROVIDER_POSITION_VERSION,
    SHIPPED_METRICS,
    EligibilityRuleSet,
    TeamSnapshot,
    snapshot_inputs,
)
from galactico.optimization.squad.depth import PROVIDER_POSITION_WARNING, STAGES, squad_depth
from galactico.optimization.squad.stress import absence_stress
from galactico.optimization.xi.domain import Formation, Slot

METRICS = ("progression", "left_pass_origins", "right_pass_origins")
KEEPER = Slot("g", "Keeper", ("GK",), 0.5, 0.9)
BACK_A = Slot("a", "Back A", ("DF",), 0.3, 0.7)
BACK_B = Slot("b", "Back B", ("DF",), 0.7, 0.7)
FRONT = Slot("c", "Front", ("MF", "FW"), 0.5, 0.2)
FOUR = Formation("four", (KEEPER, BACK_A, BACK_B, FRONT))
THREE = Formation("three", (KEEPER, BACK_A, FRONT))
# Role "x" names a back slot and the front slot: for any one position, one of them is a
# slot the position code does not allow.
ROLE_SLOTS = {"g": ("g",), "ab": ("a", "b"), "a": ("a",), "b": ("b",), "c": ("c",),
              "x": ("c", "a")}
MANUAL = EligibilityRuleSet(
    version="synthetic-manual-v1", kind="MANUAL_REVIEWED", review_status="REVIEWED",
    team_id=1, competition="Synth", role_rules={}, role_slots=ROLE_SLOTS,
    evidence_class="HEURISTIC", banner="synthetic manual rules")
PROVIDER = replace(ELIGIBILITY_RULESETS[PROVIDER_POSITION_VERSION], role_slots=ROLE_SLOTS)


def record(pid, position, minutes, roles=(), values=None):
    row = dict(player_id=pid, name=f"N{pid}", position=position, minutes=minutes,
               role_rules=tuple(roles))
    if values is not None:
        row["values"] = {"chance_creation": None, **dict.fromkeys(METRICS), **values}
    return row


def make_snapshot(rows, minima, rules, reverse=False):
    """Apply the shipped omission rule to the rows and wrap them as a snapshot."""
    manual = rules.kind == "MANUAL_REVIEWED"
    candidates, omitted = [], []
    for row in rows:
        unreviewed = manual and not row["role_rules"]
        if unreviewed or (row["position"] != "GK" and row["minutes"] < 900):
            reason = "unreviewed eligibility" if unreviewed else "below 900 prior minutes"
            omitted.append({k: v for k, v in row.items() if k != "values"} | {"reason": reason})
        else:
            candidates.append(row)
    if reverse:
        candidates, omitted = candidates[::-1], omitted[::-1]
    return TeamSnapshot(
        kind="DATE", team_id=1, competition="Synth", match_id=None,
        cutoff="2018-05-21T00:00:00", cutoff_date="2018-05-21", label="Synth before 2018-05-21",
        candidates=tuple(candidates), omitted=tuple(omitted), requirement_minima=dict(minima),
        worlds={}, world_scheme="TEAM_MATCHES", world_namespace="", prior_starters=(),
        prior_minutes={}, eligibility=rules, metrics=SHIPPED_METRICS, facts={},
        provenance={"dataset_hash": "synthetic", "providers": ["pappalardo"],
                    "solver_stages": ["old"], "depth_version": "old", "bootstrap_worlds": 0},
    )


# ---------------------------------------------------------------------------- oracle


def exact(value, normalizer, scale):
    return round(Fraction(value) / Fraction(normalizer) * scale)


def chain(snapshot, slot, metrics, excluded):
    """The stages of spec 4.2, each a list comprehension over the snapshot's records."""
    manual = snapshot.eligibility.kind == "MANUAL_REVIEWED"
    roles = snapshot.eligibility.role_slots
    roster = sorted([*snapshot.candidates, *snapshot.omitted], key=lambda p: p["player_id"])
    needed = metrics if slot.allowed_positions != ("GK",) else ()
    position = [p for p in roster if p["position"] in slot.allowed_positions]
    rule = [p for p in position
            if not manual or any(slot.slot_id in roles[r] for r in p["role_rules"])]
    gated = [p for p in rule if p["position"] == "GK" or p["minutes"] >= 900]
    # The solver also refuses a player without one recorded minute.
    measured = [p for p in gated
                if p["minutes"] > 0 and all(p["values"][m] is not None for m in needed)]
    available = [p for p in measured if p["player_id"] not in excluded]
    ids = lambda rows: [p["player_id"] for p in rows]  # noqa: E731
    return {
        "position_admissible": ids(position), "rule_eligible": ids(rule), "gated": ids(gated),
        "measured": ids(measured), "available": ids(available),
        "unreviewed": ids([p for p in position if p not in rule and not p["role_rules"]]),
        "other_slot": ids([p for p in position if p not in rule and p["role_rules"]]),
        "below_gate": ids([p for p in rule if p not in gated]),
        "unmeasured": ids([p for p in gated if p not in measured]),
        "excluded": ids([p for p in measured if p not in available]),
    }


def fillable(slot_sets, gone=frozenset()):
    def walk(index, used):
        if index == len(slot_sets):
            return True
        return any(walk(index + 1, used | {pid})
                   for pid in slot_sets[index] if pid not in used and pid not in gone)

    return walk(0, frozenset())


def brute_kappa(slot_sets):
    """Smallest number of removed players that leaves the slots unfillable; 0 if already so."""
    players = sorted(set().union(*slot_sets))
    for size in range(len(players) + 1):
        broken = [set(gone) for gone in itertools.combinations(players, size)
                  if not fillable(slot_sets, set(gone))]
        if broken:
            return size, {frozenset(gone) for gone in broken}
    raise AssertionError("removing every player always leaves a slot empty")


def least(snapshot, formation, metrics, minima, scale, available, locked=(), pin=None):
    """Least (maximum, total) over every XI of the available players, or None."""
    by_id = {p["player_id"]: p for p in snapshot.candidates}
    pool = sorted(set().union(*available.values()))
    slots = formation.slots
    best = None
    for xi in itertools.permutations(pool, len(slots)):
        if any(pid not in available[s.slot_id] for pid, s in zip(xi, slots, strict=True)):
            continue
        if not set(locked) <= set(xi):
            continue
        if pin is not None and xi[[s.slot_id for s in slots].index(pin[1])] != pin[0]:
            continue
        short = []
        for metric in metrics:
            normalizer = snapshot.requirement_minima[metric]
            total = sum(exact(by_id[pid]["values"][metric], normalizer, scale)
                        for pid, s in zip(xi, slots, strict=True)
                        if s.allowed_positions != ("GK",))
            short.append(max(0, exact(minima.get(metric, normalizer), normalizer, scale) - total))
        value = (max(short, default=0), sum(short))
        best = value if best is None or value < best else best
    return best


def near_half(value, normalizer, scale):
    part = Fraction(value) / Fraction(normalizer) * scale % 1
    return abs(part - Fraction(1, 2)) < Fraction(1, 10**9)


def instance(rng, number):
    formation = FOUR if number % 3 else THREE
    rules = PROVIDER if number % 3 == 1 else MANUAL
    while True:
        scale = rng.choice((8, 100, 100_000))
        rows = []
        for pid in range(1, rng.randint(6, 9) + 1):
            position = rng.choice(("GK", "DF", "DF", "DF", "MF", "FW"))
            minutes = rng.choice((300, 899, 900, 1500, 2000, 2400))
            roles = ()
            if rules is MANUAL and rng.random() >= 0.15:
                roles = rng.choice({
                    "GK": (("g",),), "DF": (("ab",), ("ab",), ("a",), ("b",), ("x",), ("a", "x")),
                    "MF": (("c",), ("c",), ("x",)), "FW": (("c",), ("c",), ("x",)),
                }[position])
            values = {}
            if position != "GK":
                values = {m: round(rng.uniform(0.2, 1.6), 3) for m in METRICS}
                if rng.random() < 0.12:
                    values[rng.choice(METRICS)] = None
            rows.append(record(pid, position, minutes, roles, values))
        outfield = len(formation.slots) - 1
        minima = {m: round(outfield * rng.uniform(0.6, 1.1), 3) for m in METRICS}
        numbers = [(minima[m], minima[m]) for m in METRICS]
        numbers += [(row["values"][m], minima[m]) for row in rows for m in METRICS
                    if row["values"][m] is not None]
        if not any(near_half(v, n, scale) for v, n in numbers):
            return make_snapshot(rows, minima, rules), formation, scale


def test_depth_equals_the_definition_on_seeded_snapshots(thesis_guard):
    rng = random.Random(20261011)
    seen = {key: 0 for key in (
        "unreviewed", "other_slot", "below_gate", "unmeasured", "excluded", "NEUTRAL",
        "RAISES_SHORTFALL", "UNFIELDABLE_IF_PINNED", "conflict", "unfieldable_squad",
        "stress_link", "equivalent", "gate_lowers_kappa", "locked")}
    kappas = set()
    for number in range(40):
        snapshot, formation, scale = instance(rng, number)
        opt_in = number % 2 == 0
        metrics = METRICS if opt_in else METRICS[:1]
        ids = [p["player_id"] for p in snapshot.candidates]
        excluded = (rng.choice(ids),) if number % 4 == 3 else ()
        minimums = {"progression": round(snapshot.requirement_minima["progression"] * 1.2, 3)} \
            if number % 5 == 2 else {}
        truth = {s.slot_id: chain(snapshot, s, metrics, excluded) for s in formation.slots}
        available = {sid: set(stages["available"]) for sid, stages in truth.items()}
        squad = least(snapshot, formation, metrics, minimums, scale, available)
        locked = ()
        if number % 5 == 0 and squad is not None:
            fielded = [pid for pid in ids if least(snapshot, formation, metrics, minimums, scale,
                                                   available, locked=(pid,)) is not None]
            locked = (rng.choice(fielded),)
            squad = least(snapshot, formation, metrics, minimums, scale, available, locked)
        result = squad_depth(snapshot, formation, minimums=minimums or None, locked=locked,
                             excluded=excluded, experimental_opt_in=opt_in, quantization=scale,
                             time_limit=600.0)
        thesis_guard(asdict(result))
        assert [s.slot_id for s in result.slots] == [s.slot_id for s in formation.slots]
        certificate = result.certificate
        assert certificate.squad_integer == squad and certificate.completeness == "EXACT"
        assert certificate.squad_status == ("UNFIELDABLE" if squad is None else "CERTIFIED")
        for slot in result.slots:
            stages = truth[slot.slot_id]
            got = {
                "position_admissible": slot.position_admissible,
                "unreviewed": slot.not_rule_eligible_unreviewed,
                "other_slot": slot.not_rule_eligible_other_slot,
                "below_gate": slot.below_gate, "unmeasured": slot.unmeasured,
                "excluded": slot.excluded, "available": slot.available,
            }
            for key, rows in got.items():
                assert [p.player_id for p in rows] == stages[key], (number, slot.slot_id, key)
                if key in seen:
                    seen[key] += bool(rows)
            assert {stage: slot.counts[stage] for stage in STAGES} == {
                stage: len(stages[stage]) for stage in STAGES}
            # D1: the stages are nested and the dropped lists partition what is not neutral.
            nested = [set(stages[stage]) for stage in STAGES]
            assert all(inner <= outer for outer, inner in itertools.pairwise(nested))
            neutral = {p.player_id for p in slot.pinned if p.status == "NEUTRAL"}
            dropped = [p.player_id for key in ("unreviewed", "other_slot", "below_gate",
                                               "unmeasured", "excluded") for p in got[key]]
            dropped += [p.player_id for p in slot.pinned if p.status != "NEUTRAL"]
            if squad is None:
                assert slot.pinned == () and slot.counts["shortfall_neutral"] is None
            else:
                assert len(dropped) == len(set(dropped))
                assert set(dropped) | neutral == set(stages["position_admissible"])
                assert not set(dropped) & neutral
                assert slot.counts["shortfall_neutral"] == len(neutral)
                assert [p.player_id for p in slot.pinned] == stages["available"]
            for pin in slot.pinned:
                value = least(snapshot, formation, metrics, minimums, scale, available, locked,
                              pin=(pin.player_id, slot.slot_id))
                # D4 and D5: NEUTRAL iff the enumeration with the pin equals the squad's.
                expected = ("UNFIELDABLE_IF_PINNED" if value is None
                            else "NEUTRAL" if value == squad else "RAISES_SHORTFALL")
                assert (pin.status, pin.integer_vector) == (expected, value), (number, pin)
                assert value is None or value >= squad
                seen[pin.status] += 1
            assert slot.exclusive_ids == tuple(
                pid for pid in stages["available"]
                if sum(pid in other["available"] for other in truth.values()) == 1)
            seen["equivalent"] += bool(slot.equivalent_slot_ids)
            for other in slot.equivalent_slot_ids:
                assert truth[other]["available"] == stages["available"]
        # D2: every omitted player, with the snapshot's reason, in a dropped list of every
        # slot his position admits.
        assert [(p.player_id, p.reason) for p in result.omitted] == sorted(
            (p["player_id"], p["reason"]) for p in snapshot.omitted)
        for gone in snapshot.omitted:
            for slot, shape in zip(result.slots, formation.slots, strict=True):
                listed = [p.player_id for p in (*slot.below_gate,
                                                *slot.not_rule_eligible_unreviewed,
                                                *slot.not_rule_eligible_other_slot)]
                assert (gone["player_id"] in listed) == (
                    gone["position"] in shape.allowed_positions)
        manual = snapshot.eligibility.kind == "MANUAL_REVIEWED"
        conflicts = {
            p["player_id"]: tuple(
                s.slot_id for s in formation.slots
                if any(s.slot_id in ROLE_SLOTS[r] for r in p["role_rules"])
                and p["position"] not in s.allowed_positions)
            for p in (*snapshot.candidates, *snapshot.omitted) if manual}
        assert {p.player_id: p.detail for p in result.rule_position_conflicts} == {
            pid: slots for pid, slots in conflicts.items() if slots}
        seen["conflict"] += bool(result.rule_position_conflicts)
        assert (PROVIDER_POSITION_WARNING in result.warnings) == (not manual)

        # kappa by searching player subsets, at every stage.
        for stage in STAGES:
            size, _ = brute_kappa([set(truth[s.slot_id][stage]) for s in formation.slots])
            kappa = result.kappa_by_stage[stage]
            assert kappa == size if size else kappa <= 0, (number, stage)
        seen["gate_lowers_kappa"] += (result.kappa_by_stage["gated"]
                                      < result.kappa_by_stage["rule_eligible"])
        kappa = result.kappa_by_stage["available"]
        kappas.add(kappa)
        size, broken = brute_kappa([available[s.slot_id] for s in formation.slots])
        seen["unfieldable_squad"] += squad is None
        seen["locked"] += bool(locked)
        if squad is None and not locked:
            assert kappa <= 0 and any(g.spare_by_stage["available"] < 0
                                      for g in result.tight_groups)
            continue
        # D3: the smallest sets that leave no XI are the kappa-subsets of the tight groups.
        predicted = {frozenset(gone) for group in result.tight_groups
                     for gone in itertools.combinations(group.available_ids, kappa)}
        assert predicted == broken and size == kappa
        for group in result.tight_groups:
            cover = [truth[sid] for sid in group.slot_ids]
            assert set(group.available_ids) == set().union(*(c["available"] for c in cover))
            assert group.spare_by_stage["available"] == kappa - 1
            assert {stage: len(set().union(*(c[stage] for c in cover))) - len(cover)
                    for stage in STAGES} == dict(group.spare_by_stage)
            assert set(group.restored_by_gate_ids) == set().union(
                *(c["below_gate"] for c in cover))
        assert list(result.tight_groups) == sorted(result.tight_groups, key=lambda g: g.slot_ids)
        # The groups are every inclusion-maximal slot subset of least spare, by enumeration.
        order = [s.slot_id for s in formation.slots]
        spares = {
            subset: len(set().union(*(available[sid] for sid in subset))) - len(subset)
            for size in range(1, len(order) + 1)
            for subset in itertools.combinations(order, size)}
        tightest = [subset for subset, spare in spares.items() if spare == kappa - 1]
        assert {g.slot_ids for g in result.tight_groups} == {
            subset for subset in tightest
            if not any(set(subset) < set(other) for other in tightest)}
        if locked or kappa > 3:
            continue
        # D3 / A9 against the stress tool: its first level with an unfieldable set is kappa.
        players, requirements = snapshot_inputs(snapshot, formation, minimums=minimums or None,
                                                experimental_opt_in=opt_in)
        stress = absence_stress(players, requirements, formation, k=kappa, allow_k3=True,
                                excluded=excluded, quantization=scale, time_limit=600.0)
        assert stress.certificate.baseline_integer == squad
        assert [lv.unfieldable_count > 0 for lv in stress.levels] == [False] * (kappa - 1) + [True]
        assert {frozenset(row.player_ids) for row in stress.table
                if len(row.player_ids) == kappa and row.status == "UNFIELDABLE"} == predicted
        seen["stress_link"] += 1
    assert all(seen.values()), seen
    assert len(kappas) >= 3, kappas


# ------------------------------------------------------------------ hand-built cases

HAND_MINIMA = dict.fromkeys(METRICS, 4.0)


def hand_rows(front_value=None):
    one = dict.fromkeys(METRICS, 1.0)
    return [
        record(1, "GK", 810, ("g",), {}),  # below 900, exempt: the shipped keeper rule
        record(2, "GK", 0, ("g",), {}),  # a keeper without one recorded minute
        record(3, "DF", 1200, ("ab",), one),
        record(4, "DF", 1300, ("ab",), one),
        record(5, "DF", 400, ("ab",)),
        record(6, "MF", 1000, ()),
        record(7, "FW", 500, ("c",)),
        record(8, "DF", 1500, ("x",), one),  # "x" also names the front slot, which bars a DF
        record(9, "MF", 1100, ("c",), {**one, "progression": front_value}),
    ]


def test_gate_rule_and_measurement_drops_are_named_separately_on_a_hand_built_squad():
    result = squad_depth(make_snapshot(hand_rows(), HAND_MINIMA, MANUAL), FOUR, quantization=100)
    keeper, back_a, back_b, front = result.slots
    # A goalkeeper below 900 minutes stays available, and the gate statement says why.
    assert [p.player_id for p in keeper.available] == [1] and keeper.below_gate == ()
    assert "goalkeepers exempt (shipped rule)" in result.gate_statement
    assert result.provenance["gate_statement"] == result.gate_statement
    assert [(p.player_id, p.detail) for p in keeper.unmeasured] == [(2, ("no recorded minutes",))]
    # The front slot: nobody available, each drop under its own cause, the gated one named.
    assert front.available == () and front.counts == {
        "position_admissible": 3, "rule_eligible": 2, "gated": 1, "measured": 0, "available": 0,
        "shortfall_neutral": None}
    assert [(p.player_id, p.reason) for p in front.not_rule_eligible_unreviewed] == [
        (6, "unreviewed eligibility")]
    assert [(p.player_id, p.minutes, p.reason) for p in front.below_gate] == [
        (7, 500, "below 900 prior minutes")]
    assert [(p.player_id, p.detail) for p in front.unmeasured] == [(9, ("progression",))]
    assert front.claim == (
        "0 players can fill Front in this model. 1 more is admitted by position but not by the "
        "eligibility rule set, 1 more is eligible but below the 900-minute evidence gate (N7). "
        "Whether any of them raises the least declared shortfall when used there was not "
        "established. 1 more lacks a measurement the slot needs.")
    # Back A: player 8 is reviewed for it; at Back B he is reviewed for other slots, and the
    # detail is what his rules name (the front slot too, which his position then bars).
    assert [p.player_id for p in back_a.available] == [3, 4, 8]
    assert [(p.player_id, p.detail) for p in back_b.not_rule_eligible_other_slot] == [
        (8, ("a", "c"))]
    assert [p.player_id for p in back_a.below_gate] == [5] == [
        p.player_id for p in back_b.below_gate]
    assert back_a.equivalent_slot_ids == () and back_b.exclusive_ids == ()
    assert [(p.player_id, p.detail) for p in result.rule_position_conflicts] == [(8, ("c",))]
    assert [(p.player_id, p.reason, p.detail) for p in result.omitted] == [
        (5, "below 900 prior minutes", ("a", "b")), (6, "unreviewed eligibility", ()),
        (7, "below 900 prior minutes", ("c",))]
    # No XI before any absence: stage five is skipped and the short slot group explains it.
    assert result.certificate.squad_status == "UNFIELDABLE"
    assert result.certificate.completeness == "EXACT" and result.certificate.pinned_solved == 0
    assert all(slot.pinned == () for slot in result.slots)
    assert dict(result.kappa_by_stage) == {
        "position_admissible": 2, "rule_eligible": 2, "gated": 1, "measured": 0, "available": 0}
    # The inclusion-maximal group of least spare: the front slot alone is one short, and so
    # is the front slot taken with the keeper slot (one keeper, nobody in front, two slots).
    (group,) = result.tight_groups
    assert group.slot_ids == ("g", "c") and group.available_ids == (1,)
    assert group.spare_by_stage == {"position_admissible": 3, "rule_eligible": 2, "gated": 1,
                                    "measured": -1, "available": -1}
    assert group.restored_by_gate_ids == (7,)
    assert any(w.startswith("The squad has no fieldable XI in this model before any absence")
               for w in result.warnings)
    assert any("The gate removed N7." in w for w in result.warnings)
    assert any("fewest absences that leave no fieldable XI from 2 to 1" in w
               for w in result.warnings)
    # A warning is read by a person: the docstring's symbol never appears in one.
    assert not any("kappa" in w for w in result.warnings)


def test_pinned_values_declared_inputs_and_fingerprints_on_a_fieldable_squad(thesis_guard):
    rows = hand_rows(front_value=0.4)
    snapshot = make_snapshot(rows, HAND_MINIMA, MANUAL)
    result = squad_depth(snapshot, FOUR, quantization=100)
    payload = asdict(result)
    thesis_guard(payload)
    assert not any("world" in key for part in (payload, payload["certificate"],
                                               payload["slots"][0], payload["evidence"])
                   for key in part if key != "provenance")
    # Progression only: 1.0 + 1.0 + 0.4 of a minimum of 4.0 leaves 0.4 of the normaliser.
    assert result.certificate.squad_integer == (40, 40)
    assert result.certificate.squad_objective == (0.4, 0.4)
    assert result.evidence["per_requirement"] == {"progression": "HEURISTIC"}
    assert result.evidence["composed"] == "HEURISTIC"
    assert result.evidence["binding"] == ["progression", "eligibility"]
    scope = result.evidence["requirement_scope"]
    assert scope.startswith("Requirements in force: Positive completed-pass xT per 90. "
                            "Not in force: Left wide-channel pass origins per 90; ")
    assert "left_pass_origins" not in scope  # a sentence names labels; ids are fields
    assert {row["name"] for row in result.evidence["declared_inputs"]} == {
        "formation", "minimums", "locked", "excluded", "experimental_opt_in"}
    keeper, back_a, back_b, front = result.slots
    assert [(p.player_id, p.status) for p in front.pinned] == [(9, "NEUTRAL")]
    assert front.exclusive_ids == (9,) and keeper.exclusive_ids == (1,)
    assert all(p.status == "NEUTRAL" for slot in result.slots for p in slot.pinned)
    assert back_b.claim == (
        "2 players can fill Back B in this model. 1 more is admitted by position but not by "
        "the eligibility rule set, 1 more is eligible but below the 900-minute evidence gate "
        "(N5), and 0 of the 2 raise the least declared shortfall when used there.")
    assert dict(result.kappa_by_stage)["available"] == 1
    # One keeper and one front player: either absence leaves no XI, and the two tight slots
    # are reported as the one inclusion-maximal group they form.
    assert [(g.slot_ids, g.available_ids) for g in result.tight_groups] == [(("g", "c"), (1, 9))]
    opted = squad_depth(snapshot, FOUR, quantization=100, experimental_opt_in=True)
    assert opted.evidence["composed"] == "EXPERIMENTAL"
    assert opted.evidence["binding"] == ["left_pass_origins", "right_pass_origins"]
    # Each side requirement sums to 3.0 of 4.0: a quarter short, twice, beside the 0.4.
    assert opted.certificate.squad_integer == (40, 90)
    # An exclusion is a declared drop, named under its own cause.
    without = squad_depth(snapshot, FOUR, quantization=100, excluded=(9,))
    assert [p.player_id for p in without.slots[3].excluded] == [9]
    assert without.certificate.squad_status == "UNFIELDABLE" and without.excluded == (9,)
    assert without.slots[3].counts["measured"] == 1 and without.slots[3].counts["available"] == 0
    # A lock is honoured by the pinned values and announced beside kappa.
    locked = squad_depth(snapshot, FOUR, quantization=100, locked=(8,))
    assert [(p.player_id, p.status) for p in locked.slots[2].pinned] == [
        (3, "NEUTRAL"), (4, "NEUTRAL")]
    assert [(p.player_id, p.status) for p in locked.slots[1].pinned] == [
        (3, "UNFIELDABLE_IF_PINNED"), (4, "UNFIELDABLE_IF_PINNED"), (8, "NEUTRAL")]
    assert "cannot be used there without leaving another slot or a declared lock unfilled" in (
        locked.slots[1].claim)
    assert any("ignore the declared locks" in w for w in locked.warnings)
    skipped = squad_depth(snapshot, FOUR, quantization=100, pinned_values=False)
    assert skipped.certificate.pinned_requested is False and skipped.certificate.solves <= 3
    assert all(s.pinned == () and s.counts["shortfall_neutral"] is None for s in skipped.slots)
    assert [s.available for s in skipped.slots] == [s.available for s in result.slots]

    provenance = result.provenance
    assert provenance["depth_version"] == "attributed-slot-depth-v1"
    assert provenance["dataset_hash"] == "synthetic" and "solver_stages" not in provenance
    assert provenance["providers"] == ["pappalardo"] and "bootstrap_worlds" not in provenance
    prints = {r.provenance["input_fingerprint"] for r in (opted, without, locked, skipped)}
    prints |= {squad_depth(snapshot, FOUR, quantization=100, **change).provenance[
        "input_fingerprint"] for change in (dict(minimums={"progression": 2.0}),
                                            dict(time_limit=5.0), dict(seed=3))}
    prints.add(squad_depth(snapshot, FOUR, quantization=1000).provenance["input_fingerprint"])
    below = [replace_row(r, minutes=450) if r["player_id"] == 5 else r for r in rows]
    prints.add(squad_depth(make_snapshot(below, HAND_MINIMA, MANUAL), FOUR,
                           quantization=100).provenance["input_fingerprint"])
    assert len(prints) == 9 and provenance["input_fingerprint"] not in prints
    mirrored = squad_depth(make_snapshot(rows, HAND_MINIMA, MANUAL, reverse=True), FOUR,
                           quantization=100)
    assert mirrored.provenance["input_fingerprint"] == provenance["input_fingerprint"]
    assert mirrored.slots == result.slots and mirrored.omitted == result.omitted
    for refused in (dict(locked=(5,)), dict(excluded=("3",)), dict(time_limit=0),
                    dict(minimums={"left_pass_origins": 1.0}), dict(pinned_values=1)):
        with pytest.raises(ValueError):
            squad_depth(snapshot, FOUR, quantization=100, **refused)
    with pytest.raises(ValueError, match="unknown formation"):
        squad_depth(snapshot, "5-5-5")


def replace_row(row, **changes):
    return {**row, **changes}


def test_an_unevaluated_pin_is_unknown_and_the_set_stages_do_not_depend_on_the_clock(
        monkeypatch):
    snapshot = make_snapshot(hand_rows(front_value=0.4), HAND_MINIMA, MANUAL)
    full = squad_depth(snapshot, FOUR, quantization=100)
    assert full.certificate.completeness == "EXACT" and full.certificate.pinned_unknown == 0
    outcomes = set()
    for ticks in (1, 8, 14, 22):
        with monkeypatch.context() as patch:
            clock = itertools.count()
            patch.setattr(depth_module.time, "monotonic",
                          lambda clock=clock, ticks=ticks: 0.0 if next(clock) < ticks else 1e9)
            late = squad_depth(snapshot, FOUR, quantization=100, time_limit=5.0)
        assert late.certificate.completeness == "DEADLINE" and late.certificate.pinned_unknown
        assert late.kappa_by_stage == full.kappa_by_stage
        assert late.tight_groups == full.tight_groups
        outcomes.add(late.certificate.squad_status)
        unknown = 0
        for slot, whole in zip(late.slots, full.slots, strict=True):
            assert slot.available == whole.available and slot.below_gate == whole.below_gate
            for pin, known in zip(slot.pinned, whole.pinned, strict=True):
                # Whatever was decided before the clock ran out is the full run's answer.
                assert pin.status in ("UNKNOWN", known.status)
                assert pin.status != "UNKNOWN" or pin.integer_vector is None
                unknown += pin.status == "UNKNOWN"
            if any(pin.status == "UNKNOWN" for pin in slot.pinned):
                assert slot.counts["shortfall_neutral"] is None
                assert "was not established" in slot.claim
        assert unknown >= late.certificate.pinned_unknown > 0
        assert (f"{late.certificate.pinned_unknown} player-slot pairs were not evaluated before "
                "the time limit. Unknown is not evidence that a player raises the shortfall."
                ) in late.warnings
    assert outcomes == {"UNKNOWN", "CERTIFIED"}
    # A solver that does not decide the squad's own value: nothing is compared with nothing.
    original = engine._solver

    class Undecided:
        def __init__(self, actual):
            self.actual = actual

        def solve(self, model):
            self.actual.solve(model)
            return cp_model.UNKNOWN

        def __getattr__(self, name):
            return getattr(self.actual, name)

    monkeypatch.setattr(engine, "_solver", lambda deadline, seed: Undecided(original(deadline,
                                                                                     seed)))
    undecided = squad_depth(snapshot, FOUR, quantization=100)
    assert undecided.certificate.squad_status == "UNKNOWN"
    assert undecided.certificate.completeness == "DEADLINE"
    assert {p.status for s in undecided.slots for p in s.pinned} == {"UNKNOWN"}


def test_the_broad_position_warning_is_the_sentence_the_page_must_show():
    # Typed here, not imported: a test that reads the module's own constant cannot see it drift.
    one = dict.fromkeys(METRICS, 1.0)
    rows = [record(1, "GK", 810, values={}), record(3, "DF", 1200, values=one),
            record(4, "DF", 1300, values=one), record(5, "DF", 400),
            record(7, "FW", 500), record(9, "MF", 1100, values=one)]
    snapshot = make_snapshot(rows, HAND_MINIMA, PROVIDER)
    result = squad_depth(snapshot, FOUR, quantization=100, pinned_values=False)
    assert result.warnings[0] == (
        "Under broad-position eligibility these counts mostly restate the provider's four-way "
        "position code (GK, DF, MF, FW). A club with one FW has one player for a striker slot by "
        "construction.")
    assert result.eligibility["review_status"] == "UNREVIEWED"
    assert all(s.not_rule_eligible_unreviewed == () == s.not_rule_eligible_other_slot
               for s in result.slots)
    # Under this rule every omitted player is a gate drop, named at each slot his code admits.
    assert [p.player_id for p in result.slots[3].below_gate] == [7]
    assert [p.player_id for p in result.slots[1].below_gate] == [5]


def test_the_unknown_warning_counts_every_unknown_row_when_equal_slots_share_a_solve(
        monkeypatch):
    # Back A and Back B admit the same three players, so one solve answers two rows. A
    # deadline then leaves more rows UNKNOWN than solves skipped, and the warning must count
    # what the reader sees, never fewer.
    one = dict.fromkeys(METRICS, 1.0)
    rows = [record(1, "GK", 2000, ("g",), {}),
            *(record(pid, "DF", 1200, ("ab",), one) for pid in (3, 4, 5)),
            record(9, "MF", 1100, ("c",), one)]
    snapshot = make_snapshot(rows, HAND_MINIMA, MANUAL)
    full = squad_depth(snapshot, FOUR, quantization=100)
    assert full.slots[1].equivalent_slot_ids == ("b",)
    assert full.certificate.pinned_solved == 5 and sum(len(s.pinned) for s in full.slots) == 8
    shared = 0
    for ticks in range(1, 24, 2):
        with monkeypatch.context() as patch:
            clock = itertools.count()
            patch.setattr(depth_module.time, "monotonic",
                          lambda clock=clock, ticks=ticks: 0.0 if next(clock) < ticks else 1e9)
            late = squad_depth(snapshot, FOUR, quantization=100, time_limit=5.0)
        unknown = sum(pin.status == "UNKNOWN" for slot in late.slots for pin in slot.pinned)
        if not unknown:
            assert late.certificate.completeness == "EXACT"
            continue
        assert late.certificate.completeness == "DEADLINE"
        assert [w for w in late.warnings if "player-slot pairs" in w] == [
            f"{unknown} player-slot pairs were not evaluated before the time limit. "
            "Unknown is not evidence that a player raises the shortfall."]
        shared += unknown > late.certificate.pinned_unknown
    assert shared


# -------------------------------------------------------------------- real scenario

MADRID = 675
MATCH = 2565907
BELOW = "below 900 prior minutes"
# Spec 10.3: the pairs that leave no XI are the pair-subsets of the three tight groups.
UNFIELDABLE_PAIRS = {
    (3304, 3306), (3304, 3309), (3304, 3310), (3304, 4501), (3306, 3309), (3306, 3310),
    (3306, 4501), (3309, 3310), (3309, 4501), (3310, 4501), (3563, 8287), (3563, 14723),
    (3563, 40756), (3785, 3915), (8287, 14723), (8287, 40756), (14723, 40756),
}


@pytest.mark.slow
def test_madrid_default_scenario_depth_table(corpus_root, thesis_guard):
    from galactico.optimization.snapshots import load_team_snapshot

    snapshot = load_team_snapshot(competition="Spain", team_id=MADRID, match_id=MATCH, worlds=0)
    result = squad_depth(snapshot, "4-3-3")
    thesis_guard(asdict(result))
    assert {s.slot_id: s.counts["available"] for s in result.slots} == {
        "gk": 2, "lb": 2, "lcb": 3, "rcb": 3, "rb": 2, "dm": 2, "lcm": 4, "rcm": 4, "lw": 5,
        "st": 3, "rw": 3}
    assert dict(result.kappa_by_stage) == dict.fromkeys(STAGES, 2)
    groups = {g.slot_ids: g for g in result.tight_groups}
    assert set(groups) == {("gk",), ("lb", "lcb", "rcb", "rb"), ("dm", "lcm", "rcm")}
    back = groups["lb", "lcb", "rcb", "rb"]
    assert back.spare_by_stage["available"] == 1 and back.spare_by_stage["rule_eligible"] == 4
    assert back.restored_by_gate_ids == (282441, 344132, 396475)
    assert groups["dm", "lcm", "rcm"].restored_by_gate_ids == (69404, 279538, 326523)
    assert groups["gk",].restored_by_gate_ids == ()
    assert {tuple(pair) for g in result.tight_groups
            for pair in itertools.combinations(g.available_ids, 2)} == UNFIELDABLE_PAIRS
    assert [(p.player_id, p.reason) for p in result.omitted] == [
        (pid, BELOW) for pid in (69404, 279538, 282441, 326523, 344120, 344132, 396475)]
    # Every omitted player is named beside the depth number of a slot his rules name.
    named = {p.player_id for s in result.slots for p in s.below_gate}
    assert named == {p.player_id for p in result.omitted}
    # The keeper with 810 minutes is a candidate by the shipped exemption.
    assert [(p.player_id, p.minutes) for p in result.slots[0].available] == [
        (3785, 810), (3915, 2250)]
    assert "goalkeepers exempt (shipped rule)" in result.gate_statement
    assert result.rule_position_conflicts == () and result.eligibility["kind"] == "MANUAL_REVIEWED"
    assert result.slots[2].equivalent_slot_ids == ("rcb",)
    assert result.slots[6].equivalent_slot_ids == ("rcm",)
    # Planning default: progression only, and no placement raises the squad's (0, 0).
    assert result.certificate.squad_integer == (0, 0) and result.certificate.pinned_solved == 26
    assert result.evidence["composed"] == "HEURISTIC"
    assert all(p.status == "NEUTRAL" for s in result.slots for p in s.pinned)
    # With the experimental opt-in the two full-back slots have one placement that raises
    # it, by exactly what the absence of the regular costs (spec 10.3, level 1).
    opted = squad_depth(snapshot, "4-3-3", experimental_opt_in=True)
    assert opted.evidence["composed"] == "EXPERIMENTAL"
    assert {(s.slot_id, p.player_id): p.integer_vector for s in opted.slots for p in s.pinned
            if p.status != "NEUTRAL"} == {("lb", 3304): (12709, 19483), ("rb", 3304): (9300, 9300)}
    assert [s.available for s in opted.slots] == [s.available for s in result.slots]
    assert result.provenance["providers"] == ["pappalardo"]


@pytest.mark.slow
def test_madrid_planning_snapshot_depth_names_what_the_gate_removed(corpus_root):
    from galactico.optimization.snapshots import load_team_snapshot

    snapshot = load_team_snapshot(competition="Spain", team_id=MADRID, cutoff="2018-05-21",
                                  worlds=0)
    result = squad_depth(snapshot, "4-3-3")
    assert len(snapshot.candidates) == 19 and len(result.omitted) == 5
    assert {p.reason for p in result.omitted} == {BELOW}
    # Three keepers before the gate and after it; the gate is what lowers kappa to 2.
    assert dict(result.kappa_by_stage) == {
        "position_admissible": 3, "rule_eligible": 3, "gated": 2, "measured": 2, "available": 2}
    (group,) = result.tight_groups
    assert group.slot_ids == ("lcb", "rcb", "rb")
    assert group.available_ids == (3304, 3306, 3309, 4501)
    assert group.restored_by_gate_ids == (282441, 396475)
    assert group.spare_by_stage["rule_eligible"] == 3 and group.spare_by_stage["available"] == 1
    assert any("fewest absences that leave no fieldable XI from 3 to 2" in w
               for w in result.warnings)
    assert any(w.startswith("The slots Left centre back, Right centre back, Right back have a "
                            "spare of 1 after the evidence gate and 3 before it")
               for w in result.warnings)
    assert not any("kappa" in w or "lcb" in w for w in result.warnings)
    assert result.certificate.squad_integer == (0, 0)
    assert result.certificate.completeness == "EXACT"
    assert all(p.status == "NEUTRAL" for s in result.slots for p in s.pinned)


@pytest.mark.slow
def test_a_club_under_broad_position_eligibility_drops_nobody_by_rule(corpus_root):
    from galactico.optimization.snapshots import load_team_snapshot

    # Barcelona has no reviewed rule set, so the provider's four-way position code decides.
    snapshot = load_team_snapshot(competition="Spain", team_id=676, cutoff="2018-05-21",
                                  worlds=0)
    result = squad_depth(snapshot, "4-3-3")
    assert result.eligibility["kind"] == "PROVIDER_POSITION"
    assert result.eligibility["review_status"] == "UNREVIEWED"
    assert PROVIDER_POSITION_WARNING in result.warnings and result.rule_position_conflicts == ()
    assert len(snapshot.candidates) == 16 and {p.reason for p in result.omitted} == {BELOW}
    assert len(result.omitted) == 9 and all(p.detail == () for p in result.omitted)
    # No rule drop anywhere: every slot of one position code has the same chain.
    assert all(s.not_rule_eligible_unreviewed == () == s.not_rule_eligible_other_slot
               for s in result.slots)
    chains = {s.slot_id: tuple(s.counts[stage] for stage in ("position_admissible",
                                                             "rule_eligible", "gated",
                                                             "available"))
              for s in result.slots}
    assert chains == {
        "gk": (2, 2, 2, 2), "lb": (9, 9, 6, 6), "lcb": (9, 9, 6, 6), "rcb": (9, 9, 6, 6),
        "rb": (9, 9, 6, 6), "dm": (7, 7, 4, 4), "lcm": (7, 7, 4, 4), "rcm": (7, 7, 4, 4),
        "lw": (14, 14, 8, 8), "st": (7, 7, 4, 4), "rw": (14, 14, 8, 8)}
    assert dict(result.kappa_by_stage) == dict.fromkeys(STAGES, 2)
    groups = {g.slot_ids: g for g in result.tight_groups}
    assert set(groups) == {("gk",), ("dm", "lcm", "rcm")}
    midfield = groups["dm", "lcm", "rcm"]
    assert midfield.spare_by_stage["available"] == 1 and len(midfield.available_ids) == 4
    assert midfield.spare_by_stage["rule_eligible"] == 4
    assert midfield.restored_by_gate_ids == (4256, 8323, 211885)
    assert result.certificate.squad_integer == (0, 0)
    assert result.certificate.completeness == "EXACT"
    # D3 on real data under this rule: the pairs that leave no XI are the pair-subsets of
    # the two tight groups, and each is its own core.
    players, requirements = snapshot_inputs(snapshot, "4-3-3")
    stress = absence_stress(players, requirements, "4-3-3", k=2, omitted=snapshot.omitted,
                            provenance=snapshot.provenance)
    assert stress.certificate.completeness == "EXACT"
    assert [lv.unfieldable_count for lv in stress.levels] == [0, 7]
    assert {c.player_ids for c in stress.levels[1].minimal_unfieldable} == {
        tuple(pair) for g in result.tight_groups
        for pair in itertools.combinations(g.available_ids, 2)}
    assert stress.provenance["providers"] == ["pappalardo"]
