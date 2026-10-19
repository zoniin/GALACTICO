#!/usr/bin/env python
"""E-10's structure-only counts before registration, per league, from the tag sidecar.

    python scripts/e10_root_counts.py                  # the registered config
    python scripts/e10_root_counts.py --config PATH    # a config at another path

What it counts: items 3, 4 and 5 of ``verified_by_root_before_registration`` in E-10's
``config.json``, which PIPELINE.md section 13 ("Before registration") has the root run on the
corpus and record in the registration commit, and which ROOT-DECISIONS 2.9 Z2 allows because
they compute no outcome:

3. The ``dismissal_check`` assumption. Per league, the players whose event record carries a
   ``second_yellow`` card, those among them whose sheet ``red_minute`` in that match is not
   null, and the share. The assumption holds in a league when the share is at least
   ``dismissal_assumption_minimum_share``, and holds when it holds in every league; otherwise
   ``dismissal_check_fallback`` replaces ``dismissal_check`` before registration and the draft
   is audited again. A league with no such player has no share, and the assumption is not
   shown to hold there. An event whose ``player_id`` is 0 is credited to no player (the raw
   ``playerId`` 0, kept by the neutral frames and flagged ``player_attributed`` false in the
   sidecar; no sheet lists player 0), so it is no player of this count: ROOT-DECISIONS 2.9 Z6,
   ruled before any count was seen, leaves such pairs out of the count and the share and has
   them printed apart (the unattributed cards of both teams in one match are one pair). Beside
   the count, changing none of it: those pairs, the players not listed on the sheet of that
   match, and the players left out because their ``second_yellow`` events are all outside
   ``regulation_periods``. Item 4 keeps player 0: ``dismissal_check`` counts distinct player
   ids, so an unattributed dismissal card is a residual of the rule as written.
4. The ``dismissal_check`` residuals. Per league, the players with a card of
   ``dismissal_cards`` in the event record and a null sheet ``red_minute``, and the reverse:
   the sheet players whose ``red_minute`` is not null and who have no such card in the event
   record.
5. The ``reliability_split`` calendar count. Per league and for each half, the distribution
   over teams of the share of the half's meetings dated before ``evaluation_start`` and of
   the share of the half's home meetings.

Every key is read from the config: ``leagues``, ``dismissal_cards``, ``regulation_periods``,
``dismissal_check`` (its ``sheet_table`` and ``sheet_field``), ``dismissal_check_fallback``
(printed when the assumption fails), ``dismissal_assumption_minimum_share``,
``reliability_split`` and ``evaluation_start``. The rule texts this file implements are pinned
below (``PINNED_ITEMS``, ``PINNED_DISMISSAL_RULE``, ``PINNED_SPLIT_RULE``): a config whose
words differ is refused with exit 2, never counted under a rule it no longer states.

Definitions, in the config's words and nothing added:

- A player in a match is a ``(game_id, player_id)`` pair, as "the players ... whose sheet
  red_minute in that match" reads. An event counts for items 3 and 4 when its neutral
  ``period`` is in ``regulation_periods`` ("a regulation event" of ``dismissal_check``) and its
  sidecar ``card`` is the card named. The sheet is the ``dismissal_check.sheet_table`` of the
  sidecar and its ``sheet_field``; a player the sheet of that match does not list has no
  ``red_minute`` there, so it is null. Beside each count, labelled as a part of it and changing
  none: the players not listed on the sheet at all, those whose ``player_id`` is 0, the cards
  outside ``regulation_periods`` that the counts leave out, and the card players the sheet
  lists under a team other than their event's (``dismissal_check`` compares per team).
- A meeting is one of a team's rows against an opponent: one per team per match of the
  sidecar's ``matches`` table, home or away. Its date is ``date_utc`` normalised to the day,
  as E-10's row contract normalises ``date`` (PIPELINE 4.1); "dated before" is the calendar
  date strictly before (``prior_rule``). The halves are those ``reliability_split`` gives.
- Validity. ``reliability_split`` leaves an invalid meeting out of both halves, and which
  meeting is invalid is decided by E-10's ``match_table`` (PIPELINE 2.4), which is not built.
  No validity rule is invented here: every meeting is counted, and the output says so.

Quartiles are numpy's default (linear interpolation); each distribution is also printed
exactly, as ``k/n:t`` (``t`` teams with ``k`` of their ``n`` meetings in the half).

What it reads, through the shipped loaders only: ``sidecar.verify`` and ``sidecar.load`` of
``events`` (``event_id``, ``card``), of the sheet table (``game_id``, ``team_id``,
``player_id`` and the sheet field) and of ``matches`` (``game_id``, ``date_utc``,
``home_team_id``, ``away_team_id``); and, because the sidecar carries no period, team or
player, the neutral actions through ``load_public`` (``game_id``, ``period``, ``team_id``,
``player_id``, ``event_id``), joined by ``sidecar.attach``.

Non-claim: no descriptor, conceded entry, window, goal, result or any other outcome is
computed or read, and no team or player is named in the output. The counts are of the corpus
as built; they change nothing in E-10's rules.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "experiments/preregistered/E-10-conceded-shape/config.json"
"""The registered config (the draft's until E-10's registration commit, when it moved)."""

SECOND_YELLOW = "second_yellow"  # the card item 3 names
# The raw playerId of an event no player is credited with: the neutral frames keep it as
# player_id 0, the sidecar flags it player_attributed false, and no sheet lists it.
UNATTRIBUTED = 0
ACTION_COLUMNS: tuple[str, ...] = ("game_id", "period", "team_id", "player_id", "event_id")
CALENDAR_COLUMNS: tuple[str, ...] = ("game_id", "date_utc", "home_team_id", "away_team_id")
PLAYER: list[str] = ["game_id", "player_id"]
HALVES: tuple[str, ...] = ("A", "B")
QUANTILES: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)
VALIDITY_NOTE = (
    "validity: reliability_split leaves an invalid meeting out of both halves; E-10's "
    "match_table decides validity and is not built, so every meeting is counted here and none "
    "is left out of a half."
)
NO_OUTCOME_NOTE = (
    "These counts compute no outcome: no descriptor, conceded entry, window, goal or result is "
    "read or computed, and no team or player is named."
)

# The words this file implements, as the draft states them on 18 October 2026. A config whose
# words differ is refused (exit 2): the root then reads the change and edits this file.
PINNED_ITEMS: Mapping[str, str] = {
    "dismissal_check assumption": (
        "dismissal_check assumption (ROOT 2.9 Z2): a structure-only count, run by the root on "
        "the corpus before registration and computing no outcome, per league, of the players "
        "whose event record carries a second_yellow card and of those among them whose sheet "
        "red_minute in that match is not null, its counts and share per league recorded in the "
        "registration commit; the assumption holds when that share is at least "
        "dismissal_assumption_minimum_share in every league; otherwise "
        "dismissal_check_fallback replaces dismissal_check before registration and the draft "
        "is audited again"
    ),
    "dismissal_check residuals": (
        "dismissal_check residuals: the same structure-only count of players with a dismissal "
        "card in the event record and a null sheet red_minute, and of the reverse, per league, "
        "is stated in the registration commit; these are the matches dismissals_mismatch is "
        "built to invalidate, and only G1 bounds them"
    ),
    "reliability_split calendar count": (
        "reliability_split calendar count (third audit, 2-1): a structure-only count on the "
        "match calendars, run by the root before registration and computing no outcome, per "
        "league and for each half of reliability_split, the distribution over teams of the "
        "share of the half's meetings dated before evaluation_start and of the half's home "
        "meetings; recorded in the registration commit; it changes nothing in the rule"
    ),
}
PINNED_DISMISSAL_RULE = (
    "per team and match, the number of distinct players with a regulation event whose sidecar "
    "card is in dismissal_cards equals the number of the team's sheet players whose red_minute "
    "is not null; otherwise the match is invalid (dismissals_mismatch)"
)
PINNED_SPLIT_RULE = (
    "each half holds one meeting with each opponent: the team's meetings with an opponent are "
    "its rows against it, valid or not, the earlier and the later by (date, game_id); "
    "opponents are ordered by the date of the earlier meeting, then team id; for an opponent "
    "at a position (0-based) of 0 or 1 modulo 4 half A takes the earlier meeting, at 2 or 3 "
    "modulo 4 the later meeting; half B takes the other; a team with one meeting against an "
    "opponent has no later meeting; an invalid meeting is in neither half and is not replaced"
)


class ConfigRefused(ValueError):
    """The config does not state the rules this file implements, or lacks a key it reads."""


# ------------------------------------------------------------------------------ config


@dataclass(frozen=True)
class Settings:
    """The keys of the config the counts read."""

    leagues: tuple[str, ...]
    dismissal_cards: tuple[str, ...]
    regulation_periods: tuple[str, ...]
    sheet_table: str
    sheet_field: str
    minimum_share: Fraction  # the config's decimal, read exactly
    evaluation_start: str
    fallback: str


def settings(config: Mapping[str, Any]) -> Settings:
    """The keys the counts read, after the pinned rule texts are found word for word."""
    def need(key: str) -> Any:
        if key not in config:
            raise ConfigRefused(f"the config has no {key!r}")
        return config[key]

    items = need("verified_by_root_before_registration")
    for prefix, text in PINNED_ITEMS.items():
        found = [item for item in items if isinstance(item, str) and item.startswith(prefix)]
        if found != [text]:
            raise ConfigRefused(f"verified_by_root_before_registration: the {prefix!r} item is "
                                f"not the one this file counts")
    check = need("dismissal_check")
    if not isinstance(check, Mapping) or check.get("rule") != PINNED_DISMISSAL_RULE:
        raise ConfigRefused("dismissal_check.rule is not the rule this file counts")
    if need("reliability_split") != PINNED_SPLIT_RULE:
        raise ConfigRefused("reliability_split is not the rule this file counts")

    def strings(key: str) -> tuple[str, ...]:
        value = need(key)
        if not isinstance(value, list) or not value \
                or not all(isinstance(entry, str) for entry in value):
            raise ConfigRefused(f"{key} is not a non-empty list of strings")
        return tuple(value)

    cards = strings("dismissal_cards")
    if SECOND_YELLOW not in cards:
        raise ConfigRefused(f"dismissal_cards does not hold {SECOND_YELLOW!r}, the card the "
                            f"assumption count names")
    minimum = need("dismissal_assumption_minimum_share")
    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
        raise ConfigRefused("dismissal_assumption_minimum_share is not a number")
    for key in ("sheet_table", "sheet_field"):
        if not isinstance(check.get(key), str):
            raise ConfigRefused(f"dismissal_check.{key} is not a string")
    return Settings(
        leagues=strings("leagues"),
        dismissal_cards=cards,
        regulation_periods=strings("regulation_periods"),
        sheet_table=check["sheet_table"],
        sheet_field=check["sheet_field"],
        minimum_share=Fraction(str(minimum)),
        evaluation_start=str(pd.Timestamp(need("evaluation_start")).date()),
        fallback=str(need("dismissal_check_fallback")),
    )


# -------------------------------------------------------------------- the dismissal counts


def _require(frame: pd.DataFrame, columns: Iterable[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} has no column {missing}")


def _member(frame: pd.DataFrame, keys: pd.DataFrame) -> np.ndarray:
    """Whether each row's ``(game_id, player_id)`` is a row of ``keys``."""
    if frame.empty:
        return np.zeros(0, dtype=bool)
    if keys.empty:
        return np.zeros(len(frame), dtype=bool)
    return pd.MultiIndex.from_frame(frame[PLAYER]).isin(
        pd.MultiIndex.from_frame(keys[PLAYER])).astype(bool)


