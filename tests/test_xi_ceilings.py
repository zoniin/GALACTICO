"""CEILING (OR-XI-SPEC sections 2 and 9): both ends of every range against a brute-force oracle.

The oracle is ``tests/xi_exact_oracle.py``, written by another builder from the text of the
spec; nothing here imports it into the tool. Seeded instances compare integer ends, brackets,
witnesses and the two minimum facts with the oracle's enumeration of the inner set; planted
instances pin each state, each claim, each stop and each place where a witness, a bound or
neither decides a fact. Solver outcomes that a small instance never produces (UNKNOWN,
FEASIBLE, MODEL_INVALID, a deterministic stop, a deadline between two solves) are planted by
replacing ``kernel._solver`` with a proxy. Data-free: the two corpus tests are marked slow and
skip without the corpus.
"""

from __future__ import annotations

import importlib
import importlib.util
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

from galactico.api import runtime
from galactico.domain.labels import scan_labels
from galactico.optimization.squad import kernel
from galactico.optimization.xi import ceilings
from galactico.optimization.xi.ceilings import (
    CEILING_CLAIM,
    CEILING_EMPTY,
    CEILING_NON_CLAIM,
    CEILING_NOT_DECIDED,
    CEILING_PARTIAL_CLAIM,
    CEILING_REFUSED,
    UNFIELDABLE_PROVED,
    requirement_ranges,
)
from galactico.optimization.xi.domain import Candidate, Formation, Slot, TacticalRequirement
from galactico.optimization.xi.solver import _q, solve_xi
from galactico.optimization.xi.tradeoffs import (
    MAX_MAGNITUDE,
    OBJECTIVE_POLICY,
    _scaled,
    maximize_requirement,
)

SEEDS = range(120)
TOKENS = {"EXACT", "LIMIT_REACHED", "DEADLINE", "MODEL_INVALID"}
STATES = {"FIELDABLE", "UNFIELDABLE", "NOT_SATISFIABLE", "FLOORS_UNMET", "UNKNOWN",
          "MODEL_INVALID"}


def far() -> float:
    return time.monotonic() + 600.0


def stable(result) -> dict:
    """``asdict`` without the wall times, which differ on every run (section 9)."""
    payload = asdict(result)
    del payload["provenance"]["ceiling_solve_wall_times"]
    return payload


def check(result) -> None:
    """The rules every reply keeps: copy guard, tokens, caching, the call accounting."""
    certificate = result.certificate
    assert scan_labels(asdict(result)) == []
    assert certificate.feasible_set in STATES
    assert certificate.completeness in TOKENS
    assert runtime.is_complete(asdict(result)) is (certificate.completeness == "EXACT")
    assert result.non_claim == CEILING_NON_CLAIM
    made = [s for s in certificate.statuses if s != "NOT_RUN"]
    assert certificate.solves == len(made)
    times = result.provenance["ceiling_solve_deterministic_times"]
    walls = result.provenance["ceiling_solve_wall_times"]
    assert [entry["status"] for entry in times] == made
    assert len(walls) == len(made)
    assert all(isinstance(w, float) and math.isfinite(w) and w >= 0 for w in walls)
    if certificate.completeness == "EXACT":
        assert certificate.stopped_by is None


# --------------------------------------------------------------------------- inputs


def shape(*slots: tuple[str, tuple[str, ...]]) -> Formation:
    return Formation("test", tuple(Slot(sid, f"Place {sid}", pos, 0.5, 0.5) for sid, pos in slots))


def player(pid: int, position: str, values: dict, *, slots=None, minutes: int = 900) -> Candidate:
    return Candidate(pid, f"Player {pid}", position, values, minutes, slots)


def requirement(rid: str, minimum: float = 0.0, normalizer: float = 1.0, *, slot_ids=(),
                hard: bool = False) -> TacticalRequirement:
    return TacticalRequirement(rid, f"Requirement {rid}", rid, minimum, normalizer,
                               tuple(slot_ids), hard=hard)


def domain(instance: oracle.Instance) -> oracle.DomainInputs:
    return oracle.domain_inputs(instance, slot_type=Slot, formation_type=Formation,
                                candidate_type=Candidate, requirement_type=TacticalRequirement)


def run(instance: oracle.Instance, *, floors=None, **kwargs):
    inputs = domain(instance)
    return requirement_ranges(
        inputs.candidates, inputs.requirements, inputs.formation, floors=floors,
        locked=kwargs.pop("locked", instance.locked),
        excluded=kwargs.pop("excluded", instance.excluded),
        quantization=instance.quantization, deadline=kwargs.pop("deadline", far()), **kwargs,
    )


def two_witness():
    """Section 9: q = 1, n = 1; floors f >= 2 and g >= 1 keep A1+B1 (r 1.2) and A2+B2 (r 1.8)."""
    def one(pid, slot, r, f, g):
        return player(pid, "MF", {"r": r, "f": f, "g": g}, slots=(slot,))

    candidates = [one(1, "a", 0.6, 1, 1), one(2, "a", 1.4, 2, 0), one(3, "b", 0.6, 1, 0),
                  one(4, "b", 0.4, 0, 1)]
    requirements = [requirement("r", 1.5), requirement("f"), requirement("g")]
    return candidates, requirements, shape(("a", ("MF",)), ("b", ("MF",)))


def top_tie(rates=(0.85, 0.63, 1.67, 0.2, 0.76, 1.26, 0.22)) -> oracle.Instance:
    """Section 9: q = 10; {1,3,6} and {3,5,6} tie at O = 38 with sums 3.78 and 3.69."""
    return oracle.Instance(
        (oracle.OracleSlot("s0", ("A", "B")), oracle.OracleSlot("s1", ("A", "B")),
         oracle.OracleSlot("s2", ("A",))),
        tuple(oracle.OracleCandidate(i, "A", {"r": v}) for i, v in enumerate(rates, 1)),
        (oracle.OracleRequirement("r", "r", 0.0, 1.0),),
        10,
    )


def instance_a(minimum_r1: float = 0.3) -> oracle.Instance:
    """Section 9, instance A: p1, p2 (0.15, 5.0) meet the raw floor r1 >= 0.3 exactly, and
    14999 + 14999 < 30000 leaves their XI out of the inner set."""
    values = {1: (0.15, 5.0), 2: (0.15, 5.0), 3: (1.0, 0.0), 4: (1.0, 0.0)}
    return oracle.Instance(
        (oracle.OracleSlot("a", ("DF",)), oracle.OracleSlot("b", ("MF",))),
        tuple(oracle.OracleCandidate(p, "DF" if p in (1, 3) else "MF",
                                     {"r1": v[0], "r2": v[1]}) for p, v in values.items()),
        (oracle.OracleRequirement("r1", "r1", minimum_r1, 1.0),
         oracle.OracleRequirement("r2", "r2", 8.0, 1.0)),
        100_000,
    )


def locked_pair():
    """One place, two players locked into it: no XI, and the kernel records no reason."""
    candidates = [player(1, "A", {"r1": 0.5, "r2": 0.5}), player(2, "A", {"r1": 0.5, "r2": 0.5})]
    return candidates, [requirement("r1"), requirement("r2")], shape(("a", ("A",)))


