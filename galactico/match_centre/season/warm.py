"""The warming plan: what one run of ``/api/season/warm`` reads, and in what order (PLAN D4-A,
PLATFORM 3.9).

A scheduled run (every 15 minutes) keeps the football-data.org resources the busiest pages
read in the server caches (tiers three and four), so that a reader rarely meets a cold one and
a deployment does not start every page cold. A run spends at most ``WARM_REQUESTS`` (four)
requests at priority 2, which spends only while more than four of the key's minute are left
(``budget.RESERVES``: readers keep the rest), and then at most ``SEARCH_REQUESTS`` (one) at
priority 3 for the search index. A resource still fresh in a cache costs nothing: the client
answers it without a request. So the plan lists every resource the run would have fresh, in
this order, and the run reads down it until its requests are spent:

1. the today resource (the day view's one request, B3);
2. Real Madrid's competitions' season matches and standings;
3. their clubs and squads;
4. every competition whose version moved (a finish seen today): its season matches,
   standings and scorers;
5. Real Madrid's players' lists of matches they were named for, a different player first in
   each 15-minute slot (round robin);
6. Real Madrid's competitions' earlier seasons, which the head-to-head reads;
7. at priority 3, the clubs and squads of one competition the search index lacks: the first,
   in the fixed order, that no cache holds.

Each read is the catalogue's own (the same resource, parameters and version as
``catalog.Catalog`` asks for), so what a run keeps is what the pages ask for. After the today
resource, the catalogue is shown it (``Catalog.day``, which can then make no request), so the
finishes it lists move their competitions' versions, and the rest of the plan is made again:
step 4 sees this run's finishes.

Nothing is read without a key, or once football-data.org refuses it; nothing is written but
the ephemeral caches; the run's reply (``Run.to_json``) is counts only.

Claim: a run makes at most ``WARM_REQUESTS + SEARCH_REQUESTS`` football-data.org requests,
only at priorities 2 and 3 (never a reader's 0 or 1), and none for a resource a cache holds
fresh. Non-claim: a run does not make the pages fresh by itself; a reader's cold view still
reads within its own cap (PLAN 3.6), and on an instance the scheduler never reaches nothing
is warmed.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from ..feed import FeedError
from .budget import RESERVES, Deferred, Priority, RequestBudget
from .catalog import CATALOG_GATES, H2H_PAST_SEASONS, Catalog
from .competitions import BY_SLUG, COMPETITIONS, CompetitionConfig, season_year
from .football_data import Disabled, FootballData, Throttled, madrid_day
from .keys import MADRID_FD_ID, parse

__all__ = ["Call", "Run", "Step", "plan", "run", "WARM_REQUESTS", "SEARCH_REQUESTS",
           "MADRID_COMPETITIONS", "SLOT", "WARM_DEADLINE", "SEARCH_DEADLINE"]

WARM_REQUESTS = 4
"""Requests a run may make at priority 2."""
SEARCH_REQUESTS = 1
"""Requests a run may make at priority 3, for the search index, after the rest."""
WARM_DEADLINE = 10.0
"""Seconds the priority-2 reads may take; past them no further request is begun."""
SEARCH_DEADLINE = 5.0
SLOT = timedelta(minutes=15)
"""The scheduler's interval: the round robin of step 5 moves on one player per slot."""

MADRID_COMPETITIONS: tuple[str, ...] = ("la-liga", "champions-league")
"""Real Madrid's competitions football-data.org carries (the cups come from Wikipedia)."""

Resource = Literal["day", "season_matches", "standings", "teams", "scorers", "person_matches"]
Outcome = Literal["read", "held", "deferred", "failed"]
STEPS = (1, 2, 3, 4, 5, 6, 7)


