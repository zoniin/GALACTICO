"""Synthetic oracles for E-08; no historical forecast outcomes are evaluated here."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from galactico.validation.partial_evaluation import (
    BASE_COLUMNS,
    evaluate_selection,
    evaluate_study,
    fit_selection,
)


@pytest.fixture
def config():
    path = Path(__file__).parents[1] / "experiments/preregistered/E-08-partial-history/config.json"
    configuration = json.loads(path.read_text())
    return {**configuration, "bootstrap_replicates": 50, "permutation_seeds": [0, 1]}


def panel(seed=17, *, context_target=False):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2017-11-01", "2018-05-31").repeat(2)
    count = len(dates)
    frame = pd.DataFrame(
        {
            "date": dates,
            "game_id": np.repeat(np.arange(count // 2), 2),
            "team_id": np.tile([1, 2], count // 2),
            "home": np.tile([True, False], count // 2),
        }
    )
    for name in ("team_mean", "team_recent", "opponent_mean", "role_sum", "mean_log1p_count"):
        frame[name] = rng.uniform(0.1, 1, count)
    frame["unseen_fraction"] = rng.choice([0, 0.1, 0.2], count)
    for k in (0, 1, 3, 10, 30):
        frame[f"residual_{k}"] = rng.normal(0, 0.1, count)
        for placebo in (0, 1):
            frame[f"perm_{placebo}_residual_{k}"] = rng.normal(0, 0.1, count)
    frame["target"] = 1 + 0.2 * frame.team_mean + 0.4 * frame.opponent_mean + 0.1 * frame.home
    if not context_target:
        frame["target"] += frame.residual_3
    frame["operational_sum"] = frame.team_mean
    frame["operational_available"] = True
    return frame


def holdout(rows):
    return rows[rows.date >= "2018-03-01"]


def test_forward_selection_and_future_poisoning(config):
    rows = panel()
    fit = fit_selection(rows, config)
    assert fit.report["selected_k"] == 3
    assert fit.report["status"] == "FITTED"
    poisoned = rows.copy()
    later = poisoned.date >= config["test_start"]
    poisoned.loc[later, ["target", "residual_3", "mean_log1p_count"]] = 100000
    assert fit.to_dict() == fit_selection(poisoned, config).to_dict()
    assert fit.to_dict() == fit_selection(rows.sample(frac=1, random_state=2), config).to_dict()
    result = evaluate_selection(holdout(rows), fit, config)
    assert result["metrics"]["selected"]["mse"] < 1e-20
    assert result["paired_mse_difference"] < 0


def test_context_only_tie_is_grid_order_invariant_and_exact(config):
    rows = panel(context_target=True)
    fit = fit_selection(rows, config)
    reversed_config = {**config, "pooling_grid": list(reversed(config["pooling_grid"]))}
    assert fit.report["selected_k"] == "context_only"
    assert fit.to_dict() == fit_selection(rows, reversed_config).to_dict()
    assert fit.selected is fit.baseline
    result = evaluate_selection(holdout(rows), fit, config)
    assert result["metrics"]["selected"] == result["metrics"]["strong_baseline"]
    assert result["paired_mse_difference"] == 0
    assert result["week_resampling_interval"] == (0, 0)


def test_training_constant_drop_is_frozen_and_shared(config):
    rows = panel()
    rows["unseen_fraction"] = 0.0
    rows.loc[rows.date >= "2018-03-01", "unseen_fraction"] = 0.9
    fit = fit_selection(rows, config)
    assert fit.baseline.dropped_columns == ("unseen_fraction",)
    assert "unseen_fraction" not in fit.selected.columns
    assert fit.selected.columns[:-1] == fit.baseline.columns
    assert fit.selected.dropped_columns == fit.baseline.dropped_columns
    assert "intercept" in fit.baseline.columns
    assert fit.baseline.columns == tuple(c for c in BASE_COLUMNS if c != "unseen_fraction")
    assert evaluate_selection(holdout(rows), fit, config)["metrics"]["selected"]["mse"] < 1e-20


def test_baseline_rank_failure_and_fold_floors_preserve_raw_errors(config):
    rows = panel()
    rows["team_recent"] = rows.team_mean * 2
    fit = fit_selection(rows, config)
    assert fit.report["status"] == "INCONCLUSIVE"
    assert "insufficient training design rank" in fit.report["reasons"]
    result = evaluate_selection(holdout(rows), fit, config)
    assert result["metrics"]["regularized_3"]["mse"] is not None
    assert "selected" not in result["metrics"]
    tiny = fit_selection(panel(), {**config, "minimum_training_rows": 1000})
    assert tiny.selected is None
    assert len(tiny.report["folds"]) == 2
    assert all(not candidate["eligible"] for candidate in tiny.report["candidates"].values())


def test_dependent_residual_invalidates_only_that_candidate(config):
    rows = panel()
    rows["residual_30"] = rows.team_mean + rows.role_sum
    fit = fit_selection(rows, config)
    assert fit.report["selected_k"] == 3
    assert not fit.report["candidates"]["30"]["eligible"]
    assert fit.report["candidates"]["30"]["pooled_validation_mse"] is None


def test_global_residual_scaling_is_ols_invariant_and_larger_k_wins_tie(config):
    rows = panel()
    residual = rows.residual_3.copy()
    for k in (0, 1, 3, 10, 30):
        rows[f"residual_{k}"] = residual / (k + 1)
    fit = fit_selection(rows, config)
    assert fit.report["selected_k"] == 30
    for candidate in fit.report["candidates"].values():
        if candidate is not fit.report["candidates"]["context_only"]:
            assert candidate["pooled_validation_mse"] < 1e-20
    one = fit_selection(rows, {**config, "pooling_grid": [0, "context_only"]})
    np.testing.assert_allclose(
        fit.selected.raw_predict(holdout(rows)), one.selected.raw_predict(holdout(rows)), atol=1e-12
    )


def test_pooled_validation_loss_is_row_weighted(config):
    rows = panel()
    fit = fit_selection(rows, config)
    candidate = fit.report["candidates"]["context_only"]
    folds = candidate["folds"]
    assert folds[0]["validation_rows"] != folds[1]["validation_rows"]
    expected = sum(f["mse"] * f["validation_rows"] for f in folds) / sum(
        f["validation_rows"] for f in folds
    )
    assert candidate["pooled_validation_mse"] == pytest.approx(expected)


def test_operational_subset_uses_identical_rows_and_empty_metrics_are_null(config):
    rows = panel()
    fit = fit_selection(rows, config)
    evaluation = holdout(rows).copy()
    evaluation.loc[evaluation.index[::2], "operational_sum"] = np.nan
    evaluation["operational_available"] = evaluation.operational_sum.notna()
    result = evaluate_selection(evaluation, fit, config)
    assert result["coverage"]["team_rows"] == len(evaluation)
    assert result["operational_subset"]["coverage"]["team_rows"] == len(evaluation) // 2
    expected = evaluate_selection(evaluation[evaluation.operational_available], fit, config)
    assert result["operational_subset"]["metrics"]["selected"] == expected["metrics"]["selected"]
    assert result["operational_subset"]["metrics"]["role_sum"] == expected["metrics"]["role_sum"]
    assert "operational_sum" not in result["metrics"]
    empty = evaluate_selection(evaluation.iloc[:0], fit, config)
    assert empty["metrics"]["selected"]["mse"] is None
    assert empty["operational_subset"]["metrics"]["operational_sum"]["mse"] is None
    assert empty["status"] == "INCONCLUSIVE"


def test_joint_followup_needs_both_leagues_and_all_placebos(config):
    rows = panel()
    result = evaluate_study({"Spain": rows, "England": panel(23)}, config)
    assert result["verdict"] == "FOLLOWUP_SIGNAL"
    assert all(value["discrete_rank"] == 1 for value in result["identity_stress"].values())
    assert len(result["placebos"]) == len(config["permutation_seeds"])
    small = evaluate_study({"Spain": rows, "England": rows[rows.date < "2018-03-04"]}, config)
    assert small["verdict"] == "INCONCLUSIVE"
    missing = rows.drop(columns=["perm_1_residual_3"])
    unavailable = evaluate_study({"Spain": missing, "England": rows}, config)
    assert unavailable["verdict"] == "INCONCLUSIVE"


def test_placebo_tie_cannot_establish_identity_signal(config):
    rows = panel()
    for k in (0, 1, 3, 10, 30):
        rows[f"perm_0_residual_{k}"] = rows[f"residual_{k}"]
    result = evaluate_study({"Spain": rows, "England": rows}, config)
    assert result["verdict"] == "NOT_ESTABLISHED"
    assert not result["identity_stress"]["Spain"]["strictly_beats_every_placebo"]
    assert result["identity_stress"]["Spain"]["discrete_rank"] >= 2


def test_fitted_clipping_is_reported_and_finite_inputs_enforced(config):
    rows = panel()
    fit = fit_selection(rows, config)
    evaluation = holdout(rows).copy()
    evaluation["residual_3"] = -10
    result = evaluate_selection(evaluation, fit, config)
    assert result["negative_forecasts_clipped"]["selected"] == len(evaluation)
    assert result["metrics"]["selected"]["mean_prediction"] == 0
    evaluation.iloc[0, evaluation.columns.get_loc("target")] = np.nan
    with pytest.raises(ValueError, match="finite"):
        evaluate_selection(evaluation, fit, config)


def test_operational_availability_mismatch_is_not_silently_accepted(config):
    rows = panel()
    fit = fit_selection(rows, config)
    evaluation = holdout(rows).copy()
    evaluation["operational_available"] = False
    with pytest.raises(ValueError, match="operational availability"):
        evaluate_selection(evaluation, fit, config)


def test_full_empty_object_typed_study_reports_null_errors(config):
    rows = pd.DataFrame(columns=panel().columns)
    result = evaluate_study({"Spain": rows, "England": rows}, config)
    assert result["verdict"] == "INCONCLUSIVE"
    for evaluation in result["evaluation"].values():
        assert evaluation["coverage"]["team_rows"] == 0
        assert evaluation["metrics"]["regularized_3"]["mse"] is None
        assert evaluation["operational_subset"]["metrics"]["operational_sum"]["mse"] is None
    assert len(result["placebos"]) == 2
    json.dumps(result, allow_nan=False)
