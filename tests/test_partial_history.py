import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from galactico.validation.partial_history import _permutation_maps, partial_rows

CONFIG = dict(
    minimum_team_windows=2,
    pooling_grid=[0, 1, 3, 10, 30, "context_only"],
    permutation_seeds=list(range(20)),
    seed=20260913,
)


def example():
    rows = []
    for game in range(1, 7):
        for team in (10, 20):
            for number in range(11):
                rows.append(dict(
                    game_id=game, team_id=team, opponent_id=30 - team,
                    date=f"2018-01-{game:02d}", home=team == 10,
                    player_id=team * 100 + number,
                    position="GK" if number == 0 else "MF", started=True,
                    nominal_minutes=90, full_xt=0.3 if team == 10 else 0.6,
                    opening_xt=0.1 if team == 10 else 0.2, opening_valid=True,
                ))
    return pd.DataFrame(rows)


def selected(rows, game=3, team=10):
    return rows[(rows.game_id == game) & (rows.team_id == team)].iloc[0]


def test_early_clean_history_informs_rows_and_zero_pooling_matches_observed_sum():
    rows, audit = partial_rows(example(), CONFIG)
    assert len(rows) == 8
    assert audit.accepted.sum() == 8
    row = selected(rows)
    assert row.target == pytest.approx(1)
    assert row.team_mean == pytest.approx(1)
    assert row.team_recent == pytest.approx(1)
    assert row.opponent_mean == pytest.approx(1)
    assert row.role_sum == pytest.approx(1.5)
    assert row.lineup_sum == pytest.approx(1)
    assert row.residual_0 == pytest.approx(-0.5)
    assert row.residual_3 == pytest.approx(-0.2)
    assert row.mean_log1p_count == pytest.approx(np.log(3))
    assert row.unseen_fraction == 0
    assert row.seen_players == 10
    assert row.minimum_prior_openings == row.maximum_prior_openings == 2
    assert row.operational_available
    assert row.operational_sum == pytest.approx(1)


def test_future_same_day_poison_and_input_permutations_cannot_change_prior_features():
    data = example()
    data.loc[data.game_id == 3, "date"] = "2018-01-03 20:00:00"
    data.loc[data.game_id == 4, "date"] = "2018-01-03 10:00:00"
    data["date"] = pd.to_datetime(data.date, format="mixed")
    expected, _ = partial_rows(data, CONFIG)
    poisoned = data.copy()
    poisoned.loc[poisoned.game_id >= 4, ["opening_xt", "full_xt"]] = 1000
    observed, _ = partial_rows(poisoned, CONFIG)
    pd.testing.assert_frame_equal(expected[expected.game_id == 3], observed[observed.game_id == 3])
    shuffled, _ = partial_rows(data.sample(frac=1, random_state=87), CONFIG)
    pd.testing.assert_frame_equal(expected, shuffled)
    # The maps and histories for different kickoff times share a calendar cutoff.
    feature_columns = [column for column in expected if column not in {"date", "game_id"}]
    pd.testing.assert_series_equal(
        selected(expected, game=3)[feature_columns], selected(expected, game=4)[feature_columns],
        check_names=False,
    )


def test_unseen_player_uses_role_reference_without_becoming_an_observed_zero():
    data = example()
    data.loc[(data.game_id == 3) & (data.player_id == 1001), "player_id"] = 9999
    rows, audit = partial_rows(data, CONFIG)
    row = selected(rows)
    assert row.seen_players == 9
    assert row.unseen_fraction == pytest.approx(0.1)
    assert row.minimum_prior_openings == 0
    assert row.mean_log1p_count == pytest.approx(0.9 * np.log(3))
    assert row.lineup_sum == pytest.approx(0.9 + 0.15)
    assert row.residual_0 == pytest.approx(9 * (0.1 - 0.15))
    assert not row.operational_available
    assert np.isnan(row.operational_sum)
    assert selected(audit).accepted


def test_finite_observed_zero_is_counted_and_retained_in_raw_lineup_sum():
    data = example()
    data.loc[(data.game_id < 3) & (data.player_id == 1001), "opening_xt"] = 0
    rows, _ = partial_rows(data, CONFIG)
    row = selected(rows)
    assert row.seen_players == 10
    assert row.minimum_prior_openings == 2
    assert row.unseen_fraction == 0
    assert row.lineup_sum == pytest.approx(0.9)


