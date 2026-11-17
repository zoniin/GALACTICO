"""Estimate event composition and volume from valid matches strictly before a date.

The shared E-10 estimator uses closed-form counts by team, opponent and venue. Whether
a team's estimated pattern persists in later matches is a separate research question.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .descriptors import TeamDescriptorSpec

LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART = 1.0


def descriptor_rows(
    table: pd.DataFrame, spec: TeamDescriptorSpec, *, league: str, exposure_unit_seconds: int
) -> pd.DataFrame:
    passes = table.set_index(["game_id", "team_id"]).match__completed_passes
    opponents = pd.MultiIndex.from_arrays(
        [table.game_id, table.opponent_id], names=passes.index.names
    )
    rows = pd.DataFrame(
        {
            "league": league,
            "game_id": table.game_id,
            "unit_id": table.team_id,
            "context_id": table.opponent_id,
            "date": pd.to_datetime(table.date, format="mixed").dt.normalize(),
            "context_home": ~table.is_home,
            "valid": table.valid,
            "exposure": table.window_seconds / exposure_unit_seconds,
            "unit_goals": table.goals_for,
            "context_goals": table.goals_against,
            "unit_passes": table.match__completed_passes,
            "context_passes": passes.loc[opponents].to_numpy(),
        }
    )
    rows[[f"n__{name}" for name in spec.part_names]] = spec.counts(table)
    rows["date"] = rows.date.astype("datetime64[ns]")
    return rows.sort_values(["date", "game_id", "unit_id"], ignore_index=True)


@dataclass(frozen=True)
class PriorState:
    team_ids: tuple[int, ...]
    parts: tuple[str, ...]
    counts: np.ndarray  # context team, unit team, context home, event part
    exposure: np.ndarray  # context team, unit team, context home


def empty_state(team_ids: Sequence[int], parts: Sequence[str]) -> PriorState:
    teams = tuple(sorted(team_ids))
    if len(set(teams)) != len(teams):
        raise ValueError("team ids must be unique")
    shape = (len(teams), len(teams), 2)
    return PriorState(teams, tuple(parts), np.zeros((*shape, len(parts))), np.zeros(shape))


def add_rows(state: PriorState, rows: pd.DataFrame, *, weights: np.ndarray) -> PriorState:
    weights = np.asarray(weights, dtype=float)
    if weights.shape != (len(rows),) or not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("weights must be a finite nonnegative value per row")
    teams = pd.Index(state.team_ids)
    if not (rows.unit_id.isin(teams) & rows.context_id.isin(teams)).all():
        raise ValueError("team id outside prior state")
    # Filter before multiplying: an invalid match carries NaN window exposure.
    selected = rows.assign(weight=weights).loc[rows.valid & (weights > 0)]
    selected = selected.sort_values(["game_id", "unit_id"])
    indices = (
        teams.get_indexer(selected.context_id),
        teams.get_indexer(selected.unit_id),
        selected.context_home.to_numpy(dtype=np.intp),
    )
    counts, exposure = state.counts.copy(), state.exposure.copy()
    weight = selected.weight.to_numpy()
    observed = selected[[f"n__{p}" for p in state.parts]].to_numpy(dtype=float)
    np.add.at(counts, indices, observed * weight[:, None])
    np.add.at(exposure, indices, selected.exposure.to_numpy() * weight)
    return PriorState(state.team_ids, state.parts, counts, exposure)


def state_at(
    rows: pd.DataFrame,
    *,
    team_ids: Sequence[int],
    parts: Sequence[str],
    date: str,
    weights: np.ndarray,
) -> PriorState:
    before = (
        pd.to_datetime(rows.date, format="mixed").dt.normalize() < pd.Timestamp(date).normalize()
    )
    return add_rows(
        empty_state(team_ids, parts), rows.loc[before], weights=np.asarray(weights)[before]
    )


@dataclass(frozen=True)
class ShapeEstimate:
    team_ids: tuple[int, ...]
    k_context: float
    k_unit: float | None
    league_pseudocount: float
    events: float
    pi: np.ndarray
    pi_venue: np.ndarray
    nu: np.ndarray
    context: np.ndarray
    context_without_unit: np.ndarray
    expected_share: np.ndarray
    observed: np.ndarray
    expected: np.ndarray
    delta: np.ndarray


def _composition(counts):
    return counts / counts.sum(axis=-1, keepdims=True)


def unit_deviation(
    observed: np.ndarray, expected: np.ndarray, *, k_unit: float | None
) -> np.ndarray:
    observed = np.asarray(observed, dtype=float)
    if k_unit is None:
        return np.zeros_like(observed)
    total = observed.sum(axis=-1, keepdims=True)
    # The protocol gives an unobserved unit zero deviation from the league.
    prior = np.divide(expected, total, out=np.ones_like(observed), where=total > 0)
    return np.log((observed + k_unit * prior) / (total + k_unit)) - np.log(prior)


def shape_estimate(
    state: PriorState, *, league_pseudocount: float, k_context: float, k_unit: float | None
) -> ShapeEstimate:
    counts = state.counts
    by_venue = counts.sum(axis=(0, 1))
    pi = _composition(by_venue.sum(axis=0) + league_pseudocount)
    pi_venue = _composition(by_venue + league_pseudocount)
    nu = np.log(pi_venue) - np.log(pi)
    by_context = counts.sum(axis=(1, 2))
    context = _composition(by_context + k_context * pi)
    other_counts = by_context[:, None, :] - counts.sum(axis=2)
    context_without_unit = _composition(other_counts + k_context * pi)
    expected_share = _composition(context_without_unit[:, :, None, :] * np.exp(nu))
    observed = counts.sum(axis=(0, 2))
    expected = (counts.sum(axis=-1, keepdims=True) * expected_share).sum(axis=(0, 2))
    return ShapeEstimate(
        state.team_ids,
        k_context,
        k_unit,
        league_pseudocount,
        float(by_venue.sum()),
        pi,
        pi_venue,
        nu,
        context,
        context_without_unit,
        expected_share,
        observed,
        expected,
        unit_deviation(observed, expected, k_unit=k_unit),
    )


@dataclass(frozen=True)
class LevelEstimate:
    team_ids: tuple[int, ...]
    k_context_level: float
    k_unit_level: float | None
    rate_venue: np.ndarray
    rate: float
    context_ratio: np.ndarray
    context_ratio_without_unit: np.ndarray
    unit_observed: np.ndarray
    unit_expected: np.ndarray
    unit_ratio: np.ndarray


def unit_level_ratio(
    observed: np.ndarray, expected: np.ndarray, *, k_unit_level: float | None
) -> np.ndarray:
    if k_unit_level is None:
        return np.ones_like(observed, dtype=float)
    return (observed + k_unit_level) / (expected + k_unit_level)


def level_estimate(
    state: PriorState, *, k_context_level: float, k_unit_level: float | None
) -> LevelEstimate:
    events = state.counts.sum(axis=-1)
    exposure = state.exposure
    by_venue = exposure.sum(axis=(0, 1))
    rates = np.divide(events.sum(axis=(0, 1)), by_venue, out=np.full(2, np.nan), where=by_venue > 0)
    rate = float(events.sum() / by_venue.sum()) if by_venue.sum() > 0 else np.nan
    baseline = np.multiply(exposure, rates, out=np.zeros_like(exposure), where=exposure > 0)
    by_context = events.sum(axis=(1, 2)) + k_context_level
    expected_by_context = baseline.sum(axis=(1, 2)) + k_context_level
    context_ratio = by_context / expected_by_context
    without_unit = (by_context[:, None] - events.sum(axis=2)) / (
        expected_by_context[:, None] - baseline.sum(axis=2)
    )
    observed = events.sum(axis=(0, 2))
    expected = (baseline * without_unit[:, :, None]).sum(axis=(0, 2))
    return LevelEstimate(
        state.team_ids,
        k_context_level,
        k_unit_level,
        rates,
        rate,
        context_ratio,
        without_unit,
        observed,
        expected,
        unit_level_ratio(observed, expected, k_unit_level=k_unit_level),
    )


def predicted_shape(
    estimate: ShapeEstimate, context: np.ndarray, context_home: np.ndarray, delta: np.ndarray
) -> np.ndarray:
    return _composition(
        estimate.context[context] * np.exp(estimate.nu[context_home.astype(int)] + delta)
    )


def predicted_level(
    estimate: LevelEstimate,
    context: np.ndarray,
    context_home: np.ndarray,
    exposure: np.ndarray,
    unit_ratio: np.ndarray,
) -> np.ndarray:
    return (
        exposure
        * estimate.rate_venue[context_home.astype(int)]
        * estimate.context_ratio[context]
        * unit_ratio
    )


def served_composition(estimate: ShapeEstimate, team_id: int) -> tuple[np.ndarray, float]:
    if estimate.k_unit is None:
        raise ValueError("a context-only estimate has no team composition")
    u = estimate.team_ids.index(team_id)
    total = estimate.observed[u].sum()
    return _composition(estimate.pi * np.exp(estimate.delta[u])), float(
        total / (total + estimate.k_unit)
    )


def served_volume(estimate: LevelEstimate, team_id: int) -> tuple[float, float]:
    if estimate.k_unit_level is None:
        raise ValueError("a context-only estimate has no team volume")
    u = estimate.team_ids.index(team_id)
    expected = estimate.unit_expected[u]
    return float(estimate.rate * estimate.unit_ratio[u]), float(
        expected / (expected + estimate.k_unit_level)
    )
