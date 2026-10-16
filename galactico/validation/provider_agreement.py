"""Agreement statistics, resampling and the frozen decision rule of E-11.

Claim: agreement statistics and a frozen rule that maps every outcome to one token.
For one quantity, level, pool and reader the two providers' values of the same units
give the order statistic (a rank correlation inside rank strata), Lin's concordance
with ICC(2,1) as its cross-check, and Bland-Altman summaries. One resampling world per
replicate (a match, a player and a team weight array, each drawn once from the frozen
seed and its stream and shared by every cell) gives their percentile intervals.
``classify`` maps a cell to one token of the cell vocabulary and is the only place a
cell token is produced. The permuted-link control reassigns the Wyscout aggregates of
the headline cell's own units inside cluster x role. ``admission`` applies the
protocol's admission table, and ``registry_verdicts`` the registry rule; it is the only
place a registry token is produced.

Non-claim: a token is about two coders of the same matches, not about football. It is
not validity, reliability or decision utility, and it says nothing about a player, a
team or which provider is right. The intervals are those of this resampling scheme,
conditional on the matches, the crosswalk and the fixed surfaces; the permuted-link
control is a stress test on fixed aggregates, not a p-value. Nothing here reads or
writes a file: panels hold player and match keys in process memory only, and no
exception message names a player, a team or a match. Every number is the caller's
frozen config, and a config key that restates a protocol rule is asserted, never
branched on.
"""

from __future__ import annotations

import math
import numbers
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .provider_crosswalk import permuted_partners

__all__ = [
    "AGREEMENT_VERSION",
    "InputPanel",
    "BlandAltman",
    "Agreement",
    "CellResult",
    "build_panel",
    "cluster_of_player",
    "stratified_rank_correlation",
    "concordance",
    "icc_absolute_single",
    "bland_altman",
    "block_weights",
    "match_weights",
    "player_weights",
    "team_weights",
    "aggregated_values",
    "applicable_gates",
    "cell_agreement",
    "cell_with_replicates",
    "subset_difference",
    "classify",
    "control_holds",
    "permuted_link_control",
    "difference_decomposition",
    "control_states",
    "admission",
    "registry_verdicts",
]

AGREEMENT_VERSION = "provider-agreement-v2"

# Row 1 of the decision table: the five gates of the run, then the five rules of a cell.
# The order in which the first that holds is taken is the config's.
_GATES: tuple[str, ...] = ("DATA_MISSING", "UNKNOWN_VOCABULARY", "MATCH_CROSSWALK",
                           "IDENTITY_COVERAGE", "XT_SURFACE")
_STOPPING_GATES = frozenset(_GATES[:3])
_RULE_REASONS: tuple[str, ...] = ("UNITS", "ONE_SIDED", "DEGENERATE", "REPLICATES",
                                  "UNDEFINED_STATISTIC")
_CELL_TOKENS = frozenset({"COMPARABLE", "COMPARABLE_IN_RANK_ONLY", "NOT_ESTABLISHED",
                          "NOT_COMPARABLE", "INCONCLUSIVE"})
_LINK_TOKENS = frozenset({"LINK_USABLE", "LINK_NOT_ESTABLISHED", "INCONCLUSIVE"})
_INCONCLUSIVE = "INCONCLUSIVE"
_OUTSIDE = "POINT_OUTSIDE_INTERVAL"
_EXCLUSIONS = frozenset({"DECLARED_VARIANT", "POSITIVE_CONTROL", "VERDICT",
                         "LA_LIGA_SUBSET_CONTRADICTS", "LA_LIGA_SUBSET_UNTESTED",
                         "PERMUTED_LINK_CONTROL"})
_LA_LIGA_EFFECTS = frozenset({"KEEP", "SUFFIX_LEAGUE_UNCONFIRMED",
                              "EXCLUDE_LA_LIGA_SUBSET_UNTESTED",
                              "EXCLUDE_LA_LIGA_SUBSET_CONTRADICTS"})
_EXCLUDED = "EXCLUDED"
_UNCONFIRMED = "_LEAGUE_UNCONFIRMED"
_CONTROLS = ("POSITIVE_CONTROL", "PERMUTED_LINK_CONTROL")

_PLAYER_MATCH, _TEAM_MATCH, _AGGREGATED = "player_match", "team_match", "aggregated_player"
_PLAYER_LEVELS = frozenset({_PLAYER_MATCH, _AGGREGATED})
_POOLED = "pooled"
_ROLE_STRATA = "wy_role"
_TEAM_STRATA = "team_with_most_crosswalked_matches_vs_opponents"
# Labels of the two team-match strata and of the one stratum where none is defined.
_TEAM_LABEL, _OPPONENT_LABEL, _ONE_STRATUM = "most_matches_team", "opponents", "all"

_FIXED_COHORT = "team_cluster_fixed_cohort"
_PIGEONHOLE = "pigeonhole_match_by_player"
_MATCH_CLUSTER = "match_cluster"
_SCHEMES = {_TEAM_MATCH: _MATCH_CLUSTER, _PLAYER_MATCH: _PIGEONHOLE, _AGGREGATED: _FIXED_COHORT}
_SENSITIVITY_SCHEMES = {_PLAYER_MATCH: _MATCH_CLUSTER, _AGGREGATED: _PIGEONHOLE}
# Each weight array of the shared world, and the key of its column axis.
_AXES = {"match": "matches", "player": "players", "team": "teams"}

_CLUSTER_RULE = ("team with most Wyscout regulation minutes over the player's present cells "
                 "in the pool's matches; ties to the smallest Wyscout team id")
_EXPOSURE_RULE = ("each provider's own regulation minutes summed over the player_match units "
                  "of the pool, evaluated once on unweighted data")
_COHORT_RULE = ("the units of the quantity's cell at registry_headline_cell with the two "
                "aggregates of its point estimate; the units, aggregates, exposure gate, "
                "minimum denominators and retained rank strata are the point estimate's, "
                "recomputed by the same calls on unweighted data, and no bootstrap weight "
                "enters")

# Replicates are evaluated this many at a time, so a (replicates, units) weight block of
# the largest cell stays a few megabytes.
_CHUNK = 256


# --- frames ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InputPanel:
    """One provider's player-match inputs on the player x match grid of the cells.

    ``players`` are every paired outfield player, ascending; ``matches`` every
    crosswalked match, ascending. ``present`` marks a sheet-minutes row with the
    frozen minimum regulation minutes on both providers; ``values`` maps each input
    key to a (P, M) float64 array, 0.0 where not present (``minutes_regulation``
    included); ``team_of_player_match`` is the Wyscout team id of a present cell, 0
    elsewhere. Process memory only.
    """

    players: np.ndarray
    matches: np.ndarray
    subset_of_match: np.ndarray
    team_of_player_match: np.ndarray
    role_of_player: np.ndarray
    present: np.ndarray
    values: Mapping[str, np.ndarray]

    def __post_init__(self) -> None:
        shape = (len(self.players), len(self.matches))
        if (self.subset_of_match.shape != shape[1:] or self.role_of_player.shape != shape[:1]
                or self.team_of_player_match.shape != shape or self.present.shape != shape):
            raise ValueError("panel arrays are not aligned on players x matches")
        if not (_ascending(self.players) and _ascending(self.matches)):
            raise ValueError("panel players and matches must be ascending and distinct")
        if self.present.dtype != np.bool_:
            raise ValueError("present must be boolean")
        if np.any(self.team_of_player_match[self.present] == 0):
            raise ValueError("a present cell has no team")
        for value in self.values.values():
            if value.shape != shape or value.dtype != np.float64:
                raise ValueError("panel values must be float64 players x matches")
            if np.any(value[~self.present] != 0.0):
                raise ValueError("a panel value outside a present cell is not 0.0")


@dataclass(frozen=True)
class BlandAltman:
    bias: float
    sd: float
    lower: float
    upper: float
    relative_bias: float
    scale_ratio: float
    slope: float


@dataclass(frozen=True)
class Agreement:
    """The point estimate of one cell. NaN where a statistic is undefined."""

    units: int
    strata_retained: tuple[str, ...]
    strata_dropped: tuple[str, ...]
    mean_sb: float
    mean_wy: float
    sd_sb: float
    sd_wy: float
    order: float
    spearman_unstratified: float
    concordance: float
    icc_absolute_single: float
    bland_altman: BlandAltman
    exact_share: float | None


@dataclass(frozen=True)
class CellResult:
    """One graded cell or one ungraded sensitivity row.

    ``point`` is None when a gate that applies to the cell failed: nothing was
    computed and its units are null. ``verdict`` and ``reason`` are None for an
    ungraded sensitivity. ``concordance_cross_check_gap`` is for the local results
    only; it is not a flag.
    """

    quantity: str
    level: str
    pool: str
    reader: str
    valuation: str
    exposure_minutes: int | None
    point: Agreement | None
    order_interval: tuple[float, float] | None
    concordance_interval: tuple[float, float] | None
    relative_bias_interval: tuple[float, float] | None
    replicate_mean_minus_point: float | None
    concordance_cross_check_gap: bool | None
    valid_replicates: int
    verdict: str | None
    reason: str | None
    flags: tuple[str, ...]


# --- shared helpers -------------------------------------------------------------------

def _frozen(config: Mapping[str, object], key: str, value: object) -> None:
    """A config key that restates a protocol rule is asserted; only ``value`` is built."""
    if config[key] != value:
        raise ValueError(f"config {key} restates a frozen rule; only {value!r} is implemented")


