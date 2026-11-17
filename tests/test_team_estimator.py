"""The E-10 walk-forward estimator, checked against rational arithmetic on two dates."""

import inspect
import json
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from galactico.features.team import descriptors as d
from galactico.features.team import estimator as est

TEAMS = (11, 23, 37)
PARTS = ("wide", "centre")


def example():
    return pd.DataFrame(
        [
            (1, "2018-01-01", 23, 11, False, 2.0, 3, 1),
            (1, "2018-01-01", 11, 23, True, 2.0, 0, 2),
            (2, "2018-01-02", 23, 37, True, 1.0, 1, 5),
            (2, "2018-01-02", 37, 23, False, 1.0, 0, 2),
        ],
        columns=[
            "game_id",
            "date",
            "context_id",
            "unit_id",
            "context_home",
            "exposure",
            "n__wide",
            "n__centre",
        ],
    ).assign(valid=True)


def state(rows, *, teams=TEAMS, cutoff="2018-01-03", weights=None):
    return est.state_at(
        rows,
        team_ids=teams,
        parts=PARTS,
        date=cutoff,
        weights=np.ones(len(rows)) if weights is None else weights,
    )


def test_two_date_hand_calculation():
    past = state(example(), teams=reversed(TEAMS))
    assert past.team_ids == TEAMS
    np.testing.assert_equal(past.counts[1, 0, 0], [3, 1])
    assert past.exposure[1, 0, 0] == 2
    shape = est.shape_estimate(past, league_pseudocount=1, k_context=4, k_unit=2)
    level = est.level_estimate(past, k_context_level=4, k_unit_level=2)
    assert shape.events == 14
    np.testing.assert_allclose(shape.pi, [5 / 16, 11 / 16])
    np.testing.assert_allclose(shape.pi_venue, [[1 / 2, 1 / 2], [1 / 5, 4 / 5]])
    np.testing.assert_allclose(np.exp(shape.nu[0]), [8 / 5, 8 / 11])
    np.testing.assert_allclose(shape.context[1], [21 / 56, 35 / 56])
    np.testing.assert_allclose(shape.context_without_unit[1, 0], [9 / 40, 31 / 40])
    # Unit 11 faced context 23 only. That opponent's six events against 37 supply
    # the prior against 11. Venue adjustment then gives 99:155 odds.
    p = F(99, 254)
    expected = [float(4 * p), float(4 * (1 - p))]
    np.testing.assert_allclose(shape.expected_share[1, 0, 0], np.array(expected) / 4)
    np.testing.assert_allclose(shape.expected[0], expected)
    np.testing.assert_equal(shape.observed[0], [3, 1])
    lift = np.array([float((3 + 2 * p) / (6 * p)), float((1 + 2 * (1 - p)) / (6 * (1 - p)))])
    np.testing.assert_allclose(np.exp(shape.delta[0]), lift)
    prob, weight = est.served_composition(shape, 11)
    served = np.array([5, 11]) * lift
    np.testing.assert_allclose(prob, served / served.sum())
    assert weight == pytest.approx(2 / 3)
    prediction = est.predicted_shape(shape, np.array([1]), np.array([False]), shape.delta[[0]])
    against_23 = np.array([21 * 8 / 5, 35 * 8 / 11]) * lift
    np.testing.assert_allclose(prediction[0], against_23 / against_23.sum())
    np.testing.assert_allclose(level.rate_venue, [2, 8 / 3])
    assert level.rate == pytest.approx(7 / 3)
    assert level.context_ratio[1] == pytest.approx(21 / 16)
    assert level.context_ratio_without_unit[1, 0] == pytest.approx(3 / 2)
    assert (level.unit_observed[0], level.unit_expected[0]) == pytest.approx((4, 6))
    assert level.unit_ratio[0] == pytest.approx(3 / 4)
    assert est.served_volume(level, 11) == pytest.approx((7 / 4, 3 / 4))
    prediction = est.predicted_level(
        level, np.array([1]), np.array([True]), np.array([2.0]), level.unit_ratio[[0]]
    )
    assert prediction[0] == pytest.approx(2 * F(8, 3) * F(21, 16) * F(3, 4))


