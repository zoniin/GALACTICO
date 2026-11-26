"""A designed page for an address the app does not serve, for both apps.

A browser asking for a page the app does not answer gets the site's own page, with its header,
its footer and the ways on (``site_nav.not_found``), never the framework's JSON. A request for
an API path or a static file, or one that does not ask for HTML, keeps the JSON reply.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import site_nav

__all__ = ["install", "missing_page"]


async def missing_page(request: Request, exc: StarletteHTTPException) -> Response:
    path = request.url.path
    if (exc.status_code == 404 and not path.startswith(("/api/", "/static/"))
            and "text/html" in request.headers.get("accept", "")):
        return HTMLResponse(site_nav.not_found(request), status_code=404)
    return await http_exception_handler(request, exc)


def install(app: FastAPI) -> None:
    """Answer a browser's request for a missing page with the designed page."""
    app.add_exception_handler(StarletteHTTPException, missing_page)
