"""Derivations over the season model: tables, form, head-to-head, records, positions by
matchday, goal periods, largest margins and days since (PLAN D3-B).

Pure functions. Each takes model objects (``model.py``) and returns a frozen dataclass or a
model object; none reads a source, a clock or the network. Every number they give is a count
of the rows they were handed, so a test can recompute it, and a page that prints one can say
how it was worked out.

**What counts as a result.** A match counts where its status is FINISHED or AWARDED and its
result has both sides (``counted``). A match in play or paused never counts: a table never
moves on an in-play result (PR 6.4, CP-8). A match decided on penalties counts only where its
result is level, as the result before the shoot-out, and then as a draw; a shoot-out match
whose result is not level is left out, since that source's result may include the kicks.

**The day of a match.** The Europe/Madrid calendar date of its kick-off; a match without a
kick-off instant takes the date its key ends with (``keys.match_key`` writes the Madrid day
last); a match with neither has no day, and is never counted where a rule names a date.

**Before (R9).** ``before`` is an aware datetime or a date, and names a Europe/Madrid day
(``cutoff``). Only matches on calendar days *before* that day count: a match earlier on the
same day does not. Form, head-to-head and days since always take it; tables, records, goal
periods and largest margins take it where a page asks "before" (the builder's fixture, a
match's "Before kick-off" table).

**One club, two sources.** A club is named by a ``TeamRef`` or a key. Two are one club by
the crosswalk's declared rule (``crosswalk.same_club``), the one rule the catalogue joins
clubs by too: equal football-data.org ids where both have one; else Real Madrid only with
Real Madrid; else a club form in common (the folded name, read through the declared aliases,
with the generic words dropped). A key stands for the club its slug names ("90001-a-fc", or
"a-fc" without an id). Nothing else joins two clubs: a name no rule joins stays another club.

**One match, two sources.** Rows of one meeting from two sources (the same Madrid day and the
same two clubs, either way round) are one match (``dedupe``): the football-data.org row is
kept, else the first given. Every function here dedupes what it is handed first, so a caller
that passes football-data.org's La Liga rows and Wikipedia's match boxes counts each match
once.

**Orders.** Every list is in a declared order, and ties stay ties:

- a table: points, then goal difference, then goals scored, then name (``DERIVED_ORDER``,
  PR 6.4); equal points, goal difference and goals scored share a position;
- form, head-to-head and a record's matches: by kick-off (form's results and head-to-head's
  meetings newest first, form's letters oldest first, as a table's form column reads);
- largest margins: by margin, then goals scored, then the earlier date (``LARGEST_ORDER``);
- goal periods: the six periods in match order.

Claim: each figure is a count of the rows handed in, under the rules above, and each sentence
here (an order line, the span line, a coverage line) says only what those rows hold.
Non-claim: a derived table is not the competition's official table (its tiebreaks and points
deductions can differ), and a span says where meetings were looked for, not that the sources
hold every meeting in it: a season missing from the rows handed in is missing from the count.
"""

from __future__ import annotations

import functools
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

from ..kickoff import from_utc
from . import crosswalk
from .competitions import BY_SLUG
from .keys import fold, parse, slugify
from .model import (
    Coverage,
    GoalEvent,
    Match,
    Outcome,
    SourceRef,
    StandingRow,
    Table,
    TableView,
    TeamRef,
)

__all__ = [
    "DERIVED_ORDER", "LARGEST_ORDER", "COUNTED", "PERIODS", "THRESHOLD", "Before", "Venue",
    "Form", "FormResult", "Record", "H2H", "Place", "MatchdayPlaces", "TeamPlace",
    "TeamGoal", "Period", "GoalPeriods", "Margin", "Largest", "DaysSince",
    "cutoff", "day_of", "counted", "outcome", "same_club", "dedupe",
    "table", "form", "h2h", "record", "positions_by_matchday", "team_places",
    "team_goals", "goal_periods", "largest", "days_since",
]

DERIVED_ORDER = ("Worked out here from reported results: points, then goal difference, then "
                 "goals scored, then name.")
"""The printed order line of every derived table (PR 6.4)."""
LARGEST_ORDER = "By margin, then goals scored, then the earlier date."
"""The printed order of the largest win and the largest defeat (PR 6.5)."""
COUNTED: frozenset[str] = frozenset({"FINISHED", "AWARDED"})
"""The statuses whose result counts."""
PERIODS: tuple[tuple[str, int, int], ...] = (
    ("0–15", 0, 15), ("16–30", 16, 30), ("31–45+", 31, 45),
    ("46–60", 46, 60), ("61–75", 61, 75), ("76–90+", 76, 90),
)
"""The six goal periods (PR 6.5): label, first and last minute. A goal in added time counts
in the period its minute ends (45+2 in 31–45+, 90+3 in 76–90+)."""
THRESHOLD = (4, 5)
"""Goal periods are drawn only where minutes are known for at least 4 in 5 goals (80 %)."""

