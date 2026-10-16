"""Harmonised frames, reference surfaces, inputs and event pairing of E-11, synthetic only.

Every frame below is built in memory, or written into a temporary directory, from a
seed or by hand: names, ids, seconds and coordinates are invented, and no row is
copied from either provider. Kind, type and subtype names are the providers'
vocabulary as the frozen config lists it, and every number the functions read is the
frozen config's, except where a test changes a key through ``with_keys`` and says so:
the expected match counts and the folder of the two reference corpora, set to the
test's own corpus; ``xt_max_iterations``, so that a fit stops short of converging;
and, in the refusal tests, ``xt_wy_reference_excludes_double_coded_matches``,
``xt_recipe`` and ``sb_location_scale``. Each expected value is written from
PIPELINE.md section 4 with hand numbers, ``itertools``, ``math`` and ``fractions``;
nothing from the module under test computes one. No test opens anything under
``data/``.
"""

from __future__ import annotations

import copy
import importlib.util
import inspect
import itertools
import json
import math
import random
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from galactico.domain.thesis import banned_key_paths
from galactico.features.spec import ActionFilter
from galactico.models.xt import ExpectedThreat, PitchGrid, fit_expected_threat
from galactico.providers.pappalardo import _SET_PIECE_SUBTYPE
from galactico.validation import provider_inputs
from galactico.validation.provider_inputs import (
    FLAGS,
    HARMONISED_COLUMNS,
    INPUTS_VERSION,
    WY_ACTION_COLUMNS,
    SurfaceUnfit,
    clock_offsets,
    divergence_tables,
    goal_angle,
    harmonise_statsbomb,
    harmonise_wyscout,
    in_penalty_area,
    pair_events,
    player_match_inputs,
    read_wyscout_actions,
    sheet_minutes,
    statsbomb_reference_surface,
    team_match_inputs,
    wyscout_reference_surface,
    xt_delta,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads(
    (ROOT / "experiments/preregistered/E-11-provider-agreement/config.json")
    .read_text(encoding="utf-8"))
SCALE = CONFIG["sb_location_scale"]
PAIRED = CONFIG["paired_status"]
SB_BOX, WY_BOX = CONFIG["penalty_area_sb"], CONFIG["penalty_area_wy"]
LENGTH, WIDTH, GOAL = CONFIG["pitch_length_m"], CONFIG["pitch_width_m"], CONFIG["goal_width_m"]
REFERENCE_FOLDER = "Invented_League_2030"

# The table of PIPELINE.md section 4, in its order, typed out again.
FLAG_TABLE = (
    "open_play_pass", "completed", "key_pass", "key_pass_assist_inclusive", "corner",
    "free_kick_pass", "throw_in", "goal_kick", "open_play_shot", "free_kick_shot", "penalty",
    "non_penalty_shot", "goal", "ground_duel", "interception", "foul", "duel_or_interception",
    "defensive_action", "clearance", "turnover", "sb_one_sided", "wy_one_sided",
)
PLAYER_INPUTS = (
    "minutes_regulation", "open_play_passes_attempted", "open_play_passes_completed",
    "positive_xt_gain_completed_passes", "xt_delta_key_passes",
    "xt_delta_key_passes_assist_inclusive", "key_passes", "completed_passes_from_half_space",
    "completed_passes_from_wide", "non_penalty_shots", "open_play_shots",
    "open_play_shots_in_penalty_area", "shot_goal_angle_sum", "defensive_actions",
    "opp_half_duel_or_interception",
)

SB_EVENT_DTYPES = {
    "sb_game_id": "int64", "period": "int8", "period_seconds": "float64",
    "event_order": "int64", "sb_team_id": "int64", "sb_player_id": "Int64", "kind": object,
    "start_x": "float64", "start_y": "float64", "end_x": "float64", "end_y": "float64",
    "has_outcome": "bool", "outcome": object, "pass_type": object, "pass_height": object,
    "pass_cross": "bool", "shot_assist": "bool", "goal_assist": "bool", "shot_type": object,
    "duel_type": object, "play_pattern": object, "event_id": object,
}
WY_ACTION_DTYPES = {
    "game_id": "int64", "competition": object, "period": object, "seconds": "float64",
    "team_id": "int64", "player_id": "int64", "type": object, "subtype": object,
    "start_x": "float64", "start_y": "float64", "end_x": "float64", "end_y": "float64",
    "success": object, "goal": "bool", "assist": "bool", "key_pass": "bool",
    "counter_attack": "bool", "interception": "bool", "clearance": "bool",
    "dangerous_loss": "bool", "provider": object, "event_id": "int64",
}
LINK_DTYPES = {
    "match_key": "int32", "subset": object, "sb_game_id": "int64", "wy_game_id": "int64",
    "date": object, "swapped": "bool", "duration": object, "goal_check": object,
    "sb_home_team_id": "int64", "sb_away_team_id": "int64",
    "wy_team_for_sb_home": "int64", "wy_team_for_sb_away": "int64",
}
PAIR_DTYPES = {
    "sb_player_id": "int64", "wy_player_id": "int64", "status": object,
    "sheets_named": "int64", "sheets_together": "int64", "sheets_structure_passed": "int64",
    "swap_impossible": "bool", "is_goalkeeper": "bool",
}


# Invented matches -----------------------------------------------------------------


@dataclass(frozen=True)
class Side:
    """One team of a linked match: its two ids, two paired outfield players, a paired
    goalkeeper, and one player each provider names that the other does not."""

    sb_team: int
    wy_team: int
    paired: tuple[tuple[int, int], ...]
    keeper: tuple[int, int]
    sb_unpaired: int
    wy_unpaired: int


@dataclass(frozen=True)
class Match:
    key: int
    subset: str
    sb_game: int
    wy_game: int
    home: Side
    away: Side


def make_match(rng: random.Random, key: int, subset: str = "world_cup") -> Match:
    ids = iter(rng.sample(range(10_000, 9_999_999), 22))

    def side() -> Side:
        return Side(next(ids), next(ids), ((next(ids), next(ids)), (next(ids), next(ids))),
                    (next(ids), next(ids)), next(ids), next(ids))

    return Match(key, subset, next(ids), next(ids), side(), side())


def links_of(*matches: Match) -> pd.DataFrame:
    rows = [{"match_key": m.key, "subset": m.subset, "sb_game_id": m.sb_game,
             "wy_game_id": m.wy_game, "date": f"2031-05-{1 + m.key:02d}", "swapped": False,
             "duration": "Regular", "goal_check": "agree", "sb_home_team_id": m.home.sb_team,
             "sb_away_team_id": m.away.sb_team, "wy_team_for_sb_home": m.home.wy_team,
             "wy_team_for_sb_away": m.away.wy_team} for m in matches]
    return table(rows, LINK_DTYPES)


def pairs_of(*matches: Match, extra: tuple[tuple[int, int, str], ...] = ()) -> pd.DataFrame:
    rows = []
    for m in matches:
        for side in (m.home, m.away):
            rows += [pair_row(sb, wy, PAIRED, False) for sb, wy in side.paired]
            rows.append(pair_row(*side.keeper, PAIRED, True))
    rows += [pair_row(sb, wy, status, False) for sb, wy, status in extra]
    return table(rows, PAIR_DTYPES)


def pair_row(sb: int, wy: int, status: str, keeper: bool) -> dict:
    return {"sb_player_id": sb, "wy_player_id": wy, "status": status, "sheets_named": 1,
            "sheets_together": 1, "sheets_structure_passed": 1, "swap_impossible": True,
            "is_goalkeeper": keeper}


def table(rows: list[dict], dtypes: dict) -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series([row[c] for row in rows], dtype=d)
                         for c, d in dtypes.items()})


def sb_frame(rows: list[dict]) -> pd.DataFrame:
    """A ``read_events`` frame; ``event_order`` runs in list order unless given."""
    base = {"period": 1, "period_seconds": 1.0, "sb_player_id": None, "start_x": np.nan,
            "start_y": np.nan, "end_x": np.nan, "end_y": np.nan, "has_outcome": False,
            "outcome": None, "pass_type": None, "pass_height": None, "pass_cross": False,
            "shot_assist": False, "goal_assist": False, "shot_type": None, "duel_type": None,
            "play_pattern": "Invented Pattern"}
    full = [{**base, "event_order": i + 1, "event_id": f"{i:032x}", **row}
            for i, row in enumerate(rows)]
    return table(full, SB_EVENT_DTYPES)


def wy_frame(rows: list[dict], competition: str = "World_Cup") -> pd.DataFrame:
    """A neutral ``actions.parquet`` frame, as the adapter writes it."""
    base = {"competition": competition, "period": "1H", "seconds": 1.0, "player_id": 0,
            "subtype": "", "start_x": 0.4, "start_y": 0.3, "end_x": 0.45, "end_y": 0.35,
            "success": None, "goal": False, "assist": False, "key_pass": False,
            "counter_attack": False, "interception": False, "clearance": False,
            "dangerous_loss": False, "provider": "pappalardo"}
    full = [{**base, "event_id": 100 + i, **row} for i, row in enumerate(rows)]
    return table(full, WY_ACTION_DTYPES)


def sb_row(match: Match, side: Side, kind: str, **fields: object) -> dict:
    return {"sb_game_id": match.sb_game, "sb_team_id": side.sb_team, "kind": kind, **fields}


def wy_row(match: Match, side: Side, kind: str, **fields: object) -> dict:
    return {"game_id": match.wy_game, "team_id": side.wy_team, "type": kind, **fields}


def at(x: float, y: float) -> dict:
    return {"start_x": x, "start_y": y}


def to(x: float, y: float) -> dict:
    return {"end_x": x, "end_y": y}


def sb_harmonised(matches: list[Match], rows: list[dict], variant: str = "open_play",
                  config: dict = CONFIG) -> pd.DataFrame:
    return harmonise_statsbomb(sb_frame(rows), links_of(*matches), pairs_of(*matches), config,
                               variant=variant)


def wy_harmonised(matches: list[Match], rows: list[dict], config: dict = CONFIG) -> pd.DataFrame:
    return harmonise_wyscout(wy_frame(rows), links_of(*matches), pairs_of(*matches), config)


def minutes_of(entries: list[tuple[Match, Side, int, int]]) -> pd.DataFrame:
    """``sheet_minutes`` rows by hand: (match, side, Wyscout player, minutes)."""
    return table([{"match_key": m.key, "subset": m.subset, "player_key": player,
                   "team_key": side.wy_team, "minutes_regulation": minutes}
                  for m, side, player, minutes in entries],
                 {"match_key": "int32", "subset": object, "player_key": "int64",
                  "team_key": "int64", "minutes_regulation": "int64"})


def flags_of(frame: pd.DataFrame, row: int) -> set[str]:
    return {flag for flag in FLAG_TABLE if bool(frame.loc[row, flag])}


def numbered_surface(grid: PitchGrid | None = None) -> ExpectedThreat:
    """A hand surface whose value of a cell is its flat index: cell(x, y) =
    min(11, int(12 y)) * 16 + min(15, int(16 x))."""
    grid = grid or PitchGrid(16, 12)
    return ExpectedThreat(grid=grid, values=np.arange(grid.n_cells, dtype=np.float64),
                          iterations=1, converged=True, n_actions=0)


def cell(x: float, y: float) -> int:
    return min(11, int(y * 12)) * 16 + min(15, int(x * 16))


def angle_by_hand(x: float, y: float) -> float:
    along, across = (1 - x) * LENGTH, (y - 0.5) * WIDTH
    value = math.atan2(GOAL * along, along**2 + across**2 - (GOAL / 2) ** 2)
    return value + math.pi if value < 0 else value


def with_keys(**overrides: object) -> dict:
    """The frozen config with the named keys changed, and nothing else."""
    config = copy.deepcopy(CONFIG)
    assert set(overrides) <= set(config)
    config.update(overrides)
    return config


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Module surface ---------------------------------------------------------------------


PUBLIC = [harmonise_statsbomb, harmonise_wyscout, wyscout_reference_surface,
          statsbomb_reference_surface, xt_delta, goal_angle, in_penalty_area, sheet_minutes,
          player_match_inputs, team_match_inputs, clock_offsets, pair_events,
          divergence_tables, read_wyscout_actions]


def test_the_module_names_the_functions_of_section_4_and_the_flags_in_table_order() -> None:
    assert INPUTS_VERSION == "provider-inputs-v2"
    assert FLAGS == FLAG_TABLE
    keys = ("match_key", "subset", "provider", "period", "seconds", "event_order", "team_key",
            "attributed", "player_key", "start_x", "start_y", "end_x", "end_y")
    columns = (*keys, *FLAG_TABLE)
    assert columns == HARMONISED_COLUMNS
    assert {f.__name__ for f in PUBLIC} <= set(provider_inputs.__all__)
    assert tuple(e["key"] for e in CONFIG["player_match_inputs"]) == PLAYER_INPUTS
    # The one exception the runner reads as the XT_SURFACE gate.
    assert "SurfaceUnfit" in provider_inputs.__all__ and issubclass(SurfaceUnfit, ValueError)