def card_events(actions: pd.DataFrame, *, dismissal_cards: Sequence[str],
                regulation_periods: Sequence[str], regulation: bool = True) -> pd.DataFrame:
    """The events whose sidecar ``card`` is in ``dismissal_cards``: ``game_id``, ``team_id``,
    ``player_id``, ``card``; with ``regulation`` those in ``regulation_periods``, else the
    others."""
    _require(actions, ("game_id", "period", "team_id", "player_id", "card"), "actions")
    carded = actions["card"].isin(list(dismissal_cards)).to_numpy(dtype=bool)
    inside = actions["period"].isin(list(regulation_periods)).to_numpy(dtype=bool)
    mask = carded & (inside if regulation else ~inside)
    return actions.loc[mask, ["game_id", "team_id", "player_id", "card"]].reset_index(drop=True)


def player_cards(actions: pd.DataFrame, *, dismissal_cards: Sequence[str],
                 regulation_periods: Sequence[str]) -> pd.DataFrame:
    """One row per player in a match with a regulation event whose card is in
    ``dismissal_cards``: ``game_id``, ``player_id`` and one boolean column per card, named as
    the card, true when one of his regulation events carries it. Sorted by the pair."""
    events = card_events(actions, dismissal_cards=dismissal_cards,
                         regulation_periods=regulation_periods)
    players = events[PLAYER].drop_duplicates().sort_values(PLAYER).reset_index(drop=True)
    for card in dismissal_cards:
        players[card] = _member(players, events.loc[events["card"] == card, PLAYER])
    return players


