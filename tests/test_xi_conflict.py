"""CONFLICT (OR-XI-SPEC sections 3 and 9): the deletion filter against a brute-force oracle.

The oracle is ``tests/xi_exact_oracle.py``, written by another builder from the text of the
spec: its backtracking ``satisfiable``, its ``deletion_filter`` in the declared order and its
``restores_alone``. Seeded instances compare the set, every filter row and every restore test
with it in both arithmetics; ``solve_xi`` and ``kernel.satisfiable`` are differential
references for feasibility, never the oracle. Planted instances pin each status, each claim and
each stop. Undecided, refused and skipped tests are planted by replacing ``kernel._solver`` with
a proxy or ``kernel._Run.solve`` with one that returns no solver. Data-free: the corpus test is
marked slow and skips without the corpus.
"""

from __future__ import annotations

import inspect
import math
import random
import time
from collections import Counter
from dataclasses import asdict, replace
from fractions import Fraction

import pytest
import xi_exact_oracle as oracle
from ortools.sat.python import cp_model
from xi_exact_oracle import HARD_FLOOR_CONSERVATIVE, SOLVE_HALF_EVEN

from galactico.api import runtime
from galactico.domain.labels import scan_labels
from galactico.optimization.squad import kernel
from galactico.optimization.xi import conflict
from galactico.optimization.xi.ceilings import HARD_REQUIREMENT_ERROR
from galactico.optimization.xi.conflict import (
    CONFLICT_CLAIM,
    CONFLICT_FEASIBLE,
    CONFLICT_MODEL_INVALID,
    CONFLICT_NON_CLAIM,
    CONFLICT_NOT_DECIDED,
    CONFLICT_NOT_PROVEN_CLAIM,
    DELETION_ORDER,
    explain_floors,
    explain_solve,
)
from galactico.optimization.xi.domain import Candidate, Formation, Slot, TacticalRequirement
from galactico.optimization.xi.solver import _q, solve_xi
from galactico.optimization.xi.tradeoffs import _scaled

SEEDS = range(120)
TOKENS = {"EXACT", "LIMIT_REACHED", "DEADLINE", "MODEL_INVALID"}
STATUSES = {"MINIMAL_CERTIFIED", "NOT_PROVEN_MINIMAL", "MODEL_FEASIBLE", "UNDECIDED",
            "MODEL_INVALID"}
CLAIMS = {
    "MINIMAL_CERTIFIED": CONFLICT_CLAIM,
    "NOT_PROVEN_MINIMAL": CONFLICT_NOT_PROVEN_CLAIM,
    "MODEL_FEASIBLE": CONFLICT_FEASIBLE,
    "UNDECIDED": CONFLICT_NOT_DECIDED,
    "MODEL_INVALID": CONFLICT_MODEL_INVALID,
}


def far() -> float:
    return time.monotonic() + 600.0


def stable(result) -> dict:
    """``asdict`` without the wall times, which differ on every run (section 9)."""
    payload = asdict(result)
    del payload["provenance"]["conflict_solve_wall_times"]
    return payload


def check(result) -> None:
    """The rules every reply keeps: claim by status, copy guard, tokens, call accounting."""
    certificate = result.certificate
    assert result.status in STATUSES
    assert result.claim == CLAIMS[result.status]
    assert result.non_claim == CONFLICT_NON_CLAIM
    assert scan_labels(asdict(result)) == []
    assert certificate.completeness in TOKENS
    assert runtime.is_complete(asdict(result)) is (certificate.completeness == "EXACT")
    assert certificate.deletion_order == DELETION_ORDER
    made = [s for s in certificate.statuses if s != "NOT_RUN"]
    assert certificate.solves == len(made)
    times = result.provenance["conflict_solve_deterministic_times"]
    walls = result.provenance["conflict_solve_wall_times"]
    assert [entry["status"] for entry in times] == made and len(walls) == len(made)
    assert all(isinstance(w, float) and math.isfinite(w) and w >= 0 for w in walls)
    assert certificate.statuses[0] == certificate.initial_status
    ids = tuple(d.constraint_id for d in result.declarations)
    if result.status in ("MODEL_FEASIBLE", "UNDECIDED", "MODEL_INVALID"):
        assert result.tests == result.restore_tests == result.conflict == ()
        assert certificate.final_set_proof_solve is None
        assert (result.feasible_witness != ()) is (result.status == "MODEL_FEASIBLE")
        assert len(certificate.statuses) == 1
        return
    # The filter ran: one row per declaration, one restore row per member, and the counts.
    assert tuple(row.constraint_id for row in result.tests) == ids
    assert tuple(row.constraint_id for row in result.restore_tests) == result.conflict
    assert result.conflict == tuple(c for c in ids if c in result.conflict)
    outcome = {row.constraint_id: row.outcome for row in result.tests}
    assert all(outcome[c] != "DROPPED" for c in result.conflict)
    assert {c for c in ids if outcome[c] != "DROPPED"} == set(result.conflict)
    assert (certificate.members_with_witness + certificate.members_undecided
            + certificate.members_refused) == len(result.conflict)
    restored = [r for r in result.restore_tests if r.status != "NOT_APPLICABLE"]
    assert len(certificate.statuses) == 1 + len(ids) + len(restored)
    assert certificate.statuses[1:1 + len(ids)] == tuple(row.status for row in result.tests)
    assert certificate.statuses[1 + len(ids):] == tuple(r.status for r in restored)
    # The proof of the final set: INFEASIBLE, and on exactly that set.
    proof = certificate.final_set_proof_solve
    assert certificate.statuses[proof] == "INFEASIBLE"
    if proof > 0:
        tested = result.tests[proof - 1]
        assert tested.outcome == "DROPPED"
        later = result.tests[proof:]
        assert all(row.outcome != "DROPPED" for row in later)
    else:
        assert all(row.outcome != "DROPPED" for row in result.tests)
    for row in result.tests:
        if row.outcome != "KEPT_WITNESS":
            assert (row.witness, row.witness_excluded_players,
                    row.witness_missing_locked_players) == ((), (), ())
    for row in result.restore_tests:
        assert (row.witness != ()) is (row.restores_alone is True)
        if row.status == "NOT_APPLICABLE":
            assert row.constraint_id.startswith("slot:") and row.restores_alone is None
    if result.status == "MINIMAL_CERTIFIED":
        assert {outcome[c] for c in result.conflict} == {"KEPT_WITNESS"}


# --------------------------------------------------------------------------- inputs


def shape(*slots: tuple[str, tuple[str, ...]]) -> Formation:
    return Formation("test", tuple(Slot(sid, f"Place {sid}", pos, 0.5, 0.5) for sid, pos in slots))


def player(pid: int, position: str, values: dict, *, slots=None, minutes: int = 900) -> Candidate:
    return Candidate(pid, f"Player {pid}", position, values, minutes, slots)


