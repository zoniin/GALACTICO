"""Discriminant validity: the gate that reliability alone does not provide."""

from __future__ import annotations

import math
import warnings

import numpy as np
import pytest

from galactico.reliability import ConfoundVerdict, discriminant_validity, residualise
from galactico.reliability.confound import _spearman


def test_residualise_removes_a_linear_confound() -> None:
    rng = np.random.default_rng(0)
    touches = rng.gamma(shape=8.0, scale=10.0, size=800)
    metric = 3.0 * touches + rng.normal(scale=1.0, size=800)
    residuals = residualise(metric, touches.reshape(-1, 1))
    assert abs(np.corrcoef(residuals, touches)[0, 1]) < 1e-8
    assert np.var(residuals) < 0.02 * np.var(metric)


def test_a_confounded_metric_fails_all_three_checks() -> None:
    """The Metronome Fit case, reconstructed: a metric that is almost entirely
    touch volume. Reliable, plausible leaderboard, measuring the wrong thing."""
    rng = np.random.default_rng(1)
    n = 600
    touches = rng.gamma(shape=8.0, scale=10.0, size=n)
    metric = touches + rng.normal(scale=4.0, size=n)

    verdict = discriminant_validity(
        metric, touches.reshape(-1, 1), key="metronome_index",
        confound_names=("touch volume",),
    )
    assert not verdict.passed
    assert verdict.variance_explained_by_confounds > 0.9
    assert len(verdict.failures) == 3
    assert "FAILS" in verdict.report()


def test_a_genuine_construct_survives() -> None:
    """A metric with real signal orthogonal to the confound keeps its ordering."""
    rng = np.random.default_rng(2)
    n = 600
    touches = rng.gamma(shape=8.0, scale=10.0, size=n)
    skill = rng.normal(scale=30.0, size=n)
    metric = 0.3 * touches + skill

    verdict = discriminant_validity(
        metric, touches.reshape(-1, 1), key="progression",
        confound_names=("touch volume",),
    )
    assert verdict.passed
    assert verdict.variance_explained_by_confounds < 0.3
    assert verdict.rank_correlation_after > 0.8


def test_leaderboard_survival_degrades_with_confound_share() -> None:
    """The three checks are not independent for a linear confound — variance and
    leaderboard survival move together — but they degrade at different rates, so
    the thresholds bite at different points. The top-k check exists because the
    leaderboard is what a reader actually consumes."""
    rng = np.random.default_rng(5)
    n = 600
    touches = rng.gamma(shape=8.0, scale=10.0, size=n)
    skill = rng.normal(scale=25.0, size=n)

    survivals = []
    for share in (0.1, 0.5, 2.0):
        verdict = discriminant_validity(
            share * touches + skill, touches.reshape(-1, 1), key=f"share_{share}",
            confound_names=("touch volume",), top_k=12,
        )
        survivals.append(verdict.top_k_survival)

    assert survivals[0] > survivals[-1]
    assert survivals[0] > 0.8
    assert survivals[-1] < 0.5


def test_thresholds_are_explicit_and_overridable() -> None:
    """They must be set before running. Choosing them afterwards is how a passing
    experiment gets talked into a kill verdict."""
    rng = np.random.default_rng(3)
    confound = rng.normal(size=300)
    metric = confound * 0.8 + rng.normal(scale=0.6, size=300)

    lenient = discriminant_validity(metric, confound.reshape(-1, 1), key="m",
                                    max_variance_explained=0.95,
                                    min_rank_correlation=0.1,
                                    min_top_k_survival=0.1)
    strict = discriminant_validity(metric, confound.reshape(-1, 1), key="m",
                                   max_variance_explained=0.20,
                                   min_rank_correlation=0.99,
                                   min_top_k_survival=0.99)
    assert lenient.passed and not strict.passed


def test_report_names_the_confounds() -> None:
    rng = np.random.default_rng(4)
    x = rng.normal(size=(200, 2))
    y = x[:, 0] + rng.normal(scale=0.5, size=200)
    text = discriminant_validity(y, x, key="axis",
                                 confound_names=("touch volume", "team")).report()
    assert "touch volume, team" in text
    assert "n                        200" in text


# --- an undefined check is not a pass ------------------------------------

def a_verdict(**overrides: object) -> ConfoundVerdict:
    """A verdict that passes all three checks, unless a field is overridden."""
    fields: dict = {"key": "x", "variance_explained_by_confounds": 0.10,
                    "rank_correlation_after": 0.90, "top_k": 12, "top_k_survivors": 11,
                    "n": 50, **overrides}
    return ConfoundVerdict(**fields)


