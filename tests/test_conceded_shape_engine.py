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


def _double_round_robin(teams, *, second_leg_seed=None):
    first = []
    for r in range(teams - 1):
        rotation = [(i + r) % (teams - 1) for i in range(teams - 1)]
        top = (rotation[0], teams - 1)
        matches = [top if r % 2 == 0 else top[::-1]]
        for i in range(1, teams // 2):
            pair = (rotation[i], rotation[teams - 1 - i])
            matches.append(pair if i % 2 else pair[::-1])
        first.append(matches)
    order = range(len(first))
    if second_leg_seed is not None:
        order = np.random.default_rng(second_leg_seed).permutation(len(first))
    second = [[pair[::-1] for pair in first[i]] for i in order]
    data = []
    for week, games in enumerate(first + second):
        for i, (home, away) in enumerate(games):
            for unit, context in ((home, away), (away, home)):
                data.append((week, week * teams + i, unit, context, context == home))
    frame = pd.DataFrame(data, columns=["week", "game_id", "unit_id", "context_id", "context_home"])
    return frame.assign(
        date=pd.Timestamp("2018-01-01") + pd.to_timedelta(frame.week * 7, unit="D"),
        league="West",
        valid=True,
        exposure=1.0,
        n__wide=2,
        n__centre=1,
        unit_goals=0,
        context_goals=0,
    )


def test_count_pass_tracks_the_forecast_without_fitting(monkeypatch):
    rows = _double_round_robin(6)
    rows.loc[rows.week == 0, ["n__wide", "n__centre"]] = 0
    rows.loc[rows.game_id == 6, ["valid", "n__wide", "n__centre", "exposure"]] = [
        False,
        0,
        0,
        np.nan,
    ]
    other = rows.assign(league="East", unit_goals=1)
    rows = pd.concat([rows, other]).sample(frac=1, random_state=2)
    shape = engine.walk_forward_shape(rows, FORWARD)

    def unexpected(*args, **kwargs):
        pytest.fail("pre-selection sample checks attempted a model fit")

    for name in ("empty_state", "add_rows", "shape_estimate", "level_estimate"):
        monkeypatch.setattr(estimator, name, unexpected)
    counts = engine.count_pass(rows, FORWARD)
    np.testing.assert_array_equal(counts.eligible, shape.eligible)
    np.testing.assert_array_equal(counts.donor_changed, shape.donor_changed)
    np.testing.assert_array_equal(counts.events, shape.events)
    for i, row in enumerate(rows.itertuples()):
        prior = rows[rows.valid & (rows.league == row.league) & (rows.date < row.date)]
        assert counts.unit_prior_matches[i] == (prior.unit_id == row.unit_id).sum()
        assert counts.context_prior_matches[i] == (prior.unit_id == row.context_id).sum()
    assert not counts.eligible[rows.week <= 1].any()


@pytest.mark.parametrize("teams", [18, 20])
@pytest.mark.parametrize("seed", [None, 1, 13])
def test_split_halves_balance_opponents_legs_and_venues(teams, seed):
    rows = _double_round_robin(teams, second_leg_seed=seed).sample(frac=1, random_state=7)
    halves = engine._meeting_halves(rows)
    counts = halves.groupby(["unit_id", "half"])
    assert (counts.size() == teams - 1).all()
    assert (counts.context_id.nunique() == teams - 1).all()
    home = counts.context_home.sum().unstack()
    assert ((home.A - home.B).abs() <= 1).all()
    legs = halves.assign(leg_one=halves.week < teams - 1).groupby(["unit_id", "half"]).leg_one.sum()
    assert ((2 * legs - (teams - 1)).abs() <= 1).all()
    # Invalidating an early meeting removes just that fixture from its original half.
    rows.loc[rows.game_id == 0, "valid"] = False
    kept = engine._meeting_halves(rows.sample(frac=1, random_state=9))
    keys = ["unit_id", "game_id"]
    assert (
        kept.set_index(keys)
        .half.sort_index()
        .equals(halves[halves.game_id != 0].set_index(keys).half.sort_index())
    )


def _gate_config():
    return dict(
        leagues=["West"],
        calendar_week_rule="W-SUN",
        evaluation_start="2018-02-05",
        minimum_valid_match_share_per_league=29 / 30,
        minimum_development_rows_per_league=24,
        minimum_development_weeks_per_league=4,
        minimum_evaluation_rows_per_league=28,
        minimum_evaluation_weeks_per_league=5,
        minimum_evaluation_events_per_league=84,
        minimum_half_matches_per_team=4,
        minimum_reliability_teams=6,
        permutation_seeds=list(FORWARD.permutation_seeds),
        minimum_permutation_changed_share=0.5,
    )


def test_sample_gates_count_matches_and_apply_each_subjects_limits():
    rows = _double_round_robin(6)
    rows.loc[rows.game_id == rows.game_id.max(), ["valid", "n__wide", "n__centre", "exposure"]] = [
        False,
        0,
        0,
        np.nan,
    ]
    count = engine.count_pass(rows, FORWARD)
    evaluation = count.eligible & (rows.week >= 5).to_numpy()
    donors = np.ones_like(count.donor_changed)
    donors[:, evaluation] = False
    donors[:, np.flatnonzero(evaluation)[:14]] = True
    count = replace(count, donor_changed=donors)
    cfg = _gate_config()
    audit = engine.audit_summary_from_rows(rows, ["West", "Absent"])
    assert audit == {
        "West": {"matches": 30, "valid_matches": 29},
        "Absent": {"matches": 0, "valid_matches": 0},
    }

    def gates(cfg, subject):
        return engine.sample_gates(rows, count, audit, cfg, subject=subject)

    got = gates(cfg, "shape")
    assert list(got) == ["G1", "G2", "G3", "G4", "G5"]
    assert all(v["passed"] for v in got.values())
    assert got["G2"]["detail"]["West"] == dict(rows=24, weeks=4)
    assert got["G3"]["detail"]["West"] == dict(rows=28, weeks=5, events=84)
    assert got["G4"]["detail"]["teams"] == 6
    assert list(got["G5"]["detail"].values()) == [0.5, 0.5]
    for gate, key, strict in (
        ("G1", "minimum_valid_match_share_per_league", 1),
        ("G2", "minimum_development_weeks_per_league", 5),
        ("G3", "minimum_evaluation_events_per_league", 85),
        ("G4", "minimum_half_matches_per_team", 5),
        ("G5", "minimum_permutation_changed_share", 0.51),
    ):
        result = gates({**cfg, key: strict}, "shape")
        assert [k for k, v in result.items() if not v["passed"]] == [gate]
    level = gates({**cfg, "minimum_permutation_changed_share": 1}, "level")
    assert set(level) == {"G1", "G2", "G3", "G4"} and all(g["passed"] for g in level.values())
    absent = gates({**cfg, "leagues": ["Absent", "West"]}, "level")
    assert all(not absent[k]["passed"] for k in ("G1", "G2", "G3"))
    assert absent["G1"]["detail"]["Absent"]["share"] is None
    # Replication includes missing fixture files in its denominator and starts evaluation earlier.
    audit["West"]["listed_matches"] = 35
    rep = {**cfg, "evaluation_start": "2018-01-01", "minimum_evaluation_rows_per_league": 52}
    result = gates({**cfg, "replication": rep}, "replication")
    assert set(result) == {"G1", "G3"} and not result["G1"]["passed"] and result["G3"]["passed"]
    assert result["G1"]["detail"]["West"]["share"] == 29 / 35
    assert result["G3"]["detail"]["West"] == dict(rows=52, weeks=9, events=156)


@pytest.mark.parametrize(
    ("r", "band", "number"),
    [(0.4770, True, False), (0.4769, False, False), (0.6495, True, True), (0.6494, True, False)],
)
def test_registered_reliability_bounds(r, band, number):
    c = 1.6448536269514722
    got = engine._reliability_coordinate(
        "side_balance", r, 98, 5, 38.0, critical_value=c, house_confidence=0.9, period="test"
    )
    low = np.tanh(np.arctanh(r) - c / np.sqrt(91))
    assert got["lower_bound"] == pytest.approx(2 * low / (1 + low))
    assert (got["lower_bound"] >= 0.5) == band and (got["lower_bound"] >= 0.7) == number
    reliability = 2 * r / (1 + r)
    assert got["house_lower_bound"] == pytest.approx(
        np.tanh(np.arctanh(reliability) - c / np.sqrt(95))
    )
    assert got["implied_per_match_icc"] == pytest.approx(reliability / (38 - 37 * reliability))


def test_reliability_matches_calendar_recount_for_shape_and_volume():
    from scripts.e10_root_counts import meeting_halves

    west = _double_round_robin(12, second_leg_seed=7)
    rng = np.random.default_rng(2026)
    rows = pd.concat([west, west.assign(league="East")], ignore_index=True)
    rows["n__wide"] = rng.poisson(1 + rows.unit_id + (rows.league == "West") * 30)
    rows["n__centre"] = rng.poisson(2 + (rows.context_id % 3), len(rows))
    rows["exposure"] = rng.uniform(0.3, 1.0, len(rows))
    rows.loc[(rows.league == "East") & (rows.unit_id == 1), "valid"] = False
    rows = rows.sample(frac=1, random_state=5)
    halves = []
    for _, fixtures_ in rows.groupby("league"):
        schedule = fixtures_[~fixtures_.context_home].rename(
            columns={"unit_id": "home_team_id", "context_id": "away_team_id"}
        )
        reference = meeting_halves(schedule).rename(columns={"team_id": "unit_id"})
        halves.append(
            fixtures_.merge(reference[["game_id", "unit_id", "half"]], on=["game_id", "unit_id"])
        )
    split = pd.concat(halves)
    complete = split[split.valid].groupby(["league", "unit_id", "half"])
    sized = complete.size().unstack().dropna()
    index = sized[(sized >= 6).all(axis=1)].index
    agg = complete[["n__wide", "n__centre", "exposure"]].sum()
    half_values = {}
    for h in ["A", "B"]:
        a = agg.xs(h, level="half").loc[index]
        half_values[h] = pd.DataFrame(
            dict(
                first_versus_second=np.log((a.n__wide + 0.5) / (a.n__centre + 0.5)) / np.sqrt(2),
                log_rate=np.log((a.n__wide + a.n__centre + 0.5) / a.exposure),
            )
        )
        half_values[h] -= half_values[h].groupby(level="league").transform("mean")
    options = dict(
        smoothing=0.5,
        minimum_half_matches=6,
        critical_value=1.6448536269514722,
        house_confidence=0.9,
        period="test",
        band=0.5,
        number=0.7,
    )
    for name, got in (
        ("first_versus_second", engine.split_half(rows, FORWARD.parts, **options)),
        ("log_rate", engine.level_split_half(rows, **options)),
    ):
        r = np.corrcoef(half_values["A"][name], half_values["B"][name])[0, 1]
        n = len(index)
        assert got["n_teams"] == n == 23 and got["teams_dropped"] == 1
        R = 2 * r / (1 + r)
        lo = np.tanh(np.arctanh(r) - options["critical_value"] / np.sqrt(n - 3 - 1))
        coord = got["coordinates"][name]
        assert coord["half_r"] == pytest.approx(r)
        assert coord["implied_per_match_icc"] == pytest.approx(R / (22 - 21 * R))
        assert got["minimum_lower_bound"] == pytest.approx(2 * lo / (1 + lo))
        assert got["render"] == (
            "number"
            if got["minimum_lower_bound"] >= 0.7
            else "band"
            if got["minimum_lower_bound"] >= 0.5
            else "insufficient"
        )


def test_undefined_half_bounds_cannot_support_a_number():
    import json

    rows = _double_round_robin(6).rename(
        columns={"n__wide": "n__def_left", "n__centre": "n__def_right"}
    )
    rows["n__def_centre"] = 1
    parts = ("def_left", "def_centre", "def_right")
    options = dict(
        smoothing=0.5,
        minimum_half_matches=2,
        critical_value=1.6448536269514722,
        house_confidence=0.9,
        period="test",
        band=0.5,
        number=0.7,
    )
    for frame in (rows, rows.iloc[:0], rows.assign(valid=False)):
        out = engine.split_half(frame, parts, **options)
        assert set(out["coordinates"]) == {"side_balance", "wide_versus_centre"}
        assert out["minimum_lower_bound"] is None and out["render"] == "insufficient"
        assert all(c["half_r"] is None for c in out["coordinates"].values())
        json.dumps(out, allow_nan=False)
    rows["n__def_left"] = rows.unit_id + 1
    perfect = engine.split_half(rows, parts, **options)
    assert perfect["coordinates"]["side_balance"]["half_r"] == 1
    assert perfect["minimum_lower_bound"] is None
    assert (
        engine.level_split_half(rows.assign(exposure=0), **options)["minimum_lower_bound"] is None
    )


def test_calibration_uses_held_out_rows_the_selected_candidate_and_the_shared_world():
    rows = fixtures().rename(columns={"n__wide": "n__def_left", "n__centre": "n__def_right"})
    rows = rows.assign(
        n__def_centre=1,
        date=pd.to_datetime(
            ["2018-01-08", "2018-01-10", "2018-01-11", "2018-01-16", "2018-01-17", "2018-01-18"]
        ),
    )
    parts = ("def_left", "def_centre", "def_right")
    shape = engine.walk_forward_shape(rows, replace(FORWARD, parts=parts, mirror_pairs=()))
    events = np.array([1000, 3, 4, 5, 2, 1000])
    residual = np.array(
        [[800.0, 1.0], [2.0, 1.0], [1.0, 1.0], [-3.0, 1.0], [100.0, 1.0], [800.0, 1.0]]
    )
    delta = np.zeros((2, len(rows), 2))
    delta[1, :, 0] = [1, 1, 2, -1, 1, 1]
    shape = replace(
        shape,
        eligible=np.array([1, 1, 1, 1, 1, 0], bool),
        events=events,
        residual_coordinates=residual,
        delta_coordinates_pair_excluded=delta,
    )
    world = engine.season_world(
        {"West": rows.date},
        leagues=["West"],
        evaluation_start="2018-01-10",
        seed=13,
        week_rule="W-SUN",
        replicates=40,
    )
    args = dict(minimum_events=3, **INTERVAL)
    got = engine.calibration(shape, rows, 1, world, k_unit=2, **args)
    # The first eligible evaluation week contributes (14,19), the second (15,5).
    # The 8th shares a week with the 10th but precedes the cutoff.
    draws = world.multiplicity[:, 1:]
    ratios = (draws @ np.array([14, 15])) / (draws @ np.array([19, 5]))
    assert got["side_balance"]["slope"] == pytest.approx(29 / 24)
    assert got["side_balance"]["interval"] == pytest.approx(np.quantile(ratios, [0.25, 0.75]))
    assert got["wide_versus_centre"] == {"slope": None, "interval": None}
    assert engine.calibration(shape, rows, 0, world, k_unit=None, **args) is None


def test_house_bound_confidence_matches_the_registered_critical_value():
    import json
    from pathlib import Path

    from galactico.reliability import core

    protocol = Path(__file__).resolve().parents[1] / "experiments/preregistered/E-10-conceded-shape"
    config = json.loads((protocol / "config.json").read_text())
    assert (
        core._CRITICAL_VALUES[config["house_reliability_confidence"]]
        == (config["house_reliability_critical_value"])
    )


def test_near_anticorrelation_keeps_its_finite_lower_bound():
    r = np.nextafter(-1., 0.)
    got = engine._reliability_coordinate("log_rate", r, 4, 1, 8., critical_value=1.645,
                                         house_confidence=.9, period="test")
    assert got["lower_bound"] < got["spearman_brown"] < 0
    assert np.isfinite(got["lower_bound"])
