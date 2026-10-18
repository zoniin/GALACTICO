"""DECLARED-RISK (OR-XI-SPEC section 5) on planted instances, against the kernel and the solver.

Claim: with one world TAIL(1) and MINIMAX_REGRET return BALANCE's pair there (the oracle,
``kernel.value`` and ``solve_xi``); WORST_WORLD is TAIL(1) under another name; the discard rule
and the world fingerprint are the shipped bootstrap's; the encoding is exact (doubling it changes
no rule-invariant output, a too-small one carries) and never leaves the module; the overflow
guard, the statuses, the records, the completeness tokens and the claims hold in every planted
state. Non-claim: the unit tests read no corpus file; the one slow test needs the corpus and
skips cleanly without it. The oracle (``tests/xi_exact_oracle.py``) and ``solve_xi`` are
references, never the code under test.
"""

from __future__ import annotations

import ast
import inspect
import json
import logging
import math
import re
import time
from dataclasses import asdict, fields, replace
from pathlib import Path

import numpy
import pandas as pd
import pytest
import xi_exact_oracle as oracle
from ortools.sat.python import cp_model
from xi_exact_oracle import Instance, OracleCandidate, OracleRequirement, OracleSlot

from galactico.api.runtime import WORLD_MENU, is_complete
from galactico.domain.labels import scan_labels
from galactico.optimization.squad import kernel as engine
from galactico.optimization.squad.kernel import KernelValue, ShortfallKernel
from galactico.optimization.xi import ceilings, risk
from galactico.optimization.xi.domain import (
    Candidate,
    Formation,
    Slot,
    TacticalRequirement,
    XIResult,
)
from galactico.optimization.xi.solver import _fingerprint, _q, bootstrap_selection, solve_xi
from galactico.profiles.uncertainty import shared_match_weights

SEEDS = range(120)
LATE = 1e15  # a monotonic reading past every deadline of this file
ROOT = Path(__file__).resolve().parents[1]
E13_CONFIG = (
    ROOT / "docs/research/north-star/protocol-drafts/E-13-declared-risk-selection"
    / "config.json"
)
COMPLETENESS = ("EXACT", "LIMIT_REACHED", "DEADLINE", "MODEL_INVALID")
WALL = "risk_solve_wall_times"
WORLD_SEED = 20261010
VERSION = "planted-worlds-v1"
# The membership combinations that can occur (7.5): a player of the XI shown is possible, one
# outside it is not necessary.
COMBINATIONS = {(True, True), (True, False), (True, None), (None, False), (False, False)}


def far() -> float:
    return time.monotonic() + 600.0


# --------------------------------------------------------------------------- instances


def domain(inst: Instance):
    return oracle.domain_inputs(
        inst,
        slot_type=Slot,
        formation_type=Formation,
        candidate_type=Candidate,
        requirement_type=TacticalRequirement,
    )


def run(inst: Instance, rule: str, k: int | None = None, **extra):
    """One rule on ``inst`` with its own declarations; ``extra`` overrides any of them."""
    built = domain(inst)
    options = {
        "worlds": inst.worlds,
        "world_count": len(inst.worlds),
        "world_seed": WORLD_SEED,
        "bootstrap_version": VERSION,
        "locked": inst.locked,
        "excluded": inst.excluded,
        "quantization": inst.quantization,
        "deadline": far(),
        **extra,
    }
    if rule == "TAIL":
        return risk.tail_selection(built.candidates, built.requirements, built.formation,
                                   tail_count=k, **options)
    if rule == "WORST_WORLD":
        return risk.worst_world_selection(built.candidates, built.requirements,
                                          built.formation, **options)
    return risk.minimax_regret_selection(built.candidates, built.requirements, built.formation,
                                         **options)


def seeded(seed: int) -> Instance:
    return oracle.instances(seed).risk


def vector(a: float, b: float, c: float) -> dict[str, float]:
    return {"a": float(a), "b": float(b), "c": float(c)}


def one_slot(players, worlds, *, minimum=10.0) -> Instance:
    """One MF slot, three requirements on metrics a, b, c at ``minimum``, n = 1, q = 1."""
    return Instance(
        (OracleSlot("s", ("MF",), "Slot s"),),
        tuple(OracleCandidate(pid, "MF", vector(1, 1, 1), name=f"Player {pid}")
              for pid in players),
        tuple(OracleRequirement(f"r{m}", m, minimum, 1.0, (), False, f"Requirement {m}")
              for m in "abc"),
        1,
        worlds=worlds,
    )


def carry_tail() -> Instance:
    # Two worlds, k = 2 (both). Shortfalls d = (10 - v)+ per metric:
    #   1: (9, 9, 9) in both worlds: (M, T) = (9, 27), (9, 27); tail sums (18, 54)
    #   2: (10, 0, 0) and (9, 0, 0): (10, 10), (9, 9);          tail sums (19, 19)
    # Lexicographically 1 is selected. T_bound = 30: with BIG = 31 the sums encode as 612 and
    # 608 (the T part of 1 carries into the M digit) and 2 would be selected; with the shipped
    # BIG = 2 * 2 * 30 + 1 = 121, as 2232 and 2318.
    return one_slot((1, 2), {0: {1: vector(1, 1, 1), 2: vector(0, 10, 10)},
                             1: {1: vector(1, 1, 1), 2: vector(1, 10, 10)}})


def carry_regret() -> Instance:
    # Least pairs: w0 (9, 9) by 2 or 3, w1 (9, 27) by 1. Largest differences (M - M*, T - T*):
    #   1: w0 (0, 18), w1 (0, 0):   (0, 18)
    #   2: w0 (0, 0),  w1 (1, -17): (1, -17)
    #   3: w0 (0, 0),  w1 (1, 3):   (1, 3)
    # Lexicographically 1. With BIG = T_bound + 1 = 31 they encode as 18, 14 and 34, and 2 would
    # be selected; with the shipped BIG = 121, as 18, 104 and 124.
    return one_slot((1, 2, 3), {0: {1: vector(1, 1, 1), 2: vector(1, 10, 10),
                                    3: vector(1, 10, 10)},
                                1: {1: vector(1, 1, 1), 2: vector(0, 10, 10),
                                    3: vector(0, 0, 0)}})


def keeper_and_field(*, locked=(), excluded=(), worlds=None, minimum=2.0, normalizer=1.0,
                     quantization=100, keepers=(1,)) -> Instance:
    """Slots gk (GK) and m (MF); requirement r1 on m only, so a keeper needs no value.
    Players: the keepers, 3 and 4 MF."""
    candidates = tuple(OracleCandidate(pid, "GK", {"a": None}, name=f"Keeper {pid}")
                       for pid in keepers)
    candidates += (OracleCandidate(3, "MF", {"a": 1.0}, name="Player 3"),
                   OracleCandidate(4, "MF", {"a": 2.0}, name="Player 4"))
    if worlds is None:
        worlds = {0: {3: {"a": 1.0}, 4: {"a": 0.5}}, 1: {3: {"a": 0.25}, 4: {"a": 1.5}}}
    return Instance(
        (OracleSlot("gk", ("GK",), "Goalkeeper"), OracleSlot("m", ("MF",), "Midfield")),
        candidates,
        (OracleRequirement("r1", "a", minimum, normalizer, ("m",), False, "Requirement a"),),
        quantization,
        locked=tuple(locked),
        excluded=tuple(excluded),
        worlds=worlds,
    )


def two_slots(quantization=100) -> Instance:
    # Two MF slots, three MF players with non-negative rates, r1 at 3 (n = 1) and r2 at 2
    # (n = 0.5): t = (300, 400) at q = 100, L = 0, so U = t, T_bound = 700, M_bound = 400.
    def values(a, b):
        return {"a": a, "b": b}

    return Instance(
        (OracleSlot("s1", ("MF",), "Slot 1"), OracleSlot("s2", ("MF",), "Slot 2")),
        tuple(OracleCandidate(pid, "MF", values(1.0, 0.5), name=f"Player {pid}")
              for pid in (1, 2, 3)),
        (OracleRequirement("r1", "a", 3.0, 1.0, (), False, "Requirement a"),
         OracleRequirement("r2", "b", 2.0, 0.5, (), False, "Requirement b")),
        quantization,
        worlds={0: {1: values(1.0, 0.5), 2: values(2.0, 0.0), 3: values(0.5, 1.0)},
                1: {1: values(0.0, 1.0), 2: values(1.5, 0.25), 3: values(1.0, 1.0)}},
    )


