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
