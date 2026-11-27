"""Who appeared in each Real Madrid match, from the season article's revision history (REC 1.3).

The article's squad statistics table is a running count, updated after every match. The
snapshot after match k less the snapshot before it, in the column of match k's competition,
is 1 for a player who appeared in it and 0 for one who did not. Revision content is
CC BY-SA, like the article, and is read through the MediaWiki API (B13), never scraped.

**Pairing (declared).** The table carries its own stamp, ``{{Fb cs footer|u=<day>}}``. The
snapshot after match k is the earliest revision read whose stamp is match k's day (and that is
later than the snapshot after match k−1, and not before match k's kick-off). The snapshot
before match k is the one after match k−1; before the season's first match it is the last
revision before its kick-off, and a row that revision does not have counts 0 there (a season
count before the season's first match is 0). A match whose day no revision's stamp names is
read with the next match that has one (a *span*: editors updated both in one edit).

**Changes (declared, per competition column; n is the span's matches in that column).**

- n = 1: a change of 1 is *appeared*, 0 is *did not appear*; 2 or more, or a negative change,
  is *not attributable*, and the whole change stays in his season count as units not
  attributable to a match (Espí's two after Elche).
- n ≥ 2 (the missing-stamp rule): 0 is *did not appear* in any; n is *appeared* in each; any
  other change is *not attributable* for each, the change kept as unattributed units. For n =
  2 this is REC 1.3's rule exactly: 0 neither, 2 both, 1 both "not attributable".
- A row the snapshot after has and the snapshot before does not (outside the season's first
  match), or a cell that could not be read, is *not attributable*.

**The match check.** A match with fewer than 11 or more than 16 changes of exactly 1 (11
starters and at most five substitutes) is not attributable as a whole: every change across it
becomes unattributed units, until a later revision with the same stamp repairs it (a later
revision read is tried before the match is given up). In a span of n ≥ 2 matches of one
competition the count per match is not known; the span is given up when more than 16 players
appeared in each or fewer than 11 changed at all.

**Integrity.** Each player's appearances attributed to matches, plus his unattributed units,
plus his count before the season's first match, equal his season count in the article
(``reconcile``); a player who appeared in a match football-data.org does not name him for is
a source conflict (``conflicts``): neither source is taken over the other.

**What is read.** One revision list (``rvlimit=50`` a page, newest first, back to the season's
start; later refreshes ask only for revisions newer than those listed), then the content of the
revisions the pairing needs (``plan``: the last revision before the season's first kick-off,
and for each match the last revision before the next one's), at most 50 a request. Content is
kept by revision id for the life of the process: a revision never changes. Only the derived
rows are kept.

Non-claim: an appearance is a change in a community-entered count, not an observation of the
match; nothing here says who started, for how long, or why. Orders: matches by kick-off;
players as the snapshot after lists them; units by player in that order, then competition.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from ...providers import assert_may_host
from ..feed import FeedCache, FeedError
from ..kickoff import from_utc
from ..studio import AGENT, API, MAXLAG, RAW
from .model import Appearance, AppearanceState, Match, Named, PersonRef, SeasonLine, SourceRef
from .wiki_season import PROVIDER, efs_rows, gather_limited, person_key, stamps

__all__ = [
    "MIN_APPEARED", "MAX_APPEARED", "PENDING", "Fixture", "RevisionStub", "Snap", "Span",
    "MatchCheck", "Unattributed", "Mismatch", "Conflict", "Grid", "fixture", "listing",
    "snapshot_of", "plan", "pair", "attribute", "reconcile", "conflicts", "Revisions",
]

MIN_APPEARED, MAX_APPEARED = 11, 16
"""A match's changes of exactly 1: eleven starters, and at most five substitutes."""
PENDING = "Wikipedia’s tables haven’t been updated for this match yet."
BATCH = 50
"""Revisions whose content one request may ask for (MediaWiki's limit)."""


@dataclass(frozen=True)
class Fixture:
    """A finished Madrid match, as the pairing needs it."""

    key: str
    competition: str
    day: str                 # its Europe/Madrid day, the day a stamp names
    kickoff_utc: str | None
    label: str               # "Real Madrid v A FC"