@pytest.mark.parametrize("function", PUBLIC, ids=lambda f: f.__name__)
def test_no_argument_has_a_default(function) -> None:
    parameters = inspect.signature(function).parameters.values()
    assert all(p.default is inspect.Parameter.empty for p in parameters)


def test_the_variant_and_the_provider_are_keyword_only() -> None:
    for function, name in ((harmonise_statsbomb, "variant"),
                           (statsbomb_reference_surface, "variant"),
                           (sheet_minutes, "provider")):
        parameter = inspect.signature(function).parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_the_module_and_this_test_pass_the_licence_guard() -> None:
    guard = load_script("check_licensing", ROOT / "scripts" / "check_licensing.py")
    files = [ROOT / "galactico" / "validation" / "provider_inputs.py", Path(__file__).resolve()]
    assert guard.check(files) == []


# Every flag row ---------------------------------------------------------------------

PASS_ASSIST = {"open_play_pass", "completed", "key_pass", "key_pass_assist_inclusive"}
DEFENDING = {"duel_or_interception", "defensive_action"}

# (fields of one StatsBomb event, flags under open_play, flags under as_shipped). Every
# event has a location and a player unless it says otherwise.
SB_CASES = [
    ({"kind": "Pass", "shot_assist": True}, PASS_ASSIST, PASS_ASSIST),
    ({"kind": "Pass", "goal_assist": True}, PASS_ASSIST, PASS_ASSIST),
    ({"kind": "Pass"}, {"open_play_pass", "completed"}, {"open_play_pass", "completed"}),
    ({"kind": "Pass", "has_outcome": True, "outcome": "Incomplete"},
     {"open_play_pass", "turnover"}, {"open_play_pass", "turnover"}),
    # A failed pass is no key pass, whatever it assisted.
    ({"kind": "Pass", "has_outcome": True, "outcome": "Incomplete", "shot_assist": True},
     {"open_play_pass", "turnover"}, {"open_play_pass", "turnover"}),
    ({"kind": "Pass", "has_outcome": True, "outcome": "Incomplete", "goal_assist": True},
     {"open_play_pass", "turnover"}, {"open_play_pass", "turnover"}),
    ({"kind": "Pass", "pass_type": "Kick Off"}, {"open_play_pass", "completed"},
     {"open_play_pass", "completed"}),
    ({"kind": "Pass", "pass_type": "Recovery"}, {"open_play_pass", "completed"},
     {"open_play_pass", "completed"}),
    ({"kind": "Pass", "pass_type": "Interception"},
     {"open_play_pass", "completed", "interception", *DEFENDING},
     {"open_play_pass", "completed", "interception", *DEFENDING}),
    ({"kind": "Pass", "pass_type": "Corner"}, {"corner"},
     {"open_play_pass", "completed", "corner"}),
    ({"kind": "Pass", "pass_type": "Free Kick", "shot_assist": True}, {"free_kick_pass"},
     PASS_ASSIST | {"free_kick_pass"}),
    ({"kind": "Pass", "pass_type": "Throw-in", "has_outcome": True, "outcome": "Out"},
     {"throw_in"}, {"open_play_pass", "throw_in", "turnover"}),
    ({"kind": "Pass", "pass_type": "Goal Kick"}, {"goal_kick"},
     {"open_play_pass", "completed", "goal_kick"}),
    ({"kind": "Pass", "sb_player_id": None}, {"open_play_pass", "completed"}, set()),
    ({"kind": "Pass", "start_x": np.nan, "start_y": np.nan},
     {"open_play_pass", "completed"}, set()),
    ({"kind": "Shot", "shot_type": "Open Play", "outcome": "Goal", "has_outcome": True},
     {"open_play_shot", "non_penalty_shot", "goal"},
     {"open_play_shot", "non_penalty_shot", "goal"}),
    ({"kind": "Shot", "shot_type": "Open Play", "outcome": "Saved", "has_outcome": True},
     {"open_play_shot", "non_penalty_shot"}, {"open_play_shot", "non_penalty_shot"}),
    ({"kind": "Shot", "shot_type": "Free Kick", "outcome": "Goal", "has_outcome": True},
     {"free_kick_shot", "non_penalty_shot", "goal"},
     {"open_play_shot", "free_kick_shot", "non_penalty_shot", "goal"}),
    ({"kind": "Shot", "shot_type": "Penalty", "outcome": "Goal", "has_outcome": True},
     {"penalty", "goal"}, {"open_play_shot", "penalty", "non_penalty_shot", "goal"}),
    ({"kind": "Shot", "shot_type": "Corner", "outcome": "Saved", "has_outcome": True},
     set(), {"open_play_shot", "non_penalty_shot"}),
    ({"kind": "Shot", "shot_type": "Kick Off", "outcome": "Off T", "has_outcome": True},
     set(), {"open_play_shot", "non_penalty_shot"}),
    ({"kind": "Shot", "shot_type": "Open Play", "outcome": "Saved", "has_outcome": True,
      "start_x": np.nan, "start_y": np.nan},
     {"open_play_shot", "non_penalty_shot"}, set()),
    ({"kind": "Duel", "duel_type": "Tackle"}, {"ground_duel", *DEFENDING},
     {"ground_duel", *DEFENDING}),
    ({"kind": "Duel", "duel_type": "Aerial Lost"}, set(), set()),
    ({"kind": "Dribbled Past"}, {"ground_duel", *DEFENDING}, {"ground_duel", *DEFENDING}),
    ({"kind": "Interception"}, {"interception", *DEFENDING}, {"interception", *DEFENDING}),
    ({"kind": "Foul Committed"}, {"foul", "defensive_action"}, {"foul", "defensive_action"}),
    ({"kind": "Clearance"}, {"clearance"}, {"clearance"}),
    ({"kind": "Miscontrol"}, {"turnover", "sb_one_sided"}, {"turnover", "sb_one_sided"}),
    ({"kind": "Dispossessed"}, {"turnover", "sb_one_sided"}, {"turnover", "sb_one_sided"}),
    *[({"kind": kind}, {"sb_one_sided"}, {"sb_one_sided"})
      for kind in ("Carry", "Pressure", "Ball Receipt*", "Ball Recovery", "Block", "Shield",
                   "Error", "50/50", "Dribble", "Foul Won", "Goal Keeper")],
    *[({"kind": kind}, set(), set())
      for kind in ("Offside", "Half Start", "Substitution", "Starting XI", "Own Goal For")],
]

# (fields of one Wyscout action, flags). Every action is attributed.
WY_CASES = [
    ({"type": "pass", "subtype": "Simple pass", "success": True, "key_pass": True},
     PASS_ASSIST),
    ({"type": "pass", "subtype": "Cross", "success": True, "assist": True},
     {"open_play_pass", "completed", "key_pass_assist_inclusive"}),
    ({"type": "pass", "subtype": "Simple pass", "success": True},
     {"open_play_pass", "completed"}),
    ({"type": "pass", "subtype": "Simple pass", "success": False},
     {"open_play_pass", "turnover"}),
    # A failed pass is no key pass, whatever it is tagged with.
    ({"type": "pass", "subtype": "Simple pass", "success": False, "key_pass": True},
     {"open_play_pass", "turnover"}),
    ({"type": "pass", "subtype": "Cross", "success": False, "assist": True},
     {"open_play_pass", "turnover"}),
    ({"type": "pass", "subtype": "Simple pass", "success": None}, {"open_play_pass"}),
    ({"type": "set_piece", "subtype": "corner", "success": True}, {"corner"}),
    ({"type": "set_piece", "subtype": "free_kick", "success": True}, {"free_kick_pass"}),
    ({"type": "set_piece", "subtype": "free_kick_cross", "success": True},
     {"free_kick_pass"}),
    ({"type": "set_piece", "subtype": "throw_in", "success": False}, {"throw_in"}),
    ({"type": "set_piece", "subtype": "goal_kick", "success": True}, {"goal_kick"}),
    ({"type": "shot", "subtype": "Shot", "success": True, "goal": True},
     {"open_play_shot", "non_penalty_shot", "goal"}),
    ({"type": "shot", "subtype": "Shot", "success": False},
     {"open_play_shot", "non_penalty_shot"}),
    ({"type": "set_piece", "subtype": "free_kick_shot", "success": True, "goal": True},
     {"free_kick_shot", "non_penalty_shot", "goal"}),
    ({"type": "set_piece", "subtype": "penalty", "success": True, "goal": True},
     {"penalty", "goal"}),
    ({"type": "duel", "subtype": "Ground defending duel", "success": True},
     {"ground_duel", *DEFENDING}),
    ({"type": "duel", "subtype": "Ground attacking duel", "success": True}, set()),
    ({"type": "duel", "subtype": "Air duel", "interception": True},
     {"interception", *DEFENDING}),
    ({"type": "foul", "subtype": "Foul"}, {"foul", "defensive_action"}),
    ({"type": "foul", "subtype": "Hand foul"}, set()),
    ({"type": "touch", "subtype": "Clearance"}, {"clearance"}),
    ({"type": "touch", "subtype": "Clearance", "interception": True},
     {"clearance", "interception", *DEFENDING}),
    ({"type": "touch", "subtype": "Touch", "success": True}, set()),
    ({"type": "touch", "subtype": "Touch", "dangerous_loss": True}, {"turnover"}),
    ({"type": "interruption", "subtype": "Ball out of the field"}, {"wy_one_sided"}),
    ({"type": "offside", "subtype": ""}, {"wy_one_sided"}),
    ({"type": "keeper_action", "subtype": "Goalkeeper leaving line"}, {"wy_one_sided"}),
    ({"type": "save", "subtype": "Reflexes"}, {"wy_one_sided"}),
    # The goal tag sets the goal flag on the three shot families only.
    ({"type": "save", "subtype": "Reflexes", "goal": True}, {"wy_one_sided"}),
    ({"type": "touch", "subtype": "Acceleration", "success": True}, set()),
]


@pytest.mark.parametrize("variant", ["open_play", "as_shipped"])
def test_every_statsbomb_flag_row_on_a_hand_built_match(variant) -> None:
    match = make_match(random.Random(11), 0)
    player = match.home.paired[0][0]
    rows = [sb_row(match, match.home, **{"sb_player_id": player, **at(0.5, 0.5), **fields})
            for fields, _, _ in SB_CASES]
    frame = sb_harmonised([match], rows, variant)
    column = 1 if variant == "open_play" else 2
    assert len(frame) == len(SB_CASES)
    for row, case in enumerate(SB_CASES):
        assert flags_of(frame, row) == case[column], case[0]


def test_every_wyscout_flag_row_on_a_hand_built_match() -> None:
    match = make_match(random.Random(12), 0)
    player = match.home.paired[0][1]
    frame = wy_harmonised([match], [{**wy_row(match, match.home, ""), "player_id": player, **f}
                                    for f, _ in WY_CASES])
    assert len(frame) == len(WY_CASES)
    for row, (fields, expected) in enumerate(WY_CASES):
        assert flags_of(frame, row) == expected, fields


def test_a_successful_wyscout_duel_touch_or_set_piece_is_not_completed() -> None:
    match = make_match(random.Random(13), 0)
    player = match.home.paired[0][1]
    actions = [wy_row(match, match.home, "duel", subtype="Ground defending duel", success=True),
               wy_row(match, match.home, "touch", subtype="Touch", success=True),
               wy_row(match, match.home, "set_piece", subtype="free_kick", success=True),
               wy_row(match, match.home, "pass", subtype="Simple pass", success=True)]
    frame = wy_harmonised([match], [{**row, "player_id": player} for row in actions])
    assert frame["completed"].tolist() == [False, False, False, True]
    inputs = player_match_inputs(frame, minutes_of([(match, match.home, player, 90)]), None,
                                 CONFIG)
    assert inputs.loc[0, "open_play_passes_completed"] == 1.0


def test_every_wyscout_set_piece_subtype_of_the_adapter_falls_in_exactly_one_list() -> None:
    lists = ("wy_corner_subtypes", "wy_free_kick_pass_subtypes", "wy_throw_in_subtypes",
             "wy_goal_kick_subtypes", "wy_free_kick_shot_subtypes", "wy_penalty_subtypes")
    flags = ("corner", "free_kick_pass", "throw_in", "goal_kick", "free_kick_shot", "penalty")
    subtypes = sorted(set(_SET_PIECE_SUBTYPE.values()))
    for subtype in subtypes:
        assert sum(subtype in CONFIG[key] for key in lists) == 1, subtype
    assert sorted(s for key in lists for s in CONFIG[key]) == subtypes
    match = make_match(random.Random(14), 0)
    frame = wy_harmonised([match], [wy_row(match, match.home, "set_piece", subtype=s)
                                    for s in subtypes])
    for row, subtype in enumerate(subtypes):
        set_by = [flag for flag in flags if frame.loc[row, flag]]
        assert set_by == [flags[next(i for i, key in enumerate(lists)
                                     if subtype in CONFIG[key])]]


