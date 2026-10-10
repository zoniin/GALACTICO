"""The Wyscout tag sidecar: provider facts the neutral adapter drops, keyed by ``event_id``.

Claim: for one competition of the public corpus, three tables that hold what
``galactico.providers.pappalardo`` reads past, as the provider recorded it.

``events``   one row per raw event that has a position. That is the adapter's own rule
             for a row of ``actions.parquet``, so the two ``event_id`` sets are equal. The
             build compares them when the actions file is present and refuses to finish
             when they differ.
``matches``  the match sheet: kick-off time, the score and the half-time score, the
             provider's winner field, the duration, the coach ids.
``squads``   one row per player the sheet lists, the bench players who never came on
             included.

Every tag id on an event survives in ``tags``, whether the provider's dictionary knows it
or not (an id that does not fit int16 stops the build; none is dropped). A named column
says what one tag, or one family of tags, says. Where a family should hold one tag and an
event carries two, the named column is null and both tags are still in ``tags``. For body
part, duel outcome and goal zone the build also counts the event; for the direct and
indirect free-kick pair it does not. Two columns choose instead, and say so: ``card`` and
``shot_outcome`` take the precedence Match Lab already serves, so a card or a shot has one
label in both places.

Non-claim: no column here is a construct. ``success``, ``goal`` and ``clearance`` in
``actions.parquet`` are not reinterpreted or repaired, and nothing is written under the
neutral frames tree: ``scripts/build_profiles.py`` hashes every Parquet file it finds in
``competition=Spain/`` into the dataset hash of the Player Lab bundle, so a file added
there would change that hash. ``opportunity`` is the provider's judgement and not a
probability. ``head_or_body`` is the provider's class and not "header". ``blocked`` sits on
the attacker's event and names no blocker. A ``sub_unused`` row of a side whose
substitutions were not recorded is not evidence that the player stayed on the bench.
There is no minutes column: a corrected minute would be a new definition with its own
validation.

``attach`` is the only sanctioned join. ``load`` checks the manifest and the row count and
hashes nothing. ``verify`` recomputes the content hashes; it is for tests and the build
script, not for a request handler.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from galactico.providers.base import LicenseViolation, assert_may_host
from galactico.providers.pappalardo import COMPETITIONS
from galactico.storage.public import PUBLIC
from galactico.validation.digests import lf_sha256

__all__ = [
    "SIDECAR_SCHEMA_VERSION",
    "TAG_MAPPING_VERSION",
    "RAW_ROOT",
    "SIDECAR_ROOT",
    "TABLES",
    "SORT_KEYS",
    "LIVE_TAGS",
    "DEAD_TAGS",
    "GOAL_ZONE",
    "SidecarMissing",
    "SidecarStale",
    "SidecarMismatch",
    "SidecarManifest",
    "iter_raw_events",
    "event_row",
    "event_frame",
    "match_frame",
    "squad_frame",
    "shot_outcome",
    "content_hash",
    "write_sidecar",
    "manifest",
    "load",
    "verify",
    "attach",
    "provenance",
]

SIDECAR_SCHEMA_VERSION = "wyscout-tag-sidecar-v1"
TAG_MAPPING_VERSION = "wyscout-v2-tags2name-57live-v1"
PROVIDER = "pappalardo"
ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT: Path = ROOT / "data/public/pappalardo"
SIDECAR_ROOT: Path = ROOT / "data/public/sidecar/pappalardo/v1"
TABLES: tuple[str, ...] = ("events", "matches", "squads")
SORT_KEYS: dict[str, tuple[str, ...]] = {
    "events": ("event_id",), "matches": ("game_id",),
    "squads": ("game_id", "team_id", "player_id"),
}
MANIFEST_NAME = "MANIFEST.json"
# Rows held as Python objects before they are handed to the Parquet writer.
CHUNK_ROWS = 100_000

# The provider's tag dictionary (tags2name.csv) lists 59 ids. These 57 are each on at least
# one event of every one of the five leagues.
LIVE_TAGS: frozenset[int] = frozenset({
    101, 102, 201, 301, 302, 401, 402, 403, 501, 502, 503, 504, 601, 602, 701, 702, 703,
    801, 901, 1001, 1101, 1102, *range(1201, 1224), 1301, 1302, 1401, 1601, 1701, 1702,
    1703, 1801, 1802, 1901, 2001, 2101,
})
# The other two, "low" and "clearance", are on no event of those leagues. No column reads
# them.
DEAD_TAGS: frozenset[int] = frozenset({802, 1501})
# Where the ball went, in the provider's own labels: g in the goal, o out, p on the post.
GOAL_ZONE: dict[int, str] = {
    1201: "gb", 1202: "gbr", 1203: "gc", 1204: "gl", 1205: "glb", 1206: "gr", 1207: "gt",
    1208: "gtl", 1209: "gtr", 1210: "obr", 1211: "ol", 1212: "olb", 1213: "or", 1214: "ot",
    1215: "otl", 1216: "otr", 1217: "pbr", 1218: "pl", 1219: "plb", 1220: "pr", 1221: "pt",
    1222: "ptl", 1223: "ptr",
}

_KNOWN_TAGS = LIVE_TAGS | DEAD_TAGS
_BODY_PART = ((401, "left_foot"), (402, "right_foot"), (403, "head_or_body"))
_DUEL_OUTCOME = ((703, "won"), (702, "neutral"), (701, "lost"))
# In precedence order: the first tag present names the card (match_lab.service._enrich).
_CARD = ((1703, "second_yellow"), (1701, "red_card"), (1702, "yellow_card"))
# The two corners the flags look for. A flag states the raw coordinate; it is not a
# judgement that the coordinate is a placeholder.
_CORNERS = ((0, 0), (100, 100))
_SAVE_ATTEMPT = 9
_OPEN_PLAY_SHOT = 10
_FREE_KICK_SHOT = 33
_PENALTY = 35
_BETWEEN_ITEMS = " \r\n\t,"

# What a build counts and records under ``anomalies`` in its manifest.
_EVENT_ANOMALIES = (
    "events_without_position",  # raw events left out, as the adapter leaves them out
    "multi_body_part",          # events carrying two or more of 401, 402, 403
    "multi_duel_outcome",       # events carrying two or more of 701, 702, 703
    "multi_goal_zone",          # events carrying two or more of 1201-1223
    "unknown_tag_ids",          # (event, tag id) pairs in tags whose id no dictionary entry has
)
_SQUAD_ANOMALIES = (
    "sub_in_unattributed",             # substitutions whose incoming player id is 0
    "sub_out_not_starter",             # substitutions that take off a player who had come on
    "subs_not_recorded_team_matches",  # sides whose raw substitutions field is not a list
)
# The last one: matches whose winner_agrees_with_score is false.
_ANOMALIES = (*_EVENT_ANOMALIES, *_SQUAD_ANOMALIES, "winner_disagrees_with_score")


class SidecarMissing(FileNotFoundError):
    """A table or the manifest is absent: the sidecar was not built, or not to the end."""


class SidecarStale(RuntimeError):
    """The manifest was written under a schema version other than this module's."""


