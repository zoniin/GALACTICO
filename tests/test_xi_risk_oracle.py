"""DECLARED-RISK (OR-XI-SPEC section 5) against the brute-force oracle, on 120 seeded instances.

Claim: on every seeded instance, at every tail count from 1 to the world count and for the
regret rule, the risk tools return the oracle's status in the order of 5.6, its used and
discarded worlds, its optimum, an XI of its level set, its membership, and, recomputed by the
oracle for the lineup the tool returned, the tail, the boundary ties, the binding worlds, every
world's pair and the point-estimate ledger; every selection and membership call finishes inside
its limits in a subprocess capped in memory and time. This is the file E-13's draft pins in
``risk_solver_oracle_tests``, beside ``tests/xi_exact_oracle.py``. Non-claim: the oracle is a
listing of small drawn instances, not football data; a witness the tool returns is never compared
with a witness of the oracle's choosing, and nothing here reads the corpus.
"""

from __future__ import annotations

import itertools
import math
import pickle
import subprocess
import sys
import time
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

import pytest
import xi_exact_oracle as oracle
from xi_exact_oracle import Instance, OracleCandidate, OracleRequirement, OracleSlot

from galactico.api.runtime import is_complete
from galactico.domain.labels import scan_labels
from galactico.optimization.xi import risk
from galactico.optimization.xi.domain import Candidate, Formation, Slot, TacticalRequirement

SEEDS = range(120)
TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
CALL_SECONDS = 60.0  # the wall clock each call is given; every one must finish inside it
CAP_SECONDS = 900  # the whole subprocess
CAP_BYTES = 2 * 2**30  # address space; a seeded run peaks near 0.5 GiB (ortools 9.15.6755)
WORLD_SEED = 20261010
VERSION = "oracle-worlds-v1"
COMPLETENESS = ("EXACT", "LIMIT_REACHED", "DEADLINE", "MODEL_INVALID")


def domain(inst: Instance):
    return oracle.domain_inputs(
        inst,
        slot_type=Slot,
        formation_type=Formation,
        candidate_type=Candidate,
        requirement_type=TacticalRequirement,
    )


def runs(inst: Instance) -> list[tuple[str, int | None]]:
    """Every rule the file checks on one instance: TAIL at every k of 1..B, WORST_WORLD,
    MINIMAX_REGRET."""
    count = len(inst.worlds)
    return [("TAIL", k) for k in range(1, count + 1)] + [("WORST_WORLD", 1),
                                                         ("MINIMAX_REGRET", None)]


def call(inst: Instance, rule: str, k: int | None, **extra):
    built = domain(inst)
    options = {
        "worlds": inst.worlds,
        "world_count": len(inst.worlds),
        "world_seed": WORLD_SEED,
        "bootstrap_version": VERSION,
        "locked": inst.locked,
        "excluded": inst.excluded,
        "quantization": inst.quantization,
        "deadline": time.monotonic() + CALL_SECONDS,
        **extra,
    }
    return risk.declared_risk_selection(
        built.candidates, built.requirements, built.formation, rule=rule,
        tail_count=None if rule == "MINIMAX_REGRET" else k, **options,
    )


def _produce(path: str) -> None:
    """Run in the capped subprocess: every seeded selection, pickled with its wall time."""
    produced = {}
    for seed in SEEDS:
        inst = oracle.instances(seed).risk
        for rule, k in runs(inst):
            started = time.monotonic()
            result = call(inst, rule, k)
            produced[seed, rule, k] = (result, time.monotonic() - started)
    Path(path).write_bytes(pickle.dumps(produced))


def _cap() -> None:  # pragma: no cover - runs in the child before exec
    import resource  # POSIX only; CI runs on Linux

    resource.setrlimit(resource.RLIMIT_AS, (CAP_BYTES, CAP_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CAP_SECONDS, CAP_SECONDS))