@pytest.mark.parametrize("fields", [
    {"kind": "Invented Kind"},
    {"kind": "Pass", "pass_type": "Invented Type"},
    {"kind": "Shot", "shot_type": "Invented Type"},
    {"kind": "Shot", "shot_type": None},
    {"kind": "Duel", "duel_type": "Invented Type"},
    {"kind": "Duel", "duel_type": None},
])
def test_the_closed_vocabulary_stops_on_an_unknown_name(fields) -> None:
    match = make_match(random.Random(15), 0)
    with pytest.raises(ValueError, match="closed vocabulary"):
        sb_harmonised([match], [sb_row(match, match.home, **fields)])


def test_a_type_is_read_among_the_events_of_its_own_kind_only() -> None:
    """The opposite: a known name, and a type field on another kind, stop nothing."""
    match = make_match(random.Random(16), 0)
    rows = [sb_row(match, match.home, "Carry", pass_type="Invented Type"),
            sb_row(match, match.home, "Pass", shot_type="Invented Type",
                   duel_type="Invented Type"),
            sb_row(match, match.home, "Shot", shot_type="Kick Off"),
            sb_row(match, match.home, "Duel", duel_type="Aerial Lost")]
    assert len(sb_harmonised([match], rows)) == 4


# Unions, readers and the kick-off ----------------------------------------------------


def test_a_clearance_without_the_interception_flag_is_in_no_union() -> None:
    match = make_match(random.Random(17), 0)
    sb = sb_harmonised([match], [sb_row(match, match.home, "Clearance")])
    wy = wy_harmonised([match], [
        wy_row(match, match.home, "touch", subtype="Clearance"),
        wy_row(match, match.home, "touch", subtype="Clearance", interception=True)])
    unions = ("duel_or_interception", "defensive_action")
    for frame, row in ((sb, 0), (wy, 0)):
        assert frame.loc[row, "clearance"] and not any(frame.loc[row, u] for u in unions)
    # The flagged one: in each union once, and still a clearance.
    assert wy.loc[1, "clearance"] and wy.loc[1, "interception"]
    assert all(wy.loc[1, u] for u in unions)
    minutes = minutes_of([])
    teams = team_match_inputs(wy, None, CONFIG)
    assert teams["defensive_actions"].tolist() == [1.0]
    assert player_match_inputs(wy, minutes, None, CONFIG).empty


def test_open_play_and_as_shipped_differ_by_exactly_the_injected_restarts() -> None:
    """Each paired player makes open-play passes and a few restarts; the Wyscout view
    types the restarts as set pieces. As shipped over-counts StatsBomb passes by the
    restarts of each player-match and team-match, and open play does not."""
    rng = random.Random(18)
    match = make_match(rng, 0)
    restarts = {"Corner": "corner", "Free Kick": "free_kick", "Throw-in": "throw_in",
                "Goal Kick": "goal_kick"}
    sb_rows, wy_rows, injected = [], [], {}
    for side in (match.home, match.away):
        for sb_player, wy_player in side.paired:
            injected[wy_player] = rng.randint(1, 4)
            for _ in range(rng.randint(5, 9)):
                point = (rng.uniform(0.05, 0.95), rng.uniform(0.05, 0.95))
                sb_rows.append(sb_row(match, side, "Pass", sb_player_id=sb_player, **at(*point)))
                wy_rows.append(wy_row(match, side, "pass", subtype="Simple pass", success=True,
                                      player_id=wy_player, **at(*point)))
            for _ in range(injected[wy_player]):
                kind = rng.choice(sorted(restarts))
                sb_rows.append(sb_row(match, side, "Pass", pass_type=kind,
                                      sb_player_id=sb_player, **at(0.5, 0.5)))
                wy_rows.append(wy_row(match, side, "set_piece", subtype=restarts[kind],
                                      success=True, player_id=wy_player, **at(0.5, 0.5)))
    minutes = minutes_of([(match, side, wy, 90) for side in (match.home, match.away)
                          for _, wy in side.paired])
    wy = player_match_inputs(wy_harmonised([match], wy_rows), minutes, None, CONFIG)
    shipped = player_match_inputs(sb_harmonised([match], sb_rows, "as_shipped"), minutes, None,
                                  CONFIG)
    open_play = player_match_inputs(sb_harmonised([match], sb_rows, "open_play"), minutes, None,
                                    CONFIG)
    expected = minutes["player_key"].map(injected).to_numpy(dtype=float)
    for column in ("open_play_passes_attempted", "open_play_passes_completed"):
        assert (open_play[column] == wy[column]).all()
        assert ((shipped[column] - open_play[column]).to_numpy() == expected).all()
    sb_teams = team_match_inputs(sb_harmonised([match], sb_rows, "as_shipped"), None, CONFIG)
    wy_teams = team_match_inputs(wy_harmonised([match], wy_rows), None, CONFIG)
    per_team = [sum(injected[wy] for _, wy in side.paired) for side in (match.home, match.away)]
    order = [match.home.wy_team, match.away.wy_team]
    difference = (sb_teams.set_index("team_key")["open_play_passes_completed"]
                  - wy_teams.set_index("team_key")["open_play_passes_completed"])
    assert difference.loc[order].tolist() == per_team


def test_a_kick_off_is_an_open_play_pass_on_both_sides() -> None:
    match = make_match(random.Random(19), 0)
    sb = sb_harmonised([match], [sb_row(match, match.home, "Pass", pass_type="Kick Off",
                                        **at(0.5, 0.5))])
    # The neutral Parquet types a kick-off as an ordinary pass.
    wy = wy_harmonised([match], [wy_row(match, match.home, "pass", subtype="Simple pass",
                                        success=True, **at(0.5, 0.5))])
    assert sb.loc[0, "open_play_pass"] and wy.loc[0, "open_play_pass"]
    assert team_match_inputs(sb, None, CONFIG)["open_play_passes_completed"].tolist() == [1.0]


def test_unpaired_and_unattributed_rows_are_absent_at_player_level_present_at_team_level() -> None:
    match = make_match(random.Random(20), 0)
    (sb_player, wy_player), _ = match.home.paired
    keeper_sb, keeper_wy = match.home.keeper
    actors_sb = [sb_player, match.home.sb_unpaired, None, keeper_sb]
    actors_wy = [wy_player, match.home.wy_unpaired, 0, keeper_wy]
    sb = sb_harmonised([match], [sb_row(match, match.home, "Pass", sb_player_id=p,
                                        **at(0.5, 0.5)) for p in actors_sb])
    wy = wy_harmonised([match], [wy_row(match, match.home, "pass", success=True, player_id=p,
                                        **at(0.5, 0.5)) for p in actors_wy])
    assert sb["attributed"].tolist() == [True, True, False, True]
    assert wy["attributed"].tolist() == [True, True, False, True]
    # The goalkeeper holds a paired link, so his rows carry his key.
    assert sb["player_key"].tolist() == [wy_player, pd.NA, pd.NA, keeper_wy]
    assert wy["player_key"].tolist() == [wy_player, pd.NA, pd.NA, keeper_wy]
    minutes = minutes_of([(match, match.home, wy_player, 90)])
    for frame in (sb, wy):
        inputs = player_match_inputs(frame, minutes, None, CONFIG)
        assert inputs["open_play_passes_completed"].tolist() == [1.0]
        assert team_match_inputs(frame, None, CONFIG)["open_play_passes_completed"].tolist() \
            == [4.0]


def test_the_regulation_filter_keeps_the_two_halves_on_both_sides() -> None:
    rng = random.Random(21)
    match, unlinked = make_match(rng, 0), make_match(rng, 1)
    sb = sb_harmonised([match], [sb_row(match, match.home, "Pass", period=p,
                                        period_seconds=float(p)) for p in (1, 2, 3, 4, 5)])
    # An extra-time row and a row of an unlinked match come first in the Parquet.
    wy = wy_harmonised([match], [
        wy_row(match, match.home, "pass", period="E1", seconds=7.0),
        wy_row(unlinked, unlinked.home, "pass", period="1H", seconds=8.0),
        *[wy_row(match, match.home, "pass", period=p, seconds=float(i))
          for i, p in enumerate(("1H", "2H", "E2", "P"))]])
    assert sb["period"].tolist() == [1, 2] and sb["seconds"].tolist() == [1.0, 2.0]
    assert wy["period"].tolist() == [1, 2] and wy["seconds"].tolist() == [0.0, 1.0]
    # Row positions in the Parquet, counting the two dropped rows before them.
    assert wy["event_order"].tolist() == [2, 3]


def test_unlinked_matches_are_dropped_and_teams_map_through_the_link() -> None:
    rng = random.Random(22)
    match, other = make_match(rng, 0), make_match(rng, 1)
    sb = harmonise_statsbomb(
        sb_frame([sb_row(match, match.away, "Pass"), sb_row(other, other.home, "Pass")]),
        links_of(match), pairs_of(match), CONFIG, variant="open_play")
    assert sb["team_key"].tolist() == [match.away.wy_team]
    assert sb["provider"].tolist() == ["statsbomb"] and sb["subset"].tolist() == ["world_cup"]
    with pytest.raises(ValueError, match="two teams"):
        sb_harmonised([match], [{**sb_row(match, match.home, "Pass"), "sb_team_id": 7}])
    with pytest.raises(ValueError, match="two teams"):
        wy_harmonised([match], [{**wy_row(match, match.home, "pass"), "team_id": 7}])


def test_harmonised_columns_and_dtypes_are_the_same_on_both_providers() -> None:
    match = make_match(random.Random(23), 0)
    sb = sb_harmonised([match], [sb_row(match, match.home, "Pass", **at(0.5, 0.5))])
    wy = wy_harmonised([match], [wy_row(match, match.home, "pass")])
    assert tuple(sb.columns) == tuple(wy.columns) == HARMONISED_COLUMNS
    assert sb.dtypes.equals(wy.dtypes)
    assert str(sb["player_key"].dtype) == "Int64"
    assert all(sb[flag].dtype == bool for flag in FLAG_TABLE)


def test_another_provider_in_a_wyscout_frame_is_refused(tmp_path) -> None:
    match = make_match(random.Random(24), 0)
    frame = wy_frame([wy_row(match, match.home, "pass")])
    frame.loc[0, "provider"] = "invented"
    with pytest.raises(ValueError, match="another provider"):
        harmonise_wyscout(frame, links_of(match), pairs_of(match), CONFIG)


def test_the_parquet_reader_takes_a_column_list_from_one_file(tmp_path) -> None:
    match = make_match(random.Random(25), 0)
    directory = tmp_path / "competition=Invented"
    directory.mkdir()
    wy_frame([wy_row(match, match.home, "pass")] * 3).to_parquet(
        directory / "actions.parquet", index=False)
    actions = read_wyscout_actions(tmp_path, "Invented")
    assert tuple(actions.columns) == WY_ACTION_COLUMNS and len(actions) == 3
    frame = wy_frame([wy_row(match, match.home, "pass")])
    frame["provider"] = "invented"
    frame.to_parquet(directory / "actions.parquet", index=False)
    with pytest.raises(ValueError, match="another provider"):
        read_wyscout_actions(tmp_path, "Invented")
    # A file of no rows does not hold provider == {"pappalardo"} either.
    wy_frame([]).to_parquet(directory / "actions.parquet", index=False)
    with pytest.raises(ValueError, match="no rows"):
        read_wyscout_actions(tmp_path, "Invented")


# The fifteen player inputs ---------------------------------------------------------