def sheet_players(squads: pd.DataFrame, *, sheet_field: str) -> pd.DataFrame:
    """The sheet: ``game_id``, ``player_id``, ``team_id`` and ``sheet_red`` (the field is not
    null), one row per player in a match. ``ValueError`` when the sheet lists a player twice in
    one match: such a player would not have one ``red_minute``."""
    _require(squads, ("game_id", "team_id", "player_id", sheet_field), "the sheet")
    if squads.duplicated(PLAYER).any():
        raise ValueError("the sheet lists a player twice in one match")
    sheet = squads[["game_id", "player_id", "team_id"]].reset_index(drop=True)
    sheet["sheet_red"] = squads[sheet_field].notna().to_numpy(dtype=bool)
    return sheet


@dataclass(frozen=True)
class AssumptionCount:
    """Item 3 for one league. The parts after ``holds`` change none of the counts."""

    second_yellow_players: int  # players in a match with a regulation second_yellow event
    sheet_red_not_null: int  # of them, those whose sheet red_minute in that match is not null
    share: Fraction | None  # their share; None when no player carries a second_yellow event
    holds: bool | None  # share >= dismissal_assumption_minimum_share; None without a share
    unattributed: int  # left out (Z6): matches with a regulation second_yellow on player_id 0
    not_listed: int  # of second_yellow_players, not on the sheet of that match
    outside_only: int  # left out: second_yellow events only outside regulation_periods


