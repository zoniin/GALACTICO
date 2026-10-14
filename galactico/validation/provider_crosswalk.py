"""Team-sheet crosswalk and the wide name-and-nationality link of E-11.

Claim: identity from team sheets alone. A StatsBomb match is linked to a Wyscout
match of its subset by calendar date, team-name tokens and, for the durations the
config lists, the score. Inside one linked team-match the two sheets list the same
people, so a StatsBomb player is paired with a Wyscout player by name tokens in that
closed pool, then by elimination, and the pair is checked against the sheets'
structure (started, goalkeeper, regulation minutes). The wide link then joins every
StatsBomb sheet player to the whole Pappalardo player file by name and nationality
alone and is graded against that pairing.

Non-claim: no birth date confirms any link. The pairing is name-based inside a
closed pool with structural corroboration, an estimate (``NAME_AND_CONTEXT``), not an
identification, and it is not error-free. No event enters any function here: linking
on event agreement and then measuring event agreement would be circular, so no
parameter is an event frame. The frames returned are process memory only; nothing
here writes a file, and no identifier or name reaches an exception message.

Every token, token set and Jaccard is on ``name_tokens``
(``galactico/identity/resolver.py``) of the name it is taken from; a Jaccard with an
empty side, a null name form included, is 0; countries compare on ``normalise_name``
only. ``resolve_player`` is not used: it accepts nobody without a birth date. Every
number is the caller's frozen config, and a config key that restates a protocol rule
is asserted, never branched on.
"""

from __future__ import annotations

import hashlib
import json
import math
import numbers
from collections import Counter, defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from ..identity.resolver import name_tokens, normalise_name

__all__ = [
    "CROSSWALK_VERSION",
    "MATCH_REJECTIONS",
    "LINK_OUTCOMES",
    "read_wyscout_matches",
    "read_wyscout_team_sheets",
    "read_wyscout_people",
    "crosswalk_matches",
    "assign_match_keys",
    "team_sheet_crosswalk",
    "evaluated_players",
    "name_nationality_link",
    "evaluate_wide_link",
    "namesake_collision",
    "wilson_interval",
    "link_verdict",
    "permuted_partners",
    "crosswalk_digest",
]

CROSSWALK_VERSION = "team-sheet-crosswalk-v2"

# Rejection reasons of the match crosswalk, in the order the first that holds is taken.
MATCH_REJECTIONS: tuple[str, ...] = ("NO_CANDIDATE", "AMBIGUOUS", "CLAIMED_TWICE",
                                     "GOALS_DISAGREE")
LINK_OUTCOMES: tuple[str, ...] = ("LINKED", "AMBIGUOUS", "CLAIMED_TWICE", "NO_CANDIDATE")

_PAIRED = "PAIRED_BY_TEAM_SHEET"
_STATUSES = frozenset({_PAIRED, "NAME_WEAK", "ELIMINATION_ONLY", "STRUCTURE_CONFLICT",
                       "BIJECTION_CONFLICT"})
_CLASSES = ("CORRECT", "FALSE", "UNVERIFIABLE", "NO_LINK")
_LINK_TOKENS = frozenset({"LINK_USABLE", "LINK_NOT_ESTABLISHED", "INCONCLUSIVE"})
_EVALUATED = "EVALUATED_PLAYERS"
_TIERS = frozenset({"A", "N", "B"})

# How a pair was taken in one sheet: steps 1 and 2 of the protocol.
_NAMED, _WEAK, _ELIMINATION = "named", "weak", "elimination"

_WY_MATCH_DTYPES: Mapping[str, object] = {
    "wy_game_id": "int64", "date": object, "home_wy_team_id": "int64",
    "away_wy_team_id": "int64", "home_goals": "Int64", "away_goals": "Int64",
    "duration": object,
}
_WY_SHEET_DTYPES: Mapping[str, object] = {
    "wy_game_id": "int64", "wy_team_id": "int64", "wy_player_id": "int64",
    "started": "bool", "minutes_regulation": "int64", "minute_on": "int64",
    "minute_off": "int64", "cautioned": "bool", "dismissed": "bool",
}
_WY_PEOPLE_DTYPES: Mapping[str, object] = {
    "wy_player_id": "int64", "full_name": object, "short_name": object,
    "birth_area": object, "passport_area": object, "position": object,
}
_LINK_DTYPES: Mapping[str, object] = {
    "match_key": "int32", "subset": object, "sb_game_id": "int64", "wy_game_id": "int64",
    "date": object, "swapped": "bool", "duration": object, "goal_check": object,
    "sb_home_team_id": "int64", "sb_away_team_id": "int64",
    "wy_team_for_sb_home": "int64", "wy_team_for_sb_away": "int64",
}
_PAIR_DTYPES: Mapping[str, object] = {
    "sb_player_id": "int64", "wy_player_id": "int64", "status": object,
    "sheets_named": "int64", "sheets_together": "int64",
    "sheets_structure_passed": "int64", "swap_impossible": "bool", "is_goalkeeper": "bool",
}
_DROPPED_DTYPES: Mapping[str, object] = {"match_key": "int32", "sb_player_id": "int64"}
_RESULT_DTYPES: Mapping[str, object] = {
    "left_id": "int64", "right_id": "Int64", "tier": object, "outcome": object,
}


# --- shared helpers -----------------------------------------------------------

def _frozen(config: Mapping[str, object], key: str, value: object) -> None:
    """A config key that restates a protocol rule is asserted; only ``value`` is built."""
    if config[key] != value:
        raise ValueError(f"config {key} restates a frozen rule; only {value!r} is implemented")


def _frame(rows: Sequence[Mapping[str, object]], dtypes: Mapping[str, object]) -> pd.DataFrame:
    # Column by column, so a None in a string column stays None under pandas 3.
    return pd.DataFrame({name: pd.Series([row[name] for row in rows], dtype=dtype)
                         for name, dtype in dtypes.items()})


def _text(value: object) -> str | None:
    """A provider string, or None where the field is absent (None, NaN or NA)."""
    if isinstance(value, str):
        return value
    if value is None or pd.isna(value):
        return None
    return str(value)


def _tokens(name: object) -> frozenset[str]:
    text = _text(name)
    return name_tokens(text) if text else frozenset()


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _overlap(left: Iterable[frozenset[str]], right: Sequence[frozenset[str]]) -> float:
    """Largest token Jaccard over the name forms of two rows."""
    return max((_jaccard(a, b) for a in left for b in right), default=0.0)


def _subset_keys(config: Mapping[str, object]) -> list[str]:
    return [str(entry["key"]) for entry in config["subsets"]]


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _unescape(value: object) -> str | None:
    """The adapter's unescape of ``shortName``, applied to every string read here."""
    text = _text(value)
    return None if text is None else text.encode("utf-8").decode("unicode_escape")


def _goals(value: object) -> int | None:
    return None if value is None or pd.isna(value) else int(value)


# --- Wyscout readers ----------------------------------------------------------

