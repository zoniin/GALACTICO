"""FRONTIER (OR-XI-SPEC section 4) against the brute-force oracle and on planted instances.

Claim: on 120 seeded instances, with two and with three declared requirements, floors, locks and
exclusions, the listed integer vectors are exactly the oracle's nondominated set in the declared
lexicographic-descending order, each witness reaches its point, and every feasible vector lies
weakly below a listed one; cut and undecided lists are prefixes that never read as complete, and
every stop carries the completeness and ``stopped_by`` tokens of section 1.5. Non-claim: nothing
here reads the corpus except the one slow test, which skips cleanly without it; the oracle is
``tests/xi_exact_oracle.py``, written by another builder, and is never the code under test.
"""

from __future__ import annotations

import ast
import inspect
import math
import re
import time
from dataclasses import asdict, fields
from fractions import Fraction
from pathlib import Path

import pytest
import xi_exact_oracle as oracle
from ortools.sat.python import cp_model
from xi_exact_oracle import Instance, OracleCandidate, OracleRequirement, OracleSlot

from galactico.api.runtime import is_complete
from galactico.domain.labels import scan_labels
from galactico.optimization.squad import kernel as engine
from galactico.optimization.squad.kernel import ShortfallKernel
from galactico.optimization.xi import frontier
from galactico.optimization.xi.domain import Candidate, Formation, Slot, TacticalRequirement
from galactico.optimization.xi.frontier import (
    DIMENSION_COUNTS,
    FRONTIER_CLAIM,
    FRONTIER_NON_CLAIM,
    FRONTIER_VERSION,
    MAX_FRONTIER_POINTS,
    POINT_ORDER,
    nondominated_sums,
)
from galactico.optimization.xi.solver import _q
from galactico.optimization.xi.tradeoffs import OBJECTIVE_POLICY

SEEDS = range(120)
LATE = 1e15  # a monotonic reading past every deadline of this file
COMPLETENESS = ("COMPLETE", "LIMIT_REACHED", "DEADLINE", "MODEL_INVALID")
STATUS_FIELDS = frozenset({"stage_statuses", "statuses", "final_region_status"})
# O7, read as the union of its readings (section 4): "best", "optimal", "trade-off", "knee".
FORBIDDEN = re.compile(r"best|optimal|trade[\s-]?off|knee", re.IGNORECASE)
WALL = "frontier_solve_wall_times"
DETERMINISTIC = "frontier_solve_deterministic_times"


def far() -> float:
    return time.monotonic() + 600.0


# --------------------------------------------------------------------------- instances


def hand(slots, players, requirements, quantization) -> Instance:
    """slots: (slot_id, positions); players: {pid: (position, values)}; requirements:
    (requirement_id, metric, normalizer)."""
    return Instance(
        tuple(OracleSlot(sid, positions, f"Slot {sid}") for sid, positions in slots),
        tuple(
            OracleCandidate(pid, position, dict(values), name=f"Player {pid}")
            for pid, (position, values) in players.items()
        ),
        tuple(
            OracleRequirement(rid, metric, 0.0, normalizer, (), False, f"Requirement {rid}")
            for rid, metric, normalizer in requirements
        ),
        quantization,
    )


def two_requirements(slots, players, quantization=1, normalizer=1.0) -> Instance:
    return hand(slots, players, [("r1", "m1", normalizer), ("r2", "m2", normalizer)], quantization)


def rounding_case() -> Instance:
    # Section 4.1: q = 1, n = 1, two slots, a(0.5, 1.0) b(0.5, 1.0) c(0.6, 0.5) d(0.3, 1.0) as
    # players 1 to 4. Half-even: a, b, d count (0, 1), c counts (1, 0).
    values = {1: (0.5, 1.0), 2: (0.5, 1.0), 3: (0.6, 0.5), 4: (0.3, 1.0)}
    return two_requirements(
        [("s1", ("MF",)), ("s2", ("MF",))],
        {pid: ("MF", {"m1": a, "m2": b}) for pid, (a, b) in values.items()},
    )


def one_slot_case() -> Instance:
    # One slot, players i = 1..5 at (6 - i, i): every vector is nondominated (section 4.2).
    return two_requirements(
        [("s", ("MF",))], {i: ("MF", {"m1": 6 - i, "m2": i}) for i in range(1, 6)}
    )


def one_slot_three() -> Instance:
    # The same five points with a third requirement every player meets equally.
    return hand(
        [("s", ("MF",))],
        {i: ("MF", {"m1": 6 - i, "m2": i, "m3": 1}) for i in range(1, 6)},
        [("r1", "m1", 1.0), ("r2", "m2", 1.0), ("r3", "m3", 1.0)],
        1,
    )


def instance_a() -> Instance:
    # Instance A of the ceilings tests: q = 100000, slots a, b; p1 (a) and p2 (b) at r1 0.15,
    # r2 5.0; p3 (a) and p4 (b) at r1 1.0, r2 0.
    return two_requirements(
        [("a", ("DF",)), ("b", ("MF",))],
        {
            1: ("DF", {"m1": 0.15, "m2": 5.0}),
            2: ("MF", {"m1": 0.15, "m2": 5.0}),
            3: ("DF", {"m1": 1.0, "m2": 0.0}),
            4: ("MF", {"m1": 1.0, "m2": 0.0}),
        },
        quantization=100_000,
    )


def locked_pair_case() -> Instance:
    # Players 1 and 2 are each admissible at slot a only: locking both proves no XI exists,
    # and the kernel records no reason (each has an admissible key).
    return two_requirements(
        [("a", ("DF",)), ("b", ("MF",))],
        {1: ("DF", {"m1": 1, "m2": 0}), 2: ("DF", {"m1": 0, "m2": 1}),
         3: ("MF", {"m1": 1, "m2": 1})},
    )


def empty_slot_case() -> Instance:
    # Nobody can play slot b: unfieldable by construction, with the kernel's reason.
    return two_requirements(
        [("a", ("DF",)), ("b", ("FW",))],
        {1: ("DF", {"m1": 1, "m2": 0}), 2: ("DF", {"m1": 0, "m2": 1})},
    )


def domain(inst: Instance):
    return oracle.domain_inputs(
        inst,
        slot_type=Slot,
        formation_type=Formation,
        candidate_type=Candidate,
        requirement_type=TacticalRequirement,
    )


def solve(inst: Instance, dimensions, **declared):
    built = domain(inst)
    declared.setdefault("deadline", far())
    return nondominated_sums(
        built.candidates,
        built.requirements,
        built.formation,
        dimensions=dimensions,
        quantization=inst.quantization,
        **declared,
    )


