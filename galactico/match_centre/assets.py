"""The files under ``/static``: sheets, scripts, type and images, never a page; and how long a
browser and the CDN may keep them, and the shell's pages.

Every page is served through the site shell (``galactico.site_nav.page``), which fills in its
head, header and footer. A page template asked for under ``/static`` would be a page without
the shell, and on the hosted app an archive page it does not serve (R7: the archive's research
copy and the StatsBomb logo never reach a hosted surface). So ``Assets`` refuses every
``.html`` file, and the hosted app also names the only files it serves (``HOSTED``): the
sheets and scripts of its own pages, the type and the images they load, and everything under
``season/``, the season pages' folder (the bundle boundary, ``vercel.json`` ``web/season/**``).

**Lifetimes** (PLATFORM 3.6). The hosted app runs on a plan whose function invocations and CDN
requests are capped, and a reply with no cache header is kept by neither the browser nor the
CDN, so each sheet, script and font of each page view would invoke the function. So:

- a file asked for at its content-versioned address (``?v=`` its ``site_nav.asset_version``,
  the address every served page writes) is kept for a year and never revalidated
  (``immutable``): the address changes exactly when the file does;
- a file asked for without that version (a font a sheet loads, an old link, a stale version)
  is kept ten minutes by the browser and a day by the CDN, whose cache starts empty with each
  deployment;
- a page of the shell (``PageCache``) is kept ten minutes by the CDN, which serves it stale
  for an hour while it asks again, and is revalidated by the browser on every view; the
  designed "not here" page five minutes and one minute.

Every cacheable reply may also be served stale for a day if the function fails
(``stale-if-error``), so an outage shows the last good page rather than an error.
"""

from __future__ import annotations

import posixpath
from collections.abc import Collection, Mapping
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .. import site_nav

__all__ = ["HOSTED", "Assets", "PageCache", "VERSIONED", "UNVERSIONED", "PAGE", "MISSING_PAGE",
           "allowed"]

HOSTED = frozenset({
    # The shell: tokens, base, components, the theme switch and the site script.
    "tokens.css", "base.css", "components.css", "theme.js", "site.js",
    # Matches and Table.
    "matches.css", "match-centre.js", "leagues.js",
    # Goals by opponent.
    "goals.css", "goal-scout.js", "goal-links.js", "scouting.js",
    # Lineup.
    "lineup.css", "studio.js", "studio-formation.js", "studio-map.js",
    # Type and images.
    "assets/favicon.svg", "assets/studio-kit.webp",
    "assets/type/dm-sans.woff2", "assets/type/barlow.woff2", "assets/type/barlow-italic.woff2",
    "assets/type/dmsans-OFL.txt", "assets/type/barlowcondensed-OFL.txt",
    # The season pages: their whole folder, the bundle boundary (a prefix rule).
    "season/",
})
"""The files the hosted app serves under ``/static``: what its pages load, and nothing else. An
entry ending in ``/`` is a folder: every file under it (never a page template) is served."""

STALE_IF_ERROR = "stale-if-error=86400"

VERSIONED: Mapping[str, str] = {
    "Cache-Control": "public, max-age=31536000, immutable",
    "Vercel-CDN-Cache-Control": f"s-maxage=31536000, {STALE_IF_ERROR}",
}
"""A file at its content-versioned address: kept a year, never revalidated."""

UNVERSIONED: Mapping[str, str] = {
    "Cache-Control": "public, max-age=600",
    "Vercel-CDN-Cache-Control": f"s-maxage=86400, {STALE_IF_ERROR}",
}
"""A file at its plain address: ten minutes in the browser, a day on the CDN."""

PAGE: Mapping[str, str] = {
    "Cache-Control": "max-age=0",
    "Vercel-CDN-Cache-Control": f"s-maxage=600, stale-while-revalidate=3600, {STALE_IF_ERROR}",
}
"""A page of the shell: ten minutes on the CDN, stale for an hour while it asks again."""

MISSING_PAGE: Mapping[str, str] = {
    "Cache-Control": "max-age=60",
    "Vercel-CDN-Cache-Control": f"s-maxage=300, {STALE_IF_ERROR}",
}
"""The designed page for an address the app does not serve (status 404)."""


def allowed(name: str, allow: Collection[str]) -> bool:
    """Whether ``allow`` names the file ``name``: itself, or a folder (``"season/"``) it is in."""
    return name in allow or any(entry.endswith("/") and name.startswith(entry)
                                for entry in allow)


def _version(scope: Scope) -> str | None:
    query = scope.get("query_string", b"").decode("latin-1")
    for pair in query.split("&"):
        name, _, value = pair.partition("=")
        if name == "v":
            return value
    return None


class Assets(StaticFiles):
    """``StaticFiles`` that never serves a page template, and, with ``allow``, only the files it
    names (paths relative to the directory, or folders ending in ``/``); every file it serves
    carries its lifetime (the module's)."""

    def __init__(self, *, directory: str, allow: Collection[str] | None = None) -> None:
        super().__init__(directory=directory)
        self.allow = frozenset(allow) if allow is not None else None
        self.root = Path(directory)

    async def get_response(self, path: str, scope: Scope) -> Response:
        name = posixpath.normpath(path.replace("\\", "/")).lstrip("/")
        if name.lower().endswith((".html", ".htm")) or name.startswith("..") or (
                self.allow is not None and not allowed(name, self.allow)):
            raise HTTPException(status_code=404)
        response = await super().get_response(path, scope)
        if response.status_code in (200, 304):
            asked = _version(scope)
            current = site_nav.asset_version(self.root / name) if asked else None
            for header, value in (VERSIONED if asked and asked == current
                                  else UNVERSIONED).items():
                response.headers[header] = value
        return response


_CACHE_HEADERS = frozenset({b"cache-control", b"vercel-cdn-cache-control", b"cdn-cache-control"})


class PageCache:
    """ASGI middleware: the lifetime of a page of the shell (``PAGE``) and of the designed "not
    here" page (``MISSING_PAGE``), for the app the CDN sits in front of.

    It adds them only to a GET or HEAD reply that is HTML, has status 200 or 404, is not under
    ``/api/`` or ``/static/``, sets no cookie, and carries no cache header of its own: a route
    that knows better (a live view, a degraded one) sets its own, and one that must not be
    kept says so (``Cache-Control: no-store``). Install it only where no private feed is
    mounted (the replies of a private feed are never cached)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "") if scope["type"] == "http" else ""
        if (scope["type"] != "http" or scope.get("method") not in ("GET", "HEAD")
                or path.startswith(("/api/", "/static/"))):
            await self.app(scope, receive, send)
            return

        async def send_with_lifetime(message: Message) -> None:
            if message["type"] == "http.response.start":
                lifetime = {200: PAGE, 404: MISSING_PAGE}.get(message["status"])
                headers = list(message.get("headers", ()))
                names = {name.lower() for name, _ in headers}
                html = any(name.lower() == b"content-type" and value.startswith(b"text/html")
                           for name, value in headers)
                if (lifetime is not None and html and not names & _CACHE_HEADERS
                        and b"set-cookie" not in names):
                    headers += [(name.lower().encode("latin-1"), value.encode("latin-1"))
                                for name, value in lifetime.items()]
                    message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_lifetime)