def read_wyscout_matches(raw_root: Path, competition: str) -> pd.DataFrame:
    """Every match of ``matches_<competition>.json``, ascending ``wy_game_id``.

    ``date`` is the first ten characters of ``dateutc``; goals are each side's
    ``score`` in ``teamsData``. A match without exactly one home and one away side
    raises.
    """
    rows = []
    for match in _load(Path(raw_root) / f"matches_{competition}.json"):
        sides: dict[object, list[tuple[int, Mapping[str, object]]]] = defaultdict(list)
        for team_id, side in (match.get("teamsData") or {}).items():
            sides[side.get("side")].append((int(team_id), side))
        if len(sides["home"]) != 1 or len(sides["away"]) != 1:
            raise ValueError("a match does not have exactly one home and one away side")
        (home, home_side), (away, away_side) = sides["home"][0], sides["away"][0]
        rows.append({
            "wy_game_id": int(match["wyId"]),
            "date": str(match["dateutc"])[:10],
            "home_wy_team_id": home,
            "away_wy_team_id": away,
            "home_goals": _goals(home_side.get("score")),
            "away_goals": _goals(away_side.get("score")),
            "duration": _text(match.get("duration")),
        })
    frame = _frame(rows, _WY_MATCH_DTYPES)
    if frame["wy_game_id"].duplicated().any():
        raise ValueError("a match id is listed twice")
    return frame.sort_values("wy_game_id", kind="mergesort").reset_index(drop=True)


def _sheet_row(game: int, team: int, entry: Mapping[str, object], *, started: bool,
               minutes: int, cap: int, red_cards_not_equal: str) -> dict[str, object]:
    dismissed = str(entry["redCards"]) != red_cards_not_equal
    return {
        "wy_game_id": game, "wy_team_id": team, "wy_player_id": int(entry["playerId"]),
        "started": started, "minutes_regulation": minutes,
        "minute_on": 0 if started else cap - minutes,
        "minute_off": minutes if started else cap,
        "cautioned": dismissed or str(entry["yellowCards"]) != red_cards_not_equal,
        "dismissed": dismissed,
    }


def read_wyscout_team_sheets(raw_root: Path, competition: str,
                             game_ids: Collection[int], *, cap: int,
                             red_cards_not_equal: str) -> pd.DataFrame:
    """One row per starter and per used substitute of the requested matches.

    Minutes are the adapter's rule with ``cap`` for its 90: a starter has
    ``min(off_minute, cap)`` when a substitution takes him off (an off minute of 0
    included), else ``cap``; a used substitute ``max(0, cap - on_minute)``, even when
    he is later replaced; a dismissal changes nothing. A non-list ``substitutions`` is
    empty. ``minute_on`` and ``minute_off`` bound those minutes. A card field not equal
    to ``red_cards_not_equal`` is a card. Unused substitutes have no row.
    """
    wanted = {int(game) for game in game_ids}
    rows = []
    for match in _load(Path(raw_root) / f"matches_{competition}.json"):
        game = int(match["wyId"])
        if game not in wanted:
            continue
        for team_id, side in (match.get("teamsData") or {}).items():
            formation = side.get("formation") or {}
            substitutions = formation.get("substitutions")
            substitutions = substitutions if isinstance(substitutions, list) else []
            on_at = {int(s["playerIn"]): int(s["minute"]) for s in substitutions}
            off_at = {int(s["playerOut"]): int(s["minute"]) for s in substitutions}
            for entry in formation.get("lineup") or []:
                player = int(entry["playerId"])
                minutes = min(off_at[player], cap) if player in off_at else cap
                rows.append(_sheet_row(game, int(team_id), entry, started=True,
                                       minutes=minutes, cap=cap,
                                       red_cards_not_equal=red_cards_not_equal))
            for entry in formation.get("bench") or []:
                player = int(entry["playerId"])
                if player in on_at:
                    rows.append(_sheet_row(game, int(team_id), entry, started=False,
                                           minutes=max(0, cap - on_at[player]), cap=cap,
                                           red_cards_not_equal=red_cards_not_equal))
    frame = _frame(rows, _WY_SHEET_DTYPES)
    if frame.duplicated(["wy_game_id", "wy_player_id"]).any():
        raise ValueError("a player holds two sheet rows in one match")
    return frame.sort_values(["wy_game_id", "wy_team_id", "wy_player_id"],
                             kind="mergesort").reset_index(drop=True)


def _area(value: object) -> object:
    return value.get("name") if isinstance(value, dict) else None


def read_wyscout_people(raw_root: Path) -> pd.DataFrame:
    """Every record of ``players.json``: names, the two areas and the role code.

    ``full_name`` is the first name and the last name joined by a space (None when
    both are empty); the four strings are unescaped as the adapter unescapes
    ``shortName``. The middle name is not read.
    """
    rows = []
    for record in _load(Path(raw_root) / "players.json"):
        parts = (_text(record.get("firstName")), _text(record.get("lastName")))
        role = record.get("role")
        rows.append({
            "wy_player_id": int(record["wyId"]),
            "full_name": _unescape(" ".join(part for part in parts if part) or None),
            "short_name": _unescape(record.get("shortName")),
            "birth_area": _unescape(_area(record.get("birthArea"))),
            "passport_area": _unescape(_area(record.get("passportArea"))),
            "position": role.get("code2") if isinstance(role, dict) else None,
        })
    frame = _frame(rows, _WY_PEOPLE_DTYPES)
    if frame["wy_player_id"].duplicated().any():
        raise ValueError("a player id is listed twice")
    return frame.sort_values("wy_player_id", kind="mergesort").reset_index(drop=True)


# --- match crosswalk ------------------------------------------------------------

@dataclass(frozen=True)
class _Fixture:
    game: int
    day: date
    home: int
    away: int
    home_tokens: frozenset[str]
    away_tokens: frozenset[str]
    home_goals: int | None
    away_goals: int | None


def _day(value: object) -> date:
    return date.fromisoformat(str(value)[:10])


def _orientation(sb: _Fixture, wy: _Fixture, above: float) -> bool | None:
    """None when the candidate does not qualify, else whether it is swapped.

    A candidate qualifies in the orientation with the larger smaller-side overlap;
    equal overlaps in both orientations disqualify.
    """
    straight = min(_jaccard(sb.home_tokens, wy.home_tokens),
                   _jaccard(sb.away_tokens, wy.away_tokens))
    crossed = min(_jaccard(sb.home_tokens, wy.away_tokens),
                  _jaccard(sb.away_tokens, wy.home_tokens))
    if straight == crossed or max(straight, crossed) <= above:
        return None
    return crossed > straight


