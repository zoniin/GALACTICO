"""Reliability machinery, including a synthetic case with a known answer."""

from __future__ import annotations

import math

import numpy as np
import pytest

from galactico.domain import Grade
from galactico.reliability import (
    AxisReliability,
    reliability_report,
    shrink,
    spearman_brown,
    split_half_reliability,
)


def test_spearman_brown_lifts_a_half_length_correlation() -> None:
    assert spearman_brown(0.5) == pytest.approx(2 / 3)
    assert spearman_brown(0.0) == pytest.approx(0.0)
    assert spearman_brown(1.0) == pytest.approx(1.0)


def test_split_half_recovers_a_known_reliability() -> None:
    """Synthetic players carrying a true score plus independent per-half noise.

    Half-length correlation is var(true) / (var(true) + var(noise)) = 0.5, which
    Spearman-Brown lifts to 2/3 for the full-length measure. If the machinery is
    right it recovers that.
    """
    rng = np.random.default_rng(7)
    n = 4000
    true = rng.normal(size=n)
    first = {str(i): true[i] + rng.normal() for i in range(n)}
    second = {str(i): true[i] + rng.normal() for i in range(n)}

    r, used = split_half_reliability(first, second)
    assert used == n
    assert r == pytest.approx(2 / 3, abs=0.03)


def test_split_half_returns_nan_below_three_players() -> None:
    r, used = split_half_reliability({"a": 1.0}, {"a": 1.0})
    assert math.isnan(r)
    assert used == 1


def test_split_half_ignores_players_missing_from_either_half() -> None:
    rng = np.random.default_rng(11)
    true = {str(i): rng.normal() for i in range(50)}
    first = {k: v + rng.normal(scale=0.1) for k, v in true.items()}
    second = {k: v + rng.normal(scale=0.1) for k, v in list(true.items())[:30]}
    _, used = split_half_reliability(first, second)
    assert used == 30


def test_shrinkage_pulls_thin_samples_toward_the_prior() -> None:
    thin = shrink(observed=95.0, prior_mean=50.0, sample_size=340, stabilisation_point=900)
    thick = shrink(observed=95.0, prior_mean=50.0, sample_size=3000, stabilisation_point=900)
    assert 50.0 < thin < thick < 95.0
    assert thin == pytest.approx(50 + 45 * (340 / 1240))


def test_shrinkage_approaches_the_observation_with_abundant_data() -> None:
    assert shrink(95.0, 50.0, sample_size=10**9, stabilisation_point=900) == pytest.approx(
        95.0, rel=1e-5
    )


def test_shrinkage_rejects_a_nonsense_stabilisation_point() -> None:
    with pytest.raises(ValueError):
        shrink(1.0, 0.0, sample_size=100, stabilisation_point=0)


def test_report_names_the_axes_that_fail() -> None:
    axes = [
        AxisReliability("progression", 0.88, 1200, 900, "La Liga 2015/16"),
        AxisReliability("ball_retention", 0.63, 1200, 900, "La Liga 2015/16"),
        AxisReliability("finishing", 0.11, 1200, 900, "La Liga 2015/16"),
    ]
    text = reliability_report(axes)

    assert "finishing" in text.split("not shipped:")[1]
    assert axes[0].grade is Grade.NUMBER
    assert axes[1].grade is Grade.BAND
    assert axes[2].grade is Grade.INSUFFICIENT
    assert axes[2].optimizer_weight == 0.0


def test_an_unmeasured_axis_carries_no_optimiser_weight() -> None:
    unknown = AxisReliability("mystery", float("nan"), 0, 900, "n/a")
    assert unknown.grade is Grade.BAND
    assert unknown.optimizer_weight == 0.0


# --- the gate must not itself be a bare float ----------------------------

def test_reliability_carries_its_own_confidence_interval() -> None:
    thin = AxisReliability("switch_frequency", 0.71, 40, 900, "La Liga 2015/16")
    thick = AxisReliability("switch_frequency", 0.71, 1200, 900, "La Liga 2015/16")
    assert thin.interval is not None and thick.interval is not None
    assert (thin.interval[1] - thin.interval[0]) > (thick.interval[1] - thick.interval[0])


def test_a_thin_estimate_above_the_threshold_still_fails_the_gate() -> None:
    """r = 0.71 over forty players is not reliably above 0.70. Grading on the
    measured value alone would let it ship as a number.

    Note how conservative this is: r = 0.71 fails the gate even at n = 1200,
    because its lower bound is 0.686. Clearing 0.70 on the lower bound needs a
    measured r nearer 0.74 at that sample size. That is the intended behaviour —
    the gate defends the reliability we can support, not the one we happened to
    observe."""
    thin = AxisReliability("switch_frequency", 0.71, 40, 900, "La Liga 2015/16")
    borderline = AxisReliability("switch_frequency", 0.71, 1200, 900, "La Liga 2015/16")
    solid = AxisReliability("progression", 0.75, 1200, 900, "La Liga 2015/16")

    assert thin.lower_bound < borderline.lower_bound < 0.70 < solid.lower_bound
    assert thin.grade is Grade.BAND
    assert borderline.grade is Grade.BAND
    assert solid.grade is Grade.NUMBER


def test_interval_is_undefined_for_degenerate_inputs() -> None:
    assert AxisReliability("x", 1.0, 100, 900, "p").interval is None
    assert AxisReliability("x", 0.8, 3, 900, "p").interval is None
    assert AxisReliability("x", float("nan"), 100, 900, "p").interval is None