FD = "football_data_org"
"""football-data.org's provider key: its row is kept where two sources list one match."""

Before = datetime | date
Venue = Literal["home", "away"]

_PLAYED = "FINISHED"
_KEY_DAY = re.compile(r"(\d{4}-\d{2}-\d{2})$")
_SEASON_YEAR = re.compile(r"^(\d{4})")
_SOURCE_NAMES = {FD: "football-data.org", "openfootball": "OpenFootball",
                 "openligadb": "OpenLigaDB", "wikipedia": "Wikipedia"}
_NO_ARTICLE = frozenset({"la-liga", "serie-a", "ligue-1"})
"""Competitions a sentence names without "the": "in La Liga", but "in the Champions League"."""
_NO_EXTRA_TIME_STAGES = frozenset({"REGULAR_SEASON", "LEAGUE_STAGE", "GROUP_STAGE"})
"""Stages whose matches end after 90 minutes and their added time: no extra time is played."""


# ------------------------------------------------------------------ the derived objects


@dataclass(frozen=True)
class FormResult:
    match: Match
    venue: Venue
    outcome: Outcome
    goals_for: int
    goals_against: int


@dataclass(frozen=True)
class Form:
    team: str                           # the club's key, as asked
    results: tuple[FormResult, ...]     # newest first
    outcomes: tuple[Outcome, ...]       # the same results' letters, oldest first
    count: int                          # the true count: how many results were found
    asked: int                          # how many were asked for (n)
    before: str                         # ISO day: the first day not counted (R9)


@dataclass(frozen=True)
class Record:
    team: str
    split: Venue | None                 # None: home and away
    competition: str | None             # None: every competition in the rows
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    clean_sheets: int                   # matches with no goal against
    without_a_goal: int                 # matches with no goal for
    matches: tuple[str, ...]            # the counted matches' keys, by kick-off
    before: str | None                  # ISO day, where a "before" rule applied


@dataclass(frozen=True)
class H2H:
    team: str
    opponent: str
    meetings: int
    wins: int                           # the team's
    draws: int
    losses: int                         # the team's
    matches: tuple[Match, ...]          # the meetings, newest first
    span: str                           # where meetings were looked for (the span line)
    empty: str | None                   # the line for no meeting; None where there is one
    providers: tuple[str, ...]          # the sources searched, in the span line's order
    before: str                         # ISO day: the first day not counted (R9)


@dataclass(frozen=True)
class Place:
    team: TeamRef
    position: int
    shared: bool


@dataclass(frozen=True)
class MatchdayPlaces:
    matchday: int
    after: str                          # ISO day: the matchday's last result day
    places: tuple[Place, ...]           # the derived table's order after that day


@dataclass(frozen=True)
class TeamPlace:
    matchday: int
    after: str
    position: int
    shared: bool


@dataclass(frozen=True)
class TeamGoal:
    match: str                          # Match.key of the counted match
    side: Literal["for", "against"]
    minute: int | None
    added: int | None
    extra_time: bool                    # scored after the 90 minutes and their added time


@dataclass(frozen=True)
class Period:
    label: str
    goals_for: int
    goals_against: int


@dataclass(frozen=True)
class GoalPeriods:
    periods: tuple[Period, ...] | None  # None where the chart is not drawn, with the reason
    coverage: Coverage                  # "Minutes known for 41 of 44 goals."
    reason: str | None
    extra_time_for: int                 # known minutes in extra time: in no period
    extra_time_against: int


@dataclass(frozen=True)
class Margin:
    match: Match
    venue: Venue
    goals_for: int
    goals_against: int


@dataclass(frozen=True)
class Largest:
    team: str
    win: Margin | None
    defeat: Margin | None
    order: str
    before: str | None


@dataclass(frozen=True)
class DaysSince:
    team: str
    days: int | None                    # None: no earlier match is in the rows
    last: Match | None
    before: str


# ------------------------------------------------------------------ days, results, clubs


def cutoff(before: Before) -> date:
    """The Europe/Madrid day ``before`` names (R9): only matches on days before it count.

    A date is that day. An aware datetime is the Madrid date of that instant. A naive
    datetime is refused: its zone is not known, so its day is not either."""
    if isinstance(before, datetime):
        if before.tzinfo is None or before.utcoffset() is None:
            raise ValueError("before must be an aware datetime or a date")
        return from_utc(before, "CET").date()
    if isinstance(before, date):
        return before
    raise TypeError(f"before must be a datetime or a date, not {type(before).__name__}")