def test_a_verdict_made_of_nan_does_not_pass() -> None:
    """Each check asked "is it past the limit?", and NaN answers no to every
    comparison. A verdict with nothing measured in it therefore PASSED."""
    nan = float("nan")
    empty = a_verdict(variance_explained_by_confounds=nan, rank_correlation_after=nan)
    assert not empty.passed
    assert len(empty.failures) == 2
    assert all("undefined" in reason for reason in empty.failures)
    assert "FAILS" in empty.report()


@pytest.mark.parametrize("field,value", [
    ("variance_explained_by_confounds", float("nan")),
    ("variance_explained_by_confounds", float("-inf")),
    ("rank_correlation_after", float("nan")),
    ("rank_correlation_after", float("inf")),
    ("max_variance_explained", float("nan")),
    ("min_rank_correlation", float("nan")),
    ("min_top_k_survival", float("nan")),
])
def test_one_undefined_quantity_is_enough_to_fail(field: str, value: float) -> None:
    """A threshold that is NaN disables its check exactly as a NaN measurement
    does, so it is refused the same way."""
    verdict = a_verdict(**{field: value})
    assert not verdict.passed
    assert len(verdict.failures) == 1
    assert "undefined" in verdict.failures[0]


def test_no_leaderboard_is_not_a_surviving_leaderboard() -> None:
    verdict = a_verdict(top_k=0, top_k_survivors=0)
    assert math.isnan(verdict.top_k_survival)
    assert not verdict.passed
    assert "undefined" in verdict.failures[0]


def test_a_defined_verdict_reads_exactly_as_before() -> None:
    """The repair adds a refusal. It must not reword or move a defined result."""
    assert a_verdict().passed
    assert a_verdict().failures == ()
    failing = a_verdict(variance_explained_by_confounds=0.72, rank_correlation_after=0.31,
                        top_k_survivors=4)
    assert failing.failures == (
        "confounds explain 72% of variance (ceiling 60%)",
        "ordering collapses under adjustment, rho = 0.31 (floor 0.50)",
        "only 4/12 of the leaderboard survives (floor 50%)",
    )
    # A threshold set to infinity is a declared decision to switch a check off,
    # not an undefined one, and still behaves as it did.
    assert a_verdict(variance_explained_by_confounds=0.99,
                     max_variance_explained=float("inf")).passed


@pytest.mark.parametrize("confound", [
    np.zeros((60, 1)),
    np.arange(60.0).reshape(-1, 1),
    np.random.default_rng(0).normal(size=(60, 1)),
])
def test_a_constant_metric_cannot_pass_the_audit(confound: np.ndarray) -> None:
    """A metric that is the same for every player has no ordering to preserve.
    It used to keep "all" of it: R^2 0.0, rho 1.0, twelve of twelve, PASSES."""
    verdict = discriminant_validity(np.full(60, 3.0), confound, key="flat")
    assert math.isnan(verdict.rank_correlation_after)
    assert not verdict.passed
    assert any("undefined" in reason for reason in verdict.failures)


def test_a_missing_value_cannot_pass_the_audit() -> None:
    """One NaN in the metric makes every residual NaN. Sorted input then kept its
    own order on both sides: rho 1.0, twelve of twelve, R^2 NaN, PASSES. The
    function still does not mask for the caller; it no longer rewards forgetting."""
    metric = np.arange(50, dtype=float)
    metric[-1] = float("nan")
    confound = np.random.default_rng(7).normal(size=(50, 1))
    verdict = discriminant_validity(metric, confound, key="holey")
    assert math.isnan(verdict.rank_correlation_after)
    assert not verdict.passed
    assert len(verdict.failures) >= 2


def test_one_observation_cannot_pass_the_audit() -> None:
    """n = 1: nothing to regress, nothing to rank, one of one "survivors"."""
    verdict = discriminant_validity([1.0], np.array([[2.0]]), key="one")
    assert not verdict.passed


# --- rank correlation: undefined is NaN, tied values share a rank --------

RISING = np.arange(10, dtype=float)
FLAT = np.ones(10)


@pytest.mark.parametrize("ties", ["legacy", "average"])
def test_rank_correlation_with_a_constant_is_undefined(ties: str) -> None:
    """Sorting a constant still returns n distinct positions, so its "ranks" ran
    0..n-1 and it correlated +1.0 with anything rising, -1.0 with anything
    falling."""
    for a, b in ((FLAT, RISING), (FLAT, -RISING), (RISING, FLAT), (FLAT, FLAT)):
        assert math.isnan(_spearman(a, b, ties=ties))