def pair_of_places():
    """Two places, three players, two requirements: every solve is decided and witnessed."""
    candidates = [player(1, "A", {"r1": 0.5, "r2": 1.0}), player(2, "A", {"r1": 1.5, "r2": 0.2}),
                  player(3, "A", {"r1": 1.0, "r2": 0.7})]
    requirements = [requirement("r1", 1.0), requirement("r2", 1.0)]
    return candidates, requirements, shape(("a", ("A",)), ("b", ("A",)))


def unreachable_floor():
    """XIs exist; none meets r1 >= 5."""
    candidates = [player(1, "A", {"r1": 0.5}), player(2, "A", {"r1": 0.5})]
    return candidates, [requirement("r1", 0.25)], shape(("a", ("A",))), {"r1": 5.0}


# --------------------------------------------------------------------------- planted solves


class Script:
    """Replaces ``kernel._solver``: call ``n`` (0-based) obeys ``plan[n]``, else ``every``.

    A plan may force a ``status``, a ``deterministic_time``, a ``bound`` (a function of the
    true bound), objective readings that are off by ``2**-20`` (``ulp``), or run ``after``
    once the solve returns, to move the clock between two solves.
    """

    def __init__(self, monkeypatch) -> None:
        self.calls = 0
        self.plan: dict[int, dict] = {}
        self.every: dict = {}
        self.reads: list[tuple[str, int]] = []  # (objective float read, status of that solve)
        original = kernel._solver
        script = self

        class Proxy:
            def __init__(self, actual, number):
                self.actual, self.number = actual, number
                self.status = None

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
            def best_objective_bound(self):
                script.reads.append(("best_objective_bound", self.status))
                bound = self.actual.best_objective_bound
                if self.rules.get("ulp") and self.status == cp_model.OPTIMAL:
                    return bound - 2**-20
                return self.rules["bound"](bound) if "bound" in self.rules else bound

            @property
            def objective_value(self):
                script.reads.append(("objective_value", self.status))
                value = self.actual.objective_value
                if self.rules.get("ulp") and self.status == cp_model.OPTIMAL:
                    return value - 2**-20
                return value

            def __getattr__(self, name):
                return getattr(self.actual, name)

        def factory(deadline, seed):
            script.calls += 1
            return Proxy(original(deadline, seed), script.calls - 1)

        monkeypatch.setattr(kernel, "_solver", factory)

    def reset(self, plan: dict | None = None, every: dict | None = None) -> None:
        """A new plan, counted from the next tool call's first solve."""
        self.calls, self.plan, self.every = 0, dict(plan or {}), dict(every or {})
        self.reads = []


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


def oracle_integer(instance, lineup, rid: str) -> int:
    r = next(r for r in instance.requirements if r.requirement_id == rid)
    vectors = oracle.point_vectors(instance)
    return sum(oracle.objective(vectors[p][r.metric], r.normalizer, instance.quantization)
               for s, p in lineup if not r.slot_ids or s in r.slot_ids)


def exact(instance, lineup, rid: str) -> Fraction:
    r = next(r for r in instance.requirements if r.requirement_id == rid)
    return oracle.exact_sum(lineup, r, oracle.point_vectors(instance))


def band(item, integer: int, sign: int, quantization: int) -> Fraction:
    """``(n / q) * integer + sign * e``, exact."""
    return Fraction(item.normalizer) * (2 * integer + sign * item.applicable_slots) / (
        2 * quantization)


def bracket(result) -> dict[str, tuple[Fraction | None, Fraction | None]]:
    """Per range, the proved outer ends: the least end's lower bound, the largest's upper."""
    q = result.certificate.quantization
    rows = {}
    for item in result.ranges:
        least, largest = item.least.integer_bound, item.largest.integer_bound
        rows[item.requirement_id] = (
            None if least is None else band(item, least, -1, q),
            None if largest is None else band(item, largest, 1, q),
        )
    return rows


@pytest.mark.parametrize("with_floors", [True, False])
def test_ends_brackets_witnesses_and_facts_equal_the_oracle_on_seeded_instances(with_floors):
    seen = Counter()
    for seed in SEEDS:
        instance = oracle.instances(seed).ceiling
        floors = instance.floors if with_floors else None
        truth = oracle.ceilings(instance, floors=floors, locked=instance.locked,
                                excluded=instance.excluded)
        result = run(instance, floors=floors)
        check(result)
        certificate = result.certificate
        seen[certificate.feasible_set] += 1
        assert certificate.feasible_set == truth.state, seed
        assert (certificate.completeness, certificate.stopped_by) == ("EXACT", None)
        if truth.state != "FIELDABLE":
            assert result.ranges == () and result.claim == CEILING_EMPTY, seed
            continue
        assert result.claim == CEILING_CLAIM
        # The features section 9 names, counted where a range exists.
        metrics = {r.metric for r in instance.requirements}
        values = [p.values.get(m) for p in instance.candidates for m in metrics]
        seen["locks"] += bool(instance.locked)
        seen["exclusions"] += bool(instance.excluded)
        seen["None values"] += any(v is None for v in values)
        seen["zero minutes"] += any(p.minutes == 0 for p in instance.candidates)
        seen["negative rates"] += any(v is not None and v < 0 for v in values)
        outer = bracket(result)
        floored = dict(floors or {})
        for item, want in zip(result.ranges, truth.ranges, strict=True):
            rid = item.requirement_id
            assert (rid, item.applicable_slots) == (want.requirement_id, want.applicable_slots)
            assert item.largest.integer_value == want.largest_integer, seed
            assert item.least.integer_value == want.least_integer, seed
            for end in (item.largest, item.least):
                assert end.certification == "QUANTIZED_OPTIMAL"
                assert end.integer_bound == end.integer_value
                # The witness is an XI of the inner set, its integer recomputed by the oracle.
                assert end.lineup in truth.feasible, seed
                assert oracle_integer(instance, end.lineup, rid) == end.integer_value
                assert end.attained == float(exact(instance, end.lineup, rid))
                for fid, phi in floored.items():
                    assert exact(instance, end.lineup, fid) >= Fraction(phi)
            low, high = outer[rid]
            assert low <= want.sums[0] and want.sums[-1] <= high, seed
            assert Fraction(item.largest.raw_bound) >= high
            assert Fraction(item.least.raw_bound) <= low
            assert Fraction(item.raw_rounding_error_bound) >= want.allowance
            for fact, truth_fact, reason, witness, sign in (
                (item.minimum_reached_by_some_xi, want.minimum_reached,
                 item.minimum_reached_reason, item.minimum_reached_witness, 1),
                (item.minimum_missed_by_some_xi, want.minimum_missed,
                 item.minimum_missed_reason, item.minimum_missed_witness, -1),
            ):
                seen[("fact", fact)] += 1
                if fact is None:
                    # Only a QUANTIZED_OPTIMAL end, whose band holds the minimum.
                    assert reason == "ALLOWANCE" and witness is None, seed
                    seen[("reason", reason)] += 1
                    end = item.largest if sign == 1 else item.least
                    width = abs(Fraction(end.raw_bound) - Fraction(end.attained))
                    assert width <= 2 * Fraction(item.raw_rounding_error_bound) + Fraction(
                        1, 10**9)
                    continue
                assert fact == truth_fact and reason is None, seed
                if fact:
                    end = item.largest if witness == "LARGEST" else item.least
                    total = exact(instance, end.lineup, rid)
                    assert (total >= want.minimum) if sign == 1 else (total < want.minimum)
                    seen[("witness", witness)] += 1
                else:
                    assert witness is None
    # Not vacuous: every state the oracle names, and each kind of fact.
    expected = {"FIELDABLE", "UNFIELDABLE"} | ({"NOT_SATISFIABLE"} if with_floors else set())
    assert expected <= set(seen)
    assert seen[("fact", True)] and seen[("fact", False)]
    assert seen[("witness", "LARGEST")] and seen[("witness", "LEAST")]
    assert seen[("fact", None)] == seen[("reason", "ALLOWANCE")] > 0
    for feature in ("locks", "exclusions", "None values", "zero minutes", "negative rates"):
        assert seen[feature], feature