def progression(minimum: float = 0.0, *, hard: bool = False) -> TacticalRequirement:
    return TacticalRequirement("progression", "Progression", "progression", minimum, 1.0,
                               hard=hard)


def domain(instance: oracle.Instance) -> oracle.DomainInputs:
    return oracle.domain_inputs(instance, slot_type=Slot, formation_type=Formation,
                                candidate_type=Candidate, requirement_type=TacticalRequirement)


def pinned_lock_and_exclusion(floor: float = 2.5):
    """Section 3.3 pinned: slots a, b {DF}, players 1 to 3 DF at 1.0, exclusion:1, a floor
    above 2 (no assignment sums above 2.0) and lock:1."""
    candidates = [player(p, "DF", {"progression": 1.0}) for p in (1, 2, 3)]
    return candidates, [progression()], shape(("a", ("DF",)), ("b", ("DF",))), {
        "progression": floor}


def three_slots():
    """Section 9: s1 {DF}, s2 {DF, MF}, s3 {MF}; 1 and 2 DF, 3 and 4 MF, each at 1.0."""
    candidates = [player(1, "DF", {"progression": 1.0}), player(2, "DF", {"progression": 1.0}),
                  player(3, "MF", {"progression": 1.0}), player(4, "MF", {"progression": 1.0})]
    formation = shape(("s1", ("DF",)), ("s2", ("DF", "MF")), ("s3", ("MF",)))
    return candidates, [progression()], formation


def oracle_instance(candidates, requirements, formation, quantization=100_000):
    return oracle.Instance(tuple(formation.slots), tuple(candidates), tuple(requirements),
                           quantization)


def floors_three_slots(**kwargs):
    candidates, requirements, formation = three_slots()
    return explain_floors(candidates, requirements, formation, floors={"progression": 3.5},
                          excluded=(2,), deadline=kwargs.pop("deadline", far()), **kwargs)


# --------------------------------------------------------------------------- planted solves


class Script:
    """Replaces ``kernel._solver``: call ``n`` (0-based) obeys ``plan[n]``, else ``every``.

    A plan may force a ``status`` or a ``deterministic_time``, shift the objective readings by
    ``2**-20`` (``ulp``), or run ``after`` once the solve returns, to move the clock.
    """

    def __init__(self, monkeypatch) -> None:
        self.calls = 0
        self.plan: dict[int, dict] = {}
        self.every: dict = {}
        self.reads = 0  # reads of objective_value or best_objective_bound
        original = kernel._solver
        script = self

        class Proxy:
            def __init__(self, actual, number):
                self.actual, self.number, self.status = actual, number, None

            @property
            def rules(self):
                return script.plan.get(self.number, script.every)

            def solve(self, model):
                status = self.actual.solve(model)
                self.status = self.rules.get("status", status)
                if "after" in self.rules:
                    self.rules["after"]()
                return self.status

            @property
            def deterministic_time(self):
                return self.rules.get("deterministic_time", self.actual.deterministic_time)

            @property
            def objective_value(self):
                script.reads += 1
                shift = 2**-20 if self.rules.get("ulp") and self.status == cp_model.OPTIMAL else 0
                return self.actual.objective_value - shift

            @property
            def best_objective_bound(self):
                script.reads += 1
                shift = 2**-20 if self.rules.get("ulp") and self.status == cp_model.OPTIMAL else 0
                return self.actual.best_objective_bound - shift

            def __getattr__(self, name):
                return getattr(self.actual, name)

        def factory(deadline, seed):
            script.calls += 1
            return Proxy(original(deadline, seed), script.calls - 1)

        monkeypatch.setattr(kernel, "_solver", factory)

    def reset(self, plan: dict | None = None, every: dict | None = None) -> None:
        self.calls, self.plan, self.every = 0, dict(plan or {}), dict(every or {})
        self.reads = 0


@pytest.fixture
def script(monkeypatch) -> Script:
    return Script(monkeypatch)


@pytest.fixture
def clock(monkeypatch) -> dict:
    """``time.monotonic`` plus an offset a planted solve can push past every deadline."""
    real, state = time.monotonic, {"offset": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: real() + state["offset"])
    return state


def pass_deadline(clock: dict):
    return lambda: clock.update(offset=1e7)


# --------------------------------------------------------------------------- the oracle


def meets(model: oracle.ConflictModel, tested, assignment) -> bool:
    """An independent check of an assignment against declarations of the oracle's model."""
    placed = [p for _, p in assignment if p is not None]
    if len(placed) != len(set(placed)) or [s for s, _ in assignment] != list(model.slot_ids):
        return False
    if any(p is not None and p not in model.options[i] for i, (_, p) in enumerate(assignment)):
        return False
    for c in tested:
        family, subject = c.split(":", 1)
        if family == "slot" and dict(assignment)[subject] is None:
            return False
        if family == "exclusion" and int(subject) in placed:
            return False
        if family == "lock" and int(subject) not in placed:
            return False
        if family == "floor" and sum(
            model.coefficients[subject][(i, p)] for i, (_, p) in enumerate(assignment)
            if p is not None and i in model.applicable[subject]
        ) < model.targets[subject]:
            return False
    return True


def compare(result, model: oracle.ConflictModel, seen: Counter | None = None) -> None:
    """The reply against the oracle's deletion filter and restore tests on the same model."""
    seen = seen if seen is not None else Counter()
    ids = tuple(d.constraint_id for d in result.declarations)
    assert ids == model.declarations
    targets = {d.subject: d.integer_target for d in result.declarations
               if d.family == "REQUIREMENT_FLOOR"}
    assert targets == dict(model.targets)
    truth = oracle.deletion_filter(model.declarations, model)
    assert result.status == truth.status
    assert result.certificate.completeness == "EXACT"
    seen[(result.status, len(result.conflict))] += 1
    if truth.status == "MODEL_FEASIBLE":
        assert meets(model, model.declarations, result.feasible_witness)
        assert oracle.satisfiable(model.declarations, model).satisfiable
        return
    # Equality with the oracle's set in the declared order, not just minimality.
    assert result.conflict == truth.conflict
    assert [row.outcome for row in result.tests] == [row.outcome for row in truth.rows]
    final = frozenset(result.conflict)
    assert not oracle.satisfiable(final, model).satisfiable
    for row in result.tests:
        if row.outcome == "KEPT_WITNESS":
            assert oracle.satisfiable(final - {row.constraint_id}, model).satisfiable
            assert meets(model, final - {row.constraint_id}, row.witness)
            placed = {p for _, p in row.witness if p is not None}
            assert row.witness_excluded_players == tuple(p for p in model.excluded if p in placed)
            assert row.witness_missing_locked_players == tuple(
                p for p in model.locked if p not in placed)
            seen["excluded used"] += bool(row.witness_excluded_players)
            seen["lock left out"] += bool(row.witness_missing_locked_players)
            seen["slot left empty"] += any(p is None for _, p in row.witness)
    for row in result.restore_tests:
        expected = oracle.restores_alone(row.constraint_id, model)
        assert row.restores_alone == expected
        seen[("restores", expected)] += 1
        if expected:
            assert meets(model, set(model.declarations) - {row.constraint_id}, row.witness)


