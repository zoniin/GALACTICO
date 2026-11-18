"""Exercise both fixture sources, using only invented match records in the test suite."""

import asyncio
from datetime import UTC, date, datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from galactico.api.player_lab import app
from galactico.match_centre.api_football import ApiFootball
from galactico.match_centre.feed import FeedCache, FeedError, Snapshot
from galactico.match_centre.local import create_app
from galactico.match_centre.openfootball import OpenFootball

DAY = date(2026, 10, 10)
CHECKED = datetime(2026, 10, 10, 12, tzinfo=UTC).isoformat()
GAMES = [
    dict(date="2026-09-01", team1="Real Madrid", team2="Test A", score=[0, 0]),
    dict(date="2026-10-01", team1="Test B", team2="Real Madrid", score={"ft": [0, 2]}),
    dict(date="2026-10-09", team1="Test B", team2="Test A"),
    dict(date="2026-10-10", team1="Real Madrid", team2="Test C", score={"ht": [1, 0]}),
]


def test_public_scoreboard_form_and_date_boundaries(monkeypatch):
    async def season(self, code, year):
        if code == "it.1":
            raise FeedError("Unavailable")
        return Snapshot(GAMES if code == "es.1" else [], CHECKED)

    monkeypatch.setattr(OpenFootball, "season", season)
    with TestClient(app) as client:
        response = client.get("/api/match-centre/fixtures?day=2026-10-01").json()
        assert response["warnings"] == ["Serie A · Unavailable"]
        assert response["matches"][0]["score"] == [0, 2]
        assert response["next"] == "2026-10-09"
        board = client.get("/api/match-centre/fixtures?day=2026-10-10").json()
        fixture = board["matches"][0]
        assert board["madrid_fixture"]["id"] == fixture["id"] and fixture["score"] is None
        detail = client.get("/api/match-centre/fixtures/" + fixture["id"]).json()
        assert [r["result"] for r in detail["form"]["Real Madrid"]] == ["W", "D"]
        assert detail["form"]["Test C"] == []
        assert client.get("/api/match-centre/fixtures/foo").status_code == 404
        assert client.get("/api/match-centre/fixtures?day=bad").status_code == 422


