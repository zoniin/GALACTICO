"""Pre-match classification and per-player evidence for the private scouting page.

Re-pinned under ADR-0034 ("Answer-first pages"): the group of a match against a club in places
1-6 is keyed "places_1_6", not "top", a banned token as a served value (R3); the comparison
still accepts "top" from an old link (the gated call below asks for it that way).
"""

import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from galactico.domain.labels import scan_labels
from galactico.match_centre.api_football import ApiFootball
from galactico.match_centre.feed import FeedError, Snapshot
from galactico.match_centre.local import create_app
from galactico.match_centre.scouting import (
    Scouting,
    baseline_error,
    baseline_lines,
    lines,
    opponent_groups,
)


@pytest.fixture(autouse=True)
def no_squad_names(monkeypatch):
    # The squad list (Wikipedia) writes Real Madrid's scorers on the pages (names.py); no test
    # reaches it unless it says so.
    from galactico.match_centre.studio import Studio

    async def names(self, day):
        return []

    monkeypatch.setattr(Studio, "squad_names", names)


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
    assert set(opponent_groups(slate, 1).values()) == {"places_1_6", "unclassified"}
    assert opponent_groups(slate, 1)[100] == "unclassified"
    assert opponent_groups(slate, 1)[101] == "places_1_6"
    slate.extend([game(102, 1, 8, (0, 1), "2026-09-02"),
                  game(103, 4, 5, (4, 0), "2026-09-02"),
                  game(104, 1, 5, (0, 1), "2026-09-03")])
    assert opponent_groups(slate, 1)[104] == "other"


def test_only_the_rows_a_table_counts_move_it_and_every_club_match_is_classified():
    # A European competition's table is its league phase: a knockout result never moves it,
    # though the knockout match itself is classified by the table before its date.
    slate = [game(10*r+i, i, i+4, goals=(i, 0), day=f"2026-08-{r:02}")
             for r in range(1, 6) for i in range(1, 5)]
    for row in slate:
        row["phase"] = "league"
    knockout = game(200, 8, 2, (9, 0), "2026-09-01")
    knockout["phase"] = "knockout"
    later = game(201, 1, 8, (1, 0), "2026-09-02")
    later["phase"] = "knockout"
    slate += [knockout, later]
    # Places: 4, 3, 2, 1 on 15 points, then 5, 6 (goal difference); 7 and 8 below.
    counted = opponent_groups(slate, 1, lambda row: row["phase"] == "league")
    assert counted[201] == "other"
    # Counted, the 9-0 would lift club 8 into the first six.
    assert opponent_groups(slate, 1)[201] == "places_1_6"
    assert opponent_groups(slate, 2, lambda row: row["phase"] == "league")[200] == "other"


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
        # The lines the page prints are the server's (R10), with the reports' numbers only.
        assert data["lines"] == {
            "madrid": "Real Madrid’s midfielders: 1.00 key passes per 90, from 180 observed of "
                      "180 reported minutes.",
            "order": "Ordered by key passes per 90, then observed minutes, then name.",
            "coverage": ["Club 52: player reports for 2 of 3 selected matches; 3 season "
                         "matches not classified by the opponent’s place.",
                         "Club 541: player reports for 2 of 2 selected matches; 2 season "
                         "matches not classified by the opponent’s place."]}
        gated = await service.compare(39, 2026, 52, "M", "key_passes", "top", 90)
        assert gated["players"] == [] and gated["madrid"]["per90"] is None
        assert gated["lines"]["madrid"].startswith("Real Madrid’s midfielders: under 90 "
                                                   "observed minutes for key passes")
        assert scan_labels([data["lines"], gated["lines"]]) == []

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


def test_madrid_against_the_league_is_said_by_the_server_with_its_schedule():
    data = {"madrid": {"team_games": 7}, "other_clubs": {"team_games": 131}}
    table = {"madrid": ["Real Madrid CF"], "competition": "La Liga", "code": "es.1",
             "credits": [{"name": "OpenFootball"}],
             "freshness": {"note": "La Liga results stop at Sun 20 Sep: 61 later fixtures have "
                                   "no result in the free feed yet.", "label": "", "stale": True}}
    said = baseline_lines(data, table)
    assert said["line"] == ("From Real Madrid CF’s 7 reported matches, against 131 team matches "
                            "of the other La Liga clubs.")
    assert said["schedule"] == "/match-centre/leagues?league=es.1&team=Real+Madrid+CF"
    assert said["stale"] is True and said["note"].startswith("La Liga results stop")
    fresh = baseline_lines({"madrid": {"team_games": 0}, "other_clubs": {"team_games": 0}},
                           {**table, "freshness": {"note": None, "label": "No results "
                                                   "reported yet", "stale": False}})
    assert fresh["line"] == "No Real Madrid La Liga result is reported up to that date."
    assert fresh["note"] == "No results reported yet."
    assert baseline_error("Season file unavailable.") == (
        "OpenFootball’s La Liga file can’t be reached right now.")
    assert baseline_error("Invalid season file.") == "Invalid season file."
    assert scan_labels([said, fresh, baseline_error("")]) == []
    assert lines("D", "goals", 270, {"per90": None}, [])["madrid"] == (
        "Real Madrid’s defenders: under 270 observed minutes for goals, so no reference rate "
        "(0 observed of 0 reported minutes).")