def test_both_witnesses_decide_and_an_end_without_a_solution_leaves_the_other_deciding(script):
    candidates, requirements, formation = two_witness()
    result = requirement_ranges(candidates, requirements, formation, floors={"g": 1, "f": 2},
                                quantization=1, deadline=far())
    check(result)
    item = {r.requirement_id: r for r in result.ranges}["r"]
    assert (item.largest.integer_value, item.least.integer_value) == (2, 1)
    assert item.largest.attained == 1.2 and item.least.attained == pytest.approx(1.8)
    # Reached by the LEAST witness (1.8), missed by the LARGEST one (1.2).
    assert (item.minimum_reached_by_some_xi, item.minimum_reached_witness) == (True, "LEAST")
    assert (item.minimum_missed_by_some_xi, item.minimum_missed_witness) == (True, "LARGEST")
    # f, g, r in id order: call 5 is r's LEAST solve. Without it the LARGEST witness still
    # decides "missed", and "reached" falls inside the proved LARGEST end's allowance.
    script.reset({5: {"status": cp_model.UNKNOWN}})
    partial = requirement_ranges(candidates, requirements, formation, floors={"f": 2, "g": 1},
                                 quantization=1, deadline=far())
    check(partial)
    item = {r.requirement_id: r for r in partial.ranges}["r"]
    assert item.least.certification == "NO_SOLUTION" and item.least.lineup == ()
    assert (item.minimum_missed_by_some_xi, item.minimum_missed_witness) == (True, "LARGEST")
    assert (item.minimum_reached_by_some_xi, item.minimum_reached_reason) == (None, "ALLOWANCE")
    assert partial.claim == CEILING_PARTIAL_CLAIM


def one_place(value: float, minimum: float, q: int = 1):
    candidates = [player(1, "A", {"r": value}), player(2, "A", {"r": value / 2})]
    return candidates, [requirement("r", minimum)], shape(("a", ("A",))), q


@pytest.mark.parametrize("direction,call,offset,minimum,fact,reason_field", [
    ("LARGEST", 0, 5, 3.0, "minimum_reached_by_some_xi", "minimum_reached_reason"),
    ("LEAST", 1, -5, -1.0, "minimum_missed_by_some_xi", "minimum_missed_reason"),
])
def test_an_unproved_end_leaves_a_fact_not_certified_never_inside_the_allowance(
        script, direction, call, offset, minimum, fact, reason_field):
    # The end is FEASIBLE with a finite bound 5 units out: the minimum lies between its
    # witness and that bound, more than 2e (one unit here) away from the witness.
    candidates, requirements, formation, q = one_place(1.0, minimum)
    script.plan[call] = {"status": cp_model.FEASIBLE, "bound": lambda b: b + offset}
    result = requirement_ranges(candidates, requirements, formation, quantization=q,
                                deadline=far())
    check(result)
    (item,) = result.ranges
    end = getattr(item, direction.lower())
    assert end.certification == "FEASIBLE_NOT_PROVEN" and end.integer_bound is not None
    gap = abs(Fraction(end.raw_bound) - Fraction(end.attained))
    assert gap > 2 * Fraction(item.raw_rounding_error_bound)
    assert (getattr(item, fact), getattr(item, reason_field)) == (None, "NOT_CERTIFIED")
    # A finite bound on every end: the full claim stands.
    assert result.claim == CEILING_CLAIM
    assert (result.certificate.completeness, result.certificate.stopped_by) == (
        "DEADLINE", "WALL_CLOCK")


@pytest.mark.parametrize("call,infinite", [(0, math.inf), (1, -math.inf)])
def test_an_end_whose_bound_is_not_finite_keeps_its_witness_and_reports_no_bound(
        script, call, infinite):
    candidates, requirements, formation, q = one_place(1.0, 3.0)
    script.plan[call] = {"status": cp_model.FEASIBLE, "bound": lambda _: infinite}
    result = requirement_ranges(candidates, requirements, formation, quantization=q,
                                deadline=far())
    check(result)
    (item,) = result.ranges
    end = item.largest if call == 0 else item.least
    assert end.certification == "FEASIBLE_NOT_PROVEN"
    assert end.lineup and end.integer_value is not None and end.attained is not None
    assert (end.integer_bound, end.raw_bound) == (None, None)
    assert result.claim == CEILING_PARTIAL_CLAIM
    if call == 0:
        # m = 3 above every witness and no LARGEST bound: not decided, not certified.
        assert (item.minimum_reached_by_some_xi, item.minimum_reached_reason) == (
            None, "NOT_CERTIFIED")
    else:
        # The LEAST witness (0.5) stays below m = 3: decided by the witness alone.
        assert (item.minimum_missed_by_some_xi, item.minimum_missed_witness) == (True, "LEAST")


def test_a_proved_end_decides_by_witness_or_bound_and_leaves_its_band_to_the_allowance():
    # q = 10: 0.84 rounds to 8, so the LARGEST band is [0.84, 0.85].
    candidates, requirements, formation, q = one_place(0.84, 0.845, q=10)
    result = requirement_ranges(candidates, requirements, formation, quantization=q,
                                deadline=far())
    (item,) = result.ranges
    assert (item.minimum_reached_by_some_xi, item.minimum_reached_reason) == (None, "ALLOWANCE")
    assert item.minimum_missed_by_some_xi is True
    above = requirement_ranges(candidates, [requirement("r", 0.86)], formation,
                               quantization=q, deadline=far())
    assert above.ranges[0].minimum_reached_by_some_xi is False  # off the proved bound
    below = requirement_ranges(candidates, [requirement("r", 0.8)], formation,
                               quantization=q, deadline=far())
    assert below.ranges[0].minimum_reached_by_some_xi is True   # off the witness


def test_an_unproved_end_decides_by_its_witness_or_its_finite_bound(script):
    candidates, requirements, formation, q = one_place(1.0, 2.0)
    script.reset(every={"status": cp_model.FEASIBLE})
    result = requirement_ranges(candidates, requirements, formation, quantization=q,
                                deadline=far())
    (item,) = result.ranges
    # Bound 1 (+ e 0.5) < 2: False off the unproved end's bound; missed True off its witness.
    assert item.largest.certification == "FEASIBLE_NOT_PROVEN"
    assert (item.minimum_reached_by_some_xi, item.minimum_missed_by_some_xi) == (False, True)


