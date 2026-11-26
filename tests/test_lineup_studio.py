"""The squad and map use different sources and retain their own scope and dates."""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from galactico.match_centre.feed import FeedError
from galactico.match_centre.public import create_centre
from galactico.match_centre.studio import SAMPLES, Studio, parse_roster


def squad_html():
    def table(headers, body):
        head = "".join(f"<th>{h}</th>" for h in headers)
        return f'<table class="wikitable"><tr>{head}</tr>{body}</table>'

    def player_row(slug, number, *values):
        # Deliberately use the same display name and a different shirt in the totals table.
        player = f'<a href="./{slug}" title="{slug}">Player</a>'
        cells = [number, "MF", "ESP", player, *values]
        return "<tr>" + "".join(f"<td>{v}</td>" for v in cells) + "</tr>"

    roster = table(["No.", "Pos.", "Nation", "Player"],
                   "".join(player_row(f"Test_{n}", n) for n in range(1, 12)))
    stats = table(["No.", "Pos.", "Nat.", "Player", "Total", "League"],
                  "<tr><th>Apps</th><th>Goals</th></tr>"
                  + player_row("Departed", 1, 10, 4)
                  + player_row("Test_1", 22, 7, 0)
                  + player_row("Test_3", 2, "–", 3))
    return stats + roster


def test_roster_joins_current_members_by_link_and_keeps_unknown_totals():
    players = {p["id"]: p for p in parse_roster(squad_html())}
    assert len(players) == 11 and "Departed" not in players
    assert players["Test_1"] == dict(id="Test_1", number=1, name="Player",
                                     nation="ESP", group="MF", archive=False, apps=7, goals=0)
    assert players["Test_2"]["goals"] is None
    assert players["Test_3"]["apps"] is None and players["Test_3"]["goals"] == 3
    with pytest.raises(FeedError):
        parse_roster("<html></html>")


def test_studio_routes_preserve_fixture_links_and_separate_missing_data(monkeypatch):
    async def unavailable(self, url, **kwargs):
        return httpx.Response(503, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", unavailable)
    with TestClient(create_centre("Test")) as client:
        # "/" is Matches on every app; the studio is /lineup. Old fixture links on "/" still
        # open the board.
        assert "<title>Lineup · Galáctico</title>" in client.get("/lineup").text
        for url in ("/", "/?day=2026-09-01"):
            assert "<title>Matches · Galáctico</title>" in client.get(url).text
        assert client.get("/api/studio/squad").status_code == 503
        assert client.get("/api/studio/activity/Unknown").status_code == 404
        assert client.get("/api/studio/activity/Kylian_Mbappé").status_code == 503


def test_event_map_uses_valid_action_starts_for_the_selected_player(monkeypatch):
    slug = "Kylian_Mbappé"
    _, person, match, day = SAMPLES[slug]

    def event(who=person, kind=8, *locations):
        return dict(playerId=who, eventId=kind,
                    positions=[dict(x=x, y=y) for x, y in locations])

    events = [event(person, 8, (10, 20), (80, 90)), event(person, 10, (0, 35)),
              event(person, 8, (0, 0)), event(person, 8, (100, 100)),
              event(person, 8, (-3, 5)), event(person, 8, ("6", 4)),
              event(-1, 8, (11, 12)), event(person, 2, (11, 12)), event(), None]

    async def get(self, url):
        return httpx.Response(200, json={"events": events}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    sample = asyncio.run(Studio().activity(slug))
    assert sample["match"] == match and sample["date"] == day
    assert sample["points"] == [dict(x=10, y=20, type="Pass"), dict(x=0, y=35, type="Shot")]


@pytest.mark.parametrize("payload", [[], {"events": []}])
def test_unusable_event_files_return_a_feed_error(monkeypatch, payload):
    async def get(self, url):
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    with pytest.raises(FeedError):
        asyncio.run(Studio().activity("Kylian_Mbappé"))