def test_transfer_cannot_borrow_former_teams_openings_or_exposure():
    data = example()
    data.loc[(data.game_id < 3) & (data.player_id == 2001), "player_id"] = 9999
    data.loc[(data.game_id == 3) & (data.player_id == 1001), "player_id"] = 9999
    rows, _ = partial_rows(data, CONFIG)
    row = selected(rows)
    assert row.unseen_fraction == pytest.approx(0.1)
    assert row.lineup_sum == pytest.approx(1.05)
    assert not row.operational_available


@pytest.mark.parametrize("field,value", [("full_xt", np.nan), ("nominal_minutes", np.nan),
                                       ("nominal_minutes", -1), ("nominal_minutes", 0)])
def test_missing_or_invalid_full_match_accounting_never_gates_primary_rows(field, value):
    data = example()
    original, _ = partial_rows(data, CONFIG)
    data.loc[data.player_id == 1001, field] = value
    rows, audit = partial_rows(data, CONFIG)
    assert len(rows) == len(original)
    assert audit.accepted.sum() == len(original)
    assert not rows.loc[rows.team_id == 10, "operational_available"].any()
    assert rows.loc[rows.team_id == 10, "operational_sum"].isna().all()
    fields = [column for column in rows if not column.startswith("operational_")]
    pd.testing.assert_frame_equal(original[fields], rows[fields])


def test_permutation_seed_layout_roles_team_boundaries_and_counts_are_fixed():
    history = pd.DataFrame([
        dict(team_id=10, player_id=1001 + index, position="MF", count=index + 1, mean=index / 10)
        for index in range(5)
    ] + [dict(team_id=10, player_id=1100, position="DF", count=3, mean=50),
         dict(team_id=20, player_id=2000, position="MF", count=4, mean=90)])
    original = history.copy()
    cutoff = pd.Timestamp("2018-03-01")
    maps = _permutation_maps(history, base_seed=20260913, seeds=[7], cutoff=cutoff)
    # Independently spell out the seed's public wire representation; no process hash.
    payload = '[20260913,7,"2018-03-01",10,"MF",[1001,1002,1003,1004,1005]]'
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    rng = np.random.Generator(np.random.PCG64(int.from_bytes(digest[:16], "big")))
    expected = (np.arange(5) / 10)[rng.permutation(5)]
    assert [maps[7][(10, player)] for player in range(1001, 1006)] == list(expected)
    assert sorted(maps[7][(10, player)] for player in range(1001, 1006)) == list(np.arange(5) / 10)
    assert maps[7][(10, 1100)] == 50
    assert maps[7][(20, 2000)] == 90
    pd.testing.assert_frame_equal(history, original)  # counts/unknown flags are not permuted
    assert maps == _permutation_maps(
        history.sample(frac=1, random_state=2), base_seed=20260913, seeds=[7], cutoff=cutoff
    )
    assert json.loads(payload)[-1] == [1001, 1002, 1003, 1004, 1005]


def test_permutation_uses_nonstarting_donors_but_never_borrows_their_counts():
    data = example()
    # First game's player is later replaced: the old ID remains a valid donor.
    data.loc[(data.game_id == 1) & (data.player_id == 1001), "player_id"] = 1999
    data.loc[(data.game_id == 1) & (data.player_id == 1999), "opening_xt"] = 5.0
    # One current player has a singleton broad-position donor pool.
    data.loc[data.player_id == 1010, "position"] = "DF"
    rows, _ = partial_rows(data, CONFIG)
    row = selected(rows)
    assert row.permutation_singleton_players == 1
    assert row.minimum_prior_openings == 1
    assert row.maximum_prior_openings == 2
    assert row.mean_log1p_count == pytest.approx((np.log(2) + 9 * np.log(3)) / 10)
    assert any(row[f"perm_{seed}_residual_0"] > row.residual_0 for seed in range(20))
    assert any(row[f"perm_{seed}_changed_players"] > 0 for seed in range(20))
    assert all(row[f"perm_{seed}_changed_players"] <= 9 for seed in range(20))
    prior = data[(data.game_id < 3) & data.position.ne("GK")]
    history = prior.groupby(["team_id", "player_id", "position"], as_index=False).agg(
        count=("opening_xt", "size"), mean=("opening_xt", "mean")
    )
    mapping = _permutation_maps(
        history, base_seed=CONFIG["seed"], seeds=[0], cutoff=pd.Timestamp("2018-01-03")
    )[0]
    references = prior.groupby("position").opening_xt.mean()
    # Donor 1999 has one opening, but a recipient with two keeps weight 2/(2+3).
    expected = sum(
        count / (count + 3) * (mapping[(10, player)] - references[role])
        for player, count, role in [(1001, 1, "MF")]
        + [(player, 2, "MF") for player in range(1002, 1010)] + [(1010, 2, "DF")]
    )
    assert row.perm_0_residual_3 == pytest.approx(expected)


