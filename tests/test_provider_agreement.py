"""E-11 agreement statistics, weight arrays, panels, aggregates and cell resampling.

Claim: every statistic and resampling rule of ``galactico/validation/provider_agreement.py``
(PIPELINE section 5, the protocol's "Evaluation and reporting") is checked against an
oracle written from its definition: weighted average ranks counted pair by pair in
``fractions.Fraction``, an explicit two-way ANOVA, one-way random effects in
``Fraction``, aggregates summed from the input frames with pandas, and generators built
here from the frozen seed and streams. Each rule is tested with its interesting outcome
and its opposite.

The planted corpora of ``provider_agreement_synthetic`` (PIPELINE section 6) are checked
for their structure against counts written from the generator's definition, and their
population values against the scenarios' targets.

Non-claim: nothing here reads the real corpus. Every player, team and match key is
invented and every value is drawn from a seed or written by hand.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import itertools
import json
import math
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from galactico.validation import provider_agreement
from galactico.validation.provider_agreement import (
    Agreement,
    BlandAltman,
    CellResult,
    InputPanel,
    aggregated_values,
    bland_altman,
    build_panel,
    cell_agreement,
    cell_with_replicates,
    cluster_of_player,
    concordance,
    difference_decomposition,
    icc_absolute_single,
    match_weights,
    player_weights,
    stratified_rank_correlation,
    subset_difference,
    team_weights,
)
from galactico.validation.provider_agreement_synthetic import planted_corpus, population_value

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "galactico" / "validation" / "provider_agreement.py"
CONFIG = json.loads((ROOT / "experiments" / "preregistered" / "E-11-provider-agreement"
                     / "config.json").read_text(encoding="utf-8"))
WC, LL = (str(entry["key"]) for entry in CONFIG["subsets"])
POOLED = CONFIG["primary_pool"]
ROLES = list(CONFIG["rank_strata_roles"])
QUANTITIES = {entry["key"]: entry for entry in CONFIG["aggregated_player_quantities"]}
INPUTS = {entry["key"]: entry for entry in CONFIG["player_match_inputs"]}
OFFSET = Fraction(str(CONFIG["fractional_rank_offset"]))
QUANTILES = [float(q) for q in CONFIG["interval_quantiles"]]
METHOD = CONFIG["interval_quantile_method"]
B = 30


def with_config(**changes: object) -> dict:
    return {**CONFIG, **changes}


def small_minima(value: int) -> dict:
    """``minimum_units_per_rank_stratum`` with every non-null entry set to ``value``."""
    return {level: {pool: None if entry is None else value for pool, entry in pools.items()}
            for level, pools in CONFIG["minimum_units_per_rank_stratum"].items()}


# A config for invented panels of a few dozen players: it differs from the frozen one
# only in the replicate count and the unit minima.
SMALL = with_config(
    bootstrap_replicates=B,
    minimum_units={level: {pool: 10 for pool in CONFIG["pools"]} for level in CONFIG["levels"]},
    minimum_units_per_rank_stratum=small_minima(5),
    minimum_units_nonzero_on_both_providers=5,
)


# --- oracles, from the definitions --------------------------------------------------------

def weighted_pearson(a: list, b: list, w: list) -> float:
    total = sum(w)
    mean_a = sum(wi * ai for wi, ai in zip(w, a, strict=True)) / total
    mean_b = sum(wi * bi for wi, bi in zip(w, b, strict=True)) / total
    cov = sum(wi * (ai - mean_a) * (bi - mean_b) for wi, ai, bi in zip(w, a, b, strict=True))
    var_a = sum(wi * (ai - mean_a) ** 2 for wi, ai in zip(w, a, strict=True))
    var_b = sum(wi * (bi - mean_b) ** 2 for wi, bi in zip(w, b, strict=True))
    if var_a == 0 or var_b == 0:
        return math.nan
    return float(cov) / math.sqrt(float(var_a * var_b))


def oracle_order(x, y, strata, weights=None, minimum=None) -> float:
    """The order statistic counted pair by pair: inside each retained stratum
    ``rank_i = sum w_j [v_j < v_i] + (sum w_j [v_j = v_i] + 1) / 2`` and
    ``u = (rank - offset) / sum w``, then the weighted Pearson correlation of the pooled
    ``u``. Exact in ``Fraction`` up to the final square root."""
    n = len(x)
    w = [Fraction(1)] * n if weights is None else [Fraction(int(v)) for v in weights]
    units = [i for i in range(n) if math.isfinite(x[i]) and math.isfinite(y[i]) and w[i] > 0]
    counts = Counter(str(strata[i]) for i in units)
    kept = sorted(counts)
    if minimum is not None and len(kept) > 1:
        kept = [label for label in kept if counts[label] >= minimum]
    if minimum is not None and len(kept) < CONFIG["minimum_rank_strata"]:
        return math.nan
    units = [i for i in units if str(strata[i]) in kept]
    if len(units) < CONFIG["order_statistic_minimum_units"]:
        return math.nan
    u: dict[int, tuple[Fraction, Fraction]] = {}
    for label in kept:
        members = [i for i in units if str(strata[i]) == label]
        total = sum(w[i] for i in members)

        def scaled(values, i, members=members, total=total):
            below = sum(w[j] for j in members if values[j] < values[i])
            tied = sum(w[j] for j in members if values[j] == values[i])
            return (below + (tied + 1) / 2 - OFFSET) / total

        for i in members:
            u[i] = (scaled(x, i), scaled(y, i))
    return weighted_pearson([u[i][0] for i in units], [u[i][1] for i in units],
                            [w[i] for i in units])


def oracle_concordance(x, y, weights=None) -> float:
    w = [Fraction(1)] * len(x) if weights is None else [Fraction(int(v)) for v in weights]
    xs, ys = [Fraction(v) for v in x], [Fraction(v) for v in y]
    total = sum(w)
    mx = sum(a * b for a, b in zip(w, xs, strict=True)) / total
    my = sum(a * b for a, b in zip(w, ys, strict=True)) / total
    sxx = sum(a * (b - mx) ** 2 for a, b in zip(w, xs, strict=True)) / total
    syy = sum(a * (b - my) ** 2 for a, b in zip(w, ys, strict=True)) / total
    sxy = sum(a * (b - mx) * (c - my) for a, b, c in zip(w, xs, ys, strict=True)) / total
    denominator = sxx + syy + (mx - my) ** 2
    return math.nan if denominator == 0 else float(2 * sxy / denominator)


def quantile_pair(values) -> tuple[float, float]:
    low, high = np.quantile(values, QUANTILES, method=METHOD)
    return float(low), float(high)


# --- invented panels ----------------------------------------------------------------------

TEAMS = {WC: (401, 402, 403, 404), LL: (405, 406, 407, 408)}
ALL_TEAMS = np.array(sorted(team for teams in TEAMS.values() for team in teams), dtype=np.int64)
SUBSET_OF_TEAM = np.array([next(s for s, teams in TEAMS.items() if team in teams)
                           for team in ALL_TEAMS], dtype=object)
COLUMNS = ["match_key", "subset", "player_key", "team_key", "minutes_regulation",
           "open_play_passes_attempted", "open_play_passes_completed",
           "positive_xt_gain_completed_passes"]


def schedule() -> list[dict]:
    """Each subset's four invented teams meet twice; match keys in config subset order."""
    rows: list[dict] = []
    for subset, teams in TEAMS.items():
        for _ in range(2):
            for home, away in itertools.combinations(teams, 2):
                rows.append({"match_key": len(rows), "subset": subset, "home": home,
                             "away": away})
    return rows


LINKS = pd.DataFrame([{"match_key": m["match_key"], "subset": m["subset"]} for m in schedule()])


def squad(team: int) -> list[tuple[int, str]]:
    return [(team * 100 + i, ROLES[i % len(ROLES)]) for i in range(9)]


ROLE_OF = {player: role for teams in TEAMS.values() for team in teams
           for player, role in squad(team)}


def frame(rows: list[dict]) -> pd.DataFrame:
    out = pd.DataFrame(rows, columns=COLUMNS)
    out["subset"] = out["subset"].astype(object)
    return out.astype({"match_key": "int64", "player_key": "int64", "team_key": "int64",
                       **{key: "float64" for key in COLUMNS[4:]}})