class SidecarMismatch(RuntimeError):
    """What is on disk is not what the manifest records, or a join is not one-to-one."""


@dataclass(frozen=True)
class SidecarManifest:
    """What one build wrote. It is written last, so its presence means the build finished.

    ``content_hashes`` hash the rows (``content_hash``), not the files: the footer of a
    Parquet file names the libraries that wrote it, so the bytes of a file are not a
    statement about its rows. ``packages`` records the versions the row hashes were
    computed under; it is informational and is not hashed.
    """

    sidecar_schema_version: str
    tag_mapping_version: str
    provider: str
    tier: str
    attribution: str
    competition: str
    raw_digests: dict[str, str]
    content_hashes: dict[str, str]
    row_counts: dict[str, int]
    anomalies: dict[str, int]
    actions_event_ids_equal: bool | None
    builder_source_hash: str
    packages: dict[str, str]


# --------------------------------------------------------------------------- schemas

def _schema(fields: Sequence[pa.Field], nullable_as: Mapping[str, str]) -> pa.Schema:
    """The Arrow schema, carrying the pandas dtype each nullable non-text column reads as.

    Without it ``pd.read_parquet`` chooses by content: a nullable boolean comes back as
    ``object`` when a null is present and as ``bool`` when none is, a nullable integer as
    ``float64`` or as its integer type. A column whose dtype depends on the rows of the
    day is a trap for every reader, so the file says which dtype it is.
    """
    bare = pa.schema(fields)
    typed = bare.empty_table().to_pandas().astype(dict(nullable_as))
    return pa.Table.from_pandas(typed, schema=bare, preserve_index=False).schema


def _required(name: str, kind: pa.DataType) -> pa.Field:
    return pa.field(name, kind, nullable=False)


EVENT_SCHEMA: pa.Schema = _schema([
    _required("event_id", pa.int64()),            # raw id; unique; the join key
    _required("game_id", pa.int64()),             # raw match id
    _required("sub_event_id", pa.int16()),        # 0 where the raw field is blank (offside)
    _required("n_positions", pa.int8()),          # with 1 the adapter copied start to end
    _required("start_at_corner", pa.bool_()),     # raw start is (0,0) or (100,100)
    _required("end_at_corner", pa.bool_()),       # a second position exists and is one of them
    _required("player_attributed", pa.bool_()),   # raw player id is not 0
    _required("shootout", pa.bool_()),            # raw period is "P"
    _required("tags", pa.list_(pa.int16())),      # every tag id, ascending, each once
    _required("goal_on_scoring_event", pa.bool_()),  # 101, not on a save attempt, not shootout
    _required("own_goal", pa.bool_()),            # 102
    _required("opportunity", pa.bool_()),         # 201
    pa.field("body_part", pa.string()),           # 401 / 402 / 403; null for none or several
    _required("free_space", pa.bool_()),          # 501 or 502
    _required("take_on", pa.bool_()),             # 503 or 504
    _required("anticipated", pa.bool_()),         # 601
    _required("anticipation", pa.bool_()),        # 602
    pa.field("duel_outcome", pa.string()),        # 703 / 702 / 701; null for none or several
    _required("high", pa.bool_()),                # 801
    _required("through", pa.bool_()),             # 901
    _required("fairplay", pa.bool_()),            # 1001
    pa.field("fk_direct", pa.bool_()),            # 1101 true, 1102 false; null for none or both
    pa.field("goal_zone", pa.string()),           # the one 1201-1223 tag; null for none or several
    pa.field("goal_zone_class", pa.string()),     # in_frame / out / post of that one tag
    _required("feint", pa.bool_()),               # 1301
    _required("missed_ball", pa.bool_()),         # 1302
    _required("sliding_tackle", pa.bool_()),      # 1601
    pa.field("card", pa.string()),                # 1703 over 1701 over 1702
    _required("blocked", pa.bool_()),             # 2101
    pa.field("shot_family", pa.string()),         # open_play / free_kick / penalty
    pa.field("shot_outcome", pa.string()),        # shot_outcome(tags) where shot_family is set
], {"fk_direct": "boolean"})