def truth(inst: Instance, dimensions, *, floors=None, locked=(), excluded=()):
    return oracle.frontier(
        inst, dimensions=dimensions, floors=floors, locked=locked, excluded=excluded
    )


def seeded(seed: int) -> Instance:
    return oracle.instances(seed).frontier


def first_seeded(condition) -> tuple[Instance, tuple[str, ...]]:
    """The first seeded instance and declaration whose oracle frontier meets ``condition``."""
    for seed in SEEDS:
        inst = seeded(seed)
        for dims in inst.dimensions:
            if condition(inst, truth(inst, dims, **declared_of(inst))):
                return inst, dims
    raise AssertionError("no seeded instance meets the condition")


def declared_of(inst: Instance) -> dict:
    return {"floors": inst.floors, "locked": inst.locked, "excluded": inst.excluded}


def listed(result) -> tuple[tuple[int, ...], ...]:
    return tuple(p.integer_sums for p in result.points)


def players(lineup) -> frozenset[int]:
    return frozenset(pid for _, pid in lineup)


def stable(result) -> dict:
    """``asdict`` without the wall times, which differ on every run (section 9)."""
    payload = asdict(result)
    del payload["provenance"][WALL]
    return payload


def served_strings(result) -> list[str]:
    found: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key != "provenance":
                    walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            found.append(node)

    walk(asdict(result))
    return found


def forbidden_words(result) -> list[str]:
    """Paths of served keys and strings holding a word O7 forbids, outside provenance; the
    solver status token OPTIMAL in a status field is a certified status, not the phrase."""
    found: list[str] = []

    def walk(node, key, path):
        if isinstance(node, dict):
            for child, value in node.items():
                if child == "provenance":
                    continue
                if FORBIDDEN.search(child):
                    found.append(f"{path}{child}")
                walk(value, child, f"{path}{child}.")
        elif isinstance(node, (list, tuple)):
            for position, value in enumerate(node):
                walk(value, key, f"{path}{position}.")
        elif (
            isinstance(node, str)
            and not (key in STATUS_FIELDS and node == "OPTIMAL")
            and FORBIDDEN.search(node)
        ):
            found.append(path)

    walk(asdict(result), "", "")
    return found


def check_reply(result) -> None:
    """What every reply of every state holds (sections 1.5, 4.3, 7.7 and 9)."""
    cert = result.certificate
    assert scan_labels(asdict(result)) == []
    assert forbidden_words(result) == []
    assert result.claim == FRONTIER_CLAIM and result.non_claim == FRONTIER_NON_CLAIM
    assert result.point_order == POINT_ORDER
    assert cert.completeness in COMPLETENESS
    assert is_complete(asdict(result)) == (cert.completeness == "COMPLETE")
    expected = {
        "COMPLETE": {None},
        "LIMIT_REACHED": {"POINT_LIMIT", "DETERMINISTIC_LIMIT"},
        "DEADLINE": {"WALL_CLOCK"},
        "MODEL_INVALID": {None},
    }[cert.completeness]
    assert cert.stopped_by in expected
    assert cert.completeness in {
        "FRONTIER": ("COMPLETE",),
        "UNFIELDABLE": ("COMPLETE",),
        "NOT_SATISFIABLE": ("COMPLETE",),
        "FLOORS_UNMET": ("LIMIT_REACHED", "DEADLINE"),
        "INCOMPLETE": ("LIMIT_REACHED", "DEADLINE"),
        "MODEL_INVALID": ("MODEL_INVALID",),
    }[result.status]
    made = [s for s in cert.statuses if s != "NOT_RUN"]
    assert cert.solves == len(made)
    assert [row["status"] for row in result.provenance[DETERMINISTIC]] == made
    assert all(row["deterministic_time"] >= 0 for row in result.provenance[DETERMINISTIC])
    walls = result.provenance[WALL]
    assert len(walls) == len(made)
    assert all(isinstance(w, float) and math.isfinite(w) and w >= 0 for w in walls)
    assert cert.points == len(result.points)
    assert cert.pairwise_nondominated and cert.witnesses_verified
    vectors = listed(result)
    assert not any(
        i != j and all(a <= b for a, b in zip(u, v, strict=True))
        for i, u in enumerate(vectors)
        for j, v in enumerate(vectors)
    )
    d = len(result.dimensions)
    assert d in DIMENSION_COUNTS
    assert all(p.stage_statuses == ("OPTIMAL",) * d for p in result.points)
    assert len(cert.raw_rounding_error_bounds) == d
    assert cert.objective_policy == OBJECTIVE_POLICY and cert.hard_policy == engine.HARD_POLICY
    assert cert.per_solve_deterministic_limit == engine.PER_SOLVE_DETERMINISTIC_LIMIT
    if result.status in ("UNFIELDABLE", "NOT_SATISFIABLE", "FLOORS_UNMET"):
        assert result.points == ()


def never_complete(result) -> None:
    """A cut or undecided reply serves no sentence that only a complete list would."""
    assert result.certificate.completeness != "COMPLETE"
    for text in served_strings(result):
        assert not text.startswith("Every combination"), text
        assert "Complete" not in text, text


# --------------------------------------------------------------------------- solver plants


class Planted:
    def __init__(self) -> None:
        self.objectives: list[bool] = []  # per call made: whether the model had an objective
        self.reads = 0  # reads of objective_value or best_objective_bound


def plant(monkeypatch, *, status=None, spent=None, late_after=None, shifted=False) -> Planted:
    """Wrap every CP-SAT call (``kernel._solver``). ``status`` and ``spent`` map a call number
    (1-based, calls made) to a forced status and deterministic time; after call ``late_after``
    the clock reads past every deadline; ``shifted`` reports the objective and its bound
    ``2**-20`` low on an OPTIMAL solve, as CP-SAT's floats can be."""
    original = engine._solver
    record = Planted()
    status, spent = dict(status or {}), dict(spent or {})

    class Proxy:
        def __init__(self, actual, number):
            self.actual, self.number, self.status = actual, number, None

        def solve(self, model):
            record.objectives.append(model.has_objective())
            self.status = self.actual.solve(model)
            if self.number == late_after:
                monkeypatch.setattr(time, "monotonic", lambda: LATE)
            return status.get(self.number, self.status)

        @property
        def deterministic_time(self):
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

        def __getattr__(self, name):
            return getattr(self.actual, name)

    def factory(deadline, seed):
        return Proxy(original(deadline, seed), len(record.objectives) + 1)

    monkeypatch.setattr(engine, "_solver", factory)
    return record


# --------------------------------------------------------------------------- the oracle