# --------------------------------------------------------------------------- helpers


def stable(result) -> dict:
    """``asdict`` without the wall times, which differ on every run (section 9)."""
    payload = asdict(result)
    del payload["provenance"][WALL]
    return payload


def check_reply(result) -> None:
    """What every reply holds (1.5, 5.6, 5.7, 7.7 and section 9)."""
    cert = result.certificate
    assert scan_labels(asdict(result)) == []
    assert cert.completeness in COMPLETENESS
    assert result.membership.completeness in (*COMPLETENESS, "NOT_REQUESTED")
    assert is_complete(asdict(result)) == (
        cert.completeness == "EXACT" and result.membership.completeness == "EXACT"
    )
    expected = {"EXACT": {None}, "LIMIT_REACHED": {"DETERMINISTIC_LIMIT"},
                "DEADLINE": {"WALL_CLOCK"}, "MODEL_INVALID": {None, "WALL_CLOCK",
                                                              "DETERMINISTIC_LIMIT"}}
    assert cert.stopped_by in expected[cert.completeness]
    assert result.non_claim == risk.RISK_NON_CLAIM
    assert "{" not in result.claim and "}" not in result.claim
    # The rule's bare label in every state, formatted with B and k; E-13's suffix is the
    # router's (5.7).
    count = result.certificate.world_count
    assert result.claim == {
        "WORST_WORLD": risk.RISK_WORST.format(B=count),
        "TAIL": risk.RISK_TAIL.format(B=count, k=result.tail_count),
        "MINIMAX_REGRET": risk.RISK_REGRET.format(B=count),
    }[result.rule]
    assert cert.solves == sum(1 for r in cert.records if r.status != "NOT_RUN")
    assert all(r.status != "CERTIFIED" for r in cert.records)
    made = [r.status for r in cert.records if r.purpose != "WORLD_LEAST" and r.status != "NOT_RUN"]
    assert [row["status"] for row in result.provenance["risk_solve_deterministic_times"]] == made
    walls = result.provenance[WALL]
    assert len(walls) == len(made)
    assert all(isinstance(w, float) and math.isfinite(w) and w >= 0 for w in walls)
    assert (cert.selection_deterministic_limit, cert.world_least_deterministic_limit) == (
        risk.SELECTION_DETERMINISTIC_LIMIT, engine.PER_SOLVE_DETERMINISTIC_LIMIT)
    assert (cert.shortfall_policy, cert.comparison) == (engine.SHORTFALL_POLICY, risk.COMPARISON)
    assert cert.discarded_world_count == len(cert.discarded_worlds)
    assert result.tail_boundary_ties == tuple(sorted(result.tail_boundary_ties))
    assert result.binding_world_ids == tuple(sorted(result.binding_world_ids))
    if result.rule == "MINIMAX_REGRET":
        assert cert.growth is None and result.tail_count is None
    else:
        assert cert.growth == risk.RISK_GROWTH.format(B=cert.world_count,
                                                      U=len(cert.used_world_ids))
        assert cert.undecided_world_ids == ()
    if result.status == "CERTIFIED":
        chosen = {pid for _, pid in result.lineup}
        assert [row.world_id for row in result.world_losses] == list(cert.used_world_ids)
        for row in result.membership.rows:
            assert (row.possible, row.necessary) in COMBINATIONS
            assert row.possible if row.player_id in chosen else row.necessary is False
    else:
        assert result.lineup == () and result.world_losses == () and result.point_sums == ()
        assert result.tail_sum is None and result.point_loss is None
        assert result.membership.rows == ()


def statuses(result, purpose=None) -> list[str]:
    return [r.status for r in result.certificate.records if purpose in (None, r.purpose)]


def regret_optimum(result) -> tuple[int, int]:
    return max(
        (row.selected.maximum_shortfall - row.world_least.maximum_shortfall,
         row.selected.total_shortfall - row.world_least.total_shortfall)
        for row in result.world_losses
    )


def invariant(result) -> tuple:
    """The rule-invariant outputs: status, optimum, membership."""
    optimum = (
        regret_optimum(result) if result.rule == "MINIMAX_REGRET" and result.world_losses
        else result.tail_sum
    )
    return result.status, optimum, result.membership


class Planted:
    def __init__(self) -> None:
        self.models: list[cp_model.CpModel] = []
        self.reads = 0  # reads of objective_value or best_objective_bound


def plant(monkeypatch, *, status=None, spent=None, late_on_read=None, shifted=False,
          tampered=False) -> Planted:
    """Wrap every call of ``risk._solver``. ``status`` and ``spent`` map a call number (1-based,
    calls made) to a forced status and deterministic time; the clock reads past every deadline
    once call ``late_on_read``'s deterministic time has been read (after the call returned);
    ``shifted`` reports the objective and its bound ``2**-20`` low on an OPTIMAL solve;
    ``tampered`` adds one to the value of any expression that is not a variable."""
    original = risk._solver
    record = Planted()
    status, spent = dict(status or {}), dict(spent or {})

    class Proxy:
        def __init__(self, actual, number):
            self.actual, self.number, self.status = actual, number, None

        def solve(self, model):
            record.models.append(model)
            self.status = self.actual.solve(model)
            return status.get(self.number, self.status)

        @property
        def deterministic_time(self):
            if self.number == late_on_read:
                monkeypatch.setattr(time, "monotonic", lambda: LATE)
            return spent.get(self.number, self.actual.deterministic_time)

        @property
        def objective_value(self):
            record.reads += 1
            low = shifted and self.status == cp_model.OPTIMAL
            return self.actual.objective_value - (2**-20 if low else 0)

        @property
        def best_objective_bound(self):
            record.reads += 1
            low = shifted and self.status == cp_model.OPTIMAL
            return self.actual.best_objective_bound - (2**-20 if low else 0)

        def value(self, expression):
            found = self.actual.value(expression)
            if tampered and not isinstance(expression, cp_model.IntVar):
                return found + 1
            return found

        def __getattr__(self, name):
            return getattr(self.actual, name)

    def factory(deadline, seed):
        return Proxy(original(deadline, seed), len(record.models) + 1)

    monkeypatch.setattr(risk, "_solver", factory)
    return record


def planted_values(monkeypatch, outcomes) -> list[dict]:
    """Replace ``kernel.value``: the n-th call answers ``outcomes[n]`` (a KernelValue, or None
    for the real answer). Returns the keyword arguments of every call."""
    original = ShortfallKernel.value
    calls: list[dict] = []

    def value(self, **kwargs):
        calls.append(kwargs)
        found = outcomes[len(calls) - 1]
        return original(self, **kwargs) if found is None else found

    monkeypatch.setattr(ShortfallKernel, "value", value)
    return calls


def kernel_value(status, stages, solves=None, maximum=None, total=None) -> KernelValue:
    return KernelValue(status, maximum, total, (), tuple(stages),
                       len(stages) if solves is None else solves, (), 1)


# --------------------------------------------------------------------------- invariants


def test_the_single_world_invariant() -> None:
    """5.4: with one used world, TAIL(1) and REGRET return BALANCE's pair there, as the oracle,
    kernel.value (its integers) and solve_xi (round(v * q) of its objective_vector) find it."""
    checked = 0
    for seed in SEEDS:
        base = seeded(seed)
        world_id = min(base.worlds)
        inst = base._replace(worlds={world_id: base.worlds[world_id]})
        used, _ = oracle.used_worlds(inst, inst.worlds, excluded=inst.excluded)
        if not used:
            continue
        built = domain(inst)
        table = oracle.world_vectors(inst, inst.worlds[world_id])
        least, level = oracle.balance_optimum(inst, vectors=table, locked=inst.locked,
                                              excluded=inst.excluded)
        value = ShortfallKernel(built.candidates, built.requirements, built.formation,
                                quantization=inst.quantization).value(
            excluded=inst.excluded, locked=inst.locked, values=table, deadline=far())
        changed = [replace(c, values=table[c.player_id]) for c in built.candidates]
        reference = solve_xi(changed, built.requirements, built.formation, locked=inst.locked,
                             excluded=inst.excluded, mode="BALANCE",
                             quantization=inst.quantization, analyze_ties=False)
        for result in (run(inst, "TAIL", 1), run(inst, "MINIMAX_REGRET")):
            check_reply(result)
            if least is None:
                assert result.status == "UNFIELDABLE" and value.status == "UNFIELDABLE"
                assert reference.solution_status == "INFEASIBLE"
                continue
            assert result.status == "CERTIFIED" and value.status == "CERTIFIED"
            pair = result.world_losses[0].selected
            found = (pair.maximum_shortfall, pair.total_shortfall)
            assert found == least == (value.maximum, value.total), seed
            assert reference.solution_status == "OPTIMAL"
            assert tuple(round(v * inst.quantization) for v in reference.objective_vector) == least
            assert result.lineup in level
            checked += 1
        if least is not None:
            regret = run(inst, "MINIMAX_REGRET")
            assert regret_optimum(regret) == (0, 0)
            assert regret.world_losses[0].world_least == regret.world_losses[0].selected
            assert regret.binding_world_ids == (world_id,)
    assert checked >= 100