@pytest.fixture(scope="module")
def produced(tmp_path_factory) -> dict:
    """Every seeded TAIL, WORST_WORLD and REGRET selection and membership, solved once in a
    subprocess capped in memory and time (1.5, 5.1): a regression of the crash of 5.1 fails
    here instead of exhausting the machine."""
    if sys.platform == "win32":  # pragma: no cover
        pytest.skip("the memory and time caps need POSIX resource limits")
    path = tmp_path_factory.mktemp("risk-oracle") / "results.pickle"
    script = (
        "import sys; sys.path[:0] = [sys.argv[2], sys.argv[3]]; "
        "import test_xi_risk_oracle as t; t._produce(sys.argv[1])"
    )
    try:
        done = subprocess.run(
            [sys.executable, "-c", script, str(path), str(TESTS), str(ROOT)],
            cwd=ROOT, preexec_fn=_cap, capture_output=True, text=True, timeout=CAP_SECONDS,
        )
    except subprocess.TimeoutExpired:  # pragma: no cover - a regression
        pytest.fail("the seeded risk solves did not finish inside the subprocess's time cap")
    assert done.returncode == 0, done.stderr[-4000:]
    return pickle.loads(path.read_bytes())


def truth_of(inst: Instance, rule: str, k: int | None):
    declared = {"worlds": inst.worlds, "locked": inst.locked, "excluded": inst.excluded}
    if rule == "MINIMAX_REGRET":
        return oracle.regret_optimum(inst, **declared)
    return oracle.tail_optimum(inst, k, **declared)


def check_reply(result) -> None:
    """What every reply holds (1.5, 5.7, 7.7, section 9)."""
    cert = result.certificate
    assert scan_labels(asdict(result)) == []
    assert cert.completeness in COMPLETENESS
    assert result.membership.completeness in (*COMPLETENESS, "NOT_REQUESTED")
    assert is_complete(asdict(result)) == (
        cert.completeness == "EXACT" and result.membership.completeness == "EXACT"
    )
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
    made = [r.status for r in cert.records if r.purpose != "WORLD_LEAST" and r.status != "NOT_RUN"]
    assert [row["status"] for row in result.provenance["risk_solve_deterministic_times"]] == made
    walls = result.provenance["risk_solve_wall_times"]
    assert len(walls) == len(made)
    assert all(isinstance(w, float) and math.isfinite(w) and w >= 0 for w in walls)
    if result.status != "CERTIFIED":
        assert result.lineup == () and result.world_losses == () and result.point_sums == ()
        assert result.tail_sum is None and result.point_loss is None
        assert result.membership.rows == ()


def player_set(lineup) -> frozenset[int]:
    return frozenset(pid for _, pid in lineup)


# --------------------------------------------------------------------------- the oracle


def test_every_selection_finishes_inside_its_limits(produced) -> None:
    assert len(produced) == sum(len(runs(oracle.instances(seed).risk)) for seed in SEEDS)
    for key, (result, elapsed) in produced.items():
        check_reply(result)
        # Within the wall clock and the deterministic limits: no call was cut.
        assert elapsed < CALL_SECONDS, key
        assert result.certificate.completeness == "EXACT", key
        assert result.membership.completeness == "EXACT", key
        assert result.status != "UNKNOWN", key
        for row in result.provenance["risk_solve_deterministic_times"]:
            assert row["deterministic_time"] < risk.SELECTION_DETERMINISTIC_LIMIT, key