def crosswalk_matches(sb_matches: pd.DataFrame, wy_matches: pd.DataFrame,
                      wy_teams: pd.DataFrame, config: Mapping[str, object],
                      *, subset: str) -> tuple[pd.DataFrame, dict[str, int]]:
    """Link one subset's StatsBomb matches to its Wyscout matches; count rejections.

    ``sb_matches`` is ``read_matches`` of the subset's folder, ``wy_matches``
    ``read_wyscout_matches`` of its competition and ``wy_teams`` ``teams.parquet``
    (``team_id``, ``team_name``). A match is linked when exactly one candidate within
    ``match_date_tolerance_days`` qualifies, that candidate qualifies for no other
    StatsBomb match of the subset, and, for a duration in
    ``match_require_goal_agreement_durations``, the goals agree after orientation.
    The counts hold every reason of ``MATCH_REJECTIONS``, the first that holds.

    ``match_key`` here numbers this subset's links alone, by ``wy_game_id``; the
    runner removes ``WY_ROWS_ABSENT`` matches and then numbers all subsets together
    with ``assign_match_keys``. Runs on real data only inside ``execute``.
    """
    _frozen(config, "match_allow_swapped_orientation", True)
    folders = {str(entry["key"]): entry["sb_folder"] for entry in config["subsets"]}
    if subset not in folders:
        raise ValueError("subset is not a key of config subsets")
    if not sb_matches["folder"].eq(folders[subset]).all():
        raise ValueError("crosswalk_matches takes the matches of its subset's folder only")
    tolerance = int(config["match_date_tolerance_days"])
    above = float(config["match_team_token_overlap_strictly_above"])
    checked_durations = set(config["match_require_goal_agreement_durations"])

    team_tokens = {int(team): _tokens(name)
                   for team, name in zip(wy_teams["team_id"], wy_teams["team_name"],
                                         strict=True)}
    wy = [_Fixture(int(row.wy_game_id), _day(row.date), int(row.home_wy_team_id),
                   int(row.away_wy_team_id),
                   team_tokens.get(int(row.home_wy_team_id), frozenset()),
                   team_tokens.get(int(row.away_wy_team_id), frozenset()),
                   _goals(row.home_goals), _goals(row.away_goals))
          for row in wy_matches.itertuples(index=False)]
    durations = [_text(value) for value in wy_matches["duration"]]
    sb = [_Fixture(int(row.sb_game_id), _day(row.date), int(row.home_sb_team_id),
                   int(row.away_sb_team_id), _tokens(row.home_team_name),
                   _tokens(row.away_team_name), _goals(row.home_goals),
                   _goals(row.away_goals))
          for row in sb_matches.itertuples(index=False)]

    qualifying: list[list[tuple[int, bool]]] = []
    for match in sb:
        found = []
        for position, candidate in enumerate(wy):
            if abs((match.day - candidate.day).days) > tolerance:
                continue
            swapped = _orientation(match, candidate, above)
            if swapped is not None:
                found.append((position, swapped))
        qualifying.append(found)
    claims = Counter(position for found in qualifying for position, _ in found)

    rejected = dict.fromkeys(MATCH_REJECTIONS, 0)
    rows = []
    for match, found in zip(sb, qualifying, strict=True):
        if not found:
            rejected["NO_CANDIDATE"] += 1
            continue
        if len(found) > 1:
            rejected["AMBIGUOUS"] += 1
            continue
        position, swapped = found[0]
        if claims[position] > 1:
            rejected["CLAIMED_TWICE"] += 1
            continue
        candidate = wy[position]
        goals = ((candidate.away_goals, candidate.home_goals) if swapped
                 else (candidate.home_goals, candidate.away_goals))
        checked = durations[position] in checked_durations
        agree = None not in goals and goals == (match.home_goals, match.away_goals)
        if checked and not agree:
            rejected["GOALS_DISAGREE"] += 1
            continue
        rows.append({
            "match_key": 0, "subset": subset, "sb_game_id": match.game,
            "wy_game_id": candidate.game, "date": match.day.isoformat(),
            "swapped": swapped, "duration": durations[position],
            "goal_check": "agree" if checked else "skipped",
            "sb_home_team_id": match.home, "sb_away_team_id": match.away,
            "wy_team_for_sb_home": candidate.away if swapped else candidate.home,
            "wy_team_for_sb_away": candidate.home if swapped else candidate.away,
        })
    links = _frame(rows, _LINK_DTYPES).sort_values("wy_game_id", kind="mergesort")
    links["match_key"] = np.arange(len(links), dtype=np.int32)
    return links.reset_index(drop=True), rejected


def assign_match_keys(links: Sequence[pd.DataFrame],
                      config: Mapping[str, object]) -> pd.DataFrame:
    """Concatenate per-subset links and number them ``0..M-1``.

    Subsets in config order, each by ``wy_game_id``, so a ``world_cup`` match has a
    smaller ``match_key`` than every ``la_liga`` match whatever the calendar says. A
    game id on either side may appear once.
    """
    order = {key: position for position, key in enumerate(_subset_keys(config))}
    frame = (pd.concat([frame.astype(dict(_LINK_DTYPES)) for frame in links],
                       ignore_index=True) if links else _frame([], _LINK_DTYPES))
    if not frame["subset"].isin(list(order)).all():
        raise ValueError("a link names a subset that config does not list")
    if frame["sb_game_id"].duplicated().any() or frame["wy_game_id"].duplicated().any():
        raise ValueError("a match is linked twice")
    frame = (frame.assign(_order=frame["subset"].map(order))
             .sort_values(["_order", "wy_game_id"], kind="mergesort")
             .drop(columns="_order").reset_index(drop=True))
    frame["match_key"] = np.arange(len(frame), dtype=np.int32)
    return frame[list(_LINK_DTYPES)]


# --- team-sheet crosswalk ---------------------------------------------------------

@dataclass(frozen=True)
class _Side:
    """One team-match: a linked match seen from one team."""

    match_key: int
    subset: str
    sb_game: int
    sb_team: int
    wy_game: int
    wy_team: int


@dataclass(frozen=True)
class _Row:
    """One filtered sheet row, either provider."""

    player: int
    forms: tuple[frozenset[str], ...]
    tokens: frozenset[str]
    started: bool
    minutes: int
    goalkeeper: bool
    cautioned: bool
    dismissed: bool
    permanent_off: bool


def _sides(match_links: pd.DataFrame) -> list[_Side]:
    for column in ("match_key", "sb_game_id", "wy_game_id"):
        if match_links[column].duplicated().any():
            raise ValueError(f"match_links repeats a {column}")
    sides = []
    for link in match_links.itertuples(index=False):
        for sb_team, wy_team in ((link.sb_home_team_id, link.wy_team_for_sb_home),
                                 (link.sb_away_team_id, link.wy_team_for_sb_away)):
            sides.append(_Side(int(link.match_key), str(link.subset), int(link.sb_game_id),
                               int(sb_team), int(link.wy_game_id), int(wy_team)))
    return sides


def _records_by_side(frame: pd.DataFrame, game: str, team: str, player: str,
                     sides: set[tuple[int, int]]) -> dict[tuple[int, int], list[dict]]:
    """Sheet rows of linked matches by (game, team); a row of a linked game for a
    third team raises."""
    if frame.duplicated([game, player]).any():
        raise ValueError("a player holds two sheet rows in one match")
    games = {side_game for side_game, _ in sides}
    grouped: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for record in frame.to_dict("records"):
        key = (int(record[game]), int(record[team]))
        if key in sides:
            grouped[key].append(record)
        elif key[0] in games:
            raise ValueError("a sheet row's team is not one of its linked match's teams")
    return grouped