def test_worst_world_is_tail_one_under_its_own_name() -> None:
    names = {"rule", "claim"}
    for seed in range(0, 120, 6):
        inst = seeded(seed)
        worst, tail = run(inst, "WORST_WORLD"), run(inst, "TAIL", 1)
        check_reply(worst)
        assert (worst.rule, worst.tail_count, tail.rule) == ("WORST_WORLD", 1, "TAIL")
        assert worst.claim == risk.RISK_WORST.format(B=len(inst.worlds))
        assert tail.claim == risk.RISK_TAIL.format(B=len(inst.worlds), k=1)
        left, right = stable(worst), stable(tail)
        for payload in (left, right):
            for name in names:
                del payload[name]
            del payload["certificate"]["rule"]
            del payload["provenance"]["input_contract"]["rule"]
            del payload["provenance"]["input_fingerprint"]
        assert left == right, seed
        assert worst.provenance["input_fingerprint"] != tail.provenance["input_fingerprint"]


def test_a_tail_of_every_used_world_is_the_lexicographic_minimum_of_the_sums() -> None:
    checked = 0
    for seed in SEEDS:
        inst = seeded(seed)
        used, _ = oracle.used_worlds(inst, inst.worlds, excluded=inst.excluded)
        if not used:
            continue
        result = run(inst, "TAIL", len(used))
        check_reply(result)
        space = oracle.xis(inst, locked=inst.locked, excluded=inst.excluded,
                           vectors=oracle.world_vectors(inst, inst.worlds[used[0]]))
        if not space:
            assert result.status == "UNFIELDABLE"
            continue
        totals = {
            x: tuple(map(sum, zip(*(pair for _, pair in oracle.world_pairs(
                inst, x, worlds=inst.worlds, excluded=inst.excluded)), strict=True)))
            for x in space
        }
        summed = (result.tail_sum.summed_maximum_shortfall,
                  result.tail_sum.summed_total_shortfall)
        assert summed == min(totals.values()) == totals[result.lineup]
        assert set(result.tail_world_ids) == set(used) and result.tail_boundary_ties == ()
        checked += 1
    assert checked >= 40


# --------------------------------------------------------------------------- worlds


def bootstrap(inst: Instance) -> dict:
    built = domain(inst)
    base = XIResult(built.formation.formation_id, (), (), "OPTIMAL", ())
    return bootstrap_selection(base, built.candidates, built.requirements, built.formation,
                               worlds=inst.worlds, locked=inst.locked, excluded=inst.excluded,
                               mode="BALANCE", quantization=inst.quantization).provenance


def test_discards_and_fingerprint_are_the_shipped_bootstrap_s() -> None:
    # bootstrap_selection is called directly: solve_xi(worlds=...) returns before the
    # bootstrap when its point solve is infeasible (solver.py:321-351).
    discarding = 0
    for seed in SEEDS:
        inst = seeded(seed)
        _, discarded = oracle.used_worlds(inst, inst.worlds, excluded=inst.excluded)
        if not discarded and seed >= 12:
            continue
        discarding += bool(discarded)
        shipped = bootstrap(inst)
        for result in (run(inst, "TAIL", 1, analyze_ties=False),
                       run(inst, "MINIMAX_REGRET", analyze_ties=False)):
            cert = result.certificate
            assert [asdict(d) for d in cert.discarded_worlds] == (
                shipped["bootstrap_discarded_worlds"]), seed
            assert cert.world_fingerprint == shipped["bootstrap_world_fingerprint"]
            assert cert.world_fingerprint == _fingerprint(inst.worlds)
    assert discarding >= 3


def test_a_missing_player_discards_a_world_only_where_he_is_needed() -> None:
    full = {3: {"a": 1.0}, 4: {"a": 0.5}, 1: {"a": None}}
    worlds = {
        0: dict(full),
        1: {1: {"a": None}, 4: {"a": 0.5}},  # 3 missing: eligible at m, where r1 applies
        2: {3: {"a": 1.0}, 4: {"a": 0.5}},  # only the keeper missing: needed nowhere
        3: {1: {"a": None}, 3: {"a": 1.0}},  # only 4 missing, and 4 is excluded
        4: {1: {"a": None}, 3: {"a": None}, 4: {"a": 0.5}},  # 3 has no value for a
    }
    inst = keeper_and_field(excluded=(4,), worlds=worlds)
    shipped = bootstrap(inst)
    for rule in ("TAIL", "MINIMAX_REGRET"):
        result = run(inst, rule, 1)
        check_reply(result)
        cert = result.certificate
        assert cert.used_world_ids == (0, 2, 3)
        assert cert.discarded_worlds == (risk.DiscardedWorld(1, risk.DISCARD_REASON),
                                         risk.DiscardedWorld(4, risk.DISCARD_REASON))
        assert [asdict(d) for d in cert.discarded_worlds] == shipped[
            "bootstrap_discarded_worlds"]
        assert result.status == "CERTIFIED" and result.lineup == (("gk", 1), ("m", 3))
    # Without the exclusion, world 3 lacks a player who is needed.
    again = run(keeper_and_field(worlds=worlds), "TAIL", 1)
    assert again.certificate.used_world_ids == (0, 2)


# --------------------------------------------------------------------------- the encoding


def test_doubling_the_encoding_base_changes_no_rule_invariant_output(monkeypatch) -> None:
    pairs = []
    for seed in range(0, 120, 3):
        inst = seeded(seed)
        for rule, k in (("TAIL", 1), ("TAIL", len(inst.worlds)), ("MINIMAX_REGRET", None)):
            pairs.append((seed, rule, k, invariant(run(inst, rule, k))))
    original = risk._encoding_base
    monkeypatch.setattr(risk, "_encoding_base", lambda used, total: 2 * original(used, total))
    compared = 0
    for seed, rule, k, shipped in pairs:
        try:
            doubled = run(seeded(seed), rule, k)
        except ValueError as refused:  # the doubled model can pass the guard's limit
            assert str(refused) == risk.RISK_OVERFLOW
            continue
        assert invariant(doubled) == shipped, (seed, rule, k)
        compared += shipped[0] == "CERTIFIED"
    assert compared >= 30


@pytest.mark.parametrize("rule", ["TAIL", "MINIMAX_REGRET"])
def test_a_base_that_is_too_small_carries(monkeypatch, rule) -> None:
    """5.1: BIG = T_bound + 1 orders one encoding but not a sum of two or a difference."""
    inst = carry_tail() if rule == "TAIL" else carry_regret()
    assert oracle.t_bound(inst, inst.worlds, excluded=()) == 30
    truth = (oracle.tail_optimum(inst, 2, worlds=inst.worlds, locked=(), excluded=())
             if rule == "TAIL" else
             oracle.regret_optimum(inst, worlds=inst.worlds, locked=(), excluded=()))
    assert truth.level_set == ((("s", 1),),)
    shipped = run(inst, rule, 2)
    check_reply(shipped)
    assert shipped.lineup == (("s", 1),)
    if rule == "TAIL":
        assert shipped.tail_sum == risk.TailSums(18, 54)
    else:
        assert regret_optimum(shipped) == (0, 18) and shipped.binding_world_ids == (0,)
    monkeypatch.setattr(risk, "_encoding_base", lambda used, total: total + 1)
    small = run(inst, rule, 2)
    assert small.status == "CERTIFIED" and small.lineup == (("s", 2),)


