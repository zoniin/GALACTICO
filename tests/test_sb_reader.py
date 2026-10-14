"""The raw StatsBomb research reader of E-11, on hand-built folders only.

Every folder below is written into a temporary directory from a seed: names, ids,
dates and coordinates are invented, and no row is copied from either provider.
Kind and type names are the provider's vocabulary as the frozen config lists it,
and the keyword values of the readers are the frozen config's. Each expected value
is written from PIPELINE.md section 2 with hand numbers, ``fractions`` and
``hashlib``; nothing from the module under test computes one. No test opens
anything under ``data/``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import random
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from galactico.providers.statsbomb import SEASONS, StatsBombProvider
from galactico.validation import sb_reader
from galactico.validation.sb_reader import (
    READER_VERSION,
    folder_manifest,
    folder_vocabulary,
    iter_events,
    read_events,
    read_matches,
    read_team_sheets,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads(
    (ROOT / "experiments/preregistered/E-11-provider-agreement/config.json")
    .read_text(encoding="utf-8"))
WAIVER = CONFIG["sheet_minutes_waiver"]
SHEETS = {
    "cap": CONFIG["regulation_minutes_cap"],
    "regulation_periods": CONFIG["sb_regulation_periods"],
    "goalkeeper_position": CONFIG["sb_goalkeeper_position"],
    "dismissal_card_types_exclude": WAIVER["sb_dismissal_card_types_exclude"],
    "spell_end_reason_contains": WAIVER["sb_spell_end_reason_contains"],
}
SCALE = CONFIG["sb_location_scale"]
GOALKEEPER = CONFIG["sb_goalkeeper_position"]
YELLOW = WAIVER["sb_dismissal_card_types_exclude"][0]
PERMANENT = WAIVER["sb_spell_end_reason_contains"]
FOLDER = "Invented_Cup_2031"
SYLLABLES = ("ka", "lo", "mi", "ren", "tu", "sa", "vo", "del", "ni", "ar", "pe", "zu")


def invented(rng: random.Random) -> str:
    """A two-word name drawn from syllables: nobody's."""
    def word() -> str:
        return "".join(rng.choice(SYLLABLES) for _ in range(3)).capitalize()
    return f"{word()} {word()}"


def new_ids(rng: random.Random, count: int) -> list[int]:
    return rng.sample(range(10_000, 9_999_999), count)


def match_entry(rng: random.Random, game_id: int, **fields: object) -> dict:
    entry = {
        "match_id": game_id,
        "match_date": f"2031-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
        "home_team": {"home_team_id": rng.randint(1, 9_999), "home_team_name": invented(rng)},
        "away_team": {"away_team_id": rng.randint(1, 9_999), "away_team_name": invented(rng)},
        "home_score": rng.randint(0, 5),
        "away_score": rng.randint(0, 5),
        "competition_stage": {"id": rng.randint(1, 99), "name": invented(rng)},
        "metadata": {"data_version": f"{rng.randint(1, 9)}.{rng.randint(0, 9)}.0"},
    }
    return {**entry, **fields}


def write_folder(root: Path, index: list[dict], events: dict[int, object] | None = None,
                 lineups: dict[int, object] | None = None, folder: str = FOLDER) -> Path:
    base = root / folder
    (base / "events").mkdir(parents=True, exist_ok=True)
    (base / "_lineups").mkdir(exist_ok=True)
    (base / "_matches.json").write_text(json.dumps(index), encoding="utf-8")
    for game_id, content in (events or {}).items():
        (base / "events" / f"{game_id}.json").write_text(json.dumps(content), encoding="utf-8")
    for game_id, content in (lineups or {}).items():
        (base / "_lineups" / f"{game_id}.json").write_text(json.dumps(content), encoding="utf-8")
    return base


class Events:
    """Builds one match's raw event list with consecutive ``index`` values."""

    def __init__(self, rng: random.Random, team: int) -> None:
        self.rng, self.team, self.rows = rng, team, []

    def add(self, kind: str, *, period: int = 1, timestamp: str = "00:00:01.000",
            player: int | None = None, location: list[float] | None = None,
            **details: object) -> dict:
        row = {
            "id": f"{self.rng.getrandbits(128):032x}",
            "index": len(self.rows) + 1,
            "period": period,
            "timestamp": timestamp,
            # Deliberately not the timestamp: the reader must not use these.
            "minute": self.rng.randint(0, 120),
            "second": self.rng.randint(0, 59),
            "type": {"id": self.rng.randint(1, 99), "name": kind},
            "team": {"id": self.team, "name": invented(self.rng)},
            "play_pattern": {"id": 1, "name": "Invented Pattern"},
        }
        if player is not None:
            row["player"] = {"id": player, "name": invented(self.rng)}
        if location is not None:
            row["location"] = location
        row.update(details)
        self.rows.append(row)
        return row

    def point(self) -> list[float]:
        return [round(self.rng.uniform(0, 120), 1), round(self.rng.uniform(0, 80), 1)]


def spell(position: str, start: str, end: str | None, from_period: int,
          to_period: int | None, end_reason: str | None = None) -> dict:
    return {"position_id": 0, "position": position, "from": start, "to": end,
            "from_period": from_period, "to_period": to_period,
            "start_reason": "Invented Start", "end_reason": end_reason}


