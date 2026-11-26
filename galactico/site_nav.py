"""The site shell, written once and filled into every page by the app that serves it.

Claim: the skip link, the header (wordmark, navigation, season chip, theme switch), the phone
tab bar and the footer ("About the numbers" and the data credits of the page) of every HTML
page have one definition, here. A page file carries three placeholders, ``<!--shell:head-->``,
``<!--shell:header-->`` and ``<!--shell:footer-->``; ``page`` reads the file and fills them.
Both apps serve their pages through it: the full local app (``galactico.api.player_lab``)
and the hosted one (``galactico.match_centre.public``).

The navigation is deployment-aware. It lists a destination only when the serving app
registers one of its routes, and links to the first of them that it registers, so a link to
a page that does not exist is never drawn (it would be a 404). Five destinations, in this
order everywhere: Matches, Table, Players, Lineup, Squad & signings. Exactly one carries
``aria-current``: ``page`` when its link is the page shown, ``true`` when the page shown is
another page of that destination.

A destination with more than one page the app serves (Matches: the board and the archive
match reports; Players; Lineup; Squad & signings) gets a second row under the header, the
sub-navigation: every such page, named and labelled with its season, the one shown marked
``aria-current="page"``. So every page the app serves is one or two links from any other.

The season chip says which season every number on the page comes from: the current season
("2026/27") on the current-season pages, "2017/18 archive · La Liga" on the archive pages. A
panel of a current-season page that draws from the archive carries its own chip (the lineup
studio's activity map); the page's chip speaks for the rest.

Every page's ``<title>`` is written here, in one pattern: "<page> · <destination> ·
Galáctico", or "<destination> · Galáctico" where the page is named as its destination.

Non-claim: the shell writes no football sentence and reads no data. The "About the numbers"
page is assembled here from sections the serving app hands over (``app.state.about_sections``)
and from the data credits below; the shell writes none of their content.

Dependency-free on purpose: standard library only, importing nothing from ``galactico``, so
the hosted function can ship this one file (``vercel.json`` ``includeFiles``).
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

__all__ = [
    "ARCHIVE_SEASON",
    "BRAND",
    "NAV",
    "PAGES",
    "PLACEHOLDERS",
    "SOURCES",
    "THEME_COLOURS",
    "NavItem",
    "Page",
    "Section",
    "Source",
    "about",
    "current_season",
    "footer_markup",
    "head_markup",
    "header_markup",
    "nav_markup",
    "page",
    "render",
    "served_paths",
    "sources_section",
    "subnav_markup",
    "title",
]

WEB = Path(__file__).resolve().parent.parent / "web"
BRAND = "Galáctico"
ARCHIVE_SEASON = "2017/18 archive · La Liga"
ARCHIVE_SHORT = "2017/18 archive"
"""The archive's season where the league goes without saying: the sub-navigation."""

PLACEHOLDERS = ("<!--shell:head-->", "<!--shell:header-->", "<!--shell:footer-->")
"""Each page file holds each of these exactly once."""

THEME_COLOURS = {"light": "#151937", "dark": "#161a2e"}
"""The browser chrome colour per theme: tokens.css's --header-bg, which a test holds equal."""

_ICON = ('<svg class="site-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
         'aria-hidden="true" focusable="false">{}</svg>')


@dataclass(frozen=True)
class NavItem:
    """One destination. ``hrefs`` in preference order: the first the app serves is the link."""

    key: str
    label: str
    hrefs: tuple[str, ...]
    icon: str


NAV: tuple[NavItem, ...] = (
    NavItem("matches", "Matches", ("/match-centre", "/"),
            '<circle cx="12" cy="12" r="9"/><path d="M12 7.5l4 2.9-1.5 4.6h-5L8 10.4z"/>'),
    NavItem("table", "Table", ("/match-centre/leagues",),
            '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M3 14h18M9 4v16"/>'),
    NavItem("players", "Players", ("/player", "/match-centre/scouting"),
            '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>'),
    NavItem("lineup", "Lineup", ("/lineup", "/xi"),
            '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 12h18"/>'
            '<circle cx="12" cy="12" r="3"/>'),
    NavItem("squad", "Squad & signings", ("/squad", "/transfer"),
            '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/>'
            '<path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14.3c2.1.7 3.5 2.6 3.5 5.7"/>'),
)
"""The five destinations, in the one order every page shows them."""


