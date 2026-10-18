"""The brute-force oracle of OR-XI-SPEC section 6, checked on instances worked out by hand.

Each hand instance is small enough that its answer is written in the test and derived in a
comment beside it, not computed by the oracle being checked. The pruned backtracking of the
CONFLICT part is also compared with a plain enumeration of every assignment on seeded
instances, and the generator is checked against the rules section 6 gives it. An AST check
holds the oracle to its four imports. Data-free: nothing here reads the corpus.
"""

from __future__ import annotations

import ast
import itertools
from fractions import Fraction
from pathlib import Path

import pytest
import xi_exact_oracle as oracle
from xi_exact_oracle import (
    HARD_FLOOR_CONSERVATIVE,
    SOLVE_HALF_EVEN,
    Instance,
    OracleCandidate,
    OracleRequirement,
    OracleSlot,
)

from galactico.domain.labels import scan_labels
from galactico.optimization.xi.domain import Candidate, Formation, Slot, TacticalRequirement

ORACLE = Path(__file__).with_name("xi_exact_oracle.py")
SEEDS = range(120)


def players(x):
    return frozenset(p for _, p in x)


# --------------------------------------------------------------------------- the file


def test_the_oracle_imports_four_modules_and_nothing_from_galactico() -> None:
    tree = ast.parse(ORACLE.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "no relative import"
            roots.add(node.module.split(".")[0])
    # ``from __future__ import annotations`` is a compiler directive, not a dependency.
    assert roots - {"__future__"} == {"itertools", "math", "fractions", "collections"}
    assert "galactico" not in roots
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not called & {"__import__", "exec", "eval", "compile", "open"}


def test_pytest_collects_nothing_from_the_oracle() -> None:
    assert not ORACLE.stem.startswith("test_") and not ORACLE.stem.endswith("_test")
    tree = ast.parse(ORACLE.read_text(encoding="utf-8"))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef | ast.ClassDef)]
    assert not [name for name in names if name.lower().startswith("test")]


# --------------------------------------------------------------------------- core


def test_the_three_rules_round_the_exact_value() -> None:
    # Section 1.2: the float rule gives 134446 on 1.344465 / 1.0 at 100000, the exact value 134447.
    assert int(round(1.344465 / 1.0 * 100_000)) == 134_446
    assert oracle.objective(1.344465, 1.0, 100_000) == 134_447
    assert oracle.half_even(1.344465, 1.0, 100_000) == 134_447
    # Section 2.1: the floats 0.15 and 0.3 lie just below their decimals, so 14999 + 14999 < 30000.
    assert oracle.floor_coef(0.15, 1, 100_000) == 14_999
    assert oracle.ceil_target(0.3, 1, 100_000) == 30_000
    # Half-even on exact halves; floor and ceiling below zero.
    assert [oracle.objective(v, 1, 1) for v in (0.5, 1.5, 2.5, -0.5, -1.5)] == [0, 2, 2, 0, -2]
    assert oracle.half_even(5, 4, 2) == 2  # 2.5
    assert oracle.objective(3, 4, 2) == 2  # 1.5
    assert (oracle.floor_coef(-0.5, 1, 1), oracle.ceil_target(-0.5, 1, 1)) == (-1, 0)


def eligibility_instance() -> Instance:
    # r applies at b only. Slot a takes DF, slot b DF or MF.
    #   1 DF measured            a, b
    #   2 MF measured            b
    #   3 DF zero minutes        nowhere
    #   4 DF eligible at b only  b
    #   5 MF unmeasured          eligible at b, not admissible there (r applies)
    #   6 FW                     nowhere
    #   7 DF unmeasured          admissible at a (r does not apply), not at b
    return Instance(
        (OracleSlot("a", ("DF",)), OracleSlot("b", ("DF", "MF"))),
        (
            OracleCandidate(7, "DF", {}),
            OracleCandidate(2, "MF", {"m": 0.5}),
            OracleCandidate(4, "DF", {"m": 0.25}, eligible_slots=("b",)),
            OracleCandidate(1, "DF", {"m": 1.0}),
            OracleCandidate(3, "DF", {"m": 2.0}, minutes=0),
            OracleCandidate(5, "MF", {"m": None}),
            OracleCandidate(6, "FW", {"m": 3.0}),
        ),
        (OracleRequirement("r", "m", 1.0, 1.0, ("b",)),),
        100,
    )