MATCH_SCHEMA: pa.Schema = _schema([
    _required("game_id", pa.int64()),
    _required("competition", pa.string()),
    _required("date_utc", pa.string()),           # raw text; order by this, not by gameweek
    _required("gameweek", pa.int16()),
    _required("home_team_id", pa.int64()),
    _required("away_team_id", pa.int64()),
    _required("home_score", pa.int16()),          # the raw score field, as the sheet has it
    _required("away_score", pa.int16()),
    _required("home_score_ht", pa.int16()),
    _required("away_score_ht", pa.int16()),
    pa.field("winner_team_id", pa.int64()),       # null where the raw value is 0
    _required("winner_agrees_with_score", pa.bool_()),
    _required("duration", pa.string()),
    pa.field("home_coach_id", pa.int64()),        # null where the raw value is 0
    pa.field("away_coach_id", pa.int64()),
], {"winner_team_id": "Int64", "home_coach_id": "Int64", "away_coach_id": "Int64"})

SQUAD_SCHEMA: pa.Schema = _schema([
    _required("game_id", pa.int64()),
    _required("team_id", pa.int64()),
    _required("player_id", pa.int64()),
    _required("role", pa.string()),               # start / sub_used / sub_unused
    pa.field("minute_on", pa.int16()),            # 0 for start; null for sub_unused
    pa.field("minute_off", pa.int16()),           # the substitution minute; never a dismissal
    pa.field("yellow_minute", pa.int16()),        # the sheet's card field; null where it is 0
    pa.field("red_minute", pa.int16()),
    _required("subs_recorded", pa.bool_()),       # false: the raw substitutions are not a list
], {"minute_on": "Int16", "minute_off": "Int16", "yellow_minute": "Int16", "red_minute": "Int16"})

_SCHEMAS: dict[str, pa.Schema] = {
    "events": EVENT_SCHEMA, "matches": MATCH_SCHEMA, "squads": SQUAD_SCHEMA}
_EVENT_COLUMNS: tuple[str, ...] = tuple(EVENT_SCHEMA.names)


def _columns(table: str) -> tuple[str, ...]:
    if table not in _SCHEMAS:
        raise ValueError(f"unknown table: {table!r}; the sidecar tables are {list(TABLES)!r}")
    return tuple(_SCHEMAS[table].names)


def _known_competition(competition: str) -> None:
    if competition not in COMPETITIONS:
        raise ValueError(f"unknown competition: {competition!r}")


def _as_read(table: pa.Table) -> pd.DataFrame:
    """The frame ``pd.read_parquet`` returns for ``table``.

    Frames built in memory and frames loaded from disk go through the same conversion, so
    they agree dtype for dtype by construction and hash alike.
    """
    sink = io.BytesIO()
    pq.write_table(table, sink)
    sink.seek(0)
    return pd.read_parquet(sink)


# ---------------------------------------------------------------------------- events

def _array_items(text: str, source: object) -> Iterator[Any]:
    decode = json.JSONDecoder().raw_decode
    size = len(text)
    at = 0
    while at < size and text[at] in " \r\n\t":
        at += 1
    if at >= size or text[at] != "[":
        raise ValueError(f"{source} is not a JSON array")
    at += 1
    while True:
        while at < size and text[at] in _BETWEEN_ITEMS:
            at += 1
        if at >= size:
            raise ValueError(f"{source} ends before the array is closed")
        if text[at] == "]":
            break
        item, at = decode(text, at)
        yield item
    if text[at + 1:].strip():
        raise ValueError(f"{source} has data after the array")


def iter_raw_events(path: Path) -> Iterator[dict]:
    """The items of the top-level array of a raw events file, one at a time.

    The text is held whole and each event is decoded when it is asked for, so the events
    never exist all at once as Python objects, which is what ``json.load`` of the same
    file returns. Reading the file holds its bytes and its text together for a moment:
    the peak is two copies of the file, then one.

    It reads a file that is one JSON array and yields what ``json.load`` would return for
    it. It is not a validator: between items it skips commas and whitespace without
    counting them. It does refuse a file whose top level is not an array, one that ends
    before the closing bracket, and one with anything after it.
    """
    yield from _array_items(Path(path).read_text(encoding="utf-8"), path)


def _one_of(tags: Collection[int], family: Sequence[tuple[int, str]]) -> tuple[str | None, bool]:
    """The label of the family's one tag on the event, and whether there were several."""
    found = [label for tag, label in family if tag in tags]
    return (found[0] if len(found) == 1 else None), len(found) > 1


def _at_corner(position: Mapping[str, Any]) -> bool:
    return (position.get("x"), position.get("y")) in _CORNERS


def _zone_class(tag: int) -> str:
    return "in_frame" if tag <= 1209 else "out" if tag <= 1216 else "post"


def shot_outcome(tags: Collection[int]) -> str:
    """One label for a shot from its tags: goal, then blocked, then where the ball went.

    ``goal`` (101) over ``blocked`` (2101) over ``woodwork`` (1217-1223) over ``off_target``
    (1210-1216) over ``on_target_not_goal`` (1201-1209), else ``not_goal``. The precedence
    and the labels are those of ``match_lab.service._enrich``, which computes the same
    thing from the raw file at request time; a test holds the two together.
    """
    if 101 in tags:
        return "goal"
    if 2101 in tags:
        return "blocked"
    if any(1217 <= tag <= 1223 for tag in tags):
        return "woodwork"
    if any(1210 <= tag <= 1216 for tag in tags):
        return "off_target"
    if any(1201 <= tag <= 1209 for tag in tags):
        return "on_target_not_goal"
    return "not_goal"