def floors_model(instance, floors="drawn"):
    floors = instance.floors if floors == "drawn" else floors
    return floors, oracle.conflict_model(instance, arithmetic=HARD_FLOOR_CONSERVATIVE,
                                         floors=floors, locked=instance.locked,
                                         excluded=instance.excluded)


@pytest.mark.parametrize("variant", ["drawn", "none", "empty"])
def test_explain_floors_equals_the_oracle_deletion_filter_on_seeded_instances(variant):
    # drawn: the generator's floors (explicit, φ independent of m, or None); none: every
    # requirement at its minimum; empty: no floor at all.
    seen = Counter()
    for seed in SEEDS:
        instance = oracle.instances(seed).conflict_floors
        floors = {"drawn": instance.floors, "none": None, "empty": {}}[variant]
        _, model = floors_model(instance, floors)
        inputs = domain(instance)
        result = explain_floors(inputs.candidates, inputs.requirements, inputs.formation,
                                floors=floors, locked=instance.locked, excluded=instance.excluded,
                                quantization=instance.quantization, deadline=far())
        check(result)
        assert result.certificate.arithmetic == "HARD_FLOOR_CONSERVATIVE"
        assert result.certificate.rounding_policy == kernel.HARD_POLICY
        compare(result, model, seen)
    statuses = {status for status, *_ in seen if isinstance(status, str) and status.isupper()}
    assert {"MODEL_FEASIBLE", "MINIMAL_CERTIFIED"} <= statuses
    assert any(isinstance(k, tuple) and k[0] == "MINIMAL_CERTIFIED" and k[1] >= 2 for k in seen)
    assert seen[("restores", True)] and seen[("restores", False)]
    assert seen["slot left empty"]
    if variant != "empty":
        assert seen["excluded used"]


@pytest.mark.parametrize("mode", ["drawn", "BALANCE", "SATISFY"])
def test_explain_solve_equals_the_oracle_in_half_even_and_solve_xi_on_feasibility(mode):
    seen = Counter()
    for seed in SEEDS:
        instance = oracle.instances(seed).conflict_solve
        chosen = instance.mode if mode == "drawn" else mode
        model = oracle.conflict_model(instance, arithmetic=SOLVE_HALF_EVEN, mode=chosen,
                                      locked=instance.locked, excluded=instance.excluded)
        inputs = domain(instance)
        result = explain_solve(inputs.candidates, inputs.requirements, inputs.formation,
                               mode=chosen, locked=instance.locked, excluded=instance.excluded,
                               quantization=instance.quantization, deadline=far())
        check(result)
        assert result.certificate.arithmetic == "SOLVE_HALF_EVEN"
        assert result.certificate.rounding_policy == kernel.SHORTFALL_POLICY
        compare(result, model, seen)
        # The differential reference: the shipped solve on the same declarations.
        shipped = solve_xi(inputs.candidates, inputs.requirements, inputs.formation,
                           mode=chosen, locked=instance.locked, excluded=instance.excluded,
                           quantization=instance.quantization, analyze_ties=False)
        assert (result.status == "MODEL_FEASIBLE") is (
            shipped.solution_status in ("OPTIMAL", "FEASIBLE")), seed
        active = {a.requirement_id for a in shipped.requirements if a.status != "UNMEASURED"}
        assert set(result.requirements_in_force) == active
        floored = {d.subject for d in result.declarations if d.family == "REQUIREMENT_FLOOR"}
        hard = {r.requirement_id for r in inputs.requirements if r.hard}
        assert floored == (active if chosen == "SATISFY" else hard)
        seen[("hard", bool(hard))] += 1
        seen[("locked and excluded", bool(set(instance.locked) & set(instance.excluded)))] += 1
    assert seen[("hard", True)] and seen[("hard", False)]
    assert seen[("locked and excluded", True)]
    assert any(isinstance(k, tuple) and k[0] == "MODEL_FEASIBLE" for k in seen)
    assert any(isinstance(k, tuple) and k[0] == "MINIMAL_CERTIFIED" for k in seen)


def boundary_draw(seed: int) -> oracle.Instance:
    """A seeded instance on the rounding boundary (X2): q = 10, n = 1, every value (i + 0.6) / 10,
    so ``_q`` gives the coefficient i + 1 and the conservative rule i; the minimum is the largest
    half-even sum an XI reaches, so the conservative model can never meet it. Locks and
    exclusions are drawn, so some draws conflict in both arithmetics with other filter rows."""
    rng = random.Random(seed)
    slots = tuple(oracle.OracleSlot(f"s{j}", ("MF",), f"Place {j}")
                  for j in range(rng.randint(2, 3)))
    units = [rng.randint(0, 4) for _ in range(len(slots) + rng.randint(1, 2))]
    candidates = tuple(oracle.OracleCandidate(pid, "MF", {"r": (unit + 0.6) / 10},
                                              name=f"Player {pid}")
                       for pid, unit in enumerate(units, start=1))
    best = sum(sorted((unit + 1 for unit in units), reverse=True)[: len(slots)])
    requirement = oracle.OracleRequirement("r", "r", best / 10, 1.0, (), False, "Requirement r")
    ids = range(1, len(units) + 1)
    locked = tuple(p for p in ids if rng.random() < 0.25)
    excluded = tuple(p for p in ids if rng.random() < 0.2)
    return oracle.Instance(slots, candidates, (requirement,), 10, locked=locked,
                           excluded=excluded, mode="SATISFY")


def test_explain_solve_on_boundary_draws_is_half_even_and_not_conservative():
    # The seeded instances of the test above never put a filter row on the rounding boundary,
    # so these draws show that explain_solve's arithmetic is the solve's and not the floors'.
    seen = Counter()
    for seed in SEEDS[:60]:
        instance = boundary_draw(seed)
        half_even = oracle.conflict_model(instance, arithmetic=SOLVE_HALF_EVEN, mode="SATISFY",
                                          locked=instance.locked, excluded=instance.excluded)
        hard = oracle.conflict_model(instance, arithmetic=HARD_FLOOR_CONSERVATIVE,
                                     locked=instance.locked, excluded=instance.excluded)
        inputs = domain(instance)
        result = explain_solve(inputs.candidates, inputs.requirements, inputs.formation,
                               mode="SATISFY", locked=instance.locked,
                               excluded=instance.excluded, quantization=10, deadline=far())
        check(result)
        compare(result, half_even, seen)
        floors = oracle.deletion_filter(hard.declarations, hard)
        assert floors.status == "MINIMAL_CERTIFIED"  # no XI meets the minimum conservatively
        # Read as the conservative filter, the reply would be wrong exactly here.
        differs = (result.status, result.conflict, [r.outcome for r in result.tests]) != (
            floors.status, floors.conflict, [r.outcome for r in floors.rows])
        seen[("differs", result.status)] += differs
    assert seen[("differs", "MODEL_FEASIBLE")]
    assert seen[("differs", "MINIMAL_CERTIFIED")]