def test_options_and_xis_follow_eligibility_and_the_measurement_rule() -> None:
    inst = eligibility_instance()
    point = oracle.point_vectors(inst)
    assert oracle.options(inst, vectors=point, excluded=()) == ((1, 7), (1, 2, 4))
    assert oracle.options(inst, vectors=point, excluded=(1,)) == ((7,), (2, 4))
    assert oracle.options(
        inst, vectors=point, excluded=(1,), keys_ignore_exclusions=True
    ) == ((1, 7), (1, 2, 4))
    # product (1, 7) x (1, 2, 4), injective: (1,1) is not an XI.
    assert oracle.xis(inst, locked=(), excluded=(), vectors=point) == (
        (("a", 1), ("b", 2)),
        (("a", 1), ("b", 4)),
        (("a", 7), ("b", 1)),
        (("a", 7), ("b", 2)),
        (("a", 7), ("b", 4)),
    )
    assert oracle.xis(inst, locked=(4,), excluded=(), vectors=point) == (
        (("a", 1), ("b", 4)),
        (("a", 7), ("b", 4)),
    )
    assert oracle.xis(inst, locked=(), excluded=(1,), vectors=point) == (
        (("a", 7), ("b", 2)),
        (("a", 7), ("b", 4)),
    )
    assert oracle.xis(inst, locked=(4,), excluded=(4,), vectors=point) == ()
    with pytest.raises(ValueError):
        oracle.xis(inst, locked=(99,), excluded=(), vectors=point)


def test_exact_sum_and_whole_vector_replacement() -> None:
    inst = eligibility_instance()
    point = oracle.point_vectors(inst)
    at_b = inst.requirements[0]
    everywhere = OracleRequirement("all", "m", 0.0, 1.0)
    assert oracle.exact_sum((("a", 7), ("b", 2)), at_b, point) == Fraction(1, 2)
    assert oracle.exact_sum((("a", 1), ("b", 2)), everywhere, point) == Fraction(3, 2)
    assert oracle.exact_sum((("a", None), ("b", 4)), everywhere, point) == Fraction(1, 4)
    with pytest.raises(ValueError):
        oracle.exact_sum((("a", 7), ("b", 2)), everywhere, point)
    world = {2: {"m": 1.0, "other": 2.0}}
    vector = oracle.world_vector(inst, world, 2)
    assert vector == {"m": 1.0, "other": 2.0}
    vector["m"] = None
    assert world[2]["m"] == 1.0, "a copy, never the world's own table"
    assert oracle.world_vector(inst, world, 9) == {}
    assert oracle.world_vectors(inst, world)[1] == {}


def test_the_discard_rule_reads_eligibility_requirements_and_exclusions() -> None:
    inst = eligibility_instance()
    # r applies at b; the players eligible there are 1, 2, 4, 5 and 7, measured or not.
    full = {p: {"m": 1.0} for p in (1, 2, 4, 5, 7)}
    worlds = {
        3: {**full, 4: {"m": None}},                    # 4 unmeasured at b: discarded
        0: full,                                        # used
        2: {p: v for p, v in full.items()},             # 3 and 6 eligible nowhere: used
        1: {p: v for p, v in full.items() if p != 2},   # 2 absent: discarded
    }
    assert oracle.used_worlds(inst, worlds, excluded=()) == ((0, 2), (1, 3))
    assert oracle.used_worlds(inst, worlds, excluded=(4,)) == ((0, 2, 3), (1,))
    # 7 is unmeasured in his own table, yet a world that measures him is used: the candidates'
    # tables play no part in the rule, and neither do locks.
    assert oracle.used_worlds(inst._replace(locked=(4,)), {0: full}, excluded=()) == ((0,), ())


# --------------------------------------------------------------------------- CEILING


def two_witness_instance() -> Instance:
    # Section 9's planted instance: q = 1, n = 1, slots a and b.
    #          r    f  g
    #   1 A1  0.6   1  1   at a
    #   2 A2  1.4   2  0   at a
    #   3 B1  0.6   1  0   at b
    #   4 B2  0.4   0  1   at b
    def player(pid: int, slot: str, r: float, f: int, g: int) -> OracleCandidate:
        return OracleCandidate(pid, "MF", {"r": r, "f": f, "g": g}, eligible_slots=(slot,))

    return Instance(
        (OracleSlot("a", ("MF",)), OracleSlot("b", ("MF",))),
        (player(1, "a", 0.6, 1, 1), player(2, "a", 1.4, 2, 0),
         player(3, "b", 0.6, 1, 0), player(4, "b", 0.4, 0, 1)),
        (OracleRequirement("r", "r", 1.5, 1.0), OracleRequirement("f", "f", 0.0, 1.0),
         OracleRequirement("g", "g", 0.0, 1.0)),
        1,
    )