def planted(seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Two input frames of the shape ``player_match_inputs`` returns: every squad player
    holds a row in every match of his team on both providers, some with zero minutes,
    the two providers' minutes and counts a few apart."""
    rng = np.random.default_rng(seed)
    rates = {player: rng.uniform(15, 60) for player in ROLE_OF}
    sb_rows, wy_rows = [], []
    for match in schedule():
        for team in (match["home"], match["away"]):
            for player, _ in squad(team):
                minutes = int(rng.choice([0, 30, 60, 90, 90, 90]))
                minutes_wy = int(np.clip(minutes + rng.integers(-3, 4), 0, 90))
                completed = int(rng.poisson(rates[player] * minutes / 90))
                completed_wy = max(0, completed + int(rng.integers(-3, 4)))
                base = {"match_key": match["match_key"], "subset": match["subset"],
                        "player_key": player, "team_key": team}
                sb_rows.append({**base, "minutes_regulation": minutes,
                                "open_play_passes_attempted": completed + int(rng.poisson(6)),
                                "open_play_passes_completed": completed,
                                "positive_xt_gain_completed_passes": completed / 80
                                + float(rng.uniform(0, 0.1))})
                wy_rows.append({**base, "minutes_regulation": minutes_wy,
                                "open_play_passes_attempted": completed_wy
                                + int(rng.poisson(6)),
                                "open_play_passes_completed": completed_wy,
                                "positive_xt_gain_completed_passes": completed_wy / 75
                                + float(rng.uniform(0, 0.1))})
    return frame(sb_rows), frame(wy_rows)


def panels(sb_frame, wy_frame, config=SMALL, links=LINKS, roles=None):
    roles = ROLE_OF if roles is None else roles
    return (build_panel(sb_frame, wy_frame, links, roles, config),
            build_panel(wy_frame, sb_frame, links, roles, config))


def world(panel: InputPanel, config=SMALL) -> dict:
    return {"match": match_weights(panel.subset_of_match, config), "matches": panel.matches,
            "player": player_weights(len(panel.players), config), "players": panel.players,
            "team": team_weights(ALL_TEAMS, SUBSET_OF_TEAM, config), "teams": ALL_TEAMS}


def aggregated(sb, wy, quantity, config=SMALL, *, pool=POOLED, scheme=None, weights=None,
               graded=False, exposure=None):
    return cell_agreement(
        sb, wy, quantity, config, level="aggregated_player", pool=pool, reader="open_play",
        valuation="regime", scheme=scheme or config["bootstrap_scheme"]["aggregated_player"],
        weights=weights if weights is not None else world(sb, config),
        exposure=config["exposure_minimum_minutes"][pool] if exposure is None else exposure,
        graded=graded)


def present_rows(sb_frame, wy_frame, pool):
    minimum = CONFIG["minimum_regulation_minutes_player_match"]
    both = sb_frame.merge(wy_frame, on=["match_key", "player_key"], suffixes=("_sb", "_wy"))
    both = both[(both["minutes_regulation_sb"] >= minimum)
                & (both["minutes_regulation_wy"] >= minimum)]
    return both if pool == POOLED else both[both["subset_sb"] == pool]


def oracle_aggregates(sb_frame, wy_frame, quantity, pool, exposure, match_weight=None):
    """``{player: (x, y)}`` for players defined on both providers, summed from the frames
    over the player-matches with the minimum on both: a ratio of sums under each
    provider's own exposure and minimum denominator."""
    both = present_rows(sb_frame, wy_frame, pool)
    out = {}
    for player, rows in both.groupby("player_key"):
        weight = (1.0 if match_weight is None
                  else np.array([match_weight[int(m)] for m in rows["match_key"]], dtype=float))
        values = []
        for side in ("sb", "wy"):
            num = float((rows[f"{quantity['numerator']}_{side}"] * weight).sum())
            den = float((rows[f"{quantity['denominator']}_{side}"] * weight).sum())
            minutes = float((rows[f"minutes_regulation_{side}"] * weight).sum())
            if minutes < exposure or ("minimum_denominator" in quantity
                                      and den < quantity["minimum_denominator"]):
                break
            values.append(quantity["scale"] * num / den)
        else:
            out[int(player)] = tuple(values)
    return out


def oracle_clusters(sb_frame, wy_frame, pool) -> dict[int, int]:
    """The team with most Wyscout minutes over the player's present cells, ties to the
    smallest team id."""
    both = present_rows(sb_frame, wy_frame, pool)
    out = {}
    for player, rows in both.groupby("player_key"):
        minutes = rows.groupby("team_key_wy")["minutes_regulation_wy"].sum()
        out[int(player)] = int(min(minutes[minutes == minutes.max()].index))
    return out


# --- the order statistic -----------------------------------------------------------------

def test_stratified_rank_correlation_equals_a_brute_force_oracle_with_ties_and_weights() -> None:
    rng = np.random.default_rng(3)
    for case in range(40):
        n = int(rng.integers(8, 30))
        x = rng.integers(0, 6, n).astype(float)  # few values: many ties
        y = (x + rng.integers(-2, 3, n)).astype(float)
        strata = rng.choice(["DF", "MD", "FW"], n)
        weights = rng.integers(0, 4, n) if case % 2 else None
        minimum = [None, 2, 4][case % 3]
        got, retained, dropped = stratified_rank_correlation(x, y, strata, weights, CONFIG,
                                                             minimum_stratum_units=minimum)
        expected = oracle_order(x, y, strata, weights, minimum)
        assert (math.isnan(got) and math.isnan(expected)) or got == pytest.approx(expected,
                                                                                    abs=1e-12)
        assert set(retained) | set(dropped) <= {"DF", "MD", "FW"}
        assert not set(retained) & set(dropped)


def test_one_stratum_and_unit_weights_give_spearman() -> None:
    x = np.array([3.0, 1.0, 4.0, 1.5, 5.0, 9.0, 2.0, 6.0])
    y = np.array([2.0, 7.0, 1.0, 8.0, 2.5, 8.5, 3.0, 4.0])
    rank_x = {v: i + 1 for i, v in enumerate(sorted(x))}
    rank_y = {v: i + 1 for i, v in enumerate(sorted(y))}
    d2 = sum((rank_x[a] - rank_y[b]) ** 2 for a, b in zip(x, y, strict=True))
    n = len(x)
    spearman = 1 - Fraction(6 * d2, n * (n * n - 1))
    got, retained, dropped = stratified_rank_correlation(
        x, y, np.full(n, "all"), None, CONFIG, minimum_stratum_units=None)
    assert got == pytest.approx(float(spearman), abs=1e-12)
    assert (retained, dropped) == (("all",), ())
    # With ties, Spearman is Pearson on average ranks.
    tied_x, tied_y = np.array([1.0, 1.0, 2.0, 3.0, 3.0]), np.array([1.0, 2.0, 2.0, 2.0, 5.0])
    average = {1.0: Fraction(3, 2), 2.0: Fraction(3), 3.0: Fraction(9, 2)}
    average_y = {1.0: Fraction(1), 2.0: Fraction(3), 5.0: Fraction(5)}
    expected = weighted_pearson([average[v] for v in tied_x], [average_y[v] for v in tied_y],
                                [Fraction(1)] * 5)
    got, _, _ = stratified_rank_correlation(tied_x, tied_y, np.full(5, "all"), None, CONFIG,
                                            minimum_stratum_units=None)
    assert got == pytest.approx(expected, abs=1e-12)


def test_a_constant_added_to_one_stratum_on_both_sides_changes_nothing() -> None:
    rng = np.random.default_rng(5)
    x, y = rng.normal(size=40), rng.normal(size=40)
    strata = np.array(["DF", "MD"] * 20)
    before, _, _ = stratified_rank_correlation(x, y, strata, None, CONFIG,
                                               minimum_stratum_units=5)
    shifted_x, shifted_y = x.copy(), y.copy()
    shifted_x[strata == "DF"] += 100.0
    shifted_y[strata == "DF"] -= 50.0
    after, _, _ = stratified_rank_correlation(shifted_x, shifted_y, strata, None, CONFIG,
                                              minimum_stratum_units=5)
    assert after == pytest.approx(before, abs=1e-12)
    # The opposite: unstratified, the same shift moves the statistic.
    pooled = np.full(40, "all")
    a, _, _ = stratified_rank_correlation(x, y, pooled, None, CONFIG, minimum_stratum_units=None)
    b, _, _ = stratified_rank_correlation(shifted_x, shifted_y, pooled, None, CONFIG,
                                          minimum_stratum_units=None)
    assert a != pytest.approx(b, abs=1e-6)


def test_a_stratum_below_its_minimum_is_dropped_and_counted() -> None:
    rng = np.random.default_rng(8)
    x, y = rng.normal(size=25), rng.normal(size=25)
    strata = np.array(["DF"] * 10 + ["MD"] * 10 + ["FW"] * 5)
    got, retained, dropped = stratified_rank_correlation(x, y, strata, None, CONFIG,
                                                         minimum_stratum_units=6)
    assert (retained, dropped) == (("DF", "MD"), ("FW",))
    keep = strata != "FW"
    assert got == pytest.approx(oracle_order(x[keep], y[keep], strata[keep]), abs=1e-12)
    # At the minimum the stratum is kept.
    _, retained, dropped = stratified_rank_correlation(x, y, strata, None, CONFIG,
                                                       minimum_stratum_units=5)
    assert (retained, dropped) == (("DF", "FW", "MD"), ())
    # A constant stratum label, or no minimum, drops nothing.
    _, retained, dropped = stratified_rank_correlation(x[:5], y[:5], strata[:5], None, CONFIG,
                                                       minimum_stratum_units=None)
    assert dropped == ()


def test_fewer_than_the_minimum_strata_is_nan_where_strata_are_defined() -> None:
    rng = np.random.default_rng(9)
    x, y = rng.normal(size=30), rng.normal(size=30)
    strata = np.array(["DF"] * 20 + ["MD"] * 10)
    assert CONFIG["minimum_rank_strata"] == 2
    got, retained, dropped = stratified_rank_correlation(x, y, strata, None, CONFIG,
                                                         minimum_stratum_units=15)
    assert math.isnan(got) and retained == ("DF",) and dropped == ("MD",)
    got, _, _ = stratified_rank_correlation(x, y, strata, None, CONFIG,
                                            minimum_stratum_units=10)
    assert math.isfinite(got)
    # One stratum is fewer than two where strata are defined, never where none are.
    single = np.full(30, "all")
    got, _, _ = stratified_rank_correlation(x, y, single, None, CONFIG, minimum_stratum_units=5)
    assert math.isnan(got)
    got, _, _ = stratified_rank_correlation(x, y, single, None, CONFIG,
                                            minimum_stratum_units=None)
    assert math.isfinite(got)


def test_a_stratum_with_zero_total_weight_contributes_no_unit() -> None:
    rng = np.random.default_rng(10)
    x, y = rng.normal(size=36), rng.normal(size=36)
    strata = np.array(["DF", "MD", "FW"] * 12)
    weights = rng.integers(1, 4, 36)
    weights[strata == "FW"] = 0
    # A replicate keeps the point estimate's strata and applies no stratum minimum.
    got, _, _ = stratified_rank_correlation(x, y, strata, weights, CONFIG,
                                            minimum_stratum_units=None)
    keep = strata != "FW"
    rest, _, _ = stratified_rank_correlation(x[keep], y[keep], strata[keep], weights[keep],
                                             CONFIG, minimum_stratum_units=None)
    assert math.isfinite(got)
    assert got == pytest.approx(rest, abs=1e-12)
    assert got == pytest.approx(oracle_order(x, y, strata, weights), abs=1e-12)


def test_a_constant_vector_and_too_few_units_are_nan() -> None:
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    for constant in (np.full(5, 2.0), np.zeros(5)):
        got, _, _ = stratified_rank_correlation(x, constant, np.full(5, "all"), None, CONFIG,
                                                minimum_stratum_units=None)
        assert math.isnan(got)
    # Constant inside each stratum is a constant pooled u: undefined.
    got, _, _ = stratified_rank_correlation(np.array([1.0, 2, 3, 4]), np.array([1.0, 1, 1, 1]),
                                            np.array(["a", "a", "b", "b"]), None, CONFIG,
                                            minimum_stratum_units=None)
    assert math.isnan(got)
    assert CONFIG["order_statistic_minimum_units"] == 3
    two, _, _ = stratified_rank_correlation(x[:2], x[:2], np.full(2, "all"), None, CONFIG,
                                            minimum_stratum_units=None)
    three, _, _ = stratified_rank_correlation(x[:3], x[:3], np.full(3, "all"), None, CONFIG,
                                              minimum_stratum_units=None)
    assert math.isnan(two) and three == pytest.approx(1.0)


def test_integer_weights_equal_duplicated_units() -> None:
    rng = np.random.default_rng(12)
    x = rng.integers(0, 8, 20).astype(float)
    y = (x + rng.integers(-3, 4, 20)).astype(float)
    strata = np.array(["DF", "MD"] * 10)
    weights = rng.integers(0, 4, 20)
    weighted, _, _ = stratified_rank_correlation(x, y, strata, weights, CONFIG,
                                                 minimum_stratum_units=None)
    repeated = np.repeat(np.arange(20), weights)
    duplicated, _, _ = stratified_rank_correlation(x[repeated], y[repeated], strata[repeated],
                                                   None, CONFIG, minimum_stratum_units=None)
    assert weighted == pytest.approx(duplicated, abs=1e-12)
    assert concordance(x, y, weights) == pytest.approx(concordance(x[repeated], y[repeated]),
                                                       abs=1e-12)


# --- concordance, ICC, Bland-Altman ---------------------------------------------------------

def test_concordance_on_hand_numbers() -> None:
    # x = 1, 2, 3; y = x + 1: s_x^2 = s_y^2 = s_xy = 2/3, mean gap 1: 2(2/3) / (4/3 + 1) = 4/7.
    assert concordance(np.array([1.0, 2, 3]), np.array([2.0, 3, 4])) == pytest.approx(4 / 7)
    x = np.array([0.5, 2.0, 2.5, 7.0, 3.0])
    assert concordance(x, x) == 1.0
    shifted = concordance(x, x + 0.5)
    assert shifted < 1.0
    assert concordance(x, x + 2.0) < shifted
    assert shifted == pytest.approx(oracle_concordance(x, x + 0.5), abs=1e-12)
    weights = np.array([1, 0, 3, 2, 1])
    assert concordance(x, x[::-1], weights) == pytest.approx(
        oracle_concordance(x, x[::-1], weights), abs=1e-12)
    assert math.isnan(concordance(np.full(3, 4.0), np.full(3, 4.0)))


def oracle_icc(x, y) -> float:
    """ICC(2,1) from an explicit two-way ANOVA table, in Fraction; the error sum of
    squares as the residual of the two-way additive fit."""
    data = [[Fraction(a), Fraction(b)] for a, b in zip(x, y, strict=True)]
    n, k = len(data), 2
    grand = sum(sum(row) for row in data) / (n * k)
    row_means = [sum(row) / k for row in data]
    column_means = [sum(row[j] for row in data) / n for j in range(k)]
    ss_rows = k * sum((m - grand) ** 2 for m in row_means)
    ss_columns = n * sum((m - grand) ** 2 for m in column_means)
    ss_error = sum((data[i][j] - row_means[i] - column_means[j] + grand) ** 2
                   for i in range(n) for j in range(k))
    msr, msc = ss_rows / (n - 1), ss_columns / (k - 1)
    mse = ss_error / ((n - 1) * (k - 1))
    return float((msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n))


def test_icc_absolute_single_equals_a_two_way_anova_in_fractions() -> None:
    rng = np.random.default_rng(14)
    for _ in range(10):
        x = rng.integers(0, 20, 12).astype(float)
        y = x + rng.integers(-4, 6, 12)
        assert icc_absolute_single(x, y) == pytest.approx(oracle_icc(x, y), abs=1e-12)
    # Hand numbers: x = 1..4, y = x + 1. MSR = 10/3, MSC = 2, MSE = 0:
    # 10/3 / (10/3 + 2 * 2 / 4) = 10/13.
    assert icc_absolute_single(np.array([1.0, 2, 3, 4]),
                               np.array([2.0, 3, 4, 5])) == pytest.approx(10 / 13)
    assert math.isnan(icc_absolute_single(np.array([1.0]), np.array([2.0])))


def test_bland_altman_on_hand_numbers() -> None:
    sb, wy = np.array([2.0, 4, 6, 8]), np.array([1.0, 4, 5, 6])
    z = CONFIG["bland_altman_z"]
    result = bland_altman(sb, wy, z)
    # d = 1, 0, 1, 2: bias 1, sd sqrt(2/3); means 5 and 4; sd_sb sqrt(20/3), sd_wy
    # sqrt(14/3); pair means 1.5, 4, 5.5, 7: slope 3 / 16.5 = 2/11.
    assert result.bias == 1.0
    assert result.sd == pytest.approx(math.sqrt(2 / 3))
    assert result.lower == pytest.approx(1 - z * math.sqrt(2 / 3))
    assert result.upper == pytest.approx(1 + z * math.sqrt(2 / 3))
    assert result.relative_bias == pytest.approx(2 / 9)
    assert result.scale_ratio == pytest.approx(math.sqrt(20 / 14))
    assert result.slope == pytest.approx(2 / 11)
    # A mean of the two provider means that is not strictly positive leaves it undefined.
    assert math.isnan(bland_altman(np.array([-1.0, 1.0]), np.array([0.0, 0.0]), z).relative_bias)
    assert math.isnan(bland_altman(np.array([1.0, 2.0]), np.array([3.0, 3.0]), z).scale_ratio)


# --- the three weight arrays ---------------------------------------------------------------

def generator(stream: str) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(
        [CONFIG["seed"], CONFIG["seed_streams"][stream]]))


