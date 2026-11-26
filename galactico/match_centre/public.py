"""Public server for the current match centre. It only serves public data.

``/`` is the Matches page (the router's). Old shared fixture links (``/?day=``, ``/?match=``,
``/?source=``) keep opening the match board, which reads its query itself. A page it does not
serve, an archive page included, gets the site's designed "not here" page (``errors``), and
"About the numbers" holds how this season's numbers are gathered (``methods``). Under
``/static`` it serves only what its own pages load (``assets.HOSTED``): no page template and
no file of the archive pages.
"""

from fastapi import FastAPI

from . import errors, methods
from .api_football import ApiFootball
from .assets import HOSTED, Assets
from .routes import WEB, make_router


def create_centre(title: str, private: ApiFootball | None = None) -> FastAPI:
    server = FastAPI(title=title)
    server.include_router(make_router(private))
    server.mount("/static", Assets(directory=str(WEB), allow=HOSTED), name="static")
    server.state.about_sections = (methods.current_season,)
    errors.install(server)
    return server


app = create_centre("Galáctico match centre")
