"""E-11 match crosswalk, team-sheet crosswalk, wide link and permuted partners.

Claim: every rule of ``galactico/validation/provider_crosswalk.py`` (PIPELINE section
3, the protocol's Identity section and purpose (b)) is exercised on invented sheets,
each rule with its interesting outcome and its opposite, and every expected value is
written from the definitions (hand numbers, ``fractions.Fraction``, a quadratic for
the Wilson bounds, an oracle that builds the permutation generator itself).

Non-claim: nothing here reads the real corpus. Every name, id, date and score is
invented; the roster of the planted-rates test is drawn from a seed. Files are written
under ``tmp_path`` only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import itertools
import json
import math
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from galactico.validation import provider_crosswalk
from galactico.validation.provider_crosswalk import (
    assign_match_keys,
    crosswalk_digest,
    crosswalk_matches,
    evaluate_wide_link,
    evaluated_players,
    link_verdict,
    name_nationality_link,
    namesake_collision,
    permuted_partners,
    read_wyscout_matches,
    read_wyscout_people,
    read_wyscout_team_sheets,
    team_sheet_crosswalk,
    wilson_interval,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "galactico" / "validation" / "provider_crosswalk.py"
CONFIG = json.loads((ROOT / "experiments" / "preregistered" / "E-11-provider-agreement"
                     / "config.json").read_text(encoding="utf-8"))
WC, LL = "world_cup", "la_liga"
HOME = "Arvenia"

SB_COLUMNS = ["sb_game_id", "sb_team_id", "sb_player_id", "player_name", "player_nickname",
              "country", "started", "minutes_regulation", "minute_on", "minute_off",
              "is_goalkeeper", "cautioned", "dismissed", "permanent_off"]
WY_COLUMNS = ["wy_game_id", "wy_team_id", "wy_player_id", "started", "minutes_regulation",
              "minute_on", "minute_off", "cautioned", "dismissed"]
PEOPLE_COLUMNS = ["wy_player_id", "full_name", "short_name", "birth_area", "passport_area",
                  "position"]
LINK_COLUMNS = ["match_key", "subset", "sb_game_id", "wy_game_id", "date", "swapped",
                "duration", "goal_check", "sb_home_team_id", "sb_away_team_id",
                "wy_team_for_sb_home", "wy_team_for_sb_away"]


def with_config(**changes: object) -> dict:
    return {**CONFIG, **changes}


# --- builders: invented sheets ----------------------------------------------------------

def sb(key: int, player: int, name: str | None, nickname: str | None = None, *,
       team: int = 1, started: bool = True, minutes: int = 90, keeper: bool = False,
       cautioned: bool = False, dismissed: bool = False, permanent_off: bool = False,
       country: str | None = HOME) -> dict:
    """A StatsBomb sheet row of the shape of section 2 in linked match ``key``."""
    return {"sb_game_id": 10 + key, "sb_team_id": team, "sb_player_id": player,
            "player_name": name, "player_nickname": nickname, "country": country,
            "started": started, "minutes_regulation": minutes,
            "minute_on": 0 if started else 90 - minutes,
            "minute_off": minutes if started else 90, "is_goalkeeper": keeper,
            "cautioned": cautioned, "dismissed": dismissed, "permanent_off": permanent_off}


def wy(key: int, player: int, *, team: int = 901, started: bool = True, minutes: int = 90,
       cautioned: bool = False, dismissed: bool = False) -> dict:
    return {"wy_game_id": 500 + key, "wy_team_id": team, "wy_player_id": player,
            "started": started, "minutes_regulation": minutes,
            "minute_on": 0 if started else 90 - minutes, "minute_off": minutes if started else 90,
            "cautioned": cautioned, "dismissed": dismissed}


def person(player: int, full: str | None, short: str | None = None, *, position: str = "DF",
           birth: str | None = HOME, passport: str | None = None) -> dict:
    return {"wy_player_id": player, "full_name": full, "short_name": short,
            "birth_area": birth, "passport_area": passport, "position": position}


def links(count: int, subsets: list[str] | None = None) -> pd.DataFrame:
    """``count`` linked matches; StatsBomb teams 1 and 2 are Wyscout teams 901 and 902."""
    rows = [{"match_key": key, "subset": (subsets or [WC] * count)[key],
             "sb_game_id": 10 + key, "wy_game_id": 500 + key, "date": f"2031-04-{key + 1:02d}",
             "swapped": False, "duration": "Regular", "goal_check": "agree",
             "sb_home_team_id": 1, "sb_away_team_id": 2, "wy_team_for_sb_home": 901,
             "wy_team_for_sb_away": 902} for key in range(count)]
    return pd.DataFrame(rows, columns=LINK_COLUMNS)


def frames(sb_rows, wy_rows, people):
    return (pd.DataFrame(sb_rows, columns=SB_COLUMNS), pd.DataFrame(wy_rows, columns=WY_COLUMNS),
            pd.DataFrame(people, columns=PEOPLE_COLUMNS))


def crosswalk(sb_rows, wy_rows, people, count, subsets=None, config=CONFIG):
    sb_frame, wy_frame, people_frame = frames(sb_rows, wy_rows, people)
    return team_sheet_crosswalk(sb_frame, wy_frame, people_frame, links(count, subsets), config)


def statuses(pairs: pd.DataFrame) -> dict[tuple[int, int], str]:
    return {(int(s), int(w)): status
            for s, w, status in zip(pairs.sb_player_id, pairs.wy_player_id, pairs.status,
                                    strict=True)}


def pair(pairs: pd.DataFrame, sb_player: int, wy_player: int) -> dict:
    rows = pairs[(pairs.sb_player_id == sb_player) & (pairs.wy_player_id == wy_player)]
    assert len(rows) == 1
    return rows.iloc[0].to_dict()


# --- the module itself -----------------------------------------------------------------

def test_no_function_parameter_is_an_event_frame() -> None:
    """Checklist item 1: no event content enters any crosswalk."""
    functions = [getattr(provider_crosswalk, name) for name in provider_crosswalk.__all__
                 if callable(getattr(provider_crosswalk, name))]
    assert len(functions) >= 13
    for function in functions:
        for parameter in inspect.signature(function).parameters:
            assert "event" not in parameter and "action" not in parameter, (function, parameter)
    source = MODULE.read_text(encoding="utf-8")
    for reader in ("read_events", "iter_events", "sb_reader", "actions.parquet", "events_"):
        assert reader not in source


def test_the_interface_is_the_specified_one() -> None:
    assert provider_crosswalk.CROSSWALK_VERSION == "team-sheet-crosswalk-v2"
    expected = {
        "read_wyscout_matches": ["raw_root", "competition"],
        "read_wyscout_team_sheets": ["raw_root", "competition", "game_ids", "cap",
                                     "red_cards_not_equal"],
        "read_wyscout_people": ["raw_root"],
        "crosswalk_matches": ["sb_matches", "wy_matches", "wy_teams", "config", "subset"],
        "team_sheet_crosswalk": ["sb_sheets", "wy_sheets", "wy_people", "match_links",
                                 "config"],
        "name_nationality_link": ["left", "right", "config", "tiers", "exclude_right",
                                  "unique_right"],
        "evaluate_wide_link": ["pairs", "sb_people", "wy_people", "sheet_ids_of_player",
                               "subset_of_player", "config"],
        "namesake_collision": ["wy_people", "config", "tiers"],
        "wilson_interval": ["successes", "trials", "z"],
        "link_verdict": ["block", "failed_gates", "config"],
        "permuted_partners": ["keys", "stratum", "config", "seed"],
        "crosswalk_digest": ["frame", "columns"],
    }
    for name, parameters in expected.items():
        signature = inspect.signature(getattr(provider_crosswalk, name))
        assert list(signature.parameters) == parameters, name
        # No function takes a default for anything, config values included.
        assert all(p.default is inspect.Parameter.empty
                   for p in signature.parameters.values()), name


def test_name_nationality_link_has_no_default_for_unique_or_exclude() -> None:
    parameters = inspect.signature(name_nationality_link).parameters
    for name in ("exclude_right", "unique_right", "tiers"):
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters[name].default is inspect.Parameter.empty
    left = pd.DataFrame([{"left_id": 1, "full_name": "Abel Corte", "known_as": None,
                          "country": HOME}])
    right = pd.DataFrame([{"right_id": 2, "full_name": "Abel Corte", "countries": (HOME,)}])
    with pytest.raises(TypeError):
        name_nationality_link(left, right, CONFIG, tiers=["A"], exclude_right=None)
    with pytest.raises(TypeError):
        name_nationality_link(left, right, CONFIG, tiers=["A"], unique_right=True)


def test_module_and_test_pass_the_licence_guard(tmp_path, monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "check_licensing", ROOT / "scripts" / "check_licensing.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    assert guard.check([MODULE, Path(__file__).resolve()]) == []
    # The check bites: a raw Wyscout event key, quoted and followed by a colon, is refused.
    key = "sub" + "EventId"
    planted = tmp_path / "planted.py"
    planted.write_text(f'row = {{"{key}": 3}}\n', encoding="utf-8")
    monkeypatch.setattr(guard, "REPO", tmp_path)
    assert any("Wyscout event data" in problem for problem in guard.check([planted]))


@pytest.mark.parametrize(("key", "value", "call"), [
    ("match_allow_swapped_orientation", False, "matches"),
    ("sheet_structure_conflict_scope", "player", "sheets"),
    ("sheet_require_distinguishing_token", False, "sheets"),
    ("link_requires_nationality_agreement", False, "link"),
    ("link_requires_unique_both_directions", False, "wide"),
    ("link_recall_denominator", "evaluated", "wide"),
])
def test_a_config_key_that_restates_a_rule_is_asserted(key, value, call) -> None:
    config = with_config(**{key: value})
    empty_sb = pd.DataFrame(columns=["sb_game_id", "folder", "date", "home_sb_team_id",
                                     "away_sb_team_id", "home_team_name", "away_team_name",
                                     "home_goals", "away_goals"])
    empty_wy = pd.DataFrame(columns=["wy_game_id", "date", "home_wy_team_id",
                                     "away_wy_team_id", "home_goals", "away_goals", "duration"])
    teams = pd.DataFrame(columns=["team_id", "team_name"])
    sb_frame, wy_frame, people_frame = frames([], [], [])
    pairs = pd.DataFrame(columns=["sb_player_id", "wy_player_id", "status"])
    sb_people = pd.DataFrame(columns=["left_id", "full_name", "known_as", "country"])
    right = pd.DataFrame(columns=["right_id", "full_name", "countries"])
    calls = {
        "matches": lambda c: crosswalk_matches(empty_sb, empty_wy, teams, c, subset=WC),
        "sheets": lambda c: team_sheet_crosswalk(sb_frame, wy_frame, people_frame, links(0), c),
        "link": lambda c: name_nationality_link(sb_people, right, c, tiers=["A"],
                                                exclude_right=None, unique_right=True),
        "wide": lambda c: evaluate_wide_link(pairs, sb_people, people_frame, {}, {}, c),
    }
    calls[call](CONFIG)  # the frozen value runs
    with pytest.raises(ValueError, match=key):
        calls[call](config)


# --- the Wyscout readers -----------------------------------------------------------------

def card(player: int, yellow: str = "0", red: str = "0") -> dict:
    return {"playerId": player, "yellowCards": yellow, "redCards": red, "goals": "0",
            "ownGoals": "0"}


def write_matches(root: Path, competition: str, matches: list[dict]) -> None:
    (root / f"matches_{competition}.json").write_text(json.dumps(matches), encoding="utf-8")


def raw_match(game: int, day: str, home: int, away: int, score: tuple[int, int], *,
              duration: str = "Regular", formations: dict[int, dict] | None = None) -> dict:
    formations = formations or {}
    return {"wyId": game, "dateutc": f"{day} 19:00:00", "duration": duration,
            "teamsData": {str(team): {"side": side, "score": goals, "teamId": team,
                                      "formation": formations.get(team, {})}
                          for team, side, goals in ((home, "home", score[0]),
                                                    (away, "away", score[1]))}}


def test_read_wyscout_matches(tmp_path) -> None:
    write_matches(tmp_path, "Elsewhere", [
        raw_match(7702, "2031-06-11", 41, 42, (1, 3), duration="Penalties"),
        raw_match(7701, "2031-06-10", 43, 44, (0, 0)),
    ])
    frame = read_wyscout_matches(tmp_path, "Elsewhere")
    assert list(frame.columns) == ["wy_game_id", "date", "home_wy_team_id", "away_wy_team_id",
                                   "home_goals", "away_goals", "duration"]
    assert frame.wy_game_id.tolist() == [7701, 7702]
    assert frame.date.tolist() == ["2031-06-10", "2031-06-11"]
    assert frame.home_wy_team_id.tolist() == [43, 41]
    assert frame.away_goals.tolist() == [0, 3]
    assert str(frame.home_goals.dtype) == "Int64" and str(frame.wy_game_id.dtype) == "int64"
    assert frame.duration.tolist() == ["Regular", "Penalties"]


def test_a_match_without_one_home_and_one_away_side_raises(tmp_path) -> None:
    match = raw_match(7701, "2031-06-10", 43, 44, (0, 0))
    match["teamsData"]["44"]["side"] = "home"
    write_matches(tmp_path, "Elsewhere", [match])
    with pytest.raises(ValueError):
        read_wyscout_matches(tmp_path, "Elsewhere")


def test_read_wyscout_team_sheets_applies_the_adapter_minutes_rule_with_the_cap(tmp_path) -> None:
    lineup = [card(1), card(2), card(3), card(4, yellow="37"), card(5, red="88")]
    bench = [card(11), card(12), card(13), card(14)]
    substitutions = [
        {"playerIn": 11, "playerOut": 2, "minute": 60},
        {"playerIn": 12, "playerOut": 3, "minute": 0},    # an off minute of 0 counts
        {"playerIn": 13, "playerOut": 11, "minute": 80},  # a used substitute replaced later
        {"playerIn": 14, "playerOut": 4, "minute": 95},   # beyond the cap on both sides
    ]
    other = {"lineup": [card(21)], "bench": [card(22)], "substitutions": "null"}
    write_matches(tmp_path, "Elsewhere", [
        raw_match(7701, "2031-06-10", 41, 42, (1, 0),
                  formations={41: {"lineup": lineup, "bench": bench,
                                   "substitutions": substitutions}, 42: other}),
        raw_match(7702, "2031-06-12", 41, 42, (1, 0),
                  formations={41: {"lineup": [card(1)], "bench": []}}),
    ])
    frame = read_wyscout_team_sheets(tmp_path, "Elsewhere", [7701], cap=90,
                                     red_cards_not_equal="0")
    assert list(frame.columns) == WY_COLUMNS
    rows = {int(r.wy_player_id): r for r in frame.itertuples(index=False)}
    assert set(rows) == {1, 2, 3, 4, 5, 11, 12, 13, 14, 21}  # 22 unused; match 7702 not asked
    minutes = {player: int(row.minutes_regulation) for player, row in rows.items()}
    assert minutes == {1: 90, 2: 60, 3: 0, 4: 90, 5: 90, 11: 30, 12: 90, 13: 10, 14: 0, 21: 90}
    assert [bool(rows[p].started) for p in (1, 11)] == [True, False]
    assert (int(rows[2].minute_on), int(rows[2].minute_off)) == (0, 60)
    assert (int(rows[13].minute_on), int(rows[13].minute_off)) == (80, 90)
    assert [bool(rows[p].cautioned) for p in (1, 4, 5)] == [False, True, True]
    assert [bool(rows[p].dismissed) for p in (1, 4, 5)] == [False, False, True]
    # A dismissed starter keeps the cap: Wyscout minutes ignore a red card.
    assert minutes[5] == 90


def test_read_wyscout_people_joins_first_and_last_and_unescapes(tmp_path) -> None:
    records = [
        {"wyId": 31, "firstName": "Ren\\u00e9", "middleName": "Olmo", "lastName": "Tasso",
         "shortName": "R. Tasso", "birthArea": {"name": "C\\u00f4te Sud"},
         "role": {"code2": "GK"}},
        {"wyId": 30, "firstName": "", "lastName": "Quimo", "shortName": "Quimo",
         "birthArea": {"name": HOME}, "passportArea": {"name": "Belloria"},
         "role": {"code2": "FW"}},
    ]
    (tmp_path / "players.json").write_text(json.dumps(records), encoding="utf-8")
    frame = read_wyscout_people(tmp_path)
    assert list(frame.columns) == PEOPLE_COLUMNS
    assert frame.wy_player_id.tolist() == [30, 31]
    assert frame.full_name.tolist() == ["Quimo", "René Tasso"]  # middle name not read
    assert frame.birth_area.tolist() == [HOME, "Côte Sud"]
    assert frame.passport_area.tolist() == ["Belloria", None]
    assert frame.position.tolist() == ["FW", "GK"]


# --- the match crosswalk -----------------------------------------------------------------

TEAMS = pd.DataFrame({"team_id": [9001, 9002, 9003, 9004, 9005, 9006, 9007, 9008],
                      "team_name": ["Norvik Athletic", "Sudmar Rovers", "Eastholm City",
                                    "Westry Town", "Norvik United", "Sudmar Rovers B",
                                    "Ostra", "Ostra"]})


def sb_match(game: int, day: str, home: str, away: str, goals=(1, 0), teams=(1, 2)) -> dict:
    return {"sb_game_id": game, "folder": "World_Cup_2018", "date": day,
            "home_sb_team_id": teams[0], "away_sb_team_id": teams[1], "home_team_name": home,
            "away_team_name": away, "home_goals": goals[0], "away_goals": goals[1],
            "stage": None, "data_version": None}


def wy_match(game: int, day: str, home: int, away: int, goals=(1, 0),
             duration: str = "Regular") -> dict:
    return {"wy_game_id": game, "date": day, "home_wy_team_id": home, "away_wy_team_id": away,
            "home_goals": goals[0], "away_goals": goals[1], "duration": duration}


def match_crosswalk(sb_rows, wy_rows, config=CONFIG):
    return crosswalk_matches(pd.DataFrame(sb_rows), pd.DataFrame(wy_rows), TEAMS, config,
                             subset=WC)


def test_straight_and_swapped_orientation() -> None:
    linked, rejected = match_crosswalk(
        [sb_match(1, "2031-06-10", "Norvik Athletic", "Sudmar Rovers", (2, 1)),
         sb_match(2, "2031-06-12", "Eastholm City", "Westry Town", (0, 3), teams=(3, 4))],
        [wy_match(501, "2031-06-10", 9001, 9002, (2, 1)),
         wy_match(502, "2031-06-12", 9004, 9003, (3, 0))])
    assert list(linked.columns) == LINK_COLUMNS
    assert str(linked.match_key.dtype) == "int32" and linked.match_key.tolist() == [0, 1]
    assert rejected == {"NO_CANDIDATE": 0, "AMBIGUOUS": 0, "CLAIMED_TWICE": 0,
                        "GOALS_DISAGREE": 0}
    straight, swapped = (linked.iloc[0].to_dict(), linked.iloc[1].to_dict())
    assert (straight["sb_game_id"], straight["wy_game_id"], straight["swapped"]) == (1, 501, False)
    assert (straight["wy_team_for_sb_home"], straight["wy_team_for_sb_away"]) == (9001, 9002)
    assert (swapped["sb_game_id"], swapped["wy_game_id"], swapped["swapped"]) == (2, 502, True)
    assert (swapped["wy_team_for_sb_home"], swapped["wy_team_for_sb_away"]) == (9003, 9004)
    # Goals agree after orientation: 0-3 at home is 3-0 for the Wyscout home side.
    assert straight["goal_check"] == swapped["goal_check"] == "agree"
    assert linked.subset.tolist() == [WC, WC] and linked.date.tolist() == ["2031-06-10",
                                                                            "2031-06-12"]


def test_the_same_two_teams_twice_on_different_dates() -> None:
    linked, rejected = match_crosswalk(
        [sb_match(1, "2031-06-10", "Norvik Athletic", "Sudmar Rovers"),
         sb_match(2, "2031-09-20", "Sudmar Rovers", "Norvik Athletic", teams=(2, 1))],
        [wy_match(502, "2031-09-20", 9002, 9001), wy_match(501, "2031-06-10", 9001, 9002)])
    assert dict(zip(linked.sb_game_id, linked.wy_game_id, strict=True)) == {1: 501, 2: 502}
    assert not linked.swapped.any() and sum(rejected.values()) == 0


@pytest.mark.parametrize(("day", "linked_count"), [("2031-06-11", 1), ("2031-06-09", 1),
                                                   ("2031-06-12", 0), ("2031-06-08", 0)])
def test_the_date_tolerance_edge(day, linked_count) -> None:
    assert CONFIG["match_date_tolerance_days"] == 1
    linked, rejected = match_crosswalk(
        [sb_match(1, "2031-06-10", "Norvik Athletic", "Sudmar Rovers")],
        [wy_match(501, day, 9001, 9002)])
    assert len(linked) == linked_count
    assert rejected["NO_CANDIDATE"] == 1 - linked_count


def test_an_ambiguous_day_is_rejected() -> None:
    # Both candidates qualify, the perfect one and one sharing a token per side.
    sb_rows = [sb_match(1, "2031-06-10", "Norvik Athletic", "Sudmar Rovers")]
    linked, rejected = match_crosswalk(sb_rows, [wy_match(501, "2031-06-10", 9001, 9002),
                                                 wy_match(502, "2031-06-10", 9005, 9006)])
    assert linked.empty and rejected["AMBIGUOUS"] == 1
    # The opposite: a same-day candidate that shares no token does not qualify.
    linked, rejected = match_crosswalk(sb_rows, [wy_match(501, "2031-06-10", 9001, 9002),
                                                 wy_match(502, "2031-06-10", 9003, 9004)])
    assert linked.wy_game_id.tolist() == [501] and sum(rejected.values()) == 0


def test_equal_overlaps_in_both_orientations_disqualify_a_lone_candidate() -> None:
    linked, rejected = match_crosswalk(
        [sb_match(1, "2031-06-10", "Ostra Town", "Ostra City")],
        [wy_match(501, "2031-06-10", 9007, 9008)])
    assert linked.empty and rejected["NO_CANDIDATE"] == 1


@pytest.mark.parametrize(("duration", "outcome"), [("Regular", "GOALS_DISAGREE"),
                                                   ("ExtraTime", "skipped"),
                                                   ("Penalties", "skipped")])
def test_goals_disagree_rejects_only_listed_durations(duration, outcome) -> None:
    assert CONFIG["match_require_goal_agreement_durations"] == ["Regular"]
    linked, rejected = match_crosswalk(
        [sb_match(1, "2031-06-10", "Norvik Athletic", "Sudmar Rovers", (2, 1))],
        [wy_match(501, "2031-06-10", 9001, 9002, (1, 1), duration)])
    if outcome == "GOALS_DISAGREE":
        assert linked.empty and rejected["GOALS_DISAGREE"] == 1
    else:
        assert linked.goal_check.tolist() == ["skipped"] and sum(rejected.values()) == 0


def test_a_candidate_qualifying_for_two_matches_is_claimed_twice() -> None:
    linked, rejected = match_crosswalk(
        [sb_match(1, "2031-06-10", "Norvik Athletic", "Sudmar Rovers"),
         sb_match(2, "2031-06-11", "Norvik Athletic", "Sudmar Rovers")],
        [wy_match(501, "2031-06-10", 9001, 9002)])
    assert linked.empty and rejected["CLAIMED_TWICE"] == 2
    # The opposite: three days apart, each candidate is unique in both directions.
    linked, rejected = match_crosswalk(
        [sb_match(1, "2031-06-10", "Norvik Athletic", "Sudmar Rovers"),
         sb_match(2, "2031-06-13", "Norvik Athletic", "Sudmar Rovers")],
        [wy_match(501, "2031-06-10", 9001, 9002), wy_match(502, "2031-06-13", 9001, 9002)])
    assert dict(zip(linked.sb_game_id, linked.wy_game_id, strict=True)) == {1: 501, 2: 502}
    assert sum(rejected.values()) == 0


def test_crosswalk_matches_takes_one_subset_folder() -> None:
    row = {**sb_match(1, "2031-06-10", "Norvik Athletic", "Sudmar Rovers"),
           "folder": "La_Liga_2017_18"}
    with pytest.raises(ValueError):
        match_crosswalk([row], [wy_match(501, "2031-06-10", 9001, 9002)])


def test_match_keys_follow_config_order_then_wyscout_id() -> None:
    def frame(subset, pairs):
        return pd.DataFrame([{**links(1).iloc[0].to_dict(), "subset": subset,
                              "sb_game_id": s, "wy_game_id": w} for s, w in pairs],
                            columns=LINK_COLUMNS)
    numbered = assign_match_keys([frame(LL, [(3, 100), (4, 120)]),
                                  frame(WC, [(1, 700), (2, 650)])], CONFIG)
    assert numbered.wy_game_id.tolist() == [650, 700, 100, 120]
    assert numbered.match_key.tolist() == [0, 1, 2, 3]
    assert str(numbered.match_key.dtype) == "int32"
    with pytest.raises(ValueError):
        assign_match_keys([frame(WC, [(1, 700)]), frame(LL, [(1, 701)])], CONFIG)


def test_crosswalk_digest_by_hand() -> None:
    frame = pd.DataFrame({"sb_game_id": [10, 9, 123], "wy_game_id": [200, 300, 4],
                          "other": [1, 2, 3]})
    lines = "10|200\n123|4\n9|300"  # sorted as strings, not as numbers
    assert crosswalk_digest(frame, ["sb_game_id", "wy_game_id"]) == hashlib.sha256(
        lines.encode("utf-8")).hexdigest()
    assert crosswalk_digest(frame.iloc[::-1], ["sb_game_id", "wy_game_id"]) == hashlib.sha256(
        lines.encode("utf-8")).hexdigest()
    assert crosswalk_digest(frame.iloc[:0], ["sb_game_id", "wy_game_id"]) == hashlib.sha256(
        b"").hexdigest()


# --- the team-sheet crosswalk ----------------------------------------------------------------

def test_zero_minute_rows_are_removed_on_each_side_by_its_own_minutes() -> None:
    people = [person(101, "Talo Brenvik"), person(102, "Udo Karsimo"),
              person(103, "Pell Varonne")]
    sb_rows = [sb(0, 1, "Talo Brenvik"), sb(0, 2, "Udo Karsimo", minutes=0),
               sb(1, 1, "Talo Brenvik"), sb(1, 3, "Pell Varonne", minutes=4)]
    wy_rows = [wy(0, 101), wy(0, 102, minutes=5), wy(1, 101), wy(1, 103, minutes=0)]
    pairs, _, audit = crosswalk(sb_rows, wy_rows, people, 2)
    assert audit["zero_minute_rows_dropped"] == {"sb": 1, "wy": 1}
    assert set(statuses(pairs)) == {(1, 101)}
    # The opposite: with minutes on both sheets the same rows pair.
    sb_rows[1], wy_rows[3] = sb(0, 2, "Udo Karsimo", minutes=3), wy(1, 103, minutes=2)
    pairs, _, audit = crosswalk(sb_rows, wy_rows, people, 2)
    assert audit["zero_minute_rows_dropped"] == {"sb": 0, "wy": 0}
    assert set(statuses(pairs)) == {(1, 101), (2, 102), (3, 103)}


def test_a_pair_is_taken_on_a_mutual_unique_maximum() -> None:
    people = [person(102, "Remo Tasca Bruni")]
    # 1 reaches 102 at 2/3 but 102's maximum is 2 at 1: only (2, 102) is mutual.
    pairs, _, _ = crosswalk([sb(0, 1, "Remo Tasca"), sb(0, 2, "Remo Tasca Bruni")],
                            [wy(0, 102)], people, 1)
    assert statuses(pairs) == {(2, 102): "PAIRED_BY_TEAM_SHEET"}
    # The opposite: a maximum shared by two rows is not unique, and nothing is taken.
    pairs, _, _ = crosswalk([sb(0, 1, "Remo Tasca Bruni"), sb(0, 2, "Remo Tasca Bruni")],
                            [wy(0, 102)], people, 1)
    assert pairs.empty


def test_a_shared_surname_is_resolved_by_the_full_name() -> None:
    people = [person(101, "Lusso Brenvald", "L. Brenvald"),
              person(102, "Marko Brenvald", "M. Brenvald")]
    pairs, _, _ = crosswalk([sb(0, 1, "Lusso Brenvald"), sb(0, 2, "Marko Brenvald")],
                            [wy(0, 101), wy(0, 102)], people, 1)
    assert statuses(pairs) == {(1, 101): "PAIRED_BY_TEAM_SHEET",
                               (2, 102): "PAIRED_BY_TEAM_SHEET"}
    assert pair(pairs, 1, 101)["sheets_named"] == 1


def test_leftovers_sharing_only_a_given_name_a_paired_team_mate_carries_stay_weak() -> None:
    sb_rows = [sb(0, 1, "Tomaso Varg"), sb(0, 2, "Tomaso Brill")]
    wy_rows = [wy(0, 101), wy(0, 102)]
    pairs, _, audit = crosswalk(sb_rows, wy_rows, [person(101, "Tomaso Varg"),
                                                   person(102, "Tomaso Kellen")], 1)
    assert statuses(pairs) == {(1, 101): "PAIRED_BY_TEAM_SHEET", (2, 102): "NAME_WEAK"}
    assert pair(pairs, 2, 102)["sheets_named"] == 0
    assert audit["subsets"][WC]["covered"]["sb"] == 1
    # The opposite: when the team-mate does not carry the given name, it distinguishes.
    sb_rows[0] = sb(0, 1, "Ivar Varg")
    pairs, _, _ = crosswalk(sb_rows, wy_rows, [person(101, "Ivar Varg"),
                                               person(102, "Tomaso Kellen")], 1)
    assert statuses(pairs) == {(1, 101): "PAIRED_BY_TEAM_SHEET",
                               (2, 102): "PAIRED_BY_TEAM_SHEET"}


def test_a_mononym_pairs_through_the_nickname() -> None:
    people = [person(101, "Quimo", "Quimo"), person(102, "Ravik Tenor", "R. Tenor")]
    pairs, _, _ = crosswalk([sb(0, 1, "Joaquino Sendrao Olm", "Quimo"), sb(0, 2, "Ravik Tenor")],
                            [wy(0, 101), wy(0, 102)], people, 1)
    assert statuses(pairs) == {(1, 101): "PAIRED_BY_TEAM_SHEET",
                               (2, 102): "PAIRED_BY_TEAM_SHEET"}
    # The opposite: a mononym two rows contain equally is nobody's unique maximum.
    pairs, _, _ = crosswalk([sb(0, 1, "Quimo Alvan"), sb(0, 2, "Quimo Beyra")],
                            [wy(0, 101)], people, 1)
    assert pairs.empty


def test_elimination_is_marked_and_is_not_paired() -> None:
    people = [person(101, "Ivar Varg"), person(102, "Kirr Yantoo")]
    sb_rows = [sb(0, 1, "Ivar Varg"), sb(0, 2, "Bexo Lantu")]
    pairs, _, audit = crosswalk(sb_rows, [wy(0, 101), wy(0, 102)], people, 1)
    assert statuses(pairs) == {(1, 101): "PAIRED_BY_TEAM_SHEET", (2, 102): "ELIMINATION_ONLY"}
    assert audit["subsets"][WC]["covered"] == {"sb": 1, "wy": 1}
    assert audit["subsets"][WC]["coverage"] == {"sb": 0.5, "wy": 0.5}
    # The opposite: leftovers whose started flags differ are not paired at all.
    sb_rows[1] = sb(0, 2, "Bexo Lantu", started=False, minutes=30)
    pairs, _, _ = crosswalk(sb_rows, [wy(0, 101), wy(0, 102)], people, 1)
    assert set(statuses(pairs)) == {(1, 101)}


@pytest.mark.parametrize(("started", "status"), [(False, "STRUCTURE_CONFLICT"),
                                                 (True, "PAIRED_BY_TEAM_SHEET")])
def test_a_started_conflict_fails_step_three(started, status) -> None:
    pairs, _, _ = crosswalk([sb(0, 1, "Ivar Varg", started=started)], [wy(0, 101)],
                            [person(101, "Ivar Varg")], 1)
    assert statuses(pairs) == {(1, 101): status}


@pytest.mark.parametrize(("minutes", "status"), [(80, "PAIRED_BY_TEAM_SHEET"),
                                                 (79, "STRUCTURE_CONFLICT")])
def test_the_minutes_tolerance_is_inclusive(minutes, status) -> None:
    assert CONFIG["sheet_minutes_tolerance"] == 10
    # 90 - 80 = 10 is at the tolerance and passes; 90 - 79 = 11 fails.
    pairs, _, _ = crosswalk([sb(0, 1, "Ivar Varg", minutes=minutes)], [wy(0, 101)],
                            [person(101, "Ivar Varg")], 1)
    assert statuses(pairs) == {(1, 101): status}


def test_one_failing_sheet_in_five_keeps_the_link_and_drops_that_player_match() -> None:
    sb_rows = [sb(key, 1, "Ivar Varg", minutes=60 if key == 2 else 90) for key in range(5)]
    pairs, dropped, audit = crosswalk(sb_rows, [wy(key, 101) for key in range(5)],
                                      [person(101, "Ivar Varg")], 5)
    row = pair(pairs, 1, 101)
    assert row["status"] == "PAIRED_BY_TEAM_SHEET"
    counts = (row["sheets_together"], row["sheets_structure_passed"], row["sheets_named"])
    assert counts == (5, 4, 5)
    assert dropped.to_dict("records") == [{"match_key": 2, "sb_player_id": 1}]
    assert str(dropped.match_key.dtype) == "int32"
    assert audit["player_matches_dropped"] == 1
    # A dropped player-match is not covered, on either side.
    assert audit["subsets"][WC]["player_matches"] == {"sb": 5, "wy": 5}
    assert audit["subsets"][WC]["covered"] == {"sb": 4, "wy": 4}
    assert audit["subsets"][WC]["coverage"] == {"sb": 0.8, "wy": 0.8}


def test_one_failing_sheet_in_three_is_a_structure_conflict() -> None:
    sb_rows = [sb(key, 1, "Ivar Varg", minutes=60 if key == 2 else 90) for key in range(3)]
    pairs, dropped, audit = crosswalk(sb_rows, [wy(key, 101) for key in range(3)],
                                      [person(101, "Ivar Varg")], 3)
    row = pair(pairs, 1, 101)
    assert (row["status"], row["sheets_together"], row["sheets_structure_passed"]) == (
        "STRUCTURE_CONFLICT", 3, 2)
    assert dropped.empty and audit["subsets"][WC]["covered"] == {"sb": 0, "wy": 0}


@pytest.mark.parametrize(("minutes", "status", "passed"), [(90, "PAIRED_BY_TEAM_SHEET", 2),
                                                           (60, "STRUCTURE_CONFLICT", 1)])
def test_sheets_together_counts_an_elimination_sheet_and_step_three_runs_there(
        minutes, status, passed) -> None:
    people = [person(101, "Dario Fenkel"), person(102, "Ivar Varg")]
    sb_rows = [sb(0, 1, "Dario Fenkel"), sb(0, 2, "Ivar Varg"),
               sb(1, 1, None, minutes=minutes), sb(1, 2, "Ivar Varg")]
    wy_rows = [wy(0, 101), wy(0, 102), wy(1, 101), wy(1, 102)]
    pairs, _, _ = crosswalk(sb_rows, wy_rows, people, 2)
    row = pair(pairs, 1, 101)
    assert (row["sheets_named"], row["sheets_together"]) == (1, 2)
    assert (row["status"], row["sheets_structure_passed"]) == (status, passed)


@pytest.mark.parametrize(("sb_flags", "wy_dismissed", "started", "status"), [
    ({}, False, True, "STRUCTURE_CONFLICT"),
    ({"dismissed": True}, False, True, "PAIRED_BY_TEAM_SHEET"),
    ({}, True, True, "PAIRED_BY_TEAM_SHEET"),
    ({"permanent_off": True}, False, True, "PAIRED_BY_TEAM_SHEET"),
    # The minutes check alone is waived: a started conflict still fails.
    ({"dismissed": True}, False, False, "STRUCTURE_CONFLICT"),
])
def test_both_minutes_waivers(sb_flags, wy_dismissed, started, status) -> None:
    pairs, _, _ = crosswalk([sb(0, 1, "Ivar Varg", minutes=60, started=started, **sb_flags)],
                            [wy(0, 101, dismissed=wy_dismissed)], [person(101, "Ivar Varg")], 1)
    assert statuses(pairs) == {(1, 101): status}


def test_a_cross_match_contradiction_drops_every_pair() -> None:
    people = [person(101, "Ivar Varg"), person(105, "Ivar Varg"), person(102, "Sten Ulvo")]
    sb_rows = [sb(0, 1, "Ivar Varg"), sb(1, 1, "Ivar Varg"), sb(1, 2, "Sten Ulvo")]
    pairs, _, audit = crosswalk(sb_rows, [wy(0, 101), wy(1, 105), wy(1, 102)], people, 2)
    assert statuses(pairs) == {(1, 101): "BIJECTION_CONFLICT", (1, 105): "BIJECTION_CONFLICT",
                               (2, 102): "PAIRED_BY_TEAM_SHEET"}
    assert audit["status_counts"]["BIJECTION_CONFLICT"] == 2
    assert audit["subsets"][WC]["covered"]["sb"] == 1
    # The opposite: the same partner in both matches is one link.
    pairs, _, _ = crosswalk(sb_rows, [wy(0, 101), wy(1, 101), wy(1, 102)], people, 2)
    assert statuses(pairs)[(1, 101)] == "PAIRED_BY_TEAM_SHEET"


@pytest.mark.parametrize(("keeper", "position", "status"), [
    (True, "DF", "STRUCTURE_CONFLICT"), (False, "GK", "STRUCTURE_CONFLICT"),
    (True, "GK", "PAIRED_BY_TEAM_SHEET"), (False, "DF", "PAIRED_BY_TEAM_SHEET")])
def test_the_goalkeeper_flags_must_agree(keeper, position, status) -> None:
    pairs, _, audit = crosswalk([sb(0, 1, "Ivar Varg", keeper=keeper)], [wy(0, 101)],
                                [person(101, "Ivar Varg", position=position)], 1)
    assert statuses(pairs) == {(1, 101): status}
    assert bool(pair(pairs, 1, 101)["is_goalkeeper"]) is (position == "GK")
    # Outfield per side: the StatsBomb flag and the Wyscout role code.
    assert audit["subsets"][WC]["player_matches"] == {"sb": int(not keeper),
                                                      "wy": int(position != "GK")}
    paired_outfield = int(status == "PAIRED_BY_TEAM_SHEET" and position != "GK")
    assert audit["paired_outfield"] == paired_outfield


def test_swap_impossible_and_the_cautioned_table() -> None:
    people = [person(101, "Lars Ofte"), person(102, "Mika Ruel")]
    sb_rows = [sb(0, 1, "Lars Ofte", cautioned=True), sb(0, 2, "Mika Ruel", cautioned=True)]
    wy_rows = [wy(0, 101, cautioned=True), wy(0, 102)]
    pairs, _, audit = crosswalk(sb_rows, wy_rows, people, 1)
    assert pairs.swap_impossible.tolist() == [True, True]
    assert audit["swap_impossible_share"] == 1.0
    assert audit["cautioned"] == {"both": 1, "sb_only": 1, "wy_only": 0}
    # The opposite: a shared given name across the two sheets makes a swap possible.
    people = [person(101, "Lars Ofte"), person(102, "Lars Ruel")]
    pairs, _, audit = crosswalk([sb(0, 1, "Lars Ofte"), sb(0, 2, "Lars Ruel")], wy_rows,
                                people, 1)
    assert pairs.swap_impossible.tolist() == [False, False]
    assert audit["swap_impossible_share"] == 0.0
    assert audit["cautioned"] == {"both": 0, "sb_only": 0, "wy_only": 1}


def test_names_sharing_only_a_particle_have_overlap_zero_and_a_null_form_is_zero() -> None:
    # Two rows a side, so elimination cannot pair them either.
    people = [person(101, "Caio da Prata", None), person(102, "Ivar Varg", None)]
    sb_rows = [sb(0, 1, "Bento da Lomba", None), sb(0, 2, None, None, started=False, minutes=20)]
    pairs, _, _ = crosswalk(sb_rows, [wy(0, 101), wy(0, 102, started=False, minutes=20)],
                            people, 1)
    assert pairs.empty
    # The opposite: a real shared token would have paired them.
    sb_rows[0] = sb(0, 1, "Caio da Lomba")
    pairs, _, _ = crosswalk(sb_rows, [wy(0, 101), wy(0, 102, started=False, minutes=20)],
                            people, 1)
    assert (1, 101) in statuses(pairs)


def test_coverage_is_reported_per_subset() -> None:
    people = [person(101, "Ivar Varg"), person(102, "Sten Ulvo"), person(103, "Kirr Yantoo")]
    sb_rows = [sb(0, 1, "Ivar Varg"), sb(0, 2, "Sten Ulvo"),
               sb(1, 1, "Ivar Varg"), sb(1, 3, "Remo Tasca", started=False, minutes=10)]
    wy_rows = [wy(0, 101), wy(0, 102), wy(1, 101), wy(1, 103, minutes=40)]
    pairs, _, audit = crosswalk(sb_rows, wy_rows, people, 2, subsets=[WC, LL])
    assert set(audit["subsets"]) == {WC, LL}
    assert audit["subsets"][WC]["team_matches"] == audit["subsets"][LL]["team_matches"] == 2
    assert audit["subsets"][WC]["coverage"] == {"sb": 1.0, "wy": 1.0}
    assert audit["subsets"][LL]["coverage"] == {"sb": 0.5, "wy": 0.5}
    assert audit["sheet_players"] == {"sb": 3, "wy": 3}
    assert audit["status_counts"] == {"PAIRED_BY_TEAM_SHEET": 2, "NAME_WEAK": 0,
                                      "ELIMINATION_ONLY": 0, "STRUCTURE_CONFLICT": 0,
                                      "BIJECTION_CONFLICT": 0}


# --- the wide link: name_nationality_link ------------------------------------------------------

def nn_link(lefts, rights, tiers, *, exclude=None, unique=True, config=CONFIG):
    left = pd.DataFrame(lefts, columns=["left_id", "full_name", "known_as", "country"])
    right = pd.DataFrame([{"right_id": r, "full_name": n, "countries": tuple(c)}
                          for r, n, c in rights], columns=["right_id", "full_name", "countries"])
    result = name_nationality_link(left, right, config, tiers=tiers, exclude_right=exclude,
                                   unique_right=unique)
    assert list(result.columns) == ["left_id", "right_id", "tier", "outcome"]
    assert str(result.right_id.dtype) == "Int64"
    return {int(row.left_id): (None if pd.isna(row.right_id) else int(row.right_id),
                               row.tier, row.outcome) for row in result.itertuples(index=False)}


def test_tier_a_is_on_the_legal_name_only_and_tier_n_on_the_nickname() -> None:
    lefts = [(1, "Abel Corte", "Corte Abelo", HOME), (2, "Basso Mirel", "Lino Prata", HOME)]
    rights = [(11, "Abel Corte", [HOME]), (12, "Lino Prata", [HOME])]
    assert nn_link(lefts, rights, ["A"]) == {1: (11, "A", "LINKED"),
                                             2: (None, None, "NO_CANDIDATE")}
    assert nn_link(lefts, rights, ["A", "N"]) == {1: (11, "A", "LINKED"),
                                                  2: (12, "N", "LINKED")}


def test_tier_n_is_tried_only_after_a_finds_nothing_and_only_with_a_nickname() -> None:
    lefts = [(3, "Cesar Dunn", "Dunno Cesk", HOME), (4, "Elio Fass", None, HOME),
             (5, "Gavo Hessel", "  ", HOME)]
    rights = [(13, "Cesar Dunn", [HOME]), (14, "Dunno Cesk", [HOME])]
    assert nn_link(lefts, rights, ["A", "N"]) == {3: (13, "A", "LINKED"),
                                                  4: (None, None, "NO_CANDIDATE"),
                                                  5: (None, None, "NO_CANDIDATE")}
    assert nn_link(lefts, rights, ["N", "A"])[3] == (14, "N", "LINKED")


def test_tier_b_is_strict_containment_with_enough_shared_tokens() -> None:
    lefts = [(6, "Gino Hart Ivel", None, HOME), (7, "Jono Kade", None, HOME),
             (8, "Moxo", None, HOME), (9, "Pava Rello", None, HOME)]
    rights = [(17, "Gino Hart", [HOME]), (18, "Jono Kade Lumi", [HOME]),
              (19, "Moxo Nuri", [HOME]), (20, "Pava Rello", [HOME])]
    assert nn_link(lefts, rights, ["A", "N", "B"]) == {
        6: (17, "B", "LINKED"), 7: (18, "B", "LINKED"),
        8: (None, None, "NO_CANDIDATE"),   # one shared token is below the minimum
        9: (20, "A", "LINKED")}
    assert nn_link(lefts, rights, ["A"])[6] == (None, None, "NO_CANDIDATE")
    # Equal sets are not strict containment: tier B alone does not link them.
    assert nn_link(lefts, rights, ["B"])[9] == (None, None, "NO_CANDIDATE")


def test_ambiguity_does_not_fall_through() -> None:
    lefts = [(9, "Oren Pask", "Quil Rast", HOME)]
    rights = [(20, "Oren Pask", [HOME]), (21, "Oren Pask", [HOME]), (22, "Quil Rast", [HOME])]
    assert nn_link(lefts, rights, ["A", "N"]) == {9: (None, "A", "AMBIGUOUS")}
    # The opposite: a namesake of another nationality is no candidate.
    rights[1] = (21, "Oren Pask", ["Belloria"])
    assert nn_link(lefts, rights, ["A", "N"]) == {9: (20, "A", "LINKED")}


def test_a_record_reached_by_two_lefts_is_claimed_twice_unless_unique_right_is_false() -> None:
    lefts = [(10, "Sato Tirel", None, HOME), (11, "Sato Tirel", None, HOME),
             (12, "Vino Wenz", None, HOME)]
    rights = [(23, "Sato Tirel", [HOME]), (24, "Vino Wenz", [HOME])]
    assert nn_link(lefts, rights, ["A"], unique=True) == {
        10: (23, "A", "CLAIMED_TWICE"), 11: (23, "A", "CLAIMED_TWICE"), 12: (24, "A", "LINKED")}
    assert nn_link(lefts, rights, ["A"], unique=False) == {
        10: (23, "A", "LINKED"), 11: (23, "A", "LINKED"), 12: (24, "A", "LINKED")}


def test_exclude_right_hides_one_record_from_one_left_only() -> None:
    lefts = [(30, "Vito Wenzel", None, HOME), (31, "Vito Wenzel", None, HOME)]
    rights = [(40, "Vito Wenzel", [HOME])]
    assert nn_link(lefts, rights, ["A"], exclude={30: 40}, unique=False) == {
        30: (None, None, "NO_CANDIDATE"), 31: (40, "A", "LINKED")}


def test_countries_compare_after_aliases_and_a_miss_is_no_link() -> None:
    assert CONFIG["country_aliases_normalised"]["korea south"] == "korea republic"
    lefts = [(1, "Abel Corte", None, "Korea, South"), (2, "Basso Mirel", None, "Cape Verde"),
             (3, "Cesar Dunn", None, "Ruritania"), (4, "Elio Fass", None, None),
             (5, "Gino Hart", None, ""), (6, "Jono Kade", None, HOME)]
    rights = [(11, "Abel Corte", ["Korea Republic", None]),
              (12, "Basso Mirel", [None, "Cape Verde Islands"]),
              (13, "Cesar Dunn", ["Ruritanian Republic"]),
              (14, "Elio Fass", [None, None]), (15, "Gino Hart", ["", None]),
              (16, "Jono Kade", ["Belloria", "ARVENIA"])]
    assert nn_link(lefts, rights, ["A"]) == {
        1: (11, "A", "LINKED"), 2: (12, "A", "LINKED"),
        3: (None, None, "NO_CANDIDATE"),   # outside the alias list: never a new alias
        4: (None, None, "NO_CANDIDATE"),   # a missing country never agrees
        5: (None, None, "NO_CANDIDATE"),
        6: (16, "A", "LINKED")}            # the passport area, normalised


def test_name_tokens_drop_one_letter_tokens_and_particles() -> None:
    lefts = [(1, "Abel Corte i Duran", None, HOME), (2, "Omar Al Fadel", None, HOME)]
    rights = [(11, "Abel Corte Duran", [HOME]), (12, "Omar Fadel", [HOME])]
    assert nn_link(lefts, rights, ["A"]) == {1: (11, "A", "LINKED"), 2: (12, "A", "LINKED")}
    # The opposite: a token that is neither is kept, and the sets differ.
    assert nn_link([(1, "Abel Corte io Duran", None, HOME)], rights, ["A"]) == {
        1: (None, None, "NO_CANDIDATE")}


def test_an_unknown_tier_raises() -> None:
    with pytest.raises(ValueError):
        nn_link([(1, "Abel Corte", None, HOME)], [(11, "Abel Corte", [HOME])], ["C"])


# --- the wide link: evaluation -------------------------------------------------------------

def blocks_by(blocks: list[dict]) -> dict[tuple[tuple[str, ...], str], dict]:
    return {(tuple(block["tiers"]), block["pool"]): block for block in blocks}


def test_evaluated_players_take_the_row_of_the_largest_match_key_and_count_disagreements() -> None:
    sb_rows = [sb(0, 1, "Talo Brenvik", "Tal", country="Korea, South"),
               sb(2, 1, "Talo Brenvik", "Talito", country="Korea, South"),
               sb(1, 1, "Talo Brenvik", None, minutes=0),
               sb(0, 2, "Udo Karsimo"), sb(2, 2, "Udo Karsimo"),
               sb(1, 7, "Remo Tasca", minutes=0)]
    wy_rows = [wy(0, 101), wy(0, 102), wy(1, 109, minutes=0), wy(2, 101), wy(2, 102),
               wy(1, 108, team=902)]
    sb_frame, wy_frame, _ = frames(sb_rows, wy_rows, [])
    people, sheet_ids, subsets, disagreeing = evaluated_players(
        sb_frame, wy_frame, links(3, [WC, WC, LL]))
    assert people.left_id.tolist() == [1, 2]   # player 7 has no regulation minutes
    first = people.iloc[0].to_dict()
    assert (first["full_name"], first["known_as"], first["country"]) == (
        "Talo Brenvik", "Talito", "Korea, South")
    assert disagreeing == 1
    # His sheets: every Wyscout row of his linked team, zero-minute rows on either side
    # included, and nothing of the other team.
    assert sheet_ids == {1: frozenset({101, 102, 109}), 2: frozenset({101, 102})}
    assert subsets == {1: frozenset({WC, LL}), 2: frozenset({WC, LL})}


def wide_case():
    """Sheets in which a paired player, an unpaired player linked to a record on his
    sheets (a zero-minute Wyscout row) and one linked off his sheets are evaluated."""
    people = [person(101, "Ivar Varg"), person(107, "Remo Tasca"), person(108, "Zeno Quast"),
              person(120, "Kirr Yantoo")]
    sb_rows = [sb(0, 1, "Ivar Varg"), sb(0, 7, "Remo Tasca", started=False, minutes=30),
               sb(0, 8, "Zeno Quast", started=False, minutes=20), sb(0, 9, "Sten Ulvo",
                                                                      minutes=0)]
    wy_rows = [wy(0, 101), wy(0, 107, started=False, minutes=0)]
    return frames(sb_rows, wy_rows, people)


def test_the_three_outcome_classes_on_and_off_the_sheets() -> None:
    sb_frame, wy_frame, people = wide_case()
    pairs, _, _ = team_sheet_crosswalk(sb_frame, wy_frame, people, links(1), CONFIG)
    assert statuses(pairs) == {(1, 101): "PAIRED_BY_TEAM_SHEET"}
    sb_people, sheet_ids, subsets, _ = evaluated_players(sb_frame, wy_frame, links(1))
    assert sheet_ids[7] == frozenset({101, 107})
    blocks = blocks_by(evaluate_wide_link(pairs, sb_people, people, sheet_ids, subsets, CONFIG))
    assert len(blocks) == len(CONFIG["link_tier_sets"]) * len(CONFIG["pools"])
    block = blocks[(("A",), "pooled")]
    assert (block["evaluated"], block["paired"]) == (3, 1)
    assert block["classes"] == {"CORRECT": 1, "FALSE": 1, "UNVERIFIABLE": 1, "NO_LINK": 0}
    assert block["outcomes"] == {"LINKED": 3, "AMBIGUOUS": 0, "CLAIMED_TWICE": 0,
                                 "NO_CANDIDATE": 0}
    assert block["recall"]["point"] == 0.5 and block["false_link_rate"]["point"] == 0.5
    assert block["no_link_rate"]["point"] == 0.0
    assert blocks[(("A",), LL)]["evaluated"] == 0
    assert blocks[(("A",), LL)]["recall"] == {"point": None, "lower": None, "upper": None}


def test_an_unpaired_player_whose_only_wyscout_row_has_zero_minutes_is_unverifiable() -> None:
    sb_frame, wy_frame, people = wide_case()
    pairs, _, _ = team_sheet_crosswalk(sb_frame, wy_frame, people, links(1), CONFIG)
    sb_people, sheet_ids, subsets, _ = evaluated_players(sb_frame, wy_frame, links(1))
    only = sb_people[sb_people.left_id == 7]
    block = blocks_by(evaluate_wide_link(pairs, only, people, sheet_ids, subsets, CONFIG))[
        (("A",), "pooled")]
    assert block["classes"]["UNVERIFIABLE"] == 1
    # The opposite: built after the zero-minute filter, his sheets would hold no such
    # record, and the same link would be counted FALSE.
    filtered = {7: frozenset({101})}
    block = blocks_by(evaluate_wide_link(pairs, only, people, filtered, subsets, CONFIG))[
        (("A",), "pooled")]
    assert block["classes"]["FALSE"] == 1


def stress_case(namesake_birth: str):
    sb_people = pd.DataFrame([{"left_id": 1, "full_name": "Abel Corte", "known_as": None,
                               "country": HOME}])
    people = pd.DataFrame([person(101, "Abel Corte"),
                           person(102, "Abel Corte", birth=namesake_birth,
                                  passport=namesake_birth)], columns=PEOPLE_COLUMNS)
    pairs = pd.DataFrame([{"sb_player_id": 1, "wy_player_id": 101,
                           "status": "PAIRED_BY_TEAM_SHEET"}])
    blocks = evaluate_wide_link(pairs, sb_people, people, {1: frozenset({101})},
                                {1: frozenset({WC})}, CONFIG)
    return blocks_by(blocks)[(("A",), "pooled")]


def test_absent_partner_with_a_planted_namesake() -> None:
    block = stress_case(HOME)
    # The namesake makes the full run ambiguous; with the partner hidden he links to it.
    assert block["outcomes"]["AMBIGUOUS"] == 1 and block["classes"]["NO_LINK"] == 1
    assert block["absent_partner_stress_rate"]["point"] == 1.0
    assert block["namesake_collision"]["linked"] == 2
    # The opposite: a namesake of another nationality leaves no link once the partner is gone.
    block = stress_case("Belloria")
    assert block["classes"]["CORRECT"] == 1
    assert block["absent_partner_stress_rate"]["point"] == 0.0
    assert block["namesake_collision"]["linked"] == 0


def test_the_stress_applies_the_claimed_twice_rule_against_the_full_run() -> None:
    # Player 1's partner is 101; player 2 links 102 in the full run. With 101 hidden,
    # player 1 would reach 102 too, which player 2 holds: claimed twice, not linked.
    sb_people = pd.DataFrame([{"left_id": 1, "full_name": "Abel Corte", "known_as": "Lino Prata",
                               "country": HOME},
                              {"left_id": 2, "full_name": "Lino Prata", "known_as": None,
                               "country": HOME}])
    people = pd.DataFrame([person(101, "Abel Corte"), person(102, "Lino Prata")],
                          columns=PEOPLE_COLUMNS)
    pairs = pd.DataFrame([{"sb_player_id": 1, "wy_player_id": 101,
                           "status": "PAIRED_BY_TEAM_SHEET"}])
    blocks = blocks_by(evaluate_wide_link(pairs, sb_people, people, {1: frozenset(),
                                                                      2: frozenset()},
                                          {1: frozenset({WC}), 2: frozenset({WC})}, CONFIG))
    assert blocks[(("A", "N"), "pooled")]["absent_partner_stress_rate"]["point"] == 0.0
    # The opposite: when nobody else holds 102, the hidden partner leaves a live link.
    blocks = blocks_by(evaluate_wide_link(pairs, sb_people.iloc[:1], people, {1: frozenset()},
                                          {1: frozenset({WC})}, CONFIG))
    assert blocks[(("A", "N"), "pooled")]["absent_partner_stress_rate"]["point"] == 1.0


def test_the_graded_runs_are_calls_of_the_public_link_function(monkeypatch) -> None:
    """The full run and every stress rerun go through ``name_nationality_link``, the
    function a later study calls: once per tier set on all evaluated players, then once
    per paired player alone with his partner hidden, never one call for all of them."""
    names = {1: "Abel Corte", 2: "Basso Mirel", 3: "Cesar Dunn"}
    sb_people = pd.DataFrame([{"left_id": player, "full_name": name, "known_as": None,
                               "country": HOME} for player, name in names.items()])
    people = pd.DataFrame([person(100 + player, name) for player, name in names.items()],
                          columns=PEOPLE_COLUMNS)
    pairs = pd.DataFrame([{"sb_player_id": player, "wy_player_id": 100 + player,
                           "status": "PAIRED_BY_TEAM_SHEET"} for player in (1, 2)])
    sheets = {player: frozenset({100 + player}) for player in names}
    subsets = {player: frozenset({WC}) for player in names}
    original = provider_crosswalk.name_nationality_link
    calls = []

    def spy(left, right, config, *, tiers, exclude_right, unique_right):
        calls.append(repr((list(tiers), left["left_id"].tolist(), right["right_id"].tolist(),
                           exclude_right, unique_right)))
        return original(left, right, config, tiers=tiers, exclude_right=exclude_right,
                        unique_right=unique_right)

    monkeypatch.setattr(provider_crosswalk, "name_nationality_link", spy)
    blocks = blocks_by(evaluate_wide_link(pairs, sb_people, people, sheets, subsets, CONFIG))
    expected = []
    for tiers in CONFIG["link_tier_sets"]:
        expected += [repr((tiers, [1, 2, 3], [101, 102, 103], None, True)),
                     repr((tiers, [1], [101, 102, 103], {1: 101}, True)),
                     repr((tiers, [2], [101, 102, 103], {2: 102}, True)),
                     repr((tiers, [101, 102, 103], [101, 102, 103],
                           {101: 101, 102: 102, 103: 103}, False))]
    assert sorted(calls) == sorted(expected)
    assert blocks[(("A",), "pooled")]["classes"] == {"CORRECT": 2, "FALSE": 0,
                                                    "UNVERIFIABLE": 1, "NO_LINK": 0}

    # The consequence: a step added to the public function outside its core reaches
    # every class and the stress, read from the frame it returns.
    def no_links(left, right, config, *, tiers, exclude_right, unique_right):
        links = original(left, right, config, tiers=tiers, exclude_right=exclude_right,
                         unique_right=unique_right)
        return links.assign(right_id=pd.Series(pd.NA, index=links.index, dtype="Int64"),
                            tier=None, outcome="NO_CANDIDATE")

    monkeypatch.setattr(provider_crosswalk, "name_nationality_link", no_links)
    block = blocks_by(evaluate_wide_link(pairs, sb_people, people, sheets, subsets, CONFIG))[
        (("A",), "pooled")]
    assert block["classes"] == {"CORRECT": 0, "FALSE": 0, "UNVERIFIABLE": 0, "NO_LINK": 3}
    assert (block["paired"], block["absent_partner_stress_rate"]["point"]) == (2, 0.0)


def test_namesake_collision_on_a_planted_roster() -> None:
    people = pd.DataFrame([
        person(1, "Abel Corte"), person(2, "Abel Corte"),                    # both link
        person(3, "Basso Mirel", passport="Belloria"),                       # one direction:
        person(4, "Basso Mirel", birth="Belloria"),                          # 4 reaches 3
        person(5, "Cesar Dunn"), person(6, "Cesar Dunn"), person(7, "Cesar Dunn"),  # ambiguous
        person(8, "Elio Fass"),
    ], columns=PEOPLE_COLUMNS)
    result = namesake_collision(people, CONFIG, tiers=["A"])
    lower, upper = wilson_oracle(3, 8, CONFIG["wilson_z"])
    assert result == {"linked": 3, "records": 8, "point": 3 / 8,
                      "lower": pytest.approx(lower, rel=1e-12),
                      "upper": pytest.approx(upper, rel=1e-12)}


def invented_names(seed: int, count: int) -> list[str]:
    """Distinct two-token names from syllables: a four-letter given name and a six-letter
    surname, so no two names share a token set and none contains another."""
    rng = np.random.default_rng(seed)
    syllables = ("ba", "ce", "di", "fo", "gu", "ka", "le", "mi", "no", "pu", "ra", "se",
                 "ti", "vo", "zu", "xa")
    seen, names = set(), []
    while len(names) < count:
        name = ("".join(rng.choice(syllables, 2)).capitalize() + " "
                + "".join(rng.choice(syllables, 3)).capitalize())
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def test_a_planted_hundred_person_roster_returns_the_planted_rates_exactly() -> None:
    names = iter(invented_names(20261014, 220))
    sb_people, people, pairs = [], [], []
    sheet_ids: dict[int, frozenset[int]] = {}
    wy_ids = itertools.count(5001)
    plan = ([("correct", True)] * 56 + [("namesake", True)] * 4 + [("false", True)] * 10
            + [("missing", True)] * 10 + [("on_sheet", False)] * 10
            + [("off_sheet", False)] * 5 + [("missing", False)] * 5)
    for index, (kind, paired) in enumerate(plan):
        player, name = 1001 + index, next(names)
        sb_people.append({"left_id": player, "full_name": name, "known_as": None,
                          "country": HOME})
        sheet = set()
        if paired:
            partner = next(wy_ids)
            people.append(person(partner, name if kind in ("correct", "namesake")
                                 else next(names)))
            pairs.append({"sb_player_id": player, "wy_player_id": partner,
                          "status": "PAIRED_BY_TEAM_SHEET"})
            sheet.add(partner)
        if kind in ("namesake", "false", "on_sheet", "off_sheet"):
            record = next(wy_ids)
            people.append(person(record, name))
            if kind == "on_sheet":
                sheet.add(record)
        sheet_ids[player] = frozenset(sheet)
    # A pair of another status is not a pairing.
    pairs.append({"sb_player_id": 1100, "wy_player_id": 9999, "status": "NAME_WEAK"})
    subsets = {1001 + index: frozenset({WC} if index % 2 else {WC, LL}) for index in range(100)}

    blocks = blocks_by(evaluate_wide_link(
        pd.DataFrame(pairs), pd.DataFrame(sb_people),
        pd.DataFrame(people, columns=PEOPLE_COLUMNS), sheet_ids, subsets, CONFIG))
    z = CONFIG["wilson_z"]
    planted = {"recall": (56, 90), "false_link_rate": (15, 71), "no_link_rate": (19, 100),
               "absent_partner_stress_rate": (14, 80)}
    for tiers in CONFIG["link_tier_sets"]:
        block = blocks[(tuple(tiers), "pooled")]
        assert (block["evaluated"], block["paired"]) == (100, 80)
        assert block["classes"] == {"CORRECT": 56, "FALSE": 15, "UNVERIFIABLE": 10,
                                    "NO_LINK": 19}
        assert block["outcomes"] == {"LINKED": 81, "AMBIGUOUS": 4, "CLAIMED_TWICE": 0,
                                     "NO_CANDIDATE": 15}
        for rate, (k, n) in planted.items():
            lower, upper = wilson_oracle(k, n, z)
            assert block[rate]["point"] == float(Fraction(k, n))
            assert block[rate]["lower"] == pytest.approx(lower, rel=1e-12)
            assert block[rate]["upper"] == pytest.approx(upper, rel=1e-12)
        collision = block["namesake_collision"]
        assert (collision["linked"], collision["records"]) == (8, 109)
        assert block["absent_partner_bound"] == max(
            block["absent_partner_stress_rate"]["upper"], collision["upper"])
        paired = block["paired_only"]
        assert paired["classes"] == {"CORRECT": 56, "FALSE": 10, "UNVERIFIABLE": 0,
                                     "NO_LINK": 14}
        assert paired["recall"]["point"] == 56 / 80
        assert block["nickname_absent"]["evaluated"] == 100
        assert block["nickname_present"]["evaluated"] == 0
        assert blocks[(tuple(tiers), WC)]["evaluated"] == 100
        assert blocks[(tuple(tiers), LL)]["evaluated"] == 50


def test_the_audit_and_the_blocks_are_aggregate_json() -> None:
    """Both reach results.local.json: no NaN, no identifier key, no provider-named key."""
    from galactico.domain.thesis import banned_key_paths

    sb_frame, wy_frame, people = wide_case()
    pairs, _, audit = team_sheet_crosswalk(sb_frame, wy_frame, people, links(1), CONFIG)
    sb_people, sheet_ids, subsets, _ = evaluated_players(sb_frame, wy_frame, links(1))
    blocks = evaluate_wide_link(pairs, sb_people, people, sheet_ids, subsets, CONFIG)
    _, rejected = match_crosswalk([sb_match(1, "2031-06-10", "Norvik Athletic",
                                            "Sudmar Rovers")],
                                  [wy_match(501, "2031-07-10", 9001, 9002)])
    assert rejected["NO_CANDIDATE"] == 1
    payload = {"audit": audit, "identity": blocks, "rejected": rejected}
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload

    def keys(node):
        if isinstance(node, dict):
            for key, value in node.items():
                yield key
                yield from keys(value)
        elif isinstance(node, list):
            for value in node:
                yield from keys(value)

    found = list(keys(payload))
    assert found and banned_key_paths(payload) == []
    assert not set(found) & set(CONFIG["results_identifier_key_denylist"])
    for key in found:
        assert key.startswith("SB_") is False
        assert not any(name in key.lower() for name in ("statsbomb", "pappalardo", "wyscout"))


# --- Wilson and the link verdict --------------------------------------------------------------

def wilson_oracle(k: int, n: int, z: float) -> tuple[float, float]:
    """The two roots in p of (p_hat - p)^2 = z^2 p (1 - p) / n, by the quadratic formula."""
    p_hat, z2 = Fraction(k, n), Fraction(z) ** 2
    a, b, c = 1 + z2 / n, -(2 * p_hat + z2 / n), p_hat ** 2
    root = math.sqrt(b * b - 4 * a * c)
    return float((-b - Fraction(root)) / (2 * a)), float((-b + Fraction(root)) / (2 * a))


@pytest.mark.parametrize(("k", "n"), [(56, 90), (15, 71), (1, 600), (3, 849), (400, 401)])
def test_wilson_against_the_quadratic(k, n) -> None:
    lower, upper = wilson_interval(k, n, CONFIG["wilson_z"])
    expected = wilson_oracle(k, n, CONFIG["wilson_z"])
    assert (lower, upper) == (pytest.approx(expected[0], rel=1e-12),
                              pytest.approx(expected[1], rel=1e-12))


def test_wilson_against_hand_numbers() -> None:
    z = 1.96
    # Every success: the upper bound is 1 and the lower is n / (n + z^2).
    assert wilson_interval(10, 10, z) == (pytest.approx(10 / (10 + z * z)), pytest.approx(1.0))
    # No success: the lower bound is 0 and the upper is z^2 / (n + z^2).
    assert wilson_interval(0, 10, z) == (pytest.approx(0.0), pytest.approx(z * z / (10 + z * z)))
    # 8 of 10 at 1.96, the textbook (0.4902, 0.9433).
    lower, upper = wilson_interval(8, 10, z)
    assert (round(lower, 4), round(upper, 4)) == (0.4902, 0.9433)


def test_zero_trials_give_none_and_none_fails_the_verdict() -> None:
    assert wilson_interval(0, 0, CONFIG["wilson_z"]) == (None, None)
    with pytest.raises(ValueError):
        wilson_interval(3, 2, CONFIG["wilson_z"])
    for field, key in (("recall", "lower"), ("false_link_rate", "upper"),
                       ("absent_partner_stress_rate", "upper"), ("namesake_collision", "upper")):
        block = usable_block()
        block[field] = {**block[field], key: None}
        assert link_verdict(block, [], CONFIG) == ("LINK_NOT_ESTABLISHED", None), field
        block[field] = {**block[field], key: float("nan")}
        assert link_verdict(block, [], CONFIG) == ("LINK_NOT_ESTABLISHED", None), field


def usable_block() -> dict:
    return {"tiers": ["A"], "pool": "pooled",
            "evaluated": CONFIG["link_minimum_evaluated_players"],
            "false_link_rate": {"point": 0.0, "lower": 0.0,
                                "upper": CONFIG["link_false_link_rate_upper_maximum"]},
            "recall": {"point": 0.7, "lower": CONFIG["link_recall_lower_minimum"],
                       "upper": 0.8},
            "absent_partner_stress_rate": {
                "point": 0.0, "lower": 0.0,
                "upper": CONFIG["link_absent_partner_false_link_rate_upper_maximum"]},
            "namesake_collision": {"linked": 0, "records": 10, "point": 0.0, "lower": 0.0,
                                   "upper": 0.001}}


def test_each_gate_and_too_few_players_gives_its_own_reason_in_order() -> None:
    reasons = CONFIG["link_inconclusive_reasons"]
    gates = [reason for reason in reasons if reason != "EVALUATED_PLAYERS"]
    assert reasons[-1] == "EVALUATED_PLAYERS" and len(gates) == 4
    for start, gate in enumerate(gates):
        failed = [*gates[start:], "XT_SURFACE"]
        assert link_verdict(usable_block(), failed[::-1], CONFIG) == ("INCONCLUSIVE", gate)
        # A run a gate stopped has an empty block, and still gets its verdict.
        assert link_verdict({}, failed, CONFIG) == ("INCONCLUSIVE", gate)
    too_few = {**usable_block(), "evaluated": CONFIG["link_minimum_evaluated_players"] - 1}
    assert link_verdict(too_few, ["XT_SURFACE"], CONFIG) == ("INCONCLUSIVE", "EVALUATED_PLAYERS")
    assert link_verdict({}, [], CONFIG) == ("INCONCLUSIVE", "EVALUATED_PLAYERS")
    # The opposite: a gate that is not a link gate changes nothing.
    assert link_verdict(usable_block(), ["XT_SURFACE"], CONFIG) == ("LINK_USABLE", None)


def test_the_reasons_are_the_four_link_gates_then_the_evaluated_players() -> None:
    gates = CONFIG["link_inconclusive_reasons"][:-1]
    # The gates are taken in the order the config lists them.
    reordered = with_config(link_inconclusive_reasons=[*gates[::-1], "EVALUATED_PLAYERS"])
    assert link_verdict({}, gates, reordered) == ("INCONCLUSIVE", gates[-1])
    for broken in (["EVALUATED_PLAYERS", *gates],
                   [*gates[:3], "EVALUATED_PLAYERS", gates[3]],
                   [*gates[:3], "EVALUATED_PLAYERS"],
                   [*gates, "XT_SURFACE", "EVALUATED_PLAYERS"],
                   [*gates, gates[0], "EVALUATED_PLAYERS"],
                   [*gates, "EVALUATED_PLAYERS", "EVALUATED_PLAYERS"],
                   []):
        with pytest.raises(ValueError):
            link_verdict({}, [gates[0]], with_config(link_inconclusive_reasons=broken))


def nudged(field: str, key: str, direction: float) -> dict:
    block = usable_block()
    block[field] = {**block[field], key: float(np.nextafter(block[field][key], direction))}
    return block


@pytest.mark.parametrize(("block", "verdict"), [
    (usable_block(), "LINK_USABLE"),                                 # every bound on its limit
    (nudged("false_link_rate", "upper", 1.0), "LINK_NOT_ESTABLISHED"),
    (nudged("recall", "lower", 0.0), "LINK_NOT_ESTABLISHED"),
    (nudged("absent_partner_stress_rate", "upper", 1.0), "LINK_NOT_ESTABLISHED"),
    (nudged("false_link_rate", "upper", 0.0), "LINK_USABLE"),
    (nudged("recall", "lower", 1.0), "LINK_USABLE"),
])
def test_the_link_verdict_boundaries(block, verdict) -> None:
    assert link_verdict(block, [], CONFIG) == (verdict, None)


def test_the_absent_partner_bound_is_the_larger_upper_bound() -> None:
    block = usable_block()
    block["absent_partner_stress_rate"] = {**block["absent_partner_stress_rate"], "upper": 0.0}
    block["namesake_collision"] = {**block["namesake_collision"], "upper": 0.03}
    assert link_verdict(block, [], CONFIG) == ("LINK_NOT_ESTABLISHED", None)
    block["namesake_collision"]["upper"] = 0.02
    assert link_verdict(block, [], CONFIG) == ("LINK_USABLE", None)


def test_link_verdict_grades_the_verdict_pool_only() -> None:
    with pytest.raises(ValueError):
        link_verdict({**usable_block(), "pool": WC}, [], CONFIG)


# --- permuted partners ---------------------------------------------------------------------

def oracle_partners(keys, stratum, seed) -> list[int]:
    """PIPELINE section 3, step by step, with its own generator."""
    rng = np.random.default_rng(np.random.SeedSequence(
        [CONFIG["seed"], CONFIG["seed_streams"]["permuted_link"], seed]))
    roles = CONFIG["rank_strata_roles"]
    partner = list(range(len(keys)))
    for team, role in sorted(set(stratum), key=lambda s: (s[0], roles.index(s[1]))):
        s = sorted((i for i in range(len(keys)) if stratum[i] == (team, role)),
                   key=lambda i: keys[i])
        if len(s) < 2:
            continue
        o = [s[p] for p in rng.permutation(len(s))]
        for j in range(len(o)):
            partner[o[j]] = o[(j + 1) % len(o)]
    return partner


COHORT_KEYS = np.array([11, 12, 15, 18, 20, 23, 31])
COHORT_STRATA = [(700, "DF"), (300, "MD"), (700, "FW"), (300, "MD"), (700, "DF"),
                 (300, "MD"), (300, "MD")]


@pytest.mark.parametrize("seed", [0, 1, 7, 19])
def test_the_exact_partner_array_equals_the_oracle(seed) -> None:
    partner, singletons = permuted_partners(COHORT_KEYS, COHORT_STRATA, CONFIG, seed=seed)
    assert partner.dtype == np.int64
    assert partner.tolist() == oracle_partners(COHORT_KEYS.tolist(), COHORT_STRATA, seed)
    assert singletons == 1
    assert partner[2] == 2                          # the lone forward keeps his own value
    assert (partner[0], partner[4]) == (4, 0)       # a stratum of two swaps


def test_no_fixed_point_inside_strata_and_deterministic() -> None:
    rng = np.random.default_rng(31)
    keys = np.sort(rng.choice(np.arange(1, 10_000), size=60, replace=False))
    stratum = [(int(rng.integers(1, 4)) * 100, ("DF", "MD", "FW")[int(rng.integers(0, 3))])
               for _ in keys]
    sizes = {group: stratum.count(group) for group in set(stratum)}
    outcomes = []
    for seed in range(20):
        partner, singletons = permuted_partners(keys, stratum, CONFIG, seed=seed)
        assert sorted(partner.tolist()) == list(range(len(keys)))
        assert singletons == sum(size == 1 for size in sizes.values())
        for i, j in enumerate(partner.tolist()):
            assert stratum[j] == stratum[i]
            assert (j != i) is (sizes[stratum[i]] >= 2)
        again, _ = permuted_partners(keys, stratum, CONFIG, seed=seed)
        assert again.tolist() == partner.tolist()
        outcomes.append(tuple(partner.tolist()))
    assert len(set(outcomes)) > 1


def test_a_singleton_draws_nothing() -> None:
    base, _ = permuted_partners(COHORT_KEYS, COHORT_STRATA, CONFIG, seed=3)
    # A singleton stratum visited first, with the largest key, changes nobody's partner.
    keys = np.append(COHORT_KEYS, 40)
    partner, singletons = permuted_partners(keys, [*COHORT_STRATA, (100, "DF")], CONFIG, seed=3)
    assert partner[:-1].tolist() == base.tolist() and partner[-1] == 7 and singletons == 2
    # The opposite: a stratum of two visited first draws, and the shuffles move.
    keys = np.append(COHORT_KEYS, [40, 41])
    moved = [permuted_partners(keys, [*COHORT_STRATA, (100, "DF"), (100, "DF")], CONFIG,
                               seed=seed)[0][:-2].tolist()
             != permuted_partners(COHORT_KEYS, COHORT_STRATA, CONFIG, seed=seed)[0].tolist()
             for seed in range(20)]
    assert any(moved)


def test_a_role_outside_the_rank_strata_roles_raises() -> None:
    with pytest.raises(ValueError):
        permuted_partners(COHORT_KEYS, [*COHORT_STRATA[:-1], (300, "GK")], CONFIG, seed=0)
    with pytest.raises(ValueError):
        permuted_partners(COHORT_KEYS[::-1].copy(), COHORT_STRATA, CONFIG, seed=0)