def test_the_top_tie_brackets_the_oracle_extremes_without_claiming_the_witness_reaches_them():
    instance = top_tie()
    truth = oracle.ceilings(instance, floors=None, locked=(), excluded=())
    (want,) = truth.ranges
    assert (want.largest_integer, want.largest_sum) == (38, Fraction(0.85) + Fraction(1.67)
                                                        + Fraction(1.26))
    tied = {frozenset(p for _, p in x) for x in truth.feasible
            if oracle_integer(instance, x, "r") == 38}
    assert tied == {frozenset({1, 3, 6}), frozenset({3, 5, 6})}
    result = run(instance)
    (item,) = result.ranges
    low, high = bracket(result)["r"]
    assert item.largest.integer_value == 38
    assert oracle_integer(instance, item.largest.lineup, "r") == 38
    assert exact(instance, item.largest.lineup, "r") <= want.largest_sum <= high
    assert low <= want.least_sum <= exact(instance, item.least.lineup, "r")
    # Printed outward at four decimals, the texts still hold both extremes.
    assert outward(exact(instance, item.largest.lineup, "r"), up=False) <= want.largest_sum
    assert want.largest_sum <= outward(high, up=True)
    assert outward(low, up=False) <= want.least_sum
    assert want.least_sum <= outward(exact(instance, item.least.lineup, "r"), up=True)


def outward(value: Fraction, *, up: bool) -> Fraction:
    scaled = value * 10_000
    return Fraction(math.ceil(scaled) if up else math.floor(scaled), 10_000)


def test_a_witness_tied_at_the_rounded_optimum_can_miss_the_largest_sum():
    # One place at q = 100000: 0.0000155 and 0.000015 both round to 2.
    import ortools

    assert round(Fraction(0.0000155) * 100_000) == round(Fraction(0.000015) * 100_000) == 2
    missed = 0
    for values in ((0.0000155, 0.000015), (0.000015, 0.0000155)):
        instance = oracle.Instance(
            (oracle.OracleSlot("a", ("A",)),),
            tuple(oracle.OracleCandidate(p, "A", {"r": v}) for p, v in enumerate(values, 1)),
            (oracle.OracleRequirement("r", "r", 0.0, 1.0),),
            100_000,
        )
        (want,) = oracle.ceilings(instance, floors=None, locked=(), excluded=()).ranges
        result = run(instance)
        (item,) = result.ranges
        low, high = bracket(result)["r"]
        assert exact(instance, item.largest.lineup, "r") <= want.largest_sum <= high
        assert low <= want.least_sum <= exact(instance, item.least.lineup, "r")
        missed += exact(instance, item.largest.lineup, "r") < want.largest_sum
    # Recorded with the OR-Tools version: which tied XI comes back is the solver's choice.
    assert missed >= 1, ortools.__version__


# --------------------------------------------------------------------------- states and claims


def test_claim_per_state_and_no_claim_states_more_than_its_state_proves(script):
    def solve(inputs, **kwargs):
        candidates, requirements, formation, *rest = inputs
        floors = rest[0] if rest else None
        result = requirement_ranges(candidates, requirements, formation, floors=floors,
                                    deadline=kwargs.pop("deadline", far()), **kwargs)
        check(result)
        return result

    proved = solve(pair_of_places())
    assert (proved.certificate.feasible_set, proved.claim) == ("FIELDABLE", CEILING_CLAIM)
    assert proved.certificate.completeness == "EXACT"
    # A proved LARGEST end beside an UNKNOWN LEAST solve: FIELDABLE, partial.
    script.reset({1: {"status": cp_model.UNKNOWN}})
    assert solve(pair_of_places()).claim == CEILING_PARTIAL_CLAIM
    # Every solve UNKNOWN: nothing found, nothing proved.
    script.reset(every={"status": cp_model.UNKNOWN})
    undecided = solve(pair_of_places())
    assert (undecided.certificate.feasible_set, undecided.claim) == (
        "UNKNOWN", CEILING_NOT_DECIDED)
    assert {end.certification for r in undecided.ranges for end in (r.largest, r.least)} == {
        "NO_SOLUTION"}
    script.reset()
    late = solve(pair_of_places(), deadline=time.monotonic() - 1.0)
    assert (late.certificate.feasible_set, late.claim) == ("UNKNOWN", CEILING_NOT_DECIDED)
    # Proved empty: by proof (two players locked into one place), by construction, by floors.
    for empty, state in ((solve(locked_pair(), locked=(1, 2)), "UNFIELDABLE"),
                         (solve(locked_pair(), locked=(1,), excluded=(1,)), "UNFIELDABLE"),
                         (solve(unreachable_floor()), "NOT_SATISFIABLE")):
        assert (empty.certificate.feasible_set, empty.claim, empty.ranges) == (
            state, CEILING_EMPTY, ())
    # FLOORS_UNMET: the cause solve undecided.
    script.reset({1: {"status": cp_model.UNKNOWN}})
    unmet = solve(unreachable_floor())
    assert (unmet.certificate.feasible_set, unmet.claim) == ("FLOORS_UNMET", CEILING_EMPTY)
    # Refused, at a range solve and at the cause solve.
    script.reset({2: {"status": cp_model.MODEL_INVALID}})
    refused = solve(pair_of_places())
    script.reset({1: {"status": cp_model.MODEL_INVALID}})
    cause = solve(unreachable_floor())
    for reply in (refused, cause):
        assert (reply.certificate.feasible_set, reply.claim) == ("MODEL_INVALID", CEILING_REFUSED)
        assert (reply.ranges, reply.certificate.completeness) == ((), "MODEL_INVALID")
    assert refused.certificate.statuses == ("OPTIMAL", "OPTIMAL", "MODEL_INVALID")
    assert cause.certificate.statuses == ("INFEASIBLE", "MODEL_INVALID")
    assert cause.certificate.stopped_by is None


def test_floors_scope_every_bound_to_the_conservative_inner_set():
    instance = instance_a()
    every = oracle.xis(instance, locked=(), excluded=(), vectors=oracle.point_vectors(instance))
    boundary = (("a", 1), ("b", 2))
    # (p1, p2) meets the raw floor exactly and sums to 10 on r2, yet lies outside the set.
    assert boundary in every
    assert exact(instance, boundary, "r1") >= Fraction(0.3)
    assert exact(instance, boundary, "r2") == 10
    truth = oracle.ceilings(instance, floors={"r1": 0.3}, locked=(), excluded=())
    assert boundary not in truth.feasible
    result = run(instance, floors={"r1": 0.3})
    check(result)
    r1, r2 = result.ranges
    assert result.floors == (("r1", 0.3),)
    # No XI of the inner set reaches 8 on r2; the boundary XI does.
    assert r2.largest.integer_value == 500_000
    assert r2.minimum_reached_by_some_xi is False
    every_reaches = run(instance_a(minimum_r1=1.0), floors={"r1": 0.3})
    assert every_reaches.ranges[0].minimum_missed_by_some_xi is False
    # Without floors the boundary XI counts and reaches the minimum.
    free = run(instance)
    assert free.floors == () and free.ranges[1].minimum_reached_by_some_xi is True


def test_an_exact_fact_can_differ_from_the_half_even_satisfy_solve():
    # Instance B: 0.500004 twice sums to 1.000008 >= 1.000006, while _q gives
    # 50000 + 50000 < 100001.
    candidates = [player(1, "A", {"r": 0.500004}), player(2, "A", {"r": 0.500004})]
    requirements = [requirement("r", 1.000006)]
    formation = shape(("a", ("A",)), ("b", ("A",)))
    result = requirement_ranges(candidates, requirements, formation, deadline=far())
    assert result.ranges[0].minimum_reached_by_some_xi is True
    shipped = solve_xi(candidates, requirements, formation, mode="SATISFY", analyze_ties=False)
    assert shipped.solution_status == "INFEASIBLE"


