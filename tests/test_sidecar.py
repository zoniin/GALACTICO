"""The tag sidecar restores provider facts, joins on ``event_id`` and reinterprets nothing.

Synthetic raw events are built with keyword dicts: a double-quoted provider key followed
by a colon in a committed file is what the licence guard refuses, and the first test holds
this file, the module and the build script to that.

Every synthetic event below is a raw-shaped mapping, not a neutral frame row, so the traps
of the neutral schema are met in raw form: an event with no accuracy tag (the null
``success``), a player id of 0, and types that are not passes (duel, foul, save, shot, set
piece, offside). The provider's ``MD`` position code lives in the players table, which the
sidecar never reads.

The truth tables are typed here from the tag table of the specification, not read from the
module, so a wrong constant in the module cannot agree with itself.
"""

from __future__ import annotations

import dataclasses
import gc
import hashlib
import importlib.util
import inspect
import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pytest

from galactico.ingestion import sidecar
from galactico.match_lab.service import _enrich
from galactico.optimization.historical import frame_hash
from galactico.providers.base import PROVIDERS, LicenseViolation
from galactico.providers.pappalardo import PappalardoProvider

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "galactico" / "ingestion" / "sidecar.py"
SCRIPT = ROOT / "scripts" / "build_sidecar.py"

# The interface of the specification, name by name.
INTERFACE = [
    "SIDECAR_SCHEMA_VERSION", "TAG_MAPPING_VERSION", "RAW_ROOT", "SIDECAR_ROOT", "TABLES",
    "SORT_KEYS", "LIVE_TAGS", "DEAD_TAGS", "GOAL_ZONE", "SidecarMissing", "SidecarStale",
    "SidecarMismatch", "SidecarManifest", "iter_raw_events", "event_row", "event_frame",
    "match_frame", "squad_frame", "shot_outcome", "content_hash", "write_sidecar", "manifest",
    "load", "verify", "attach", "provenance",
]

EVENT_COLUMNS = [
    "event_id", "game_id", "sub_event_id", "n_positions", "start_at_corner", "end_at_corner",
    "player_attributed", "shootout", "tags", "goal_on_scoring_event", "own_goal", "opportunity",
    "body_part", "free_space", "take_on", "anticipated", "anticipation", "duel_outcome", "high",
    "through", "fairplay", "fk_direct", "goal_zone", "goal_zone_class", "feint", "missed_ball",
    "sliding_tackle", "card", "blocked", "shot_family", "shot_outcome",
]
MATCH_COLUMNS = [
    "game_id", "competition", "date_utc", "gameweek", "home_team_id", "away_team_id",
    "home_score", "away_score", "home_score_ht", "away_score_ht", "winner_team_id",
    "winner_agrees_with_score", "duration", "home_coach_id", "away_coach_id",
]
SQUAD_COLUMNS = [
    "game_id", "team_id", "player_id", "role", "minute_on", "minute_off", "yellow_minute",
    "red_minute", "subs_recorded",
]
ANOMALY_KEYS = {
    "events_without_position", "multi_body_part", "multi_duel_outcome", "multi_goal_zone",
    "unknown_tag_ids", "sub_in_unattributed", "sub_out_not_starter",
    "subs_not_recorded_team_matches", "winner_disagrees_with_score",
}

# Every named tag column at rest: what an event says when it carries none of the tags.
OFF = dict(
    goal_on_scoring_event=False, own_goal=False, opportunity=False, body_part=None,
    free_space=False, take_on=False, anticipated=False, anticipation=False, duel_outcome=None,
    high=False, through=False, fairplay=False, fk_direct=None, goal_zone=None,
    goal_zone_class=None, feint=False, missed_ball=False, sliding_tackle=False, card=None,
    blocked=False,
)
ZONES = {
    1201: "gb", 1202: "gbr", 1203: "gc", 1204: "gl", 1205: "glb", 1206: "gr", 1207: "gt",
    1208: "gtl", 1209: "gtr", 1210: "obr", 1211: "ol", 1212: "olb", 1213: "or", 1214: "ot",
    1215: "otl", 1216: "otr", 1217: "pbr", 1218: "pl", 1219: "plb", 1220: "pr", 1221: "pt",
    1222: "ptl", 1223: "ptr",
}
ZONE_CLASS = {
    **dict.fromkeys(range(1201, 1210), "in_frame"),
    **dict.fromkeys(range(1210, 1217), "out"),
    **dict.fromkeys(range(1217, 1224), "post"),
}
# What one tag, alone on a pass, switches on. Everything else must stay at rest.
ON = {
    101: dict(goal_on_scoring_event=True),
    102: dict(own_goal=True),
    201: dict(opportunity=True),
    401: dict(body_part="left_foot"),
    402: dict(body_part="right_foot"),
    403: dict(body_part="head_or_body"),
    501: dict(free_space=True),
    502: dict(free_space=True),
    503: dict(take_on=True),
    504: dict(take_on=True),
    601: dict(anticipated=True),
    602: dict(anticipation=True),
    701: dict(duel_outcome="lost"),
    702: dict(duel_outcome="neutral"),
    703: dict(duel_outcome="won"),
    801: dict(high=True),
    901: dict(through=True),
    1001: dict(fairplay=True),
    1101: dict(fk_direct=True),
    1102: dict(fk_direct=False),
    **{tag: dict(goal_zone=ZONES[tag], goal_zone_class=ZONE_CLASS[tag]) for tag in ZONES},
    1301: dict(feint=True),
    1302: dict(missed_ball=True),
    1601: dict(sliding_tackle=True),
    1701: dict(card="red_card"),
    1702: dict(card="yellow_card"),
    1703: dict(card="second_yellow"),
    2101: dict(blocked=True),
}
# Tags the neutral frame already carries as columns: no second named column, only `tags`.
CARRIED_BY_ACTIONS = (301, 302, 1401, 1801, 1802, 1901, 2001)
DEAD = (802, 1501)
OUTCOMES = {"goal", "blocked", "woodwork", "off_target", "on_target_not_goal", "not_goal"}


# --------------------------------------------------------------------- builders

def raw_event(**over):
    base = dict(id=1, eventId=8, subEventId=85, matchId=7, teamId=10, playerId=3,
                matchPeriod="1H", eventSec=1.0,
                positions=[dict(x=50, y=50), dict(x=60, y=50)], tags=[dict(id=1801)])
    return {**base, **over}


def tagged(*ids: int, **over) -> dict:
    return raw_event(tags=[dict(id=tag) for tag in ids], **over)


def shot(*ids: int, **over) -> dict:
    return tagged(*ids, eventId=10, subEventId=100, **over)


def sheet_player(player: int, yellow: str = "0", red: str = "0") -> dict:
    return dict(playerId=player, goals="null", ownGoals="0", yellowCards=yellow, redCards=red)


def swap(player_in: int, player_out: int, minute: int) -> dict:
    return dict(playerIn=player_in, playerOut=player_out, minute=minute)


def sheet_side(team: int, side: str, score: int, half: int, lineup, bench, subs,
               coach: int = 0) -> dict:
    as_entry = [p if isinstance(p, dict) else sheet_player(p) for p in lineup]
    on_bench = [p if isinstance(p, dict) else sheet_player(p) for p in bench]
    return dict(teamId=team, side=side, score=score, scoreHT=half, scoreET=0, scoreP=0,
                coachId=coach, hasFormation=1,
                formation=dict(lineup=as_entry, bench=on_bench, substitutions=subs))


def raw_match(game_id: int, home: dict, away: dict, winner: int, **over) -> dict:
    base = dict(wyId=game_id, dateutc="2018-01-06 15:15:00", gameweek=18, winner=winner,
                duration="Regular", status="Played", label="Home - Away, 9 - 9", venue="",
                referees=[], teamsData={str(home["teamId"]): home, str(away["teamId"]): away})
    return {**base, **over}


def plain_match(game_id: int = 7, home: int = 10, away: int = 20) -> dict:
    return raw_match(
        game_id,
        sheet_side(home, "home", 2, 1, range(101, 112), [112, 113], [swap(112, 101, 60)]),
        sheet_side(away, "away", 1, 0, range(201, 212), [212], []),
        winner=home,
    )


def small_events() -> list[dict]:
    return [
        raw_event(id=11),
        tagged(703, 1801, 504, id=12, eventId=1, subEventId=11, playerId=0),
        tagged(1702, id=13, eventId=2, subEventId=20, positions=[dict(x=30, y=40)]),
        shot(101, 402, 1203, 1801, 201, id=14),
        tagged(101, 1203, 1802, id=15, eventId=9, subEventId=90,
               positions=[dict(x=0, y=0), dict(x=100, y=100)]),
        tagged(1101, 401, 2101, 1802, id=16, eventId=3, subEventId=33),
        tagged(id=17, eventId=6, subEventId=""),
        tagged(102, id=18, eventId=7, subEventId=72),
        raw_event(id=19, positions=[]),
    ]


def write_raw(root: Path, competition: str, events, matches) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / f"events_{competition}.json").write_text(json.dumps(list(events)), encoding="utf-8")
    (root / f"matches_{competition}.json").write_text(
        json.dumps(list(matches)), encoding="utf-8")
    return root


def build(tmp_path: Path, events=None, matches=None, competition: str = "Spain", **kwargs):
    """A sidecar under ``tmp_path`` from synthetic raw files; never looks at the real corpus."""
    raw = write_raw(tmp_path / "raw", competition,
                    small_events() if events is None else events,
                    [plain_match()] if matches is None else matches)
    kwargs.setdefault("actions_path", tmp_path / "no-actions.parquet")
    made = sidecar.write_sidecar(competition, raw_root=raw, out_root=tmp_path / "v1", **kwargs)
    return made, tmp_path / "v1"


def plain(value):
    """A cell as a Python value: NaN and NA are None, an array is a list."""
    if isinstance(value, np.ndarray):
        return [int(item) for item in value]
    if value is None or value is pd.NA or (isinstance(value, float) and np.isnan(value)):
        return None
    return value.item() if isinstance(value, np.generic) else value


def records(frame: pd.DataFrame) -> list[dict]:
    return [{name: plain(row[name]) for name in frame.columns}
            for row in frame.to_dict("records")]


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_of_files(directory: Path) -> dict[str, str]:
    return {path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file()}


# ------------------------------------------------------------------- the guard

def test_module_and_test_pass_the_licence_guard(tmp_path, monkeypatch):
    guard = load_script("check_licensing", ROOT / "scripts" / "check_licensing.py")
    assert guard.check([MODULE, Path(__file__).resolve(), SCRIPT]) == []
    # The check bites: the raw event of this file, written with its key quoted, is refused.
    key = "event" + "Id"
    planted = tmp_path / "planted.py"
    planted.write_text(f'event = {{"{key}": 8}}\n', encoding="utf-8")
    monkeypatch.setattr(guard, "REPO", tmp_path)
    assert any("Wyscout event data" in problem for problem in guard.check([planted]))


