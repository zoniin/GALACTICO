import hashlib
from dataclasses import fields, replace
from fractions import Fraction as F

import numpy as np
import pandas as pd
import pytest

from galactico.features.team import estimator
from galactico.validation import conceded_shape as engine
from galactico.validation.conceded_shape import ClusterEstimate, cluster_ratio, season_world

CALENDAR = {
    "East": pd.Series(["2018-01-10"]),
    "West": pd.Series(["2018-01-01", "2018-01-08", "2018-01-12", "2018-01-17"]),
}
SETTINGS = dict(leagues=("West", "East"), evaluation_start="2018-01-10",
                week_rule="W-SUN", replicates=4, seed=3)
INTERVAL = dict(quantiles=(.25, .75), method="linear", zero_tolerance=1e-12)


def test_world_labels_strata_and_leagues():
    world = season_world(CALENDAR, **SETTINGS)
    assert world.strata == ("West|development", "West|evaluation", "East|evaluation")
    # The cutoff bisects a week. Its two parts belong to different strata.
    assert world.labels == (
        "West|development|2018-01-01/2018-01-07", "West|development|2018-01-08/2018-01-14",
        "West|evaluation|2018-01-08/2018-01-14", "West|evaluation|2018-01-15/2018-01-21",
        "East|evaluation|2018-01-08/2018-01-14",
    )
    counts = np.array([[1, 1, 2, 0, 1], [2, 0, 2, 0, 1], [1, 1, 1, 1, 1], [0, 2, 2, 0, 1]],
                      dtype="<i4")
    np.testing.assert_array_equal(world.multiplicity, counts)
    prefix = "\n".join(world.labels).encode() + b"\0"
    assert world.fingerprint == hashlib.sha256(prefix + counts.tobytes()).hexdigest()
    counts[0, 0] += 1
    assert world.fingerprint != hashlib.sha256(prefix + counts.tobytes()).hexdigest()
    assert not world.multiplicity.flags.writeable
    # Identical dates on both fixture sides and shuffled fixture order use the same draw.
    repeated = {k: pd.concat([v[::-1], v]) for k, v in CALENDAR.items()}
    assert season_world(repeated, **SETTINGS).fingerprint == world.fingerprint
    with pytest.raises(ValueError, match="leagues"):
        season_world({"West": CALENDAR["West"]}, **SETTINGS)


def test_cluster_ratio_is_a_ratio_of_sums_with_linear_quantiles_and_the_p_value_rule():
    world = season_world(CALENDAR, **SETTINGS)
    first, second = world.labels[:2]
    labels = np.array([first, first, second])
    num, den = np.array([-2, 1, 3]), np.array([1, 1, 6])
    result = cluster_ratio(num, den, labels, world, **INTERVAL)
    # The four ratios are 2/8, -1/2, 2/8 and 3/6. Both rows in week one move together.
    assert result == ClusterEstimate(.25, (.0625, .3125), .8, 3, 8., 2, 0)
    assert cluster_ratio(num[::-1], den[::-1], labels[::-1], world, **INTERVAL) == result
    zero = cluster_ratio(num * 0, den, labels, world, **INTERVAL)
    assert (zero.estimate, zero.interval, zero.p_one_sided) == (0., (0., 0.), 1.)
    near_zero = cluster_ratio(-1e-13 * den, den, labels, world, **INTERVAL)
    assert near_zero.p_one_sided == 1.
    cancelling = cluster_ratio(
        np.array([-1e16, 1., 1e16]), np.ones(3), np.array([first] * 3), world, **INTERVAL
    )
    assert cancelling.estimate == 1 / 3
    assert cancelling.interval == (1 / 3, 1 / 3)