def leaked_values(inst: Instance, result) -> set[int]:
    """BIG, the optimum Φ* or ρ*, every E^w with M^w >= 1 and every E*^w with M*^w >= 1 of the
    returned lineup, each where the spec's condition holds (section 9)."""
    found: set[int] = set()
    if result.status != "CERTIFIED":
        return found
    used = result.certificate.used_world_ids
    total = oracle.t_bound(inst, inst.worlds, excluded=inst.excluded)
    big = 2 * len(used) * total + 1
    if total >= 1:
        found.add(big)
    encoded = []
    for row in result.world_losses:
        pair = row.selected
        encoded.append(big * pair.maximum_shortfall + pair.total_shortfall)
        if pair.maximum_shortfall >= 1:
            found.add(encoded[-1])
        least = row.world_least
        if least is not None and least.maximum_shortfall >= 1:
            found.add(big * least.maximum_shortfall + least.total_shortfall)
    if result.rule == "MINIMAX_REGRET":
        if regret_optimum(result)[0] >= 1:
            found.add(max(
                big * (r.selected.maximum_shortfall - r.world_least.maximum_shortfall)
                + r.selected.total_shortfall - r.world_least.total_shortfall
                for r in result.world_losses
            ))
    elif result.tail_sum.summed_maximum_shortfall >= 1:
        found.add(sum(sorted(encoded, reverse=True)[: result.tail_count]))
    return found


ALLOWED = frozenset({
    "player_id", "world_id", "lineup", "used_world_ids", "tail_world_ids", "tail_boundary_ties",
    "binding_world_ids", "undecided_world_ids", "locked", "excluded", "world_count",
    "tail_count", "discarded_world_count", "solves", "world_seed", "solver_seed", "seed",
    "quantization", "minutes", "maximum_shortfall", "total_shortfall",
    "summed_maximum_shortfall", "summed_total_shortfall",
})
TOKEN = re.compile(r"\b\d+\b")
# Strings that are declared names and versions, never computed: their digits are not numbers
# the module produced.
NAMED = frozenset({"name", "label", "slot_id", "formation_id", "requirement_id", "metric",
                   "solver_package_version", "wall_clock_limit"})


def walk(node, key=""):
    """(key, value) for every int and string, with the nearest dict key above it."""
    if isinstance(node, dict):
        for child, value in node.items():
            yield from walk(value, str(child))
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from walk(value, key)
    else:
        yield key, node


def keys(node) -> list[str]:
    if isinstance(node, dict):
        return [str(k) for k in node] + [k for v in node.values() for k in keys(v)]
    if isinstance(node, (list, tuple)):
        return [k for v in node for k in keys(v)]
    return []


def test_no_encoding_leaves_the_module(caplog) -> None:
    forbidden_seen = 0
    for seed in range(0, 120, 2):
        inst = seeded(seed)
        for rule, k in (("TAIL", 1), ("TAIL", len(inst.worlds)), ("WORST_WORLD", 1),
                        ("MINIMAX_REGRET", None)):
            with caplog.at_level(logging.DEBUG):
                result = run(inst, rule, k)
            payload = asdict(result)
            assert not [k for k in keys(payload)
                        if re.search("encod|big|base|objective", k, re.IGNORECASE)]
            allowed = {v for key, v in walk(payload) if key in ALLOWED and type(v) is int}
            forbidden = leaked_values(inst, result) - allowed
            forbidden_seen += bool(forbidden)
            for key, value in walk(payload):
                if type(value) is int:
                    assert value not in forbidden, (seed, rule, key)
                elif isinstance(value, str) and key not in NAMED:
                    assert not {int(t) for t in TOKEN.findall(value)} & forbidden, (seed, key)
            assert not {int(t) for t in TOKEN.findall(caplog.text)} & forbidden
    assert forbidden_seen >= 50


def test_no_variable_domain_is_wider_than_the_base(monkeypatch) -> None:
    """5.1, split variables: every variable of every model risk._solver solves has a domain of
    width at most BIG (the encoding variables are split)."""
    checked = 0
    for seed in range(0, 120, 4):
        inst = seeded(seed)
        used, _ = oracle.used_worlds(inst, inst.worlds, excluded=inst.excluded)
        if not used:
            continue
        big = 2 * len(used) * oracle.t_bound(inst, inst.worlds, excluded=inst.excluded) + 1
        for rule, k in (("TAIL", len(used)), ("MINIMAX_REGRET", None)):
            with monkeypatch.context() as patch:
                record = plant(patch)
                run(inst, rule, k)
            for model in record.models:
                for variable in model.proto.variables:
                    assert variable.domain[-1] - variable.domain[0] <= big, (seed, rule)
                checked += 1
    assert checked >= 50


# --------------------------------------------------------------------------- the guard


def test_the_overflow_guard_refuses_at_its_limit(monkeypatch) -> None:
    assert risk.EXACT_OBJECTIVE_LIMIT == 2**53
    inst = two_slots()
    t_bound, m_bound, used = 700, 400, 2
    assert oracle.t_bound(inst, inst.worlds, excluded=()) == t_bound
    cap = (2 * used * t_bound + 1) * (m_bound + 1)  # E_cap
    for rule, k, terms in (("TAIL", 2, 2 + used + 2), ("WORST_WORLD", 1, 1 + used + 2),
                           ("MINIMAX_REGRET", None, 3)):
        monkeypatch.setattr(risk, "EXACT_OBJECTIVE_LIMIT", terms * cap)
        with pytest.raises(ValueError) as refused:
            run(inst, rule, k)
        assert str(refused.value) == risk.RISK_OVERFLOW
        monkeypatch.setattr(risk, "EXACT_OBJECTIVE_LIMIT", terms * cap + 1)
        assert run(inst, rule, k).status == "CERTIFIED"
    assert not re.search(r"\d", risk.RISK_OVERFLOW)


def huge_minimum(*, keepers) -> Instance:
    # Minimum 1000, normaliser 0.001, q = 100000: t = 10**11, so E_cap is near 10**22.
    worlds = {0: {pid: {"a": None} for pid in keepers} | {3: {"a": 1.0}, 4: {"a": 2.0}}}
    return keeper_and_field(worlds=worlds, minimum=1000.0, normalizer=0.001,
                            quantization=100_000, keepers=keepers)


def test_the_guard_comes_after_not_evaluable_and_before_any_solve(monkeypatch) -> None:
    # |U| = 0 is NOT_EVALUABLE before any bound is formed (never a max() over nothing).
    empty = huge_minimum(keepers=(1,))._replace(worlds={0: {1: {"a": None}}})
    for rule in ("TAIL", "MINIMAX_REGRET"):
        result = run(empty, rule, 1)
        check_reply(result)
        assert result.status == "NOT_EVALUABLE" and result.certificate.used_world_ids == ()
    # No keeper: β.model is None. The guard refuses before UNFIELDABLE, and before the
    # deadline rule.
    unfieldable = huge_minimum(keepers=())
    for rule in ("TAIL", "WORST_WORLD", "MINIMAX_REGRET"):
        for deadline in (far(), time.monotonic() - 1.0):
            with pytest.raises(ValueError) as refused:
                run(unfieldable, rule, 1, deadline=deadline)
            assert str(refused.value) == risk.RISK_OVERFLOW
    # REGRET refuses before any per-world optimum is spent.
    calls = planted_values(monkeypatch, [None] * 4)
    with pytest.raises(ValueError):
        run(huge_minimum(keepers=(1,)), "MINIMAX_REGRET")
    assert calls == []


# --------------------------------------------------------------------------- statuses