def _event_values(event: Mapping[str, Any], counts: dict[str, int] | None) -> tuple | None:
    """The cells of one ``events`` row in schema order, or None for an event with no position.

    The one definition behind ``event_row``, ``event_frame`` and the build. ``counts``,
    when given, receives the anomalies this event shows.
    """
    positions = event.get("positions") or []
    if not positions:
        return None
    ordered = sorted({int(tag["id"]) for tag in event.get("tags") or []})
    if ordered and not -32768 <= ordered[0] <= ordered[-1] <= 32767:
        raise ValueError(f"event {event.get('id')}: a tag id outside int16 cannot be stored "
                         f"in tags: {ordered}")
    tags = frozenset(ordered)
    kind = int(event["eventId"])
    sub = event.get("subEventId")
    sub_event_id = int(sub) if sub is not None and str(sub).strip() else 0
    shootout = event.get("matchPeriod") == "P"

    body_part, several_body_parts = _one_of(tags, _BODY_PART)
    duel_outcome, several_duel_outcomes = _one_of(tags, _DUEL_OUTCOME)
    zones = [tag for tag in ordered if 1201 <= tag <= 1223]
    zone = zones[0] if len(zones) == 1 else None
    direct, indirect = 1101 in tags, 1102 in tags
    family = ("open_play" if kind == _OPEN_PLAY_SHOT
              else "free_kick" if sub_event_id == _FREE_KICK_SHOT
              else "penalty" if sub_event_id == _PENALTY
              else None)

    if counts is not None:
        if several_body_parts:
            counts["multi_body_part"] += 1
        if several_duel_outcomes:
            counts["multi_duel_outcome"] += 1
        if len(zones) > 1:
            counts["multi_goal_zone"] += 1
        if not tags <= _KNOWN_TAGS:
            counts["unknown_tag_ids"] += len(tags - _KNOWN_TAGS)

    return (
        int(event["id"]),
        int(event["matchId"]),
        sub_event_id,
        len(positions),
        _at_corner(positions[0]),
        len(positions) > 1 and _at_corner(positions[1]),
        int(event["playerId"]) != 0,
        shootout,
        ordered,
        101 in tags and kind != _SAVE_ATTEMPT and not shootout,
        102 in tags,
        201 in tags,
        body_part,
        501 in tags or 502 in tags,
        503 in tags or 504 in tags,
        601 in tags,
        602 in tags,
        duel_outcome,
        801 in tags,
        901 in tags,
        1001 in tags,
        None if direct == indirect else direct,
        None if zone is None else GOAL_ZONE[zone],
        None if zone is None else _zone_class(zone),
        1301 in tags,
        1302 in tags,
        1601 in tags,
        next((label for tag, label in _CARD if tag in tags), None),
        2101 in tags,
        family,
        None if family is None else shot_outcome(tags),
    )


def event_row(event: Mapping[str, object]) -> dict[str, object] | None:
    """One ``events`` row for a raw event, or None when its position list is empty.

    None is the adapter's rule (``PappalardoProvider._iter_actions`` skips such an event),
    which is what keeps the sidecar and ``actions.parquet`` on the same ``event_id`` set.
    ``tags`` is a list of ints here and an int16 array once it is in a frame.
    """
    values = _event_values(event, None)
    return None if values is None else dict(zip(_EVENT_COLUMNS, values, strict=True))


def _event_table(rows: Sequence[tuple]) -> pa.Table:
    if not rows:
        return EVENT_SCHEMA.empty_table()
    arrays = [pa.array(column, type=field.type)
              for column, field in zip(zip(*rows, strict=True), EVENT_SCHEMA, strict=True)]
    return pa.Table.from_arrays(arrays, schema=EVENT_SCHEMA)


def event_frame(events: Iterable[Mapping[str, object]]) -> pd.DataFrame:
    """The ``events`` table for any iterable of raw-shaped events, read once, in its order.

    Pure: no file is touched. The columns and dtypes are those ``load`` returns, for zero
    rows as for many. Events without a position are left out, as in ``event_row``.
    """
    rows = [values for event in events if (values := _event_values(event, None)) is not None]
    return _as_read(_event_table(rows))


# ---------------------------------------------------------------------- match sheets

def _match_rows(matches: Iterable[Mapping[str, Any]], competition: str) -> list[dict[str, Any]]:
    rows = []
    for match in matches:
        game_id = int(match["wyId"])
        sides: dict[str, tuple[int, Mapping[str, Any]]] = {}
        listed = (match.get("teamsData") or {}).items()
        for team_id, side in listed:
            sides[str(side.get("side"))] = (int(team_id), side)
        if len(listed) != 2 or set(sides) != {"home", "away"}:
            raise ValueError(f"match {game_id}: the sheet does not have one home and one away "
                             f"side: {[side.get('side') for _, side in listed]}")
        (home_id, home), (away_id, away) = sides["home"], sides["away"]
        home_score, away_score = int(home["score"]), int(away["score"])
        winner = int(match["winner"])
        by_score = (home_id if home_score > away_score
                    else away_id if away_score > home_score else 0)
        rows.append({
            "game_id": game_id,
            "competition": competition,
            "date_utc": match["dateutc"],
            "gameweek": int(match["gameweek"]),
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_score": home_score,
            "away_score": away_score,
            "home_score_ht": int(home["scoreHT"]),
            "away_score_ht": int(away["scoreHT"]),
            "winner_team_id": winner or None,
            "winner_agrees_with_score": winner == by_score,
            "duration": match["duration"],
            "home_coach_id": int(home["coachId"]) or None,
            "away_coach_id": int(away["coachId"]) or None,
        })
    return rows