def test_statuses_and_worlds_equal_the_oracle(produced) -> None:
    for seed in SEEDS:
        inst = oracle.instances(seed).risk
        used, discarded = oracle.used_worlds(inst, inst.worlds, excluded=inst.excluded)
        for rule, k in runs(inst):
            result, _ = produced[seed, rule, k]
            known = truth_of(inst, rule, k)
            # 5.6's order: NOT_EVALUABLE (|U| = 0, or |U| < k for TAIL), then UNFIELDABLE iff
            # the used worlds share no XI, then a selection.
            expected = (
                "NOT_EVALUABLE" if not used or (rule != "MINIMAX_REGRET" and len(used) < k)
                else "UNFIELDABLE" if not oracle.xis(
                    inst, locked=inst.locked, excluded=inst.excluded,
                    vectors=oracle.world_vectors(inst, inst.worlds[used[0]]))
                else "CERTIFIED"
            )
            assert result.status == known.status == expected, (seed, rule, k)
            cert = result.certificate
            assert cert.used_world_ids == known.used_world_ids == used
            assert tuple(d.world_id for d in cert.discarded_worlds) == discarded
            assert all(d.reason == oracle.DISCARD_REASON for d in cert.discarded_worlds)
            assert cert.discarded_world_count == len(discarded)
            assert (cert.rule, cert.tail_count, result.tail_count) == (
                rule, k, k)
            assert (cert.world_count, cert.world_seed, cert.bootstrap_version) == (
                len(inst.worlds), WORLD_SEED, VERSION)
            if result.status in ("NOT_EVALUABLE", "UNFIELDABLE"):
                # A proved terminal outcome: EXACT, with an EXACT empty membership block.
                assert cert.completeness == "EXACT" and cert.stopped_by is None
                assert result.membership == risk.MembershipBlock((), "EXACT")
                assert is_complete(asdict(result))
            if result.status == "NOT_EVALUABLE":
                assert cert.records == () and cert.solves == 0
                assert result.reasons == (risk.RISK_NOT_EVALUABLE,)


def test_tail_optimum_level_set_tail_and_membership(produced) -> None:
    for seed in SEEDS:
        inst = oracle.instances(seed).risk
        declared = {"worlds": inst.worlds, "excluded": inst.excluded}
        for rule, k in runs(inst):
            result, _ = produced[seed, rule, k]
            if rule == "MINIMAX_REGRET" or result.status != "CERTIFIED":
                continue
            known = truth_of(inst, rule, k)
            summed = (result.tail_sum.summed_maximum_shortfall,
                      result.tail_sum.summed_total_shortfall)
            assert summed == known.optimum, (seed, rule, k)
            # The lineup is an XI of the level set, and its own tail sum is the optimum.
            assert result.lineup in known.level_set
            assert player_set(result.lineup) in known.player_sets
            assert oracle.tail_sum_of(inst, result.lineup, k, **declared) == known.optimum
            # The tail and its boundary ties, recomputed for the lineup the tool returned.
            assert (result.tail_world_ids, result.tail_boundary_ties) == oracle.tail_of(
                inst, result.lineup, k, **declared)
            assert list(result.tail_boundary_ties) == sorted(result.tail_boundary_ties)
            assert result.binding_world_ids == ()
            rows = tuple((r.player_id, r.possible, r.necessary) for r in result.membership.rows)
            assert rows == known.membership, (seed, rule, k)


def test_regret_least_pairs_optimum_binding_and_membership(produced) -> None:
    for seed in SEEDS:
        inst = oracle.instances(seed).risk
        result, _ = produced[seed, "MINIMAX_REGRET", None]
        if result.status != "CERTIFIED":
            continue
        known = truth_of(inst, "MINIMAX_REGRET", None)
        least = tuple(
            (row.world_id, (row.world_least.maximum_shortfall, row.world_least.total_shortfall))
            for row in result.world_losses
        )
        assert least == known.world_least, seed
        assert result.lineup in known.level_set
        assert player_set(result.lineup) in known.player_sets
        declared = {"worlds": inst.worlds, "locked": inst.locked, "excluded": inst.excluded}
        assert oracle.regret_of(inst, result.lineup, **declared) == known.optimum
        assert result.binding_world_ids == oracle.binding_of(inst, result.lineup, **declared)
        assert list(result.binding_world_ids) == sorted(result.binding_world_ids)
        assert (result.tail_world_ids, result.tail_boundary_ties, result.tail_sum) == (
            (), (), None)
        rows = tuple((r.player_id, r.possible, r.necessary) for r in result.membership.rows)
        assert rows == known.membership, seed