def test_the_interface_is_the_specified_one():
    assert sorted(sidecar.__all__) == sorted(INTERFACE)
    assert all(hasattr(sidecar, name) for name in INTERFACE)
    assert sidecar.SIDECAR_SCHEMA_VERSION == "wyscout-tag-sidecar-v1"
    assert sidecar.TAG_MAPPING_VERSION == "wyscout-v2-tags2name-57live-v1"
    assert sidecar.TABLES == ("events", "matches", "squads")
    assert sidecar.SORT_KEYS == {"events": ("event_id",), "matches": ("game_id",),
                                 "squads": ("game_id", "team_id", "player_id")}
    assert ROOT / "data/public/pappalardo" == sidecar.RAW_ROOT
    assert ROOT / "data/public/sidecar/pappalardo/v1" == sidecar.SIDECAR_ROOT
    assert issubclass(sidecar.SidecarMissing, FileNotFoundError)
    assert issubclass(sidecar.SidecarStale, RuntimeError)
    assert issubclass(sidecar.SidecarMismatch, RuntimeError)
    assert frozenset({802, 1501}) == sidecar.DEAD_TAGS
    assert len(sidecar.LIVE_TAGS) == 57 and not sidecar.LIVE_TAGS & sidecar.DEAD_TAGS
    assert set(ON) | set(CARRIED_BY_ACTIONS) == sidecar.LIVE_TAGS
    assert ZONES == sidecar.GOAL_ZONE

    def shape(function):
        parameters = inspect.signature(function).parameters.values()
        return ([p.name for p in parameters if p.kind is p.POSITIONAL_OR_KEYWORD],
                [p.name for p in parameters if p.kind is p.KEYWORD_ONLY])

    assert shape(sidecar.iter_raw_events) == (["path"], [])
    assert shape(sidecar.event_row) == (["event"], [])
    assert shape(sidecar.event_frame) == (["events"], [])
    assert shape(sidecar.match_frame) == (["matches", "competition"], [])
    assert shape(sidecar.squad_frame) == (["matches"], [])
    assert shape(sidecar.shot_outcome) == (["tags"], [])
    assert shape(sidecar.content_hash) == (["frame", "table"], [])
    assert shape(sidecar.write_sidecar) == (["competition"],
                                            ["raw_root", "out_root", "actions_path"])
    assert shape(sidecar.manifest) == (["competition"], ["root"])
    assert shape(sidecar.load) == (["competition", "table"], ["columns", "root"])
    assert shape(sidecar.verify) == (["competition"], ["root"])
    assert shape(sidecar.attach) == (["actions", "events", "columns"], [])
    assert shape(sidecar.provenance) == (["competition"], ["root"])
    build_defaults = inspect.signature(sidecar.write_sidecar).parameters
    assert [build_defaults[name].default for name in ("raw_root", "out_root", "actions_path")] == [
        sidecar.RAW_ROOT, sidecar.SIDECAR_ROOT, None]
    for reader in (sidecar.manifest, sidecar.load, sidecar.verify, sidecar.provenance):
        assert inspect.signature(reader).parameters["root"].default == sidecar.SIDECAR_ROOT
    assert inspect.signature(sidecar.load).parameters["columns"].default is None
    assert [field.name for field in dataclasses.fields(sidecar.SidecarManifest)] == [
        "sidecar_schema_version", "tag_mapping_version", "provider", "tier", "attribution",
        "competition", "raw_digests", "content_hashes", "row_counts", "anomalies",
        "actions_event_ids_equal", "builder_source_hash", "packages"]
    assert sidecar.SidecarManifest.__dataclass_params__.frozen
    # A whole events file is never handed to json.load: the stream decoder is the reader.
    assert "json.load(" not in MODULE.read_text(encoding="utf-8")


# ------------------------------------------------------------ named tag columns

@pytest.mark.parametrize("tag", [*sorted(ON), *CARRIED_BY_ACTIONS, *DEAD])
def test_every_named_column_follows_its_tag_table(tag):
    row = sidecar.event_row(tagged(tag))
    assert {name: row[name] for name in OFF} == {**OFF, **ON.get(tag, {})}
    assert row["tags"] == [tag]
    assert list(row) == EVENT_COLUMNS
    # A pass is not a shot whatever it carries: 101 and 2101 alone do not make an outcome.
    assert row["shot_family"] is None and row["shot_outcome"] is None


@pytest.mark.parametrize(("tags", "expected"), [
    ((401, 402), dict(body_part=None)),
    ((402, 403), dict(body_part=None)),
    ((701, 703), dict(duel_outcome=None)),
    ((701, 702, 703), dict(duel_outcome=None)),
    ((1201, 1210), dict(goal_zone=None, goal_zone_class=None)),
    ((1201, 1202), dict(goal_zone=None, goal_zone_class=None)),  # two zones of one class
    ((1101, 1102), dict(fk_direct=None)),
    ((1702, 1701), dict(card="red_card")),
    ((1702, 1703), dict(card="second_yellow")),
    ((1701, 1703), dict(card="second_yellow")),
    ((1701, 1702, 1703), dict(card="second_yellow")),
    ((501, 502), dict(free_space=True)),
    ((503, 504), dict(take_on=True)),
    ((601, 602), dict(anticipated=True, anticipation=True)),
])
def test_tags_that_meet_on_one_event(tags, expected):
    row = sidecar.event_row(tagged(*tags))
    assert {name: row[name] for name in expected} == expected
    # Nothing is lost when a named column declines to choose: every tag is still in `tags`.
    assert row["tags"] == sorted(tags)


def test_coordinate_and_identity_facts():
    row = sidecar.event_row(raw_event(id=77, matchId=2500001, subEventId=85, playerId=3))
    assert (row["event_id"], row["game_id"], row["sub_event_id"]) == (77, 2500001, 85)
    assert (row["n_positions"], row["start_at_corner"], row["end_at_corner"]) == (2, False, False)
    assert row["player_attributed"] is True and row["shootout"] is False

    assert sidecar.event_row(raw_event(playerId=0))["player_attributed"] is False
    for empty in ("", "  "):  # offside: the provider leaves the sub-event id blank
        assert sidecar.event_row(raw_event(eventId=6, subEventId=empty))["sub_event_id"] == 0

    def corners(*points):
        row = sidecar.event_row(raw_event(positions=[dict(x=x, y=y) for x, y in points]))
        return row["n_positions"], row["start_at_corner"], row["end_at_corner"]

    assert corners((0, 0), (100, 100)) == (2, True, True)
    assert corners((100, 100), (0, 0)) == (2, True, True)
    assert corners((50, 50), (0, 0)) == (2, False, True)
    assert corners((0, 100), (100, 0)) == (2, False, False)  # the other two corners are not it
    # One position: the adapter copied the start to the end, so there is no end to describe.
    assert corners((0, 0)) == (1, True, False)
    assert corners((100, 100)) == (1, True, False)


@pytest.mark.parametrize(("over", "family"), [
    (dict(eventId=10, subEventId=100), "open_play"),
    (dict(eventId=3, subEventId=33), "free_kick"),
    (dict(eventId=3, subEventId=35), "penalty"),
    (dict(eventId=3, subEventId=30), None),   # a corner that goes in is a goal, not a shot
    (dict(eventId=3, subEventId=32), None),
    (dict(eventId=9, subEventId=90), None),   # the keeper's row carries the zone and the goal
    (dict(eventId=8, subEventId=85), None),
])
def test_shot_family_and_the_rows_that_get_an_outcome(over, family):
    row = sidecar.event_row(tagged(101, 1203, **over))
    assert row["shot_family"] == family
    assert row["shot_outcome"] == ("goal" if family else None)
    missed = sidecar.event_row(tagged(1212, **over))
    assert missed["shot_outcome"] == ("off_target" if family else None)


def test_tags_list_keeps_unknown_and_live_tags_sorted(tmp_path):
    row = sidecar.event_row(tagged(1801, 9999, 101, 101))
    assert row["tags"] == [101, 1801, 9999]
    assert row["goal_on_scoring_event"] is True  # the unknown id hides nothing beside it

    events = [
        tagged(1801, 9999, 101, 101, id=1),   # one unknown id, given once
        tagged(9999, 9998, 9999, id=2),       # two unknown ids, one of them repeated
        tagged(1801, 802, id=3),              # a dead tag is in the dictionary: not unknown
        raw_event(id=4),
    ]
    made, root = build(tmp_path, events=events)
    # Counted per kept id, as `tags` keeps them: 3, not 2 events and not 2 distinct ids.
    assert made.anomalies["unknown_tag_ids"] == 3
    stored = sidecar.load("Spain", "events", columns=["event_id", "tags"], root=root)
    assert {int(i): plain(t) for i, t in zip(stored.event_id, stored.tags, strict=True)} == {
        1: [101, 1801, 9999], 2: [9998, 9999], 3: [802, 1801], 4: [1801]}
    with pytest.raises(ValueError, match="int16"):
        sidecar.event_row(tagged(40000))


def test_shot_outcome_matches_match_lab_enrichment(tmp_path):
    pool = (101, 2101, 1203, 1212, 1219)
    subsets = [combo for size in range(len(pool) + 1)
               for combo in itertools.combinations(pool, size)]
    assert len(subsets) == 32
    cards = [combo for size in range(4) for combo in itertools.combinations((1701, 1702, 1703),
                                                                           size)]
    bodies = [(), (401,), (402,), (403,)]
    events = [shot(*tags, id=100 + n) for n, tags in enumerate(subsets)]
    events += [tagged(*tags, id=200 + n, eventId=2, subEventId=20) for n, tags in enumerate(cards)]
    events += [shot(*tags, id=300 + n) for n, tags in enumerate(bodies)]
    events += [tagged(102, id=400, eventId=7, subEventId=72)]
    path = tmp_path / "events_Spain.json"
    path.write_text(json.dumps(events), encoding="utf-8")

    enriched = _enrich(pd.DataFrame({"event_id": [e["id"] for e in events]}), path)
    ours = sidecar.event_frame(events)
    assert enriched.event_id.tolist() == ours.event_id.tolist()

    by_id = dict(zip(enriched.event_id, enriched.shot_outcome, strict=True))
    for n, tags in enumerate(subsets):
        assert sidecar.shot_outcome(tags) == by_id[100 + n], tags
        assert sidecar.shot_outcome(set(tags)) == by_id[100 + n]
    assert {by_id[100 + n] for n in range(32)} == OUTCOMES  # every label occurs, none is spare
    on_shots = ours[ours.event_id.between(100, 131)]
    assert on_shots.shot_outcome.tolist() == [by_id[i] for i in on_shots.event_id]

    # One definition, two call sites, for the card and the own goal as well.
    assert [plain(v) for v in ours.card] == [plain(v) for v in enriched.card]
    assert {plain(v) for v in ours.card} == {None, "red_card", "yellow_card", "second_yellow"}
    assert ours.own_goal.tolist() == enriched.own_goal.tolist() and ours.own_goal.sum() == 1
    single = ours.event_id.between(300, 303)
    assert [plain(v) for v in ours.body_part[single]] == [
        plain(v) for v in enriched.body_part[single]] == [
        None, "left_foot", "right_foot", "head_or_body"]


def test_two_body_parts_are_null_here_and_the_first_one_in_match_lab(tmp_path):
    # Match Lab takes the first of several body parts, the sidecar gives null. No event in
    # the seven files carries two. (_enrich also labels rows that are not shots; Match Lab
    # reads that label on shot rows only.)
    events = [shot(401, 402, id=1)]
    path = tmp_path / "events_Spain.json"
    path.write_text(json.dumps(events), encoding="utf-8")
    assert _enrich(pd.DataFrame({"event_id": [1]}), path).body_part.tolist() == ["left_foot"]
    assert sidecar.event_row(events[0])["body_part"] is None


