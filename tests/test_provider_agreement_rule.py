"""E-11 decision rule, gates, permuted-link control, admission and registry rule.

Claim: ``classify``, ``applicable_gates``, ``control_holds``, ``permuted_link_control``,
``control_states``, ``admission`` and ``registry_verdicts`` of
``galactico/validation/provider_agreement.py`` follow the protocol's decision table,
"Order of the gates", "Models and baselines", the admission table and the registry
rule (PIPELINE sections 5 and 10). Each expected token is written from those tables,
each rule is tested with its interesting outcome and its opposite, the decision table
and the registry rule are swept over every combination of a grid, and the permuted
control is checked against an oracle that builds the derangement generator itself.

A reduced acceptance run grades the comparable, boundary and null scenarios of section 6
through the same rule, and each requirement of ``scenario_requirements`` is tested on hand
numbers with the record that meets it and the one that does not.

Non-claim: nothing here reads the real corpus; every key and value is invented. The
reduced run has fewer corpora and replicates than the acceptance stamp, so its shares
are coarser; it shows the rule and the generator behave, not the operating
characteristics the protocol states.
"""

from __future__ import annotations

import dataclasses
import inspect
import itertools
import json
import math
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from galactico.validation import provider_agreement
from galactico.validation.provider_agreement import (
    CellResult,
    InputPanel,
    admission,
    applicable_gates,
    cell_agreement,
    classify,
    control_holds,
    control_states,
    match_weights,
    permuted_link_control,
    player_weights,
    registry_verdicts,
    team_weights,
)
from galactico.validation.provider_agreement_synthetic import (
    run_acceptance,
    scenario_requirements,
    scenario_structures,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "experiments" / "preregistered" / "E-11-provider-agreement"
                     / "config.json").read_text(encoding="utf-8"))
WC, LL = (str(entry["key"]) for entry in CONFIG["subsets"])
POOLED = CONFIG["primary_pool"]
ROLES = list(CONFIG["rank_strata_roles"])
QUANTITIES = {entry["key"]: entry for entry in CONFIG["aggregated_player_quantities"]}
INPUTS = {entry["key"]: entry for entry in CONFIG["player_match_inputs"]}
TEAM_QUANTITIES = {entry["key"]: entry for entry in CONFIG["team_match_quantities"]}
TOKENS = list(CONFIG["verdict_vocabulary"]["cell"])
AGREEING = list(CONFIG["registry_token_rule"]["agreeing_tokens"])
T = CONFIG["order_statistic_lower_bound_minimum"]
MARGIN = CONFIG["relative_bias_margin"]
CCC = CONFIG["ccc_lower_bound_minimum"]
ENOUGH = CONFIG["minimum_units_nonzero_on_both_providers"]
HEADLINE = CONFIG["registry_headline_cell"]
OFFSET = Fraction(str(CONFIG["fractional_rank_offset"]))

# The tables as the protocol writes them; the config must hold the same orders.
PRECEDENCE = ["DATA_MISSING", "UNKNOWN_VOCABULARY", "MATCH_CROSSWALK", "IDENTITY_COVERAGE",
              "XT_SURFACE", "UNITS", "ONE_SIDED", "DEGENERATE", "REPLICATES",
              "UNDEFINED_STATISTIC"]
GATES = PRECEDENCE[:5]
EXCLUSIONS = ["DECLARED_VARIANT", "POSITIVE_CONTROL", "VERDICT", "LA_LIGA_SUBSET_CONTRADICTS",
              "LA_LIGA_SUBSET_UNTESTED", "PERMUTED_LINK_CONTROL"]


def with_config(**changes: object) -> dict:
    return {**CONFIG, **changes}


def test_the_config_holds_the_protocol_orders() -> None:
    assert CONFIG["inconclusive_reason_precedence"] == PRECEDENCE
    assert CONFIG["exclusion_reason_precedence"] == EXCLUSIONS
    assert CONFIG["registry_token_rule"]["row_a_control_failed"]["reason_precedence"] == [
        "POSITIVE_CONTROL", "PERMUTED_LINK_CONTROL"]
    assert (T, CCC, MARGIN, ENOUGH) == (0.8, 0.8, 0.1, 30)


# --- the decision table -------------------------------------------------------------------

# Keyword arguments of ``classify`` that pass row 1 and give COMPARABLE.
PASSING = dict(
    failed_gates=(), units=200, minimum_units=150, strata_defined=True, strata_retained=3,
    nonzero_statsbomb=200, nonzero_wyscout=200, nonzero_both=200, constant_statsbomb=False,
    constant_wyscout=False, valid_share=1.0, order_point=0.9, order_interval=(0.85, 0.95),
    concordance_interval=(0.85, 0.95), relative_bias_interval=(-0.05, 0.05),
)


def rule(**changes: object) -> tuple:
    return classify(**{**PASSING, **changes}, config=CONFIG)


def test_each_decision_row() -> None:
    assert rule() == ("COMPARABLE", None, ())
    assert rule(concordance_interval=(0.79, 0.9)) == ("COMPARABLE_IN_RANK_ONLY", None, ())
    assert rule(relative_bias_interval=(-0.2, 0.0)) == ("COMPARABLE_IN_RANK_ONLY", None, ())
    assert rule(order_point=0.7, order_interval=(0.6, 0.79)) == ("NOT_COMPARABLE", None, ())
    assert rule(order_point=0.82, order_interval=(0.75, 0.9)) == ("NOT_ESTABLISHED", None, ())
    assert rule(units=149) == ("INCONCLUSIVE", "UNITS", ())


def test_the_threshold_and_the_flag() -> None:
    admitted = set(CONFIG["acceptance_admitted_tokens"])
    # Lower bound and point exactly at the threshold are admitted.
    assert rule(order_point=T, order_interval=(T, 0.9))[0] in admitted
    assert rule(order_point=T, order_interval=(T, 0.9),
                concordance_interval=(0.5, 0.9))[0] == "COMPARABLE_IN_RANK_ONLY"
    # Lower bound at the threshold with the point below: not established, and flagged.
    assert rule(order_point=0.79, order_interval=(T, 0.9)) == (
        "NOT_ESTABLISHED", None, ("POINT_OUTSIDE_INTERVAL",))
    # A point below its interval, both at or above the threshold: row 2 or 3, flagged.
    assert rule(order_point=0.82, order_interval=(0.85, 0.95)) == (
        "COMPARABLE", None, ("POINT_OUTSIDE_INTERVAL",))
    assert rule(order_point=0.82, order_interval=(0.85, 0.95),
                concordance_interval=(0.7, 0.9)) == (
        "COMPARABLE_IN_RANK_ONLY", None, ("POINT_OUTSIDE_INTERVAL",))
    # A point above its interval, both below the threshold: still not comparable, flagged.
    assert rule(order_point=0.75, order_interval=(0.6, 0.7)) == (
        "NOT_COMPARABLE", None, ("POINT_OUTSIDE_INTERVAL",))
    # A point inside, or on a bound, is not flagged.
    assert rule(order_point=0.85, order_interval=(0.85, 0.95))[2] == ()
    assert rule(order_point=0.95, order_interval=(0.85, 0.95))[2] == ()
    # Upper bound exactly at the threshold is not established; just below excludes.
    assert rule(order_point=0.7, order_interval=(0.6, T))[0] == "NOT_ESTABLISHED"
    assert rule(order_point=0.7, order_interval=(0.6, 0.7999))[0] == "NOT_COMPARABLE"


def test_the_level_rows_are_inclusive_and_fail_closed() -> None:
    assert rule(relative_bias_interval=(-MARGIN, MARGIN))[0] == "COMPARABLE"
    assert rule(relative_bias_interval=(-MARGIN - 1e-9, 0.0))[0] == "COMPARABLE_IN_RANK_ONLY"
    assert rule(relative_bias_interval=(0.0, MARGIN + 1e-9))[0] == "COMPARABLE_IN_RANK_ONLY"
    assert rule(concordance_interval=(CCC, 0.9))[0] == "COMPARABLE"
    # NaN or missing concordance or relative bias falls to row 3, never passes row 2.
    for broken in ({"concordance_interval": (math.nan, math.nan)},
                   {"concordance_interval": None},
                   {"relative_bias_interval": (math.nan, math.nan)},
                   {"relative_bias_interval": (-0.05, math.nan)},
                   {"relative_bias_interval": None}):
        assert rule(**broken) == ("COMPARABLE_IN_RANK_ONLY", None, ())