def test_one_world_for_every_estimand_subset_and_window():
    world = season_world(CALENDAR, **SETTINGS)
    first, second = world.labels[:2]
    labels = np.array([first, second, world.labels[-1]])
    num, den = np.array([-1., 3., 2.]), np.array([2., 6., 2.])
    # East contributes 2/2 in every draw. Its week and each West week retain
    # their original weights in the pooled, West-only, and single-week windows.
    pooled = cluster_ratio(num, den, labels, world, **INTERVAL)
    ratios = [.4, 0., .4, 8 / 14]
    assert pooled.estimate == .4
    assert pooled.interval == pytest.approx(np.quantile(ratios, [.25, .75]))
    west = cluster_ratio(num[:2], den[:2], labels[:2], world, **INTERVAL)
    assert west == ClusterEstimate(.25, (.0625, .3125), .8, 2, 8., 2, 0)
    first_week = cluster_ratio(num[:1], den[:1], labels[:1], world, **INTERVAL)
    assert first_week == ClusterEstimate(-.5, (-.5, -.5), .25, 1, 2., 1, 1)
    empty = cluster_ratio(num[:0], den[:0], labels[:0], world, **INTERVAL)
    assert empty == ClusterEstimate(None, None, None, 0, 0., 0, 4)
    no_events = cluster_ratio(num * 0, den * 0, labels, world, **INTERVAL)
    assert no_events == ClusterEstimate(None, None, None, 3, 0., 3, 4)
    with pytest.raises(ValueError, match="outside"):
        cluster_ratio(num[:1], den[:1], np.array(["missing week"]), world, **INTERVAL)


FORWARD = engine.ForwardSettings(
    parts=("wide", "centre"),
    mirror_pairs=(("wide", "centre"),),
    k_context=4,
    k_unit_candidates=(None, 2),
    minimum_prior_matches=1,
    league_pseudocount=1,
    raw_matches=1,
    smoothing=0.5,
    permutation_seeds=(11, 23),
    seed=7,
    tercile_count=1,
)


def fixtures():
    # Two sides of each fixture, in deliberately non-consecutive team ids.
    return pd.DataFrame(
        [
            (1, "2018-01-01", 11, 23, False, 2.0, 3, 1),
            (1, "2018-01-01", 23, 11, True, 2.0, 0, 2),
            (2, "2018-01-02", 37, 23, True, 1.0, 1, 5),
            (2, "2018-01-02", 23, 37, False, 1.0, 0, 2),
            (3, "2018-01-03", 11, 23, False, 1.0, 4, 2),
            (3, "2018-01-03", 23, 11, True, 1.0, 1, 3),
        ],
        columns=[
            "game_id",
            "date",
            "unit_id",
            "context_id",
            "context_home",
            "exposure",
            "n__wide",
            "n__centre",
        ],
    ).assign(league="West", valid=True, unit_goals=0, context_goals=0)