def test_ceilings_where_each_witness_decides_one_fact() -> None:
    inst = two_witness_instance()
    # f >= 2 and g >= 1 keep A1+B1 (r 1.2, f 2, g 1) and A2+B2 (r 1.8, f 2, g 1); A1+B2 has
    # f 1 and A2+B1 has g 0. O_r: round(0.6) + round(0.6) = 2, round(1.4) + round(0.4) = 1.
    truth = oracle.ceilings(inst, floors={"g": 1, "f": 2}, locked=(), excluded=())
    assert (truth.state, truth.xi_count, truth.feasible_count) == ("FIELDABLE", 4, 2)
    assert set(truth.feasible) == {(("a", 1), ("b", 3)), (("a", 2), ("b", 4))}
    by_id = {r.requirement_id: r for r in truth.ranges}
    assert [r.requirement_id for r in truth.ranges] == ["f", "g", "r"]
    r = by_id["r"]
    assert (r.largest_integer, r.least_integer) == (2, 1)
    assert r.largest_sum == Fraction(1.4) + Fraction(0.4)    # the LEAST end's XI, 1.8
    assert r.least_sum == 2 * Fraction(0.6)                  # the LARGEST end's XI, 1.2
    assert (r.minimum_reached, r.minimum_missed) == (True, True)
    assert r.minimum == Fraction(1.5)
    assert (r.applicable_slots, r.allowance) == (2, Fraction(1))   # a_r * n_r / (2q)
    assert r.sums == (2 * Fraction(0.6), Fraction(1.4) + Fraction(0.4))
    assert (by_id["f"].largest_integer, by_id["f"].least_integer) == (2, 2)

    # Without floors every XI counts: O_r of A1+B2 is 1, of A2+B1 is 2.
    free = {r.requirement_id: r for r in oracle.ceilings(inst, floors=None, locked=(),
                                                         excluded=()).ranges}["r"]
    assert (free.largest_integer, free.least_integer) == (2, 1)
    assert free.largest_sum == Fraction(1.4) + Fraction(0.6)
    assert free.least_sum == Fraction(0.6) + Fraction(0.4)

    empty = oracle.ceilings(inst, floors={"f": 4}, locked=(), excluded=())
    assert (empty.state, empty.feasible_count, empty.ranges) == ("NOT_SATISFIABLE", 0, ())
    none = oracle.ceilings(inst, floors={}, locked=(1, 2), excluded=())   # both only at a
    assert (none.state, none.xi_count, none.ranges) == ("UNFIELDABLE", 0, ())
    with pytest.raises(ValueError):
        oracle.ceilings(inst, floors={"unknown": 1.0}, locked=(), excluded=())


# --------------------------------------------------------------------------- FRONTIER


def rounding_instance() -> Instance:
    # Section 4.1's counterexample: q = 1, n = 1, two slots, a(0.5, 1.0) b(0.5, 1.0)
    # c(0.6, 0.5) d(0.3, 1.0) as players 1 to 4.
    values = {1: (0.5, 1.0), 2: (0.5, 1.0), 3: (0.6, 0.5), 4: (0.3, 1.0)}
    return Instance(
        (OracleSlot("s1", ("MF",)), OracleSlot("s2", ("MF",))),
        tuple(OracleCandidate(p, "MF", {"m1": v[0], "m2": v[1]}) for p, v in values.items()),
        (OracleRequirement("r1", "m1", 0.0, 1.0), OracleRequirement("r2", "m2", 0.0, 1.0)),
        1,
    )


def test_frontier_on_the_rounding_counterexample() -> None:
    inst = rounding_instance()
    # {a,b} (0,2) raw (1.0,2.0); {a,c} {b,c} (1,1) raw (1.1,1.5); {a,d} {b,d} (0,2) raw
    # (0.8,2.0); {c,d} (1,1) raw (0.9,1.5). Both integer vectors are nondominated.
    truth = oracle.frontier(inst, dimensions=("r1", "r2"), floors=None, locked=(), excluded=())
    assert truth.state == "FIELDABLE"
    assert truth.points == truth.vectors == ((1, 1), (0, 2))
    assert {players(x) for x in truth.witnesses((1, 1))} == {
        frozenset({1, 3}), frozenset({2, 3}), frozenset({3, 4})}
    assert {players(x) for x in truth.witnesses((0, 2))} == {
        frozenset({1, 2}), frozenset({1, 4}), frozenset({2, 4})}
    assert len({truth.raw_of[x] for x in truth.witnesses((1, 1))}) == 2
    # Raw sums: (1.0, 2.0) dominates (0.8, 2.0) and (1.1, 1.5) dominates (0.9, 1.5).
    assert {players(x) for x in truth.raw_nondominated} == {
        frozenset({1, 2}), frozenset({1, 3}), frozenset({2, 3})}
    assert len(truth.vector_of) == 12   # six player sets, each in two slot orders

    reversed_ = oracle.frontier(inst, dimensions=("r2", "r1"), floors=None, locked=(),
                                excluded=())
    assert reversed_.points == ((2, 0), (1, 1))

    without_c = oracle.frontier(inst, dimensions=("r1", "r2"), floors=None, locked=(),
                                excluded=(3,))
    assert without_c.points == ((0, 2),)
    assert len({without_c.raw_of[x] for x in without_c.witnesses((0, 2))}) == 2

    with pytest.raises(ValueError):
        oracle.frontier(inst, dimensions=("r1", "r1"), floors=None, locked=(), excluded=())