@dataclass(frozen=True)
class Source:
    """A data source a page reads, as its credit line prints it."""

    key: str
    name: str
    used_for: str
    licence: str
    licence_url: str
    url: str


SOURCES: dict[str, Source] = {source.key: source for source in (
    Source("openfootball", "OpenFootball", "Fixtures, results and league tables, 2026/27",
           "CC0 1.0", "https://github.com/openfootball/football.json/blob/master/LICENSE.md",
           "https://github.com/openfootball/football.json"),
    Source("openligadb", "OpenLigaDB", "Goal reports, 2026/27",
           "ODbL 1.0", "https://opendatacommons.org/licenses/odbl/1-0/",
           "https://www.openligadb.de/"),
    Source("wikipedia", "Wikipedia contributors", "Squad, appearances and goals, 2026/27",
           "CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/",
           "https://en.wikipedia.org/"),
    Source("pappalardo", "Pappalardo et al. / Wyscout", "Match events, 2017/18 archive",
           "CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/",
           "https://doi.org/10.6084/m9.figshare.c.4415000"),
)}
"""The hostable sources the pages read. Their licences are the provider registry's
(``galactico.providers.base.PROVIDERS``); a test holds the two equal."""

FONTS = (("DM Sans", "/static/assets/type/dmsans-OFL.txt"),
         ("Barlow Condensed", "/static/assets/type/barlowcondensed-OFL.txt"))


@dataclass(frozen=True)
class Page:
    """One HTML page: its file, the routes that serve it, its destination, its season and its
    name, which its title and the sub-navigation print."""

    key: str
    file: str
    path: str
    nav: str | None
    season: str | None
    name: str
    sources: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()


PAGES: dict[str, Page] = {item.key: item for item in (
    Page("matches", "match-centre.html", "/match-centre", "matches", "current", "Matches",
         ("openfootball",), aliases=("/",)),
    Page("table", "leagues.html", "/match-centre/leagues", "table", "current", "Table",
         ("openfootball",)),
    Page("scouting", "scouting.html", "/match-centre/scouting", "players", "current",
         "Goals by opponent", ("openligadb", "openfootball")),
    Page("lineup", "studio.html", "/lineup", "lineup", "current", "Lineup",
         ("wikipedia", "openligadb", "openfootball", "pappalardo")),
    Page("player", "index.html", "/player", "players", "archive", "Player profiles",
         ("pappalardo",)),
    Page("match", "match.html", "/match", "matches", "archive", "Match reports",
         ("pappalardo",)),
    Page("xi", "xi.html", "/xi", "lineup", "archive", "Check against targets", ("pappalardo",)),
    Page("squad", "squad.html", "/squad", "squad", "archive", "Squad depth", ("pappalardo",)),
    Page("transfer", "transfer.html", "/transfer", "squad", "archive", "Signings",
         ("pappalardo",)),
    Page("about", "about.html", "/about", None, None, "About the numbers"),
)}
"""Every page the apps serve through the shell, the current season's first within a
destination (the sub-navigation's order). ``/`` serves the Matches page."""

_NAV_KEYS = frozenset(item.key for item in NAV)
_SEASONS = frozenset({"current", "archive"})
for _page in PAGES.values():
    if _page.nav is not None and _page.nav not in _NAV_KEYS:
        raise ValueError(f"{_page.key}: {_page.nav!r} is not a destination")
    if _page.season is not None and _page.season not in _SEASONS:
        raise ValueError(f"{_page.key}: {_page.season!r} is not a season kind")
    if not set(_page.sources) <= set(SOURCES):
        raise ValueError(f"{_page.key}: an unknown source in {_page.sources}")
del _page

_PAGE_AT: dict[str, str] = {path: spec.key for spec in PAGES.values()
                            for path in (spec.path, *spec.aliases)}


def _e(value: str) -> str:
    return html.escape(value, quote=True)


def _serves(app: Any, path: str) -> bool:
    # Asked the way a request asks: each route of the app matches a GET scope for the path.
    # An included router is matched through, whatever form the framework keeps it in.
    scope = {"type": "http", "method": "GET", "path": path, "root_path": "",
             "query_string": b"", "headers": []}
    for route in getattr(app, "routes", ()):
        matches = getattr(route, "matches", None)
        if matches is not None and getattr(matches(scope)[0], "name", None) == "FULL":
            return True
    return False


