"""Public server for the current match centre. It only serves public data."""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api_football import ApiFootball
from .routes import WEB, make_router


def create_centre(title: str, private: ApiFootball | None = None) -> FastAPI:
    server = FastAPI(title=title)

    @server.get("/", include_in_schema=False)
    def home():
        return FileResponse(WEB / "match-centre.html")

    server.include_router(make_router(private))
    server.mount("/static", StaticFiles(directory=WEB), name="static")
    return server


app = create_centre("Galáctico match centre")