def match_frame(matches: Iterable[Mapping[str, object]], competition: str) -> pd.DataFrame:
    """The ``matches`` table for raw match sheets, in sheet order.

    ``home_score`` and ``away_score`` are the raw score field. In the five leagues every
    match has duration ``Regular`` and that is the full-time score. A cup match that went
    to extra time or to a shootout carries those in raw fields this table leaves out, so
    there the score columns are not the result and ``duration`` says so.

    ``winner_agrees_with_score`` is true when the raw winner is the side with the larger
    score, or 0 when the scores are level. It is false where the provider's winner field
    contradicts its own score, and also on a match decided after the score this table
    carries. In the leagues, read a result from the scores and not from the winner field.

    The match label is left out on purpose: it contains the final result, and an object
    built before a decision must not carry it.
    """
    rows = _match_rows(matches, competition)
    return _as_read(pa.Table.from_pylist(rows, schema=MATCH_SCHEMA))


def _card_minute(entry: Mapping[str, Any], field: str, where: str) -> int | None:
    try:
        minute = int(entry[field])
    except (TypeError, ValueError) as error:
        raise ValueError(f"{where}: the {field} field {entry.get(field)!r} of player "
                         f"{entry.get('playerId')} is not a minute") from error
    return minute or None


def _squad_rows(matches: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]],
                                                              dict[str, int]]:
    rows: list[dict[str, Any]] = []
    counts = dict.fromkeys(_SQUAD_ANOMALIES, 0)
    for match in matches:
        game_id = int(match["wyId"])
        for team_key, side in (match.get("teamsData") or {}).items():
            team_id = int(team_key)
            where = f"match {game_id}, team {team_id}"
            formation = side.get("formation") or {}
            lineup = formation.get("lineup") or []
            bench = formation.get("bench") or []
            substitutions = formation.get("substitutions")
            recorded = isinstance(substitutions, list)
            if not recorded:
                counts["subs_not_recorded_team_matches"] += 1
            starters = {int(entry["playerId"]) for entry in lineup}
            on_bench = {int(entry["playerId"]) for entry in bench}
            changes = [(int(change["minute"]), int(change["playerIn"]), int(change["playerOut"]))
                       for change in (substitutions if recorded else ())]
            on_at: dict[int, int] = {}
            off_at: dict[int, int] = {}
            for minute, incoming, _ in changes:
                if incoming == 0:
                    counts["sub_in_unattributed"] += 1
                elif incoming not in on_bench:
                    raise ValueError(f"{where}: incoming player {incoming} is neither on the "
                                     f"bench list nor 0")
                elif incoming in on_at:
                    raise ValueError(f"{where}: player {incoming} is named as incoming twice")
                else:
                    on_at[incoming] = minute
            # Who came on is settled first, so the order the sheet lists the changes in does
            # not decide whether a substitute who goes off again is recognised.
            for minute, _, outgoing in changes:
                if outgoing in off_at:
                    raise ValueError(f"{where}: player {outgoing} is named as outgoing twice")
                if outgoing in on_at:
                    counts["sub_out_not_starter"] += 1
                elif outgoing not in starters:
                    raise ValueError(f"{where}: outgoing player {outgoing} neither started "
                                     f"nor came on")
                off_at[outgoing] = minute
            for entries, started in ((lineup, True), (bench, False)):
                for entry in entries:
                    player_id = int(entry["playerId"])
                    if started:
                        role, minute_on = "start", 0
                    elif player_id in on_at:
                        role, minute_on = "sub_used", on_at[player_id]
                    else:
                        role, minute_on = "sub_unused", None
                    rows.append({
                        "game_id": game_id,
                        "team_id": team_id,
                        "player_id": player_id,
                        "role": role,
                        "minute_on": minute_on,
                        "minute_off": off_at.get(player_id),
                        "yellow_minute": _card_minute(entry, "yellowCards", where),
                        "red_minute": _card_minute(entry, "redCards", where),
                        "subs_recorded": recorded,
                    })
    return rows, counts


def squad_frame(matches: Iterable[Mapping[str, object]]) -> pd.DataFrame:
    """The ``squads`` table for raw match sheets: one row per listed player, in sheet order.

    ``start`` is on the starting-eleven list. ``sub_used`` is on the bench list and named
    as the incoming player of a substitution. ``sub_unused`` is on the bench list and never
    named as incoming. ``minute_off`` is the minute of the substitution that names the
    player as outgoing; a dismissal does not set it, and the card minutes are the sheet's
    own fields. Second yellow against straight red is told apart only by ``events.card``.

    A substitution whose incoming id is 0 invents no row: the outgoing player keeps his
    ``minute_off`` and the build counts the record. A substitution this table cannot carry
    raises ``ValueError`` instead of being dropped: an incoming id that is neither 0 nor on
    the bench list, an outgoing player who neither started nor came on, one player named
    twice in one direction. None was met when the seven competition files were built on
    10 October 2026.

    The per-player goal and own-goal fields of the sheet are not carried.
    """
    rows, _ = _squad_rows(matches)
    return _as_read(pa.Table.from_pylist(rows, schema=SQUAD_SCHEMA))


# ------------------------------------------------------------------------------ hash

