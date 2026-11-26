"""Current results and goals from the community OpenLigaDB API.

Two uses. First, a fill: OpenFootball's free files lag behind play, and OpenLigaDB carries two
of its leagues (the Bundesliga as ``bl1``, the Premier League as ``pl``). A fixture OpenFootball
has not given a result yet takes OpenLigaDB's final result, once the club matching of
``goal_scout.verify_fixtures`` has confirmed both clubs and the matchday. A result OpenFootball
already has is never replaced; where the two disagree, the fixture's goal list is dropped, as
the goal explorer drops it. Second, the Champions League (``ucl``), which has no OpenFootball
file: its fixtures come from OpenLigaDB alone, written in OpenFootball's row shape, so the
board, the table and the match report read every competition the same way. Its clubs take
OpenFootball's name for them where OpenFootball carries their league, else the English form
(``CLUB_NAMES``), so a club has one name on every page.

A filled result also takes the date and kick-off OpenLigaDB gives the match: OpenFootball's
date for a fixture it has no result for can be provisional. The original date stays as
``scheduled_date``. OpenLigaDB states each kick-off in UTC (``matchDateTimeUTC``); a row keeps
that instant as ``utc`` (``kickoff``), and its date and time in the league's own published zone,
the convention of OpenFootball's files (UK time for the Premier League, Central European time
otherwise).

Goals (the scorer as the feed names him, the minute where it gives one) ride with each
confirmed fixture.

Non-claim: nothing here invents a result, a scorer or a minute. A goal the feed does not name
stays unnamed, and a fixture it has not finished has no result.
"""

from __future__ import annotations

import re
from datetime import datetime
from random import randrange

import httpx

from ..providers import assert_may_host
from .feed import FeedCache, FeedError, Snapshot
from .kickoff import ZONES, from_utc, utc_text

API = "https://api.openligadb.de/getmatchdata"
LICENCE = "https://opendatacommons.org/licenses/odbl/1-0/"
FILLS = {"de.1": "bl1", "en.1": "pl"}
"""OpenFootball leagues OpenLigaDB also carries, by its shortcut."""
EUROPE = {"ucl": "ucl"}
"""Competitions read from OpenLigaDB alone, by its shortcut."""

CLUB_NAMES = {
    # The five leagues' clubs, as OpenFootball names them, so a club has one name on every page.
    "Real Madrid": "Real Madrid CF",
    "Atletico Madrid": "Club Atlético de Madrid",
    "Atlético Madrid": "Club Atlético de Madrid",
    "Real Betis": "Real Betis Balompié",
    "Athletic Bilbao": "Athletic Club",
    "Real Sociedad": "Real Sociedad de Fútbol",
    "FC Sevilla": "Sevilla FC",
    "FC Valencia": "Valencia CF",
    "FC Villarreal": "Villarreal CF",
    "Celta Vigo": "RC Celta de Vigo",
    "FC Arsenal": "Arsenal FC",
    "FC Liverpool": "Liverpool FC",
    "FC Chelsea": "Chelsea FC",
    "Aston Villa": "Aston Villa FC",
    "Manchester City": "Manchester City FC",
    "Manchester United": "Manchester United FC",
    "Tottenham Hotspur": "Tottenham Hotspur FC",
    "Newcastle United": "Newcastle United FC",
    "Bayer Leverkusen": "Bayer 04 Leverkusen",
    "Inter Mailand": "FC Internazionale Milano",
    "AC Mailand": "AC Milan",
    "Juventus Turin": "Juventus FC",
    "AS Rom": "AS Roma",
    "Lazio Rom": "SS Lazio",
    "SSC Neapel": "SSC Napoli",
    "Atalanta Bergamo": "Atalanta BC",
    "FC Bologna": "Bologna FC 1909",
    "Paris St. Germain": "Paris Saint-Germain FC",
    "Paris Saint-Germain": "Paris Saint-Germain FC",
    "AS Monaco": "AS Monaco FC",
    "Olympique Marseille": "Olympique de Marseille",
    "Olympique Lyon": "Olympique Lyonnais",
    "OSC Lille": "Lille OSC",
    "RC Lens": "Racing Club de Lens",
    "Stade Brest": "Stade Brestois 29",
    # Clubs outside the five leagues, in the English form.
    "AEK Athen": "AEK Athens",
    "FC Brügge": "Club Brugge",
    "FK Bodö/Glimt": "FK Bodø/Glimt",
    "Feyenoord Rotterdam": "Feyenoord",
    "Galatasaray Istanbul": "Galatasaray",
    "Fenerbahce Istanbul": "Fenerbahçe SK",
    "Besiktas Istanbul": "Beşiktaş",
    "Slavia Prag": "Slavia Prague",
    "Sparta Prag": "Sparta Prague",
    "Benfica Lissabon": "Benfica",
    "Sporting Lissabon": "Sporting CP",
    "Ajax Amsterdam": "Ajax",
    "Celtic Glasgow": "Celtic",
    "Rangers Glasgow": "Rangers",
    "Roter Stern Belgrad": "Red Star Belgrade",
    "FC Kopenhagen": "FC Copenhagen",
    "Olympiakos Piräus": "Olympiacos",
    "Schachtar Donezk": "Shakhtar Donetsk",
    "Qarabag Agdam": "Qarabağ",
    "RB Salzburg": "Red Bull Salzburg",
    "Young Boys Bern": "Young Boys",
}
"""OpenLigaDB writes its clubs in German forms ("Inter Mailand", "FC Brügge"). A European
competition's clubs take the name OpenFootball gives the club where it carries the club's
league, else the English form; a name not listed here is kept as the feed writes it."""