def test_refusals_name_no_value() -> None:
    inst = two_slots()
    hard = inst._replace(requirements=(inst.requirements[0]._replace(hard=True),
                                       inst.requirements[1]))
    for rule in ("TAIL", "WORST_WORLD", "MINIMAX_REGRET"):
        with pytest.raises(ValueError) as refused:
            run(hard, rule, 1)
        assert str(refused.value) == risk.RISK_HARD
    cases = [
        ({"world_count": 3}, risk.WORLDS_ERROR),
        ({"world_count": True}, risk.WORLDS_ERROR),
        ({"worlds": {}, "world_count": 0}, risk.WORLDS_ERROR),
        ({"worlds": {"0": inst.worlds[0]}, "world_count": 1}, risk.WORLDS_ERROR),
        ({"worlds": {0: {1: {"a": math.nan}}}, "world_count": 1}, risk.WORLDS_ERROR),
        ({"worlds": {0: {1: {"a": True}}}, "world_count": 1}, risk.WORLDS_ERROR),
        ({"world_seed": "1"}, risk.WORLDS_ERROR),
        ({"bootstrap_version": 1}, risk.WORLDS_ERROR),
        ({"analyze_ties": 1}, risk.WORLDS_ERROR),
        ({"locked": (99,)}, risk.PLAYER_ERROR),
        ({"excluded": ("1",)}, risk.PLAYER_ERROR),
    ]
    for extra, sentence in cases:
        with pytest.raises(ValueError) as refused:
            run(inst, "TAIL", 1, **extra)
        assert str(refused.value) == sentence, extra
    # None included: the rule, not a missing count, chooses the algorithm.
    for k in (0, 3, True, 1.0, None):
        with pytest.raises(ValueError) as refused:
            run(inst, "TAIL", k)
        assert str(refused.value) == risk.TAIL_COUNT_ERROR
    built = domain(inst)
    options = {"worlds": inst.worlds, "world_count": 2, "world_seed": 1,
               "bootstrap_version": "v", "quantization": 100, "deadline": far()}
    for rule, k in (("WORST_WORLD", 2), ("MINIMAX_REGRET", 1), ("TAIL", None)):
        with pytest.raises(ValueError) as refused:
            risk.declared_risk_selection(built.candidates, built.requirements, built.formation,
                                         rule=rule, tail_count=k, **options)
        assert str(refused.value) == risk.TAIL_COUNT_ERROR
    with pytest.raises(ValueError) as refused:
        risk.declared_risk_selection(built.candidates, built.requirements, built.formation,
                                     rule="CVAR", **options)
    assert str(refused.value) == risk.RULE_ERROR
    for rule, k in (("WORST_WORLD", None), ("WORST_WORLD", 1), ("TAIL", 2),
                    ("MINIMAX_REGRET", None)):
        result = risk.declared_risk_selection(built.candidates, built.requirements,
                                              built.formation, rule=rule, tail_count=k, **options)
        assert (result.rule, result.tail_count) == (rule, 1 if rule == "WORST_WORLD" else k)
    for sentence in (risk.RISK_HARD, risk.RISK_OVERFLOW, risk.RISK_NOT_EVALUABLE,
                     risk.WORLDS_ERROR, risk.PLAYER_ERROR, risk.TAIL_COUNT_ERROR,
                     risk.RULE_ERROR, risk.LINEUP_ERROR):
        assert scan_labels(sentence) == []
    # Fixed sentences: the bounds they state are the module's, never a declared value.
    for sentence in (risk.RISK_HARD, risk.RISK_OVERFLOW, risk.RISK_NOT_EVALUABLE,
                     risk.PLAYER_ERROR, risk.RULE_ERROR, risk.LINEUP_ERROR):
        assert not re.search(r"\d", sentence), sentence


def test_fewer_used_worlds_than_k_is_not_evaluable_without_a_solve() -> None:
    inst = two_slots()
    one_used = inst._replace(worlds={0: inst.worlds[0], 1: {1: {"a": 1.0}}})
    result = run(one_used, "TAIL", 2)
    check_reply(result)
    cert = result.certificate
    assert (result.status, cert.completeness, cert.stopped_by) == ("NOT_EVALUABLE", "EXACT", None)
    assert cert.records == () and cert.solves == 0
    assert result.membership == risk.MembershipBlock((), "EXACT")
    assert result.reasons == (risk.RISK_NOT_EVALUABLE,)
    assert (cert.used_world_ids, cert.discarded_world_count, cert.world_count) == ((0,), 1, 2)
    assert run(one_used, "TAIL", 1).status == "CERTIFIED"
    assert is_complete(asdict(result))


def test_two_locked_goalkeepers_are_unfieldable_by_proof_for_every_rule() -> None:
    inst = keeper_and_field(locked=(1, 2), keepers=(1, 2))
    reasons = set()
    for rule in ("TAIL", "WORST_WORLD", "MINIMAX_REGRET"):
        result = run(inst, rule, 1)
        check_reply(result)
        assert (result.status, result.certificate.completeness) == ("UNFIELDABLE", "EXACT")
        assert result.lineup == () and result.membership == risk.MembershipBlock((), "EXACT")
        assert result.reasons == (risk.UNFIELDABLE_PROVED,)
        assert not any("pins" in reason for reason in result.reasons)
        reasons.add(result.reasons)
        assert is_complete(asdict(result))
    assert reasons == {(ceilings.UNFIELDABLE_PROVED,)}
    # By construction (a player both locked and excluded): the kernel's reason, no solve.
    built = run(keeper_and_field(locked=(3,), excluded=(3,)), "TAIL", 1)
    assert built.status == "UNFIELDABLE" and built.certificate.records == ()
    assert built.reasons[0] == "A player cannot be both locked and excluded."


def test_a_proved_empty_world_supersedes_an_undecided_one(monkeypatch) -> None:
    inst = keeper_and_field()
    planted_values(monkeypatch, [
        kernel_value("UNKNOWN", ("UNKNOWN",)),
        kernel_value("UNFIELDABLE", ("INFEASIBLE", "INFEASIBLE")),
    ])
    result = run(inst, "MINIMAX_REGRET")
    check_reply(result)
    cert = result.certificate
    assert (result.status, cert.completeness, cert.stopped_by) == ("UNFIELDABLE", "EXACT", None)
    assert statuses(result) == ["UNKNOWN", "INFEASIBLE", "INFEASIBLE"]
    assert cert.undecided_world_ids == () and result.reasons == (risk.UNFIELDABLE_PROVED,)
    assert is_complete(asdict(result))


@pytest.mark.parametrize(
    ("planted", "status", "completeness", "stopped_by", "records"),
    [
        (kernel_value("UNKNOWN", ("INFEASIBLE", "UNKNOWN")), "UNKNOWN", "DEADLINE",
         "WALL_CLOCK", ["INFEASIBLE", "UNKNOWN"]),
        (kernel_value("UNKNOWN", ("INFEASIBLE", "OPTIMAL")), "UNKNOWN", "DEADLINE",
         "WALL_CLOCK", ["INFEASIBLE", "OPTIMAL", "NOT_RUN"]),
        (kernel_value("UNKNOWN", ()), "UNKNOWN", "DEADLINE", "WALL_CLOCK", ["NOT_RUN"]),
        (kernel_value("MODEL_INVALID", ("MODEL_INVALID",)), "MODEL_INVALID", "MODEL_INVALID",
         None, ["MODEL_INVALID"]),
    ],
)
def test_an_undecided_or_refused_world_least(monkeypatch, planted, status, completeness,
                                             stopped_by, records) -> None:
    inst = keeper_and_field()
    planted_values(monkeypatch, [None, planted])
    result = run(inst, "MINIMAX_REGRET")
    check_reply(result)
    cert = result.certificate
    assert (result.status, cert.completeness, cert.stopped_by) == (
        status, completeness, stopped_by)
    assert result.lineup == () and result.membership == risk.MembershipBlock((), completeness)
    first = [r.status for r in cert.records if r.world_id == 0]
    assert first and all(s != "NOT_RUN" for s in first)
    assert [r.status for r in cert.records if r.world_id == 1] == records
    assert all(r.purpose == "WORLD_LEAST" for r in cert.records)
    assert cert.undecided_world_ids == ((1,) if status == "UNKNOWN" else ())
    assert not is_complete(asdict(result))


def test_a_passed_deadline_answers_unknown_without_a_solve() -> None:
    inst = two_slots()
    gone = time.monotonic() - 1.0
    for rule in ("TAIL", "WORST_WORLD", "MINIMAX_REGRET"):
        result = run(inst, rule, 1, deadline=gone)
        check_reply(result)
        cert = result.certificate
        assert (result.status, cert.completeness, cert.stopped_by) == (
            "UNKNOWN", "DEADLINE", "WALL_CLOCK")
        assert cert.solves == 0 and result.lineup == ()
        assert result.membership == risk.MembershipBlock((), "DEADLINE")
        if rule == "MINIMAX_REGRET":
            assert [(r.purpose, r.world_id, r.status) for r in cert.records] == [
                ("WORLD_LEAST", 0, "NOT_RUN"), ("WORLD_LEAST", 1, "NOT_RUN")]
            assert cert.undecided_world_ids == (0, 1)
        else:
            assert [(r.purpose, r.status) for r in cert.records] == [("SELECTION", "NOT_RUN")]
        assert not is_complete(asdict(result))
    # Even where a reason proves that no XI exists, as the kernel answers.
    proved = run(keeper_and_field(locked=(3,), excluded=(3,)), "TAIL", 1, deadline=gone)
    assert proved.status == "UNKNOWN"


