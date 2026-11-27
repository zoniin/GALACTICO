"""OpenFootball and OpenLigaDB rows as the season model's ``Match`` (PLAN D3-A).

Without a football-data.org key the season pages read the six competitions the free feeds
cover, as the Matches board does today: OpenFootball's five league files (the Bundesliga and
the Premier League filled from OpenLigaDB by ``openligadb.fill``) and OpenLigaDB's Champions
League (``openligadb.europe``). ``OpenFootball.league`` gives each as one ``League`` of
OpenFootball-shaped rows; ``league_matches`` turns those rows into ``Match`` objects. A raw
OpenLigaDB record (the goal feed, and the Europa League a later wave adds) is read by
``ol_match``.

What each field takes, and from where:

- **key**: the match key of the two clubs and the Europe/Madrid day (``keys.match_key``),
  slug-only, since no football-data.org id is known; **legacy_keys**: the board's id
  (``es.1-2026-<hash16>``), which every existing link carries, computed by the board's own
  function so the two never differ;
- **kickoff_utc**: the instant ``kickoff.py`` gives the row (the source's stated UTC, else its
  published local time in the competition's zone); ``None`` where the time or zone is not
  known, and then ``kickoff_confirmed`` is false and the status SCHEDULED;
- **status**: FINISHED where the row carries a final result, else TIMED or SCHEDULED. A free
  file's fixture without a result may have been played: the status says what the row says,
  and the freshness lines say how far the results reach;
- **result** and **half_time**: as the row states them; **winner**: from the result, in a
  league or a league phase only (a knockout tie level after play is decided by more than its
  result); **duration**, **referee**, **report_url**, **source_updated**: not stated, ``None``;
- **stage**: football-data.org's stage words, so one vocabulary serves every source:
  ``REGULAR_SEASON`` for a league, ``LEAGUE_STAGE`` for a league phase, the knockout rounds
  by ``KNOCKOUT_STAGES``; a round not listed there has no stage;
- **clubs**: the name as the feed writes it (OpenLigaDB's German forms already English, by
  ``openligadb.CLUB_NAMES``); Real Madrid is ``wiki_season.MADRID_REF`` whichever feed names
  it, so the club the site is about has one key in every mode;
- **sources**: OpenFootball for its rows, plus OpenLigaDB where a result was filled from it;
  OpenLigaDB alone for a European competition.

Claim: every field is a field of the row or the rule above. Non-claim: nothing here checks a
row against another source; the crosswalk joins them.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime

from ..kickoff import from_utc, utc_text
from ..openfootball import COMPETITIONS as BOARD_COMPETITIONS
from ..openfootball import League, _fixture, final_score
from ..openligadb import club_name
from .competitions import BY_SLUG, season_label
from .crosswalk import MADRID_FORM, club_form
from .keys import match_key, plate, slugify
from .model import Match, Side, SourceRef, TeamRef
from .wiki_season import MADRID_REF

__all__ = ["FREE", "FREE_SLUGS", "CODE_OF", "OL_SHORTCUT", "KNOCKOUT_STAGES",
           "OPENFOOTBALL_URL", "OPENLIGADB_URL", "team_ref", "league_matches", "ol_result",
           "ol_match", "ol_matches", "madrid_day"]

OPENFOOTBALL_URL = "https://github.com/openfootball/football.json"
OPENLIGADB_URL = "https://www.openligadb.de/"

FREE: dict[str, str] = {"la-liga": "es.1", "champions-league": "ucl",
                        "premier-league": "en.1", "bundesliga": "de.1", "serie-a": "it.1",
                        "ligue-1": "fr.1"}
"""The six competitions the free feeds carry, by slug, with the board's competition code
(``openfootball.COMPETITIONS``), in PR 2.1's order."""
FREE_SLUGS: tuple[str, ...] = tuple(sorted(FREE, key=lambda slug: BY_SLUG[slug].order))
CODE_OF: dict[str, str] = {code: slug for slug, code in FREE.items()}
assert set(CODE_OF) == set(BOARD_COMPETITIONS), "the six free competitions are the board's"