def test_points_equal_the_oracle_on_seeded_instances() -> None:
    seen: set[str] = set()
    for seed in SEEDS:
        inst = seeded(seed)
        declared = declared_of(inst)
        by_id = {c.player_id: c for c in inst.candidates}
        requirements = {r.requirement_id: r for r in inst.requirements}
        for dims in inst.dimensions:
            d = len(dims)
            known = truth(inst, dims, **declared)
            result = solve(inst, dims, **declared)
            check_reply(result)
            got = listed(result)
            state = {"FIELDABLE": "FRONTIER"}.get(known.state, known.state)
            assert result.status == state, (seed, dims)
            assert result.dimensions == tuple(dims)
            assert result.floors == tuple(sorted((k, float(v)) for k, v in inst.floors.items()))
            if len(known.points) > MAX_FRONTIER_POINTS:  # never on these seeds; kept general
                assert got == known.points[:MAX_FRONTIER_POINTS]
                assert result.certificate.stopped_by == "POINT_LIMIT"
                continue
            # The set, and its order: lexicographic-descending in the declared order.
            assert got == known.points, (seed, dims)
            assert result.certificate.completeness == "COMPLETE"
            for vector in known.vectors:
                assert any(all(a <= b for a, b in zip(vector, p, strict=True)) for p in got)
            for p in result.points:
                # The witness is an XI of the inner set reaching its point, and its sums are
                # the exact sums of that XI.
                assert known.vector_of[p.lineup] == p.integer_sums
                assert p.raw_sums == tuple(float(s) for s in known.raw_of[p.lineup])
                assert p.quantized_sums == tuple(
                    float(Fraction(v) * Fraction(requirements[r].normalizer) / inst.quantization)
                    for v, r in zip(p.integer_sums, dims, strict=True)
                )
                if any(
                    oracle.objective(
                        by_id[pid].values[requirements[r].metric],
                        requirements[r].normalizer,
                        inst.quantization,
                    ) < 0
                    for sid, pid in p.lineup
                    for r in dims
                    if oracle._applies(requirements[r], sid)
                ):
                    seen.add("negative coefficient in a witness")
            cert = result.certificate
            if result.status == "FRONTIER":
                assert cert.solves == d * len(got) + 1
                assert cert.statuses[-1] == "INFEASIBLE" == cert.final_region_status
            elif cert.final_region_status == "INFEASIBLE_BY_CONSTRUCTION":
                assert cert.solves == 0 and cert.statuses == ()
                assert result.status == "UNFIELDABLE"
            else:
                assert cert.solves == (2 if inst.floors else 1)
                assert cert.final_region_status == "INFEASIBLE"
            seen.add(result.status)
            if d == 3 and len(got) >= 2:
                seen.add("three dimensions, two points")
            if len(got) >= 3:
                seen.add("three points")
            if any(len({known.raw_of[x] for x in known.witnesses(p)}) > 1 for p in got):
                seen.add("one point, different raw sums")
            reached = frozenset(x for x, v in known.vector_of.items() if v in set(got))
            if result.status == "FRONTIER" and reached != known.raw_nondominated:
                seen.add("raw and integer frontiers differ")
            if inst.floors and result.status == "FRONTIER":
                free = truth(inst, dims, locked=inst.locked, excluded=inst.excluded)
                if free.points != known.points:
                    seen.add("a floor binds")
            if d == 2 and result.status == "FRONTIER":
                # Reversing a complete two-dimension declaration reverses the list and swaps
                # every pair.
                back = solve(inst, tuple(reversed(dims)), **declared)
                assert listed(back) == tuple(p[::-1] for p in reversed(got))
            if len(got) >= 2:
                # Cut one short: the lexicographic-largest prefix, a further point proved by
                # a feasibility solve. Exactly at the limit: complete, the limit check
                # INFEASIBLE.
                cut = solve(inst, dims, max_points=len(got) - 1, **declared)
                check_reply(cut)
                never_complete(cut)
                assert listed(cut) == got[:-1]
                assert (cut.status, cut.certificate.stopped_by) == ("INCOMPLETE", "POINT_LIMIT")
                assert cut.certificate.solves == d * (len(got) - 1) + 1
                assert cut.certificate.final_region_status in ("OPTIMAL", "FEASIBLE")
                exact = solve(inst, dims, max_points=len(got), **declared)
                assert listed(exact) == got and exact.status == "FRONTIER"
                assert exact.certificate.final_region_status == "INFEASIBLE"
    # Section 6: the seeded instances are not vacuous.
    assert seen >= {
        "three dimensions, two points",
        "three points",
        "one point, different raw sums",
        "raw and integer frontiers differ",
        "negative coefficient in a witness",
        "a floor binds",
        "FRONTIER",
        "UNFIELDABLE",
        "NOT_SATISFIABLE",
    }


def test_the_rounding_counterexample_of_section_4_1() -> None:
    inst = rounding_case()
    known = truth(inst, ("r1", "r2"))
    result = solve(inst, ("r1", "r2"))
    check_reply(result)
    assert listed(result) == ((1, 1), (0, 2)) == known.points
    assert (result.status, result.certificate.completeness) == ("FRONTIER", "COMPLETE")
    for p in result.points:
        reaching = known.witnesses(p.integer_sums)
        # Each point is listed once although XIs with different raw sums reach it.
        assert len({known.raw_of[x] for x in reaching}) == 2
        larger = max(reaching, key=lambda x: known.raw_of[x])
        assert all(
            all(a >= b for a, b in zip(known.raw_of[larger], known.raw_of[x], strict=True))
            for x in reaching
        )
        assert known.vector_of[larger] == p.integer_sums
        # Whichever XI the tool returns, its vector is the point.
        assert known.vector_of[p.lineup] == p.integer_sums
    assert {players(x) for x in known.witnesses((1, 1))} == {
        frozenset({1, 3}), frozenset({2, 3}), frozenset({3, 4})}
    assert {players(x) for x in known.witnesses((0, 2))} == {
        frozenset({1, 2}), frozenset({1, 4}), frozenset({2, 4})}

    without_c = solve(inst, ("r1", "r2"), excluded=(3,))
    check_reply(without_c)
    assert listed(without_c) == ((0, 2),) and without_c.status == "FRONTIER"
    known = truth(inst, ("r1", "r2"), excluded=(3,))
    reaching = known.witnesses((0, 2))
    assert len({players(x) for x in reaching}) == 3
    assert len({known.raw_of[x] for x in reaching}) > 1
    assert players(without_c.points[0].lineup) in {players(x) for x in reaching}