@pytest.mark.parametrize("planted", ["UNKNOWN", "MODEL_INVALID", "FEASIBLE"])
def test_an_undecided_or_refused_selection_has_no_rows(monkeypatch, planted) -> None:
    plant(monkeypatch, status={1: getattr(cp_model, planted)})
    result = run(two_slots(), "TAIL", 1)
    check_reply(result)
    expected = "MODEL_INVALID" if planted == "MODEL_INVALID" else "UNKNOWN"
    completeness = "MODEL_INVALID" if planted == "MODEL_INVALID" else "DEADLINE"
    assert (result.status, result.certificate.completeness) == (expected, completeness)
    assert result.membership == risk.MembershipBlock((), completeness)
    assert statuses(result) == [planted]
    assert not is_complete(asdict(result))


def test_a_selection_proved_infeasible_is_unfieldable(monkeypatch) -> None:
    with monkeypatch.context() as patch:
        plant(patch, status={1: cp_model.INFEASIBLE})
        result = run(two_slots(), "TAIL", 1)
    check_reply(result)
    assert (result.status, result.certificate.completeness) == ("UNFIELDABLE", "EXACT")
    assert result.reasons == (risk.UNFIELDABLE_PROVED,)
    assert statuses(result) == ["INFEASIBLE"]
    # For REGRET every world's least is a verified XI: an INFEASIBLE selection contradicts it.
    plant(monkeypatch, status={1: cp_model.INFEASIBLE})
    with pytest.raises(RuntimeError):
        run(two_slots(), "MINIMAX_REGRET")


def test_analyze_ties_false_is_not_requested() -> None:
    result = run(two_slots(), "TAIL", 1, analyze_ties=False)
    check_reply(result)
    assert result.status == "CERTIFIED"
    assert result.membership == risk.MembershipBlock((), "NOT_REQUESTED")
    assert statuses(result, "MEMBERSHIP") == [] and result.certificate.completeness == "EXACT"
    assert not is_complete(asdict(result))


def test_membership_by_construction_and_by_solve() -> None:
    inst = keeper_and_field(locked=(4,), excluded=(3,), keepers=(1, 2))
    result = run(inst, "TAIL", 1)
    check_reply(result)
    rows = {row.player_id: (row.possible, row.necessary) for row in result.membership.rows}
    # 3 excluded and 4 locked: by construction; the keepers 1 and 2 by solve.
    assert rows[3] == (False, False) and rows[4] == (True, True)
    assert [r.player_id for r in result.certificate.records if r.purpose == "MEMBERSHIP"] == [
        1, 2]
    assert list(rows) == sorted(rows)
    assert rows[1] == rows[2] == (True, False)  # either keeper fills gk at the same loss


# --------------------------------------------------------------------------- stops


def test_a_deterministic_stop_alone_is_load_independent(monkeypatch) -> None:
    plant(monkeypatch, status={1: cp_model.UNKNOWN}, spent={1: risk.SELECTION_DETERMINISTIC_LIMIT})
    result = run(two_slots(), "TAIL", 1)
    check_reply(result)
    cert = result.certificate
    assert (result.status, cert.completeness, cert.stopped_by) == (
        "UNKNOWN", "LIMIT_REACHED", "DETERMINISTIC_LIMIT")
    assert result.membership == risk.MembershipBlock((), "LIMIT_REACHED")


def test_a_deterministic_stop_in_membership_keeps_the_selection(monkeypatch) -> None:
    plant(monkeypatch, status={2: cp_model.UNKNOWN}, spent={2: risk.SELECTION_DETERMINISTIC_LIMIT})
    result = run(two_slots(), "TAIL", 1)
    check_reply(result)
    cert = result.certificate
    assert result.status == "CERTIFIED"
    assert (cert.completeness, cert.stopped_by) == ("LIMIT_REACHED", "DETERMINISTIC_LIMIT")
    assert result.membership.completeness == "LIMIT_REACHED"
    assert sum(None in (r.possible, r.necessary) for r in result.membership.rows) == 1


def test_a_deterministic_stop_then_a_call_not_made_is_wall_clock(monkeypatch) -> None:
    plant(monkeypatch, status={2: cp_model.UNKNOWN},
          spent={2: risk.SELECTION_DETERMINISTIC_LIMIT}, late_on_read=2)
    result = run(two_slots(), "TAIL", 1)
    check_reply(result)
    cert = result.certificate
    assert result.status == "CERTIFIED"
    assert statuses(result, "MEMBERSHIP") == ["UNKNOWN", "NOT_RUN", "NOT_RUN"]
    assert (cert.completeness, cert.stopped_by) == ("DEADLINE", "WALL_CLOCK")
    assert result.membership.completeness == "DEADLINE"
    assert sum(None in (r.possible, r.necessary) for r in result.membership.rows) == 3


def test_an_unknown_that_reached_no_limit_is_wall_clock(monkeypatch) -> None:
    plant(monkeypatch, status={1: cp_model.UNKNOWN})
    result = run(two_slots(), "MINIMAX_REGRET")
    check_reply(result)
    cert = result.certificate
    assert (result.status, cert.completeness, cert.stopped_by) == (
        "UNKNOWN", "DEADLINE", "WALL_CLOCK")


# --------------------------------------------------------------------------- integers


def test_integers_come_from_solver_values_not_objective_floats(monkeypatch) -> None:
    inst = carry_tail()
    plain = [stable(run(inst, rule, 2)) for rule in ("TAIL", "MINIMAX_REGRET")]
    record = plant(monkeypatch, shifted=True)
    shifted = [stable(run(inst, rule, 2)) for rule in ("TAIL", "MINIMAX_REGRET")]
    assert shifted == plain and record.reads == 0


def test_a_tampered_witness_or_objective_raises(monkeypatch) -> None:
    inst = carry_tail()
    with monkeypatch.context() as patch:
        plant(patch, tampered=True)
        with pytest.raises(RuntimeError):
            run(inst, "TAIL", 2)
    original = ShortfallKernel._witness
    for swap in (2, 99):  # another XI with another loss, and a player who is not a candidate
        with monkeypatch.context() as patch:
            patch.setattr(ShortfallKernel, "_witness", staticmethod(
                lambda background, solver, swap=swap: tuple(
                    (sid, swap) for sid, _ in original(background, solver))))
            for rule in ("TAIL", "MINIMAX_REGRET"):
                with pytest.raises(RuntimeError):
                    run(inst, rule, 2)


def test_shortfalls_use_the_float_rule_of_the_shipped_solver() -> None:
    inst = Instance(
        (OracleSlot("s", ("MF",), "Slot s"),),
        (OracleCandidate(1, "MF", {"a": 1.344465}, name="Player 1"),),
        (OracleRequirement("r1", "a", 2.0, 1.0, (), False, "Requirement a"),),
        100_000,
        worlds={0: {1: {"a": 1.344465}}},
    )
    result = run(inst, "TAIL", 1)
    assert _q(1.344465, 1.0, 100_000) == 134446  # exact half-even is 134447
    expected = risk.LossPair(200_000 - 134446, 200_000 - 134446)
    assert result.world_losses[0].selected == expected == result.point_loss
    built = domain(inst)
    assert risk.world_losses(result.lineup, built.candidates, built.requirements,
                             built.formation, worlds=inst.worlds,
                             quantization=100_000)[0].selected == expected


def test_a_point_value_past_the_magnitude_bound_refuses_nothing() -> None:
    """5.6: the ValueErrors of step 2 are the world tables'; ``point_loss`` is a field that can
    be None. A point coefficient past MAX_MAGNITUDE leaves the selection on the worlds and gives
    no point pair; ``point_sums`` stays exact."""
    inst = Instance(
        (OracleSlot("s", ("MF",), "Slot s"),),
        (OracleCandidate(1, "MF", {"a": 1e12}, name="Player 1"),
         OracleCandidate(2, "MF", {"a": 1.0}, name="Player 2")),
        (OracleRequirement("r1", "a", 2.0, 1.0, (), False, "Requirement a"),),
        100,
        worlds={0: {1: {"a": 1.0}, 2: {"a": 0.5}}, 1: {1: {"a": 1.0}, 2: {"a": 0.5}}},
    )
    for rule, k in (("TAIL", 1), ("WORST_WORLD", 1), ("MINIMAX_REGRET", None)):
        result = run(inst, rule, k)
        check_reply(result)
        assert result.status == "CERTIFIED" and result.lineup == (("s", 1),)
        assert result.world_losses[0].selected == risk.LossPair(100, 100)
        assert result.point_loss is None
        assert result.point_sums == (("r1", 1e12),)
    # Without the large value the same lineup has its point pair.
    plain = inst._replace(candidates=(inst.candidates[0]._replace(values={"a": 1.0}),
                                      inst.candidates[1]))
    assert run(plain, "TAIL", 1).point_loss == risk.LossPair(100, 100)