def test_the_report_shows_the_interval() -> None:
    text = reliability_report([AxisReliability("progression", 0.88, 1200, 900, "p")])
    assert "90% CI" in text and "0.87-0.89" in text


# --- no interval, no lower bound, no grade -------------------------------

def test_the_thinnest_sample_does_not_pass_the_gate_built_to_stop_it() -> None:
    """Three players give no Fisher-z interval. The lower bound then fell back to
    the measured r, so r = 0.95 on n = 3 graded NUMBER at weight 1.0, while the
    same r on n = 4, which has an interval, was withheld. Without an interval
    there is nothing to defend."""
    three = AxisReliability("x", 0.95, 3, 900, "p")
    four = AxisReliability("x", 0.95, 4, 900, "p")

    assert three.interval is None
    assert math.isnan(three.lower_bound)
    assert three.grade is Grade.INSUFFICIENT
    assert three.optimizer_weight == 0.0
    assert three.verdict == "does not ship; weight zero"

    assert four.interval is not None and four.lower_bound < 0.50
    assert four.grade is Grade.INSUFFICIENT
    assert four.optimizer_weight == 0.0


@pytest.mark.parametrize("r,n", [
    (0.95, 3), (0.95, 2), (0.95, 1), (0.95, 0),      # too few units for an interval
    (0.60, 3),                                        # would have been a band
    (1.0, 100), (1.0, 3), (1.5, 100),                 # |r| >= 1 is a duplicate or not a correlation
    (-1.0, 100), (0.30, 3),                           # already withheld; must stay withheld
])
def test_a_measured_reliability_without_an_interval_never_ships(r: float, n: int) -> None:
    axis = AxisReliability("x", r, n, 900, "p")
    assert axis.interval is None
    assert axis.grade is Grade.INSUFFICIENT
    assert axis.optimizer_weight == 0.0


def test_a_row_without_an_interval_is_reported_as_not_shipped() -> None:
    text = reliability_report([
        AxisReliability("solid", 0.88, 1200, 900, "p"),
        AxisReliability("three_teams", 0.95, 3, 900, "p"),
    ])
    row = next(line for line in text.splitlines() if line.startswith("three_teams"))
    assert "n/a" in row and "0.00" in row and "does not ship" in row
    assert "three_teams" in text.split("not shipped:")[1]
    assert "solid" not in text.split("not shipped:")[1]


def test_rows_that_have_an_interval_are_graded_exactly_as_before() -> None:
    """The repair is confined to rows with no interval. These are the published
    Stage 1 figures for Spain: r, n and interval as stored in
    experiments/stage1_axes.json."""
    progression = AxisReliability("progression", 0.887920510464265, 333, 900, "Spain 2017/18")
    chance = AxisReliability("chance_creation", 0.5999259707376644, 333, 900, "Spain 2017/18")

    assert progression.interval == pytest.approx(
        (0.8671478494608997, 0.9056093712637681), abs=1e-12)
    assert progression.lower_bound == pytest.approx(0.8671478494608997, abs=1e-12)
    assert progression.grade is Grade.NUMBER
    assert progression.optimizer_weight == 1.0

    assert chance.interval == pytest.approx(
        (0.5388156943619802, 0.6547554368343254), abs=1e-12)
    assert chance.grade is Grade.BAND
    assert chance.optimizer_weight == pytest.approx((0.5388156943619802 - 0.50) / 0.20, abs=1e-9)


# --- the interval level is stated, not assumed ---------------------------

@pytest.mark.parametrize("confidence", [0.99, 0.80, 0.5, 90, 95, 0.9000001, float("nan"), None])
def test_an_unsupported_confidence_level_is_refused(confidence: object) -> None:
    """Every value other than 0.90 was silently computed at 95%, so a requested
    99% interval came back narrower than asked for and was graded as if it were
    the real thing. The row is refused when it is built, so it cannot be printed
    either."""
    with pytest.raises(ValueError, match="confidence"):
        AxisReliability("x", 0.8, 100, 900, "p", confidence=confidence)


def test_the_interval_itself_refuses_a_level_it_cannot_state() -> None:
    """Belt and braces: the property does not trust the constructor to have run."""
    forced = AxisReliability("x", 0.8, 100, 900, "p")
    object.__setattr__(forced, "confidence", 0.99)
    with pytest.raises(ValueError, match="confidence"):
        _ = forced.interval
    with pytest.raises(ValueError, match="confidence"):
        _ = forced.grade


def test_the_two_supported_levels_keep_their_intervals() -> None:
    """Fisher z by hand: atanh(r) -+ crit / sqrt(n - 3), back through tanh."""
    z, se = math.atanh(0.8), 1.0 / math.sqrt(100 - 3)
    ninety = AxisReliability("x", 0.8, 100, 900, "p").interval
    ninety_five = AxisReliability("x", 0.8, 100, 900, "p", confidence=0.95).interval

    assert ninety == pytest.approx(
        (math.tanh(z - 1.6448536269514722 * se), math.tanh(z + 1.6448536269514722 * se)),
        abs=1e-12)
    assert ninety_five == pytest.approx(
        (math.tanh(z - 1.959963984540054 * se), math.tanh(z + 1.959963984540054 * se)),
        abs=1e-12)
    assert ninety_five[0] < ninety[0] < 0.8 < ninety[1] < ninety_five[1]
    assert AxisReliability("x", 0.8, 100, 900, "p", confidence=0.90).interval == ninety
