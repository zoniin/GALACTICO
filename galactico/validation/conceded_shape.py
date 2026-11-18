"""Walk-forward comparisons and paired weekly intervals for the E-10 conceded-shape study.

All comparisons within a season use one draw of weeks per league and period.
The intervals condition on the selected settings and omit selection uncertainty.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
import pandas as pd

from galactico.features.team import estimator
from galactico.features.team.descriptors import F3_CHANNELS, log_ratio_basis
from galactico.reliability.core import AxisReliability

__all__ = [
    "ClusterEstimate", "CountPass", "ForwardSettings", "LevelForward",
    "SeasonWorld", "ShapeForward",
    "audit_summary_from_rows", "calibration", "cluster_ratio", "count_pass", "level_split_half",
    "sample_gates", "season_world", "select_k", "split_half", "walk_forward_level",
    "walk_forward_shape",
]


@dataclass(frozen=True)
class SeasonWorld:
    labels: tuple[str, ...]
    strata: tuple[str, ...]
    multiplicity: np.ndarray
    fingerprint: str
    # Needed to distinguish the two parts of a week that crosses the cutoff.
    calendar: tuple[pd.Timestamp, str] | None = field(default=None, kw_only=True, repr=False)


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
    return SeasonWorld(tuple(labels), tuple(strata), weights, hashlib.sha256(payload).hexdigest(),
                       calendar=(cutoff, week_rule))


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
        # NumPy validates the configured method name at runtime.
        low, high = np.quantile(ratios, quantiles, method=cast(Any, method))
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


@dataclass(frozen=True)
class _ScheduleDay:
    league: str
    date: pd.Timestamp
    teams: pd.Index
    frame: pd.DataFrame
    unit: np.ndarray
    context: np.ndarray
    unit_prior: np.ndarray
    context_prior: np.ndarray
    counts: np.ndarray
    eligible: np.ndarray
    tiers: np.ndarray


def _schedule(rows: pd.DataFrame, settings: ForwardSettings) -> Iterator[_ScheduleDay]:
    """Take a snapshot of prior match counts and standings before each calendar date."""
    if settings.tercile_count < 1:
        raise ValueError("positive strength group count required")
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
        played = np.zeros(len(teams), dtype=int)
        sheet = np.zeros_like(played)
        points = np.zeros_like(played)
        margin = np.zeros_like(played)
        prior_events = False
        for date, day in fixtures.groupby("date", sort=False):
            unit = teams.get_indexer(day.unit_id)
            context = teams.get_indexer(day.context_id)
            valid = day.valid.to_numpy(dtype=bool)
            counts = day[cols].to_numpy(dtype=np.int64)
            u_prior, c_prior = played[unit], played[context]
            eligible = (
                prior_events
                & valid
                & (u_prior >= settings.minimum_prior_matches)
                & (c_prior >= settings.minimum_prior_matches)
            )
            tiers = np.full(len(teams), -1)
            if eligible.any():
                active = np.flatnonzero(sheet)
                rank = np.lexsort(
                    (active, -margin[active] / sheet[active], -points[active] / sheet[active])
                )
                tiers[active[rank]] = settings.tercile_count * np.arange(len(active)) // len(active)
            yield _ScheduleDay(
                league, date, teams, day, unit, context, u_prior, c_prior, counts, eligible, tiers
            )
            diff = (day.unit_goals - day.context_goals).to_numpy(dtype=int)
            np.add.at(sheet, unit, 1)
            np.add.at(points, unit, (diff > 0) * 3 + (diff == 0))
            np.add.at(margin, unit, diff)
            np.add.at(played, unit[valid], 1)
            prior_events = prior_events or bool(counts[valid].any())


def _prior_dates(rows: pd.DataFrame, settings: ForwardSettings) -> Iterator[_MatchDay]:
    """Yield eligible fixtures together before adding any fixture on their date."""
    if settings.raw_matches < 1:
        raise ValueError("positive history length required")
    league = None
    for day in _schedule(rows, settings):
        if day.league != league:
            league = day.league
            state = estimator.empty_state(day.teams, settings.parts)
            recent = np.zeros((len(day.teams), settings.raw_matches, len(settings.parts)))
            recent_exposure = np.zeros((len(day.teams), settings.raw_matches))
            next_slot = np.zeros(len(day.teams), dtype=int)
        keep = day.eligible
        exposure = day.frame.exposure.to_numpy(dtype=float)
        if keep.any():
            u = day.unit[keep]
            yield _MatchDay(
                day.league,
                day.date,
                state,
                day.frame.index.to_numpy()[keep],
                u,
                day.context[keep],
                day.frame.context_home.to_numpy(dtype=int)[keep],
                day.counts[keep],
                exposure[keep],
                recent[u].sum(axis=1),
                recent_exposure[u].sum(axis=1),
                day.tiers,
            )
        for i in np.flatnonzero(day.frame.valid):
            team = day.unit[i]
            slot = next_slot[team]
            recent[team, slot] = day.counts[i]
            recent_exposure[team, slot] = exposure[i]
            next_slot[team] = (slot + 1) % settings.raw_matches
        state = estimator.add_rows(state, day.frame, weights=np.ones(len(day.frame)))


def _donor_maps(
    league: str, date: pd.Timestamp, tiers: np.ndarray, unit: np.ndarray, settings: ForwardSettings
) -> np.ndarray:
    donors = np.tile(np.arange(len(tiers)), (len(settings.permutation_seeds), 1))
    for p, placebo in enumerate(settings.permutation_seeds):
        for tier in np.unique(tiers[tiers >= 0]):
            members = np.flatnonzero(tiers == tier)
            key = f"{settings.seed}|{placebo}|{league}|{date:%Y-%m-%d}|{tier}"
            seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
            donors[p, members] = np.random.default_rng(seed).permutation(members)
    return donors[:, unit]


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
        donors = _donor_maps(day.league, day.date, day.tiers, u, settings)
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
    threshold = min(losses) + tolerance
    tied = [(i, k) for i, k in enumerate(candidates) if losses[i] <= threshold]
    winner, _ = max(tied, key=lambda option: math.inf if option[1] is None else option[1])
    return winner, losses


@dataclass(frozen=True)
class CountPass:
    eligible: np.ndarray
    events: np.ndarray
    unit_prior_matches: np.ndarray
    context_prior_matches: np.ndarray
    permutation_seeds: tuple[int, ...]
    donor_changed: np.ndarray


def count_pass(rows: pd.DataFrame, settings: ForwardSettings) -> CountPass:
    """Measure sample support on the same schedule as the forecasts, before fitting."""
    n = len(rows)
    counts = CountPass(
        np.zeros(n, bool),
        np.zeros(n, np.int64),
        np.zeros(n, int),
        np.zeros(n, int),
        settings.permutation_seeds,
        np.zeros((len(settings.permutation_seeds), n), bool),
    )
    for day in _schedule(rows, settings):
        ix = day.frame.index.to_numpy()
        counts.eligible[ix] = day.eligible
        counts.events[ix] = day.counts.sum(axis=1)
        counts.unit_prior_matches[ix] = day.unit_prior
        counts.context_prior_matches[ix] = day.context_prior
        if day.eligible.any():
            unit = day.unit[day.eligible]
            donors = _donor_maps(day.league, day.date, day.tiers, unit, settings)
            counts.donor_changed[:, ix[day.eligible]] = donors != unit
    return counts


def audit_summary_from_rows(rows: pd.DataFrame, leagues: Sequence[str]) -> dict[str, dict]:
    total = rows.groupby("league").game_id.nunique()
    valid = rows.loc[rows.valid].groupby("league").game_id.nunique()
    return {
        league: {"matches": int(total.get(league, 0)), "valid_matches": int(valid.get(league, 0))}
        for league in leagues
    }


def _meeting_halves(rows: pd.DataFrame) -> pd.DataFrame:
    """Assign opponents on the entire calendar before removing invalid meetings."""
    team = ["league", "unit_id"]
    pair = [*team, "context_id"]
    meetings = rows.assign(
        date=pd.to_datetime(rows.date, format="mixed").dt.normalize()
    ).sort_values([*pair, "date", "game_id"])
    meetings = meetings.assign(leg=meetings.groupby(pair).cumcount())
    if (meetings.leg > 1).any():
        raise ValueError("the split requires at most two meetings with an opponent")
    first = meetings[meetings.leg == 0].sort_values([*team, "date", "context_id"])
    first = first.assign(position=first.groupby(team).cumcount())
    meetings = meetings.merge(first[[*pair, "position"]], on=pair, validate="many_to_one")
    # In successive pairs of opponents, A alternates between the earlier and later leg.
    meetings["half"] = np.where(meetings.leg == meetings.position.floordiv(2).mod(2), "A", "B")
    return meetings.loc[meetings.valid]


def _qualifying_teams(halves: pd.DataFrame, minimum: int) -> pd.DataFrame:
    played = halves.groupby(["league", "unit_id", "half"]).size().unstack(fill_value=0)
    played = played.reindex(columns=["A", "B"], fill_value=0)
    return played[(played >= minimum).all(axis=1)]


def sample_gates(
    rows: pd.DataFrame,
    counts: CountPass,
    audit_summary: Mapping,
    config: dict,
    *,
    subject: str,
) -> dict[str, dict]:
    """Evaluate the registered sample gates that precede model selection."""
    if subject not in ("shape", "level", "replication"):
        raise ValueError("unknown E-10 sample-gate subject")
    replication = subject == "replication"
    limits = config["replication"] if replication else config
    leagues = limits["leagues"]
    dates = pd.to_datetime(rows.date, format="mixed").dt.normalize()
    evaluation = (dates >= pd.Timestamp(limits["evaluation_start"])).to_numpy()
    weeks = dates.dt.to_period(config["calendar_week_rule"])
    gates: dict[str, dict] = {}
    for league in leagues:
        eligible = counts.eligible & (rows.league == league).to_numpy()
        audit = audit_summary[league]
        total = audit["listed_matches"] if replication else audit["matches"]
        valid_share = audit["valid_matches"] / total if total else None
        metrics = {"matches": total, "valid_matches": audit["valid_matches"], "share": valid_share}
        passed = (
            valid_share is not None
            and valid_share >= limits["minimum_valid_match_share_per_league"]
        )
        records = {"G1": (passed, metrics)}
        for gate, period, mask in (
            ("G2", "development", eligible & ~evaluation),
            ("G3", "evaluation", eligible & evaluation),
        ):
            if replication and gate == "G2":
                continue
            detail = {"rows": int(mask.sum()), "weeks": int(weeks[mask].nunique())}
            ok = (
                detail["rows"] >= limits[f"minimum_{period}_rows_per_league"]
                and detail["weeks"] >= limits[f"minimum_{period}_weeks_per_league"]
            )
            if gate == "G3":
                detail["events"] = int(counts.events[mask].sum())
                ok = ok and detail["events"] >= limits["minimum_evaluation_events_per_league"]
            records[gate] = (ok and bool(mask.any()), detail)
        for gate, (ok, detail) in records.items():
            item = gates.setdefault(gate, {"passed": True, "detail": {}})
            item["passed"] &= ok
            item["detail"][league] = detail
    if replication:
        return gates
    included = rows.league.isin(leagues).to_numpy()
    qualifying = _qualifying_teams(
        _meeting_halves(rows.loc[included]), config["minimum_half_matches_per_team"]
    )
    gates["G4"] = {
        "passed": len(qualifying) >= config["minimum_reliability_teams"],
        "detail": {"teams": len(qualifying)},
    }
    if subject == "shape":
        mask = counts.eligible & included & evaluation
        shares = {
            seed: float(changed[mask].mean()) if mask.any() else None
            for seed, changed in zip(counts.permutation_seeds, counts.donor_changed, strict=True)
        }
        by_seed = {str(seed): shares.get(seed) for seed in config["permutation_seeds"]}
        passed = all(
            s is not None and s >= config["minimum_permutation_changed_share"]
            for s in by_seed.values()
        )
        gates["G5"] = {"passed": bool(by_seed) and passed, "detail": by_seed}
    return gates


def _coordinate_names(parts: Sequence[str]) -> tuple[str, ...]:
    if len(parts) == 2:
        return ("first_versus_second",)
    if len(parts) != 3:
        raise ValueError("a shape descriptor needs two or three parts")
    if set(parts) == set(F3_CHANNELS.part_names):
        return ("side_balance", "wide_versus_centre")
    return ("first_versus_last", "ends_versus_middle")


def calibration(
    forward: ShapeForward,
    rows: pd.DataFrame,
    selected: int,
    world: SeasonWorld,
    *,
    k_unit: float | None,
    minimum_events: int,
    quantiles: tuple[float, float],
    method: str,
    zero_tolerance: float,
) -> dict | None:
    """Estimate held-out event-weighted slopes on the pair-excluded team adjustments."""
    if k_unit is None:
        return None
    if world.calendar is None:
        raise ValueError("calibration requires a world with an evaluation cutoff and week rule")
    cutoff, week_rule = world.calendar
    dates = pd.to_datetime(rows.date, format="mixed")
    keep = forward.eligible & (dates >= cutoff).to_numpy() & (forward.events >= minimum_events)
    weeks = dates[keep].dt.to_period(week_rule).astype(str)
    labels = (rows.league[keep] + "|evaluation|" + weeks).to_numpy()
    parts = [key.removeprefix("n__") for key in rows.columns if key.startswith("n__")]
    names = _coordinate_names(parts)
    x = forward.delta_coordinates_pair_excluded[selected, keep]
    y = forward.residual_coordinates[keep]
    n = forward.events[keep]
    result = {}
    for i, name in enumerate(names):
        estimate = cluster_ratio(
            n * x[:, i] * y[:, i],
            n * x[:, i] ** 2,
            labels,
            world,
            quantiles=quantiles,
            method=method,
            zero_tolerance=zero_tolerance,
        )
        result[name] = {"slope": estimate.estimate, "interval": estimate.interval}
    return result


def _half_correlation(x: np.ndarray, y: np.ndarray) -> float | None:
    if len(x) < 2 or not (np.isfinite(x).all() and np.isfinite(y).all()):
        return None
    x, y = x - x.mean(), y - y.mean()
    if not x.any() or not y.any():
        return None
    if np.array_equal(x, y):
        return 1.0
    if np.array_equal(x, -y):
        return -1.0
    return float(np.clip((x @ y) / (np.linalg.norm(x) * np.linalg.norm(y)), -1, 1))


def _reliability_coordinate(
    name: str,
    r: float | None,
    n: int,
    leagues: int,
    mean_matches: float,
    *,
    critical_value: float,
    house_confidence: float,
    period: str,
) -> dict:
    reliability = 2 * r / (1 + r) if r is not None and r > -1 else math.nan
    house = AxisReliability(name, reliability, n, 0, period, confidence=house_confidence).interval
    bound = None
    df = n - 3 - (leagues - 1)
    if r is not None and abs(r) < 1 and df >= 1:
        low_z = math.atanh(r) - critical_value / math.sqrt(df)
        # SB(tanh(z)) = 1 - exp(-2z), even when tanh(z) would round to -1.
        bound = -math.expm1(-2 * low_z)
    denominator = mean_matches - (mean_matches - 1) * reliability
    icc = reliability / denominator if denominator else math.nan
    return {
        "half_r": r,
        "spearman_brown": reliability if math.isfinite(reliability) else None,
        "lower_bound": bound,
        "house_lower_bound": house[0] if house is not None else None,
        "implied_per_match_icc": icc if math.isfinite(icc) else None,
    }


def _split_reliability(
    rows: pd.DataFrame,
    parts: Sequence[str],
    *,
    level: bool,
    smoothing: float,
    minimum_half_matches: int,
    critical_value: float,
    house_confidence: float,
    period: str,
    band: float,
    number: float,
) -> dict:
    halves = _meeting_halves(rows)
    played = _qualifying_teams(halves, minimum_half_matches)
    team = ["league", "unit_id"]
    n = len(played)
    leagues = played.index.get_level_values("league").nunique()
    mean_matches = float(played.sum(axis=1).mean()) if n else 0.0
    cols = [f"n__{part}" for part in parts]
    names = ("log_rate",) if level else _coordinate_names(parts)
    values = []
    for half in ("A", "B"):
        frame = halves.loc[halves.half == half]
        totals = frame.groupby(team)[[*cols, "exposure"]].sum().reindex(played.index)
        counts = totals[cols].to_numpy(dtype=float)
        if level:
            exposure = totals.exposure.to_numpy()
            rate = np.divide(
                counts.sum(axis=1) + smoothing, exposure, out=np.full(n, np.nan), where=exposure > 0
            )
            coords = np.log(rate)[:, None]
        else:
            counts += smoothing
            coords = (
                np.log(counts / counts.sum(axis=1, keepdims=True)) @ log_ratio_basis(len(parts)).T
            )
        measures = pd.DataFrame(coords, index=played.index, columns=names)
        # Subtract an anchor first so a constant league coordinate centres to exactly zero.
        offset = measures - measures.groupby(level="league").transform("first")
        values.append(offset - offset.groupby(level="league").transform("mean"))
    coordinates = {}
    for name in names:
        r = _half_correlation(values[0][name].to_numpy(), values[1][name].to_numpy())
        coordinates[name] = _reliability_coordinate(
            name,
            r,
            n,
            leagues,
            mean_matches,
            critical_value=critical_value,
            house_confidence=house_confidence,
            period=period,
        )
    bounds = [c["lower_bound"] for c in coordinates.values()]
    minimum = min(bounds) if all(bound is not None for bound in bounds) else None
    render = "insufficient"
    if minimum is not None and minimum >= band:
        render = "number" if minimum >= number else "band"
    return {
        "coordinates": coordinates,
        "n_teams": n,
        "teams_dropped": len(rows[team].drop_duplicates()) - n,
        "minimum_lower_bound": minimum,
        "render": render,
    }


def split_half(
    rows: pd.DataFrame,
    parts: Sequence[str],
    *,
    smoothing: float,
    minimum_half_matches: int,
    critical_value: float,
    house_confidence: float,
    period: str,
    band: float,
    number: float,
) -> dict:
    """Compare league-centred team compositions on the registered opponent-balanced halves."""
    return _split_reliability(
        rows,
        parts,
        level=False,
        smoothing=smoothing,
        minimum_half_matches=minimum_half_matches,
        critical_value=critical_value,
        house_confidence=house_confidence,
        period=period,
        band=band,
        number=number,
    )


def level_split_half(
    rows: pd.DataFrame,
    *,
    smoothing: float,
    minimum_half_matches: int,
    critical_value: float,
    house_confidence: float,
    period: str,
    band: float,
    number: float,
) -> dict:
    """Compare league-centred log event rates on the same calendar halves."""
    parts = [key.removeprefix("n__") for key in rows.columns if key.startswith("n__")]
    return _split_reliability(
        rows,
        parts,
        level=True,
        smoothing=smoothing,
        minimum_half_matches=minimum_half_matches,
        critical_value=critical_value,
        house_confidence=house_confidence,
        period=period,
        band=band,
        number=number,
    )