def test_goal_on_scoring_event_excludes_keeper_rows_and_shootouts():
    def scored(**over):
        return sidecar.event_row(tagged(101, 1203, **over))["goal_on_scoring_event"]

    assert scored(eventId=10, subEventId=100) is True
    assert scored(eventId=9, subEventId=90) is False   # the conceding keeper's record
    assert scored(eventId=9, subEventId=91) is False
    assert scored(eventId=3, subEventId=35) is True    # a penalty in play
    assert scored(eventId=3, subEventId=35, matchPeriod="P") is False
    assert scored(eventId=10, subEventId=100, matchPeriod="P") is False
    assert scored(eventId=3, subEventId=30) is True    # a corner that goes straight in
    assert scored(eventId=10, subEventId=100, matchPeriod="E2") is True
    assert sidecar.event_row(shot(1203))["goal_on_scoring_event"] is False

    shootout = sidecar.event_row(tagged(101, eventId=3, subEventId=35, matchPeriod="P"))
    assert shootout["shootout"] is True and shootout["shot_family"] == "penalty"
    assert shootout["shot_outcome"] == "goal"  # the kick went in; it is not a goal of the match
    assert shootout["tags"] == [101]


def test_event_without_position_is_dropped_like_the_adapter(tmp_path):
    no_key = raw_event(id=5)
    del no_key["positions"]
    events = [
        raw_event(id=1),
        raw_event(id=2, positions=[]),
        raw_event(id=3, positions=None),
        raw_event(id=4, positions=[dict(x=10, y=10)]),
        no_key,
        tagged(id=6, eventId=6, subEventId=""),
    ]
    raw = write_raw(tmp_path / "raw", "Spain", events, [plain_match()])
    adapter_rows = list(PappalardoProvider(raw)._iter_actions("Spain"))
    adapter_ids = {row["event_id"] for row in adapter_rows}
    assert adapter_ids == {1, 4, 6}  # the test has both kinds: three kept and three dropped

    streamed = list(sidecar.iter_raw_events(raw / "events_Spain.json"))
    assert set(sidecar.event_frame(streamed).event_id) == adapter_ids
    assert [sidecar.event_row(event) is None for event in events] == [
        False, True, True, False, True, False]

    actions = tmp_path / "actions.parquet"
    pd.DataFrame(adapter_rows).to_parquet(actions, index=False)
    # The three paths as plain strings: a caller's path need not be a Path.
    made = sidecar.write_sidecar("Spain", raw_root=str(raw), out_root=str(tmp_path / "v1"),
                                 actions_path=str(actions))
    assert made.anomalies["events_without_position"] == 3
    assert made.actions_event_ids_equal is True and made.row_counts["events"] == 3
    assert sidecar.manifest("Spain", root=str(tmp_path / "v1")) == made
    assert len(sidecar.load("Spain", "events", root=str(tmp_path / "v1"))) == 3


# ------------------------------------------------------------------ the stream

@pytest.mark.parametrize("render", [
    lambda items: json.dumps(items),
    lambda items: json.dumps(items, separators=(",", ":")),
    lambda items: json.dumps(items, indent=2),
    lambda items: json.dumps(items, indent=2) + "\n",
    lambda items: json.dumps(items, indent=1).replace("\n", "\r\n"),
    lambda items: json.dumps(items, indent=1).replace("\n", "\r\n") + "\r\n",
    lambda items: " \r\n\t" + json.dumps(items),
    lambda items: json.dumps(items, ensure_ascii=False),
], ids=["one-line", "compact", "indented", "trailing-newline", "crlf", "crlf-trailing",
        "leading-space", "utf8"])
@pytest.mark.parametrize("count", [0, 1, 3])
def test_stream_decoder_equals_json_load_on_small_file(tmp_path, render, count):
    items = [raw_event(id=n, eventName="Pass \u00e9 \"quoted\" [x], {y}") for n in range(count)]
    path = tmp_path / "events.json"
    path.write_bytes(render(items).encode("utf-8"))
    with path.open(encoding="utf-8") as handle:
        expected = json.load(handle)
    assert list(sidecar.iter_raw_events(path)) == expected
    assert len(expected) == count


@pytest.mark.parametrize(("text", "message"), [
    ('{"a": [1, 2]}', "not a JSON array"),       # the first bracket in the file is not the top
    ("", "not a JSON array"),
    ('[{"a": 1}, {"a": 2}', "before the array is closed"),
    ('[{"a": 1}, ', "before the array is closed"),
    ('[{"a": 1}] [{"a": 2}]', "after the array"),
    ('[{"a": 1}, {"a": ', None),                 # cut inside an object: the decoder says so
])
def test_stream_decoder_refuses_what_is_not_one_array(tmp_path, text, message):
    path = tmp_path / "events.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        list(sidecar.iter_raw_events(path))