@dataclass(frozen=True)
class RevisionStub:
    revid: int
    timestamp: str           # ISO UTC, as MediaWiki writes it


@dataclass(frozen=True)
class Snap:
    """One revision's statistics table: each article's appearances per competition."""

    revid: int
    timestamp: str
    stamp: str | None                            # the table's {{Fb cs footer|u=}} day
    rows: dict[str, dict[str, int | None]]       # title -> competition slug -> count
    names: dict[str, str]                        # title -> the row's name, in table order


@dataclass(frozen=True)
class Span:
    """The matches between two snapshots: one, or several where a stamp is missing."""

    fixtures: tuple[Fixture, ...]
    before: Snap | None      # None: the zero count before the season's first match
    after: Snap | None       # None: the tables have not been updated for these yet


@dataclass(frozen=True)
class MatchCheck:
    match: str
    competition: str
    day: str
    appeared: int            # changes of exactly 1 attributed to it
    attributable: bool
    before: int | None       # revision ids of the pair
    after: int | None
    line: str | None         # why it is not attributable


@dataclass(frozen=True)
class Unattributed:
    """Units of a player's season count not attributable to a match (may be negative)."""

    person: PersonRef
    competition: str
    units: int
    matches: tuple[str, ...]


@dataclass(frozen=True)
class Mismatch:
    person: PersonRef
    competition: str
    attributed: int
    unattributed: int
    before_season: int
    listed: int | None
    line: str


@dataclass(frozen=True)
class Conflict:
    person: PersonRef
    match: str
    line: str


@dataclass(frozen=True)
class Grid:
    appearances: tuple[Appearance, ...]
    checks: tuple[MatchCheck, ...]
    unattributed: tuple[Unattributed, ...]
    first: dict[str, dict[str, int]]   # title -> competition -> count before the first match


# ------------------------------------------------------------------ reading replies


def fixture(match: Match) -> Fixture:
    """A finished match as the pairing reads it: its Europe/Madrid day from its kick-off, or
    the day its key ends with."""
    day = match.key[-10:]
    if match.kickoff_utc:
        instant = datetime.fromisoformat(match.kickoff_utc.replace("Z", "+00:00"))
        day = from_utc(instant, "CET").date().isoformat()
    return Fixture(match.key, match.competition, day, match.kickoff_utc,
                   f"{match.home.short} v {match.away.short}")


def listing(payload: object) -> tuple[list[RevisionStub], str | None]:
    """A ``prop=revisions&rvprop=ids|timestamp`` page: its revisions, and the ``rvcontinue``
    of the next page (``None`` on the last)."""
    if not isinstance(payload, dict) or "error" in payload:
        raise FeedError("Wikipedia’s revision list couldn’t be read.")
    found = []
    for page in (payload.get("query") or {}).get("pages") or []:
        for revision in (page.get("revisions") or []) if isinstance(page, dict) else []:
            revid, stamp = revision.get("revid"), revision.get("timestamp")
            if isinstance(revid, int) and isinstance(stamp, str):
                found.append(RevisionStub(revid, stamp))
    more = (payload.get("continue") or {}).get("rvcontinue")
    return found, more if isinstance(more, str) else None


def snapshot_of(revid: int, timestamp: str, wikitext: str) -> Snap:
    """A revision's statistics table and stamp (``wiki_season``'s parsers)."""
    table = efs_rows(wikitext)
    rows = {row.title: {key.split(":", 1)[1]: count for key, count in row.counts.items()
                        if key.startswith("apps:")} for row in table.rows}
    names = {row.title: row.name for row in table.rows}
    return Snap(revid, timestamp, stamps(wikitext, revid, timestamp).statistics, rows, names)


def _contents(payload: object) -> dict[int, tuple[str, str]]:
    if not isinstance(payload, dict) or "error" in payload:
        raise FeedError("Wikipedia’s revisions couldn’t be read.")
    found = {}
    for page in (payload.get("query") or {}).get("pages") or []:
        for revision in (page.get("revisions") or []) if isinstance(page, dict) else []:
            content = ((revision.get("slots") or {}).get("main") or {}).get("content")
            if (isinstance(revision.get("revid"), int) and isinstance(content, str)
                    and isinstance(revision.get("timestamp"), str)):
                found[revision["revid"]] = (revision["timestamp"], content)
    return found


