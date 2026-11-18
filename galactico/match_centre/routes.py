"""The public centre is constructed without a licensed data adapter."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from .api_football import ApiFootball
from .feed import FeedError
from .openfootball import LEAGUES, OpenFootball, season_start
from .scouting import LEAGUES as SCOUT_LEAGUES
from .scouting import METRICS, ROLES, SPLITS, Scouting, teams

WEB = Path(__file__).resolve().parents[2] / "web"


def make_router(private: ApiFootball | None = None) -> APIRouter:
    router, public = APIRouter(), OpenFootball()

    @router.get("/match-centre", include_in_schema=False)
    def centre():
        return FileResponse(WEB / "match-centre.html")

    @router.get("/match-centre/leagues", include_in_schema=False)
    def leagues_page():
        return FileResponse(WEB / "leagues.html")

    @router.get("/api/match-centre/leagues/{code}")
    async def competition(code: str, day: date, team: str | None = None):
        if code not in LEAGUES:
            raise HTTPException(404, "Unknown competition.")
        try:
            return await public.competition(code, day, datetime.now(UTC).date(), team)
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc

    @router.get("/match-centre/demo", include_in_schema=False)
    def demo():
        return FileResponse(WEB / "matchroom-demo.html")

    @router.get("/match-centre/scouting", include_in_schema=False)
    def scouting_page():
        return FileResponse(WEB / "scouting.html")

    scout = Scouting(private) if private else None

    def scouting_feed(league: int, season: int) -> Scouting:
        if scout is None:
            raise HTTPException(403, "Season scouting requires the local API-Football connection.")
        current = season_start(datetime.now(UTC).date())
        if league not in SCOUT_LEAGUES or not 2010 <= season <= current:
            raise HTTPException(422, "Select a supported league and season.")
        return scout

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
        if role not in ROLES or metric not in METRICS or split not in SPLITS:
            raise HTTPException(422, "Select a supported role, metric and opponent group.")
        try:
            return await service.compare(league, season, club, role, metric, split, min_minutes)
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc

    @router.get("/api/match-centre")
    def sources():
        today = datetime.now(UTC).date()
        return {"private_feed": private is not None, "today": today.isoformat(),
                "season": season_start(today), "leagues": SCOUT_LEAGUES, "roles": ROLES,
                "public_leagues": LEAGUES}

    @router.get("/api/match-centre/fixtures")
    async def fixtures(day: date, source: str = "openfootball"):
        today = datetime.now(UTC).date()
        if source == "api_football" and private is None:
            raise HTTPException(403, "The private feed requires the local match centre and a key.")
        if source not in {"openfootball", "api_football"}:
            raise HTTPException(422, "Unknown fixture source.")
        try:
            if source == "api_football" and private is not None:
                payload = await private.fixtures(day, today)
            else:
                payload = await public.fixtures(day, today)
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        return {"source": source, "day": day, **payload}

    @router.get("/api/match-centre/fixtures/{key}")
    async def detail(key: str):
        try:
            if re.fullmatch(r"[1-9][0-9]{0,9}", key):
                if private is None:
                    raise HTTPException(403, "Private match reports are available locally.")
                source = "api_football"
                result = await private.detail(key)
            else:
                parts = key.split("-")
                if (len(parts) != 3 or parts[0] not in LEAGUES or
                        not re.fullmatch(r"[0-9]{4}-[0-9a-f]{16}", "-".join(parts[1:]))):
                    raise HTTPException(404, "Unknown fixture.")
                source = "openfootball"
                result = await public.detail(parts[0], int(parts[1]), key,
                                             datetime.now(UTC).date())
        except FeedError as exc:
            raise HTTPException(503, str(exc)) from exc
        if result is None:
            raise HTTPException(404, "Fixture unavailable.")
        return {"source": source, **result}

    return router
