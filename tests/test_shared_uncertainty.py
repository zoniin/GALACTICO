"""Independent covariance and exposure oracles, not agreement with marginal quantiles."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from galactico.models.xt import ExpectedThreat, PitchGrid
from galactico.profiles.uncertainty import (
    bootstrap_players,
    difference_distribution,
    paired_differences,
    shared_match_weights,
)


def corpus():
    rows = []
    appearances = []
    for player in (1, 2):
        for match in range(1, 9):
            appearances.append(dict(player_id=player, game_id=match, minutes=90))
            for _ in range(match):
                rows.append(dict(player_id=player, game_id=match, type="pass", success=True,
                                 start_x=.1, start_y=.1, end_x=.8, end_y=.1, key_pass=True))
    grid = PitchGrid(2, 1)
    return (pd.DataFrame(rows), pd.DataFrame(appearances),
            ExpectedThreat(grid, np.array([0., .2]), 1, True, len(rows)))


def test_identical_teammates_have_zero_paired_difference_despite_wide_marginals():
    actions, lineups, xt = corpus()
    result = bootstrap_players(actions=actions, lineups=lineups, xt=xt,
                               players=pd.Index([1, 2]), replicates=200, seed=4)
    a, b = result[1]["progression"], result[2]["progression"]
    assert a.spread > .1
    assert a.draws == b.draws
    assert difference_distribution(a, b) == (0., (0., 0.), False)
    # Identical per-match components across constructs retain their identity too.
    assert result[1]["chance_creation"].draws == a.draws


def test_shared_worlds_are_invariant_to_player_and_row_order():
    actions, lineups, xt = corpus()
    common = dict(xt=xt, replicates=100, seed=9)
    a = bootstrap_players(actions=actions, lineups=lineups, players=pd.Index([1, 2]), **common)
    b = bootstrap_players(actions=actions.iloc[::-1], lineups=lineups.iloc[::-1],
                          players=pd.Index([2, 1]), **common)
    assert a == b


def test_zero_exposure_worlds_keep_their_identity():
    actions, lineups, xt = corpus()
    lineups = lineups[(lineups.player_id == 1) | (lineups.game_id <= 2)]
    actions = actions[(actions.player_id == 1) | (actions.game_id <= 2)]
    result = bootstrap_players(actions=actions, lineups=lineups, xt=xt,
                               players=pd.Index([1, 2]), replicates=200, seed=4)
    a, b = result[1]["progression"], result[2]["progression"]
    assert any(d is None for d in b.draws)
    assert a.world_ids == b.world_ids
    games, weights = shared_match_weights(lineups.game_id, 200, 4)
    for world, draw in zip(b.world_ids, b.draws, strict=True):
        exposure = weights[world, games <= 2].sum()
        assert (draw is None) == (exposure == 0)


def test_quantile_only_or_unrelated_worlds_cannot_be_compared():
    actions, lineups, xt = corpus()
    result = bootstrap_players(actions=actions, lineups=lineups, xt=xt,
                               players=pd.Index([1, 2]))
    a = result[1]["progression"]
    with pytest.raises(ValueError, match="namespace"):
        difference_distribution(a, replace(a, world_namespace="different"))
    with pytest.raises(ValueError, match="align"):
        difference_distribution(a, replace(a, draws=()))


def test_pairing_intersects_world_ids_without_compacting_missing_draws():
    actual = paired_differences([5., None, 9.], [2., 4., 1.], [1, 2, 3], [3, 2, 1], "x", "x")
    assert actual.tolist() == [4., 7.]