def test_frontier_order_and_floors_on_one_slot() -> None:
    # One slot, players i = 1..5 with (6 - i, i): every vector is nondominated.
    inst = Instance(
        (OracleSlot("s", ("MF",)),),
        tuple(OracleCandidate(i, "MF", {"m1": 6 - i, "m2": i}) for i in range(1, 6)),
        (OracleRequirement("r1", "m1", 0.0, 1.0), OracleRequirement("r2", "m2", 0.0, 1.0)),
        1,
    )
    listed = ((5, 1), (4, 2), (3, 3), (2, 4), (1, 5))
    forward = oracle.frontier(inst, dimensions=("r1", "r2"), floors=None, locked=(), excluded=())
    backward = oracle.frontier(inst, dimensions=("r2", "r1"), floors=None, locked=(), excluded=())
    assert forward.points == backward.points == listed
    assert players(forward.witnesses((5, 1))[0]) == {1}
    assert players(backward.witnesses((5, 1))[0]) == {5}
    floored = oracle.frontier(inst, dimensions=("r1", "r2"), floors={"r1": 3}, locked=(),
                              excluded=())
    assert floored.points == listed[:3]
    assert oracle.frontier(inst, dimensions=("r1", "r2"), floors={"r1": 6}, locked=(),
                           excluded=()).state == "NOT_SATISFIABLE"
    assert oracle.dominates((1, 2), (1, 1)) and not oracle.dominates((1, 1), (1, 1))
    assert oracle.nondominated([(1, 1), (0, 2), (0, 1), (1, 1)]) == ((1, 1), (0, 2))


# --------------------------------------------------------------------------- CONFLICT


def progression_instance(slots: tuple[OracleSlot, ...], positions: dict[int, str]) -> Instance:
    return Instance(
        slots,
        tuple(OracleCandidate(p, pos, {"progression": 1.0}) for p, pos in positions.items()),
        (OracleRequirement("progression", "progression", 0.0, 1.0),),
        100,
    )


def test_the_deletion_filter_on_the_pinned_lock_and_exclusion_instance() -> None:
    # Section 3.3: slots a, b {DF}, players 1, 2, 3 DF at 1.0, exclusion:1, a floor of 2.5 (no
    # assignment sums above 2.0) and lock:1.
    inst = progression_instance(
        (OracleSlot("a", ("DF",)), OracleSlot("b", ("DF",))), {1: "DF", 2: "DF", 3: "DF"}
    )
    model = oracle.conflict_model(inst, arithmetic=HARD_FLOOR_CONSERVATIVE,
                                  floors={"progression": 2.5}, locked=(1,), excluded=(1,))
    assert model.declarations == ("slot:a", "slot:b", "exclusion:1", "floor:progression",
                                  "lock:1")
    assert model.targets == {"progression": 250}
    assert set(model.coefficients["progression"].values()) == {100}
    # Drop slot:a, slot:b (lock with exclusion), exclusion:1 (the floor alone), keep the floor
    # ({lock:1} holds), drop lock:1 ({floor} still fails).
    truth = oracle.deletion_filter(model.declarations, model)
    assert truth.status == "MINIMAL_CERTIFIED"
    assert truth.conflict == ("floor:progression",)
    assert [row.outcome for row in truth.rows] == [
        "DROPPED", "DROPPED", "DROPPED", "KEPT_WITNESS", "DROPPED"]
    kept = truth.rows[3].witness
    assert 1 in players(kept)                     # it meets {lock:1}, and uses the excluded 1
    assert len(truth.nodes) == 1 + len(model.declarations)
    assert oracle.restores_alone("floor:progression", model) is False
    assert oracle.restores_alone("slot:a", model) is None
    assert oracle.minimal_conflicting_sets(model) == (
        ("floor:progression",), ("exclusion:1", "lock:1"))
    floor_first = ("floor:progression", "slot:a", "slot:b", "exclusion:1", "lock:1")
    assert oracle.deletion_filter(floor_first, model).conflict == ("exclusion:1", "lock:1")
    with pytest.raises(ValueError):
        oracle.deletion_filter(model.declarations[1:], model)
    with pytest.raises(RuntimeError):
        oracle.satisfiable(("lock:1",), model, node_limit=1)