def day_of(match: Match) -> date | None:
    """The match's Europe/Madrid day: its kick-off's, else the date its key ends with, else
    ``None``."""
    if match.kickoff_utc:
        try:
            instant = datetime.fromisoformat(match.kickoff_utc.replace("Z", "+00:00"))
        except ValueError:
            instant = None
        if instant is not None and instant.tzinfo is not None:
            return from_utc(instant, "CET").date()
    found = _KEY_DAY.search(match.key)
    if found:
        try:
            return date.fromisoformat(found[1])
        except ValueError:
            return None
    return None


def counted(match: Match) -> bool:
    """Whether the match's result counts: FINISHED or AWARDED, both sides known, and, where it
    was decided on penalties, level."""
    home, away = match.result.home, match.result.away
    if match.status not in COUNTED or home is None or away is None:
        return False
    return not (match.duration == "PENALTY_SHOOTOUT" and home != away)


@functools.lru_cache(maxsize=8192)
def _club(team: str | TeamRef) -> TeamRef:
    """The club ``team`` names, as a ``TeamRef``: itself, or a key read by the key grammar
    (its id, and its slug as the club's name)."""
    if isinstance(team, TeamRef):
        return team
    if isinstance(team, str):
        parsed = parse(team)
        slug = parsed.slug if parsed else slugify(team)
        name = slug.replace("-", " ") or team
        return TeamRef(key=team, fd_id=parsed.fd_id if parsed else None, name=name,
                       short=name, plate="")
    raise TypeError(f"a club is a TeamRef or a key, not {type(team).__name__}")


@functools.lru_cache(maxsize=65536)
def _same(x: TeamRef, y: TeamRef) -> bool:
    return crosswalk.same_club(x, y)


def same_club(a: str | TeamRef, b: str | TeamRef) -> bool:
    """Whether ``a`` and ``b`` name one club, by ``crosswalk.same_club`` (a key read as the
    club its id and slug name)."""
    return _same(_club(a), _club(b))


def _venue(club: TeamRef, match: Match) -> Venue | None:
    home, away = _same(club, match.home), _same(club, match.away)
    if home == away:
        return None
    return "home" if home else "away"


def _goals(match: Match, venue: Venue) -> tuple[int, int]:
    home, away = match.result.home, match.result.away
    assert home is not None and away is not None  # only called on a counted match
    return (home, away) if venue == "home" else (away, home)


def _letter(goals_for: int, goals_against: int) -> Outcome:
    return "W" if goals_for > goals_against else "L" if goals_for < goals_against else "D"


def outcome(team: str | TeamRef, match: Match) -> Outcome | None:
    """W, D or L for ``team`` in ``match``; ``None`` where the result does not count or the
    club did not play in it. A match decided on penalties is a D (its level result)."""
    venue = _venue(_club(team), match)
    if venue is None or not counted(match):
        return None
    return _letter(*_goals(match, venue))


def _is_fd(match: Match) -> bool:
    return any(source.provider == FD for source in match.sources)


def _pair(x: Match, y: Match) -> bool | None:
    """``None`` where ``x`` and ``y`` are not one meeting by their clubs; else whether one
    lists the other's home club as away."""
    hx, ax, hy, ay = x.home, x.away, y.home, y.away
    if _same(hx, hy) and _same(ax, ay):
        return False
    if _same(hx, ay) and _same(ax, hy):
        return True
    return None


def _dedupe(matches: Iterable[Match]) -> tuple[list[Match], dict[str, tuple[str, bool]]]:
    """The rows with each meeting once, in the order given (a kept football-data.org row
    takes the place of the row it replaces), and each dropped key's (kept key, flipped)."""
    kept: list[Match] = []
    by_day: dict[date, list[int]] = {}
    alias: dict[str, tuple[str, bool]] = {}
    for match in matches:
        day = day_of(match)
        if day is None:
            kept.append(match)
            continue
        for index in by_day.get(day, ()):
            old = kept[index]
            flipped = _pair(old, match)
            if flipped is None:
                continue
            if _is_fd(match) and not _is_fd(old):
                kept[index] = match
                for key, (target, turned) in list(alias.items()):
                    if target == old.key:
                        alias[key] = (match.key, turned != flipped)
                if old.key != match.key:
                    alias[old.key] = (match.key, flipped)
            elif old.key != match.key:
                alias[match.key] = (old.key, flipped)
            break
        else:
            by_day.setdefault(day, []).append(len(kept))
            kept.append(match)
    return kept, alias


def dedupe(matches: Iterable[Match]) -> list[Match]:
    """``matches`` with each meeting once: rows on one Europe/Madrid day between the same two
    clubs (either way round) are one match, and the football-data.org row is kept, else the
    first given. A row with no day is kept as it is."""
    return _dedupe(matches)[0]


