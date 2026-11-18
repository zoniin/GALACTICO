"""Paired weekly uncertainty estimates for the E-10 conceded-shape study.

All comparisons within a season use one draw of weeks per league and period.
The intervals condition on the selected settings and omit selection uncertainty.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = ["ClusterEstimate", "SeasonWorld", "cluster_ratio", "season_world"]


@dataclass(frozen=True)
class SeasonWorld:
    labels: tuple[str, ...]
    strata: tuple[str, ...]
    multiplicity: np.ndarray
    fingerprint: str


def season_world(
    dates_by_league: Mapping[str, pd.Series], *, leagues: Sequence[str],
    evaluation_start: str, week_rule: str, replicates: int, seed: int,
) -> SeasonWorld:
    """Draw each stratum's weeks with replacement, once for every comparison."""
    if set(dates_by_league) != set(leagues) or len(set(leagues)) != len(leagues):
        raise ValueError("the calendar must cover exactly the requested leagues")
    if replicates < 1:
        raise ValueError("at least one bootstrap replicate is required")
    cutoff = pd.Timestamp(evaluation_start)
    if pd.isna(cutoff):
        raise ValueError("the evaluation start date is missing")
    rng = np.random.default_rng(seed)
    labels: list[str] = []
    strata: list[str] = []
    blocks: list[np.ndarray] = []
    for league in leagues:
        dates = pd.to_datetime(dates_by_league[league])
        if dates.isna().any():
            raise ValueError("a match date is missing")
        for part, days in (("development", dates[dates < cutoff]),
                           ("evaluation", dates[dates >= cutoff])):
            weeks = sorted(days.dt.to_period(week_rule).unique())
            if not weeks:
                continue
            stratum = f"{league}|{part}"
            strata.append(stratum)
            labels.extend(f"{stratum}|{week}" for week in weeks)
            size = len(weeks)
            draws = rng.integers(0, size, size=(replicates, size))
            counts = np.zeros((replicates, size), dtype=np.int32)
            np.add.at(counts, (np.arange(replicates)[:, None], draws), 1)
            blocks.append(counts)

    weights = np.column_stack(blocks) if blocks else np.empty((replicates, 0), dtype=np.int32)
    weights.setflags(write=False)
    payload = "\n".join(labels).encode() + b"\0" + weights.astype("<i4", copy=False).tobytes()
    return SeasonWorld(tuple(labels), tuple(strata), weights, hashlib.sha256(payload).hexdigest())


@dataclass(frozen=True)
class ClusterEstimate:
    estimate: float | None
    interval: tuple[float, float] | None
    p_one_sided: float | None
    rows: int
    weight: float
    clusters: int
    holes: int


def cluster_ratio(
    numerator: np.ndarray, denominator: np.ndarray, labels: np.ndarray, world: SeasonWorld,
    *, quantiles: tuple[float, float], method: str, zero_tolerance: float,
) -> ClusterEstimate:
    """Compare sums in the original rows and in the same resampled weeks."""
    num, den = np.asarray(numerator, dtype=float), np.asarray(denominator, dtype=float)
    labels = np.asarray(labels)
    if num.ndim != 1 or den.shape != num.shape or labels.shape != num.shape:
        raise ValueError("one numerator, denominator and week label per row required")
    if not (np.isfinite(num).all() and np.isfinite(den).all()) or (den < 0).any():
        raise ValueError("finite components and nonnegative denominators required")
    if not len(num):
        return ClusterEstimate(None, None, None, 0, 0.0, 0, len(world.multiplicity))

    positions = pd.Index(world.labels).get_indexer(labels)
    if (positions < 0).any():
        raise ValueError("a row belongs to a week outside this season's world")
    order = np.argsort(positions)
    included, starts = np.unique(positions[order], return_index=True)
    # Paired loss differences can cancel within a week. Sum them accurately
    # before applying the shared weight to that week.
    weeks = np.split(order, starts[1:])
    totals = np.array([(math.fsum(num[week]), math.fsum(den[week])) for week in weeks])
    weight = math.fsum(totals[:, 1])
    estimate = math.fsum(totals[:, 0]) / weight if weight else None
    sampled = world.multiplicity[:, included] @ totals
    kept = sampled[:, 1] > 0
    ratios = sampled[kept, 0] / sampled[kept, 1]
    holes = len(kept) - len(ratios)
    interval = None
    if len(ratios):
        low, high = np.quantile(ratios, quantiles, method=method)
        interval = (float(low), float(high))
    p = (1 + int(np.count_nonzero(ratios >= -zero_tolerance))) / (1 + len(ratios))
    return ClusterEstimate(
        estimate, interval, p if weight else None, len(num), weight, len(included), holes
    )