def _people(wy_people: pd.DataFrame) -> dict[int, tuple[tuple[frozenset[str], ...], str | None]]:
    """Wyscout name forms (full name, short name) and role code by player."""
    if wy_people["wy_player_id"].duplicated().any():
        raise ValueError("a player id is listed twice")
    return {int(row.wy_player_id): ((_tokens(row.full_name), _tokens(row.short_name)),
                                     _text(row.position))
            for row in wy_people.itertuples(index=False)}


def _maxima(overlaps: Mapping[int, float], above: float) -> frozenset[int]:
    """The rows reaching the largest overlap, when it is above the threshold."""
    best = max(overlaps.values(), default=0.0)
    if best <= above:
        return frozenset()
    return frozenset(key for key, value in overlaps.items() if value == best)


def _pair_sheet(sb: Sequence[_Row], wy: Sequence[_Row],
                above: float) -> list[tuple[int, int, str]]:
    """Steps 1 and 2 of the protocol in one team-match: (sb row, wy row, how taken)."""
    overlap = [[_overlap(a.forms, b.forms) for b in wy] for a in sb]
    # A token carried by exactly the two rows of a pair is in no name form of any
    # other row of either filtered sheet.
    carriers = Counter(token for row in (*sb, *wy) for token in row.tokens)
    open_sb, open_wy = set(range(len(sb))), set(range(len(wy)))
    taken: list[tuple[int, int, str]] = []
    while True:
        best_sb = {i: _maxima({j: overlap[i][j] for j in open_wy}, above) for i in open_sb}
        best_wy = {j: _maxima({i: overlap[i][j] for i in open_sb}, above) for j in open_wy}
        found = sorted((i, j) for i, best in best_sb.items() if len(best) == 1
                       for j in best if best_wy[j] == {i})
        if not found:
            break
        for i, j in found:
            shared = sb[i].tokens & wy[j].tokens
            named = any(carriers[token] == 2 for token in shared)
            taken.append((i, j, _NAMED if named else _WEAK))
            open_sb.discard(i)
            open_wy.discard(j)
    if len(open_sb) == 1 and len(open_wy) == 1:
        (i,), (j,) = open_sb, open_wy
        if sb[i].started == wy[j].started:
            taken.append((i, j, _ELIMINATION))
    return taken


def _structure(a: _Row, b: _Row, tolerance: int) -> bool:
    """Step 3 in one sheet; the minutes check alone is waived by a dismissal on either
    sheet or a permanent StatsBomb player-off."""
    if a.started != b.started or a.goalkeeper != b.goalkeeper:
        return False
    if a.dismissed or b.dismissed or a.permanent_off:
        return True
    return abs(a.minutes - b.minutes) <= tolerance


def _share(part: int, whole: int) -> float | None:
    return part / whole if whole else None