def oracle_blocks(blocks, stream: str, replicates: int) -> np.ndarray:
    rng = generator(stream)
    out = np.zeros((replicates, len(blocks)), dtype=np.int16)
    for key in (entry["key"] for entry in CONFIG["subsets"]):
        columns = [i for i, block in enumerate(blocks) if block == key]
        if columns:
            m = len(columns)
            out[:, columns] = rng.multinomial(m, [1 / m] * m, size=replicates)
    return out


def test_weight_arrays_are_the_frozen_draws() -> None:
    config = with_config(bootstrap_replicates=40)
    subsets = np.array([LL, WC, WC, LL, WC, WC, LL], dtype=object)
    matches = match_weights(subsets, config)
    assert matches.shape == (40, 7) and matches.dtype == np.int16
    for key in (WC, LL):
        assert np.all(matches[:, subsets == key].sum(axis=1) == np.sum(subsets == key))
    assert np.array_equal(matches, oracle_blocks(subsets, "match_weights", 40))
    assert np.array_equal(matches, match_weights(subsets, config))

    players = player_weights(11, config)
    assert players.shape == (40, 11) and players.dtype == np.int16
    assert np.all(players.sum(axis=1) == 11)
    expected = generator("player_weights").multinomial(11, [1 / 11] * 11, size=40)
    assert np.array_equal(players, expected)

    teams = np.array([3, 8, 12, 40, 41])
    team_subsets = np.array([WC, WC, LL, WC, LL], dtype=object)
    drawn = team_weights(teams, team_subsets, config)
    assert drawn.shape == (40, 5) and drawn.dtype == np.int16
    assert np.array_equal(drawn, oracle_blocks(team_subsets, "team_weights", 40))
    assert config["bootstrap_replicates"] == 40 and CONFIG["bootstrap_replicates"] == 2000
    assert match_weights(subsets, CONFIG).shape == (2000, 7)

    # The streams are distinct: the same shape drawn on each axis differs.
    one_block = np.array([WC] * 11, dtype=object)
    assert not np.array_equal(match_weights(one_block, config), players)
    assert not np.array_equal(team_weights(np.arange(11), one_block, config), players)
    assert len(set(CONFIG["seed_streams"].values())) == len(CONFIG["seed_streams"])