def assumption_count(actions: pd.DataFrame, squads: pd.DataFrame, *,
                     dismissal_cards: Sequence[str], regulation_periods: Sequence[str],
                     sheet_field: str, minimum_share: Fraction) -> AssumptionCount:
    if SECOND_YELLOW not in dismissal_cards:
        raise ValueError(f"dismissal_cards does not hold {SECOND_YELLOW!r}")
    cards = player_cards(actions, dismissal_cards=dismissal_cards,
                         regulation_periods=regulation_periods)
    carded = cards.loc[cards[SECOND_YELLOW], PLAYER]
    unattributed = carded["player_id"] == UNATTRIBUTED  # no player (ROOT 2.9 Z6)
    second = carded.loc[~unattributed]
    sheet = sheet_players(squads, sheet_field=sheet_field)
    with_red = int(_member(second, sheet.loc[sheet["sheet_red"], PLAYER]).sum())
    share = Fraction(with_red, len(second)) if len(second) else None
    outside = card_events(actions, dismissal_cards=(SECOND_YELLOW,),
                          regulation_periods=regulation_periods, regulation=False)
    outside = outside[PLAYER].drop_duplicates()
    return AssumptionCount(
        second_yellow_players=len(second),
        sheet_red_not_null=with_red,
        share=share,
        holds=None if share is None else share >= minimum_share,
        unattributed=int(unattributed.sum()),
        not_listed=int((~_member(second, sheet)).sum()),
        outside_only=int((~_member(outside, second)).sum()),
    )


@dataclass(frozen=True)
class ResidualCount:
    """Item 4 for one league. The parts beside each count change none of them."""

    card_players: int  # players in a match with a regulation event carrying a dismissal card
    card_sheet_null: int  # of them, a null sheet red_minute in that match (unlisted included)
    card_sheet_null_by_card: tuple[tuple[str, int], ...]  # of those, carrying each card
    card_not_listed: int  # of card_sheet_null, not listed on the sheet of that match at all
    card_unattributed: int  # of card_sheet_null, player_id 0 (never on a sheet)
    card_listed_other_team: int  # card players the sheet lists under a team not their event's
    sheet_red_players: int  # sheet players in a match whose red_minute is not null
    sheet_red_no_card: int  # of them, no regulation event carrying a dismissal card
    sheet_red_card_outside: int  # of those, a dismissal card on an event outside regulation