def sheet_player(rng: random.Random, player_id: int, spells: list[dict],
                 cards: tuple[str, ...] = (), nickname: bool = True,
                 country: bool = True) -> dict:
    return {
        "player_id": player_id,
        "player_name": invented(rng),
        "player_nickname": invented(rng) if nickname else None,
        "jersey_number": rng.randint(1, 99),
        "country": {"id": rng.randint(1, 250), "name": invented(rng)} if country else None,
        "cards": [{"time": "50:00", "card_type": card, "reason": "Invented", "period": 2}
                  for card in cards],
        "positions": spells,
    }


def one_sheet(root: Path, seed: int, spells_by_player: list[list[dict]],
              cards_by_player: list[tuple[str, ...]] | None = None) -> pd.DataFrame:
    """One match, one team, the players in order; rows indexed by their place."""
    rng = random.Random(seed)
    game_id, team_id, *player_ids = new_ids(rng, 2 + len(spells_by_player))
    cards = cards_by_player or [()] * len(spells_by_player)
    lineup = [sheet_player(rng, pid, spells, held)
              for pid, spells, held in zip(player_ids, spells_by_player, cards, strict=True)]
    write_folder(root, [match_entry(rng, game_id)], events={game_id: []},
                 lineups={game_id: [{"team_id": team_id, "team_name": invented(rng),
                                     "lineup": lineup}]})
    sheets = read_team_sheets(root, FOLDER, [game_id], **SHEETS)
    place = {pid: i for i, pid in enumerate(player_ids)}
    return sheets.set_index(sheets.sb_player_id.map(place)).sort_index()


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Module surface


def test_the_module_names_exactly_the_functions_of_section_2() -> None:
    assert READER_VERSION == "statsbomb-research-reader-v2"
    assert sorted(sb_reader.__all__) == sorted([
        "READER_VERSION", "read_matches", "read_team_sheets", "iter_events", "read_events",
        "folder_vocabulary", "folder_manifest"])


@pytest.mark.parametrize("function", [read_matches, read_team_sheets, iter_events, read_events,
                                      folder_vocabulary, folder_manifest])
def test_no_argument_has_a_default(function) -> None:
    """The cap, the periods, the card and spell rules and the scale come from config."""
    parameters = inspect.signature(function).parameters.values()
    assert all(p.default is inspect.Parameter.empty for p in parameters)


def test_the_sheet_and_scale_rules_are_keyword_only() -> None:
    sheets = inspect.signature(read_team_sheets).parameters
    assert [n for n, p in sheets.items() if p.kind is p.KEYWORD_ONLY] == list(SHEETS)
    assert inspect.signature(read_events).parameters["scale"].kind is inspect.Parameter.KEYWORD_ONLY


# Matches from the index


def test_matches_come_from_the_index_not_the_directory(tmp_path) -> None:
    rng = random.Random(101)
    listed, delisted = new_ids(rng, 2), new_ids(rng, 1)[0]
    write_folder(tmp_path, [match_entry(rng, g) for g in listed],
                 events={g: [] for g in [*listed, delisted]},
                 lineups={g: [] for g in [*listed, delisted]})
    frame, missing = read_matches(tmp_path, FOLDER)
    assert frame.sb_game_id.tolist() == listed and missing == []
    # A delisted file on disk is not a match anywhere in the reader.
    with pytest.raises(ValueError, match="not listed"):
        read_events(tmp_path, FOLDER, [delisted], scale=SCALE)
    with pytest.raises(ValueError, match="not listed"):
        read_team_sheets(tmp_path, FOLDER, [delisted], **SHEETS)
    with pytest.raises(ValueError, match="not listed"):
        list(iter_events(tmp_path, FOLDER, [delisted]))
    assert read_events(tmp_path, FOLDER, listed, scale=SCALE).empty


def test_an_index_that_lists_a_match_twice_is_refused(tmp_path) -> None:
    rng = random.Random(102)
    game_id = new_ids(rng, 1)[0]
    write_folder(tmp_path, [match_entry(rng, game_id), match_entry(rng, game_id)],
                 events={game_id: []}, lineups={game_id: []})
    with pytest.raises(ValueError, match="twice"):
        read_matches(tmp_path, FOLDER)


def test_a_listed_match_without_a_file_is_returned_as_missing_not_raised(tmp_path) -> None:
    rng = random.Random(103)
    both, no_events, no_lineup, neither = new_ids(rng, 4)
    write_folder(tmp_path, [match_entry(rng, g) for g in (both, no_events, no_lineup, neither)],
                 events={both: [], no_lineup: []}, lineups={both: [], no_events: []})
    frame, missing = read_matches(tmp_path, FOLDER)
    assert frame.sb_game_id.tolist() == [both]
    assert missing == [no_events, no_lineup, neither]
    # The opposite: every file present, nothing missing.
    (tmp_path / FOLDER / "events" / f"{no_events}.json").write_text("[]", encoding="utf-8")
    for game_id in (no_lineup, neither):
        (tmp_path / FOLDER / "_lineups" / f"{game_id}.json").write_text("[]", encoding="utf-8")
    (tmp_path / FOLDER / "events" / f"{neither}.json").write_text("[]", encoding="utf-8")
    frame, missing = read_matches(tmp_path, FOLDER)
    assert frame.sb_game_id.tolist() == [both, no_events, no_lineup, neither] and missing == []


