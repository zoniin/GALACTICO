"""Public server for the current match centre. It only serves public data."""

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api_football import ApiFootball
from .routes import WEB, make_router


def create_centre(title: str, private: ApiFootball | None = None) -> FastAPI:
    server = FastAPI(title=title)

    @server.get("/", include_in_schema=False)
    def home(request: Request):
        board = any(key in request.query_params for key in ("day", "match", "source"))
        return FileResponse(WEB / ("match-centre.html" if board else "studio.html"))

    server.include_router(make_router(private))
    server.mount("/static", StaticFiles(directory=WEB), name="static")
    return server


app = create_centre("Galáctico match centre")
