"""Public server for the current match centre. It only serves public data.

``/`` is the Matches page (the router's). Old shared fixture links (``/?day=``, ``/?match=``,
``/?source=``) keep opening the match board, which reads its query itself. A page it does not
serve, an archive page included, gets the site's designed "not here" page (``errors``), and
"About the numbers" holds how this season's numbers are gathered (``methods``).
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import errors, methods
from .api_football import ApiFootball
from .routes import WEB, make_router


def create_centre(title: str, private: ApiFootball | None = None) -> FastAPI:
    server = FastAPI(title=title)
    server.include_router(make_router(private))
    server.mount("/static", StaticFiles(directory=WEB), name="static")
    server.state.about_sections = (methods.current_season,)
    errors.install(server)
    return server


app = create_centre("Galáctico match centre")