def test_match_columns_and_dtypes(tmp_path) -> None:
    rng = random.Random(104)
    scored, unscored = new_ids(rng, 2)
    first = match_entry(rng, scored, home_score=3, away_score=0)
    second = match_entry(rng, unscored, home_score=None, away_score=None,
                         competition_stage=None, metadata=None)
    write_folder(tmp_path, [first, second], events={scored: [], unscored: []},
                 lineups={scored: [], unscored: []})
    frame, _ = read_matches(tmp_path, FOLDER)
    assert frame.columns.tolist() == [
        "sb_game_id", "folder", "date", "home_sb_team_id", "away_sb_team_id",
        "home_team_name", "away_team_name", "home_goals", "away_goals", "stage", "data_version"]
    assert {c: str(frame[c].dtype) for c in frame} == {
        "sb_game_id": "int64", "folder": "object", "date": "object",
        "home_sb_team_id": "int64", "away_sb_team_id": "int64", "home_team_name": "object",
        "away_team_name": "object", "home_goals": "Int64", "away_goals": "Int64",
        "stage": "object", "data_version": "object"}
    row, bare = frame.iloc[0], frame.iloc[1]
    assert (row.folder, row.date) == (FOLDER, first["match_date"])
    assert row.home_sb_team_id == first["home_team"]["home_team_id"]
    assert row.away_team_name == first["away_team"]["away_team_name"]
    assert (row.home_goals, row.away_goals) == (3, 0)
    assert row.stage == first["competition_stage"]["name"]
    assert row.data_version == first["metadata"]["data_version"]
    assert bare.home_goals is pd.NA and bare.away_goals is pd.NA
    assert bare.stage is None and bare.data_version is None


# Team sheets


def test_regulation_clipping_with_an_extra_time_spell_and_a_spell_from_90_plus_2(
        tmp_path) -> None:
    assert SHEETS["cap"] == 90, "the hand numbers below are for the frozen cap"
    sheets = one_sheet(tmp_path, 201, [
        [spell("Back", "00:00", "105:00", 1, 3)],                 # ends in extra time: cap
        [spell("Wing", "92:00", None, 2, None)],                  # 90+2: clipped to nothing
        [spell("Back", "60:00", "100:00", 2, 3),
         spell("Wing", "100:00", None, 3, None)],                 # the extra-time spell drops
        [spell("Back", "30:00", "95:00", 1, 2)],                  # a 95:00 end clips to 90
        [spell("Wing", "97:00", None, 3, None)],                  # extra time only: no row
        [spell("Back", "00:00", "70:00", 1, 2)],                  # nothing to clip
        # Invented clocks no match has: an end outside regulation runs to the cap
        # whatever its minute, and so does an end with no period.
        [spell("Back", "20:00", "30:00", 1, 3)],
        [spell("Back", "20:00", "30:00", 1, None)],
    ])
    assert sheets.index.tolist() == [0, 1, 2, 3, 5, 6, 7]
    assert sheets.minutes_regulation.tolist() == [90, 0, 30, 60, 70, 70, 70]
    assert sheets.minute_on.tolist() == [0, 90, 60, 30, 0, 20, 20]
    assert sheets.minute_off.tolist() == [90, 90, 90, 90, 70, 90, 90]


def test_a_spell_to_47_in_the_first_half_then_from_45_in_the_second_gives_the_cap(
        tmp_path) -> None:
    sheets = one_sheet(tmp_path, 202, [
        [spell("Back", "00:00", "47:00", 1, 1), spell("Back", "45:00", None, 2, None)],
        [spell("Back", "00:00", "44:00", 1, 1), spell("Back", "45:00", None, 2, None)],
    ])
    # 47 + 45 = 92, capped after summing; 44 + 45 = 89 is below the cap.
    assert sheets.minutes_regulation.tolist() == [90, 89]


def test_an_off_pitch_gap_lowers_minutes(tmp_path) -> None:
    sheets = one_sheet(tmp_path, 203, [
        [spell("Wing", "00:00", "30:00", 1, 1), spell("Wing", "34:00", None, 1, None)],
        [spell("Wing", "00:00", "30:00", 1, 1), spell("Back", "30:00", None, 1, None)],
    ])
    assert sheets.minutes_regulation.tolist() == [86, 90]


def test_started_is_a_spell_from_minute_zero_of_the_first_half(tmp_path) -> None:
    sheets = one_sheet(tmp_path, 204, [
        [spell("Back", "00:00", None, 1, None)],
        [spell("Back", "00:40", None, 1, None)],     # minute field 0: the shipped rule
        [spell("Back", "12:00", None, 1, None)],
        [spell("Back", "45:00", None, 2, None)],
        [spell("Back", "00:00", None, 2, None)],     # an invented clock: minute 0, period 2
    ])
    assert sheets.started.tolist() == [True, True, False, False, False]