def test_explain_floors_without_floors_is_feasible_exactly_when_the_kernel_floors_are():
    compared = Counter()
    for seed in SEEDS:
        instance = oracle.instances(seed).conflict_floors
        inputs = domain(instance)
        assert not any(r.hard for r in inputs.requirements)
        result = explain_floors(inputs.candidates, inputs.requirements, inputs.formation,
                                locked=instance.locked, excluded=instance.excluded,
                                quantization=instance.quantization, deadline=far())
        floor = kernel.ShortfallKernel(
            inputs.candidates, inputs.requirements, inputs.formation,
            quantization=instance.quantization,
        ).satisfiable(locked=instance.locked, excluded=instance.excluded, deadline=far())
        assert (result.status == "MODEL_FEASIBLE") is (floor.status == "SATISFIABLE"), seed
        compared[floor.status] += 1
    assert {"SATISFIABLE", "NOT_SATISFIABLE", "UNFIELDABLE"} <= set(compared)


# --------------------------------------------------------------------------- pinned instances


def test_the_pinned_instance_of_3_3_returns_the_floor_with_a_conditional_claim():
    candidates, requirements, formation, floors = pinned_lock_and_exclusion()
    result = explain_floors(candidates, requirements, formation, floors=floors, locked=(1,),
                            excluded=(1,), deadline=far())
    check(result)
    assert (result.status, result.claim) == ("MINIMAL_CERTIFIED", CONFLICT_CLAIM)
    assert result.conflict == ("floor:progression",)
    (kept,) = [row for row in result.tests if row.outcome == "KEPT_WITNESS"]
    # The witness meets {lock:1}: player 1 is in it, his exclusion set aside. Which
    # assignment comes back is the solver's choice.
    assert 1 in {p for _, p in kept.witness} and kept.witness_excluded_players == (1,)
    (restore,) = result.restore_tests
    assert (restore.status, restore.restores_alone, restore.witness) == ("INFEASIBLE", False, ())
    # The clause "checking in another order can return another" is true here.
    model = oracle.conflict_model(oracle_instance(candidates, requirements, formation),
                                  arithmetic=HARD_FLOOR_CONSERVATIVE, floors=floors, locked=(1,),
                                  excluded=(1,))
    assert meets(model, {"lock:1"}, kept.witness)
    assert oracle.minimal_conflicting_sets(model) == (
        ("floor:progression",), ("exclusion:1", "lock:1"))
    floor_first = ("floor:progression", "slot:a", "slot:b", "exclusion:1", "lock:1")
    assert oracle.deletion_filter(floor_first, model).conflict == ("exclusion:1", "lock:1")


def test_the_three_slot_instance_has_one_set_and_its_member_restores_alone():
    result = floors_three_slots()
    check(result)
    assert (result.status, result.claim) == ("MINIMAL_CERTIFIED", CONFLICT_CLAIM)
    assert result.conflict == ("floor:progression",)
    assert [r.restores_alone for r in result.restore_tests] == [True]
    candidates, requirements, formation = three_slots()
    model = oracle.conflict_model(oracle_instance(candidates, requirements, formation),
                                  arithmetic=HARD_FLOOR_CONSERVATIVE,
                                  floors={"progression": 3.5}, locked=(), excluded=(2,))
    assert oracle.minimal_conflicting_sets(model) == (("floor:progression",),)
    assert meets(model, set(model.declarations) - {"floor:progression"},
                 result.restore_tests[0].witness)


def test_two_independent_conflicts_never_say_a_member_restores_an_xi():
    # Two players locked into one place, and a floor above every sum.
    candidates = [player(1, "DF", {"progression": 1.0}, slots=("a",)),
                  player(2, "DF", {"progression": 1.0}, slots=("a",)),
                  player(3, "MF", {"progression": 1.0})]
    formation = shape(("a", ("DF",)), ("b", ("MF",)))
    result = explain_floors(candidates, [progression()], formation,
                            floors={"progression": 5.0}, locked=(1, 2), deadline=far())
    check(result)
    assert result.status == "MINIMAL_CERTIFIED" and len(result.conflict) >= 1
    assert all(r.restores_alone is False for r in result.restore_tests)
    assert all(r.witness == () for r in result.restore_tests)
    assert result.feasible_witness == ()
    served = " ".join(str(v) for v in (result.claim, result.non_claim))
    assert "leaves at least one XI" not in served
    assert result.claim == CONFLICT_CLAIM  # conditional: "may still leave no XI"
    assert "may still leave no XI" in result.claim


def test_a_locked_and_excluded_player_alone_gives_exactly_that_pair():
    candidates, requirements, formation, _ = pinned_lock_and_exclusion()
    result = explain_floors(candidates, requirements, formation, floors={}, locked=(2,),
                            excluded=(2,), deadline=far())
    check(result)
    assert (result.status, result.conflict) == ("MINIMAL_CERTIFIED", ("exclusion:2", "lock:2"))
    witnesses = {row.constraint_id: row for row in result.tests}
    # Leaving the exclusion out, the lock can hold: player 2 placed. Leaving the lock out,
    # the exclusion can hold.
    assert witnesses["exclusion:2"].witness_excluded_players == (2,)
    assert witnesses["lock:2"].witness_missing_locked_players == (2,)
    assert [r.restores_alone for r in result.restore_tests] == [True, True]


def test_a_witness_that_leaves_out_a_locked_player_names_him():
    # Players 1 and 2 can only take place a; both locked.
    candidates = [player(1, "DF", {"progression": 1.0}), player(2, "DF", {"progression": 1.0})]
    result = explain_floors(candidates, [progression()], shape(("a", ("DF",))), floors={},
                            locked=(1, 2), deadline=far())
    check(result)
    assert result.conflict == ("lock:1", "lock:2")
    rows = {row.constraint_id: row for row in result.tests}
    assert rows["lock:1"].witness_missing_locked_players == (1,)
    assert rows["lock:2"].witness_missing_locked_players == (2,)
    assert rows["slot:a"].outcome == "DROPPED"


def test_a_place_nobody_can_fill_is_the_set_on_its_own():
    # Place c takes a FW and there is none; player 2 is unmeasured and admissible nowhere.
    candidates = [player(1, "DF", {"progression": 1.0}), player(2, "FW", {"progression": None}),
                  player(3, "DF", {"progression": 0.5})]
    formation = shape(("a", ("DF",)), ("b", ("DF",)), ("c", ("FW",)))
    result = explain_floors(candidates, [progression()], formation, floors={}, locked=(3,),
                            deadline=far())
    check(result)
    assert (result.status, result.conflict) == ("MINIMAL_CERTIFIED", ("slot:c",))
    (restore,) = result.restore_tests
    assert (restore.status, restore.restores_alone, restore.witness) == (
        "NOT_APPLICABLE", None, ())
    assert result.certificate.solves == 1 + len(result.declarations)