def _finite(value: object) -> bool:
    return (isinstance(value, numbers.Real) and not isinstance(value, bool)
            and math.isfinite(value))


def _number(value: float) -> float | None:
    return float(value) if _finite(value) else None


def _ascending(keys: np.ndarray) -> bool:
    return keys.ndim == 1 and (len(keys) < 2 or bool(np.all(np.diff(keys) > 0)))


def _subset_keys(config: Mapping[str, object]) -> list[str]:
    return [str(entry["key"]) for entry in config["subsets"]]


def _minutes_key(config: Mapping[str, object]) -> str:
    keys = [str(entry["key"]) for entry in config["player_match_inputs"]
            if entry["kind"] == "minutes"]
    if len(keys) != 1:
        raise ValueError("player_match_inputs must hold exactly one input of kind minutes")
    return keys[0]


def _in_pool(subsets: np.ndarray, pool: str, config: Mapping[str, object]) -> np.ndarray:
    """The pooled pool is every subset; a subset pool is its own matches."""
    keys = _subset_keys(config)
    if set(config["pools"]) != {_POOLED, *keys} or len(config["pools"]) != len(keys) + 1:
        raise ValueError("pools must be the pooled pool and one pool per subset")
    if pool == _POOLED:
        return np.ones(len(subsets), dtype=bool)
    if pool not in keys:
        raise ValueError("unknown pool")
    return np.asarray(subsets == pool, dtype=bool)


def _strata_rule(config: Mapping[str, object], level: str, pool: str) -> str | None:
    """Role strata at the two player levels; at ``team_match`` one stratum or the team
    with most crosswalked matches against its opponents."""
    rule = config["rank_strata"][level]
    if isinstance(rule, Mapping):
        rule = rule[pool]
    if rule not in ((_TEAM_STRATA, None) if level == _TEAM_MATCH else (_ROLE_STRATA,)):
        raise ValueError("rank_strata names a stratification not implemented here")
    return rule


def _stratum_minimum(config: Mapping[str, object], level: str, pool: str) -> int | None:
    value = config["minimum_units_per_rank_stratum"][level][pool]
    if (value is None) != (_strata_rule(config, level, pool) is None):
        raise ValueError("minimum_units_per_rank_stratum is null exactly where no strata are")
    return None if value is None else int(value)


def _labels(strata: np.ndarray) -> np.ndarray:
    return np.array([str(label) for label in np.asarray(strata).tolist()], dtype=object)


def _mean(values: np.ndarray) -> float:
    return float(np.mean(values)) if len(values) else math.nan


def _sd(values: np.ndarray) -> float:
    return float(np.std(values, ddof=1)) if len(values) >= 2 else math.nan


def _interval(values: np.ndarray, config: Mapping[str, object]) -> tuple[float, float]:
    low, high = np.quantile(values, [float(q) for q in config["interval_quantiles"]],
                            method=str(config["interval_quantile_method"]))
    return float(low), float(high)


def _columns(axis: np.ndarray, keys: np.ndarray, what: str) -> np.ndarray:
    """Positions of ``keys`` on an ascending axis; every key must be on it."""
    axis = np.asarray(axis)
    if not _ascending(axis):
        raise ValueError(f"the {what} axis must be ascending and distinct")
    positions = np.searchsorted(axis, keys)
    if not (np.all(positions < len(axis)) and np.array_equal(axis[positions], keys)):
        raise ValueError(f"a key is not on the {what} axis")
    return positions


# --- the panel ------------------------------------------------------------------------

def _grid(frame: pd.DataFrame, players: np.ndarray, matches: np.ndarray
          ) -> tuple[np.ndarray, np.ndarray]:
    if frame.duplicated(["match_key", "player_key"]).any():
        raise ValueError("a player-match holds two input rows")
    rows = _columns(players, frame["player_key"].to_numpy(dtype=np.int64), "paired player")
    columns = _columns(matches, frame["match_key"].to_numpy(dtype=np.int64), "linked match")
    return rows, columns


def _dense(rows: np.ndarray, columns: np.ndarray, values: np.ndarray, shape: tuple[int, int],
           fill: float) -> np.ndarray:
    out = np.full(shape, fill, dtype=np.float64)
    out[rows, columns] = values
    return out


def build_panel(inputs: pd.DataFrame, partner: pd.DataFrame, match_links: pd.DataFrame,
                roles: Mapping[int, str], config: Mapping[str, object]) -> InputPanel:
    """One provider's panel from its ``player_match_inputs`` frame.

    ``partner`` is the other provider's ``player_match_inputs`` frame, read for its
    minutes only; ``roles`` maps every paired outfield player key to his Wyscout role
    code and fixes the player axis; ``match_links`` fixes the match axis. A cell is
    present when both frames hold its row with at least
    ``minimum_regulation_minutes_player_match`` regulation minutes; a row on one
    provider only, or under the minimum on either, is no unit and enters nothing on
    either side. Called once per provider with the two frames swapped, it gives two
    panels with the same axes, presence and teams.
    """
    _frozen(config, "outfield_only_at_player_levels", True)
    minimum = int(config["minimum_regulation_minutes_player_match"])
    minutes = _minutes_key(config)
    if any(role == config["wy_goalkeeper_position"] or role not in config["rank_strata_roles"]
           for role in roles.values()):
        raise ValueError("a panel player is not an outfield player of rank_strata_roles")
    players = np.array(sorted(int(key) for key in roles), dtype=np.int64)
    links = match_links[["match_key", "subset"]].sort_values("match_key", kind="mergesort")
    matches = links["match_key"].to_numpy(dtype=np.int64)
    shape = (len(players), len(matches))

    rows, columns = _grid(inputs, players, matches)
    other_rows, other_columns = _grid(partner, players, matches)
    own = _dense(rows, columns, inputs[minutes].to_numpy(dtype=np.float64), shape, math.nan)
    other = _dense(other_rows, other_columns, partner[minutes].to_numpy(dtype=np.float64),
                   shape, math.nan)
    present = (own >= minimum) & (other >= minimum)
    teams = _dense(rows, columns, inputs["team_key"].to_numpy(dtype=np.float64), shape, 0.0)
    other_teams = _dense(other_rows, other_columns,
                         partner["team_key"].to_numpy(dtype=np.float64), shape, 0.0)
    if np.any(teams[present] != other_teams[present]):
        raise ValueError("the two providers place a present player-match in different teams")

    keys = [str(entry["key"]) for entry in config["player_match_inputs"]
            if entry["key"] in inputs.columns]
    if minutes not in keys:
        raise ValueError("the inputs frame has no minutes column")
    values = {key: np.where(present, _dense(rows, columns,
                                            inputs[key].to_numpy(dtype=np.float64),
                                            shape, 0.0), 0.0)
              for key in keys}
    return InputPanel(
        players=players,
        matches=matches,
        subset_of_match=links["subset"].to_numpy(dtype=object),
        team_of_player_match=np.where(present, teams, 0.0).astype(np.int64),
        role_of_player=np.array([roles[int(player)] for player in players], dtype=object),
        present=present,
        values=values,
    )


def _aligned(statsbomb: InputPanel, wyscout: InputPanel) -> None:
    if not (np.array_equal(statsbomb.players, wyscout.players)
            and np.array_equal(statsbomb.matches, wyscout.matches)
            and np.array_equal(statsbomb.subset_of_match, wyscout.subset_of_match)
            and np.array_equal(statsbomb.role_of_player, wyscout.role_of_player)
            and np.array_equal(statsbomb.present, wyscout.present)
            and np.array_equal(statsbomb.team_of_player_match, wyscout.team_of_player_match)):
        raise ValueError("the two providers' panels do not share axes, presence and teams")


def cluster_of_player(panel: InputPanel, minutes_wyscout: np.ndarray, *, pool: str) -> np.ndarray:
    """Each player's bootstrap cluster in ``pool``: the team with most Wyscout
    regulation minutes over his present cells in the pool's matches, ties to the
    smallest Wyscout team id; 0 for a player with no present cell there.

    ``minutes_wyscout`` is the Wyscout panel's ``minutes_regulation``. The pooled pool
    is every match, a subset pool its own; the callers check the pool against config.
    """
    if minutes_wyscout.shape != panel.present.shape:
        raise ValueError("minutes_wyscout must be players x matches")
    in_pool = (np.ones(len(panel.matches), dtype=bool) if pool == _POOLED
               else np.asarray(panel.subset_of_match == pool, dtype=bool))
    rows, columns = np.nonzero(panel.present & in_pool[None, :])
    totals = pd.DataFrame({
        "player": rows,
        "team": panel.team_of_player_match[rows, columns],
        "minutes": minutes_wyscout[rows, columns],
    }).groupby(["player", "team"], as_index=False)["minutes"].sum()
    best = totals.sort_values(["player", "minutes", "team"], ascending=[True, False, True],
                              kind="mergesort").drop_duplicates("player")
    cluster = np.zeros(len(panel.players), dtype=np.int64)
    cluster[best["player"].to_numpy(dtype=np.int64)] = best["team"].to_numpy(dtype=np.int64)
    return cluster


# --- statistics -----------------------------------------------------------------------