def test_hand_computed_two_date_example():
    rows = fixtures()
    shape = engine.walk_forward_shape(rows, FORWARD)
    level = engine.walk_forward_level(rows, FORWARD)
    np.testing.assert_array_equal(shape.eligible, [False] * 4 + [True] * 2)
    np.testing.assert_array_equal(level.scored, shape.eligible)
    np.testing.assert_array_equal(shape.events, [4, 2, 6, 2, 6, 4])

    def composition(a, b):
        return (a / (a + b), b / (a + b))

    def adjusted(base, lift):
        return composition(base[0] * lift[0], base[1] * lift[1])

    def lift(obs, exp):
        total = sum(obs)
        return tuple(
            (o + 2 * e / total) / (total + 2) / (e / total) for o, e in zip(obs, exp, strict=True)
        )

    # Leave each unit out of its opponent's counts. Unit 23 faced two opponents;
    # both revert to the venue prior when its meetings with them are removed.
    expected11 = (4 * F(99, 254), 4 * F(155, 254))
    expected23 = (F(7, 5), F(13, 5))
    p37 = adjusted((F(17, 32), F(15, 32)), (F(16, 25), F(64, 55)))
    expected37 = tuple(6 * p for p in p37)
    expected = (expected11, expected23, expected37)
    observed = ((3, 1), (0, 4), (1, 5))
    lifts = [lift(o, e) for o, e in zip(observed, expected, strict=True)]
    venue = ((F(1, 2), F(1, 2)), (F(1, 5), F(4, 5)))
    baselines = (
        adjusted((F(21, 56), F(35, 56)), (F(8, 5), F(8, 11))),
        adjusted((F(5, 24), F(19, 24)), (F(16, 25), F(64, 55))),
    )
    for team, r in enumerate((4, 5)):
        counts = np.array([(4, 2), (1, 3)][team])
        base = baselines[team]
        others = [j for j in range(3) if j != team]
        peer = lift(
            [sum(observed[j][k] for j in others) for k in range(2)],
            [sum(expected[j][k] for j in others) for k in range(2)],
        )

        def loss(prob, counts=counts):
            return -counts @ np.log(np.asarray(prob, dtype=float))

        assert shape.loss_league_venue[r] == pytest.approx(loss(venue[team]))
        assert shape.loss_context[r] == pytest.approx(loss(base))
        assert shape.loss_candidate[1, r] == pytest.approx(loss(adjusted(base, lifts[team])))
        assert shape.loss_mirror[1, r] == pytest.approx(loss(adjusted(base, lifts[team][::-1])))
        assert shape.loss_peers[1, r] == pytest.approx(loss(adjusted(base, peer)))
        raw = ((F(7, 10), F(3, 10)), (F(1, 6), F(5, 6)))[team]
        assert shape.loss_raw_five[r] == pytest.approx(loss(raw))
        for p, placebo in enumerate(FORWARD.permutation_seeds):
            token = f"7|{placebo}|West|2018-01-03|0".encode()
            seed = int.from_bytes(hashlib.sha256(token).digest()[:8], "big")
            donor = np.random.default_rng(seed).permutation(3)[team]
            assert shape.donor_changed[p, r] == (donor != team)
            assert shape.loss_permuted[p, 1, r] == pytest.approx(loss(adjusted(base, lifts[donor])))
        residual = np.log((counts[0] + 0.5) / (counts[1] + 0.5) / float(base[0] / base[1]))
        assert shape.residual_coordinates[r, 0] == pytest.approx(residual / np.sqrt(2))

        # All of 11's history drops out; 23 keeps the (0, 2) row vs 37, at venue 0.
        other_lift = ((1, 1), lift((0, 2), (F(1), F(1))))[team]
        coordinate = np.log(float(other_lift[0] / other_lift[1])) / np.sqrt(2)
        assert shape.delta_coordinates_pair_excluded[1, r, 0] == pytest.approx(coordinate)

        # Context 11's observed 2 events and expected 16/3 (two exposure units
        # at home) give a 9/14 ratio. Every number here is a prior-date quantity.
        venue_mean = (F(2), F(8, 3))[team]
        context_mean = venue_mean * (F(21, 16), F(9, 14))[team]
        unit_ratio = (F(6, 8), F(6) / (F(22, 3) + 2))[team]
        peer_ratio = (F(1), F(12) / (F(26, 3) + 2))[team]
        recent_events, exposure = ((4, 2), (2, 1))[team]
        raw_mean = (recent_events + F(1, 2)) / (exposure + F(1, 2) / F(7, 3))
        for value, mu in (
            (level.deviance_league_venue[r], venue_mean),
            (level.deviance_context[r], context_mean),
            (level.deviance_unit[1, r], context_mean * unit_ratio),
            (level.deviance_peers[1, r], context_mean * peer_ratio),
            (level.deviance_raw_five[r], raw_mean),
        ):
            y = counts.sum()
            assert value == pytest.approx(2 * (y * np.log(y / float(mu)) - y + float(mu)))

    for losses in (
        shape.loss_candidate[0],
        shape.loss_mirror[0],
        shape.loss_peers[0],
        *shape.loss_permuted[:, 0],
    ):
        np.testing.assert_array_equal(losses, shape.loss_context)
    for losses in (level.deviance_unit[0], level.deviance_peers[0]):
        np.testing.assert_array_equal(losses, level.deviance_context)