# --------------------------------------------------------------------------- the certificate


def test_claims_growth_seeds_and_records() -> None:
    inst = carry_regret()
    for rule, k, claim in (
        ("TAIL", 2, risk.RISK_TAIL.format(B=2, k=2)),
        ("WORST_WORLD", 1, risk.RISK_WORST.format(B=2)),
        ("MINIMAX_REGRET", None, risk.RISK_REGRET.format(B=2)),
    ):
        result = run(inst, rule, k)
        check_reply(result)
        assert result.claim == claim and "E-13" not in result.claim
        cert = result.certificate
        assert (cert.world_seed, cert.bootstrap_version, cert.solver_seed) == (
            WORLD_SEED, VERSION, 20260906)
        assert (cert.world_count, cert.quantization) == (2, 1)
        assert cert.growth == (None if rule == "MINIMAX_REGRET"
                               else risk.RISK_GROWTH.format(B=2, U=2))
        if rule == "MINIMAX_REGRET":
            built = domain(inst)
            kernel = ShortfallKernel(built.candidates, built.requirements, built.formation,
                                     quantization=1)
            for w in (0, 1):
                least = kernel.value(values=oracle.world_vectors(inst, inst.worlds[w]),
                                     deadline=far())
                assert [r.status for r in cert.records if r.world_id == w] == list(
                    least.stage_statuses)
            kernel_solves = sum(1 for r in cert.records if r.purpose == "WORLD_LEAST")
            assert cert.solves == kernel_solves + len(result.provenance[WALL])
        assert [r.purpose for r in cert.records if r.purpose != "WORLD_LEAST"] == [
            "SELECTION", "MEMBERSHIP", "MEMBERSHIP", "MEMBERSHIP"]
    texts = (risk.RISK_WORST, risk.RISK_TAIL, risk.RISK_REGRET, risk.RISK_GROWTH,
             risk.RISK_NON_CLAIM, risk.RISK_HARD, risk.RISK_OVERFLOW, risk.RISK_NOT_EVALUABLE)
    for text in texts:
        assert scan_labels(text.format(B=12, k=3, U=11)) == []
    assert risk.UNFIELDABLE_PROVED is ceilings.UNFIELDABLE_PROVED


def test_the_tail_and_its_boundary_ties_for_the_xi_shown() -> None:
    # One slot, one player, three worlds with pairs (2, 2), (2, 2), (1, 1): the tail of 1 is
    # world 0 by id, and world 1 has the same pair as its last member.
    inst = Instance(
        (OracleSlot("s", ("MF",), "Slot s"),),
        (OracleCandidate(1, "MF", {"a": 0.0}, name="Player 1"),),
        (OracleRequirement("r1", "a", 2.0, 1.0, (), False, "Requirement a"),),
        1,
        worlds={0: {1: {"a": 0.0}}, 1: {1: {"a": 0.0}}, 2: {1: {"a": 1.0}}},
    )
    result = run(inst, "TAIL", 1)
    assert (result.tail_world_ids, result.tail_boundary_ties) == ((0,), (1,))
    assert result.tail_sum == risk.TailSums(2, 2)
    result = run(inst, "TAIL", 2)
    assert (result.tail_world_ids, result.tail_boundary_ties) == ((0, 1), ())
    result = run(inst, "TAIL", 3)
    assert result.tail_world_ids == (0, 1, 2) and result.tail_sum == risk.TailSums(5, 5)
    regret = run(inst, "MINIMAX_REGRET")
    assert regret.binding_world_ids == (0, 1, 2)


def test_the_tail_menu_is_the_e13_draft_s() -> None:
    config = json.loads(E13_CONFIG.read_text(encoding="utf-8"))
    tiers = {row["worlds"]: row for row in config["tail_counts"]}
    assert set(risk.TAIL_MENU) == set(WORLD_MENU)
    for count in WORLD_MENU:
        row = tiers[count]
        assert row["WORST_WORLD"] == 1
        assert (row["TAIL_10"], row["TAIL_25"], row["TAIL_50"]) == risk.TAIL_MENU[count]
        assert risk.TAIL_MENU[count] == tuple(math.ceil(count * f) for f in (0.1, 0.25, 0.5))
        assert 1 not in risk.TAIL_MENU[count]
    assert risk.RULES == ("WORST_WORLD", "TAIL", "MINIMAX_REGRET")
    with pytest.raises(TypeError):
        risk.TAIL_MENU[12] = (1,)  # type: ignore[index]


def sampled_worlds(games, weights, components, players) -> dict:
    """The world vectors of historical.py:203-212, written out on synthetic frames."""
    sampled = {world: {pid: {} for pid in players} for world in range(len(weights))}
    for key, table in components.items():
        for pid in players:
            block = table[table.player_id == pid].set_index("game_id").reindex(games).fillna(0.0)
            den = weights @ block.denominator.to_numpy()
            num = weights @ block.numerator.to_numpy()
            for world in range(len(weights)):
                sampled[world][pid][key] = (
                    float(num[world] / den[world] * 90) if den[world] > 0 else None
                )
    return sampled


def test_the_twelve_worlds_are_the_first_twelve_of_forty(record_property) -> None:
    """1.4, the prefix property, under the installed numpy (recorded, not asserted)."""
    record_property("numpy_version", numpy.__version__)
    rng = numpy.random.default_rng(7)
    game_ids = [int(g) for g in rng.choice(10_000, size=34, replace=False)]
    players = list(range(1, 16))
    components = {}
    for key in ("progression", "left_pass_origins"):
        rows = [
            {"player_id": pid, "game_id": g, "numerator": float(rng.poisson(3)),
             "denominator": float(rng.integers(0, 91))}
            for pid in players for g in game_ids if rng.random() < 0.7
        ]
        components[key] = pd.DataFrame(rows)
    seed = 20260906  # historical.SEED, written out: this test imports no snapshot builder
    games12, weights12 = shared_match_weights(game_ids, 12, seed)
    games40, weights40 = shared_match_weights(game_ids, 40, seed)
    assert (games12 == games40).all() and (weights40[:12] == weights12).all()
    twelve = sampled_worlds(games12, weights12, components, players)
    forty = sampled_worlds(games40, weights40, components, players)
    assert _fingerprint({w: forty[w] for w in range(12)}) == _fingerprint(twelve)


# --------------------------------------------------------------------------- identity


def test_determinism_and_shuffled_inputs() -> None:
    for seed in (3, 17, 42, 77):
        inst = seeded(seed)
        for rule, k in (("TAIL", len(inst.worlds)), ("MINIMAX_REGRET", None)):
            first = run(inst, rule, k)
            assert stable(run(inst, rule, k)) == stable(first)
            built = domain(inst)
            shuffled_worlds = {w: dict(reversed(list(inst.worlds[w].items())))
                               for w in reversed(list(inst.worlds))}
            options = {"worlds": shuffled_worlds, "world_count": len(inst.worlds),
                       "world_seed": WORLD_SEED, "bootstrap_version": VERSION,
                       "locked": (*reversed(inst.locked), *inst.locked),
                       "excluded": (*reversed(inst.excluded), *inst.excluded),
                       "quantization": inst.quantization, "deadline": far()}
            again = risk.declared_risk_selection(
                tuple(reversed(built.candidates)), tuple(reversed(built.requirements)),
                built.formation, rule=rule, tail_count=k if rule == "TAIL" else None, **options)
            assert stable(again) == stable(first), (seed, rule)