def served_paths(app: Any) -> frozenset[str]:
    """The paths of the shell's pages and links that ``app`` answers a GET for."""
    wanted = {href for item in NAV for href in item.hrefs} | set(_PAGE_AT)
    return frozenset(path for path in wanted if _serves(app, path))


def current_season(today: date) -> str:
    """"2026/27" for any day from 1 July 2026 to 30 June 2027.

    The rule of ``galactico.match_centre.openfootball.season_start``; a test holds them equal.
    """
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start}/{(start + 1) % 100:02d}"


def _season_label(kind: str | None, today: date, *, short: bool = False) -> str | None:
    if kind == "current":
        return current_season(today)
    if kind == "archive":
        return ARCHIVE_SHORT if short else ARCHIVE_SEASON
    return None


def title(spec: Page) -> str:
    """The page's ``<title>``: "<page> · <destination> · Galáctico"."""
    destination = next((item.label for item in NAV if item.key == spec.nav), None)
    parts = [spec.name] if destination in (None, spec.name) else [spec.name, destination]
    return " · ".join([*parts, BRAND])


def _link(item: NavItem, routes: Collection[str]) -> str | None:
    return next((href for href in item.hrefs if href in routes), None)


def nav_markup(current: str | None, routes: Collection[str], shown: str | None = None) -> str:
    """The ``<nav>`` of the header, which is the tab bar on a phone.

    ``current`` is a destination key or ``None``. ``shown`` is the key of the page shown: the
    current destination is marked ``aria-current="page"`` when its link opens that page, and
    ``"true"`` when it opens another page of the destination. A destination the app does not
    serve is left out, and an unknown ``current`` raises.
    """
    if current is not None and current not in _NAV_KEYS:
        raise ValueError(f"{current!r} is not a destination; destinations are "
                         f"{[item.key for item in NAV]}")
    links: list[str] = []
    for item in NAV:
        href = _link(item, routes)
        if href is None:
            continue
        mark = ""
        if item.key == current:
            here = shown is not None and _PAGE_AT.get(href) == shown
            mark = ' aria-current="page"' if here else ' aria-current="true"'
        links.append(f'<a href="{_e(href)}" data-nav="{item.key}"{mark}>'
                     f'{_ICON.format(item.icon)}<span>{_e(item.label)}</span></a>')
    return f'<nav class="site-nav" aria-label="Main">{"".join(links)}</nav>'


_THEME_ICON = ('<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">'
               '<circle cx="10" cy="10" r="7.2" fill="none" stroke="currentColor" '
               'stroke-width="1.6"/><path class="theme-toggle-half" '
               'd="M10 2.8a7.2 7.2 0 0 1 0 14.4z" fill="currentColor"/></svg>')


_CURRENT = ' aria-current="page"'


def subnav_markup(spec: Page, routes: Collection[str], *, today: date | None = None) -> str:
    """The pages of the shown page's destination that the app serves, when there are two or
    more: each named, with its season, the one shown marked ``aria-current="page"``."""
    if spec.nav is None:
        return ""
    pages = [other for other in PAGES.values() if other.nav == spec.nav and other.path in routes]
    if len(pages) < 2:
        return ""
    today = today or datetime.now(UTC).date()
    label = next(item.label for item in NAV if item.key == spec.nav)
    links = "".join(
        f'<a href="{_e(other.path)}" data-page="{other.key}"'
        f'{_CURRENT if other.key == spec.key else ""}>'
        f'<span class="site-subnav-name">{_e(other.name)}</span> <span class="site-subnav-season">'
        f'{_e(_season_label(other.season, today, short=True) or "")}</span></a>'
        for other in pages)
    return (f'<nav class="site-subnav" aria-label="{_e(label)} pages" data-shell>'
            f'<div class="site-frame site-subnav-inner">{links}</div></nav>')


def header_markup(spec: Page, routes: Collection[str], *, today: date | None = None) -> str:
    """The skip link, the header (wordmark, navigation, season chip and theme switch) and,
    under it, the sub-navigation of the destination shown."""
    today = today or datetime.now(UTC).date()
    home = "/" if "/" in routes else next(
        (href for item in NAV if (href := _link(item, routes))), "/")
    season = _season_label(spec.season, today)
    chip = ""
    if season is not None:
        chip = (f'<span class="season-chip" data-season="{spec.season}">'
                f'<span class="sr-only">Season </span>{_e(season)}</span>')
    return (
        '<a class="skip-link" href="#main" data-shell>Skip to content</a>'
        '<header class="site-header" data-shell><div class="site-frame site-header-inner">'
        f'<a class="wordmark" href="{_e(home)}"><span class="wordmark-g" aria-hidden="true">G'
        f'</span><span class="wordmark-text">{_e(BRAND)}</span></a>'
        f'{nav_markup(spec.nav, routes, spec.key)}'
        f'<div class="site-tools">{chip}'
        '<button type="button" class="theme-toggle" data-theme-toggle aria-pressed="false" '
        f'title="Dark theme" hidden>{_THEME_ICON}<span class="sr-only">Dark theme</span>'
        '</button></div></div></header>'
        f'{subnav_markup(spec, routes, today=today)}'
    )