def test_a_subset_with_no_match_draws_nothing() -> None:
    config = with_config(bootstrap_replicates=25)
    only_la_liga = np.array([LL] * 4, dtype=object)
    rng = generator("match_weights")
    expected = rng.multinomial(4, [0.25] * 4, size=25)
    assert np.array_equal(match_weights(only_la_liga, config), expected)
    with pytest.raises(ValueError, match="no block"):
        match_weights(np.array(["elsewhere"], dtype=object), config)
    with pytest.raises(ValueError, match="bootstrap_stratified_by_subset"):
        match_weights(only_la_liga, with_config(bootstrap_stratified_by_subset=False))
    with pytest.raises(ValueError, match="ascending"):
        team_weights(np.array([5, 4]), np.array([WC, WC], dtype=object), config)


# --- panels, clusters and aggregates -------------------------------------------------------

def hand_rows(rows) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``rows``: (match, subset, player, team, minutes_sb, minutes_wy, completed_sb,
    completed_wy, attempted_sb, attempted_wy)."""
    sb_rows, wy_rows = [], []
    for match, subset, player, team, m_sb, m_wy, c_sb, c_wy, a_sb, a_wy in rows:
        base = {"match_key": match, "subset": subset, "player_key": player, "team_key": team}
        if m_sb is not None:
            sb_rows.append({**base, "minutes_regulation": m_sb, "open_play_passes_attempted": a_sb,
                            "open_play_passes_completed": c_sb,
                            "positive_xt_gain_completed_passes": 0.0})
        if m_wy is not None:
            wy_rows.append({**base, "minutes_regulation": m_wy, "open_play_passes_attempted": a_wy,
                            "open_play_passes_completed": c_wy,
                            "positive_xt_gain_completed_passes": 0.0})
    return frame(sb_rows), frame(wy_rows)


HAND_LINKS = pd.DataFrame({"match_key": [0, 1, 2, 3], "subset": [WC, WC, LL, LL]})


def test_a_cell_is_present_only_with_the_minimum_on_both_providers() -> None:
    sb_frame, wy_frame = hand_rows([
        (0, WC, 11, 401, 90, 90, 10, 9, 20, 18),
        (1, WC, 11, 401, 90, 0, 50, 0, 60, 0),     # Wyscout credits no minute
        (2, LL, 11, 401, 90, None, 40, None, 50, None),  # no Wyscout row
        (3, LL, 11, 401, 90, 90, 12, 14, 20, 20),
    ])
    roles = {11: "MD", 12: "FW"}
    sb, wy = panels(sb_frame, wy_frame, links=HAND_LINKS, roles=roles)
    assert sb.players.tolist() == [11, 12] and sb.matches.tolist() == [0, 1, 2, 3]
    assert sb.present.tolist() == [[True, False, False, True], [False] * 4]
    assert np.array_equal(sb.present, wy.present)
    completed = sb.values["open_play_passes_completed"]
    assert completed.tolist() == [[10.0, 0.0, 0.0, 12.0], [0.0] * 4]
    assert sb.values["minutes_regulation"].tolist()[0] == [90.0, 0.0, 0.0, 90.0]
    assert sb.team_of_player_match.tolist() == [[401, 0, 0, 401], [0] * 4]
    assert sb.role_of_player.tolist() == ["MD", "FW"]
    # Present on one provider only: no aggregate and no exposure sum on either.
    quantity = QUANTITIES["completed_passes_per_90"]
    for panel, total in ((sb, 22.0), (wy, 23.0)):
        value, defined = aggregated_values(panel, quantity, CONFIG, pool=POOLED, exposure=180)
        assert defined.tolist() == [True, False]
        assert value[0] == pytest.approx(90 * total / 180)
        _, defined = aggregated_values(panel, quantity, CONFIG, pool=POOLED, exposure=181)
        assert defined.tolist() == [False, False]


def test_the_panel_refuses_what_it_cannot_hold() -> None:
    sb_frame, wy_frame = hand_rows([(0, WC, 11, 401, 90, 90, 1, 1, 2, 2)])
    with pytest.raises(ValueError, match="outfield"):
        panels(sb_frame, wy_frame, links=HAND_LINKS, roles={11: CONFIG["wy_goalkeeper_position"]})
    with pytest.raises(ValueError, match="paired player"):
        panels(sb_frame, wy_frame, links=HAND_LINKS, roles={12: "DF"})
    moved = wy_frame.assign(team_key=402)
    with pytest.raises(ValueError, match="different teams"):
        panels(sb_frame, moved, links=HAND_LINKS, roles={11: "DF"})
    with pytest.raises(ValueError, match="outfield_only_at_player_levels"):
        panels(sb_frame, wy_frame, config=with_config(outfield_only_at_player_levels=False),
               links=HAND_LINKS, roles={11: "DF"})
    sb, _ = panels(sb_frame, wy_frame, links=HAND_LINKS, roles={11: "DF"})
    leaked = {**sb.values, "open_play_passes_completed": np.ones((1, 4))}
    with pytest.raises(ValueError, match="outside a present cell"):
        dataclasses.replace(sb, values=leaked)


def test_ratio_of_sums_not_mean_of_ratios() -> None:
    sb_frame, wy_frame = hand_rows([
        (0, WC, 11, 401, 90, 90, 10, 10, 20, 20),
        (1, WC, 11, 401, 90, 90, 30, 30, 30, 30),
        (2, LL, 11, 401, 90, 90, 5, 5, 50, 50),
    ])
    sb, _ = panels(sb_frame, wy_frame, links=HAND_LINKS, roles={11: "DF"})
    value, defined = aggregated_values(sb, QUANTITIES["pass_completion"], CONFIG, pool=POOLED,
                                       exposure=270)
    assert defined.tolist() == [True]
    assert value[0] == pytest.approx(45 / 100)          # not (0.5 + 1 + 0.1) / 3
    # The pool restricts the match axis.
    value, _ = aggregated_values(sb, QUANTITIES["pass_completion"], CONFIG, pool=WC,
                                 exposure=180)
    assert value[0] == pytest.approx(40 / 50)


def test_exposure_and_minimum_denominator_apply_to_both_providers_and_a_hole_stays_a_hole():
    rows = []
    for match in range(4):
        subset = WC if match < 2 else LL
        rows += [
            (match, subset, 11, 401, 90, 90, 9, 9, 40, 40),       # defined on both
            (match, subset, 12, 401, 90, 65, 9, 9, 40, 40),       # Wyscout exposure 260
            (match, subset, 13, 401, 90, 90, 9, 9, 10, 6),        # Wyscout attempts 24
            (match, subset, 14, 401, 60, 60, 9, 9, 40, 40),       # under the gate on both
        ]
    sb_frame, wy_frame = hand_rows(rows)
    roles = {11: "DF", 12: "DF", 13: "DF", 14: "DF"}
    sb, wy = panels(sb_frame, wy_frame, links=HAND_LINKS, roles=roles)
    quantity = QUANTITIES["pass_completion"]
    assert quantity["minimum_denominator"] == 30
    x, dx = aggregated_values(sb, quantity, CONFIG, pool=POOLED, exposure=270)
    y, dy = aggregated_values(wy, quantity, CONFIG, pool=POOLED, exposure=270)
    assert dx.tolist() == [True, True, True, False]
    assert dy.tolist() == [True, False, False, False]
    assert np.isnan(x[3]) and np.isnan(y[1]) and np.isnan(y[2])   # holes, not zeros
    config = with_config(bootstrap_replicates=5)
    cell = aggregated(sb, wy, quantity, config,
                      weights={**world(sb, config), "teams": np.array([401]),
                               "team": np.ones((5, 1), dtype=np.int16)})
    assert cell.point.units == 1


def test_cluster_of_player_takes_the_team_with_most_wyscout_minutes() -> None:
    sb_frame, wy_frame = hand_rows([
        (0, WC, 11, 402, 90, 45, 1, 1, 1, 1),
        (1, WC, 11, 401, 90, 45, 1, 1, 1, 1),    # 45 and 45 in the world cup: tie
        (2, LL, 11, 405, 20, 90, 1, 1, 1, 1),
        (3, LL, 11, 405, 20, 30, 1, 1, 1, 1),    # 120 Wyscout minutes, 40 StatsBomb
        (0, WC, 12, 402, 90, 0, 1, 1, 1, 1),     # not present anywhere
    ])
    sb, wy = panels(sb_frame, wy_frame, links=HAND_LINKS, roles={11: "MD", 12: "FW"})
    minutes = wy.values["minutes_regulation"]
    assert cluster_of_player(wy, minutes, pool=WC).tolist() == [401, 0]
    assert cluster_of_player(wy, minutes, pool=LL).tolist() == [405, 0]
    assert cluster_of_player(wy, minutes, pool=POOLED).tolist() == [405, 0]
    # The Wyscout minutes decide, not the StatsBomb ones.
    assert cluster_of_player(sb, sb.values["minutes_regulation"], pool=POOLED)[0] == 401


# --- cells: the resampling schemes --------------------------------------------------------

def spy_on_aggregates(monkeypatch) -> list:
    calls: list = []
    original = provider_agreement.aggregated_values

    def spy(*args, **kwargs):
        value, defined = original(*args, **kwargs)
        calls.append((kwargs.get("match_weight"), defined.copy()))
        return value, defined

    monkeypatch.setattr(provider_agreement, "aggregated_values", spy)
    return calls


def test_the_fixed_cohort_reweights_fixed_units_by_their_team(monkeypatch) -> None:
    sb_frame, wy_frame = planted(11)
    sb, wy = panels(sb_frame, wy_frame)
    weights = world(sb)
    calls = spy_on_aggregates(monkeypatch)
    quantity = QUANTITIES["completed_passes_per_90"]
    cell = aggregated(sb, wy, quantity, weights=weights)
    # The gates and the aggregates are computed once per provider, on unweighted data.
    assert len(calls) == 2 and all(match_weight is None for match_weight, _ in calls)

    exposure = SMALL["exposure_minimum_minutes"][POOLED]
    expected = oracle_aggregates(sb_frame, wy_frame, quantity, POOLED, exposure)
    players = sorted(expected)
    assert cell.point.units == len(players) > 40
    x = [expected[p][0] for p in players]
    y = [expected[p][1] for p in players]
    strata = [ROLE_OF[p] for p in players]
    minimum = SMALL["minimum_units_per_rank_stratum"]["aggregated_player"][POOLED]
    assert cell.point.order == pytest.approx(oracle_order(x, y, strata, None, minimum), abs=1e-12)
    assert cell.point.mean_sb == pytest.approx(np.mean(x))
    assert cell.point.concordance == pytest.approx(oracle_concordance(x, y), abs=1e-12)
    clusters = oracle_clusters(sb_frame, wy_frame, POOLED)
    columns = [ALL_TEAMS.tolist().index(clusters[p]) for p in players]
    keep = [i for i, label in enumerate(strata) if label in cell.point.strata_retained]
    orders, agreements = [], []
    for b in range(B):
        w = [int(weights["team"][b, c]) for c in columns]
        orders.append(oracle_order([x[i] for i in keep], [y[i] for i in keep],
                                   [strata[i] for i in keep], [w[i] for i in keep]))
        agreements.append(oracle_concordance(x, y, w))
    valid = [i for i, value in enumerate(orders) if math.isfinite(value)]
    assert cell.valid_replicates == len(valid)
    assert cell.order_interval == pytest.approx(quantile_pair([orders[i] for i in valid]),
                                                abs=1e-9)
    assert cell.concordance_interval == pytest.approx(
        quantile_pair([agreements[i] for i in valid]), abs=1e-9)
    assert cell.replicate_mean_minus_point == pytest.approx(
        np.mean([orders[i] for i in valid]) - cell.point.order, abs=1e-9)


def test_a_replicate_in_which_a_retained_stratum_has_zero_total_weight_is_valid() -> None:
    # Every forward plays for team 401 and team 401 fields forwards only, so a replicate
    # that gives team 401 weight 0 gives the retained FW stratum zero total weight.
    roles = {player: "FW" if player // 100 == 401 else ("DF" if player % 2 else "MD")
             for player in ROLE_OF}
    sb_frame, wy_frame = planted(13)
    sb, wy = panels(sb_frame, wy_frame, roles=roles)
    weights = world(sb)
    team = weights["team"].copy()
    # Replicate 0 by hand: the World Cup block (401 to 404) and the league block.
    assert ALL_TEAMS.tolist()[:4] == [401, 402, 403, 404]
    team[0] = [0, 2, 1, 1, 1, 1, 1, 1]
    quantity = QUANTITIES["completed_passes_per_90"]
    cell, orders = cell_with_replicates(
        sb, wy, quantity, SMALL, level="aggregated_player", pool=POOLED, reader="open_play",
        valuation="regime", scheme="team_cluster_fixed_cohort",
        weights={**weights, "team": team},
        exposure=SMALL["exposure_minimum_minutes"][POOLED], graded=True)
    assert cell.point.strata_retained == ("DF", "FW", "MD")

    exposure = SMALL["exposure_minimum_minutes"][POOLED]
    expected = oracle_aggregates(sb_frame, wy_frame, quantity, POOLED, exposure)
    clusters = oracle_clusters(sb_frame, wy_frame, POOLED)
    players = sorted(expected)
    x = [expected[p][0] for p in players]
    y = [expected[p][1] for p in players]
    strata = [roles[p] for p in players]
    columns = [ALL_TEAMS.tolist().index(clusters[p]) for p in players]
    assert {clusters[p] for p in players if roles[p] == "FW"} == {401}
    rest = [i for i, label in enumerate(strata) if label != "FW"]
    w0 = [int(team[0, columns[i]]) for i in rest]
    # Valid, and equal to the statistic on the other two strata.
    assert math.isfinite(orders[0])
    assert orders[0] == pytest.approx(
        oracle_order([x[i] for i in rest], [y[i] for i in rest], [strata[i] for i in rest],
                     w0), abs=1e-12)
    assert cell.valid_replicates == int(np.isfinite(orders).sum()) == B
    # The opposite: replicate 1 weights the forwards, and all three strata enter.
    w1 = [int(team[1, c]) for c in columns]
    assert sum(w1[i] for i, label in enumerate(strata) if label == "FW") > 0
    assert orders[1] == pytest.approx(oracle_order(x, y, strata, w1), abs=1e-12)


def test_the_sensitivity_scheme_recomputes_the_gates(monkeypatch) -> None:
    sb_frame, wy_frame = planted(12)
    sb, wy = panels(sb_frame, wy_frame)
    weights = world(sb)
    calls = spy_on_aggregates(monkeypatch)
    quantity = QUANTITIES["completed_passes_per_90"]
    cell = aggregated(sb, wy, quantity, scheme="pigeonhole_match_by_player", weights=weights)
    weighted = [defined for match_weight, defined in calls if match_weight is not None]
    assert len(weighted) == 2 * B
    point_set = calls[0][1] & calls[1][1]
    replicate_sets = [weighted[2 * b] & weighted[2 * b + 1] for b in range(B)]
    assert any(not np.array_equal(units, point_set) for units in replicate_sets)

    exposure = SMALL["exposure_minimum_minutes"][POOLED]
    players = sb.players.tolist()
    orders = []
    for b in range(B):
        values = oracle_aggregates(sb_frame, wy_frame, quantity, POOLED, exposure,
                                   match_weight=weights["match"][b])
        units = [p for p in sorted(values) if ROLE_OF[p] in cell.point.strata_retained]
        orders.append(oracle_order([values[p][0] for p in units], [values[p][1] for p in units],
                                   [ROLE_OF[p] for p in units],
                                   [weights["player"][b, players.index(p)] for p in units]))
    valid = [value for value in orders if math.isfinite(value)]
    assert cell.valid_replicates == len(valid)
    assert cell.order_interval == pytest.approx(quantile_pair(valid), abs=1e-9)
    with pytest.raises(ValueError, match="primary scheme"):
        aggregated(sb, wy, quantity, scheme="pigeonhole_match_by_player", weights=weights,
                   graded=True)


def test_player_match_weights_a_cell_by_its_match_and_its_player() -> None:
    sb_frame, wy_frame = planted(13)
    sb, wy = panels(sb_frame, wy_frame)
    config = with_config(**{**SMALL, "bootstrap_replicates": 12})
    weights = world(sb, config)
    quantity = INPUTS["open_play_passes_completed"]
    both = present_rows(sb_frame, wy_frame, LL).sort_values(["player_key", "match_key"])
    x = both["open_play_passes_completed_sb"].tolist()
    y = both["open_play_passes_completed_wy"].tolist()
    strata = [ROLE_OF[p] for p in both["player_key"]]
    players = sb.players.tolist()
    for scheme in ("pigeonhole_match_by_player", "match_cluster"):
        cell = cell_agreement(sb, wy, quantity, config, level="player_match", pool=LL,
                              reader="open_play", valuation="regime", scheme=scheme,
                              weights=weights, exposure=None, graded=False)
        assert cell.point.units == len(x)
        assert cell.point.exact_share == pytest.approx(
            np.mean(np.array(x) == np.array(y)))
        orders = []
        for b in range(12):
            w = [int(weights["match"][b, m])
                 * (int(weights["player"][b, players.index(p)])
                    if scheme == "pigeonhole_match_by_player" else 1)
                 for m, p in zip(both["match_key"], both["player_key"], strict=True)]
            orders.append(oracle_order(x, y, strata, w))
        valid = [value for value in orders if math.isfinite(value)]
        assert cell.order_interval == pytest.approx(quantile_pair(valid), abs=1e-9)
    xt = cell_agreement(sb, wy, INPUTS["positive_xt_gain_completed_passes"], config,
                        level="player_match", pool=LL, reader="open_play", valuation="regime",
                        scheme="pigeonhole_match_by_player", weights=weights, exposure=None,
                        graded=False)
    assert xt.point.exact_share is None


def team_frames(seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Team-match frames of the shape ``team_match_inputs`` returns, from the planted
    player frames and a few invented entry counts."""
    rng = np.random.default_rng(seed)
    sb_frame, wy_frame = planted(seed)
    out = []
    for source in (sb_frame, wy_frame):
        teams = source.groupby(["match_key", "subset", "team_key"], as_index=False)[
            "open_play_passes_completed"].sum()
        teams["final_third_entries"] = rng.integers(5, 40, len(teams)).astype(float)
        teams["final_third_entries_wide"] = np.floor(teams["final_third_entries"] / 2)
        out.append(teams)
    return out[0], out[1]