def test_world_losses_equal_the_oracle_pairs(produced) -> None:
    for seed in SEEDS:
        inst = oracle.instances(seed).risk
        built = domain(inst)
        for rule, k in runs(inst):
            result, _ = produced[seed, rule, k]
            if result.status != "CERTIFIED":
                continue
            pairs = oracle.world_pairs(inst, result.lineup, worlds=inst.worlds,
                                       excluded=inst.excluded)
            served = tuple(
                (row.world_id, (row.selected.maximum_shortfall, row.selected.total_shortfall))
                for row in result.world_losses
            )
            assert served == pairs, (seed, rule, k)
            again = risk.world_losses(
                result.lineup, built.candidates, built.requirements, built.formation,
                worlds=inst.worlds, locked=inst.locked, excluded=inst.excluded,
                quantization=inst.quantization,
            )
            assert tuple((row.world_id, row.selected) for row in again) == tuple(
                (row.world_id, row.selected) for row in result.world_losses)
            assert all(row.world_least is None for row in again)


def test_world_losses_refuses_a_lineup_that_is_not_an_xi() -> None:
    checked = 0
    for seed in SEEDS:
        inst = oracle.instances(seed).risk
        used, _ = oracle.used_worlds(inst, inst.worlds, excluded=inst.excluded)
        vectors = (oracle.world_vectors(inst, inst.worlds[used[0]]) if used
                   else oracle.point_vectors(inst))
        every = oracle.xis(inst, locked=inst.locked, excluded=inst.excluded, vectors=vectors)
        built = domain(inst)

        def losses(lineup, inst=inst, built=built):
            return risk.world_losses(
                lineup, built.candidates, built.requirements, built.formation,
                worlds=inst.worlds, locked=inst.locked, excluded=inst.excluded,
                quantization=inst.quantization,
            )

        for lineup in every[:3]:
            rows = losses(lineup)
            if used:
                assert tuple((r.world_id, (r.selected.maximum_shortfall,
                                           r.selected.total_shortfall)) for r in rows) == (
                    oracle.world_pairs(inst, lineup, worlds=inst.worlds, excluded=inst.excluded))
            else:
                assert rows == ()
        # Every lineup over admissible keys that is not an XI of the declarations is refused:
        # a missing lock, a repeated player, a slot out of order or a key that is not admissible.
        # Exclusions are not applied to these keys, so an excluded player can appear.
        options = oracle.options(inst, vectors=vectors, excluded=())
        slot_ids = [s.slot_id for s in inst.slots]
        known = set(every)
        broken = []
        for players in itertools.product(*options):
            lineup = tuple(zip(slot_ids, players, strict=True))
            if lineup not in known:
                broken.append(lineup)
            if len(broken) == 10:
                break
        if every and len(slot_ids) > 1:
            broken.append(tuple(reversed(every[0])))
        broken.append(())
        for lineup in broken:
            with pytest.raises(ValueError) as refused:
                losses(lineup)
            assert str(refused.value) == risk.LINEUP_ERROR
            checked += 1
    assert checked > 100
    assert not any(ch.isdigit() for ch in risk.LINEUP_ERROR)


def test_point_values_equal_the_oracle(produced) -> None:
    for seed in SEEDS:
        inst = oracle.instances(seed).risk
        for rule, k in runs(inst):
            result, _ = produced[seed, rule, k]
            if result.status != "CERTIFIED":
                continue
            loss = oracle.point_loss(inst, result.lineup)
            served = result.point_loss
            assert (None if served is None else (served.maximum_shortfall,
                                                 served.total_shortfall)) == loss
            exact = oracle.point_sums(inst, result.lineup)
            assert result.point_sums == tuple(
                (rid, None if value is None else float(value)) for rid, value in exact)


