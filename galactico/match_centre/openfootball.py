"""Season schedules, results, tables and match reports from the public feeds.

OpenFootball's public-domain files give the five leagues' schedules and results. Its volunteers'
results lag behind play, so the Bundesliga and the Premier League take the results it lacks
from OpenLigaDB (``openligadb.fill``), and the Champions League, which it does not carry, comes
from OpenLigaDB alone (``openligadb.europe``). Every competition reaches the pages as one
``League``: OpenFootball's row shape, each row with its goals where a feed names them.

The board, the table and the report each say how far a competition's results reach
(``freshness.progress``) and open with one sentence composed here (``answers``), never in the
browser (R10). A list's order is declared: fixtures by competition, then kick-off; a table by
points, then goal difference, then goals scored.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode

import httpx

from ..providers import assert_may_host
from .answers import (
    MADRID,
    board_status,
    club_answer,
    form_note,
    lag_answer,
    madrid_answer,
    match_line,
    standings_answer,
    table_answer,
)
from .feed import FeedCache, FeedError, Snapshot
from .freshness import progress
from .kickoff import ZONES, to_utc
from .names import NameBook, Names
from .openligadb import EUROPE, FILLS, LICENCE, OpenLigaDB, europe, fill

LEAGUES = {
    "es.1": "La Liga",
    "en.1": "Premier League",
    "de.1": "Bundesliga",
    "it.1": "Serie A",
    "fr.1": "Ligue 1",
}
COMPETITIONS = {"es.1": "La Liga", "ucl": "Champions League", "en.1": "Premier League",
                "de.1": "Bundesliga", "it.1": "Serie A", "fr.1": "Ligue 1"}
"""Every competition the pages show, in the order they show them: Madrid's two first."""
ORDER = "Ordered by points, then goal difference, then goals scored."
SAVED_LIMIT = 60
CREDITS = {
    "openfootball": {"name": "OpenFootball", "licence": "CC0 1.0",
                     "url": "https://github.com/openfootball/football.json",
                     "licence_url": "https://github.com/openfootball/football.json/blob/"
                                    "master/LICENSE.md"},
    "openligadb": {"name": "OpenLigaDB", "licence": "ODbL 1.0",
                   "url": "https://www.openligadb.de/", "licence_url": LICENCE},
}


def season_start(day: date) -> int:
    return day.year if day.month >= 7 else day.year - 1


def season_name(year: int) -> str:
    """"2026/27"."""
    return f"{year}/{(year + 1) % 100:02d}"


class NoSeason(FeedError):
    """No feed holds a schedule for the season asked for: a 404, not an outage."""


def final_score(row: dict) -> list[int] | None:
    score = row.get("score")
    if isinstance(score, dict):
        score = score.get("ft")
    if (isinstance(score, list) and len(score) == 2
            and all(type(n) is int and n >= 0 for n in score)):
        return score
    return None


def _fixture(code: str, season: int, row: dict, day: date) -> dict:
    home, away = row["team1"], row["team2"]
    identity = "\0".join([code, str(season), home, away, row.get("round") or ""])
    key = hashlib.sha256(identity.encode()).hexdigest()[:16]
    score = final_score(row)
    return {
        "id": f"{code}-{season}-{key}", "code": code, "competition": COMPETITIONS[code],
        "home": home, "away": away, "madrid": home in MADRID or away in MADRID,
        "day": row["date"], "kickoff": row.get("time"),
        # The instant (kickoff.py): the source's stated UTC, else its published local time in
        # the competition's zone; ``None`` where either is unknown.
        "kickoff_utc": row.get("utc") or to_utc(row["date"], row.get("time"), ZONES.get(code)),
        "round": row.get("round"),
        "score": score, "live": False, "status": "FT" if score is not None else (
            "Result pending" if row["date"] < day.isoformat() else "Scheduled"),
    }


