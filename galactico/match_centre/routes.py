"""The public centre is constructed without a licensed data adapter."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .api_football import ApiFootball
from .feed import FeedError
from .openfootball import LEAGUES, OpenFootball

WEB = Path(__file__).resolve().parents[2] / "web"


def make_router(private: ApiFootball | None = None) -> APIRouter:
    router, public = APIRouter(), OpenFootball()

    @router.get("/match-centre", include_in_schema=False)
    def centre():
        return FileResponse(WEB / "match-centre.html")

    @router.get("/match-centre/demo", include_in_schema=False)
    def demo():
        return FileResponse(WEB / "matchroom-demo.html")

    @router.get("/api/match-centre")
    def sources():
        return {"private_feed": private is not None, "today": datetime.now(UTC).date().isoformat()}

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