OL_SHORTCUT: dict[str, str] = {"champions-league": "ucl", "bundesliga": "bl1",
                               "europa-league": "uel2026"}
"""The competitions whose goals OpenLigaDB names, by its league shortcut (B11). The
Premier League's shortcut fills results only: its goal reports are not read (PR 2.1)."""

KNOCKOUT_STAGES: dict[str, str] = {
    "knockout play-offs": "PLAYOFFS", "round of 16": "LAST_16",
    "quarter-finals": "QUARTER_FINALS", "semi-finals": "SEMI_FINALS", "final": "FINAL",
    "playoffs": "PLAYOFFS", "achtelfinale": "LAST_16", "viertelfinale": "QUARTER_FINALS",
    "halbfinale": "SEMI_FINALS", "finale": "FINAL",
}
"""A European round as the free feeds write it, and football-data.org's stage word for it."""

_MATCHDAY = re.compile(r"Matchday (\d{1,2})")
_SPIELTAG = re.compile(r"(\d{1,2})\.\s*Spieltag")
_LEAGUE_STAGES = frozenset({"REGULAR_SEASON", "LEAGUE_STAGE"})


def madrid_day(kickoff_utc: str | None, fallback: str) -> str:
    """The Europe/Madrid day of an instant, else the row's own date."""
    if kickoff_utc:
        try:
            instant = datetime.fromisoformat(kickoff_utc.replace("Z", "+00:00"))
        except ValueError:
            return fallback
        return from_utc(instant, "CET").date().isoformat()
    return fallback


def team_ref(name: str) -> TeamRef | None:
    """A club as a free feed names it; Real Madrid as ``MADRID_REF``. ``None`` for a name with
    no slug (the row is then left out)."""
    name = " ".join(str(name).split())
    if club_form(name) == MADRID_FORM:
        return MADRID_REF
    slug = slugify(name)
    if not slug:
        return None
    try:
        return TeamRef(key=slug, fd_id=None, name=name, short=name, plate=plate(name))
    except ValueError:
        return None


def _winner(result: Side, stage: str | None) -> str | None:
    if stage not in _LEAGUE_STAGES or result.home is None or result.away is None:
        return None
    if result.home == result.away:
        return "DRAW"
    return "HOME_TEAM" if result.home > result.away else "AWAY_TEAM"


def _half(row: Mapping) -> Side:
    score = row.get("score")
    half = score.get("ht") if isinstance(score, Mapping) else None
    if (isinstance(half, list) and len(half) == 2
            and all(type(n) is int and n >= 0 for n in half)):
        return Side(half[0], half[1])
    return Side(None, None)


def _stage(code: str, row: Mapping) -> tuple[str | None, int | None]:
    found = _MATCHDAY.fullmatch(str(row.get("round") or ""))
    matchday = int(found[1]) if found else None
    if code != "ucl":
        return "REGULAR_SEASON", matchday
    if row.get("stage", "league") == "league":
        return "LEAGUE_STAGE", matchday
    return KNOCKOUT_STAGES.get(str(row.get("round") or "").casefold()), None


def _sources(code: str, row: Mapping, checked: str) -> tuple[SourceRef, ...]:
    ligadb = SourceRef("openligadb", checked, None, None, OPENLIGADB_URL)
    if code == "ucl":
        return (ligadb,)
    own = SourceRef("openfootball", checked, None, None, OPENFOOTBALL_URL)
    return (own, ligadb) if row.get("filled") == "openligadb" else (own,)


