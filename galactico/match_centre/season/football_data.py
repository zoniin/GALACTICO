"""football-data.org v4: fixtures, results, tables, squads and scorers (PLAN D2-A, PLATFORM 2).

One client per app. It reads the eight resources of PLAN 3.4 in bulk, never one entity where a
bulk resource covers it, and turns each reply into the season model (``model.py``) before
anything keeps it. Every read runs the same steps, in this order (PLAN D2-A):

1. ``assert_may_host("football_data_org")``: the licence gate, before anything else;
2. tier three, ``FeedCache``: single flight per resource within the process;
3. tier four, the shared store (``store.py``), where a fresh entry makes no request;
4. and 5. ``Budget.acquire``, which charges the page view's ``RequestBudget`` first and then
   the key's minute, or raises ``Deferred`` having made no request;
6. the GET, with the ``X-Auth-Token`` header on that request only;
7. ``Budget.observe`` of the reply's rate headers and status;
8. the status map (below), on the status and ``errorCode`` only;
9. the normaliser of the resource;
10. ``Snapshot(rows, checked)``;
11. the shared store's ``set``, kept at most seven days and tagged ``fd``.

**Freshness.** Each resource has a lifetime (``TTL``, PLAN 3.4); a day's depends on its state
(``day_ttl``). The lifetime is judged against the rows' own ``checked`` time, wherever they
were kept, so rows another instance stored are not held for a second full lifetime. Tier
three is asked again every ``recheck`` seconds (60); asking again costs nothing upstream while
the rows are fresh. A version (PLATFORM 2.4) is part of the resource's key: when the catalogue
sees a finish, it asks for the next version, and that is read once.

**The status map** (PLATFORM 2.5). Every error is a ``FeedError``, so stale rows are served
for any of them where the client still holds some:

- 400 or 401: ``KeyRejected``. The client makes no request for an hour and logs one line,
  which names no credential;
- 403: ``NotCovered``, and 404: ``NotFound`` (both ``Unknown``, which the routes answer 404),
  remembered for 24 hours and one hour;
- 429: ``Throttled``; the budget makes no request until the reset, plus one second;
- any other status, a timeout, a connection failure or a body that cannot be read:
  ``FeedError``;
- no request at all: ``Deferred`` (the budget), ``Disabled`` (no key when the request was due,
  the hour after a rejection, or the pytest guard).

The reply's own words are never read or repeated; each error carries one fixed line a reader
may be shown, naming no key, token, plan or quota.

**Normalisation** (B1). A model object has no field for ``playedMatches``, ``shirtNumber``,
``crest``, ``emblem``, ``flag``, ``odds``, ``filters`` or a team record's ``lastUpdated``, so none
of them survives: a squad's and a person's shirt are ``None`` (Wikipedia's squad list is the
only source of one), and a team's sources carry no revision stamp. ``score.fullTime`` is a
match's ``result`` and ``score.halfTime`` its ``half_time`` (B5). Positions ``Goalkeeper``,
``Defence``, ``Midfield`` and ``Offence`` are GK, DF, MF and FW; ``null``, the string ``"null"``
and any other value are ``None``. The referee is the name, with the nationality in brackets
where stated, of ``referees[type=REFEREE]``.

**Declared skips.** Rows of a competition the site does not cover (``competitions.by_fd_code``
gives none, as for the European Championship) and matches whose clubs are not known yet (a
knockout slot the source sends with every team field ``null``) are left out of every list;
such a match comes back once the source names its clubs. A reply missing a field a row
needs (an id, a name, a kick-off, a known status) is unreadable as a whole, never part-read.

**Order.** Lists of matches are by kick-off, then the competition's order (PR 2.1), then the
home club's name, then football-data.org's id. Competitions are in PR 2.1's order. Tables,
squads, teams and scorers keep the source's order.

**Key handling.** ``from_env()`` keeps a reader of ``FOOTBALL_DATA_KEY``, not its value, and
returns ``None`` where it is unset. The key travels only in the request's header: it is in no
cache key, row, model object, log line, exception or ``repr``. Under pytest a client without an
injected transport is off (``from_env()`` gives ``None``, and a client built directly raises
``Disabled`` without a request), so a shell with the key exported cannot reach the API from a
test.

Claim: a resource is requested at most once per lifetime per process while it answers, never
beyond the budget, and what is served says when it was read. Non-claim: the free plan carries
no line-ups, goals, bookings, minutes or match statistics, and nothing here fills them in; the
source's delay on results is not measured here.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from functools import partial
from time import monotonic
from typing import Any, Generic, TypeVar
from urllib.parse import urlencode

import httpx

from ...providers import assert_may_host
from ..feed import FeedCache, FeedError, Snapshot
from ..kickoff import from_utc, utc_text
from .budget import BLOCK_MARGIN, BLOCK_WITHOUT_RESET, Budget, Deferred, Priority
from .competitions import (
    BY_FD_CODE,
    BY_SLUG,
    COMPETITIONS,
    CompetitionConfig,
    competition,
    season_label,
    season_year,
)
from .keys import entity_key, match_key, plate
from .model import (
    STATUSES,
    Competition,
    Match,
    Named,
    Person,
    PersonRef,
    ScorerLine,
    Side,
    SourceRef,
    SquadEntry,
    StandingRow,
    Table,
    Team,
    TeamRef,
    from_json,
    to_json,
)
from .store import MAX_TTL, SharedStore, age

__all__ = [
    "FootballData", "Disabled", "KeyRejected", "Unknown", "NotCovered", "NotFound", "Throttled",
    "Deferred", "PROVIDER", "KEY_VARIABLE", "HEADER", "TTL", "DAY_TTL", "SCORERS_LIMIT",
    "TABLE_ORDER", "GROUP_OF_POSITION", "madrid_day", "day_ttl",
    "normalise_competitions", "normalise_matches", "normalise_standings", "normalise_teams",
    "normalise_scorers", "normalise_person", "normalise_person_matches",
]

log = logging.getLogger(__name__)

PROVIDER = "football_data_org"
"""This source's key in ``providers.base.PROVIDERS`` (not ``football_data``, the .co.uk files)."""
KEY_VARIABLE = "FOOTBALL_DATA_KEY"
HEADER = "X-Auth-Token"
TIMEOUT = httpx.Timeout(5.0, connect=2.0)
SCHEMA = "v2"
"""Part of every cache key: a change to a normaliser's output changes it, so rows another
deployment stored in the old shape are never read as the new one."""
STORE_TAG = "fd"