def test_a_proof_after_an_undecided_end_supersedes_it(script):
    # r1's LARGEST solve planted UNKNOWN at its deterministic limit, r1's LEAST INFEASIBLE.
    script.plan[0] = {"status": cp_model.UNKNOWN, "deterministic_time": 10.0}
    candidates, requirements, formation = locked_pair()
    result = requirement_ranges(candidates, requirements, formation, locked=(1, 2),
                                deadline=far())
    check(result)
    certificate = result.certificate
    assert certificate.feasible_set == "UNFIELDABLE"
    assert (certificate.completeness, certificate.stopped_by) == ("EXACT", None)
    assert certificate.statuses == ("UNKNOWN", "INFEASIBLE")
    assert result.reasons == (UNFIELDABLE_PROVED,)
    assert runtime.is_complete(asdict(result))
    # With floors, a cause solve that finds an XI: NOT_SATISFIABLE, proved.
    script.reset({0: {"status": cp_model.UNKNOWN, "deterministic_time": 10.0}})
    candidates, requirements, formation, floors = unreachable_floor()
    floored = requirement_ranges(candidates, requirements, formation, floors=floors,
                                 deadline=far())
    check(floored)
    assert floored.certificate.feasible_set == "NOT_SATISFIABLE"
    assert floored.certificate.statuses[:2] == ("UNKNOWN", "INFEASIBLE")
    assert (floored.certificate.completeness, floored.certificate.stopped_by) == ("EXACT", None)
    assert floored.reasons == ()


def test_empty_feasible_sets_by_construction_by_proof_and_by_floors():
    candidates, requirements, formation = locked_pair()
    construction = requirement_ranges(candidates, requirements, formation, locked=(1,),
                                      excluded=(1,), deadline=far())
    check(construction)
    assert construction.certificate.feasible_set == "UNFIELDABLE"
    assert (construction.certificate.statuses, construction.certificate.solves) == ((), 0)
    # The kernel's own reasons, by construction (kernel.py:489-527).
    assert construction.reasons == kernel.ShortfallKernel(
        candidates, requirements, formation)._background((1,), (1,), None, (), None).reasons
    assert "A player cannot be both locked and excluded." in construction.reasons
    proof = requirement_ranges(candidates, requirements, formation, locked=(1, 2),
                               deadline=far())
    check(proof)
    assert proof.certificate.feasible_set == "UNFIELDABLE"
    assert proof.certificate.statuses == ("INFEASIBLE",)
    assert proof.reasons == (UNFIELDABLE_PROVED,)
    candidates, requirements, formation, floors = unreachable_floor()
    floored = requirement_ranges(candidates, requirements, formation, floors=floors,
                                 deadline=far())
    check(floored)
    assert floored.certificate.feasible_set == "NOT_SATISFIABLE"
    assert floored.certificate.statuses == ("INFEASIBLE", "OPTIMAL")
    for result in (construction, proof, floored):
        assert result.certificate.completeness == "EXACT" and result.ranges == ()


def test_an_undecided_or_skipped_cause_solve_leaves_the_floors_unmet_and_unstored(script, clock):
    candidates, requirements, formation, floors = unreachable_floor()
    script.plan[1] = {"status": cp_model.UNKNOWN}
    unknown = requirement_ranges(candidates, requirements, formation, floors=floors,
                                 deadline=far())
    check(unknown)
    assert unknown.certificate.feasible_set == "FLOORS_UNMET"
    assert (unknown.certificate.completeness, unknown.certificate.stopped_by) == (
        "DEADLINE", "WALL_CLOCK")
    assert not runtime.is_complete(asdict(unknown))
    script.reset({1: {"status": cp_model.UNKNOWN, "deterministic_time": 10.0}})
    limited = requirement_ranges(candidates, requirements, formation, floors=floors,
                                 deadline=far())
    assert (limited.certificate.completeness, limited.certificate.stopped_by) == (
        "LIMIT_REACHED", "DETERMINISTIC_LIMIT")
    # The deadline passes between the INFEASIBLE solve and the cause solve.
    script.reset({0: {"after": pass_deadline(clock)}})
    skipped = requirement_ranges(candidates, requirements, formation, floors=floors,
                                 deadline=far())
    check(skipped)
    certificate = skipped.certificate
    assert certificate.feasible_set == "FLOORS_UNMET"
    assert certificate.statuses == ("INFEASIBLE", "NOT_RUN") and certificate.solves == 1
    assert (certificate.completeness, certificate.stopped_by) == ("DEADLINE", "WALL_CLOCK")
    assert not runtime.is_complete(asdict(skipped))


def test_a_deadline_after_the_first_requirement_leaves_every_later_end_not_certified(
        script, clock):
    script.plan[1] = {"after": pass_deadline(clock)}
    candidates, requirements, formation = pair_of_places()
    result = requirement_ranges(candidates, requirements, formation, deadline=far())
    check(result)
    certificate = result.certificate
    assert certificate.feasible_set == "FIELDABLE"
    assert certificate.statuses == ("OPTIMAL", "OPTIMAL", "NOT_RUN", "NOT_RUN")
    assert (certificate.completeness, certificate.stopped_by) == ("DEADLINE", "WALL_CLOCK")
    assert result.claim == CEILING_PARTIAL_CLAIM
    first, second = result.ranges
    assert first.largest.certification == first.least.certification == "QUANTIZED_OPTIMAL"
    for end in (second.largest, second.least):
        assert (end.solver_status, end.certification, end.integer_value) == (
            "NOT_RUN", "NO_SOLUTION", None)
    assert (second.minimum_reached_by_some_xi, second.minimum_reached_reason) == (
        None, "NOT_CERTIFIED")
    assert (second.minimum_missed_by_some_xi, second.minimum_missed_reason) == (
        None, "NOT_CERTIFIED")


def test_a_passed_deadline_runs_nothing_and_states_no_number():
    candidates, requirements, formation = pair_of_places()
    result = requirement_ranges(candidates, requirements, formation,
                                deadline=time.monotonic() - 1.0)
    check(result)
    certificate = result.certificate
    assert certificate.statuses == ("NOT_RUN",) * 4 and certificate.solves == 0
    assert (certificate.completeness, certificate.stopped_by) == ("DEADLINE", "WALL_CLOCK")
    assert all(end.integer_value is None and end.attained is None and end.lineup == ()
               for item in result.ranges for end in (item.largest, item.least))
    # Even where a reason is a proof by construction.
    blocked = requirement_ranges(candidates, requirements, formation, locked=(1,), excluded=(1,),
                                 deadline=time.monotonic() - 1.0)
    assert blocked.certificate.feasible_set == "UNKNOWN" and blocked.reasons == ()


LIMIT = {"status": cp_model.UNKNOWN, "deterministic_time": 10.0}