def recent_form(rows: list[dict], name: str, before: str) -> list[dict]:
    games = []
    for row in rows:
        if row["date"] >= before or name not in (row["team1"], row["team2"]):
            continue
        score = final_score(row)
        if score is None:
            continue
        home = name == row["team1"]
        own, against = score if home else reversed(score)
        games.append({"day": row["date"], "opponent": row["team2"] if home else row["team1"],
                      "score": f"{own}–{against}", "venue": "H" if home else "A",
                      "result": "W" if own > against else "L" if own < against else "D"})
    return sorted(games, key=lambda r: r["day"], reverse=True)[:5]


def results_table(rows: list[dict], cutoff: str) -> tuple[list[dict], int, int]:
    clubs = {r[side] for r in rows for side in ("team1", "team2")}
    table = {club: dict(team=club, played=0, wins=0, draws=0, losses=0, gf=0, ga=0, points=0)
             for club in clubs}
    reported = missing = 0
    for row in rows:
        if row["date"] > cutoff:
            continue
        score = final_score(row)
        if score is None:
            missing += 1
            continue
        reported += 1
        for team, gf, ga in ((row["team1"], *score), (row["team2"], *reversed(score))):
            entry = table[team]
            entry["played"] += 1
            entry["wins"] += int(gf > ga)
            entry["draws"] += int(gf == ga)
            entry["losses"] += int(gf < ga)
            entry["gf"] += gf
            entry["ga"] += ga
            entry["points"] += 3 if gf > ga else int(gf == ga)
    ordered = sorted(table.values(), key=lambda c: (-c["points"], c["ga"]-c["gf"],
                                                    -c["gf"], c["team"].casefold()))
    last = None
    for position, entry in enumerate(ordered, start=1):
        entry["gd"] = entry["gf"] - entry["ga"]
        record = (entry["points"], entry["gd"], entry["gf"])
        if record != last:
            rank = position
        entry["rank"] = rank
        last = record
    return ordered, reported, missing


def parse_key(key: str) -> tuple[str, int] | None:
    """A public fixture id's competition and season, or ``None`` for a malformed id."""
    parts = key.split("-")
    if (len(parts) != 3 or parts[0] not in COMPETITIONS
            or not re.fullmatch(r"[0-9]{4}-[0-9a-f]{16}", "-".join(parts[1:]))):
        return None
    return parts[0], int(parts[1])


def _kickoff(game: dict) -> tuple:
    return (game["day"], game["kickoff"] or "99:99", game["home"].casefold())


def _board_order(game: dict) -> tuple:
    return (list(COMPETITIONS).index(game["code"]), game["kickoff"] or "99:99",
            game["home"].casefold())


@dataclass(frozen=True)
class League:
    """One competition's season as the pages read it."""

    code: str
    year: int
    rows: list[dict]
    checked: str
    warning: str | None
    filled: int
    sources: tuple[str, ...]

    @property
    def name(self) -> str:
        return COMPETITIONS[self.code]

    @property
    def table_rows(self) -> list[dict]:
        """The rows a table counts: a European competition's league phase only."""
        return [row for row in self.rows if row.get("stage", "league") == "league"]

    def freshness(self, cutoff: date, today: date) -> dict:
        return progress(self.name, self.table_rows, cutoff, today,
                        "openligadb" if self.filled else None)

    def credits(self) -> list[dict]:
        return [CREDITS[key] for key in self.sources]