def test_the_deletion_filter_on_the_three_slot_instance() -> None:
    # Slots s1 {DF}, s2 {DF, MF}, s3 {MF}; 1, 2 DF and 3, 4 MF at 1.0; a floor of 3.5 (three
    # players reach 3.0) and exclusion:2. Every set holding the floor fails; the empty set holds.
    inst = progression_instance(
        (OracleSlot("s1", ("DF",)), OracleSlot("s2", ("DF", "MF")), OracleSlot("s3", ("MF",))),
        {1: "DF", 2: "DF", 3: "MF", 4: "MF"},
    )
    model = oracle.conflict_model(inst, arithmetic=HARD_FLOOR_CONSERVATIVE,
                                  floors={"progression": 3.5}, locked=(), excluded=(2,))
    truth = oracle.deletion_filter(model.declarations, model)
    assert truth.conflict == ("floor:progression",)
    assert [row.outcome for row in truth.rows] == ["DROPPED"] * 4 + ["KEPT_WITNESS"]
    # Without the floor, 1 at s1, 3 at s2, 4 at s3 is an XI that leaves 2 out.
    assert oracle.restores_alone("floor:progression", model) is True
    assert oracle.minimal_conflicting_sets(model) == (("floor:progression",),)
    assert oracle.satisfiable(model.declarations[:4], model).satisfiable


def test_the_two_arithmetics_differ_at_the_boundary() -> None:
    # q = 1, n = 1, two slots, players at 0.75, minimum 1.5. Half-even: 1 + 1 >= 2. Conservative:
    # floor(0.75) = 0 each, 0 + 0 < ceil(1.5) = 2.
    inst = Instance(
        (OracleSlot("a", ("MF",)), OracleSlot("b", ("MF",))),
        (OracleCandidate(1, "MF", {"m": 0.75}), OracleCandidate(2, "MF", {"m": 0.75})),
        (OracleRequirement("r", "m", 1.5, 1.0),),
        1,
    )
    solve = oracle.conflict_model(inst, arithmetic=SOLVE_HALF_EVEN, mode="SATISFY", locked=(),
                                  excluded=())
    assert solve.targets == {"r": 2} and set(solve.coefficients["r"].values()) == {1}
    feasible = oracle.deletion_filter(solve.declarations, solve)
    assert (feasible.status, feasible.conflict, feasible.rows) == ("MODEL_FEASIBLE", (), ())
    assert players(feasible.initial_witness) == {1, 2}
    floors = oracle.conflict_model(inst, arithmetic=HARD_FLOOR_CONSERVATIVE, locked=(),
                                   excluded=())
    assert oracle.deletion_filter(floors.declarations, floors).conflict == ("floor:r",)
    assert oracle.conflict_model(inst, arithmetic=HARD_FLOOR_CONSERVATIVE, floors={}, locked=(),
                                 excluded=()).declarations == ("slot:a", "slot:b")
    balance = oracle.conflict_model(inst, arithmetic=SOLVE_HALF_EVEN, mode="BALANCE", locked=(),
                                    excluded=())
    assert balance.declarations == ("slot:a", "slot:b")
    hard = inst._replace(requirements=(OracleRequirement("r", "m", 1.5, 1.0, hard=True),))
    assert "floor:r" in oracle.conflict_model(hard, arithmetic=SOLVE_HALF_EVEN, mode="BALANCE",
                                              locked=(), excluded=()).declarations
    with pytest.raises(ValueError):
        oracle.conflict_model(inst, arithmetic=SOLVE_HALF_EVEN, mode="LEXICOGRAPHIC", locked=(),
                              excluded=())
    with pytest.raises(ValueError):
        oracle.conflict_model(inst, arithmetic=SOLVE_HALF_EVEN, mode="SATISFY", floors={},
                              locked=(), excluded=())


def every_assignment_meets(model: oracle.ConflictModel) -> list[frozenset[str]]:
    """Per assignment, the declarations it meets: a plain enumeration, no pruning."""
    met = []
    for chosen in itertools.product(*((*row, None) for row in model.options)):
        placed = [p for p in chosen if p is not None]
        if len(placed) != len(set(placed)):
            continue
        holds = {f"slot:{s}" for s, p in zip(model.slot_ids, chosen, strict=True)
                 if p is not None}
        holds |= {f"exclusion:{p}" for p in model.excluded if p not in placed}
        holds |= {f"lock:{p}" for p in model.locked if p in placed}
        for r, target in model.targets.items():
            total = sum(model.coefficients[r][(i, p)] for i, p in enumerate(chosen)
                        if p is not None and i in model.applicable[r])
            if total >= target:
                holds.add(f"floor:{r}")
        met.append(frozenset(holds))
    return met


