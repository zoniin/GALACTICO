"""API-Football v3 fixture reports for the private match centre."""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx

from ..providers.base import assert_may_ingest
from .feed import FeedCache, FeedError

LIVE = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"}
CLOCK = {"1H", "2H", "ET"}


def _match(row: dict) -> dict:
    fixture, teams = row["fixture"], row["teams"]
    kickoff = datetime.fromisoformat(fixture["date"]).astimezone(UTC)
    status = fixture.get("status") or {}
    short, minute = status.get("short"), status.get("elapsed")
    label = status.get("long") or short or "Status unavailable"
    if short in CLOCK and minute is not None:
        extra = status.get("extra")
        label = f"{minute}+{extra}′" if extra else f"{minute}′"
    goals = row.get("goals") or {}
    score = [goals.get("home"), goals.get("away")]
    competition = row.get("league") or {}
    return {
        "id": str(fixture["id"]), "competition": " · ".join(filter(None, [
            competition.get("country"), competition.get("name")])) or "Competition unknown",
        "round": competition.get("round"), "home": teams["home"]["name"],
        "away": teams["away"]["name"], "madrid": 541 in (
            teams["home"].get("id"), teams["away"].get("id")),
        "day": kickoff.date().isoformat(), "kickoff": f"{kickoff:%H:%M} UTC",
        "score": score if any(g is not None for g in score) else None,
        "live": short in LIVE, "status": label,
    }


def _report(row: dict) -> dict:
    events, lineups, stats, players = [], [], [], []
    for event in row.get("events") or []:
        clock = event.get("time") or {}
        events.append({"minute": clock.get("elapsed"), "extra": clock.get("extra"),
                       "team": (event.get("team") or {}).get("name"), "type": event.get("type"),
                       "detail": event.get("detail"), "player": (event.get("player") or {})
                       .get("name"), "assist": (event.get("assist") or {}).get("name")})
    for side in row.get("lineups") or []:
        def names(entries: list) -> list:
            return [entry["player"].get("name") for entry in entries if entry.get("player")]

        lineups.append({"team": side["team"]["name"], "formation": side.get("formation"),
                       "starters": names(side.get("startXI") or []),
                       "subs": names(side.get("substitutes") or [])})
    for side in row.get("statistics") or []:
        stats.append({"team": side["team"]["name"], "values": {
            s["type"]: s.get("value") for s in side.get("statistics") or []}})
    for side in row.get("players") or []:
        for entry in side.get("players") or []:
            for stat in entry.get("statistics") or []:
                goals, passes = stat.get("goals") or {}, stat.get("passes") or {}
                players.append({"team": side["team"]["name"], "name": entry["player"]["name"],
                                "minutes": (stat.get("games") or {}).get("minutes"),
                                "goals": goals.get("total"), "assists": goals.get("assists"),
                                "shots": (stat.get("shots") or {}).get("total"),
                                "passes": passes.get("total"), "key_passes": passes.get("key"),
                                "tackles": (stat.get("tackles") or {}).get("total")})
    return dict(events=events, lineups=lineups, statistics=stats, players=players)


class ApiFootball:
    def __init__(self, key: str) -> None:
        self.key = key
        self.cache = FeedCache()

    async def _fetch(self, params: dict) -> list:
        assert_may_ingest("api_football")
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            response = await client.get("https://v3.football.api-sports.io/fixtures",
                                        params=params, headers={"x-apisports-key": self.key})
        if response.status_code in {401, 403, 429}:
            raise FeedError("API-Football denied this request. Check the key, plan and quota.")
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or data.get("errors"):
            raise FeedError("API-Football rejected this query. Check your plan and quota.")
        rows = data.get("response")
        if not isinstance(rows, list):
            raise FeedError("API-Football returned an invalid fixture report.")
        # Validate the required fields before replacing a previous successful snapshot.
        try:
            for row in rows:
                _match(row)
                if "id" in params:
                    _report(row)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise FeedError("API-Football returned an incomplete fixture report.") from exc
        return rows

    async def fixtures(self, day: date, today: date) -> dict:
        params = {"date": day.isoformat(), "timezone": "UTC"}
        data = await self.cache.get(str(day), 60 if day == today else 900,
                                    lambda: self._fetch(params))
        return {"matches": [_match(row) for row in data.rows], "checked": data.checked,
                "warnings": [data.warning] if data.warning else []}

    async def detail(self, fixture_id: str) -> dict | None:
        data = await self.cache.get(f"match/{fixture_id}", 60,
                                    lambda: self._fetch({"id": fixture_id}))
        if not data.rows:
            return None
        row = data.rows[0]
        return {"match": _match(row), **_report(row), "checked": data.checked,
                "warnings": [data.warning] if data.warning else []}