TEAM_QUANTITIES = {entry["key"]: entry for entry in CONFIG["team_match_quantities"]}


def team_cell(sb, wy, quantity, config=SMALL, *, pool=POOLED, weights=None, graded=False,
              failed_gates=()):
    if weights is None:
        weights = {"match": match_weights(LINKS["subset"].to_numpy(dtype=object), config),
                   "matches": LINKS["match_key"].to_numpy()}
    return cell_agreement(sb, wy, quantity, config, level="team_match", pool=pool,
                          reader="open_play", valuation="regime", scheme="match_cluster",
                          weights=weights, exposure=None, graded=graded,
                          failed_gates=failed_gates)


def test_team_match_weights_a_team_match_by_its_match_and_strata_the_la_liga_pool() -> None:
    sb, wy = team_frames(21)
    weights = {"match": match_weights(LINKS["subset"].to_numpy(dtype=object), SMALL),
               "matches": LINKS["match_key"].to_numpy()}
    quantity = TEAM_QUANTITIES["open_play_passes_completed"]
    cell = team_cell(sb, wy, quantity, weights=weights)
    assert cell.point.units == 2 * len(LINKS)
    assert cell.point.strata_retained == ("all",)
    keys = sb.sort_values(["match_key", "team_key"])
    x = keys["open_play_passes_completed"].tolist()
    y = wy.sort_values(["match_key", "team_key"])["open_play_passes_completed"].tolist()
    orders = [oracle_order(x, y, ["all"] * len(x),
                           [int(weights["match"][b, m]) for m in keys["match_key"]])
              for b in range(B)]
    assert cell.order_interval == pytest.approx(
        quantile_pair([v for v in orders if math.isfinite(v)]), abs=1e-9)

    # La Liga: the team with most crosswalked matches against its opponents. All four
    # teams play six, so the smallest id is that team.
    cell = team_cell(sb, wy, quantity, pool=LL, weights=weights)
    assert cell.point.strata_retained == ("most_matches_team", "opponents")
    la_liga = keys[keys["subset"] == LL]
    labels = ["most_matches_team" if t == 405 else "opponents" for t in la_liga["team_key"]]
    xl = la_liga["open_play_passes_completed"].tolist()
    yl = wy.sort_values(["match_key", "team_key"])
    yl = yl[yl["subset"] == LL]["open_play_passes_completed"].tolist()
    assert cell.point.order == pytest.approx(oracle_order(xl, yl, labels, None, 4), abs=1e-12)
    # Drop team 405 from one match: 406 now has the most crosswalked matches.
    fewer = (sb["team_key"] != 405) | (sb["match_key"] != 12)
    cell = team_cell(sb[fewer].reset_index(drop=True), wy[fewer].reset_index(drop=True),
                     quantity, pool=LL, weights=weights)
    kept = la_liga[(la_liga["team_key"] != 405) | (la_liga["match_key"] != 12)]
    labels = ["most_matches_team" if t == 406 else "opponents" for t in kept["team_key"]]
    yk = wy.sort_values(["match_key", "team_key"])
    yk = yk[(yk["subset"] == LL) & ((yk["team_key"] != 405) | (yk["match_key"] != 12))]
    assert cell.point.order == pytest.approx(
        oracle_order(kept["open_play_passes_completed"].tolist(),
                     yk["open_play_passes_completed"].tolist(), labels, None, 4), abs=1e-12)