def test_objective_coefficients_are_exact_half_even_not_the_shortfall_rule() -> None:
    inst = two_requirements(
        [("s", ("MF",))], {1: ("MF", {"m1": 1.344465, "m2": 0.0})}, quantization=100_000
    )
    result = solve(inst, ("r1", "r2"))
    assert listed(result) == ((134447, 0),)
    assert _q(1.344465, 1.0, 100_000) == 134446  # the float rule would print another point
    assert round(Fraction(1.344465) * 100_000) == 134447


def test_declared_floors_are_conservative_and_scope_the_list() -> None:
    inst = instance_a()
    result = solve(inst, ("r1", "r2"), floors={"r1": 0.3})
    check_reply(result)
    known = truth(inst, ("r1", "r2"), floors={"r1": 0.3})
    assert listed(result) == known.points == ((200000, 0), (115000, 500000))
    # The floors a router scopes its completeness sentence by (FLOORS_SCOPE, 7.5).
    assert result.floors == (("r1", 0.3),)
    # (p1, p2) meets the raw floor exactly and lies above every listed point on r2; the
    # conservative comparison leaves it out (14999 + 14999 < 30000).
    pair = (("a", 1), ("b", 2))
    vectors = oracle.point_vectors(inst)
    r1 = next(r for r in inst.requirements if r.requirement_id == "r1")
    assert oracle.exact_sum(pair, r1, vectors) >= Fraction(0.3)
    free = truth(inst, ("r1", "r2"))
    assert free.vector_of[pair] == (30000, 1000000)
    assert (30000, 1000000) not in listed(result)
    assert (30000, 1000000) in listed(solve(inst, ("r1", "r2")))
    for p in result.points:
        raw = oracle.exact_sum(p.lineup, r1, vectors)
        assert raw >= Fraction(0.3)


# --------------------------------------------------------------------------- the point limit


def test_the_limit_check_is_one_solve_with_no_objective(monkeypatch) -> None:
    inst = rounding_case()
    record = plant(monkeypatch)
    cut = solve(inst, ("r1", "r2"), max_points=1)
    check_reply(cut)
    never_complete(cut)
    assert listed(cut) == (truth(inst, ("r1", "r2")).points[0],) == ((1, 1),)
    cert = cut.certificate
    assert (cut.status, cert.completeness, cert.stopped_by) == (
        "INCOMPLETE", "LIMIT_REACHED", "POINT_LIMIT")
    assert cert.final_region_status == "OPTIMAL" == cert.statuses[-1]
    assert cert.solves == 2 * 1 + 1 and cert.max_points == 1
    assert record.objectives == [True, True, False]
    assert set(truth(inst, ("r1", "r2")).points) > set(listed(cut))

    record.objectives.clear()
    exact = solve(inst, ("r1", "r2"), max_points=2)
    check_reply(exact)
    assert (exact.status, exact.certificate.completeness) == ("FRONTIER", "COMPLETE")
    assert exact.certificate.final_region_status == "INFEASIBLE" == exact.certificate.statuses[-1]
    assert exact.certificate.solves == 2 * 2 + 1
    assert record.objectives == [True, True, True, True, False]


@pytest.mark.parametrize(
    "forced,completeness,stopped_by,final",
    [
        (cp_model.UNKNOWN, "DEADLINE", "WALL_CLOCK", "UNKNOWN"),
        (cp_model.FEASIBLE, "LIMIT_REACHED", "POINT_LIMIT", "FEASIBLE"),
        (cp_model.MODEL_INVALID, "MODEL_INVALID", None, "MODEL_INVALID"),
    ],
)
def test_an_undecided_limit_check_is_never_a_point_limit(
    monkeypatch, forced, completeness, stopped_by, final
) -> None:
    inst = rounding_case()
    plant(monkeypatch, status={3: forced})
    result = solve(inst, ("r1", "r2"), max_points=1)
    check_reply(result)
    never_complete(result)
    cert = result.certificate
    assert listed(result) == ((1, 1),)
    assert (cert.completeness, cert.stopped_by, cert.final_region_status) == (
        completeness, stopped_by, final)
    assert cert.statuses[-1] == final and cert.solves == 3
    if forced == cp_model.UNKNOWN:
        assert result.status == "INCOMPLETE" and cert.stopped_by != "POINT_LIMIT"


def test_a_cut_list_is_a_prefix_in_the_declared_order() -> None:
    inst = one_slot_case()
    forward = solve(inst, ("r1", "r2"), max_points=2)
    backward = solve(inst, ("r2", "r1"), max_points=2)
    for result in (forward, backward):
        check_reply(result)
        never_complete(result)
        assert result.certificate.stopped_by == "POINT_LIMIT"
        assert result.point_order == POINT_ORDER
    # Each in its own coordinates: the reversed declaration lists the other end.
    assert listed(forward) == listed(backward) == ((5, 1), (4, 2))
    assert set(truth(inst, ("r1", "r2")).points) > set(listed(forward))
    assert set(truth(inst, ("r2", "r1")).points) > set(listed(backward))
    assert listed(backward) != tuple(p[::-1] for p in reversed(listed(forward)))
    assert players(forward.points[0].lineup) == {1}
    assert players(backward.points[0].lineup) == {5}
    complete = solve(inst, ("r1", "r2"))
    assert listed(complete) == truth(inst, ("r1", "r2")).points
    reverse = solve(inst, ("r2", "r1"))
    assert listed(reverse) == tuple(p[::-1] for p in reversed(listed(complete)))


@pytest.mark.parametrize("case,dims", [(one_slot_case, ("r1", "r2")),
                                       (one_slot_three, ("r1", "r2", "r3"))])
def test_a_stop_at_stage_two_of_the_third_iteration_keeps_the_two_earlier_points(
    monkeypatch, case, dims
) -> None:
    inst = case()
    d = len(dims)
    plant(monkeypatch, status={2 * d + 2: cp_model.UNKNOWN})
    result = solve(inst, dims)
    check_reply(result)
    never_complete(result)
    cert = result.certificate
    assert listed(result) == truth(inst, dims).points[:2]
    assert set(truth(inst, dims).points) > set(listed(result))
    assert (result.status, cert.completeness, cert.stopped_by, cert.final_region_status) == (
        "INCOMPLETE", "DEADLINE", "WALL_CLOCK", "UNKNOWN")
    assert cert.solves == 2 * d + 2 and cert.statuses[-1] == "UNKNOWN"