def test_the_boundary_instance_holds_under_half_even_and_not_conservatively():
    # q = 1, n = 1, two places, players at 0.75, minimum 1.5. Half-even 1 + 1 >= 2;
    # conservative 0 + 0 < 2.
    candidates = [player(1, "MF", {"r": 0.75}), player(2, "MF", {"r": 0.75})]
    requirements = [TacticalRequirement("r", "Requirement r", "r", 1.5, 1.0)]
    formation = shape(("a", ("MF",)), ("b", ("MF",)))
    floors = explain_floors(candidates, requirements, formation, quantization=1, deadline=far())
    check(floors)
    assert floors.status == "MINIMAL_CERTIFIED" and "floor:r" in floors.conflict
    solved = explain_solve(candidates, requirements, formation, mode="SATISFY", quantization=1,
                           deadline=far())
    check(solved)
    assert solved.status == "MODEL_FEASIBLE" and solved.claim == CONFLICT_FEASIBLE
    assert {p for _, p in solved.feasible_witness} == {1, 2}
    assert (solved.tests, solved.restore_tests, solved.conflict) == ((), (), ())
    assert solved.certificate.completeness == "EXACT"
    assert runtime.is_complete(asdict(solved))


def test_a_balance_explanation_without_a_hard_requirement_declares_no_floor():
    candidates, requirements, formation = three_slots()
    balance = explain_solve(candidates, requirements, formation, mode="BALANCE", deadline=far())
    assert {d.family for d in balance.declarations} == {"SLOT_COVERAGE"}
    hard = explain_solve(candidates, [replace(requirements[0], minimum=3.5, hard=True)],
                         formation, mode="BALANCE", deadline=far())
    assert "floor:progression" in hard.conflict
    # Two locked goalkeepers: both arithmetics, both modes, and solve_xi, find no XI.
    keepers = [player(1, "GK", {"progression": 0.0}), player(2, "GK", {"progression": 0.0}),
               player(3, "DF", {"progression": 1.0})]
    formation = shape(("gk", ("GK",)), ("lb", ("DF",)))
    for mode in ("BALANCE", "SATISFY"):
        result = explain_solve(keepers, requirements, formation, mode=mode, locked=(1, 2),
                               deadline=far())
        check(result)
        assert result.conflict == ("lock:1", "lock:2")
        shipped = solve_xi(keepers, requirements, formation, mode=mode, locked=(1, 2),
                           analyze_ties=False)
        assert shipped.solution_status == "INFEASIBLE"
    # The input contract floors different sets for the two modes.
    satisfy = explain_solve(candidates, requirements, formation=three_slots()[2],
                            mode="SATISFY", deadline=far())
    assert (balance.provenance["input_fingerprint"]
            != satisfy.provenance["input_fingerprint"])
    assert balance.provenance["input_contract"]["mode"] == "BALANCE"
    assert satisfy.provenance["input_contract"]["floors"] == [["progression", 0.0]]


def test_requirements_in_force_are_the_shipped_solve_s_active_set():
    candidates, requirements, formation = three_slots()
    unavailable = TacticalRequirement("goalkeeping", "Goalkeeping", "goalkeeping", 0, 1,
                                      evidence_class="UNAVAILABLE", status="unavailable")
    research = TacticalRequirement("side", "Side", "side", 0, 1, status="research")
    declared = [*requirements, unavailable, research]
    result = explain_solve(candidates, declared, formation, mode="SATISFY", deadline=far())
    shipped = solve_xi(candidates, declared, formation, mode="SATISFY", analyze_ties=False)
    active = tuple(sorted(a.requirement_id for a in shipped.requirements
                          if a.status != "UNMEASURED"))
    assert result.requirements_in_force == active == ("progression",)


# --------------------------------------------------------------------------- statuses and claims


def test_an_undecided_filter_test_keeps_its_member_unproved(script):
    # s0, slot:s1, slot:s2, slot:s3, then call 4 tests {floor:progression}: exclusion:2's test.
    script.plan[4] = {"status": cp_model.UNKNOWN}
    result = floors_three_slots()
    check(result)
    assert (result.status, result.claim) == ("NOT_PROVEN_MINIMAL", CONFLICT_NOT_PROVEN_CLAIM)
    assert result.conflict == ("exclusion:2", "floor:progression")
    rows = {row.constraint_id: row for row in result.tests}
    assert rows["exclusion:2"].outcome == "KEPT_UNDECIDED"
    assert rows["floor:progression"].outcome == "KEPT_WITNESS"
    assert result.certificate.members_undecided == 1
    assert (result.certificate.completeness, result.certificate.stopped_by) == (
        "DEADLINE", "WALL_CLOCK")
    # CONFLICT_CLAIM would be false: {floor:progression} alone cannot hold.
    candidates, requirements, formation = three_slots()
    model = oracle.conflict_model(oracle_instance(candidates, requirements, formation),
                                  arithmetic=HARD_FLOOR_CONSERVATIVE,
                                  floors={"progression": 3.5}, locked=(), excluded=(2,))
    assert not oracle.satisfiable({"floor:progression"}, model).satisfiable


def test_a_deadline_after_the_slot_tests_leaves_both_members_not_run(script, clock):
    script.plan[3] = {"after": pass_deadline(clock)}
    result = floors_three_slots()
    check(result)
    assert (result.status, result.claim) == ("NOT_PROVEN_MINIMAL", CONFLICT_NOT_PROVEN_CLAIM)
    assert result.conflict == ("exclusion:2", "floor:progression")
    assert [row.outcome for row in result.tests] == ["DROPPED"] * 3 + ["NOT_RUN"] * 2
    assert [r.status for r in result.restore_tests] == ["NOT_RUN", "NOT_RUN"]
    assert result.certificate.members_undecided == 2
    assert result.certificate.statuses == ("INFEASIBLE",) * 4 + ("NOT_RUN",) * 4
    assert result.certificate.solves == 4
    assert (result.certificate.completeness, result.certificate.stopped_by) == (
        "DEADLINE", "WALL_CLOCK")
    assert not runtime.is_complete(asdict(result))


def test_a_test_whose_run_returns_no_solver_is_not_run_with_every_later_one(
        monkeypatch, clock):
    # The deadline passes between the loop's own check and the call (kernel.py:197-200).
    original, calls = kernel._Run.solve, []

    def solve(self, model):
        calls.append(1)
        if len(calls) == 3:
            clock.update(offset=1e7)
            return "UNKNOWN", None
        return original(self, model)

    monkeypatch.setattr(kernel._Run, "solve", solve)
    result = floors_three_slots()
    check(result)
    outcomes = [row.outcome for row in result.tests]
    assert outcomes == ["DROPPED", "NOT_RUN", "NOT_RUN", "NOT_RUN", "NOT_RUN"]
    assert "KEPT_UNDECIDED" not in outcomes and "UNKNOWN" not in result.certificate.statuses
    assert result.status == "NOT_PROVEN_MINIMAL"
    assert [r.status for r in result.restore_tests] == ["NOT_APPLICABLE", "NOT_APPLICABLE",
                                                        "NOT_RUN", "NOT_RUN"]
    assert result.certificate.solves == 2
    assert (result.certificate.completeness, result.certificate.stopped_by) == (
        "DEADLINE", "WALL_CLOCK")