def _order(day: date, match: Match) -> tuple:
    return (day, match.kickoff_utc or "", match.key)


def _iso(day: date | None) -> str | None:
    return day.isoformat() if day is not None else None


def _team_key(team: str | TeamRef) -> str:
    return team.key if isinstance(team, TeamRef) else team


def _played(club: TeamRef, matches: Iterable[Match], *, last: date | None = None,
            split: Venue | None = None, competition: str | None = None
            ) -> list[tuple[date | None, Match, Venue]]:
    """The club's counted matches, deduped, by kick-off: only those on or before ``last``
    where it is given, at ``split`` and in ``competition`` where given."""
    found = []
    for match in dedupe(matches):
        if competition is not None and match.competition != competition:
            continue
        venue = _venue(club, match)
        if venue is None or not counted(match) or (split is not None and venue != split):
            continue
        day = day_of(match)
        if last is not None and (day is None or day > last):
            continue
        found.append((day, match, venue))
    return sorted(found, key=lambda item: (item[0] is None, item[0] or date.min,
                                           item[1].kickoff_utc or "", item[1].key))


def _last_day(before: Before | None) -> date | None:
    if before is None:
        return None
    return date.fromordinal(cutoff(before).toordinal() - 1)


# ------------------------------------------------------------------ tables


@dataclass
class _Tally:
    ref: TeamRef
    members: list[TeamRef]
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    letters: list[tuple[tuple, Outcome]] = field(default_factory=list)

    @property
    def points(self) -> int:
        return 3 * self.won + self.drawn

    @property
    def key(self) -> tuple[int, int, int]:
        return (self.points, self.goals_for - self.goals_against, self.goals_for)

    def add(self, goals_for: int, goals_against: int, when: tuple) -> None:
        self.played += 1
        self.goals_for += goals_for
        self.goals_against += goals_against
        letter = _letter(goals_for, goals_against)
        self.won += letter == "W"
        self.drawn += letter == "D"
        self.lost += letter == "L"
        self.letters.append((when, letter))


def _tallies(rows: Sequence[Match]) -> tuple[list[_Tally], dict[TeamRef, _Tally]]:
    """One tally per club in ``rows`` (every status), clubs joined by ``same_club``."""
    tallies: list[_Tally] = []
    of: dict[TeamRef, _Tally] = {}
    for match in rows:
        for ref in (match.home, match.away):
            if ref in of:
                continue
            found = next((t for t in tallies if any(_same(ref, m) for m in t.members)), None)
            if found is None:
                found = _Tally(ref=ref, members=[ref])
                tallies.append(found)
            else:
                found.members.append(ref)
                if found.ref.fd_id is None and ref.fd_id is not None:
                    found.ref = ref
            of[ref] = found
    return tallies, of


def _sources(matches: Iterable[Match]) -> tuple[SourceRef, ...]:
    """One reference per provider whose rows were used, in first-seen order: the latest time
    it was read and the latest stamp it gave."""
    found: dict[str, list[SourceRef]] = {}
    for match in matches:
        for source in match.sources:
            found.setdefault(source.provider, []).append(source)
    refs = []
    for provider, sources in found.items():
        checked = max((s.checked for s in sources), key=_instant_order)
        stamps = [s.revised for s in sources if s.revised]
        urls = {s.url for s in sources}
        refs.append(SourceRef(provider=provider, checked=checked,
                              revised=max(stamps, key=_instant_order) if stamps else None,
                              revision=None, url=urls.pop() if len(urls) == 1 else None))
    return tuple(refs)


def _instant_order(text: str) -> tuple:
    try:
        return (0, datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp(), text)
    except (ValueError, OverflowError):
        return (-1, 0.0, text)


