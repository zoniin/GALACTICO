"""Public server for the current match centre. It only serves public data.

``/`` is the Matches page (the router's). Old shared fixture links (``/?day=``, ``/?match=``,
``/?source=``) keep opening the match board, which reads its query itself.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api_football import ApiFootball
from .routes import WEB, make_router


def create_centre(title: str, private: ApiFootball | None = None) -> FastAPI:
    server = FastAPI(title=title)
    server.include_router(make_router(private))
    server.mount("/static", StaticFiles(directory=WEB), name="static")
    return server


app = create_centre("Galáctico match centre")
