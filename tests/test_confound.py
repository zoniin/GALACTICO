"""Discriminant validity: the gate that reliability alone does not provide."""

from __future__ import annotations

import numpy as np
import pytest

from galactico.reliability import discriminant_validity, residualise


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