def _weighted_ranks(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """``rank_i = sum w_j [x_j < x_i] + (sum w_j [x_j = x_i] + 1) / 2`` under each row
    of ``weights`` (replicates x units)."""
    ranks = np.empty(weights.shape, dtype=np.float64)
    if len(values) == 0:
        return ranks
    order = np.argsort(values, kind="mergesort")
    ordered = values[order]
    first = np.concatenate(([True], ordered[1:] != ordered[:-1]))
    group = np.cumsum(first) - 1
    sums = np.add.reduceat(weights[:, order], np.flatnonzero(first), axis=1)
    below = np.cumsum(sums, axis=1) - sums
    ranks[:, order] = below[:, group] + (sums[:, group] + 1.0) / 2.0
    return ranks


def _constant(values: np.ndarray, positive: np.ndarray) -> np.ndarray:
    """True per row where every unit of positive weight holds the same value."""
    if values.shape[1] == 0:
        return np.ones(values.shape[0], dtype=bool)
    high = np.where(positive, values, -np.inf).max(axis=1)
    low = np.where(positive, values, np.inf).min(axis=1)
    return ~(high > low)


def _weighted_pearson(a: np.ndarray, b: np.ndarray, weights: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        total = weights.sum(axis=1)
        da = a - ((weights * a).sum(axis=1) / total)[:, None]
        db = b - ((weights * b).sum(axis=1) / total)[:, None]
        spread = (weights * da * da).sum(axis=1) * (weights * db * db).sum(axis=1)
        result = (weights * da * db).sum(axis=1) / np.sqrt(spread)
    result[~(spread > 0)] = np.nan
    return result


def _order_rows(x: np.ndarray, y: np.ndarray, strata: np.ndarray, weights: np.ndarray,
                config: Mapping[str, object]) -> np.ndarray:
    """The order statistic under each row of ``weights``, every stratum of ``strata``
    kept: ranks inside each stratum per side, ``u = (rank - offset) / sum w``, and the
    weighted Pearson correlation of the pooled ``u``. A stratum with zero total weight
    contributes no unit. NaN with fewer than ``order_statistic_minimum_units`` units of
    positive weight or a constant pooled ``u`` on either side."""
    offset = float(config["fractional_rank_offset"])
    ux = np.zeros(weights.shape, dtype=np.float64)
    uy = np.zeros(weights.shape, dtype=np.float64)
    for label in np.unique(strata):
        columns = np.flatnonzero(strata == label)
        block = weights[:, columns]
        total = block.sum(axis=1, keepdims=True)
        scale = np.where(total > 0, total, 1.0)
        ux[:, columns] = (_weighted_ranks(x[columns], block) - offset) / scale
        uy[:, columns] = (_weighted_ranks(y[columns], block) - offset) / scale
    positive = weights > 0
    result = _weighted_pearson(ux, uy, weights)
    undefined = ((positive.sum(axis=1) < int(config["order_statistic_minimum_units"]))
                 | _constant(ux, positive) | _constant(uy, positive))
    result[undefined] = np.nan
    return result


def _weights_of(weights: np.ndarray | None, units: int) -> np.ndarray:
    if weights is None:
        return np.ones(units, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if weights.shape != (units,) or not np.all(np.isfinite(weights)) or np.any(weights < 0):
        raise ValueError("weights must be finite, non-negative and one per unit")
    return weights


def stratified_rank_correlation(x: np.ndarray, y: np.ndarray, strata: np.ndarray,
                                weights: np.ndarray | None, config: Mapping[str, object],
                                *, minimum_stratum_units: int | None
                                ) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    """The order statistic and the strata it retained and dropped (labels, sorted).

    Among finite pairs of positive weight, a stratum with fewer than
    ``minimum_stratum_units`` units is dropped, never when ``strata`` is constant or
    the minimum is None. Inside each retained stratum, per side, weighted average
    ranks give ``u = (rank - fractional_rank_offset) / sum w`` (unit weights when
    ``weights`` is None); the result is the weighted Pearson correlation of the
    pooled ``(u_x, u_y)``. NaN with fewer than ``order_statistic_minimum_units`` units,
    a constant pooled ``u``, or, where strata are defined (the minimum is not None),
    fewer than ``minimum_rank_strata`` retained. One stratum and unit weights give
    Spearman's coefficient on average ranks.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    labels = _labels(strata)
    if not (x.shape == y.shape == labels.shape) or x.ndim != 1:
        raise ValueError("x, y and strata must be aligned vectors")
    weight = _weights_of(weights, len(x))
    keep = np.isfinite(x) & np.isfinite(y) & (weight > 0)
    counts = pd.Series(labels[keep], dtype=object).value_counts()
    distinct = sorted(str(label) for label in counts.index)
    if minimum_stratum_units is None or len(distinct) <= 1:
        retained, dropped = distinct, []
    else:
        retained = [label for label in distinct if counts[label] >= minimum_stratum_units]
        dropped = [label for label in distinct if counts[label] < minimum_stratum_units]
    if (minimum_stratum_units is not None
            and len(retained) < int(config["minimum_rank_strata"])):
        return math.nan, tuple(retained), tuple(dropped)
    keep &= np.isin(labels, retained)
    statistic = _order_rows(x[keep], y[keep], labels[keep], weight[keep][None, :], config)[0]
    return float(statistic), tuple(retained), tuple(dropped)


def _concordance_rows(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        total = weights.sum(axis=1)
        mean_x = (weights * x).sum(axis=1) / total
        mean_y = (weights * y).sum(axis=1) / total
        dx = x[None, :] - mean_x[:, None]
        dy = y[None, :] - mean_y[:, None]
        sxx = (weights * dx * dx).sum(axis=1) / total
        syy = (weights * dy * dy).sum(axis=1) / total
        sxy = (weights * dx * dy).sum(axis=1) / total
        denominator = sxx + syy + (mean_x - mean_y) ** 2
        result = 2.0 * sxy / denominator
    result[~(denominator > 0)] = np.nan
    return result


def _relative_bias_rows(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        total = weights.sum(axis=1)
        bias = (weights * (x - y)).sum(axis=1) / total
        half = ((weights * x).sum(axis=1) / total + (weights * y).sum(axis=1) / total) / 2.0
        result = bias / half
    result[~(half > 0)] = np.nan
    return result


def concordance(x: np.ndarray, y: np.ndarray, weights: np.ndarray | None = None) -> float:
    """Lin's ``2 s_xy / (s_x^2 + s_y^2 + (mean_x - mean_y)^2)``, moments with ``1/n``
    (weighted when given); NaN when the denominator is 0."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.shape != y.shape or x.ndim != 1:
        raise ValueError("x and y must be aligned vectors")
    return float(_concordance_rows(x, y, _weights_of(weights, len(x))[None, :])[0])


def icc_absolute_single(x: np.ndarray, y: np.ndarray) -> float:
    """ICC(2,1): two-way random, absolute agreement, single measure, ``k = 2``:
    ``(MSR - MSE) / (MSR + (k - 1) MSE + k (MSC - MSE) / n)``; NaN below two units or
    on a zero denominator."""
    data = np.column_stack([np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)])
    n, k = data.shape
    if n < 2:
        return math.nan
    grand = data.mean()
    ss_rows = k * float(np.sum((data.mean(axis=1) - grand) ** 2))
    ss_columns = n * float(np.sum((data.mean(axis=0) - grand) ** 2))
    ss_error = float(np.sum((data - grand) ** 2)) - ss_rows - ss_columns
    ms_rows = ss_rows / (n - 1)
    ms_columns = ss_columns / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))
    denominator = ms_rows + (k - 1) * ms_error + k * (ms_columns - ms_error) / n
    return (ms_rows - ms_error) / denominator if denominator != 0 else math.nan


def bland_altman(statsbomb: np.ndarray, wyscout: np.ndarray, z: float) -> BlandAltman:
    """``d = statsbomb - wyscout``: bias, sd (``ddof = 1``), limits ``bias +- z sd``,
    relative bias over the mean of the two provider means (NaN unless that mean is
    strictly positive), ``sd_sb / sd_wy`` and the least-squares slope of ``d`` on the
    pair mean. NaN wherever undefined."""
    sb = np.asarray(statsbomb, dtype=np.float64)
    wy = np.asarray(wyscout, dtype=np.float64)
    if sb.shape != wy.shape or sb.ndim != 1:
        raise ValueError("the two providers' values must be aligned vectors")
    difference = sb - wy
    bias = _mean(difference)
    sd = _sd(difference)
    half = (_mean(sb) + _mean(wy)) / 2.0
    sd_wy = _sd(wy)
    centred = (sb + wy) / 2.0 - _mean((sb + wy) / 2.0)
    spread = float(np.sum(centred ** 2))
    return BlandAltman(
        bias=bias,
        sd=sd,
        lower=bias - z * sd,
        upper=bias + z * sd,
        relative_bias=bias / half if half > 0 else math.nan,
        scale_ratio=_sd(sb) / sd_wy if sd_wy > 0 else math.nan,
        slope=(float(np.sum(centred * (difference - bias))) / spread
               if spread > 0 else math.nan),
    )


# --- the three weight arrays ----------------------------------------------------------

def _generator(config: Mapping[str, object], stream: str) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(
        [int(config["seed"]), int(config["seed_streams"][stream])]))