@pytest.mark.parametrize("planted,completeness,stopped_by", [
    # A call stopped at its deterministic limit, then the clock passes the deadline during the
    # next one, so the last two are skipped: the load-dependent stop wins.
    ({0: LIMIT, 1: {"jump": True}}, "DEADLINE", "WALL_CLOCK"),
    # Deterministic stops alone, an UNKNOWN and an unproved FEASIBLE incumbent.
    ({0: LIMIT, 2: {"status": cp_model.FEASIBLE, "deterministic_time": 10.0}},
     "LIMIT_REACHED", "DETERMINISTIC_LIMIT"),
    # An UNKNOWN that reached neither limit.
    ({1: {"status": cp_model.UNKNOWN}}, "DEADLINE", "WALL_CLOCK"),
    # Its deterministic time reached the limit, but the wall clock had run out as well.
    ({1: {**LIMIT, "jump": True}}, "DEADLINE", "WALL_CLOCK"),
])
def test_the_stop_of_each_undecided_call_decides_the_tokens(
        script, clock, planted, completeness, stopped_by):
    for number, rules in planted.items():
        rules = dict(rules)
        if rules.pop("jump", False):
            rules["after"] = pass_deadline(clock)
        script.plan[number] = rules
    candidates, requirements, formation = pair_of_places()
    result = requirement_ranges(candidates, requirements, formation, deadline=far())
    check(result)
    assert (result.certificate.completeness, result.certificate.stopped_by) == (
        completeness, stopped_by)
    assert not runtime.is_complete(asdict(result))


def test_a_feasible_incumbent_is_not_an_optimum_but_its_bound_still_brackets_every_sum(script):
    instance = top_tie()
    truth = oracle.ceilings(instance, floors=None, locked=(), excluded=())
    script.reset({1: {"status": cp_model.FEASIBLE, "bound": lambda b: b - 3}},
                 every={"status": cp_model.FEASIBLE, "bound": lambda b: b + 3})
    result = run(instance)
    check(result)
    (item,) = result.ranges
    assert {item.largest.certification, item.least.certification} == {"FEASIBLE_NOT_PROVEN"}
    assert item.largest.integer_bound == item.largest.integer_value + 3
    assert item.least.integer_bound == item.least.integer_value - 3
    low, high = bracket(result)["r"]
    assert all(low <= s <= high for s in truth.ranges[0].sums)
    assert result.claim == CEILING_CLAIM


# ----------------------------------------------------------------------- inputs and arithmetic


def test_refusals_name_no_value():
    candidates, requirements, formation = pair_of_places()
    hard = [replace(requirements[0], hard=True), requirements[1]]
    for case, refused_text in (
        (dict(requirements=[replace(r, status="research") for r in requirements]), "research"),
        (dict(requirements=hard), "r1"),
        (dict(floors={"stamina": 1.25}), "stamina"),
        (dict(floors={"r1": math.inf}), "inf"),
        (dict(floors={"r1": True}), "True"),
        (dict(floors={"r1": 7.25e12}), "7.25"),
    ):
        arguments = {"requirements": requirements, **case}
        with pytest.raises(ValueError) as refused:
            requirement_ranges(candidates, arguments.pop("requirements"), formation,
                               deadline=far(), **arguments)
        assert refused_text not in str(refused.value)
        assert scan_labels(str(refused.value)) == []
    # The hard flag is refused even when a floor is declared for that requirement.
    with pytest.raises(ValueError, match="marked hard"):
        requirement_ranges(candidates, [replace(requirements[0], hard=True), requirements[1]],
                           formation, floors={"r1": 0.5}, deadline=far())


def test_the_facts_compare_the_declared_minimum_not_the_floor():
    candidates = [player(1, "A", {"r": 1.0}), player(2, "A", {"r": 2.0})]
    formation = shape(("a", ("A",)))
    result = requirement_ranges(candidates, [requirement("r", 10.0)], formation,
                                floors={"r": 0.5}, deadline=far())
    (item,) = result.ranges
    assert item.minimum == 10.0 and result.floors == (("r", 0.5),)
    # Read against the floor 0.5 it would be reached; against m = 10 it is not.
    assert (item.minimum_reached_by_some_xi, item.minimum_missed_by_some_xi) == (False, True)
    assert result.provenance["input_contract"]["minima"] == {"r": 10.0}


def test_a_reordered_floor_mapping_and_shuffled_inputs_give_one_answer():
    instance = oracle.instances(7).ceiling
    inputs = domain(instance)
    floors = {r.requirement_id: r.minimum - 1.0 for r in inputs.requirements}
    reference = stable(requirement_ranges(
        inputs.candidates, inputs.requirements, inputs.formation, floors=floors,
        locked=instance.locked, excluded=instance.excluded,
        quantization=instance.quantization, deadline=far()))
    rng = random.Random(20261018)
    for _ in range(3):
        candidates, requirements = list(inputs.candidates), list(inputs.requirements)
        rng.shuffle(candidates)
        rng.shuffle(requirements)
        reordered = dict(sorted(floors.items(), key=lambda _: rng.random()))
        again = requirement_ranges(candidates, requirements, inputs.formation, floors=reordered,
                                   locked=tuple(reversed(instance.locked)),
                                   excluded=tuple(reversed(instance.excluded)),
                                   quantization=instance.quantization, deadline=far())
        assert stable(again) == reference


def test_an_integer_floor_and_its_float_are_one_declaration():
    # 10: the same declaration has one fingerprint; floors are kept as floats, as the frontier
    # keeps them.
    candidates, requirements, formation = pair_of_places()
    whole = requirement_ranges(candidates, requirements, formation, floors={"r1": 1},
                               deadline=far())
    real = requirement_ranges(candidates, requirements, formation, floors={"r1": 1.0},
                              deadline=far())
    assert stable(whole) == stable(real)
    assert [type(value) for _, value in whole.floors] == [float]
    assert whole.provenance["input_fingerprint"] == real.provenance["input_fingerprint"]


def test_determinism():
    for seed in (0, 1, 2, 3):
        instance = oracle.instances(seed).ceiling
        first, second = run(instance, floors=instance.floors), run(instance, floors=instance.floors)
        assert stable(first) == stable(second)


def test_a_magnitude_refusal_does_not_depend_on_the_clock_or_the_background():
    candidates = [player(1, "A", {"r": 1e12}), player(2, "A", {"r": 1.0})]
    requirements = [requirement("r")]
    for formation in (shape(("a", ("A",))), shape(("a", ("A",)), ("b", ("B",)))):
        for deadline in (far(), time.monotonic() - 1.0):
            with pytest.raises(ValueError, match="too large"):
                requirement_ranges(candidates, requirements, formation, deadline=deadline)
    # The empty slot b makes the background None; the coefficient is checked all the same.
    assert kernel.ShortfallKernel(candidates, requirements, shape(
        ("a", ("A",)), ("b", ("B",))))._background((), (), None, (), None).model is None
    assert abs(math.floor(_scaled(1e12, 1.0, 100_000))) > MAX_MAGNITUDE


def test_the_objective_is_exact_half_even_and_not_the_float_rule():
    candidates = [player(1, "A", {"r": 1.344465})]
    result = requirement_ranges(candidates, [requirement("r")], shape(("a", ("A",))),
                                deadline=far())
    (item,) = result.ranges
    assert item.largest.integer_value == round(_scaled(1.344465, 1.0, 100_000)) == 134_447
    assert _q(1.344465, 1.0, 100_000) == 134_446
    assert result.certificate.objective_policy == OBJECTIVE_POLICY