def test_equal_means_report_no_changed_players_even_with_nontrivial_permutation_pools():
    rows, _ = partial_rows(example(), CONFIG)
    row = selected(rows)
    assert row.permutation_singleton_players == 0
    assert all(row[f"perm_{seed}_changed_players"] == 0 for seed in range(20))
    assert all(row[f"perm_{seed}_residual_3"] == row.residual_3 for seed in range(20))


def test_entire_unseen_xi_can_enter_aggregate_cohort_with_explicit_reference_fallback():
    data = example()
    newcomer = (data.game_id == 3) & (data.team_id == 10) & data.position.ne("GK")
    data.loc[newcomer, "player_id"] += 50000
    rows, _ = partial_rows(data, CONFIG)
    row = selected(rows)
    assert row.unseen_fraction == 1
    assert row.seen_players == row.minimum_prior_openings == row.maximum_prior_openings == 0
    assert row.mean_log1p_count == 0
    assert row.lineup_sum == row.role_sum
    assert all(row[f"residual_{strength}"] == 0 for strength in [0, 1, 3, 10, 30])
    assert all(row[f"perm_{seed}_changed_players"] == 0 for seed in range(20))


def test_unseen_broad_position_without_prior_reference_is_not_invented():
    data = example()
    newcomer = (data.game_id == 3) & (data.player_id == 1001)
    data.loc[newcomer, "player_id"] = 9999
    data.loc[newcomer, "position"] = "FW"
    rows, audit = partial_rows(data, CONFIG)
    assert not ((rows.game_id == 3) & (rows.team_id == 10)).any()
    assert "unavailable_role_history" in selected(audit).reasons


def test_unknown_roles_changing_metadata_duplicates_and_missing_observations_fail_closed():
    data = example()
    data.loc[(data.game_id == 6) & (data.player_id == 1001), "position"] = "FW"
    with pytest.raises(ValueError, match="changing"):
        partial_rows(data, CONFIG)
    data = example()
    data.loc[data.player_id == 1001, "position"] = "UNKNOWN"
    with pytest.raises(ValueError, match="known broad position"):
        partial_rows(data, CONFIG)
    data = example()
    with pytest.raises(ValueError, match="duplicate"):
        partial_rows(pd.concat([data, data.iloc[:1]]), CONFIG)
    data.loc[(data.game_id == 1) & (data.player_id == 1001), "opening_xt"] = np.nan
    with pytest.raises(ValueError, match="finite"):
        partial_rows(data, CONFIG)


def test_invalid_openings_are_neither_evaluated_nor_counted_as_clean_history():
    data = example()
    data.loc[data.game_id == 1, "opening_valid"] = False
    data.loc[data.game_id == 1, "opening_xt"] = np.nan
    rows, audit = partial_rows(data, CONFIG)
    assert not rows.game_id.isin([1, 2, 3]).any()
    assert selected(rows, game=4).minimum_prior_openings == 2
    assert "invalid_opening" in selected(audit, game=1).reasons
    assert "insufficient_team_history" in selected(audit, game=3).reasons


def test_empty_panel_and_wholly_invalid_openings_keep_a_schema():
    rows, audit = partial_rows(pd.DataFrame(), CONFIG)
    assert rows.empty and audit.empty
    assert {"residual_0", "perm_19_residual_30", "operational_available"} <= set(rows)
    assert "accepted" in audit
    data = example()
    data["opening_valid"] = False
    data["opening_xt"] = np.nan
    rows, audit = partial_rows(data, CONFIG)
    assert rows.empty
    assert len(audit) == 12