def test_cautioned_is_any_card_and_dismissed_any_card_not_excluded(tmp_path) -> None:
    full = [spell("Back", "00:00", None, 1, None)]
    sheets = one_sheet(tmp_path, 205, [full] * 5,
                       [(), (YELLOW,), ("Second Yellow",), ("Red Card",), (YELLOW, YELLOW)])
    assert sheets.cautioned.tolist() == [False, True, True, True, True]
    assert sheets.dismissed.tolist() == [False, False, True, True, False]


def test_permanent_off_is_any_spell_whose_end_reason_holds_the_frozen_text(tmp_path) -> None:
    sheets = one_sheet(tmp_path, 206, [
        [spell("Back", "00:00", "61:00", 1, 2, f"Off ({PERMANENT})")],
        [spell("Back", "00:00", "20:00", 1, 1, f"Off - {PERMANENT}"),
         spell("Wing", "20:00", None, 1, None)],
        [spell("Back", "00:00", "61:00", 1, 2, "Invented Replacement")],
        [spell("Back", "00:00", None, 1, None, None)],
    ])
    assert sheets.permanent_off.tolist() == [True, True, False, False]


def test_goalkeeper_is_the_position_of_the_modal_spell_and_a_tie_goes_to_the_earliest(
        tmp_path) -> None:
    sheets = one_sheet(tmp_path, 207, [
        [spell(GOALKEEPER, "00:00", "30:00", 1, 1), spell("Back", "30:00", None, 1, None)],
        [spell(GOALKEEPER, "00:00", "60:00", 1, 2), spell("Back", "60:00", None, 2, None)],
        [spell(GOALKEEPER, "00:00", "45:00", 1, 1), spell("Back", "45:00", None, 2, None)],
        [spell("Back", "00:00", "45:00", 1, 1), spell(GOALKEEPER, "45:00", None, 2, None)],
        # Listed out of time order: earliest is the first-half spell, not the first listed.
        [spell(GOALKEEPER, "45:00", None, 2, None), spell("Back", "00:00", "45:00", 1, 1)],
        # Extra-time minutes are not regulation minutes.
        [spell("Back", "00:00", "50:00", 1, 2), spell(GOALKEEPER, "50:00", "100:00", 2, 3),
         spell(GOALKEEPER, "100:00", None, 3, None)],
    ])
    assert sheets.is_goalkeeper.tolist() == [False, True, True, False, False, False]


def test_sheet_columns_dtypes_and_one_row_per_player_with_a_regulation_spell(tmp_path) -> None:
    rng = random.Random(208)
    game_id, home, away, *players = new_ids(rng, 8)
    lineup_home = [
        sheet_player(rng, players[0], [spell("Back", "00:00", None, 1, None)]),
        sheet_player(rng, players[1], [], nickname=False),   # unused substitute: no spell
        sheet_player(rng, players[2], [spell("Wing", "70:00", None, 2, None)], nickname=False,
                     country=False),
    ]
    lineup_away = [sheet_player(rng, players[3], [spell(GOALKEEPER, "00:00", None, 1, None)]),
                   sheet_player(rng, players[4], [spell("Wing", "106:00", None, 3, None)])]
    write_folder(tmp_path, [match_entry(rng, game_id)], events={game_id: []},
                 lineups={game_id: [{"team_id": home, "team_name": invented(rng),
                                     "lineup": lineup_home},
                                    {"team_id": away, "team_name": invented(rng),
                                     "lineup": lineup_away}]})
    sheets = read_team_sheets(tmp_path, FOLDER, [game_id], **SHEETS)
    assert sheets.columns.tolist() == [
        "sb_game_id", "sb_team_id", "sb_player_id", "player_name", "player_nickname", "country",
        "started", "minutes_regulation", "minute_on", "minute_off", "is_goalkeeper",
        "cautioned", "dismissed", "permanent_off"]
    assert {c: str(sheets[c].dtype) for c in sheets} == {
        "sb_game_id": "int64", "sb_team_id": "int64", "sb_player_id": "int64",
        "player_name": "object", "player_nickname": "object", "country": "object",
        "started": "bool", "minutes_regulation": "int64", "minute_on": "int64",
        "minute_off": "int64", "is_goalkeeper": "bool", "cautioned": "bool",
        "dismissed": "bool", "permanent_off": "bool"}
    assert sheets.sb_player_id.tolist() == [players[0], players[2], players[3]]
    assert sheets.sb_team_id.tolist() == [home, home, away]
    assert sheets.sb_game_id.tolist() == [game_id] * 3
    assert sheets.player_name.tolist() == [lineup_home[0]["player_name"],
                                           lineup_home[2]["player_name"],
                                           lineup_away[0]["player_name"]]
    assert sheets.player_nickname.tolist() == [lineup_home[0]["player_nickname"], None,
                                               lineup_away[0]["player_nickname"]]
    assert sheets.country.tolist() == [lineup_home[0]["country"]["name"], None,
                                       lineup_away[0]["country"]["name"]]
    assert sheets.minutes_regulation.tolist() == [90, 20, 90]
    assert sheets.is_goalkeeper.tolist() == [False, False, True]