def table(matches: Iterable[Match], *, view: TableView,
          after: datetime | date | str | None = None,
          before: Before | None = None, competition: str | None = None,
          stage: str | None = None) -> Table:
    """The table worked out from reported results (PR 6.4), in ``DERIVED_ORDER``.

    ``matches`` are one competition's (``competition`` names it where the rows hold others;
    ``stage`` keeps one stage, such as a league phase). Every club in the rows has a row,
    with zeros where it has no counted result yet. ``view``:

    - ``"all"``: every counted result;
    - ``"home"`` or ``"away"``: each club's home (or away) results only;
    - ``"after"``: every counted result on or before the day ``after`` (Europe/Madrid; an
      aware datetime names its Madrid day, as ``cutoff`` reads it), the day itself included.

    ``before`` (R9) keeps only results on days before its day; with ``after`` too, the
    earlier limit applies. A table with a last day reads it in ``after``, and an ``"all"``
    table with one is the ``"after"`` view. Equal points, goal difference and goals scored
    share a position (``shared``); within them clubs are listed by name. A row's ``form`` is
    its last five results in the view, oldest first. ``derived`` is ``True`` and ``order``
    is ``DERIVED_ORDER``."""
    if view not in ("all", "home", "away", "after"):
        raise ValueError(f"a table view is all, home, away or after, not {view!r}")
    rows = [m for m in matches if (competition is None or m.competition == competition)
            and (stage is None or m.stage == stage)]
    if competition is None:
        slugs = {m.competition for m in rows}
        if len(slugs) != 1:
            raise ValueError("a table is of one competition; name it")
        competition = slugs.pop()
    if isinstance(after, str):
        after = date.fromisoformat(after)
    elif isinstance(after, datetime):
        after = cutoff(after)
    limits = [day for day in (after, _last_day(before)) if day is not None]
    last = min(limits) if limits else None
    if view == "after" and last is None:
        raise ValueError("the 'after' view needs a day")
    if view == "all" and last is not None:
        view = "after"
    rows = dedupe(rows)
    tallies, of = _tallies(rows)
    used = []
    for match in rows:
        day = day_of(match)
        if not counted(match) or (last is not None and (day is None or day > last)):
            continue
        used.append(match)
        when = (day is None, day or date.min, match.kickoff_utc or "", match.key)
        home, away = _goals(match, "home")
        if view != "away":
            of[match.home].add(home, away, when)
        if view != "home":
            of[match.away].add(away, home, when)
    ordered = sorted(tallies, key=lambda t: (-t.points, -(t.goals_for - t.goals_against),
                                             -t.goals_for, fold(t.ref.name), t.ref.key))
    keys = [t.key for t in ordered]
    standing = []
    for tally in ordered:
        position = 1 + sum(k > tally.key for k in keys)
        letters = sorted(tally.letters)[-5:]
        standing.append(StandingRow(
            position=position, shared=keys.count(tally.key) > 1, team=tally.ref,
            played=tally.played, won=tally.won, drawn=tally.drawn, lost=tally.lost,
            goals_for=tally.goals_for, goals_against=tally.goals_against,
            goal_difference=tally.goals_for - tally.goals_against, points=tally.points,
            form=tuple(letter for _, letter in letters)))
    return Table(competition=competition, view=view, after=_iso(last), rows=tuple(standing),
                 order=DERIVED_ORDER, derived=True, sources=_sources(used))


def positions_by_matchday(slug: str, matches: Iterable[Match], *,
                          stage: str | None = None) -> tuple[MatchdayPlaces, ...]:
    """Each club's position after each matchday (PR 6.5), by matchday.

    A matchday's point is the derived table (``table``, view ``"after"``) on the day of its
    last counted result, over every counted result of the competition (``stage`` keeps one
    stage) on or before that day. A matchday with no counted result has no point. Only a
    league or a league phase has matchdays to chart; any other competition is refused."""
    config = BY_SLUG.get(slug)
    if config is None or config.kind not in ("league", "league_phase"):
        raise ValueError(f"positions by matchday are for a league, not {slug!r}")
    rows = dedupe(m for m in matches if m.competition == slug
                  and (stage is None or m.stage == stage))
    last: dict[int, date] = {}
    for match in rows:
        day = day_of(match)
        if counted(match) and match.matchday is not None and day is not None:
            last[match.matchday] = max(last.get(match.matchday, day), day)
    found = []
    for matchday in sorted(last):
        after = table(rows, view="after", after=last[matchday], competition=slug)
        found.append(MatchdayPlaces(
            matchday=matchday, after=last[matchday].isoformat(),
            places=tuple(Place(team=r.team, position=r.position, shared=r.shared)
                         for r in after.rows)))
    return tuple(found)


def team_places(team: str | TeamRef,
                positions: Iterable[MatchdayPlaces]) -> tuple[TeamPlace, ...]:
    """One club's line through ``positions_by_matchday``: its place at each matchday, by
    matchday; a matchday whose table does not hold the club is left out."""
    club = _club(team)
    found = []
    for point in positions:
        place = next((p for p in point.places if _same(club, p.team)), None)
        if place is not None:
            found.append(TeamPlace(matchday=point.matchday, after=point.after,
                                   position=place.position, shared=place.shared))
    return tuple(found)


# ------------------------------------------------------------------ form and records