# ------------------------------------------------------------------ the rules (pure)


def _start(fx: Fixture) -> str:
    """The instant a revision must be at or after to follow ``fx``: its kick-off, else the
    start of its day."""
    return fx.kickoff_utc or f"{fx.day}T00:00:00Z"


def plan(stubs: Sequence[RevisionStub], fixtures: Sequence[Fixture],
         upcoming: str | None = None) -> list[int]:
    """The revisions whose content the pairing reads: the last before the first kick-off, and
    for each match the last before the next match's kick-off (``upcoming`` after the last;
    the newest revision without one). Oldest first, each once."""
    ordered = sorted(stubs, key=lambda s: (s.timestamp, s.revid))
    if not fixtures or not ordered:
        return []
    starts = [_start(fx) for fx in fixtures] + [upcoming]
    wanted = []
    for n, limit in enumerate(starts):
        floor = starts[n - 1] if n else None
        inside = [s for s in ordered if (limit is None or s.timestamp < limit)
                  and (floor is None or s.timestamp >= floor)]
        if inside:
            wanted.append(inside[-1].revid)
    return list(dict.fromkeys(wanted))


def pair(fixtures: Sequence[Fixture], snaps: Iterable[Snap]) -> list[Span]:
    """The spans of ``fixtures`` (in kick-off order) by the declared pairing rule. A span's
    ``after`` is the earliest snapshot whose stamp names its last match; ``attribute`` may
    move it to a later one with the same stamp that repairs the match check."""
    ordered = sorted(snaps, key=lambda s: (s.timestamp, s.revid))
    if not fixtures:
        return []
    baseline = [s for s in ordered if s.timestamp < _start(fixtures[0])]
    before = baseline[-1] if baseline else None
    spans, waiting = [], []
    for fx in fixtures:
        waiting.append(fx)
        after = next((s for s in ordered if s.stamp == fx.day and s.timestamp >= _start(fx)
                      and (before is None or s.timestamp > before.timestamp)), None)
        if after is None:
            continue
        spans.append(Span(tuple(waiting), before, after))
        before, waiting = after, []
    if waiting:
        spans.append(Span(tuple(waiting), before, None))
    return spans


def _source(snap: Snap, checked: str) -> SourceRef:
    return SourceRef(provider=PROVIDER, checked=checked, revised=snap.timestamp,
                     revision=snap.revid,
                     url=f"https://en.wikipedia.org/wiki/Special:PermanentLink/{snap.revid}")


@dataclass
class _Read:
    states: dict[tuple[str, str], AppearanceState]   # (title, match key) -> state
    units: dict[tuple[str, str], tuple[int, tuple[str, ...]]]  # (title, comp) -> units
    checks: list[MatchCheck]
    ok: bool


def _read_span(span: Span, after: Snap, first: bool) -> _Read:
    states: dict[tuple[str, str], AppearanceState] = {}
    units: dict[tuple[str, str], tuple[int, tuple[str, ...]]] = {}
    checks: list[MatchCheck] = []
    ok = True
    before = span.before
    by_comp: dict[str, list[Fixture]] = {}
    for fx in span.fixtures:
        by_comp.setdefault(fx.competition, []).append(fx)
    for competition, group in by_comp.items():
        n = len(group)
        keys = tuple(fx.key for fx in group)
        changes: dict[str, int | None] = {}
        for title, counts in after.rows.items():
            a = counts.get(competition)
            if before is not None and title in before.rows:
                b = before.rows[title].get(competition)
            else:
                b = 0 if first else None
            changes[title] = a - b if a is not None and b is not None else None
        exact = [t for t, d in changes.items() if d == n]
        moved = [t for t, d in changes.items() if d is not None and d > 0]
        if n == 1:
            good = MIN_APPEARED <= len(exact) <= MAX_APPEARED
            line = None if good else (
                f"Wikipedia’s appearance table changes by one for {len(exact)} "
                f"{'player' if len(exact) == 1 else 'players'} across this match, outside the "
                f"{MIN_APPEARED} to {MAX_APPEARED} a match can have; no appearance is "
                "attributed to it until a later revision repairs it.")
        else:
            good = len(exact) <= MAX_APPEARED and len(moved) >= MIN_APPEARED
            line = None if good else (
                f"Wikipedia’s tables were updated for {n} matches in one edit and the changes "
                "don’t settle who appeared in which; no appearance is attributed to them.")
        ok = ok and good
        for title, d in changes.items():
            if not good:
                state: AppearanceState = "not_attributable"
            elif d == 0:
                state = "did_not_appear"
            elif d == n:
                state = "appeared"
            else:
                state = "not_attributable"
            for key in keys:
                states[(title, key)] = state
            if d is not None and d != 0 and state == "not_attributable":
                held, where = units.get((title, competition), (0, ()))
                units[(title, competition)] = (held + d, where + keys)
        for fx in group:
            if n > 1 and good:
                line = (f"Wikipedia’s tables were updated for {n} matches in one edit; an "
                        "appearance is attributed only where the change settles it.")
            checks.append(MatchCheck(fx.key, competition, fx.day,
                                     len(exact) if good else 0, good,
                                     before.revid if before else None, after.revid, line))
    return _Read(states, units, checks, ok)