def content_hash(frame: pd.DataFrame, table: str) -> str:
    """sha256 over the rows of one whole table, whatever order they or the columns come in.

    The frame is put in the table's column order, sorted by ``SORT_KEYS[table]`` and
    reindexed; ``tags`` becomes its ids joined by commas; then it is hashed with the
    ``frame_hash`` recipe of ``galactico.optimization.historical``. Column names are not
    hashed and a projection has no content hash, so the frame must hold exactly the
    table's columns. The sort key must be unique: among equal keys the order of the rows
    would decide the hash.

    Nothing is claimed across pandas versions: the recipe rests on
    ``pd.util.hash_pandas_object``, and the manifest records the versions beside each hash.
    """
    columns = _columns(table)
    if sorted(frame.columns) != sorted(columns):
        raise ValueError(f"{table} is hashed over its columns {list(columns)}; "
                         f"got {list(frame.columns)}")
    keys = list(SORT_KEYS[table])
    if frame.duplicated(keys).any():
        raise ValueError(f"{table}: the sort key {keys} is not unique, so row order would "
                         f"decide the hash")
    ordered = frame.loc[:, list(columns)].sort_values(keys).reset_index(drop=True)
    if "tags" in ordered.columns:
        ordered["tags"] = pd.Series(
            [",".join(str(int(tag)) for tag in tags) for tags in ordered["tags"]], dtype=object)
    hashed = pd.util.hash_pandas_object(ordered, index=False).to_numpy()
    return hashlib.sha256(hashed.tobytes()).hexdigest()


# ----------------------------------------------------------------------------- build

def _inside(path: Path, tree: Path) -> bool:
    """Whether ``path`` is ``tree`` or lies under it, asked of the file system.

    The same directory has more than one spelling (an extended-length prefix, a share of
    the same disk), and ``Path.resolve`` keeps them apart. A path that does not exist yet
    cannot be asked; its existing ancestors can.
    """
    for candidate in (path, *path.parents):
        try:
            if os.path.samefile(candidate, tree):
                return True
        except OSError:
            continue
    return False


def _refuse_neutral_tree(out_root: Path) -> None:
    resolved = out_root.resolve()
    named = [part for part in resolved.parts if part.casefold().startswith("competition=")]
    if named:
        raise ValueError(f"the sidecar is never written under a competition= directory: "
                         f"{out_root} names {named[0]!r}")
    neutral = PUBLIC.resolve().parent
    if resolved == neutral or neutral in resolved.parents or _inside(resolved, neutral):
        raise ValueError(f"the sidecar is never written inside the neutral frames tree "
                         f"{neutral}: {out_root}")


def _write_events(source: Path, target: Path, counts: dict[str, int]) -> str:
    """Stream the raw events into ``target``; return the sha256 of the bytes that were read.

    The digest and the rows come from one read of the file, so the manifest cannot name
    bytes other than those the table was derived from.
    """
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    text = data.decode("utf-8")
    del data
    rows: list[tuple] = []
    wrote = False
    with pq.ParquetWriter(target, EVENT_SCHEMA, compression="zstd") as writer:
        for event in _array_items(text, source):
            values = _event_values(event, counts)
            if values is None:
                counts["events_without_position"] += 1
                continue
            rows.append(values)
            if len(rows) >= CHUNK_ROWS:
                writer.write_table(_event_table(rows))
                rows.clear()
                wrote = True
        if rows or not wrote:
            writer.write_table(_event_table(rows))
    return digest


def _action_event_ids(path: Path) -> np.ndarray:
    """The ``event_id`` column of a neutral actions file, under the public loader's guard.

    ``load_public`` resolves a file from a root and a competition and this takes a file, so
    the rule is restated: every action row read must carry ``provider == "pappalardo"``.
    """
    if "provider" not in pq.read_schema(path).names:
        raise LicenseViolation(f"{path} has no provider column; its origin is unverified")
    actions = pd.read_parquet(path, columns=["event_id", "provider"])
    providers = set(actions["provider"].unique().tolist())
    if providers != {PROVIDER}:
        raise LicenseViolation(f"{path} carries providers {sorted(map(str, providers))!r}; "
                               f"the sidecar is compared with {PROVIDER!r} actions only")
    return actions["event_id"].to_numpy()


def _require_same_event_ids(ours: np.ndarray, theirs: np.ndarray, path: Path) -> None:
    if len(ours) == len(theirs) and np.array_equal(np.sort(ours), np.sort(theirs)):
        return
    only_ours, only_theirs = np.setdiff1d(ours, theirs), np.setdiff1d(theirs, ours)
    raise SidecarMismatch(
        f"the event_id values of the sidecar ({len(ours)} rows) and of {path} "
        f"({len(theirs)} rows) differ: {len(only_ours)} only in the sidecar "
        f"{only_ours[:5].tolist()}, {len(only_theirs)} only in actions "
        f"{only_theirs[:5].tolist()}")


def _packages() -> dict[str, str]:
    return {"numpy": np.__version__, "pandas": pd.__version__, "pyarrow": pa.__version__}