def three_worlds() -> Instance:
    # The oracle file's three-world instance (one slot, players 1 to 3, r1 and r2 at 2, q = 1):
    # player 3 has no point value for m1, and alone in world 1 he is the one least XI.
    def world(*rows):
        return {p: {"m1": a, "m2": b} for p, (a, b) in enumerate(rows, start=1)}

    return Instance(
        (OracleSlot("s", ("MF",), "Slot s"),),
        (OracleCandidate(1, "MF", {"m1": 1.0, "m2": 1.0}, name="Player 1"),
         OracleCandidate(2, "MF", {"m1": 2.0, "m2": 0.0}, name="Player 2"),
         OracleCandidate(3, "MF", {"m1": None, "m2": 2.0}, name="Player 3")),
        (OracleRequirement("r1", "m1", 2.0, 1.0, (), False, "Requirement 1"),
         OracleRequirement("r2", "m2", 2.0, 1.0, (), False, "Requirement 2")),
        1,
        worlds={1: world((0.0, 0.0), (1.0, 1.0), (2.0, 2.0))},
    )


def test_a_planted_none_in_each_point_field() -> None:
    inst = three_worlds()
    for rule in ("TAIL", "WORST_WORLD", "MINIMAX_REGRET"):
        result = call(inst, rule, 1)
        check_reply(result)
        assert result.status == "CERTIFIED" and result.lineup == (("s", 3),)
        # The lineup uses a key the point vectors forbid: no point pair; r1's sum is None, r2's
        # is exact.
        assert result.point_loss is None and oracle.point_loss(inst, result.lineup) is None
        assert result.point_sums == (("r1", None), ("r2", 2.0))
        assert oracle.point_sums(inst, result.lineup) == (("r1", None), ("r2", Fraction(2)))
    # Player 2 measured everywhere at the point: (2, 0) gives shortfalls (0, 2).
    second = inst._replace(worlds={1: {1: {"m1": 0.0, "m2": 0.0}, 2: {"m1": 2.0, "m2": 2.0},
                                       3: {"m1": 0.0, "m2": 0.0}}})
    result = call(second, "TAIL", 1)
    assert result.lineup == (("s", 2),)
    assert result.point_loss == risk.LossPair(2, 2)
    assert oracle.point_loss(second, result.lineup) == (2, 2)
    assert result.point_sums == (("r1", 2.0), ("r2", 0.0))


def test_the_seeded_instances_are_not_vacuous(produced) -> None:
    seen: set[str] = set()
    for seed in SEEDS:
        inst = oracle.instances(seed).risk
        used, discarded = oracle.used_worlds(inst, inst.worlds, excluded=inst.excluded)
        if discarded:
            seen.add("a world discarded")
        declared = {"worlds": inst.worlds, "excluded": inst.excluded}
        for rule, k in runs(inst):
            result, _ = produced[seed, rule, k]
            if result.status != "CERTIFIED":
                continue
            known = truth_of(inst, rule, k)
            seen.add("one XI in a level set" if len(known.level_set) == 1
                     else "several XIs in a level set")
            if rule != "TAIL":
                continue
            # The comparison of E-13's own non-vacuity test: sets of player sets.
            _, point_xis = oracle.balance_optimum(
                inst, vectors=oracle.point_vectors(inst), locked=inst.locked,
                excluded=inst.excluded)
            balance = frozenset(player_set(x) for x in point_xis)
            seen.add("a tail level set equal to the point BALANCE one"
                     if known.player_sets == balance
                     else "a tail level set unlike the point BALANCE one")
            space = oracle.xis(inst, locked=inst.locked, excluded=inst.excluded,
                               vectors=oracle.world_vectors(inst, inst.worlds[used[0]]))
            sums = {oracle.tail_sum_of(inst, x, k, **declared) for x in space}
            if len({t for m, t in sums if m == known.optimum[0]}) > 1:
                seen.add("a tail decided by T at equal M")
            if result.tail_sum.summed_total_shortfall > oracle.t_bound(inst, inst.worlds,
                                                                       excluded=inst.excluded):
                seen.add("a summed T over a tail above T_bound")
    assert seen == {
        "a world discarded",
        "one XI in a level set",
        "several XIs in a level set",
        "a tail level set equal to the point BALANCE one",
        "a tail level set unlike the point BALANCE one",
        "a tail decided by T at equal M",
        "a summed T over a tail above T_bound",
    }