def test_each_of_the_fifteen_player_inputs_on_a_hand_built_match() -> None:
    """One Wyscout player-match, valued on a surface whose cell value is its index."""
    match = make_match(random.Random(30), 0)
    (_, me), (_, idle) = match.home.paired
    keeper = match.home.keeper[1]
    mine = [
        # a: completed key pass in the half-space, cell 52 -> 59
        dict(type="pass", success=True, key_pass=True, **at(0.30, 0.25), **to(0.70, 0.30)),
        # b: completed assist (no key-pass tag), wide, cell 25 -> 22
        dict(type="pass", success=True, assist=True, **at(0.60, 0.10), **to(0.40, 0.12)),
        # c: failed pass
        dict(type="pass", success=False, **at(0.50, 0.50), **to(0.55, 0.50)),
        # d: completed, wide on the right, cell 163 -> 164
        dict(type="pass", success=True, **at(0.20, 0.90), **to(0.25, 0.85)),
        # e, f: open-play shots, one inside the Wyscout box
        dict(type="shot", **at(0.90, 0.50)),
        dict(type="shot", **at(0.70, 0.30)),
        # g: a penalty, h: a free-kick shot
        dict(type="set_piece", subtype="penalty", goal=True, **at(0.885, 0.50)),
        dict(type="set_piece", subtype="free_kick_shot", **at(0.75, 0.60)),
        # i, j: ground duels on and past the halfway line; k: an interception; l: a foul
        dict(type="duel", subtype="Ground defending duel", **at(0.55, 0.40)),
        dict(type="duel", subtype="Ground defending duel", **at(0.50, 0.40)),
        dict(type="duel", subtype="Air duel", interception=True, **at(0.80, 0.20)),
        dict(type="foul", subtype="Foul", **at(0.30, 0.30)),
        # m: a clearance, in no compared quantity
        dict(type="touch", subtype="Clearance", **at(0.10, 0.50)),
        # n, o: failed passes from the half-space and from wide, in no completed count
        dict(type="pass", success=False, **at(0.30, 0.25), **to(0.70, 0.30)),
        dict(type="pass", success=False, **at(0.60, 0.10), **to(0.40, 0.12)),
        # p: a foul past the halfway line, a defensive action but no duel or interception
        dict(type="foul", subtype="Foul", **at(0.80, 0.30)),
        # q: a free-kick shot inside the Wyscout box, not an open-play shot
        dict(type="set_piece", subtype="free_kick_shot", **at(0.90, 0.50)),
    ]
    others = [  # the goalkeeper, an unpaired player and nobody: no player-level row
        dict(type="pass", success=True, player_id=keeper, **at(0.1, 0.5), **to(0.9, 0.5)),
        dict(type="pass", success=True, player_id=match.home.wy_unpaired, **at(0.3, 0.3)),
        dict(type="shot", player_id=0, **at(0.95, 0.5)),
    ]
    rows = [{**wy_row(match, match.home, ""), "player_id": me, **fields} for fields in mine]
    rows += [{**wy_row(match, match.home, ""), **fields} for fields in others]
    frame = wy_harmonised([match], rows)
    minutes = minutes_of([(match, match.home, me, 77), (match, match.home, idle, 13)])
    inputs = player_match_inputs(frame, minutes, numbered_surface(), CONFIG)

    assert (cell(0.30, 0.25), cell(0.70, 0.30)) == (52, 59)
    assert (cell(0.60, 0.10), cell(0.40, 0.12)) == (25, 22)
    assert (cell(0.20, 0.90), cell(0.25, 0.85)) == (163, 164)
    expected = {
        "minutes_regulation": 77, "open_play_passes_attempted": 6,
        "open_play_passes_completed": 3,
        "positive_xt_gain_completed_passes": max(0, 7) + max(0, -3) + max(0, 1),
        "xt_delta_key_passes": 7, "xt_delta_key_passes_assist_inclusive": 7 - 3,
        "key_passes": 1, "completed_passes_from_half_space": 1,
        "completed_passes_from_wide": 2, "non_penalty_shots": 4, "open_play_shots": 2,
        "open_play_shots_in_penalty_area": 1,
        "shot_goal_angle_sum": (angle_by_hand(0.90, 0.50) + angle_by_hand(0.70, 0.30)
                                + angle_by_hand(0.75, 0.60) + angle_by_hand(0.90, 0.50)),
        "defensive_actions": 5, "opp_half_duel_or_interception": 2,
    }
    assert list(inputs.columns) == ["match_key", "subset", "player_key", "team_key",
                                    *PLAYER_INPUTS]
    assert all(inputs[key].dtype == np.float64 for key in PLAYER_INPUTS)
    row = inputs.set_index("player_key").loc[me]
    for key, value in expected.items():
        assert row[key] == pytest.approx(value, abs=1e-12), key
    # key_passes counts the shipped flag: the assist-inclusive count would be two.
    assert row["key_passes"] == 1 and frame["key_pass_assist_inclusive"].sum() == 2
    idle_row = inputs.set_index("player_key").loc[idle]
    assert idle_row["minutes_regulation"] == 13
    assert all(idle_row[key] == 0.0 for key in PLAYER_INPUTS[1:])


def test_statsbomb_key_passes_and_its_own_penalty_area() -> None:
    match = make_match(random.Random(31), 0)
    sb_player, wy_player = match.home.paired[0]
    rows = [sb_row(match, match.home, "Pass", sb_player_id=sb_player, shot_assist=True,
                   **at(0.3, 0.3), **to(0.4, 0.3)),
            sb_row(match, match.home, "Pass", sb_player_id=sb_player, goal_assist=True,
                   **at(0.3, 0.3), **to(0.4, 0.3)),
            # x = 0.845: inside the Wyscout drawing, outside the StatsBomb one
            sb_row(match, match.home, "Shot", shot_type="Open Play", sb_player_id=sb_player,
                   **at(0.845, 0.5)),
            sb_row(match, match.home, "Shot", shot_type="Open Play", sb_player_id=sb_player,
                   **at(0.85, 0.775))]
    sb = sb_harmonised([match], rows)
    wy = wy_harmonised([match], [wy_row(match, match.home, "shot", player_id=wy_player,
                                        **at(0.845, 0.5))])
    minutes = minutes_of([(match, match.home, wy_player, 90)])
    sb_inputs = player_match_inputs(sb, minutes, None, CONFIG)
    assert sb_inputs.loc[0, "key_passes"] == 2.0
    assert sb_inputs.loc[0, "open_play_shots_in_penalty_area"] == 1.0
    wy_inputs = player_match_inputs(wy, minutes, None, CONFIG)
    assert wy_inputs.loc[0, "open_play_shots_in_penalty_area"] == 1.0


def test_box_entry_passes_enter_each_providers_own_penalty_area_from_outside_it() -> None:
    """Completed passes that end inside the provider's own drawing and do not start
    inside it. x = 0.845 is inside the Wyscout drawing and outside the StatsBomb one."""
    match = make_match(random.Random(43), 0)
    passes = [  # (start, end, completed)
        ((0.80, 0.50), (0.90, 0.50), True),   # 0: enters both drawings
        ((0.80, 0.50), (0.845, 0.50), True),  # 1, 2: end inside the Wyscout drawing only
        ((0.80, 0.45), (0.845, 0.55), True),
        ((0.845, 0.50), (0.90, 0.50), True),  # 3: starts inside the Wyscout drawing only
        ((0.90, 0.50), (0.95, 0.50), True),   # 4: inside to inside on both
        ((0.80, 0.50), (0.90, 0.50), False),  # 5: a failed entry
    ]
    sb = sb_harmonised([match], [sb_row(match, match.home, "Pass", has_outcome=not completed,
                                        outcome=None if completed else "Incomplete",
                                        **at(*start), **to(*end))
                                 for start, end, completed in passes])
    wy = wy_harmonised([match], [wy_row(match, match.home, "pass", success=completed,
                                        **at(*start), **to(*end))
                                 for start, end, completed in passes])
    # StatsBomb: rows 0 and 3. Wyscout: rows 0, 1 and 2.
    assert team_match_inputs(sb, None, CONFIG)["box_entry_passes"].tolist() == [2.0]
    assert team_match_inputs(wy, None, CONFIG)["box_entry_passes"].tolist() == [3.0]


def test_without_a_surface_no_xt_column_is_returned_and_with_one_each_is() -> None:
    match = make_match(random.Random(32), 0)
    wy_player = match.home.paired[0][1]
    frame = wy_harmonised([match], [wy_row(match, match.home, "pass", success=True,
                                           player_id=wy_player)])
    minutes = minutes_of([(match, match.home, wy_player, 90)])
    xt_keys = {e["key"] for e in CONFIG["player_match_inputs"] if e["kind"] == "xt_sum"}
    team_xt = {e["key"] for e in CONFIG["team_match_quantities"] if e["kind"] == "xt_sum"}
    assert xt_keys and team_xt
    assert not xt_keys & set(player_match_inputs(frame, minutes, None, CONFIG).columns)
    assert not team_xt & set(team_match_inputs(frame, None, CONFIG).columns)
    assert xt_keys <= set(player_match_inputs(frame, minutes, numbered_surface(), CONFIG).columns)
    assert team_xt <= set(team_match_inputs(frame, numbered_surface(), CONFIG).columns)


def test_team_inputs_hold_every_count_and_sum_and_the_three_helpers() -> None:
    match = make_match(random.Random(33), 0)
    frame = wy_harmonised([match], [wy_row(match, side, "pass", success=True)
                                    for side in (match.home, match.away)])
    teams = team_match_inputs(frame, numbered_surface(), CONFIG)
    sums = [e["key"] for e in CONFIG["team_match_quantities"] if e["kind"] != "ratio"]
    assert list(teams.columns) == ["match_key", "subset", "team_key", *sums,
                                   "final_third_entries_wide", "high_defensive_actions",
                                   "high_defensive_actions_plus_opponent_build_up_passes"]
    assert sorted(teams["team_key"]) == sorted([match.home.wy_team, match.away.wy_team])
    for ratio in (e for e in CONFIG["team_match_quantities"] if e["kind"] == "ratio"):
        assert {ratio["numerator"], ratio["denominator"]} <= set(teams.columns)


# Sentinels and NaN -------------------------------------------------------------------


def test_sentinel_starts_and_ends_leave_location_quantities_and_stay_in_counts() -> None:
    match = make_match(random.Random(34), 0)
    me = match.home.paired[0][1]
    rows = [
        # a sentinel start: y = 0 would be wide, and this would be a final-third entry
        dict(type="pass", success=True, **at(0.0, 0.0), **to(0.70, 0.50)),
        # a sentinel end: the start still counts in the half-space; x = 1 would be an entry
        dict(type="pass", success=True, **at(0.50, 0.25), **to(1.0, 1.0)),
        # a shot from a sentinel start keeps its count and has no angle
        dict(type="shot", **at(0.0, 0.0)),
        # x = 1 would be in the opponent's half and the opposition third
        dict(type="duel", subtype="Ground defending duel", **at(1.0, 1.0)),
    ]
    frame = wy_harmonised([match], [{**wy_row(match, match.home, ""), "player_id": me, **r}
                                    for r in rows])
    assert frame[["start_x", "start_y", "end_x", "end_y"]].isna().to_numpy().tolist() == [
        [True] * 4, [False, False, True, True], [True] * 4, [True] * 4]
    minutes = minutes_of([(match, match.home, me, 90)])
    inputs = player_match_inputs(frame, minutes, numbered_surface(), CONFIG).loc[0]
    assert (inputs["open_play_passes_completed"], inputs["completed_passes_from_half_space"],
            inputs["completed_passes_from_wide"]) == (2, 1, 0)
    assert inputs["positive_xt_gain_completed_passes"] == 0.0
    assert (inputs["open_play_shots"], inputs["shot_goal_angle_sum"]) == (1, 0.0)
    assert (inputs["defensive_actions"], inputs["opp_half_duel_or_interception"]) == (1, 0)
    teams = team_match_inputs(frame, None, CONFIG).loc[0]
    assert teams["final_third_entries"] == 0 and teams["defensive_actions"] == 1
    assert sum(teams[f"defensive_actions_{third}_third"]
               for third in ("own", "middle", "opposition")) == 0


def test_xt_delta_is_nan_on_nan_and_the_row_leaves_every_xt_sum() -> None:
    class Guarded(PitchGrid):
        def cells(self, xs, ys):
            assert np.isfinite(xs).all() and np.isfinite(ys).all()
            return super().cells(xs, ys)

    surface = numbered_surface(Guarded(16, 12))
    frame = pd.DataFrame({"start_x": [0.30, np.nan, 0.30, 0.30],
                          "start_y": [0.25, 0.25, 0.25, 0.25],
                          "end_x": [0.70, 0.70, np.nan, 0.70],
                          "end_y": [0.30, 0.30, 0.30, np.nan]})
    delta = xt_delta(frame, surface)
    assert delta[0] == cell(0.70, 0.30) - cell(0.30, 0.25)
    assert np.isnan(delta[1:]).all()
    match = make_match(random.Random(35), 0)
    me = match.home.paired[0][1]
    rows = [{**wy_row(match, match.home, "pass", success=True, key_pass=True,
                      player_id=me), **frame.iloc[i].to_dict()} for i in range(4)]
    sentinel_free = wy_harmonised([match], rows)
    inputs = player_match_inputs(sentinel_free, minutes_of([(match, match.home, me, 90)]),
                                 surface, CONFIG).loc[0]
    assert inputs["open_play_passes_completed"] == 4
    assert inputs["positive_xt_gain_completed_passes"] == delta[0]
    assert inputs["xt_delta_key_passes"] == delta[0]