# Events


def test_pass_type_and_shot_type_are_read_from_a_hand_built_match(tmp_path) -> None:
    assert {None, "Corner", "Kick Off"} <= set(CONFIG["sb_known_pass_types"])
    assert {"Open Play", "Penalty"} <= set(CONFIG["sb_known_shot_types"])
    assert "Tackle" in CONFIG["sb_known_duel_types"]
    rng = random.Random(301)
    game_id, team, player = new_ids(rng, 3)
    match = Events(rng, team)
    match.add("Half Start")
    match.add("Pass", player=player, location=match.point(),
              **{"pass": {"end_location": match.point(), "height": {"name": "Low"}}})
    match.add("Pass", player=player, location=match.point(),
              **{"pass": {"end_location": match.point(), "type": {"name": "Corner"},
                          "height": {"name": "High"}, "cross": True, "shot_assist": True,
                          "outcome": {"name": "Invented Miss"}}})
    match.add("Shot", player=player, location=match.point(),
              shot={"end_location": [*match.point(), 1.5], "type": {"name": "Open Play"},
                    "outcome": {"name": "Goal"}})
    match.add("Shot", player=player, location=match.point(),
              shot={"end_location": match.point(), "type": {"name": "Penalty"}})
    match.add("Duel", player=player, location=match.point(),
              duel={"type": {"name": "Tackle"}, "outcome": {"name": "Invented Won"}})
    match.add("Pass", player=player, location=match.point(),
              **{"pass": {"end_location": match.point(), "type": {"name": "Kick Off"},
                          "goal_assist": True}})
    match.add("Goal Keeper", player=player, location=match.point(),
              goalkeeper={"outcome": {"name": "Invented Save"}})
    match.add("Ball Receipt*", player=player, location=match.point(),
              ball_receipt={"outcome": {"name": "Invented Loss"}})
    match.add("50/50", player=player, location=match.point(),
              **{"50_50": {"outcome": {"name": "Invented Draw"}}})
    match.add("Pressure", player=player, location=match.point())
    write_folder(tmp_path, [match_entry(rng, game_id)], events={game_id: match.rows},
                 lineups={game_id: []})
    events = read_events(tmp_path, FOLDER, [game_id], scale=SCALE)
    assert events.kind.tolist() == [row["type"]["name"] for row in match.rows]
    assert events.pass_type.tolist() == [None, None, "Corner", None, None, None, "Kick Off",
                                         None, None, None, None]
    assert events.shot_type.tolist() == [None, None, None, "Open Play", "Penalty", None, None,
                                         None, None, None, None]
    assert events.duel_type.tolist() == [None] * 5 + ["Tackle"] + [None] * 5
    assert events.pass_height.tolist() == [None, "Low", "High"] + [None] * 8
    assert events.pass_cross.tolist() == [False, False, True] + [False] * 8
    assert events.shot_assist.tolist() == [False, False, True] + [False] * 8
    assert events.goal_assist.tolist() == [False] * 6 + [True] + [False] * 4
    # The detail object of each kind, under the provider's key for it.
    assert events.has_outcome.tolist() == [False, False, True, True, False, True, False,
                                           True, True, True, False]
    assert events.outcome.tolist() == [
        None, None, "Invented Miss", "Goal", None, "Invented Won", None, "Invented Save",
        "Invented Loss", "Invented Draw", None]
    assert events.play_pattern.tolist() == ["Invented Pattern"] * 11
    assert events.event_id.tolist() == [row["id"] for row in match.rows]
    assert events.event_order.tolist() == list(range(1, 12))


def test_events_without_location_are_kept_with_nan_and_an_end_is_never_the_start(
        tmp_path) -> None:
    rng = random.Random(302)
    game_id, team, player = new_ids(rng, 3)
    match = Events(rng, team)
    match.add("Half Start")                                               # no location
    match.add("Pressure", player=player, location=match.point())         # no end by kind
    match.add("Pass", player=player, location=match.point(), **{"pass": {}})  # no end_location
    match.add("Carry", player=player, location=match.point(),
              carry={"end_location": match.point()})
    match.add("Shot", player=player, location=match.point(),
              shot={"end_location": [*match.point(), 2.25], "type": {"name": "Open Play"}})
    match.add("Pass", player=player, **{"pass": {"end_location": match.point()}})  # no start
    match.add("Injury Stoppage")                                          # no player either
    write_folder(tmp_path, [match_entry(rng, game_id)], events={game_id: match.rows},
                 lineups={game_id: []})

    def scaled(value: float | None, by: float) -> float:
        return np.nan if value is None else float(Fraction(value) / Fraction(by))

    for scale in (SCALE, [100, 50]):
        events = read_events(tmp_path, FOLDER, [game_id], scale=scale)
        assert len(events) == len(match.rows), "nothing is dropped"
        for column, axis, by in (("start_x", 0, scale[0]), ("start_y", 1, scale[1])):
            expected = [scaled(row["location"][axis] if "location" in row else None, by)
                        for row in match.rows]
            np.testing.assert_array_equal(events[column].to_numpy(), expected)
        ends = [None, None, None, match.rows[3]["carry"]["end_location"],
                match.rows[4]["shot"]["end_location"], match.rows[5]["pass"]["end_location"],
                None]
        for column, axis, by in (("end_x", 0, scale[0]), ("end_y", 1, scale[1])):
            expected = [scaled(None if end is None else end[axis], by) for end in ends]
            np.testing.assert_array_equal(events[column].to_numpy(), expected)
    assert events.sb_player_id.isna().tolist() == [True, False, False, False, False, False, True]
    assert events.sb_player_id.dropna().tolist() == [player] * 5
    assert events.sb_team_id.tolist() == [team] * 7