def test_future_and_same_day_rows_cannot_change_a_prediction():
    base = fixtures()
    day = base.iloc[-2:].copy()
    extra = pd.concat(
        [
            day.assign(game_id=0, date="2018-01-03 09:00"),
            day.assign(game_id=4, date="2018-01-04"),
            base.assign(league="East"),
        ]
    ).assign(n__wide=9999, unit_goals=13)
    combined = pd.concat([base, extra], ignore_index=True)
    order = np.random.default_rng(123).permutation(len(combined))
    for walk in (engine.walk_forward_shape, engine.walk_forward_level):
        plain = walk(base, FORWARD)
        shuffled = walk(combined.iloc[order], FORWARD)
        for field in fields(plain):
            arr = getattr(shuffled, field.name)
            # Most arrays end in rows. Coordinate arrays carry their coordinate axis last.
            axis = -2 if "coordinates" in field.name else -1
            restored = np.take(arr, np.argsort(order)[: len(base)], axis=axis)
            np.testing.assert_array_equal(restored, getattr(plain, field.name))


def test_positive_exposure_and_recent_zero_counts():
    rows = fixtures()
    rows.loc[3, ["n__wide", "n__centre"]] = 0
    rows.loc[4, ["exposure", "n__wide", "n__centre"]] = 0
    level = engine.walk_forward_level(rows, FORWARD)
    assert level.eligible[4] and not level.scored[4] and level.scored[5]
    assert np.isfinite(level.deviance_raw_five[5])
    empty_history = rows.assign(n__wide=0, n__centre=0)
    assert not engine.walk_forward_level(empty_history, FORWARD).eligible.any()
    assert not engine.walk_forward_shape(empty_history, FORWARD).eligible.any()


def test_selection_ties_and_nonfinite_development_losses():
    candidates = (None, 25, 50, 100)
    mask = np.array([True, True, False])
    weights = np.array([4.0, 1.0, 100.0])
    losses = np.array(
        [[4.0, 1.0, np.nan], [2.0, 3.0 + 1e-13, np.nan], [5.0, 1.0, np.nan], [6.0, 0.5, np.nan]]
    )
    q, pooled = engine.select_k(losses, weights, mask, candidates, tolerance=1e-12)
    assert q == 0 and pooled == pytest.approx([1, 1, 1.2, 1.3])
    # The final candidate is near the second-best, outside tolerance of the best.
    losses[:, 1] = [5, 0, -3 + 0.004, -4 + 0.008]
    q, _ = engine.select_k(losses, weights, mask, candidates, tolerance=0.001)
    assert q == 2
    losses[1, 0] = np.nan
    assert engine.select_k(losses, weights, mask, candidates, tolerance=0)[0] is None
    assert engine.select_k(losses, weights, ~np.ones_like(mask), candidates, tolerance=0)[0] is None


def test_invalid_rows_count_on_the_sheet_and_never_enter_the_forecast():
    teams = [11, 23, 37, 41, 53, 67]
    opener = pd.concat(
        [
            fixtures()
            .iloc[:2]
            .assign(
                game_id=i, unit_id=[a, b], context_id=[b, a], n__wide=[i + 1, 2], n__centre=[2, 3]
            )
            for i, (a, b) in enumerate(zip(teams[::2], teams[1::2], strict=True))
        ]
    )
    future = opener.assign(date="2018-01-03", game_id=opener.game_id + 10)
    invalid = opener.iloc[:2].assign(
        game_id=6,
        date="2018-01-02",
        unit_id=[67, 11],
        context_id=[11, 67],
        unit_goals=[1, 0],
        context_goals=[0, 1],
        valid=False,
        exposure=np.nan,
        n__wide=0,
        n__centre=0,
    )
    data = pd.concat([opener, invalid, future], ignore_index=True)
    clean = pd.concat([opener, future], ignore_index=True)
    settings = replace(FORWARD, tercile_count=3, permutation_seeds=(1, 5, 7))
    result = engine.walk_forward_shape(data, settings)
    without = engine.walk_forward_shape(clean, settings)
    assert not result.eligible[:8].any() and result.eligible[8:].all()
    for name in (
        "loss_league_venue",
        "loss_context",
        "loss_raw_five",
        "loss_candidate",
        "loss_mirror",
    ):
        np.testing.assert_array_equal(
            getattr(result, name)[..., 8:], getattr(without, name)[..., 6:]
        )
    lvl = engine.walk_forward_level(data, settings)
    plain = engine.walk_forward_level(clean, settings)
    for name in ("deviance_league_venue", "deviance_context", "deviance_raw_five", "deviance_unit"):
        np.testing.assert_array_equal(getattr(lvl, name)[..., 8:], getattr(plain, name)[..., 6:])
    # The sheet win puts 67 first and 11 last. The remaining four teams still
    # tie on both strength measures and are ordered by id.
    expected = np.zeros((3, 6), dtype=bool)
    for p, placebo in enumerate(settings.permutation_seeds):
        for tier, members in enumerate(([23, 67], [37, 41], [11, 53])):
            salt = f"7|{placebo}|West|2018-01-03|{tier}".encode()
            seed = int.from_bytes(hashlib.sha256(salt).digest()[:8], "big")
            shuffled = np.random.default_rng(seed).permutation(members)
            for team, donor in zip(members, shuffled, strict=True):
                expected[p, teams.index(team)] = team != donor
    np.testing.assert_array_equal(result.donor_changed[:, 8:], expected)
    assert not np.array_equal(expected, without.donor_changed[:, 6:])
    level_fields = (lvl.deviance_unit, lvl.deviance_peers, lvl.deviance_raw_five)
    assert all(np.isfinite(values).all() for values in level_fields)
    extra_meeting = invalid.assign(date="2018-01-04", game_id=20, valid=True, exposure=1)
    short = pd.concat([opener, invalid, extra_meeting], ignore_index=True)
    assert not engine.walk_forward_shape(
        short, replace(settings, minimum_prior_matches=2)
    ).eligible.any()