def test_an_undefined_order_statistic_is_inconclusive() -> None:
    for broken in ({"order_point": math.nan}, {"order_interval": None},
                   {"order_interval": (math.nan, 0.9)}, {"order_interval": (0.85, math.nan)}):
        assert rule(**broken) == ("INCONCLUSIVE", "UNDEFINED_STATISTIC", ())


def holding(code: str) -> dict:
    """The one change that makes ``code`` hold from the passing case."""
    return {
        **{gate: {"failed_gates": (gate,)} for gate in GATES},
        "UNITS": {"units": 149},
        "ONE_SIDED": dict(nonzero_statsbomb=0, nonzero_both=0, constant_statsbomb=True),
        "DEGENERATE": dict(constant_wyscout=True),
        "REPLICATES": {"valid_share": 0.9499},
        "UNDEFINED_STATISTIC": {"order_point": math.nan},
    }[code]


def test_each_reason_is_returned_when_no_earlier_one_holds_and_wins_over_later_ones() -> None:
    returned = set()
    for index, code in enumerate(PRECEDENCE):
        alone = rule(**holding(code))
        assert alone == ("INCONCLUSIVE", code, ())
        returned.add(alone[1])
        # Every later reason holds too: the earlier still decides.
        later = {}
        for other in reversed(PRECEDENCE[index:]):
            change = holding(other)
            if "failed_gates" in change:
                change = {"failed_gates": tuple(later.get("failed_gates", ()))
                          + change["failed_gates"]}
            later.update(change)
        assert rule(**later)[:2] == ("INCONCLUSIVE", code)
    assert returned == set(PRECEDENCE)
    # Each gate in precedence order, whatever order the gates are listed in.
    for index, gate in enumerate(GATES):
        assert rule(failed_gates=tuple(reversed(GATES[index:])))[1] == gate
    # Fewer than minimum_rank_strata retained is UNITS where strata are defined only.
    assert rule(strata_retained=1)[1] == "UNITS"
    assert rule(strata_retained=1, strata_defined=False)[0] == "COMPARABLE"
    assert rule(valid_share=CONFIG["minimum_valid_replicate_share"])[0] == "COMPARABLE"
    assert rule(valid_share=math.nan)[1] == "REPLICATES"
    with pytest.raises(ValueError, match="not a gate"):
        rule(failed_gates=("UNITS",))


def test_missing_files_with_too_few_matches_left_is_data_missing() -> None:
    assert rule(failed_gates=("MATCH_CROSSWALK", "DATA_MISSING"))[1] == "DATA_MISSING"
    cell = cell_agreement(None, None, QUANTITIES["width"], CONFIG, level="aggregated_player",
                          pool=LL, reader="open_play", valuation="regime",
                          scheme="team_cluster_fixed_cohort", weights={}, exposure=180,
                          graded=True, failed_gates=["MATCH_CROSSWALK", "DATA_MISSING"])
    assert (cell.verdict, cell.reason, cell.point, cell.flags) == (
        "INCONCLUSIVE", "DATA_MISSING", None, ())


def test_one_sided_against_degenerate() -> None:
    # No non-zero unit on one side against a constant non-zero side: one-sided.
    assert rule(nonzero_statsbomb=0, nonzero_both=0, constant_statsbomb=True,
                constant_wyscout=True)[1] == "ONE_SIDED"
    assert rule(nonzero_wyscout=0, nonzero_both=0, constant_wyscout=True)[1] == "ONE_SIDED"
    # A side that is constant and non-zero while the other varies: degenerate.
    assert rule(constant_statsbomb=True)[1] == "DEGENERATE"
    # Too few non-zero units on the other side is not one-sided.
    assert rule(nonzero_statsbomb=0, nonzero_wyscout=ENOUGH - 1, nonzero_both=0,
                constant_statsbomb=True)[1] == "DEGENERATE"
    assert rule(nonzero_statsbomb=0, nonzero_wyscout=ENOUGH, nonzero_both=0,
                constant_statsbomb=True)[1] == "ONE_SIDED"
    assert rule(nonzero_both=ENOUGH - 1)[1] == "DEGENERATE"
    assert rule(nonzero_both=ENOUGH)[0] == "COMPARABLE"
    assert rule(nonzero_statsbomb=0, nonzero_wyscout=0, nonzero_both=0,
                constant_statsbomb=True, constant_wyscout=True)[1] == "DEGENERATE"


def table(case: dict) -> tuple:
    """The protocol's decision table, written out from its text."""
    holds = {gate: gate in case["failed_gates"] for gate in GATES}
    holds["UNITS"] = case["units"] < case["minimum_units"] or (
        case["strata_defined"] and case["strata_retained"] < CONFIG["minimum_rank_strata"])
    holds["ONE_SIDED"] = ((case["nonzero_statsbomb"] == 0 and case["nonzero_wyscout"] >= ENOUGH)
                          or (case["nonzero_wyscout"] == 0
                              and case["nonzero_statsbomb"] >= ENOUGH))
    holds["DEGENERATE"] = (case["constant_statsbomb"] or case["constant_wyscout"]
                           or case["nonzero_both"] < ENOUGH)
    holds["REPLICATES"] = not case["valid_share"] >= CONFIG["minimum_valid_replicate_share"]
    interval = case["order_interval"]
    holds["UNDEFINED_STATISTIC"] = (math.isnan(case["order_point"]) or interval is None
                                    or any(math.isnan(bound) for bound in interval))
    for code in PRECEDENCE:
        if holds[code]:
            return "INCONCLUSIVE", code, ()
    point, (low, high) = case["order_point"], interval
    ccc, rb = case["concordance_interval"], case["relative_bias_interval"]
    level = (ccc is not None and ccc[0] >= CCC and rb is not None
             and rb[0] >= -MARGIN and rb[1] <= MARGIN)
    if low >= T and point >= T:
        token = "COMPARABLE" if level else "COMPARABLE_IN_RANK_ONLY"
    elif high < T and point < T:
        token = "NOT_COMPARABLE"
    else:
        token = "NOT_ESTABLISHED"
    return token, None, ("POINT_OUTSIDE_INTERVAL",) if point < low or point > high else ()


def test_every_combination_of_the_grid_gets_exactly_one_token() -> None:
    gates = [(), ("XT_SURFACE",), ("IDENTITY_COVERAGE", "DATA_MISSING")]
    sizes = [{"units": 150}, {"units": 149}, {"strata_retained": 1},
             {"strata_retained": 1, "strata_defined": False}]
    sides = [{}, holding("ONE_SIDED"), holding("DEGENERATE"), {"nonzero_both": ENOUGH - 1}]
    shares = [0.95, 0.9499]
    points = [math.nan, 0.7, 0.79, T, 0.9]
    intervals = [(0.6, 0.79), (0.6, T), (0.75, 0.9), (T, 0.9), (0.85, 0.95), (math.nan, 0.9),
                 None]
    agreements = [None, (math.nan, math.nan), (0.79, 0.9), (CCC, 0.9)]
    biases = [None, (math.nan, math.nan), (-MARGIN, MARGIN), (-0.10000001, 0.0), (0.0, 0.11)]
    seen = Counter()
    for combo in itertools.product(gates, sizes, sides, shares, points, intervals, agreements,
                                   biases):
        gate, size, side, share, point, interval, agreement, bias = combo
        case = {**PASSING, **size, **side, "failed_gates": gate, "valid_share": share,
                "order_point": point, "order_interval": interval,
                "concordance_interval": agreement, "relative_bias_interval": bias}
        token, reason, flags = classify(**case, config=CONFIG)
        assert token in TOKENS
        assert (token, reason, flags) == table(case)
        assert (reason is None) == (token != "INCONCLUSIVE")
        assert set(flags) <= set(CONFIG["cell_flags"])
        seen[token] += 1
    assert set(seen) == set(TOKENS)


# --- which gates reach which cells ---------------------------------------------------------