def test_pruned_backtracking_agrees_with_plain_enumeration() -> None:
    compared = 0
    for seed in range(40):
        drawn = oracle.instances(seed)
        for inst, model in (
            (drawn.conflict_floors, oracle.conflict_model(
                drawn.conflict_floors, arithmetic=HARD_FLOOR_CONSERVATIVE,
                floors=drawn.conflict_floors.floors, locked=drawn.conflict_floors.locked,
                excluded=drawn.conflict_floors.excluded)),
            (drawn.conflict_solve, oracle.conflict_model(
                drawn.conflict_solve, arithmetic=SOLVE_HALF_EVEN, mode=drawn.conflict_solve.mode,
                locked=drawn.conflict_solve.locked, excluded=drawn.conflict_solve.excluded)),
        ):
            size = 1
            for row in model.options:
                size *= len(row) + 1
            if size > 20_000:
                continue
            met = every_assignment_meets(model)
            every = frozenset(model.declarations)
            tests = [every, frozenset()] + [every - {c} for c in every] + [
                frozenset({c}) for c in every]
            for tested in tests:
                answer = oracle.satisfiable(tested, model)
                assert answer.satisfiable == any(tested <= m for m in met), (inst.seed, tested)
                compared += 1
    assert compared > 500


# --------------------------------------------------------------------------- RISK


def risk_instance() -> Instance:
    # One slot, three MF players, r1 and r2 at minimum 2, n = 1, q = 1. World values (m1, m2):
    #        w0      w1      w2      w3
    #   1  (2, 0)  (0, 0)  (2, 2)  (2, 2)
    #   2  (1, 1)  (1, 1)  (0, 1)  (-, 0)    w3 lacks 2's m1: discarded
    #   3  (0, 2)  (2, 2)  (0, 0)  (0, 0)
    # Shortfalls d = (2 - v1, 2 - v2)+ give the pairs (M, T):
    #   1  (2, 2)  (2, 4)  (0, 0)
    #   2  (1, 2)  (1, 2)  (2, 3)
    #   3  (2, 2)  (0, 0)  (2, 4)
    def world(*rows: tuple[float | None, float]) -> dict[int, dict[str, float | None]]:
        return {p: {"m1": a, "m2": b} for p, (a, b) in enumerate(rows, start=1)}

    return Instance(
        (OracleSlot("s", ("MF",)),),
        (OracleCandidate(1, "MF", {"m1": 1.0, "m2": 1.0}),
         OracleCandidate(2, "MF", {"m1": 2.0, "m2": 0.0}),
         OracleCandidate(3, "MF", {"m1": None, "m2": 2.0})),
        (OracleRequirement("r1", "m1", 2.0, 1.0), OracleRequirement("r2", "m2", 2.0, 1.0)),
        1,
        worlds={
            0: world((2.0, 0.0), (1.0, 1.0), (0.0, 2.0)),
            1: world((0.0, 0.0), (1.0, 1.0), (2.0, 2.0)),
            2: world((2.0, 2.0), (0.0, 1.0), (0.0, 0.0)),
            3: world((2.0, 2.0), (None, 0.0), (0.0, 0.0)),
        },
    )


def test_tail_rules_on_three_worlds() -> None:
    inst = risk_instance()
    worlds = inst.worlds
    one, two, three = ((("s", 1),), (("s", 2),), (("s", 3),))
    assert oracle.used_worlds(inst, worlds, excluded=()) == ((0, 1, 2), (3,))
    assert oracle.used_worlds(inst, worlds, excluded=(2,)) == ((0, 1, 2, 3), ())
    assert oracle.world_pairs(inst, one, worlds=worlds, excluded=()) == (
        (0, (2, 2)), (1, (2, 4)), (2, (0, 0)))
    # k = 1: worst pairs (2,4), (2,3), (2,4): equal M, T decides for player 2.
    worst = oracle.tail_optimum(inst, 1, worlds=worlds, locked=(), excluded=())
    assert (worst.status, worst.optimum, worst.level_set) == ("CERTIFIED", (2, 3), (two,))
    assert (worst.used_world_ids, worst.discarded_world_ids) == ((0, 1, 2), (3,))
    assert worst.membership == ((1, False, False), (2, True, True), (3, False, False))
    # k = 2: (4,6), (3,5), (4,6).
    assert oracle.tail_optimum(inst, 2, worlds=worlds, locked=(), excluded=()).optimum == (3, 5)
    # k = 3: (4,6), (4,7), (4,6): two XIs tie.
    every = oracle.tail_optimum(inst, 3, worlds=worlds, locked=(), excluded=())
    assert every.optimum == (4, 6)
    assert every.player_sets == {frozenset({1}), frozenset({3})}
    assert every.membership == ((1, True, False), (2, False, False), (3, True, False))
    assert oracle.tail_optimum(inst, 4, worlds=worlds, locked=(), excluded=()).status == (
        "NOT_EVALUABLE")
    # Player 2's pairs in key order: w2 (2,3), w0 (1,2), w1 (1,2).
    assert oracle.tail_of(inst, two, 2, worlds=worlds, excluded=()) == ((2, 0), (1,))
    assert oracle.tail_of(inst, one, 1, worlds=worlds, excluded=()) == ((1,), ())
    assert oracle.tail_sum_of(inst, two, 2, worlds=worlds, excluded=()) == (3, 5)
    assert oracle.tail_sum_of(inst, three, 3, worlds=worlds, excluded=()) == (4, 6)
    # Every rate is non-negative, so L = 0 and U = t = 2 per requirement: T_bound = 4.
    assert oracle.t_bound(inst, worlds, excluded=()) == 4
    with pytest.raises(ValueError):
        oracle.tail_of(inst, two, 4, worlds=worlds, excluded=())