def attribute(spans: Sequence[Span], snaps: Iterable[Snap], *, checked: str,
              refs: Mapping[str, PersonRef] | None = None) -> Grid:
    """Each player's state in each match by the declared rules, each match's check, and each
    player's units not attributable to a match. ``refs`` names players by article title (the
    squad list's names); a player it does not name is named as the table writes him."""
    refs = refs or {}
    later = sorted(snaps, key=lambda s: (s.timestamp, s.revid))
    appearances: list[Appearance] = []
    checks: list[MatchCheck] = []
    units: dict[tuple[str, str], tuple[int, tuple[str, ...]]] = {}
    names: dict[str, str] = {}
    first: dict[str, dict[str, int]] = {}
    previous: Snap | None = None
    for n, span in enumerate(spans):
        before = previous if n else span.before
        if n == 0 and before is not None:
            first = {t: {c: v for c, v in row.items() if v is not None}
                     for t, row in before.rows.items()}
        span = Span(span.fixtures, before, span.after)
        if span.after is None:
            last = previous or span.before
            for fx in span.fixtures:
                checks.append(MatchCheck(fx.key, fx.competition, fx.day, 0, False,
                                         last.revid if last else None, None, PENDING))
                for title in (last.rows if last else {}):
                    names.setdefault(title, last.names.get(title, title))
                    appearances.append(_appearance(title, fx.key, "not_attributable",
                                                   (last,), checked, refs, names))
            continue
        day = span.fixtures[-1].day
        candidates = [s for s in later if s.stamp == day and s.timestamp >= span.after.timestamp]
        read = None
        for candidate in candidates or [span.after]:
            read = _read_span(span, candidate, first=n == 0)
            if read.ok:
                chosen = candidate
                break
        else:
            chosen = span.after
            read = _read_span(span, chosen, first=n == 0)
        for title in chosen.rows:
            names.setdefault(title, chosen.names.get(title, title))
        pair_sources = tuple(s for s in (before, chosen) if s is not None)
        for fx in span.fixtures:
            for title in chosen.rows:
                state = read.states.get((title, fx.key))
                if state is not None:
                    appearances.append(_appearance(title, fx.key, state, pair_sources,
                                                   checked, refs, names))
        checks += read.checks
        for key, (count, where) in read.units.items():
            held, places = units.get(key, (0, ()))
            units[key] = (held + count, places + where)
        previous = chosen
    order = {title: n for n, title in enumerate(names)}
    unattributed = tuple(
        Unattributed(_ref(title, refs, names), competition, count, where)
        for (title, competition), (count, where) in sorted(
            units.items(), key=lambda item: (order.get(item[0][0], len(order)), item[0][1])))
    return Grid(tuple(appearances), tuple(checks), unattributed, first)


def _ref(title: str, refs: Mapping[str, PersonRef], names: Mapping[str, str]) -> PersonRef:
    return refs.get(title) or PersonRef(key=person_key(title), name=names.get(title, title))