def test_cut_and_stopped_seeded_lists_are_oracle_prefixes(monkeypatch) -> None:
    checked = set()
    for seed in SEEDS:
        inst = seeded(seed)
        for dims in inst.dimensions:
            known = truth(inst, dims, **declared_of(inst))
            if len(known.points) < 3 or len(dims) in checked:
                continue
            d = len(dims)
            with monkeypatch.context() as patch:
                plant(patch, status={2 * d + 2: cp_model.UNKNOWN})
                stopped = solve(inst, dims, **declared_of(inst))
            check_reply(stopped)
            never_complete(stopped)
            assert listed(stopped) == known.points[:2]
            assert set(known.points) > set(listed(stopped))
            checked.add(d)
    assert checked == {2, 3}


# --------------------------------------------------------------------------- empty sets


def test_unfieldable_by_proof_and_by_construction() -> None:
    proved = solve(locked_pair_case(), ("r1", "r2"), locked=(1, 2))
    check_reply(proved)
    cert = proved.certificate
    assert (proved.status, cert.completeness, cert.stopped_by) == ("UNFIELDABLE", "COMPLETE", None)
    assert cert.final_region_status == "INFEASIBLE" and cert.statuses == ("INFEASIBLE",)
    assert proved.reasons == (frontier.UNFIELDABLE_PROVED,)
    assert truth(locked_pair_case(), ("r1", "r2"), locked=(1, 2)).state == "UNFIELDABLE"

    floored = solve(locked_pair_case(), ("r1", "r2"), locked=(1, 2), floors={"r2": 0.0})
    check_reply(floored)
    assert floored.status == "UNFIELDABLE"
    assert floored.certificate.statuses == ("INFEASIBLE", "INFEASIBLE")
    assert floored.certificate.solves == 2
    assert floored.reasons == (frontier.UNFIELDABLE_PROVED,)

    built = solve(empty_slot_case(), ("r1", "r2"))
    check_reply(built)
    cert = built.certificate
    assert (built.status, cert.completeness) == ("UNFIELDABLE", "COMPLETE")
    assert cert.final_region_status == "INFEASIBLE_BY_CONSTRUCTION"
    assert (cert.statuses, cert.solves) == ((), 0)
    assert built.reasons == ("No eligible measured candidate for Slot b.",)
    clash = solve(rounding_case(), ("r1", "r2"), locked=(1,), excluded=(1,))
    assert clash.status == "UNFIELDABLE"
    # The kernel's reasons by construction, as it records them.
    assert clash.reasons == (
        "A player cannot be both locked and excluded.",
        "Locked player Player 1 has no admissible assignment.",
    )


def test_not_satisfiable_is_proved_with_the_cause_solve() -> None:
    result = solve(rounding_case(), ("r1", "r2"), floors={"r1": 5})
    check_reply(result)
    cert = result.certificate
    assert (result.status, cert.completeness, cert.stopped_by) == (
        "NOT_SATISFIABLE", "COMPLETE", None)
    assert cert.statuses == ("INFEASIBLE", "OPTIMAL") and cert.solves == 2
    assert cert.final_region_status == "INFEASIBLE" and result.reasons == ()
    assert truth(rounding_case(), ("r1", "r2"), floors={"r1": 5}).state == "NOT_SATISFIABLE"


@pytest.mark.parametrize(
    "plan,status,completeness,stopped_by,cause",
    [
        ({"status": {2: cp_model.UNKNOWN}}, "FLOORS_UNMET", "DEADLINE", "WALL_CLOCK", "UNKNOWN"),
        (
            {"status": {2: cp_model.UNKNOWN}, "spent": {2: engine.PER_SOLVE_DETERMINISTIC_LIMIT}},
            "FLOORS_UNMET", "LIMIT_REACHED", "DETERMINISTIC_LIMIT", "UNKNOWN",
        ),
        ({"late_after": 1}, "FLOORS_UNMET", "DEADLINE", "WALL_CLOCK", "NOT_RUN"),
        (
            {"status": {2: cp_model.MODEL_INVALID}},
            "MODEL_INVALID", "MODEL_INVALID", None, "MODEL_INVALID",
        ),
    ],
)
def test_an_undecided_or_refused_cause_solve(
    monkeypatch, plan, status, completeness, stopped_by, cause
) -> None:
    plant(monkeypatch, **plan)
    result = solve(rounding_case(), ("r1", "r2"), floors={"r1": 5})
    check_reply(result)
    never_complete(result)
    cert = result.certificate
    assert (result.status, cert.completeness, cert.stopped_by) == (
        status, completeness, stopped_by)
    # The empty frontier is proved by the first solve; only its cause is not decided.
    assert cert.final_region_status == "INFEASIBLE"
    assert cert.statuses == ("INFEASIBLE", cause)
    assert cert.solves == (1 if cause == "NOT_RUN" else 2)
    assert result.points == () and not is_complete(asdict(result))


# --------------------------------------------------------------------------- stops


def test_a_deadline_passed_at_entry_answers_nothing(monkeypatch) -> None:
    record = plant(monkeypatch)
    late = time.monotonic() - 1.0
    for inst, declared in ((rounding_case(), {}), (empty_slot_case(), {}),
                           (rounding_case(), {"floors": {"r1": 5}})):
        result = solve(inst, ("r1", "r2"), deadline=late, **declared)
        check_reply(result)
        never_complete(result)
        cert = result.certificate
        assert (result.status, cert.completeness, cert.stopped_by) == (
            "INCOMPLETE", "DEADLINE", "WALL_CLOCK")
        assert (cert.final_region_status, cert.statuses, cert.solves) == (
            "NOT_RUN", ("NOT_RUN",), 0)
        assert result.points == () and result.provenance[WALL] == []
    assert record.objectives == []