RECHECK = 60.0
"""Seconds tier three holds a resource before the client looks at its lifetime again."""
OFF_FOR = 3600.0
"""Seconds the client makes no request after the source rejected its key."""
NOT_COVERED_FOR = 86400.0
NOT_FOUND_FOR = 3600.0

MINUTE, HOUR, DAY = 60, 3600, 86400
TTL: dict[str, int] = {
    "competitions": 7 * DAY,
    "season_matches": 6 * HOUR,
    "past_season": 30 * DAY,
    "standings": 12 * HOUR,
    "teams": DAY,
    "scorers": DAY,
    "person": 7 * DAY,
    "person_matches": DAY,
}
"""Each resource's lifetime in seconds (PLAN 3.4). A season before the current one is
``past_season``."""
DAY_TTL: dict[str, int] = {"live": MINUTE, "near": 2 * MINUTE, "today": 15 * MINUTE,
                           "past": DAY, "future": 6 * HOUR}
"""A day's lifetime by its state (PLAN 3.4); ``day_ttl`` chooses."""
KICKOFF_LEAD = timedelta(minutes=30)
PLAY = timedelta(hours=2)
"""From kick-off to the final whistle, as declared: the source states no finish time."""
AFTER_FINISH = timedelta(hours=2)

SCORERS_LIMIT = 500
"""The scorers ``limit`` asked for (B2): the highest D4-B's probe found accepted (27 November
2026: 500 answered for La Liga and the Champions League, with 173 and 198 scorers, so no list
was cut). The stop line is printed where the source lists as many as were asked for."""
PERSON_COMPETITIONS = ("PD", "CL")
PERSON_MATCHES_LIMIT = 50

TABLE_ORDER = "Positions as the source publishes them."
"""The order line of the source's own table (PR 6.4, "All matches")."""

GROUP_OF_POSITION: dict[str, str] = {"Goalkeeper": "GK", "Defence": "DF", "Midfield": "MF",
                                     "Offence": "FW"}
"""football-data.org's coarse positions and the squad groups they are. Nothing else maps."""
_STATUS_ALIASES = {"EXTRA_TIME": "IN_PLAY", "PENALTY_SHOOTOUT": "IN_PLAY", "LIVE": "IN_PLAY"}
"""Statuses the v4 documentation also names, read as the model's: the match is in play."""
_LIVE = frozenset({"IN_PLAY", "PAUSED"})
_CONFIRMED = frozenset({"TIMED", "IN_PLAY", "PAUSED", "FINISHED", "SUSPENDED"})
"""Statuses whose kick-off time is a stated one: a confirmed time, or a match that began."""
_NOT_PLAYED = frozenset({"POSTPONED", "CANCELLED"})
_DURATIONS = frozenset({"REGULAR", "EXTRA_TIME", "PENALTY_SHOOTOUT"})
_WINNERS = frozenset({"HOME_TEAM", "AWAY_TEAM", "DRAW"})

# The lines a reader may be shown (``FeedCache`` serves an error's text as a stale result's
# warning). None names a key, token, plan or quota (PLATFORM 2.5).
UNAVAILABLE = "Feed unavailable."
UNREADABLE = "football-data.org sent an unreadable reply."
OFF_LINE = "football-data.org can’t be read right now."
NOT_COVERED_LINE = "This isn’t in the sources this site reads."
NOT_FOUND_LINE = "football-data.org lists no such entry."
THROTTLED_LINE = "football-data.org asked this site to wait before reading again."


# ------------------------------------------------------------------ the error taxonomy


class Disabled(FeedError):
    """No request was made: the client is off. The catalogue reads the next source."""

    def __init__(self, line: str = OFF_LINE) -> None:
        super().__init__(line)


class KeyRejected(Disabled):
    """The source answered 400 or 401: it refused the key. Off for ``OFF_FOR`` seconds."""


class Unknown(FeedError):
    """Not in the sources: an unknown entity, or a competition not covered. Answered 404."""


class NotCovered(Unknown):
    """The source answered 403, or the site covers no such competition."""

    def __init__(self) -> None:
        super().__init__(NOT_COVERED_LINE)


class NotFound(Unknown):
    """The source answered 404."""

    def __init__(self) -> None:
        super().__init__(NOT_FOUND_LINE)