def league_matches(league: League, *, today: date) -> list[Match]:
    """Every row of ``league`` as a ``Match``, in the league's row order. A row whose clubs
    give no key is left out."""
    slug = CODE_OF[league.code]
    config = BY_SLUG[slug]
    season = season_label(config, league.year)
    found = []
    for row in league.rows:
        home, away = team_ref(row["team1"]), team_ref(row["team2"])
        if home is None or away is None:
            continue
        board = _fixture(league.code, league.year, row, today)
        kickoff = board["kickoff_utc"]
        result = final_score(row)
        side = Side(*result) if result is not None else Side(None, None)
        stage, matchday = _stage(league.code, row)
        day = madrid_day(kickoff, row["date"])
        found.append(Match(
            key=match_key(None, home.short, away.short, day), fd_id=None,
            legacy_keys=(board["id"],), competition=slug, season=season, stage=stage,
            matchday=matchday, group=None, kickoff_utc=kickoff,
            kickoff_confirmed=kickoff is not None,
            status="FINISHED" if result is not None else ("TIMED" if kickoff else "SCHEDULED"),
            home=home, away=away, result=side, half_time=_half(row),
            duration=None, winner=_winner(side, stage), referee=None, ground=None,
            attendance=None, report_url=None, source_updated=None,
            sources=_sources(league.code, row, league.checked)))
    return found


def _instant(raw: Mapping) -> datetime | None:
    try:
        value = datetime.fromisoformat(str(raw["matchDateTimeUTC"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return None
    return value if value.tzinfo is not None else None


def _whole(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def ol_result(raw: Mapping) -> Side | None:
    """The final result an OpenLigaDB record states (result type 2 of a finished match)."""
    if raw.get("matchIsFinished") is not True:
        return None
    for result in raw.get("matchResults") or ():
        if isinstance(result, Mapping) and result.get("resultTypeID") == 2:
            home, away = _whole(result.get("pointsTeam1")), _whole(result.get("pointsTeam2"))
            if home is not None and away is not None:
                return Side(home, away)
    return None


def ol_match(raw: object, slug: str, year: int, checked: str) -> Match | None:
    """One OpenLigaDB match record of competition ``slug``'s season ``year`` as a ``Match``;
    ``None`` for a record without both clubs, an id or a kick-off instant."""
    if not isinstance(raw, Mapping) or _whole(raw.get("matchID")) is None:
        return None
    teams = []
    for side in ("team1", "team2"):
        club = raw.get(side)
        name = club.get("teamName") if isinstance(club, Mapping) else None
        teams.append(team_ref(club_name(name)) if isinstance(name, str) and name.strip()
                     else None)
    home, away = teams
    instant = _instant(raw)
    if home is None or away is None or instant is None:
        return None
    config = BY_SLUG[slug]
    group = raw.get("group") if isinstance(raw.get("group"), Mapping) else {}
    name = str(group.get("groupName") or "")
    if config.kind == "league":
        stage, matchday = "REGULAR_SEASON", _whole(group.get("groupOrderID"))
    elif (phase := _SPIELTAG.search(name)) is not None:
        stage, matchday = "LEAGUE_STAGE", int(phase[1])
    else:
        stage = KNOCKOUT_STAGES.get(re.sub(r"[^a-z]", "", name.casefold()))
        matchday = None
    result = ol_result(raw)
    side = result if result is not None else Side(None, None)
    location = raw.get("location") if isinstance(raw.get("location"), Mapping) else {}
    ground = location.get("locationStadium")
    kickoff = utc_text(instant)
    return Match(
        key=match_key(None, home.short, away.short, madrid_day(kickoff, kickoff[:10])),
        fd_id=None, legacy_keys=(), competition=slug, season=season_label(config, year),
        stage=stage, matchday=matchday, group=None, kickoff_utc=kickoff,
        kickoff_confirmed=True, status="FINISHED" if result is not None else "TIMED",
        home=home, away=away, result=side, half_time=Side(None, None), duration=None,
        winner=_winner(side, stage), referee=None,
        ground=" ".join(ground.split()) if isinstance(ground, str) and ground.strip() else None,
        attendance=_whole(raw.get("numberOfViewers")) or None, report_url=None,
        source_updated=None,
        sources=(SourceRef("openligadb", checked, None, None, OPENLIGADB_URL),))


def ol_matches(payload: Sequence, slug: str, year: int, checked: str) -> list[Match]:
    """Every readable record of an OpenLigaDB season, by kick-off then home club."""
    found = [m for m in (ol_match(raw, slug, year, checked) for raw in payload or ())
             if m is not None]
    return sorted(found, key=lambda m: (m.kickoff_utc or "", m.home.name, m.key))
