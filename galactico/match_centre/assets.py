"""The files under ``/static``: sheets, scripts, type and images, never a page.

Every page is served through the site shell (``galactico.site_nav.page``), which fills in its
head, header and footer. A page template asked for under ``/static`` would be a page without
the shell, and on the hosted app an archive page it does not serve (R7: the archive's research
copy and the StatsBomb logo never reach a hosted surface). So ``Assets`` refuses every
``.html`` file, and the hosted app also names the only files it serves (``HOSTED``): the
sheets and scripts of its own pages, the type and the images they load.
"""

from __future__ import annotations

from collections.abc import Collection

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

__all__ = ["HOSTED", "Assets"]

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
})
"""The files the hosted app serves under ``/static``: what its pages load, and nothing else."""


class Assets(StaticFiles):
    """``StaticFiles`` that never serves a page template, and, with ``allow``, only the files it
    names (paths relative to the directory)."""

    def __init__(self, *, directory: str, allow: Collection[str] | None = None) -> None:
        super().__init__(directory=directory)
        self.allow = frozenset(allow) if allow is not None else None

    async def get_response(self, path: str, scope: Scope) -> Response:
        name = path.replace("\\", "/").lstrip("/")
        if name.lower().endswith((".html", ".htm")) or (
                self.allow is not None and name not in self.allow):
            raise HTTPException(status_code=404)
        return await super().get_response(path, scope)