def form(team: str | TeamRef, matches: Iterable[Match], before: Before, n: int = 5) -> Form:
    """The club's last ``n`` counted results on days before ``before``'s day (R9), across
    every competition in the rows. ``count`` is how many were found, which is fewer than
    ``n`` where the rows hold fewer: the page says so, and never pads."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n is a whole number of results, at least 1")
    first = cutoff(before)
    club = _club(team)
    found = [(day, match, venue) for day, match, venue in _played(club, matches)
             if day is not None and day < first][-n:]
    results = []
    for _, match, venue in reversed(found):
        goals_for, goals_against = _goals(match, venue)
        results.append(FormResult(match=match, venue=venue,
                                  outcome=_letter(goals_for, goals_against),
                                  goals_for=goals_for, goals_against=goals_against))
    return Form(team=_team_key(team), results=tuple(results),
                outcomes=tuple(r.outcome for r in reversed(results)), count=len(results),
                asked=n, before=first.isoformat())


def record(team: str | TeamRef, matches: Iterable[Match], split: Venue | None = None,
           competition: str | None = None, *, before: Before | None = None) -> Record:
    """The club's record over the counted results in the rows (PR 6.5's Season tab): played,
    won, drawn, lost, goals for and against, clean sheets (no goal against) and matches
    without a goal (none for). ``split`` keeps home or away matches; ``competition`` one
    competition; ``before`` (R9) the days before its day. ``matches`` lists the keys
    counted, so a test can recompute every figure from them."""
    if split not in (None, "home", "away"):
        raise ValueError(f"a split is home or away, not {split!r}")
    club = _club(team)
    last = _last_day(before)
    rows = _played(club, matches, last=last, split=split, competition=competition)
    goals = [_goals(match, venue) for _, match, venue in rows]
    return Record(
        team=_team_key(team), split=split, competition=competition, played=len(rows),
        won=sum(f > a for f, a in goals), drawn=sum(f == a for f, a in goals),
        lost=sum(f < a for f, a in goals), goals_for=sum(f for f, _ in goals),
        goals_against=sum(a for _, a in goals), clean_sheets=sum(a == 0 for _, a in goals),
        without_a_goal=sum(f == 0 for f, _ in goals),
        matches=tuple(match.key for _, match, _ in rows),
        before=cutoff(before).isoformat() if before is not None else None)


# ------------------------------------------------------------------ head-to-head


def _season_year(season: str) -> int | None:
    found = _SEASON_YEAR.match(season or "")
    return int(found[1]) if found else None


def _named(slug: str) -> str:
    config = BY_SLUG.get(slug)
    name = config.name if config else slug
    return name if slug in _NO_ARTICLE or config is None else f"the {name}"


def _listing(names: Sequence[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _provider(match: Match) -> str | None:
    return match.sources[0].provider if match.sources else None


def _span(team: TeamRef, opponent: TeamRef,
          rows: Sequence[Match]) -> tuple[str, str | None, tuple[str, ...]]:
    """The span line, the earliest season in it, and the providers it names.

    The span is each (source, competition) whose rows hold a match of each club, from the
    earliest season of that source's rows of that competition."""
    seen: dict[tuple[str, str], list[bool]] = {}
    earliest: dict[tuple[str, str], tuple[int, str]] = {}
    for match in rows:
        provider = _provider(match)
        year = _season_year(match.season)
        if provider is None or year is None:
            continue
        pair = (provider, match.competition)
        has = seen.setdefault(pair, [False, False])
        has[0] = has[0] or _venue(team, match) is not None
        has[1] = has[1] or _venue(opponent, match) is not None
        if pair not in earliest or year < earliest[pair][0]:
            earliest[pair] = (year, match.season)
    pairs = [pair for pair, has in seen.items() if all(has)]
    if not pairs:
        return ("The free sources this site reads hold no competition with both clubs in it.",
                None, ())
    by_provider: dict[str, dict[tuple[int, str], list[str]]] = {}
    for provider, slug in pairs:
        by_provider.setdefault(provider, {}).setdefault(earliest[(provider, slug)],
                                                        []).append(slug)

    def _rank(slug: str) -> tuple:
        config = BY_SLUG.get(slug)
        return (config.order if config else len(BY_SLUG) + 1, slug)

    providers = sorted(by_provider, key=lambda p: (min(by_provider[p])[0],
                                                   _SOURCE_NAMES.get(p, p), p))
    phrases = []
    for provider in providers:
        groups = sorted(by_provider[provider].items())
        parts = [f"in {_listing([_named(s) for s in sorted(slugs, key=_rank)])} since {season}"
                 for (_, season), slugs in groups]
        name = _SOURCE_NAMES.get(provider, "another source")
        phrases.append(f"{' and '.join(parts)} ({name})")
    line = "Meetings " + ", and ".join(phrases) + "."
    first = min(earliest[pair] for pair in pairs)[1]
    return line, first, tuple(providers)


