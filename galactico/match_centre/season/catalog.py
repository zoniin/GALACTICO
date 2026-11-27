"""The catalogue: the one API every season page and the lineup builder read (PLAN 3.3).

A view never calls a source. It asks the catalogue, which reads the sources through their
clients (tiers three and four, the request budget, the licence gate), joins them by the
crosswalk's declared rules and answers with a ``View``: the value, the sources it used
(``credits``), how fresh it is, its coverage lines and what the sources do not carry.

**The source chain (PLAN 3.5).** Each call takes the first source in its chain that can
answer. football-data.org (FD) comes first wherever it carries the competition; where the app
has no key, or FD refused the key (``Disabled``), the call reads the next source:

=====================  ==========================================  ==========================
Resource               Chain                                       With no key
=====================  ==========================================  ==========================
day, season matches    FD; then OpenFootball and OpenLigaDB        the six free competitions
tables                 FD standings; then derived from results     derived, its order printed
scorers                FD; then OpenLigaDB's goals (CL, BL1)       OpenLigaDB only
squads                 FD for every club; Wikipedia for Madrid     Madrid only
persons                FD; then Wikipedia for Madrid               Madrid only; others 404
goals                  OpenLigaDB (CL, BL1); Wikipedia (Madrid)    the same
Madrid's deep facts    Wikipedia and Wikidata; FD for named lists  no named lists
=====================  ==========================================  ==========================

The Copa del Rey and the Supercopa come from Real Madrid's season article only (their ties).
A competition gated by a root decision (``CompetitionConfig.gate``, and the Europa League
until P5-B) is not listed and answers ``Unknown`` until the catalogue is built with that gate
passed. A competition FD does not reach (403) falls back to the free feeds where they carry
it, and is ``Unknown`` otherwise.

**Mixing rows (PLATFORM 4.2).** Rows of two sources are combined only by a declared rule:

- *the today overlay*: a season list holds, for each match the today resource also lists
  (by football-data.org id), the row with the later ``source_updated``; on a tie, or where
  neither states one, the today row, which was read no earlier;
- *the Madrid fill*: a Real Madrid match football-data.org lists takes the ground, attendance
  and report link its Wikipedia box states (football-data.org's free plan has none), and
  the referee only where football-data.org names none;
- *the Madrid squad*: Wikipedia's squad list in its declared order, each player joined to
  football-data.org's squad by date of birth and folded surname (``crosswalk.join_people``;
  Wikipedia's date of birth is his infobox's), then football-data.org's players the list
  does not hold (``crosswalk.unlisted``: no one listed has their name, or their date of
  birth and surname), in its order. A joined player keeps football-data.org's key, date of birth
  and nationality, and the list's name, shirt number and group (ADR-0035 D3).

**Budgets (PLAN 3.6).** No call makes more football-data.org requests cold than its view's
cap: the day view one (the day resource), a match one (its day's resource), a head-to-head at
most one, a team two, a player two, the search none. A resource a call does not need cold is
read only where held (``_peek``, which makes no request), and the view is marked partial
where it is not held.

**Versions (PLATFORM 2.4).** A finish the day resource shows for today moves that
competition's version (``version``); the season matches and scorers are read under it, and
the standings once the finish is ten minutes old (``STANDINGS_DEBOUNCE``), so each finish is
read once.

Claim: every value is what a source stated, a rule above, or a derivation ``derive.py`` makes
and a test recomputes; ``credits`` are the sources the value used. Non-claim: the catalogue
does not judge one source against another beyond these rules.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal, TypeVar

from ..feed import FeedError
from ..freshness import day_label
from ..names import NameBook
from ..openfootball import NoSeason, OpenFootball, season_start
from ..openligadb import OpenLigaDB
from ..studio import Studio
from . import adapters, crosswalk, derive
from . import goals as goal_rules
from .budget import DEFERRED_LINE, Deferred, RequestBudget
from .competitions import BY_SLUG, COMPETITIONS, CompetitionConfig, season_year
from .competitions import competition as competition_object
from .football_data import Disabled, FootballData, NotCovered, Unknown, madrid_day
from .infobox import Infobox, Infoboxes
from .keys import MADRID_FD_ID, MADRID_KEY, Key, legacy, parse, slugify
from .model import (
    Appearance,
    Competition,
    Coverage,
    Freshness,
    GoalEvent,
    Match,
    Named,
    Person,
    PersonRef,
    ScorerLine,
    SourceRef,
    SquadEntry,
    Table,
    Team,
    TeamRef,
    View,
)
from .revisions import Grid, Mismatch, Revisions, fixture, reconcile
from .wiki_season import MADRID_REF, MadridSeason, MadridSeasonFacts
from .wikidata import Wikidata, WikidataPerson

__all__ = [
    "Catalog", "Unknown", "NotListed", "MadridFacts", "Entry", "CREDIT_ORDER",
    "DAY_ORDER", "SCHEDULE_ORDER", "SCORERS_ORDER", "SQUAD_ORDER", "SEARCH_ORDER",
    "CATALOG_GATES", "STANDINGS_DEBOUNCE", "H2H_PAST_SEASONS", "H2H_OPENFOOTBALL_SINCE",
    "LINES", "listed_line", "cut_line",
]

T = TypeVar("T")

CREDIT_ORDER: tuple[str, ...] = ("football_data_org", "wikipedia", "wikidata",
                                 "openfootball", "openligadb")
"""The order credits are listed in. A credit is listed only where the value used it."""

DAY_ORDER = "By competition in the fixed order, then kick-off, then home club."
SCHEDULE_ORDER = "By kick-off, then competition in the fixed order, then home club."
SCORERS_ORDER = "By goals, then name."
SQUAD_ORDER = ("Wikipedia’s squad list in its order (by position, then shirt number), then "
               "football-data.org’s players it doesn’t list, in that source’s order.")
SEARCH_ORDER = ("Competitions in the fixed order; then clubs, then players, Real Madrid’s "
                "first, each by name.")

CATALOG_GATES: dict[str, str] = {"europa-league": "P5-B"}
"""Competitions this build lists only once a later wave passes its gate (PR 2.1 row 9)."""

STANDINGS_DEBOUNCE = timedelta(minutes=10)
H2H_PAST_SEASONS: tuple[int, ...] = (2025, 2024, 2023)
"""The earlier seasons football-data.org's free plan answers (newest first)."""
H2H_OPENFOOTBALL_SINCE = 2010
"""The first season OpenFootball's files are read from for meetings before 2023/24."""

_FD = "football_data_org"
_TABLE_STAGES = frozenset({"REGULAR_SEASON", "LEAGUE_STAGE"})
_SLUG_DAY = re.compile(
    r"^(?P<home>[a-z0-9-]+?)-v-(?P<away>[a-z0-9-]+)-(?P<day>\d{4}-\d{2}-\d{2})$")

# The lines a reader may be shown. None names a key, token, plan or quota.
NO_SQUADS = "Squads come from a source this site can’t reach right now."
NO_SCORERS = "The free sources this site reads don’t list this competition’s scorers."
NO_NAMED = ("Matchday squads come from football-data.org, which this site can’t read right "
            "now.")
NOT_JOINED = ("football-data.org’s record of this player couldn’t be joined to Wikipedia’s, "
              "so its facts are left out.")
NO_APPEARANCES = "Appearances by match aren’t read here."
GROUP_TABLES = "This competition has more than one table; the first is shown."
WIKI_DOWN = "Wikipedia can’t be read right now, so Real Madrid’s cup ties are left out."
WIKI_STALE = "Wikipedia: the last version read is shown."
FD_DOWN = "football-data.org can’t be read right now."
OL_DOWN = "OpenLigaDB can’t be read right now."
REVISIONS_DOWN = "Wikipedia’s revision history can’t be read right now."
SEARCH_PARTIAL = "The search holds the clubs and players of the competitions read so far."
NOT_LISTED = "The sources this site reads list no such entry."