def residual_counts(actions: pd.DataFrame, squads: pd.DataFrame, *,
                    dismissal_cards: Sequence[str], regulation_periods: Sequence[str],
                    sheet_field: str) -> ResidualCount:
    cards = player_cards(actions, dismissal_cards=dismissal_cards,
                         regulation_periods=regulation_periods)
    sheet = sheet_players(squads, sheet_field=sheet_field)
    red = sheet.loc[sheet["sheet_red"], PLAYER]
    null = cards.loc[~_member(cards, red)]
    listed = _member(null, sheet)
    events = card_events(actions, dismissal_cards=dismissal_cards,
                         regulation_periods=regulation_periods)
    joined = events.merge(sheet[["game_id", "player_id", "team_id"]], on=PLAYER,
                          suffixes=("", "_sheet"))
    other = joined.loc[joined["team_id"] != joined["team_id_sheet"], PLAYER].drop_duplicates()
    unmatched = red.loc[~_member(red, cards)]
    outside = card_events(actions, dismissal_cards=dismissal_cards,
                          regulation_periods=regulation_periods, regulation=False)
    return ResidualCount(
        card_players=len(cards),
        card_sheet_null=len(null),
        card_sheet_null_by_card=tuple((card, int(null[card].sum())) for card in dismissal_cards),
        card_not_listed=int((~listed).sum()),
        card_unattributed=int((null["player_id"] == UNATTRIBUTED).sum()),
        card_listed_other_team=len(other),
        sheet_red_players=len(red),
        sheet_red_no_card=len(unmatched),
        sheet_red_card_outside=int(_member(unmatched, outside).sum()),
    )


# ------------------------------------------------------------------- the calendar count


def team_meetings(calendar: pd.DataFrame) -> pd.DataFrame:
    """Two rows per match, one per team: ``team_id``, ``opponent_id``, ``game_id``, ``date``
    (normalised to the day) and ``is_home``. ``calendar`` holds ``game_id``, ``date``,
    ``home_team_id`` and ``away_team_id``; ``ValueError`` when a ``game_id`` repeats."""
    _require(calendar, ("game_id", "date", "home_team_id", "away_team_id"), "the calendar")
    if calendar["game_id"].duplicated().any():
        raise ValueError("a game_id repeats in the calendar")
    day = pd.to_datetime(calendar["date"]).dt.normalize().to_numpy()
    sides = [
        pd.DataFrame({"team_id": calendar[team].to_numpy(dtype="int64"),
                      "opponent_id": calendar[opponent].to_numpy(dtype="int64"),
                      "game_id": calendar["game_id"].to_numpy(dtype="int64"),
                      "date": day, "is_home": home})
        for team, opponent, home in (("home_team_id", "away_team_id", True),
                                     ("away_team_id", "home_team_id", False))
    ]
    return pd.concat(sides, ignore_index=True)


def meeting_halves(calendar: pd.DataFrame) -> pd.DataFrame:
    """Every meeting of every team with its half under ``reliability_split``.

    Columns: ``team_id``, ``opponent_id``, ``game_id``, ``date``, ``is_home``, ``position``
    (the opponent's 0-based place: by the date of the earlier meeting, then the opponent's
    team id), ``meeting`` (``earlier`` or ``later`` by ``(date, game_id)``) and ``half``. At a
    position of 0 or 1 modulo 4 half A takes the earlier meeting and half B the later; at 2 or 3
    half A takes the later and half B the earlier. With one meeting there is no later meeting,
    so the half that would take it has none for that opponent. Every meeting is in a half: no
    validity is applied (``VALIDITY_NOTE``). ``ValueError`` when a team meets an opponent more
    than twice: the rule names an earlier and a later meeting only.
    """
    rows = team_meetings(calendar).sort_values(["team_id", "opponent_id", "date", "game_id"])
    rows["order"] = rows.groupby(["team_id", "opponent_id"]).cumcount()
    if (rows["order"] > 1).any():
        raise ValueError("a team meets an opponent more than twice; reliability_split names "
                         "an earlier and a later meeting only")
    earlier = rows.loc[rows["order"] == 0].sort_values(["team_id", "date", "opponent_id"])
    earlier = earlier.assign(position=earlier.groupby("team_id").cumcount())
    rows = rows.merge(earlier[["team_id", "opponent_id", "position"]],
                      on=["team_id", "opponent_id"], validate="many_to_one")
    takes_earlier_in_a = (rows["position"] % 4 < 2).to_numpy()
    is_earlier = (rows["order"] == 0).to_numpy()
    rows["meeting"] = np.where(is_earlier, "earlier", "later")
    rows["half"] = np.where(is_earlier == takes_earlier_in_a, "A", "B")
    return (rows.drop(columns="order")
            .sort_values(["team_id", "half", "date", "game_id"]).reset_index(drop=True))