def test_a_feasible_model_is_shown_with_one_xi_and_nothing_else():
    candidates, requirements, formation = three_slots()
    result = explain_floors(candidates, requirements, formation, floors={"progression": 2.0},
                            deadline=far())
    check(result)
    assert (result.status, result.claim) == ("MODEL_FEASIBLE", CONFLICT_FEASIBLE)
    assert (result.tests, result.restore_tests, result.conflict) == ((), (), ())
    assert len(result.feasible_witness) == 3 and result.certificate.completeness == "EXACT"
    assert runtime.is_complete(asdict(result))


def test_a_passed_deadline_decides_nothing_and_is_not_stored():
    result = floors_three_slots(deadline=time.monotonic() - 1.0)
    check(result)
    assert (result.status, result.claim) == ("UNDECIDED", CONFLICT_NOT_DECIDED)
    assert result.certificate.statuses == ("NOT_RUN",) and result.certificate.solves == 0
    assert (result.certificate.completeness, result.certificate.stopped_by) == (
        "DEADLINE", "WALL_CLOCK")
    assert not runtime.is_complete(asdict(result))


def test_a_refused_initial_test_states_nothing(script):
    script.plan[0] = {"status": cp_model.MODEL_INVALID}
    result = floors_three_slots()
    check(result)
    assert (result.status, result.claim) == ("MODEL_INVALID", CONFLICT_MODEL_INVALID)
    assert (result.certificate.completeness, result.certificate.stopped_by) == (
        "MODEL_INVALID", None)
    assert not runtime.is_complete(asdict(result))
    script.reset({0: {"status": cp_model.UNKNOWN, "deterministic_time": 10.0}})
    limited = floors_three_slots()
    check(limited)
    assert (limited.status, limited.certificate.completeness, limited.certificate.stopped_by) == (
        "UNDECIDED", "LIMIT_REACHED", "DETERMINISTIC_LIMIT")


def test_a_refused_filter_test_keeps_its_member_and_the_filter_continues(script):
    # Call 4 is the filter test of exclusion:2, which tests the set {floor:progression}.
    script.plan[4] = {"status": cp_model.MODEL_INVALID}
    result = floors_three_slots()
    check(result)
    certificate = result.certificate
    assert (result.status, result.claim) == ("NOT_PROVEN_MINIMAL", CONFLICT_NOT_PROVEN_CLAIM)
    assert result.conflict == ("exclusion:2", "floor:progression")
    rows = {row.constraint_id: row for row in result.tests}
    refused = rows["exclusion:2"]
    assert (refused.status, refused.outcome) == ("MODEL_INVALID", "KEPT_REFUSED")
    assert (refused.witness, refused.witness_excluded_players,
            refused.witness_missing_locked_players) == ((), (), ())
    assert rows["floor:progression"].outcome == "KEPT_WITNESS"
    assert "NOT_RUN" not in certificate.statuses
    assert certificate.final_set_proof_solve == 3
    assert certificate.statuses[0] == certificate.statuses[3] == "INFEASIBLE"
    assert certificate.members_refused == 1
    assert (certificate.completeness, certificate.stopped_by) == ("MODEL_INVALID", None)
    assert [r.status for r in result.restore_tests] == ["INFEASIBLE", "OPTIMAL"]
    candidates, requirements, formation = three_slots()
    model = oracle.conflict_model(oracle_instance(candidates, requirements, formation),
                                  arithmetic=HARD_FLOOR_CONSERVATIVE,
                                  floors={"progression": 3.5}, locked=(), excluded=(2,))
    assert not oracle.satisfiable(result.conflict, model).satisfiable
    assert not oracle.satisfiable({"floor:progression"}, model).satisfiable


def test_a_refused_restore_test_leaves_the_set_and_its_claim_standing(script):
    # The pinned 3.3 instance with floors {}: the set {exclusion:2, lock:2}. s0, two slots,
    # two filter tests, then the restore tests are calls 5 and 6.
    candidates, requirements, formation, _ = pinned_lock_and_exclusion()
    script.plan[5] = {"status": cp_model.MODEL_INVALID}
    result = explain_floors(candidates, requirements, formation, floors={}, locked=(2,),
                            excluded=(2,), deadline=far())
    check(result)
    assert (result.status, result.claim) == ("MINIMAL_CERTIFIED", CONFLICT_CLAIM)
    first, second = result.restore_tests
    assert (first.status, first.restores_alone) == ("MODEL_INVALID", None)
    assert (second.status, second.restores_alone) == ("OPTIMAL", True)
    assert result.certificate.completeness == "MODEL_INVALID"
    assert not runtime.is_complete(asdict(result))


@pytest.mark.parametrize("planted,completeness,stopped_by", [
    # A filter test stopped at its deterministic limit, then the clock passes the deadline.
    ({1: {"status": cp_model.UNKNOWN, "deterministic_time": 10.0}, 2: {"jump": True}},
     "DEADLINE", "WALL_CLOCK"),
    # Deterministic stops alone.
    ({4: {"status": cp_model.UNKNOWN, "deterministic_time": 10.0}},
     "LIMIT_REACHED", "DETERMINISTIC_LIMIT"),
    # An UNKNOWN that reached neither limit.
    ({4: {"status": cp_model.UNKNOWN}}, "DEADLINE", "WALL_CLOCK"),
    # One on a restore test (call 6, the restore test of floor:progression).
    ({6: {"status": cp_model.UNKNOWN, "deterministic_time": 10.0}},
     "LIMIT_REACHED", "DETERMINISTIC_LIMIT"),
    ({6: {"status": cp_model.UNKNOWN}}, "DEADLINE", "WALL_CLOCK"),
])
def test_the_stop_of_each_undecided_test_decides_the_tokens(
        script, clock, planted, completeness, stopped_by):
    for number, rules in planted.items():
        rules = dict(rules)
        if rules.pop("jump", False):
            rules["after"] = pass_deadline(clock)
        script.plan[number] = rules
    result = floors_three_slots()
    check(result)
    assert (result.certificate.completeness, result.certificate.stopped_by) == (
        completeness, stopped_by)
    assert not runtime.is_complete(asdict(result))
    if 6 in planted:
        # An undecided restore test never changes the status of the set.
        assert (result.status, result.conflict) == ("MINIMAL_CERTIFIED", ("floor:progression",))
        assert result.restore_tests[0].restores_alone is None