def _appearance(title: str, match: str, state: AppearanceState, pair_: Sequence[Snap],
                checked: str, refs: Mapping[str, PersonRef],
                names: Mapping[str, str]) -> Appearance:
    return Appearance(person=_ref(title, refs, names), match=match, state=state,
                      sources=tuple(_source(s, checked) for s in pair_))


def reconcile(grid: Grid, lines: Iterable[SeasonLine], fixtures: Sequence[Fixture],
              titles: Mapping[str, str]) -> tuple[Mismatch, ...]:
    """Each player's attributed appearances, unattributed units and count before the
    season's first match against his season count in the article (``lines``), per
    competition; a line where they don't add up. ``titles`` maps a person key to his
    article title. A count the article holds for a match whose stamp it has not yet written
    shows here as a line, until the stamp catches up."""
    competition = {fx.key: fx.competition for fx in fixtures}
    attributed: dict[tuple[str, str], int] = {}
    for row in grid.appearances:
        if row.state == "appeared":
            key = (row.person.key, competition.get(row.match, ""))
            attributed[key] = attributed.get(key, 0) + 1
    units = {(u.person.key, u.competition): u.units for u in grid.unattributed}
    found = []
    for line in lines:
        title = titles.get(line.person.key)
        first = grid.first.get(title or "", {}).get(line.competition, 0)
        a = attributed.get((line.person.key, line.competition), 0)
        u = units.get((line.person.key, line.competition), 0)
        if line.appearances is not None and a + u + first == line.appearances:
            continue
        if line.appearances is None and a == 0 and u == 0:
            continue
        listed = "no count" if line.appearances is None else str(line.appearances)
        found.append(Mismatch(
            person=line.person, competition=line.competition, attributed=a, unattributed=u,
            before_season=first, listed=line.appearances,
            line=(f"{line.person.name}: {a} {'appearance' if a == 1 else 'appearances'} "
                  f"attributed to matches and {u} not attributable add up to {a + u + first}; "
                  f"Wikipedia’s season table lists {listed}.")))
    return tuple(found)


def conflicts(appearances: Iterable[Appearance], named: Iterable[Named], *,
              persons: Iterable[str], matches: Iterable[str],
              labels: Mapping[str, str] | None = None) -> tuple[Conflict, ...]:
    """Players who appeared (Wikipedia) in a match football-data.org's list does not name them
    for, among the ``persons`` whose named lists were read and the ``matches`` those lists
    cover. Person and match keys are the caller's (the catalogue joins the two sources)."""
    named_pairs = {(n.person.key, n.match) for n in named}
    persons, matches = set(persons), set(matches)
    labels = labels or {}
    found = []
    for row in appearances:
        if (row.state == "appeared" and row.person.key in persons and row.match in matches
                and (row.person.key, row.match) not in named_pairs):
            where = labels.get(row.match, "this match")
            found.append(Conflict(row.person, row.match, (
                f"Wikipedia’s appearance table has {row.person.name} appearing in {where}, "
                "and football-data.org’s matchday squad for it doesn’t name him; neither "
                "source is taken over the other.")))
    return tuple(found)


# ------------------------------------------------------------------ the service