def club_name(name: str) -> str:
    """A European competition's club as the pages name it (``CLUB_NAMES``)."""
    name = name.strip()
    return CLUB_NAMES.get(name, name)


_LEAGUE_PHASE = re.compile(r"(\d+)\.\s*Spieltag")
_STAGES = {"playoffs": "Knockout play-offs", "achtelfinale": "Round of 16",
           "viertelfinale": "Quarter-finals", "halbfinale": "Semi-finals", "finale": "Final"}


class OpenLigaDB:
    def __init__(self) -> None:
        self.cache = FeedCache(8, max_retry=900)

    async def season(self, shortcut: str, year: int) -> Snapshot:
        """The feed's season as published: a list of its match records."""
        assert_may_host("openligadb")

        async def fetch() -> list:
            async with httpx.AsyncClient(timeout=12) as client:
                response = await client.get(f"{API}/{shortcut}/{year}")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise FeedError("OpenLigaDB returned an unreadable season.")
            return payload

        return await self.cache.get(f"{shortcut}/{year}", 3600 + randrange(300), fetch)


def _goals(game: dict) -> list[dict]:
    home = game["teams"]["home"]["id"]
    return [{"side": "home" if goal["team"] == home else "away", "name": goal["name"] or None,
             "minute": goal["minute"], "own": goal["own"], "penalty": goal["penalty"]}
            for goal in game["timeline"]]


def _instant(raw: dict) -> datetime | None:
    """The kick-off the feed states in UTC, or ``None``."""
    try:
        value = datetime.fromisoformat(str(raw["matchDateTimeUTC"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return None
    return value if value.tzinfo is not None else None


def _finished(game: dict) -> list[int] | None:
    goals = [game["goals"]["home"], game["goals"]["away"]]
    if game["fixture"]["status"]["short"] == "FT" and all(type(n) is int for n in goals):
        return goals
    return None


def fill(schedule: list[dict], payload: list, code: str | None = None) -> tuple[list[dict], int]:
    """``schedule``'s rows, each one OpenLigaDB confirms carrying its goals, and each one
    without a result taking OpenLigaDB's final result. Returns the rows and how many it filled.
    ``code`` is the league's (``FILLS``): a filled row's date and time are written in its zone.

    The schedule itself is left as it was; the rows are copies.
    """
    # The goal explorer's parser and club matching, imported here: goal_scout imports
    # openfootball, which imports this module.
    from .goal_scout import parse_matches, verify_fixtures

    rows = [dict(row) for row in schedule]
    try:
        games = verify_fixtures(parse_matches(payload), schedule)
    except FeedError:
        return rows, 0
    zone = ZONES.get(code or "", "CET")
    kickoffs = {}
    for raw in payload:
        if isinstance(raw, dict) and (instant := _instant(raw)) is not None:
            kickoffs[raw.get("matchID")] = instant
    found = {(game["round"], game["teams"]["home"]["name"], game["teams"]["away"]["name"]): game
             for game in games if game["verified"]}
    filled = 0
    for row in rows:
        number = re.fullmatch(r"Matchday (\d+)", str(row.get("round", "")))
        game = found.get((int(number[1]), row["team1"], row["team2"])) if number else None
        result = _finished(game) if game is not None else None
        if result is None:
            continue
        score = row.get("score")
        if isinstance(score, dict):
            score = score.get("ft")
        if not (isinstance(score, list) and len(score) == 2):
            row["score"] = result
            row["filled"] = "openligadb"
            filled += 1
            # The schedule's date can be a provisional one; the result's is when it was played.
            # The fixture id does not hash the date, so a saved match keeps its id.
            kickoff = kickoffs.get(game["fixture"]["id"])
            if kickoff is not None:
                local = from_utc(kickoff, zone)
                if local.date().isoformat() != row["date"]:
                    row["scheduled_date"] = row["date"]
                    row["date"] = local.date().isoformat()
                row["time"] = f"{local:%H:%M}"
                row["utc"] = utc_text(kickoff)
        if not game["omit_events"]:
            row["goals"] = _goals(game)
    return rows, filled


def europe(payload: list) -> list[dict]:
    """A European season from OpenLigaDB, as OpenFootball rows with their goals."""
    from .goal_scout import parse_matches

    if not payload:
        return []
    games = {game["fixture"]["id"]: game for game in parse_matches(payload)}
    rows = []
    for raw in payload:
        game = games.get(raw.get("matchID")) if isinstance(raw, dict) else None
        if game is None:
            continue
        instant = _instant(raw)
        if instant is None:
            continue
        kickoff = from_utc(instant, ZONES["ucl"])
        name = str((raw.get("group") or {}).get("groupName") or "")
        phase = _LEAGUE_PHASE.search(name)
        row = {"round": f"Matchday {phase[1]}" if phase else _STAGES.get(
                   re.sub(r"[^a-z]", "", name.lower())),
               "stage": "league" if phase else "knockout",
               "date": kickoff.date().isoformat(), "time": f"{kickoff:%H:%M}",
               "utc": utc_text(instant),
               "team1": club_name(game["teams"]["home"]["name"]),
               "team2": club_name(game["teams"]["away"]["name"])}
        result = _finished(game)
        if result is not None:
            row["score"] = result
            row["goals"] = _goals(game)
        rows.append(row)
    return rows
