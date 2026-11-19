"""Public goal coverage with invented matches and a mocked upstream."""

import httpx
from fastapi.testclient import TestClient

from galactico.match_centre.goal_scout import parse_matches
from galactico.match_centre.public import create_centre


def fixture():
    return dict(
        matchID=1,
        matchDateTimeUTC="2025-10-01T20:00:00Z",
        matchIsFinished=True,
        team1=dict(teamId=11, teamName="A"),
        team2=dict(teamId=22, teamName="B"),
        matchResults=[
            dict(resultTypeID=1, pointsTeam1=1, pointsTeam2=0),
            dict(resultTypeID=2, pointsTeam1=2, pointsTeam2=1),
        ],
        goals=[
            dict(scoreTeam1=2, scoreTeam2=1, isOwnGoal=True, goalGetterName="A. One"),
            dict(scoreTeam1=1, scoreTeam2=0, matchMinute=5, goalGetterName="A. Two"),
            dict(scoreTeam1=0, scoreTeam2=0, goalGetterName="Placeholder"),
            dict(scoreTeam1=1, scoreTeam2=1, matchMinute=None, goalGetterName=""),
            dict(scoreTeam1=3, scoreTeam2=1, goalGetterName="Invalid"),
        ],
    )


def test_event_order_sides_missing_names_and_final_only():
    game = parse_matches([fixture()])[0]
    assert game["goals"] == {"home": 2, "away": 1}
    events = game["timeline"]
    assert [e["name"] for e in events] == ["A. Two", "", "A. One"]
    assert [e["team"] for e in events] == [11, 22, 11]
    assert events[1]["minute"] is None and events[2]["own"]
    for incomplete in (dict(matchIsFinished=False), dict(matchResults=[])):
        assert parse_matches([fixture() | incomplete])[0]["timeline"] == []


def test_conflicting_goals_do_not_double_count_or_credit_guessed_scorer():
    raw = fixture()
    raw["goals"].extend(
        [
            dict(scoreTeam1=1, scoreTeam2=0, goalGetterName="Uncertain"),
            dict(scoreTeam1=1, scoreTeam2=1, goalGetterName="Also uncertain"),
        ]
    )
    events = parse_matches([raw])[0]["timeline"]
    assert events == []


def test_public_report_uses_one_season_download_for_multiple_clubs(monkeypatch):
    calls = []

    async def get(self, url):
        calls.append(url)
        return httpx.Response(200, json=[fixture()], request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    with TestClient(create_centre("Test")) as client:
        base = "/api/match-centre/goal-scout/"
        for club, expected, venue in [(11, (2, 1), "H"), (22, (1, 2), "A")]:
            r = client.get(base + "en", params={"club": club})
            assert r.status_code == 200 and "s-maxage" in r.headers["Vercel-CDN-Cache-Control"]
            report = r.json()
            assert "odbl" in report["licence"] and report["source"] == calls[0]
            g = report["matches"][0]
            assert (g["for"], g["against"]) == expected and g["venue"] == venue
            assert g["split"] == "unclassified" and g["events"][0]["for_club"] == (club == 11)
        assert client.get(base + "en?club=999").status_code == 404
        assert client.get(base + "bad").status_code == 404
    assert len(calls) == 1


def test_failed_source_returns_service_unavailable(monkeypatch):
    async def get(self, url):
        return httpx.Response(429, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    with TestClient(create_centre("Test")) as client:
        assert client.get("/api/match-centre/goal-scout/es").status_code == 503