def block_weights(blocks: np.ndarray, order: Sequence[str], replicates: int,
                  rng: np.random.Generator) -> np.ndarray:
    """``(replicates, len(blocks))`` int16 multinomial weights drawn block by block.

    For each block of ``order``, in that order, ``rng.multinomial(m, [1/m]*m,
    size=replicates)`` is written into its ``m`` columns, in column order; a block
    with no column draws nothing. The run's three arrays are this rule with the
    run's generators; the acceptance run passes its own generator and replicate count.
    """
    blocks = np.asarray(blocks, dtype=object)
    if not set(blocks.tolist()) <= set(order):
        raise ValueError("a column belongs to no block of the order")
    weights = np.zeros((int(replicates), len(blocks)), dtype=np.int16)
    for block in order:
        columns = np.flatnonzero(blocks == block)
        m = len(columns)
        if m == 0:
            continue
        if m > np.iinfo(np.int16).max:
            raise ValueError("a block is too large for int16 weights")
        weights[:, columns] = rng.multinomial(m, [1 / m] * m, size=int(replicates))
    return weights


def match_weights(subset_of_match: np.ndarray, config: Mapping[str, object]) -> np.ndarray:
    """``(bootstrap_replicates, M)`` int16: matches drawn with replacement inside each
    subset, in config order, from the ``match_weights`` stream."""
    _frozen(config, "bootstrap_stratified_by_subset", True)
    return block_weights(subset_of_match, _subset_keys(config),
                         int(config["bootstrap_replicates"]), _generator(config, "match_weights"))


def player_weights(players: int, config: Mapping[str, object]) -> np.ndarray:
    """``(bootstrap_replicates, P)`` int16 from the ``player_weights`` stream; ``P`` is
    every paired outfield player, in the panel's order."""
    rng = _generator(config, "player_weights")
    replicates = int(config["bootstrap_replicates"])
    if players == 0:
        return np.zeros((replicates, 0), dtype=np.int16)
    if players > np.iinfo(np.int16).max:
        raise ValueError("too many players for int16 weights")
    return rng.multinomial(players, [1 / players] * players, size=replicates).astype(np.int16)


def team_weights(teams: np.ndarray, subset_of_team: np.ndarray,
                 config: Mapping[str, object]) -> np.ndarray:
    """``(bootstrap_replicates, T)`` int16 from the ``team_weights`` stream; ``teams``
    are every Wyscout team of a linked match, ascending, and ``subset_of_team`` the
    subset whose matches each plays; teams are drawn inside each subset block."""
    _frozen(config, "bootstrap_stratified_by_subset", True)
    if not _ascending(np.asarray(teams)) or len(teams) != len(subset_of_team):
        raise ValueError("teams must be ascending and distinct, one subset each")
    return block_weights(subset_of_team, _subset_keys(config),
                         int(config["bootstrap_replicates"]), _generator(config, "team_weights"))


# --- cells ----------------------------------------------------------------------------