def test_a_team_match_ratio_needs_its_minimum_denominator_on_both_providers() -> None:
    sb, wy = team_frames(22)
    quantity = TEAM_QUANTITIES["final_third_entries_wide_share"]
    minimum = quantity["minimum_denominator"]
    defined = ((sb.sort_values(["match_key", "team_key"])["final_third_entries"] >= minimum)
               .to_numpy()
               & (wy.sort_values(["match_key", "team_key"])["final_third_entries"] >= minimum)
               .to_numpy())
    cell = team_cell(sb, wy, quantity)
    assert 0 < cell.point.units == int(defined.sum()) < len(sb)
    with pytest.raises(ValueError, match="rows differ"):
        team_cell(sb, wy.iloc[1:], quantity)


def test_concordance_cross_check_gap_is_strict_and_none_on_nan(monkeypatch) -> None:
    sb_frame, wy_frame = planted(14)
    sb, wy = panels(sb_frame, wy_frame)
    weights = world(sb)
    quantity = QUANTITIES["completed_passes_per_90"]
    assert CONFIG["ccc_icc_cross_check_tolerance"] == 0.02
    for ccc, icc, expected in ((0.03, 0.0, True), (0.02, 0.0, False), (0.0, 0.02, False),
                               (0.0, 0.025, True), (math.nan, 0.5, None), (0.5, math.nan, None)):
        monkeypatch.setattr(provider_agreement, "concordance",
                            lambda x, y, weights=None, value=ccc: value)
        monkeypatch.setattr(provider_agreement, "icc_absolute_single",
                            lambda x, y, value=icc: value)
        assert aggregated(sb, wy, quantity, weights=weights).concordance_cross_check_gap is expected


def test_the_same_weight_arrays_reach_every_quantity_and_both_providers() -> None:
    sb_frame, _ = planted(15)
    sb, wy = panels(sb_frame, sb_frame.copy())
    weights = world(sb)
    same = aggregated(sb, wy, QUANTITIES["completed_passes_per_90"], weights=weights)
    # Identical values on both providers: every replicate weights both sides alike.
    assert same.order_interval == pytest.approx((1.0, 1.0))
    assert same.concordance_interval == pytest.approx((1.0, 1.0))

    sb_frame, wy_frame = planted(16)
    sb, wy = panels(*(source.assign(
        open_play_passes_attempted=2 * source["open_play_passes_completed"])
        for source in (sb_frame, wy_frame)))
    weights = world(sb)
    single = aggregated(sb, wy, QUANTITIES["completed_passes_per_90"], weights=weights)
    twice = {**QUANTITIES["completed_passes_per_90"], "key": "twice",
             "numerator": "open_play_passes_attempted"}
    double = aggregated(sb, wy, twice, weights=weights)
    # The order statistic reads ranks only: the same replicate worlds give the same interval.
    assert double.order_interval == single.order_interval
    assert double.valid_replicates == single.valid_replicates
    # The opposite: another team world gives another interval.
    shuffled = {**weights, "team": weights["team"][:, ::-1].copy()}
    assert aggregated(sb, wy, twice, weights=shuffled).order_interval != single.order_interval
    with pytest.raises(ValueError, match="match weight columns"):
        aggregated(sb, wy, twice, scheme="pigeonhole_match_by_player",
                   weights={**weights, "matches": weights["matches"][::-1]})


def test_row_order_changes_nothing() -> None:
    sb_frame, wy_frame = planted(17)
    sb, wy = panels(sb_frame, wy_frame)
    rng = np.random.default_rng(0)
    shuffled_sb = sb_frame.iloc[rng.permutation(len(sb_frame))].reset_index(drop=True)
    shuffled_wy = wy_frame.iloc[rng.permutation(len(wy_frame))].reset_index(drop=True)
    links = LINKS.iloc[::-1].reset_index(drop=True)
    sb2, wy2 = panels(shuffled_sb, shuffled_wy, links=links)
    weights = world(sb)
    for quantity in (QUANTITIES["completed_passes_per_90"], QUANTITIES["pass_completion"]):
        assert repr(aggregated(sb, wy, quantity, weights=weights)) == repr(
            aggregated(sb2, wy2, quantity, weights=weights))
    team_sb, team_wy = team_frames(17)
    quantity = TEAM_QUANTITIES["open_play_passes_completed"]
    assert repr(team_cell(team_sb, team_wy, quantity)) == repr(
        team_cell(team_sb.iloc[::-1], team_wy.sample(frac=1.0, random_state=1), quantity))