def test_regret_and_binding_worlds_on_three_worlds() -> None:
    inst = risk_instance()
    worlds = inst.worlds
    one, two, three = ((("s", 1),), (("s", 2),), (("s", 3),))
    # Least pairs: w0 (1,2) by 2, w1 (0,0) by 3, w2 (0,0) by 1. Largest differences:
    # 1: (2,4) at w1; 2: (2,3) at w2; 3: (2,4) at w2.
    regret = oracle.regret_optimum(inst, worlds=worlds, locked=(), excluded=())
    assert (regret.status, regret.optimum, regret.level_set) == ("CERTIFIED", (2, 3), (two,))
    assert regret.world_least == ((0, (1, 2)), (1, (0, 0)), (2, (0, 0)))
    assert oracle.binding_of(inst, two, worlds=worlds, locked=(), excluded=()) == (2,)
    assert oracle.binding_of(inst, one, worlds=worlds, locked=(), excluded=()) == (1,)
    assert oracle.regret_of(inst, three, worlds=worlds, locked=(), excluded=()) == (2, 4)
    # One world: the regret level set is BALANCE's in that world.
    alone = oracle.regret_optimum(inst, worlds={1: worlds[1]}, locked=(), excluded=())
    assert (alone.optimum, alone.level_set) == ((0, 0), (three,))
    assert oracle.balance_optimum(inst, vectors=oracle.world_vectors(inst, worlds[1]), locked=(),
                                  excluded=()) == ((0, 0), (three,))


def test_risk_terminal_outcomes_and_point_values() -> None:
    inst = risk_instance()
    worlds = inst.worlds
    # Two locked players and one slot: no XI in any world.
    for truth in (
        oracle.tail_optimum(inst, 1, worlds=worlds, locked=(1, 2), excluded=()),
        oracle.regret_optimum(inst, worlds=worlds, locked=(1, 2), excluded=()),
    ):
        assert (truth.status, truth.optimum, truth.level_set, truth.membership) == (
            "UNFIELDABLE", None, (), ())
    # Fewer used worlds than k comes first.
    assert oracle.tail_optimum(inst, 4, worlds=worlds, locked=(1, 2), excluded=()).status == (
        "NOT_EVALUABLE")
    only_discarded = {3: worlds[3]}
    assert oracle.regret_optimum(inst, worlds=only_discarded, locked=(), excluded=()).status == (
        "NOT_EVALUABLE")
    with pytest.raises(ValueError):
        oracle.t_bound(inst, only_discarded, excluded=())
    # Point values: 1 (1, 1) -> d (1, 1); 2 (2, 0) -> d (0, 2); 3 lacks m1.
    assert oracle.point_loss(inst, (("s", 1),)) == (1, 2)
    assert oracle.point_loss(inst, (("s", 3),)) is None
    assert oracle.point_sums(inst, (("s", 3),)) == (("r1", None), ("r2", Fraction(2)))
    assert oracle.point_sums(inst, (("s", 1),)) == (("r1", Fraction(1)), ("r2", Fraction(1)))
    assert oracle.balance_optimum(inst, vectors=oracle.point_vectors(inst), locked=(),
                                  excluded=()) == ((1, 2), ((("s", 1),),))
    # With no requirement in force every loss is (0, 0).
    assert oracle.loss_pair(inst._replace(requirements=()), (("s", 1),), {}) == (0, 0)


# --------------------------------------------------------------------------- instances


