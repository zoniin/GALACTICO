import hashlib

import numpy as np
import pandas as pd
import pytest

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