def test_identity_coverage_reaches_player_levels_only_and_the_surface_xt_quantities_only():
    stopping = ["DATA_MISSING"]
    assert applicable_gates(stopping, TEAM_QUANTITIES["key_passes"], CONFIG,
                            level="team_match") == ("DATA_MISSING",)
    identity = ["IDENTITY_COVERAGE"]
    assert applicable_gates(identity, INPUTS["key_passes"], CONFIG,
                            level="player_match") == ("IDENTITY_COVERAGE",)
    assert applicable_gates(identity, QUANTITIES["width"], CONFIG,
                            level="aggregated_player") == ("IDENTITY_COVERAGE",)
    assert applicable_gates(identity, TEAM_QUANTITIES["key_passes"], CONFIG,
                            level="team_match") == ()
    surface = ["XT_SURFACE"]
    for quantity, level in ((INPUTS["positive_xt_gain_completed_passes"], "player_match"),
                            (INPUTS["xt_delta_key_passes"], "player_match"),
                            (TEAM_QUANTITIES["positive_xt_gain_completed_passes"], "team_match"),
                            (QUANTITIES["progression"], "aggregated_player"),
                            (QUANTITIES["progression_per_action"], "aggregated_player"),
                            (QUANTITIES["chance_creation"], "aggregated_player")):
        assert applicable_gates(surface, quantity, CONFIG, level=level) == ("XT_SURFACE",)
    for quantity, level in ((INPUTS["key_passes"], "player_match"),
                            (INPUTS["shot_goal_angle_sum"], "player_match"),
                            (TEAM_QUANTITIES["final_third_entries_wide_share"], "team_match"),
                            (QUANTITIES["completed_passes_per_90"], "aggregated_player"),
                            (QUANTITIES["width"], "aggregated_player")):
        assert applicable_gates(surface, quantity, CONFIG, level=level) == ()
    # A cell both reach takes the first.
    both = applicable_gates(["XT_SURFACE", "IDENTITY_COVERAGE"], QUANTITIES["progression"],
                            CONFIG, level="aggregated_player")
    assert both == ("IDENTITY_COVERAGE", "XT_SURFACE")


def team_frames(seed: int, *, zero_statsbomb: bool = False, constant_statsbomb: bool = False):
    """Two invented team-match frames over 30 matches, two teams each."""
    rng = np.random.default_rng(seed)
    rows = [{"match_key": m, "subset": WC if m < 18 else LL, "team_key": team}
            for m in range(30) for team in (300 + m % 6, 320 + m % 7)]
    sb = pd.DataFrame(rows)
    wy = sb.copy()
    truth = rng.integers(100, 600, len(sb)).astype(float)
    sb["open_play_passes_completed"] = truth
    wy["open_play_passes_completed"] = truth + rng.integers(-15, 16, len(sb))
    if zero_statsbomb:
        sb["open_play_passes_completed"] = 0.0
    if constant_statsbomb:
        sb["open_play_passes_completed"] = 5.0
    return sb, wy


TEAM_LINKS = pd.DataFrame({"match_key": range(30), "subset": [WC] * 18 + [LL] * 12})


def team_cell(sb, wy, config, *, failed_gates=()):
    weights = {"match": match_weights(TEAM_LINKS["subset"].to_numpy(dtype=object), config),
               "matches": TEAM_LINKS["match_key"].to_numpy()}
    return cell_agreement(sb, wy, TEAM_QUANTITIES["open_play_passes_completed"], config,
                          level="team_match", pool=POOLED, reader="open_play",
                          valuation="regime", scheme="match_cluster", weights=weights,
                          exposure=None, graded=True, failed_gates=failed_gates)


def test_a_cell_grades_on_the_gates_that_reach_it() -> None:
    config = with_config(bootstrap_replicates=40)
    sb, wy = team_frames(1)
    # IDENTITY_COVERAGE does not reach the team level: the cell is computed and graded
    # on its own units (60 team-matches, under the frozen minimum).
    cell = team_cell(sb, wy, config, failed_gates=["IDENTITY_COVERAGE"])
    assert cell.point is not None and cell.point.units == 60
    assert (cell.verdict, cell.reason) == ("INCONCLUSIVE", "UNITS")
    small = with_config(bootstrap_replicates=40,
                        minimum_units={**CONFIG["minimum_units"],
                                       "team_match": {POOLED: 50, WC: 30, LL: 20}})
    graded = team_cell(sb, wy, small, failed_gates=["IDENTITY_COVERAGE", "XT_SURFACE"])
    assert graded.verdict == "COMPARABLE" and graded.reason is None
    # A stopping gate reaches it: nothing is computed.
    stopped = team_cell(sb, wy, small, failed_gates=["UNKNOWN_VOCABULARY"])
    assert (stopped.verdict, stopped.reason, stopped.point) == (
        "INCONCLUSIVE", "UNKNOWN_VOCABULARY", None)
    # The cell's own counts decide one-sided against degenerate.
    zero_sb, zero_wy = team_frames(1, zero_statsbomb=True)
    assert team_cell(zero_sb, zero_wy, small).reason == "ONE_SIDED"
    constant_sb, constant_wy = team_frames(1, constant_statsbomb=True)
    assert team_cell(constant_sb, constant_wy, small).reason == "DEGENERATE"


# --- the permuted-link control -----------------------------------------------------------

def test_control_holds_on_hand_numbers() -> None:
    assert control_holds(0.9, [0.1, 0.5, 0.89])
    assert not control_holds(0.5, [0.5, 0.1])              # a tie fails
    assert not control_holds(0.9, [math.nan, 0.1])         # a NaN value fails
    assert not control_holds(math.nan, [0.1])              # a NaN point fails
    assert not control_holds(0.9, [])                      # nothing computed fails
    assert not control_holds(0.9, [None, 0.1])
    assert not control_holds(0.4, [0.5])


TEAMS = (401, 402, 403, 404)