def test_period_seconds_come_from_the_timestamp_which_restarts_each_period(tmp_path) -> None:
    rng = random.Random(303)
    game_id, team = new_ids(rng, 2)
    stamps = [(1, "00:00:00.000"), (1, "00:47:12.345"), (2, "00:00:03.100"),
              (2, "00:51:59.999"), (3, "00:09:00.001"), (4, "01:02:03.004")]
    match = Events(rng, team)
    for period, stamp in stamps:
        match.add("Invented Kind", period=period, timestamp=stamp)
    write_folder(tmp_path, [match_entry(rng, game_id)], events={game_id: match.rows},
                 lineups={game_id: []})
    events = read_events(tmp_path, FOLDER, [game_id], scale=SCALE)

    def by_hand(stamp: str) -> float:
        hours, minutes, seconds = stamp.split(":")
        return float(Fraction(int(hours) * 3600 + int(minutes) * 60) + Fraction(seconds))

    assert events.period.tolist() == [period for period, _ in stamps]
    assert events.period_seconds.tolist() == [by_hand(stamp) for _, stamp in stamps]
    # Not the minute and second fields, which the builder sets to something else.
    assert events.period_seconds.tolist() != [
        60.0 * row["minute"] + row["second"] for row in match.rows]


def test_a_malformed_timestamp_is_refused(tmp_path) -> None:
    rng = random.Random(304)
    game_id, team = new_ids(rng, 2)
    match = Events(rng, team)
    match.add("Invented Kind", timestamp="12:34")
    write_folder(tmp_path, [match_entry(rng, game_id)], events={game_id: match.rows},
                 lineups={game_id: []})
    with pytest.raises(ValueError, match="timestamp"):
        read_events(tmp_path, FOLDER, [game_id], scale=SCALE)


def test_event_columns_and_dtypes(tmp_path) -> None:
    rng = random.Random(305)
    game_id, team, player = new_ids(rng, 3)
    match = Events(rng, team)
    match.add("Pass", player=player, location=match.point(),
              **{"pass": {"end_location": match.point()}})
    match.add("Half End")
    write_folder(tmp_path, [match_entry(rng, game_id)], events={game_id: match.rows},
                 lineups={game_id: []})
    events = read_events(tmp_path, FOLDER, [game_id], scale=SCALE)
    expected = {
        "sb_game_id": "int64", "period": "int8", "period_seconds": "float64",
        "event_order": "int64", "sb_team_id": "int64", "sb_player_id": "Int64",
        "kind": "object", "start_x": "float64", "start_y": "float64", "end_x": "float64",
        "end_y": "float64", "has_outcome": "bool", "outcome": "object", "pass_type": "object",
        "pass_height": "object", "pass_cross": "bool", "shot_assist": "bool",
        "goal_assist": "bool", "shot_type": "object", "duel_type": "object",
        "play_pattern": "object", "event_id": "object"}
    assert events.columns.tolist() == list(expected)
    assert {c: str(events[c].dtype) for c in events} == expected
    empty = read_events(tmp_path, FOLDER, [], scale=SCALE)
    assert empty.empty and {c: str(empty[c].dtype) for c in empty} == expected


def test_scale_is_two_positive_numbers(tmp_path) -> None:
    rng = random.Random(306)
    game_id = new_ids(rng, 1)[0]
    write_folder(tmp_path, [match_entry(rng, game_id)], events={game_id: []},
                 lineups={game_id: []})
    for scale in ([120], [120, 0], [120, 80, 1], [float("nan"), 80]):
        with pytest.raises(ValueError, match="scale"):
            read_events(tmp_path, FOLDER, [game_id], scale=scale)


def test_iter_events_streams_raw_lists_one_listed_match_at_a_time(tmp_path) -> None:
    rng = random.Random(307)
    first, second, team = sorted(new_ids(rng, 2)) + new_ids(rng, 1)
    lists = {}
    for game_id in (first, second):
        match = Events(rng, team)
        for _ in range(rng.randint(2, 5)):
            match.add("Invented Kind")
        lists[game_id] = match.rows
    write_folder(tmp_path, [match_entry(rng, second), match_entry(rng, first)], events=lists,
                 lineups={first: [], second: []})
    streamed = iter_events(tmp_path, FOLDER, [second, first, second])
    assert next(streamed) == (first, lists[first])
    assert list(streamed) == [(second, lists[second])]


# Vocabulary


