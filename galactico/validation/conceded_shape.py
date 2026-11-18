"""Walk-forward comparisons and paired weekly intervals for the E-10 conceded-shape study.

All comparisons within a season use one draw of weeks per league and period.
The intervals condition on the selected settings and omit selection uncertainty.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from galactico.features.team import estimator
from galactico.features.team.descriptors import log_ratio_basis

__all__ = [
    "ClusterEstimate", "ForwardSettings", "LevelForward", "SeasonWorld", "ShapeForward",
    "cluster_ratio", "season_world", "select_k", "walk_forward_level", "walk_forward_shape",
]


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


@dataclass(frozen=True)
class ForwardSettings:
    parts: tuple[str, ...]
    mirror_pairs: tuple[tuple[str, str], ...]
    k_context: float
    k_unit_candidates: tuple[float | None, ...]
    minimum_prior_matches: int
    league_pseudocount: float
    raw_matches: int
    smoothing: float
    permutation_seeds: tuple[int, ...]
    seed: int
    tercile_count: int


@dataclass(frozen=True)
class ShapeForward:
    """Losses are indexed by input row, with zero placeholders outside eligible."""

    eligible: np.ndarray
    events: np.ndarray
    loss_league_venue: np.ndarray
    loss_context: np.ndarray
    loss_raw_five: np.ndarray
    loss_candidate: np.ndarray
    loss_mirror: np.ndarray
    loss_peers: np.ndarray
    loss_permuted: np.ndarray
    donor_changed: np.ndarray
    residual_coordinates: np.ndarray
    delta_coordinates_pair_excluded: np.ndarray


@dataclass(frozen=True)
class LevelForward:
    """Rows require positive exposure as well as eligibility to carry a deviance."""

    eligible: np.ndarray
    scored: np.ndarray
    deviance_league_venue: np.ndarray
    deviance_context: np.ndarray
    deviance_raw_five: np.ndarray
    deviance_unit: np.ndarray
    deviance_peers: np.ndarray


@dataclass(frozen=True)
class _MatchDay:
    league: str
    date: pd.Timestamp
    state: estimator.PriorState
    rows: np.ndarray
    unit: np.ndarray
    context: np.ndarray
    home: np.ndarray
    counts: np.ndarray
    exposure: np.ndarray
    recent_counts: np.ndarray
    recent_exposure: np.ndarray
    tiers: np.ndarray

    def peers(self) -> np.ndarray:
        """Other teams with a match on the sheet in the same strength group."""
        same = self.tiers[:, None] == self.tiers
        np.fill_diagonal(same, False)
        return same & (self.tiers >= 0)


def _prior_dates(rows: pd.DataFrame, settings: ForwardSettings) -> Iterator[_MatchDay]:
    """Yield eligible fixtures together before adding any fixture on their date."""
    if settings.raw_matches < 1 or settings.tercile_count < 1:
        raise ValueError("positive history length and strength group count required")
    calendar = (
        rows.reset_index(drop=True)
        .assign(date=pd.to_datetime(rows.date, format="mixed").dt.normalize().to_numpy())
        .sort_values(["league", "date", "game_id", "unit_id"])
    )
    if calendar.date.isna().any():
        raise ValueError("a match date is missing")
    cols = [f"n__{part}" for part in settings.parts]
    for league, fixtures in calendar.groupby("league", sort=False):
        teams = pd.Index(np.union1d(fixtures.unit_id, fixtures.context_id))
        state = estimator.empty_state(teams, settings.parts)
        played = np.zeros(len(teams), dtype=int)
        sheet = np.zeros_like(played)
        points = np.zeros_like(played)
        margin = np.zeros_like(played)
        recent = np.zeros((len(teams), settings.raw_matches, len(cols)))
        recent_exposure = np.zeros((len(teams), settings.raw_matches))
        for date, day in fixtures.groupby("date", sort=False):
            unit = teams.get_indexer(day.unit_id)
            context = teams.get_indexer(day.context_id)
            valid = day.valid.to_numpy(dtype=bool)
            counts = day[cols].to_numpy(dtype=np.int64)
            exposure = day.exposure.to_numpy(dtype=float)
            eligible = (
                valid
                & (played[unit] >= settings.minimum_prior_matches)
                & (played[context] >= settings.minimum_prior_matches)
            )
            if eligible.any() and state.counts.any():
                active = np.flatnonzero(sheet)
                # The final tie-break is ascending team id (the order in teams).
                rank = np.lexsort(
                    (active, -margin[active] / sheet[active], -points[active] / sheet[active])
                )
                tiers = np.full(len(teams), -1)
                tiers[active[rank]] = settings.tercile_count * np.arange(len(active)) // len(active)
                u = unit[eligible]
                yield _MatchDay(
                    league,
                    date,
                    state,
                    day.index.to_numpy()[eligible],
                    u,
                    context[eligible],
                    day.context_home.to_numpy(dtype=int)[eligible],
                    counts[eligible],
                    exposure[eligible],
                    recent[u].sum(axis=1),
                    recent_exposure[u].sum(axis=1),
                    tiers,
                )

            # Every sheet result counts towards peer strength. Only valid rows enter
            # the model and the rolling team history, including valid warm-up matches.
            diff = (day.unit_goals - day.context_goals).to_numpy(dtype=int)
            np.add.at(sheet, unit, 1)
            np.add.at(points, unit, (diff > 0) * 3 + (diff == 0))
            np.add.at(margin, unit, diff)
            for i in np.flatnonzero(valid):
                team = unit[i]
                slot = played[team] % settings.raw_matches
                recent[team, slot] = counts[i]
                recent_exposure[team, slot] = exposure[i]
                played[team] += 1
            state = estimator.add_rows(state, day, weights=np.ones(len(day)))


def _donor_maps(day: _MatchDay, settings: ForwardSettings) -> np.ndarray:
    donors = np.tile(np.arange(len(day.tiers)), (len(settings.permutation_seeds), 1))
    for p, placebo in enumerate(settings.permutation_seeds):
        for tier in np.unique(day.tiers[day.tiers >= 0]):
            members = np.flatnonzero(day.tiers == tier)
            key = f"{settings.seed}|{placebo}|{day.league}|{day.date:%Y-%m-%d}|{tier}"
            seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
            donors[p, members] = np.random.default_rng(seed).permutation(members)
    return donors[:, day.unit]


def _shape_loss(counts: np.ndarray, probability: np.ndarray) -> np.ndarray:
    return -(counts * np.log(probability)).sum(axis=-1)


def walk_forward_shape(rows: pd.DataFrame, settings: ForwardSettings) -> ShapeForward:
    """Score event composition against venue, opponent, team, peer and placebo histories."""
    n, k = len(rows), len(settings.parts)
    q, p = len(settings.k_unit_candidates), len(settings.permutation_seeds)
    forward = ShapeForward(
        eligible=np.zeros(n, bool),
        events=rows[[f"n__{part}" for part in settings.parts]].sum(axis=1).to_numpy(dtype=np.int64),
        loss_league_venue=np.zeros(n),
        loss_context=np.zeros(n),
        loss_raw_five=np.zeros(n),
        loss_candidate=np.zeros((q, n)),
        loss_mirror=np.zeros((q, n)),
        loss_peers=np.zeros((q, n)),
        loss_permuted=np.zeros((p, q, n)),
        donor_changed=np.zeros((p, n), bool),
        residual_coordinates=np.zeros((n, k - 1)),
        delta_coordinates_pair_excluded=np.zeros((q, n, k - 1)),
    )
    basis = log_ratio_basis(k)
    mirror = np.arange(k)
    for left, right in settings.mirror_pairs:
        i, j = settings.parts.index(left), settings.parts.index(right)
        mirror[i], mirror[j] = j, i

    for day in _prior_dates(rows, settings):
        r, u, c, v = day.rows, day.unit, day.context, day.home
        fit = estimator.shape_estimate(
            day.state,
            league_pseudocount=settings.league_pseudocount,
            k_context=settings.k_context,
            k_unit=None,
        )
        baseline = estimator.predicted_shape(fit, c, v, np.zeros_like(day.counts))
        raw = day.recent_counts + settings.smoothing
        forward.eligible[r] = True
        forward.loss_league_venue[r] = _shape_loss(day.counts, fit.pi_venue[v])
        forward.loss_context[r] = _shape_loss(day.counts, baseline)
        forward.loss_raw_five[r] = _shape_loss(day.counts, raw / raw.sum(axis=1, keepdims=True))
        observed = day.counts + settings.smoothing
        observed = observed / observed.sum(axis=1, keepdims=True)
        forward.residual_coordinates[r] = (np.log(observed) - np.log(baseline)) @ basis.T
        donors = _donor_maps(day, settings)
        forward.donor_changed[:, r] = donors != u
        peers = day.peers()
        peer_observed, peer_expected = peers @ fit.observed, peers @ fit.expected
        # For calibration, remove this opponent at both venues from the team's
        # observed counts and from its opponent-adjusted expected counts.
        pair = day.state.counts[c, u]
        other_observed = fit.observed[u] - pair.sum(axis=1)
        other_expected = fit.expected[u] - (
            pair.sum(axis=-1, keepdims=True) * fit.expected_share[c, u]
        ).sum(axis=1)

        for i, strength in enumerate(settings.k_unit_candidates):
            if strength is None:
                for losses in (forward.loss_candidate, forward.loss_mirror, forward.loss_peers):
                    losses[i, r] = forward.loss_context[r]
                forward.loss_permuted[:, i, r] = forward.loss_context[r]
                continue
            delta = estimator.unit_deviation(fit.observed, fit.expected, k_unit=strength)
            peer = estimator.unit_deviation(peer_observed, peer_expected, k_unit=strength)
            excluded = estimator.unit_deviation(other_observed, other_expected, k_unit=strength)
            forward.delta_coordinates_pair_excluded[i, r] = excluded @ basis.T
            for losses, adjustment in (
                (forward.loss_candidate, delta[u]),
                (forward.loss_mirror, delta[u][:, mirror]),
                (forward.loss_peers, peer[u]),
            ):
                losses[i, r] = _shape_loss(
                    day.counts, estimator.predicted_shape(fit, c, v, adjustment)
                )
            permuted = estimator.predicted_shape(fit, c, v, delta[donors])
            forward.loss_permuted[:, i, r] = _shape_loss(day.counts, permuted)
    return forward


def _deviance(events: np.ndarray, mean: np.ndarray) -> np.ndarray:
    # At zero observed events the logarithmic term has limit zero. A positive
    # count with a zero forecast mean has infinite deviance under the model.
    term = np.zeros_like(mean)
    positive = events > 0
    with np.errstate(divide="ignore"):
        term[positive] = events[positive] * np.log(events[positive] / mean[positive])
    return 2 * (term - (events - mean))


def walk_forward_level(rows: pd.DataFrame, settings: ForwardSettings) -> LevelForward:
    """Score event volume per positive-exposure fixture using the same prior calendar."""
    n, q = len(rows), len(settings.k_unit_candidates)
    forward = LevelForward(
        eligible=np.zeros(n, bool),
        scored=np.zeros(n, bool),
        deviance_league_venue=np.zeros(n),
        deviance_context=np.zeros(n),
        deviance_raw_five=np.zeros(n),
        deviance_unit=np.zeros((q, n)),
        deviance_peers=np.zeros((q, n)),
    )
    for day in _prior_dates(rows, settings):
        forward.eligible[day.rows] = True
        keep = day.exposure > 0
        if not keep.any():
            continue
        r, u, c, v = day.rows[keep], day.unit[keep], day.context[keep], day.home[keep]
        events, exposure = day.counts[keep].sum(axis=1), day.exposure[keep]
        forward.scored[r] = True
        fit = estimator.level_estimate(
            day.state, k_context_level=settings.k_context, k_unit_level=None
        )
        baseline = estimator.predicted_level(fit, c, v, exposure, np.ones(len(r)))
        forward.deviance_context[r] = _deviance(events, baseline)
        forward.deviance_league_venue[r] = _deviance(events, exposure * fit.rate_venue[v])
        raw_rate = (day.recent_counts[keep].sum(axis=1) + settings.smoothing) / (
            day.recent_exposure[keep] + settings.smoothing / fit.rate
        )
        forward.deviance_raw_five[r] = _deviance(events, exposure * raw_rate)
        peers = day.peers()
        for i, strength in enumerate(settings.k_unit_candidates):
            if strength is None:
                forward.deviance_unit[i, r] = forward.deviance_context[r]
                forward.deviance_peers[i, r] = forward.deviance_context[r]
                continue
            unit_ratio = estimator.unit_level_ratio(
                fit.unit_observed, fit.unit_expected, k_unit_level=strength
            )
            peer_ratio = estimator.unit_level_ratio(
                peers @ fit.unit_observed, peers @ fit.unit_expected, k_unit_level=strength
            )
            for losses, ratio in (
                (forward.deviance_unit, unit_ratio),
                (forward.deviance_peers, peer_ratio),
            ):
                losses[i, r] = _deviance(
                    events, estimator.predicted_level(fit, c, v, exposure, ratio[u])
                )
    return forward


def select_k(
    loss_by_candidate: np.ndarray,
    weights: np.ndarray,
    mask: np.ndarray,
    candidates: Sequence[float | None],
    *,
    tolerance: float,
) -> tuple[int | None, list[float]]:
    """Select on the supplied development rows, applying the registered tie rule."""
    total = weights[mask].sum()
    pooled = (
        loss_by_candidate[:, mask].sum(axis=1) / total
        if total > 0
        else np.full(len(candidates), np.nan)
    )
    losses = pooled.tolist()
    if not np.isfinite(pooled).all():
        return None, losses
    tied = np.flatnonzero(pooled <= pooled.min() + tolerance)
    winner = max(tied, key=lambda i: math.inf if candidates[i] is None else candidates[i])
    return int(winner), losses
