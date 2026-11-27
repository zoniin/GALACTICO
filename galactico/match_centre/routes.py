"""The public centre is constructed without a licensed data adapter.

Every page is served through the site shell (``galactico.site_nav``), which fills in the header,
the navigation and the footer for the app that serves it. ``/`` is the Matches page on every app
that includes this router; an old Player Lab link to ``/`` with a player or a view in its query
is sent to ``/player`` where the app serves it.

``make_router`` also builds the season catalogue (``season.catalog.Catalog``, ADR-0036) on the
same OpenFootball reader and squad list as the board, with the football-data.org client it is
handed (``None`` without a key) and the Wikipedia and Wikidata readers. No route reads it yet:
the season pages do (PLAN phase P). The router's lifespan closes the client's connections.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from .. import site_nav
from .api_football import ApiFootball
from .feed import FeedError
from .goal_scout import LEAGUES as GOAL_LEAGUES
from .goal_scout import GoalScout, goal_error, league_options, missing_club, unknown_league
from .openfootball import COMPETITIONS, LEAGUES, NoSeason, OpenFootball, parse_key, season_start
from .scouting import LEAGUES as SCOUT_LEAGUES
from .scouting import (
    METRICS,
    ROLES,
    SPLIT_ALIASES,
    SPLITS,
    Scouting,
    baseline_error,
    baseline_lines,
    teams,
)
from .season.catalog import PASSED_GATES, Catalog
from .season.football_data import FootballData
from .season.infobox import Infoboxes
from .season.revisions import Revisions
from .season.wiki_season import MadridSeason
from .season.wikidata import Wikidata
from .studio import ANALYST_TOOLS, Studio, next_card, opponent_goals_link

LINK_WAIT = 2.5
"""Seconds a page waits for the sentence of the view its link opens (the card a shared link
shows); past it, the page's own description stands."""

WEB = Path(__file__).resolve().parents[2] / "web"

PLAYER_LAB_QUERY = ("player", "view")
"""Query keys of an old Player Lab link to ``/``. Such a link opens ``/player``."""


def season_catalog(public: OpenFootball, studio: Studio,
                   football: FootballData | None) -> Catalog:
    """The season catalogue of one app: the board's OpenFootball reader (and through it its
    OpenLigaDB reader), the Lineup's squad list, football-data.org where ``football`` is a
    client, Real Madrid's season article, the players' infoboxes, the article's revisions,
    Wikidata, and the root decisions passed (``PASSED_GATES``)."""
    return Catalog(football=football, openfootball=public, studio=studio,
                   madrid=MadridSeason(), wikidata=Wikidata(), infoboxes=Infoboxes(),
                   revisions=Revisions(), gates=PASSED_GATES)