def _credit(source: Source) -> str:
    return (f'<a href="{_e(source.url)}">{_e(source.name)}</a> '
            f'(<a href="{_e(source.licence_url)}">{_e(source.licence)}</a>)')


def footer_markup(spec: Page, routes: Collection[str]) -> str:
    """The footer: "About the numbers", the page's data credits and the type credit."""
    about = PAGES["about"].path
    links = (f'<ul class="site-footer-links"><li><a href="{about}">About the numbers</a></li></ul>'
             if about in routes and spec.key != "about" else "")
    credits = ""
    if spec.sources:
        credits = ("<p>Data: " + " · ".join(_credit(SOURCES[key]) for key in spec.sources)
                   + ".</p>")
    fonts = " and ".join(f'{_e(name)} (<a href="{_e(url)}">SIL Open Font License</a>)'
                         for name, url in FONTS)
    return ('<footer class="site-footer" data-shell><div class="site-frame site-footer-inner">'
            f'{links}{credits}<p>Type: {fonts}.</p></div></footer>')


PRELOADED_FONTS = ("dm-sans.woff2", "barlow.woff2", "barlow-italic.woff2")
"""The type above the fold of every page: the text, the headings and the wordmark."""


def head_markup(spec: Page) -> str:
    """What every page loads before its own sheets: its title, the type above the fold, the
    three sheets in layer order, the theme switch and the site script, the icon and the chrome
    colour per theme."""
    fonts = "".join(f'<link rel="preload" href="/static/assets/type/{name}" as="font" '
                    'type="font/woff2" crossorigin>' for name in PRELOADED_FONTS)
    return (
        f'<title>{_e(title(spec))}</title>{fonts}'
        '<link rel="icon" href="/static/assets/favicon.svg" type="image/svg+xml">'
        '<meta name="color-scheme" content="light dark">'
        f'<meta name="theme-color" media="(prefers-color-scheme: light)" '
        f'content="{THEME_COLOURS["light"]}">'
        f'<meta name="theme-color" media="(prefers-color-scheme: dark)" '
        f'content="{THEME_COLOURS["dark"]}">'
        '<link rel="stylesheet" href="/static/tokens.css">'
        '<link rel="stylesheet" href="/static/base.css">'
        '<link rel="stylesheet" href="/static/components.css">'
        '<script src="/static/theme.js"></script>'
        '<script src="/static/site.js"></script>'
    )


def render(markup: str, spec: Page, routes: Collection[str], *, today: date | None = None,
           slots: dict[str, str] | None = None) -> str:
    """``markup`` with the shell filled in. Each placeholder must occur exactly once.

    ``slots`` fills further ``<!--slot:name-->`` placeholders of the page with server markup.
    """
    for placeholder in PLACEHOLDERS:
        found = markup.count(placeholder)
        if found != 1:
            raise ValueError(f"{spec.file}: {placeholder} occurs {found} times, not once")
    if "<title>" in markup[:markup.find("</head>")]:
        raise ValueError(f"{spec.file}: the shell writes the <title>; the page's head holds none")
    # The skip link's target takes focus, so a keyboard reader goes on from there.
    if markup.count('<main id="main"') == 1:
        markup = markup.replace('<main id="main"', '<main id="main" tabindex="-1"')
    filled = (markup.replace(PLACEHOLDERS[0], head_markup(spec))
              .replace(PLACEHOLDERS[1], header_markup(spec, routes, today=today))
              .replace(PLACEHOLDERS[2], footer_markup(spec, routes)))
    for name, value in (slots or {}).items():
        slot = f"<!--slot:{name}-->"
        if filled.count(slot) != 1:
            raise ValueError(f"{spec.file}: {slot} must occur exactly once")
        filled = filled.replace(slot, value)
    return filled