# --------------------------------------------------------------------------- inputs and arithmetic


def test_refusals_name_no_value():
    candidates, requirements, formation = three_slots()
    for call, refused_text in (
        (lambda: explain_solve(candidates, requirements, formation, mode="LEXICOGRAPHIC",
                               deadline=far()), "LEXICOGRAPHIC"),
        (lambda: explain_solve(candidates, requirements, formation, mode=None, deadline=far()),
         "None"),
        (lambda: explain_floors(candidates, requirements, formation, floors={"stamina": 1.25},
                                deadline=far()), "stamina"),
        (lambda: explain_floors(candidates, requirements, formation,
                                floors={"progression": math.nan}, deadline=far()), "nan"),
        (lambda: explain_floors(candidates, [replace(requirements[0], hard=True)], formation,
                                deadline=far()), "progression"),
        # The hard flag is refused even when explicit floors leave it out.
        (lambda: explain_floors(candidates, [replace(requirements[0], hard=True)], formation,
                                floors={}, deadline=far()), "progression"),
    ):
        with pytest.raises(ValueError) as refused:
            call()
        assert refused_text not in str(refused.value)
        assert scan_labels(str(refused.value)) == []
    with pytest.raises(ValueError, match="marked hard"):
        explain_floors(candidates, [replace(requirements[0], hard=True)], formation,
                       floors={}, deadline=far())
    assert str(HARD_REQUIREMENT_ERROR) and conflict.MODE_ERROR == "mode must be BALANCE or SATISFY"


def test_tables_equal_the_kernel_tables_on_the_keys_both_hold():
    for seed in SEEDS[:40]:
        for instance, conservative in ((oracle.instances(seed).conflict_floors, True),
                                       (oracle.instances(seed).conflict_solve, False)):
            inputs = domain(instance)
            engine = kernel.ShortfallKernel(inputs.candidates, inputs.requirements,
                                            inputs.formation, quantization=instance.quantization)
            reference = engine._tables(
                engine._background(instance.excluded, (), None, (), None),
                conservative=conservative)
            keys = engine._background((), (), None, (), None)
            for r in inputs.requirements:
                own = conflict._floor(r, r.minimum, list(keys.variables), keys.vectors,
                                      instance.quantization, conservative)
                coefficients, target = reference[r.requirement_id]
                assert own.target == target
                shared = set(own.coefficients) & set(coefficients)
                assert {k: own.coefficients[k] for k in shared} == {
                    k: coefficients[k] for k in shared}
                assert set(coefficients) <= set(own.coefficients)  # exclusions are declarations
    # The two rules differ where the float division does: _q, not exact half-even.
    one = [player(1, "MF", {"r": 1.344465})]
    r = TacticalRequirement("r", "Requirement r", "r", 1.344465, 1.0)
    keys = kernel.ShortfallKernel(one, [r], shape(("a", ("MF",))))._background(
        (), (), None, (), None)
    half_even = conflict._floor(r, 1.344465, list(keys.variables), keys.vectors, 100_000, False)
    floor = conflict._floor(r, 1.344465, list(keys.variables), keys.vectors, 100_000, True)
    assert half_even.target == _q(1.344465, 1.0, 100_000) == 134_446
    assert floor.target == math.ceil(_scaled(1.344465, 1.0, 100_000)) == 134_447


def test_a_magnitude_refusal_reads_excluded_players_too():
    candidates = [player(1, "MF", {"r": 1e12}), player(2, "MF", {"r": 1.0})]
    requirements = [TacticalRequirement("r", "Requirement r", "r", 0.5, 1.0)]
    with pytest.raises(ValueError, match="too large"):
        explain_solve(candidates, requirements, shape(("a", ("MF",))), mode="SATISFY",
                      excluded=(1,), deadline=far())
    # solve_xi never reads an excluded player's coefficient (solver.py:200-201, 267).
    shipped = solve_xi(candidates, requirements, shape(("a", ("MF",))), mode="SATISFY",
                       excluded=(1,), analyze_ties=False)
    assert shipped.solution_status == "OPTIMAL"


def test_a_tampered_filter_witness_and_a_tampered_restore_witness_each_raise(monkeypatch):
    original = conflict._Model.assignment

    def empty_places(self, solver):
        return tuple((sid, None) for sid, _ in original(self, solver))

    # The pinned 3.3 instance: its one KEPT_WITNESS assignment must place player 1 (lock:1).
    candidates, requirements, formation, floors = pinned_lock_and_exclusion()
    with monkeypatch.context() as patch:
        patch.setattr(conflict._Model, "assignment", empty_places)
        with pytest.raises(RuntimeError):
            explain_floors(candidates, requirements, formation, floors=floors, locked=(1,),
                           excluded=(1,), deadline=far())
    # The three-slot instance: the restore witness of floor:progression must fill each place.
    calls = []

    def late_empty(self, solver):
        calls.append(1)
        found = original(self, solver)
        return tuple((sid, None) for sid, _ in found) if len(calls) == 2 else found

    with monkeypatch.context() as patch:
        patch.setattr(conflict._Model, "assignment", late_empty)
        with pytest.raises(RuntimeError):
            floors_three_slots()
    assert len(calls) == 2  # the filter witness, then the restore witness


def test_an_integer_floor_and_its_float_are_one_declaration():
    candidates, requirements, formation = three_slots()
    whole, real = (explain_floors(candidates, requirements, formation,
                                  floors={"progression": value}, excluded=(2,), deadline=far())
                   for value in (4, 4.0))
    assert stable(whole) == stable(real)
    (floor,) = [d for d in whole.declarations if d.family == "REQUIREMENT_FLOOR"]
    assert type(floor.raw_floor) is float


def test_deterministic_times_are_recorded_at_ten_significant_digits(script):
    # 1.5: the solver's deterministic_time, from the response, recorded by one rule in all four
    # tools: ten significant digits, because identical solves can differ in the last ulp.
    script.reset({0: {"deterministic_time": 1.2345678901234567}})
    result = floors_three_slots()
    times = result.provenance["conflict_solve_deterministic_times"]
    assert times[0]["deterministic_time"] == 1.23456789


def test_integers_from_the_solver_are_never_read_off_objective_value(script, monkeypatch):
    plain = floors_three_slots()
    script.reset(every={"ulp": True})
    shifted = floors_three_slots()
    assert stable(shifted) == stable(plain)
    assert script.reads == 0  # a feasibility test has no objective: neither float is read
    monkeypatch.setattr(conflict._Model, "holds", lambda self, assignment, tested: False)
    with pytest.raises(RuntimeError):
        floors_three_slots()