class OpenFootball:
    def __init__(self, names: Names | None = None) -> None:
        self.cache = FeedCache(30)
        self.ligadb = OpenLigaDB()
        self._built: dict[tuple, list[dict]] = {}
        self.names = names
        """Real Madrid's squad names (Wikipedia), to write a feed's scorer the squad's way."""

    async def book(self, day: date) -> NameBook:
        """The squad names for ``day``'s season, or an empty book: a page never waits long for
        them, and the feed's own spelling stays where they can't be read."""
        if self.names is None:
            return NameBook(())
        try:
            return NameBook(await asyncio.wait_for(self.names(day), 4))
        except (FeedError, TimeoutError):
            return NameBook(())

    async def season(self, code: str, year: int) -> Snapshot:
        assert_may_host("openfootball")

        async def fetch() -> list:
            source = "https://raw.githubusercontent.com/openfootball/football.json/master"
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(f"{source}/{year}-{(year+1)%100:02}/{code}.json")
            if response.status_code == 404:
                raise FeedError("Season file unavailable.")
            response.raise_for_status()
            data = response.json()
            rows = data.get("matches") if isinstance(data, dict) else None
            if not isinstance(rows, list) or any(
                not isinstance(row, dict) or not all(isinstance(row.get(k), str)
                                                     for k in ("team1", "team2", "date"))
                for row in rows
            ):
                raise FeedError("Invalid season file.")
            return rows

        return await self.cache.get(f"{code}/{year}", 3600, fetch)

    def _memo(self, key: tuple, build) -> list[dict]:
        # A season is rebuilt only when one of its snapshots was refetched (a new time and a
        # new list); the cache holds each snapshot's list for as long as it serves it.
        if key not in self._built:
            self._built[key] = build()
            while len(self._built) > 24:
                self._built.pop(next(iter(self._built)))
        return self._built[key]

    async def league(self, code: str, year: int) -> League:
        """``code``'s season: OpenFootball's, filled from OpenLigaDB where it carries the league;
        or OpenLigaDB's alone for a European competition (no rows when it publishes none)."""
        if code in EUROPE:
            snap = await self.ligadb.season(EUROPE[code], year)
            rows = self._memo((code, year, snap.checked, id(snap.rows)),
                              lambda: europe(snap.rows))
            return League(code, year, rows, snap.checked, snap.warning, 0, ("openligadb",))
        if code in FILLS:
            # The two feeds are asked at once: a cold page waits for the slower, not the sum.
            season, extra = await asyncio.gather(self.season(code, year),
                                                 self.ligadb.season(FILLS[code], year),
                                                 return_exceptions=True)
            if isinstance(season, BaseException):
                raise season
        else:
            season, extra = await self.season(code, year), None
        rows, filled, sources = season.rows, 0, ("openfootball",)
        if code in FILLS and season.rows:
            if isinstance(extra, BaseException) and not isinstance(extra, FeedError):
                raise extra
            if isinstance(extra, Snapshot):
                built = self._memo((code, year, season.checked, id(season.rows),
                                    extra.checked, id(extra.rows)),
                                   lambda: [fill(season.rows, extra.rows, code)])
                rows, filled = built[0]
                sources = ("openfootball", "openligadb")
        return League(code, year, rows, season.checked, season.warning, filled, sources)

    async def _leagues(self, year: int, codes=None) -> dict[str, League | FeedError]:
        codes = list(codes or COMPETITIONS)
        found = await asyncio.gather(*(self.league(code, year) for code in codes),
                                     return_exceptions=True)
        for value in found:
            if isinstance(value, BaseException) and not isinstance(value, FeedError):
                raise value
        return dict(zip(codes, found, strict=True))

    async def fixtures(self, day: date, today: date) -> dict:
        year = season_start(day)
        matches, dates, checked, warnings, notes = [], set(), [], [], {}
        madrid_fixture = None
        for code, league in (await self._leagues(year)).items():
            if isinstance(league, FeedError):
                warnings.append(f"{COMPETITIONS[code]} · {league}")
                continue
            if not league.rows:
                continue  # A European competition with no season published.
            checked.append(league.checked)
            if league.warning:
                warnings.append(f"{league.name} · showing cached schedule.")
            for row in league.rows:
                dates.add(row["date"])
                is_madrid = row["team1"] in MADRID or row["team2"] in MADRID
                if (is_madrid and row["date"] >= day.isoformat() and
                    (madrid_fixture is None or row["date"] < madrid_fixture["day"])):
                    madrid_fixture = _fixture(code, year, row, today)
                if row["date"] == day.isoformat():
                    matches.append(_fixture(code, year, row, today))
            fresh = league.freshness(today, today)
            if any(m["code"] == code and m["status"] == "Result pending" for m in matches):
                notes[code] = fresh["label"]
        if not checked:
            raise _missing(year, today, warnings)
        ordered = sorted(matches, key=_board_order)
        return {"matches": ordered, "checked": min(checked),
                "warnings": warnings,
                "next": min((d for d in dates if d > day.isoformat()), default=None),
                "previous": max((d for d in dates if d < day.isoformat()), default=None),
                "first": min(dates, default=None), "last": max(dates, default=None),
                "season": season_name(year),
                "status": board_status(day.isoformat(), ordered, today),
                "madrid_fixture": madrid_fixture, "through": notes,
                "order": "By competition, then kick-off time."}

    async def nearest(self, today: date) -> date:
        """The day the board opens on: today when it has fixtures, else the nearer of the
        previous and the next day that has (the next on a tie)."""
        board = await self.fixtures(today, today)
        if board["matches"]:
            return today
        options = [date.fromisoformat(d) for d in (board["next"], board["previous"]) if d]
        return min(options, key=lambda d: abs((d - today).days), default=today)

    async def summary(self, today: date) -> dict:
        """Madrid's next fixture and latest reported result, and each competition's freshness."""
        year = season_start(today)
        leagues, book = await asyncio.gather(self._leagues(year), self.book(today))
        games, freshness, warnings, checked = [], [], [], []
        goals: dict[str, list | None] = {}
        for code, league in leagues.items():
            if isinstance(league, FeedError):
                warnings.append(f"{COMPETITIONS[code]} · {league}")
                continue
            if not league.rows:
                continue
            checked.append(league.checked)
            freshness.append({"code": code, **league.freshness(today, today)})
            for row in league.rows:
                if row["team1"] in MADRID or row["team2"] in MADRID:
                    games.append(game := _fixture(code, year, row, today))
                    side = "home" if row["team1"] in MADRID else "away"
                    goals[game["id"]] = book.goals(row.get("goals"), side)
        if not checked:
            raise _missing(year, today, warnings)
        upcoming = min((g for g in games if g["score"] is None
                        and g["day"] >= today.isoformat()), key=_kickoff, default=None)
        last = max((g for g in games if g["score"] is not None
                    and g["day"] <= today.isoformat()), key=_kickoff, default=None)
        missing = sum(1 for g in games if g["score"] is None and last is not None
                      and last["day"] < g["day"] < today.isoformat())
        # Madrid's own competitions must all answer, or the sentence could name the wrong
        # next fixture; it is withheld instead.
        whole = not any(isinstance(leagues[code], FeedError) for code in ("es.1", "ucl"))
        # The sentence names the last result's scorers where the feed lists every goal.
        latest = dict(last, goals=goals.get(last["id"])) if last is not None else None
        return {"answer": madrid_answer(upcoming, latest, missing, today) if whole else None,
                "unavailable": None if whole else "Real Madrid’s fixtures can’t be loaded "
                                                  "right now.",
                "next": upcoming if whole else None, "last": last if whole else None,
                "freshness": freshness, "lag": lag_answer(freshness), "today": today,
                "checked": min(checked),
                "warnings": warnings}

    async def competition(self, code: str, day: date, today: date, team: str | None) -> dict:
        year = season_start(day)
        try:
            league = await self.league(code, year)
        except FeedError as exc:
            if str(exc) == "Season file unavailable.":
                raise _missing(year, today, [str(exc)]) from exc
            raise
        cutoff = min(day, today)
        table, reported, missing = results_table(league.table_rows, cutoff.isoformat())
        fresh = league.freshness(cutoff, today)
        matches = sorted((_fixture(code, year, row, today) for row in league.rows
                          if team and team in (row["team1"], row["team2"])), key=_kickoff)
        payload = {"competition": league.name, "code": code, "season": year, "cutoff": cutoff,
                   "table": table, "reported": reported, "missing": missing,
                   "fixtures": matches, "checked": league.checked,
                   "warnings": [league.warning] if league.warning else [],
                   "freshness": fresh, "order": ORDER,
                   "answer": table_answer(league.name, table, fresh, dated=cutoff < today),
                   "credits": league.credits(),
                   "madrid": sorted(row["team"] for row in table if row["team"] in MADRID),
                   "stage": "League phase" if code in EUROPE else None}
        if team:
            # Each result as the club's (W, D or L), decided here, not in the browser.
            outcomes = {}
            for game in matches:
                if game["score"] is not None:
                    own, against = (game["score"] if game["home"] == team
                                    else reversed(game["score"]))
                    outcomes[game["id"]] = "W" if own > against else "L" if own < against else "D"
            payload["outcomes"] = outcomes
            row = next((entry for entry in table if entry["team"] == team), None)
            upcoming = next((m for m in matches if m["score"] is None
                             and m["day"] >= today.isoformat()), None)
            payload["club_answer"] = club_answer(team, league.name, row, upcoming, today)
        return payload

    async def madrid_baseline(self, day: date, today: date) -> dict:
        league = await self.competition("es.1", day, today, None)
        madrid = [row for row in league["table"] if row["team"] in MADRID]
        others = [row for row in league["table"] if row["team"] not in MADRID]

        def rates(rows: list[dict]) -> dict:
            games = sum(row["played"] for row in rows)
            scored = sum(row["gf"] for row in rows)
            conceded = sum(row["ga"] for row in rows)
            return {"team_games": games, "scored": scored, "conceded": conceded,
                    "scored_per_game": scored / games if games else None,
                    "conceded_per_game": conceded / games if games else None}

        return {k: league[k] for k in ("season", "cutoff", "reported", "missing",
                                      "checked", "warnings")} | {
            "madrid": rates(madrid), "other_clubs": rates(others)}

    async def detail(self, code: str, year: int, key: str, today: date) -> dict | None:
        # The squad list is this season's: an earlier season's scorers keep the feed's names.
        current = year == season_start(today)
        league, book = await asyncio.gather(
            self.league(code, year), self.book(today) if current else _empty_book())
        for row in league.rows:
            game = _fixture(code, year, row, today)
            if game["id"] != key:
                continue
            form = {name: recent_form(league.rows, name, row["date"])
                    for name in (game["home"], game["away"])}
            report = {"match": game, "checked": league.checked, "warnings": (
                ["Showing a cached season file."] if league.warning else []),
                "form": form, "form_note": form_note(form),
                "line": match_line(game, today),
                "clubs": [_club_links(code, name, None if year == season_start(today)
                                      else row["date"]) for name in (game["home"], game["away"])],
                "through": league.freshness(today, today)["label"],
                "credits": league.credits()}
            if game["madrid"]:
                side = "home" if game["home"] in MADRID else "away"
                row = dict(row, goals=book.goals(row.get("goals"), side))
            report.update(_goals_report(league, row, game))
            return report
        return None

    async def saved(self, keys: list[str], today: date) -> dict:
        """The saved fixtures still in the feeds, by date then kick-off, whatever their day."""
        wanted: dict[tuple[str, int], set[str]] = {}
        for key in dict.fromkeys(keys[:SAVED_LIMIT]):
            if (parsed := parse_key(key)) is not None:
                wanted.setdefault(parsed, set()).add(key)
        found, warnings, missing = [], [], []
        loaded = await asyncio.gather(*(self.league(code, year) for code, year in wanted),
                                      return_exceptions=True)
        for (code, year), league in zip(wanted, loaded, strict=True):
            if isinstance(league, BaseException):
                if not isinstance(league, FeedError):
                    raise league
                warnings.append(f"{COMPETITIONS[code]} · {league}")
                continue
            games = {g["id"]: g for g in (_fixture(code, year, row, today) for row in league.rows)}
            found += [games[key] for key in wanted[(code, year)] if key in games]
            missing += sorted(key for key in wanted[(code, year)] if key not in games)
        gone = len(missing)
        return {"matches": sorted(found, key=lambda g: (_kickoff(g)[:2], _board_order(g))),
                "missing": missing, "warnings": warnings,
                "missing_note": (f"{gone} saved {'match is' if gone == 1 else 'matches are'} no "
                                 "longer in the feeds.") if gone else None}

    async def standings(self, today: date) -> dict:
        """Table's first view: Madrid's place in each competition of theirs with a table, the
        competition of their latest reported result first, and that competition's code, the tab
        the page opens on."""
        year = season_start(today)
        codes = [code for code in COMPETITIONS if code in ("es.1", "ucl")]
        leagues = await self._leagues(year, codes)
        latest: dict[str, str] = {}
        items = []
        for code in codes:
            league = leagues[code]
            if isinstance(league, FeedError) or not league.rows:
                continue
            rows = league.table_rows
            table, _, _ = results_table(rows, today.isoformat())
            items.append((code, league.name, table, league.freshness(today, today)))
            played = [row["date"] for row in rows if final_score(row) is not None
                      and (row["team1"] in MADRID or row["team2"] in MADRID)
                      and row["date"] <= today.isoformat()]
            if played:
                latest[code] = max(played)
        if not items:
            raise _missing(year, today, [])
        items.sort(key=lambda item: (-int(latest.get(item[0], "0").replace("-", "")),
                                     codes.index(item[0])))
        return {"code": items[0][0],
                "answer": standings_answer([(name, table, fresh)
                                            for _, name, table, fresh in items])}