def vocabulary_folder(root: Path, seed: int, shot_without_type: bool) -> dict:
    rng = random.Random(seed)
    first, second, unread, delisted, team, player = new_ids(rng, 6)
    one, two = Events(rng, team), Events(rng, team)
    for _ in range(3):
        one.add("Pass", player=player, location=one.point(), **{"pass": {}})
    one.add("Pass", player=player, location=one.point(), **{"pass": {"type": {"name": "Corner"}}})
    one.add("Carry", player=player, location=one.point(), carry={})
    one.add("Pressure", player=player, location=one.point())
    two.add("Shot", player=player, location=two.point(), shot={"type": {"name": "Open Play"}})
    two.add("Shot", player=player, location=two.point(),
            shot={} if shot_without_type else {"type": {"name": "Penalty"}})
    two.add("Duel", player=player, location=two.point(), duel={"type": {"name": "Tackle"}})
    stray = Events(rng, team)
    stray.add("Invented Unknown Kind")
    write_folder(root, [match_entry(rng, g) for g in (first, second, unread)],
                 events={first: one.rows, second: two.rows, delisted: stray.rows},
                 lineups={first: [], second: []})
    return {"first": first, "one": one}


def test_folder_vocabulary_returns_names_by_kind_and_none_for_a_missing_type(tmp_path) -> None:
    vocabulary_folder(tmp_path, 401, shot_without_type=True)
    vocabulary = folder_vocabulary(tmp_path, FOLDER)
    assert vocabulary == {
        "kind": ["Carry", "Duel", "Pass", "Pressure", "Shot"],
        "pass_type": [None, "Corner"],
        "shot_type": [None, "Open Play"],
        # Carries, passes, pressures and shots carry no duel type, and add no None.
        "duel_type": ["Tackle"],
    }


def test_folder_vocabulary_has_no_none_when_every_shot_is_typed(tmp_path) -> None:
    vocabulary_folder(tmp_path, 402, shot_without_type=False)
    vocabulary = folder_vocabulary(tmp_path, FOLDER)
    assert vocabulary["shot_type"] == ["Open Play", "Penalty"]
    assert vocabulary["pass_type"] == [None, "Corner"]


def test_folder_vocabulary_holds_no_counts(tmp_path) -> None:
    built = vocabulary_folder(tmp_path, 403, shot_without_type=True)
    before = folder_vocabulary(tmp_path, FOLDER)
    path = tmp_path / FOLDER / "events" / f"{built['first']}.json"
    path.write_text(json.dumps(built["one"].rows * 4), encoding="utf-8")
    after = folder_vocabulary(tmp_path, FOLDER)
    assert after == before
    for names in after.values():
        assert all(name is None or isinstance(name, str) for name in names)
        assert len(names) == len(set(names))


# Folder manifest


def manifest_folder(root: Path, seed: int) -> dict:
    """A listed match with both files, one with events only, one with a lineup only,
    and a match on disk that the index does not list."""
    rng = random.Random(seed)
    # One six-digit and two seven-digit ids, so string order is not numeric order.
    both = rng.randrange(100_000, 1_000_000)
    events_only, lineup_only, delisted = (rng.randrange(1_000_000, 10_000_000) for _ in "abc")
    shared = {"data_version": "7.0.1", "shot_fidelity_version": "3"}
    index = [match_entry(rng, both, metadata=shared),
             match_entry(rng, events_only, metadata=dict(reversed(list(shared.items())))),
             match_entry(rng, lineup_only, metadata={"data_version": "7.0.1"})]
    content = {g: [{"invented": invented(rng), "n": rng.random()}] for g in
               (both, events_only, lineup_only, delisted)}
    write_folder(root, index,
                 events={both: content[both], events_only: content[events_only],
                         delisted: content[delisted]},
                 lineups={both: content[both], lineup_only: content[lineup_only],
                          delisted: content[delisted]})
    return {"both": both, "events_only": events_only, "lineup_only": lineup_only,
            "delisted": delisted, "shared": shared}


def lines_by_hand(root: Path, relatives: list[str]) -> list[str]:
    """``<path>:<sha256>`` per file, sorted as strings."""
    return sorted(f"{relative}:{hashlib.sha256((root / relative).read_bytes()).hexdigest()}"
                  for relative in relatives)


def test_folder_manifest_is_the_digest_of_section_2_by_hand(tmp_path) -> None:
    ids = manifest_folder(tmp_path, 501)
    # The listed files on disk, and nothing else: no line for the absent lineup of
    # events_only or the absent events of lineup_only, none for the delisted match.
    hashed = [f"{FOLDER}/_matches.json", f"{FOLDER}/events/{ids['both']}.json",
              f"{FOLDER}/events/{ids['events_only']}.json",
              f"{FOLDER}/_lineups/{ids['both']}.json",
              f"{FOLDER}/_lineups/{ids['lineup_only']}.json"]
    lines = lines_by_hand(tmp_path, hashed)
    size = sum(len((tmp_path / relative).read_bytes()) for relative in hashed)
    manifest = folder_manifest(tmp_path, FOLDER)
    assert manifest["digest"] == hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    # The opposite: the same lines with a trailing newline are another digest.
    assert manifest["digest"] != hashlib.sha256(
        ("\n".join(lines) + "\n").encode("utf-8")).hexdigest()
    assert {k: manifest[k] for k in ("folder", "event_files", "lineup_files", "bytes")} == {
        "folder": FOLDER, "event_files": 2, "lineup_files": 2, "bytes": size}
    assert sorted(manifest) == sorted(
        ["folder", "event_files", "lineup_files", "bytes", "data_versions", "digest"])
    versions = sorted(((json.loads(key), count) for key, count
                       in manifest["data_versions"].items()), key=lambda pair: pair[1])
    assert versions == [({"data_version": "7.0.1"}, 1), (ids["shared"], 2)]