class Throttled(FeedError):
    """The source answered 429. ``retry_after`` seconds pass before the next request, so
    ``FeedCache`` holds the resource that long without counting it as a failure."""

    def __init__(self, retry_after: float) -> None:
        super().__init__(THROTTLED_LINE)
        self.retry_after = retry_after


# ------------------------------------------------------------------ time


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _instant(text: object) -> datetime | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo is not None else None


def madrid_day(instant: datetime) -> date:
    """The Europe/Madrid calendar day of ``instant`` (the rule ``kickoff`` writes out)."""
    return from_utc(instant, "CET").date()


def day_ttl(rows: Sequence[Mapping[str, Any]], day: date, *, now: datetime) -> int:
    """The lifetime, in seconds, of day ``day``'s matches ``rows`` (``Match`` JSON) at ``now``.

    In this order: a minute while any of them is in play or paused; two minutes while any not
    postponed or cancelled kicks off within half an hour, or finished within two hours (its
    finish taken as two hours after kick-off, since the source states none; a match still
    shown as not started after its kick-off counts too); then by the day in Europe/Madrid:
    fifteen minutes for today, a day for a past day, six hours for a future one.
    """
    for row in rows:
        if row.get("status") in _LIVE:
            return DAY_TTL["live"]
    for row in rows:
        kickoff = _instant(row.get("kickoff_utc"))
        if kickoff is None or row.get("status") in _NOT_PLAYED:
            continue
        if now - (PLAY + AFTER_FINISH) <= kickoff <= now + KICKOFF_LEAD:
            return DAY_TTL["near"]
    today = madrid_day(now)
    if day == today:
        return DAY_TTL["today"]
    return DAY_TTL["past"] if day < today else DAY_TTL["future"]


# ------------------------------------------------------------------ reading a reply


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _count(value: object) -> int | None:
    number = _int(value)
    return number if number is not None and number >= 0 else None


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    return value or None


