import numpy as np
import pandas as pd
import pytest

from galactico.validation.forecast_evaluation import (
    BASELINES,
    FrozenForecasts,
    design,
    evaluate_period,
    fit_forecasts,
    joint_verdict,
    paired_week_interval,
)


def rows(n=80):
    rng = np.random.default_rng(321)
    frame = pd.DataFrame({name: rng.uniform(0.1, 1, n) for name in BASELINES})
    frame["home"] = np.arange(n) % 2
    frame["target"] = 0.2 + frame.team_mean * 0.3 + frame.opponent_mean * 0.4 + frame.home * 0.1
    frame["target"] += 0.5 * (frame.lineup_sum - frame.team_mean)
    frame["date"] = pd.date_range("2018-03-01", periods=n, freq="D")
    frame["game_id"] = np.arange(n)
    frame["team_id"] = np.arange(n) % 5
    return frame


def test_added_information_is_exactly_one_column_not_a_different_context():
    data = rows()
    np.testing.assert_array_equal(
        design(data, augmented=False), design(data, augmented=True)[:, :4]
    )
    fits = fit_forecasts(data)
    np.testing.assert_allclose(fits.augmented, [0.2, 0.3, 0.4, 0.1, 0.5], atol=1e-12)
    config = dict(
        bootstrap_replicates=200,
        seed=5,
        interval_quantiles=[0.025, 0.975],
        minimum_test_rows=50,
        minimum_test_weeks=8,
    )
    result = evaluate_period(rows(), fits, config)
    assert result["metrics"]["context_plus_lineup"]["mse"] < 1e-25
    assert result["paired_mse_difference"] < 0
    assert result["status"] == "INCREMENTAL_PREDICTION"


def test_evaluation_cannot_refit_frozen_coefficients_to_test_outcomes():
    data = rows()
    fits = fit_forecasts(data)
    coefficients = fits.to_dict()
    data["target"] = 1000
    config = dict(
        bootstrap_replicates=100,
        seed=5,
        interval_quantiles=[0.025, 0.975],
        minimum_test_rows=50,
        minimum_test_weeks=8,
    )
    result = evaluate_period(data, fits, config)
    assert fits.to_dict() == coefficients
    assert result["metrics"]["context_plus_lineup"]["mean_prediction"] < 2


def test_week_draw_keeps_correlated_fixture_sides_and_is_order_invariant():
    data = pd.DataFrame({"date": ["2018-03-01", "2018-03-01", "2018-03-08", "2018-03-08"]})
    differences = np.array([100, -100, 200, -200])
    interval = paired_week_interval(data, differences, replicates=100, seed=3)
    assert interval == (0.0, 0.0)
    order = [3, 0, 2, 1]
    assert (
        paired_week_interval(data.iloc[order], differences[order], replicates=100, seed=3)
        == interval
    )


def test_rank_floor_missing_values_and_declared_joint_rule():
    with pytest.raises(ValueError, match="insufficient development rows"):
        fit_forecasts(rows(10))
    data = rows()
    data["lineup_sum"] = data.team_mean
    with pytest.raises(ValueError, match="rank"):
        fit_forecasts(data)
    data.loc[0, "opponent_mean"] = np.nan
    with pytest.raises(ValueError, match="finite"):
        fit_forecasts(data)
    assert (
        joint_verdict(
            {
                "Spain": {"status": "INCREMENTAL_PREDICTION"},
                "England": {"status": "NOT_ESTABLISHED"},
            }
        )
        == "NOT_ESTABLISHED"
    )
    assert (
        joint_verdict(
            {"Spain": {"status": "INCONCLUSIVE"}, "England": {"status": "INCREMENTAL_PREDICTION"}}
        )
        == "INCONCLUSIVE"
    )


def test_clipping_and_primary_squared_loss_are_explicit():
    data = rows()
    data["target"] = 2
    fits = FrozenForecasts((-1, 0, 0, 0), (-1, 0, 0, 0, 0), 80, 4, 5)
    config = dict(
        bootstrap_replicates=100,
        seed=5,
        interval_quantiles=[0.025, 0.975],
        minimum_test_rows=50,
        minimum_test_weeks=8,
    )
    result = evaluate_period(data, fits, config)
    assert result["negative_forecasts_clipped"]["context"] == 80
    assert result["metrics"]["context"]["mse"] == 4
    assert result["metrics"]["context"]["mae"] == 2
    assert result["paired_mse_difference"] == 0
    assert result["status"] == "NOT_ESTABLISHED"
