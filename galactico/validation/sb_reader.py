"""Raw StatsBomb reader for E-11 research, not a provider adapter.

Claim: reads, from one local open-data folder, the fields the shipped adapter
drops and E-11 needs: pass, shot and duel types, the period clock, every event
whether or not it has a location or a player, position spells by period, cards,
spell end reasons, the stage and data version of the match index, and a byte
digest of the folder. Matches come from ``_matches.json`` only, never from a
directory listing, so a delisted file on disk never becomes a match: every
function that takes match ids refuses one the index does not list.

Non-claim: it is not a provider adapter, feeds no product path and changes no
shipped number. ``StatsBombProvider`` keeps its own reader and its own minutes
rule. Nothing here joins the other provider, writes or logs anything, or keeps a
frame past the call: every frame lives in the caller's memory, and no exception
message names a match or a player. The data is LOCAL tier (ADR-0005): no product
package may import this module.

Minutes follow the protocol's rule 2 and are not the adapter's: spells that start
in a later period are dropped, both ends are clipped at the cap, a spell that ends
outside regulation runs to the cap, and a recorded off-pitch gap is simply the
absence of a spell. The cap is applied after summing. No argument has a default:
the cap, the periods and the card and spell-end rules are the caller's, from the
frozen config.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = [
    "READER_VERSION",
    "read_matches",
    "read_team_sheets",
    "iter_events",
    "read_events",
    "folder_vocabulary",
    "folder_manifest",
]

READER_VERSION = "statsbomb-research-reader-v2"

INDEX = "_matches.json"
EVENTS = "events"
LINEUPS = "_lineups"

# The provider numbers the first half 1. ``started`` is the shipped rule: a spell
# from minute 0 of the first half.
_FIRST_PERIOD = 1

# The detail object of an event is keyed by its kind in snake case; the one kind
# whose key is not derived that way.
_DETAIL_KEY_EXCEPTIONS = {"Goal Keeper": "goalkeeper"}
# The kinds whose detail carries an end location.
_END_DETAIL = {"Pass": "pass", "Carry": "carry", "Shot": "shot"}
# Vocabulary entry -> (kind whose events carry it, detail key).
_TYPED = {"pass_type": ("Pass", "pass"), "shot_type": ("Shot", "shot"),
          "duel_type": ("Duel", "duel")}

_TIMESTAMP = re.compile(r"(\d+):(\d{2}):(\d{2})(?:\.(\d+))?")

_MATCH_DTYPES: Mapping[str, object] = {
    "sb_game_id": "int64", "folder": object, "date": object,
    "home_sb_team_id": "int64", "away_sb_team_id": "int64",
    "home_team_name": object, "away_team_name": object,
    "home_goals": "Int64", "away_goals": "Int64", "stage": object, "data_version": object,
}
_SHEET_DTYPES: Mapping[str, object] = {
    "sb_game_id": "int64", "sb_team_id": "int64", "sb_player_id": "int64",
    "player_name": object, "player_nickname": object, "country": object,
    "started": "bool", "minutes_regulation": "int64", "minute_on": "int64",
    "minute_off": "int64", "is_goalkeeper": "bool", "cautioned": "bool",
    "dismissed": "bool", "permanent_off": "bool",
}
_EVENT_DTYPES: Mapping[str, object] = {
    "sb_game_id": "int64", "period": "int8", "period_seconds": "float64",
    "event_order": "int64", "sb_team_id": "int64", "sb_player_id": "Int64", "kind": object,
    "start_x": "float64", "start_y": "float64", "end_x": "float64", "end_y": "float64",
    "has_outcome": "bool", "outcome": object, "pass_type": object, "pass_height": object,
    "pass_cross": "bool", "shot_assist": "bool", "goal_assist": "bool", "shot_type": object,
    "duel_type": object, "play_pattern": object, "event_id": object,
}


@dataclass(frozen=True)
class _Spell:
    """One regulation position spell, both ends clipped at the cap."""

    order: tuple[int, int, int]  # from_period, minute of ``from``, place in the list
    start: int
    end: int
    position: str | None

    @property
    def minutes(self) -> int:
        return max(0, self.end - self.start)


def read_matches(root: Path, folder: str) -> tuple[pd.DataFrame, list[int]]:
    """The listed matches whose event and lineup files both exist, and the listed
    ids for which one is absent, both in index order. Nothing raises for an absent
    file: the runner drops and counts those matches."""
    rows: list[dict[str, object]] = []
    missing: list[int] = []
    for match in _listed(root, folder):
        game_id = int(match["match_id"])
        if not (_file(root, folder, EVENTS, game_id).is_file()
                and _file(root, folder, LINEUPS, game_id).is_file()):
            missing.append(game_id)
            continue
        home, away = match["home_team"], match["away_team"]
        rows.append({
            "sb_game_id": game_id,
            "folder": folder,
            "date": date.fromisoformat(str(match["match_date"])).isoformat(),
            "home_sb_team_id": int(home["home_team_id"]),
            "away_sb_team_id": int(away["away_team_id"]),
            "home_team_name": str(home["home_team_name"]),
            "away_team_name": str(away["away_team_name"]),
            "home_goals": match.get("home_score"),
            "away_goals": match.get("away_score"),
            "stage": _name(match, "competition_stage"),
            "data_version": (match.get("metadata") or {}).get("data_version"),
        })
    return _frame(rows, _MATCH_DTYPES), missing


def read_team_sheets(root: Path, folder: str, game_ids: Collection[int], *, cap: int,
                     regulation_periods: Collection[int], goalkeeper_position: str,
                     dismissal_card_types_exclude: Collection[str],
                     spell_end_reason_contains: str) -> pd.DataFrame:
    """One row per player with at least one spell that starts in a regulation period.

    ``minutes_regulation`` is ``min(cap, sum(max(0, end - start)))`` over the
    regulation spells, with ``start = min(mm(from), cap)`` and ``end = min(mm(to),
    cap)`` when ``to`` exists and ``to_period`` is a regulation period, else ``cap``;
    ``mm`` is the integer before the colon. ``minute_on`` and ``minute_off`` are the
    smallest start and the largest end. ``is_goalkeeper``: the spell with most
    regulation minutes, the earliest on a tie, is at ``goalkeeper_position``. Cards
    and spell end reasons are read over every card and every spell.
    """
    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise ValueError("cap must be a positive whole number of minutes")
    regulation = {int(period) for period in regulation_periods}
    excluded_cards = set(dismissal_card_types_exclude)
    rows: list[dict[str, object]] = []
    for game_id in _requested(root, folder, game_ids):
        teams = json.loads(_file(root, folder, LINEUPS, game_id).read_bytes())
        for team in teams:
            for player in team.get("lineup") or []:
                spells = player.get("positions") or []
                kept = [_spell(spell, place, cap, regulation)
                        for place, spell in enumerate(spells)
                        if spell.get("from_period") in regulation]
                if not kept:
                    continue
                # max() keeps the first of equal maxima, so a tie goes to the earliest.
                modal = max(sorted(kept, key=lambda spell: spell.order),
                            key=lambda spell: spell.minutes)
                cards = player.get("cards") or []
                end_reasons = [spell.get("end_reason") or "" for spell in spells]
                rows.append({
                    "sb_game_id": game_id,
                    "sb_team_id": int(team["team_id"]),
                    "sb_player_id": int(player["player_id"]),
                    "player_name": str(player["player_name"]),
                    "player_nickname": player.get("player_nickname"),
                    "country": _name(player, "country"),
                    "started": any(spell.get("from_period") == _FIRST_PERIOD
                                   and _minute(spell["from"]) == 0 for spell in spells),
                    "minutes_regulation": min(cap, sum(spell.minutes for spell in kept)),
                    "minute_on": min(spell.start for spell in kept),
                    "minute_off": max(spell.end for spell in kept),
                    "is_goalkeeper": modal.position == goalkeeper_position,
                    "cautioned": len(cards) > 0,
                    "dismissed": any(card["card_type"] not in excluded_cards for card in cards),
                    "permanent_off": any(spell_end_reason_contains in reason
                                         for reason in end_reasons),
                })
    sheets = _frame(rows, _SHEET_DTYPES)
    if sheets.duplicated(["sb_game_id", "sb_player_id"]).any():
        raise ValueError(f"a lineup file of {folder} lists one player twice")
    return sheets


def iter_events(root: Path, folder: str,
                game_ids: Collection[int]) -> Iterator[tuple[int, list[dict]]]:
    """``(match id, raw event list)`` per requested match, ascending, one file at a
    time, so a caller that keeps only a few arrays never holds a whole folder."""
    for game_id in _requested(root, folder, game_ids):
        yield game_id, json.loads(_file(root, folder, EVENTS, game_id).read_bytes())


def read_events(root: Path, folder: str, game_ids: Collection[int], *,
                scale: Sequence[float]) -> pd.DataFrame:
    """Every event of every requested match, nothing dropped, in file order.

    Locations are divided by ``scale`` (x, y). An absent start or end is NaN; an
    end is read from the pass, carry or shot detail only and is never a copy of
    the start. ``period_seconds`` is the ``timestamp``, which restarts each period.
    """
    if len(scale) != 2 or not all(math.isfinite(value) and value > 0 for value in scale):
        raise ValueError("scale must be two positive finite numbers")
    width, height = float(scale[0]), float(scale[1])
    rows: list[dict[str, object]] = []
    for game_id, events in iter_events(root, folder, game_ids):
        for event in events:
            kind = str(event["type"]["name"])
            detail = event.get(_detail_key(kind)) or {}
            passing = event.get("pass") or {}
            start = _point(event.get("location"), width, height)
            end = _point((event.get(_END_DETAIL[kind]) or {}).get("end_location")
                         if kind in _END_DETAIL else None, width, height)
            rows.append({
                "sb_game_id": game_id,
                "period": int(event["period"]),
                "period_seconds": _period_seconds(str(event["timestamp"])),
                "event_order": int(event["index"]),
                "sb_team_id": int(event["team"]["id"]),
                "sb_player_id": (event.get("player") or {}).get("id"),
                "kind": kind,
                "start_x": start[0],
                "start_y": start[1],
                "end_x": end[0],
                "end_y": end[1],
                "has_outcome": detail.get("outcome") is not None,
                "outcome": _name(detail, "outcome"),
                "pass_type": _name(passing, "type"),
                "pass_height": _name(passing, "height"),
                "pass_cross": bool(passing.get("cross")),
                "shot_assist": bool(passing.get("shot_assist")),
                "goal_assist": bool(passing.get("goal_assist")),
                "shot_type": _name(event.get("shot"), "type"),
                "duel_type": _name(event.get("duel"), "type"),
                "play_pattern": _name(event, "play_pattern"),
                "event_id": str(event["id"]),
            })
    return _frame(rows, _EVENT_DTYPES)


def folder_vocabulary(root: Path, folder: str) -> dict[str, list[str | None]]:
    """Distinct names, no counts: ``kind`` over every event, and each type over the
    events of its own kind only, a missing type being None. Read from the event
    file of every listed match that has one. None sorts first, then the names in
    code-point order."""
    present = [int(match["match_id"]) for match in _listed(root, folder)
               if _file(root, folder, EVENTS, int(match["match_id"])).is_file()]
    seen: dict[str, set[str | None]] = {"kind": set(), **{entry: set() for entry in _TYPED}}
    for _, events in iter_events(root, folder, present):
        for event in events:
            kind = str(event["type"]["name"])
            seen["kind"].add(kind)
            for entry, (typed_kind, key) in _TYPED.items():
                if kind == typed_kind:
                    seen[entry].add(_name(event.get(key), "type"))
    return {entry: _none_first(names) for entry, names in seen.items()}


def folder_manifest(root: Path, folder: str) -> dict[str, object]:
    """File counts, bytes, ``metadata`` versions and the folder digest of
    PIPELINE.md section 2, which ``scripts/fetch_statsbomb_double_coded.py`` also
    computes: one line ``<path>:<sha256>`` for the match index and for the event
    and lineup file of every listed match id, ``<path>`` relative to ``root`` in
    POSIX form; a listed file that is absent writes no line and a file the index
    does not list is never opened; the lines sorted as strings, joined with a
    newline and no trailing one, and hashed as UTF-8.

    ``bytes`` is the size of the files hashed; ``data_versions`` counts listed
    matches per distinct ``metadata`` object, keyed by its JSON with sorted keys.
    """
    index_path = root / folder / INDEX
    index_bytes = index_path.read_bytes()
    listed = json.loads(index_bytes)
    ids = [int(match["match_id"]) for match in listed]
    event_files = [path for path in (_file(root, folder, EVENTS, i) for i in ids)
                   if path.is_file()]
    lineup_files = [path for path in (_file(root, folder, LINEUPS, i) for i in ids)
                    if path.is_file()]
    lines = [_line(root, index_path, index_bytes)]
    size = len(index_bytes)
    for path in [*event_files, *lineup_files]:
        content = path.read_bytes()
        lines.append(_line(root, path, content))
        size += len(content)
    versions = Counter(json.dumps(match.get("metadata"), sort_keys=True) for match in listed)
    return {
        "folder": folder,
        "event_files": len(event_files),
        "lineup_files": len(lineup_files),
        "bytes": size,
        "data_versions": dict(sorted(versions.items())),
        "digest": hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest(),
    }


def _listed(root: Path, folder: str) -> list[dict]:
    """The match index. Matches are enumerated from it and from nothing else."""
    listed = json.loads((root / folder / INDEX).read_bytes())
    ids = [int(match["match_id"]) for match in listed]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{folder}/{INDEX} lists a match twice")
    return listed


def _requested(root: Path, folder: str, game_ids: Collection[int]) -> list[int]:
    """The distinct requested ids, ascending, each one listed in the match index."""
    requested = sorted({int(game_id) for game_id in game_ids})
    listed = {int(match["match_id"]) for match in _listed(root, folder)}
    unlisted = sum(game_id not in listed for game_id in requested)
    if unlisted:
        raise ValueError(f"{unlisted} requested match(es) are not listed in {folder}/{INDEX}")
    return requested


def _file(root: Path, folder: str, kind: str, game_id: int) -> Path:
    return root / folder / kind / f"{game_id}.json"


def _line(root: Path, path: Path, content: bytes) -> str:
    return f"{path.relative_to(root).as_posix()}:{hashlib.sha256(content).hexdigest()}"


def _frame(rows: list[dict[str, object]], dtypes: Mapping[str, object]) -> pd.DataFrame:
    """Columns in the order of ``dtypes``. Text columns are ``object`` so that a
    missing value stays None on every pandas version, never a NaN string."""
    return pd.DataFrame({column: pd.Series([row[column] for row in rows], dtype=dtype)
                         for column, dtype in dtypes.items()})


def _name(record: Mapping | None, field: str) -> str | None:
    """``record[field]["name"]``, None where either is absent."""
    named = (record or {}).get(field)
    return None if named is None else named.get("name")


def _none_first(names: set[str | None]) -> list[str | None]:
    named = sorted(name for name in names if name is not None)
    return [None, *named] if None in names else named


def _detail_key(kind: str) -> str:
    """The key of an event's detail object: ``Ball Receipt*`` -> ``ball_receipt``,
    ``50/50`` -> ``50_50``, ``Foul Committed`` -> ``foul_committed``."""
    if kind in _DETAIL_KEY_EXCEPTIONS:
        return _DETAIL_KEY_EXCEPTIONS[kind]
    return kind.lower().replace(" ", "_").replace("/", "_").rstrip("*")


def _point(location: Sequence[float] | None, width: float, height: float) -> tuple[float, float]:
    if not location:
        return np.nan, np.nan
    return float(location[0]) / width, float(location[1]) / height


def _period_seconds(stamp: str) -> float:
    """Seconds since the period started, from ``HH:MM:SS.mmm``, correctly rounded:
    the true division of two Python ints rounds the exact quotient once."""
    match = _TIMESTAMP.fullmatch(stamp)
    if match is None:
        raise ValueError("an event timestamp is not HH:MM:SS.mmm")
    hours, minutes, seconds, fraction = match.groups(default="")
    whole = (int(hours) * 60 + int(minutes)) * 60 + int(seconds)
    unit = 10 ** len(fraction)
    return (whole * unit + int(fraction or 0)) / unit


def _minute(stamp: str) -> int:
    """``mm``: the integer before the colon of a spell's ``MM:SS``."""
    return int(stamp.split(":", 1)[0])


def _spell(spell: Mapping, place: int, cap: int, regulation: set[int]) -> _Spell:
    start = min(_minute(spell["from"]), cap)
    ends_inside = bool(spell.get("to")) and spell.get("to_period") in regulation
    end = min(_minute(spell["to"]), cap) if ends_inside else cap
    return _Spell(order=(int(spell["from_period"]), _minute(spell["from"]), place),
                  start=start, end=end, position=spell.get("position"))
