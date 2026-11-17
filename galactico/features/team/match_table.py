"""Count team and opponent events within a declared match state (E-10 section 2).

Each table row describes one side of one match. A descriptor applies the defending
frame mirror when reading counts. Invalid matches retain their recorded full-match totals.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from .descriptors import REGULATION_PERIODS, Column, Window
from .descriptors import location_valid as location_valid

TEAM_MATCH_VERSION = "team-match-table-v2"
INCIDENT_FLAGS = ("home_goal", "away_goal", "dismissal")
SIDES = ("home", "away")


def _time_keys(actions, periods):
    offsets = {p: (i + 1) * 100_000 for i, p in enumerate(periods)}
    # The source clock includes fractions of a second. Keep them when ordering
    # events: a pass 0.2 s after a goal is already in the new score state.
    return actions.period.map(offsets).astype(float) + actions.seconds


def _indexed(frame, keys):
    indexed = frame.set_index(keys)
    if not indexed.index.is_unique:
        raise ValueError(f"duplicate rows for {keys}")
    return indexed


def _incidents(actions, matches, regulation_periods, dismissal_cards):
    missing = {"own_goal", "goal_on_scoring_event", "card"} - set(actions)
    if missing:
        raise ValueError(f"missing match-state columns: {sorted(missing)}")
    calendar = _indexed(matches, "game_id")
    home = actions.game_id.map(calendar.home_team_id)
    away = actions.game_id.map(calendar.away_team_id)
    if not (actions.team_id.eq(home) | actions.team_id.eq(away)).fillna(False).all():
        raise ValueError("action team is not a side of its match")
    reg = actions.period.isin(regulation_periods)
    own = actions.own_goal.isin([True])
    goals = reg & (own | actions.goal_on_scoring_event.isin([True]))
    cards = reg & actions.card.isin(dismissal_cards)
    home_scored = actions.team_id.eq(home) ^ own
    cols = ["game_id", "period", "seconds"]
    scored = actions.loc[goals, cols].assign(
        home_goal=home_scored[goals].astype("int64"),
        away_goal=(~home_scored[goals]).astype("int64"),
        dismissal=0,
    )
    sent_off = actions.loc[cards, cols].assign(home_goal=0, away_goal=0, dismissal=1)
    incidents = pd.concat([scored, sent_off], ignore_index=True)
    incidents["time_key"] = _time_keys(incidents, regulation_periods)
    return incidents.sort_values(["game_id", "time_key", *INCIDENT_FLAGS], ignore_index=True)


def match_state(
    actions: pd.DataFrame,
    matches: pd.DataFrame,
    *,
    regulation_periods: Sequence[str],
    dismissal_cards: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    incidents = _incidents(actions, matches, regulation_periods, dismissal_cards)
    state = actions[["game_id"]].copy()
    state["time_key"] = _time_keys(actions, regulation_periods)
    before = np.zeros((len(actions), 3), dtype=np.int64)
    positions = actions.groupby("game_id").indices
    timed = incidents.loc[np.isfinite(incidents.time_key)]
    for game, rows in timed.groupby("game_id"):
        pos = positions[game]
        keys = state.time_key.to_numpy()[pos]
        n = np.searchsorted(rows.time_key, keys, side="left")
        cumulative = np.vstack((np.zeros(3, dtype=np.int64), rows[list(INCIDENT_FLAGS)].cumsum()))
        before[pos] = cumulative[np.where(np.isfinite(keys), n, 0)]
    state[["home_goals_before", "away_goals_before", "dismissals_before"]] = before
    return state, incidents


def period_ends(actions: pd.DataFrame, *, regulation_periods: Sequence[str]) -> pd.DataFrame:
    ends = (
        actions.loc[actions.period.isin(regulation_periods)]
        .groupby(["game_id", "period"], observed=True)
        .seconds.max()
        .rename("last_second")
        .reset_index()
    )
    ends["period"] = pd.Categorical(ends.period, categories=regulation_periods, ordered=True)
    return ends


def _in_window(home, away, dismissals, window):
    eligible = np.ones(len(home), dtype=bool)
    if window.eleven_v_eleven:
        eligible &= dismissals == 0
    if window.max_abs_goal_difference is not None:
        eligible &= abs(home - away) <= window.max_abs_goal_difference
    return eligible


def window_mask(actions: pd.DataFrame, state: pd.DataFrame, window: Window) -> np.ndarray:
    return actions.period.isin(window.periods).to_numpy() & _in_window(
        state.home_goals_before.to_numpy(),
        state.away_goals_before.to_numpy(),
        state.dismissals_before.to_numpy(),
        window,
    )


def window_seconds(incidents: pd.DataFrame, period_ends: pd.DataFrame, window: Window) -> pd.Series:
    # Breakpoints at kick-off, each incident and the final whistle. Carry cumulative
    # scores and dismissals across halves while measuring lengths within each half.
    ends = period_ends.rename(columns={"last_second": "seconds"})
    changes = pd.concat([ends.assign(seconds=0), ends, incidents], ignore_index=True)
    changes = changes.loc[np.isfinite(changes.seconds) & changes.seconds.ge(0)]
    # period_ends retains the order given to the clock. Standalone callers may
    # also provide ordinary strings for the registered 1H/2H competition clock.
    clock = (
        period_ends.period.cat.categories
        if isinstance(period_ends.period.dtype, pd.CategoricalDtype)
        else REGULATION_PERIODS
    )
    changes["period_order"] = changes.period.map({p: i for i, p in enumerate(clock)})
    keys = ["game_id", "period_order", "period", "seconds"]
    changes = changes.groupby(keys, as_index=False, observed=True)[list(INCIDENT_FLAGS)].sum()
    states = changes.groupby("game_id")[list(INCIDENT_FLAGS)].cumsum()
    allowed = changes.period.isin(window.periods) & _in_window(
        states.home_goal.to_numpy(),
        states.away_goal.to_numpy(),
        states.dismissal.to_numpy(),
        window,
    )
    next_second = changes.groupby(["game_id", "period"], observed=True).seconds.shift(-1)
    elapsed = (next_second - changes.seconds).where(allowed, 0)
    return elapsed.groupby(changes.game_id).sum().astype(float).rename("window_seconds")


def _validity(
    actions,
    matches,
    match_meta,
    sheet_dismissals,
    regulation_periods,
    dismissal_cards,
    incidents,
    ends,
):
    calendar = _indexed(matches, "game_id")
    meta = _indexed(match_meta, "game_id")
    if not calendar.index.isin(meta.index).all():
        raise ValueError("match has no match_meta row")
    sheet = _indexed(sheet_dismissals, ["game_id", "team_id"])
    audit = pd.DataFrame(index=calendar.index)
    reg = actions.loc[actions.period.isin(regulation_periods)]
    cards = reg.loc[reg.card.isin(dismissal_cards)]
    dismissed = cards.groupby(["game_id", "team_id"]).player_id.nunique()
    goals = incidents.groupby("game_id")[list(INCIDENT_FLAGS)].sum()
    for side in SIDES:
        teams = pd.MultiIndex.from_arrays([calendar.index, calendar[f"{side}_team_id"]])
        if not teams.isin(sheet.index).all():
            raise ValueError("team-match has no sheet dismissal row")
        audit[f"{side}_goals_events"] = goals[f"{side}_goal"].reindex(calendar.index, fill_value=0)
        audit[f"{side}_goals_meta"] = meta.loc[calendar.index, f"{side}_score"].astype("int64")
        audit[f"{side}_dismissed_events"] = dismissed.reindex(teams, fill_value=0).to_numpy()
        audit[f"{side}_dismissed_sheet"] = sheet.dismissed_players.loc[teams].to_numpy()
    audit["goal_incidents"] = audit.home_goals_events + audit.away_goals_events
    audit["dismissal_incidents"] = goals.dismissal.reindex(calendar.index, fill_value=0)
    first = incidents.loc[incidents.dismissal.eq(1)].drop_duplicates("game_id").set_index("game_id")
    audit["first_dismissal_period"] = first.period
    audit["first_dismissal_seconds"] = first.seconds
    for p in regulation_periods:
        audit[f"period_seconds_{p}"] = ends.loc[ends.period.eq(p)].set_index("game_id").last_second
    missing_period = reg.groupby("game_id").period.nunique().reindex(calendar.index, fill_value=0)
    bad_clock = ~np.isfinite(reg.seconds.to_numpy(dtype=float, na_value=np.nan)) | reg.seconds.lt(0)
    reasons = [
        ("period_missing", missing_period.ne(len(regulation_periods))),
        ("clock_invalid", calendar.index.isin(reg.loc[bad_clock, "game_id"])),
        (
            "goals_mismatch",
            (audit.home_goals_events != audit.home_goals_meta)
            | (audit.away_goals_events != audit.away_goals_meta),
        ),
        (
            "dismissals_mismatch",
            (audit.home_dismissed_events != audit.home_dismissed_sheet)
            | (audit.away_dismissed_events != audit.away_dismissed_sheet),
        ),
    ]
    audit["invalid_reason"] = np.select(
        [v for _, v in reasons], [k for k, _ in reasons], default=""
    )
    audit["valid"] = audit.invalid_reason.eq("")
    return audit.sort_index().reset_index()


def match_validity(
    actions: pd.DataFrame,
    matches: pd.DataFrame,
    match_meta: pd.DataFrame,
    sheet_dismissals: pd.DataFrame,
    *,
    regulation_periods: Sequence[str],
    dismissal_cards: Sequence[str],
) -> pd.DataFrame:
    incidents = _incidents(actions, matches, regulation_periods, dismissal_cards)
    ends = period_ends(actions, regulation_periods=regulation_periods)
    return _validity(
        actions,
        matches,
        match_meta,
        sheet_dismissals,
        regulation_periods,
        dismissal_cards,
        incidents,
        ends,
    )


def _match_totals(actions, xt):
    rows = actions.loc[~actions.period.isin(["P"])]
    passed = rows.type.eq("pass") & rows.success.isin([True])
    values = rows[["game_id", "team_id"]].assign(
        match__recorded_actions=1,
        match__completed_passes=passed,
        match__shots=rows.type.eq("shot") | rows.subtype.isin(["penalty", "free_kick_shot"]),
        match__key_passes=passed & rows.key_pass.isin([True]),
        match__interception_flags=rows.interception.isin([True]),
    )
    if xt is not None:
        passes = rows.loc[passed]
        end = xt.grid.cells(passes.end_x, passes.end_y)
        start = xt.grid.cells(passes.start_x, passes.start_y)
        values["match__positive_xt_gain"] = 0.0
        values.loc[passed, "match__positive_xt_gain"] = np.maximum(
            0, xt.values[end] - xt.values[start]
        )
        values = (
            values.assign(event_id=rows.event_id).sort_values("event_id").drop(columns="event_id")
        )
    return values.groupby(["game_id", "team_id"]).sum()


def build_team_match_table(
    actions: pd.DataFrame,
    matches: pd.DataFrame,
    *,
    columns: Sequence[Column],
    window: Window,
    match_meta: pd.DataFrame,
    sheet_dismissals: pd.DataFrame,
    regulation_periods: Sequence[str],
    dismissal_cards: Sequence[str],
    sentinels: Sequence[tuple[float, float]],
    coordinate_range: tuple[float, float],
    xt,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    state, incidents = match_state(
        actions, matches, regulation_periods=regulation_periods, dismissal_cards=dismissal_cards
    )
    ends = period_ends(actions, regulation_periods=regulation_periods)
    audit = _validity(
        actions,
        matches,
        match_meta,
        sheet_dismissals,
        regulation_periods,
        dismissal_cards,
        incidents,
        ends,
    ).set_index("game_id")
    duration = window_seconds(incidents, ends, window).reindex(audit.index).where(audit.valid)
    selected = window_mask(actions, state, window) & actions.game_id.isin(audit.index[audit.valid])
    audit["events_in_window"] = (
        actions.loc[selected].groupby("game_id").size().reindex(audit.index, fill_value=0)
    )
    audit["events_all_states"] = (
        actions.loc[actions.period.isin(regulation_periods)]
        .groupby("game_id")
        .size()
        .reindex(audit.index, fill_value=0)
    )
    sides = []
    for side, other in (("home", "away"), ("away", "home")):
        teams = matches[["game_id", "competition", "date"]].assign(
            team_id=matches[f"{side}_team_id"],
            opponent_id=matches[f"{other}_team_id"],
            is_home=(side == "home"),
            window=window.key,
        )
        teams["goals_for"] = teams.game_id.map(audit[f"{side}_goals_meta"])
        teams["goals_against"] = teams.game_id.map(audit[f"{other}_goals_meta"])
        sides.append(teams)
    table = pd.concat(sides, ignore_index=True)
    table = table.join(audit[["valid", "invalid_reason"]], on="game_id")
    table["window_seconds"] = table.game_id.map(duration)
    own = pd.MultiIndex.from_frame(table[["game_id", "team_id"]])
    rival = pd.MultiIndex.from_arrays([table.game_id, table.opponent_id], names=own.names)
    totals = _match_totals(actions, xt).reindex(own, fill_value=0)
    for key in totals:
        table[key] = totals[key].to_numpy()

    counted = actions.loc[selected].reset_index(drop=True)
    by_event = {}
    for c in columns:
        by_event.setdefault(c.event_set, []).append(c)
    for event, wanted in by_event.items():
        eligible = event.clause_mask(counted)
        located = event.located(counted, sentinels=sentinels, coordinate_range=coordinate_range)
        dropped = counted.loc[eligible & ~located]
        audit[f"dropped_location__{event.key}"] = (
            dropped.groupby("game_id").size().reindex(audit.index, fill_value=0)
        )
        for i, (x, y) in enumerate(sentinels):
            at_point = np.zeros(len(dropped), dtype=bool)
            for anchor in event.needs:
                at_point |= dropped[f"{anchor}_x"].isin([x]) & dropped[f"{anchor}_y"].isin([y])
            n = dropped.loc[at_point].groupby("game_id").size()
            audit[f"dropped_sentinel__{event.key}__{i}"] = n.reindex(audit.index, fill_value=0)
        rows = counted.loc[event.mask(counted) & located]
        parts = {p: p.assign(rows) for p in {c.partition for c in wanted if c.partition}}
        for c in wanted:
            subset = rows if c.partition is None else rows.loc[parts[c.partition] == c.part]
            n = subset.groupby(["game_id", "team_id"]).size()
            table[c.name] = n.reindex(own if c.side == "for" else rival, fill_value=0).to_numpy()
    return table.sort_values(["date", "game_id", "team_id"], ignore_index=True), audit.reset_index()