def _born(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return None


def _group(*values: object) -> str | None:
    """The squad group of the first value that is one of the four positions."""
    for value in values:
        group = GROUP_OF_POSITION.get(_text(value) or "")
        if group is not None:
            return group
    return None


def _need(value: Any, what: str) -> Any:
    if value is None:
        raise ValueError(f"the reply has no {what}")
    return value


def _source(checked: str, revised: object = None) -> SourceRef:
    stamp = _text(revised)
    return SourceRef(PROVIDER, checked, stamp if _instant(stamp) else None, None, None)


def _key(fd_id: int | None, *names: str | None) -> str:
    for name in names:
        if name:
            try:
                return entity_key(fd_id, name)
            except ValueError:
                continue
    if fd_id is None:
        raise ValueError("an entity with neither an id nor a name")
    return entity_key(fd_id, str(fd_id))


def _team_ref(raw: object) -> TeamRef | None:
    """A club as a match, a table row, a scorer line or a team names it; ``None`` where the
    source does not know the club yet (every field ``null``)."""
    if not isinstance(raw, Mapping):
        raise ValueError("a club that is not an object")
    fd_id, name = _int(raw.get("id")), _text(raw.get("name"))
    if fd_id is None and name is None:
        return None
    fd_id, name = _need(fd_id, "club id"), _need(name, "club name")
    short = _text(raw.get("shortName")) or name
    return TeamRef(key=_key(fd_id, short, name), fd_id=fd_id, name=name, short=short,
                   plate=plate(short, _text(raw.get("tla"))))


def _person_ref(raw: object) -> PersonRef:
    if not isinstance(raw, Mapping):
        raise ValueError("a person who is not an object")
    fd_id, name = _int(raw.get("id")), _need(_text(raw.get("name")), "person name")
    return PersonRef(key=_key(fd_id, name), name=name)


def _config(code: object) -> CompetitionConfig | None:
    return BY_FD_CODE.get(code) if isinstance(code, str) else None


def _items(body: object, field: str) -> list:
    if not isinstance(body, Mapping):
        raise ValueError("the reply is not an object")
    items = body.get(field)
    if not isinstance(items, list):
        raise ValueError(f"the reply has no {field} list")
    return items


def _season(config: CompetitionConfig, season: object, fallback: date) -> str:
    start = _text(season.get("startDate")) if isinstance(season, Mapping) else None
    try:
        return season_label(config, date.fromisoformat(start).year if start else
                            season_year(config, fallback))
    except ValueError:
        return season_label(config, season_year(config, fallback))


def _match(raw: object, checked: str, season: int | None = None) -> Match | None:
    """One listed match, or ``None`` for a declared skip (a competition the site does not
    cover, or clubs not known yet). ``season`` is the season asked for, where one was: it names
    the match's season; else the match's own ``season.startDate`` does."""
    if not isinstance(raw, Mapping):
        raise ValueError("a match that is not an object")
    competition_raw = raw.get("competition")
    config = _config(competition_raw.get("code") if isinstance(competition_raw, Mapping)
                     else None)
    if config is None:
        return None
    home, away = _team_ref(raw.get("homeTeam")), _team_ref(raw.get("awayTeam"))
    if home is None or away is None:
        return None
    fd_id = _need(_int(raw.get("id")), "match id")
    kickoff = _need(_instant(raw.get("utcDate")), "kick-off")
    status = _text(raw.get("status")) or ""
    status = _STATUS_ALIASES.get(status, status)
    if status not in STATUSES:
        raise ValueError("a match status the model does not hold")
    score = raw.get("score") if isinstance(raw.get("score"), Mapping) else {}
    referee = None
    for official in raw.get("referees") or ():
        if isinstance(official, Mapping) and official.get("type") == "REFEREE":
            name, nationality = _text(official.get("name")), _text(official.get("nationality"))
            if name:
                referee = f"{name} ({nationality})" if nationality else name
                break
    day = madrid_day(kickoff)
    updated = _text(raw.get("lastUpdated"))
    duration, winner = _text(score.get("duration")), _text(score.get("winner"))
    return Match(
        key=match_key(fd_id, home.short, away.short, day), fd_id=fd_id, legacy_keys=(),
        competition=config.slug,
        season=(season_label(config, season) if season is not None
                else _season(config, raw.get("season"), day)),
        stage=_text(raw.get("stage")), matchday=_int(raw.get("matchday")),
        group=_text(raw.get("group")), kickoff_utc=utc_text(kickoff),
        kickoff_confirmed=status in _CONFIRMED, status=status, home=home, away=away,
        result=_side(score.get("fullTime")), half_time=_side(score.get("halfTime")),
        duration=duration if duration in _DURATIONS else None,
        winner=winner if winner in _WINNERS else None, referee=referee, ground=None,
        attendance=None, report_url=None,
        source_updated=updated if _instant(updated) else None,
        sources=(_source(checked, updated),))


def _side(raw: object) -> Side:
    if not isinstance(raw, Mapping):
        return Side(None, None)
    return Side(_count(raw.get("home")), _count(raw.get("away")))


def _order(match: Match) -> tuple:
    return (match.kickoff_utc or "", BY_SLUG[match.competition].order, match.home.name,
            match.fd_id or 0)


# ------------------------------------------------------------------ the normalisers
#
# Each takes a reply body and the time it was read, and gives JSON rows of model objects
# (``to_json``), which is what tiers three and four keep. Each raises ``ValueError``,
# ``KeyError`` or ``TypeError`` for a body it cannot read; the client reports that as
# ``UNREADABLE``.


def normalise_competitions(body: object, checked: str) -> list[dict]:
    """``/competitions``: the covered competitions the source lists, in PR 2.1's order."""
    listed: dict[str, Mapping] = {}
    for raw in _items(body, "competitions"):
        if isinstance(raw, Mapping) and _config(raw.get("code")) is not None:
            listed[raw["code"]] = raw
    rows = []
    for config in COMPETITIONS:
        raw = listed.get(config.fd_code or "")
        if raw is None:
            continue
        season = raw.get("currentSeason")
        season = season if isinstance(season, Mapping) else {}
        start = _text(season.get("startDate"))
        year = date.fromisoformat(_need(start, "season start")).year
        rows.append(to_json(competition(
            config, year, current_matchday=_count(season.get("currentMatchday")))))
    return rows


def normalise_matches(body: object, checked: str, *, day: date | None = None,
                      season: int | None = None) -> list[dict]:
    """``/matches`` and ``/competitions/{c}/matches``: every covered match, in the declared
    order; only those on Europe/Madrid day ``day`` where one is given. ``season`` is the
    season a season request asked for."""
    found = [m for m in (_match(raw, checked, season) for raw in _items(body, "matches"))
             if m is not None]
    if day is not None:
        found = [m for m in found if madrid_day(_instant(m.kickoff_utc)) == day]
    return [to_json(m) for m in sorted(found, key=_order)]


def _table_group(standing: Mapping[str, Any]) -> str | None:
    """The group a group stage's table is of, as the page names it: the source's ``GROUP_A``
    is "Group A", any other name as written. ``None`` for a table of any other stage: the
    source writes "Matchday" or "League phase" in the same field for a league or a league
    phase (27 November 2026), which names no group."""
    text = _text(standing.get("group"))
    if text is None or _text(standing.get("stage")) != "GROUP_STAGE":
        return None
    head, _, letter = text.replace(" ", "_").partition("_")
    if head.upper() == "GROUP" and 1 <= len(letter) <= 2 and letter.isalnum():
        return f"Group {letter.upper()}"
    return text


def normalise_standings(body: object, checked: str, *, config: CompetitionConfig) -> list[dict]:
    """``/competitions/{c}/standings``: one ``Table`` per TOTAL table the source lists (one for
    a league or a league phase, one per group of a group stage, each with its ``group``), in
    the source's order. A position two rows share is marked ``shared``; the source's ``form``
    is not read (form is derived from results, D3-B)."""
    tables = []
    for standing in _items(body, "standings"):
        if not isinstance(standing, Mapping) or standing.get("type") != "TOTAL":
            continue
        rows = []
        for raw in _items(standing, "table"):
            team = _need(_team_ref(raw.get("team")), "table club")
            numbers = {name: _need(_int(raw.get(field)), field) for name, field in (
                ("position", "position"), ("played", "playedGames"), ("won", "won"),
                ("drawn", "draw"), ("lost", "lost"), ("goals_for", "goalsFor"),
                ("goals_against", "goalsAgainst"), ("goal_difference", "goalDifference"),
                ("points", "points"))}
            rows.append((team, numbers))
        positions = [numbers["position"] for _, numbers in rows]
        tables.append(to_json(Table(
            competition=config.slug, view="all", after=None,
            rows=tuple(StandingRow(team=team, shared=positions.count(numbers["position"]) > 1,
                                   form=(), **numbers) for team, numbers in rows),
            order=TABLE_ORDER, derived=False, sources=(_source(checked),),
            group=_table_group(standing))))
    return tables


def normalise_teams(body: object, checked: str) -> list[dict]:
    """``/competitions/{c}/teams``: each club with its squad, in the source's order. A club
    listed without a ``squad`` list has an empty squad (PLAN 1.3: squads are verified for La
    Liga only; D4-B probes the rest)."""
    teams = []
    for raw in _items(body, "teams"):
        if not isinstance(raw, Mapping):
            raise ValueError("a club that is not an object")
        ref = _need(_team_ref(raw), "club")
        coach = raw.get("coach")
        coach_ref = (_person_ref(coach) if isinstance(coach, Mapping)
                     and _text(coach.get("name")) else None)
        running = {c.get("code") for c in raw.get("runningCompetitions") or ()
                   if isinstance(c, Mapping)}
        squad = []
        for member in raw.get("squad") or ():
            if not isinstance(member, Mapping):
                raise ValueError("a squad member who is not an object")
            squad.append(SquadEntry(person=_person_ref(member), group=_group(
                member.get("position")), shirt=None, born=_born(member.get("dateOfBirth")),
                nationality=_text(member.get("nationality"))))
        area = raw.get("area") if isinstance(raw.get("area"), Mapping) else {}
        teams.append(to_json(Team(
            ref=ref, area=_text(area.get("name")), founded=_int(raw.get("founded")),
            ground=_text(raw.get("venue")), coach=coach_ref,
            competitions=tuple(c.slug for c in COMPETITIONS if c.fd_code in running),
            squad=tuple(squad), sources=(_source(checked),))))
    return teams


def normalise_scorers(body: object, checked: str, *, config: CompetitionConfig,
                      limit: int) -> list[dict]:
    """``/competitions/{c}/scorers``: the lines in the source's order. ``listed`` is the
    reply's ``count``; ``cut`` says the list reached the limit asked for (or the one the reply
    states, if lower), so a player with fewer goals may be missing (B2). ``assists`` and
    ``penalties`` the source leaves ``null`` stay ``None``."""
    lines = _items(body, "scorers")
    listed = _count(body.get("count"))
    listed = len(lines) if listed is None else listed
    stated = body.get("filters", {}).get("limit") if isinstance(body.get("filters"),
                                                                Mapping) else None
    limits = [limit] + ([stated] if _count(stated) else [])
    rows = []
    for raw in lines:
        if not isinstance(raw, Mapping):
            raise ValueError("a scorer line that is not an object")
        rows.append(to_json(ScorerLine(
            person=_person_ref(raw.get("player")),
            team=_need(_team_ref(raw.get("team")), "scorer's club"),
            competition=config.slug, goals=_need(_count(raw.get("goals")), "goals"),
            assists=_count(raw.get("assists")), penalties=_count(raw.get("penalties")),
            listed=listed, cut=listed >= min(limits))))
    return rows


def normalise_person(body: object, checked: str) -> list[dict]:
    """``/persons/{id}``: one row. The group is the coarse ``section``, else ``position``."""
    if not isinstance(body, Mapping):
        raise ValueError("the reply is not an object")
    ref = _person_ref(body)
    return [to_json(Person(
        ref=ref, fd_id=_need(_int(body.get("id")), "person id"), wp_title=None, qid=None,
        born=_born(body.get("dateOfBirth")), nationality=_text(body.get("nationality")),
        group=_group(body.get("section"), body.get("position")), positions=(), shirt=None,
        height_cm=None, birthplace=None,
        sources=(_source(checked, body.get("lastUpdated")),)))]


def normalise_person_matches(body: object, checked: str) -> list[dict]:
    """``/persons/{id}/matches``: one ``Named`` per covered match the person was named for,
    by kick-off."""
    if not isinstance(body, Mapping):
        raise ValueError("the reply is not an object")
    person = _person_ref(body.get("person"))
    found = [m for m in (_match(raw, checked) for raw in _items(body, "matches"))
             if m is not None]
    return [to_json(Named(person=person, match=m.key,
                          sources=(_source(checked, m.source_updated),)))
            for m in sorted(found, key=_order)]


# ------------------------------------------------------------------ small bounded maps

K = TypeVar("K")
V = TypeVar("V")


class _Bounded(Generic[K, V]):
    """A dict that forgets its least recently used entry past ``limit``."""

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._items: OrderedDict[K, V] = OrderedDict()

    def __len__(self) -> int:
        return len(self._items)

    def get(self, key: K) -> V | None:
        value = self._items.get(key)
        if value is not None:
            self._items.move_to_end(key)
        return value

    def put(self, key: K, value: V) -> None:
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self._limit:
            self._items.popitem(last=False)

    def pop(self, key: K) -> None:
        self._items.pop(key, None)


T = TypeVar("T")
Lifetime = Callable[[list], float]


# ------------------------------------------------------------------ the client


class FootballData:
    """football-data.org v4 through the shared request budget and the two server cache tiers.

    ``key`` is the key, or a function that reads it when a request is due (``from_env``'s).
    ``transport`` is for tests (``httpx.MockTransport``). ``clock`` is monotonic and times the
    budget, the hour off and the remembered 403s and 404s; ``now`` is the wall clock that
    stamps ``checked`` and judges lifetimes. ``recheck`` is how long tier three holds a
    resource before its lifetime is looked at again.
    """

    BASE = "https://api.football-data.org/v4"

    def __init__(self, key: str | Callable[[], str | None], *,
                 transport: httpx.AsyncBaseTransport | None = None,
                 budget: Budget | None = None, store: SharedStore | None = None,
                 clock: Callable[[], float] = monotonic,
                 now: Callable[[], datetime] = _utc_now, recheck: float = RECHECK) -> None:
        self._read_key: Callable[[], str | None] = key if callable(key) else (lambda: key)
        self._transport = transport
        self._guarded = transport is None and bool(os.environ.get("PYTEST_CURRENT_TEST"))
        self._clock = clock
        self._now = now
        self.recheck = recheck
        self.cache = FeedCache(256, max_retry=300)
        self.budget = budget if budget is not None else Budget(per_minute=10, reserve=2,
                                                               clock=clock)
        self.store = store if store is not None else SharedStore.from_environment()
        self._client: httpx.AsyncClient | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None
        self._off_until = -1.0
        self._memo: _Bounded[str, Snapshot] = _Bounded(256)
        self._failures: _Bounded[str, FeedError] = _Bounded(256)
        self._absent: _Bounded[str, tuple[float, Unknown]] = _Bounded(256)
        self._built: _Bounded[str, tuple[list, list]] = _Bounded(64)

    def __repr__(self) -> str:
        return f"<FootballData {self.BASE} {'on' if self.enabled else 'off'}>"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None,
                 **options: Any) -> FootballData | None:
        """A client that reads ``FOOTBALL_DATA_KEY`` when each request is due; ``None`` where
        it is unset or blank, and under pytest unless ``transport`` is given."""
        env = os.environ if environ is None else environ
        if env.get("PYTEST_CURRENT_TEST") and options.get("transport") is None:
            return None
        if not (env.get(KEY_VARIABLE) or "").strip():
            return None
        return cls(lambda: (env.get(KEY_VARIABLE) or "").strip() or None, **options)

    @property
    def enabled(self) -> bool:
        """Whether the client would make a request now (key permitting)."""
        return not self._guarded and self._off_until <= self._clock()

    # -- the one shared HTTP client

    def _http(self) -> httpx.AsyncClient:
        loop = asyncio.get_running_loop()
        if self._client is None or self._client_loop is not loop:
            # A client's connections belong to the loop that opened them.
            self._client = httpx.AsyncClient(base_url=self.BASE, transport=self._transport,
                                             timeout=TIMEOUT, follow_redirects=False)
            self._client_loop = loop
        return self._client

    async def aclose(self) -> None:
        """Close the HTTP client (the app's lifespan calls this)."""
        client, self._client, self._client_loop = self._client, None, None
        if client is not None:
            await client.aclose()

    async def __aenter__(self) -> FootballData:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # -- the read every resource goes through

    @staticmethod
    def key_for(path: str, params: Mapping[str, object], version: int | None = None) -> str:
        """The resource's cache key in tiers three and four: path, sorted query, version."""
        query = urlencode(sorted((name, str(value)) for name, value in params.items()))
        return f"fd:{SCHEMA}:{path}?{query}" + ("" if version is None else f"@{version}")

    async def resource(self, path: str, params: Mapping[str, object], *,
                       ttl: float | Lifetime, priority: Priority,
                       normalise: Callable[[Any, str], list],
                       version: int | None = None) -> Snapshot:
        """The normalised rows of ``path`` with ``params``: from tier three, tier four or one
        request, in that order (the module's steps 1 to 11).

        ``ttl`` is the lifetime in seconds, or a function of the rows that gives it.
        Raises a ``FeedError`` subclass of the status map where nothing is held; where rows
        are held, an error that is not ``Disabled`` or ``Unknown`` returns them with the
        error's line as ``warning`` and their own ``checked``.
        """
        assert_may_host(PROVIDER)
        key = self.key_for(path, params, version)
        self._refuse(key)
        lifetime: Lifetime = ttl if callable(ttl) else (lambda rows, s=float(ttl): s)

        async def fetch() -> Snapshot:
            return await self._fetch(key, path, params, lifetime, priority, normalise)

        snap: Snapshot | None = None
        line = UNAVAILABLE
        try:
            snap = await self.cache.get(key, self.recheck, fetch)
        except FeedError as plain:
            line = str(plain)
        self._refuse(key)
        # FeedCache passes on only an error's text; the fetch kept the error itself, and it
        # is raised here, outside any handler, so it carries no chained error.
        failure = self._failures.get(key) if snap is None or snap.warning else None
        final = isinstance(failure, (Disabled, Unknown))
        if snap is not None and not final:
            return snap
        error = _clone(failure) if failure is not None else FeedError(line)
        held = None if final else await self._last_known(key)
        if held is not None:
            return replace(held, warning=str(error))
        raise error

    def _refuse(self, key: str) -> None:
        """Raise, making no request, while the client is off or the resource is known absent."""
        if self._guarded:
            raise Disabled()
        if self._off_until > self._clock():
            raise KeyRejected()
        absent = self._absent.get(key)
        if absent is not None:
            until, error = absent
            if until > self._clock():
                raise _clone(error)
            self._absent.pop(key)

    def _fresh(self, snap: Snapshot, lifetime: Lifetime) -> bool:
        try:
            return age(snap, now=self._now()) < lifetime(snap.rows)
        except (AttributeError, KeyError, TypeError, ValueError):
            return False

    async def _last_known(self, key: str) -> Snapshot | None:
        """The latest rows held for ``key`` at any age: this process's, else tier four's."""
        held = [snap for snap in (self._memo.get(key), await self.store.get(key)) if snap]
        if not held:
            return None
        return max(held, key=lambda snap: (_instant(snap.checked) or datetime.min.replace(
            tzinfo=UTC)))

    async def _fetch(self, key: str, path: str, params: Mapping[str, object],
                     lifetime: Lifetime, priority: Priority,
                     normalise: Callable[[Any, str], list]) -> Snapshot:
        known = self._memo.get(key)
        if known is not None and self._fresh(known, lifetime):
            self._failures.pop(key)
            return known
        shared = await self.store.get(key)
        if shared is not None and self._fresh(shared, lifetime):
            self._failures.pop(key)
            self._memo.put(key, shared)
            return shared
        try:
            snap = await self._request(path, params, priority, normalise)
        except FeedError as error:
            # Kept without its traceback, so no frame of the request stays reachable.
            kept = _clone(error)
            self._failures.put(key, kept)
            if isinstance(kept, Unknown):
                hold = NOT_COVERED_FOR if isinstance(kept, NotCovered) else NOT_FOUND_FOR
                self._absent.put(key, (self._clock() + hold, kept))
            raise
        self._failures.pop(key)
        self._memo.put(key, snap)
        await self.store.set(key, snap, ttl=MAX_TTL, tags=(STORE_TAG,))
        return snap

    async def _request(self, path: str, params: Mapping[str, object], priority: Priority,
                       normalise: Callable[[Any, str], list]) -> Snapshot:
        if not self._read_key():
            raise Disabled()
        await self.budget.acquire(priority)
        reply = await self._get(path, params)
        if reply is None:
            raise FeedError(UNAVAILABLE)
        status, headers, content = reply
        self.budget.observe(headers, status)
        body = self._mapped(status, headers, content)
        checked = self._now().astimezone(UTC).isoformat()
        rows = _normalised(normalise, body, checked)
        if rows is None:
            raise FeedError(UNREADABLE)
        return Snapshot(rows, checked)

    async def _get(self, path: str, params: Mapping[str, object]
                   ) -> tuple[int, httpx.Headers, bytes] | None:
        """The reply's status, headers and body, or ``None`` for a timeout or a connection
        failure. The key is read into the request's header and kept nowhere else: the
        request (which carries it) is not returned, and no error from here is chained."""
        try:
            reply = await self._http().get(
                path, params={name: str(value) for name, value in params.items()},
                headers={HEADER: self._read_key() or ""})
            return reply.status_code, reply.headers, reply.content
        except httpx.HTTPError:
            return None

    def _mapped(self, status: int, headers: httpx.Headers, content: bytes) -> Any:
        """The body of a reply that carries data; else the status map's error."""
        body = _json(content)
        code = status
        if status < 400 and isinstance(body, Mapping):
            stated = _int(body.get("errorCode"))
            if stated is not None and stated >= 400:
                code = stated
        if 200 <= code < 300:
            if body is None:
                raise FeedError(UNREADABLE)
            return body
        if code in (400, 401):
            self._reject(code)
            raise KeyRejected()
        if code == 403:
            raise NotCovered()
        if code == 404:
            raise NotFound()
        if code == 429:
            if status != 429:
                self.budget.observe(headers, 429)
            reset = _seconds(headers.get("x-requestcounter-reset"))
            wait = float(reset) if reset is not None else BLOCK_WITHOUT_RESET
            raise Throttled(retry_after=wait + BLOCK_MARGIN)
        raise FeedError(UNAVAILABLE)

    def _reject(self, status: int) -> None:
        now = self._clock()
        was_on = self._off_until <= now
        self._off_until = now + OFF_FOR
        if was_on:
            log.warning("football-data.org refused this client's credential (HTTP %d); no "
                        "request is made for the next hour.", status)

    # -- model objects from rows

    def _objects(self, key: str, snap: Snapshot, hint: type[T]) -> list[T]:
        built = self._built.get(key)
        if built is not None and built[0] is snap.rows:
            return list(built[1])
        objects = _rebuilt(hint, snap.rows)
        if objects is None:
            raise FeedError(UNREADABLE)
        self._built.put(key, (snap.rows, objects))
        return list(objects)

    async def _read(self, hint: type[T], path: str, params: Mapping[str, object], *,
                    ttl: float | Lifetime, priority: Priority,
                    normalise: Callable[[Any, str], list], version: int | None = None
                    ) -> list[T]:
        snap = await self.resource(path, params, ttl=ttl, priority=priority,
                                   normalise=normalise, version=version)
        return self._objects(self.key_for(path, params, version), snap, hint)

    def _today(self) -> date:
        return madrid_day(self._now())

    @staticmethod
    def _covered(code: str) -> CompetitionConfig:
        config = _config(code)
        if config is None:
            raise NotCovered()
        return config

    def _season(self, config: CompetitionConfig, season: int | None) -> int:
        return season_year(config, self._today()) if season is None else int(season)

    # -- the eight resources (PLAN 3.4)

    async def competitions(self, *, priority: Priority = 1) -> list[Competition]:
        """The covered competitions the source lists, in PR 2.1's order."""
        return await self._read(Competition, "/competitions", {}, ttl=TTL["competitions"],
                                priority=priority, normalise=normalise_competitions)

    async def day(self, day: date, *, priority: Priority | None = None) -> list[Match]:
        """The matches of Europe/Madrid day ``day``, from one request for the day before to the
        day after (B3). Its lifetime follows its state (``day_ttl``); it is read at priority
        0 while the rows held show a match in play, else 1."""
        params = {"dateFrom": (day - timedelta(days=1)).isoformat(),
                  "dateTo": (day + timedelta(days=1)).isoformat()}
        if priority is None:
            known = self._memo.get(self.key_for("/matches", params))
            live = known is not None and any(isinstance(row, Mapping) and row.get("status")
                                             in _LIVE for row in known.rows)
            priority = 0 if live else 1
        return await self._read(
            Match, "/matches", params, priority=priority,
            ttl=lambda rows: day_ttl(rows, day, now=self._now()),
            normalise=partial(normalise_matches, day=day))

    async def season_matches(self, code: str, season: int | None = None, *,
                             version: int | None = None,
                             priority: Priority = 1) -> list[Match]:
        """Every covered match of competition ``code``'s season (the current one by default;
        a season is named by its first year). An earlier season lives 30 days."""
        config = self._covered(code)
        year = self._season(config, season)
        past = year < season_year(config, self._today())
        return await self._read(
            Match, f"/competitions/{code}/matches", {"season": year}, priority=priority,
            ttl=TTL["past_season" if past else "season_matches"],
            normalise=partial(normalise_matches, season=year), version=version)

    async def standings(self, code: str, *, version: int | None = None,
                        priority: Priority = 1) -> list[Table]:
        """The source's current tables of competition ``code`` (``normalise_standings``)."""
        config = self._covered(code)
        return await self._read(
            Table, f"/competitions/{code}/standings", {}, ttl=TTL["standings"],
            priority=priority, normalise=partial(normalise_standings, config=config),
            version=version)

    async def teams(self, code: str, season: int | None = None, *,
                    priority: Priority = 1) -> list[Team]:
        """The clubs of competition ``code``'s season with their squads."""
        config = self._covered(code)
        return await self._read(
            Team, f"/competitions/{code}/teams", {"season": self._season(config, season)},
            ttl=TTL["teams"], priority=priority, normalise=normalise_teams)

    async def scorers(self, code: str, season: int | None = None, *,
                      limit: int = SCORERS_LIMIT, version: int | None = None,
                      priority: Priority = 1) -> list[ScorerLine]:
        """Competition ``code``'s scorers, at most ``limit`` (B2); the current season unless
        ``season`` is given."""
        config = self._covered(code)
        params: dict[str, object] = {"limit": int(limit)}
        if season is not None:
            params["season"] = int(season)
        return await self._read(
            ScorerLine, f"/competitions/{code}/scorers", params, ttl=TTL["scorers"],
            priority=priority, version=version,
            normalise=partial(normalise_scorers, config=config, limit=int(limit)))

    async def person(self, person_id: int, *, priority: Priority = 1) -> Person:
        """One person. Read only where a squad lacks a field (PLAN 3.4)."""
        found = await self._read(Person, f"/persons/{_whole_id(person_id)}", {},
                                 ttl=TTL["person"], priority=priority,
                                 normalise=normalise_person)
        if len(found) != 1:
            raise FeedError(UNREADABLE)
        return found[0]

    async def person_matches(self, person_id: int, *,
                             competitions: Sequence[str] = PERSON_COMPETITIONS,
                             limit: int = PERSON_MATCHES_LIMIT, version: int | None = None,
                             priority: Priority = 2) -> list[Named]:
        """The covered matches a person was named for (named, started or on the bench: the
        source does not say which; DC 1.2), by kick-off. Warmed at priority 2."""
        for code in competitions:
            self._covered(code)
        params = {"limit": int(limit), "competitions": ",".join(competitions)}
        return await self._read(
            Named, f"/persons/{_whole_id(person_id)}/matches", params, ttl=TTL["person_matches"],
            priority=priority, normalise=normalise_person_matches, version=version)


def _whole_id(value: object) -> int:
    number = _int(value)
    if number is None or number < 0:
        raise NotFound()
    return number


def _seconds(text: object) -> int | None:
    try:
        value = int(str(text).strip())
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _json(content: bytes) -> Any:
    try:
        return json.loads(content)
    except (UnicodeDecodeError, ValueError):
        return None


def _normalised(normalise: Callable[[Any, str], list], body: Any, checked: str) -> list | None:
    """``normalise``'s rows, or ``None`` for a body it cannot read (no error is chained, so
    nothing of the reply travels with the client's own error)."""
    try:
        return normalise(body, checked)
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def _rebuilt(hint: type[T], rows: list) -> list[T] | None:
    try:
        return [from_json(hint, row) for row in rows]
    except (TypeError, ValueError):
        return None


E = TypeVar("E", bound=BaseException)


def _clone(error: E) -> E:
    """``error`` again, with its text and attributes and without its traceback or chain:
    raised once per reader, and kept without the frames it passed through."""
    clone = type(error).__new__(type(error))
    clone.args = error.args
    clone.__dict__.update(vars(error))
    return clone