@pytest.mark.parametrize(
    "plan,completeness,stopped_by,final",
    [
        # A deterministic stop, the deadline not passed: load-independent.
        ({"status": {3: cp_model.UNKNOWN}, "spent": {3: engine.PER_SOLVE_DETERMINISTIC_LIMIT}},
         "LIMIT_REACHED", "DETERMINISTIC_LIMIT", "UNKNOWN"),
        # UNKNOWN that reached neither limit.
        ({"status": {3: cp_model.UNKNOWN}}, "DEADLINE", "WALL_CLOCK", "UNKNOWN"),
        # The deterministic limit reached, but the wall clock had passed when it returned.
        ({"status": {3: cp_model.UNKNOWN}, "spent": {3: engine.PER_SOLVE_DETERMINISTIC_LIMIT},
          "late_after": 3}, "DEADLINE", "WALL_CLOCK", "UNKNOWN"),
        # A FEASIBLE incumbent where a maximum was asked is not a maximum.
        ({"status": {4: cp_model.FEASIBLE}}, "DEADLINE", "WALL_CLOCK", "FEASIBLE"),
        ({"status": {4: cp_model.FEASIBLE}, "spent": {4: engine.PER_SOLVE_DETERMINISTIC_LIMIT}},
         "LIMIT_REACHED", "DETERMINISTIC_LIMIT", "FEASIBLE"),
        # The deadline passes between calls: the next call is NOT_RUN, never UNKNOWN.
        ({"late_after": 2}, "DEADLINE", "WALL_CLOCK", "NOT_RUN"),
        # A refusal keeps the point recorded before it.
        ({"status": {3: cp_model.MODEL_INVALID}}, "MODEL_INVALID", None, "MODEL_INVALID"),
    ],
)
def test_a_planted_stop_keeps_the_earlier_points(
    monkeypatch, plan, completeness, stopped_by, final
) -> None:
    plant(monkeypatch, **plan)
    result = solve(rounding_case(), ("r1", "r2"))
    check_reply(result)
    never_complete(result)
    cert = result.certificate
    assert listed(result) == ((1, 1),)
    assert (cert.completeness, cert.stopped_by, cert.final_region_status) == (
        completeness, stopped_by, final)
    assert result.status == ("MODEL_INVALID" if final == "MODEL_INVALID" else "INCOMPLETE")
    assert cert.statuses[-1] == final
    assert cert.solves == len(cert.statuses) - (final == "NOT_RUN")
    assert set(truth(rounding_case(), ("r1", "r2")).points) > set(listed(result))


def test_a_stop_before_any_point(monkeypatch) -> None:
    limit_of_one = engine.PER_SOLVE_DETERMINISTIC_LIMIT
    plant(monkeypatch, status={1: cp_model.UNKNOWN}, spent={1: limit_of_one})
    limit = solve(rounding_case(), ("r1", "r2"))
    check_reply(limit)
    never_complete(limit)
    assert (limit.status, limit.points) == ("INCOMPLETE", ())
    assert (limit.certificate.completeness, limit.certificate.stopped_by) == (
        "LIMIT_REACHED", "DETERMINISTIC_LIMIT")
    monkeypatch.undo()
    plant(monkeypatch, status={1: cp_model.MODEL_INVALID})
    refused = solve(rounding_case(), ("r1", "r2"))
    check_reply(refused)
    never_complete(refused)
    assert (refused.status, refused.points, refused.certificate.stopped_by) == (
        "MODEL_INVALID", (), None)


# --------------------------------------------------------------------------- defects raise


def test_a_tampered_witness_raises(monkeypatch) -> None:
    original = ShortfallKernel._witness

    def duplicated(background, solver):
        lineup = original(background, solver)
        return (*lineup[:-1], (lineup[-1][0], lineup[0][1]))

    with monkeypatch.context() as patch:
        patch.setattr(ShortfallKernel, "_witness", staticmethod(duplicated))
        with pytest.raises(RuntimeError):
            solve(rounding_case(), ("r1", "r2"))
    with monkeypatch.context() as patch:
        # An XI of the model, but not one that reaches the point (1, 1): {a, b} is (0, 2).
        wrong = staticmethod(lambda background, solver: (("s1", 1), ("s2", 2)))
        patch.setattr(ShortfallKernel, "_witness", wrong)
        with pytest.raises(RuntimeError, match="integer"):
            solve(rounding_case(), ("r1", "r2"))
    with monkeypatch.context() as patch:
        # Floors are re-checked: (p1, p2) is an XI of the background that misses the
        # conservative floor r1 >= 0.3 (14999 + 14999 < 30000).
        missing = staticmethod(lambda background, solver: (("a", 1), ("b", 2)))
        patch.setattr(ShortfallKernel, "_witness", missing)
        with pytest.raises(RuntimeError, match="floor"):
            solve(instance_a(), ("r1", "r2"), floors={"r1": 0.3})


def test_a_list_that_is_not_pairwise_nondominated_raises(monkeypatch) -> None:
    # Without the cut, the search finds the same point again.
    monkeypatch.setattr(frontier, "_leave_down_set", lambda *args: None)
    with pytest.raises(RuntimeError):
        solve(rounding_case(), ("r1", "r2"), max_points=3)


def test_an_infeasible_later_stage_raises(monkeypatch) -> None:
    plant(monkeypatch, status={2: cp_model.INFEASIBLE})
    with pytest.raises(RuntimeError):
        solve(rounding_case(), ("r1", "r2"))


def test_integers_come_from_the_solver_values_not_its_objective_floats(monkeypatch) -> None:
    inst, dims = first_seeded(lambda inst, known: len(known.dimensions) == 3
                              and len(known.points) >= 3)
    plain = solve(inst, dims, **declared_of(inst))
    with monkeypatch.context() as patch:
        record = plant(patch, shifted=True)
        wrapped = solve(inst, dims, **declared_of(inst))
        assert record.reads == 0  # neither float is read, so neither can be off by an ulp
        assert stable(wrapped) == stable(plain)
        original = ShortfallKernel._witness

        def duplicated(background, solver):
            lineup = original(background, solver)
            return (*lineup[:-1], (lineup[-1][0], lineup[0][1]))

        patch.setattr(ShortfallKernel, "_witness", staticmethod(duplicated))
        with pytest.raises(RuntimeError):
            solve(inst, dims, **declared_of(inst))


# --------------------------------------------------------------------------- declarations