@pytest.mark.parametrize("ties", ["legacy", "average"])
@pytest.mark.parametrize("hole", [float("nan"), float("inf"), float("-inf")])
def test_rank_correlation_with_a_non_finite_value_is_undefined(ties: str, hole: float) -> None:
    """NaN sorts last, so a missing value was ranked as the largest one."""
    a = np.array([1.0, hole, 3.0, 4.0, 5.0])
    b = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert math.isnan(_spearman(a, b, ties=ties))
    assert math.isnan(_spearman(b, a, ties=ties))


def test_tied_values_share_a_rank_worked_by_hand() -> None:
    """a = [1, 2, 2, 3] has ranks [1, 2.5, 2.5, 4]. b = [1, 3, 2, 4] has ranks
    [1, 3, 2, 4]. Centred on 2.5: [-1.5, 0, 0, 1.5] and [-1.5, 0.5, -0.5, 1.5].
    Cross product 4.5, sums of squares 4.5 and 5, so rho = 4.5 / sqrt(22.5),
    which is sqrt(0.9).

    The two tied observations are interchangeable, so handing them each other's
    partner cannot change the answer. Ranking ties in sort order gave 0.8 for one
    arrangement and 1.0 for the other."""
    a = np.array([1.0, 2.0, 2.0, 3.0])
    expected = math.sqrt(0.9)
    assert _spearman(a, np.array([1.0, 3.0, 2.0, 4.0]), ties="average") == pytest.approx(
        expected, abs=1e-12)
    assert _spearman(a, np.array([1.0, 2.0, 3.0, 4.0]), ties="average") == pytest.approx(
        expected, abs=1e-12)


def test_a_count_with_a_mass_at_zero_worked_by_hand() -> None:
    """[0, 0, 0, 1, 2] has ranks [2, 2, 2, 4, 5], centred [-1, -1, -1, 1, 2].
    Against 1..5, centred [-2, -1, 0, 1, 2]: cross product 8, sums of squares 8
    and 10, so rho = 8 / sqrt(80) = 2 / sqrt(5)."""
    counts = np.array([0.0, 0.0, 0.0, 1.0, 2.0])
    rho = _spearman(counts, np.array([1.0, 2.0, 3.0, 4.0, 5.0]), ties="average")
    assert rho == pytest.approx(2 / math.sqrt(5), abs=1e-12)


def test_ties_on_both_sides_worked_by_hand() -> None:
    """[1, 1, 2, 2] against [1, 2, 2, 3]: ranks [1.5, 1.5, 3.5, 3.5] and
    [1, 2.5, 2.5, 4], centred [-1, -1, 1, 1] and [-1.5, 0, 0, 1.5]. Cross product
    3, sums of squares 4 and 4.5, so rho = 3 / sqrt(18) = 1 / sqrt(2)."""
    rho = _spearman(np.array([1.0, 1.0, 2.0, 2.0]), np.array([1.0, 2.0, 2.0, 3.0]),
                    ties="average")
    assert rho == pytest.approx(1 / math.sqrt(2), abs=1e-12)


def test_average_ranks_do_not_depend_on_the_order_of_the_rows() -> None:
    """A statistic of the data cannot move when the same pairs arrive in another
    order. With ties ranked in sort order it did."""
    rng = np.random.default_rng(8)
    shots = rng.poisson(0.8, size=200).astype(float)
    other = shots + rng.normal(size=200)
    reference = _spearman(shots, other, ties="average")
    assert 0.0 < reference < 1.0
    for _ in range(25):
        order = rng.permutation(200)
        assert _spearman(shots[order], other[order], ties="average") == pytest.approx(
            reference, abs=1e-12)


def test_without_ties_both_policies_are_the_same_number() -> None:
    """No ties: rho = 1 - 6 * sum(d^2) / (n (n^2 - 1)). For [1..5] against
    [2, 1, 4, 3, 5] the squared rank differences sum to 4: 1 - 24/120 = 0.8.

    Equality between the two policies is exact, not approximate. It is the reason
    no published figure for a tie-free construct can move."""
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = np.array([2.0, 1.0, 4.0, 3.0, 5.0])
    assert _spearman(a, b, ties="average") == pytest.approx(0.8, abs=1e-12)

    rng = np.random.default_rng(9)
    with warnings.catch_warnings():
        warnings.simplefilter("error")          # no ties, so nothing to announce
        assert _spearman(a, b, ties="legacy") == _spearman(a, b, ties="average")
        for n in (3, 4, 17, 64, 333, 345):
            x, y = rng.normal(size=n), rng.normal(size=n)
            assert _spearman(x, y, ties="legacy") == _spearman(x, y, ties="average")


