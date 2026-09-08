"""Observed opening-window panel for temporal transport research, not XI utility.

The opening window is first-half elapsed seconds [0, 1800). It deliberately
avoids reconstructed full-match minutes and stoppage-time exposure. Nominal
substitution minutes cannot place a substitution precisely at the boundary, so
minute 30 is excluded conservatively. Dismissals use event clocks, not rounded
lineup metadata. Callers supply a pre-training-period xT surface; this module
does not fit one or infer unavailable exposure.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRANSPORT_PANEL_VERSION = "opening-30-observed-lineup-v1"
NORMAL_PERIODS = ("1H", "2H", "E1", "E2")
KEYS = ["game_id", "team_id", "player_id"]
POSITIONS = {"GK", "DF", "MF", "FW"}


def build_transport_panel(
    actions, lineups, matches, players, *, xt, substitutions, dismissals
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return player-match observations and explicit whole-game quality gates.

    ``substitutions`` contains game_id/team_id/minute; ``dismissals`` contains
    game_id/team_id/period/seconds, already mapped from provider red-card tags.
    Both must be supplied, including an explicit empty list for no incidents.
    Only starting players in accepted games receive ``opening_valid=True``.
    Invalid targets are NaN, never a zero-valued performance. Full-match totals
    remain available independently, unless that player's pass coordinates are
    invalid. These totals include stoppage time; ``nominal_minutes`` does not.
    """
    if substitutions is None or dismissals is None:
        raise ValueError("explicit substitution and dismissal records are required")
    if lineups.duplicated(["game_id", "player_id"]).any():
        raise ValueError("a player must have exactly one lineup row per game")
    if matches.game_id.duplicated().any() or players.player_id.duplicated().any():
        raise ValueError("match and player metadata identifiers must be unique")
    if not np.isfinite(xt.values).all():
        raise ValueError("the supplied xT surface must be finite")
    if not set(lineups.game_id).issubset(set(matches.game_id)):
        raise ValueError("lineups reference a game without match metadata")

    panel = lineups.rename(columns={"minutes": "nominal_minutes"}).copy()
    if panel.started.isna().any() or not panel.started.isin([True, False]).all():
        raise ValueError("started must be an observed boolean")
    panel["started"] = panel.started.astype(bool)
    panel = panel.merge(players[["player_id", "position"]], on="player_id", how="left")
    panel["position"] = panel.position.replace({"MD": "MF"})
    panel = panel.merge(matches[["game_id", "date", "home_team_id", "away_team_id"]], on="game_id")
    if not (panel.team_id.eq(panel.home_team_id) | panel.team_id.eq(panel.away_team_id)).all():
        raise ValueError("a lineup team is not one of the match's two teams")
    panel["home"] = panel.team_id.eq(panel.home_team_id)
    panel["opponent_id"] = np.where(panel.home, panel.away_team_id, panel.home_team_id)
    panel = panel.drop(columns=["home_team_id", "away_team_id"])

    rows = actions.reset_index(drop=True).copy()
    seconds = pd.to_numeric(rows.seconds, errors="coerce")
    first_half = rows.period.eq("1H")
    opening = first_half & seconds.ge(0) & seconds.lt(1800)
    completed = rows.type.eq("pass") & rows.success.eq(True)
    normal_pass = completed & rows.period.isin(NORMAL_PERIODS)
    coordinates = rows[["start_x", "start_y", "end_x", "end_y"]].apply(
        pd.to_numeric, errors="coerce"
    )
    coordinates_valid = (
        pd.Series(np.isfinite(coordinates.to_numpy()).all(axis=1), index=rows.index)
        & coordinates.ge(0).all(axis=1)
        & coordinates.le(1).all(axis=1)
    )
    usable = normal_pass & coordinates_valid
    selected = coordinates[usable]
    rows["_gain"] = np.nan
    rows.loc[usable, "_gain"] = np.maximum(
        xt.values[xt.grid.cells(selected.end_x, selected.end_y)]
        - xt.values[xt.grid.cells(selected.start_x, selected.start_y)],
        0,
    )
    full = rows[usable].groupby(KEYS)._gain.sum().rename("full_xt")
    opening_totals = rows[usable & opening].groupby(KEYS)._gain.sum().rename("opening_xt")
    panel = panel.merge(full, on=KEYS, how="left").merge(opening_totals, on=KEYS, how="left")
    panel[["full_xt", "opening_xt"]] = panel[["full_xt", "opening_xt"]].fillna(0.0)
    bad_full_keys = set(
        rows.loc[normal_pass & ~coordinates_valid, KEYS].itertuples(index=False, name=None)
    )
    panel.loc[
        [key in bad_full_keys for key in panel[KEYS].itertuples(index=False, name=None)],
        "full_xt",
    ] = np.nan

    early_subs = set()
    for sub in substitutions:
        minute = float(sub["minute"])
        if not np.isfinite(minute) or minute < 0:
            raise ValueError("substitution minutes must be finite and nonnegative")
        if minute <= 30:
            early_subs.add(int(sub["game_id"]))
    early_reds = set()
    for dismissal in dismissals:
        elapsed = float(dismissal["seconds"])
        if not np.isfinite(elapsed) or elapsed < 0:
            raise ValueError("dismissal seconds must be finite and nonnegative")
        if dismissal["period"] == "1H" and elapsed < 1800:
            early_reds.add(int(dismissal["game_id"]))

    started = panel[panel.started]
    starter_keys = set(started[KEYS].itertuples(index=False, name=None))
    roster_keys = set(panel[KEYS].itertuples(index=False, name=None))
    actor_keys = list(rows[KEYS].itertuples(index=False, name=None))
    named = rows.player_id.notna() & rows.player_id.ne(0)
    nonstarting = pd.Series([key not in starter_keys for key in actor_keys], index=rows.index)
    not_on_roster = pd.Series([key not in roster_keys for key in actor_keys], index=rows.index)
    nonstarting_games = set(rows.loc[opening & named & nonstarting, "game_id"])
    off_roster_games = set(rows.loc[opening & named & not_on_roster, "game_id"])
    unattributed_games = set(rows.loc[opening & completed & ~named, "game_id"])
    bad_coordinate_games = set(rows.loc[opening & completed & ~coordinates_valid, "game_id"])
    bad_clock_games = set(rows.loc[first_half & (~np.isfinite(seconds) | seconds.lt(0)), "game_id"])
    first_half_end = rows.loc[first_half].assign(_seconds=seconds).groupby("game_id")._seconds.max()
    first_half_start = (
        rows.loc[first_half].assign(_seconds=seconds).groupby("game_id")._seconds.min()
    )
    by_game = {int(gid): group for gid, group in panel.groupby("game_id")}
    quality = []
    for match in matches.sort_values(["date", "game_id"]).itertuples(index=False):
        game_id = int(match.game_id)
        group = by_game.get(game_id, panel.iloc[:0])
        sides = (match.home_team_id, match.away_team_id)
        starting_sides = [group[group.started & group.team_id.eq(team_id)] for team_id in sides]
        flags = {
            "invalid_starting_xi": any(len(side) != 11 for side in starting_sides),
            "invalid_goalkeeper_count": any(
                side.position.eq("GK").sum() != 1 for side in starting_sides
            ),
            "unknown_player_metadata": not group.position.isin(POSITIONS).all(),
            "incomplete_first_half_clock": not (
                first_half_start.get(game_id, np.inf) < 1800
                and first_half_end.get(game_id, -np.inf) >= 1800
            ),
            "early_substitution": game_id in early_subs,
            "early_dismissal": game_id in early_reds,
            "invalid_opening_pass_coordinates": game_id in bad_coordinate_games,
            "nonstarting_opening_actor": game_id in nonstarting_games,
            "off_roster_opening_actor": game_id in off_roster_games,
            "unattributed_opening_pass": game_id in unattributed_games,
            "invalid_first_half_clock": game_id in bad_clock_games,
        }
        reasons = tuple(name for name, failed in flags.items() if failed)
        quality.append(
            {
                "game_id": game_id,
                "date": match.date,
                "opening_valid": not reasons,
                "reasons": reasons,
                **flags,
            }
        )
    quality = pd.DataFrame(quality)
    panel = panel.merge(quality[["game_id", "opening_valid"]], on="game_id", how="left")
    panel["opening_valid"] = panel.opening_valid & panel.started
    panel.loc[~panel.opening_valid, "opening_xt"] = np.nan
    columns = [
        "game_id",
        "team_id",
        "opponent_id",
        "date",
        "home",
        "player_id",
        "position",
        "started",
        "nominal_minutes",
        "full_xt",
        "opening_xt",
        "opening_valid",
    ]
    return panel[columns].sort_values(["date", *KEYS]).reset_index(drop=True), quality