# Geometry ---------------------------------------------------------------------------


def test_goal_angle_on_the_centre_line_on_the_goal_line_and_in_mirror() -> None:
    xs = np.array([0.0, 0.3, 0.6, 0.9, 0.99])
    expected = [2 * math.atan((GOAL / 2) / ((1 - x) * LENGTH)) for x in xs]
    assert goal_angle(xs, np.full(5, 0.5), CONFIG) == pytest.approx(expected, rel=1e-12)
    # On the goal line outside the posts the mouth subtends nothing ...
    outside = 0.5 + (GOAL / 2 + 1.0) / WIDTH
    assert goal_angle(np.array([1.0, 1.0]), np.array([outside, 1 - outside]), CONFIG).tolist() \
        == [0.0, 0.0]
    # ... and between them it subtends a straight angle.
    assert goal_angle(np.array([1.0]), np.array([0.5]), CONFIG)[0] == pytest.approx(math.pi)
    rng = np.random.default_rng(36)
    x, y = rng.uniform(0, 1, 50), rng.uniform(0, 1, 50)
    assert goal_angle(x, y, CONFIG) == pytest.approx(goal_angle(x, 1 - y, CONFIG), rel=1e-12)
    assert goal_angle(x, y, CONFIG) == pytest.approx([angle_by_hand(a, b)
                                                      for a, b in zip(x, y, strict=True)])
    assert np.isnan(goal_angle(np.array([np.nan]), np.array([0.5]), CONFIG)).all()


@pytest.mark.parametrize("box", [SB_BOX, WY_BOX], ids=["sb", "wy"])
def test_each_penalty_area_has_inclusive_edges_and_nan_is_outside(box) -> None:
    middle = (box["min_y"] + box["max_y"]) / 2
    on_edges = in_penalty_area(np.array([box["min_x"], 1.0, 1.0]),
                               np.array([middle, box["min_y"], box["max_y"]]), box)
    assert on_edges.tolist() == [True, True, True]
    off = in_penalty_area(
        np.array([np.nextafter(box["min_x"], 0), 1.0, 1.0, np.nan, 0.9]),
        np.array([middle, np.nextafter(box["min_y"], 0), np.nextafter(box["max_y"], 1),
                  middle, np.nan]), box)
    assert off.tolist() == [False] * 5


def test_the_opponent_half_is_strict_at_the_halfway_line() -> None:
    match = make_match(random.Random(37), 0)
    me = match.home.paired[0][1]
    half = CONFIG["opponent_half_x_minimum_exclusive"]
    rows = [{**wy_row(match, match.home, "duel", subtype="Ground defending duel",
                      player_id=me), **at(x, 0.5)} for x in (half, np.nextafter(half, 1))]
    inputs = player_match_inputs(wy_harmonised([match], rows),
                                 minutes_of([(match, match.home, me, 90)]), None, CONFIG)
    assert inputs.loc[0, "opp_half_duel_or_interception"] == 1.0


def test_final_third_entries_lanes_and_pitch_thirds() -> None:
    match = make_match(random.Random(38), 0)
    cut = Fraction(*CONFIG["final_third_x_fraction"])
    final = cut.numerator / cut.denominator
    lane = [a / b for a, b in CONFIG["lane_y_edge_fractions"]]
    third = [a / b for a, b in CONFIG["pitch_third_x_fractions"]]
    passes = [  # (start x, end x, end y, completed): an entry is a completed pass that
        # ends at or beyond the cut from short of it
        (0.60, final, 0.10, True), (0.60, np.nextafter(final, 0), 0.50, True),
        (final, 0.90, 0.50, True), (0.60, 0.90, np.nextafter(lane[0], 0), True),
        (0.60, 0.90, 0.20, True), (0.60, 0.90, lane[0], True), (0.60, 0.90, lane[1], True),
        (0.60, 0.90, np.nextafter(lane[1], 1), True), (0.60, 0.90, 0.95, True),
        (0.60, 0.90, 0.20, False)]
    defending = [np.nextafter(third[0], 0), third[0], np.nextafter(third[1], 0), third[1]]
    wy_rows = [wy_row(match, match.home, "pass", success=completed, **at(x0, 0.5),
                      **to(x1, y1)) for x0, x1, y1, completed in passes]
    wy_rows += [wy_row(match, match.home, "foul", subtype="Foul", **at(x, 0.5))
                for x in defending]
    sb_rows = [sb_row(match, match.home, "Pass", has_outcome=not completed,
                      outcome=None if completed else "Incomplete", **at(x0, 0.5), **to(x1, y1))
               for x0, x1, y1, completed in passes]
    sb_rows += [sb_row(match, match.home, "Foul Committed", **at(x, 0.5)) for x in defending]
    # Entries: rows 0 and 3 to 8. y = 0 is the attacker's left on both sides, and the
    # lanes are planted unequal (three left, two on the cuts, two right), so a flip of
    # y on either side moves a count.
    for frame in (wy_harmonised([match], wy_rows), sb_harmonised([match], sb_rows)):
        teams = team_match_inputs(frame, None, CONFIG).loc[0]
        assert teams["final_third_entries"] == 7
        assert (teams["final_third_entries_left"], teams["final_third_entries_centre"],
                teams["final_third_entries_right"]) == (3, 2, 2)
        assert teams["final_third_entries_wide"] == 5
        assert (teams["defensive_actions_own_third"], teams["defensive_actions_middle_third"],
                teams["defensive_actions_opposition_third"]) == (1, 2, 1)


def test_statsbomb_cuts_are_float64_quotients() -> None:
    """x = 80/120 as the reader divides it is the cut 2/3 in float64, and 40/120 is 1/3."""
    match = make_match(random.Random(39), 0)
    width, height = SCALE
    rows = [sb_row(match, match.home, "Pass", **at(70 / width, 40 / height),
                   **to(80 / width, 40 / height)),
            sb_row(match, match.home, "Foul Committed", **at(40 / width, 40 / height))]
    assert 80 / width == 2 / 3 and 40 / width == 1 / 3
    teams = team_match_inputs(sb_harmonised([match], rows), None, CONFIG).loc[0]
    assert teams["final_third_entries"] == 1
    assert (teams["defensive_actions_own_third"], teams["defensive_actions_middle_third"]) == (0, 1)


def test_channel_bands_equal_the_shipped_action_filter() -> None:
    match = make_match(random.Random(40), 0)
    rng = random.Random(40)
    ys = [k / 100 for k in range(101)]
    players = rng.sample(range(10_000_000, 99_999_999), len(ys))
    rows = [wy_row(match, match.home, "pass", success=True, player_id=p, **at(0.5, y))
            for p, y in zip(players, ys, strict=True)]
    pairs = pairs_of(match, extra=tuple((p + 1, p, PAIRED) for p in players))
    frame = harmonise_wyscout(wy_frame(rows), links_of(match), pairs, CONFIG)
    inputs = player_match_inputs(frame, minutes_of([(match, match.home, p, 90)
                                                    for p in players]), None, CONFIG)
    neutral = pd.DataFrame({"type": "pass", "success": True, "start_y": ys})
    for channel, column in (("half_space", "completed_passes_from_half_space"),
                            ("wide", "completed_passes_from_wide")):
        shipped = ActionFilter(types=frozenset({"pass"}), completed=True,
                               channel=channel).apply(neutral).index
        assert inputs[column].to_numpy().nonzero()[0].tolist() == shipped.tolist(), channel


def test_opponent_build_up_passes_are_the_other_teams_own_passes() -> None:
    match = make_match(random.Random(41), 0)
    high = CONFIG["high_defensive_action_x_minimum"]
    build_up = CONFIG["build_up_x_maximum"]
    home, away = match.home, match.away
    rows = [
        # home: three defensive actions at or beyond the high zone, one short of it
        wy_row(match, home, "foul", subtype="Foul", **at(high, 0.5)),
        wy_row(match, home, "duel", subtype="Ground defending duel", **at(0.9, 0.5)),
        wy_row(match, home, "duel", subtype="Air duel", interception=True, **at(0.5, 0.5)),
        wy_row(match, home, "foul", subtype="Foul", **at(np.nextafter(high, 0), 0.5)),
        # home's own build-up: counts for away, never for home
        wy_row(match, home, "pass", success=True, **at(0.1, 0.5)),
        # away: open-play passes at or short of the cut in its own frame, attempted
        wy_row(match, away, "pass", success=True, **at(build_up, 0.5)),
        wy_row(match, away, "pass", success=False, **at(0.2, 0.5)),
        wy_row(match, away, "pass", success=None, **at(0.0, 0.5)),
        # away: past the cut, a restart, and a sentinel start: none counts
        wy_row(match, away, "pass", success=True, **at(np.nextafter(build_up, 1), 0.5)),
        wy_row(match, away, "set_piece", subtype="goal_kick", **at(0.05, 0.5)),
        wy_row(match, away, "pass", success=True, **at(0.0, 0.0)),
    ]
    teams = team_match_inputs(wy_harmonised([match], rows), None, CONFIG).set_index("team_key")
    assert teams.loc[home.wy_team, "high_defensive_actions"] == 3
    assert teams.loc[home.wy_team, "high_defensive_actions_plus_opponent_build_up_passes"] == 3 + 3
    assert teams.loc[away.wy_team, "high_defensive_actions"] == 0
    assert teams.loc[away.wy_team, "high_defensive_actions_plus_opponent_build_up_passes"] == 1


# Sheet minutes -----------------------------------------------------------------------


def test_sheet_minutes_keeps_paired_outfield_rows_minus_the_dropped_ones() -> None:
    rng = random.Random(42)
    match, unlinked = make_match(rng, 0), make_match(rng, 1)
    (p_sb, p_wy), (d_sb, d_wy) = match.home.paired
    (q_sb, q_wy), _ = match.away.paired
    weak_sb, weak_wy = rng.sample(range(10_000_000, 99_999_999), 2)
    pairs = pairs_of(match, extra=((weak_sb, weak_wy, "NAME_WEAK"),))
    sb_sheets = pd.DataFrame({
        "sb_game_id": [match.sb_game] * 6 + [unlinked.sb_game],
        "sb_team_id": [match.home.sb_team] * 5 + [match.away.sb_team, unlinked.home.sb_team],
        "sb_player_id": [p_sb, d_sb, match.home.keeper[0], match.home.sb_unpaired, weak_sb,
                         q_sb, p_sb],
        "minutes_regulation": [90, 45, 90, 30, 60, 0, 90],
    })
    wy_sheets = pd.DataFrame({
        "wy_game_id": [match.wy_game] * 5,
        "wy_team_id": [match.home.wy_team] * 4 + [match.away.wy_team],
        "wy_player_id": [p_wy, d_wy, match.home.keeper[1], weak_wy, q_wy],
        "minutes_regulation": [88, 45, 90, 60, 2],
    })
    dropped = pd.DataFrame({"match_key": pd.Series([0], dtype="int32"), "sb_player_id": [d_sb]})
    links = links_of(match)
    sb = sheet_minutes(sb_sheets, links, pairs, dropped, provider="statsbomb")
    wy = sheet_minutes(wy_sheets, links, pairs, dropped, provider="wyscout")
    expected = sorted([(0, p_wy, match.home.wy_team), (0, q_wy, match.away.wy_team)])
    for frame in (sb, wy):
        assert list(frame.columns) == ["match_key", "subset", "player_key", "team_key",
                                       "minutes_regulation"]
        keys = zip(frame.match_key, frame.player_key, frame.team_key, strict=True)
        assert sorted(keys) == expected
    assert dict(zip(sb.player_key, sb.minutes_regulation, strict=True)) == {p_wy: 90, q_wy: 0}
    assert dict(zip(wy.player_key, wy.minutes_regulation, strict=True)) == {p_wy: 88, q_wy: 2}
    with pytest.raises(ValueError):
        sheet_minutes(sb_sheets, links, pairs, dropped, provider="sb")


# Reference surfaces --------------------------------------------------------------------


def spain_actions(seed: int, matches: int, *, sentinels: bool) -> pd.DataFrame:
    """Invented league actions; no coordinate at a sentinel unless asked."""
    rng = random.Random(seed)
    rows = []
    for game in rng.sample(range(10_000, 9_999_999), matches):
        teams = rng.sample(range(100, 9_999), 2)
        for i in range(400):
            kind = rng.choices(["pass", "shot", "duel", "touch", "set_piece"],
                               [70, 4, 15, 8, 3])[0]
            row = {"game_id": game, "team_id": rng.choice(teams), "type": kind,
                   "period": "1H" if i < 200 else "2H", "seconds": float(i * 13 % 2700),
                   "player_id": rng.randint(1, 50), "subtype": "Simple pass",
                   "start_x": rng.uniform(0.01, 0.99), "start_y": rng.uniform(0.01, 0.99),
                   "end_x": rng.uniform(0.01, 0.99), "end_y": rng.uniform(0.01, 0.99),
                   "success": rng.choice([True, False, None]),
                   "dangerous_loss": rng.random() < 0.05,
                   "goal": kind == "shot" and rng.random() < 0.3}
            if sentinels and rng.random() < 0.05:
                row.update(to(1.0, 1.0) if rng.random() < 0.5 else at(0.0, 0.0))
            rows.append(row)
    return wy_frame(rows, competition=CONFIG["xt_wy_reference_competition"])