def test_the_build_reads_one_layout_of_the_raw_file_like_another(tmp_path):
    compact, _ = build(tmp_path / "compact")
    raw = write_raw(tmp_path / "spaced" / "raw", "Spain", small_events(), [plain_match()])
    laid_out = " \r\n" + json.dumps(small_events(), indent=1).replace("\n", "\r\n") + "\r\n"
    (raw / "events_Spain.json").write_bytes(laid_out.encode("utf-8"))
    (raw / "matches_Spain.json").write_bytes(
        json.dumps([plain_match()], indent=1).replace("\n", "\r\n").encode("utf-8"))
    spaced = sidecar.write_sidecar("Spain", raw_root=raw, out_root=tmp_path / "spaced" / "v1",
                                   actions_path=tmp_path / "no-actions.parquet")
    # The build decodes the bytes itself and nothing translates the line ends for it.
    assert b"\r\n" in (raw / "events_Spain.json").read_bytes()
    assert spaced.content_hashes == compact.content_hashes
    assert spaced.row_counts == compact.row_counts and spaced.anomalies == compact.anomalies
    assert spaced.raw_digests["events"] != compact.raw_digests["events"]
    assert spaced.raw_digests["matches"] != compact.raw_digests["matches"]

    (raw / "events_Spain.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="not a JSON array"):
        sidecar.write_sidecar("Spain", raw_root=raw, out_root=tmp_path / "spaced" / "v2",
                              actions_path=tmp_path / "no-actions.parquet")
    write_raw(raw, "Spain", small_events(), [])
    (raw / "matches_Spain.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="not a JSON array"):
        sidecar.write_sidecar("Spain", raw_root=raw, out_root=tmp_path / "spaced" / "v2",
                              actions_path=tmp_path / "no-actions.parquet")
    assert not [path for path in (tmp_path / "spaced" / "v2").rglob("*") if path.is_file()]


# ---------------------------------------------------------------- event frame

def test_event_frame_has_the_stated_columns_and_dtypes_even_for_zero_rows(tmp_path):
    full = sidecar.event_frame(small_events())
    empty = sidecar.event_frame([])
    assert list(full.columns) == list(empty.columns) == EVENT_COLUMNS
    assert len(empty) == 0 and len(full) == 8  # the ninth event has no position
    assert empty.dtypes.astype(str).to_dict() == full.dtypes.astype(str).to_dict()

    dtypes = full.dtypes.astype(str).to_dict()
    assert {dtypes[name] for name in ("event_id", "game_id")} == {"int64"}
    assert (dtypes["sub_event_id"], dtypes["n_positions"]) == ("int16", "int8")
    plain_bool = [name for name, value in OFF.items() if value is False]
    plain_bool += ["start_at_corner", "end_at_corner", "player_attributed", "shootout"]
    assert {dtypes[name] for name in plain_bool} == {"bool"}
    # Nullable, and nullable whatever the rows hold: not bool on a day without nulls.
    assert dtypes["fk_direct"] == "boolean"
    assert str(sidecar.event_frame([tagged(1101)]).fk_direct.dtype) == "boolean"
    for name in ("body_part", "duel_outcome", "goal_zone", "goal_zone_class", "card",
                 "shot_family", "shot_outcome"):
        assert pd.api.types.is_string_dtype(full[name]), name
    assert all(isinstance(cell, np.ndarray) and cell.dtype == np.int16 for cell in full.tags)

    # The frame is the rows: nothing is added or reordered on the way into pandas.
    assert records(full) == [sidecar.event_row(e) for e in small_events() if e["positions"]]
    # And it is the frame a reader gets back from disk, dtype for dtype.
    made, root = build(tmp_path)
    stored = sidecar.load("Spain", "events", root=root)
    pd.testing.assert_frame_equal(stored, full)
    assert sidecar.content_hash(full, "events") == made.content_hashes["events"]


def test_event_frame_accepts_any_iterable_and_reads_it_once():
    def stream():
        yield from small_events()

    assert len(sidecar.event_frame(stream())) == 8
    assert len(sidecar.event_frame(tuple(small_events()))) == 8


# -------------------------------------------------------------- match sheets

def test_squad_roles_and_minutes(tmp_path):
    first = raw_match(
        100,
        # Starter 1 goes off at 60 for 12; 12 goes off at 80 for 13; 14 never comes on.
        # The later change is listed first: who came on does not depend on the order.
        sheet_side(10, "home", 1, 0, range(1, 12), [12, 13, 14],
                   [swap(13, 12, 80), swap(12, 1, 60)]),
        # The provider wrote the string null where the list of substitutions belongs.
        sheet_side(20, "away", 0, 0, range(21, 32), [32, 33], "null"),
        winner=10,
    )
    second = raw_match(
        101,
        # Starter 2 goes off at 70 and the incoming player has no id; 14 replaces 3 at 75.
        sheet_side(10, "home", 0, 0, range(1, 12), [12, 14], [swap(0, 2, 70), swap(14, 3, 75)]),
        sheet_side(30, "away", 0, 0,
                   [sheet_player(41, yellow="34"), sheet_player(42, red="88"),
                    sheet_player(43, yellow="12", red="57"), *range(44, 52)],
                   [sheet_player(52, yellow="90"), 53], [swap(52, 44, 46)]),
        winner=0,
    )
    squads = sidecar.squad_frame([first, second])
    assert list(squads.columns) == SQUAD_COLUMNS
    dtypes = squads.dtypes.astype(str).to_dict()
    assert {dtypes[name] for name in ("game_id", "team_id", "player_id")} == {"int64"}
    assert {dtypes[name] for name in ("minute_on", "minute_off", "yellow_minute",
                                      "red_minute")} == {"Int16"}
    assert dtypes["subs_recorded"] == "bool" and pd.api.types.is_string_dtype(squads.role)
    assert len(squads) == (11 + 3) + (11 + 2) + (11 + 2) + (11 + 2)  # one row per listed player

    rows = {(r["game_id"], r["team_id"], r["player_id"]): r for r in records(squads)}

    def facts(key):
        row = rows[key]
        return (row["role"], row["minute_on"], row["minute_off"], row["yellow_minute"],
                row["red_minute"], row["subs_recorded"])

    assert facts((100, 10, 1)) == ("start", 0, 60, None, None, True)
    assert facts((100, 10, 2)) == ("start", 0, None, None, None, True)
    assert facts((100, 10, 12)) == ("sub_used", 60, 80, None, None, True)
    assert facts((100, 10, 13)) == ("sub_used", 80, None, None, None, True)
    assert facts((100, 10, 14)) == ("sub_unused", None, None, None, None, True)
    # No list of substitutions: the label is not evidence that nobody came on.
    assert facts((100, 20, 21)) == ("start", 0, None, None, None, False)
    assert facts((100, 20, 32)) == ("sub_unused", None, None, None, None, False)
    assert facts((100, 20, 33)) == ("sub_unused", None, None, None, None, False)
    # Incoming id 0: no row is invented, and the outgoing minute is kept.
    assert facts((101, 10, 2)) == ("start", 0, 70, None, None, True)
    assert facts((101, 10, 3)) == ("start", 0, 75, None, None, True)
    assert facts((101, 10, 14)) == ("sub_used", 75, None, None, None, True)
    assert facts((101, 10, 12)) == ("sub_unused", None, None, None, None, True)
    assert not (squads.player_id == 0).any()
    # Cards are the minute on the sheet; a dismissal does not write a minute_off.
    assert facts((101, 30, 41)) == ("start", 0, None, 34, None, True)
    assert facts((101, 30, 42)) == ("start", 0, None, None, 88, True)
    assert facts((101, 30, 43)) == ("start", 0, None, 12, 57, True)
    assert facts((101, 30, 44)) == ("start", 0, 46, None, None, True)
    assert facts((101, 30, 52)) == ("sub_used", 46, None, 90, None, True)
    assert squads.role.value_counts().to_dict() == {"start": 44, "sub_unused": 5, "sub_used": 4}

    made, root = build(tmp_path, matches=[first, second])
    assert made.anomalies["sub_in_unattributed"] == 1
    assert made.anomalies["sub_out_not_starter"] == 1  # player 12, a substitute substituted
    assert made.anomalies["subs_not_recorded_team_matches"] == 1
    assert made.row_counts["squads"] == len(squads) == 53
    # Stored as the sheets list them: match, side, starting eleven, then the bench.
    pd.testing.assert_frame_equal(sidecar.load("Spain", "squads", root=root), squads)
    assert squads.player_id.tolist()[:14] == [*range(1, 12), 12, 13, 14]


@pytest.mark.parametrize(("subs", "bench", "message"), [
    ([swap(99, 1, 60)], [12], "neither on the bench"),       # an incoming id nobody listed
    ([swap(12, 1, 60), swap(12, 2, 70)], [12], "twice"),     # one player comes on twice
    ([swap(12, 1, 60), swap(13, 1, 70)], [12, 13], "twice"),  # one player goes off twice
    ([swap(12, 0, 60)], [12], "neither started nor came on"),      # nobody goes off
    ([swap(12, 99, 60)], [12], "neither started nor came on"),     # an id on neither list
    ([swap(12, 13, 60)], [12, 13], "neither started nor came on"),  # he was never brought on
])
def test_a_substitution_the_sheet_cannot_carry_is_refused(subs, bench, message):
    match = raw_match(100, sheet_side(10, "home", 0, 0, range(1, 12), bench, subs),
                      sheet_side(20, "away", 0, 0, range(21, 32), [], []), winner=0)
    with pytest.raises(ValueError, match=message):
        sidecar.squad_frame([match])


def test_a_card_field_that_is_not_a_minute_is_refused():
    def match(**card):
        return raw_match(100, sheet_side(10, "home", 0, 0, [sheet_player(1, **card),
                                                            *range(2, 12)], [], []),
                         sheet_side(20, "away", 0, 0, range(21, 32), [], []), winner=0)

    assert sidecar.squad_frame([match(yellow="45")]).yellow_minute.tolist()[0] == 45
    for card in (dict(yellow="null"), dict(red="")):
        with pytest.raises(ValueError, match="not a minute"):
            sidecar.squad_frame([match(**card)])


def test_match_and_squad_frames_keep_their_dtypes_whatever_the_rows_hold():
    # Coaches named, a winner named, no substitution, no card: no null in a match column
    # and nothing but nulls in three squad columns. The dtypes are the same all the same.
    quiet = raw_match(1, sheet_side(10, "home", 1, 0, range(1, 12), [12], [], coach=5),
                      sheet_side(20, "away", 0, 0, range(21, 32), [], [], coach=6), winner=10)
    for frame_of in (lambda sheets: sidecar.match_frame(sheets, "Spain"), sidecar.squad_frame):
        mixed, plain_rows, none = frame_of([plain_match()]), frame_of([quiet]), frame_of([])
        assert len(none) == 0 and list(none.columns) == list(mixed.columns)
        assert (mixed.dtypes.astype(str).to_dict() == plain_rows.dtypes.astype(str).to_dict()
                == none.dtypes.astype(str).to_dict())
    matches, squads = sidecar.match_frame([quiet], "Spain"), sidecar.squad_frame([quiet])
    assert not matches.isna().any().any()
    assert (matches.winner_team_id.tolist(), matches.home_coach_id.tolist()) == ([10], [5])
    assert squads[["minute_off", "yellow_minute", "red_minute"]].isna().all().all()
    assert squads.minute_on.isna().tolist() == [False] * 11 + [True] + [False] * 11


def test_match_detail_scores_and_winner_flag(tmp_path):
    def match(game_id, home_score, away_score, winner, **over):
        return raw_match(
            game_id,
            sheet_side(10, "home", home_score, min(home_score, 1), range(1, 12), [], [],
                       coach=501),
            sheet_side(20, "away", away_score, 0, range(21, 32), [], [], coach=0),
            winner=winner, **over)

    sheets = [
        match(5, 2, 1, 10, dateutc="2018-05-20 18:45:00", gameweek=38),
        match(1, 1, 1, 0),
        match(2, 0, 3, 20),
        match(3, 1, 0, 20),                         # the sheet names the loser as winner
        match(4, 2, 2, 10, duration="Penalties"),   # level in the score, decided elsewhere
        match(6, 2, 0, 0),                          # no winner named for a match that had one
    ]
    frame = sidecar.match_frame(sheets, "Spain")
    assert list(frame.columns) == MATCH_COLUMNS and "label" not in frame.columns
    assert frame.game_id.tolist() == [5, 1, 2, 3, 4, 6]  # sheet order: nothing is sorted here
    dtypes = frame.dtypes.astype(str).to_dict()
    assert {dtypes[n] for n in ("game_id", "home_team_id", "away_team_id")} == {"int64"}
    assert {dtypes[n] for n in ("gameweek", "home_score", "away_score", "home_score_ht",
                                "away_score_ht")} == {"int16"}
    assert {dtypes[n] for n in ("winner_team_id", "home_coach_id", "away_coach_id")} == {"Int64"}
    assert dtypes["winner_agrees_with_score"] == "bool"

    rows = {row["game_id"]: row for row in records(frame)}
    assert rows[5] == dict(
        game_id=5, competition="Spain", date_utc="2018-05-20 18:45:00", gameweek=38,
        home_team_id=10, away_team_id=20, home_score=2, away_score=1, home_score_ht=1,
        away_score_ht=0, winner_team_id=10, winner_agrees_with_score=True, duration="Regular",
        home_coach_id=501, away_coach_id=None)
    assert {g: (r["winner_team_id"], r["winner_agrees_with_score"]) for g, r in rows.items()} == {
        5: (10, True), 1: (None, True), 2: (20, True), 3: (20, False), 4: (10, False),
        6: (None, False)}
    assert rows[4]["duration"] == "Penalties"
    # The raw value 0 means no coach is recorded, on either side.
    no_home_coach = raw_match(
        8, sheet_side(10, "home", 1, 0, range(1, 12), [], [], coach=0),
        sheet_side(20, "away", 0, 0, range(21, 32), [], [], coach=502), winner=10)
    lone = records(sidecar.match_frame([no_home_coach], "Spain"))[0]
    assert (lone["home_coach_id"], lone["away_coach_id"]) == (None, 502)

    made, root = build(tmp_path, matches=sheets)
    assert made.anomalies["winner_disagrees_with_score"] == 3
    stored = sidecar.load("Spain", "matches", root=root)
    assert stored.game_id.tolist() == [5, 1, 2, 3, 4, 6]
    pd.testing.assert_frame_equal(stored, frame)


def test_a_sheet_without_one_home_and_one_away_side_is_refused():
    both_home = raw_match(1, sheet_side(10, "home", 0, 0, range(1, 12), [], []),
                          sheet_side(20, "home", 0, 0, range(21, 32), [], []), winner=0)
    with pytest.raises(ValueError, match="one home and one away"):
        sidecar.match_frame([both_home], "Spain")


# ------------------------------------------------------------------ the build

def test_write_refuses_competition_directories(tmp_path, monkeypatch):
    raw = write_raw(tmp_path / "raw", "Spain", small_events(), [plain_match()])
    absent = tmp_path / "no-actions.parquet"
    for refused in (tmp_path / "competition=Spain",
                    tmp_path / "competition=Spain" / "v1",
                    tmp_path / "side" / "competition=anything" / "deep"):
        with pytest.raises(ValueError, match="competition="):
            sidecar.write_sidecar("Spain", raw_root=raw, out_root=refused, actions_path=absent)
        assert not refused.exists()

    # The neutral tree itself, pointed at a temporary directory so nothing real is at stake.
    parquet = tmp_path / "public" / "parquet"
    monkeypatch.setattr(sidecar, "PUBLIC", parquet / "pappalardo")
    for refused in (parquet / "pappalardo", parquet / "pappalardo" / "sidecar",
                    parquet / "elsewhere"):
        with pytest.raises(ValueError, match="neutral"):
            sidecar.write_sidecar("Spain", raw_root=raw, out_root=refused, actions_path=absent)
        assert not refused.exists()
    if sys.platform == "win32":
        # Another spelling of the same directory: the extended-length prefix survives
        # Path.resolve, so only the file system can say it is inside the neutral tree.
        parquet.mkdir(parents=True)
        spelled = Path("\\\\?\\" + str(parquet.resolve() / "elsewhere"))
        with pytest.raises(ValueError, match="neutral"):
            sidecar.write_sidecar("Spain", raw_root=raw, out_root=spelled, actions_path=absent)
        assert not (parquet / "elsewhere").exists()
    # A sibling of the neutral tree is where the sidecar lives.
    made = sidecar.write_sidecar("Spain", raw_root=raw, actions_path=absent,
                                 out_root=tmp_path / "public" / "sidecar" / "pappalardo" / "v1")
    assert made.row_counts["events"] == 8

    with pytest.raises(ValueError, match="unknown competition"):
        sidecar.write_sidecar("Atlantis", raw_root=raw, out_root=tmp_path / "v1",
                              actions_path=absent)
    with pytest.raises(FileNotFoundError):  # a known competition whose raw files are absent
        sidecar.write_sidecar("Italy", raw_root=raw, out_root=tmp_path / "v1",
                              actions_path=absent)
    assert not (tmp_path / "v1").exists()


def test_a_build_writes_three_tables_and_then_the_manifest(tmp_path):
    made, root = build(tmp_path)
    directory = root / "Spain"
    assert sorted(path.name for path in directory.iterdir()) == [
        "MANIFEST.json", "events.parquet", "matches.parquet", "squads.parquet"]
    assert made == sidecar.manifest("Spain", root=root)

    posture = PROVIDERS["pappalardo"]
    assert (made.provider, made.tier, made.attribution) == (
        "pappalardo", "PUBLIC", posture.attribution)
    assert made.sidecar_schema_version == sidecar.SIDECAR_SCHEMA_VERSION
    assert made.tag_mapping_version == sidecar.TAG_MAPPING_VERSION
    assert made.competition == "Spain"
    assert made.row_counts == {"events": 8, "matches": 1, "squads": 25}
    assert set(made.anomalies) == ANOMALY_KEYS
    assert made.anomalies == dict.fromkeys(ANOMALY_KEYS, 0) | {"events_without_position": 1}
    assert made.actions_event_ids_equal is None  # there was no actions file to compare with
    raw = tmp_path / "raw"
    assert made.raw_digests == {
        name: hashlib.sha256((raw / f"{name}_Spain.json").read_bytes()).hexdigest()
        for name in ("events", "matches")}
    assert made.builder_source_hash == hashlib.sha256(
        MODULE.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert made.packages == {"numpy": np.__version__, "pandas": pd.__version__,
                             "pyarrow": __import__("pyarrow").__version__}
    assert set(made.content_hashes) == set(sidecar.TABLES)
    for table in sidecar.TABLES:
        assert made.content_hashes[table] == sidecar.content_hash(
            sidecar.load("Spain", table, root=root), table)
    sidecar.verify("Spain", root=root)
    stored = __import__("pyarrow.parquet", fromlist=["ParquetFile"]).ParquetFile(
        directory / "events.parquet")
    assert stored.metadata.row_group(0).column(0).compression == "ZSTD"

    assert sidecar.provenance("Spain", root=root) == {
        "sidecar_schema_version": "wyscout-tag-sidecar-v1",
        "tag_mapping_version": "wyscout-v2-tags2name-57live-v1",
        "content_hashes": made.content_hashes,
        "raw_digests": made.raw_digests,
        "competition": "Spain",
    }
    json.dumps(sidecar.provenance("Spain", root=root), allow_nan=False)


def test_the_same_raw_bytes_build_the_same_sidecar(tmp_path):
    first, _ = build(tmp_path / "a")
    second, _ = build(tmp_path / "b")
    assert first == second
    # Raw file order is not part of the content: the hash is taken over sorted rows.
    reordered, _ = build(tmp_path / "c", events=list(reversed(small_events())))
    assert reordered.content_hashes == first.content_hashes
    assert reordered.raw_digests["events"] != first.raw_digests["events"]
    changed, _ = build(tmp_path / "d", events=[*small_events()[:-1], raw_event(id=20)])
    assert changed.content_hashes["events"] != first.content_hashes["events"]
    assert changed.content_hashes["matches"] == first.content_hashes["matches"]


def test_chunk_boundaries_do_not_change_the_table(tmp_path, monkeypatch):
    whole, whole_root = build(tmp_path / "whole")
    monkeypatch.setattr(sidecar, "CHUNK_ROWS", 3)  # eight rows: chunks of 3, 3 and 2
    chunked, chunked_root = build(tmp_path / "chunked")
    assert chunked == whole
    pd.testing.assert_frame_equal(sidecar.load("Spain", "events", root=chunked_root),
                                  sidecar.load("Spain", "events", root=whole_root))
    monkeypatch.setattr(sidecar, "CHUNK_ROWS", 8)  # the last chunk is exactly full
    assert build(tmp_path / "exact")[0] == whole
    # A competition with no event at all still gets a table with the full schema.
    empty, empty_root = build(tmp_path / "empty", events=[])
    assert empty.row_counts["events"] == 0
    assert list(sidecar.load("Spain", "events", root=empty_root).columns) == EVENT_COLUMNS
    sidecar.verify("Spain", root=empty_root)


def test_the_build_checks_the_event_ids_against_the_actions_frame(tmp_path):
    raw = write_raw(tmp_path / "raw", "Spain", small_events(), [plain_match()])
    kept = [e["id"] for e in small_events() if e["positions"]]

    def actions(ids, provider="pappalardo"):
        path = tmp_path / f"actions-{len(list(tmp_path.glob('actions-*')))}.parquet"
        pd.DataFrame({"event_id": ids, "provider": provider}).to_parquet(path, index=False)
        return path

    made = sidecar.write_sidecar("Spain", raw_root=raw, out_root=tmp_path / "ok",
                                 actions_path=actions(list(reversed(kept))))
    assert made.actions_event_ids_equal is True

    # One short, one too many, one swapped for a repeat, and the same set with a repeat:
    # the last is equal as a set and still not a one-to-one join.
    for ids in (kept[:-1], [*kept, 999], [*kept[:-1], kept[0]], [*kept, kept[0]]):
        target = tmp_path / f"bad-{len(ids)}-{ids[-1]}"
        with pytest.raises(sidecar.SidecarMismatch, match="event_id"):
            sidecar.write_sidecar("Spain", raw_root=raw, out_root=target,
                                  actions_path=actions(ids))
        # Nothing is left that a reader could take for a sidecar.
        assert not [path for path in target.rglob("*") if path.is_file()]
        with pytest.raises(sidecar.SidecarMissing):
            sidecar.load("Spain", "events", root=target)

    with pytest.raises(LicenseViolation):  # an actions file of another provider is not read
        sidecar.write_sidecar("Spain", raw_root=raw, out_root=tmp_path / "foreign",
                              actions_path=actions(kept, provider="statsbomb"))
    unlabelled = tmp_path / "unlabelled.parquet"
    pd.DataFrame({"event_id": kept}).to_parquet(unlabelled, index=False)
    with pytest.raises(LicenseViolation, match="provider"):  # nor one that does not say whose
        sidecar.write_sidecar("Spain", raw_root=raw, out_root=tmp_path / "foreign",
                              actions_path=unlabelled)
    assert not [path for path in (tmp_path / "foreign").rglob("*") if path.is_file()]

    duplicated = [*small_events(), raw_event(id=11)]
    with pytest.raises(sidecar.SidecarMismatch, match="unique"):
        build(tmp_path / "dup", events=duplicated)


def test_a_failed_rebuild_leaves_the_complete_sidecar_it_found(tmp_path):
    made, root = build(tmp_path)
    before = sha256_of_files(root)
    bad = tmp_path / "bad-actions.parquet"
    pd.DataFrame({"event_id": [1], "provider": "pappalardo"}).to_parquet(bad, index=False)
    with pytest.raises(sidecar.SidecarMismatch):
        sidecar.write_sidecar("Spain", raw_root=tmp_path / "raw", out_root=root, actions_path=bad)
    assert sha256_of_files(root) == before
    assert sidecar.manifest("Spain", root=root) == made
    # A rebuild that succeeds replaces all four files and is again complete.
    again = sidecar.write_sidecar("Spain", raw_root=write_raw(
        tmp_path / "raw", "Spain", [*small_events(), raw_event(id=20)], [plain_match()]),
        out_root=root, actions_path=tmp_path / "no-actions.parquet")
    assert again.row_counts["events"] == 9 and again != made
    sidecar.verify("Spain", root=root)
    assert sorted(path.name for path in (root / "Spain").iterdir()) == [
        "MANIFEST.json", "events.parquet", "matches.parquet", "squads.parquet"]


def test_a_build_interrupted_while_the_tables_change_hands_leaves_no_manifest(tmp_path,
                                                                             monkeypatch):
    made, root = build(tmp_path)
    replace, moved = os.replace, []

    def fail_on_the_second(source, target):
        moved.append(Path(target).name)
        if len(moved) == 2:
            raise OSError("the disk went away")
        replace(source, target)

    monkeypatch.setattr(sidecar.os, "replace", fail_on_the_second)
    with pytest.raises(OSError, match="the disk went away"):
        build(tmp_path, events=[*small_events(), raw_event(id=20)])
    monkeypatch.undo()
    # A new events table beside the old matches and squads. With the old manifest still
    # there a reader would take that for the sidecar the manifest describes.
    assert moved == ["events.parquet", "matches.parquet"]
    assert sorted(path.name for path in (root / "Spain").iterdir()) == [
        "events.parquet", "matches.parquet", "squads.parquet"]
    assert len(pd.read_parquet(root / "Spain" / "events.parquet")) == 9 != made.row_counts["events"]
    for table in sidecar.TABLES:
        with pytest.raises(sidecar.SidecarMissing, match="MANIFEST"):
            sidecar.load("Spain", table, root=root)


def test_hosting_guard_runs_before_anything_is_read_or_written(tmp_path, monkeypatch):
    made, root = build(tmp_path)
    before = sha256_of_files(tmp_path)
    touched: list[object] = []

    def refuse(provider_id: str):
        raise LicenseViolation(f"{provider_id} refused")

    monkeypatch.setattr(sidecar, "assert_may_host", refuse)
    monkeypatch.setattr(sidecar.pd, "read_parquet", lambda *a, **k: touched.append(a))
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: touched.append(self))
    monkeypatch.setattr(Path, "read_bytes", lambda self, *a, **k: touched.append(self))
    monkeypatch.setattr(Path, "mkdir", lambda self, *a, **k: touched.append(self))
    calls = [
        lambda: sidecar.load("Spain", "events", root=root),
        lambda: sidecar.load("Atlantis", "nothing", root=root),  # the guard outranks validation
        lambda: sidecar.manifest("Spain", root=root),
        lambda: sidecar.verify("Spain", root=root),
        lambda: sidecar.provenance("Spain", root=root),
        lambda: sidecar.write_sidecar("Spain", raw_root=tmp_path / "raw",
                                      out_root=tmp_path / "v2"),
    ]
    for call in calls:
        with pytest.raises(LicenseViolation, match="pappalardo refused"):
            call()
    assert touched == []
    monkeypatch.undo()
    assert sha256_of_files(tmp_path) == before and made == sidecar.manifest("Spain", root=root)


# -------------------------------------------------------------------- the load

def test_load_rejects_stale_schema_and_missing_tables(tmp_path):
    made, root = build(tmp_path)
    with pytest.raises(sidecar.SidecarMissing):  # nothing was ever built here
        sidecar.load("Spain", "events", root=tmp_path / "empty")
    with pytest.raises(sidecar.SidecarMissing):  # built, but not this competition
        sidecar.load("Italy", "events", root=root)
    with pytest.raises(sidecar.SidecarMissing):
        sidecar.manifest("Italy", root=root)

    (root / "Spain" / "squads.parquet").unlink()
    with pytest.raises(sidecar.SidecarMissing, match="squads"):
        sidecar.load("Spain", "squads", root=root)
    assert len(sidecar.load("Spain", "events", root=root)) == 8  # the other tables still load
    with pytest.raises(sidecar.SidecarMissing):
        sidecar.verify("Spain", root=root)

    manifest_path = root / "Spain" / "MANIFEST.json"
    record = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert record["sidecar_schema_version"] == "wyscout-tag-sidecar-v1"
    record["sidecar_schema_version"] = "wyscout-tag-sidecar-v0"
    manifest_path.write_text(json.dumps(record), encoding="utf-8")
    for call in (lambda: sidecar.load("Spain", "events", root=root),
                 lambda: sidecar.manifest("Spain", root=root),
                 lambda: sidecar.verify("Spain", root=root),
                 lambda: sidecar.provenance("Spain", root=root)):
        with pytest.raises(sidecar.SidecarStale, match="wyscout-tag-sidecar-v0"):
            call()

    # A manifest alone is not a sidecar, and tables alone are not one either.
    manifest_path.unlink()
    with pytest.raises(sidecar.SidecarMissing, match="MANIFEST"):
        sidecar.load("Spain", "events", root=root)


def test_load_projects_columns_and_refuses_what_it_does_not_know(tmp_path):
    made, root = build(tmp_path)
    picked = sidecar.load("Spain", "events", columns=["card", "event_id", "tags"], root=root)
    assert list(picked.columns) == ["card", "event_id", "tags"]
    whole = sidecar.load("Spain", "events", root=root)
    pd.testing.assert_frame_equal(picked, whole[["card", "event_id", "tags"]])
    assert list(whole.columns) == EVENT_COLUMNS
    assert list(sidecar.load("Spain", "matches", root=root).columns) == MATCH_COLUMNS
    assert list(sidecar.load("Spain", "squads", root=root).columns) == SQUAD_COLUMNS

    with pytest.raises(ValueError, match="unknown column"):
        sidecar.load("Spain", "events", columns=["event_id", "rating"], root=root)
    with pytest.raises(ValueError, match="unknown column"):  # a column of another table
        sidecar.load("Spain", "matches", columns=["event_id"], root=root)
    with pytest.raises(ValueError, match="unknown table"):
        sidecar.load("Spain", "actions", root=root)
    with pytest.raises(ValueError, match="unknown competition"):
        sidecar.load("Atlantis", "events", root=root)
    with pytest.raises(TypeError):  # one string is a sequence of its letters
        sidecar.load("Spain", "events", columns="event_id", root=root)
    with pytest.raises(ValueError, match="twice"):
        sidecar.load("Spain", "events", columns=["event_id", "event_id"], root=root)
    with pytest.raises(ValueError, match="empty"):
        sidecar.load("Spain", "events", columns=[], root=root)


def test_load_and_verify_notice_a_table_that_is_not_the_one_built(tmp_path):
    made, root = build(tmp_path)
    path = root / "Spain" / "events.parquet"
    events = pd.read_parquet(path)

    # Same rows, one tag list changed: the row count holds, the content hash does not.
    forged = sidecar.event_frame([e if e["id"] != 12 else tagged(701, 1801, id=12, eventId=1,
                                                                 subEventId=11, playerId=0)
                                  for e in small_events()])
    forged.to_parquet(path, index=False)
    assert len(sidecar.load("Spain", "events", root=root)) == made.row_counts["events"]
    with pytest.raises(sidecar.SidecarMismatch, match="events"):
        sidecar.verify("Spain", root=root)

    events.iloc[:-1].to_parquet(path, index=False)  # one row short: load notices by itself
    with pytest.raises(sidecar.SidecarMismatch, match="rows"):
        sidecar.load("Spain", "events", root=root)
    with pytest.raises(sidecar.SidecarMismatch):
        sidecar.load("Spain", "events", columns=["event_id"], root=root)

    events.to_parquet(path, index=False)  # put back: verify passes again
    sidecar.verify("Spain", root=root)

    # The other two tables are verified as well: one cell each, same number of rows.
    for table, column, value in (("matches", "home_score", 9), ("squads", "minute_on", 1)):
        path = root / "Spain" / f"{table}.parquet"
        original = pd.read_parquet(path)
        changed = original.copy()
        changed.loc[0, column] = value
        changed.to_parquet(path, index=False)
        assert len(sidecar.load("Spain", table, root=root)) == made.row_counts[table]
        with pytest.raises(sidecar.SidecarMismatch, match=table):
            sidecar.verify("Spain", root=root)
        original.to_parquet(path, index=False)
        sidecar.verify("Spain", root=root)
    # A table with other columns is not the table either.
    pd.read_parquet(path).drop(columns="role").to_parquet(path, index=False)
    with pytest.raises(sidecar.SidecarMismatch, match="squads"):
        sidecar.verify("Spain", root=root)

    # A file that is not Parquet at all is a mismatch too, named by its table.
    kept = path.read_bytes()
    path.write_bytes(b"not a table")
    with pytest.raises(sidecar.SidecarMismatch, match="squads"):
        sidecar.verify("Spain", root=root)
    path.write_bytes(kept)

    # A manifest filed under another competition is not that competition's manifest.
    (root / "Italy").mkdir()
    (root / "Italy" / "MANIFEST.json").write_bytes(
        (root / "Spain" / "MANIFEST.json").read_bytes())
    with pytest.raises(sidecar.SidecarMismatch, match="Spain"):
        sidecar.manifest("Italy", root=root)
    # The right version with a field missing is not a manifest this module wrote.
    record = json.loads((root / "Spain" / "MANIFEST.json").read_text(encoding="utf-8"))
    del record["row_counts"]
    (root / "Spain" / "MANIFEST.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(sidecar.SidecarMismatch, match="fields"):
        sidecar.load("Spain", "events", root=root)


# ------------------------------------------------------------------ the join

def test_attach_is_one_to_one_or_raises():
    events = sidecar.event_frame(small_events())
    actions = pd.DataFrame({
        "event_id": [14, 11, 16],
        "type": ["shot", "pass", "set_piece"],
        "success": [True, None, False],
    }, index=[40, 10, 20])
    actions_before, events_before = actions.copy(deep=True), events.copy(deep=True)

    joined = sidecar.attach(actions, events, ["body_part", "shot_outcome", "tags"])
    assert list(joined.columns) == ["event_id", "type", "success", "body_part", "shot_outcome",
                                    "tags"]
    assert joined.event_id.tolist() == [14, 11, 16]  # the caller's rows, in the caller's order
    assert joined.index.tolist() == [40, 10, 20]     # and under the caller's index
    assert [plain(v) for v in joined.body_part] == ["right_foot", None, "left_foot"]
    assert [plain(v) for v in joined.shot_outcome] == ["goal", None, "blocked"]
    assert [plain(v) for v in joined.tags] == [[101, 201, 402, 1203, 1801], [1801],
                                               [401, 1101, 1802, 2101]]
    assert joined is not actions
    pd.testing.assert_frame_equal(actions, actions_before)
    pd.testing.assert_frame_equal(events, events_before)

    missing = pd.DataFrame({"event_id": [14, 999]})
    with pytest.raises(sidecar.SidecarMismatch, match="999"):
        sidecar.attach(missing, events, ["card"])
    twice_left = pd.DataFrame({"event_id": [14, 14]})
    with pytest.raises(sidecar.SidecarMismatch, match="one-to-one"):
        sidecar.attach(twice_left, events, ["card"])
    twice_right = pd.concat([events, events.iloc[[0]]], ignore_index=True)
    with pytest.raises(sidecar.SidecarMismatch, match="one-to-one"):
        sidecar.attach(actions, twice_right, ["card"])
    pd.testing.assert_frame_equal(actions, actions_before)
    pd.testing.assert_frame_equal(events, events_before)

    with pytest.raises(ValueError, match="rating"):  # not a sidecar column
        sidecar.attach(actions, events, ["rating"])
    with pytest.raises(ValueError, match="already"):  # would come back as type_x and type_y
        sidecar.attach(actions, events.assign(type="x"), ["type"])
    with pytest.raises(ValueError, match="event_id"):
        sidecar.attach(actions, events, ["event_id"])
    with pytest.raises(TypeError):
        sidecar.attach(actions, events, "card")
    assert list(sidecar.attach(actions, events, []).columns) == ["event_id", "type", "success"]


# ------------------------------------------------------------------ the hash

def test_content_hash_is_row_order_invariant():
    frame = sidecar.event_frame(small_events())
    reference = sidecar.content_hash(frame, "events")
    assert len(reference) == 64 and int(reference, 16) >= 0
    rng = np.random.default_rng(7)
    for _ in range(5):
        shuffled = frame.iloc[rng.permutation(len(frame))]
        assert sidecar.content_hash(shuffled, "events") == reference
        assert sidecar.content_hash(shuffled.reset_index(drop=True), "events") == reference
    assert sidecar.content_hash(frame[list(reversed(EVENT_COLUMNS))], "events") == reference

    def with_tags(event_id, *tags):
        return sidecar.event_frame([e if e["id"] != event_id else {**e, "tags": [
            dict(id=tag) for tag in tags]} for e in small_events()])

    # One tag changed on one event, in a way no named column sees (1801 for 1802).
    one_tag = with_tags(11, 1802)
    assert records(one_tag.drop(columns="tags")) == records(frame.drop(columns="tags"))
    assert sidecar.content_hash(one_tag, "events") != reference
    assert sidecar.content_hash(with_tags(11), "events") != reference          # no tag at all
    assert sidecar.content_hash(with_tags(11, 1, 2, 3), "events") != sidecar.content_hash(
        with_tags(11, 1, 23), "events")           # 1,2,3 and 1,23 are different lists
    assert sidecar.content_hash(frame.iloc[:-1], "events") != reference

    # It is the frozen frame_hash recipe on the canonical frame, not a recipe of its own.
    canonical = frame.sort_values("event_id").reset_index(drop=True)
    canonical["tags"] = pd.Series([",".join(str(int(t)) for t in tags) for tags in canonical.tags],
                                  dtype=object)
    assert frame_hash(canonical) == reference

    for table, built in (("matches", sidecar.match_frame([plain_match(7), plain_match(8)],
                                                         "Spain")),
                         ("squads", sidecar.squad_frame([plain_match(7), plain_match(8)]))):
        assert sidecar.content_hash(built.iloc[::-1], table) == sidecar.content_hash(built, table)
        assert sidecar.content_hash(built.iloc[1:], table) != sidecar.content_hash(built, table)

    with pytest.raises(ValueError, match="unique"):  # ties would make row order matter
        sidecar.content_hash(pd.concat([frame, frame.iloc[[0]]]), "events")
    with pytest.raises(ValueError, match="columns"):
        sidecar.content_hash(frame.drop(columns="card"), "events")
    with pytest.raises(ValueError, match="unknown table"):
        sidecar.content_hash(frame, "actions")


# ----------------------------------------------------------------- the script

def test_build_script_builds_checks_and_reports(tmp_path, capsys):
    script = load_script("build_sidecar", SCRIPT)
    raw = write_raw(tmp_path / "raw", "Spain", small_events(), [plain_match()])
    write_raw(raw, "World_Cup", [raw_event(id=1, matchPeriod="P")], [plain_match(9, 30, 40)])
    # public_root points away from the corpus: a synthetic build must not meet real actions.
    roots = dict(raw_root=raw, out_root=tmp_path / "v1", public_root=tmp_path / "public")

    assert script.main(["--all"], **roots) == 0
    said = capsys.readouterr().out
    assert [line.split()[0] for line in said.splitlines() if line[:1].isalpha()] == [
        "competition", "Spain", "World_Cup"]  # provider order, one line each, serially
    spain = next(line.split() for line in said.splitlines() if line.startswith("Spain"))
    assert spain[1:4] == ["8", "1", "25"]  # rows: events, matches, squads
    assert float(spain[4]) >= 0.0          # seconds
    assert float(spain[5]) > 0.0           # peak resident memory, in MB
    assert "events_without_position=1" in said
    assert sidecar.manifest("World_Cup", root=tmp_path / "v1").row_counts["events"] == 1

    assert script.main(["--check"], **roots) == 0
    assert script.main(["--check", "--only", "Spain"], **roots) == 0
    checked = capsys.readouterr().out
    assert checked.count(" ok ") == 3 and "FAILED" not in checked
    assert "current" in checked  # the tables were built by the module as it stands
    # Nothing to build is a failure, not an empty success.
    (tmp_path / "empty-raw").mkdir()
    assert script.main(["--all"], raw_root=tmp_path / "empty-raw", out_root=tmp_path / "v2",
                       public_root=tmp_path / "public") == 1
    capsys.readouterr()

    # A table changed after the build: the check says which competition and exits 1.
    path = tmp_path / "v1" / "World_Cup" / "events.parquet"
    sidecar.event_frame([raw_event(id=1)]).to_parquet(path, index=False)
    assert script.main(["--check"], **roots) == 1
    failed = capsys.readouterr().out
    assert "World_Cup" in failed and failed.count("FAILED") == 1 and failed.count(" ok ") == 1
    assert script.main(["--check", "--only", "Spain"], **roots) == 0
    # A competition with raw events and no sidecar is a failed check, not a silent pass.
    write_raw(raw, "Italy", [raw_event(id=5)], [plain_match(3, 50, 60)])
    assert script.main(["--check", "--only", "Italy"], **roots) == 1
    capsys.readouterr()

    assert script.main(["--only", "Italy"], **roots) == 0
    assert script.main(["--check", "--only", "Italy"], **roots) == 0
    # The raw file changed after the build: the tables still verify, the check says stale.
    write_raw(raw, "Italy", [raw_event(id=6)], [plain_match(3, 50, 60)])
    capsys.readouterr()
    assert script.main(["--check", "--only", "Italy"], **roots) == 1
    assert "raw" in capsys.readouterr().out

    for argv in ([], ["--all", "--only", "Spain"], ["--only", "Atlantis"]):
        with pytest.raises(SystemExit) as stopped:
            script.main(argv, **roots)
        assert stopped.value.code == 2
    capsys.readouterr()


def test_build_script_reports_a_failed_build_and_goes_on(tmp_path, capsys):
    script = load_script("build_sidecar", SCRIPT)
    raw = write_raw(tmp_path / "raw", "Spain", [*small_events(), raw_event(id=11)],
                    [plain_match()])  # event id 11 twice: not joinable
    write_raw(raw, "Italy", small_events(), [plain_match()])
    assert script.main(["--all"], raw_root=raw, out_root=tmp_path / "v1",
                       public_root=tmp_path / "public") == 1
    said = capsys.readouterr().out
    assert "Spain" in said and "FAILED" in said
    assert sidecar.manifest("Italy", root=tmp_path / "v1").row_counts["events"] == 8
    with pytest.raises(sidecar.SidecarMissing):
        sidecar.manifest("Spain", root=tmp_path / "v1")


def test_peak_memory_is_the_high_water_mark_of_the_process():
    # A fresh interpreter that loads the one function and nothing else, so the mark starts
    # low and a 96 MB block has to move it.
    program = (
        "import ast, sys\n"
        f"tree = ast.parse(open(r'{SCRIPT}', encoding='utf-8').read())\n"
        "function = next(n for n in tree.body if getattr(n, 'name', '') == 'peak_rss_bytes')\n"
        "scope = {'sys': sys}\n"
        "exec(compile(ast.Module([function], []), 'peak_rss_bytes', 'exec'), scope)\n"
        "before = scope['peak_rss_bytes']()\n"
        "block = bytearray(96 * 1024 * 1024)\n"
        "block[::4096] = b'x' * len(block[::4096])\n"
        "del block\n"
        "import gc\n"
        "gc.collect()\n"
        "print(before, scope['peak_rss_bytes']())\n"
    )
    done = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    before, after = (int(value) for value in done.stdout.split())
    assert before > 2 * 1024 * 1024
    assert after - before >= 64 * 1024 * 1024
    # This process has pandas and Arrow loaded: its mark is above the bare interpreter's.
    assert load_script("build_sidecar", SCRIPT).peak_rss_bytes() > before


# ------------------------------------------------------------------ the corpus

# Structure counts of the event-taxonomy audit of 2026-10-09, one column per league as the
# audit prints them; the comment names its section. The audit counted them from the raw
# files with its own scripts, and here the sidecar has to arrive at the same numbers. No
# outcome of any experiment is among them.
AUDIT = {
    #                     Spain    England  Italy    Germany  France
    "events":            (628_659, 643_150, 647_372, 519_407, 632_807),  # I1 raw events
    "player_id_zero":    (46_681, 48_031, 46_787, 37_244, 47_295),       # I1 player_id == 0
    "offside":           (1_881, 1_558, 1_620, 1_219, 1_543),            # A1 blank sub-event id
    "start_corner":      (12_726, 12_788, 13_476, 10_154, 13_173),       # I1 start at a corner
    "end_corner":        (44_717, 46_082, 46_196, 36_371, 46_593),       # I1 end at a corner
    "goal_tag":          (2_018, 2_007, 1_997, 1_689, 2_032),            # B1 tag 101
    "goal_tag_on_save":  (1_024, 1_019, 1_017, 856, 1_034),              # C4 keeper rows
    "own_goal":          (30, 29, 37, 22, 35),                           # B1 tag 102
    "left_foot":         (8_311, 8_329, 9_005, 6_222, 8_121),            # B1 tag 401
    "right_foot":        (11_429, 11_470, 11_812, 8_947, 11_432),        # B1 tag 402
    "head_or_body":      (1_388, 1_334, 1_386, 1_152, 1_338),            # B1 tag 403
    "won":               (66_790, 68_074, 64_559, 55_754, 65_312),       # B1 tag 703
    "neutral":           (38_050, 40_148, 38_371, 32_220, 40_140),       # B1 tag 702
    "lost":              (66_983, 68_305, 64_701, 55_979, 65_649),       # B1 tag 701
    "red":               (29, 22, 46, 21, 53),                           # B1 tag 1701
    "yellow":            (1_863, 1_180, 1_508, 1_033, 1_433),            # B1 tag 1702
    "second_yellow":     (42, 19, 45, 22, 33),                           # B1 tag 1703
    "open_play_shots":   (7_979, 8_451, 8_806, 6_898, 8_327),            # 4 event type 10
    "free_kick_shots":   (453, 350, 415, 299, 521),                      # 4 sub-event 33
    "penalties":         (113, 80, 126, 93, 129),                        # 4 sub-event 35
    "shot_goals":        (993, 988, 978, 833, 998),                      # C5 goals on those three
    "shots_blocked":     (1_881, 2_399, 2_211, 1_669, 2_068),            # C tag 2101 on those three
    "matches":           (380, 380, 380, 306, 380),                      # H1
    "winner_agrees":     (379, 378, 380, 304, 378),                      # H1
    "goals":             (1_024, 1_018, 1_017, 855, 1_033),              # H3 sum of score
    "score_from_events": (760, 759, 760, 612, 760),                      # C5 follow-up
    "coach_zero":        (80, 45, 17, 34, 52),                           # H3 coachId == 0
    "substitutions":     (2_195, 2_083, 2_221, 1_769, 2_155),            # H4
    "sub_in_zero":       (0, 0, 8, 0, 0),                                # H4 playerIn == 0
    "sub_out_bench":     (1, 3, 3, 2, 0),                                # H4 out, not a starter
    "sheet_reds":        (71, 39, 91, 43, 87),                           # I2 redCards entries
    "lineups":           (10_555, 10_443, 10_573, 8_501, 10_515),        # I1 lineups rows
}
LEAGUES = ("Spain", "England", "Italy", "Germany", "France")


def audit(league: str) -> dict[str, int]:
    return {name: values[LEAGUES.index(league)] for name, values in AUDIT.items()}


def built(league: str) -> sidecar.SidecarManifest:
    try:
        return sidecar.manifest(league)
    except sidecar.SidecarMissing:
        pytest.skip(f"tag sidecar not built for {league}")


@pytest.fixture
def league_given_back():
    """A corpus test holds the tables of a whole league. When it ends, what it held goes
    back to the system, so the session does not carry one league into the next test."""
    yield
    gc.collect()
    pa.default_memory_pool().release_unused()


def tag_counts(tags: pd.Series) -> dict[int, int]:
    """Events carrying each tag id. A list holds an id once, so occurrences are events."""
    ids, counts = np.unique(np.concatenate(tags.to_numpy()), return_counts=True)
    return dict(zip(ids.tolist(), counts.tolist(), strict=True))


def goals_from_events(actions: pd.DataFrame, events: pd.DataFrame,
                      matches: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Per side (every home side, then every away side): goals counted from events, and the
    score on the sheet. A side's goals are its scoring events plus the other side's own goals.
    """
    joined = sidecar.attach(actions, events, ["goal_on_scoring_event", "own_goal"])
    assert joined.event_id.equals(actions.event_id)
    assert list(joined.columns) == [*actions.columns, "goal_on_scoring_event", "own_goal"]
    scored = joined[joined.goal_on_scoring_event].groupby(["game_id", "team_id"]).size()
    conceded_own = joined[joined.own_goal].groupby(["game_id", "team_id"]).size()
    games = [*matches.game_id, *matches.game_id]
    sides = [*matches.home_team_id, *matches.away_team_id]
    others = [*matches.away_team_id, *matches.home_team_id]

    def per_side(counts: pd.Series, teams: list) -> np.ndarray:
        return counts.reindex(pd.MultiIndex.from_arrays([games, teams]), fill_value=0).to_numpy()

    on_sheet = np.array([*matches.home_score, *matches.away_score])
    return per_side(scored, sides) + per_side(conceded_own, others), on_sheet


def assert_sidecar_matches_the_audit(league: str, public: Path) -> None:
    pinned, made = audit(league), built(league)
    sidecar.verify(league)  # first, and alone: it reads every table whole
    directory = public / f"competition={league}"
    events = sidecar.load(league, "events")
    actions = pd.read_parquet(directory / "actions.parquet",
                              columns=["event_id", "game_id", "team_id", "type", "goal"])

    # The same events as the neutral frame, each once.
    assert len(events) == len(actions) == pinned["events"] == made.row_counts["events"]
    assert events.event_id.is_unique and set(events.event_id) == set(actions.event_id)
    assert made.actions_event_ids_equal is True
    assert made.anomalies["events_without_position"] == 0
    assert made.anomalies["unknown_tag_ids"] == 0

    # Identity and coordinates.
    assert int((~events.player_attributed).sum()) == pinned["player_id_zero"]
    assert int((events.sub_event_id == 0).sum()) == pinned["offside"]
    assert set(events.n_positions) == {1, 2} and not events.shootout.any()
    assert int(events.start_at_corner.sum()) == pinned["start_corner"]
    # The audit counted end corners in the neutral frame, where a lone position is copied
    # to the end. No lone position is a corner, so both counts are the same rows.
    assert not (events.start_at_corner & (events.n_positions == 1)).any()
    assert int(events.end_at_corner.sum()) == pinned["end_corner"]

    # Counted on `tags`, not on the derived columns: their precedence may merge tags that
    # meet on one event.
    seen = tag_counts(events.tags)
    assert set(seen) == sidecar.LIVE_TAGS  # all 57 in every league, and neither dead tag
    assert (seen[703], seen[702], seen[701]) == (pinned["won"], pinned["neutral"], pinned["lost"])
    assert (seen[1701], seen[1702], seen[1703]) == (
        pinned["red"], pinned["yellow"], pinned["second_yellow"])
    assert int(events.own_goal.sum()) == seen[102] == pinned["own_goal"]
    # In these five files no event carries two tags of one family, so each named column
    # is its tag and nothing else.
    assert [made.anomalies[name] for name in (
        "multi_body_part", "multi_duel_outcome", "multi_goal_zone")] == [0, 0, 0]
    assert events.duel_outcome.value_counts().to_dict() == {
        "lost": pinned["lost"], "won": pinned["won"], "neutral": pinned["neutral"]}
    assert events.body_part.value_counts().to_dict() == {name: pinned[name] for name in (
        "right_foot", "left_foot", "head_or_body")}
    assert events.card.value_counts().to_dict() == {
        "yellow_card": pinned["yellow"], "red_card": pinned["red"],
        "second_yellow": pinned["second_yellow"]}
    assert (int(events.fk_direct.eq(True).sum()), int(events.fk_direct.eq(False).sum())) == (
        seen[1101], seen[1102])  # never both on one event

    # The neutral goal column is the tag, the conceding keeper's row included. The sidecar
    # column leaves the keeper out.
    assert int(actions.goal.sum()) == seen[101] == pinned["goal_tag"]
    assert int(actions.goal[actions.type == "save"].sum()) == pinned["goal_tag_on_save"]
    assert int(events.goal_on_scoring_event.sum()) == (
        pinned["goal_tag"] - pinned["goal_tag_on_save"])

    on_shots = events[events.shot_family.notna()]
    assert events.shot_family.value_counts().to_dict() == {
        "open_play": pinned["open_play_shots"], "free_kick": pinned["free_kick_shots"],
        "penalty": pinned["penalties"]}
    assert on_shots.body_part.notna().all()
    assert set(on_shots.shot_outcome) <= OUTCOMES and on_shots.shot_outcome.notna().all()
    assert events.shot_outcome[events.shot_family.isna()].isna().all()
    assert int((on_shots.shot_outcome == "goal").sum()) == pinned["shot_goals"]
    assert int(on_shots.blocked.sum()) == pinned["shots_blocked"]

    matches = sidecar.load(league, "matches")
    assert len(matches) == pinned["matches"] == made.row_counts["matches"]
    assert int(matches.home_score.sum() + matches.away_score.sum()) == pinned["goals"]
    assert int(matches.winner_agrees_with_score.sum()) == pinned["winner_agrees"]
    assert made.anomalies["winner_disagrees_with_score"] == (
        pinned["matches"] - pinned["winner_agrees"])
    assert int(matches.home_coach_id.isna().sum() + matches.away_coach_id.isna().sum()) == (
        pinned["coach_zero"])
    assert set(matches.duration) == {"Regular"}

    # The sanctioned join on the whole league, and what it is for: every team-match score
    # rebuilt from event facts. The audit found one goal of the sheets with no event
    # (England), and none the other way.
    from_events, on_sheet = goals_from_events(actions, events, matches)
    assert int((from_events == on_sheet).sum()) == pinned["score_from_events"]
    assert not (from_events > on_sheet).any()

    squads = sidecar.load(league, "squads")
    roles = squads.role.value_counts().to_dict()
    assert roles["start"] == 11 * 2 * pinned["matches"]
    assert roles["sub_used"] == pinned["substitutions"] - pinned["sub_in_zero"]
    assert int(squads.minute_off.notna().sum()) == pinned["substitutions"]
    assert made.anomalies["sub_in_unattributed"] == pinned["sub_in_zero"]
    assert made.anomalies["sub_out_not_starter"] == pinned["sub_out_bench"]
    assert int(squads.red_minute.notna().sum()) == pinned["sheet_reds"]
    lineups = pd.read_parquet(directory / "lineups.parquet", columns=["game_id", "player_id"])
    on_pitch = squads[squads.role.isin(["start", "sub_used"])]
    assert len(lineups) == len(on_pitch) == pinned["lineups"]
    assert set(zip(on_pitch.game_id, on_pitch.player_id, strict=True)) == set(
        zip(lineups.game_id, lineups.player_id, strict=True))
    assert not squads.duplicated(["game_id", "team_id", "player_id"]).any()
    assert set(squads.game_id) == set(matches.game_id) == set(
        pd.read_parquet(directory / "matches.parquet", columns=["game_id"]).game_id)


@pytest.mark.slow
def test_spain_sidecar_matches_the_audit(corpus_root, league_given_back):
    """The pins of the specification, as the audit states them. All of them hold.

    own goals 30; events whose tags contain 703 / 702 / 701: 66,790 / 38,050 / 66,983;
    1701 / 1702 / 1703: 29 / 1,863 / 42; no event without a position; 8,360 starters and
    2,195 used substitutes, the same (match, player) set as lineups.parquet; 1,024 goals;
    the winner field disagrees with the score on exactly one match.
    """
    pinned = audit("Spain")
    assert (pinned["own_goal"], pinned["won"], pinned["neutral"], pinned["lost"]) == (
        30, 66_790, 38_050, 66_983)
    assert (pinned["red"], pinned["yellow"], pinned["second_yellow"]) == (29, 1_863, 42)
    assert 11 * 2 * pinned["matches"] == 8_360 and pinned["substitutions"] == 2_195
    assert pinned["goals"] == 1_024 and pinned["matches"] - pinned["winner_agrees"] == 1
    assert_sidecar_matches_the_audit("Spain", corpus_root)


@pytest.mark.slow
@pytest.mark.parametrize("league", LEAGUES[1:])
def test_the_other_audited_leagues_match_the_audit_too(league, league_available, corpus_root,
                                                       league_given_back):
    league_available(league)
    assert_sidecar_matches_the_audit(league, corpus_root)


@pytest.mark.slow
@pytest.mark.parametrize("cup", ["European_Championship", "World_Cup"])
def test_cup_sidecars_say_what_happened_after_ninety_minutes(cup, league_available, corpus_root,
                                                             league_given_back):
    """Relations the two cup files have to satisfy. The audit covered the leagues only.

    A match that went to extra time or to a shootout keeps the score it had before extra
    time, so its winner field cannot agree with that score. Shootout kicks are rows of
    exactly the matches the sheet says went to penalties, and none of them is a goal of
    the match.
    """
    league_available(cup)
    made = built(cup)
    sidecar.verify(cup)
    events = sidecar.load(cup, "events")
    matches = sidecar.load(cup, "matches")
    actions = pd.read_parquet(corpus_root / f"competition={cup}" / "actions.parquet",
                              columns=["event_id", "game_id", "team_id"])
    assert made.actions_event_ids_equal is True
    assert events.event_id.is_unique and set(events.event_id) == set(actions.event_id)
    assert [made.anomalies[name] for name in (
        "events_without_position", "unknown_tag_ids", "multi_body_part", "multi_duel_outcome",
        "multi_goal_zone", "sub_in_unattributed", "subs_not_recorded_team_matches")] == [0] * 7

    regular = (matches.duration == "Regular").to_numpy()
    assert set(matches.duration) == {"Regular", "ExtraTime", "Penalties"}
    assert (matches.winner_agrees_with_score.to_numpy() == regular).all()
    assert matches.winner_team_id.notna().to_numpy()[~regular].all()
    assert made.anomalies["winner_disagrees_with_score"] == int((~regular).sum()) > 0

    kicks = events[events.shootout]
    assert set(kicks.game_id) == set(matches.game_id[matches.duration == "Penalties"])
    assert not kicks.goal_on_scoring_event.any()
    assert set(kicks.shot_family.dropna()) == {"penalty"}
    assert {"goal"} < set(kicks.shot_outcome.dropna())  # some went in, some did not

    from_events, on_sheet = goals_from_events(actions, events, matches)
    in_ninety = np.concatenate([regular, regular])
    assert (from_events[in_ninety] == on_sheet[in_ninety]).all()
    assert (from_events[~in_ninety] >= on_sheet[~in_ninety]).all()
    assert (from_events[~in_ninety] > on_sheet[~in_ninety]).any()  # goals of extra time


@pytest.mark.slow
def test_the_tag_dictionary_is_the_providers(corpus_root):
    dictionary = sidecar.RAW_ROOT / "tags2name.csv"
    if not dictionary.is_file():
        pytest.skip("raw provider files not downloaded")
    listed = pd.read_csv(dictionary)
    assert set(listed.Tag) == sidecar.LIVE_TAGS | sidecar.DEAD_TAGS and len(listed) == 59
    labels = dict(zip(listed.Tag, listed.Label, strict=True))
    assert {tag: labels[tag] for tag in sidecar.GOAL_ZONE} == sidecar.GOAL_ZONE


@pytest.mark.slow
def test_building_the_sidecar_leaves_competition_directories_untouched(corpus_root, tmp_path,
                                                                       league_given_back):
    if not (sidecar.RAW_ROOT / "events_Spain.json").is_file():
        pytest.skip("raw provider files not downloaded")
    directory = corpus_root / "competition=Spain"
    before = sha256_of_files(directory)
    assert sorted(before) == ["actions.parquet", "lineups.parquet", "matches.parquet"]
    fresh = sidecar.write_sidecar("Spain", out_root=tmp_path / "v1")
    assert sha256_of_files(directory) == before
    assert sorted(path.name for path in directory.iterdir()) == sorted(before)
    assert fresh.actions_event_ids_equal is True
    sidecar.verify("Spain", root=tmp_path / "v1")
    # The same raw bytes and the same builder give the same content, wherever it is written.
    try:
        standing = sidecar.manifest("Spain")
    except sidecar.SidecarMissing:
        return
    assert standing.raw_digests == fresh.raw_digests
    if (standing.builder_source_hash, standing.packages) == (
            fresh.builder_source_hash, fresh.packages):
        assert standing == fresh


def test_the_build_counts_events_that_carry_two_tags_of_one_family(tmp_path):
    events = [
        tagged(401, 402, id=1),            # two body parts
        tagged(401, 402, 403, id=2),       # three: still one event
        tagged(701, 703, id=3),            # two duel outcomes
        tagged(1201, 1210, id=4),          # two zones of different classes
        tagged(1201, 1202, id=5),          # two zones of one class
        tagged(1203, 1217, 1219, id=6),    # three zones
        tagged(401, 703, 1203, id=7),      # one of each: nothing to count
        tagged(1101, 1102, id=8),          # the pair with no counter
    ]
    made, root = build(tmp_path, events=events)
    counted = {name: made.anomalies[name] for name in (
        "multi_body_part", "multi_duel_outcome", "multi_goal_zone")}
    assert counted == {"multi_body_part": 2, "multi_duel_outcome": 1, "multi_goal_zone": 3}
    stored = sidecar.load("Spain", "events", root=root)
    both = stored[stored.event_id == 8].iloc[0]
    assert pd.isna(both.fk_direct) and [int(tag) for tag in both.tags] == [1101, 1102]