LINES: tuple[str, ...] = (
    DAY_ORDER, SCHEDULE_ORDER, SCORERS_ORDER, SQUAD_ORDER, SEARCH_ORDER, NO_SQUADS,
    NO_SCORERS, NO_NAMED, NOT_JOINED, NO_APPEARANCES, GROUP_TABLES, WIKI_DOWN, WIKI_STALE,
    FD_DOWN, OL_DOWN, REVISIONS_DOWN, SEARCH_PARTIAL, NOT_LISTED,
)
"""Every fixed sentence the catalogue serves, for the copy-guard test."""


class NotListed(Unknown):
    """No source the catalogue reads lists the key asked for: answered 404."""

    def __init__(self) -> None:
        super().__init__(NOT_LISTED)


def listed_line(count: int) -> str:
    """B2: how many players a scorers list holds."""
    return (f"The source lists {count} {'player' if count == 1 else 'players'} with at least "
            "one goal.")


def cut_line(count: int) -> str:
    """B2: the line added where the list reached its limit."""
    return (f"The source’s list stops at {count} players, so a player with fewer goals may be "
            "missing.")


# ------------------------------------------------------------------ what some calls return


@dataclass(frozen=True)
class MadridFacts:
    """``Catalog.madrid``'s value: Real Madrid's season as the free sources state it."""

    article: MadridSeasonFacts
    """The season article's facts; a match the crosswalk joins to a schedule held carries
    the catalogue's key, and so do its goals."""
    squad: tuple[SquadEntry, ...]
    """The joined squad, ``SQUAD_ORDER``."""
    people: tuple[Person, ...]
    """The same players, as people."""
    appearances: tuple[Appearance, ...]
    """REC 1.3, as the revision reader orders them; empty without it."""
    grid: Grid | None
    mismatches: tuple[Mismatch, ...]


@dataclass(frozen=True)
class Entry:
    """One search entry: a competition, a club or a player the held sources list."""

    kind: Literal["competition", "club", "player"]
    key: str
    name: str
    context: str | None      # a competition's area, a club's competition, a player's club
    madrid: bool


# ------------------------------------------------------------------ the trace of one call


@dataclass
class _Trace:
    today: date
    used: dict[str, None] = field(default_factory=dict)
    checked: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    coverage: list[Coverage] = field(default_factory=list)
    partial: bool = False

    def read(self, refs: Iterable[SourceRef]) -> None:
        for ref in refs:
            self.credit(ref.provider, ref.checked)

    def credit(self, provider: str, checked: str) -> None:
        self.used.setdefault(provider, None)
        self.checked.append(checked)

    def line(self, text: str | None) -> None:
        if text and text not in self.lines:
            self.lines.append(text)

    def lack(self, text: str) -> None:
        if text not in self.missing:
            self.missing.append(text)