def team_sheet_crosswalk(sb_sheets: pd.DataFrame, wy_sheets: pd.DataFrame,
                         wy_people: pd.DataFrame, match_links: pd.DataFrame,
                         config: Mapping[str, object]
                         ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Pair players inside every linked team-match; return pairs, dropped
    player-matches and the audit.

    Exactly the protocol's steps. Rows with zero ``minutes_regulation`` are removed
    on each sheet by that sheet's own minutes and counted. Name forms: StatsBomb
    ``player_name`` and ``player_nickname``; Wyscout ``full_name`` and
    ``short_name``. Step 3 is evaluated on every team-match in which both players of
    a link hold a filtered row (``sheets_together``), whether or not steps 1 and 2
    paired them there. A sheet in which a ``PAIRED_BY_TEAM_SHEET`` link fails step 3
    drops that one player-match. ``is_goalkeeper`` of a pair is the Wyscout role code.
    """
    _frozen(config, "sheet_drop_zero_regulation_minute_rows", True)
    _frozen(config, "sheet_require_distinguishing_token", True)
    _frozen(config, "sheet_require_started_agreement", True)
    _frozen(config, "sheet_require_goalkeeper_flag_agreement", True)
    _frozen(config, "sheet_structure_conflict_scope", "player_match")
    _frozen(config["sheet_minutes_waiver"], "either_provider_records_dismissal", True)
    _frozen(config, "coverage_outfield_rule",
            {"sb": "is_goalkeeper flag of the StatsBomb sheet", "wy": "role code"})
    if set(config["pair_status_vocabulary"]) != _STATUSES or config["paired_status"] != _PAIRED:
        raise ValueError("pair_status_vocabulary is not the vocabulary implemented here")
    above = float(config["sheet_name_overlap_strictly_above"])
    tolerance = int(config["sheet_minutes_tolerance"])
    share_minimum = float(config["sheet_structure_pass_share_minimum"])
    keeper = config["wy_goalkeeper_position"]

    people = _people(wy_people)
    sides = _sides(match_links)
    sb_records = _records_by_side(sb_sheets, "sb_game_id", "sb_team_id", "sb_player_id",
                                  {(side.sb_game, side.sb_team) for side in sides})
    wy_records = _records_by_side(wy_sheets, "wy_game_id", "wy_team_id", "wy_player_id",
                                  {(side.wy_game, side.wy_team) for side in sides})

    zero = {"sb": 0, "wy": 0}
    sheets: list[tuple[_Side, dict[int, _Row], dict[int, _Row]]] = []
    for side in sides:
        sb_rows: dict[int, _Row] = {}
        for record in sb_records.get((side.sb_game, side.sb_team), []):
            if int(record["minutes_regulation"]) <= 0:
                zero["sb"] += 1
                continue
            forms = (_tokens(record["player_name"]), _tokens(record["player_nickname"]))
            sb_rows[int(record["sb_player_id"])] = _Row(
                int(record["sb_player_id"]), forms, frozenset().union(*forms),
                bool(record["started"]), int(record["minutes_regulation"]),
                bool(record["is_goalkeeper"]), bool(record["cautioned"]),
                bool(record["dismissed"]), bool(record["permanent_off"]))
        wy_rows: dict[int, _Row] = {}
        for record in wy_records.get((side.wy_game, side.wy_team), []):
            if int(record["minutes_regulation"]) <= 0:
                zero["wy"] += 1
                continue
            player = int(record["wy_player_id"])
            forms, position = people.get(player, ((frozenset(), frozenset()), None))
            wy_rows[player] = _Row(
                player, forms, frozenset().union(*forms), bool(record["started"]),
                int(record["minutes_regulation"]), position == keeper,
                bool(record["cautioned"]), bool(record["dismissed"]), False)
        sheets.append((side, sb_rows, wy_rows))

    # Steps 1 and 2, sheet by sheet.
    taken_as: dict[tuple[int, int], set[str]] = defaultdict(set)
    named_in: Counter[tuple[int, int]] = Counter()
    sheets_of_sb: dict[int, list[int]] = defaultdict(list)
    for index, (_, sb_rows, wy_rows) in enumerate(sheets):
        for player in sb_rows:
            sheets_of_sb[player].append(index)
        sb_list, wy_list = list(sb_rows.values()), list(wy_rows.values())
        for i, j, how in _pair_sheet(sb_list, wy_list, above):
            link = (sb_list[i].player, wy_list[j].player)
            taken_as[link].add(how)
            named_in[link] += how == _NAMED
    partners_sb: dict[int, set[int]] = defaultdict(set)
    partners_wy: dict[int, set[int]] = defaultdict(set)
    for sb_player, wy_player in taken_as:
        partners_sb[sb_player].add(wy_player)
        partners_wy[wy_player].add(sb_player)

    # Step 3 on every sheet the two share, step 4, and the status of each link.
    pairs, dropped = [], []
    cautioned = {"both": 0, "sb_only": 0, "wy_only": 0}
    for sb_player, wy_player in sorted(taken_as):
        together = [index for index in sheets_of_sb[sb_player]
                    if wy_player in sheets[index][2]]
        passed = [index for index in together
                  if _structure(sheets[index][1][sb_player], sheets[index][2][wy_player],
                                tolerance)]
        swap_impossible = all(
            not any(sheets[index][1][sb_player].tokens & row.tokens
                    for player, row in sheets[index][2].items() if player != wy_player)
            and not any(sheets[index][2][wy_player].tokens & row.tokens
                        for player, row in sheets[index][1].items() if player != sb_player)
            for index in together)
        if len(partners_sb[sb_player]) > 1 or len(partners_wy[wy_player]) > 1:
            status = "BIJECTION_CONFLICT"
        elif not together or len(passed) / len(together) < share_minimum:
            status = "STRUCTURE_CONFLICT"
        elif named_in[(sb_player, wy_player)] > 0:
            status = _PAIRED
        elif _WEAK in taken_as[(sb_player, wy_player)]:
            status = "NAME_WEAK"
        else:
            status = "ELIMINATION_ONLY"
        if status == _PAIRED:
            for index in together:
                side, sb_rows, wy_rows = sheets[index]
                if index not in passed:
                    dropped.append({"match_key": side.match_key, "sb_player_id": sb_player})
                both = (sb_rows[sb_player].cautioned, wy_rows[wy_player].cautioned)
                if all(both):
                    cautioned["both"] += 1
                elif both[0]:
                    cautioned["sb_only"] += 1
                elif both[1]:
                    cautioned["wy_only"] += 1
        pairs.append({
            "sb_player_id": sb_player, "wy_player_id": wy_player, "status": status,
            "sheets_named": named_in[(sb_player, wy_player)],
            "sheets_together": len(together), "sheets_structure_passed": len(passed),
            "swap_impossible": swap_impossible,
            "is_goalkeeper": people.get(wy_player, ((), None))[1] == keeper,
        })
    pair_frame = _frame(pairs, _PAIR_DTYPES)
    dropped_frame = _frame(dropped, _DROPPED_DTYPES).sort_values(
        ["match_key", "sb_player_id"], kind="mergesort").reset_index(drop=True)

    # Coverage: outfield player-matches with regulation minutes whose player's paired
    # partner holds a filtered row on the other sheet of the team-match, not dropped.
    paired = pair_frame[pair_frame["status"] == _PAIRED]
    partner_of_sb = {int(sb): int(wy) for sb, wy in zip(paired["sb_player_id"],
                                                       paired["wy_player_id"], strict=True)}
    partner_of_wy = {wy: sb for sb, wy in partner_of_sb.items()}
    removed = {(row["match_key"], row["sb_player_id"]) for row in dropped}
    subsets = {key: {"team_matches": 0, "player_matches": {"sb": 0, "wy": 0},
                     "covered": {"sb": 0, "wy": 0}} for key in _subset_keys(config)}
    for side, sb_rows, wy_rows in sheets:
        block = subsets[side.subset]
        block["team_matches"] += 1
        for player, row in sb_rows.items():
            if row.goalkeeper:
                continue
            block["player_matches"]["sb"] += 1
            block["covered"]["sb"] += (partner_of_sb.get(player) in wy_rows
                                       and (side.match_key, player) not in removed)
        for player, row in wy_rows.items():
            if row.goalkeeper:
                continue
            block["player_matches"]["wy"] += 1
            partner = partner_of_wy.get(player)
            block["covered"]["wy"] += (partner in sb_rows
                                       and (side.match_key, partner) not in removed)
    for block in subsets.values():
        block["coverage"] = {provider: _share(block["covered"][provider],
                                              block["player_matches"][provider])
                             for provider in ("sb", "wy")}

    audit: dict[str, object] = {
        "status_counts": {status: int((pair_frame["status"] == status).sum())
                          for status in config["pair_status_vocabulary"]},
        "zero_minute_rows_dropped": zero,
        "player_matches_dropped": len(dropped_frame),
        "paired_outfield": int((~paired["is_goalkeeper"]).sum()),
        "swap_impossible_share": _share(int(paired["swap_impossible"].sum()), len(paired)),
        "cautioned": cautioned,
        "sheet_players": {"sb": len({p for _, rows, _ in sheets for p in rows}),
                          "wy": len({p for _, _, rows in sheets for p in rows})},
        "subsets": subsets,
    }
    return pair_frame, dropped_frame, audit


# --- the wide link ------------------------------------------------------------------

def evaluated_players(sb_sheets: pd.DataFrame, wy_sheets: pd.DataFrame,
                      match_links: pd.DataFrame
                      ) -> tuple[pd.DataFrame, dict[int, frozenset[int]],
                                 dict[int, frozenset[str]], int]:
    """The left side of the wide link and what grading it needs, from the sheets as read.

    Evaluated players are the StatsBomb sheet players with regulation minutes in a
    linked match. Returns ``sb_people`` (``left_id``, ``full_name``, ``known_as``,
    ``country``: the ``player_name``, ``player_nickname`` and ``country`` of his row in
    the linked match of largest ``match_key``, nulls included), ``sheet_ids_of_player``
    (every Wyscout player with a row for the linked team in every linked match in
    which he holds a row, zero-minute rows on either side included), the subsets in
    which he has regulation minutes, and the number of evaluated players whose rows in
    the linked matches disagree on any of the three values. Built from the readers'
    frames, never from the filter of ``team_sheet_crosswalk``.
    """
    sides = {(side.sb_game, side.sb_team): side for side in _sides(match_links)}
    sb_records = _records_by_side(sb_sheets, "sb_game_id", "sb_team_id", "sb_player_id",
                                  set(sides))
    wy_records = _records_by_side(wy_sheets, "wy_game_id", "wy_team_id", "wy_player_id",
                                  {(side.wy_game, side.wy_team) for side in sides.values()})
    values: dict[int, list[tuple[int, tuple[str | None, ...]]]] = defaultdict(list)
    sheet_ids: dict[int, set[int]] = defaultdict(set)
    subsets: dict[int, set[str]] = defaultdict(set)
    for key, records in sb_records.items():
        side = sides[key]
        roster = {int(row["wy_player_id"]) for row in wy_records.get((side.wy_game,
                                                                          side.wy_team), [])}
        for record in records:
            player = int(record["sb_player_id"])
            names = (_text(record["player_name"]), _text(record["player_nickname"]),
                     _text(record["country"]))
            values[player].append((side.match_key, names))
            sheet_ids[player] |= roster
            if int(record["minutes_regulation"]) > 0:
                subsets[player].add(side.subset)
    evaluated = sorted(subsets)
    rows, disagreeing = [], 0
    for player in evaluated:
        _, names = max(values[player], key=lambda item: item[0])
        disagreeing += len({entry for _, entry in values[player]}) > 1
        rows.append({"left_id": player, "full_name": names[0], "known_as": names[1],
                     "country": names[2]})
    people = _frame(rows, {"left_id": "int64", "full_name": object, "known_as": object,
                           "country": object})
    return (people, {player: frozenset(sheet_ids[player]) for player in evaluated},
            {player: frozenset(subsets[player]) for player in evaluated}, disagreeing)


@dataclass(frozen=True)
class _Left:
    left_id: int
    full: frozenset[str]
    known: frozenset[str] | None
    country: str | None


@dataclass(frozen=True)
class _Records:
    """The right side of the link, indexed once per call."""

    ids: tuple[int, ...]
    tokens: tuple[frozenset[str], ...]
    countries: tuple[frozenset[str], ...]
    exact: Mapping[frozenset[str], tuple[int, ...]]
    holding: Mapping[str, tuple[int, ...]]


def _country(value: object, aliases: Mapping[str, str]) -> str | None:
    """``normalise_name``, then the alias list; a missing country never agrees."""
    country = normalise_name(_text(value) or "")
    return aliases.get(country, country) or None


def _lefts(left: pd.DataFrame, config: Mapping[str, object]) -> list[_Left]:
    if left["left_id"].duplicated().any():
        raise ValueError("a left id is listed twice")
    aliases = config["country_aliases_normalised"]
    return [_Left(int(row.left_id), _tokens(row.full_name),
                  _tokens(row.known_as) if (_text(row.known_as) or "").strip() else None,
                  _country(row.country, aliases))
            for row in left.itertuples(index=False)]


def _index(right: pd.DataFrame) -> _Records:
    if right["right_id"].duplicated().any():
        raise ValueError("a right id is listed twice")
    ids = tuple(int(value) for value in right["right_id"])
    tokens = tuple(_tokens(value) for value in right["full_name"])
    countries = tuple(frozenset(normalise_name(text) for text in map(_text, values) if text)
                      - {""} for values in right["countries"])
    exact: dict[frozenset[str], list[int]] = defaultdict(list)
    holding: dict[str, list[int]] = defaultdict(list)
    for position, token_set in enumerate(tokens):
        exact[token_set].append(position)
        for token in token_set:
            holding[token].append(position)
    return _Records(ids, tokens, countries, {key: tuple(value) for key, value in exact.items()},
                    {key: tuple(value) for key, value in holding.items()})


def _candidates(tier: str, left: _Left, records: _Records, hidden: int | None,
                config: Mapping[str, object]) -> list[int]:
    """Positions of the right records that pass one tier for one left."""
    if tier == "A":
        enough = len(left.full) >= int(config["link_tier_a_minimum_tokens"])
        pool: Iterable[int] = records.exact.get(left.full, ()) if enough else ()
    elif tier == "N":
        enough = (left.known is not None
                  and len(left.known) >= int(config["link_tier_n_minimum_tokens"]))
        pool = records.exact.get(left.known, ()) if enough else ()
    else:
        shared_minimum = int(config["link_tier_b_minimum_shared_tokens"])
        near = sorted({position for token in left.full
                       for position in records.holding.get(token, ())})
        pool = [position for position in near
                if (records.tokens[position] < left.full or left.full < records.tokens[position])
                and len(records.tokens[position] & left.full) >= shared_minimum]
    return [position for position in pool
            if left.country is not None and left.country in records.countries[position]
            and records.ids[position] != hidden]


def _tiers(tiers: Sequence[str]) -> tuple[str, ...]:
    if not tiers or not set(tiers) <= _TIERS:
        raise ValueError("tiers must be a non-empty sequence of A, N and B")
    return tuple(tiers)


def _link(lefts: Sequence[_Left], records: _Records, config: Mapping[str, object],
          tiers: Sequence[str], exclude_right: Mapping[int, int] | None,
          unique_right: bool) -> list[tuple[int, int | None, str | None, str]]:
    """(left id, right id, tier, outcome) per left, in the order given."""
    results: list[tuple[int, int | None, str | None, str]] = []
    for left in lefts:
        hidden = exclude_right.get(left.left_id) if exclude_right is not None else None
        outcome: tuple[int, int | None, str | None, str] = (left.left_id, None, None,
                                                           "NO_CANDIDATE")
        for tier in tiers:
            found = _candidates(tier, left, records, hidden, config)
            if len(found) == 1:
                outcome = (left.left_id, records.ids[found[0]], tier, "LINKED")
                break
            if found:
                # Several candidates at one tier do not fall through to the next.
                outcome = (left.left_id, None, tier, "AMBIGUOUS")
                break
        results.append(outcome)
    if unique_right:
        taken = Counter(right for _, right, _, outcome in results if outcome == "LINKED")
        results = [(left, right, tier, "CLAIMED_TWICE")
                   if outcome == "LINKED" and taken[right] > 1 else (left, right, tier, outcome)
                   for left, right, tier, outcome in results]
    return results


def name_nationality_link(left: pd.DataFrame, right: pd.DataFrame,
                          config: Mapping[str, object], *, tiers: Sequence[str],
                          exclude_right: Mapping[int, int] | None,
                          unique_right: bool) -> pd.DataFrame:
    """Link each left record to at most one right record by name tokens and country.

    ``left``: ``left_id``, ``full_name``, ``known_as`` (nullable), ``country``.
    ``right``: ``right_id``, ``full_name``, ``countries`` (a tuple). Tiers are tried
    in the order given; a tier is tried only when the one before found no candidate,
    and several candidates at one tier are ``AMBIGUOUS``. Tier A: equal full-name
    token sets of at least ``link_tier_a_minimum_tokens`` tokens; tier N: the same
    with ``known_as`` (skipped when null), ``link_tier_n_minimum_tokens``; tier B:
    one full-name token set strictly contains the other with at least
    ``link_tier_b_minimum_shared_tokens`` shared. Every tier requires the
    nationality to agree: the left country after ``normalise_name`` and
    ``country_aliases_normalised`` equals one of the right's normalised countries.
    ``exclude_right`` hides one right id from one left; with ``unique_right`` a right
    id reached by two or more lefts makes all of them ``CLAIMED_TWICE``. Neither
    keyword has a default.

    Returns ``left_id``, ``right_id`` (Int64: the record for ``LINKED`` and for
    ``CLAIMED_TWICE``, NA otherwise), ``tier`` (None for ``NO_CANDIDATE``) and
    ``outcome``. Only a ``LINKED`` row is a link.
    """
    _frozen(config, "link_requires_nationality_agreement", True)
    _frozen(config, "country_alias_miss_is_no_link", True)
    results = _link(_lefts(left, config), _index(right), config, _tiers(tiers),
                    exclude_right, unique_right)
    return _frame([dict(zip(_RESULT_DTYPES, result, strict=True)) for result in results],
                  _RESULT_DTYPES)


def _right(wy_people: pd.DataFrame) -> pd.DataFrame:
    """Every record of the Wyscout people file, with both areas as its countries."""
    return pd.DataFrame({
        "right_id": wy_people["wy_player_id"].to_numpy(dtype=np.int64),
        "full_name": pd.Series(list(wy_people["full_name"]), dtype=object),
        "countries": pd.Series([(_text(birth), _text(passport)) for birth, passport
                                in zip(wy_people["birth_area"], wy_people["passport_area"],
                                       strict=True)], dtype=object),
    })


def _interval(successes: int, trials: int, z: float) -> dict[str, float | None]:
    lower, upper = wilson_interval(successes, trials, z)
    return {"point": successes / trials if trials else None, "lower": lower, "upper": upper}


def _rates(players: Sequence[int], classes: Mapping[int, str], outcomes: Mapping[int, str],
           still_linked: Mapping[int, bool], z: float) -> dict[str, object]:
    """Counts and the four rates of the protocol's purpose (b) over a set of players."""
    by_class = Counter(classes[player] for player in players)
    paired = [player for player in players if player in still_linked]
    stressed = sum(still_linked[player] for player in paired)
    return {
        "evaluated": len(players),
        "paired": len(paired),
        "classes": {name: by_class[name] for name in _CLASSES},
        "outcomes": {name: sum(outcomes[player] == name for player in players)
                     for name in LINK_OUTCOMES},
        "recall": _interval(by_class["CORRECT"], len(players) - by_class["UNVERIFIABLE"], z),
        "false_link_rate": _interval(by_class["FALSE"],
                                     by_class["CORRECT"] + by_class["FALSE"], z),
        "no_link_rate": _interval(by_class["NO_LINK"], len(players), z),
        "absent_partner_stress_rate": _interval(stressed, len(paired), z),
    }


def evaluate_wide_link(pairs: pd.DataFrame, sb_people: pd.DataFrame, wy_people: pd.DataFrame,
                       sheet_ids_of_player: Mapping[int, frozenset[int]],
                       subset_of_player: Mapping[int, frozenset[str]],
                       config: Mapping[str, object]) -> list[dict[str, object]]:
    """Grade the wide link against the team-sheet pairing, per tier set and pool.

    Left = ``sb_people`` (``evaluated_players``); right = every Wyscout record.
    ``name_nationality_link`` runs once per tier set on all evaluated players. A
    player with a ``LINKED`` record is ``CORRECT`` (paired, the record is his
    partner), ``FALSE`` (paired and another record, or unpaired and a record on none
    of his sheets) or ``UNVERIFIABLE`` (unpaired, a record on one of his sheets);
    any other outcome is ``NO_LINK``. The absent-partner stress is one evaluation per
    paired player with his partner hidden from him alone; every other player keeps the
    record his full run reached, ``LINKED`` or ``CLAIMED_TWICE``, and the
    ``CLAIMED_TWICE`` rule is applied against those. A pool block holds the players
    whose subsets meet the pool, with the class and stress result of the single run.

    Each block: ``tiers``, ``pool``, counts and rates over its players, the same on
    paired players only and by nickname present or absent, ``namesake_collision`` for
    the tier set and ``absent_partner_bound``. Verdicts are ``link_verdict``'s.
    """
    _frozen(config, "link_requires_unique_both_directions", True)
    _frozen(config, "link_recall_denominator", "evaluated_minus_unverifiable")
    _frozen(config, "link_false_link_rate_denominator", "correct_plus_false")
    _frozen(config, "link_absent_partner_denominator", "paired_players")
    _frozen(config, "link_absent_partner_bound", "max(stress_upper, namesake_collision_upper)")
    _frozen(config, "link_left_name_form",
            {"A": "player_name", "N": "player_nickname", "B": "player_name"})
    _frozen(config, "link_right_name_form", "first name plus last name")
    _frozen(config, "link_candidate_pool", "every record of the Pappalardo players file")
    _frozen(config, "link_evaluated_players",
            "every StatsBomb sheet player with regulation minutes in a linked match, "
            "goalkeepers included, paired or not")
    _frozen(config, "link_outcome_classes", list(_CLASSES))
    paired_rows = pairs[pairs["status"] == config["paired_status"]]
    if paired_rows["sb_player_id"].duplicated().any():
        raise ValueError("a paired link is not a partial bijection")
    partner = {int(sb): int(wy) for sb, wy in zip(paired_rows["sb_player_id"],
                                                 paired_rows["wy_player_id"], strict=True)}
    lefts = _lefts(sb_people, config)
    records = _index(_right(wy_people))
    nickname = {left.left_id: left.known is not None for left in lefts}
    z = float(config["wilson_z"])

    players = [left.left_id for left in lefts]
    if any(not subset_of_player.get(player) for player in players):
        raise ValueError("an evaluated player has regulation minutes in no subset")
    subset_keys = _subset_keys(config)
    pools: list[tuple[str, list[int]]] = []
    for pool in config["pools"]:
        if pool in subset_keys:
            pools.append((pool, [p for p in players if pool in subset_of_player[p]]))
        elif pool == config["primary_pool"]:
            pools.append((pool, players))
        else:
            raise ValueError("a pool is neither a subset nor the primary pool")

    blocks: list[dict[str, object]] = []
    for tier_set in config["link_tier_sets"]:
        tiers = _tiers(tier_set)
        full = _link(lefts, records, config, tiers, None, True)
        holders: dict[int, set[int]] = defaultdict(set)
        classes, outcomes = {}, {}
        for left_id, right_id, _, outcome in full:
            outcomes[left_id] = outcome
            if outcome in ("LINKED", "CLAIMED_TWICE"):
                holders[right_id].add(left_id)
            if outcome != "LINKED":
                classes[left_id] = "NO_LINK"
            elif left_id in partner:
                classes[left_id] = "CORRECT" if right_id == partner[left_id] else "FALSE"
            elif right_id in sheet_ids_of_player.get(left_id, frozenset()):
                classes[left_id] = "UNVERIFIABLE"
            else:
                classes[left_id] = "FALSE"
        still_linked = {}
        for left in lefts:
            if left.left_id not in partner:
                continue
            ((_, right_id, _, outcome),) = _link([left], records, config, tiers,
                                                 {left.left_id: partner[left.left_id]}, True)
            others = holders.get(right_id, set()) - {left.left_id}
            still_linked[left.left_id] = outcome == "LINKED" and not others
        namesake = namesake_collision(wy_people, config, tiers=tiers)
        for pool, members in pools:
            block: dict[str, object] = {"tiers": list(tiers), "pool": pool}
            block.update(_rates(members, classes, outcomes, still_linked, z))
            for name, chosen in (
                    ("paired_only", [p for p in members if p in partner]),
                    ("nickname_present", [p for p in members if nickname[p]]),
                    ("nickname_absent", [p for p in members if not nickname[p]])):
                block[name] = _rates(chosen, classes, outcomes, still_linked, z)
            stress_upper = block["absent_partner_stress_rate"]["upper"]
            block["namesake_collision"] = dict(namesake)
            block["absent_partner_bound"] = (
                None if stress_upper is None or namesake["upper"] is None
                else max(stress_upper, namesake["upper"]))
            blocks.append(block)
    return blocks


def namesake_collision(wy_people: pd.DataFrame, config: Mapping[str, object],
                       *, tiers: Sequence[str]) -> dict[str, object]:
    """Pappalardo alone: records whose own name and birth area link another record.

    Left = each record with its own ``full_name``, no ``known_as`` and the country of
    ``link_namesake_left_country``; right = every record, with each left's own record
    hidden from it and ``unique_right`` false, the only call that passes false.
    ``linked`` lefts over all ``records``, with a Wilson interval.
    """
    left = pd.DataFrame({
        "left_id": wy_people["wy_player_id"].to_numpy(dtype=np.int64),
        "full_name": pd.Series(list(wy_people["full_name"]), dtype=object),
        "known_as": pd.Series([None] * len(wy_people), dtype=object),
        "country": pd.Series(list(wy_people[config["link_namesake_left_country"]]),
                             dtype=object),
    })
    own = {int(player): int(player) for player in wy_people["wy_player_id"]}
    links = name_nationality_link(left, _right(wy_people), config, tiers=tiers,
                                  exclude_right=own, unique_right=False)
    linked = int((links["outcome"] == "LINKED").sum())
    return {"linked": linked, "records": len(links),
            **_interval(linked, len(links), float(config["wilson_z"]))}


def wilson_interval(successes: int, trials: int, z: float) -> tuple[float | None, float | None]:
    """Wilson score interval for ``successes`` of ``trials``; (None, None) for none."""
    if not 0 <= successes <= trials:
        raise ValueError("successes must lie between 0 and trials")
    if trials == 0:
        return None, None
    p = successes / trials
    z2 = z * z
    denominator = 1 + z2 / trials
    centre = (p + z2 / (2 * trials)) / denominator
    half = z * math.sqrt(p * (1 - p) / trials + z2 / (4 * trials * trials)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def _finite(value: object) -> bool:
    return isinstance(value, numbers.Real) and math.isfinite(value)


def link_verdict(block: Mapping[str, object], failed_gates: Sequence[str],
                 config: Mapping[str, object]) -> tuple[str, str | None]:
    """The protocol's wide-link table on the ``link_verdict_pool`` block.

    ``INCONCLUSIVE`` with the first of ``link_inconclusive_reasons`` that holds: a
    gate in ``failed_gates``, then too few evaluated players (an empty block, from a
    run a gate stopped, has none). Otherwise ``LINK_USABLE`` iff the false-link
    upper bound, the larger of the stress and namesake upper bounds and the recall
    lower bound all meet their limits, each inclusive; an undefined bound fails.
    """
    if set(config["verdict_vocabulary"]["link"]) != _LINK_TOKENS:
        raise ValueError("the link vocabulary is not the one implemented here")
    reasons = list(config["link_inconclusive_reasons"])
    if _EVALUATED not in reasons:
        raise ValueError("link_inconclusive_reasons does not end in the evaluated-players gate")
    failed = set(failed_gates)
    minimum = int(config["link_minimum_evaluated_players"])
    for reason in reasons:
        if reason == _EVALUATED:
            evaluated = block.get("evaluated")
            holds = not (_finite(evaluated) and evaluated >= minimum)
        else:
            holds = reason in failed
        if holds:
            return "INCONCLUSIVE", reason
    if block.get("pool") != config["link_verdict_pool"]:
        raise ValueError("link_verdict grades the link_verdict_pool block only")
    false_upper = block["false_link_rate"]["upper"]
    recall_lower = block["recall"]["lower"]
    stress_upper = block["absent_partner_stress_rate"]["upper"]
    namesake_upper = block["namesake_collision"]["upper"]
    bound = (max(stress_upper, namesake_upper)
             if _finite(stress_upper) and _finite(namesake_upper) else None)
    usable = (_finite(false_upper)
              and false_upper <= float(config["link_false_link_rate_upper_maximum"])
              and _finite(bound)
              and bound <= float(config["link_absent_partner_false_link_rate_upper_maximum"])
              and _finite(recall_lower)
              and recall_lower >= float(config["link_recall_lower_minimum"]))
    return ("LINK_USABLE", None) if usable else ("LINK_NOT_ESTABLISHED", None)


# --- the permuted-link control and the digest ------------------------------------------

def permuted_partners(keys: np.ndarray, stratum: Sequence[tuple[int, str]],
                      config: Mapping[str, object], *, seed: int) -> tuple[np.ndarray, int]:
    """A derangement inside each (cluster team, Wyscout role) stratum.

    ``keys`` are one cell's Wyscout player keys, ascending and distinct; ``stratum``
    is aligned with them. ``partner[i]`` is the position of the unit whose Wyscout
    value unit ``i`` takes. Strata are visited in ascending team id, then in the order
    of ``rank_strata_roles``; in a stratum of ``k >= 2`` units the positions in key
    order are shuffled by one generator per call and shifted cyclically, so no unit
    keeps its own value. A stratum of one draws nothing and keeps itself; the number
    of such units is returned beside ``partner``. Reads no frame and no value.
    """
    _frozen(config, "permuted_link_stratum", "bootstrap_cluster_aggregated_player x wy_role")
    keys = np.asarray(keys)
    if keys.ndim != 1 or len(stratum) != len(keys):
        raise ValueError("stratum must give one (team, role) per key")
    if len(keys) > 1 and not bool(np.all(np.diff(keys) > 0)):
        raise ValueError("keys must be ascending and distinct")
    roles = list(config["rank_strata_roles"])
    groups: dict[tuple[int, int], list[int]] = defaultdict(list)
    for position, (team, role) in enumerate(stratum):
        if role not in roles:
            raise ValueError("a role outside rank_strata_roles")
        groups[(int(team), roles.index(role))].append(position)
    rng = np.random.default_rng(np.random.SeedSequence(
        [int(config["seed"]), int(config["seed_streams"]["permuted_link"]), int(seed)]))
    partner = np.arange(len(keys), dtype=np.int64)
    singletons = 0
    for group in sorted(groups):
        positions = np.asarray(groups[group], dtype=np.int64)
        if len(positions) == 1:
            singletons += 1
            continue
        shuffled = positions[rng.permutation(len(positions))]
        partner[shuffled] = np.roll(shuffled, -1)
    return partner, singletons


def crosswalk_digest(frame: pd.DataFrame, columns: Sequence[str]) -> str:
    """sha256 of the rows as ``a|b`` lines, sorted as strings and joined by newlines.

    No trailing newline, UTF-8, the convention of the folder digest. The digest is
    written to the local results only.
    """
    lines = sorted("|".join(str(value) for value in row)
                   for row in frame[list(columns)].itertuples(index=False, name=None))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
