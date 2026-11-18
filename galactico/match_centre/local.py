"""Run the private match centre with python -m galactico.match_centre.local."""

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from .api_football import ApiFootball
from .public import create_centre

LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def create_app(key: str | None) -> FastAPI:
    app = create_centre("Galáctico private match centre", ApiFootball(key) if key else None)

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        peer = request.client
        if (not peer or peer.host not in LOOPBACK or request.url.hostname not in LOOPBACK
                or any(h == "forwarded" or h.startswith("x-forwarded-") for h in request.headers)
                or request.headers.get("sec-fetch-site") == "cross-site"):
            return PlainTextResponse("Open the private centre directly on localhost.", 403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    return app


def run() -> None:
    from dotenv import load_dotenv

    load_dotenv(Path.cwd() / ".env", override=False)
    uvicorn.run(create_app(os.getenv("API_FOOTBALL_KEY")), host="127.0.0.1",
                port=8091, proxy_headers=False)


if __name__ == "__main__":
    run()