def test_the_generator_is_deterministic_and_keeps_its_ranges() -> None:
    assert oracle.instances(7) == oracle.instances(7)
    assert oracle.instances(7) != oracle.instances(8)
    for seed in SEEDS:
        drawn = oracle.instances(seed)
        assert [inst.kind for inst in drawn] == list(oracle.KINDS)
        for inst in drawn:
            assert inst.seed == seed and inst.quantization in oracle.QUANTIZATIONS
            assert 3 <= len(inst.slots) <= 5 and 5 <= len(inst.candidates) <= 8
            expected = (3,) if inst.kind == "FRONTIER" else (1, 2, 3)
            assert len(inst.requirements) in expected
            assert len({c.player_id for c in inst.candidates}) == len(inst.candidates)
            assert all(r.hard is False for r in inst.requirements if inst.kind != "CONFLICT_SOLVE")
        ids = sorted(r.requirement_id for r in drawn.frontier.requirements)
        two, three = drawn.frontier.dimensions
        assert len(two) == len(set(two)) == 2 and set(two) <= set(ids)
        assert sorted(three) == ids
        risk = drawn.risk
        assert 1 <= len(risk.worlds) <= 5 and sorted(risk.worlds) == list(range(len(risk.worlds)))
        assert oracle._guard_admits(risk)


def test_risk_and_explain_solve_draws_are_dyadic_and_round_alike() -> None:
    for seed in SEEDS:
        drawn = oracle.instances(seed)
        for inst in (drawn.conflict_solve, drawn.risk):
            q = inst.quantization
            for r in inst.requirements:
                n = r.normalizer
                assert n in oracle.DYADIC_NORMALIZERS
                assert (r.minimum * 64).is_integer() and 0 <= r.minimum <= 4
                values = [c.values.get(r.metric) for c in inst.candidates]
                for world in (inst.worlds or {}).values():
                    values += [vector.get(r.metric) for vector in world.values()]
                for v in [r.minimum] + [v for v in values if v is not None]:
                    assert (v * 64).is_integer() and -2 <= v <= 4
                    # The shipped float rule, written out, against exact half-even.
                    assert int(round(v / n * q)) == oracle.half_even(v, n, q)


def test_the_drawn_instances_cover_what_the_tool_tests_need() -> None:
    seen: set[str] = set()
    for seed in SEEDS:
        drawn = oracle.instances(seed)
        for inst in (drawn.ceiling, drawn.frontier, drawn.conflict_floors):
            for c in inst.candidates:
                for v in c.values.values():
                    if v is not None and not (v * 64).is_integer():
                        seen.add("decimal")
                    if v is not None and v < 0:
                        seen.add("negative")
        for inst in drawn:
            if any(v is None for c in inst.candidates for v in c.values.values()):
                seen.add("none")
            if any(c.minutes == 0 for c in inst.candidates):
                seen.add("zero minutes")
            if any(c.eligible_slots is not None for c in inst.candidates):
                seen.add("eligible slots")
            if inst.locked:
                seen.add("lock")
            if set(inst.locked) & set(inst.excluded):
                seen.add("locked and excluded")
        c = oracle.ceilings(drawn.ceiling, floors=drawn.ceiling.floors,
                            locked=drawn.ceiling.locked, excluded=drawn.ceiling.excluded)
        seen.add(f"ceiling {c.state}")
        floors_model = oracle.conflict_model(
            drawn.conflict_floors, arithmetic=HARD_FLOOR_CONSERVATIVE,
            floors=drawn.conflict_floors.floors, locked=drawn.conflict_floors.locked,
            excluded=drawn.conflict_floors.excluded)
        seen.add(f"floors {oracle.deletion_filter(floors_model.declarations, floors_model).status}")
        solve = drawn.conflict_solve
        solve_model = oracle.conflict_model(solve, arithmetic=SOLVE_HALF_EVEN, mode=solve.mode,
                                            locked=solve.locked, excluded=solve.excluded)
        seen.add(f"solve {oracle.deletion_filter(solve_model.declarations, solve_model).status}")
        if oracle.used_worlds(drawn.risk, drawn.risk.worlds, excluded=drawn.risk.excluded)[1]:
            seen.add("discarded world")
    assert seen >= {
        "decimal", "negative", "none", "zero minutes", "eligible slots", "lock",
        "locked and excluded", "ceiling FIELDABLE", "ceiling UNFIELDABLE",
        "ceiling NOT_SATISFIABLE", "floors MODEL_FEASIBLE", "floors MINIMAL_CERTIFIED",
        "solve MODEL_FEASIBLE", "solve MINIMAL_CERTIFIED", "discarded world",
    }


def test_drawn_instances_build_domain_objects_whose_labels_pass_the_copy_guard() -> None:
    for seed in SEEDS:
        for inst in oracle.instances(seed):
            built = oracle.domain_inputs(
                inst, slot_type=Slot, formation_type=Formation, candidate_type=Candidate,
                requirement_type=TacticalRequirement)
            assert [c.player_id for c in built.candidates] == [
                c.player_id for c in inst.candidates]
            assert all(r.active for r in built.requirements)
            assert [s.slot_id for s in built.formation.slots] == [s.slot_id for s in inst.slots]
            texts = [r.label for r in built.requirements] + [c.name for c in built.candidates]
            texts += [s.label for s in built.formation.slots] + [built.formation.formation_id]
            assert scan_labels(texts) == []