def half_counts(halves: pd.DataFrame, *, evaluation_start: str) -> pd.DataFrame:
    """Per half and team: ``meetings``, ``before`` (dated strictly before ``evaluation_start``)
    and ``home``. Every team of the calendar has a row in each half, 0 meetings included."""
    start = pd.Timestamp(evaluation_start).normalize()
    marked = halves.assign(before=(halves["date"] < start).to_numpy())
    counts = marked.groupby(["half", "team_id"]).agg(
        meetings=("game_id", "size"), before=("before", "sum"), home=("is_home", "sum"))
    teams = sorted(set(halves["team_id"].tolist()))
    full = pd.MultiIndex.from_product([list(HALVES), teams], names=["half", "team_id"])
    return counts.reindex(full, fill_value=0).astype("int64").reset_index()


@dataclass(frozen=True)
class Distribution:
    """The distribution over teams of one share ``k / n``."""

    teams: int
    quantiles: tuple[float, ...]  # at QUANTILES: minimum, first quartile, median, third, maximum
    exact: tuple[tuple[int, int, int], ...]  # (k, n, teams), by k / n then n


def distribution(pairs: Iterable[tuple[int, int]]) -> Distribution | None:
    """The distribution of ``k / n`` over the given ``(k, n)`` pairs, ``n > 0``; None for none."""
    kept = [(int(k), int(n)) for k, n in pairs]
    if any(n <= 0 or not 0 <= k <= n for k, n in kept):
        raise ValueError("a share needs 0 <= k <= n and n > 0")
    if not kept:
        return None
    values = np.array([k / n for k, n in kept], dtype=float)
    quantiles = tuple(float(q) for q in np.quantile(values, QUANTILES))
    tally = Counter(kept)
    exact = tuple((k, n, tally[(k, n)])
                  for k, n in sorted(tally, key=lambda pair: (Fraction(*pair), pair[1])))
    return Distribution(len(kept), quantiles, exact)


@dataclass(frozen=True)
class HalfCount:
    """Item 5 for one league and half."""

    half: str
    teams: int  # teams of the calendar
    teams_without_meeting: int  # teams with no meeting in this half (no share)
    meetings_range: tuple[int, int]  # least and most meetings of a team in this half
    before: Distribution | None
    home: Distribution | None


def split_count(calendar: pd.DataFrame, *, evaluation_start: str) -> tuple[HalfCount, ...]:
    """Item 5 for one league: one ``HalfCount`` per half, every meeting counted."""
    counts = half_counts(meeting_halves(calendar), evaluation_start=evaluation_start)
    out = []
    for half in HALVES:
        rows = counts.loc[counts["half"] == half]
        met = rows.loc[rows["meetings"] > 0]
        out.append(HalfCount(
            half=half,
            teams=len(rows),
            teams_without_meeting=int((rows["meetings"] == 0).sum()),
            meetings_range=((int(rows["meetings"].min()), int(rows["meetings"].max()))
                            if len(rows) else (0, 0)),
            before=distribution(zip(met["before"], met["meetings"], strict=True)),
            home=distribution(zip(met["home"], met["meetings"], strict=True)),
        ))
    return tuple(out)


# ------------------------------------------------------------------------------- output


