"""Prior-date partial-evidence features for research, not individual player estimates.

A known player's observed opening mean is pooled toward the league broad-role
mean by n / (n + k). An unseen player receives that role mean, not a zero-valued
performance. Counts and means refer only to the player's current team.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

VERSION = "partial-opening-history-v1"
BASE_COLUMNS = [
    "game_id", "team_id", "date", "home", "target", "team_mean", "team_recent",
    "opponent_mean", "role_sum", "lineup_sum", "mean_log1p_count", "unseen_fraction",
    "seen_players", "minimum_prior_openings", "median_prior_openings",
    "maximum_prior_openings", "permutation_singleton_players", "operational_sum",
    "operational_available",
]
AUDIT_COLUMNS = [
    "game_id", "team_id", "date", "accepted", "reasons", "seen_players",
    "mean_log1p_count", "unseen_fraction", "operational_available",
]


def _configuration(config: dict) -> tuple[list[float], list[int]]:
    numeric = []
    for value in config["pooling_grid"]:
        if value == "context_only":
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("pooling strengths must be nonnegative finite numbers")
        if not np.isfinite(value) or value < 0:
            raise ValueError("pooling strengths must be nonnegative finite numbers")
        numeric.append(float(value))
    if not numeric or 0 not in numeric or len(set(numeric)) != len(numeric):
        raise ValueError("pooling_grid must include zero and distinct numeric strengths")
    seeds = config["permutation_seeds"]
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("permutation identifiers must be integers")
    if len(set(seeds)) != len(seeds):
        raise ValueError("permutation identifiers must be distinct")
    if config["minimum_team_windows"] < 1:
        raise ValueError("minimum_team_windows must be positive")
    return numeric, seeds


def _permutation_maps(
    history: pd.DataFrame, *, base_seed: int, seeds: list[int], cutoff: pd.Timestamp
) -> dict[int, dict[tuple[int, int], float]]:
    """Shuffle means, never counts, among all known same-team/same-role players.

    SHA256 input is UTF-8 compact JSON of
    [base_seed, permutation_id, cutoff.date().isoformat(), team_id, position,
    sorted_player_ids]. The first 16 digest bytes interpreted big-endian seed a
    NumPy PCG64 generator. Its permutation indexes the sorted players' means.
    This deterministic identity-link stress test is not an exchangeable p-value.
    Maps are built once per date/stratum, shared by every lineup on that date.
    """
    maps = {seed: {} for seed in seeds}
    for (team_id, position), group in history.groupby(["team_id", "position"], sort=True):
        group = group.sort_values("player_id")
        player_ids = [int(player) for player in group.player_id]
        values = group["mean"].to_numpy(dtype=float)
        for seed in seeds:
            payload = [
                int(base_seed), seed, cutoff.date().isoformat(), int(team_id), position, player_ids
            ]
            digest = hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).digest()
            rng = np.random.Generator(np.random.PCG64(int.from_bytes(digest[:16], "big")))
            donor_values = values[rng.permutation(len(values))]
            maps[seed].update(
                ((int(team_id), player), float(value))
                for player, value in zip(player_ids, donor_values, strict=True)
            )
    return maps


def partial_rows(panel: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build a common primary cohort without individual minutes/start gates.

    Opening quality comes from the E-07 panel. All earlier clean ten-outfielder
    windows contribute history, whether or not eligible for evaluation. Only
    dates strictly before the current CALENDAR date enter features. Static
    provider broad positions are required; these are not inferred tactical roles.

    Optional full-match accounting is retained solely as an explicitly available
    comparator. Missing accounting/exposure cannot exclude a primary cohort row.
    """
    strengths, seeds = _configuration(config)
    residual_columns = [f"residual_{strength:g}" for strength in strengths]
    permutation_columns = [
        f"perm_{seed}_residual_{strength:g}" for seed in seeds for strength in strengths
    ]
    columns = BASE_COLUMNS + residual_columns + permutation_columns + [
        f"perm_{seed}_changed_players" for seed in seeds
    ]
    if panel.empty:
        return pd.DataFrame(columns=columns), pd.DataFrame(columns=AUDIT_COLUMNS)
    if panel.duplicated(["game_id", "player_id"]).any():
        raise ValueError("duplicate player-game observations")
    if not panel.position.isin({"GK", "DF", "MF", "FW"}).all():
        raise ValueError("a known broad position is required for every player")
    if panel.groupby("player_id").position.nunique().gt(1).any():
        raise ValueError("changing player broad-position metadata is unsupported")
    for flag in ("started", "opening_valid", "home"):
        if panel[flag].isna().any() or not panel[flag].isin([True, False]).all():
            raise ValueError(f"{flag} must be an observed boolean")
    panel = panel.copy()
    panel["date"] = pd.to_datetime(panel.date)
    if panel.date.isna().any():
        raise ValueError("every appearance requires a known date")
    panel = panel.sort_values(["date", "game_id", "team_id", "player_id"])
    observed = panel[panel.opening_valid & panel.started & panel.position.ne("GK")]
    if not np.isfinite(observed.opening_xt.to_numpy(dtype=float)).all():
        raise ValueError("valid opening observations must be finite; missing is not zero")
    windows = observed.groupby(["game_id", "team_id"], as_index=False).agg(
        date=("date", "first"), opponent_id=("opponent_id", "first"),
        total=("opening_xt", "sum"), players=("player_id", "nunique"),
    )
    windows = windows[windows.players == 10].sort_values(["date", "game_id", "team_id"])
    # A malformed partial panel must not silently contribute one-sided history.
    keys = set(windows[["game_id", "team_id"]].itertuples(index=False, name=None))
    windows = windows.loc[np.array(
        [(row.game_id, row.opponent_id) in keys for row in windows.itertuples()], dtype=bool
    )]
    clean_keys = set(windows[["game_id", "team_id"]].itertuples(index=False, name=None))
    observed = observed.loc[np.array(
        [key in clean_keys for key in observed[["game_id", "team_id"]].itertuples(
            index=False, name=None
        )], dtype=bool
    )]
    targets = {(int(row.game_id), int(row.team_id)): float(row.total)
               for row in windows.itertuples()}
    rows, audit = [], []
    cached_date = None
    for (date, game_id, team_id), team in panel.groupby(["date", "game_id", "team_id"], sort=True):
        cutoff = date.normalize()
        if cutoff != cached_date:
            prior = panel[panel.date < cutoff]
            prior_observed = observed[observed.date < cutoff]
            prior_windows = windows[windows.date < cutoff]
            role_means = prior_observed.groupby("position").opening_xt.mean()
            history = prior_observed.groupby(
                ["team_id", "player_id", "position"], as_index=False
            ).agg(count=("opening_xt", "size"), mean=("opening_xt", "mean"))
            player_history = {
                (int(row.team_id), int(row.player_id)): (int(row.count), float(row.mean))
                for row in history.itertuples()
            }
            permutations = _permutation_maps(
                history, base_seed=config["seed"], seeds=seeds, cutoff=cutoff
            )
            pool_sizes = history.groupby(["team_id", "position"]).size()
            full_history = {}
            for key, group in prior.groupby(["team_id", "player_id"]):
                minutes = group.nominal_minutes.to_numpy(dtype=float)
                full = group.full_xt.to_numpy(dtype=float)
                usable = (
                    np.isfinite(minutes).all() and (minutes >= 0).all()
                    and minutes.sum() > 0 and np.isfinite(full).all()
                )
                full_history[key] = float(full.sum() / minutes.sum() * 30) if usable else np.nan
            cached_date = cutoff
        starters = team[team.started & team.position.ne("GK")]
        opponent = int(team.iloc[0].opponent_id)
        own_windows = prior_windows[prior_windows.team_id == team_id]
        opponent_windows = prior_windows[prior_windows.team_id == opponent]
        reasons = []
        if len(starters) != 10 or not starters.opening_valid.all() or (
            int(game_id), int(team_id)
        ) not in clean_keys:
            reasons.append("invalid_opening")
        if min(len(own_windows), len(opponent_windows)) < config["minimum_team_windows"]:
            reasons.append("insufficient_team_history")
        role_values = np.array([role_means.get(role, np.nan) for role in starters.position])
        if not np.isfinite(role_values).all():
            reasons.append("unavailable_role_history")
        player_keys = [(int(team_id), int(player)) for player in starters.player_id]
        counts = np.array([player_history.get(key, (0, 0))[0] for key in player_keys])
        means = np.array([player_history.get(key, (0, 0))[1] for key in player_keys])
        full_values = np.array([full_history.get(key, np.nan) for key in player_keys])
        operational_available = len(starters) == 10 and bool(np.isfinite(full_values).all())
        seen = int((counts > 0).sum())
        mean_count = float(np.log1p(counts).mean()) if len(counts) else np.nan
        unseen = float((counts == 0).mean()) if len(counts) else np.nan
        reasons = tuple(sorted(set(reasons)))
        audit.append({
            "game_id": int(game_id), "team_id": int(team_id), "date": date,
            "accepted": not reasons, "reasons": reasons, "seen_players": seen,
            "mean_log1p_count": mean_count, "unseen_fraction": unseen,
            "operational_available": operational_available,
        })
        if reasons:
            continue
        weights = [np.divide(counts, counts + strength, out=np.zeros(10),
                             where=counts + strength > 0) for strength in strengths]
        residuals = [float(np.sum(weight * (means - role_values))) for weight in weights]
        conceded = [targets[(int(row.game_id), int(row.opponent_id))]
                    for row in opponent_windows.itertuples()]
        row = {
            "game_id": int(game_id), "team_id": int(team_id), "date": date,
            "home": bool(team.iloc[0].home), "target": targets[(int(game_id), int(team_id))],
            "team_mean": float(own_windows.total.mean()),
            "team_recent": float(own_windows.tail(5).total.mean()),
            "opponent_mean": float(np.mean(conceded)), "role_sum": float(role_values.sum()),
            "lineup_sum": float(role_values.sum()) + residuals[strengths.index(0)],
            "mean_log1p_count": mean_count, "unseen_fraction": unseen, "seen_players": seen,
            "minimum_prior_openings": int(counts.min()),
            "median_prior_openings": float(np.median(counts)),
            "maximum_prior_openings": int(counts.max()),
            "permutation_singleton_players": sum(
                count > 0 and pool_sizes.get((team_id, position), 0) == 1
                for count, position in zip(counts, starters.position, strict=True)
            ),
            "operational_sum": float(full_values.sum()) if operational_available else np.nan,
            "operational_available": operational_available,
            **dict(zip(residual_columns, residuals, strict=True)),
        }
        for seed in seeds:
            permuted = np.array([permutations[seed].get(key, 0) for key in player_keys])
            row[f"perm_{seed}_changed_players"] = int(((counts > 0) & (means != permuted)).sum())
            for strength, weight in zip(strengths, weights, strict=True):
                row[f"perm_{seed}_residual_{strength:g}"] = float(
                    np.sum(weight * (permuted - role_values))
                )
        required = [column for column in columns if column not in {"date", "operational_sum"}]
        if not all(np.isfinite(row[column]) for column in required):
            raise ValueError("accepted partial-evidence row contains a nonfinite feature")
        rows.append(row)
    return pd.DataFrame(rows, columns=columns), pd.DataFrame(audit, columns=AUDIT_COLUMNS)