def aggregated_values(panel: InputPanel, quantity: Mapping[str, object],
                      config: Mapping[str, object], *, pool: str, exposure: int,
                      match_weight: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Each player's aggregate over his present cells in the pool's matches, and
    whether it is defined.

    ``num``, ``den`` and minutes are the input arrays times ``w`` (all ones unless
    ``match_weight``, the sensitivity scheme's one replicate, is given): a ratio of
    sums. Defined requires minutes at or above ``exposure`` and, when the quantity
    has one, ``den >= minimum_denominator``; ``value = scale num / den``, NaN where not
    defined (a hole, never a zero). The caller requires defined on both providers.
    """
    _frozen(config, "exposure_applies_to", _EXPOSURE_RULE)
    weight = _in_pool(panel.subset_of_match, pool, config).astype(np.float64)
    if match_weight is not None:
        if np.shape(match_weight) != weight.shape:
            raise ValueError("match_weight must be one replicate's weight per match")
        weight = weight * np.asarray(match_weight, dtype=np.float64)
    numerator = panel.values[str(quantity["numerator"])] @ weight
    denominator = panel.values[str(quantity["denominator"])] @ weight
    minutes = panel.values[_minutes_key(config)] @ weight
    defined = minutes >= exposure
    if "minimum_denominator" in quantity:
        defined &= denominator >= float(quantity["minimum_denominator"])
    if np.any(denominator[defined] <= 0):
        raise ValueError("a defined aggregate has no positive denominator")
    value = np.full(len(panel.players), np.nan)
    value[defined] = float(quantity["scale"]) * numerator[defined] / denominator[defined]
    return value, defined


def _reads_surface(quantity: Mapping[str, object], config: Mapping[str, object]) -> bool:
    kinds = {str(entry["key"]): str(entry["kind"]) for entry in config["player_match_inputs"]}
    if "kind" in quantity and quantity["kind"] == "xt_sum":
        return True
    return "numerator" in quantity and kinds.get(str(quantity["numerator"])) == "xt_sum"


def applicable_gates(failed_gates: Sequence[str], quantity: Mapping[str, object],
                     config: Mapping[str, object], *, level: str) -> tuple[str, ...]:
    """The failed gates that reach one cell, in precedence order: a gate that stops
    the run reaches every cell, ``IDENTITY_COVERAGE`` the two player levels,
    ``XT_SURFACE`` inputs of kind ``xt_sum`` and quantities whose numerator is one."""
    if not set(failed_gates) <= set(_GATES):
        raise ValueError("failed_gates holds a code that is not a gate")
    reach = {
        **{gate: True for gate in _STOPPING_GATES},
        "IDENTITY_COVERAGE": level in _PLAYER_LEVELS,
        "XT_SURFACE": _reads_surface(quantity, config),
    }
    return tuple(gate for gate in config["inconclusive_reason_precedence"]
                 if gate in failed_gates and reach[gate])


@dataclass(frozen=True)
class _Cohort:
    """The units of one cell at its point estimate. ``players`` and ``matches`` are
    panel positions (``matches`` holds match keys at the team level); ``clusters``
    are team ids at the aggregated level."""

    x: np.ndarray
    y: np.ndarray
    strata: np.ndarray
    minimum: int | None
    players: np.ndarray | None
    matches: np.ndarray | None
    clusters: np.ndarray | None


def _aggregated_cohort(statsbomb: InputPanel, wyscout: InputPanel,
                       quantity: Mapping[str, object], config: Mapping[str, object], *,
                       pool: str, exposure: int, role: str | None) -> _Cohort:
    _aligned(statsbomb, wyscout)
    x, defined_x = aggregated_values(statsbomb, quantity, config, pool=pool, exposure=exposure)
    y, defined_y = aggregated_values(wyscout, quantity, config, pool=pool, exposure=exposure)
    units = defined_x & defined_y
    if role is not None:
        units &= wyscout.role_of_player == role
    index = np.flatnonzero(units)
    clusters = cluster_of_player(wyscout, wyscout.values[_minutes_key(config)], pool=pool)
    _strata_rule(config, _AGGREGATED, pool)
    return _Cohort(x=x[index], y=y[index], strata=_labels(wyscout.role_of_player[index]),
                   minimum=None if role is not None else _stratum_minimum(config, _AGGREGATED,
                                                                         pool),
                   players=index, matches=None, clusters=clusters[index])


def _player_match_cohort(statsbomb: InputPanel, wyscout: InputPanel,
                         quantity: Mapping[str, object], config: Mapping[str, object], *,
                         pool: str) -> _Cohort:
    _aligned(statsbomb, wyscout)
    key = str(quantity["key"])
    in_pool = _in_pool(statsbomb.subset_of_match, pool, config)
    players, matches = np.nonzero(statsbomb.present & in_pool[None, :])
    _strata_rule(config, _PLAYER_MATCH, pool)
    return _Cohort(x=statsbomb.values[key][players, matches],
                   y=wyscout.values[key][players, matches],
                   strata=_labels(wyscout.role_of_player[players]),
                   minimum=_stratum_minimum(config, _PLAYER_MATCH, pool),
                   players=players, matches=matches, clusters=None)


def _team_values(frame: pd.DataFrame, quantity: Mapping[str, object]
                 ) -> tuple[np.ndarray, np.ndarray]:
    if quantity["kind"] != "ratio":
        values = frame[str(quantity["key"])].to_numpy(dtype=np.float64)
        return values, np.isfinite(values)
    numerator = frame[str(quantity["numerator"])].to_numpy(dtype=np.float64)
    denominator = frame[str(quantity["denominator"])].to_numpy(dtype=np.float64)
    defined = denominator >= float(quantity["minimum_denominator"])
    values = np.full(len(frame), np.nan)
    values[defined] = numerator[defined] / denominator[defined]
    return values, defined


def _team_cohort(statsbomb: pd.DataFrame, wyscout: pd.DataFrame,
                 quantity: Mapping[str, object], config: Mapping[str, object], *,
                 pool: str) -> _Cohort:
    keys = ["match_key", "team_key"]
    for frame in (statsbomb, wyscout):
        if frame.duplicated(keys).any():
            raise ValueError("a team-match holds two rows")
    sb_rows = statsbomb.sort_values(keys, kind="mergesort", ignore_index=True)
    wy_rows = wyscout.sort_values(keys, kind="mergesort", ignore_index=True)
    if not (np.array_equal(sb_rows[keys].to_numpy(dtype=np.int64),
                           wy_rows[keys].to_numpy(dtype=np.int64))
            and np.array_equal(sb_rows["subset"].to_numpy(dtype=object),
                               wy_rows["subset"].to_numpy(dtype=object))):
        raise ValueError("the two providers' team-match rows differ")
    in_pool = _in_pool(wy_rows["subset"].to_numpy(dtype=object), pool, config)
    x, defined_x = _team_values(sb_rows, quantity)
    y, defined_y = _team_values(wy_rows, quantity)
    units = np.flatnonzero(in_pool & defined_x & defined_y)
    teams = wy_rows["team_key"].to_numpy(dtype=np.int64)
    rule = _strata_rule(config, _TEAM_MATCH, pool)
    if rule is None:
        strata = np.full(len(units), _ONE_STRATUM, dtype=object)
    else:
        # The team with most crosswalked matches in the pool, ties to the smallest id,
        # against its opponents.
        played = pd.Series(teams[in_pool]).value_counts()
        most = int(min(played[played == played.max()].index)) if len(played) else 0
        strata = np.where(teams[units] == most, _TEAM_LABEL, _OPPONENT_LABEL).astype(object)
    return _Cohort(x=x[units], y=y[units], strata=strata,
                   minimum=_stratum_minimum(config, _TEAM_MATCH, pool), players=None,
                   matches=wy_rows["match_key"].to_numpy(dtype=np.int64)[units], clusters=None)


def _agreement(cohort: _Cohort, quantity: Mapping[str, object], config: Mapping[str, object],
               *, level: str) -> Agreement:
    x, y = cohort.x, cohort.y
    order, retained, dropped = stratified_rank_correlation(
        x, y, cohort.strata, None, config, minimum_stratum_units=cohort.minimum)
    spearman, _, _ = stratified_rank_correlation(
        x, y, np.full(len(x), _ONE_STRATUM, dtype=object), None, config,
        minimum_stratum_units=None)
    exact = None
    if level == _PLAYER_MATCH and quantity["kind"] == "count":
        exact = float(np.mean(x == y)) if len(x) else math.nan
    return Agreement(
        units=len(x), strata_retained=retained, strata_dropped=dropped,
        mean_sb=_mean(x), mean_wy=_mean(y), sd_sb=_sd(x), sd_wy=_sd(y),
        order=order, spearman_unstratified=spearman,
        concordance=concordance(x, y), icc_absolute_single=icc_absolute_single(x, y),
        bland_altman=bland_altman(x, y, float(config["bland_altman_z"])),
        exact_share=exact,
    )


def _scheme(config: Mapping[str, object], level: str, scheme: str, graded: bool) -> None:
    _frozen(config, "bootstrap_scheme", _SCHEMES)
    _frozen(config, "bootstrap_sensitivity_scheme", _SENSITIVITY_SCHEMES)
    if scheme not in (_SCHEMES[level], _SENSITIVITY_SCHEMES.get(level)):
        raise ValueError("not a resampling scheme of this level")
    if graded and scheme != _SCHEMES[level]:
        raise ValueError("a graded cell uses its level's primary scheme")


def _axis(weights: Mapping[str, np.ndarray], name: str, keys: np.ndarray) -> np.ndarray:
    """The weight array ``name``, whose column keys must be ``keys`` exactly: one shared
    world for both providers and every quantity."""
    if not np.array_equal(np.asarray(weights[_AXES[name]]), keys):
        raise ValueError(f"the {name} weight columns are not the panel's {_AXES[name]}")
    return weights[name]


def _resample(cohort: _Cohort, statsbomb: InputPanel | pd.DataFrame,
              wyscout: InputPanel | pd.DataFrame, quantity: Mapping[str, object],
              config: Mapping[str, object], *, level: str, pool: str, exposure: int | None,
              role: str | None, scheme: str, weights: Mapping[str, np.ndarray],
              retained: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Order statistic, concordance and relative bias of every replicate."""
    if level == _AGGREGATED and scheme == _PIGEONHOLE:
        return _recomputed_replicates(statsbomb, wyscout, quantity, config, pool=pool,
                                      exposure=int(exposure), role=role, weights=weights,
                                      retained=retained)
    factors: list[tuple[np.ndarray, np.ndarray]]
    if scheme == _FIXED_COHORT:
        _frozen(config, "bootstrap_cluster_aggregated_player", _CLUSTER_RULE)
        factors = [(weights["team"], _columns(weights[_AXES["team"]], cohort.clusters, "team"))]
    elif level == _TEAM_MATCH:
        factors = [(weights["match"],
                    _columns(weights[_AXES["match"]], cohort.matches, "match"))]
    else:
        match = _axis(weights, "match", statsbomb.matches)
        factors = [(match, cohort.matches)]
        if scheme == _PIGEONHOLE:
            factors.append((_axis(weights, "player", statsbomb.players), cohort.players))
    if len({array.shape[0] for array, _ in factors}) != 1:
        raise ValueError("the weight arrays hold different numbers of replicates")
    return _fixed_replicates(cohort, factors, retained, config)


def _fixed_replicates(cohort: _Cohort, factors: Sequence[tuple[np.ndarray, np.ndarray]],
                      retained: tuple[str, ...], config: Mapping[str, object]
                      ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Units and values fixed; each replicate only reweights them."""
    count = factors[0][0].shape[0]
    keep = np.isin(cohort.strata, list(retained))
    order = np.full(count, np.nan)
    agreement = np.full(count, np.nan)
    relative = np.full(count, np.nan)
    for start in range(0, count, _CHUNK):
        stop = min(count, start + _CHUNK)
        block = np.ones((stop - start, len(cohort.x)), dtype=np.float64)
        for array, columns in factors:
            block = block * array[start:stop][:, columns].astype(np.float64)
        order[start:stop] = _order_rows(cohort.x[keep], cohort.y[keep], cohort.strata[keep],
                                        block[:, keep], config)
        agreement[start:stop] = _concordance_rows(cohort.x, cohort.y, block)
        relative[start:stop] = _relative_bias_rows(cohort.x, cohort.y, block)
    return order, agreement, relative


def _recomputed_replicates(statsbomb: InputPanel, wyscout: InputPanel,
                           quantity: Mapping[str, object], config: Mapping[str, object], *,
                           pool: str, exposure: int, role: str | None,
                           weights: Mapping[str, np.ndarray], retained: tuple[str, ...]
                           ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The aggregated sensitivity scheme: each replicate re-aggregates under its match
    weights, recomputes the gates and weights each defined player by his player
    weight; the retained strata are the point estimate's."""
    match = _axis(weights, "match", statsbomb.matches)
    player = _axis(weights, "player", statsbomb.players)
    if match.shape[0] != player.shape[0]:
        raise ValueError("the weight arrays hold different numbers of replicates")
    count = match.shape[0]
    roles = _labels(wyscout.role_of_player)
    order = np.full(count, np.nan)
    agreement = np.full(count, np.nan)
    relative = np.full(count, np.nan)
    for replicate in range(count):
        x, defined_x = aggregated_values(statsbomb, quantity, config, pool=pool,
                                         exposure=exposure, match_weight=match[replicate])
        y, defined_y = aggregated_values(wyscout, quantity, config, pool=pool,
                                         exposure=exposure, match_weight=match[replicate])
        units = defined_x & defined_y
        if role is not None:
            units &= roles == role
        index = np.flatnonzero(units)
        weight = player[replicate, index].astype(np.float64)[None, :]
        keep = np.isin(roles[index], list(retained))
        order[replicate] = _order_rows(x[index][keep], y[index][keep], roles[index][keep],
                                       weight[:, keep], config)[0]
        agreement[replicate] = _concordance_rows(x[index], y[index], weight)[0]
        relative[replicate] = _relative_bias_rows(x[index], y[index], weight)[0]
    return order, agreement, relative


def cell_agreement(statsbomb: InputPanel | pd.DataFrame | None,
                   wyscout: InputPanel | pd.DataFrame | None, quantity: Mapping[str, object],
                   config: Mapping[str, object], *, level: str, pool: str, reader: str,
                   valuation: str, scheme: str, weights: Mapping[str, np.ndarray],
                   exposure: int | None, graded: bool,
                   failed_gates: Sequence[str] = ()) -> CellResult:
    """Point estimate, replicate intervals and, when ``graded``, the token of one cell:
    ``cell_with_replicates`` without the replicates."""
    return cell_with_replicates(statsbomb, wyscout, quantity, config, level=level, pool=pool,
                                reader=reader, valuation=valuation, scheme=scheme,
                                weights=weights, exposure=exposure, graded=graded,
                                failed_gates=failed_gates)[0]


def cell_with_replicates(statsbomb: InputPanel | pd.DataFrame | None,
                         wyscout: InputPanel | pd.DataFrame | None,
                         quantity: Mapping[str, object], config: Mapping[str, object], *,
                         level: str, pool: str, reader: str, valuation: str, scheme: str,
                         weights: Mapping[str, np.ndarray], exposure: int | None, graded: bool,
                         failed_gates: Sequence[str] = ()
                         ) -> tuple[CellResult, np.ndarray | None]:
    """Point estimate, replicate intervals and, when ``graded``, the token of one cell,
    with the order statistic of every replicate (NaN where invalid), or None when a gate
    that reaches the cell failed and nothing was computed. ``subset_difference`` reads
    the replicates of two cells of the same world.

    ``statsbomb`` and ``wyscout`` are the two ``InputPanel`` objects at the player levels and
    the two ``team_match_inputs`` frames at ``team_match``; both may be None when a
    gate that reaches the cell failed, since nothing is then computed. ``exposure``
    is the aggregated level's minutes gate and None elsewhere. ``weights`` holds the
    run's shared arrays and their column keys: ``match`` with ``matches``, ``player``
    with ``players``, ``team`` with ``teams``. Replicate ``b`` by ``scheme``:
    ``team_cluster_fixed_cohort`` weights the point estimate's units and aggregates by
    ``team[b, cluster]``; ``pigeonhole_match_by_player`` weights a present cell by
    ``match[b, m] * player[b, p]`` at ``player_match`` and, at the aggregated level,
    re-aggregates with ``match[b]``, recomputes the gates and weights by
    ``player[b, p]``; ``match_cluster`` weights a team-match or a present cell by
    ``match[b, m]``. The retained strata are the point estimate's.

    A quantity mapping with a ``role`` key asks for the ungraded ``role_<code>`` row:
    that role's units only, as one stratum with no stratum minimum.
    """
    _frozen(config, "order_statistic", "stratified_rank_correlation")
    _frozen(config, "difference_direction", "statsbomb_minus_wyscout")
    if level not in config["levels"]:
        raise ValueError("unknown level")
    _scheme(config, level, scheme, graded)
    role = str(quantity["role"]) if "role" in quantity else None
    if role is not None and (level != _AGGREGATED or graded
                             or role not in config["rank_strata_roles"]):
        raise ValueError("a role row is an ungraded aggregated row of a rank_strata role")
    if (exposure is None) != (level != _AGGREGATED):
        raise ValueError("an exposure gate is given at the aggregated level only")
    label = {"quantity": str(quantity["key"]), "level": level, "pool": pool, "reader": reader,
             "valuation": valuation, "exposure_minutes": exposure}
    minimum_units = int(config["minimum_units"][level][pool])

    gates = applicable_gates(failed_gates, quantity, config, level=level)
    if gates:
        verdict, reason, flags = (None, None, ())
        if graded:
            verdict, reason, flags = classify(
                failed_gates=gates, units=0, minimum_units=minimum_units,
                strata_defined=False, strata_retained=0, nonzero_statsbomb=0,
                nonzero_wyscout=0, nonzero_both=0, constant_statsbomb=False,
                constant_wyscout=False, valid_share=0.0, order_point=math.nan,
                order_interval=None, concordance_interval=None,
                relative_bias_interval=None, config=config)
        return CellResult(**label, point=None, order_interval=None, concordance_interval=None,
                          relative_bias_interval=None, replicate_mean_minus_point=None,
                          concordance_cross_check_gap=None, valid_replicates=0,
                          verdict=verdict, reason=reason, flags=flags), None

    if level == _AGGREGATED:
        cohort = _aggregated_cohort(statsbomb, wyscout, quantity, config, pool=pool,
                                    exposure=int(exposure), role=role)
    elif level == _PLAYER_MATCH:
        cohort = _player_match_cohort(statsbomb, wyscout, quantity, config, pool=pool)
    else:
        cohort = _team_cohort(statsbomb, wyscout, quantity, config, pool=pool)
    point = _agreement(cohort, quantity, config, level=level)
    order, agreement, relative = _resample(
        cohort, statsbomb, wyscout, quantity, config, level=level, pool=pool,
        exposure=exposure, role=role, scheme=scheme, weights=weights,
        retained=point.strata_retained)

    valid = np.isfinite(order)
    count = len(order)
    any_valid = bool(valid.any())
    gap = None
    if _finite(point.concordance) and _finite(point.icc_absolute_single):
        gap = (abs(point.concordance - point.icc_absolute_single)
               > float(config["ccc_icc_cross_check_tolerance"]))
    result = {
        **label,
        "point": point,
        "order_interval": _interval(order[valid], config) if any_valid else None,
        "concordance_interval": _interval(agreement[valid], config) if any_valid else None,
        "relative_bias_interval": _interval(relative[valid], config) if any_valid else None,
        "replicate_mean_minus_point": (float(np.mean(order[valid]) - point.order)
                                       if any_valid and _finite(point.order) else None),
        "concordance_cross_check_gap": gap,
        "valid_replicates": int(valid.sum()),
    }
    if not graded:
        return CellResult(**result, verdict=None, reason=None, flags=()), order
    x, y = cohort.x, cohort.y
    verdict, reason, flags = classify(
        failed_gates=(), units=point.units, minimum_units=minimum_units,
        strata_defined=cohort.minimum is not None, strata_retained=len(point.strata_retained),
        nonzero_statsbomb=int(np.count_nonzero(x)), nonzero_wyscout=int(np.count_nonzero(y)),
        nonzero_both=int(np.count_nonzero((x != 0) & (y != 0))),
        constant_statsbomb=len(x) > 0 and bool(np.all(x == x[0])),
        constant_wyscout=len(y) > 0 and bool(np.all(y == y[0])),
        valid_share=int(valid.sum()) / count if count else 0.0,
        order_point=point.order, order_interval=result["order_interval"],
        concordance_interval=result["concordance_interval"],
        relative_bias_interval=result["relative_bias_interval"], config=config)
    return CellResult(**result, verdict=verdict, reason=reason, flags=flags), order


def subset_difference(world_cup: CellResult, la_liga: CellResult,
                      world_cup_orders: np.ndarray | None, la_liga_orders: np.ndarray | None,
                      config: Mapping[str, object]) -> dict[str, object] | None:
    """The order statistic of a subset cell minus that of the other subset's cell of the
    same quantity, level, reader and valuation, with its interval: ``np.quantile`` at
    ``interval_quantiles`` of the per-replicate difference over the replicates valid in
    both cells (the same world, so replicate ``b`` is one draw for both). Null when
    either cell is ``INCONCLUSIVE`` or ungraded; the interval is null when no replicate
    is valid in both."""
    if (world_cup.verdict in (None, _INCONCLUSIVE) or la_liga.verdict in (None, _INCONCLUSIVE)
            or world_cup.point is None or la_liga.point is None
            or world_cup_orders is None or la_liga_orders is None):
        return None
    if world_cup_orders.shape != la_liga_orders.shape:
        raise ValueError("the two cells were not resampled in one world")
    both = np.isfinite(world_cup_orders) & np.isfinite(la_liga_orders)
    interval = None
    if both.any():
        low, high = _interval(world_cup_orders[both] - la_liga_orders[both], config)
        interval = [low, high]
    return {"difference": _number(world_cup.point.order - la_liga.point.order),
            "interval": interval, "replicates": int(both.sum())}


# --- the decision rule ----------------------------------------------------------------

def _cell_vocabulary(config: Mapping[str, object]) -> None:
    if set(config["verdict_vocabulary"]["cell"]) != _CELL_TOKENS:
        raise ValueError("the cell vocabulary is not the one implemented here")
    precedence = list(config["inconclusive_reason_precedence"])
    if sorted(precedence) != sorted(_GATES + _RULE_REASONS):
        raise ValueError("inconclusive_reason_precedence holds codes not implemented here")
    if list(config["cell_flags"]) != [_OUTSIDE]:
        raise ValueError("cell_flags is not the flag implemented here")


def classify(*, failed_gates: Sequence[str], units: int, minimum_units: int,
             strata_defined: bool, strata_retained: int,
             nonzero_statsbomb: int, nonzero_wyscout: int, nonzero_both: int,
             constant_statsbomb: bool, constant_wyscout: bool, valid_share: float,
             order_point: float, order_interval: tuple[float, float] | None,
             concordance_interval: tuple[float, float] | None,
             relative_bias_interval: tuple[float, float] | None,
             config: Mapping[str, object]) -> tuple[str, str | None, tuple[str, ...]]:
    """The protocol's decision table, rows 1 to 5 in order; the first match wins.

    Row 1 returns ``INCONCLUSIVE`` with the first reason of
    ``inconclusive_reason_precedence`` that holds, the gates being ``failed_gates``.
    Row 2 ``COMPARABLE``: ``L >= T``, ``P >= T``, the concordance lower bound at or
    above ``ccc_lower_bound_minimum`` and the whole relative-bias interval within
    ``+- relative_bias_margin``, bounds inclusive; a NaN or missing bound fails row 2
    only. Row 3 ``COMPARABLE_IN_RANK_ONLY``: ``L >= T`` and ``P >= T``. Row 4
    ``NOT_COMPARABLE``: ``U < T`` and ``P < T``. Row 5 ``NOT_ESTABLISHED``. The flag
    ``POINT_OUTSIDE_INTERVAL`` is set after the token, only past row 1, and changes no
    token. This is the only place a cell token is produced.
    """
    _cell_vocabulary(config)
    _frozen(config, "relative_bias_margin_unit", "fraction of the mean of the two provider means")
    if not set(failed_gates) <= set(_GATES):
        raise ValueError("failed_gates holds a code that is not a gate")
    enough = int(config["minimum_units_nonzero_on_both_providers"])
    holds = {gate: gate in failed_gates for gate in _GATES}
    holds["UNITS"] = units < minimum_units or (
        strata_defined and strata_retained < int(config["minimum_rank_strata"]))
    holds["ONE_SIDED"] = ((nonzero_statsbomb == 0 and nonzero_wyscout >= enough)
                          or (nonzero_wyscout == 0 and nonzero_statsbomb >= enough))
    holds["DEGENERATE"] = constant_statsbomb or constant_wyscout or nonzero_both < enough
    holds["REPLICATES"] = not valid_share >= float(config["minimum_valid_replicate_share"])
    holds["UNDEFINED_STATISTIC"] = not (
        _finite(order_point) and order_interval is not None
        and all(_finite(bound) for bound in order_interval))
    for reason in config["inconclusive_reason_precedence"]:
        if holds[reason]:
            return _INCONCLUSIVE, reason, ()

    threshold = float(config["order_statistic_lower_bound_minimum"])
    margin = float(config["relative_bias_margin"])
    lower, upper = order_interval
    ordered = lower >= threshold and order_point >= threshold
    level_agrees = (
        concordance_interval is not None and _finite(concordance_interval[0])
        and concordance_interval[0] >= float(config["ccc_lower_bound_minimum"])
        and relative_bias_interval is not None
        and all(_finite(bound) for bound in relative_bias_interval)
        and -margin <= relative_bias_interval[0] and relative_bias_interval[1] <= margin)
    if ordered and level_agrees:
        token = "COMPARABLE"
    elif ordered:
        token = "COMPARABLE_IN_RANK_ONLY"
    elif upper < threshold and order_point < threshold:
        token = "NOT_COMPARABLE"
    else:
        token = "NOT_ESTABLISHED"
    flags = (_OUTSIDE,) if order_point < lower or order_point > upper else ()
    return token, None, flags


# --- controls -------------------------------------------------------------------------

def control_holds(point: float, values: Sequence[float]) -> bool:
    """True iff ``point`` and every value are finite and ``point > max(values)``: a
    tie, a NaN value, a NaN point or no values fail."""
    return (len(values) > 0 and _finite(point) and all(_finite(value) for value in values)
            and point > max(values))


def _identical(a: float, b: float) -> bool:
    return a == b or (math.isnan(a) and math.isnan(b))


def permuted_link_control(statsbomb: InputPanel, wyscout: InputPanel,
                          quantity: Mapping[str, object], headline: CellResult,
                          config: Mapping[str, object]) -> dict[str, object]:
    """The permuted-link control of one aggregated quantity on its headline cell.

    The units and the two aggregates are the point estimate's, recomputed by the same
    calls on unweighted data; inside each (cluster, Wyscout role) stratum the Wyscout
    aggregates are reassigned by ``permuted_partners``, one derangement per seed of
    ``permuted_link_seeds``, and the order statistic is recomputed with unit weights
    on the same units and role strata. No weight array enters. An ``INCONCLUSIVE``
    headline computes nothing: ``values`` empty and the rest null.
    """
    cell = config["registry_headline_cell"]
    for part in ("level", "pool", "reader", "valuation"):
        if config[f"permuted_link_{part}"] != cell[part]:
            raise ValueError(f"permuted_link_{part} is not the registry headline cell's")
    _frozen(config, "permuted_link_cohort", _COHORT_RULE)
    _frozen(config, "bootstrap_cluster_aggregated_player", _CLUSTER_RULE)
    level, pool = str(cell["level"]), str(cell["pool"])
    if (headline.quantity, headline.level, headline.pool, headline.reader,
            headline.valuation) != (str(quantity["key"]), level, pool, cell["reader"],
                                    cell["valuation"]):
        raise ValueError("headline is not the quantity's cell at registry_headline_cell")
    if headline.verdict is None:
        raise ValueError("the headline cell is not graded")
    if headline.verdict == _INCONCLUSIVE:
        return {"values": [], "point": None, "strictly_above_all": None,
                "singleton_players": None}
    exposure = int(config["exposure_minimum_minutes"][pool])
    if headline.point is None or headline.exposure_minutes != exposure:
        raise ValueError("the headline cell carries no point estimate at its pool's exposure")
    cohort = _aggregated_cohort(statsbomb, wyscout, quantity, config, pool=pool,
                                exposure=exposure, role=None)
    point, _, _ = stratified_rank_correlation(cohort.x, cohort.y, cohort.strata, None, config,
                                              minimum_stratum_units=cohort.minimum)
    if not _identical(point, headline.point.order):
        raise ValueError("the recomputed order statistic is not the headline point")
    keys = wyscout.players[cohort.players]
    stratum = list(zip(cohort.clusters.tolist(), cohort.strata.tolist(), strict=True))
    values: list[float] = []
    singletons: set[int] = set()
    for seed in config["permuted_link_seeds"]:
        partner, alone = permuted_partners(keys, stratum, config, seed=int(seed))
        value, _, _ = stratified_rank_correlation(cohort.x, cohort.y[partner], cohort.strata,
                                                  None, config,
                                                  minimum_stratum_units=cohort.minimum)
        values.append(value)
        singletons.add(int(alone))
    if len(singletons) != 1:
        raise ValueError("the singleton count differs between seeds")
    return {
        "values": [_number(value) for value in sorted(values, key=lambda v: (math.isnan(v), v))],
        "point": _number(point),
        "strictly_above_all": control_holds(point, values),
        "singleton_players": singletons.pop(),
    }


def _between_share(sizes: np.ndarray, sums: np.ndarray, means: np.ndarray,
                   within: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """One-way random effects, unbalanced, each player entering as ``w`` groups:
    the between-player share of the variance under each row of ``weights``."""
    with np.errstate(divide="ignore", invalid="ignore"):
        groups = weights.sum(axis=1)
        rows = weights @ sizes
        grand = (weights @ sums) / rows
        between = (weights * (sizes * (means[None, :] - grand[:, None]) ** 2)).sum(axis=1)
        mean_between = between / (groups - 1)
        mean_within = (weights @ within) / (rows - groups)
        n0 = (rows - (weights @ sizes ** 2) / rows) / (groups - 1)
        variance = np.maximum(0.0, (mean_between - mean_within) / n0)
        share = variance / (variance + mean_within)
    undefined = ((groups < 2) | ~(rows - groups > 0) | ~(n0 > 0)
                 | ~(variance + mean_within > 0) | ~np.isfinite(share))
    share[undefined] = np.nan
    return share, groups


def difference_decomposition(statsbomb: InputPanel, wyscout: InputPanel,
                             quantity: Mapping[str, object], team_weight: np.ndarray,
                             config: Mapping[str, object], *, pool: str) -> dict[str, object]:
    """Between-player share of the per-90 provider difference, with a team-cluster
    interval; descriptive, no verdict.

    Rows: present cells of the pool with at least
    ``difference_decomposition_minimum_minutes`` on both providers, of players with
    at least ``difference_decomposition_minimum_matches`` such rows;
    ``d = scale (num_sb / min_sb - num_wy / min_wy)``. Replicate ``b`` enters player
    ``i`` as ``team_weight[b, cluster]`` groups; the columns of ``team_weight`` are
    the Wyscout teams of the panel's present cells, ascending. When the numerator was
    not formed (a failed surface) only ``quantity``, ``pool``, ``rows`` and
    ``players`` are returned.
    """
    _frozen(config, "bootstrap_cluster_aggregated_player", _CLUSTER_RULE)
    minutes = _minutes_key(config)
    if quantity["denominator"] != minutes:
        raise ValueError("the decomposition is defined for per-minute quantities only")
    _aligned(statsbomb, wyscout)
    sb_minutes, wy_minutes = statsbomb.values[minutes], wyscout.values[minutes]
    floor = float(config["difference_decomposition_minimum_minutes"])
    rows = (statsbomb.present & _in_pool(statsbomb.subset_of_match, pool, config)[None, :]
            & (sb_minutes >= floor) & (wy_minutes >= floor))
    players = rows.sum(axis=1) >= int(config["difference_decomposition_minimum_matches"])
    rows &= players[:, None]
    block: dict[str, object] = {"quantity": str(quantity["key"]), "pool": pool,
                                "rows": int(rows.sum()), "players": int(players.sum())}
    numerator = str(quantity["numerator"])
    if numerator not in statsbomb.values or numerator not in wyscout.values:
        return block

    who, where = np.nonzero(rows)
    scale = float(quantity["scale"])
    difference = scale * (statsbomb.values[numerator][who, where] / sb_minutes[who, where]
                          - wyscout.values[numerator][who, where] / wy_minutes[who, where])
    gated = np.flatnonzero(players)
    group = np.searchsorted(gated, who)
    sizes = np.bincount(group, minlength=len(gated)).astype(np.float64)
    sums = np.bincount(group, weights=difference, minlength=len(gated))
    means = np.divide(sums, sizes, out=np.zeros_like(sums), where=sizes > 0)
    within = np.bincount(group, weights=(difference - means[group]) ** 2, minlength=len(gated))
    point, _ = _between_share(sizes, sums, means, within, np.ones((1, len(gated))))

    teams = np.unique(wyscout.team_of_player_match[wyscout.present])
    if team_weight.ndim != 2 or team_weight.shape[1] != len(teams):
        raise ValueError("team_weight columns must be the panel's teams, ascending")
    clusters = cluster_of_player(wyscout, wy_minutes, pool=pool)[gated]
    weight = team_weight[:, _columns(teams, clusters, "team")].astype(np.float64)
    shares, groups = _between_share(sizes, sums, means, within, weight)
    valid = groups >= 2
    interval = None
    if valid.any():
        low, high = _interval(shares[valid], config)
        interval = [_number(low), _number(high)]
    block.update(between_player_share=_number(point[0]), interval=interval)
    return block


# --- admission and the registry ---------------------------------------------------------

def _index(cells: Sequence[CellResult]) -> dict[tuple[str, str, str, str, str], CellResult]:
    index: dict[tuple[str, str, str, str, str], CellResult] = {}
    for cell in cells:
        key = (cell.quantity, cell.level, cell.pool, cell.reader, cell.valuation)
        if key in index:
            raise ValueError("two cells share quantity, level, pool, reader and valuation")
        index[key] = cell
    return index


def _verdict(index: Mapping[tuple[str, str, str, str, str], CellResult], quantity: str,
             level: str, pool: str, reader: str, valuation: str) -> str:
    key = (quantity, level, pool, reader, valuation)
    if key not in index or index[key].verdict not in _CELL_TOKENS:
        raise ValueError("a cell the rule reads is missing or ungraded")
    return str(index[key].verdict)


def _headline(index: Mapping[tuple[str, str, str, str, str], CellResult], quantity: str,
              config: Mapping[str, object], *, pool: str) -> str:
    cell = config["registry_headline_cell"]
    return _verdict(index, quantity, str(cell["level"]), pool, str(cell["reader"]),
                    str(cell["valuation"]))


def control_states(cells: Sequence[CellResult], controls: Mapping[str, object],
                   config: Mapping[str, object]) -> tuple[bool, bool | None]:
    """``positive_passed`` and ``permuted_link_passed``.

    ``positive_passed`` is false iff a cell of ``positive_controls`` (at the graded
    valuation) has a verdict outside ``positive_control_passing_tokens``, which a run
    stopped by a gate always gives. ``permuted_link_passed`` is None when no subject
    of ``registry_cell_subjects`` has an agreeing headline (the control tested
    nothing); otherwise true iff ``strictly_above_all`` is true for every such
    subject. ``controls["permuted_link"]`` maps each quantity to its control.
    """
    index = _index(cells)
    passing = set(config["positive_control_passing_tokens"])
    positive = all(
        _verdict(index, str(entry["quantity"]), str(entry["level"]), str(entry["pool"]),
                 str(entry["reader"]), str(config["graded_valuation"])) in passing
        for entry in config["positive_controls"])
    rule = config["registry_token_rule"]
    agreeing = set(rule["agreeing_tokens"])
    pool = str(config["registry_headline_cell"]["pool"])
    tested = [str(subject) for subject in config["registry_cell_subjects"]
              if _headline(index, str(subject), config, pool=pool) in agreeing]
    if not tested:
        return positive, None
    permuted = controls["permuted_link"]
    return positive, all(permuted[subject]["strictly_above_all"] is True for subject in tested)


def admission(cells: Sequence[CellResult], controls: Mapping[str, object],
              config: Mapping[str, object]) -> dict[str, dict[str, str | None]]:
    """The protocol's admission table for every aggregated quantity.

    ``{status, reason, pooled_verdict, la_liga_verdict}``, from the cells of
    ``admission_rule``; ``reason`` is the first of ``exclusion_reason_precedence``
    that holds, else null. The registry rule does not enter: a quantity is admitted
    or excluded on its own cells and its own permuted-link control.
    """
    rule = config["admission_rule"]
    precedence = list(config["exclusion_reason_precedence"])
    if set(precedence) != _EXCLUSIONS or len(precedence) != len(_EXCLUSIONS):
        raise ValueError("exclusion_reason_precedence holds codes not implemented here")
    effects = rule["la_liga_token_effect"]
    if set(effects) != _CELL_TOKENS or not set(effects.values()) <= _LA_LIGA_EFFECTS:
        raise ValueError("la_liga_token_effect is not the table implemented here")
    statuses = rule["pooled_token_to_status"]
    vocabulary = set(config["admission_vocabulary"])
    index = _index(cells)
    positive, _ = control_states(cells, controls, config)
    permuted = controls["permuted_link"]
    level, reader, valuation = str(rule["level"]), str(rule["reader"]), str(rule["valuation"])
    out: dict[str, dict[str, str | None]] = {}
    for entry in config["aggregated_player_quantities"]:
        key = str(entry["key"])
        pooled = _verdict(index, key, level, str(rule["pooled_pool"]), reader, valuation)
        la_liga = _verdict(index, key, level, str(rule["la_liga_pool"]), reader, valuation)
        effect = effects[la_liga]
        holds = {
            "DECLARED_VARIANT": key in rule["declared_variants_never_admitted"],
            "POSITIVE_CONTROL": not positive,
            "VERDICT": pooled not in statuses,
            "LA_LIGA_SUBSET_CONTRADICTS": effect == "EXCLUDE_LA_LIGA_SUBSET_CONTRADICTS",
            "LA_LIGA_SUBSET_UNTESTED": effect == "EXCLUDE_LA_LIGA_SUBSET_UNTESTED",
            "PERMUTED_LINK_CONTROL": permuted[key]["strictly_above_all"] is not True,
        }
        reason = next((code for code in precedence if holds[code]), None)
        if reason is None:
            status = str(statuses[pooled])
            if effect == "SUFFIX_LEAGUE_UNCONFIRMED":
                status += _UNCONFIRMED
        else:
            status = _EXCLUDED
        if status not in vocabulary:
            raise ValueError("an admission status outside admission_vocabulary")
        out[key] = {"status": status, "reason": reason, "pooled_verdict": pooled,
                    "la_liga_verdict": la_liga}
    return out


def registry_verdicts(cells: Sequence[CellResult], controls: Mapping[str, object],
                      link_blocks: Sequence[Mapping[str, object]],
                      config: Mapping[str, object]) -> dict[str, dict[str, str | None]]:
    """``{subject: {token, reason, second_reason}}`` for every registry subject.

    A cell subject follows ``registry_token_rule``, rows a to c, first match wins,
    ``H`` the verdict of its headline cell and ``S`` that of the same cell in the
    rule's ``la_liga_pool``. Row a: a failed positive control or a failed
    permuted-link control (``control_states``; a null state fails nothing) gives every
    cell subject the row's token and the first failed control of its precedence. Row
    b: an agreeing ``H`` and ``S`` in the row's tokens. Row c: ``H`` with the headline
    reason, and the second reason when ``H`` agrees and ``S`` is one of its tokens. A
    link subject takes the verdict and reason of its tier set's ``link_verdict_pool``
    block; no control enters it. This is the only place a registry token is produced.
    """
    rule = config["registry_token_rule"]
    row_a, row_b, row_c = (rule["row_a_control_failed"], rule["row_b_la_liga_contradicts"],
                           rule["row_c_headline_token"])
    _frozen(row_a, "every_cell_subject", True)
    if sorted(row_a["reason_precedence"]) != sorted(_CONTROLS):
        raise ValueError("row a names controls not implemented here")
    positive, permuted = control_states(cells, controls, config)
    for key, state in (("positive_passed", positive), ("permuted_link_passed", permuted)):
        if key in controls and controls[key] != state:
            raise ValueError(f"controls {key} is not the state of the cells and controls")
    failed = {"POSITIVE_CONTROL": positive is False, "PERMUTED_LINK_CONTROL": permuted is False}
    agreeing = set(rule["agreeing_tokens"])
    cell_reasons = set(config["registry_reason_vocabulary"])
    inconclusive_reasons = set(config["inconclusive_reason_precedence"])
    index = _index(cells)
    headline = config["registry_headline_cell"]
    pool, la_liga_pool = str(headline["pool"]), str(rule["la_liga_pool"])

    out: dict[str, dict[str, str | None]] = {}
    for subject in (str(name) for name in config["registry_cell_subjects"]):
        h = _headline(index, subject, config, pool=pool)
        s = _headline(index, subject, config, pool=la_liga_pool)
        first_failed = next((code for code in row_a["reason_precedence"] if failed[code]), None)
        if first_failed is not None:
            token, reason, second = str(row_a["token"]), first_failed, None
            reasons = cell_reasons
        elif h in agreeing and s in row_b["la_liga_tokens"]:
            token, reason, second = str(row_b["token"]), str(row_b["reason"]), None
            reasons = cell_reasons
        else:
            cell = index[(subject, str(headline["level"]), pool, str(headline["reader"]),
                          str(headline["valuation"]))]
            token, reason = h, cell.reason
            second = (str(row_c["second_reason"])
                      if h in agreeing and s in row_c["second_reason_la_liga_tokens"] else None)
            reasons = inconclusive_reasons
        if token not in _CELL_TOKENS or token not in config["verdict_vocabulary"]["cell"]:
            raise ValueError("a registry token outside the cell vocabulary")
        if (reason is not None and reason not in reasons) or (
                second is not None and second not in cell_reasons):
            raise ValueError("a registry reason outside its frozen vocabulary")
        out[subject] = {"token": token, "reason": reason, "second_reason": second}

    link_reasons = set(config["link_inconclusive_reasons"])
    for subject, tiers in config["registry_link_subjects"].items():
        blocks = [block for block in link_blocks
                  if list(block["tiers"]) == list(tiers)
                  and block["pool"] == config["link_verdict_pool"]]
        if len(blocks) != 1:
            raise ValueError("a link subject has no single verdict-pool block")
        token, reason = blocks[0]["verdict"], blocks[0]["reason"]
        if token not in _LINK_TOKENS or token not in config["verdict_vocabulary"]["link"]:
            raise ValueError("a link token outside the link vocabulary")
        if reason is not None and reason not in link_reasons:
            raise ValueError("a link reason outside link_inconclusive_reasons")
        out[str(subject)] = {"token": str(token), "reason": reason, "second_reason": None}
    return out