def page(request: Any, key: str, *, slots: dict[str, str] | None = None) -> str:
    """The page ``key`` as the app serving ``request`` shows it. Routes return it as HTML."""
    spec = PAGES[key]
    markup = (WEB / spec.file).read_text(encoding="utf-8")
    return render(markup, spec, served_paths(request.app), slots=slots)


# ------------------------------------------------------------------ About the numbers


@dataclass(frozen=True)
class Section:
    """One section of "About the numbers". ``body`` is markup the server wrote, with every
    served string in it escaped. ``key`` is a plain word: the section's anchor. ``answers`` is
    the clause the page's opening sentence gives it ("what this site does not measure"), so the
    sentence promises only the sections the page holds."""

    key: str
    heading: str
    body: str
    answers: str = ""

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", self.key):
            raise ValueError(f"{self.key!r} is not a plain anchor")


def sources_section(routes: Collection[str]) -> Section:
    """The data sources of the pages this app serves, with their licences, and the type."""
    used: list[str] = []
    for spec in PAGES.values():
        if spec.path in routes:
            used += [key for key in spec.sources if key not in used]
    rows = "".join(
        f'<tr><th scope="row" data-label="Source"><a href="{_e(s.url)}">{_e(s.name)}</a></th>'
        f'<td data-label="Used for">{_e(s.used_for)}</td>'
        f'<td data-label="Licence"><a href="{_e(s.licence_url)}">{_e(s.licence)}</a></td></tr>'
        for s in (SOURCES[key] for key in used))
    rows += "".join(
        f'<tr><th scope="row" data-label="Source">{_e(name)}</th>'
        '<td data-label="Used for">Typeface</td>'
        f'<td data-label="Licence"><a href="{_e(url)}">SIL Open Font License 1.1</a></td></tr>'
        for name, url in FONTS)
    said = ('The numbers on these pages come from these sources, and each page names its own '
            'in the footer.')
    if PAGES["player"].path in routes:
        said += (' The research analysis under Why only five? on the Player profiles page '
                 'comes from elsewhere: it is formed from StatsBomb data, shown only on a local '
                 "install, and credited there with the provider's logo.")
    body = (f'<p>{_e(said)}</p>'
            '<div class="ui-table-wrap"><table class="ui-table ui-table-stack">'
            '<caption>Data sources and licences, in the order the pages use them</caption>'
            '<thead><tr><th scope="col">Source</th><th scope="col">Used for</th>'
            f'<th scope="col">Licence</th></tr></thead><tbody>{rows}</tbody></table></div>')
    return Section("sources", "Data sources and licences", body,
                   answers="where every number comes from")


AboutBuilder = Callable[[], "Section | None"]


def about(request: Any) -> str:
    """"About the numbers": the sections the serving app hands over, then the sources.

    ``app.state.about_sections`` is a sequence of callables, each returning a ``Section`` or
    ``None``. The hosted app hands over none: it serves no archive, so the page lists its
    sources only.
    """
    routes = served_paths(request.app)
    state = getattr(request.app, "state", None)
    builders: Sequence[AboutBuilder] = getattr(state, "about_sections", ()) or ()
    sections = [section for build in builders if (section := build()) is not None]
    sections.append(sources_section(routes))
    answer = _answer(sections)
    return page(request, "about", slots={
        "description": _e(answer),
        "answer": _e(answer),
        "contents": _contents(sections),
        "sections": "".join(_section(section) for section in sections),
    })


def _answer(sections: Sequence[Section]) -> str:
    """The page's opening sentence, from the sections it holds and nothing more."""
    clauses = [section.answers for section in sections if section.answers]
    if not clauses:
        return ""
    joined = clauses[0] if len(clauses) == 1 else ", ".join(clauses[:-1]) + " and " + clauses[-1]
    return joined[0].upper() + joined[1:] + "."


def _contents(sections: Sequence[Section]) -> str:
    # One section needs no list of contents.
    if len(sections) < 2:
        return ""
    items = "".join(f'<li><a href="#{s.key}">{_e(s.heading)}</a></li>' for s in sections)
    return f'<nav class="about-contents" aria-label="On this page"><ul>{items}</ul></nav>'


def _section(section: Section) -> str:
    return (f'<section class="page-section about-section" id="{section.key}" '
            f'aria-labelledby="{section.key}-title"><h2 id="{section.key}-title">'
            f'{_e(section.heading)}</h2>{section.body}</section>')