def test_half_even_infeasibility_implies_conservative_infeasibility():
    """Section 1.2: floor(v / n * q) <= _q(v, n, q) and ceil(m / n * q) >= _q(m, n, q)."""
    cases = [(0.005, 1.0, 100), (0.015, 1.0, 100), (0.15, 1.0, 100), (1.344465, 1.0, 100_000)]
    cases += [(10**12 - k * 0.25, 1.0, 1) for k in range(8)]
    cases += [(-(10**12) + k * 0.125, 1.0, 1) for k in range(8)]
    rng = random.Random(1_2_2026)
    for _ in range(20_000):
        q = rng.choice((1, 10, 100, 1000, 100_000))
        n = rng.choice((0.3, 0.5, 0.7, 1.0, 1.5, 2.5, rng.uniform(1e-3, 1e3)))
        limit = MAX_MAGNITUDE * n / q
        v = rng.choice((rng.uniform(-limit, limit), rng.uniform(-10, 10),
                        round(rng.uniform(-50, 50), rng.randint(0, 6))))
        cases.append((v, n, q))
    for v, n, q in cases:
        if abs(_scaled(v, n, q)) > MAX_MAGNITUDE:
            continue
        assert math.floor(_scaled(v, n, q)) <= _q(v, n, q), (v, n, q)
        assert math.ceil(_scaled(v, n, q)) >= _q(v, n, q), (v, n, q)


# --------------------------------------------------------------------- witnesses and the solver


def swap_first(lineup):
    """The witness with its first player replaced by the one of players 1 to 3 left out."""
    (sid, _), *rest = lineup
    spare = ({1, 2, 3} - {pid for _, pid in lineup}).pop()
    return ((sid, spare), *rest)


def test_a_tampered_witness_raises(monkeypatch):
    candidates, requirements, formation = pair_of_places()
    original = kernel.ShortfallKernel._witness
    # Out of formation order (inadmissible), then another XI (its integer differs).
    for tamper in (lambda lineup: tuple(reversed(lineup)), swap_first):
        with monkeypatch.context() as patch:
            patch.setattr(kernel.ShortfallKernel, "_witness",
                          staticmethod(lambda b, s, t=tamper: t(original(b, s))))
            with pytest.raises(RuntimeError):
                requirement_ranges(candidates, requirements, formation, deadline=far())


def fieldable(seeds=SEEDS) -> oracle.Instance:
    """The first seeded CEILING instance whose inner set holds an XI."""
    for seed in seeds:
        instance = oracle.instances(seed).ceiling
        truth = oracle.ceilings(instance, floors=instance.floors, locked=instance.locked,
                                excluded=instance.excluded)
        if truth.state == "FIELDABLE" and len(truth.feasible) > 1:
            return instance
    raise AssertionError("no seeded instance holds two XIs")


def test_an_infeasible_solve_after_a_verified_witness_is_a_fault_not_an_answer(script):
    script.plan[2] = {"status": cp_model.INFEASIBLE}
    candidates, requirements, formation = pair_of_places()
    with pytest.raises(RuntimeError):
        requirement_ranges(candidates, requirements, formation, deadline=far())


def test_deterministic_times_are_recorded_at_ten_significant_digits(script):
    # 1.5: the solver's deterministic_time, from the response, recorded by one rule in all four
    # tools: ten significant digits, because identical solves can differ in the last ulp.
    script.reset({0: {"deterministic_time": 1.2345678901234567}})
    candidates, requirements, formation = pair_of_places()
    result = requirement_ranges(candidates, requirements, formation, deadline=far())
    times = result.provenance["ceiling_solve_deterministic_times"]
    assert times[0]["deterministic_time"] == 1.23456789


def test_integers_come_from_the_expression_never_from_objective_value(script, monkeypatch):
    instance = fieldable()
    plain = run(instance, floors=instance.floors)
    script.reset(every={"ulp": True})
    shifted = run(instance, floors=instance.floors)
    assert stable(shifted) == stable(plain)
    assert shifted.certificate.feasible_set == "FIELDABLE"
    # The shift could change nothing if neither float were read: count the reads. Neither is
    # read on an OPTIMAL end; the bound only on a FEASIBLE one, rounded outward (2.3 step 7).
    assert script.reads == []
    script.reset(plan={0: {"status": cp_model.FEASIBLE}}, every={"ulp": True})
    feasible = run(instance, floors=instance.floors)
    assert feasible.ranges[0].largest.certification == "FEASIBLE_NOT_PROVEN"
    assert script.reads == [("best_objective_bound", cp_model.FEASIBLE)]
    original = kernel.ShortfallKernel._witness
    monkeypatch.setattr(kernel.ShortfallKernel, "_witness",
                        staticmethod(lambda b, s: tuple(reversed(original(b, s)))))
    with pytest.raises(RuntimeError):
        run(instance, floors=instance.floors)


def test_the_largest_end_equals_the_shipped_maximiser_with_every_minimum_a_floor():
    compared = 0
    for seed in SEEDS:
        instance = oracle.instances(seed).ceiling
        floors = {r.requirement_id: r.minimum for r in instance.requirements}
        truth = oracle.ceilings(instance, floors=floors, locked=instance.locked,
                                excluded=instance.excluded)
        if truth.state != "FIELDABLE":
            continue
        inputs = domain(instance)
        result = run(instance, floors=floors)
        for item in result.ranges:
            shipped = maximize_requirement(
                inputs.candidates, inputs.requirements, inputs.formation,
                target_requirement_id=item.requirement_id, locked=instance.locked,
                excluded=instance.excluded, quantization=instance.quantization)
            certificate = shipped.objective
            assert (item.largest.integer_value, item.largest.integer_bound,
                    item.largest.certification) == (
                certificate.integer_value, certificate.integer_upper_bound,
                certificate.certification), seed
            # Each witness lies in the band of the shared integer value; neither is compared
            # with the other.
            low = band(item, certificate.integer_value, -1, instance.quantization)
            high = band(item, certificate.integer_value, 1, instance.quantization)
            theirs = tuple((a.slot_id, a.player_id) for a in shipped.assignments)
            for lineup in (item.largest.lineup, theirs):
                assert low <= exact(instance, lineup, item.requirement_id) <= high, seed
            compared += 1
    assert compared >= 20


@pytest.mark.parametrize("module", ["frontier", "risk"])
def test_shared_sentences_are_one_text(module):
    name = f"galactico.optimization.xi.{module}"
    if importlib.util.find_spec(name) is None:  # built beside this module by another builder
        pytest.skip(f"{module}.py is not in the tree yet")
    other = importlib.import_module(name)
    assert other.UNFIELDABLE_PROVED == ceilings.UNFIELDABLE_PROVED
    if module == "frontier":
        assert other.FLOORS_CONSERVATIVE == ceilings.FLOORS_CONSERVATIVE


def test_every_served_sentence_passes_the_copy_guard():
    for name in ceilings.__all__:
        value = getattr(ceilings, name)
        if isinstance(value, str):
            assert scan_labels(value) == [], name