@pytest.mark.parametrize(
    ("source", "field", "output"),
    [
        ("shape_estimate", "context", "loss_context"),
        ("shape_estimate", "nu", "loss_context"),
        ("shape_estimate", "expected", "loss_candidate"),
        ("shape_estimate", "observed", "loss_candidate"),
        ("shape_estimate", "pi_venue", "loss_league_venue"),
        ("shape_estimate", "expected_share", "delta_coordinates_pair_excluded"),
        ("level_estimate", "rate", "deviance_raw_five"),
        ("level_estimate", "rate_venue", "deviance_league_venue"),
        ("level_estimate", "context_ratio", "deviance_context"),
        ("level_estimate", "unit_expected", "deviance_unit"),
        ("level_estimate", "unit_observed", "deviance_unit"),
        ("unit_deviation", None, "loss_candidate"),
        ("unit_deviation", None, "delta_coordinates_pair_excluded"),
        ("unit_level_ratio", None, "deviance_unit"),
    ],
)
def test_forward_models_use_the_shared_estimator(monkeypatch, source, field, output):
    shape = source in ("shape_estimate", "unit_deviation")
    walk = engine.walk_forward_shape if shape else engine.walk_forward_level
    base = fixtures()
    # Give each unit positive history against a second opponent so that perturbing
    # the observed or expected totals still leaves a meaningful pair-excluded rate.
    extra = base.iloc[:2].assign(game_id=0, unit_id=[11, 37], context_id=[37, 11])
    rows = pd.concat([extra, base], ignore_index=True)
    rows[["n__wide", "n__centre"]] += 1
    settings = replace(FORWARD, minimum_prior_matches=2)
    reference = getattr(walk(rows, settings), output)
    original = getattr(estimator, source)

    def perturbed(*args, **kwargs):
        result = original(*args, **kwargs)
        tilt = np.array([0.2, -0.2])
        if field is None:
            return result + tilt if shape else 2 * result
        value = getattr(result, field)
        if field == "nu":
            changed = value + tilt
        elif shape:
            changed = value * np.exp(tilt)
            if field in ("context", "expected_share", "pi_venue"):
                changed /= changed.sum(axis=-1, keepdims=True)
        else:
            changed = value * 2
        return replace(result, **{field: changed})

    monkeypatch.setattr(estimator, source, perturbed)
    assert np.max(np.abs(getattr(walk(rows, settings), output) - reference)) > 1e-6