def test_a_gate_that_reaches_the_cell_computes_nothing() -> None:
    quantity = QUANTITIES["progression"]
    cell = cell_agreement(
        None, None, quantity, SMALL, level="aggregated_player", pool=POOLED,
        reader="open_play", valuation="regime", scheme="team_cluster_fixed_cohort",
        weights={}, exposure=270, graded=True, failed_gates=["XT_SURFACE"])
    assert (cell.verdict, cell.reason, cell.flags, cell.point) == (
        "INCONCLUSIVE", "XT_SURFACE", (), None)
    ungraded = cell_agreement(
        None, None, quantity, SMALL, level="aggregated_player", pool=POOLED,
        reader="open_play", valuation="regime", scheme="team_cluster_fixed_cohort",
        weights={}, exposure=270, graded=False, failed_gates=["XT_SURFACE"])
    assert (ungraded.verdict, ungraded.reason, ungraded.point) == (None, None, None)


def test_a_role_row_is_that_role_as_one_stratum() -> None:
    sb_frame, wy_frame = planted(18)
    sb, wy = panels(sb_frame, wy_frame)
    weights = world(sb)
    quantity = QUANTITIES["completed_passes_per_90"]
    cell = aggregated(sb, wy, {**quantity, "role": "FW"}, weights=weights)
    expected = oracle_aggregates(sb_frame, wy_frame, quantity, POOLED,
                                 SMALL["exposure_minimum_minutes"][POOLED])
    forwards = [p for p in sorted(expected) if ROLE_OF[p] == "FW"]
    assert cell.point.units == len(forwards)
    assert cell.point.strata_retained == ("FW",)
    assert cell.point.order == pytest.approx(oracle_order(
        [expected[p][0] for p in forwards], [expected[p][1] for p in forwards],
        ["FW"] * len(forwards)), abs=1e-12)
    with pytest.raises(ValueError, match="role row"):
        aggregated(sb, wy, {**quantity, "role": "FW"}, weights=weights, graded=True)


# --- the difference decomposition -------------------------------------------------------

def direct_panels(differences: dict[int, list[float]], teams: dict[int, int],
                  minutes_wy: dict[int, list[float]] | None = None):
    """Two panels built directly: every player present in his matches, 90 minutes on
    the StatsBomb side, numerators set so the per-90 difference is ``differences``."""
    players = np.array(sorted(differences), dtype=np.int64)
    matches = np.arange(max(len(v) for v in differences.values()), dtype=np.int64)
    shape = (len(players), len(matches))
    present = np.zeros(shape, dtype=bool)
    team = np.zeros(shape, dtype=np.int64)
    num_sb, num_wy = np.zeros(shape), np.zeros(shape)
    min_sb, min_wy = np.zeros(shape), np.zeros(shape)
    for row, player in enumerate(players):
        for column, d in enumerate(differences[int(player)]):
            present[row, column] = True
            team[row, column] = teams[int(player)]
            min_sb[row, column] = 90.0
            min_wy[row, column] = 90.0 if minutes_wy is None else minutes_wy[int(player)][column]
            num_wy[row, column] = 10.0 * min_wy[row, column] / 90
            num_sb[row, column] = 10.0 + d
    common = {"players": players, "matches": matches,
              "subset_of_match": np.array([WC] * len(matches), dtype=object),
              "team_of_player_match": team,
              "role_of_player": np.array(["DF"] * len(players), dtype=object),
              "present": present}
    return (InputPanel(**common, values={"minutes_regulation": min_sb,
                                         "open_play_passes_completed": num_sb}),
            InputPanel(**common, values={"minutes_regulation": min_wy,
                                         "open_play_passes_completed": num_wy}))


def oracle_share(groups: list[list[Fraction]]) -> float:
    """One-way random effects, unbalanced, in Fraction."""
    k = len(groups)
    sizes = [len(g) for g in groups]
    n = sum(sizes)
    grand = sum(sum(g) for g in groups) / n
    means = [sum(g) / len(g) for g in groups]
    msb = sum(s * (m - grand) ** 2 for s, m in zip(sizes, means, strict=True)) / (k - 1)
    msw = sum((v - m) ** 2 for g, m in zip(groups, means, strict=True) for v in g) / (n - k)
    n0 = (n - Fraction(sum(s * s for s in sizes), n)) / (k - 1)
    between = max(Fraction(0), (msb - msw) / n0)
    return float(between / (between + msw))


def test_difference_decomposition_matches_one_way_anova_and_its_row_rules() -> None:
    differences = {1: [1.0, 3.0, 2.0], 2: [5.0, 4.0], 3: [-1.0, 0.0, 2.0, 1.0], 4: [7.0]}
    teams = {1: 401, 2: 402, 3: 401, 4: 402}
    sb, wy = direct_panels(differences, teams)
    quantity = QUANTITIES["completed_passes_per_90"]
    config = with_config(bootstrap_replicates=50)
    weight = team_weights(np.array([401, 402]), np.array([WC, WC], dtype=object), config)
    block = difference_decomposition(sb, wy, quantity, weight, config, pool=POOLED)
    # Player 4 holds one row, under difference_decomposition_minimum_matches.
    assert CONFIG["difference_decomposition_minimum_matches"] == 2
    assert (block["rows"], block["players"]) == (9, 3)
    groups = [[Fraction(v) for v in differences[p]] for p in (1, 2, 3)]
    assert block["between_player_share"] == pytest.approx(oracle_share(groups), abs=1e-12)
    low, high = block["interval"]
    assert low <= high
    # Rows under the minimum minutes on either provider leave the decomposition.
    floor = CONFIG["difference_decomposition_minimum_minutes"]
    sb, wy = direct_panels(differences, teams,
                           minutes_wy={1: [90, floor - 1, 90], 2: [90, 90],
                                       3: [90, 90, 90, floor], 4: [90]})
    block = difference_decomposition(sb, wy, quantity, weight, config, pool=POOLED)
    assert (block["rows"], block["players"]) == (8, 3)
    # A numerator that was not formed (a failed surface): counts only.
    progression = QUANTITIES["progression"]
    assert difference_decomposition(sb, wy, progression, weight, config, pool=POOLED) == {
        "quantity": "progression", "pool": POOLED, "rows": 8, "players": 3}
    with pytest.raises(ValueError, match="per-minute"):
        difference_decomposition(sb, wy, QUANTITIES["pass_completion"], weight, config,
                                 pool=POOLED)


@pytest.mark.parametrize(("between", "within"), [(1.0, 1.0), (0.0, 1.0), (3.0, 1.0)])
def test_difference_decomposition_recovers_planted_variance_shares(between, within) -> None:
    rng = np.random.default_rng(int(10 * between))
    differences, teams = {}, {}
    for player in range(1000, 1400):
        effect = rng.normal(0, math.sqrt(between))
        differences[player] = list(effect + rng.normal(0, math.sqrt(within),
                                                       int(rng.integers(2, 7))))
        teams[player] = 400 + player % 20
    sb, wy = direct_panels(differences, teams)
    config = with_config(bootstrap_replicates=200)
    weight = team_weights(np.arange(400, 420), np.array([WC] * 20, dtype=object), config)
    block = difference_decomposition(sb, wy, QUANTITIES["completed_passes_per_90"], weight,
                                     config, pool=POOLED)
    planted_share = between / (between + within)
    assert block["between_player_share"] == pytest.approx(planted_share, abs=0.07)
    low, high = block["interval"]
    assert low - 0.03 <= planted_share <= high + 0.03


# --- the replicates of a cell and the subset difference -------------------------------------

def test_cell_with_replicates_is_the_cell_and_the_order_statistic_of_each_replicate() -> None:
    sb, wy = panels(*planted(31))
    weights = {"match": match_weights(sb.subset_of_match, SMALL), "matches": sb.matches,
               "player": player_weights(len(sb.players), SMALL), "players": sb.players}
    arguments = dict(level="player_match", pool=POOLED, reader="open_play", valuation="regime",
                     scheme="pigeonhole_match_by_player", weights=weights, exposure=None,
                     graded=True)
    quantity = INPUTS["open_play_passes_completed"]
    cell, orders = cell_with_replicates(sb, wy, quantity, SMALL, **arguments)
    assert repr(cell) == repr(cell_agreement(sb, wy, quantity, SMALL, **arguments))
    valid = orders[np.isfinite(orders)]
    assert orders.shape == (B,) and cell.valid_replicates == len(valid) > 0
    assert cell.order_interval == pytest.approx(quantile_pair(valid), abs=1e-12)
    gated, nothing = cell_with_replicates(None, None, quantity, SMALL,
                                          **{**arguments, "weights": {}},
                                          failed_gates=["IDENTITY_COVERAGE"])
    assert gated.point is None and gated.reason == "IDENTITY_COVERAGE" and nothing is None


def hand_cell(order: float, verdict: str | None) -> CellResult:
    differences = BlandAltman(0.0, 1.0, -2.0, 2.0, 0.0, 1.0, 0.0)
    point = Agreement(units=40, strata_retained=("DF",), strata_dropped=(), mean_sb=1.0,
                      mean_wy=1.0, sd_sb=1.0, sd_wy=1.0, order=order,
                      spearman_unstratified=order, concordance=0.9, icc_absolute_single=0.9,
                      bland_altman=differences, exact_share=None)
    return CellResult(quantity="q", level="team_match", pool=WC, reader="open_play",
                      valuation="regime", exposure_minutes=None, point=point,
                      order_interval=(order - 0.1, order + 0.1), concordance_interval=None,
                      relative_bias_interval=None, replicate_mean_minus_point=0.0,
                      concordance_cross_check_gap=None, valid_replicates=4, verdict=verdict,
                      reason=None if verdict != "INCONCLUSIVE" else "UNITS", flags=())