def write_sidecar(competition: str, *, raw_root: Path = RAW_ROOT, out_root: Path = SIDECAR_ROOT,
                  actions_path: Path | None = None) -> SidecarManifest:
    """Build the three tables and the manifest of one competition under ``out_root``.

    The tables are written beside their final names and checked there: each sort key is
    unique, and when ``actions_path`` exists (default: the competition's
    ``actions.parquet`` in the neutral tree) its ``event_id`` values are the sidecar's,
    row for row. Only then is the previous manifest removed, the tables moved into place
    and the new manifest written, last. A build that fails a check leaves what it found.
    One that is interrupted while the tables change hands leaves no manifest, and without
    a manifest there is no sidecar for a reader.

    ``ValueError`` for an unknown competition, for an ``out_root`` under a ``competition=``
    directory or inside ``data/public/parquet``, and for a raw file that is not one JSON
    array; ``FileNotFoundError`` when a raw file is absent; ``SidecarMismatch`` when a key
    repeats or the event ids differ; ``LicenseViolation`` when the actions file does not
    say that every row is the public provider's.
    """
    posture = assert_may_host(PROVIDER)
    _known_competition(competition)
    raw_root, out_root = Path(raw_root), Path(out_root)
    _refuse_neutral_tree(out_root)
    sources = {name: raw_root / f"{name}_{competition}.json" for name in ("events", "matches")}
    absent = [str(path) for path in sources.values() if not path.is_file()]
    if absent:
        raise FileNotFoundError(f"raw files not present: {absent}")
    actions_path = (PUBLIC / f"competition={competition}" / "actions.parquet"
                    if actions_path is None else Path(actions_path))

    directory = out_root / competition
    directory.mkdir(parents=True, exist_ok=True)
    final = {table: directory / f"{table}.parquet" for table in TABLES}
    draft = {table: directory / f"{table}.parquet.{os.getpid()}.tmp" for table in TABLES}
    manifest_path = directory / MANIFEST_NAME
    manifest_draft = directory / f"{MANIFEST_NAME}.{os.getpid()}.tmp"
    try:
        anomalies = dict.fromkeys(_ANOMALIES, 0)
        raw_digests = {"events": _write_events(sources["events"], draft["events"], anomalies)}

        sheet_bytes = sources["matches"].read_bytes()
        raw_digests["matches"] = hashlib.sha256(sheet_bytes).hexdigest()
        sheets = json.loads(sheet_bytes.decode("utf-8"))
        if not isinstance(sheets, list):
            raise ValueError(f"{sources['matches']} is not a JSON array")
        match_rows = _match_rows(sheets, competition)
        squad_rows, squad_anomalies = _squad_rows(sheets)
        anomalies.update(squad_anomalies)
        anomalies["winner_disagrees_with_score"] = sum(
            not row["winner_agrees_with_score"] for row in match_rows)
        pq.write_table(pa.Table.from_pylist(match_rows, schema=MATCH_SCHEMA), draft["matches"],
                       compression="zstd")
        pq.write_table(pa.Table.from_pylist(squad_rows, schema=SQUAD_SCHEMA), draft["squads"],
                       compression="zstd")

        content_hashes: dict[str, str] = {}
        row_counts: dict[str, int] = {}
        event_ids = np.empty(0, dtype=np.int64)
        for table in TABLES:
            frame = pd.read_parquet(draft[table])
            keys = list(SORT_KEYS[table])
            repeated = int(frame.duplicated(keys).sum())
            if repeated:
                raise SidecarMismatch(f"{competition} {table}: {keys} is not unique "
                                      f"({repeated} repeated rows), so the table is not joinable")
            content_hashes[table] = content_hash(frame, table)
            row_counts[table] = len(frame)
            if table == "events":
                event_ids = frame["event_id"].to_numpy()
            del frame

        equal: bool | None = None
        if actions_path.is_file():
            _require_same_event_ids(event_ids, _action_event_ids(actions_path), actions_path)
            equal = True

        made = SidecarManifest(
            sidecar_schema_version=SIDECAR_SCHEMA_VERSION,
            tag_mapping_version=TAG_MAPPING_VERSION,
            provider=PROVIDER,
            tier=posture.tier.name,
            attribution=posture.attribution,
            competition=competition,
            raw_digests=raw_digests,
            content_hashes=content_hashes,
            row_counts=row_counts,
            anomalies=anomalies,
            actions_event_ids_equal=equal,
            builder_source_hash=lf_sha256(__file__),
            packages=_packages(),
        )
        text = json.dumps(asdict(made), indent=2, sort_keys=True) + "\n"
        manifest_draft.write_bytes(text.encode("utf-8"))
        # No manifest while the tables change hands: a reader meets a complete sidecar or
        # none, never the new tables under the old record.
        manifest_path.unlink(missing_ok=True)
        for table in TABLES:
            os.replace(draft[table], final[table])
        os.replace(manifest_draft, manifest_path)
        return made
    finally:
        for leftover in (*draft.values(), manifest_draft):
            leftover.unlink(missing_ok=True)
        # Arrow keeps the memory it has freed. Hand it back, so that a run over several
        # competitions does not carry the last one into the next.
        pa.default_memory_pool().release_unused()


# ------------------------------------------------------------------------------ read

def manifest(competition: str, *, root: Path = SIDECAR_ROOT) -> SidecarManifest:
    """The manifest of one built competition.

    ``SidecarMissing`` when it is absent, ``SidecarStale`` when it was written under
    another schema version, ``SidecarMismatch`` when it is the manifest of another
    competition or does not have this version's fields.
    """
    assert_may_host(PROVIDER)
    _known_competition(competition)
    path = Path(root) / competition / MANIFEST_NAME
    if not path.is_file():
        raise SidecarMissing(f"{path} is absent: the {competition} tag sidecar is not built. "
                             f"Run scripts/build_sidecar.py --only {competition}")
    record = json.loads(path.read_text(encoding="utf-8"))
    found = record.get("sidecar_schema_version") if isinstance(record, dict) else None
    if found != SIDECAR_SCHEMA_VERSION:
        raise SidecarStale(f"{path} was written as {found!r}; this module reads "
                           f"{SIDECAR_SCHEMA_VERSION!r}. Rebuild the sidecar")
    try:
        made = SidecarManifest(**record)
    except TypeError as error:
        raise SidecarMismatch(f"{path} does not have the fields of a manifest: {error}") from error
    if made.competition != competition:
        raise SidecarMismatch(f"{path} is the manifest of {made.competition!r}, "
                              f"not of {competition!r}")
    return made