def test_the_wyscout_surface_equals_fit_xt_on_the_same_actions() -> None:
    from experiments import run_external_replication as stage_1c

    actions = spain_actions(50, 4, sentinels=False)
    games = sorted(actions["game_id"].unique())
    config = with_keys(xt_wy_reference_expected_matches=4)  # the corpus's own count
    surface = wyscout_reference_surface(actions, [], config)
    shipped = stage_1c.fit_xt(actions)
    assert np.array_equal(surface.values, shipped.values)
    assert surface.iterations == shipped.iterations and surface.n_actions == shipped.n_actions
    # Without the linked matches, it is the shipped fit on the rest.
    surface = wyscout_reference_surface(actions, [games[0], games[2]], config)
    rest = actions[~actions["game_id"].isin([games[0], games[2]])]
    assert np.array_equal(surface.values, stage_1c.fit_xt(rest).values)
    assert surface.record()["matches"] == 2


def test_fit_xt_keeps_sentinel_rows_and_the_harmonised_fit_drops_them() -> None:
    from experiments import run_external_replication as stage_1c

    actions = spain_actions(51, 3, sentinels=True)
    config = with_keys(xt_wy_reference_expected_matches=3)
    surface = wyscout_reference_surface(actions, [], config)
    assert not np.array_equal(surface.values, stage_1c.fit_xt(actions).values)
    record = surface.record()
    sentinel = (((actions.start_x == 0.0) & (actions.start_y == 0.0))
                | ((actions.start_x == 1.0) & (actions.start_y == 1.0)))
    end_sentinel = (((actions.end_x == 0.0) & (actions.end_y == 0.0))
                    | ((actions.end_x == 1.0) & (actions.end_y == 1.0)))
    moves = (actions.type == "pass") & actions.success.eq(True)
    assert record["dropped_nan"]["moves"] == int((moves & (sentinel | end_sentinel)).sum()) > 0
    assert record["moves"] == int((moves & ~sentinel & ~end_sentinel).sum())


def test_a_failed_pass_with_a_sentinel_end_is_a_wyscout_turnover() -> None:
    game, other = 4_321_001, 4_321_002
    rows = [
        {"game_id": game, "team_id": 7, "type": "pass", "success": True,
         **at(0.30, 0.40), **to(0.60, 0.45)},
        {"game_id": game, "team_id": 7, "type": "shot", "goal": True, **at(0.90, 0.50)},
        {"game_id": game, "team_id": 7, "type": "pass", "success": False,
         **at(0.55, 0.20), **to(1.0, 1.0)},
        {"game_id": other, "team_id": 8, "type": "pass", "success": False,
         **at(0.0, 0.0), **to(0.3, 0.3)},
        {"game_id": other, "team_id": 8, "type": "touch", "dangerous_loss": True,
         **at(0.25, 0.75)},
    ]
    actions = wy_frame(rows, competition=CONFIG["xt_wy_reference_competition"])
    surface = wyscout_reference_surface(actions, [],
                                        with_keys(xt_wy_reference_expected_matches=2))
    oracle = fit_expected_threat(
        move_start=np.array([[0.30, 0.40]]), move_end=np.array([[0.60, 0.45]]),
        shot_start=np.array([[0.90, 0.50]]), shot_goal=np.array([True]),
        turnover_start=np.array([[0.55, 0.20], [0.25, 0.75]]), grid=PitchGrid(16, 12),
        max_iterations=CONFIG["xt_max_iterations"], tolerance=CONFIG["xt_tolerance"])
    assert np.array_equal(surface.values, oracle.values)
    assert surface.record() | {"hash": None} == {
        "hash": None, "matches": 2, "moves": 1, "shots": 1, "turnovers": 2,
        "dropped_nan": {"moves": 0, "shots": 0, "turnovers": 1},
        "iterations": oracle.iterations}


def refusal(function, *args: object, **kwargs: object) -> ValueError:
    """The call raises a plain ValueError, never SurfaceUnfit: the runner records it
    as a failed run, not as the XT_SURFACE gate."""
    with pytest.raises(ValueError) as raised:
        function(*args, **kwargs)
    assert type(raised.value) is ValueError, raised.value
    return raised.value


def test_a_spain_frame_without_its_expected_matches_is_unfit() -> None:
    actions = spain_actions(52, 3, sentinels=False)
    with pytest.raises(SurfaceUnfit, match="expected matches"):
        wyscout_reference_surface(actions, [], with_keys(xt_wy_reference_expected_matches=4))
    with pytest.raises(SurfaceUnfit, match="expected matches"):
        wyscout_reference_surface(actions, [], CONFIG)
    assert wyscout_reference_surface(actions, [], with_keys(xt_wy_reference_expected_matches=3))


def test_a_surface_that_does_not_converge_is_unfit() -> None:
    actions = spain_actions(53, 2, sentinels=False)
    config = with_keys(xt_wy_reference_expected_matches=2, xt_max_iterations=1)
    with pytest.raises(SurfaceUnfit, match="converge"):
        wyscout_reference_surface(actions, [], config)


def write_reference_folder(root: Path, matches: dict[int, list[dict]],
                           listed_only: tuple[int, ...] = ()) -> None:
    base = root / REFERENCE_FOLDER
    (base / "events").mkdir(parents=True)
    (base / "_lineups").mkdir()
    index = [{"match_id": game, "match_date": f"2030-03-0{1 + i % 9}",
              "home_team": {"home_team_id": 11, "home_team_name": "Invented Home"},
              "away_team": {"away_team_id": 12, "away_team_name": "Invented Away"},
              "home_score": 0, "away_score": 0}
             for i, game in enumerate([*matches, *listed_only])]
    (base / "_matches.json").write_text(json.dumps(index), encoding="utf-8")
    for game, events in matches.items():
        (base / "events" / f"{game}.json").write_text(json.dumps(events), encoding="utf-8")
        (base / "_lineups" / f"{game}.json").write_text("[]", encoding="utf-8")


def raw_event(index: int, kind: str, location: list[float] | None, period: int = 1,
              **detail: object) -> dict:
    event = {"id": f"{index:032x}", "index": index, "period": period,
             "timestamp": "00:01:00.000", "type": {"id": 1, "name": kind},
             "team": {"id": 11, "name": "Invented Home"}, "player": {"id": 900 + index}}
    if location is not None:
        event["location"] = location
    event.update(detail)
    return event


def reference_events() -> dict[int, list[dict]]:
    """Two invented matches. Locations on the provider's 120 by 80 drawing."""
    first = [
        raw_event(1, "Pass", [36.0, 32.0], **{"pass": {"end_location": [72.0, 36.0]}}),
        raw_event(2, "Pass", [60.0, 40.0], **{"pass": {"end_location": [90.0, 20.0],
                                                       "type": {"name": "Corner"}}}),
        raw_event(3, "Miscontrol", [66.0, 16.0]),
        raw_event(4, "Shot", [108.0, 40.0], **{"shot": {"type": {"name": "Open Play"},
                                                        "outcome": {"name": "Goal"},
                                                        "end_location": [120.0, 40.0]}}),
        # extra time: in no fit input
        raw_event(5, "Pass", [12.0, 8.0], period=3, **{"pass": {"end_location": [24.0, 8.0]}}),
    ]
    second = [
        raw_event(1, "Pass", [48.0, 60.0], **{"pass": {"end_location": [54.0, 70.0],
                                                       "outcome": {"name": "Incomplete"}}}),
        raw_event(2, "Pass", None, **{"pass": {"end_location": [10.0, 10.0]}}),
        raw_event(3, "Dispossessed", [30.0, 50.0]),
        raw_event(4, "Shot", [100.0, 30.0], **{"shot": {"type": {"name": "Free Kick"},
                                                        "outcome": {"name": "Saved"}}}),
    ]
    return {50_001: first, 50_002: second}


def by_scale(*points: tuple[float, float]) -> np.ndarray:
    width, height = SCALE
    return np.array([[x / width, y / height] for x, y in points]).reshape(-1, 2)


@pytest.mark.parametrize("variant", ["open_play", "as_shipped"])
def test_the_statsbomb_surface_streams_the_reference_folder(tmp_path, variant) -> None:
    write_reference_folder(tmp_path, reference_events())
    config = with_keys(xt_sb_reference_folder=REFERENCE_FOLDER,
                       xt_sb_reference_expected_matches=2)  # the corpus's own count
    surface = statsbomb_reference_surface(tmp_path, config, variant=variant)
    # A Miscontrol has no end and stays a turnover; the pass without a location is
    # dropped from the moves and counted; the extra-time pass is in nothing.
    moves = [((36.0, 32.0), (72.0, 36.0))]
    shots = [((108.0, 40.0), True)]
    turnovers = [(66.0, 16.0), (48.0, 60.0), (30.0, 50.0)]
    if variant == "as_shipped":  # the corner is a move and the free kick an open-play shot
        moves.append(((60.0, 40.0), (90.0, 20.0)))
        shots.append(((100.0, 30.0), False))
    oracle = fit_expected_threat(
        move_start=by_scale(*(m[0] for m in moves)), move_end=by_scale(*(m[1] for m in moves)),
        shot_start=by_scale(*(s[0] for s in shots)), shot_goal=np.array([s[1] for s in shots]),
        turnover_start=by_scale(*turnovers), grid=PitchGrid(16, 12),
        max_iterations=CONFIG["xt_max_iterations"], tolerance=CONFIG["xt_tolerance"])
    assert np.array_equal(surface.values, oracle.values)
    record = surface.record()
    assert (record["matches"], record["moves"], record["shots"], record["turnovers"]) == (
        2, len(moves), len(shots), len(turnovers))
    # As shipped, a pass needs a location, so the one without is in no input at all.
    assert record["dropped_nan"] == {"moves": 1 if variant == "open_play" else 0,
                                     "shots": 0, "turnovers": 0}


def test_the_statsbomb_reference_needs_its_matches_and_its_vocabulary(tmp_path) -> None:
    events = reference_events()
    write_reference_folder(tmp_path / "short", events, listed_only=(50_003,))
    config = with_keys(xt_sb_reference_folder=REFERENCE_FOLDER,
                       xt_sb_reference_expected_matches=3)
    with pytest.raises(SurfaceUnfit, match="expected matches"):
        statsbomb_reference_surface(tmp_path / "short", config, variant="open_play")
    # The two matches with files are its count; one iteration does not converge.
    config = with_keys(xt_sb_reference_folder=REFERENCE_FOLDER,
                       xt_sb_reference_expected_matches=2, xt_max_iterations=1)
    with pytest.raises(SurfaceUnfit, match="converge"):
        statsbomb_reference_surface(tmp_path / "short", config, variant="open_play")
    # An unknown name is a refusal of the input, not an unfit surface.
    events[50_002].append(raw_event(9, "Invented Kind", [1.0, 1.0]))
    write_reference_folder(tmp_path / "unknown", events)
    config = with_keys(xt_sb_reference_folder=REFERENCE_FOLDER,
                       xt_sb_reference_expected_matches=2)
    error = refusal(statsbomb_reference_surface, tmp_path / "unknown", config,
                    variant="open_play")
    assert "closed vocabulary" in str(error)


@pytest.mark.parametrize("value", [np.nan, np.inf])
def test_a_surface_with_a_value_that_is_not_finite_is_unfit(tmp_path, monkeypatch,
                                                           value) -> None:
    """No finite input makes the shipped fit return such a value, so the fit is
    replaced by one that writes it into one cell and says it converged."""
    def fit(**inputs: object) -> ExpectedThreat:
        surface = fit_expected_threat(**inputs)
        values = surface.values.copy()
        values[0] = value
        return replace(surface, values=values, converged=True)

    monkeypatch.setattr(provider_inputs, "fit_expected_threat", fit)
    with pytest.raises(SurfaceUnfit, match="not finite"):
        wyscout_reference_surface(spain_actions(54, 2, sentinels=False), [],
                                  with_keys(xt_wy_reference_expected_matches=2))
    write_reference_folder(tmp_path, reference_events())
    config = with_keys(xt_sb_reference_folder=REFERENCE_FOLDER,
                       xt_sb_reference_expected_matches=2)
    with pytest.raises(SurfaceUnfit, match="not finite"):
        statsbomb_reference_surface(tmp_path, config, variant="open_play")


