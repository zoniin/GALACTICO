"""Pre-match classification and per-player evidence for the private scouting page."""

import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from galactico.match_centre.api_football import ApiFootball
from galactico.match_centre.feed import FeedError, Snapshot
from galactico.match_centre.local import create_app
from galactico.match_centre.scouting import Scouting, opponent_groups


def game(fid, home, away, goals=(1, 0), day="2026-08-01"):
    return {"fixture": {"id": fid, "date": day+"T20:00:00Z", "status": {"short": "FT"}},
            "teams": {side: {"id": i, "name": f"Club {i}"}
                      for side, i in zip(["home", "away"], [home, away], strict=True)},
            "goals": {"home": goals[0], "away": goals[1]}}


def test_classification_uses_only_prior_dates_and_withholds_cutoff_ties():
    # After five rounds teams 1–4 have 15 points, teams 5–8 are tied on zero.
    slate = [game(10*r+i, i, i+4, day=f"2026-08-{r:02}")
             for r in range(1, 6) for i in range(1, 5)]
    slate.extend([game(100, 1, 6, (0, 8), "2026-09-01"),
                  game(101, 2, 1, (0, 3), "2026-09-01")])
    assert set(opponent_groups(slate, 1).values()) == {"top", "unclassified"}
    assert opponent_groups(slate, 1)[100] == "unclassified"
    assert opponent_groups(slate, 1)[101] == "top"
    slate.extend([game(102, 1, 8, (0, 1), "2026-09-02"),
                  game(103, 4, 5, (4, 0), "2026-09-02"),
                  game(104, 1, 5, (0, 1), "2026-09-03")])
    assert opponent_groups(slate, 1)[104] == "other"


def player(pid, role, mins, passes):
    return {"player": {"id": pid, "name": f"Player {pid}"},
            "statistics": [{"games": {"position": role, "minutes": mins}, "passes": passes}]}


def test_compare_uses_only_metric_supported_minutes_and_reports_coverage(monkeypatch):
    reports = [
        game(1, 52, 1), game(2, 52, 2), game(3, 52, 3),
        game(4, 541, 9), game(5, 541, 8),
    ]
    reports[0]["players"] = [{"team": {"id": 52}, "players": [
        player(1, "M", 90, {"key": 2}), player(2, "D", 90, {"key": 8})]}]
    reports[1]["players"] = [{"team": {"id": 52}, "players": [player(1, "M", 45, {})]}]
    reports[3]["players"] = [{"team": {"id": 541}, "players": [player(3, "M", 90, {"key": 0})]}]
    reports[4]["players"] = [{"team": {"id": 541}, "players": [player(4, "M", 90, {"key": 2})]}]
    service = Scouting(ApiFootball("test-only"))

    async def league(code, season):
        return Snapshot(reports[:3] if code == 39 else reports[3:], "2026-10-01T12:00Z")

    async def fetch(params):
        return [r for r in reports if str(r["fixture"]["id"]) in params["ids"].split("-")]

    monkeypatch.setattr(service, "league", league)
    monkeypatch.setattr(service.feed, "fetch_fixtures", fetch)

    async def run():
        data = await service.compare(39, 2026, 52, "M", "key_passes", "all", 90)
        assert data["madrid"]["per90"] == 1.0
        assert data["players"] == [{"id": 1, "name": "Player 1", "minutes": 135,
                                    "observed": 90, "count": 2, "per90": 2.0, "gap": 1.0}]
        assert data["coverage"][0] == {"club": "Club 52", "covered": 2, "matches": 3,
                                       "unclassified": 3}
        gated = await service.compare(39, 2026, 52, "M", "key_passes", "top", 90)
        assert gated["players"] == [] and gated["madrid"]["per90"] is None

    asyncio.run(run())


def test_remote_scouting_routes_refuse_before_accessing_data():
    async def run():
        transport = httpx.ASGITransport(app=create_app(None), client=("127.0.0.1", 10000))
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            response = await client.get("/api/match-centre/scouting/clubs",
                                        params={"league": 39, "season": datetime.now(UTC).year})
        assert response.status_code == 403

    asyncio.run(run())


def test_vendor_query_rejection_is_sanitised(monkeypatch):
    async def get(self, url, **kwargs):
        return httpx.Response(200, json={"errors": {"plan": "internal vendor detail"}},
                              request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    with pytest.raises(FeedError, match="plan and quota"):
        asyncio.run(ApiFootball("test-only").fetch_fixtures({"ids": "1-2"}))
