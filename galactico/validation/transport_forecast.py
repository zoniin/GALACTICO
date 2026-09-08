"""Prior-date-only descriptive forecasts on a common observed-lineup cohort."""

from __future__ import annotations

import numpy as np
import pandas as pd

VERSION = "opening-history-forecasts-v1"
FORECAST_COLUMNS = [
    "game_id",
    "team_id",
    "date",
    "home",
    "target",
    "team_mean",
    "team_recent",
    "opponent_mean",
    "role_sum",
    "lineup_sum",
    "operational_sum",
]


def forecast_rows(panel: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return common eligible forecast rows and an audit of every team-match.

    Histories are assembled BEFORE applying evaluation sample floors. Thus an
    early clean appearance can inform later history without qualifying as a test
    observation itself. Player rates are restricted to the current team's history.
    """
    if panel.duplicated(["game_id", "player_id"]).any():
        raise ValueError("duplicate player-game observations")
    panel = panel.copy()
    panel["date"] = pd.to_datetime(panel.date)
    panel = panel.sort_values(["date", "game_id", "team_id", "player_id"])
    valid = panel[panel.opening_valid & panel.started & panel.position.ne("GK")]
    windows = valid.groupby(["game_id", "team_id"], as_index=False).agg(
        date=("date", "first"),
        opponent_id=("opponent_id", "first"),
        total=("opening_xt", "sum"),
        players=("player_id", "nunique"),
    )
    windows = windows[windows.players == 10].sort_values(["date", "game_id", "team_id"])
    targets = {(int(r.game_id), int(r.team_id)): float(r.total) for r in windows.itertuples()}
    rows, audit = [], []
    cached_date, prior, prior_windows, role_means = None, None, None, None
    for (date, game_id, team_id), team in panel.groupby(["date", "game_id", "team_id"], sort=True):
        cutoff = date.normalize()
        if cutoff != cached_date:
            prior = panel[panel.date < cutoff]
            prior_windows = windows[windows.date < cutoff]
            role_means = (
                prior[prior.opening_valid & prior.position.ne("GK")]
                .groupby("position")
                .opening_xt.mean()
            )
            cached_date = cutoff
        starters = team[team.started & team.position.ne("GK")]
        reasons = []
        if len(starters) != 10 or not starters.opening_valid.all():
            reasons.append("invalid_opening")
        opponent = int(team.iloc[0].opponent_id)
        own_windows = prior_windows[prior_windows.team_id == team_id]
        opponent_windows = prior_windows[prior_windows.team_id == opponent]
        if min(len(own_windows), len(opponent_windows)) < config["minimum_team_windows"]:
            reasons.append("insufficient_team_history")
        own_history = prior[prior.team_id == team_id]
        lineup_sum, operational_sum, role_sum = 0.0, 0.0, 0.0
        for player in starters.itertuples():
            history = own_history[own_history.player_id == player.player_id]
            minutes = history.nominal_minutes.to_numpy(dtype=float)
            if not np.isfinite(minutes).all() or (minutes < 0).any():
                reasons.append("invalid_nominal_exposure")
                continue
            total_minutes = minutes.sum()
            if total_minutes < config["minimum_prior_minutes"] or total_minutes <= 0:
                reasons.append("below_prior_minutes_floor")
            opening_history = history[history.opening_valid]
            if len(opening_history) < config["minimum_opening_starts"]:
                reasons.append("insufficient_player_openings")
            full = history.full_xt.to_numpy(dtype=float)
            if not np.isfinite(full).all():
                reasons.append("unavailable_full_match_accounting")
            position_mean = role_means.get(player.position, np.nan)
            if not np.isfinite(position_mean):
                reasons.append("unavailable_role_history")
            # These arithmetic intermediates never escape a rejected cohort row.
            lineup_sum += float(opening_history.opening_xt.mean())
            operational_sum += (
                float(full.sum() / total_minutes * 30) if total_minutes > 0 else np.nan
            )
            role_sum += float(position_mean)
        reasons = tuple(sorted(set(reasons)))
        audit.append(
            {
                "game_id": int(game_id),
                "team_id": int(team_id),
                "date": date,
                "accepted": not reasons,
                "reasons": reasons,
            }
        )
        if reasons:
            continue
        conceded = [
            targets[(int(r.game_id), int(r.opponent_id))] for r in opponent_windows.itertuples()
        ]
        row = {
            "game_id": int(game_id),
            "team_id": int(team_id),
            "date": date,
            "home": bool(team.iloc[0].home),
            "target": targets[(int(game_id), int(team_id))],
            "team_mean": float(own_windows.total.mean()),
            "team_recent": float(own_windows.tail(5).total.mean()),
            "opponent_mean": float(np.mean(conceded)),
            "role_sum": role_sum,
            "lineup_sum": lineup_sum,
            "operational_sum": operational_sum,
        }
        if not all(np.isfinite(row[k]) for k in FORECAST_COLUMNS if k not in {"date"}):
            raise ValueError("accepted forecast row contains a missing value")
        rows.append(row)
    return pd.DataFrame(rows, columns=FORECAST_COLUMNS), pd.DataFrame(audit)