def test_every_other_refusal_of_a_surface_function_is_a_plain_value_error(tmp_path) -> None:
    """A changed rule restatement, a row of another provider or competition, another
    variant or a scale ``read_events`` refuses is a defect or an integrity failure."""
    actions = spain_actions(55, 2, sentinels=False)
    two = {"xt_wy_reference_expected_matches": 2}
    for frame, config, words in (
            (actions.assign(competition="Invented"), with_keys(**two), "another competition"),
            (actions.assign(provider="invented"), with_keys(**two), "another provider"),
            (actions, with_keys(**two, xt_wy_reference_excludes_double_coded_matches=False),
             "frozen rule"),
            (actions, with_keys(**two, xt_recipe="an invented recipe"), "frozen rule")):
        assert words in str(refusal(wyscout_reference_surface, frame, [], config))
    write_reference_folder(tmp_path, reference_events())
    folder = {"xt_sb_reference_folder": REFERENCE_FOLDER, "xt_sb_reference_expected_matches": 2}
    error = refusal(statsbomb_reference_surface, tmp_path, with_keys(**folder),
                    variant="invented")
    assert "frozen variants" in str(error)
    error = refusal(statsbomb_reference_surface, tmp_path,
                    with_keys(**folder, xt_recipe="an invented recipe"), variant="open_play")
    assert "frozen rule" in str(error)
    # Each scale read_events refuses; a negative one would mirror every location silently.
    for scale in ([-120, 80], [0, 80], [120, math.nan], [120]):
        error = refusal(statsbomb_reference_surface, tmp_path,
                        with_keys(**folder, sb_location_scale=scale), variant="open_play")
        assert "positive finite" in str(error), scale


# Clock offsets and pairing -----------------------------------------------------------


def harmonised_like(rows: list[dict]) -> pd.DataFrame:
    """The columns of a harmonised frame that the offsets and the pairing read."""
    frame = pd.DataFrame(rows)
    for flag in FLAG_TABLE:
        frame[flag] = frame.get(flag, False)
    frame["match_key"] = frame["match_key"].astype("int32")
    frame["period"] = frame["period"].astype("int8")
    return frame


def test_the_clock_offset_recovers_a_planted_three_and_a_half_seconds() -> None:
    sb, wy = [], []
    noise = (0.75, -0.75, 0.0)
    for match, period, planted in ((0, 1, 3.5), (0, 2, -2.0), (1, 1, 3.5)):
        for k in range(40):
            seconds = 30.0 * k + 7.25
            sb.append({"match_key": match, "period": period, "team_key": 5, "seconds": seconds,
                       "open_play_pass": True})
            wy.append({"match_key": match, "period": period, "team_key": 5,
                       "seconds": seconds + planted + noise[k % 3], "open_play_pass": True})
            # The other team's passes at the StatsBomb times would win offset 0 if the
            # team were ignored.
            wy.append({"match_key": match, "period": period, "team_key": 6, "seconds": seconds,
                       "open_play_pass": True})
    offsets = clock_offsets(harmonised_like(sb), harmonised_like(wy), CONFIG)
    assert offsets == {(0, 1): 3.5, (0, 2): -2.0, (1, 1): 3.5}


def test_clock_offset_ties_go_to_the_smallest_absolute_value_then_the_negative() -> None:
    sb = harmonised_like([
        {"match_key": 0, "period": 1, "team_key": 5, "seconds": 100.0, "open_play_pass": True},
        {"match_key": 0, "period": 2, "team_key": 5, "seconds": 10.0, "open_play_pass": False}])
    wy = harmonised_like([
        {"match_key": 0, "period": 1, "team_key": 5, "seconds": s, "open_play_pass": True}
        for s in (95.0, 105.0)])
    # Every offset within one second of -5 or +5 holds the one pass: -4 and +4 tie.
    assert clock_offsets(sb, wy, CONFIG) == {(0, 1): -4.0, (0, 2): 0.0}


def greedy_by_hand(sb: pd.DataFrame, wy: pd.DataFrame, family: dict,
                   offsets: dict) -> set[tuple[int, int]]:
    """Section 4 from the definition: every same-match, same-period, same-team pair in
    tolerance, sorted, then taken greedily."""
    key = family["key"]
    candidates = []
    for (i, a), (j, b) in itertools.product(sb[sb[key]].iterrows(), wy[wy[key]].iterrows()):
        if (a.match_key, a.period, a.team_key) != (b.match_key, b.period, b.team_key):
            continue
        gap = b.seconds - (a.seconds + offsets[(a.match_key, a.period)])
        distance = math.hypot((a.start_x - b.start_x) * LENGTH, (a.start_y - b.start_y) * WIDTH)
        if abs(gap) > family["time_tolerance_seconds"]:
            continue
        tolerance = family["distance_tolerance_m"]
        if tolerance is not None and not distance <= tolerance:
            continue
        distance = math.inf if math.isnan(distance) else distance
        candidates.append(((abs(gap), distance, a.event_order, b.event_order), i, j))
    taken_sb, taken_wy, pairs = set(), set(), set()
    for _, i, j in sorted(candidates):
        if i not in taken_sb and j not in taken_wy:
            taken_sb.add(i)
            taken_wy.add(j)
            pairs.add((i, j))
    return pairs


def pairing_corpus(seed: int) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rng = random.Random(seed)
    sb, wy = [], []
    offsets = {}
    for match, period in itertools.product(range(3), (1, 2)):
        offsets[(match, period)] = rng.choice([-3.0, -0.5, 0.0, 2.5])
        for team in (5, 6):
            for side, rows in (("sb", sb), ("wy", wy)):
                for _ in range(rng.randint(8, 14)):
                    seconds = round(rng.uniform(0, 120), 1)
                    rows.append({
                        "match_key": match, "period": period, "team_key": team,
                        "seconds": seconds + (offsets[(match, period)] if side == "wy" else 0),
                        "start_x": round(rng.uniform(0, 1), 2) if rng.random() > 0.1 else np.nan,
                        "start_y": round(rng.uniform(0, 1), 2),
                        "open_play_pass": True, "corner": rng.random() < 0.3})
    sb_frame_, wy_frame_ = harmonised_like(sb), harmonised_like(wy)
    sb_frame_["event_order"] = rng.sample(range(1, 10_000), len(sb_frame_))
    wy_frame_["event_order"] = rng.sample(range(10_000, 20_000), len(wy_frame_))
    return sb_frame_, wy_frame_, offsets


@pytest.mark.parametrize("family", [CONFIG["pair_families"][0],
                                    next(f for f in CONFIG["pair_families"]
                                         if f["key"] == "corner")], ids=lambda f: f["key"])
def test_pairing_is_one_to_one_within_tolerance_and_invariant_to_row_order(family) -> None:
    sb, wy, offsets = pairing_corpus(60)
    pairs = pair_events(sb, wy, family, offsets, CONFIG)
    assert list(pairs.columns) == ["match_key", "period", "sb_row", "wy_row", "time_gap",
                                   "start_distance_m"]
    taken = set(zip(pairs.sb_row, pairs.wy_row, strict=True))
    assert taken == greedy_by_hand(sb, wy, family, offsets)
    assert not pairs.sb_row.duplicated().any() and not pairs.wy_row.duplicated().any()
    assert (pairs.time_gap.abs() <= family["time_tolerance_seconds"]).all()
    if family["distance_tolerance_m"] is not None:
        assert (pairs.start_distance_m <= family["distance_tolerance_m"]).all()
    else:
        assert pairs.start_distance_m.isna().any()  # a NaN start still pairs here
    assert len(pairs) > 10
    shuffled = pair_events(sb.sample(frac=1, random_state=1), wy.sample(frac=1, random_state=2),
                           family, offsets, CONFIG)
    pd.testing.assert_frame_equal(shuffled, pairs)


def test_a_wider_window_cannot_take_a_row_twice() -> None:
    # Each side's event_order runs against its row order, so the tie-break is read
    # from event_order and not from the frame.
    sb = harmonised_like([{"match_key": 0, "period": 1, "team_key": 5, "seconds": s,
                           "start_x": 0.5, "start_y": 0.5, "event_order": order,
                           "open_play_pass": True} for s, order in ((10.0, 5), (11.0, 2))])
    wy = harmonised_like([{"match_key": 0, "period": 1, "team_key": 5, "seconds": 10.5,
                           "start_x": 0.5, "start_y": 0.5, "event_order": 0,
                           "open_play_pass": True}])
    pairs = pair_events(sb, wy, CONFIG["pair_families"][0], {(0, 1): 0.0}, CONFIG)
    # Both are 0.5 s away: the tie goes to the earlier StatsBomb event.
    assert pairs[["sb_row", "wy_row"]].to_numpy().tolist() == [[1, 0]]
    # The mirror: one StatsBomb row 0.5 s from two Wyscout rows; the earlier Wyscout
    # event wins.
    wy = harmonised_like([{"match_key": 0, "period": 1, "team_key": 5, "seconds": s,
                           "start_x": 0.5, "start_y": 0.5, "event_order": order,
                           "open_play_pass": True} for s, order in ((9.5, 7), (10.5, 3))])
    pairs = pair_events(sb.iloc[:1], wy, CONFIG["pair_families"][0], {(0, 1): 0.0}, CONFIG)
    assert pairs[["sb_row", "wy_row"]].to_numpy().tolist() == [[0, 1]]


def test_a_candidate_exactly_at_a_tolerance_pairs_and_one_past_it_does_not() -> None:
    family = CONFIG["pair_families"][0]
    seconds, metres = family["time_tolerance_seconds"], family["distance_tolerance_m"]
    at_metres = 0.5 - metres / LENGTH
    past_metres = np.nextafter(at_metres, 0)
    assert math.hypot((0.5 - at_metres) * LENGTH, 0.0) == metres
    assert math.hypot((0.5 - past_metres) * LENGTH, 0.0) > metres
    # (team, Wyscout seconds, Wyscout start x) against a StatsBomb pass at 10 s from
    # x = 0.5: exactly at each tolerance, then one step past it.
    cases = ((5, 10.0 + seconds, 0.5), (6, 10.0, at_metres),
             (7, np.nextafter(10.0 + seconds, math.inf), 0.5), (8, 10.0, past_metres))
    sb = harmonised_like([{"match_key": 0, "period": 1, "team_key": team, "seconds": 10.0,
                           "start_x": 0.5, "start_y": 0.5, "event_order": i,
                           "open_play_pass": True} for i, (team, _, _) in enumerate(cases)])
    wy = harmonised_like([{"match_key": 0, "period": 1, "team_key": team, "seconds": s,
                           "start_x": x, "start_y": 0.5, "event_order": i,
                           "open_play_pass": True} for i, (team, s, x) in enumerate(cases)])
    pairs = pair_events(sb, wy, family, {(0, 1): 0.0}, CONFIG)
    assert pairs[["sb_row", "wy_row"]].to_numpy().tolist() == [[0, 0], [1, 1]]
    assert pairs["time_gap"].tolist() == [seconds, 0.0]
    assert pairs["start_distance_m"].tolist() == [0.0, metres]


# Divergence tables -----------------------------------------------------------------------

# The La Liga open-play pass pairs of ``divergence_world``, each from (0.40, 0.50) on
# both sides: (period, seconds, who the two sides name, StatsBomb end x, Wyscout end x,
# Wyscout success). "same" is one paired player on both sides, "nobody" no player on
# either, "other" a paired player against his teammate's partner. The second-half pass
# fails on the Wyscout side only.
LA_LIGA_PASSES = (
    (1, 10.0, "same", 0.60, 0.55, True),
    (1, 300.0, "nobody", 0.70, 0.60, True),
    (1, 600.0, "other", 0.80, 0.55, True),
    (2, 50.0, "same", 0.60, 0.90, False),
)


