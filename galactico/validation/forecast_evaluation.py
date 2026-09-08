"""Frozen mean forecasts and paired calendar-block evaluation for E-07.

This is predictive validation of observed opening lineups, never causal XI utility.
The fitted parameters are not exported to the decision engine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

VERSION = "opening-forecast-evaluation-v1"
BASELINES = (
    "team_mean",
    "team_recent",
    "opponent_mean",
    "role_sum",
    "lineup_sum",
    "operational_sum",
)


def design(rows: pd.DataFrame, *, augmented: bool) -> np.ndarray:
    columns = [
        np.ones(len(rows)),
        rows.team_mean.to_numpy(),
        rows.opponent_mean.to_numpy(),
        rows.home.astype(float).to_numpy(),
    ]
    if augmented:
        columns.append((rows.lineup_sum - rows.team_mean).to_numpy())
    matrix = np.column_stack(columns)
    if not np.isfinite(matrix).all():
        raise ValueError("forecast inputs must be finite; no missing-value imputation")
    return matrix


@dataclass(frozen=True)
class FrozenForecasts:
    context: tuple[float, ...]
    augmented: tuple[float, ...]
    development_rows: int
    context_rank: int
    augmented_rank: int

    def to_dict(self):
        return asdict(self)


def fit_forecasts(rows: pd.DataFrame, *, minimum_rows: int = 50) -> FrozenForecasts:
    if len(rows) < minimum_rows:
        raise ValueError(f"insufficient development rows: {len(rows)} < {minimum_rows}")
    target = rows.target.to_numpy(dtype=float)
    if not np.isfinite(target).all():
        raise ValueError("development outcomes must be finite")
    fits, ranks = [], []
    for augmented in (False, True):
        matrix = design(rows, augmented=augmented)
        coefficients, _, rank, _ = np.linalg.lstsq(matrix, target, rcond=None)
        if rank != matrix.shape[1]:
            raise ValueError("insufficient development design rank")
        fits.append(tuple(float(c) for c in coefficients))
        ranks.append(int(rank))
    return FrozenForecasts(fits[0], fits[1], len(rows), *ranks)


def paired_week_interval(
    rows: pd.DataFrame, differences, *, replicates: int, seed: int, quantiles=(0.025, 0.975)
) -> tuple[float, float] | None:
    """Draw weeks once for the paired loss difference; both fixture sides stay together."""
    if not len(rows):
        return None
    frame = pd.DataFrame(
        {
            "week": pd.to_datetime(rows.date).dt.to_period("W-SUN").astype(str).to_numpy(),
            "difference": np.asarray(differences, dtype=float),
        }
    )
    if not np.isfinite(frame.difference).all() or replicates < 1:
        raise ValueError("finite paired differences and positive replicates required")
    grouped = frame.groupby("week", sort=True).difference.agg(["sum", "count"])
    indices = np.random.default_rng(seed).integers(0, len(grouped), (replicates, len(grouped)))
    sampled = grouped["sum"].to_numpy()[indices].sum(axis=1)
    sampled /= grouped["count"].to_numpy()[indices].sum(axis=1)
    return tuple(float(v) for v in np.quantile(sampled, quantiles))


def evaluate_period(rows: pd.DataFrame, fits: FrozenForecasts, config: dict) -> dict:
    rows = rows.sort_values(["date", "game_id", "team_id"]).reset_index(drop=True)
    weeks = pd.to_datetime(rows.date).dt.to_period("W-SUN").nunique()
    counts = rows.team_id.value_counts()
    coverage = {
        "team_rows": len(rows),
        "matches": int(rows.game_id.nunique()),
        "weeks": int(weeks),
        "clubs": int(rows.team_id.nunique()),
        "maximum_club_share": float(counts.max() / len(rows)) if len(rows) else None,
    }
    predictions = {name: rows[name].to_numpy(dtype=float) for name in BASELINES}
    clipped = {}
    for name, coefficients, augmented in (
        ("context", fits.context, False),
        ("context_plus_lineup", fits.augmented, True),
    ):
        raw = design(rows, augmented=augmented) @ np.asarray(coefficients)
        clipped[name] = int((raw < 0).sum())
        predictions[name] = np.maximum(0, raw)
    target = rows.target.to_numpy(dtype=float)
    if not np.isfinite(target).all() or any(not np.isfinite(p).all() for p in predictions.values()):
        raise ValueError("evaluation requires common finite outcomes and forecasts")
    metrics = {}
    for name, forecast in predictions.items():
        error = forecast - target
        metrics[name] = {
            "mse": float(np.mean(error**2)) if len(rows) else None,
            "rmse": float(np.sqrt(np.mean(error**2))) if len(rows) else None,
            "mae": float(np.mean(np.abs(error))) if len(rows) else None,
            "mean_prediction": float(np.mean(forecast)) if len(rows) else None,
            "mean_observation": float(np.mean(target)) if len(rows) else None,
        }
    differences = (predictions["context_plus_lineup"] - target) ** 2 - (
        predictions["context"] - target
    ) ** 2
    interval = paired_week_interval(
        rows,
        differences,
        replicates=config["bootstrap_replicates"],
        seed=config["seed"],
        quantiles=config["interval_quantiles"],
    )
    sufficient = len(rows) >= config["minimum_test_rows"] and weeks >= config["minimum_test_weeks"]
    return {
        "coverage": coverage,
        "metrics": metrics,
        "negative_forecasts_clipped": clipped,
        "paired_mse_difference": float(np.mean(differences)) if len(rows) else None,
        "week_resampling_interval": interval,
        "status": "INCONCLUSIVE"
        if not sufficient
        else "INCREMENTAL_PREDICTION"
        if interval[1] < 0
        else "NOT_ESTABLISHED",
        "interpretation": "Conditional forecast error on observed stable openings, not XI utility",
    }


def joint_verdict(results: dict) -> str:
    statuses = [results[league]["status"] for league in ("Spain", "England")]
    if "INCONCLUSIVE" in statuses:
        return "INCONCLUSIVE"
    return (
        "INCREMENTAL_PREDICTION"
        if all(s == "INCREMENTAL_PREDICTION" for s in statuses)
        else "NOT_ESTABLISHED"
    )


def unfitted_metrics(rows: pd.DataFrame) -> dict:
    """Descriptive comparator errors remain reportable when model fitting is gated."""
    target = rows.target.to_numpy(dtype=float)
    output = {}
    for name in BASELINES:
        forecast = rows[name].to_numpy(dtype=float)
        if not np.isfinite(target).all() or not np.isfinite(forecast).all():
            raise ValueError("unfitted comparison needs common finite targets and forecasts")
        error = forecast - target
        output[name] = {
            "mse": float(np.mean(error**2)) if len(rows) else None,
            "rmse": float(np.sqrt(np.mean(error**2))) if len(rows) else None,
            "mae": float(np.mean(np.abs(error))) if len(rows) else None,
            "mean_prediction": float(np.mean(forecast)) if len(rows) else None,
            "mean_observation": float(np.mean(target)) if len(rows) else None,
        }
    return output