def test_the_private_kernel_members_this_module_uses_keep_their_signatures():
    """X9: ceilings.py reads these members of the unedited kernel.py."""
    members = {
        kernel.ShortfallKernel._deadline: ["deadline"],
        kernel.ShortfallKernel._background: ["self", "excluded", "locked", "pinned", "vacant",
                                             "values"],
        kernel.ShortfallKernel._tables: ["self", "background", "conservative"],
        kernel.ShortfallKernel._expression: ["background", "coefficients"],
        kernel.ShortfallKernel._witness: ["background", "solver"],
        kernel.ShortfallKernel._admissible: ["background", "lineup"],
        kernel._Run.__init__: ["self", "deadline", "seed"],
        kernel._Run.solve: ["self", "model"],
        kernel._at_least: ["model", "expression", "lower"],
    }
    for member, parameters in members.items():
        assert list(inspect.signature(member).parameters) == parameters, member.__qualname__
    assert inspect.signature(kernel.ShortfallKernel._tables).parameters[
        "conservative"].kind is inspect.Parameter.KEYWORD_ONLY
    assert {"model", "variables", "slots", "vectors", "reasons"} <= set(
        kernel._Background.__dataclass_fields__)
    assert isinstance(inspect.getattr_static(kernel.ShortfallKernel, "_deadline"), staticmethod)
    run_ = kernel._Run(far(), 1)
    assert run_.statuses == [] and run_.solve(cp_model.CpModel())[0] == "OPTIMAL"
    assert kernel._Run(time.monotonic() - 1.0, 1).solve(cp_model.CpModel()) == ("UNKNOWN", None)


# --------------------------------------------------------------------------- the corpus


def madrid_ranges_equal_a_brute_force(candidates, requirements, formation, locks=()) -> int:
    """Both ends, both facts and the bracket against the oracle's listing of every XI."""
    instance = oracle.Instance(tuple(formation.slots), tuple(candidates), tuple(requirements),
                               100_000)
    checked = 0
    for floors in (None, {r.requirement_id: r.minimum for r in requirements if r.active}):
        truth = oracle.ceilings(instance, floors=floors, locked=locks, excluded=())
        result = requirement_ranges(candidates, requirements, formation, floors=floors,
                                    locked=locks, deadline=far())
        check(result)
        assert result.certificate.feasible_set == truth.state
        assert result.certificate.completeness == "EXACT"
        outer = bracket(result)
        for item, want in zip(result.ranges, truth.ranges, strict=True):
            assert (item.largest.integer_value, item.least.integer_value) == (
                want.largest_integer, want.least_integer)
            low, high = outer[item.requirement_id]
            assert low <= want.sums[0] and want.sums[-1] <= high
            if item.minimum_reached_by_some_xi is not None:
                assert item.minimum_reached_by_some_xi == want.minimum_reached
            if item.minimum_missed_by_some_xi is not None:
                assert item.minimum_missed_by_some_xi == want.minimum_missed
            checked += 1
    return checked


def test_the_brute_force_check_runs_on_a_synthetic_eleven():
    """The body of the corpus test on a made-up squad, so it is exercised without data."""
    from galactico.optimization.xi.domain import FORMATIONS

    formation = FORMATIONS["4-3-3"]
    # Places as the role rules of decision_inputs give them: one or two per player.
    squad = [("GK", ("gk",)), ("GK", ("gk",)), ("DF", ("lb",)), ("DF", ("lcb", "rcb")),
             ("DF", ("lcb", "rcb")), ("DF", ("rcb",)), ("DF", ("rb", "lb")), ("MF", ("dm",)),
             ("MF", ("lcm", "rcm")), ("MF", ("lcm", "dm")), ("MF", ("rcm",)), ("FW", ("lw",)),
             ("FW", ("st",)), ("FW", ("rw",)), ("FW", ("st", "lw"))]
    candidates = [
        Candidate(100 + i, f"Player {i}", position,
                  {"progression": 0.1 * (i % 5), "side": 0.05 * i}, 900, slots)
        for i, (position, slots) in enumerate(squad)
    ]
    outfield = tuple(s.slot_id for s in formation.slots if s.slot_id != "gk")
    requirements = [
        TacticalRequirement("progression", "Progression", "progression", 0.6, 0.5, outfield),
        TacticalRequirement("side", "Side", "side", 1.0, 0.5, outfield),
        TacticalRequirement("missing", "Missing", "missing", 0, 1, outfield,
                            evidence_class="UNAVAILABLE", status="unavailable"),
    ]
    assert madrid_ranges_equal_a_brute_force(candidates, requirements, formation) == 4


@pytest.mark.slow
def test_madrid_ends_equal_a_brute_force_enumeration(corpus_root):
    from galactico.api.decision_lab import decision_inputs, scenarios
    from galactico.optimization.historical import load_snapshot
    from galactico.optimization.xi.domain import FORMATIONS

    candidates, requirements = decision_inputs(load_snapshot(2565907, worlds=0), "4-3-3")
    assert len([r for r in requirements if r.active]) == 3
    bbc = next(p for p in scenarios()["presets"] if p["id"] == "bbc")
    for locks in ((), tuple(bbc["locks"])):
        # Three ranges without floors at least; three more if the floors leave an XI.
        assert madrid_ranges_equal_a_brute_force(
            candidates, requirements, FORMATIONS["4-3-3"], locks) >= 3


@pytest.mark.slow
def test_the_largest_end_equals_planning_attained_on_the_planning_problem(corpus_root):
    """Section 13: no floors (``attained`` sets every minimum to 0, planning.py:1160)."""
    from galactico.api import planning

    planning.planning_snapshot.cache_clear()
    try:
        scenario = planning.resolve_scenario(planning.DEFAULT_PLANNING_SCENARIO)
        for inputs in (planning.PlanningInputs(),
                       planning.PlanningInputs(presets=["exclude-3322"])):
            problem = planning.declare(scenario, inputs)
            active = [r for r in problem.requirements if r.active]
            by_id = {r.requirement_id: r for r in active}
            # The equivalence with floors at 0 needs non-negative rates.
            assert all(p.values.get(r.metric) is None or p.values[r.metric] >= 0
                       for p in problem.candidates for r in active)
            free = tuple(replace(r, minimum=0.0) if r.active else r
                         for r in problem.requirements)
            result = requirement_ranges(problem.candidates, problem.requirements,
                                        problem.formation, locked=problem.locks,
                                        excluded=problem.excludes, deadline=far())
            check(result)
            assert [item.requirement_id for item in result.ranges] == [
                r.requirement_id for r in sorted(active, key=lambda r: r.requirement_id)]
            for item in result.ranges:
                shipped = maximize_requirement(
                    problem.candidates, free, problem.formation,
                    target_requirement_id=item.requirement_id, locked=problem.locks,
                    excluded=problem.excludes, time_limit=60.0)
                certificate = shipped.objective
                assert (item.largest.integer_value, item.largest.integer_bound,
                        item.largest.certification) == (
                    certificate.integer_value, certificate.integer_upper_bound,
                    certificate.certification)
                q = result.certificate.quantization
                low = band(item, certificate.integer_value, -1, q)
                high = band(item, certificate.integer_value, 1, q)
                values = {p.player_id: p.values for p in problem.candidates}
                counted = by_id[item.requirement_id]
                theirs = tuple((a.slot_id, a.player_id) for a in shipped.assignments)
                for lineup in (item.largest.lineup, theirs):
                    total = sum((Fraction(values[pid][counted.metric]) for sid, pid in lineup
                                 if not counted.slot_ids or sid in counted.slot_ids), Fraction())
                    assert low <= total <= high
    finally:
        planning.planning_snapshot.cache_clear()