def divergence_world(seed: int):
    """Three matches, two in the World Cup subset and one in La Liga. Corners per match
    and team are placed by hand; the La Liga open-play pass pairs are placed by hand;
    everything else is a few rows for the tables."""
    rng = random.Random(seed)
    matches = [make_match(rng, 0, "world_cup"), make_match(rng, 1, "world_cup"),
               make_match(rng, 2, "la_liga")]
    sb_rows, wy_rows = [], []
    # Home corners per match: StatsBomb 2, 1, 3 and Wyscout 1, 0, 2.
    for m, (sb_count, wy_count) in zip(matches, ((2, 1), (1, 0), (3, 2)), strict=True):
        sb_player, wy_player = m.home.paired[0]
        for k in range(sb_count):
            sb_rows.append(sb_row(m, m.home, "Pass", pass_type="Corner", sb_player_id=sb_player,
                                  period_seconds=100.0 * (k + 1), **at(0.99, 0.01)))
        for k in range(wy_count):
            wy_rows.append(wy_row(m, m.home, "set_piece", subtype="corner", player_id=wy_player,
                                  seconds=100.0 * (k + 1) + 2.0, **at(0.99, 0.01)))
    m = matches[0]
    sb_player, wy_player = m.home.paired[0]
    sb_rows += [
        sb_row(m, m.home, "Pass", sb_player_id=sb_player, period_seconds=10.0,
               **at(0.40, 0.50), **to(0.60, 0.50)),
        sb_row(m, m.home, "Shot", shot_type="Corner", sb_player_id=sb_player,
               period_seconds=20.0, **at(0.90, 0.50)),
        sb_row(m, m.home, "Shot", shot_type="Kick Off", sb_player_id=sb_player,
               period_seconds=21.0, **at(0.50, 0.50)),
        sb_row(m, m.home, "Carry", sb_player_id=sb_player, period_seconds=22.0),
        sb_row(m, m.home, "Shot", shot_type="Corner", period=3, period_seconds=5.0),
        # in no family, so not a row without location
        sb_row(m, m.home, "Half Start", period_seconds=0.0),
    ]
    wy_rows += [
        wy_row(m, m.home, "pass", subtype="Simple pass", success=True, player_id=wy_player,
               seconds=12.0, **at(0.41, 0.50), **to(0.62, 0.50)),
        wy_row(m, m.home, "offside", seconds=30.0),
        wy_row(m, m.home, "pass", success=True, seconds=40.0, **at(0.0, 0.0)),
        wy_row(m, m.home, "pass", success=True, seconds=41.0, **to(1.0, 1.0)),
    ]
    m = matches[2]
    (sb_player, wy_player), (_, wy_teammate) = m.home.paired
    actors = {"same": (sb_player, wy_player), "nobody": (None, 0),
              "other": (sb_player, wy_teammate)}
    # The second-half pair is this late on the Wyscout clock: only the top offset of
    # the grid holds it within the window.
    late = CONFIG["pair_offset_grid_seconds"][1] + CONFIG["pair_offset_match_window_seconds"]
    for period, seconds, who, sb_end, wy_end, wy_success in LA_LIGA_PASSES:
        sb_actor, wy_actor = actors[who]
        sb_rows.append(sb_row(m, m.home, "Pass", sb_player_id=sb_actor, period=period,
                              period_seconds=seconds, **at(0.40, 0.50), **to(sb_end, 0.50)))
        wy_rows.append(wy_row(m, m.home, "pass", subtype="Simple pass", success=wy_success,
                              player_id=wy_actor, period=f"{period}H",
                              seconds=seconds + (late if period == 2 else 0.0),
                              **at(0.40, 0.50), **to(wy_end, 0.50)))
    sb_events = sb_frame(sb_rows)
    links, pairs = links_of(*matches), pairs_of(*matches)
    sb = harmonise_statsbomb(sb_events, links, pairs, CONFIG, variant="open_play")
    wy = harmonise_wyscout(wy_frame(wy_rows), links, pairs, CONFIG)
    weights = np.array([[1, 1, 1], [2, 0, 1], [0, 2, 1], [1, 1, 1]], dtype=np.int16)
    return matches, sb_events, sb, wy, links, weights


def linear_quantile(values: list[Fraction], q: float) -> Fraction:
    """numpy's linear method from its definition: position q (n - 1), interpolated."""
    ordered = sorted(values)
    position = Fraction(q) * (len(ordered) - 1)
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (position - low) * (ordered[high] - ordered[low])


def test_divergence_count_ratios_and_their_match_cluster_intervals() -> None:
    _, sb_events, sb, wy, links, weights = divergence_world(70)
    offsets = clock_offsets(sb, wy, CONFIG)
    tables = divergence_tables(sb_events, sb, wy, offsets, numbered_surface(), links, weights,
                               CONFIG)
    sb_counts, wy_counts = [2, 1, 3], [1, 0, 2]
    for pool, columns in (("pooled", [0, 1, 2]), ("world_cup", [0, 1]), ("la_liga", [2])):
        row = tables["families"]["corner"][pool]
        assert row["events"] == {"sb": sum(sb_counts[c] for c in columns),
                                 "wy": sum(wy_counts[c] for c in columns)}
        assert row["count_ratio"] == pytest.approx(Fraction(row["events"]["sb"],
                                                            row["events"]["wy"]))
        ratios = []
        for replicate in weights.tolist():
            numerator = sum(replicate[c] * sb_counts[c] for c in columns)
            denominator = sum(replicate[c] * wy_counts[c] for c in columns)
            if denominator > 0:
                ratios.append(Fraction(numerator, denominator))
        assert row["replicates_without_wy_events"] == len(weights) - len(ratios)
        assert row["interval"] == pytest.approx(
            [float(linear_quantile(ratios, q)) for q in CONFIG["interval_quantiles"]])
        assert row["team_matches"] == 2 * len(columns)
    pooled = tables["families"]["corner"]["pooled"]
    home_counts = [Fraction(c) for c in (2, 0, 1, 0, 3, 0)]
    assert pooled["per_team_match"]["sb"] == pytest.approx(
        [float(linear_quantile(home_counts, q)) for q in CONFIG["descriptive_quantiles"]])
    assert tables["families"]["corner"]["world_cup"]["replicates_without_wy_events"] == 1
    penalty = tables["families"]["penalty"]["pooled"]
    assert (penalty["count_ratio"], penalty["interval"]) == (None, None)
    assert penalty["replicates_without_wy_events"] == len(weights)


def test_divergence_one_sided_counts_and_rows_without_location() -> None:
    _, sb_events, sb, wy, links, weights = divergence_world(71)
    tables = divergence_tables(sb_events, sb, wy, clock_offsets(sb, wy, CONFIG), None, links,
                               weights, CONFIG)
    # Under open play a Corner-type shot sets no shot flag and no one-sided flag ...
    corner_shot = sb[(sb.seconds == 20.0) & (sb.match_key == 0)].iloc[0]
    assert not any(corner_shot[f] for f in ("open_play_shot", "free_kick_shot", "penalty",
                                            "non_penalty_shot", "sb_one_sided"))
    # ... is counted among the one-sided shots (with the kick-off shot; the extra-time
    # one is not), and is not a non-penalty shot.
    assert tables["one_sided"]["sb_one_sided_shots"] == {"pooled": 2, "world_cup": 2,
                                                         "la_liga": 0}
    assert tables["one_sided"]["sb_one_sided"]["pooled"] == 1  # the Carry
    assert tables["one_sided"]["wy_one_sided"]["pooled"] == 1  # the offside
    assert int(sb["non_penalty_shot"].sum()) == 0
    count_only = tables["count_only"]["pooled"]
    assert count_only["wy_sentinel_rows"] == {"start": 1, "end_only": 1}
    # The offside, the two sentinel passes and the La Liga pass that names nobody.
    assert count_only["wy_unattributed_rows"] == 4
    # The Carry; the Half Start has no location either but sets no family flag.
    assert count_only["sb_rows_without_location"] == 1
    types = {(row["kind"], row["type"]): row["events"]
             for row in tables["sb_pass_and_shot_types"]["pooled"]}
    assert types[("Pass", "Corner")] == 6 and types[("Pass", None)] == 1 + len(LA_LIGA_PASSES)
    assert types[("Shot", "Corner")] == 1 and types[("Shot", "Kick Off")] == 1
    assert set(types) == ({("Pass", t) for t in CONFIG["sb_known_pass_types"]}
                          | {("Shot", t) for t in CONFIG["sb_known_shot_types"]})


def test_divergence_pairing_rows_and_a_failed_surface() -> None:
    _, sb_events, sb, wy, links, weights = divergence_world(72)
    offsets = clock_offsets(sb, wy, CONFIG)
    # The one open-play pass is planted 2 s late; every offset within the window of it
    # holds it, and the smallest wins.
    assert offsets[(0, 1)] == 2.0 - CONFIG["pair_offset_match_window_seconds"]
    valued = divergence_tables(sb_events, sb, wy, offsets, numbered_surface(), links, weights,
                               CONFIG)
    passes = valued["pairing"]["open_play_pass"]["world_cup"]
    assert (passes["pairs"], passes["events"]) == (1, {"sb": 1, "wy": 3})
    assert passes["paired_share"] == {"sb": 1.0, "wy": pytest.approx(1 / 3)}
    assert passes["player_agreement"] == {"pairs": 1, "share": 1.0}
    assert passes["completion_agreement"] == {"pairs": 1, "share": 1.0}
    assert passes["goal_agreement"] is None
    expected_start = math.hypot(0.01 * LENGTH, 0.0)
    assert passes["start_displacement_m"]["quantiles"] == pytest.approx([expected_start] * 3)
    assert passes["xt_delta_difference"] == {
        "pairs": 1, "mean": (cell(0.60, 0.50) - cell(0.40, 0.50))
        - (cell(0.62, 0.50) - cell(0.41, 0.50)), "sd": None}
    la_liga = valued["pairing"]["open_play_pass"]["la_liga"]
    assert (la_liga["pairs"], la_liga["events"]) == (4, {"sb": 4, "wy": 4})
    assert valued["pairing"]["open_play_pass"]["pooled"]["pairs"] == 5
    # Named on both sides: "same" twice and "other" once; "nobody" is no pair of names.
    assert la_liga["player_agreement"] == {"pairs": 3, "share": pytest.approx(2 / 3)}
    assert la_liga["completion_agreement"] == {"pairs": 4, "share": 3 / 4}
    # Valued: the three pairs completed on both sides, with sd at ddof 1.
    start = cell(0.40, 0.50)
    differences = [(cell(sb_end, 0.50) - start) - (cell(wy_end, 0.50) - start)
                   for _, _, _, sb_end, wy_end, completed in LA_LIGA_PASSES if completed]
    assert differences == [1, 2, 4]
    mean = Fraction(sum(differences), len(differences))
    variance = sum((d - mean) ** 2 for d in differences) / (len(differences) - 1)
    assert la_liga["xt_delta_difference"] == {
        "pairs": 3, "mean": pytest.approx(float(mean)),
        "sd": pytest.approx(math.sqrt(variance))}
    corners = valued["pairing"]["corner"]["la_liga"]
    assert corners["pairs"] == 2 and corners["completion_agreement"] is None
    failed = divergence_tables(sb_events, sb, wy, offsets, None, links, weights, CONFIG)
    for family, pools in failed["pairing"].items():
        for pool, row in pools.items():
            assert row["xt_delta_difference"] is None
            assert {k: v for k, v in row.items() if k != "xt_delta_difference"} == {
                k: v for k, v in valued["pairing"][family][pool].items()
                if k != "xt_delta_difference"}
    assert {k: v for k, v in failed.items() if k != "pairing"} == {
        k: v for k, v in valued.items() if k != "pairing"}
    offsets_table = valued["clock_offsets"]["pooled"]
    assert offsets_table["match_periods"] == len(offsets)
    # The La Liga second half sits on the top edge of the grid.
    assert offsets[(2, 2)] == CONFIG["pair_offset_grid_seconds"][1]
    assert {pool: row["at_grid_edge"] for pool, row in valued["clock_offsets"].items()} == {
        "pooled": 1, "world_cup": 0, "la_liga": 1}


def keys_of(payload: object) -> list[str]:
    if isinstance(payload, dict):
        return [str(k) for k in payload] + [k for v in payload.values() for k in keys_of(v)]
    if isinstance(payload, list):
        return [k for v in payload for k in keys_of(v)]
    return []


def test_divergence_tables_are_aggregate_json_with_no_provider_named_in_a_key() -> None:
    _, sb_events, sb, wy, links, weights = divergence_world(73)
    tables = divergence_tables(sb_events, sb, wy, clock_offsets(sb, wy, CONFIG),
                               numbered_surface(), links, weights, CONFIG)
    text = json.dumps(tables, allow_nan=False, sort_keys=True)
    assert json.loads(text) == tables
    names = ("statsbomb", "pappalardo", "wyscout")
    assert not [k for k in keys_of(tables) if any(n in k.lower() for n in names)
                or k.startswith("SB_")]
    assert not set(keys_of(tables)) & set(CONFIG["results_identifier_key_denylist"])
    families = [f["key"] for f in CONFIG["pair_families"]] + ["interception", "ground_duel"]
    assert list(tables["families"]) == families
    assert list(tables["pairing"]) == [f["key"] for f in CONFIG["pair_families"]]
    assert set(tables) == {"families", "sb_pass_and_shot_types", "pairing", "clock_offsets",
                           "one_sided", "count_only"}
    assert banned_key_paths(tables) == []
    record = wyscout_reference_surface(spain_actions(74, 2, sentinels=False), [],
                                       with_keys(xt_wy_reference_expected_matches=2)).record()
    assert not [k for k in keys_of(record) if any(n in k for n in names)]
    json.dumps(record, allow_nan=False)