def test_invalid_declarations_are_value_errors_naming_no_value() -> None:
    inst = rounding_case()
    built = domain(inst)
    candidates, requirements, formation = built
    call = {"quantization": 1, "deadline": far()}
    with pytest.raises(TypeError):
        nondominated_sums(candidates, requirements, formation, **call)  # no default dimension
    inactive = TacticalRequirement("zzz", "Inactive", "m1", 0.0, 1.0, status="research")
    hard = TacticalRequirement("r3", "Hard", "m1", 0.0, 1.0, hard=True)
    bad = [
        ({"dimensions": ("r1",)}, requirements),
        ({"dimensions": ("r1", "r2", "r1", "r2")}, requirements),
        ({"dimensions": ("r1", "r1")}, requirements),
        ({"dimensions": ("r1", "zzz")}, requirements),
        ({"dimensions": ("r1", "zzz")}, (*requirements, inactive)),
        ({"dimensions": ("r1", 7)}, requirements),
        ({"dimensions": ("r1", "r2"), "max_points": 0}, requirements),
        ({"dimensions": ("r1", "r2"), "max_points": 65}, requirements),
        ({"dimensions": ("r1", "r2"), "max_points": True}, requirements),
        ({"dimensions": ("r1", "r2"), "max_points": 2.0}, requirements),
        ({"dimensions": ("r1", "r2"), "floors": {"zzz": 1.0}}, requirements),
        ({"dimensions": ("r1", "r2"), "floors": {"zzz": 1.0}}, (*requirements, inactive)),
        ({"dimensions": ("r1", "r2"), "floors": {"r1": math.nan}}, requirements),
        ({"dimensions": ("r1", "r2"), "floors": {"r1": math.inf}}, requirements),
        ({"dimensions": ("r1", "r2"), "floors": {"r1": True}}, requirements),
        ({"dimensions": ("r1", "r2"), "floors": {"r1": 1e13}}, requirements),
        ({"dimensions": ("r1", "r2"), "floors": {"r1": "1"}}, requirements),
        ({"dimensions": ("r1", "r2")}, (*requirements, hard)),
    ]
    for declared, given in bad:
        with pytest.raises(ValueError) as caught:
            nondominated_sums(candidates, given, formation, **call, **declared)
        assert "zzz" not in str(caught.value) and "nan" not in str(caught.value)
    # A hard flag on a requirement that is not in force sets nothing aside.
    hard_inactive = TacticalRequirement("r3", "Hard", "m1", 0.0, 1.0, hard=True, status="research")
    accepted = nondominated_sums(
        candidates, (*requirements, hard_inactive), formation, dimensions=("r1", "r2"), **call)
    assert accepted.status == "FRONTIER"


def test_an_objective_coefficient_too_large_is_refused_before_any_check() -> None:
    # floor(x) is the magnitude limit itself while round(x) is one above it: only the
    # objective rule (2.3 step 4) refuses it, and it does so whatever the deadline or the
    # background.
    value = (10**12 + 0.75) * 0.5
    big = {1: ("MF", {"m1": value, "m2": 0.0}), 2: ("MF", {"m1": 0.0, "m2": 1.0})}
    fieldable = two_requirements([("s", ("MF",))], big, normalizer=0.5)
    unfieldable = two_requirements([("s", ("MF",)), ("t", ("GK",))], big, normalizer=0.5)
    for inst in (fieldable, unfieldable):
        for deadline in (far(), time.monotonic() - 1.0):
            with pytest.raises(ValueError, match="objective coefficient"):
                solve(inst, ("r1", "r2"), deadline=deadline)
    # The conservative table of the same value is within the limit: the kernel accepts it.
    kernel = ShortfallKernel(*domain(fieldable)[:2], domain(fieldable).formation, quantization=1)
    background = kernel._background((), (), None, (), None)
    assert kernel._tables(background, conservative=True)["r1"][0][1, "s"] == 10**12


# --------------------------------------------------------------------------- identity


def test_determinism_shuffled_inputs_and_the_input_fingerprint() -> None:
    inst, dims = first_seeded(lambda inst, known: len(inst.floors) >= 2 and inst.locked
                              and len(known.points) >= 2)
    declared = declared_of(inst)
    first = solve(inst, dims, **declared)
    assert stable(solve(inst, dims, **declared)) == stable(first)
    built = domain(inst)
    shuffled = nondominated_sums(
        tuple(reversed(built.candidates)),
        tuple(reversed(built.requirements)),
        built.formation,
        dimensions=dims,
        floors=dict(reversed(list(inst.floors.items()))),
        locked=(*reversed(inst.locked), *inst.locked),
        excluded=(*reversed(inst.excluded), *inst.excluded),
        quantization=inst.quantization,
        deadline=far(),
    )
    assert stable(shuffled) == stable(first)
    assert first.provenance["input_fingerprint"] == shuffled.provenance["input_fingerprint"]
    fingerprints = {first.provenance["input_fingerprint"]}
    fingerprints.add(solve(inst, dims[::-1], **declared).provenance["input_fingerprint"])
    for change in ({"max_points": 63}, {"floors": {}}, {"locked": ()}):
        again = solve(inst, dims, **{**declared, **change})
        fingerprints.add(again.provenance["input_fingerprint"])
    assert len(fingerprints) == 5


def test_provenance_keeps_lineage_and_records_every_call() -> None:
    source = {
        "dataset_hash": "data",
        "bootstrap_version": "shared-v1",
        "bootstrap_worlds": 12,
        "frontier_version": "old",
        "frontier_solve_wall_times": [1.0],
        "input_contract": {"old": True},
        "solver_status": "OPTIMAL",
    }
    result = solve(rounding_case(), ("r1", "r2"), floors={"r2": 0.0}, provenance=source)
    record = result.provenance
    assert record["dataset_hash"] == "data" and record["bootstrap_version"] == "shared-v1"
    assert "bootstrap_worlds" not in record and "solver_status" not in record
    assert record["frontier_version"] == FRONTIER_VERSION
    contract = record["input_contract"]
    assert contract["dimensions"] == ["r1", "r2"] and contract["floors"] == [["r2", 0.0]]
    assert contract["max_points"] == MAX_FRONTIER_POINTS
    assert contract["objective_policy"] == OBJECTIVE_POLICY
    assert contract["hard_policy"] == engine.HARD_POLICY
    assert contract["kernel"]["kernel_version"] == engine.KERNEL_VERSION
    assert (contract["locked"], contract["excluded"]) == ([], [])
    assert record["input_fingerprint"] == engine.fingerprint(
        {"version": FRONTIER_VERSION, "contract": contract})
    # Never the deadline, never a solve time (section 10).
    assert not {"deadline", DETERMINISTIC, WALL} & (set(contract) | set(contract["kernel"]))
    assert set(record["source_fingerprints"]) == {
        "galactico/optimization/xi/frontier.py",
        "galactico/optimization/squad/kernel.py",
        "galactico/optimization/xi/solver.py",
        "galactico/optimization/xi/tradeoffs.py",
        "galactico/optimization/xi/domain.py",
    }
    assert contract["source_fingerprints"] == record["source_fingerprints"]
    assert len(record[WALL]) == result.certificate.solves == 5


# --------------------------------------------------------------------------- the module


def test_frontier_reexports_the_ceilings_sentences() -> None:
    from galactico.optimization.xi import ceilings

    # Defined once, in ceilings.py (7.7): the same object, so the same text.
    assert frontier.UNFIELDABLE_PROVED is ceilings.UNFIELDABLE_PROVED
    assert frontier.FLOORS_CONSERVATIVE is ceilings.FLOORS_CONSERVATIVE
    for text in (FRONTIER_CLAIM, FRONTIER_NON_CLAIM, POINT_ORDER, frontier.UNFIELDABLE_PROVED,
                 frontier.FLOORS_CONSERVATIVE):
        assert scan_labels(text) == [] and not FORBIDDEN.search(text)
    assert not FRONTIER_CLAIM.startswith("Every combination") and "Complete" not in FRONTIER_CLAIM
    assert (MAX_FRONTIER_POINTS, DIMENSION_COUNTS) == (64, (2, 3))