def _when(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo is not None else None


def _match_day(match: Match) -> str:
    """A match's Europe/Madrid day: from its kick-off, else the day its key ends with."""
    instant = _when(match.kickoff_utc)
    return madrid_day(instant).isoformat() if instant else match.key[-10:]


def _day_order(match: Match) -> tuple:
    return (BY_SLUG[match.competition].order, match.kickoff_utc or _match_day(match) + "T99",
            match.home.name, match.key)


def _schedule_order(match: Match) -> tuple:
    return (match.kickoff_utc or _match_day(match) + "T99", BY_SLUG[match.competition].order,
            match.home.name, match.key)


def _plays(team: TeamRef, match: Match) -> bool:
    return crosswalk.same_club(team, match.home) or crosswalk.same_club(team, match.away)


def _goals_in(match: Match) -> int:
    return (match.result.home or 0) + (match.result.away or 0)


# ------------------------------------------------------------------ the catalogue


class Catalog:
    """The season data layer's one reader. ``football`` is ``None`` without a key.

    ``openligadb`` defaults to ``openfootball.ligadb``, so OpenLigaDB is read once for the
    board's rows and the goal reports. ``infoboxes``, ``wikidata`` and ``revisions`` are
    optional: without the infoboxes a Madrid player has no Wikipedia birth date (so no join to
    football-data.org) and no listed positions; without Wikidata no height or place of birth;
    without the revision reader no appearances by match. ``studio`` is accepted for the
    wiring PLAN 3.3 names and is not read (the season article holds the same squad list).
    ``gates`` names the root decisions passed ("P-D9", "P5-B"). ``clock`` gives the time.
    """

    def __init__(self, *, football: FootballData | None, openfootball: OpenFootball,
                 openligadb: OpenLigaDB | None = None, studio: Studio | None = None,
                 madrid: MadridSeason, wikidata: Wikidata | None = None,
                 infoboxes: Infoboxes | None = None, revisions: Revisions | None = None,
                 gates: Iterable[str] = (),
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.football = football
        self.openfootball = openfootball
        self.openligadb = openligadb if openligadb is not None else openfootball.ligadb
        self.studio = studio
        self.madrid_season = madrid
        self.wikidata = wikidata
        self.infoboxes = infoboxes
        self.revisions = revisions
        self.gates = frozenset(gates)
        self._clock = clock
        self._finishes: dict[tuple[str, date], dict[str, datetime]] = {}
        self._clubs: dict[int, list[str]] = {}
        self._club_refs: dict[int, TeamRef] = {}
        self._adapted: dict[tuple, list[Match]] = {}
        self._madrid_matches: tuple[Match, ...] = ()
        self._checked_madrid: datetime | None = None

    # -- time and configuration

    def _now(self) -> datetime:
        return self._clock().astimezone(UTC)

    def _today(self) -> date:
        return madrid_day(self._now())

    def _listed(self, config: CompetitionConfig) -> bool:
        gate = config.gate or CATALOG_GATES.get(config.slug)
        return gate is None or gate in self.gates

    def _config(self, slug: str) -> CompetitionConfig:
        config = BY_SLUG.get(slug)
        if config is None or not self._listed(config):
            raise NotCovered()
        return config

    def _fd_on(self) -> bool:
        """Whether FD would be asked now: a client, not off after a refused key."""
        return self.football is not None and self.football.enabled

    def _fd_covers(self, config: CompetitionConfig) -> bool:
        return self._fd_on() and config.fd_code is not None

    def _fd_configs(self) -> list[CompetitionConfig]:
        return [c for c in COMPETITIONS if self._fd_covers(c) and self._listed(c)]

    # -- one call's trace, and the View it ends in

    @contextmanager
    def _call(self) -> Iterator[_Trace]:
        trace = _Trace(today=self._today())
        budget = RequestBudget.current()
        before = budget.deferred if budget is not None else 0
        yield trace
        if budget is not None and budget.deferred > before:
            trace.partial = True

    def _view(self, trace: _Trace, value: T, *, matches: Sequence[Match] = (),
              shown: Sequence[Any] | None = None) -> View[T]:
        """The ``View`` of one call. ``shown``: the rows the value lists, whose sources are
        then its credits (a source read but not shown is not credited); where it is empty,
        or not given, every source read is credited (an empty day is the sources' answer)."""
        used = list(trace.used)
        if shown:
            used = [ref.provider for row in shown for ref in getattr(row, "sources", ())]
        finished = [_match_day(m) for m in matches if m.status == "FINISHED"]
        through = max(finished) if finished else None
        lines = [f"Results through {day_label(through, trace.today)}."] if through else []
        lines += [line for line in trace.lines if line not in lines]
        if trace.partial:
            lines.append(DEFERRED_LINE)
        stamps = [stamp for stamp in (_when(c) for c in trace.checked) if stamp is not None]
        checked = (min(stamps) if stamps else self._now()).isoformat()
        return View(value=value,
                    credits=tuple(p for p in CREDIT_ORDER if p in used),
                    freshness=Freshness(through=through, checked=checked, lines=tuple(lines),
                                        partial=trace.partial),
                    coverage=tuple(trace.coverage), missing=tuple(trace.missing))

    # -- football-data.org, through the chain

    async def _fd(self, trace: _Trace, call: Callable[[FootballData], Awaitable[T]]) -> T | None:
        """FD's answer, or ``None`` where FD cannot be read (no key, a refused key): the
        caller reads the next source. ``Unknown`` and every other failure pass on."""
        if self.football is None:
            return None
        try:
            found = await call(self.football)
        except Disabled:
            return None
        self._credit_fd(trace, found)
        return found

    def _credit_fd(self, trace: _Trace, found: object) -> None:
        items = found if isinstance(found, list) else [found]
        refs = [ref for item in items for ref in getattr(item, "sources", ())
                if ref.provider == _FD]
        if refs:
            trace.read(refs)
        else:
            trace.credit(_FD, self._now().isoformat())

    async def _peek(self, call: Callable[[FootballData], Awaitable[T]]) -> T | None:
        """An FD resource only where this process or the shared store holds it (at any
        age): the call runs under a cap of no request, so none is made."""
        if self.football is None:
            return None
        with RequestBudget(0):
            try:
                return await call(self.football)
            except FeedError:
                return None

    async def _fd_read(self, trace: _Trace, call: Callable[[FootballData], Awaitable[T]], *,
                       cold: bool) -> T | None:
        """``_fd`` where ``cold``, else ``_peek`` (credited where it finds the resource)."""
        if cold:
            return await self._fd(trace, call)
        found = await self._peek(call)
        if found is not None:
            self._credit_fd(trace, found)
        return found

    def _index(self, matches: Iterable[Match] = (), teams: Iterable[Team] = ()) -> None:
        """Remember each FD club seen, and its competitions (``team`` and ``h2h`` read it)."""
        def note(club: TeamRef, slug: str) -> None:
            if club.fd_id is None:
                return
            self._club_refs.setdefault(club.fd_id, club)
            seen = self._clubs.setdefault(club.fd_id, [])
            if slug not in seen:
                seen.append(slug)
                seen.sort(key=lambda s: BY_SLUG[s].order)

        for match in matches:
            note(match.home, match.competition)
            note(match.away, match.competition)
        for team in teams:
            for slug in team.competitions:
                note(team.ref, slug)

    # -- versions

    def _observe(self, matches: Iterable[Match]) -> None:
        """Record today's finishes the day resource shows (PLATFORM 2.4)."""
        today = self._today()
        now = self._now()
        for stale in [k for k in self._finishes if k[1] != today]:
            del self._finishes[stale]
        for match in matches:
            if match.status == "FINISHED" and _match_day(match) == today.isoformat():
                self._finishes.setdefault((match.competition, today), {}).setdefault(
                    match.key, now)

    def version(self, slug: str) -> int:
        """Competition ``slug``'s version: today's date and the finishes seen today in it
        (``ordinal * 1000 + finishes``), so a key never repeats a stale day's."""
        today = self._today()
        return today.toordinal() * 1000 + len(self._finishes.get((slug, today), {}))

    def standings_version(self, slug: str) -> int:
        """The version the standings are read under: ``version``'s, counting only finishes
        seen at least ``STANDINGS_DEBOUNCE`` ago (the warm plan reads under it too)."""
        today = self._today()
        settled = self._now() - STANDINGS_DEBOUNCE
        seen = self._finishes.get((slug, today), {})
        return today.toordinal() * 1000 + sum(1 for at in seen.values() if at <= settled)

    # -- the free feeds

    async def _free(self, trace: _Trace, slugs: Sequence[str], year: int) -> dict[str, list[Match]]:
        """The free feeds' matches of ``slugs`` for the season starting ``year``. A competition
        that can't be read is left out with a line; where none can, the call raises
        (``NoSeason``, a 404, where no feed holds the season)."""
        leagues = await asyncio.gather(
            *(self.openfootball.league(adapters.FREE[slug], year) for slug in slugs),
            return_exceptions=True)
        found: dict[str, list[Match]] = {}
        failures: list[str] = []
        for slug, league in zip(slugs, leagues, strict=True):
            name = BY_SLUG[slug].name
            if isinstance(league, BaseException):
                if not isinstance(league, FeedError):
                    raise league
                failures.append(str(league))
                trace.line(f"{name} can’t be read right now.")
                continue
            if not league.rows:
                continue
            for provider in league.sources:
                trace.credit(provider, league.checked)
            if league.warning:
                trace.line(f"{name}: the last schedule read is shown.")
            if year == season_start(trace.today):
                trace.line(league.freshness(trace.today, trace.today).get("note"))
            memo = (league.code, league.year, league.checked, id(league.rows))
            if memo not in self._adapted:
                self._adapted[memo] = adapters.league_matches(league, today=trace.today)
                while len(self._adapted) > 32:
                    self._adapted.pop(next(iter(self._adapted)))
            found[slug] = self._adapted[memo]
        if not found and failures:
            if all(text == "Season file unavailable." for text in failures):
                later = year > season_start(trace.today)
                raise NoSeason(f"The free feeds have no fixtures for {year}/"
                               f"{(year + 1) % 100:02}{' yet' if later else ''}.")
            raise FeedError("No league schedules could be loaded for this season.")
        return found

    async def _ol_season(self, trace: _Trace, slug: str, year: int) -> tuple[list, str]:
        snap = await self.openligadb.season(adapters.OL_SHORTCUT[slug], year)
        trace.credit("openligadb", snap.checked)
        return list(snap.rows), snap.checked

    # -- Real Madrid's season article

    async def _facts(self, trace: _Trace, *, required: bool = False
                     ) -> MadridSeasonFacts | None:
        """The season article's facts for today's season; ``None`` (with a line) where it
        can't be read, unless ``required``."""
        await self._recheck_madrid()
        try:
            facts = await self.madrid_season.facts(trace.today)
        except FeedError:
            if required:
                raise
            trace.line(WIKI_DOWN)
            return None
        trace.read(facts.sources)
        if facts.warning:
            trace.line(WIKI_STALE)
        self._madrid_matches = facts.matches
        return facts

    async def _recheck_madrid(self) -> None:
        """While a Madrid match finished in the last 24 hours (two hours of play allowed),
        ask Wikipedia for the article's newest revision every 30 minutes (PLAN 3.4)."""
        now = self._now()
        if self._checked_madrid is not None and now - self._checked_madrid < timedelta(
                minutes=30):
            return
        recent = any(m.status == "FINISHED" and (k := _when(m.kickoff_utc)) is not None
                     and now - timedelta(hours=26) <= k <= now for m in self._madrid_matches)
        if recent:
            self._checked_madrid = now
            await self.madrid_season.check(self._today())

    async def _names(self, trace: _Trace) -> tuple[NameBook, dict[str, PersonRef],
                                                    dict[str, PersonRef]]:
        """Real Madrid's squad names (``names.NameBook``), each name's person as the
        catalogue keys him, and each Wikipedia key's person."""
        people = await self._madrid_people(trace) or []
        by_name = {p.person.ref.name: p.person.ref for p in people if p.wp_key}
        by_wp = {p.wp_key: p.person.ref for p in people if p.wp_key}
        return NameBook(list(by_name)), by_name, by_wp

    # ------------------------------------------------------------------ competitions

    async def competitions(self) -> View[list[Competition]]:
        """The competitions the readable sources cover, in PR 2.1's order: FD's list (with
        its current matchdays), the free feeds' six, Real Madrid's two cups."""
        with self._call() as trace:
            value = await self._competitions(trace, cold=True)
        return self._view(trace, value)

    async def _competitions(self, trace: _Trace, *, cold: bool) -> list[Competition]:
        listed: dict[str, Competition] = {}
        try:
            found = await self._fd_read(trace, lambda fd: fd.competitions(), cold=cold)
        except FeedError:
            found = None
            trace.line(FD_DOWN)
        for item in found or ():
            if self._listed(BY_SLUG[item.slug]):
                listed[item.slug] = item
        for config in COMPETITIONS:
            if config.slug in listed or not self._listed(config):
                continue
            free = config.slug in adapters.FREE or config.madrid_only or (
                config.slug in adapters.OL_SHORTCUT and config.fd_code is None)
            if free:
                listed[config.slug] = competition_object(config,
                                                         season_year(config, trace.today))
        return sorted(listed.values(), key=lambda c: c.order)

    # ------------------------------------------------------------------ matches

    async def day(self, day: date) -> View[list[Match]]:
        """The matches of Europe/Madrid day ``day``: one FD request (B3), else the free
        feeds; with Real Madrid's cup ties from Wikipedia. ``DAY_ORDER``."""
        with self._call() as trace:
            value = await _or_partial(trace, self._day(trace, day))
        return self._view(trace, value, matches=value, shown=value)

    async def _day(self, trace: _Trace, day: date) -> list[Match]:
        rows = await self._fd(trace, lambda fd: fd.day(day))
        if rows is not None:
            self._index(rows)
            if day == trace.today:
                self._observe(rows)
            found = [m for m in rows if self._listed(BY_SLUG[m.competition])]
        else:
            free = await self._free(trace, adapters.FREE_SLUGS, season_start(day))
            found = [m for listed in free.values() for m in listed
                     if _match_day(m) == day.isoformat()]
        facts = await self._facts(trace)
        if facts is not None:
            found += [m for m in facts.matches if BY_SLUG[m.competition].madrid_only
                      and _match_day(m) == day.isoformat()]
        return sorted(found, key=_day_order)

    async def season_matches(self, slug: str, *, season: int | None = None
                             ) -> View[list[Match]]:
        """Every match of ``slug``'s season (the current one unless ``season``, a first
        year, is given), today's rows overlaid. ``SCHEDULE_ORDER``."""
        with self._call() as trace:
            value = await _or_partial(trace, self._season(trace, slug, season))
        return self._view(trace, value, matches=value, shown=value)

    async def _season(self, trace: _Trace, slug: str, season: int | None = None, *,
                      cold: bool = True) -> list[Match]:
        """``slug``'s season matches. With ``cold`` false an FD season is read only where
        held, and is empty otherwise (the free feeds are not read in its place)."""
        config = self._config(slug)
        year = season if season is not None else season_year(config, trace.today)
        if config.madrid_only:
            if year != season_start(trace.today):
                raise NotListed()
            facts = await self._facts(trace, required=True)
            return sorted((m for m in facts.matches if m.competition == slug),
                          key=_schedule_order)
        if self._fd_covers(config):
            current = year == season_year(config, trace.today)
            version = self.version(slug) if current else None
            try:
                rows = await self._fd_read(trace, lambda fd: fd.season_matches(
                    config.fd_code, year, version=version), cold=cold)
            except Unknown:
                rows = None
                if slug not in adapters.FREE:
                    raise
            if rows is not None:
                self._index(rows)
                if current:
                    rows = await self._overlay(trace, rows)
                return sorted(rows, key=_schedule_order)
            if not cold:
                return []
        if slug in adapters.FREE:
            free = await self._free(trace, (slug,), year)
            return sorted(free.get(slug, []), key=_schedule_order)
        if slug in adapters.OL_SHORTCUT:
            payload, checked = await self._ol_season(trace, slug, year)
            return adapters.ol_matches(payload, slug, year, checked)
        raise NotCovered()

    async def _overlay(self, trace: _Trace, rows: list[Match]) -> list[Match]:
        """The today overlay (module), from the today resource where held."""
        today = await self._peek(lambda fd: fd.day(self._today()))
        if not today:
            return rows
        self._observe(today)
        newer = {m.fd_id: m for m in today if m.fd_id is not None}
        out = []
        for match in rows:
            other = newer.get(match.fd_id)
            if other is not None and (match.source_updated or "") <= (other.source_updated
                                                                      or ""):
                self._credit_fd(trace, other)
                match = other
            out.append(match)
        return out

    async def match(self, key: str) -> View[Match]:
        """One match by its key, a legacy board id or a slug key; raises ``Unknown``."""
        with self._call() as trace:
            found = await self._match(trace, key)
        return self._view(trace, found, shown=[found])

    async def _match(self, trace: _Trace, key: str) -> Match:
        old = legacy(key)
        if old is not None:
            return await self._legacy(trace, key, *old)
        parsed = parse(key)
        if parsed is None:
            raise NotListed()
        shape = _SLUG_DAY.fullmatch(parsed.slug) or _SLUG_DAY.fullmatch(parsed.whole)
        try:
            day = date.fromisoformat(shape["day"]) if shape else None
        except ValueError:
            day = None
        if parsed.fd_id is not None and self._fd_on():
            # The id is authoritative while FD answers (PLATFORM 5.2): the slug is not read.
            found = await self._by_fd_id(trace, parsed.fd_id, day)
            if found is None:
                raise NotListed()
            return await self._fill(trace, found)
        if shape is None or day is None:
            raise NotListed()
        candidates = await self._day(trace, day)
        whole = [m for m in candidates if m.key == parsed.whole]
        if len(whole) == 1:
            return await self._fill(trace, whole[0])
        facts = await self._facts(trace)
        if facts is not None:
            exact = [m for m in facts.matches if m.key in (parsed.whole, parsed.slug)]
            if exact:
                joined = crosswalk.join_matches(candidates, exact)
                return await self._fill(trace, joined.get(exact[0].key, exact[0]))
        named = [m for m in candidates
                 if crosswalk.slug_names_match(shape["home"], m.home)
                 and crosswalk.slug_names_match(shape["away"], m.away)]
        if len(named) == 1:
            return await self._fill(trace, named[0])
        raise NotListed()

    async def _by_fd_id(self, trace: _Trace, fd_id: int, day: date | None) -> Match | None:
        """The FD match ``fd_id``: in its day's resource (one request), else in a season
        resource held."""
        if day is not None:
            rows = await self._fd(trace, lambda fd: fd.day(day))
            if rows is not None:
                self._index(rows)
                if day == trace.today:
                    self._observe(rows)
                found = [m for m in rows if m.fd_id == fd_id
                         and self._listed(BY_SLUG[m.competition])]
                if found:
                    return found[0]
        for config in self._fd_configs():
            year = season_year(config, trace.today)
            held = await self._peek(lambda fd, c=config, y=year: fd.season_matches(
                c.fd_code, y, version=self.version(c.slug)))
            for match in held or ():
                if match.fd_id == fd_id:
                    self._credit_fd(trace, match)
                    return match
        return None

    async def _legacy(self, trace: _Trace, key: str, code: str, year: int) -> Match:
        """A board id: its free-feed row, or the FD match the crosswalk joins it to."""
        slug = adapters.CODE_OF.get(code)
        if slug is None:
            raise NotListed()
        free = await self._free(trace, (slug,), year)
        found = [m for m in free.get(slug, []) if key in m.legacy_keys]
        if not found:
            raise NotListed()
        match = found[0]
        if self._fd_covers(BY_SLUG[slug]) and match.kickoff_utc:
            day = date.fromisoformat(_match_day(match))
            try:
                rows = await self._fd(trace, lambda fd: fd.day(day))
            except Unknown:
                rows = None
            joined = crosswalk.join_matches(rows or [], [match]).get(match.key)
            if joined is not None:
                return await self._fill(trace, replace(
                    joined, legacy_keys=tuple(dict.fromkeys(joined.legacy_keys + (key,)))))
        return await self._fill(trace, match)

    async def _fill(self, trace: _Trace, match: Match) -> Match:
        """The Madrid fill (module)."""
        if goal_rules.madrid_side(match) is None or BY_SLUG[match.competition].madrid_only:
            return match
        facts = await self._facts(trace)
        if facts is None:
            return match
        joined = crosswalk.join_matches([match], list(facts.matches))
        box = next((m for m in facts.matches if m.key in joined), None)
        if box is None:
            return match
        return replace(match, ground=match.ground or box.ground,
                       attendance=(match.attendance if match.attendance is not None
                                   else box.attendance),
                       report_url=match.report_url or box.report_url,
                       referee=match.referee or box.referee,
                       sources=tuple(dict.fromkeys(match.sources + box.sources)))

    # ------------------------------------------------------------------ goals

    async def goals(self, key: str) -> View[list[GoalEvent]]:
        """The goals of match ``key``, with the coverage lines (``goals.py``)."""
        with self._call() as trace:
            match = await self._match(trace, key)
            events, coverage = await self._goals(trace, match)
            trace.coverage.extend(coverage)
        return self._view(trace, events, shown=[match, *events])

    async def _goals(self, trace: _Trace, match: Match
                     ) -> tuple[list[GoalEvent], tuple[Coverage, ...]]:
        if match.status == "AWARDED" or match.status not in goal_rules.STARTED:
            return goal_rules.assess([], match)
        madrid = goal_rules.madrid_side(match) is not None
        facts = await self._facts(trace) if madrid else None
        book, squad, by_wp = await self._names(trace) if facts is not None else (
            NameBook(()), {}, {})
        if match.competition in adapters.OL_SHORTCUT:
            year = int(match.season[:4])
            try:
                payload, checked = await self._ol_season(trace, match.competition, year)
            except FeedError:
                payload, checked = [], self._now().isoformat()
                trace.line(OL_DOWN)
            records = {}
            for raw in payload:
                adapted = adapters.ol_match(raw, match.competition, year, checked)
                if adapted is not None:
                    records[adapted.key] = (adapted, raw)
            joined = crosswalk.join_matches([match], [m for m, _ in records.values()])
            if joined:
                raw = records[next(iter(joined))][1]
                events, unread = goal_rules.ol_events(raw, match, checked=checked, book=book,
                                                      squad=squad)
                return goal_rules.assess(events, match, reported=adapters.ol_result(raw),
                                         unread=unread)
            if not madrid:
                return [], (Coverage("scorers", 0, _goals_in(match), goal_rules.NO_REPORT),)
        if madrid and facts is not None:
            joined = crosswalk.join_matches([match], list(facts.matches))
            box = next((m for m in facts.matches if m.key in joined or m.key == match.key),
                       None)
            if box is not None:
                events = [replace(e, scorer_key=by_wp[e.scorer_key].key)
                          if e.scorer_key in by_wp else e
                          for e in goal_rules.wp_events(facts.goals, box.key, match)]
                return goal_rules.assess(events, match, reported=box.result)
            return [], (Coverage("scorers", 0, _goals_in(match), goal_rules.NO_REPORT),)
        return [], (Coverage("scorers", 0, _goals_in(match), goal_rules.NO_SOURCE),)

    # ------------------------------------------------------------------ tables and scorers

    async def table(self, slug: str, view: Literal["all", "home", "away", "after"] = "all",
                    after: date | None = None) -> View[Table]:
        """``slug``'s table: the source's own for "all" (FD), else worked out from results by
        ``derive.table`` (its ``order`` says so); "after" is the table as it stood at the end
        of day ``after``, counting results on or before it."""
        with self._call() as trace:
            config = self._config(slug)
            if config.zones is None:
                raise NotCovered()
            if view == "all" and after is None and self._fd_covers(config):
                try:
                    tables = await self._fd(trace, lambda fd: fd.standings(
                        config.fd_code, version=self.standings_version(slug)))
                except Unknown:
                    tables = None
                    if slug not in adapters.FREE:
                        raise
                if tables:
                    if len(tables) > 1:
                        trace.line(GROUP_TABLES)
                    return self._view(trace, tables[0])
            matches = await self._season(trace, slug)
            value = _derived_table(slug, matches, view, after)
        return self._view(trace, value)

    async def scorers(self, slug: str) -> View[list[ScorerLine]]:
        """``slug``'s scorers: FD's list, with B2's lines; else counted from OpenLigaDB's
        goals of finished matches (``SCORERS_ORDER``); else none, with a line."""
        with self._call() as trace:
            config = self._config(slug)
            if config.madrid_only:
                raise NotCovered()
            lines = None
            if self._fd_covers(config):
                try:
                    lines = await self._fd(trace, lambda fd: fd.scorers(
                        config.fd_code, version=self.version(slug)))
                except Deferred:
                    lines = []
                    trace.partial = True
                except Unknown:
                    if slug not in adapters.OL_SHORTCUT:
                        raise
            if lines is not None:
                count = lines[0].listed if lines else 0
                trace.coverage.append(Coverage("listed", count, count, listed_line(count)))
                if lines and lines[0].cut:
                    trace.coverage.append(Coverage("cut", count, count, cut_line(count)))
                value = lines
            elif slug in adapters.OL_SHORTCUT:
                value = await self._ol_scorers(trace, slug)
            else:
                trace.lack(NO_SCORERS)
                value = []
        return self._view(trace, value)

    async def _ol_scorers(self, trace: _Trace, slug: str) -> list[ScorerLine]:
        year = season_year(BY_SLUG[slug], trace.today)
        payload, checked = await self._ol_season(trace, slug, year)
        book, squad, _ = (await self._names(trace) if slug == "champions-league"
                          else (NameBook(()), {}, {}))
        counts: dict[tuple[str, str], list] = {}
        named = total = 0
        for raw in payload:
            match = adapters.ol_match(raw, slug, year, checked)
            if match is None or match.status != "FINISHED":
                continue
            events, unread = goal_rules.ol_events(raw, match, checked=checked, book=book,
                                                  squad=squad)
            total += len(events) + unread
            for event in events:
                if not event.scorer:
                    continue
                named += 1
                if event.own_goal:
                    continue
                team = match.home if event.side == "home" else match.away
                entry = counts.setdefault((team.key, event.scorer),
                                          [team, event.scorer_key, 0, 0])
                entry[2] += 1
                entry[3] += int(event.penalty)
        trace.coverage.append(Coverage("scorers", named, total,
                                       goal_rules.scorers_line(named, total)))
        ordered = sorted(counts.items(), key=lambda item: (-item[1][2], item[0][1].casefold(),
                                                           item[0][0]))
        return [ScorerLine(person=PersonRef(key=person_key or slugify(name) or team_key,
                                            name=name),
                           team=team, competition=slug, goals=goals, assists=None,
                           penalties=penalties, listed=len(counts), cut=False)
                for (team_key, name), (team, person_key, goals, penalties) in ordered]

    # ------------------------------------------------------------------ teams

    async def teams(self, slug: str) -> View[list[Team]]:
        """The clubs of ``slug`` with their squads (FD, Madrid's joined to Wikipedia's);
        without FD, the clubs its schedule names, by name, with Real Madrid's squad only."""
        with self._call() as trace:
            value = await _or_partial(trace, self._teams(trace, slug))
        return self._view(trace, value)

    async def _fd_teams(self, trace: _Trace, config: CompetitionConfig, *, cold: bool
                        ) -> list[Team] | None:
        """FD's clubs of ``config`` as FD lists them, or ``None`` where FD can't give them."""
        if not self._fd_covers(config):
            return None
        try:
            found = await self._fd_read(trace, lambda fd: fd.teams(config.fd_code), cold=cold)
        except Unknown:
            if config.slug not in adapters.FREE:
                raise
            return None
        if found is not None:
            self._index(teams=found)
        return found

    async def _teams(self, trace: _Trace, slug: str, *, cold: bool = True) -> list[Team]:
        config = self._config(slug)
        if config.madrid_only:
            raise NotCovered()
        found = await self._fd_teams(trace, config, cold=cold)
        if found is not None:
            return [await self._madrid_team(trace, t, fd_team=t)
                    if t.ref.fd_id == MADRID_FD_ID else t for t in found]
        if self._fd_covers(config) and not cold:
            return []
        matches = await self._season(trace, slug)
        clubs: dict[str, TeamRef] = {}
        for match in matches:
            for club in (match.home, match.away):
                clubs.setdefault(club.key, club)
        trace.lack(NO_SQUADS)
        out = []
        for club in sorted(clubs.values(), key=lambda c: (c.name.casefold(), c.key)):
            team = Team(ref=club, area=None, founded=None, ground=None, coach=None,
                        competitions=(slug,), squad=(), sources=())
            out.append(await self._madrid_team(trace, team) if crosswalk.is_madrid(club)
                       else team)
        return out

    async def _madrid_team(self, trace: _Trace, team: Team, *, fd_team: Team | None = None
                           ) -> Team:
        people = await self._madrid_people(trace, fd_team=fd_team, lookup=False)
        if people is None:
            return team
        return replace(team, squad=tuple(p.entry for p in people), sources=tuple(
            dict.fromkeys(team.sources + tuple(s for p in people for s in p.wp_sources))))

    async def team(self, key: str, *, competition: str | None = None) -> View[Team]:
        """One club by key. ``competition`` is a hint (the page's ``comp``). An FD club is
        looked for in the competitions it was seen in, then in every competition's list held,
        then in at most two lists read; ``Unknown`` only once every list is held without it
        (until then the view is partial)."""
        with self._call() as trace:
            value = await self._team(trace, key, competition)
        return self._view(trace, value)

    async def _team(self, trace: _Trace, key: str, hint: str | None) -> Team:
        parsed = parse(key)
        if parsed is None:
            raise NotListed()
        if parsed.fd_id is not None and self._fd_on():
            found = await self._fd_team(trace, parsed.fd_id, hint)
            if found is not None:
                return found
            if parsed.fd_id != MADRID_FD_ID:
                raise FeedError(DEFERRED_LINE)
        if parsed.fd_id == MADRID_FD_ID or parsed.whole in ("real-madrid", MADRID_KEY):
            team = Team(ref=MADRID_REF, area=None, founded=None, ground=None, coach=None,
                        competitions=tuple(c.slug for c in COMPETITIONS
                                           if c.slug in ("la-liga", "champions-league")
                                           or c.madrid_only),
                        squad=(), sources=())
            return await self._madrid_team(trace, team)
        free = await self._free(trace, adapters.FREE_SLUGS, season_start(trace.today))
        clubs: dict[str, tuple[TeamRef, list[str]]] = {}
        for slug, matches in free.items():
            for match in matches:
                for club in (match.home, match.away):
                    if club.key in (parsed.whole, parsed.slug) or crosswalk.slug_names_match(
                            parsed.slug, club):
                        seen = clubs.setdefault(club.key, (club, []))[1]
                        if slug not in seen:
                            seen.append(slug)
        if len(clubs) != 1:
            raise NotListed()
        club, slugs = next(iter(clubs.values()))
        trace.lack(NO_SQUADS)
        return Team(ref=club, area=None, founded=None, ground=None, coach=None,
                    competitions=tuple(slugs), squad=(), sources=())

    async def _fd_team(self, trace: _Trace, fd_id: int, hint: str | None) -> Team | None:
        """FD's club ``fd_id`` (``team``'s search); ``None`` when not found within the reads
        allowed, with the view partial."""
        configs = self._fd_configs()
        order = ([c for c in configs if c.kind == "league"]
                 + [c for c in configs if c.kind != "league"])
        seen = list(self._clubs.get(fd_id, ()))
        if fd_id == MADRID_FD_ID and "la-liga" not in seen:
            seen.insert(0, "la-liga")
        first = [s for s in ([hint] if hint else []) + seen
                 if s in BY_SLUG and BY_SLUG[s] in configs]
        tried: set[str] = set()
        reads = 0
        for slug in dict.fromkeys(first):
            tried.add(slug)
            reads += 1
            team = _pick(await self._teams(trace, slug), fd_id)
            if team is not None:
                return team
        held_all = True
        for config in order:
            if config.slug in tried:
                continue
            held = await self._fd_teams(trace, config, cold=False)
            if held is None:
                held_all = False
                continue
            tried.add(config.slug)
            team = _pick(held, fd_id)
            if team is not None:
                return await self._madrid_team(trace, team, fd_team=team) if (
                    fd_id == MADRID_FD_ID) else team
        if held_all:
            raise NotListed()
        for config in order:
            if config.slug in tried or reads >= 2:
                continue
            reads += 1
            tried.add(config.slug)
            try:
                team = _pick(await self._teams(trace, config.slug), fd_id)
            except Deferred:
                break
            if team is not None:
                return team
        if all(c.slug in tried for c in order):
            raise NotListed()
        trace.partial = True
        return None

    async def team_matches(self, key: str) -> View[list[Match]]:
        """A club's matches in the competitions it plays in (``SCHEDULE_ORDER``): its league
        read cold, the others where held (the view is partial otherwise), and Real Madrid's
        cup ties from Wikipedia."""
        with self._call() as trace:
            team = await self._team(trace, key, None)
            slugs = [s for s in team.competitions if s in BY_SLUG and self._listed(BY_SLUG[s])]
            if crosswalk.is_madrid(team.ref):
                slugs = [c.slug for c in COMPETITIONS if self._listed(c) and (
                    c.slug in slugs or c.madrid_only or c.slug in ("la-liga",
                                                                   "champions-league"))]
            slugs.sort(key=lambda s: (BY_SLUG[s].kind != "league", BY_SLUG[s].order))
            found: dict[str, Match] = {}
            first = True
            for slug in slugs:
                config = BY_SLUG[slug]
                if config.madrid_only:
                    facts = await self._facts(trace)
                    rows = [m for m in (facts.matches if facts else ()) if m.competition == slug]
                else:
                    cold = first or not self._fd_covers(config)
                    try:
                        rows = await self._season(trace, slug, cold=cold)
                    except Deferred:
                        rows = []
                    if not rows and self._fd_covers(config):
                        trace.partial = True
                    first = False
                for match in rows:
                    if _plays(team.ref, match):
                        found.setdefault(match.key, match)
            value = sorted(found.values(), key=_schedule_order)
        return self._view(trace, value, matches=value, shown=value)

    # ------------------------------------------------------------------ people

    async def _madrid_people(self, trace: _Trace, *, fd_team: Team | None = None,
                             lookup: bool = True) -> list[_Player] | None:
        """Real Madrid's squad joined across the sources (the Madrid squad rule). Without
        ``fd_team``, FD's Madrid squad is used where held (``lookup``); ``None`` where the
        season article can't be read."""
        facts = await self._facts(trace)
        if facts is None:
            return None
        if fd_team is None and lookup and self._listed(BY_SLUG["la-liga"]):
            held = await self._fd_teams(trace, BY_SLUG["la-liga"], cold=False)
            fd_team = _pick(held or [], MADRID_FD_ID)
        titles = {a.person.key: a.title for a in facts.articles}
        boxes: dict[str, Infobox] = {}
        if self.infoboxes is not None and titles:
            boxes = await self.infoboxes.read(list(titles.values()))
        wd: dict[str, WikidataPerson] = {}
        if self.wikidata is not None and titles:
            wd = await self.wikidata.people(list(titles.values()))
            for person in wd.values():
                trace.read(person.sources)
        wp_who = [crosswalk.Who(entry.person.key, entry.person.name,
                                b.born if (b := boxes.get(titles.get(entry.person.key, "")))
                                else None)
                  for entry in facts.squad]
        fd_squad = list(fd_team.squad) if fd_team is not None else []
        fd_who = [crosswalk.Who(e.person.key, e.person.name, e.born) for e in fd_squad]
        joined = crosswalk.join_people(fd_who, wp_who)
        by_fd = {e.person.key: e for e in fd_squad}
        fd_sources = tuple(s for s in (fd_team.sources if fd_team is not None else ())
                           if s.provider == _FD)
        people = []
        for entry in facts.squad:
            title = titles.get(entry.person.key)
            people.append(_Player.of(entry, by_fd.get(joined.get(entry.person.key, "")),
                                     title, boxes.get(title or ""), wd.get(title or ""),
                                     facts.sources, fd_sources))
        people += [_Player.of(None, by_fd[key], None, None, None, (), fd_sources)
                   for key in crosswalk.unlisted(fd_who, wp_who, joined)]
        return people

    async def person(self, key: str) -> View[Person]:
        """One player: Real Madrid's from the joined squad (FD's Madrid squad read cold where
        the key is FD's); another club's from a squad held, else FD's person resource.
        Raises ``Unknown``."""
        with self._call() as trace:
            value = await self._person(trace, key)
        return self._view(trace, value)

    async def _person(self, trace: _Trace, key: str) -> Person:
        parsed = parse(key)
        if parsed is None:
            raise NotListed()
        fd_on = self._fd_on() and parsed.fd_id is not None
        held: dict[str, list[Team]] = {}
        if fd_on:
            for config in self._fd_configs():
                held[config.slug] = await self._fd_teams(trace, config, cold=False) or []
        madrid = _pick(held.get("la-liga", []), MADRID_FD_ID)
        other = next(((team, entry) for slug, teams in held.items() for team in teams
                      for entry in team.squad if team.ref.fd_id != MADRID_FD_ID
                      and _fd_id_of(entry.person.key) == parsed.fd_id), None)
        if fd_on and madrid is None and other is None and self._listed(BY_SLUG["la-liga"]):
            madrid = _pick(await self._fd_teams(trace, BY_SLUG["la-liga"], cold=True) or [],
                           MADRID_FD_ID)
        if other is None:
            for player in await self._madrid_people(trace, fd_team=madrid) or ():
                if player.answers(parsed):
                    if self._fd_on() and player.fd_id is None:
                        trace.lack(NOT_JOINED)
                    return player.person
        if not fd_on:
            raise NotListed()
        if other is not None:
            team, entry = other
            return Person(ref=entry.person, fd_id=parsed.fd_id, wp_title=None, qid=None,
                          born=entry.born, nationality=entry.nationality, group=entry.group,
                          positions=(), shirt=None, height_cm=None, birthplace=None,
                          sources=team.sources)
        found = await self._fd(trace, lambda fd: fd.person(parsed.fd_id))
        if found is None:
            raise NotListed()
        return found

    async def named(self, key: str) -> View[list[Named]]:
        """The matches FD names player ``key`` for (named, started or on the bench: the source
        does not say which), by kick-off. Without FD, or for a player FD's key does not name,
        none, with a line."""
        with self._call() as trace:
            parsed = parse(key)
            if parsed is None:
                raise NotListed()
            value: list[Named] = []
            found = None
            if parsed.fd_id is not None:
                found = await self._fd(trace, lambda fd: fd.person_matches(parsed.fd_id,
                                                                           priority=1))
            if found is not None:
                value = found
            else:
                trace.lack(NOT_JOINED if self._fd_on() else NO_NAMED)
        return self._view(trace, value)

    async def madrid(self) -> View[MadridFacts]:
        """Real Madrid's season: the article's facts (keyed as the catalogue keys matches,
        against the schedules held), the joined squad and people, and appearances by match
        (REC 1.3) where the revision reader is given. Makes no FD request."""
        with self._call() as trace:
            facts = await self._facts(trace, required=True)
            people = await self._madrid_people(trace) or []
            schedule: list[Match] = []
            for slug in ("la-liga", "champions-league"):
                if self._listed(BY_SLUG[slug]):
                    rows = await self._season(trace, slug, cold=not self._fd_on())
                    schedule += [m for m in rows if goal_rules.madrid_side(m) is not None]
            keyed = crosswalk.join_matches(schedule, list(facts.matches))
            refs = {p.wp_key: p.person.ref for p in people if p.wp_key}
            article = replace(
                facts,
                squad=tuple(replace(e, person=refs.get(e.person.key, e.person))
                            for e in facts.squad),
                articles=tuple(replace(a, person=refs.get(a.person.key, a.person))
                               for a in facts.articles),
                lines=tuple(replace(line, person=refs.get(line.person.key, line.person))
                            for line in facts.lines),
                matches=tuple(_rekey(m, keyed.get(m.key)) for m in facts.matches),
                goals=tuple(replace(
                    g, match=keyed[g.match].key if g.match in keyed else g.match,
                    scorer_key=refs[g.scorer_key].key if g.scorer_key in refs else g.scorer_key)
                    for g in facts.goals))
            grid: Grid | None = None
            mismatches: tuple[Mismatch, ...] = ()
            appearances: tuple[Appearance, ...] = ()
            if self.revisions is None:
                trace.lack(NO_APPEARANCES)
            elif facts.matches:
                titles = {a.title: refs.get(a.person.key, a.person) for a in facts.articles}
                upcoming = min((m.kickoff_utc for m in facts.matches
                                if m.status != "FINISHED" and m.kickoff_utc), default=None)
                since = f"{season_start(trace.today)}-07-01T00:00:00Z"
                try:
                    grid, _ = await self.revisions.grid(facts.title, list(facts.matches),
                                                        since=since, upcoming=upcoming,
                                                        refs=titles)
                except FeedError:
                    trace.line(REVISIONS_DOWN)
                if grid is not None:
                    finished = [fixture(m) for m in facts.matches if m.status == "FINISHED"]
                    mismatches = reconcile(grid, article.lines, finished,
                                           {ref.key: title for title, ref in titles.items()})
                    appearances = tuple(
                        replace(a, match=keyed[a.match].key) if a.match in keyed else a
                        for a in grid.appearances)
            value = MadridFacts(article=article, squad=tuple(p.entry for p in people),
                                people=tuple(p.person for p in people),
                                appearances=appearances, grid=grid, mismatches=mismatches)
        return self._view(trace, value, matches=article.matches)

    # ------------------------------------------------------------------ head-to-head

    async def h2h(self, a: str, b: str, before: datetime | date) -> View[derive.H2H]:
        """``derive.h2h`` of clubs ``a`` and ``b`` (team keys) before ``before`` (R9), over
        every row read of the competitions both were seen in: the current season, FD's three
        earlier seasons, and OpenFootball's files from 2010/11 up to FD's first season (to
        this season without FD) for a league. ``derive`` keeps one row per meeting, FD's
        first, and writes the span line from the rows. At most one FD request is made cold
        (the first season not held); the others are read where held, and the view is
        partial where one is not."""
        with self._call() as trace:
            first, second = (await self._h2h_club(trace, a), await self._h2h_club(trace, b))
            shared = [s for s in first[1] if s in second[1] and s in BY_SLUG
                      and self._listed(BY_SLUG[s]) and not BY_SLUG[s].madrid_only]
            rows: list[Match] = []
            cold = 1
            for slug in shared:
                config = BY_SLUG[slug]
                current = season_year(config, trace.today)
                years = [current] + ([y for y in H2H_PAST_SEASONS if y < current]
                                     if self._fd_covers(config) else [])
                for year in years:
                    found = await self._season(trace, slug, year, cold=False)
                    if not found and self._fd_covers(config) and cold > 0:
                        cold -= 1
                        try:
                            found = await self._season(trace, slug, year)
                        except Deferred:
                            found = []
                    if not found and self._fd_covers(config):
                        trace.partial = True
                    rows += found
                if slug in adapters.FREE and config.kind == "league":
                    last = min(H2H_PAST_SEASONS) if self._fd_covers(config) else current
                    years = list(range(H2H_OPENFOOTBALL_SINCE, last))
                    leagues = await asyncio.gather(
                        *(self.openfootball.league(adapters.FREE[slug], y) for y in years),
                        return_exceptions=True)
                    for league in leagues:
                        if isinstance(league, BaseException):
                            if not isinstance(league, FeedError):
                                raise league
                            continue
                        if league.rows:
                            trace.credit("openfootball", league.checked)
                            rows += adapters.league_matches(league, today=trace.today)
            value = derive.h2h(first[0], second[0], rows, before)
        return self._view(trace, value)

    async def _h2h_club(self, trace: _Trace, key: str) -> tuple[TeamRef, list[str]]:
        """A club and the competitions it was seen in, without an FD request: the FD index,
        else (no key) the free feeds' schedules."""
        parsed = parse(key)
        if parsed is None:
            raise NotListed()
        if parsed.fd_id is not None and parsed.fd_id in self._club_refs:
            return self._club_refs[parsed.fd_id], list(self._clubs.get(parsed.fd_id, ()))
        if self._fd_on() and parsed.fd_id is not None:
            raise FeedError(DEFERRED_LINE)
        team = await self._team(trace, key, None)
        return team.ref, list(team.competitions)

    # ------------------------------------------------------------------ search

    async def search_entries(self) -> View[list[Entry]]:
        """Every competition listed, then the clubs and players of the squads held: no FD
        request is made (Search's cap is 0), and the view says when it is partial.
        ``SEARCH_ORDER``."""
        with self._call() as trace:
            competitions = await self._competitions(trace, cold=False)
            entries = [Entry("competition", c.slug, c.name, c.area,
                             c.slug in ("la-liga", "champions-league") or c.madrid_only)
                       for c in competitions]
            clubs: dict[str, Entry] = {}
            players: dict[str, Entry] = {}
            short = False
            for c in competitions:
                config = BY_SLUG[c.slug]
                if not self._fd_covers(config):
                    continue
                held = await self._fd_teams(trace, config, cold=False)
                if held is None:
                    short = True
                    continue
                for team in held:
                    madrid = team.ref.fd_id == MADRID_FD_ID
                    clubs.setdefault(team.ref.key, Entry("club", team.ref.key, team.ref.name,
                                                         c.name, madrid))
                    if madrid:
                        continue
                    for entry in team.squad:
                        players.setdefault(entry.person.key, Entry(
                            "player", entry.person.key, entry.person.name, team.ref.name,
                            False))
            for player in await self._madrid_people(trace) or ():
                players[player.person.ref.key] = Entry(
                    "player", player.person.ref.key, player.person.ref.name, MADRID_REF.name,
                    True)
            clubs.setdefault(MADRID_KEY, Entry("club", MADRID_KEY, MADRID_REF.name,
                                               BY_SLUG["la-liga"].name, True))
            if short:
                trace.partial = True
                trace.line(SEARCH_PARTIAL)

            def by_name(entry: Entry) -> tuple:
                return (not entry.madrid, entry.name.casefold(), entry.key)

            entries += sorted(clubs.values(), key=by_name)
            entries += sorted(players.values(), key=by_name)
        return self._view(trace, entries)


# ------------------------------------------------------------------ helpers


async def _or_partial(trace: _Trace, call: Awaitable[list[T]]) -> list[T]:
    """A list call's rows; none, with the view partial, where the budget deferred the
    request it needed (PLATFORM 2.5: "stale, else a partial view")."""
    try:
        return await call
    except Deferred:
        trace.partial = True
        return []


def _pick(teams: Sequence[Team], fd_id: int) -> Team | None:
    return next((t for t in teams if t.ref.fd_id == fd_id), None)


def _fd_id_of(key: str) -> int | None:
    parsed = parse(key)
    return parsed.fd_id if parsed is not None else None


def _derived_table(slug: str, matches: Sequence[Match], view: str,
                   after: date | None) -> Table:
    """The table ``derive.table`` (D3-B) works out from a league's or a league phase's
    matches; "after" is the table as it stood at the end of day ``after``."""
    counted = [m for m in matches if m.stage is None or m.stage in _TABLE_STAGES]
    return derive.table(counted, view=view, after=after, competition=slug)


@dataclass(frozen=True)
class _Player:
    """A Madrid squad player joined across the sources."""

    entry: SquadEntry
    person: Person
    fd_id: int | None
    wp_key: str | None
    keys: frozenset[str]
    wp_sources: tuple[SourceRef, ...]

    @classmethod
    def of(cls, wp: SquadEntry | None, fd: SquadEntry | None, title: str | None,
           box: Infobox | None, wd: WikidataPerson | None,
           wp_sources: tuple[SourceRef, ...], fd_sources: tuple[SourceRef, ...]) -> _Player:
        base = wp if wp is not None else fd
        if base is None:
            raise ValueError("a player needs a squad entry")
        fd_id = _fd_id_of(fd.person.key) if fd is not None else None
        ref = PersonRef(key=fd.person.key if fd is not None else base.person.key,
                        name=base.person.name)
        entry = SquadEntry(
            person=ref,
            group=(wp.group if wp is not None and wp.group else
                   fd.group if fd is not None else None),
            shirt=wp.shirt if wp is not None else None,
            born=(fd.born if fd is not None and fd.born else box.born if box else None),
            nationality=(fd.nationality if fd is not None and fd.nationality else
                         wp.nationality if wp is not None else None))
        sources = tuple(dict.fromkeys(
            (fd_sources if fd is not None else ()) + (wp_sources if wp is not None else ())
            + (wd.sources if wd is not None else ())))
        person = Person(ref=ref, fd_id=fd_id, wp_title=title,
                        qid=wd.qid if wd is not None else None, born=entry.born,
                        nationality=entry.nationality, group=entry.group,
                        positions=box.positions if box is not None else (), shirt=entry.shirt,
                        height_cm=wd.height_cm if wd is not None else None,
                        birthplace=wd.birthplace if wd is not None else None, sources=sources)
        keys = {ref.key, base.person.key}
        return cls(entry=entry, person=person, fd_id=fd_id,
                   wp_key=wp.person.key if wp is not None else None, keys=frozenset(keys),
                   wp_sources=wp_sources if wp is not None else ())

    def answers(self, parsed: Key) -> bool:
        """Whether a parsed key names this player: by FD id where both have one, else by a
        key (or a key's slug) the player is known by."""
        if parsed.fd_id is not None and self.fd_id is not None:
            return parsed.fd_id == self.fd_id
        slugs = {k.split("-", 1)[1] if _fd_id_of(k) is not None else k for k in self.keys}
        return parsed.whole in self.keys or parsed.slug in slugs or parsed.whole in slugs


def _rekey(match: Match, keyed: Match | None) -> Match:
    if keyed is None:
        return match
    return replace(match, key=keyed.key, fd_id=keyed.fd_id,
                   legacy_keys=tuple(dict.fromkeys(keyed.legacy_keys + (match.key,))))