def test_the_published_tie_order_is_kept_for_the_record_and_says_so() -> None:
    """Averaging ties moves published figures: `chance_creation` has about sixty
    players at exactly zero in every league, and its ordering rho shifts in the
    third decimal. The owner decided in October 2026: average ranks are the
    default, the published reports stay as they are, and M-07 is the erratum.
    The sort-order ranks remain behind `ties="legacy"` to reproduce the record,
    and using them on tied data is announced rather than silent."""
    a = np.array([1.0, 2.0, 2.0, 3.0])
    b = np.array([1.0, 3.0, 2.0, 4.0])
    with pytest.warns(RuntimeWarning, match="tied"):
        legacy = _spearman(a, b, ties="legacy")
    # Whichever of the two tied rows the sort put first: 0.8 or 1.0, never sqrt(0.9).
    assert legacy == pytest.approx(0.8, abs=1e-12) or legacy == pytest.approx(1.0, abs=1e-12)
    with warnings.catch_warnings():
        warnings.simplefilter("error")          # the default has nothing to announce
        assert _spearman(a, b) == pytest.approx(math.sqrt(0.9), abs=1e-12)


def test_an_unknown_tie_policy_is_refused() -> None:
    with pytest.raises(ValueError, match="tie policy"):
        _spearman(RISING, RISING, ties="first")
    with pytest.raises(ValueError, match="tie policy"):
        discriminant_validity(RISING, RISING.reshape(-1, 1) ** 2, key="k", ties="first")


def test_the_audit_takes_a_declared_tie_policy() -> None:
    """A count-valued candidate gets an ordering figure that is a property of its
    data, declared or not. Asked for the sort-order ranks, it is told."""
    rng = np.random.default_rng(10)
    shots = rng.poisson(0.7, size=300).astype(float)
    confound = rng.normal(size=(300, 1))

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        declared = discriminant_validity(shots, confound, key="shots", ties="average")
        order = rng.permutation(300)
        reordered = discriminant_validity(shots[order], confound[order], key="shots",
                                          ties="average")
        undeclared = discriminant_validity(shots, confound, key="shots")
    assert reordered.rank_correlation_after == pytest.approx(
        declared.rank_correlation_after, abs=1e-12)
    assert undeclared.rank_correlation_after == declared.rank_correlation_after

    with pytest.warns(RuntimeWarning, match="tied"):
        discriminant_validity(shots, confound, key="shots", ties="legacy")


# --- the leaderboard count: a tie across the last place is not a count ----

# Eight players, a leaderboard of three. The third and fourth largest values are both 7,
# and so is the fifth: three rows have the same claim on the last place.
TIED_METRIC = np.array([9.0, 8.0, 7.0, 7.0, 7.0, 3.0, 2.0, 1.0])
TIED_CONFOUND = np.array([1.0, 5.0, 2.0, 8.0, 3.0, 7.0, 4.0, 6.0]).reshape(-1, 1)


def test_a_tie_across_the_last_place_leaves_no_leaderboard_to_count() -> None:
    """Which of three equal rows a sort puts in the top three depends on the order they
    arrive in. The count of survivors is then not a number, and the check says so."""
    verdict = discriminant_validity(TIED_METRIC, TIED_CONFOUND, key="tied", top_k=3)
    assert verdict.top_k == 3
    assert verdict.top_k_survivors is None
    assert (verdict.top_k_tied_raw, verdict.top_k_tied_adjusted) == (3, 0)
    assert math.isnan(verdict.top_k_survival)
    assert not verdict.passed
    assert ("leaderboard survival is undefined: 3 rows share the value at place 3 of the raw "
            "metric, so the top 3 is not a set of rows (floor 0.5); undefined is not a pass"
            ) in verdict.failures
    assert "top-3 survivors        no count" in verdict.report()

    rng = np.random.default_rng(11)
    for _ in range(50):
        order = rng.permutation(TIED_METRIC.size)
        moved = discriminant_validity(TIED_METRIC[order], TIED_CONFOUND[order], key="tied",
                                      top_k=3)
        assert moved.top_k_survivors is None and moved.top_k_tied_raw == 3