def test_mirror_swaps_only_the_named_parts_and_no_placebos_can_be_requested():
    rows = fixtures().assign(n__left=[4, 1, 0, 2, 3, 0], n__right=[1, 0, 5, 2, 0, 4])
    settings = replace(
        FORWARD,
        parts=("left", "centre", "right"),
        mirror_pairs=(("left", "right"),),
        permutation_seeds=(),
    )
    result = engine.walk_forward_shape(rows, settings)
    state = estimator.state_at(
        rows,
        team_ids=(11, 23, 37),
        parts=settings.parts,
        date="2018-01-03",
        weights=np.ones(len(rows)),
    )
    fit = estimator.shape_estimate(state, league_pseudocount=1, k_context=4, k_unit=2)
    mirror = fit.delta[0, [2, 1, 0]]
    pred = estimator.predicted_shape(fit, np.array([1]), np.array([False]), mirror)[0]
    assert result.loss_mirror[1, 4] == pytest.approx(-np.array([3, 2, 0]) @ np.log(pred))
    assert result.loss_candidate[1, 4] != pytest.approx(result.loss_mirror[1, 4])
    assert result.loss_permuted.shape == (0, 2, 6)


def test_poisson_multinomial_factorisation():
    rows = fixtures()
    settings = replace(FORWARD, smoothing=1)
    shape = engine.walk_forward_shape(rows, settings)
    level = engine.walk_forward_level(rows, settings)
    state = estimator.state_at(
        rows,
        team_ids=(11, 23, 37),
        parts=FORWARD.parts,
        date="2018-01-03",
        weights=np.ones(len(rows)),
    )
    fit = estimator.shape_estimate(state, league_pseudocount=1, k_context=4, k_unit=2)
    pred = estimator.predicted_shape(fit, np.array([1]), np.array([False]), fit.delta[0])[0]
    means = pred * float(F(2) * F(21, 16) * F(6, 8))
    counts = np.array([4.0, 2.0])
    joint = 2 * np.sum(counts * np.log(counts / means) - counts + means)
    empirical = -counts @ np.log(counts / counts.sum())
    conditional = 2 * (shape.loss_candidate[1, 4] - empirical)
    assert joint == pytest.approx(level.deviance_unit[1, 4] + conditional)


@pytest.mark.parametrize("planted", [False, True])
def test_walk_forward_recovers_a_repeatable_side_on_held_out_fixtures(planted):
    rounds = (((0, 1), (2, 3)), ((0, 2), (3, 1)), ((3, 0), (1, 2)))
    games = []
    for week in range(12):
        for game, pair in enumerate(rounds[week % 3]):
            home, away = pair if week % 2 else pair[::-1]
            for unit, context in ((home, away), (away, home)):
                left = (8 if unit < 2 else 2) if planted else 5
                games.append(
                    (
                        2 * week + game,
                        pd.Timestamp("2018-01-01") + pd.Timedelta(weeks=week),
                        unit,
                        context,
                        context == home,
                        left,
                        5,
                        10 - left,
                    )
                )
    rows = pd.DataFrame(
        games,
        columns=[
            "game_id",
            "date",
            "unit_id",
            "context_id",
            "context_home",
            "n__left",
            "n__centre",
            "n__right",
        ],
    ).assign(league="West", exposure=1.0, valid=True, unit_goals=0, context_goals=0)
    settings = replace(
        FORWARD, parts=("left", "centre", "right"), mirror_pairs=(("left", "right"),)
    )
    shape = engine.walk_forward_shape(rows, settings)
    development = (rows.date < "2018-02-12").to_numpy()
    selected, _ = engine.select_k(
        shape.loss_candidate,
        shape.events,
        shape.eligible & development,
        settings.k_unit_candidates,
        tolerance=1e-12,
    )
    held_out = shape.eligible & ~development
    assert held_out.sum() == 24
    if planted:
        assert selected == 1
        assert shape.loss_candidate[selected, held_out].sum() < shape.loss_context[held_out].sum()
        assert (
            shape.loss_candidate[selected, held_out].sum()
            < shape.loss_mirror[selected, held_out].sum()
        )
    else:
        assert selected == 0
        np.testing.assert_equal(
            shape.loss_candidate[selected, held_out], shape.loss_context[held_out]
        )