def test_reordered_inputs_and_repeated_runs_give_one_answer():
    rng = random.Random(20261018)
    for seed in (0, 3, 5, 8):
        instance = oracle.instances(seed).conflict_floors
        inputs = domain(instance)

        def run(candidates, requirements, locked, excluded, floors, inst=instance, inp=inputs):
            return explain_floors(candidates, requirements, inp.formation, floors=floors,
                                  locked=locked, excluded=excluded,
                                  quantization=inst.quantization, deadline=far())

        reference = stable(run(inputs.candidates, inputs.requirements, instance.locked,
                               instance.excluded, instance.floors))
        assert stable(run(inputs.candidates, inputs.requirements, instance.locked,
                          instance.excluded, instance.floors)) == reference
        candidates, requirements = list(inputs.candidates), list(inputs.requirements)
        rng.shuffle(candidates)
        rng.shuffle(requirements)
        floors = None if instance.floors is None else dict(
            sorted(instance.floors.items(), reverse=True))
        again = run(candidates, requirements, tuple(reversed(instance.locked)),
                    tuple(reversed(instance.excluded)), floors)
        assert stable(again) == reference


def test_every_served_sentence_passes_the_copy_guard():
    for name in conflict.__all__:
        value = getattr(conflict, name)
        if isinstance(value, str):
            assert scan_labels(value) == [], name


def test_the_private_kernel_members_this_module_uses_keep_their_signatures():
    """X9: conflict.py reads these members of the unedited kernel.py (and ceilings._Calls
    reads ``_Run``)."""
    members = {
        kernel.ShortfallKernel._deadline: ["deadline"],
        kernel.ShortfallKernel._player_ids: ["self", "ids", "name"],
        kernel.ShortfallKernel._background: ["self", "excluded", "locked", "pinned", "vacant",
                                             "values"],
        kernel._Run.__init__: ["self", "deadline", "seed"],
        kernel._Run.solve: ["self", "model"],
    }
    for member, parameters in members.items():
        assert list(inspect.signature(member).parameters) == parameters, member.__qualname__
    assert {"variables", "vectors"} <= set(kernel._Background.__dataclass_fields__)
    engine = kernel.ShortfallKernel([player(1, "MF", {"r": 1.0})], [], shape(("a", ("MF",))))
    assert engine._player_ids([1], "locked") == frozenset({1})
    with pytest.raises(ValueError):
        engine._player_ids([2], "locked")


# --------------------------------------------------------------------------- the corpus


NODE_LIMIT = 10**7  # a guard on run time, not an expectation about the data (section 9)


def conflict_equals_the_oracle(candidates, requirements, formation, locks) -> tuple[str, int]:
    """``explain_floors`` with a floor two units above every XI's conservative sum under the
    locks, against the oracle's deletion filter and restore tests. Above the node limit the
    oracle raises, so the test fails rather than skips."""
    instance = oracle.Instance(tuple(formation.slots), tuple(candidates), tuple(requirements),
                               100_000)
    r = next(r for r in requirements if r.requirement_id == "progression")
    vectors = oracle.point_vectors(instance)
    best = max(
        sum(oracle.floor_coef(vectors[p][r.metric], r.normalizer, 100_000) for s, p in x
            if not r.slot_ids or s in r.slot_ids)
        for x in oracle.xis(instance, locked=locks, excluded=(), vectors=vectors)
    )
    floors = {"progression": (best + 1.5) * r.normalizer / 100_000}
    model = oracle.conflict_model(instance, arithmetic=HARD_FLOOR_CONSERVATIVE, floors=floors,
                                  locked=locks, excluded=())
    assert model.targets["progression"] > best
    truth = oracle.deletion_filter(model.declarations, model, node_limit=NODE_LIMIT)
    result = explain_floors(candidates, requirements, formation, floors=floors, locked=locks,
                            deadline=far())
    check(result)
    assert (result.status, result.conflict) == (truth.status, truth.conflict)
    assert [row.outcome for row in result.tests] == [row.outcome for row in truth.rows]
    for row in result.restore_tests:
        assert row.restores_alone == oracle.restores_alone(row.constraint_id, model,
                                                           node_limit=NODE_LIMIT)
    return result.status, max(truth.nodes)


def test_the_corpus_check_runs_on_a_synthetic_eleven():
    """The body of the corpus test on a made-up squad, so it is exercised without data."""
    from galactico.optimization.xi.domain import FORMATIONS

    squad = [("GK", ("gk",)), ("DF", ("lb",)), ("DF", ("lcb", "rcb")), ("DF", ("lcb", "rcb")),
             ("DF", ("rb", "lb")), ("MF", ("dm",)), ("MF", ("lcm", "rcm")), ("MF", ("rcm",)),
             ("FW", ("lw",)), ("FW", ("st",)), ("FW", ("rw", "st"))]
    candidates = [Candidate(100 + i, f"Player {i}", position,
                            {"progression": 0.1 * (i % 4), "side": 0.1}, 900, slots)
                  for i, (position, slots) in enumerate(squad)]
    outfield = tuple(s.slot_id for s in FORMATIONS["4-3-3"].slots if s.slot_id != "gk")
    requirements = [
        TacticalRequirement("progression", "Progression", "progression", 0.6, 0.5, outfield),
        TacticalRequirement("side", "Side", "side", 0.5, 0.5, outfield),
    ]
    status, nodes = conflict_equals_the_oracle(candidates, requirements, FORMATIONS["4-3-3"],
                                               (108, 109))
    assert status == "MINIMAL_CERTIFIED" and nodes <= NODE_LIMIT


@pytest.mark.slow
def test_madrid_bbc_locks_and_a_raised_floor_equal_the_oracle(corpus_root):
    from galactico.api.decision_lab import decision_inputs, scenarios
    from galactico.optimization.historical import load_snapshot
    from galactico.optimization.xi.domain import FORMATIONS

    # The opt-in: the three measured requirements in force, as decision_inputs builds them.
    candidates, requirements = decision_inputs(load_snapshot(2565907, worlds=0), "4-3-3")
    assert len([r for r in requirements if r.active]) == 3
    bbc = next(p for p in scenarios()["presets"] if p["id"] == "bbc")
    status, _ = conflict_equals_the_oracle(candidates, requirements, FORMATIONS["4-3-3"],
                                           tuple(sorted(bbc["locks"])))
    assert status in ("MINIMAL_CERTIFIED", "NOT_PROVEN_MINIMAL")


def test_the_raw_floor_check_is_exact_in_the_conservative_arithmetic():
    # 0.15 + 0.15 meets 0.3 exactly, while 14999 + 14999 < 30000: conservatively unmet.
    candidates = [player(1, "DF", {"r": 0.15}), player(2, "MF", {"r": 0.15})]
    requirements = [TacticalRequirement("r", "Requirement r", "r", 0.3, 1.0)]
    formation = shape(("a", ("DF",)), ("b", ("MF",)))
    assert Fraction(0.15) * 2 >= Fraction(0.3)
    result = explain_floors(candidates, requirements, formation, deadline=far())
    check(result)
    assert result.conflict == ("floor:r",)
    assert result.declarations[-1].integer_target == 30_000