def test_deterministic_times_are_recorded_at_ten_significant_digits(monkeypatch) -> None:
    # 1.5: the solver's deterministic_time, from the response, recorded by one rule in all four
    # tools: ten significant digits, because identical solves can differ in the last ulp.
    plant(monkeypatch, spent={1: 1.2345678901234567})
    result = solve(one_slot_case(), ("r1", "r2"))
    times = result.provenance["frontier_solve_deterministic_times"]
    assert times[0]["deterministic_time"] == 1.23456789


def test_the_module_calls_no_shipped_solver_and_reads_no_objective_float() -> None:
    tree = ast.parse(Path(frontier.__file__).read_text(encoding="utf-8"))
    names = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
             for alias in node.names}
    names |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
              for alias in node.names}
    assert not names & {"solve_xi", "maximize_requirement", "bootstrap_selection",
                        "removal_sensitivity", "candidate_injection"}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not attributes & {"objective_value", "best_objective_bound", "ObjectiveValue",
                             "BestObjectiveBound"}
    # Section 0: no data file, no environment variable, no clock but time.monotonic.
    clocks = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
              and isinstance(node.value, ast.Name) and node.value.id == "time"}
    assert clocks == {"monotonic"}
    called = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call)
              and isinstance(node.func, ast.Name)}
    assert "open" not in called and "environ" not in attributes and "os" not in names


def test_the_kernel_members_this_module_uses_are_pinned() -> None:
    # X9: kernel.py is not edited; these are the private members frontier.py relies on.
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
                            ("_deadline", ["deadline"])):
        assert isinstance(inspect.getattr_static(ShortfallKernel, name), staticmethod), name
        assert [p for p, _ in parameters(getattr(ShortfallKernel, name))] == arguments, name
    assert parameters(engine._Run.__init__) == [
        ("self", "POSITIONAL_OR_KEYWORD"), ("deadline", "POSITIONAL_OR_KEYWORD"),
        ("seed", "POSITIONAL_OR_KEYWORD")]
    assert parameters(engine._Run.solve) == [
        ("self", "POSITIONAL_OR_KEYWORD"), ("model", "POSITIONAL_OR_KEYWORD")]
    assert parameters(engine._at_least) == [
        ("model", "POSITIONAL_OR_KEYWORD"), ("expression", "POSITIONAL_OR_KEYWORD"),
        ("lower", "POSITIONAL_OR_KEYWORD")]
    assert parameters(engine._solver) == [
        ("deadline", "POSITIONAL_OR_KEYWORD"), ("seed", "POSITIONAL_OR_KEYWORD")]
    assert {f.name for f in fields(engine._Background)} >= {
        "model", "variables", "slots", "vectors", "reasons"}
    assert engine.Lineup == tuple[tuple[str, int], ...]
    # _Run.solve answers a passed deadline with no solver, which this module records NOT_RUN.
    run = engine._Run(time.monotonic() - 1.0, 1)
    assert run.solve(cp_model.CpModel()) == ("UNKNOWN", None) and run.statuses == []


# --------------------------------------------------------------------------- the corpus


def shipped_frontier_against_the_brute_force(candidates, requirements, formation: str):
    """The comparison of the slow test: the XI Lab model with the opt-in, three dimensions."""
    from galactico.optimization.xi.domain import FORMATIONS
    from galactico.optimization.xi.solver import QUANTIZATION

    dims = ("progression", "left_pass_origins", "right_pass_origins")
    result = nondominated_sums(
        candidates, requirements, formation, dimensions=dims, deadline=time.monotonic() + 600
    )
    check_reply(result)
    inst = Instance(
        FORMATIONS[formation].slots, tuple(candidates), tuple(requirements), QUANTIZATION
    )
    known = truth(inst, dims)
    if len(known.points) > MAX_FRONTIER_POINTS:
        assert (result.certificate.completeness, result.certificate.stopped_by) == (
            "LIMIT_REACHED", "POINT_LIMIT")
        assert listed(result) == known.points[:MAX_FRONTIER_POINTS]
    else:
        assert (result.status, result.certificate.completeness) == ("FRONTIER", "COMPLETE")
        assert listed(result) == known.points
    for p in result.points:
        assert known.vector_of[p.lineup] == p.integer_sums
    return result, known


def test_the_shipped_model_shape_on_a_synthetic_snapshot(synthetic_snapshot) -> None:
    # A rehearsal of the slow test without the corpus: decision_inputs' eleven slots, its
    # role rules and its normalisers, with drawn rates and three extra players who can play
    # several places, so that the frontier has more than one point.
    from galactico.api.decision_lab import decision_inputs

    snap = synthetic_snapshot
    snap.candidates += [
        {"player_id": 9001, "name": "P9001", "position": "MF", "role_rules": ["cm", "dm"],
         "minutes": 1000, "values": {}},
        {"player_id": 9002, "name": "P9002", "position": "FW", "role_rules": ["lw", "rw"],
         "minutes": 1000, "values": {}},
        {"player_id": 9003, "name": "P9003", "position": "DF", "role_rules": ["cb", "lb", "rb"],
         "minutes": 1000, "values": {}},
    ]
    for c in snap.candidates:
        pid = c["player_id"]
        c["values"] = {
            "progression": (pid * 7 % 13) / 10,
            "left_pass_origins": None if c["position"] == "GK" else (pid * 5 % 11) / 10,
            "right_pass_origins": (pid * 3 % 7) / 10,
        }
    candidates, requirements = decision_inputs(snap, "4-3-3")
    result, known = shipped_frontier_against_the_brute_force(candidates, requirements, "4-3-3")
    assert len(known.points) >= 2 and len(result.points) == len(known.points)


@pytest.mark.slow
def test_madrid_three_dimensional_frontier_equals_the_brute_force(corpus_root) -> None:
    from galactico.api.decision_lab import decision_inputs
    from galactico.optimization.historical import load_snapshot

    snapshot = load_snapshot(2565907, worlds=0)
    # decision_inputs holds the two side requirements in force: the opt-in state (1.3). The
    # count is the brute force's, never a pinned number (1.6).
    candidates, requirements = decision_inputs(snapshot, "4-3-3")
    shipped_frontier_against_the_brute_force(candidates, requirements, "4-3-3")