def _names(columns: Sequence[str], known: Sequence[str], table: str) -> list[str]:
    # A str is a Sequence[str] of its letters: columns="event_id" would ask for e, v, e...
    if isinstance(columns, (str, bytes)):
        raise TypeError(f"columns takes a sequence of names, not one string: {columns!r}")
    wanted = list(columns)
    if not wanted:
        raise ValueError("columns is empty; pass None to read every column")
    if len(set(wanted)) != len(wanted):
        raise ValueError(f"columns names a column twice: {wanted!r}")
    unknown = [name for name in wanted if name not in known]
    if unknown:
        raise ValueError(f"unknown column: {unknown!r}; {table} has {list(known)!r}")
    return wanted


def load(competition: str, table: str, *, columns: Sequence[str] | None = None,
         root: Path = SIDECAR_ROOT) -> pd.DataFrame:
    """One table of one built competition, or the named columns of it in the named order.

    The hosting guard runs before anything is read. ``SidecarMissing`` when the manifest
    or the table is absent, ``SidecarStale`` for another schema version, ``ValueError``
    for an unknown competition, table or column, ``SidecarMismatch`` when the table does
    not hold the number of rows the manifest records. Nothing is hashed here: a table
    with the right number of wrong rows is ``verify``'s to find.
    """
    assert_may_host(PROVIDER)
    known = _columns(table)
    _known_competition(competition)
    directory = Path(root) / competition
    path = directory / f"{table}.parquet"
    if (directory / MANIFEST_NAME).is_file() and not path.is_file():
        raise SidecarMissing(f"{path} is absent although {MANIFEST_NAME} is present. "
                             f"Rebuild the {competition} sidecar")
    made = manifest(competition, root=root)
    wanted = None if columns is None else _names(columns, known, table)
    frame = pd.read_parquet(path, columns=wanted)
    if len(frame) != made.row_counts[table]:
        raise SidecarMismatch(f"{path} holds {len(frame)} rows; its manifest records "
                              f"{made.row_counts[table]}")
    return frame


def verify(competition: str, *, root: Path = SIDECAR_ROOT) -> None:
    """Recompute the three content hashes and compare them with the manifest.

    ``SidecarMismatch`` names every table that differs. It shows that the tables are the
    ones the manifest describes. It does not show that the raw files or this module are
    the ones the sidecar was built from: ``raw_digests`` and ``builder_source_hash`` are in
    the manifest for a caller that needs to know.
    """
    made = manifest(competition, root=root)
    differing = []
    try:
        for table in TABLES:
            try:
                frame = load(competition, table, root=root)
                found = content_hash(frame, table)
            except ValueError as error:   # pyarrow's "not a Parquet file" is one too
                raise SidecarMismatch(f"{competition} {table}: {error}") from error
            if found != made.content_hashes[table]:
                differing.append(table)
            del frame
    finally:
        # A whole table was read and dropped; hand back what Arrow kept of it.
        pa.default_memory_pool().release_unused()
    if differing:
        raise SidecarMismatch(f"{competition}: the content of {differing} is not what the "
                              f"manifest records")


def attach(actions: pd.DataFrame, events: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """``actions`` with the named sidecar columns beside it, joined on ``event_id``.

    The only sanctioned join. A new frame with the rows of ``actions`` in their order and
    under their index; neither input is changed. ``SidecarMismatch`` when ``event_id``
    repeats on either side or an action row has no sidecar row. Sidecar rows that no
    action row asks for are not an error: ``actions`` may be one match or one type.

    ``ValueError`` for a column the sidecar frame does not have, for one ``actions``
    already has (it would come back twice under suffixed names), and for the key itself.
    """
    if isinstance(columns, (str, bytes)):
        raise TypeError(f"columns takes a sequence of names, not one string: {columns!r}")
    wanted = list(columns)
    if "event_id" not in actions.columns or "event_id" not in events.columns:
        raise ValueError("both frames need an event_id column to be joined on")
    if "event_id" in wanted or len(set(wanted)) != len(wanted):
        raise ValueError(f"columns must be distinct and must not name the key event_id: "
                         f"{wanted!r}")
    absent = [name for name in wanted if name not in events.columns]
    if absent:
        raise ValueError(f"not a column of the sidecar frame: {absent!r}")
    taken = [name for name in wanted if name in actions.columns]
    if taken:
        raise ValueError(f"already a column of actions: {taken!r}")
    try:
        merged = actions.merge(events[["event_id", *wanted]], on="event_id", how="left",
                               validate="one_to_one", indicator=True)
    except pd.errors.MergeError as error:
        raise SidecarMismatch(f"the join on event_id is not one-to-one: {error}") from error
    unmatched = merged["_merge"] != "both"
    if unmatched.any():
        raise SidecarMismatch(
            f"{int(unmatched.sum())} action rows have no sidecar row; first event ids: "
            f"{merged.loc[unmatched, 'event_id'].head(5).tolist()}")
    merged = merged.drop(columns="_merge")
    merged.index = actions.index
    return merged


def provenance(competition: str, *, root: Path = SIDECAR_ROOT) -> dict[str, object]:
    """What a response that read a sidecar column records under the key ``sidecar``."""
    made = manifest(competition, root=root)
    return {
        "sidecar_schema_version": made.sidecar_schema_version,
        "tag_mapping_version": made.tag_mapping_version,
        "content_hashes": dict(made.content_hashes),
        "raw_digests": dict(made.raw_digests),
        "competition": made.competition,
    }