def make_router(private: ApiFootball | None = None, *,
                football: FootballData | None = None) -> APIRouter:
    """The match centre's routes. ``football`` is the football-data.org client the season
    catalogue reads (``None``: none, the free sources only); the catalogue is the router's
    ``catalog``."""

    @asynccontextmanager
    async def lifespan(_app) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if football is not None:
                await football.aclose()

    router = APIRouter(lifespan=lifespan)
    studio = Studio()
    # A Real Madrid scorer is written as the squad list writes him on every page (names.py).
    public = OpenFootball(names=lambda day: studio.squad_names(day))
    router.catalog = season_catalog(public, studio, football)

    async def in_time(work, fallback=None):
        # The sentence a shared link's card shows, if it comes in time; else the page's own.
        try:
            return await asyncio.wait_for(work, LINK_WAIT)
        except (TimeoutError, FeedError, ValueError):
            return fallback

    async def match_page(request: Request):
        key = request.query_params.get("match", "")
        line = None
        if (parsed := parse_key(key)) is not None:
            found = await in_time(public.detail(*parsed, key, datetime.now(UTC).date()))
            line = (found or {}).get("line")
        return site_nav.page(request, "matches", description=line)

    @router.get("/", include_in_schema=False, response_class=HTMLResponse)
    async def home(request: Request):
        player_lab = site_nav.PAGES["player"].path
        if (any(key in request.query_params for key in PLAYER_LAB_QUERY)
                and player_lab in site_nav.served_paths(request.app)):
            query = urlencode(list(request.query_params.multi_items()))
            # Player Lab moved for good: a permanent redirect that keeps the method (308).
            return RedirectResponse(player_lab + (f"?{query}" if query else ""), 308)
        return await match_page(request)

    @router.get("/about", include_in_schema=False, response_class=HTMLResponse)
    def about(request: Request):
        return site_nav.about(request)

    @router.get("/lineup", include_in_schema=False, response_class=HTMLResponse)
    async def lineup(request: Request):
        query = request.query_params
        said = None
        if "xi" in query or "formation" in query:
            found = await in_time(studio.compare(datetime.now(UTC).date(),
                                                 query.get("formation", "")[:8],
                                                 query.get("xi", "")[:40],
                                                 query.get("season", "")[:8] or None))
            said = (found or {}).get("answer")
        # The analyst's import shows only on a local install, the app that serves the archive.
        local = site_nav.PAGES["player"].path in site_nav.served_paths(request.app)
        return site_nav.page(request, "lineup", description=said,
                             slots={"tools": ANALYST_TOOLS if local else ""})

    # Lineup's replies. The CDN keeps a reply that carries no warning for a while and serves it
    # stale while it refreshes; nothing at all when the private feed is mounted.
    def studio_cache(response: Response, payload: dict, seconds: int) -> dict:
        if private is None and not payload.get("warning"):
            response.headers["Vercel-CDN-Cache-Control"] = (
                f"s-maxage={seconds}, stale-while-revalidate=3600, stale-if-error=86400")
        return payload

    # The squad, the formations and the XI the server proposes for each (F9).
    @router.get("/api/studio/squad")
    async def studio_squad(response: Response):
        try:
            payload = await studio.lineup(datetime.now(UTC).date())
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        return studio_cache(response, payload, 3600)

    # The squad's scorers this season, all competitions, by goals then name: the Players
    # page's first card (Wikipedia's counts; the sentence is the server's, R10).
    @router.get("/api/studio/scorers")
    async def studio_scorers(response: Response):
        try:
            payload = await studio.scorers(datetime.now(UTC).date())
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        return studio_cache(response, payload, 3600)

    # A lineup from a link or from the board, with its sentence (F12, R10).
    @router.get("/api/studio/lineup")
    async def studio_lineup(response: Response, formation: str = Query("", max_length=8),
                            xi: str = Query("", max_length=40),
                            season: str | None = Query(None, max_length=8)):
        try:
            payload = await studio.compare(datetime.now(UTC).date(), formation, xi, season)
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return studio_cache(response, payload, 3600)

    # Madrid's next fixture from the Matches page's schedule (F1). The goal explorer is linked
    # only where it covers the opponent's competition.
    @router.get("/api/studio/next")
    async def studio_next(response: Response):
        today = datetime.now(UTC).date()
        try:
            summary = await public.summary(today)
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        if summary.get("next") is None and summary.get("unavailable"):
            raise HTTPException(503, summary["unavailable"])
        card = next_card(summary.get("next"), today)
        if (fixture := card["fixture"]) is not None:
            fixture["links"]["goals"] = await opponent_goals_link(
                goals, fixture["code"], fixture["opponent"], today)
        return studio_cache(response, {**card, "warning": " ".join(summary.get("warnings") or [])
                                       or None}, 900)

    @router.get("/api/studio/activity/{player}")
    async def studio_activity(player: str, response: Response):
        try:
            sample = await studio.activity(player)
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        if sample is None:
            raise HTTPException(404, "No archived spatial sample for this player.")
        return studio_cache(response, sample, 86400)

    @router.get("/match-centre", include_in_schema=False, response_class=HTMLResponse)
    async def centre(request: Request):
        return await match_page(request)

    @router.get("/match-centre/leagues", include_in_schema=False, response_class=HTMLResponse)
    def leagues_page(request: Request):
        return site_nav.page(request, "table")

    # The public replies of Matches and Table: the CDN keeps each for a while and serves it
    # stale while it refreshes, but never a reply that carries a warning (a cached upstream, a
    # league that failed) and nothing at all when the private feed is mounted.
    def shared_cache(response: Response, payload: dict, seconds: int = 900) -> dict:
        if private is None and not payload.get("warnings"):
            response.headers["Vercel-CDN-Cache-Control"] = (
                f"s-maxage={seconds}, stale-while-revalidate=3600, stale-if-error=86400")
        return payload

    @router.get("/api/match-centre/leagues/{code}")
    async def competition(code: str, response: Response, day: date | None = None,
                          team: str | None = None):
        if code not in COMPETITIONS:
            raise HTTPException(404, "Unknown competition.")
        today = datetime.now(UTC).date()
        try:
            payload = await public.competition(code, day or today, today, team)
        except NoSeason as exc:
            raise HTTPException(404, str(exc)) from exc
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        return shared_cache(response, payload)

    # Table's first view: Madrid's place in each of their competitions, and the tab to open on.
    @router.get("/api/match-centre/standings")
    async def standings(response: Response):
        try:
            payload = await public.standings(datetime.now(UTC).date())
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        return shared_cache(response, payload)

    @router.get("/api/match-centre/summary")
    async def summary(response: Response):
        try:
            payload = await public.summary(datetime.now(UTC).date())
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        return shared_cache(response, payload) if payload["answer"] else payload

    @router.get("/api/match-centre/saved")
    async def saved(request: Request, response: Response):
        try:
            payload = await public.saved(request.query_params.getlist("id"),
                                         datetime.now(UTC).date())
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        return shared_cache(response, payload)

    # The demo printed invented figures beside real players' names (R8) and is gone. An old
    # link to it opens the Matches page, permanently (308).
    @router.get("/match-centre/demo", include_in_schema=False)
    def demo():
        return RedirectResponse("/match-centre", 308)

    @router.get("/match-centre/scouting", include_in_schema=False, response_class=HTMLResponse)
    def scouting_page(request: Request):
        # The competitions the goal feed carries are listed by the server, not the browser.
        return site_nav.page(request, "scouting", slots={"leagues": league_options()})

    goals = GoalScout(public)

    # Goals by opponent. The CDN keeps a reply with no warning for a while and serves it stale
    # while it refreshes; nothing at all when the private feed is mounted.
    def goals_cache(response: Response, report: dict, seconds: int) -> dict:
        if private is None and not report["warning"]:
            response.headers["Vercel-CDN-Cache-Control"] = (
                f"s-maxage={seconds}, stale-while-revalidate=3600, stale-if-error=86400")
        return report

    # The page's first view (F1, F20): Real Madrid's next opponent where the goal feed carries
    # its competition, else Real Madrid in the Champions League, with the line that says which.
    # ``asked`` is the league of an old link the feed does not carry ("es").
    @router.get("/api/match-centre/goal-scout")
    async def goal_default(response: Response, asked: str | None = Query(None, max_length=8)):
        today = datetime.now(UTC).date()
        # The schedules and the Champions League's goals are asked for at once (SPD-4).
        summary, _ = await asyncio.gather(public.summary(today), goals.prefetch(today),
                                          return_exceptions=True)
        if isinstance(summary, BaseException):
            if not isinstance(summary, FeedError):
                raise summary
            summary = None
        listed = summary is not None and not summary.get("unavailable")
        try:
            report = await goals.opening(today, (summary or {}).get("next"), listed=listed,
                                         asked=asked)
        except FeedError as exc:
            raise HTTPException(503, goal_error(exc)) from exc
        return goals_cache(response, report, 900)

    @router.get("/api/match-centre/goal-scout/{league}")
    async def goal_report(league: str, response: Response, club: int | None = Query(None, gt=0),
                          opponent: str | None = Query(None, max_length=80)):
        if league not in GOAL_LEAGUES:
            raise HTTPException(404, unknown_league(league))
        try:
            report = await goals.report(league, club, datetime.now(UTC).date(), opponent)
        except FeedError as exc:
            raise HTTPException(503, goal_error(exc)) from exc
        if report is None:
            raise HTTPException(404, missing_club(league))
        return goals_cache(response, report, 1800)

    scout = Scouting(private) if private else None

    def scouting_feed(league: int, season: int) -> Scouting:
        if scout is None:
            raise HTTPException(403, "Season scouting requires the local API-Football connection.")
        current = season_start(datetime.now(UTC).date())
        if league not in SCOUT_LEAGUES or not 2010 <= season <= current:
            raise HTTPException(422, "Select a supported league and season.")
        return scout

    @router.get("/api/match-centre/scouting/madrid")
    async def madrid_baseline(day: date):
        # The rates, with the lines the page prints beside them (R10) and the club's schedule.
        today = datetime.now(UTC).date()
        try:
            data = await public.madrid_baseline(day, today)
            table = await public.competition("es.1", day, today, None)
        except FeedError as exc:
            raise HTTPException(503, baseline_error(str(exc))) from exc
        return {**data, **baseline_lines(data, table)}

    @router.get("/api/match-centre/scouting/clubs")
    async def scouting_clubs(league: int, season: int):
        service = scouting_feed(league, season)
        try:
            data = await service.league(league, season)
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        clubs = sorted(teams(data.rows).items(), key=lambda t: t[1])
        return {"clubs": [{"id": k, "name": v} for k, v in clubs],
                "warnings": [data.warning] if data.warning else []}

    @router.get("/api/match-centre/scouting/comparison")
    async def scouting_comparison(league: int, season: int, club: int, role: str, metric: str,
                                  split: str, min_minutes: int = Query(270, ge=1, le=5000)):
        service = scouting_feed(league, season)
        split = SPLIT_ALIASES.get(split, split)
        if role not in ROLES or metric not in METRICS or split not in SPLITS:
            raise HTTPException(422, "Select a supported role, metric and opponent group.")
        try:
            return await service.compare(league, season, club, role, metric, split, min_minutes)
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc

    @router.get("/api/match-centre")
    def sources(response: Response):
        today = datetime.now(UTC).date()
        return shared_cache(response, {
            "private_feed": private is not None, "today": today.isoformat(),
            "season": season_start(today), "leagues": SCOUT_LEAGUES, "roles": ROLES,
            "public_leagues": LEAGUES, "competitions": COMPETITIONS}, 300)

    # With no day the board opens on the nearest day that has fixtures (F3), chosen here.
    @router.get("/api/match-centre/fixtures")
    async def fixtures(response: Response, day: date | None = None,
                       source: str = "openfootball"):
        today = datetime.now(UTC).date()
        if source == "api_football" and private is None:
            raise HTTPException(403, "The private feed requires the local match centre and a key.")
        if source not in {"openfootball", "api_football"}:
            raise HTTPException(422, "Unknown fixture source.")
        try:
            if source == "api_football" and private is not None:
                day = day or today
                payload = await private.fixtures(day, today)
            else:
                day = day or await public.nearest(today)
                payload = await public.fixtures(day, today)
        except NoSeason as exc:
            # A season the free feeds hold no schedule for is not an outage (H10).
            raise HTTPException(404, str(exc)) from exc
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        return shared_cache(response, {"source": source, "day": day, **payload})

    @router.get("/api/match-centre/fixtures/{key}")
    async def detail(key: str, request: Request, response: Response):
        try:
            if re.fullmatch(r"[1-9][0-9]{0,9}", key):
                if private is None:
                    raise HTTPException(403, "Private match reports are available locally.")
                source = "api_football"
                result = await private.detail(key)
            else:
                if (parsed := parse_key(key)) is None:
                    raise HTTPException(404, "Unknown fixture.")
                source = "openfootball"
                result = await public.detail(*parsed, key, datetime.now(UTC).date())
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        if result is None:
            raise HTTPException(404, "Fixture unavailable.")
        game = result["match"]
        # A Madrid league match of the 2017/18 archive has a full report where this app serves
        # the archive's Match reports page; the page looks the match up by its date.
        archive = site_nav.PAGES["match"].path
        if (source == "openfootball" and game.get("code") == "es.1" and game["madrid"]
                and season_start(date.fromisoformat(game["day"])) == 2017
                and archive in site_nav.served_paths(request.app)):
            result["archive"] = {"href": archive, "day": game["day"]}
        payload = {"source": source, **result}
        return shared_cache(response, payload) if source == "openfootball" else payload

    return router