def test_public_application_never_enables_private_adapter(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_KEY", "test-only")
    with TestClient(app) as client:
        assert client.get("/api/match-centre").json()["private_feed"] is False
        assert client.get("/api/match-centre/fixtures/42").status_code == 403
        assert client.get("/api/match-centre/fixtures?day=2026-10-10&source=api_football"
                          ).status_code == 403


def test_private_reports_keep_zero_unknown_and_extra_time_distinct(monkeypatch):
    calls = []

    async def get(self, url, **kwargs):
        calls.append(kwargs)
        row = dict(fixture=dict(id=42, date="2026-10-10T20:00:00+02:00",
                                status=dict(short="2H", elapsed=90, extra=3)),
                   league=dict(name="Cup"), teams=dict(home=dict(name="Test A", id=541),
                                                       away=dict(name="Test B", id=1)),
                   goals=dict(home=1, away=0), players=[dict(team=dict(name="Test A"), players=[
                       dict(player=dict(name="Player A"), statistics=[
                           dict(passes=dict(key=0), games=dict(minutes=90))])])])
        return httpx.Response(200, json={"response": [row], "errors": []},
                              request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    feed = ApiFootball("test-only")

    async def run():
        board = await feed.fixtures(DAY, DAY)
        match = board["matches"][0]
        assert match["score"] == [1, 0] and match["madrid"] and match["live"]
        assert match["kickoff"] == "18:00 UTC" and match["status"] == "90+3′"
        results = await asyncio.gather(feed.detail("42"), feed.detail("42"))
        assert results[0] == results[1]
        player = results[0]["players"][0]
        assert player["key_passes"] == 0 and player["assists"] is None
        assert len(calls) == 2 and calls[-1]["params"] == {"id": "42"}

    asyncio.run(run())


def test_private_server_refuses_remote_peer_host_and_forwarded_requests():
    async def run():
        local = create_app("test-only")
        for peer, host, headers, status in [
            ("127.0.0.1", "localhost", {}, 200),
            ("192.0.2.1", "localhost", {}, 403),
            ("127.0.0.1", "public.example", {}, 403),
            ("127.0.0.1", "localhost", {"X-Forwarded-For": "192.0.2.1"}, 403),
        ]:
            transport = httpx.ASGITransport(app=local, client=(peer, 1234))
            async with httpx.AsyncClient(transport=transport, base_url="http://" + host) as client:
                response = await client.get("/api/match-centre", headers=headers)
            assert response.status_code == status
            if status == 200:
                assert response.headers["Cache-Control"] == "no-store"
                assert response.json()["private_feed"]

    asyncio.run(run())


def test_failed_refresh_retains_last_success_and_backs_off():
    attempts = 0

    async def load():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return [{"id": 1}]
        raise FeedError("Check quota")

    async def run():
        cache = FeedCache()
        first = await cache.get("day", 0, load)
        stale = await cache.get("day", 0, load)
        assert stale.rows == first.rows and stale.checked == first.checked
        assert stale.warning == "Check quota"
        assert await cache.get("day", 0, load) == stale
        assert attempts == 2
        with pytest.raises(FeedError, match="quota"):
            await cache.get("other", 60, load)

    asyncio.run(run())


def test_league_table_counts_reported_results_and_ties_and_links_team_schedule(monkeypatch):
    async def season(self, code, year):
        return Snapshot(GAMES, CHECKED)

    monkeypatch.setattr(OpenFootball, "season", season)
    with TestClient(app) as client:
        url = "/api/match-centre/leagues/es.1"
        overview = client.get(url, params={"day": "2026-09-01"}).json()
        assert overview["reported"] == 1 and overview["missing"] == 0
        assert [c["rank"] for c in overview["table"]] == [1, 1, 3, 3]
        team = client.get(url, params={"day": "2026-10-10", "team": "Real Madrid"}).json()
        assert team["reported"] == 2 and team["missing"] == 2
        madrid = team["table"][0]
        assert madrid["team"] == "Real Madrid" and madrid["gf"] == 2 and madrid["points"] == 4
        assert len(team["fixtures"]) == 3
        fixture = team["fixtures"][0]
        assert client.get("/api/match-centre/fixtures/" + fixture["id"]).json()["match"] == fixture
        assert client.get("/api/match-centre/leagues/unknown?day=2026-09-01").status_code == 404


def test_hosted_entrypoint_serves_current_app_without_private_data(monkeypatch):
    from api.index import app as hosted

    monkeypatch.setenv("API_FOOTBALL_KEY", "example")
    with TestClient(hosted) as client:
        for path in ("/", "/match-centre", "/match-centre/leagues", "/match-centre/scouting",
                     "/match-centre/demo", "/static/match-centre.js"):
            assert client.get(path).status_code == 200
        assert "Match centre" in client.get("/").text
        assert client.get("/api/match-centre").json()["private_feed"] is False
        assert client.get("/api/match-centre/fixtures/42").status_code == 403


def test_local_launcher_reads_dotenv_and_preserves_an_exported_key(tmp_path, monkeypatch):
    from galactico.match_centre import local

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    (tmp_path / ".env").write_text("API_FOOTBALL_KEY=file-example\n")
    captured = []
    monkeypatch.setattr(local, "create_app", lambda key: captured.append(key))
    monkeypatch.setattr(local.uvicorn, "run", lambda *args, **kwargs: None)
    local.run()
    monkeypatch.setenv("API_FOOTBALL_KEY", "env-example")
    local.run()
    assert captured == ["file-example", "env-example"]


def test_public_scouting_uses_reported_scores_and_counts_other_team_appearances(monkeypatch):
    async def season(self, code, year):
        return Snapshot([
            {"team1": "Real Madrid CF", "team2": "A", "date": "2025-10-01", "score": [3, 0]},
            {"team1": "A", "team2": "B", "date": "2025-10-02", "score": [1, 1]},
            {"team1": "B", "team2": "Real Madrid CF", "date": "2025-10-03"},
            {"team1": "A", "team2": "Real Madrid CF", "date": "2025-10-04", "score": [8, 4]},
        ], CHECKED)

    monkeypatch.setattr(OpenFootball, "season", season)
    with TestClient(app) as client:
        url = "/api/match-centre/scouting/madrid"
        report = client.get(url, params={"day": "2025-10-03"}).json()
        assert report["reported"] == 2 and report["missing"] == 1
        assert report["madrid"]["scored_per_game"] == 3 and report["madrid"]["team_games"] == 1
        assert report["other_clubs"]["scored_per_game"] == 2 / 3
        assert report["other_clubs"]["conceded_per_game"] == 5 / 3
        empty = client.get(url, params={"day": "2025-09-18"}).json()
        assert empty["madrid"]["scored_per_game"] is None