def h2h(a: str | TeamRef, b: str | TeamRef, matches: Iterable[Match], before: Before) -> H2H:
    """The meetings of ``a`` and ``b`` on days before ``before``'s day (R9), from the match
    lists only: football-data.org's ``aggregates`` are never read (DC 1.2 found them wrong),
    and the model carries none. Rows of one meeting from two sources are one meeting, the
    football-data.org row first (``dedupe``). ``wins`` and ``losses`` are ``a``'s; a match
    decided on penalties is a draw.

    ``span`` says where meetings were looked for: each source and competition whose rows
    hold both clubs, from its earliest season ("Meetings in La Liga since 2010/11
    (OpenFootball), and in La Liga and the Champions League since 2023/24
    (football-data.org)."). With no meeting, ``empty`` says so for that span."""
    team, opponent = _club(a), _club(b)
    if _same(team, opponent):
        raise ValueError("a head-to-head is of two clubs")
    first = cutoff(before)
    rows = dedupe(matches)
    meetings = []
    for match in rows:
        venue, other = _venue(team, match), _venue(opponent, match)
        day = day_of(match)
        if (venue is None or other is None or venue == other or not counted(match)
                or day is None or day >= first):
            continue
        meetings.append((_order(day, match), match, _letter(*_goals(match, venue))))
    meetings.sort(key=lambda item: item[0], reverse=True)
    span, earliest, providers = _span(team, opponent, rows)
    letters = [letter for *_, letter in meetings]
    empty = None
    if not meetings:
        empty = (f"No meeting in the free sources since {earliest}." if earliest
                 else "No meeting in the free sources this site reads.")
    return H2H(team=_team_key(a), opponent=_team_key(b), meetings=len(meetings),
               wins=letters.count("W"), draws=letters.count("D"), losses=letters.count("L"),
               matches=tuple(match for _, match, _ in meetings), span=span, empty=empty,
               providers=providers, before=first.isoformat())


# ------------------------------------------------------------------ goal periods


def _plural(n: int, one: str) -> str:
    return f"{n} {one}" if n == 1 else f"{n} {one}s"


def team_goals(team: str | TeamRef, matches: Iterable[Match], events: Iterable[GoalEvent],
               *, before: Before | None = None, competition: str | None = None
               ) -> tuple[tuple[TeamGoal, ...], Coverage]:
    """The club's goals for and against in its counted matches, with how many have a minute.

    ``events`` are ``GoalEvent``s; each joins its match by key (a row ``dedupe`` dropped, or a
    legacy key, joins the row kept). An event's ``side`` is the side the goal counts for, as
    the result does (an own goal counts for the other club). Where two sources report one
    match's goals, the report that agrees with the result and gives most minutes is used; a
    report listing more goals for a side than the result is not used, and those goals count
    as not known. ``extra_time`` marks a minute past 90 without added time in a match that
    can have gone to extra time (``_extra_time_possible``); in any other match such a minute
    is added time, in the last period (OpenLigaDB writes 90+3 as minute 93).

    The coverage counts every goal of the counted matches by their results (``of``) and
    those whose minute is known (``known``): "Minutes known for 41 of 44 goals."."""
    club = _club(team)
    rows = list(matches)
    kept, alias = _dedupe(rows)
    for match in kept:
        for legacy in match.legacy_keys:
            alias.setdefault(legacy, (match.key, False))
    played = {match.key: (match, venue) for _, match, venue in
              _played(club, kept, last=_last_day(before), competition=competition)}
    reports: dict[str, dict[tuple, list]] = {}
    for event in events:
        target, flipped = alias.get(event.match, (event.match, False))
        if target not in played:
            continue
        side = event.side if not flipped else ("away" if event.side == "home" else "home")
        source = event.sources[0].provider if event.sources else None
        reports.setdefault(target, {}).setdefault((event.match, source), []).append(
            (side, event))
    goals: list[TeamGoal] = []
    of = known = 0
    for key, (match, venue) in played.items():
        home, away = _goals(match, "home")
        of += home + away
        usable = [listed for listed in reports.get(key, {}).values()
                  if sum(side == "home" for side, _ in listed) <= home
                  and sum(side == "away" for side, _ in listed) <= away]
        if not usable:
            continue
        chosen = max(usable, key=lambda listed: sum(e.minute is not None for _, e in listed))
        for side, event in chosen:
            extra = (event.minute is not None and event.minute > 90 and event.added is None
                     and _extra_time_possible(match))
            goals.append(TeamGoal(match=key, side="for" if side == venue else "against",
                                  minute=event.minute, added=event.added, extra_time=extra))
            known += event.minute is not None
    line = f"Minutes known for {known} of {_plural(of, 'goal')}."
    return tuple(goals), Coverage(what="goal minutes", known=known, of=of, line=line)


