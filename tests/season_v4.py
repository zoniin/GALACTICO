"""Synthetic football-data.org v4 replies, built in code.

R7: no football data enters git. These builders are code, not recordings: every club, player,
id, date and result is invented ("A FC", "Norte CF", "Test Roma"). One club plays the part of
Real Madrid: it has football-data.org's id 86 and Real Madrid's name, because the site's
Madrid pages are keyed on both (``keys.MADRID_KEY``); its players, results and every other
value are invented. Nothing here is the example text of the design documents.

The replies take football-data.org's shape, field for field, so the normalisers are tested on
what the API sends. ``tests/fixtures/football_data_v4_fields.json`` names those fields (names
only, no values), and a test holds the builders to it: every builder emits only those keys, and
the sample world emits every one of them. That includes the fields the normalisers must drop
(B1: ``playedMatches``, ``shirtNumber``, ``crest``, ``emblem``, ``flag``, ``odds``,
``filters.client``, ``lastUpdated`` of team records). Their values are invented too, and a crest
or emblem here points at ``example.invalid``, never at football-data.org's crest host, so a test
can see one leak without the repository holding a real link.

What the builders cover:

- every resource of PLAN 3.4: ``competitions``, ``day``, ``season_matches``, ``standings``,
  ``teams``, ``scorers``, ``person`` and ``person_matches``;
- every match status, null assists and penalties, a scorers list cut at its limit
  (``count == limit``), a knockout tie whose clubs are not yet known (every team field
  ``None``), and a squad position given as ``None`` and as the string ``"null"``;
- the five error replies (400 bad token, 401, 403 restricted, 404, 429 with ``errorCode``) and
  the rate headers football-data.org sends with every reply;
- ``World``, a small consistent season, and its ``handler`` for ``httpx.MockTransport``.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx

__all__ = [
    "FIELDS_FILE", "STAMP", "Club", "Player", "Result",
    "MADRID", "A_FC", "NORTE", "RIBERA", "TEST_ROMA", "TEST_PORTO", "NORD", "TEST_ALBION",
    "TEST_CITY", "TESTLAND", "TBD", "SQUAD", "COACH", "COMPETITION_META",
    "area", "competition_ref", "season_ref", "team_ref", "team_record", "match",
    "day", "season_matches", "table_rows", "standings", "squad_entry", "team", "teams",
    "scorer", "scorers", "person", "person_matches", "competitions",
    "ERRORS", "error", "rate_headers", "response", "World", "sample_world", "paths",
]

FIELDS_FILE = Path(__file__).resolve().parent / "fixtures" / "football_data_v4_fields.json"

STAMP = "2026-11-26T10:20:30Z"
"""An invented bulk re-sync stamp (football-data.org's ``lastUpdated``)."""

_ASSET = "https://assets.example.invalid"
"""Where an invented crest, emblem or flag points: a host that cannot resolve."""


# ------------------------------------------------------------------ clubs and players


@dataclass(frozen=True)
class Club:
    """An invented club as football-data.org would describe it."""

    id: int | None
    name: str | None
    short: str | None
    tla: str | None
    area: str = "Spain"
    area_code: str = "ESP"
    founded: int | None = 1920
    venue: str | None = "Estadio de Prueba"
    colours: str | None = "White / Navy"


MADRID = Club(86, "Real Madrid CF", "Real Madrid", "RMA", founded=1900,
              venue="Estadio Invento", colours="White / Gold")
A_FC = Club(90001, "A FC", "A FC", "AFC", venue="Campo A")
NORTE = Club(90002, "Norte CF", "Norte", "NOR", venue="Estadio del Norte")
RIBERA = Club(90003, "Ribera Unión Deportiva", "Ribera", "RIB", venue=None, colours=None)
TEST_ROMA = Club(90011, "Test Roma", "Test Roma", "TRO", "Italy", "ITA")
TEST_PORTO = Club(90012, "Test Porto FC", "Test Porto", "TPO", "Portugal", "POR")
NORD = Club(90013, "Nord Kickers 1904", "Nord Kickers", "NKI", "Germany", "DEU")
TEST_ALBION = Club(90021, "Test Albion FC", "Test Albion", "TAL", "England", "ENG")
TEST_CITY = Club(90022, "Test City FC", "Test City", "TCI", "England", "ENG")
TESTLAND = Club(90031, "Testland", "Testland", "TSL", "Testland", "TST", founded=1910,
                venue=None)
TBD = Club(None, None, None, None)
"""A knockout slot whose club is not known yet: football-data.org sends every field null."""


@dataclass(frozen=True)
class Player:
    """An invented player, as football-data.org names him and as Wikipedia's squad list does.

    The two names differ the way real sources differ (accents dropped, a mononym), so the
    crosswalk is tested on the cases it must handle."""

    fd_id: int
    name: str              # football-data.org's
    born: str
    nationality: str
    position: str | None   # football-data.org's coarse position; None or "null" as it sends
    shirt: int | None      # Wikipedia's squad list
    group: str | None      # Wikipedia's squad list
    wp_title: str | None   # his article, as the squad list links it
    wp_name: str | None    # as the squad list writes him
    nation: str = "ESP"    # the squad list's three letters

    @property
    def first(self) -> str:
        return "" if " " not in self.name else self.name.rsplit(" ", 1)[0]

    @property
    def last(self) -> str:
        return self.name.rsplit(" ", 1)[-1]

    @property
    def section(self) -> str:
        return self.position if self.position not in (None, "null") else "Offence"


def _p(fd_id, name, born, position, shirt, group, wp_name=None, nation="ESP",
       nationality="Spain", title=None):
    wp_name = wp_name or name
    return Player(fd_id, name, born, nationality, position, shirt, group,
                  title or wp_name.replace(" ", "_"), wp_name, nation)


SQUAD: tuple[Player, ...] = (
    _p(70001, "Inaki Portero", "1996-03-14", "Goalkeeper", 1, "GK", "Iñaki Portero"),
    _p(70002, "Bruno Guante", "2001-07-02", "Goalkeeper", 13, "GK", nation="POR",
       nationality="Portugal"),
    _p(70003, "Dario Lateral", "1999-01-21", "Defence", 2, "DF", "Dário Lateral",
       nation="BRA", nationality="Brazil"),
    _p(70004, "Hugo Central", "1998-10-09", "Defence", 3, "DF"),
    _p(70005, "Tomas Muro", "2000-04-30", "Defence", 4, "DF", "Tomás Muro"),
    _p(70006, "Leon Zaga", "1997-12-12", "Defence", 5, "DF", "León Zaga", nation="FRA",
       nationality="France"),
    _p(70007, "Ali Carril", "2002-02-02", "Defence", 12, "DF", nation="MAR",
       nationality="Morocco"),
    _p(70008, "Rui Banda", "2000-05-05", "Defence", 22, "DF", nation="POR",
       nationality="Portugal"),
    _p(70009, "Pablo Medio", "1999-06-18", "Midfield", 6, "MF"),
    _p(70010, "Santi Pivote", "1995-09-27", "Midfield", 8, "MF"),
    _p(70011, "Nico Enlace", "2003-03-03", "Midfield", 10, "MF"),
    _p(70012, "Oscar Volante", "2001-11-11", "Midfield", 14, "MF", "Óscar Volante"),
    _p(70013, "Kemal Olcu", "2004-08-08", "Midfield", 15, "MF", "Kemal Ölçü", nation="TUR",
       nationality="Turkey"),
    _p(70014, "Ruben Banda", "2000-05-05", "Midfield", 23, "MF", "Rúben Banda", nation="POR",
       nationality="Portugal"),
    _p(70015, "Joan Interior", "2005-01-15", "Midfield", 20, "MF"),
    _p(70016, "Vinicio Ala", "2000-07-12", "Offence", 7, "FW", "Vinício Ala", nation="BRA",
       nationality="Brazil"),
    _p(70017, "Kai Delantero", "1998-02-28", "Offence", 9, "FW", nation="GER",
       nationality="Germany"),
    _p(70018, "Rafa Extremo", "2002-09-09", "Offence", 11, "FW"),
    _p(70019, "Carlos Punta", "2006-04-04", "Offence", 19, "FW", "Carlos Puntá",
       title="Carlos_Puntá_(footballer,_born_2006)"),
    _p(70020, "Ferrito", "2007-10-10", "Offence", 21, "FW", nation="BRA",
       nationality="Brazil"),
    _p(70021, "Oleh Nuevo", "2007-01-01", None, None, None, nation="UKR",
       nationality="Ukraine"),
    _p(70022, "Marco Reserva", "2006-06-06", "null", None, None),
)
"""The Madrid-like club's invented squad. ``Rui Banda`` and ``Rúben Banda`` share a date of
birth and a folded surname, so a join by those two is ambiguous for them. ``Oleh Nuevo`` (no
position) and ``Marco Reserva`` (position the string ``"null"``) are in football-data.org's
squad and not in Wikipedia's list."""

COACH = ("Mateo Banquillo", "1970-05-20", "Spain", 80001)
"""The Madrid-like club's invented coach: (name, born, nationality, id)."""


# ------------------------------------------------------------------ competition metadata

COMPETITION_META: dict[str, dict[str, Any]] = {
    # code: invented id, football-data.org's name, type, area (id, name, code), plan, season
    "PD": dict(id=7001, name="Primera Division", type="LEAGUE", area=(5001, "Spain", "ESP"),
               plan="TIER_ONE", start="2026-08-14", end="2027-05-30", season_id=6001),
    "CL": dict(id=7002, name="UEFA Champions League", type="CUP",
               area=(5002, "Europe", "EUR"), plan="TIER_ONE", start="2026-09-08",
               end="2027-06-05", season_id=6002),
    "PL": dict(id=7003, name="Premier League", type="LEAGUE", area=(5003, "England", "ENG"),
               plan="TIER_ONE", start="2026-08-21", end="2027-05-23", season_id=6003),
    "BL1": dict(id=7004, name="Bundesliga", type="LEAGUE", area=(5004, "Germany", "DEU"),
                plan="TIER_ONE", start="2026-08-28", end="2027-05-15", season_id=6004),
    "SA": dict(id=7005, name="Serie A", type="LEAGUE", area=(5005, "Italy", "ITA"),
               plan="TIER_ONE", start="2026-08-23", end="2027-05-30", season_id=6005),
    "FL1": dict(id=7006, name="Ligue 1", type="LEAGUE", area=(5006, "France", "FRA"),
                plan="TIER_ONE", start="2026-08-22", end="2027-05-22", season_id=6006),
    "DED": dict(id=7007, name="Eredivisie", type="LEAGUE", area=(5007, "Netherlands", "NLD"),
                plan="TIER_ONE", start="2026-08-07", end="2027-05-16", season_id=6007),
    "PPL": dict(id=7008, name="Primeira Liga", type="LEAGUE", area=(5008, "Portugal", "POR"),
                plan="TIER_ONE", start="2026-08-08", end="2027-05-23", season_id=6008),
    "ELC": dict(id=7009, name="Championship", type="LEAGUE", area=(5003, "England", "ENG"),
                plan="TIER_ONE", start="2026-08-14", end="2027-05-08", season_id=6009),
    "BSA": dict(id=7010, name="Campeonato Brasileiro Série A", type="LEAGUE",
                area=(5009, "Brazil", "BRA"), plan="TIER_ONE", start="2026-01-28",
                end="2026-12-02", season_id=6010),
    "CLI": dict(id=7011, name="Copa Libertadores", type="CUP",
                area=(5010, "South America", "SAM"), plan="TIER_FOUR", start="2026-02-04",
                end="2026-11-28", season_id=6011),
    "WC": dict(id=7012, name="FIFA World Cup", type="CUP", area=(5011, "World", "INT"),
               plan="TIER_ONE", start="2026-06-11", end="2026-07-19", season_id=6012),
    "EC": dict(id=7013, name="European Championship", type="CUP", area=(5002, "Europe", "EUR"),
               plan="TIER_ONE", start="2024-06-14", end="2024-07-14", season_id=6013),
}
"""Every competition football-data.org's free plan lists, with invented ids and dates. The
European Championship is listed by the API and covered by no page."""

_AREAS = {"Spain": (5001, "ESP"), "Italy": (5005, "ITA"), "Portugal": (5008, "POR"),
          "Germany": (5004, "DEU"), "England": (5003, "ENG"), "Testland": (5012, "TST")}


# ------------------------------------------------------------------ shared fragments


def area(name: str, code: str | None = None, area_id: int | None = None) -> dict:
    known = _AREAS.get(name, (5099, code or "XXX"))
    code = code or known[1]
    return {"id": area_id or known[0], "name": name, "code": code,
            "flag": f"{_ASSET}/flags/{code.lower()}.svg"}


def competition_ref(code: str) -> dict:
    meta = COMPETITION_META[code]
    return {"id": meta["id"], "name": meta["name"], "code": code, "type": meta["type"],
            "emblem": f"{_ASSET}/emblems/{code.lower()}.png"}


def season_ref(code: str, *, current_matchday: int | None = 14,
               winner: Club | None = None) -> dict:
    meta = COMPETITION_META[code]
    return {"id": meta["season_id"], "startDate": meta["start"], "endDate": meta["end"],
            "currentMatchday": current_matchday,
            "winner": team_record(winner) if winner is not None else None}


def team_ref(club: Club) -> dict:
    """A club as a match, a table row or a standings reply names it."""
    return {"id": club.id, "name": club.name, "shortName": club.short, "tla": club.tla,
            "crest": None if club.id is None else f"{_ASSET}/crests/{club.id}.png"}


def team_record(club: Club) -> dict:
    """A club as a scorers line or a season's winner carries it (with ``lastUpdated``)."""
    return {**team_ref(club), "address": f"{club.short} Street 1", "website":
            "https://club.example.invalid", "founded": club.founded,
            "clubColors": club.colours, "venue": club.venue, "lastUpdated": STAMP}


# ------------------------------------------------------------------ matches


@dataclass(frozen=True)
class Result:
    home: int | None
    away: int | None


def _winner(result: Result | None) -> str | None:
    if result is None or result.home is None or result.away is None:
        return None
    if result.home == result.away:
        return "DRAW"
    return "HOME_TEAM" if result.home > result.away else "AWAY_TEAM"


def match(match_id: int, utc: str, home: Club, away: Club, *, status: str = "TIMED",
          code: str = "PD", result: tuple[int, int] | None = None,
          half_time: tuple[int, int] | None = None, matchday: int | None = 1,
          stage: str = "REGULAR_SEASON", group: str | None = None,
          referee: tuple[int, str, str | None] | None = None,
          duration: str = "REGULAR", winner: str | None = "auto",
          last_updated: str = STAMP, current_matchday: int | None = 14) -> dict:
    """One match as football-data.org lists it.

    ``result`` is the full-time result where the status has one (FINISHED, AWARDED, and the
    running one while IN_PLAY or PAUSED); ``half_time`` likewise. ``winner`` is derived from a
    FINISHED or AWARDED result unless given. ``referee`` is (id, name, nationality)."""
    full = Result(*result) if result else Result(None, None)
    half = Result(*half_time) if half_time else Result(None, None)
    if winner == "auto":
        winner = _winner(full) if status in ("FINISHED", "AWARDED") else None
    meta = COMPETITION_META[code]
    return {
        "area": area(meta["area"][1], meta["area"][2], meta["area"][0]),
        "competition": competition_ref(code),
        "season": season_ref(code, current_matchday=current_matchday),
        "id": match_id,
        "utcDate": utc,
        "status": status,
        "matchday": matchday,
        "stage": stage,
        "group": group,
        "lastUpdated": last_updated,
        "homeTeam": team_ref(home),
        "awayTeam": team_ref(away),
        "score": {"winner": winner, "duration": duration,
                  "fullTime": {"home": full.home, "away": full.away},
                  "halfTime": {"home": half.home, "away": half.away}},
        "odds": {"msg": "Odds are not part of this plan."},
        "referees": ([] if referee is None else
                     [{"id": referee[0], "name": referee[1], "type": "REFEREE",
                       "nationality": referee[2]}]),
    }


def _day_of(m: dict) -> str:
    return m["utcDate"][:10]


def _result_set(matches: Sequence[dict], *, competitions: bool) -> dict:
    if not matches:
        return {"count": 0}
    days = sorted(_day_of(m) for m in matches)
    found: dict = {"count": len(matches)}
    if competitions:
        found["competitions"] = ",".join(dict.fromkeys(m["competition"]["code"]
                                                       for m in matches))
    found.update(first=days[0], last=days[-1],
                 played=sum(m["status"] == "FINISHED" for m in matches))
    return found


def day(matches: Sequence[dict], date_from: str, date_to: str) -> dict:
    """``/v4/matches?dateFrom=&dateTo=``: every listed match across competitions."""
    return {"filters": {"dateFrom": date_from, "dateTo": date_to, "permission": "TIER_ONE"},
            "resultSet": _result_set(matches, competitions=True),
            "matches": list(matches)}


def season_matches(code: str, matches: Sequence[dict], season: int = 2026) -> dict:
    """``/v4/competitions/{code}/matches?season=``."""
    return {"filters": {"season": str(season)},
            "resultSet": _result_set(matches, competitions=False),
            "competition": competition_ref(code),
            "matches": list(matches)}


# ------------------------------------------------------------------ standings


def table_rows(matches: Iterable[dict], clubs: Iterable[Club]) -> list[dict]:
    """Standings rows tallied from the FINISHED and AWARDED matches, ordered by points, goal
    difference, goals for, then name. Positions run 1, 2, 3 as football-data.org numbers them
    (it never shares one)."""
    rows = {club.id: dict(club=club, played=0, won=0, draw=0, lost=0, gf=0, ga=0)
            for club in clubs}
    for m in matches:
        if m["status"] not in ("FINISHED", "AWARDED"):
            continue
        full = m["score"]["fullTime"]
        for side, gf, ga in (("homeTeam", full["home"], full["away"]),
                             ("awayTeam", full["away"], full["home"])):
            row = rows.get(m[side]["id"])
            if row is None:
                continue
            row["played"] += 1
            row["won"] += gf > ga
            row["draw"] += gf == ga
            row["lost"] += gf < ga
            row["gf"] += gf
            row["ga"] += ga
    ordered = sorted(rows.values(), key=lambda r: (-(3 * r["won"] + r["draw"]),
                                                   -(r["gf"] - r["ga"]), -r["gf"],
                                                   r["club"].name))
    return [{"position": n, "team": team_ref(r["club"]), "playedGames": r["played"],
             "form": None, "won": r["won"], "draw": r["draw"], "lost": r["lost"],
             "points": 3 * r["won"] + r["draw"], "goalsFor": r["gf"], "goalsAgainst": r["ga"],
             "goalDifference": r["gf"] - r["ga"]}
            for n, r in enumerate(ordered, start=1)]


def standings(code: str, rows: Sequence[dict], *, season: int = 2026,
              stage: str = "REGULAR_SEASON", group: str | None = "Matchday",
              types: Sequence[str] = ("TOTAL",), current_matchday: int | None = 14) -> dict:
    """``/v4/competitions/{code}/standings``. The current season has one TOTAL table (the
    free plan ignores ``standingType``); a past one has TOTAL, HOME and AWAY, which a caller
    asks for with ``types``. The HOME and AWAY tables repeat ``rows``: a builder does not
    derive them."""
    meta = COMPETITION_META[code]
    return {"filters": {"season": str(season)},
            "area": area(meta["area"][1], meta["area"][2], meta["area"][0]),
            "competition": competition_ref(code),
            "season": season_ref(code, current_matchday=current_matchday),
            "standings": [{"stage": stage, "type": kind, "group": group, "table": list(rows)}
                          for kind in types]}


# ------------------------------------------------------------------ teams and squads


def squad_entry(player: Player) -> dict:
    return {"id": player.fd_id, "name": player.name, "position": player.position,
            "dateOfBirth": player.born, "nationality": player.nationality}


def team(club: Club, squad: Sequence[Player] = (), *, running: Sequence[str] = ("PD",),
         coach: tuple[str, str, str, int] | None = None) -> dict:
    """One club of ``/v4/competitions/{code}/teams``, with its squad inline."""
    name, born, nationality, coach_id = coach or (f"{club.short} Coach", "1975-01-01",
                                                  club.area, (club.id or 0) + 1000000)
    first, _, last = name.rpartition(" ")
    return {
        "area": area(club.area, club.area_code),
        **{k: v for k, v in team_record(club).items() if k != "lastUpdated"},
        "runningCompetitions": [competition_ref(code) for code in running],
        "coach": {"id": coach_id, "firstName": first or None, "lastName": last or None,
                  "name": name, "dateOfBirth": born, "nationality": nationality,
                  "contract": {"start": None, "until": None}},
        "squad": [squad_entry(p) for p in squad],
        "staff": [],
        "lastUpdated": STAMP,
    }


def teams(code: str, entries: Sequence[dict], season: int = 2026) -> dict:
    """``/v4/competitions/{code}/teams?season=``: ``entries`` from ``team``."""
    return {"count": len(entries), "filters": {"season": str(season)},
            "competition": competition_ref(code), "season": season_ref(code),
            "teams": list(entries)}


# ------------------------------------------------------------------ scorers


def _player_record(player: Player) -> dict:
    return {"id": player.fd_id, "name": player.name, "firstName": player.first,
            "lastName": player.last, "dateOfBirth": player.born,
            "nationality": player.nationality, "section": player.section,
            "position": None, "shirtNumber": player.shirt, "lastUpdated": STAMP}


def scorer(player: Player, club: Club, goals: int, *, assists: int | None = None,
           penalties: int | None = None, played: int = 10) -> dict:
    """One scorers line. ``assists`` and ``penalties`` are ``None`` where the source records
    none, as it sends them (it never sends 0). ``played`` is ``playedMatches``, which the
    normaliser drops (B1)."""
    return {"player": _player_record(player), "team": team_record(club),
            "playedMatches": played, "goals": goals, "assists": assists,
            "penalties": penalties}


def scorers(code: str, lines: Sequence[dict], *, limit: int = 500, season: int = 2026) -> dict:
    """``/v4/competitions/{code}/scorers?limit=``: the first ``limit`` lines, with ``count`` the
    number listed. A list as long as its limit is cut (B2)."""
    listed = list(lines)[:limit]
    return {"count": len(listed), "filters": {"season": str(season), "limit": limit},
            "competition": competition_ref(code), "season": season_ref(code),
            "scorers": listed}


# ------------------------------------------------------------------ persons


def person(player: Player, club: Club = MADRID, *, running: Sequence[str] = ("PD", "CL"),
           shirt: int | None = 99) -> dict:
    """``/v4/persons/{id}``. ``shirtNumber`` is football-data.org's, which is not the club's
    number (it can be a national team's), so it differs from the squad list's on purpose."""
    current = {
        "area": area(club.area, club.area_code),
        **{k: v for k, v in team_record(club).items() if k != "lastUpdated"},
        "runningCompetitions": [competition_ref(code) for code in running],
        "contract": {"start": "2024-07", "until": None},
    }
    return {**_player_record(player), "position": player.position, "shirtNumber": shirt,
            "currentTeam": current}


def person_matches(player: Player, matches: Sequence[dict], *,
                   competitions: Sequence[str] = ("PD", "CL"), limit: int = 50) -> dict:
    """``/v4/persons/{id}/matches?limit=&competitions=``: the matches he was named for."""
    listed = list(matches)[:limit]
    found = _result_set(listed, competitions=True)
    found.pop("played", None)
    return {"filters": {"limit": limit, "offset": 0, "competitions": ",".join(competitions),
                        "permission": "TIER_ONE"},
            "resultSet": found,
            "aggregations": "Aggregations are not part of this plan.",
            "person": _player_record(player) | {"position": None, "shirtNumber": None},
            "matches": listed}


def competitions(codes: Iterable[str] | None = None, *,
                 winners: dict[str, Club] | None = None,
                 matchdays: dict[str, int] | None = None) -> dict:
    """``/v4/competitions``: the competitions the free plan lists (``COMPETITION_META``)."""
    winners = winners or {}
    matchdays = matchdays or {}
    listed = []
    for code in codes or COMPETITION_META:
        meta = COMPETITION_META[code]
        listed.append({
            "id": meta["id"],
            "area": area(meta["area"][1], meta["area"][2], meta["area"][0]),
            "name": meta["name"], "code": code, "type": meta["type"],
            "emblem": f"{_ASSET}/emblems/{code.lower()}.png", "plan": meta["plan"],
            "currentSeason": season_ref(code, current_matchday=matchdays.get(code, 14),
                                        winner=winners.get(code)),
            "numberOfAvailableSeasons": 4,
            "lastUpdated": STAMP,
        })
    return {"count": len(listed), "filters": {"client": "synthetic"}, "competitions": listed}


# ------------------------------------------------------------------ errors and headers

ERRORS: dict[str, tuple[int, str]] = {
    "token": (400, "Your API token is invalid."),
    "unauthorised": (401, "Authentication failed."),
    "restricted": (403, "The resource you are looking for is restricted and apparently not "
                        "within your permissions. Please check your subscription."),
    "not_found": (404, "The resource you are looking for does not exist."),
    "throttled": (429, "You reached your request limit. Wait 4 seconds."),
}
"""The five error replies, by kind: (status, message). A client maps on the status and
``errorCode`` only, and never echoes the message."""


def error(kind: str) -> tuple[int, dict]:
    """(status, body) of an error reply: ``{"message": ..., "errorCode": status}``."""
    status, message = ERRORS[kind]
    return status, {"message": message, "errorCode": status}


def rate_headers(available: int = 9, reset: int = 60) -> dict[str, str]:
    """The headers football-data.org sends with every reply, in its own spelling (a reader
    must match them without regard to case)."""
    return {"X-API-Version": "v4", "X-Requestcounter-Reset": str(reset),
            "X-Requests-Available-Minute": str(available)}


def response(body: Any, status: int = 200, *, available: int = 9, reset: int = 60,
             request: httpx.Request | None = None) -> httpx.Response:
    """An ``httpx.Response`` carrying ``body`` as JSON and the rate headers."""
    headers = {"Content-Type": "application/json;charset=UTF-8",
               **rate_headers(available, reset)}
    return httpx.Response(status, headers=headers, content=json.dumps(body).encode(),
                          request=request)


# ------------------------------------------------------------------ a small consistent season


def _md(n: int) -> str:
    return (date(2026, 8, 22) + timedelta(days=7 * (n - 1))).isoformat()


@dataclass
class World:
    """A small invented season football-data.org could serve, and the handler that serves it.

    ``handler`` answers the v4 paths of PLAN 3.4 from the world's data, filtering as the API
    does (``dateFrom``/``dateTo`` by UTC date, ``limit``, a person's ``competitions``). Every
    request is recorded in ``calls`` (path and query, never a header). ``token`` is the
    ``X-Auth-Token`` the world accepts; any other answers 400. ``fail`` maps a path prefix
    (after ``/v4``) to an error kind of ``ERRORS``, for a test that needs one resource to fail.
    ``matches`` is the 2026 season by competition code; ``past`` holds earlier seasons by
    (code, year), and a season before 2023 answers 403 as the free plan does.
    """

    matches: dict[str, list[dict]] = field(default_factory=dict)
    clubs: dict[str, list[Club]] = field(default_factory=dict)
    squads: dict[int, tuple[Player, ...]] = field(default_factory=dict)
    scorer_lines: dict[str, list[dict]] = field(default_factory=dict)
    named: dict[int, list[int]] = field(default_factory=dict)
    winners: dict[str, Club] = field(default_factory=dict)
    past: dict[tuple[str, int], list[dict]] = field(default_factory=dict)
    token: str = "test-only"
    fail: dict[str, str] = field(default_factory=dict)
    available: int = 9
    reset: int = 60
    calls: list[str] = field(default_factory=list)

    def all_matches(self) -> list[dict]:
        return [m for listed in self.matches.values() for m in listed]

    def players(self) -> dict[int, tuple[Player, Club]]:
        found = {}
        for listed in self.clubs.values():
            for club in listed:
                for player in self.squads.get(club.id, ()):
                    found.setdefault(player.fd_id, (player, club))
        return found

    def body(self, path: str, query: dict[str, str]) -> tuple[int, Any]:
        """(status, body) for one request path (after ``/v4``) and its query."""
        for prefix, kind in self.fail.items():
            if path.startswith(prefix):
                return error(kind)
        parts = [p for p in path.split("/") if p]
        if parts == ["competitions"]:
            return 200, competitions(winners=self.winners)
        if parts == ["matches"]:
            start, end = query.get("dateFrom"), query.get("dateTo")
            if not start or not end:
                return 400, {"message": "Both dates are required.", "errorCode": 400}
            found = sorted((m for m in self.all_matches() if start <= _day_of(m) <= end),
                           key=lambda m: (m["utcDate"], m["id"]))
            return 200, day(found, start, end)
        if len(parts) == 3 and parts[0] == "competitions":
            code, what = parts[1], parts[2]
            if code not in self.matches:
                return error("restricted")
            season = int(query.get("season", "2026"))
            if season < 2023:
                return error("restricted")
            current = season == 2026
            listed = self.matches[code] if current else self.past.get((code, season), [])
            if what == "matches":
                return 200, season_matches(code, listed, season)
            if what == "standings":
                rows = table_rows(listed, self.clubs.get(code, ()))
                if not current:
                    return 200, standings(code, rows, season=season, group=None,
                                          types=("TOTAL", "HOME", "AWAY"), current_matchday=38)
                if code == "CL":
                    return 200, standings(code, rows, stage="LEAGUE_STAGE",
                                          group="League phase", current_matchday=2)
                return 200, standings(code, rows, season=season)
            if what == "teams":
                entries = [team(c, self.squads.get(c.id, ()), running=[code],
                                coach=COACH if c.id == MADRID.id else None)
                           for c in self.clubs.get(code, ())]
                return 200, teams(code, entries, season)
            if what == "scorers":
                return 200, scorers(code, self.scorer_lines.get(code, []),
                                    limit=int(query.get("limit", "10")), season=season)
        if len(parts) in (2, 3) and parts[0] == "persons" and parts[1].isdigit():
            found = self.players().get(int(parts[1]))
            if found is None:
                return error("not_found")
            player, club = found
            if len(parts) == 2:
                return 200, person(player, club)
            if parts[2] == "matches":
                codes = query.get("competitions", "").split(",") if query.get(
                    "competitions") else list(self.matches)
                ids = set(self.named.get(player.fd_id, ()))
                listed = sorted((m for m in self.all_matches()
                                 if m["id"] in ids and m["competition"]["code"] in codes),
                                key=lambda m: (m["utcDate"], m["id"]))
                return 200, person_matches(player, listed, competitions=codes,
                                           limit=int(query.get("limit", "15")))
        return error("not_found")

    def reply(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append(path + (f"?{request.url.query.decode()}" if request.url.query else ""))
        if request.headers.get("X-Auth-Token") != self.token:
            status, body = error("token")
        elif not path.startswith("/v4/"):
            status, body = error("not_found")
        else:
            status, body = self.body(path.removeprefix("/v4"), dict(request.url.params))
        available = 0 if status == 429 else self.available
        return response(body, status, available=available, reset=self.reset, request=request)

    @property
    def handler(self) -> Callable[[httpx.Request], httpx.Response]:
        """The function ``httpx.MockTransport`` takes."""
        return self.reply

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.reply)


def sample_world() -> World:
    """A small season around the Madrid-like club, with every status somewhere in it.

    Today is taken to be Friday 27 November 2026. La Liga has four clubs and the Champions
    League four; the Premier League has two, enough for a day across competitions. Madrid
    plays Norte on Saturday 28 November at 20:00 UTC (TIMED). On the 27th a La Liga match is
    IN_PLAY, a Champions League match PAUSED and a Premier League match SUSPENDED; one
    Premier League match was CANCELLED, one La Liga match POSTPONED and one AWARDED, and a
    Champions League play-off is SCHEDULED between clubs not yet known.
    """
    ref = (95001, "Iván Silbato", "Spain")
    pd = [
        match(100001, f"{_md(1)}T19:00:00Z", MADRID, A_FC, status="FINISHED", result=(3, 1),
              half_time=(1, 0), matchday=1, referee=ref),
        match(100002, f"{_md(1)}T17:00:00Z", NORTE, RIBERA, status="FINISHED", result=(0, 0),
              half_time=(0, 0), matchday=1, referee=(95002, "Pau Arbitro", None)),
        match(100003, f"{_md(2)}T19:30:00Z", RIBERA, MADRID, status="FINISHED", result=(1, 2),
              half_time=(1, 1), matchday=2, referee=ref),
        match(100004, f"{_md(2)}T17:00:00Z", A_FC, NORTE, status="FINISHED", result=(2, 2),
              half_time=(0, 1), matchday=2),
        match(100005, "2026-10-04T15:00:00Z", NORTE, A_FC, status="AWARDED", result=(0, 3),
              matchday=3),
        match(100006, "2026-11-01T20:00:00Z", A_FC, MADRID, status="POSTPONED", matchday=3),
        match(100007, "2026-11-27T20:00:00Z", RIBERA, A_FC, status="IN_PLAY", result=(1, 0),
              half_time=(1, 0), matchday=4),
        match(100008, "2026-11-28T20:00:00Z", MADRID, NORTE, status="TIMED", matchday=4),
        match(100009, "2026-12-06T00:00:00Z", NORTE, MADRID, status="SCHEDULED", matchday=5),
    ]
    cl = [
        match(200001, "2026-09-16T19:00:00Z", MADRID, TEST_ROMA, code="CL", status="FINISHED",
              result=(2, 0), half_time=(1, 0), matchday=1, stage="LEAGUE_STAGE"),
        match(200002, "2026-09-16T19:00:00Z", TEST_PORTO, NORD, code="CL", status="FINISHED",
              result=(1, 1), half_time=(0, 1), matchday=1, stage="LEAGUE_STAGE"),
        match(200003, "2026-11-24T20:00:00Z", TEST_ROMA, MADRID, code="CL", status="FINISHED",
              result=(1, 3), half_time=(1, 1), matchday=2, stage="LEAGUE_STAGE",
              referee=(95003, "Lars Pfeife", "Testland")),
        match(200004, "2026-11-27T17:45:00Z", TEST_PORTO, TEST_ROMA, code="CL",
              status="PAUSED", result=(0, 1), half_time=(0, 1), matchday=2,
              stage="LEAGUE_STAGE"),
        match(200005, "2027-02-16T00:00:00Z", TBD, TBD, code="CL", status="SCHEDULED",
              matchday=None, stage="PLAYOFFS"),
    ]
    pl = [
        match(300001, "2026-11-25T20:00:00Z", TEST_CITY, TEST_ALBION, code="PL",
              status="CANCELLED", matchday=12),
        match(300002, "2026-11-26T20:00:00Z", TEST_ALBION, TEST_CITY, code="PL",
              status="FINISHED", result=(2, 1), half_time=(2, 1), matchday=13),
        match(300003, "2026-11-27T12:30:00Z", TEST_CITY, TEST_ALBION, code="PL",
              status="SUSPENDED", matchday=14),
    ]
    madrid_squad = SQUAD
    # Three invented players for each other club, a family name per club and dates of birth
    # no Madrid player shares, so a join by date of birth and surname finds none of them.
    positions = ("Goalkeeper", "Defence", "Offence")
    others = {club.id: tuple(
        Player(fd_id=71000 + 10 * n + k, name=f"{first} {family}",
               born=f"{1990 + n}-0{k + 1}-1{k}", nationality=club.area, position=position,
               shirt=None, group=None, wp_title=None, wp_name=None)
        for k, (first, position) in enumerate(zip(("Andres", "Bruno", "Ciro"), positions,
                                                  strict=True)))
        for n, (club, family) in enumerate(zip(
            (A_FC, NORTE, RIBERA, TEST_ROMA, TEST_PORTO, NORD, TEST_ALBION, TEST_CITY),
            ("Arco", "Brisa", "Cumbre", "Duna", "Estela", "Faro", "Glaciar", "Horizonte"),
            strict=True), start=1)}
    by_name = {p.name: p for p in SQUAD}
    a_striker = others[A_FC.id][2]
    pd_lines = [
        scorer(by_name["Kai Delantero"], MADRID, 3, assists=1, penalties=1),
        scorer(by_name["Vinicio Ala"], MADRID, 1, assists=2),
        scorer(a_striker, A_FC, 3, penalties=None),
        scorer(by_name["Carlos Punta"], MADRID, 1),
    ]
    cl_lines = [
        scorer(by_name["Kai Delantero"], MADRID, 2, assists=None, penalties=None),
        scorer(by_name["Nico Enlace"], MADRID, 2, assists=1),
        scorer(others[TEST_ROMA.id][2], TEST_ROMA, 1),
    ]
    played = [m["id"] for m in pd + cl
              if m["status"] == "FINISHED" and MADRID.id in (m["homeTeam"]["id"],
                                                               m["awayTeam"]["id"])]
    named = {p.fd_id: (played if p.group not in (None,) else []) for p in madrid_squad}
    named[by_name["Bruno Guante"].fd_id] = played[:2]
    return World(
        matches={"PD": pd, "CL": cl, "PL": pl},
        clubs={"PD": [MADRID, A_FC, NORTE, RIBERA], "CL": [MADRID, TEST_ROMA, TEST_PORTO, NORD],
               "PL": [TEST_ALBION, TEST_CITY]},
        squads={MADRID.id: madrid_squad, **others},
        scorer_lines={"PD": pd_lines, "CL": cl_lines},
        named=named,
        winners={"WC": TESTLAND},
    )


# ------------------------------------------------------------------ the shape contract


def paths(node: Any, prefix: str = "") -> set[str]:
    """The dotted key paths of a JSON-like reply, ``[]`` marking a list item: the form the
    fields file writes them in."""
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{prefix}.{key}" if prefix else key
            found.add(here)
            found |= paths(value, here)
    elif isinstance(node, list):
        for item in node:
            found |= paths(item, f"{prefix}[]")
    return found