async def _empty_book() -> NameBook:
    return NameBook(())


def _missing(year: int, today: date, warnings: list[str]) -> FeedError:
    """No schedule loaded: a season no feed holds (a 404 that says so), else an outage."""
    if warnings and all(w.endswith("Season file unavailable.") for w in warnings):
        later = year > season_start(today)
        return NoSeason(f"The free feeds have no fixtures for {season_name(year)}"
                        f"{' yet' if later else ''}.")
    return FeedError("No league schedules could be loaded for this season.")


def _club_links(code: str, team: str, day: str | None) -> dict:
    """A club's schedule and its row in the table; of the match's own season when that is
    not the current one."""
    page = "/match-centre/leagues?"
    season = {"day": day} if day else {}
    return {"team": team,
            "schedule": page + urlencode({"league": code, **season, "team": team}),
            "table": page + urlencode({"league": code, **season, "highlight": team})}


def _goals_report(league: League, row: dict, game: dict) -> dict:
    """The match's goals where a feed lists them, or one plain line where none does."""
    if game["score"] is None:
        return {"goals": None, "goals_note": None}
    if sum(game["score"]) == 0:
        return {"goals": [], "goals_note": "No goals."}
    goals = row.get("goals")
    if goals is None:
        if "openligadb" in league.sources:
            note = "The feed has no goal list for this match."
        else:
            note = f"The free {league.name} feed doesn’t name scorers."
        return {"goals": None, "goals_note": note}
    unlisted = sum(game["score"]) - len(goals)
    note = None
    if unlisted > 0:
        note = (f"{unlisted} {'goal is' if unlisted == 1 else 'goals are'} "
                "missing from the feed’s goal list.")
    return {"goals": goals, "goals_note": note, "goals_credit": CREDITS["openligadb"]}


__all__ = ["COMPETITIONS", "LEAGUES", "League", "NoSeason", "OpenFootball", "final_score",
           "parse_key", "recent_form", "results_table", "season_name", "season_start"]
