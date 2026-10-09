"""Tied values share a rank. Sort order is not a property of the data.

The confound audit ranked with ``argsort(argsort(.))``, which hands tied values
distinct ranks in whatever order the sort leaves them. The published ordering
figures therefore depended on the order of the rows. Average ranks are the
definition now; the sort-order ranks stay available to reproduce the record.
See docs/research/M-07-rank-ties.md.
"""

from __future__ import annotations

import inspect
import json
import math
import warnings
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from galactico.reliability import discriminant_validity
from galactico.reliability.confound import _spearman

# Four rows, two of them tied on the metric. SWAPPED is the same four pairs with
# the two tied rows handed over in the other order.
METRIC = np.array([1.0, 2.0, 2.0, 3.0])
OTHER = np.array([1.0, 3.0, 2.0, 4.0])
SWAPPED = np.array([1.0, 2.0, 3.0, 4.0])


def by_definition(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman written from the definition, sharing no code with the module.

    The rank of a value is the number of values below it, plus the middle of the
    block of values equal to it. Quadratic, and obviously right.
    """
    def ranks(values: np.ndarray) -> np.ndarray:
        below = (values[None, :] < values[:, None]).sum(axis=1)
        equal = (values[None, :] == values[:, None]).sum(axis=1)
        return below + (equal + 1) / 2.0

    ra, rb = ranks(np.asarray(a, dtype=float)), ranks(np.asarray(b, dtype=float))
    ra, rb = ra - ra.mean(), rb - rb.mean()
    return float((ra * rb).sum() / math.sqrt((ra * ra).sum() * (rb * rb).sum()))


def zero_heavy(seed: int, n: int = 345, zeros: int = 60) -> tuple[np.ndarray, np.ndarray]:
    """The shape of chance creation: a block at exactly zero, the rest continuous."""
    rng = np.random.default_rng(seed)
    metric = np.r_[np.zeros(zeros), rng.gamma(2.0, 0.01, size=n - zeros)]
    other = metric + rng.normal(scale=0.01, size=n)
    order = rng.permutation(n)
    return metric[order], other[order]


# --- the defect ----------------------------------------------------------

def test_sort_order_ranks_answer_differently_for_the_same_rows_in_another_order() -> None:
    """One data set, two answers. That is the defect, pinned so that the policy
    kept for the record cannot be mistaken for a statistic."""
    with pytest.warns(RuntimeWarning, match="tied"):
        one = _spearman(METRIC, OTHER, ties="legacy")
    with pytest.warns(RuntimeWarning, match="tied"):
        other = _spearman(METRIC, SWAPPED, ties="legacy")
    assert one == pytest.approx(0.8, abs=1e-12)
    assert other == pytest.approx(1.0, abs=1e-12)

    metric, against = zero_heavy(0)
    rng = np.random.default_rng(1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        seen = set()
        for _ in range(20):
            order = rng.permutation(metric.size)
            seen.add(_spearman(metric[order], against[order], ties="legacy"))
    assert max(seen) - min(seen) > 1e-3


def test_average_ranks_answer_once() -> None:
    expected = math.sqrt(0.9)
    assert _spearman(METRIC, OTHER, ties="average") == pytest.approx(expected, abs=1e-12)
    assert _spearman(METRIC, SWAPPED, ties="average") == pytest.approx(expected, abs=1e-12)

    metric, against = zero_heavy(0)
    reference = _spearman(metric, against, ties="average")
    rng = np.random.default_rng(1)
    for _ in range(20):
        order = rng.permutation(metric.size)
        assert _spearman(metric[order], against[order], ties="average") == pytest.approx(
            reference, abs=1e-12)


# --- the definition ------------------------------------------------------

CASES = [
    (METRIC, OTHER),
    (METRIC, SWAPPED),
    (np.array([0.0, 0.0, 0.0, 1.0, 2.0]), np.array([1.0, 2.0, 3.0, 4.0, 5.0])),
    (np.array([1.0, 1.0, 2.0, 2.0]), np.array([1.0, 2.0, 2.0, 3.0])),
    zero_heavy(2),
    zero_heavy(3, n=290, zeros=75),
    tuple(np.random.default_rng(4).poisson(0.8, size=(2, 200)).astype(float)),
    tuple(np.random.default_rng(5).normal(size=(2, 333))),
]


@pytest.mark.parametrize("a,b", CASES)
def test_average_ranks_are_spearman_as_defined(a: np.ndarray, b: np.ndarray) -> None:
    """Against the definition written out above, and against pandas, whose ranks
    average ties and which is installed wherever this suite runs."""
    rho = _spearman(a, b, ties="average")
    assert rho == pytest.approx(by_definition(a, b), abs=1e-12)
    assert rho == pytest.approx(pd.Series(a).rank().corr(pd.Series(b).rank()), abs=1e-12)


@pytest.mark.parametrize("a,b", CASES)
def test_average_ranks_agree_with_scipy_where_it_is_installed(a, b) -> None:
    """scipy is not a dependency, so the check job skips this one. The test above
    is the guard that always runs; this is a second opinion on a laptop."""
    stats = pytest.importorskip("scipy.stats")
    assert _spearman(a, b, ties="average") == pytest.approx(
        stats.spearmanr(a, b).statistic, abs=1e-12)


# --- the default ---------------------------------------------------------

def test_average_ranks_are_the_default() -> None:
    """Undeclared means average, silently: there is nothing to announce about a
    statistic that is a property of the data."""
    for function in (_spearman, discriminant_validity):
        assert inspect.signature(function).parameters["ties"].default == "average"

    expected = math.sqrt(0.9)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert _spearman(METRIC, OTHER) == pytest.approx(expected, abs=1e-12)
        assert _spearman(METRIC, SWAPPED) == pytest.approx(expected, abs=1e-12)

        metric, against = zero_heavy(6)
        confound = against.reshape(-1, 1)
        undeclared = discriminant_validity(metric, confound, key="zero_heavy")
    declared = discriminant_validity(metric, confound, key="zero_heavy", ties="average")
    assert undeclared.rank_correlation_after == declared.rank_correlation_after


def test_the_audit_does_not_move_when_the_rows_do() -> None:
    metric, against = zero_heavy(7)
    confound = against.reshape(-1, 1)
    reference = discriminant_validity(metric, confound, key="k").rank_correlation_after
    rng = np.random.default_rng(8)
    for _ in range(10):
        order = rng.permutation(metric.size)
        moved = discriminant_validity(metric[order], confound[order], key="k")
        assert moved.rank_correlation_after == pytest.approx(reference, abs=1e-12)


def test_the_record_policy_is_still_there_and_still_warns() -> None:
    """Kept for one purpose: recomputing a figure published before the correction.
    It announces itself every time it meets tied data."""
    with pytest.warns(RuntimeWarning, match="depends on the order of the rows"):
        legacy = _spearman(METRIC, OTHER, ties="legacy")
    assert legacy != pytest.approx(math.sqrt(0.9), abs=1e-6)

    metric, against = zero_heavy(9)
    with pytest.warns(RuntimeWarning, match="60 tied values"):
        discriminant_validity(metric, against.reshape(-1, 1), key="k", ties="legacy")


def test_without_ties_the_two_policies_are_one_number() -> None:
    """Exact equality. It is why a figure for a tie-free construct did not move."""
    rng = np.random.default_rng(10)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for n in (3, 17, 290, 345):
            a, b = rng.normal(size=n), rng.normal(size=n)
            assert _spearman(a, b, ties="legacy") == _spearman(a, b, ties="average")


# --- the erratum: docs/research/M-07-rank-ties.md -------------------------
#
# Every published ordering figure that has a tied value, as the note prints it:
# (construct, league, tied players, published, corrected, difference). A figure
# not listed has no tied value and is the same number under both policies.

ROOT = Path(__file__).resolve().parents[1]
NOTE = ROOT / "docs/research/M-07-rank-ties.md"
LEAGUE = {"ESP": "Spain", "ENG": "England", "ITA": "Italy", "GER": "Germany", "FRA": "France"}

STAGE_1B = [
    ("chance_creation", "ESP", 64, 0.868563, 0.871168, +0.002604),
    ("chance_creation", "ENG", 65, 0.906808, 0.908954, +0.002146),
    ("chance_creation", "ITA", 65, 0.889226, 0.891736, +0.002510),
    ("chance_creation", "GER", 60, 0.888765, 0.893134, +0.004369),
    ("chance_creation", "FRA", 61, 0.889558, 0.889365, -0.000193),
    ("half_space_share", "ESP", 2, 0.973775, 0.973773, -0.000002),
    ("half_space_share", "FRA", 2, 0.960543, 0.960553, +0.000010),
    ("width", "GER", 2, 0.989539, 0.989550, +0.000011),
]
STAGE_1C_WYSCOUT = [
    ("chance_creation", "ESP", 64, 0.899189, 0.901755, +0.002567),
    ("chance_creation", "ENG", 65, 0.925167, 0.929447, +0.004281),
    ("chance_creation", "ITA", 65, 0.908403, 0.910831, +0.002428),
    ("chance_creation", "FRA", 61, 0.908562, 0.909104, +0.000542),
    ("half_space_share", "ESP", 6, 0.971112, 0.971110, -0.000001),
    ("half_space_share", "ENG", 8, 0.942470, 0.942469, -0.000001),
    ("half_space_share", "FRA", 2, 0.935407, 0.935415, +0.000008),
    ("width", "ENG", 5, 0.984156, 0.984149, -0.000007),
    ("width", "ITA", 2, 0.990689, 0.990693, +0.000004),
]
E02_T3 = 0.594833505570755
ORDERING_FLOOR = 0.50


def committed(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_the_note_prints_every_figure_that_moved() -> None:
    note = NOTE.read_text(encoding="utf-8")
    for construct, league, tied, published, corrected, difference in STAGE_1B + STAGE_1C_WYSCOUT:
        row = (f"| `{construct}` | {league} | {tied} | {published:.6f} | {corrected:.6f} "
               f"| {difference:+.6f} |")
        assert row in note, row
        assert abs((corrected - published) - difference) < 1.5e-6, row
    largest = max(abs(row[5]) for row in STAGE_1B + STAGE_1C_WYSCOUT)
    assert f"**{largest:.6f}**" in note
    assert repr(E02_T3) in note


def test_the_published_column_is_the_committed_record() -> None:
    """The erratum corrects the figures that were published, not figures like
    them. The records themselves are not rewritten: the old value is still what
    the result files hold."""
    stage_1b = {(row["axis"], row["league"]): row["rho"]
                for row in committed("experiments/replication.json")}
    stage_1 = {row["axis"]: row["rho"] for row in committed("experiments/stage1_axes.json")}
    stage_1c = committed("experiments/external_replication.json")

    for construct, league, _, published, _, _ in STAGE_1B:
        recorded = stage_1b[(construct, LEAGUE[league])]
        assert f"{recorded:.6f}" == f"{published:.6f}", (construct, league)
        if league == "ESP":
            assert stage_1[construct] == recorded       # Stage 1 is Spain's row of Stage 1B
    for construct, league, _, published, _, _ in STAGE_1C_WYSCOUT:
        recorded = stage_1c[f"WY_{league}"][construct]["rho"]
        assert f"{recorded:.6f}" == f"{published:.6f}", (construct, league)

    t3 = committed("experiments/preregistered/E-02-metronome-confirmatory/results.json")
    assert t3["tests"]["T3_ordering_rho"] == {"value": E02_T3, "passed": True}
    assert t3["decision"] == "RESEARCH_ONLY"


def test_no_published_figure_is_near_the_floor_it_would_be_judged_against() -> None:
    """The audit fails an ordering below 0.50, and E-02 froze the same floor. The
    largest correction is 0.0044. No committed figure is within reach of it."""
    stage_1b = [row["rho"] for row in committed("experiments/replication.json")]
    wyscout = [cell["rho"]
               for label, block in committed("experiments/external_replication.json").items()
               if label.startswith("WY_") for cell in block.values()]
    largest = max(abs(row[5]) for row in STAGE_1B + STAGE_1C_WYSCOUT)
    assert len(stage_1b) == 35 and len(wyscout) == 20
    assert largest < 0.005
    assert min(*stage_1b, *wyscout, E02_T3) - largest > ORDERING_FLOOR


@pytest.fixture(scope="module")
def recomputed(corpus_root, league_available):
    """Every public figure of the note, from the corpus. About a minute."""
    for league in LEAGUE.values():
        league_available(league)
    from experiments import run_rank_tie_erratum as erratum

    _, stage_1b, statuses, _ = erratum.stage_1b()
    return SimpleNamespace(stage_1b=stage_1b, statuses=statuses,
                           stage_1c=erratum.stage_1c_wyscout(), t3=erratum.e02())


def assert_cells_match(cells: list, pinned: list) -> None:
    expected = {(construct, league): (tied, corrected)
                for construct, league, tied, _, corrected, _ in pinned}
    assert {(c.construct, c.league) for c in cells if c.tied} == set(expected)
    for cell in cells:
        assert cell.passed_average == cell.passed_legacy
        assert not cell.leaderboard_boundary_tied
        if cell.tied:
            tied, corrected = expected[(cell.construct, cell.league)]
            assert cell.tied == tied
            assert cell.average == pytest.approx(corrected, abs=2e-6)
        else:
            # No tie, so nothing to correct: the committed figure stands as it is.
            assert cell.average == cell.legacy
            assert cell.average == pytest.approx(cell.published, abs=1e-9)


@pytest.mark.slow
def test_the_corrected_column_is_recomputed_from_the_corpus(recomputed) -> None:
    """Asserted on the corrected figures only. Which ranks an unstable sort hands
    to tied values is not promised from one machine to the next, so the old
    figures are checked against the committed record above and not recomputed
    here."""
    assert len(recomputed.stage_1b) == 35 and len(recomputed.stage_1c) == 20
    assert_cells_match(recomputed.stage_1b, STAGE_1B)
    assert_cells_match(recomputed.stage_1c, STAGE_1C_WYSCOUT)


@pytest.mark.slow
def test_no_status_or_gate_changes_under_the_corrected_default(recomputed) -> None:
    statuses = recomputed.statuses
    assert len(statuses["committed"]) == 35
    assert statuses["recomputed"] == statuses["committed"]
    assert statuses["replication"] == {
        "progression": "replicated", "progression_per_action": "replicated",
        "half_space_share": "replicated", "width": "replicated",
        "chance_creation": "partial", "ball_retention": "failed", "verticality": "failed",
    }

    t3 = recomputed.t3
    assert t3["tied"] == 0 and t3["floor"] == ORDERING_FLOOR
    assert t3["average"] == t3["legacy"]
    assert t3["average"] == pytest.approx(E02_T3, abs=1e-9)
    assert t3["average"] >= t3["floor"]


@pytest.mark.slow
def test_the_statsbomb_half_is_compared_with_the_local_record_only() -> None:
    """The StatsBomb-side figures of Stage 1C as published are not in the repository.
    Where the local cache and the local record of the run exist, the sort-order policy
    reproduces every one of them. Elsewhere there is nothing to compare and this skips."""
    from experiments import run_external_replication as runner
    from experiments import run_rank_tie_erratum as erratum

    assert "SB_" not in "".join(committed("experiments/external_replication.json"))
    cells = erratum.stage_1c_statsbomb() if (ROOT / runner.LOCAL_RECORD).exists() else None
    if cells is None:
        pytest.skip("the local StatsBomb cache or the local record of the run is not present")
    assert len(cells) == 20 and all(cell.published is not None for cell in cells)
    assert all(cell.reproduced for cell in cells)
    assert not any(cell.passed_legacy != cell.passed_average for cell in cells)