def test_subset_difference_takes_the_replicates_valid_in_both_cells() -> None:
    first, second = hand_cell(0.9, "COMPARABLE"), hand_cell(0.75, "NOT_ESTABLISHED")
    first_orders = np.array([0.91, np.nan, 0.85, 0.80, 0.95])
    second_orders = np.array([0.70, 0.60, np.nan, 0.78, 0.65])
    found = subset_difference(first, second, first_orders, second_orders, CONFIG)
    shared = [0.91 - 0.70, 0.80 - 0.78, 0.95 - 0.65]
    assert found["difference"] == pytest.approx(0.9 - 0.75)
    assert found["interval"] == pytest.approx(list(quantile_pair(shared)))
    assert found["replicates"] == 3
    # Null when either cell is INCONCLUSIVE or ungraded; no interval without a shared
    # valid replicate; two worlds of different sizes are refused.
    assert subset_difference(first, hand_cell(0.75, "INCONCLUSIVE"), first_orders,
                             second_orders, CONFIG) is None
    assert subset_difference(hand_cell(0.9, None), second, first_orders, second_orders,
                             CONFIG) is None
    disjoint = subset_difference(first, second, np.array([0.9, np.nan]),
                                 np.array([np.nan, 0.7]), CONFIG)
    assert disjoint["interval"] is None and disjoint["replicates"] == 0
    with pytest.raises(ValueError, match="one world"):
        subset_difference(first, second, first_orders, second_orders[:3], CONFIG)


# --- planted corpora (PIPELINE section 6) ---------------------------------------------------

SCENARIOS = {entry["key"]: entry for entry in CONFIG["acceptance_scenarios"]}
GENERATOR = CONFIG["acceptance_generator"]


def schedule_counts(groups: int, club: bool) -> dict[str, int]:
    """Matches of each block, from step 2: a round robin per group, a single-elimination
    bracket of the advancing teams and the third-place match, and the club meetings."""
    per_group = GENERATOR["tournament_teams_per_group"]
    advancing = groups * GENERATOR["tournament_advance_per_group"]
    tournament = (groups * math.comb(per_group, 2) + advancing - 1
                  + int(GENERATOR["tournament_third_place_match"] and advancing >= 4))
    meetings = GENERATOR["club_block_meetings_per_opponent"]
    club_matches = (GENERATOR["club_block_opponents"] * meetings
                    - GENERATOR["club_block_opponents_met_once"] * (meetings - 1))
    return {WC: tournament, **({LL: club_matches} if club else {})}


def test_planted_corpus_structure() -> None:
    cap = CONFIG["regulation_minutes_cap"]
    low, high = GENERATOR["substitution_minute_range"]
    squad = sum(GENERATOR["squad_outfield_by_role"])
    first_ten = sum(GENERATOR["first_ten_by_role"])
    statsbomb, wyscout, info = planted_corpus([7, 7, 7], SCENARIOS["planted_comparable"],
                                              "independent", CONFIG)
    # Step 2: the default keys give the subsets' expected matches.
    assert Counter(statsbomb.subset_of_match.tolist()) == schedule_counts(
        GENERATOR["tournament_groups"], True) == {
        entry["key"]: entry["expected_matches"] for entry in CONFIG["subsets"]}
    teams = GENERATOR["tournament_groups"] * GENERATOR["tournament_teams_per_group"] + 1 \
        + GENERATOR["club_block_opponents"]
    assert len(info["teams"]) == teams and len(statsbomb.players) == teams * squad
    club = 1 + GENERATOR["club_block_opponents"]
    assert Counter(info["subset_of_team"].tolist()) == {WC: teams - club, LL: club}
    # Step 3: minutes equal on both providers, the first ten's worth per team-match, each
    # value the cap, a substitution minute, or the cap minus one.
    minutes = statsbomb.values["minutes_regulation"]
    assert np.array_equal(minutes, wyscout.values["minutes_regulation"])
    assert np.array_equal(statsbomb.present, wyscout.present)
    allowed = {cap, *range(low, high + 1), *range(cap - high, cap - low + 1)}
    assert set(np.unique(minutes[statsbomb.present]).astype(int)) <= allowed
    per_team_match = Counter()
    players_per_team_match = Counter()
    for player, match in zip(*np.nonzero(statsbomb.present), strict=True):
        key = (int(match), int(statsbomb.team_of_player_match[player, match]))
        per_team_match[key] += minutes[player, match]
        players_per_team_match[key] += 1
    assert len(per_team_match) == 2 * len(statsbomb.matches)
    assert set(per_team_match.values()) == {first_ten * cap}
    assert set(players_per_team_match.values()) == {
        first_ten + GENERATOR["substitutions_per_team_match"]}
    # Players exactly on the gate, below it and unused all exist.
    totals = minutes.sum(axis=1)
    gate = CONFIG["exposure_minimum_minutes"][POOLED]
    assert (totals == gate).any() and ((totals > 0) & (totals < gate)).any()
    assert (totals == 0).any()
    # Roles by squad slot, and the panels' invariants.
    roles = Counter(statsbomb.role_of_player.tolist())
    assert roles == {role: teams * count for role, count in
                     zip(GENERATOR["roles"], GENERATOR["squad_outfield_by_role"], strict=True)}
    assert info["quantity"] == {"key": "planted_rate", "numerator": "planted_numerator",
                                "denominator": "minutes_regulation", "scale": 90.0}
    # One seed, one corpus; another seed, another.
    again, _, _ = planted_corpus([7, 7, 7], SCENARIOS["planted_comparable"], "independent",
                                 CONFIG)
    other, _, _ = planted_corpus([7, 7, 8], SCENARIOS["planted_comparable"], "independent",
                                 CONFIG)
    assert np.array_equal(again.values["planted_numerator"],
                          statsbomb.values["planted_numerator"])
    assert not np.array_equal(other.values["planted_numerator"],
                              statsbomb.values["planted_numerator"])


def test_a_scenario_key_overrides_the_generator_and_the_count_family_counts() -> None:
    gate, _, info = planted_corpus([1], SCENARIOS["planted_gate"], "independent", CONFIG)
    assert Counter(gate.subset_of_match.tolist()) == schedule_counts(
        SCENARIOS["planted_gate"]["tournament_groups"], False)
    assert set(info["subset_of_team"].tolist()) == {WC}
    counts, wyscout, _ = planted_corpus([2], SCENARIOS["planted_count_boundary"],
                                        "count_family", CONFIG)
    for panel in (counts, wyscout):
        values = panel.values["planted_numerator"]
        assert np.array_equal(values, np.round(values)) and values.min() >= 0
    # With a Wyscout scale, the Wyscout numerators of planted_order_only are larger.
    sb, wy, _ = planted_corpus([3], SCENARIOS["planted_order_only"], "independent", CONFIG)
    assert wy.values["planted_numerator"].sum() > 1.2 * sb.values["planted_numerator"].sum()
    with pytest.raises(ValueError, match="does not name"):
        planted_corpus([4], SCENARIOS["planted_null"], "systematic", CONFIG)


@pytest.mark.parametrize(("key", "structure"), [
    ("planted_comparable", "independent"), ("planted_moderate", "systematic"),
    ("la_liga_veto_060", "team_match"), ("planted_count_boundary", "count_family")])
def test_population_values_lie_within_the_tolerance_of_their_targets(key, structure) -> None:
    """Fewer population corpora than the acceptance run uses, and the same tolerance."""
    config = with_config(acceptance_population_corpora=150)
    value = population_value(SCENARIOS[key], structure, config)
    assert abs(value - SCENARIOS[key]["target"]) <= CONFIG["acceptance_population_tolerance"]


# --- the module -----------------------------------------------------------------------

def test_module_and_tests_pass_the_licence_guard() -> None:
    spec = importlib.util.spec_from_file_location(
        "check_licensing", ROOT / "scripts" / "check_licensing.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    rule_tests = ROOT / "tests" / "test_provider_agreement_rule.py"
    assert guard.check([MODULE, Path(__file__).resolve(), rule_tests]) == []


def test_the_module_states_its_claim_and_exports_the_section_five_names() -> None:
    doc = provider_agreement.__doc__
    assert "Claim:" in doc and "Non-claim:" in doc
    assert provider_agreement.AGREEMENT_VERSION == "provider-agreement-v2"
    for name in ("InputPanel", "BlandAltman", "Agreement", "CellResult", "build_panel",
                 "cluster_of_player", "stratified_rank_correlation", "concordance",
                 "icc_absolute_single", "bland_altman", "match_weights", "player_weights",
                 "team_weights", "aggregated_values", "cell_agreement", "classify",
                 "control_holds", "permuted_link_control", "difference_decomposition",
                 "admission", "registry_verdicts"):
        assert name in provider_agreement.__all__
    for dataclass_type in (provider_agreement.InputPanel, provider_agreement.BlandAltman,
                           provider_agreement.Agreement, provider_agreement.CellResult):
        assert dataclass_type.__dataclass_params__.frozen