def club_panels(seed: int, *, inverse: bool = False, under_gate=(), short_attempts=(),
                alone=()):
    """Two invented panels: four teams of twelve outfield players (four per role) meet
    twice in a round robin, every player present for 90 minutes on both providers in
    each of his team's six matches. The Wyscout counts are the StatsBomb ones plus
    noise, or with ``inverse`` ordered against them. ``under_gate`` players play two
    matches only;
    ``short_attempts`` players attempt too few passes on the Wyscout side; ``alone``
    is a list of (team, role) strata reduced to one eligible player."""
    rng = np.random.default_rng(seed)
    matches = [(home, away) for _ in range(2) for home, away in itertools.combinations(TEAMS, 2)]
    players = sorted(team * 100 + i for team in TEAMS for i in range(12))
    role = {p: ROLES[(p % 100) % 3] for p in players}
    shape = (len(players), len(matches))
    present = np.zeros(shape, dtype=bool)
    team_of = np.zeros(shape, dtype=np.int64)
    for row, player in enumerate(players):
        played = [column for column, pair in enumerate(matches) if player // 100 in pair]
        limited = player in under_gate or any(
            player // 100 == team and role[player] == code and player % 100 >= 3
            for team, code in alone)
        for column in played[:2] if limited else played:
            present[row, column] = True
            team_of[row, column] = player // 100
    minutes = np.where(present, 90.0, 0.0)
    ability = rng.uniform(10, 60, len(players))[:, None]
    completed_sb = np.where(present, rng.poisson(np.broadcast_to(ability, shape)), 0.0)
    noise = rng.integers(-4, 5, shape)
    completed_wy = np.where(present, np.maximum(0, completed_sb + noise), 0.0)
    if inverse:
        completed_wy = np.where(present, 100.0 - completed_sb, 0.0)
    attempted_sb = np.where(present, completed_sb + 12, 0.0)
    attempted_wy = np.where(present, completed_wy + 12, 0.0)
    for row, player in enumerate(players):
        if player in short_attempts:
            attempted_wy[row] = np.where(present[row], 3.0, 0.0)
            completed_wy[row] = np.where(present[row], 1.0, 0.0)
    common = {"players": np.array(players, dtype=np.int64),
              "matches": np.arange(len(matches), dtype=np.int64),
              "subset_of_match": np.array([WC] * len(matches), dtype=object),
              "team_of_player_match": team_of,
              "role_of_player": np.array([role[p] for p in players], dtype=object),
              "present": present}
    sb = InputPanel(**common, values={"minutes_regulation": minutes,
                                      "open_play_passes_completed": completed_sb.astype(float),
                                      "open_play_passes_attempted": attempted_sb.astype(float)})
    wy = InputPanel(**common, values={"minutes_regulation": minutes.copy(),
                                      "open_play_passes_completed": completed_wy.astype(float),
                                      "open_play_passes_attempted": attempted_wy.astype(float)})
    return sb, wy


# Small panels: the stratum minimum and the replicate count are the only keys changed.
CLUB = with_config(
    bootstrap_replicates=20,
    minimum_units_per_rank_stratum={**CONFIG["minimum_units_per_rank_stratum"],
                                    "aggregated_player": {POOLED: 5, WC: 5, LL: 5}})


def club_cell(sb, wy, quantity, config=CLUB, *, graded=False) -> CellResult:
    """The quantity's cell at ``registry_headline_cell`` on the club panels."""
    teams = np.array(TEAMS, dtype=np.int64)
    weights = {"match": match_weights(sb.subset_of_match, config), "matches": sb.matches,
               "player": player_weights(len(sb.players), config), "players": sb.players,
               "team": team_weights(teams, np.array([WC] * 4, dtype=object), config),
               "teams": teams}
    return cell_agreement(sb, wy, quantity, config, level=HEADLINE["level"],
                          pool=HEADLINE["pool"], reader=HEADLINE["reader"],
                          valuation=HEADLINE["valuation"],
                          scheme=config["bootstrap_scheme"][HEADLINE["level"]], weights=weights,
                          exposure=config["exposure_minimum_minutes"][HEADLINE["pool"]],
                          graded=graded)


def headline_cell(sb, wy, quantity, config=CLUB, verdict="COMPARABLE"):
    return dataclasses.replace(club_cell(sb, wy, quantity, config), verdict=verdict)


def stratum_minimum(minimum: int, **changes: object) -> dict:
    """``CLUB`` with the aggregated stratum minimum of every pool set to ``minimum``."""
    return {**CLUB, **changes, "minimum_units_per_rank_stratum": {
        **CONFIG["minimum_units_per_rank_stratum"],
        HEADLINE["level"]: dict.fromkeys(CONFIG["pools"], minimum)}}


def oracle_order(x, y, strata, minimum) -> float:
    """The unweighted order statistic counted pair by pair in Fraction."""
    counts = Counter(strata)
    kept = sorted(counts)
    if minimum is not None and len(kept) > 1:
        kept = [label for label in kept if counts[label] >= minimum]
    if minimum is not None and len(kept) < CONFIG["minimum_rank_strata"]:
        return math.nan
    units = [i for i in range(len(x)) if strata[i] in kept]
    u = {}
    for label in kept:
        members = [i for i in units if strata[i] == label]
        for i in members:
            u[i] = tuple((sum(1 for j in members if v[j] < v[i])
                          + Fraction(sum(1 for j in members if v[j] == v[i]) + 1, 2) - OFFSET)
                         / len(members) for v in (x, y))
    a, b = [u[i][0] for i in units], [u[i][1] for i in units]
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    cov = sum((p - mean_a) * (q - mean_b) for p, q in zip(a, b, strict=True))
    var = sum((p - mean_a) ** 2 for p in a) * sum((q - mean_b) ** 2 for q in b)
    return float(cov) / math.sqrt(float(var)) if var else math.nan


def oracle_partner(keys: list[int], stratum: list[tuple[int, str]], seed: int) -> list[int]:
    """Section 3 step by step: one generator, strata by ascending team then role order,
    positions in ascending key order, shuffled, then a cyclic shift."""
    rng = np.random.default_rng(np.random.SeedSequence(
        [CONFIG["seed"], CONFIG["seed_streams"]["permuted_link"], seed]))
    partner = list(range(len(keys)))
    groups = defaultdict(list)
    for position in sorted(range(len(keys)), key=lambda i: keys[i]):
        groups[(stratum[position][0], ROLES.index(stratum[position][1]))].append(position)
    for group in sorted(groups):
        s = groups[group]
        if len(s) < 2:
            continue
        o = [s[i] for i in rng.permutation(len(s))]
        for j in range(len(o)):
            partner[o[j]] = o[(j + 1) % len(o)]
    return partner


def oracle_control(sb, wy, quantity, config=CLUB) -> dict:
    """The control from its definition: aggregates summed over present cells, units
    defined on both, the Wyscout vector reassigned directly by the oracle derangement."""
    pool = HEADLINE["pool"]
    exposure = config["exposure_minimum_minutes"][pool]
    minimum = config["minimum_units_per_rank_stratum"][HEADLINE["level"]][pool]
    sides = []
    for panel in (sb, wy):
        num = panel.values[quantity["numerator"]].sum(axis=1)
        den = panel.values[quantity["denominator"]].sum(axis=1)
        minutes = panel.values["minutes_regulation"].sum(axis=1)
        defined = minutes >= exposure
        if "minimum_denominator" in quantity:
            defined &= den >= quantity["minimum_denominator"]
        sides.append((quantity["scale"] * num / np.where(den > 0, den, 1), defined))
    (x, dx), (y, dy) = sides
    units = [i for i in range(len(sb.players)) if dx[i] and dy[i]]
    keys = [int(sb.players[i]) for i in units]
    roles = [str(wy.role_of_player[i]) for i in units]
    clusters = []
    for i in units:
        minutes = Counter()
        for column in np.flatnonzero(wy.present[i]):
            minutes[int(wy.team_of_player_match[i, column])] += wy.values["minutes_regulation"][
                i, column]
        best = max(minutes.values())
        clusters.append(min(team for team, value in minutes.items() if value == best))
    xs, ys = [float(x[i]) for i in units], [float(y[i]) for i in units]
    values = []
    for seed in config["permuted_link_seeds"]:
        partner = oracle_partner(keys, list(zip(clusters, roles, strict=True)), int(seed))
        values.append(oracle_order(xs, [ys[p] for p in partner], roles, minimum))
    sizes = Counter(zip(clusters, roles, strict=True))
    return {"keys": keys, "point": oracle_order(xs, ys, roles, minimum),
            "values": sorted(values), "singletons": sum(1 for n in sizes.values() if n == 1)}


def test_the_permuted_control_equals_an_oracle_that_reassigns_the_wyscout_vector() -> None:
    quantity = QUANTITIES["completed_passes_per_90"]
    sb, wy = club_panels(1, alone=[(402, "FW")])
    headline = headline_cell(sb, wy, quantity)
    result = permuted_link_control(sb, wy, quantity, headline, CLUB)
    expected = oracle_control(sb, wy, quantity)
    assert expected["singletons"] == 1
    assert result["singleton_players"] == expected["singletons"]
    assert result["point"] == headline.point.order
    assert result["point"] == pytest.approx(expected["point"], abs=1e-12)
    assert len(result["values"]) == len(CONFIG["permuted_link_seeds"])
    assert result["values"] == pytest.approx(expected["values"], abs=1e-12)
    assert result["values"] == sorted(result["values"])
    # Related providers: the point is above twenty derangements inside team and role.
    assert result["strictly_above_all"] is True
    # The opposite: Wyscout values ordered against StatsBomb's cannot hold it.
    sb, wy = club_panels(2, inverse=True)
    unrelated = permuted_link_control(sb, wy, quantity, headline_cell(sb, wy, quantity), CLUB)
    assert unrelated["strictly_above_all"] is False
    assert unrelated["values"] == pytest.approx(oracle_control(sb, wy, quantity)["values"],
                                                abs=1e-12)


def test_the_permuted_control_keeps_the_point_estimates_units_and_uses_no_weight(
        monkeypatch) -> None:
    quantity = QUANTITIES["pass_completion"]
    sb, wy = club_panels(3, under_gate=(40101, 40204), short_attempts=(40305, 40108))
    headline = headline_cell(sb, wy, quantity)
    seen = []
    original = provider_agreement.permuted_partners

    def spy(keys, stratum, config, *, seed):
        seen.append(([int(k) for k in keys], list(stratum)))
        return original(keys, stratum, config, seed=seed)

    def refuse(*args, **kwargs):
        raise AssertionError("a weight array was drawn")

    monkeypatch.setattr(provider_agreement, "permuted_partners", spy)
    for name in ("match_weights", "player_weights", "team_weights", "block_weights"):
        monkeypatch.setattr(provider_agreement, name, refuse)
    result = permuted_link_control(sb, wy, quantity, headline, CLUB)
    expected = oracle_control(sb, wy, quantity)
    # The units are the point estimate's: nobody under the exposure gate or a minimum
    # denominator takes or gives a partner.
    assert len(seen) == len(CONFIG["permuted_link_seeds"])
    assert all(keys == expected["keys"] for keys, _ in seen)
    assert not {40101, 40204, 40305, 40108} & set(expected["keys"])
    assert headline.point.units == len(expected["keys"])
    assert result["values"] == pytest.approx(expected["values"], abs=1e-12)
    assert "weights" not in inspect.signature(permuted_link_control).parameters


def test_an_inconclusive_headline_has_no_control(monkeypatch) -> None:
    quantity = QUANTITIES["completed_passes_per_90"]
    sb, wy = club_panels(4)
    headline = headline_cell(sb, wy, quantity, verdict="INCONCLUSIVE")

    def refuse(*args, **kwargs):
        raise AssertionError("computed for an INCONCLUSIVE headline")

    monkeypatch.setattr(provider_agreement, "aggregated_values", refuse)
    monkeypatch.setattr(provider_agreement, "permuted_partners", refuse)
    assert permuted_link_control(sb, wy, quantity, headline, CLUB) == {
        "values": [], "point": None, "strictly_above_all": None, "singleton_players": None}


def test_the_permuted_link_cell_keys_are_asserted_against_the_headline_cell() -> None:
    quantity = QUANTITIES["completed_passes_per_90"]
    sb, wy = club_panels(5)
    headline = headline_cell(sb, wy, quantity)
    assert permuted_link_control(sb, wy, quantity, headline, CLUB)["point"] is not None
    for part, other in (("level", "player_match"), ("pool", WC), ("reader", "as_shipped"),
                        ("valuation", "common")):
        assert CONFIG[f"permuted_link_{part}"] == HEADLINE[part]
        with pytest.raises(ValueError, match=f"permuted_link_{part}"):
            permuted_link_control(sb, wy, quantity, headline,
                                  {**CLUB, f"permuted_link_{part}": other})
    with pytest.raises(ValueError, match="headline"):
        permuted_link_control(sb, wy, QUANTITIES["width"], headline, CLUB)
    with pytest.raises(ValueError, match="headline"):
        permuted_link_control(sb, wy, quantity, dataclasses.replace(headline, pool=WC), CLUB)
    # An ungraded cell (a sensitivity row) is not a headline.
    with pytest.raises(ValueError, match="the headline cell is not graded"):
        permuted_link_control(sb, wy, quantity, dataclasses.replace(headline, verdict=None),
                              CLUB)


def test_the_permuted_control_keeps_the_retained_rank_strata_of_the_point_estimate() -> None:
    quantity = QUANTITIES["completed_passes_per_90"]
    # Three of the sixteen forwards play under the exposure gate. Under a stratum minimum
    # of fourteen the point estimate keeps DF and MD and drops FW; every permuted value
    # is computed on those two strata, the forwards still exchanging values among
    # themselves inside their (team, role) strata.
    sb, wy = club_panels(1, under_gate=(40102, 40205, 40308))
    config = stratum_minimum(14)
    headline = headline_cell(sb, wy, quantity, config)
    assert (headline.point.strata_retained, headline.point.strata_dropped) == (
        ("DF", "MD"), ("FW",))
    result = permuted_link_control(sb, wy, quantity, headline, config)
    expected = oracle_control(sb, wy, quantity, config)
    assert result["point"] == pytest.approx(expected["point"], abs=1e-12)
    assert result["values"] == pytest.approx(expected["values"], abs=1e-12)
    # The opposite: under CLUB's minimum of five the forwards are retained, and the
    # permuted values are those of all three strata.
    kept = headline_cell(sb, wy, quantity)
    assert kept.point.strata_retained == ("DF", "FW", "MD")
    every = permuted_link_control(sb, wy, quantity, kept, CLUB)
    assert every["values"] == pytest.approx(oracle_control(sb, wy, quantity)["values"],
                                            abs=1e-12)
    assert every["values"] != pytest.approx(result["values"], abs=1e-6)


def test_a_graded_cell_left_with_one_rank_stratum_is_inconclusive_for_units() -> None:
    quantity = QUANTITIES["completed_passes_per_90"]
    # Sixteen invented players per role and a stratum minimum of fourteen. Four
    # midfielders and four forwards under the exposure gate leave DF alone, fewer than
    # minimum_rank_strata where strata are defined: row 1, UNITS, although the forty
    # units reach minimum_units.
    config = stratum_minimum(14, minimum_units={
        **CONFIG["minimum_units"], HEADLINE["level"]: dict.fromkeys(CONFIG["pools"], 30)})
    assert CONFIG["minimum_rank_strata"] == 2
    midfielders, forwards = (40101, 40104, 40201, 40204), (40102, 40105, 40202, 40205)
    sb, wy = club_panels(6, under_gate=midfielders + forwards)
    cell = club_cell(sb, wy, quantity, config, graded=True)
    assert cell.point.units == 40 and cell.point.strata_retained == ("DF",)
    assert (cell.verdict, cell.reason) == ("INCONCLUSIVE", "UNITS")
    # The opposite: with the midfielders back, DF and MD remain and the cell is graded.
    sb, wy = club_panels(6, under_gate=forwards)
    cell = club_cell(sb, wy, quantity, config, graded=True)
    assert cell.point.units == 44 and cell.point.strata_retained == ("DF", "MD")
    assert cell.verdict in TOKENS and cell.verdict != "INCONCLUSIVE"
    assert cell.reason is None


# --- admission and the registry ---------------------------------------------------------

RULE = CONFIG["admission_rule"]
SUBJECTS = list(CONFIG["registry_cell_subjects"])
POSITIVE_TEAM, POSITIVE_AGGREGATED = CONFIG["positive_controls"]
DECLARED = RULE["declared_variants_never_admitted"][0]


def cell(quantity, level, pool, verdict, reader="open_play") -> CellResult:
    return CellResult(quantity=quantity, level=level, pool=pool, reader=reader,
                      valuation=CONFIG["graded_valuation"], exposure_minutes=None, point=None,
                      order_interval=None, concordance_interval=None,
                      relative_bias_interval=None, replicate_mean_minus_point=None,
                      concordance_cross_check_gap=None, valid_replicates=0, verdict=verdict,
                      reason="UNITS" if verdict == "INCONCLUSIVE" else None, flags=())


def board(tokens=None, *, positive_team="COMPARABLE", default=("COMPARABLE", "COMPARABLE")):
    """The graded cells the two tables read: every aggregated quantity in the pooled
    and the La Liga pool at the headline reader, plus the team-match positive control.
    ``tokens`` maps a quantity to its (pooled, la_liga) tokens."""
    tokens = tokens or {}
    cells = [cell(POSITIVE_TEAM["quantity"], POSITIVE_TEAM["level"], POSITIVE_TEAM["pool"],
                  positive_team)]
    for quantity in QUANTITIES:
        pooled, la_liga = tokens.get(quantity, default)
        cells.append(cell(quantity, RULE["level"], RULE["pooled_pool"], pooled))
        cells.append(cell(quantity, RULE["level"], RULE["la_liga_pool"], la_liga))
    return cells


def controls(cells, overrides=None) -> dict:
    """Every non-INCONCLUSIVE headline holds its control unless overridden."""
    overrides = overrides or {}
    headline = {c.quantity: c.verdict for c in cells
                if c.level == RULE["level"] and c.pool == RULE["pooled_pool"]}
    return {"permuted_link": {
        quantity: {"strictly_above_all": overrides.get(
            quantity, None if verdict == "INCONCLUSIVE" else True)}
        for quantity, verdict in headline.items()}}


def admission_table(quantity, pooled, la_liga, positive, permuted) -> tuple:
    """The protocol's admission table in exclusion precedence."""
    if quantity in RULE["declared_variants_never_admitted"]:
        return "EXCLUDED", "DECLARED_VARIANT"
    if not positive:
        return "EXCLUDED", "POSITIVE_CONTROL"
    if pooled not in ("COMPARABLE", "COMPARABLE_IN_RANK_ONLY"):
        return "EXCLUDED", "VERDICT"
    if la_liga == "NOT_COMPARABLE":
        return "EXCLUDED", "LA_LIGA_SUBSET_CONTRADICTS"
    if la_liga == "INCONCLUSIVE":
        return "EXCLUDED", "LA_LIGA_SUBSET_UNTESTED"
    if permuted is not True:
        return "EXCLUDED", "PERMUTED_LINK_CONTROL"
    status = {"COMPARABLE": "ADMITTED_LEVEL_AND_ORDER",
              "COMPARABLE_IN_RANK_ONLY": "ADMITTED_ORDER_ONLY"}[pooled]
    return (status + "_LEAGUE_UNCONFIRMED" if la_liga == "NOT_ESTABLISHED" else status), None


def test_every_admission_row_in_precedence_order() -> None:
    for quantity in ("progression", DECLARED):
        for pooled, la_liga, positive, permuted in itertools.product(
                TOKENS, TOKENS, (True, False), (True, False, None)):
            cells = board({quantity: (pooled, la_liga)},
                          positive_team="COMPARABLE" if positive else "NOT_COMPARABLE")
            result = admission(cells, controls(cells, {quantity: permuted}), CONFIG)
            entry = result[quantity]
            assert (entry["status"], entry["reason"]) == admission_table(
                quantity, pooled, la_liga, positive, permuted)
            assert (entry["pooled_verdict"], entry["la_liga_verdict"]) == (pooled, la_liga)
            assert entry["status"] in CONFIG["admission_vocabulary"]
            assert set(result) == set(QUANTITIES)


def test_the_admission_rows_by_name() -> None:
    def status(tokens, **kwargs):
        cells = board(tokens, **{k: v for k, v in kwargs.items() if k == "positive_team"})
        return admission(cells, controls(cells, kwargs.get("permuted")), CONFIG)

    # The declared variant is never admitted, whatever its cells and controls.
    assert status({DECLARED: ("COMPARABLE", "COMPARABLE")})[DECLARED]["reason"] == (
        "DECLARED_VARIANT")
    # A positive-control failure excludes all; the declared variant keeps its reason.
    failed = status({}, positive_team="NOT_ESTABLISHED")
    assert {entry["reason"] for key, entry in failed.items() if key != DECLARED} == {
        "POSITIVE_CONTROL"}
    assert failed[DECLARED]["reason"] == "DECLARED_VARIANT"
    # La Liga INCONCLUSIVE excludes; NOT_ESTABLISHED gives the suffix; agreeing keeps.
    assert status({"width": ("COMPARABLE", "INCONCLUSIVE")})["width"]["reason"] == (
        "LA_LIGA_SUBSET_UNTESTED")
    assert status({"width": ("COMPARABLE", "NOT_ESTABLISHED")})["width"]["status"] == (
        "ADMITTED_LEVEL_AND_ORDER_LEAGUE_UNCONFIRMED")
    assert status({"width": ("COMPARABLE_IN_RANK_ONLY", "NOT_ESTABLISHED")})["width"][
        "status"] == "ADMITTED_ORDER_ONLY_LEAGUE_UNCONFIRMED"
    assert status({"width": ("COMPARABLE_IN_RANK_ONLY", "COMPARABLE")})["width"] == {
        "status": "ADMITTED_ORDER_ONLY", "reason": None,
        "pooled_verdict": "COMPARABLE_IN_RANK_ONLY", "la_liga_verdict": "COMPARABLE"}
    # Precedence: the La Liga contradiction is named before a failed permuted control.
    assert status({"width": ("COMPARABLE", "NOT_COMPARABLE")},
                  permuted={"width": False})["width"]["reason"] == "LA_LIGA_SUBSET_CONTRADICTS"
    assert status({"width": ("COMPARABLE", "COMPARABLE")},
                  permuted={"width": False})["width"]["reason"] == "PERMUTED_LINK_CONTROL"


def registry_table(h, s, reason, positive, permuted) -> tuple:
    """The protocol's registry rule, rows a to c."""
    if not positive:
        return "INCONCLUSIVE", "POSITIVE_CONTROL", None
    if permuted is False:
        return "INCONCLUSIVE", "PERMUTED_LINK_CONTROL", None
    if h in AGREEING and s == "NOT_COMPARABLE":
        return "NOT_ESTABLISHED", "LA_LIGA_SUBSET_CONTRADICTS", None
    second = ("LA_LIGA_SUBSET_DID_NOT_CONFIRM"
              if h in AGREEING and s in ("NOT_ESTABLISHED", "INCONCLUSIVE") else None)
    return h, reason, second


LINK_BLOCKS = [
    {"tiers": tiers, "pool": pool, **({"verdict": verdict, "reason": reason}
                                      if pool == CONFIG["link_verdict_pool"] else {})}
    for (tiers, verdict, reason) in zip(CONFIG["link_tier_sets"],
                                        ("LINK_USABLE", "LINK_NOT_ESTABLISHED", "INCONCLUSIVE"),
                                        (None, None, "EVALUATED_PLAYERS"), strict=True)
    for pool in CONFIG["pools"]
]


def link_expected() -> dict:
    by_tiers = {tuple(block["tiers"]): block for block in LINK_BLOCKS
                if block["pool"] == CONFIG["link_verdict_pool"]}
    return {subject: {"token": by_tiers[tuple(tiers)]["verdict"],
                      "reason": by_tiers[tuple(tiers)]["reason"], "second_reason": None}
            for subject, tiers in CONFIG["registry_link_subjects"].items()}


def test_registry_every_combination_of_controls_headline_and_la_liga() -> None:
    target, trigger = "progression", "width"
    assert POSITIVE_AGGREGATED["quantity"] == "completed_passes_per_90"
    rest = {q: ("NOT_ESTABLISHED", "COMPARABLE") for q in QUANTITIES}
    for h, s, positive, trigger_holds, own_holds in itertools.product(
            TOKENS, TOKENS, (True, False), (True, False), (True, False)):
        tokens = {**rest, target: (h, s), trigger: ("COMPARABLE", "COMPARABLE"),
                  "completed_passes_per_90": ("COMPARABLE", "COMPARABLE")}
        cells = board(tokens, positive_team="COMPARABLE" if positive else "NOT_COMPARABLE")
        overrides = {trigger: trigger_holds}
        if h != "INCONCLUSIVE":
            overrides[target] = own_holds
        state = controls(cells, overrides)
        tested = [q for q in SUBJECTS if tokens[q][0] in AGREEING]
        permuted = all(state["permuted_link"][q]["strictly_above_all"] is True for q in tested)
        assert control_states(cells, state, CONFIG) == (positive, permuted)
        verdicts = registry_verdicts(cells, state, LINK_BLOCKS, CONFIG)
        entry = verdicts[target]
        assert entry["token"] in TOKENS
        assert entry["token"] in (h, "NOT_ESTABLISHED", "INCONCLUSIVE")
        assert (entry["token"], entry["reason"], entry["second_reason"]) == registry_table(
            h, s, "UNITS" if h == "INCONCLUSIVE" else None, positive, permuted)
        for subject in SUBJECTS:
            reason, second = verdicts[subject]["reason"], verdicts[subject]["second_reason"]
            assert reason is None or reason in (CONFIG["registry_reason_vocabulary"]
                                                + CONFIG["inconclusive_reason_precedence"])
            assert second is None or second in CONFIG["registry_reason_vocabulary"]
            if not (positive and permuted):
                assert verdicts[subject]["token"] == "INCONCLUSIVE"
        assert {key: verdicts[key] for key in CONFIG["registry_link_subjects"]} == link_expected()


def test_registry_rows_by_name() -> None:
    def verdicts(tokens, *, positive_team="COMPARABLE", permuted=None, config=CONFIG):
        cells = board(tokens, positive_team=positive_team)
        return registry_verdicts(cells, controls(cells, permuted), LINK_BLOCKS, config)

    # A failed positive control: every cell subject INCONCLUSIVE (POSITIVE_CONTROL).
    failed = verdicts({}, positive_team="NOT_ESTABLISHED")
    assert {(failed[q]["token"], failed[q]["reason"]) for q in SUBJECTS} == {
        ("INCONCLUSIVE", "POSITIVE_CONTROL")}
    # A permuted failure on one subject with an agreeing headline: every cell subject.
    one = verdicts({}, permuted={"shot_volume": False})
    assert {(one[q]["token"], one[q]["reason"]) for q in SUBJECTS} == {
        ("INCONCLUSIVE", "PERMUTED_LINK_CONTROL")}
    # Both failing: the positive control is named.
    both = verdicts({}, positive_team="NOT_ESTABLISHED", permuted={"shot_volume": False})
    assert {both[q]["reason"] for q in SUBJECTS} == {"POSITIVE_CONTROL"}
    # A permuted value at or above the point of a non-agreeing headline fails nothing.
    quiet = verdicts({"shot_volume": ("NOT_ESTABLISHED", "COMPARABLE")},
                     permuted={"shot_volume": False})
    assert quiet["width"]["token"] == "COMPARABLE"
    assert quiet["shot_volume"] == {"token": "NOT_ESTABLISHED", "reason": None,
                                    "second_reason": None}
    # La Liga against an agreeing headline.
    assert verdicts({"width": ("COMPARABLE", "NOT_COMPARABLE")})["width"] == {
        "token": "NOT_ESTABLISHED", "reason": "LA_LIGA_SUBSET_CONTRADICTS",
        "second_reason": None}
    for la_liga in ("NOT_ESTABLISHED", "INCONCLUSIVE"):
        assert verdicts({"width": ("COMPARABLE_IN_RANK_ONLY", la_liga)})["width"] == {
            "token": "COMPARABLE_IN_RANK_ONLY", "reason": None,
            "second_reason": "LA_LIGA_SUBSET_DID_NOT_CONFIRM"}
    for la_liga in AGREEING:
        assert verdicts({"width": ("COMPARABLE", la_liga)})["width"]["second_reason"] is None
    # A headline that is not agreeing keeps its token and reason under every La Liga token.
    for h in ("NOT_ESTABLISHED", "NOT_COMPARABLE", "INCONCLUSIVE"):
        for la_liga in TOKENS:
            assert verdicts({"width": (h, la_liga)})["width"] == {
                "token": h, "reason": "UNITS" if h == "INCONCLUSIVE" else None,
                "second_reason": None}


def test_permuted_link_passed_is_null_when_nothing_was_tested() -> None:
    # Only the team-match positive control, so no subject's headline need agree.
    config = with_config(positive_controls=[POSITIVE_TEAM])
    tokens = {q: ("NOT_ESTABLISHED", "COMPARABLE") for q in QUANTITIES}
    cells = board(tokens)
    state = controls(cells, {q: False for q in QUANTITIES})
    assert control_states(cells, state, config) == (True, None)
    verdicts = registry_verdicts(cells, state, LINK_BLOCKS, config)
    # Null is not a failure: row a does not apply on its account.
    assert {verdicts[q]["token"] for q in SUBJECTS} == {"NOT_ESTABLISHED"}
    # With the frozen controls the aggregated positive control is a subject's headline, so
    # no agreeing headline means a failed positive control, not a passed permuted one.
    assert control_states(cells, state, CONFIG) == (False, None)
    # A stale state passed in is refused.
    with pytest.raises(ValueError, match="permuted_link_passed"):
        registry_verdicts(cells, {**state, "permuted_link_passed": True}, LINK_BLOCKS, config)


def test_a_run_stopped_by_a_gate() -> None:
    gate = "DATA_MISSING"
    cells = [cell_agreement(None, None, TEAM_QUANTITIES[POSITIVE_TEAM["quantity"]], CONFIG,
                            level="team_match", pool=POSITIVE_TEAM["pool"],
                            reader="open_play", valuation="regime", scheme="match_cluster",
                            weights={}, exposure=None, graded=True, failed_gates=[gate])]
    for quantity, pool in itertools.product(QUANTITIES.values(), CONFIG["pools"]):
        cells.append(cell_agreement(
            None, None, quantity, CONFIG, level="aggregated_player", pool=pool,
            reader="open_play", valuation="regime", scheme="team_cluster_fixed_cohort",
            weights={}, exposure=CONFIG["exposure_minimum_minutes"][pool], graded=True,
            failed_gates=[gate]))
    assert {(c.verdict, c.reason, c.point) for c in cells} == {("INCONCLUSIVE", gate, None)}
    headlines = {c.quantity: c for c in cells
                 if c.level == HEADLINE["level"] and c.pool == HEADLINE["pool"]}
    state = {"permuted_link": {q: permuted_link_control(None, None, QUANTITIES[q],
                                                        headlines[q], CONFIG)
                               for q in QUANTITIES}}
    assert {repr(v) for v in state["permuted_link"].values()} == {repr({
        "values": [], "point": None, "strictly_above_all": None, "singleton_players": None})}
    blocks = [{"tiers": tiers, "pool": pool, **({"verdict": "INCONCLUSIVE", "reason": gate}
                                                if pool == CONFIG["link_verdict_pool"] else {})}
              for tiers in CONFIG["link_tier_sets"] for pool in CONFIG["pools"]]
    verdicts = registry_verdicts(cells, state, blocks, CONFIG)
    assert {(verdicts[q]["token"], verdicts[q]["reason"]) for q in SUBJECTS} == {
        ("INCONCLUSIVE", "POSITIVE_CONTROL")}
    assert {(verdicts[s]["token"], verdicts[s]["reason"])
            for s in CONFIG["registry_link_subjects"]} == {("INCONCLUSIVE", gate)}
    result = admission(cells, state, CONFIG)
    assert {entry["status"] for entry in result.values()} == {"EXCLUDED"}
    assert result[DECLARED]["reason"] == "DECLARED_VARIANT"
    assert {entry["reason"] for key, entry in result.items() if key != DECLARED} == {
        "POSITIVE_CONTROL"}


def test_link_subjects_are_unchanged_by_any_control() -> None:
    for positive_team, permuted in itertools.product(("COMPARABLE", "NOT_COMPARABLE"),
                                                     (None, {"width": False})):
        cells = board({}, positive_team=positive_team)
        verdicts = registry_verdicts(cells, controls(cells, permuted), LINK_BLOCKS, CONFIG)
        assert {key: verdicts[key] for key in CONFIG["registry_link_subjects"]} == link_expected()


def test_admission_is_unchanged_by_the_registry_rule() -> None:
    cells = board({})
    state = controls(cells, {"width": False})
    verdicts = registry_verdicts(cells, state, LINK_BLOCKS, CONFIG)
    result = admission(cells, state, CONFIG)
    assert verdicts["progression"]["token"] == "INCONCLUSIVE"
    assert verdicts["progression"]["reason"] == "PERMUTED_LINK_CONTROL"
    assert result["progression"]["status"] == "ADMITTED_LEVEL_AND_ORDER"
    assert result["width"] == {"status": "EXCLUDED", "reason": "PERMUTED_LINK_CONTROL",
                               "pooled_verdict": "COMPARABLE", "la_liga_verdict": "COMPARABLE"}
    # And the opposite: an agreeing registry token while EXCLUDED (the declared variant).
    clean = registry_verdicts(cells, controls(cells), LINK_BLOCKS, CONFIG)
    assert clean[DECLARED]["token"] == "COMPARABLE"
    assert admission(cells, controls(cells), CONFIG)[DECLARED]["status"] == "EXCLUDED"


# --- the acceptance run (PIPELINE section 6) ------------------------------------------------

SCENARIOS = {entry["key"]: entry for entry in CONFIG["acceptance_scenarios"]}
REDUCED_KEYS = ("planted_comparable", "planted_boundary", "planted_null")
REDUCED = with_config(acceptance_corpora=20, acceptance_bootstrap_replicates=100,
                      acceptance_population_corpora=40,
                      acceptance_scenarios=[SCENARIOS[key] for key in REDUCED_KEYS])


@pytest.fixture(scope="module")
def reduced_run() -> dict:
    return run_acceptance(REDUCED)


def test_a_reduced_acceptance_run_for_the_comparable_boundary_and_null_scenarios(
        reduced_run) -> None:
    scenarios = reduced_run["scenarios"]
    assert list(scenarios) == list(REDUCED_KEYS)
    assert list(scenarios["planted_comparable"]) == ["independent", "systematic", "team_match"]
    assert list(scenarios["planted_null"]) == ["independent"]
    expected = {"planted_comparable": {"required_tokens", "point_inside_interval",
                                       "population", "permuted_link"},
                "planted_boundary": {"limited_tokens", "second_limited_tokens", "population"},
                "planted_null": {"required_tokens", "forbidden_tokens", "population"}}
    tolerance = CONFIG["acceptance_population_tolerance"]
    for key, structures in scenarios.items():
        scenario = SCENARIOS[key]
        for record in structures.values():
            assert record["corpora"] == REDUCED["acceptance_corpora"]
            assert list(record["tokens"]) == list(record["token_counts"]) == TOKENS
            assert all(type(count) is int for count in record["token_counts"].values())
            assert sum(record["token_counts"].values()) == record["corpora"]
            assert record["tokens"] == {token: count / record["corpora"]
                                        for token, count in record["token_counts"].items()}
            assert set(record["requirements"]) == expected[key]
            assert record["passed"] is True and all(record["requirements"].values())
            assert abs(record["population_value"] - scenario["target"]) <= tolerance
            assert record["mean_units"] > 0
    comparable = scenarios["planted_comparable"]
    for record in comparable.values():
        assert record["tokens"]["COMPARABLE"] >= 0.95
        assert record["point_inside_interval_share"] >= 0.95
        assert record["permuted_link_holds_share"] == 1.0
    null = scenarios["planted_null"]["independent"]
    assert sum(null["tokens"][token] for token in AGREEING) == 0.0
    assert null["permuted_link_holds_share"] is None
    for structure, record in scenarios["planted_boundary"].items():
        limit = SCENARIOS["planted_boundary"]["maximum_share"][structure]
        assert sum(record["tokens"][token] for token in AGREEING) <= limit
    assert reduced_run["passed"] is True


CORPORA = CONFIG["acceptance_corpora"]


def hand_record(counts: dict[str, int], *, inside: float | None = 1.0,
                population: float | None = None, held: float | None = None) -> dict:
    """A record as ``run_acceptance`` writes it: the count of corpora per token and its
    share, one division each, over the frozen ``acceptance_corpora``."""
    counts = {token: counts.get(token, 0) for token in TOKENS}
    assert sum(counts.values()) == CORPORA
    return {"corpora": CORPORA, "token_counts": counts,
            "tokens": {token: count / CORPORA for token, count in counts.items()},
            "point_inside_interval_share": inside, "population_value": population,
            "permuted_link_holds_share": held}


def met(key: str, structure: str, record: dict) -> dict:
    return scenario_requirements(SCENARIOS[key], structure, record, CONFIG)


def test_each_requirement_is_met_and_missed_on_hand_numbers() -> None:
    assert CORPORA == 200
    target = SCENARIOS["planted_comparable"]["target"]
    good = hand_record({"COMPARABLE": 190, "NOT_ESTABLISHED": 10}, inside=0.95,
                       population=target + 0.01, held=0.99)
    assert met("planted_comparable", "independent", good) == dict.fromkeys(
        ("required_tokens", "point_inside_interval", "population", "permuted_link"), True)
    short = hand_record({"COMPARABLE": 188, "NOT_ESTABLISHED": 12})
    for change, failing in (
            (dict(token_counts=short["token_counts"], tokens=short["tokens"]),
             "required_tokens"),
            (dict(point_inside_interval_share=0.94), "point_inside_interval"),
            (dict(point_inside_interval_share=None), "point_inside_interval"),
            (dict(population_value=target + 0.02), "population"),
            (dict(population_value=None), "population"),
            (dict(permuted_link_holds_share=0.98), "permuted_link"),
            (dict(permuted_link_holds_share=None), "permuted_link")):
        found = met("planted_comparable", "independent", {**good, **change})
        assert [name for name, value in found.items() if not value] == [failing]
    # A share requirement mapped by structure is read for its structure.
    power = hand_record({"COMPARABLE_IN_RANK_ONLY": 140, "NOT_ESTABLISHED": 60},
                        population=SCENARIOS["planted_power_090"]["target"], held=1.0)
    assert met("planted_power_090", "team_match", power)["required_tokens"] is True
    assert met("planted_power_090", "independent", power)["required_tokens"] is False
    # A forbidden token never occurs; a limited share is inclusive at its maximum.
    null = hand_record({"NOT_COMPARABLE": 190, "NOT_ESTABLISHED": 10}, population=0.0)
    assert met("planted_null", "independent", null)["forbidden_tokens"] is True
    null = hand_record({"NOT_COMPARABLE": 199, "COMPARABLE": 1}, population=0.0)
    assert met("planted_null", "independent", null)["forbidden_tokens"] is False
    boundary = hand_record({"COMPARABLE": 20, "NOT_COMPARABLE": 30, "NOT_ESTABLISHED": 150},
                           population=SCENARIOS["planted_boundary"]["target"])
    assert all(met("planted_boundary", "independent", boundary).values())
    boundary = hand_record({"COMPARABLE": 22, "NOT_COMPARABLE": 30, "NOT_ESTABLISHED": 148},
                           population=SCENARIOS["planted_boundary"]["target"])
    assert met("planted_boundary", "independent", boundary)["limited_tokens"] is False
    boundary = hand_record({"COMPARABLE": 20, "NOT_COMPARABLE": 32, "NOT_ESTABLISHED": 148},
                           population=SCENARIOS["planted_boundary"]["target"])
    assert met("planted_boundary", "independent", boundary)["second_limited_tokens"] is False
    # A report-only scenario requires only its population value; a scenario without the
    # population check requires none.
    report = hand_record({"NOT_COMPARABLE": 200},
                         population=SCENARIOS["planted_power_085"]["target"])
    assert met("planted_power_085", "independent", report) == {"population": True}
    gate = hand_record({"COMPARABLE": 200}, population=None)
    assert met("planted_gate", "independent", gate) == {"required_tokens": False}
    gate = hand_record({"INCONCLUSIVE": 200}, population=None)
    assert met("planted_gate", "independent", gate) == {"required_tokens": True}


def test_two_tokens_exactly_at_their_threshold_meet_it_however_the_count_splits() -> None:
    # planted_power_090: COMPARABLE and COMPARABLE_IN_RANK_ONLY must reach 0.8, which is
    # 160 of 200 corpora; 159 misses it. planted_boundary, team_match: the two may hold
    # 0.12, which is 24 of 200; 25 exceeds it. Every split of the count between the two
    # tokens is judged alike: the shares are not summed after rounding.
    assert CORPORA == 200
    assert SCENARIOS["planted_power_090"]["minimum_share"]["independent"] == 0.8
    assert SCENARIOS["planted_boundary"]["maximum_share"]["team_match"] == 0.12
    power = SCENARIOS["planted_power_090"]
    for total, expected in ((160, True), (159, False)):
        for comparable in range(total + 1):
            record = hand_record({"COMPARABLE": comparable,
                                  "COMPARABLE_IN_RANK_ONLY": total - comparable,
                                  "NOT_ESTABLISHED": CORPORA - total},
                                 population=power["target"], held=1.0)
            for structure in ("independent", "systematic"):
                assert met("planted_power_090", structure, record)["required_tokens"] is (
                    expected), (total, comparable, structure)
    boundary = SCENARIOS["planted_boundary"]
    for total, expected in ((24, True), (25, False)):
        for comparable in range(total + 1):
            record = hand_record({"COMPARABLE": comparable,
                                  "COMPARABLE_IN_RANK_ONLY": total - comparable,
                                  "NOT_ESTABLISHED": CORPORA - total},
                                 population=boundary["target"])
            found = met("planted_boundary", "team_match", record)
            assert found["limited_tokens"] is expected, (total, comparable)
            assert found["second_limited_tokens"] is True


def test_each_scenario_names_its_structures() -> None:
    for scenario in CONFIG["acceptance_scenarios"]:
        structures = scenario_structures(scenario, CONFIG)
        if scenario.get("count_family"):
            assert structures == ["count_family"]
        else:
            assert structures == list(scenario["coder_sd"])
    assert sum(len(scenario_structures(s, CONFIG)) for s in CONFIG["acceptance_scenarios"]) == 37