class Revisions:
    """The revision list and the revisions' tables, read through the MediaWiki API."""

    LIST_TTL = 30 * 60
    MAX_PAGES = 30
    KEEP = 4000
    """Revisions whose derived rows the process keeps (a season is a few hundred)."""

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None,
                 clock=lambda: datetime.now(UTC)) -> None:
        self._transport = transport
        self._clock = clock
        self.cache = FeedCache(8)
        self._known: dict[str, list[RevisionStub]] = {}
        self._snaps: dict[int, Snap] = {}
        self.content_requests = 0

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=AGENT, timeout=12, transport=self._transport)

    async def stubs(self, title: str, since: str) -> list[RevisionStub]:
        """The article's revisions back to ``since`` (ISO UTC), newest first; a refresh asks
        only for revisions newer than those already listed."""
        assert_may_host(PROVIDER)

        async def fetch() -> list:
            known = self._known.get(title, [])
            end = known[0].timestamp if known else since
            found: list[RevisionStub] = []
            more: str | None = None
            async with self._client() as client:
                for _ in range(self.MAX_PAGES):
                    params = {"action": "query", "prop": "revisions", "titles": title,
                              "rvprop": "ids|timestamp", "rvlimit": str(BATCH), "rvend": end,
                              "format": "json", "formatversion": "2", "maxlag": MAXLAG}
                    if more:
                        params["rvcontinue"] = more
                    response = await client.get(API, params=params)
                    response.raise_for_status()
                    page, more = listing(response.json())
                    found += page
                    if more is None:
                        break
            merged = {s.revid: s for s in known + found}
            ordered = sorted(merged.values(), key=lambda s: (s.timestamp, s.revid), reverse=True)
            self._known[title] = ordered
            return [{"revid": s.revid, "timestamp": s.timestamp} for s in ordered]

        snap = await self.cache.get(f"list/{title}", self.LIST_TTL, fetch)
        return [RevisionStub(row["revid"], row["timestamp"]) for row in snap.rows]

    async def snapshots(self, title: str, wanted: Sequence[RevisionStub]) -> list[Snap]:
        """The tables of ``wanted`` revisions, each read once for the process's life: at most
        50 a request; where ``api.php`` turns a request away, each revision's wikitext through
        ``index.php?action=raw``, a few at a time."""
        assert_may_host(PROVIDER)
        missing = [s for s in wanted if s.revid not in self._snaps]
        stamp = {s.revid: s.timestamp for s in wanted}
        async with self._client() as client:
            for start in range(0, len(missing), BATCH):
                batch = missing[start:start + BATCH]
                params = {"action": "query", "prop": "revisions",
                          "revids": "|".join(str(s.revid) for s in batch),
                          "rvprop": "ids|timestamp|content", "rvslots": "main",
                          "format": "json", "formatversion": "2", "maxlag": MAXLAG}
                self.content_requests += 1
                try:
                    response = await client.get(API, params=params)
                    response.raise_for_status()
                    contents = _contents(response.json())
                except (httpx.HTTPError, ValueError, FeedError):
                    contents = await self._raw(client, title, batch)
                for revid, (timestamp, text) in contents.items():
                    self._keep(snapshot_of(revid, stamp.get(revid, timestamp), text))
        return [self._snaps[s.revid] for s in wanted if s.revid in self._snaps]

    async def _raw(self, client: httpx.AsyncClient, title: str,
                   batch: Sequence[RevisionStub]) -> dict[int, tuple[str, str]]:
        async def one(stub: RevisionStub) -> tuple[RevisionStub, str | None]:
            try:
                response = await client.get(RAW, params={"title": title, "oldid": str(stub.revid),
                                                         "action": "raw"})
                response.raise_for_status()
            except httpx.HTTPError:
                return stub, None
            return stub, response.text

        found = await gather_limited([one(stub) for stub in batch])
        return {stub.revid: (stub.timestamp, text) for stub, text in found if text is not None}

    def _keep(self, snap: Snap) -> None:
        if len(self._snaps) >= self.KEEP:
            self._snaps.pop(next(iter(self._snaps)))
        self._snaps[snap.revid] = snap

    async def grid(self, title: str, matches: Sequence[Match], *,
                   upcoming: str | None = None, since: str,
                   refs: Mapping[str, PersonRef] | None = None) -> tuple[Grid, list[Span]]:
        """Madrid's finished ``matches`` (any order) paired and read: the grid and the spans.
        ``since`` bounds the revision list (the season's first day); ``upcoming`` is the
        next match's kick-off, so the last finished match's snapshot is the newest revision
        before it."""
        fixtures = [fixture(m) for m in sorted(
            (m for m in matches if m.status == "FINISHED"),
            key=lambda m: (m.kickoff_utc or m.key[-10:] + "T99", m.key))]
        stubs = await self.stubs(title, since)
        wanted_ids = set(plan(stubs, fixtures, upcoming))
        snaps = await self.snapshots(title, [s for s in reversed(stubs)
                                             if s.revid in wanted_ids])
        spans = pair(fixtures, snaps)
        checked = self._clock().astimezone(UTC).isoformat()
        return attribute(spans, snaps, checked=checked, refs=refs), spans