def _extra_time_possible(match: Match) -> bool:
    """Whether ``match`` can have gone to extra time: where the source states its length,
    exactly where that length is extra time or a shoot-out; where it does not (OpenLigaDB,
    OpenFootball), unless the match is a league's, a league phase's or a group's."""
    if match.duration is not None:
        return match.duration != "REGULAR"
    config = BY_SLUG.get(match.competition)
    if config is not None and config.kind == "league":
        return False
    return match.stage not in _NO_EXTRA_TIME_STAGES


def _period(minute: int) -> int:
    for n, (_, first, last) in enumerate(PERIODS):
        if first <= minute <= last:
            return n
    return len(PERIODS) - 1  # past 90 in a match of regular length: added time


def goal_periods(events: Sequence[TeamGoal], coverage: Coverage) -> GoalPeriods:
    """Goals for and against in the six periods of ``PERIODS``, from ``team_goals``.

    The chart is drawn only where minutes are known for at least 80 % of the goals
    (``THRESHOLD``); otherwise ``periods`` is ``None`` and ``reason`` is the line that says
    why. Goals in extra time have a known minute and no period: they are counted apart.
    ``coverage`` must be the one ``team_goals`` gave with these events."""
    timed = [e for e in events if e.minute is not None]
    if len(timed) != coverage.known:
        raise ValueError("the coverage is not of these goals")
    extra_for = sum(e.extra_time and e.side == "for" for e in timed)
    extra_against = sum(e.extra_time and e.side == "against" for e in timed)
    if coverage.of == 0:
        return GoalPeriods(periods=None, coverage=coverage, extra_time_for=0,
                           extra_time_against=0,
                           reason="The chart isn’t drawn: no goal is reported in these "
                                  "matches.")
    if coverage.known * THRESHOLD[1] < coverage.of * THRESHOLD[0]:
        return GoalPeriods(periods=None, coverage=coverage, extra_time_for=extra_for,
                           extra_time_against=extra_against,
                           reason=(f"The chart isn’t drawn: minutes are known for "
                                   f"{coverage.known} of {_plural(coverage.of, 'goal')}, "
                                   "under 80%."))
    counts = [[0, 0] for _ in PERIODS]
    for event in timed:
        if not event.extra_time:
            counts[_period(event.minute)][event.side == "against"] += 1
    return GoalPeriods(
        periods=tuple(Period(label=label, goals_for=counts[n][0], goals_against=counts[n][1])
                      for n, (label, _, _) in enumerate(PERIODS)),
        coverage=coverage, reason=None, extra_time_for=extra_for,
        extra_time_against=extra_against)


# ------------------------------------------------------------------ largest, days since


def largest(team: str | TeamRef, matches: Iterable[Match], *, before: Before | None = None,
            competition: str | None = None) -> Largest:
    """The club's largest win and largest defeat in the rows, in ``LARGEST_ORDER``: by
    margin, then goals scored, then the earlier date. ``None`` where the rows hold no win (or
    no defeat). ``before`` (R9) keeps the days before its day."""
    club = _club(team)
    rows = _played(club, matches, last=_last_day(before), competition=competition)
    wins, defeats = [], []
    for day, match, venue in rows:
        goals_for, goals_against = _goals(match, venue)
        margin = Margin(match=match, venue=venue, goals_for=goals_for,
                        goals_against=goals_against)
        when = (day is None, day or date.min, match.kickoff_utc or "", match.key)
        if goals_for > goals_against:
            wins.append(((goals_against - goals_for, -goals_for, when), margin))
        elif goals_for < goals_against:
            defeats.append(((goals_for - goals_against, -goals_for, when), margin))
    return Largest(team=_team_key(team), win=min(wins, key=lambda w: w[0])[1] if wins else None,
                   defeat=min(defeats, key=lambda d: d[0])[1] if defeats else None,
                   order=LARGEST_ORDER,
                   before=cutoff(before).isoformat() if before is not None else None)


def days_since(team: str | TeamRef, matches: Iterable[Match], before: Before) -> DaysSince:
    """Calendar days from the club's last match played (FINISHED) on a day before
    ``before``'s day (R9) to that day. An awarded match is not one played. ``days`` is
    ``None`` where the rows hold no earlier match: missing, never 0."""
    first = cutoff(before)
    club = _club(team)
    last: tuple | None = None
    for match in dedupe(matches):
        day = day_of(match)
        if (match.status != _PLAYED or day is None or day >= first
                or _venue(club, match) is None):
            continue
        if last is None or _order(day, match) > last[0]:
            last = (_order(day, match), day, match)
    return DaysSince(team=_team_key(team), days=(first - last[1]).days if last else None,
                     last=last[2] if last else None, before=first.isoformat())
