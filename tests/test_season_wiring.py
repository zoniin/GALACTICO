"""The season data layer wired into both apps (PLAN root step D5, ADR-0036).

Each test targets one way the wiring could mislead or leak:

- an app whose catalogue reads other sources than its board (a second OpenFootball reader, no
  infoboxes, so no Real Madrid player joins football-data.org), or a gate passed that the
  root has not passed;
- a client built from the environment under pytest (a developer shell with the key exported
  would reach the real API), or a stub client the app does not hand to its catalogue;
- the client's connections left open at shutdown;
- a page view that reaches football-data.org before any page reads the catalogue.

Every client here has an injected transport that fails the test on any request, or none.
"""

from __future__ import annotations

import asyncio

import httpx
import season_v4 as v4
from fastapi.testclient import TestClient

from galactico.match_centre.public import create_centre
from galactico.match_centre.routes import make_router
from galactico.match_centre.season import warm
from galactico.match_centre.season.budget import Budget
from galactico.match_centre.season.catalog import PASSED_GATES, Catalog
from galactico.match_centre.season.football_data import FootballData
from galactico.match_centre.season.infobox import Infoboxes
from galactico.match_centre.season.revisions import Revisions
from galactico.match_centre.season.wiki_season import MadridSeason
from galactico.match_centre.season.wikidata import Wikidata
from galactico.match_centre.studio import Studio


def refused(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"no request may leave: {request.url.host}")


def test_both_apps_build_one_catalogue_on_the_readers_the_board_uses(monkeypatch):
    # A shell with the key exported: under pytest the environment's client is off (None).
    monkeypatch.setenv("FOOTBALL_DATA_KEY", "not-a-key")
    from galactico.api.player_lab import app as local

    for app in (create_centre("Hosted"), local):
        catalog = app.state.catalog
        assert isinstance(catalog, Catalog) and catalog.football is None
        assert catalog.gates == frozenset(PASSED_GATES) == frozenset({"P-D9"})
        assert isinstance(catalog.studio, Studio)
        assert isinstance(catalog.madrid_season, MadridSeason)
        assert isinstance(catalog.infoboxes, Infoboxes)
        assert isinstance(catalog.revisions, Revisions)
        assert isinstance(catalog.wikidata, Wikidata)
        # OpenLigaDB is read once: the catalogue's is the board's OpenFootball reader's.
        assert catalog.openligadb is catalog.openfootball.ligadb
    router = make_router()
    assert router.catalog.football is None and router.catalog is not make_router().catalog


def test_a_client_handed_over_is_the_catalogues_idle_and_closed_at_shutdown():
    football = FootballData("test-only", transport=httpx.MockTransport(refused))
    closed: list[bool] = []

    async def aclose() -> None:
        closed.append(True)

    football.aclose = aclose
    app = create_centre("Stub", football=football)
    assert app.state.catalog.football is football
    with TestClient(app) as client:
        for path in ("/", "/about", "/match-centre/leagues"):
            assert client.get(path).status_code == 200, path
        assert closed == []
    assert closed == [True], "the router's lifespan closes the client once, at shutdown"


def test_the_copa_libertadores_is_listed_and_the_europa_league_is_not():
    world = v4.sample_world()
    world.available = 1000
    football = FootballData("test-only", transport=world.transport(),
                            budget=Budget(per_minute=1000, reserve=0))
    catalog = create_centre("Stub", football=football).state.catalog
    slugs = [c.slug for c in asyncio.run(catalog.competitions()).value]
    assert "copa-libertadores" in slugs and "europa-league" not in slugs
    # The warm plan's search step reads the passed gate's competition too, never the other.
    assert "copa-libertadores" in [c.slug for c in warm._carried(catalog)]
    assert "europa-league" not in [c.slug for c in warm._carried(catalog)]