@dataclass(frozen=True)
class Call:
    """One resource a run would have fresh. ``season`` is an earlier season's first year
    (``None``: the current one, read under the competition's version); ``person`` a
    football-data.org person id."""

    step: int
    resource: Resource
    competition: str | None = None
    season: int | None = None
    person: int | None = None
    priority: Priority = 2

    @property
    def ident(self) -> tuple:
        return (self.resource, self.competition, self.season, self.person)

    async def read(self, catalog: Catalog, now: datetime) -> None:
        """Read the resource as the catalogue would, at this call's priority."""
        football = catalog.football
        if football is None:
            raise Disabled()
        today = madrid_day(now)
        if self.resource == "day":
            await football.day(today, priority=self.priority)
            return
        if self.resource == "person_matches":
            await football.person_matches(_whole(self.person), priority=self.priority)
            return
        config = BY_SLUG[str(self.competition)]
        code = str(config.fd_code)
        current = self.season is None
        year = season_year(config, today) if current else int(self.season)
        if self.resource == "season_matches":
            await football.season_matches(code, year, priority=self.priority,
                                          version=catalog.version(config.slug) if current
                                          else None)
        elif self.resource == "standings":
            await football.standings(code, version=catalog.standings_version(config.slug),
                                     priority=self.priority)
        elif self.resource == "teams":
            await football.teams(code, year, priority=self.priority)
        elif self.resource == "scorers":
            await football.scorers(code, version=catalog.version(config.slug),
                                   priority=self.priority)
        else:
            raise ValueError(f"{self.resource!r} is not a warmed resource")


def _whole(value: int | None) -> int:
    if value is None:
        raise ValueError("a person list needs a person")
    return int(value)


# ------------------------------------------------------------------ the plan


def _listed(catalog: Catalog, config: CompetitionConfig) -> bool:
    """The catalogue's rule: a competition gated by a root decision is read only once the
    catalogue is built with that gate passed."""
    gate = config.gate or CATALOG_GATES.get(config.slug)
    return gate is None or gate in catalog.gates


def _carried(catalog: Catalog) -> list[CompetitionConfig]:
    """The listed competitions football-data.org carries, in the fixed order."""
    return [c for c in COMPETITIONS if c.fd_code is not None and _listed(catalog, c)]


def _moved(catalog: Catalog, config: CompetitionConfig, today: date) -> bool:
    """Whether a finish seen today moved ``config``'s version (the day's first version is the
    date's alone: ``Catalog.version``)."""
    return catalog.version(config.slug) != today.toordinal() * 1000


async def _madrid_squad(football: FootballData, year: int) -> list[int]:
    """Real Madrid's football-data.org person ids, in the source's squad order, from La Liga's
    clubs and squads where a cache holds them (no request: the read is capped at none)."""
    with RequestBudget(0):
        try:
            teams = await football.teams(str(BY_SLUG["la-liga"].fd_code), year, priority=2)
        except FeedError:
            return []
    madrid = next((team for team in teams if team.ref.fd_id == MADRID_FD_ID), None)
    ids = []
    for entry in madrid.squad if madrid is not None else ():
        parsed = parse(entry.person.key)
        if parsed is not None and parsed.fd_id is not None and parsed.fd_id not in ids:
            ids.append(parsed.fd_id)
    return ids