def test_cutoff_whole_day_invalid_rows_and_weights():
    rows = example()
    invalid = rows.iloc[:1].assign(exposure=np.nan, valid=False)
    poisoned = pd.concat([rows, invalid, invalid], ignore_index=True)
    weights = np.array([2, 1, 7, 3, 0, 1])
    expected = state(rows.iloc[[0, 0, 1]])
    got = state(poisoned, cutoff="2018-01-02 20:00", weights=weights)
    reverse = state(poisoned.iloc[::-1], cutoff="2018-01-02 20:00", weights=weights[::-1])
    for s in (got, reverse):
        np.testing.assert_array_equal(s.counts, expected.counts)
        np.testing.assert_array_equal(s.exposure, expected.exposure)
    prior = est.empty_state(TEAMS, PARTS)
    est.add_rows(prior, rows, weights=np.ones(len(rows)))
    assert not prior.counts.any() and not prior.exposure.any()
    with pytest.raises(ValueError, match="team id"):
        est.add_rows(prior, rows.assign(context_id=999), weights=np.zeros(len(rows)))


def test_context_only_and_idle_team():
    extended = state(example(), teams=(*TEAMS, 99))
    shape = est.shape_estimate(extended, league_pseudocount=1, k_context=4, k_unit=None)
    level = est.level_estimate(extended, k_context_level=4, k_unit_level=None)
    assert not shape.delta.any()
    assert (level.unit_ratio == 1).all()
    with pytest.raises(ValueError, match="context-only"):
        est.served_composition(shape, 11)
    with pytest.raises(ValueError, match="context-only"):
        est.served_volume(level, 11)
    fitted = est.shape_estimate(extended, league_pseudocount=1, k_context=4, k_unit=2)
    baseline = est.shape_estimate(state(example()), league_pseudocount=1, k_context=4, k_unit=2)
    np.testing.assert_allclose(fitted.delta[:-1], baseline.delta)
    np.testing.assert_array_equal(fitted.delta[-1], [0.0, 0.0])
    with pytest.raises(ValueError):
        est.served_composition(fitted, 998)


def test_descriptor_rows_pair_pass_counts_by_opponent():
    table = pd.DataFrame(
        {
            "game_id": [3, 3],
            "team_id": [23, 11],
            "opponent_id": [11, 23],
            "goals_for": [0, 1],
            "goals_against": [1, 0],
            "is_home": [False, True],
            "valid": True,
            "window_seconds": [2700.0, 2700.0],
            "date": "2018-01-01 15:00",
            "match__completed_passes": [15, 20],
            **{c.name: [1, 3] for c in d.F3_WIDE.columns},
        }
    )
    r = est.descriptor_rows(table, d.F3_WIDE, league="Spain", exposure_unit_seconds=5400)
    assert r.unit_id.tolist() == [11, 23] and r.context_home.tolist() == [False, True]
    assert r.context_passes.tolist() == [15, 20] and r.unit_passes.tolist() == [20, 15]
    assert r["n__wide"].tolist() == [6, 2] and r.exposure.tolist() == [0.5, 0.5]
    assert r.date.tolist() == [pd.Timestamp("2018-01-01")] * 2


def test_estimator_contract():
    config = Path("experiments/preregistered/E-10-conceded-shape/config.json")
    assert (
        json.loads(config.read_text())["league_prior_pseudocount_per_part"]
        == est.LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART
    )
    for name, function in inspect.getmembers(est, inspect.isfunction):
        if function.__module__ == est.__name__ and not name.startswith("_"):
            assert all(
                p.default is inspect.Parameter.empty
                for p in inspect.signature(function).parameters.values()
            )
