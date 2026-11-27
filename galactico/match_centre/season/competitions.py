"""The competitions the season pages cover, in the one order every list uses (PR 2.1).

This is configuration in code, not data: which competitions exist on the site, their slugs,
which source carries each, and the order. Real Madrid's competitions come first, then a fixed
order, and a page that lists competitions prints ``ORDER_LINE`` once.

Each entry names the source codes a reader of it needs:

- ``fd_code``: football-data.org's competition code, where football-data.org carries it;
- ``ol_shortcut``: OpenLigaDB's league shortcut, where OpenLigaDB carries it (the Bundesliga and
  the Premier League as fills, the Champions League and the Europa League alone);
- ``of_file``: OpenFootball's season file, for the five leagues it publishes.

``madrid_only`` marks the two Spanish cups no free source carries beyond Real Madrid's own ties,
which come from Wikipedia. ``gate`` names a root decision that must pass before a competition is
shown (the Copa Libertadores waits on probe 3, P-D9). ``zones`` is the id ``zones.py`` keys its
table zones by; a competition with no table has none.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from .model import Competition, Kind

__all__ = ["CompetitionConfig", "COMPETITIONS", "ORDER_LINE", "BY_SLUG", "BY_FD_CODE",
           "by_slug", "by_fd_code", "season_year", "season_label", "competition"]

ORDER_LINE = "Real Madrid’s competitions first, then a fixed order."


@dataclass(frozen=True)
class CompetitionConfig:
    slug: str
    name: str
    area: str
    kind: Kind
    order: int
    fd_code: str | None
    ol_shortcut: str | None
    of_file: str | None
    madrid_only: bool
    zones: str | None
    span: Literal["split", "calendar"]
    """A split season runs across two years ("2026/27"); a calendar one within one ("2026")."""
    gate: str | None = None


def _entry(order: int, slug: str, name: str, area: str, kind: Kind, *, fd: str | None = None,
           ol: str | None = None, of: str | None = None, madrid_only: bool = False,
           table: bool = True, span: Literal["split", "calendar"] = "split",
           gate: str | None = None) -> CompetitionConfig:
    return CompetitionConfig(slug=slug, name=name, area=area, kind=kind, order=order, fd_code=fd,
                             ol_shortcut=ol, of_file=of, madrid_only=madrid_only,
                             zones=slug if table else None, span=span, gate=gate)


COMPETITIONS: tuple[CompetitionConfig, ...] = (
    _entry(1, "la-liga", "La Liga", "Spain", "league", fd="PD", of="es.1"),
    _entry(2, "champions-league", "Champions League", "Europe", "league_phase", fd="CL",
           ol="ucl"),
    _entry(3, "copa-del-rey", "Copa del Rey", "Spain", "cup", madrid_only=True, table=False),
    _entry(4, "supercopa", "Supercopa de España", "Spain", "cup", madrid_only=True,
           table=False),
    _entry(5, "premier-league", "Premier League", "England", "league", fd="PL", ol="pl",
           of="en.1"),
    _entry(6, "bundesliga", "Bundesliga", "Germany", "league", fd="BL1", ol="bl1", of="de.1"),
    _entry(7, "serie-a", "Serie A", "Italy", "league", fd="SA", of="it.1"),
    _entry(8, "ligue-1", "Ligue 1", "France", "league", fd="FL1", of="fr.1"),
    _entry(9, "europa-league", "Europa League", "Europe", "league_phase", ol="uel2026"),
    _entry(10, "eredivisie", "Eredivisie", "Netherlands", "league", fd="DED"),
    _entry(11, "primeira-liga", "Primeira Liga", "Portugal", "league", fd="PPL"),
    _entry(12, "championship", "Championship", "England", "league", fd="ELC"),
    _entry(13, "brasileirao", "Brasileirão Série A", "Brazil", "league", fd="BSA",
           span="calendar"),
    _entry(14, "copa-libertadores", "Copa Libertadores", "South America", "tournament",
           fd="CLI", span="calendar", gate="P-D9"),
    _entry(15, "world-cup", "World Cup", "World", "tournament", fd="WC", span="calendar"),
)
"""Every competition, in PR 2.1's order. Nothing else orders competitions."""

BY_SLUG: dict[str, CompetitionConfig] = {c.slug: c for c in COMPETITIONS}
BY_FD_CODE: dict[str, CompetitionConfig] = {c.fd_code: c for c in COMPETITIONS if c.fd_code}


def by_slug(slug: str) -> CompetitionConfig | None:
    return BY_SLUG.get(slug)


def by_fd_code(code: str) -> CompetitionConfig | None:
    """The competition football-data.org calls ``code``; ``None`` for one the site does not
    cover (the European Championship, for example)."""
    return BY_FD_CODE.get(code)


def season_year(config: CompetitionConfig, day: date) -> int:
    """The year football-data.org names ``day``'s season by: its first year. A split season
    starts in July, so 26 November 2026 is in 2026/27 and 10 March 2027 is too; a calendar
    season is its year."""
    if config.span == "calendar":
        return day.year
    return day.year if day.month >= 7 else day.year - 1


def season_label(config: CompetitionConfig, year: int) -> str:
    """"2026/27" for a split season starting in 2026; "2026" for a calendar one."""
    if config.span == "calendar":
        return str(year)
    return f"{year}/{(year + 1) % 100:02}"


def competition(config: CompetitionConfig, year: int, *, current_matchday: int | None = None,
                matchdays: int | None = None) -> Competition:
    """The model object for ``config``'s season starting in ``year``. The matchday figures are
    the caller's, read from a source or derived from the season's matches; none is assumed."""
    return Competition(slug=config.slug, name=config.name, area=config.area, kind=config.kind,
                       order=config.order, fd_code=config.fd_code,
                       ol_shortcut=config.ol_shortcut, of_file=config.of_file,
                       madrid_only=config.madrid_only, season=season_label(config, year),
                       current_matchday=current_matchday, matchdays=matchdays)
