"""Public server for the current match centre. It only serves public data.

``/`` is the Matches page (the router's). Old shared fixture links (``/?day=``, ``/?match=``,
``/?source=``) keep opening the match board, which reads its query itself. A page it does not
serve, an archive page included, gets the site's designed "not here" page (``errors``), and
"About the numbers" holds how this season's numbers are gathered (``methods``). Under
``/static`` it serves only what its own pages load (``assets.HOSTED``): no page template and
no file of the archive pages.

**The season data layer** (ADR-0036). ``football`` is the football-data.org client the
router's catalogue reads (``season.catalog.Catalog``); by default the one
``FootballData.from_env()`` gives, which is ``None`` without ``FOOTBALL_DATA_KEY`` (and under
pytest unless a transport is injected), so with no key the app reads exactly the free
sources it read before. The catalogue is built here and idle until the season pages read it.

**Lifetimes** (PLATFORM 3.6). Where no private feed is mounted, the shell's pages carry the
CDN's lifetime (``assets.PageCache``); a private feed's replies are never cached.
"""

from fastapi import FastAPI

from . import errors, methods
from .api_football import ApiFootball
from .assets import HOSTED, Assets, PageCache
from .routes import WEB, make_router
from .season.football_data import FootballData


def create_centre(title: str, private: ApiFootball | None = None,
                  football: FootballData | None = None) -> FastAPI:
    """The match centre. ``football``, where given, is the client the catalogue reads (a
    stub for the e2e server and the tests); else ``FootballData.from_env()``."""
    football = football if football is not None else FootballData.from_env()
    server = FastAPI(title=title)
    router = make_router(private, football=football)
    server.include_router(router)
    server.state.catalog = router.catalog
    server.mount("/static", Assets(directory=str(WEB), allow=HOSTED), name="static")
    server.state.about_sections = (methods.current_season,)
    errors.install(server)
    if private is None:
        # The CDN may keep the shell's pages (PLATFORM 3.6); a private feed's never.
        server.add_middleware(PageCache)
    return server


app = create_centre("Galáctico match centre")
