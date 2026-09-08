import pandas as pd
import pytest

from galactico.validation.transport_forecast import forecast_rows


def example():
    rows = []
    for game in range(1, 6):
        for team in (10, 20):
            for number in range(11):
                rows.append(
                    dict(
                        game_id=game,
                        team_id=team,
                        opponent_id=30 - team,
                        date=f"2018-01-{game:02d}",
                        home=team == 10,
                        player_id=team * 100 + number,
                        position="GK" if number == 0 else "MF",
                        started=True,
                        nominal_minutes=90,
                        full_xt=0.3 if team == 10 else 0.6,
                        opening_xt=0.1 if team == 10 else 0.2,
                        opening_valid=True,
                    )
                )
    return pd.DataFrame(rows)


CONFIG = dict(minimum_team_windows=2, minimum_prior_minutes=180, minimum_opening_starts=2)


def test_first_histories_inform_later_rows_without_recursively_passing_floors():
    data = example()
    rows, audit = forecast_rows(data, CONFIG)
    assert len(rows) == 6  # first two matches are history, not evaluated rows
    assert audit.accepted.sum() == 6
    row = rows[(rows.game_id == 3) & (rows.team_id == 10)].iloc[0]
    assert row.target == pytest.approx(1)
    assert row.team_mean == pytest.approx(1)
    assert row.team_recent == pytest.approx(1)
    assert row.opponent_mean == pytest.approx(1)  # what team20 conceded, not produced
    assert row.lineup_sum == pytest.approx(1)
    assert row.operational_sum == pytest.approx(1)
    assert row.role_sum == pytest.approx(1.5)


def test_future_and_same_day_history_poison_does_not_leak():
    data = example()
    # Match4 shares date with3: it must not inform either match3 or itself.
    data.loc[data.game_id == 4, "date"] = "2018-01-03"
    expected, _ = forecast_rows(data, CONFIG)
    poisoned = data.copy()
    poisoned.loc[poisoned.game_id >= 4, ["opening_xt", "full_xt"]] = 1000
    observed, _ = forecast_rows(poisoned, CONFIG)
    pd.testing.assert_frame_equal(expected[expected.game_id == 3], observed[observed.game_id == 3])
    shuffled, _ = forecast_rows(data.sample(frac=1, random_state=3), CONFIG)
    pd.testing.assert_frame_equal(expected, shuffled)


def test_missing_prior_accounting_is_not_zero_and_player_history_is_team_specific():
    data = example()
    data.loc[(data.game_id == 1) & (data.player_id == 1001), "full_xt"] = float("nan")
    rows, audit = forecast_rows(data, CONFIG)
    assert not (rows.team_id == 10).any()
    assert any("unavailable_full_match_accounting" in reasons for reasons in audit.reasons)
    data = example()
    # A newcomer borrows an opponent's ID, not its accumulated team history.
    data.loc[(data.game_id == 5) & (data.player_id == 1001), "player_id"] = 9999
    data.loc[(data.game_id < 5) & (data.player_id == 2001), "player_id"] = 9999
    rows, audit = forecast_rows(data, CONFIG)
    assert not ((rows.game_id == 5) & (rows.team_id == 10)).any()
    failed = audit[(audit.game_id == 5) & (audit.team_id == 10)].iloc[0]
    assert "below_prior_minutes_floor" in failed.reasons