def test_a_leaderboard_is_counted_when_its_last_place_is_decided() -> None:
    """With a leaderboard of four the three sevens still straddle the last place. With
    five they all fit (9, 8, 7, 7, 7), and with two none of them is in question."""
    for top_k, tied in ((4, 3), (5, 0), (2, 0)):
        verdict = discriminant_validity(TIED_METRIC, TIED_CONFOUND, key="tied", top_k=top_k)
        assert verdict.top_k_tied_raw == tied
        assert (verdict.top_k_survivors is None) == bool(tied)


def test_a_tie_on_the_adjusted_side_is_counted_too() -> None:
    """Two rows identical in metric and confound have identical residuals. Here they are
    the fourth and fifth largest raw values and the third and fourth largest residuals,
    so a leaderboard of three is defined before the adjustment and not after it."""
    metric = np.array([10.0, 6.0, 6.0, 5.0, 4.0, 1.0, 8.0, 3.0, 7.0, 2.0])
    confound = np.array([9.0, 1.0, 1.0, 5.0, 8.0, 7.0, 6.0, 2.0, 9.0, 0.0]).reshape(-1, 1)
    adjusted = residualise(metric, confound)
    assert adjusted[1] == adjusted[2] and (adjusted > adjusted[1]).sum() == 2
    assert (metric > metric[1]).sum() == 3

    verdict = discriminant_validity(metric, confound, key="twins", top_k=3)
    assert verdict.top_k_survivors is None
    assert (verdict.top_k_tied_raw, verdict.top_k_tied_adjusted) == (0, 2)
    assert any("2 rows share the value at place 3 of the adjusted metric, so the top 3 is "
               "not a set of rows" in reason for reason in verdict.failures)


def test_when_every_row_is_in_the_leaderboard_a_tie_decides_nothing() -> None:
    """Four players and a leaderboard of twelve: all four are in it on both sides."""
    verdict = discriminant_validity(np.array([1.0, 1.0, 1.0, 2.0]),
                                    np.array([[0.0], [1.0], [3.0], [2.0]]), key="few")
    assert (verdict.top_k, verdict.top_k_survivors) == (4, 4)
    assert (verdict.top_k_tied_raw, verdict.top_k_tied_adjusted) == (0, 0)


def test_the_undefined_count_is_said_in_words() -> None:
    both = a_verdict(top_k_survivors=None, top_k_tied_raw=45, top_k_tied_adjusted=3)
    assert both.failures == (
        "leaderboard survival is undefined: 45 rows share the value at place 12 of the raw "
        "metric and 3 rows share the value at place 12 of the adjusted metric, so the top 12 "
        "is not a set of rows (floor 0.5); undefined is not a pass",)
    # No count and no tie recorded: the sentence claims no reason it was not given.
    bare = a_verdict(top_k_survivors=None)
    assert bare.failures == (
        "leaderboard survival is undefined (no count out of 12, floor 0.5); "
        "undefined is not a pass",)
    assert math.isnan(bare.top_k_survival) and not bare.passed


def test_a_value_that_is_not_finite_leaves_no_leaderboard_to_count() -> None:
    """NaN sorts last, so a missing value was placed at the head of the leaderboard, and
    rows that are all NaN after adjustment entered it by row position."""
    metric = np.arange(50, dtype=float)
    metric[7] = float("nan")
    confound = np.random.default_rng(7).normal(size=(50, 1))
    verdict = discriminant_validity(metric, confound, key="holey")
    assert verdict.top_k_survivors is None
    assert any(reason.startswith("leaderboard survival is undefined (no count out of 12")
               for reason in verdict.failures)


def test_the_record_policy_counts_the_leaderboard_as_it_always_did() -> None:
    """ties="legacy" reproduces the record: the count is taken from the sort, whatever the
    sort did with the tie, and the policy announces itself."""
    with pytest.warns(RuntimeWarning, match="tied"):
        verdict = discriminant_validity(TIED_METRIC, TIED_CONFOUND, key="tied", top_k=3,
                                        ties="legacy")
    assert isinstance(verdict.top_k_survivors, int)
    assert (verdict.top_k_tied_raw, verdict.top_k_tied_adjusted) == (0, 0)
    assert not any("is not a set of rows" in reason for reason in verdict.failures)

    holey = np.arange(50, dtype=float)
    holey[7] = float("nan")
    legacy = discriminant_validity(holey, np.random.default_rng(7).normal(size=(50, 1)),
                                   key="holey", ties="legacy")
    assert isinstance(legacy.top_k_survivors, int)
