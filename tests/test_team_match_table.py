"""Hand-counted, time-ordered match examples and a comparison with Match Lab."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from galactico.features.team import descriptors as d
from galactico.features.team import match_table as m
from galactico.match_lab import build_match
from galactico.models.xt import ExpectedThreat, PitchGrid


def event(event_id, period, seconds, team=10, kind="touch", **changes):
    return dict(
        game_id=1,
        player_id=team + 1,
        team_id=team,
        event_id=event_id,
        provider="pappalardo",
        period=period,
        seconds=seconds,
        type=kind,
        **(
            {
                "subtype": kind,
                "success": True,
                "key_pass": False,
                "interception": False,
                "goal": False,
                "goal_on_scoring_event": False,
                "card": None,
                "own_goal": False,
                "start_x": 0.3,
                "start_y": 0.1,
                "end_x": 0.8,
                "end_y": 0.9,
            }
            | changes
        ),
    )


@pytest.fixture
def fixture():
    # 1-0 at 10, 2-0 at 20, and 2-1 at 30, with a second-yellow dismissal at 2H + 8.
    actions = pd.DataFrame(
        [
            event(1, "1H", 10, kind="shot", goal=True, goal_on_scoring_event=True),
            event(2, "1H", 20, team=20, own_goal=True, goal_on_scoring_event=True),
            event(3, "1H", 20, kind="pass", key_pass=True),
            event(4, "1H", 20.2, kind="pass"),
            event(
                5,
                "1H",
                30,
                team=20,
                kind="set_piece",
                subtype="penalty",
                goal=True,
                goal_on_scoring_event=True,
            ),
            event(6, "1H", 40, team=20, kind="set_piece", subtype="free_kick_shot"),
            event(7, "2H", 3, team=20, kind="save", goal=True),
            event(
                8,
                "2H",
                8,
                team=20,
                kind="duel",
                subtype="Ground defending duel",
                interception=True,
                card="second_yellow",
            ),
            event(9, "2H", 8, kind="pass", start_x=0, start_y=0, end_x=1, end_y=1),
            event(10, "2H", 10, kind="touch", interception=True),
            event(11, "P", 1, kind="shot", goal=True),
        ]
    )
    matches = pd.DataFrame(
        [dict(game_id=1, competition="Spain", date="2018-01-01", home_team_id=10, away_team_id=20)]
    )
    meta = pd.DataFrame([dict(game_id=1, home_score=2, away_score=1)])
    sheet = pd.DataFrame({"game_id": [1, 1], "team_id": [10, 20], "dismissed_players": [0, 1]})
    return actions, matches, meta, sheet


def build(fixture, *, window=d.CLOSE, sentinels=d.WY_LOCATION_SENTINELS, xt=None, columns=None):
    actions, matches, meta, sheet = fixture
    return m.build_team_match_table(
        actions,
        matches,
        columns=d.required_columns(d.TEAM_DESCRIPTORS.values()) if columns is None else columns,
        window=window,
        regulation_periods=d.REGULATION_PERIODS,
        dismissal_cards=d.DISMISSAL_CARDS,
        sentinels=sentinels,
        coordinate_range=d.COORDINATE_RANGE,
        match_meta=meta,
        sheet_dismissals=sheet,
        xt=xt,
    )


def test_window_seconds_tied_incidents_and_defending_frame(fixture):
    table, audit = build(fixture)
    assert audit.at[0, "valid"] and audit.at[0, "events_all_states"] == 10
    assert audit.at[0, "events_in_window"] == 7
    assert audit.at[0, "goal_incidents"] == 3 and audit.at[0, "dismissal_incidents"] == 1
    assert audit.at[0, "first_dismissal_period"] == "2H"
    assert table.window_seconds.tolist() == [38.0, 38.0]
    assert d.F3_CHANNELS.counts(table).tolist() == [[0, 0, 0], [1, 0, 0]]
    assert d.DEFENSIVE_THIRDS.counts(table).tolist() == [[0, 0, 0], [1, 0, 0]]
    for i in (0, 1):
        assert audit.at[0, f"dropped_sentinel__f3_entry_pass__{i}"] == 1
    assert audit.at[0, "dropped_location__f3_entry_pass"] == 1
    every, _ = build(fixture, window=d.WINDOWS["all_states"], sentinels=())
    assert every.window_seconds.tolist() == [50.0, 50.0]
    assert d.F3_CHANNELS.counts(every).tolist() == [[0, 0, 0], [3, 0, 0]]
    state, _ = m.match_state(
        fixture[0],
        fixture[1],
        regulation_periods=d.REGULATION_PERIODS,
        dismissal_cards=d.DISMISSAL_CARDS,
    )
    assert list(state.home_goals_before.iloc[1:4]) == [1, 1, 2]
    assert list(state.dismissals_before.iloc[7:10]) == [0, 0, 1]


@pytest.mark.parametrize(
    "reason", ["goals_mismatch", "dismissals_mismatch", "clock_invalid", "period_missing"]
)
def test_invalid_match_keeps_full_totals_but_never_supplies_a_descriptor(fixture, reason):
    actions, matches, meta, sheet = fixture
    if reason == "goals_mismatch":
        meta.loc[0, "away_score"] += 1
    elif reason == "dismissals_mismatch":
        sheet.loc[1, "dismissed_players"] = 0
    elif reason == "clock_invalid":
        actions.loc[0, "seconds"] = np.nan
    else:
        actions = actions.loc[actions.period.ne("1H")]
    for window in d.WINDOWS.values():
        table, audit = build((actions, matches, meta, sheet), window=window)
        assert audit.at[0, "invalid_reason"] == reason
        assert table.invalid_reason.tolist() == [reason, reason]
        assert table.window_seconds.isna().all()
        assert not d.F3_CHANNELS.counts(table).any()
        assert table.match__recorded_actions.sum() == actions.period.ne("P").sum()


def test_subsets_missing_sheets_and_row_order(fixture):
    actions, matches, meta, sheet = fixture
    expected = build(fixture)
    shuffled = build((actions.sample(frac=1, random_state=9), matches, meta, sheet.iloc[::-1]))
    for left, right in zip(expected, shuffled, strict=True):
        pd.testing.assert_frame_equal(left, right)
    with pytest.raises(ValueError, match="sheet"):
        build((actions, matches, meta, sheet.iloc[:1]))
    with pytest.raises(ValueError, match="side"):
        build((actions.assign(team_id=99), matches, meta, sheet))
    with pytest.raises(ValueError, match="match_meta"):
        build((actions, matches, meta.iloc[:0], sheet))
    with pytest.raises(ValueError, match="match-state columns"):
        build((actions.drop(columns="own_goal"), matches, meta, sheet))


def assert_match_lab_totals(table, report):
    lookup = {
        "match__recorded_actions": "recorded_actions",
        "match__completed_passes": "completed_passes",
        "match__shots": "shots",
        "match__interception_flags": "interceptions",
        "match__key_passes": "key_passes",
        "match__positive_xt_gain": "progression",
    }
    for side in report.team_profiles:
        row = table.loc[
            (table.game_id == report.match_id) & (table.team_id == side["team_id"])
        ].iloc[0]
        metrics = {item["id"]: item["value"] for item in side["metrics"]}
        for col, key in lookup.items():
            if key == "progression":
                assert row[col] == pytest.approx(metrics[key], abs=1e-9, rel=0)
            else:
                assert row[col] == metrics[key]


def test_oracle_against_build_match_synthetic(fixture):
    actions, matches, _, _ = fixture
    xt = ExpectedThreat(PitchGrid(2, 1), np.array([0.0, 0.25]), 1, True, len(actions))
    table, _ = build(fixture, xt=xt)
    teams = pd.DataFrame({"team_id": [10, 20], "team_name": ["home", "away"]})
    players = pd.DataFrame(
        {"player_id": [11, 21], "name": ["home-11", "away-21"], "position": ["MF", "DF"]}
    )
    lineups = pd.DataFrame(
        {"game_id": 1, "team_id": [10, 20], "player_id": [11, 21], "started": True, "minutes": 90}
    )
    report = build_match(
        actions=actions,
        match=dict(matches.iloc[0]) | {"label": "synthetic"},
        teams=teams,
        players=players,
        lineups=lineups,
        xt=xt,
        provenance={"provider": "pappalardo"},
    )
    assert_match_lab_totals(table, report)


@pytest.mark.slow
@pytest.mark.parametrize("league", ["Spain", "England", "Italy", "Germany", "France"])
def test_oracle_against_build_match_real(league):
    from galactico.ingestion import sidecar
    from galactico.storage.public import available_competitions, load_public

    if league not in available_competitions():
        pytest.skip(f"neutral frames for {league} are absent")
    try:
        sidecar.verify(league)
    except sidecar.SidecarMissing:
        pytest.skip(f"tag sidecar for {league} is absent")
    frames = load_public(league)
    matches = frames.matches.sort_values("game_id").head(5)
    actions = frames.actions.loc[frames.actions.game_id.isin(matches.game_id)]
    columns = ["card", "own_goal", "goal_on_scoring_event"]
    tags = sidecar.load(league, "events", columns=["event_id", *columns])
    # The full neutral frame carries legacy flags too. The sidecar supplies
    # authoritative incident flags for match state; Match Lab reads its own frame.
    joined = sidecar.attach(actions.drop(columns=columns, errors="ignore"), tags, columns)
    meta = sidecar.load(league, "matches", columns=["game_id", "home_score", "away_score"])
    squads = sidecar.load(league, "squads", columns=["game_id", "team_id", "red_minute"])
    sheet = (
        squads.groupby(["game_id", "team_id"])
        .red_minute.count()
        .rename("dismissed_players")
        .reset_index()
    )
    xt = ExpectedThreat(PitchGrid(2, 2), np.array([0.01, 0.11, 0.19, 0.41]), 1, True, len(actions))
    table, _ = build((joined, matches, meta, sheet), xt=xt, columns=())
    for match in matches.to_dict("records"):
        report = build_match(
            actions=actions,
            lineups=frames.lineups,
            players=frames.players,
            teams=frames.teams,
            match=match,
            xt=xt,
            provenance={"provider": "pappalardo"},
        )
        assert_match_lab_totals(table, report)


def test_against_columns_and_mirror_negative_control(fixture):
    from dataclasses import replace

    opponent = d.F3_CHANNELS.columns
    own = [replace(c, side="for") for c in opponent]
    table, _ = build(fixture, columns=[*own, *opponent])
    for a, b in zip(own, opponent, strict=True):
        assert table[a.name].tolist() == table[b.name].iloc[::-1].tolist()
    smoothed = d.F3_CHANNELS.counts(table) + 1
    axis = d.log_ratio_basis(3)[0]
    correct = np.log(smoothed) @ axis
    reversed_sides = np.log(smoothed[:, ::-1]) @ axis
    # The away side conceded the planted entry on its left; reversing the
    # defender frame changes the sign of its balance relative to the home side.
    assert correct[1] - correct[0] > 0
    assert reversed_sides[1] - reversed_sides[0] < 0


def test_invalid_reason_precedence_duplicate_keys_and_immutability(fixture):
    actions, matches, meta, sheet = fixture
    before = [frame.copy(deep=True) for frame in fixture]
    build(fixture)
    for frame, original in zip(fixture, before, strict=True):
        pd.testing.assert_frame_equal(frame, original)
    wrong_scores = meta.assign(home_score=99)
    missing_red = sheet.assign(dismissed_players=0)
    broken = actions.loc[actions.period.eq("1H")].assign(seconds=-1)
    for events, expected in (
        (broken, "period_missing"),
        (actions.assign(seconds=-1), "clock_invalid"),
        (actions, "goals_mismatch"),
    ):
        _, audit = build((events, matches, wrong_scores, missing_red))
        assert audit.at[0, "invalid_reason"] == expected
    for i in (1, 2, 3):
        duplicate = list(fixture)
        duplicate[i] = pd.concat([duplicate[i], duplicate[i].iloc[:1]])
        with pytest.raises(ValueError, match="duplicate"):
            build(duplicate)


def test_empty_calendar_and_missing_match_events(fixture):
    actions, matches, meta, sheet = fixture
    empty, audit = build((actions.iloc[:0], matches.iloc[:0], meta, sheet))
    assert empty.empty and audit.empty
    table, audit = build((actions.iloc[:0], matches, meta, sheet))
    assert len(table) == 2 and table.window_seconds.isna().all()
    assert audit.invalid_reason.tolist() == ["period_missing"]