def table(header: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    """A plain-text table: the first column left-aligned, the others right-aligned."""
    cells = [list(map(str, header)), *([str(cell) for cell in row] for row in rows)]
    widths = [max(len(row[i]) for row in cells) for i in range(len(header))]
    lines = []
    for row in cells:
        parts = [row[0].ljust(widths[0])] + [cell.rjust(width)
                                             for cell, width in zip(row[1:], widths[1:],
                                                                    strict=True)]
        lines.append("  ".join(parts).rstrip())
    return "\n".join(lines)


def _share_text(share: Fraction | None, count: int, of: int) -> str:
    return "undefined" if share is None else f"{count}/{of} = {float(share):.4f}"


def _holds_text(holds: bool | None) -> str:
    return "undefined" if holds is None else "yes" if holds else "no"


def assumption_table(counts: Mapping[str, AssumptionCount], minimum: Fraction) -> str:
    rows = [(league, count.second_yellow_players, count.sheet_red_not_null,
             _share_text(count.share, count.sheet_red_not_null, count.second_yellow_players),
             f"{float(minimum):g}", _holds_text(count.holds), count.unattributed,
             count.not_listed, count.outside_only)
            for league, count in counts.items()]
    return table(("league", "second_yellow players", "sheet red_minute not null", "share",
                  "minimum share", "holds", "left out: player_id 0",
                  "of which not on the sheet", "left out: only outside regulation_periods"),
                 rows)


def assumption_verdict(counts: Mapping[str, AssumptionCount]) -> bool:
    """The assumption holds when it holds in every league; a league without a share fails."""
    return bool(counts) and all(count.holds is True for count in counts.values())


def residual_tables(counts: Mapping[str, ResidualCount], cards: Sequence[str]) -> str:
    forward = table(
        ("league", "dismissal-card players", "null sheet red_minute",
         *(f"of which {card}" for card in cards), "of which not on the sheet",
         "of which player_id 0", "listed under another team"),
        [(league, count.card_players, count.card_sheet_null,
          *(number for _, number in count.card_sheet_null_by_card), count.card_not_listed,
          count.card_unattributed, count.card_listed_other_team)
         for league, count in counts.items()])
    reverse = table(
        ("league", "sheet red_minute not null", "no regulation dismissal card",
         "of which a card outside regulation_periods"),
        [(league, count.sheet_red_players, count.sheet_red_no_card, count.sheet_red_card_outside)
         for league, count in counts.items()])
    return "\n".join([
        "event record to sheet: players with a regulation dismissal card and a null sheet "
        "red_minute (a player can carry both cards; 'listed under another team' counts every "
        "dismissal-card player)",
        forward,
        "",
        "sheet to event record: sheet players whose red_minute is not null and who carry no "
        "regulation dismissal card",
        reverse,
    ])


def _quantile_text(found: Distribution | None) -> list[str]:
    if found is None:
        return ["-"] * len(QUANTILES)
    return [f"{value:.4f}" for value in found.quantiles]


def _exact_text(found: Distribution | None) -> str:
    if found is None:
        return "none"
    return " ".join(f"{k}/{n}:{teams}" for k, n, teams in found.exact)


def split_tables(counts: Mapping[str, tuple[HalfCount, ...]]) -> str:
    names = ("min", "q1", "median", "q3", "max")
    summary = table(
        ("league", "half", "teams", "no meeting", "meetings/team",
         *(f"before {name}" for name in names), *(f"home {name}" for name in names)),
        [(league, half.half, half.teams, half.teams_without_meeting,
          f"{half.meetings_range[0]}-{half.meetings_range[1]}",
          *_quantile_text(half.before), *_quantile_text(half.home))
         for league, halves in counts.items() for half in halves])
    exact = [f"{league} {half.half} {kind}: {_exact_text(found)}"
             for league, halves in counts.items() for half in halves
             for kind, found in (("before", half.before), ("home", half.home))]
    return "\n".join([summary, "", "exact distributions (k/n:t = t teams with k of n "
                      "meetings in the half):", *exact])


# ------------------------------------------------------------------------------- corpus


@dataclass(frozen=True)
class LeagueFrames:
    """What the counts of one league read: the joined actions, the sheet, the calendar."""

    actions: pd.DataFrame  # ACTION_COLUMNS and the sidecar card
    squads: pd.DataFrame  # game_id, team_id, player_id and the sheet field
    calendar: pd.DataFrame  # game_id, date, home_team_id, away_team_id
    provenance: Mapping[str, object]


def load_league(league: str, chosen: Settings) -> LeagueFrames:
    """One league through the shipped loaders: ``sidecar.verify`` first, then the three
    sidecar tables, then the neutral actions, joined by ``sidecar.attach``."""
    from galactico.ingestion import sidecar
    from galactico.storage.public import load_public

    sidecar.verify(league)
    events = sidecar.load(league, "events", columns=["event_id", "card"])
    squads = sidecar.load(league, chosen.sheet_table,
                          columns=["game_id", "team_id", "player_id", chosen.sheet_field])
    matches = sidecar.load(league, "matches", columns=list(CALENDAR_COLUMNS))
    actions = load_public(league, tables=("actions",), action_columns=ACTION_COLUMNS).actions
    joined = sidecar.attach(actions, events, ["card"])
    calendar = matches.rename(columns={"date_utc": "date"})
    return LeagueFrames(joined, squads, calendar, sidecar.provenance(league))


def _provenance_lines(league: str, record: Mapping[str, object]) -> list[str]:
    hashes = record.get("content_hashes") or {}
    digests = record.get("raw_digests") or {}
    return [f"{league}: {record.get('sidecar_schema_version')} "
            f"{record.get('tag_mapping_version')}",
            *(f"  content {name} {value}" for name, value in sorted(hashes.items())),
            *(f"  raw {name} {value}" for name, value in sorted(digests.items()))]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                        help="E-10's config.json (default: the registered one)")
    args = parser.parse_args(argv)

    from galactico.validation.digests import lf_sha256

    try:
        chosen = settings(json.loads(args.config.read_text(encoding="utf-8")))
    except ConfigRefused as error:
        print(f"refused: {error}. Nothing was counted.")
        return 2

    print("E-10 structure-only counts before registration "
          "(verified_by_root_before_registration, items 3 to 5)")
    print(f"config {args.config} lf_sha256 {lf_sha256(args.config)}")
    print(f"script {Path(__file__).name} lf_sha256 {lf_sha256(Path(__file__))}")
    print(f"read from the config: leagues={','.join(chosen.leagues)} "
          f"dismissal_cards={','.join(chosen.dismissal_cards)} "
          f"regulation_periods={','.join(chosen.regulation_periods)} "
          f"sheet={chosen.sheet_table}.{chosen.sheet_field} "
          f"dismissal_assumption_minimum_share={float(chosen.minimum_share):g} "
          f"evaluation_start={chosen.evaluation_start}")
    print(NO_OUTCOME_NOTE)
    print("A player in a match is a (game_id, player_id) pair; an event counts for items 3 and "
          "4 when its period is in regulation_periods.")
    print(flush=True)

    assumption: dict[str, AssumptionCount] = {}
    residuals: dict[str, ResidualCount] = {}
    split: dict[str, tuple[HalfCount, ...]] = {}
    provenance: list[str] = []
    for league in chosen.leagues:
        frames = load_league(league, chosen)
        options = {"dismissal_cards": chosen.dismissal_cards,
                   "regulation_periods": chosen.regulation_periods,
                   "sheet_field": chosen.sheet_field}
        assumption[league] = assumption_count(frames.actions, frames.squads,
                                              minimum_share=chosen.minimum_share, **options)
        residuals[league] = residual_counts(frames.actions, frames.squads, **options)
        split[league] = split_count(frames.calendar, evaluation_start=chosen.evaluation_start)
        provenance += _provenance_lines(league, frames.provenance)
        del frames

    print("sidecar read (versions, content hashes, raw digests)")
    print("\n".join(provenance))
    print()
    print("[item 3] dismissal_check assumption: players with a regulation second_yellow event, "
          "and those whose sheet red_minute in that match is not null")
    print(assumption_table(assumption, chosen.minimum_share))
    print("parts, changing no count: 'of which player_id 0' are pairs of an event no player is "
          "credited with (raw playerId 0; the sidecar's player_attributed is false), each "
          "counted as one player, never on a sheet, so in the denominator only; 'of which not "
          "on the sheet' includes them; 'left out' are players whose second_yellow events are "
          "all outside regulation_periods. The root rules on them before registration.")
    holds = assumption_verdict(assumption)
    print(f"the assumption holds in every league: {'yes' if holds else 'no'}")
    if not holds:
        print("so dismissal_check_fallback replaces dismissal_check before registration and the "
              f"draft is audited again: {chosen.fallback}")
    print()
    print("[item 4] dismissal_check residuals")
    print(residual_tables(residuals, chosen.dismissal_cards))
    print()
    print(f"[item 5] reliability_split calendar count: per half, the distribution over teams of "
          f"the share of the half's meetings dated before {chosen.evaluation_start} (before) "
          f"and of its home meetings (home); quartiles by linear interpolation")
    print(VALIDITY_NOTE)
    print(split_tables(split))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
