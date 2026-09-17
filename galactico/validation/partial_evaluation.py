"""E-08 forward-selected aggregate forecasts, never player or XI utility.

Selection uses Spain development dates only. Reports contain aggregate diagnostics;
the prediction arrays and player-match inputs are not research artifacts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .forecast_evaluation import paired_week_interval

VERSION = "partial-opening-evaluation-v1"
BASE_COLUMNS = (
    "intercept",
    "team_mean",
    "team_recent",
    "opponent_mean",
    "home",
    "role_sum",
    "mean_log1p_count",
    "unseen_fraction",
)
WEAK_COLUMNS = ("intercept", "team_mean", "opponent_mean", "home")
RAW_COLUMNS = ("team_mean", "team_recent", "opponent_mean", "role_sum")


def _period(rows, start, end):
    dates = pd.to_datetime(rows.date)
    return (
        rows[(dates >= pd.Timestamp(start)) & (dates < pd.Timestamp(end))]
        .sort_values(["date", "game_id", "team_id"])
        .reset_index(drop=True)
    )


def _matrix(rows, columns):
    matrix = np.column_stack(
        [
            np.ones(len(rows)) if name == "intercept" else rows[name].to_numpy(dtype=float)
            for name in columns
        ]
    )
    if not np.isfinite(matrix).all():
        raise ValueError("nonfinite forecast features")
    return matrix


@dataclass(frozen=True)
class LinearFit:
    columns: tuple[str, ...]
    coefficients: tuple[float, ...]
    dropped_columns: tuple[str, ...]
    rank: int

    def raw_predict(self, rows):
        return _matrix(rows, self.columns) @ np.asarray(self.coefficients)


def _fit(rows, columns, dropped=()):
    matrix = _matrix(rows, columns)
    target = rows.target.to_numpy(dtype=float)
    if not np.isfinite(target).all():
        raise ValueError("nonfinite development outcomes")
    coefficients, _, rank, _ = np.linalg.lstsq(matrix, target, rcond=None)
    if rank != len(columns):
        raise ValueError("insufficient training design rank")
    return LinearFit(tuple(columns), tuple(map(float, coefficients)), tuple(dropped), int(rank))


def _base_fit(rows, config, columns=BASE_COLUMNS):
    matrix = _matrix(rows, columns)
    dropped = tuple(
        name
        for i, name in enumerate(columns)
        if name != "intercept" and np.ptp(matrix[:, i]) <= config["constant_tolerance"]
    )
    return _fit(rows, tuple(name for name in columns if name not in dropped), dropped)


@dataclass
class Selection:
    report: dict
    baseline: LinearFit | None = None
    selected: LinearFit | None = None
    weak_context: LinearFit | None = None

    def to_dict(self):
        return {
            **self.report,
            "final_fits": {
                name: asdict(fit) if fit is not None else None
                for name, fit in (
                    ("strong_baseline", self.baseline),
                    ("selected", self.selected),
                    ("weak_context", self.weak_context),
                )
            },
        }


def fit_selection(rows, config, residual_prefix="residual_") -> Selection:
    """Select/refit only inside the frozen development dates, even if passed all rows."""
    development = _period(rows, config["development_start"], config["test_start"])
    grid = sorted(
        set(config["pooling_grid"]),
        key=lambda k: (k != "context_only", -int(k) if k != "context_only" else 0),
    )
    reports = {str(k): {"folds": [], "eligible": True} for k in grid}
    report = {
        "status": "INCONCLUSIVE",
        "selected_k": None,
        "development_rows": len(development),
        "residual_prefix": residual_prefix,
        "folds": [],
        "candidates": reports,
        "reasons": [],
    }
    required = set(BASE_COLUMNS[1:]) | {
        f"{residual_prefix}{k}" for k in grid if k != "context_only"
    }
    missing = sorted(required.difference(rows.columns))
    if missing:
        report["reasons"].append(f"missing required features: {missing}")
        return Selection(report)
    for fold in config["forward_folds"]:
        train = _period(development, config["development_start"], fold["train_end"])
        validation = _period(development, fold["train_end"], fold["validation_end"])
        fold_report = {**fold, "training_rows": len(train), "validation_rows": len(validation)}
        report["folds"].append(fold_report)
        try:
            if (
                len(train) < config["minimum_training_rows"]
                or len(validation) < config["minimum_validation_rows"]
            ):
                raise ValueError("insufficient forward-fold sample")
            baseline = _base_fit(train, config)
            fold_report["dropped_columns"] = list(baseline.dropped_columns)
            fold_report["base_columns"] = list(baseline.columns)
        except ValueError as error:
            fold_report["reason"] = str(error)
            report["reasons"].append(str(error))
            for candidate in reports.values():
                candidate["eligible"] = False
                candidate["folds"].append({"reason": str(error)})
            continue
        for k in grid:
            candidate = reports[str(k)]
            try:
                fit = (
                    baseline
                    if k == "context_only"
                    else _fit(
                        train,
                        (*baseline.columns, f"{residual_prefix}{k}"),
                        baseline.dropped_columns,
                    )
                )
                raw = fit.raw_predict(validation)
                metrics = _metrics(validation.target.to_numpy(dtype=float), np.maximum(raw, 0))
                candidate["folds"].append(
                    {
                        "validation_rows": len(validation),
                        "mse": metrics["mse"],
                        "squared_error_sum": metrics["mse"] * len(validation),
                        "negative_forecasts_clipped": int((raw < 0).sum()),
                    }
                )
            except ValueError as error:
                candidate["eligible"] = False
                candidate["folds"].append({"reason": str(error)})
    for candidate in reports.values():
        candidate["pooled_validation_mse"] = (
            sum(f["squared_error_sum"] for f in candidate["folds"])
            / sum(f["validation_rows"] for f in candidate["folds"])
            if candidate["eligible"] and candidate["folds"]
            else None
        )
    if report["reasons"]:
        return Selection(report)
    eligible = [k for k in grid if reports[str(k)]["eligible"]]
    if not eligible:
        report["reasons"].append("no eligible model candidate")
        return Selection(report)
    best = min(reports[str(k)]["pooled_validation_mse"] for k in eligible)
    chosen = next(
        k
        for k in eligible
        if reports[str(k)]["pooled_validation_mse"] <= best + config["selection_tie_tolerance"]
    )
    report["selected_k"] = chosen
    try:
        baseline = _base_fit(development, config)
        selected = (
            baseline
            if chosen == "context_only"
            else _fit(
                development,
                (*baseline.columns, f"{residual_prefix}{chosen}"),
                baseline.dropped_columns,
            )
        )
    except ValueError as error:
        report["reasons"].append(f"final refit failed: {error}")
        return Selection(report)
    # This secondary bridge cannot veto the strong-baseline experiment.
    weak = None
    try:
        weak = _base_fit(development, config, WEAK_COLUMNS)
    except ValueError as error:
        report["weak_context_reason"] = str(error)
    report["status"] = "FITTED"
    return Selection(report, baseline, selected, weak)


def _metrics(target, predictions):
    if not np.isfinite(target).all() or not np.isfinite(predictions).all():
        raise ValueError("metrics require common finite outcomes and predictions")
    error = predictions - target
    return {
        "mse": float(np.mean(error**2)) if len(target) else None,
        "rmse": float(np.sqrt(np.mean(error**2))) if len(target) else None,
        "mae": float(np.mean(np.abs(error))) if len(target) else None,
        "mean_prediction": float(np.mean(predictions)) if len(target) else None,
        "mean_observation": float(np.mean(target)) if len(target) else None,
    }


def _coverage(rows):
    counts = rows.team_id.value_counts()
    return {
        "team_rows": len(rows),
        "matches": int(rows.game_id.nunique()),
        "weeks": int(pd.to_datetime(rows.date).dt.to_period("W-SUN").nunique()),
        "clubs": int(rows.team_id.nunique()),
        "maximum_club_share": float(counts.max() / len(rows)) if len(rows) else None,
        "mean_unseen_player_fraction": float(rows.unseen_fraction.mean()) if len(rows) else None,
        "mean_log1p_count": float(rows.mean_log1p_count.mean()) if len(rows) else None,
    }


def _predictions(rows, selection, config):
    predictions = {name: rows[name].to_numpy(dtype=float) for name in RAW_COLUMNS}
    for k in config["pooling_grid"]:
        if k != "context_only":
            predictions[f"regularized_{k}"] = (rows.role_sum + rows[f"residual_{k}"]).to_numpy(
                dtype=float
            )
    clipped = {}
    for name, fit in (
        ("strong_baseline", selection.baseline),
        ("selected", selection.selected),
        ("weak_context", selection.weak_context),
    ):
        if fit is not None:
            raw = fit.raw_predict(rows)
            clipped[name] = int((raw < 0).sum())
            predictions[name] = np.maximum(raw, 0)
    return predictions, clipped


def evaluate_selection(rows, selection: Selection, config) -> dict:
    """Common-cohort errors remain reportable even if model selection was gated."""
    rows = rows.sort_values(["date", "game_id", "team_id"]).reset_index(drop=True)
    predictions, clipped = _predictions(rows, selection, config)
    target = rows.target.to_numpy(dtype=float)
    coverage = _coverage(rows)
    available = np.isfinite(rows.operational_sum.to_numpy(dtype=float))
    if "operational_available" in rows and not np.array_equal(
        available, rows.operational_available.to_numpy(dtype=bool)
    ):
        raise ValueError("operational availability disagrees with finite accounting")
    subset_predictions = {name: values[available] for name, values in predictions.items()}
    subset_predictions["operational_sum"] = rows.operational_sum.to_numpy(dtype=float)[available]
    output = {
        "coverage": coverage,
        "metrics": {name: _metrics(target, values) for name, values in predictions.items()},
        "negative_forecasts_clipped": clipped,
        "operational_subset": {
            "coverage": _coverage(rows.loc[available]),
            "metrics": {
                name: _metrics(target[available], values)
                for name, values in subset_predictions.items()
            },
            "interpretation": "Every listed comparator uses this same available subset",
        },
        "paired_mse_difference": None,
        "week_resampling_interval": None,
        "status": "INCONCLUSIVE",
    }
    if selection.selected is None:
        output["reason"] = "model selection/refit unavailable"
        return output
    differences = (predictions["selected"] - target) ** 2 - (
        predictions["strong_baseline"] - target
    ) ** 2
    interval = paired_week_interval(
        rows,
        differences,
        replicates=config["bootstrap_replicates"],
        seed=config["seed"],
        quantiles=config["interval_quantiles"],
    )
    output["paired_mse_difference"] = float(np.mean(differences)) if len(rows) else None
    output["week_resampling_interval"] = interval
    sufficient = (
        len(rows) >= config["minimum_test_rows"]
        and coverage["weeks"] >= config["minimum_test_weeks"]
    )
    output["status"] = "EVALUATED" if sufficient else "INCONCLUSIVE"
    return output


def evaluate_study(forecasts: dict[str, pd.DataFrame], config: dict) -> dict:
    """Execute frozen development selection and both reused-period evaluations."""
    tests = {
        league: _period(forecasts[league], config["test_start"], config["end"])
        for league in ("Spain", "England")
    }
    selected = fit_selection(forecasts["Spain"], config)
    evaluation = {
        league: evaluate_selection(rows, selected, config) for league, rows in tests.items()
    }
    placebos = []
    for seed in config["permutation_seeds"]:
        placebo = fit_selection(forecasts["Spain"], config, f"perm_{seed}_residual_")
        results = {
            league: evaluate_selection(rows, placebo, config) for league, rows in tests.items()
        }
        placebos.append(
            {
                "seed": seed,
                "selection": placebo.to_dict(),
                "evaluation": {
                    league: {
                        key: values[key]
                        for key in (
                            "coverage",
                            "paired_mse_difference",
                            "week_resampling_interval",
                            "status",
                            "negative_forecasts_clipped",
                        )
                    }
                    | {
                        "fitted_metrics": {
                            key: values["metrics"].get(key)
                            for key in ("strong_baseline", "selected", "weak_context")
                        }
                    }
                    for league, values in results.items()
                },
            }
        )
    stress, complete, passes = {}, selected.selected is not None, []
    for league, actual in evaluation.items():
        differences = [p["evaluation"][league]["paired_mse_difference"] for p in placebos]
        supported = actual["status"] == "EVALUATED" and all(
            p["evaluation"][league]["status"] == "EVALUATED" for p in placebos
        )
        complete &= supported
        actual_difference = actual["paired_mse_difference"]
        comparable = actual_difference is not None and all(v is not None for v in differences)
        beats_all = comparable and all(actual_difference < v for v in differences)
        stress[league] = {
            "placebo_differences": differences,
            "discrete_rank": 1 + sum(v <= actual_difference for v in differences)
            if comparable
            else None,
            "strictly_beats_every_placebo": bool(beats_all),
            "interpretation": "Identity-link stress diagnostic, not a permutation p-value",
        }
        passes.append(supported and beats_all and actual["week_resampling_interval"][1] < 0)
    verdict = (
        "INCONCLUSIVE"
        if not complete
        else (
            "FOLLOWUP_SIGNAL"
            if selected.report["selected_k"] != "context_only" and all(passes)
            else "NOT_ESTABLISHED"
        )
    )
    return {
        "version": VERSION,
        "selection": selected.to_dict(),
        "evaluation": evaluation,
        "placebos": placebos,
        "identity_stress": stress,
        "verdict": verdict,
        "interpretation": (
            "Reused-period aggregate follow-up; no player or XI utility certification"
        ),
    }