def test_provenance_keeps_lineage_and_hashes_the_declarations() -> None:
    source = {"dataset_hash": "data", "bootstrap_version": "shared-v1", "bootstrap_worlds": 12,
              "risk_version": "old", WALL: [1.0], "input_contract": {"old": True},
              "solver_status": "OPTIMAL"}
    result = run(carry_tail(), "TAIL", 2, provenance=source)
    record = result.provenance
    assert record["dataset_hash"] == "data" and record["bootstrap_version"] == "shared-v1"
    assert "bootstrap_worlds" not in record and "solver_status" not in record
    assert record["risk_version"] == risk.RISK_VERSION
    contract = record["input_contract"]
    assert (contract["rule"], contract["tail_count"], contract["world_count"]) == ("TAIL", 2, 2)
    assert (contract["world_seed"], contract["bootstrap_version"]) == (WORLD_SEED, VERSION)
    assert contract["world_fingerprint"] == result.certificate.world_fingerprint
    assert contract["kernel"]["kernel_version"] == engine.KERNEL_VERSION
    # The search setting risk._solver adds to 1.5's settings is part of what reproduces a run.
    assert contract["selection_search"] == "objective lower-bound probing"
    assert risk._solver(far(), 1).parameters.use_objective_lb_search
    assert record["input_fingerprint"] == engine.fingerprint(
        {"version": risk.RISK_VERSION, "contract": contract})
    assert not {"deadline", WALL, "risk_solve_deterministic_times"} & set(contract)
    assert set(record["source_fingerprints"]) == {
        "galactico/optimization/xi/risk.py",
        "galactico/optimization/squad/kernel.py",
        "galactico/optimization/xi/solver.py",
        "galactico/optimization/xi/tradeoffs.py",
        "galactico/optimization/xi/domain.py",
    }
    fingerprints = {record["input_fingerprint"]}
    for change in ({"world_seed": 1}, {"bootstrap_version": "other"}, {"locked": (1,)},
                   {"analyze_ties": False}):
        fingerprints.add(run(carry_tail(), "TAIL", 2, **change).provenance["input_fingerprint"])
    fingerprints.add(run(carry_tail(), "TAIL", 1).provenance["input_fingerprint"])
    assert len(fingerprints) == 6


# --------------------------------------------------------------------------- the module


def test_deterministic_times_are_recorded_at_ten_significant_digits(monkeypatch) -> None:
    # 1.5: the solver's deterministic_time, from the response, recorded by one rule in all four
    # tools: ten significant digits, because identical solves can differ in the last ulp.
    plant(monkeypatch, spent={1: 1.2345678901234567})
    result = run(carry_tail(), "TAIL", 2)
    times = result.provenance["risk_solve_deterministic_times"]
    assert times[0] == {"status": "OPTIMAL", "deterministic_time": 1.23456789}


def test_the_module_calls_no_shipped_solver_and_reads_no_objective_float() -> None:
    tree = ast.parse(Path(risk.__file__).read_text(encoding="utf-8"))
    names = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import,
                                                                         ast.ImportFrom))
             for alias in node.names}
    assert not names & {"solve_xi", "maximize_requirement", "bootstrap_selection",
                        "removal_sensitivity", "candidate_injection", "logging", "os"}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not attributes & {"objective_value", "best_objective_bound", "ObjectiveValue",
                             "BestObjectiveBound", "environ", "add_max_equality"}
    clocks = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
              and isinstance(node.value, ast.Name) and node.value.id == "time"}
    assert clocks == {"monotonic"}
    called = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call)
              and isinstance(node.func, ast.Name)}
    assert not called & {"open", "print"}
    # The encoding has no home outside the device: no public name and no dataclass field.
    public = set(risk.__all__)
    assert not {name for name in public if re.search("big|encod|base", name, re.IGNORECASE)}
    for cls in (risk.LossPair, risk.TailSums, risk.WorldLoss, risk.SolveRecord,
                risk.MembershipRow, risk.MembershipBlock, risk.RiskCertificate,
                risk.RiskSelection, risk.DiscardedWorld):
        assert not [f.name for f in fields(cls)
                    if re.search("big|encod|base|objective", f.name, re.IGNORECASE)]


def test_the_kernel_members_this_module_uses_are_pinned() -> None:
    # X9: kernel.py is not edited; these are the members risk.py relies on.
    def parameters(function):
        return [(p.name, p.kind.name) for p in inspect.signature(function).parameters.values()]

    assert parameters(ShortfallKernel._background) == [
        ("self", "POSITIONAL_OR_KEYWORD"), ("excluded", "POSITIONAL_OR_KEYWORD"),
        ("locked", "POSITIONAL_OR_KEYWORD"), ("pinned", "POSITIONAL_OR_KEYWORD"),
        ("vacant", "POSITIONAL_OR_KEYWORD"), ("values", "POSITIONAL_OR_KEYWORD")]
    assert parameters(ShortfallKernel._tables) == [
        ("self", "POSITIONAL_OR_KEYWORD"), ("background", "POSITIONAL_OR_KEYWORD"),
        ("conservative", "KEYWORD_ONLY")]
    for name, arguments in (("_expression", ["background", "coefficients"]),
                            ("_witness", ["background", "solver"]),
                            ("_admissible", ["background", "lineup"]),
                            ("_shortfalls", ["tables", "lineup"]),
                            ("_deadline", ["deadline"])):
        assert isinstance(inspect.getattr_static(ShortfallKernel, name), staticmethod), name
        assert [p for p, _ in parameters(getattr(ShortfallKernel, name))] == arguments, name
    assert parameters(ShortfallKernel.value) == [
        ("self", "POSITIONAL_OR_KEYWORD"), ("excluded", "KEYWORD_ONLY"),
        ("locked", "KEYWORD_ONLY"), ("pinned", "KEYWORD_ONLY"), ("vacant", "KEYWORD_ONLY"),
        ("values", "KEYWORD_ONLY"), ("deadline", "KEYWORD_ONLY")]
    assert {f.name for f in fields(KernelValue)} >= {
        "status", "maximum", "total", "stage_statuses", "solves", "reasons"}
    assert {f.name for f in fields(engine._Background)} >= {
        "model", "variables", "slots", "vectors", "locked", "reasons"}
    assert engine.Lineup == tuple[tuple[str, int], ...]
    assert engine.PER_SOLVE_DETERMINISTIC_LIMIT == 10.0


# --------------------------------------------------------------------------- the corpus


@pytest.mark.slow
def test_madrid_worlds_are_the_main_solve_s(corpus_root) -> None:
    """At B = 12 the fingerprint and the discarded worlds are those of the main solve with the
    same requirements and exclusions, and on world 0 alone the single-world invariant holds
    against solve_xi."""
    from galactico.api.decision_lab import SCENARIOS, decision_inputs
    from galactico.optimization.historical import SEED, load_snapshot

    snap = load_snapshot(SCENARIOS["madrid-2018-05-06"]["match_id"], worlds=12, seed=SEED)
    candidates, requirements = decision_inputs(snap, "4-3-3")  # the opt-in state (1.3)
    main = solve_xi(candidates, requirements, "4-3-3", seed=SEED, worlds=snap.worlds,
                    provenance=snap.provenance)
    options = {"world_seed": snap.provenance["seed"],
               "bootstrap_version": snap.provenance["bootstrap_version"], "seed": SEED}
    # A passed deadline answers UNKNOWN after the worlds are read: no selection is spent here.
    gone = risk.worst_world_selection(candidates, requirements, "4-3-3", worlds=snap.worlds,
                                      world_count=12, deadline=time.monotonic() - 1.0, **options)
    cert = gone.certificate
    assert cert.world_fingerprint == main.provenance["bootstrap_world_fingerprint"]
    assert [asdict(d) for d in cert.discarded_worlds] == main.provenance[
        "bootstrap_discarded_worlds"]
    one = {0: snap.worlds[0]}
    alone = risk.tail_selection(candidates, requirements, "4-3-3", worlds=one, world_count=1,
                                tail_count=1, analyze_ties=False,
                                deadline=time.monotonic() + 600, **options)
    if alone.status == "NOT_EVALUABLE":
        assert cert.discarded_worlds and cert.discarded_worlds[0].world_id == 0
        return
    changed = [replace(c, values=dict(snap.worlds[0].get(c.player_id, {}))) for c in candidates]
    reference = solve_xi(changed, requirements, "4-3-3", seed=SEED, analyze_ties=False)
    assert alone.status == "CERTIFIED" and reference.solution_status == "OPTIMAL"
    pair = alone.world_losses[0].selected
    assert (pair.maximum_shortfall, pair.total_shortfall) == tuple(
        round(v * 100_000) for v in reference.objective_vector)