async def plan(now: datetime, catalog: Catalog) -> list[Call]:
    """The resources a run at ``now`` would have fresh, in the module's order, each once.

    Empty without a key, or while football-data.org refuses it. Makes no request: the one
    resource it looks at (Madrid's squad, for step 5) is read only where a cache holds it."""
    football = catalog.football
    if football is None or not football.enabled:
        return []
    today = madrid_day(now)
    carried = _carried(catalog)
    madrid = [c for c in carried if c.slug in MADRID_COMPETITIONS]
    calls = [Call(1, "day")]
    for config in madrid:
        calls += [Call(2, "season_matches", config.slug), Call(2, "standings", config.slug)]
    calls += [Call(3, "teams", config.slug) for config in madrid]
    for config in carried:
        if _moved(catalog, config, today):
            calls += [Call(4, "season_matches", config.slug), Call(4, "standings", config.slug),
                      Call(4, "scorers", config.slug)]
    if madrid and madrid[0].slug == "la-liga":
        squad = await _madrid_squad(football, season_year(madrid[0], today))
        if squad:
            turn = int(now.timestamp() // SLOT.total_seconds()) % len(squad)
            calls += [Call(5, "person_matches", person=person)
                      for person in squad[turn:] + squad[:turn]]
    for config in madrid:
        current = season_year(config, today)
        calls += [Call(6, "season_matches", config.slug, season=year)
                  for year in H2H_PAST_SEASONS if year < current]
    calls += [Call(7, "teams", config.slug, priority=3) for config in carried
              if config.slug not in MADRID_COMPETITIONS]
    once: dict[tuple, Call] = {}
    for call in calls:
        once.setdefault(call.ident, call)
    return list(once.values())


# ------------------------------------------------------------------ the run


@dataclass(frozen=True)
class Step:
    """What a run did for one step of the plan: how many calls it planned, and how many it
    read with a request, found held in a cache, could not make (budget) or saw fail."""

    step: int
    planned: int
    read: int
    held: int
    deferred: int
    failed: int


@dataclass(frozen=True)
class Run:
    """A run's account, counts only: no row of any reply."""

    enabled: bool
    requests: int
    steps: tuple[Step, ...]

    def to_json(self) -> dict:
        return {"enabled": self.enabled, "requests": self.requests,
                "planned": sum(s.planned for s in self.steps),
                "read": sum(s.read for s in self.steps),
                "held": sum(s.held for s in self.steps),
                "deferred": sum(s.deferred for s in self.steps),
                "failed": sum(s.failed for s in self.steps),
                "steps": [{"step": s.step, "planned": s.planned, "read": s.read, "held": s.held,
                           "deferred": s.deferred, "failed": s.failed} for s in self.steps]}


class _Stop(Exception):
    """football-data.org refused the key or asked to wait: no further call is made."""


def _spent_out(football: FootballData, cap: RequestBudget, priority: Priority) -> bool:
    """Whether no later call of this priority could make a request in this run: the key is
    blocked, its minute is down to the class's reserve, or the run's deadline has passed."""
    budget = football.budget
    return (budget.blocked_until is not None or budget.tokens <= RESERVES[priority]
            or cap.time_left() <= 0)


async def _walk(calls: Sequence[Call], catalog: Catalog, now: datetime, cap: RequestBudget,
                outcomes: list[tuple[int, Outcome]]) -> None:
    """Read ``calls`` in order under ``cap``, recording each outcome. A call the run's cap
    refuses is passed over (a later one may be held); once the minute, a block or the
    deadline refuses one, the walk ends, since every later request would be refused too."""
    football = catalog.football
    for call in calls:
        spent, deferred = cap.spent, cap.deferred
        try:
            await call.read(catalog, now)
        except (Disabled, Throttled):
            outcomes.append((call.step, "failed"))
            raise _Stop() from None
        except Deferred as refused:
            outcomes.append((call.step, "deferred"))
            if refused.reason != "view":
                return
            continue
        except FeedError:
            outcomes.append((call.step, "failed"))
            continue
        # Rows held stale are served without an error where the request was refused; the
        # cap's counts say which it was.
        outcome: Outcome = ("read" if cap.spent > spent else
                            "deferred" if cap.deferred > deferred else "held")
        outcomes.append((call.step, outcome))
        if outcome == "deferred" and football is not None and _spent_out(football, cap,
                                                                          call.priority):
            return


async def _observe(catalog: Catalog, now: datetime) -> None:
    """Show the catalogue the day it now holds, under a cap of no request, so the finishes
    it lists move their competitions' versions (``Catalog.version``)."""
    with RequestBudget(0), suppress(FeedError):
        await catalog.day(madrid_day(now))


async def run(now: datetime, catalog: Catalog) -> Run:
    """One run of the warming plan at ``now`` (module). Never raises a ``FeedError``."""
    football = catalog.football
    if football is None or not football.enabled:
        return Run(enabled=False, requests=0, steps=())
    outcomes: list[tuple[int, Outcome]] = []
    planned: list[Call] = []
    rest: list[Call] = []
    requests = 0
    stopped = False
    with RequestBudget(WARM_REQUESTS, WARM_DEADLINE) as warm:
        try:
            first = [call for call in await plan(now, catalog) if call.step == 1]
            planned += first
            await _walk(first, catalog, now, warm, outcomes)
            if any(outcome in ("read", "held") for _, outcome in outcomes):
                await _observe(catalog, now)
            rest = [call for call in await plan(now, catalog) if call.step > 1]
            planned += rest
            await _walk([c for c in rest if c.priority == 2], catalog, now, warm, outcomes)
        except _Stop:
            stopped = True
        requests += warm.spent
    if not stopped:
        with RequestBudget(SEARCH_REQUESTS, SEARCH_DEADLINE) as search:
            with suppress(_Stop):
                await _walk([c for c in rest if c.priority == 3], catalog, now, search,
                            outcomes)
            requests += search.spent
    steps = []
    for step in STEPS:
        mine = [outcome for at, outcome in outcomes if at == step]
        steps.append(Step(step, planned=sum(1 for c in planned if c.step == step),
                          read=mine.count("read"), held=mine.count("held"),
                          deferred=mine.count("deferred"), failed=mine.count("failed")))
    return Run(enabled=True, requests=requests, steps=tuple(steps))