def test_folder_manifest_agrees_with_the_fetch_script(tmp_path) -> None:
    manifest_folder(tmp_path, 502)
    fetch = load_script("fetch_statsbomb_double_coded",
                        ROOT / "scripts" / "fetch_statsbomb_double_coded.py")
    digest, listed, event_files, lineup_files = fetch.folder_digest(tmp_path, FOLDER)
    manifest = folder_manifest(tmp_path, FOLDER)
    assert (manifest["digest"], manifest["event_files"], manifest["lineup_files"]) == (
        digest, event_files, lineup_files)
    assert listed == sum(manifest["data_versions"].values()) == 3


def test_folder_manifest_changes_with_one_byte_and_ignores_unlisted_files(tmp_path) -> None:
    ids = manifest_folder(tmp_path, 503)
    before = folder_manifest(tmp_path, FOLDER)["digest"]
    # A file the index does not list: any change to it leaves the digest alone.
    stray = tmp_path / FOLDER / "events" / f"{ids['delisted']}.json"
    stray.write_bytes(stray.read_bytes() + b" ")
    (tmp_path / FOLDER / "events" / "not-a-match.json").write_text("[]", encoding="utf-8")
    assert folder_manifest(tmp_path, FOLDER)["digest"] == before
    # One byte of one listed file, same length: the digest changes, and returns with it.
    listed = tmp_path / FOLDER / "_lineups" / f"{ids['both']}.json"
    original = listed.read_bytes()
    flipped = bytearray(original)
    flipped[len(flipped) // 2] ^= 0x01
    listed.write_bytes(bytes(flipped))
    assert folder_manifest(tmp_path, FOLDER)["digest"] != before
    listed.write_bytes(original)
    assert folder_manifest(tmp_path, FOLDER)["digest"] == before
    # A listed file that was absent and now exists adds its line.
    absent = tmp_path / FOLDER / "_lineups" / f"{ids['events_only']}.json"
    absent.write_text("[]", encoding="utf-8")
    after = folder_manifest(tmp_path, FOLDER)
    assert after["digest"] != before and after["lineup_files"] == 3


# Boundaries


def test_no_reader_opens_a_file_outside_its_folder(tmp_path, monkeypatch) -> None:
    """Every file opened is the index, an event file or a lineup file of the folder."""
    rng = random.Random(601)
    game_id, team, player = new_ids(rng, 3)
    match = Events(rng, team)
    match.add("Pass", player=player, location=match.point(), **{"pass": {}})
    lineup = [{"team_id": team, "team_name": invented(rng), "lineup": [
        sheet_player(rng, player, [spell("Back", "00:00", None, 1, None)])]}]
    write_folder(tmp_path, [match_entry(rng, game_id)], events={game_id: match.rows},
                 lineups={game_id: lineup})
    write_folder(tmp_path, [match_entry(rng, game_id)], events={game_id: match.rows},
                 lineups={game_id: lineup}, folder="Neighbour")
    opened: list[Path] = []
    original = Path.open

    def recording(self, *args, **kwargs):
        opened.append(Path(self))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", recording)
    read_matches(tmp_path, FOLDER)
    read_team_sheets(tmp_path, FOLDER, [game_id], **SHEETS)
    read_events(tmp_path, FOLDER, [game_id], scale=SCALE)
    folder_vocabulary(tmp_path, FOLDER)
    folder_manifest(tmp_path, FOLDER)
    monkeypatch.undo()
    allowed = {tmp_path / FOLDER / "_matches.json", tmp_path / FOLDER / "events" /
               f"{game_id}.json", tmp_path / FOLDER / "_lineups" / f"{game_id}.json"}
    assert opened and set(opened) == allowed


def test_the_module_and_this_test_pass_the_licence_guard() -> None:
    guard = load_script("check_licensing", ROOT / "scripts" / "check_licensing.py")
    files = [ROOT / "galactico" / "validation" / "sb_reader.py", Path(__file__).resolve()]
    assert guard.check(files) == []


def test_statsbomb_provider_competitions_are_unchanged(tmp_path) -> None:
    """The shipped adapter still lists the four 2015/16 leagues only: the double-coded
    folders and the reference folder beside them are not picked up."""
    assert SEASONS == ("La_Liga", "Premier_League", "Serie_A", "Ligue_1")
    for folder in [*SEASONS, "World_Cup_2018", "La_Liga_2017_18", FOLDER]:
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "_matches.json").write_text("[]", encoding="utf-8")
    assert tuple(StatsBombProvider(tmp_path).competitions()) == SEASONS
