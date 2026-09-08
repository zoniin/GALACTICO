"""Independent clock/exposure cases for the opening-30 transport panel."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from galactico.models.xt import PitchGrid
from galactico.validation.transport import build_transport_panel


@pytest.fixture
def source():
    grid = PitchGrid(n_x=2, n_y=1)
    xt = SimpleNamespace(grid=grid, values=np.array([0.0, 1.0]))
    ids = list(range(1, 12)) + list(range(101, 112))
    players = pd.DataFrame(
        {"player_id": ids, "position": ["GK" if p in (1, 101) else "MD" for p in ids]}
    )
    lineups = pd.DataFrame(
        [
            dict(game_id=7, team_id=10 if p < 100 else 20, player_id=p, started=True, minutes=90)
            for p in ids
        ]
    )
    matches = pd.DataFrame([dict(game_id=7, home_team_id=10, away_team_id=20, date="2018-01-01")])
    actions = pd.DataFrame(
        [
            dict(
                game_id=7,
                team_id=team,
                player_id=player,
                period=period,
                seconds=seconds,
                type="pass",
                success=True,
                start_x=0.1,
                start_y=0.5,
                end_x=0.9,
                end_y=0.5,
            )
            for team, player, period, seconds in [
                (10, 2, "1H", 100),
                (20, 102, "1H", 1799.9),
                (10, 2, "1H", 1800),
                (10, 2, "2H", 100),
                (10, 2, "P", 100),
            ]
        ]
    )
    return dict(
        actions=actions,
        lineups=lineups,
        matches=matches,
        players=players,
        xt=xt,
        substitutions=[],
        dismissals=[],
    )


def test_exact_window_period_and_zero_event_appearances(source):
    panel, quality = build_transport_panel(**source)
    assert len(panel) == 22
    assert quality.opening_valid.all()
    assert panel.opening_valid.all()
    assert panel.loc[panel.player_id.eq(2), "opening_xt"].item() == 1
    assert panel.loc[panel.player_id.eq(2), "full_xt"].item() == 3
    assert panel.loc[panel.player_id.eq(3), "opening_xt"].item() == 0
    assert set(panel.position) == {"GK", "MF"}
    assert panel.loc[panel.player_id.eq(2), "opponent_id"].item() == 20


@pytest.mark.parametrize("minute,valid", [(29, False), (30, False), (31, True)])
def test_nominal_minute_30_substitution_is_excluded_for_both_teams(source, minute, valid):
    source["substitutions"] = [dict(game_id=7, team_id=20, minute=minute)]
    panel, quality = build_transport_panel(**source)
    assert quality.opening_valid.item() == valid
    assert panel.opening_valid.eq(valid).all()
    if not valid:
        assert panel.opening_xt.isna().all()


@pytest.mark.parametrize(
    "period,seconds,valid", [("1H", 1798.98, False), ("1H", 1800, True), ("2H", 100, True)]
)
def test_dismissals_use_period_seconds_not_nominal_minute(source, period, seconds, valid):
    source["dismissals"] = [dict(game_id=7, team_id=20, period=period, seconds=seconds)]
    panel, quality = build_transport_panel(**source)
    assert quality.opening_valid.item() == valid
    assert panel.opening_valid.eq(valid).all()


@pytest.mark.parametrize("coordinate", [np.nan, -0.1, 1.1, np.inf])
def test_bad_opening_pass_coordinates_invalidate_game_and_player_full_total(source, coordinate):
    source["actions"].loc[0, "start_x"] = coordinate
    panel, quality = build_transport_panel(**source)
    assert "invalid_opening_pass_coordinates" in quality.reasons.item()
    assert panel.opening_xt.isna().all()
    assert np.isnan(panel.loc[panel.player_id.eq(2), "full_xt"].item())


def test_nonopening_bad_coordinate_preserves_opening_target(source):
    source["actions"].loc[3, "start_x"] = np.nan
    panel, quality = build_transport_panel(**source)
    assert quality.opening_valid.all()
    assert panel.loc[panel.player_id.eq(2), "opening_xt"].item() == 1
    assert np.isnan(panel.loc[panel.player_id.eq(2), "full_xt"].item())


def test_incomplete_first_half_and_missing_starter_are_explicit(source):
    source["actions"] = source["actions"].iloc[:2]
    source["lineups"] = source["lineups"].iloc[1:]
    _, quality = build_transport_panel(**source)
    assert {
        "invalid_starting_xi",
        "invalid_goalkeeper_count",
        "incomplete_first_half_clock",
    } <= set(quality.reasons.item())


def test_unknown_actor_and_unknown_player_metadata_are_not_silently_zeroed(source):
    source["actions"].loc[0, "player_id"] = 999
    source["players"].loc[source["players"].player_id.eq(3), "position"] = None
    _, quality = build_transport_panel(**source)
    assert {
        "off_roster_opening_actor",
        "nonstarting_opening_actor",
        "unknown_player_metadata",
    } <= set(quality.reasons.item())


def test_unattributed_completed_pass_is_explicit(source):
    source["actions"].loc[0, "player_id"] = 0
    _, quality = build_transport_panel(**source)
    assert "unattributed_opening_pass" in quality.reasons.item()


def test_unique_player_game_and_deterministic_order(source):
    baseline, quality = build_transport_panel(**source)
    permuted = {
        key: value.sample(frac=1, random_state=9) if isinstance(value, pd.DataFrame) else value
        for key, value in source.items()
    }
    shuffled, shuffled_quality = build_transport_panel(**permuted)
    pd.testing.assert_frame_equal(baseline, shuffled)
    pd.testing.assert_frame_equal(quality, shuffled_quality)
    source["lineups"] = pd.concat([source["lineups"], source["lineups"].iloc[:1]])
    with pytest.raises(ValueError, match="one lineup row"):
        build_transport_panel(**source)


def test_later_substitute_has_no_opening_exposure_but_keeps_full_observation(source):
    source["lineups"] = pd.concat(
        [
            source["lineups"],
            pd.DataFrame([dict(game_id=7, team_id=10, player_id=12, started=False, minutes=20)]),
        ],
        ignore_index=True,
    )
    source["players"] = pd.concat(
        [source["players"], pd.DataFrame([dict(player_id=12, position="FW")])], ignore_index=True
    )
    source["substitutions"] = [dict(game_id=7, team_id=10, minute=70)]
    panel, quality = build_transport_panel(**source)
    substitute = panel[panel.player_id.eq(12)].iloc[0]
    assert quality.opening_valid.all()
    assert not substitute.opening_valid
    assert np.isnan(substitute.opening_xt)
    assert substitute.full_xt == 0
