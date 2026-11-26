"""The site shell: one navigation, drawn for the app that serves the page.

Corpus-free. Each test targets one way the shell could drift: a destination linked on an app
that does not serve it, two current marks, a page served without the shell, a route that used
to work and no longer does, a credit whose licence differs from the provider registry, or a
module the hosted function cannot import.
"""

from __future__ import annotations

import ast
import json
import re
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from galactico import site_nav
from galactico.api import shell
from galactico.domain.labels import scan_labels
from galactico.match_centre.openfootball import season_start
from galactico.match_centre.public import create_centre
from galactico.providers.base import PROVIDERS, DataTier

ROOT = Path(__file__).resolve().parents[1]
ALL_ROUTES = frozenset({href for item in site_nav.NAV for href in item.hrefs}
                       | {spec.path for spec in site_nav.PAGES.values()})
HOSTED_ROUTES = frozenset({"/", "/match-centre", "/match-centre/leagues",
                           "/match-centre/scouting", "/lineup", "/about"})
NAV_LINK = re.compile(r'<a href="([^"]+)" data-nav="(\w+)"((?: aria-current="\w+")?)>')


@pytest.fixture(scope="module")
def hosted():
    with TestClient(create_centre("Hosted")) as client:
        yield client


@pytest.fixture(scope="module")
def local():
    from galactico.api.player_lab import app

    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------- the module


def test_the_module_is_dependency_free_and_ships_with_the_hosted_function():
    tree = ast.parse((ROOT / "galactico" / "site_nav.py").read_text(encoding="utf-8"))
    imported = {alias.name.split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom) and node.module and not node.level}
    assert not any(isinstance(node, ast.ImportFrom) and node.level for node in ast.walk(tree))
    assert imported <= {"__future__", "html", "re", "collections", "dataclasses", "datetime",
                        "pathlib", "typing"}, imported
    include = json.loads((ROOT / "vercel.json").read_text())["builds"][0]["config"][
        "includeFiles"]
    assert "galactico/site_nav.py" in include
    # Everything the hosted centre imports from the package ships with it.
    shipped = {"match_centre", "providers", "site_nav"}
    for module in (ROOT / "galactico" / "match_centre").glob("*.py"):
        for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level == 2:
                names = [node.module] if node.module else [a.name for a in node.names]
                assert {name.split(".")[0] for name in names} <= shipped, (module.name, names)


def test_five_destinations_in_one_order():
    assert [item.label for item in site_nav.NAV] == [
        "Matches", "Table", "Players", "Lineup", "Squad & signings"]
    assert [item.hrefs for item in site_nav.NAV] == [
        ("/match-centre", "/"), ("/match-centre/leagues",), ("/player", "/match-centre/scouting"),
        ("/lineup", "/xi"), ("/squad", "/transfer")]
    assert "opponent" not in str(site_nav.NAV) and "desk" not in str(site_nav.NAV)
    assert scan_labels([item.label for item in site_nav.NAV]) == []


def test_the_nav_lists_only_what_the_app_serves_and_links_its_first_route():
    full = NAV_LINK.findall(site_nav.nav_markup(None, ALL_ROUTES))
    assert [(href, key) for href, key, _ in full] == [
        ("/match-centre", "matches"), ("/match-centre/leagues", "table"), ("/player", "players"),
        ("/lineup", "lineup"), ("/squad", "squad")]
    hosted = NAV_LINK.findall(site_nav.nav_markup(None, HOSTED_ROUTES))
    assert [(href, key) for href, key, _ in hosted] == [
        ("/match-centre", "matches"), ("/match-centre/leagues", "table"),
        ("/match-centre/scouting", "players"), ("/lineup", "lineup")]
    archive_only = NAV_LINK.findall(site_nav.nav_markup(None, {"/xi", "/transfer", "/"}))
    assert [(href, key) for href, key, _ in archive_only] == [
        ("/", "matches"), ("/xi", "lineup"), ("/transfer", "squad")]
    assert NAV_LINK.findall(site_nav.nav_markup(None, set())) == []
    assert "aria-current" not in site_nav.nav_markup(None, ALL_ROUTES)


@pytest.mark.parametrize("key", sorted(k for k, s in site_nav.PAGES.items() if s.nav))
def test_one_destination_is_current_and_says_whether_its_link_is_this_page(key):
    spec = site_nav.PAGES[key]
    nav = site_nav.nav_markup(spec.nav, ALL_ROUTES, spec.key)
    marks = [(href, k, mark) for href, k, mark in NAV_LINK.findall(nav) if mark]
    assert len(marks) == 1 and marks[0][1] == spec.nav
    href = marks[0][0]
    opens_this_page = href in (spec.path, *spec.aliases)
    assert marks[0][2] == (' aria-current="page"' if opens_this_page else ' aria-current="true"')
    assert nav.replace(marks[0][2], "") == site_nav.nav_markup(None, ALL_ROUTES)


@pytest.mark.parametrize("missing", ["opponent", "desk", "", "Matches"])
def test_a_destination_that_does_not_exist_has_no_nav_position(missing):
    with pytest.raises(ValueError, match="not a destination"):
        site_nav.nav_markup(missing, ALL_ROUTES)


def test_the_season_chip_names_the_season_of_every_number():
    for day, label in ((date(2026, 11, 26), "2026/27"), (date(2026, 7, 1), "2026/27"),
                       (date(2026, 6, 30), "2025/26"), (date(2030, 1, 1), "2029/30")):
        assert site_nav.current_season(day) == label
    for month in range(1, 13):
        day = date(2026, month, 15)
        start = season_start(day)
        assert site_nav.current_season(day) == f"{start}/{str(start + 1)[-2:]}"
    today = date(2026, 11, 26)
    chip = re.compile(r'<span class="season-chip" data-season="(\w+)"><span class="sr-only">'
                      r'Season </span>([^<]+)</span>')
    for spec in site_nav.PAGES.values():
        found = chip.findall(site_nav.header_markup(spec, ALL_ROUTES, today=today))
        expected = {"current": [("current", "2026/27")],
                    "archive": [("archive", "2017/18 archive · La Liga")], None: []}
        assert found == expected[spec.season], spec.key
    # A panel of a current-season page that draws from the archive says so itself: the lineup
    # studio's activity map, whose samples are archive matches. Its chip shows while one is
    # drawn and hides for a drawn role zone or the reader's own file.
    studio = (ROOT / "web" / "studio.html").read_text(encoding="utf-8")
    assert re.search(r'<span class="season-chip" data-season="archive" id="map-season" hidden'
                     r'\s*><span class="sr-only">Season </span>2017/18 archive</span', studio)
    script = (ROOT / "web" / "studio.js").read_text(encoding="utf-8")
    assert "$('map-season').hidden = role || !sample || Boolean(sample.imported);" in script


def test_every_page_has_one_title_in_one_pattern():
    titles = {key: site_nav.title(spec) for key, spec in site_nav.PAGES.items()}
    assert titles == {
        "matches": "Matches · Galáctico", "table": "Table · Galáctico",
        "scouting": "Goals by opponent · Players · Galáctico", "lineup": "Lineup · Galáctico",
        "player": "Player profiles · Players · Galáctico",
        "match": "Match reports · Matches · Galáctico",
        "xi": "Check against targets · Lineup · Galáctico",
        "squad": "Squad depth · Squad & signings · Galáctico",
        "transfer": "Signings · Squad & signings · Galáctico",
        "about": "About the numbers · Galáctico"}
    assert scan_labels(list(titles.values())) == []
    for spec in site_nav.PAGES.values():
        head = site_nav.head_markup(spec)
        assert head.startswith(f"<title>{site_nav._e(titles[spec.key])}</title>")
        # The type above the fold: the text, the upright headings and the wordmark.
        assert re.findall(r'<link rel="preload" href="/static/assets/type/([\w-]+\.woff2)"',
                          head) == ["dm-sans.woff2", "barlow.woff2", "barlow-italic.woff2"]
        assert '<script src="/static/site.js"></script>' in head
        markup = (ROOT / "web" / spec.file).read_text(encoding="utf-8")
        assert "<title>" not in markup[:markup.index("</head>")], spec.file
    for name in site_nav.PRELOADED_FONTS:
        assert (ROOT / "web" / "assets" / "type" / name).exists()
    with pytest.raises(ValueError, match="writes the <title>"):
        site_nav.render("<head><title>x</title></head>" + "".join(site_nav.PLACEHOLDERS),
                        site_nav.PAGES["about"], ALL_ROUTES)


SUBNAV = re.compile(r'<a href="([^"]+)" data-page="(\w+)"((?: aria-current="page")?)>'
                    r'<span class="site-subnav-name">([^<]+)</span> '
                    r'<span class="site-subnav-season">([^<]+)</span></a>')


def test_a_destination_with_two_pages_lists_both_under_the_header():
    today = date(2026, 11, 26)
    expected = {
        "matches": [("/match-centre", "Matches", "2026/27"),
                    ("/match", "Match reports", "2017/18 archive")],
        "players": [("/match-centre/scouting", "Goals by opponent", "2026/27"),
                    ("/player", "Player profiles", "2017/18 archive")],
        "lineup": [("/lineup", "Lineup", "2026/27"),
                   ("/xi", "Check against targets", "2017/18 archive")],
        "squad": [("/squad", "Squad depth", "2017/18 archive"),
                  ("/transfer", "Signings", "2017/18 archive")],
    }
    for spec in site_nav.PAGES.values():
        sub = site_nav.subnav_markup(spec, ALL_ROUTES, today=today)
        assert (sub in site_nav.header_markup(spec, ALL_ROUTES, today=today)) and (
            sub == "" or sub.endswith("</nav>"))
        if spec.nav not in expected:
            assert sub == "", spec.key
            continue
        links = SUBNAV.findall(sub)
        assert [(href, name, season) for href, _, _, name, season in links] == expected[spec.nav]
        assert [key for _, key, mark, _, _ in links if mark] == [spec.key]
        label = next(item.label for item in site_nav.NAV if item.key == spec.nav)
        assert f'aria-label="{site_nav._e(label)} pages"' in sub
        assert scan_labels([name for *_, name, _ in links]) == []
    # A destination with one page the app serves has no second row: the hosted app.
    for spec in site_nav.PAGES.values():
        assert site_nav.subnav_markup(spec, HOSTED_ROUTES, today=today) == ""


def test_the_credits_are_the_provider_registrys():
    for key, source in site_nav.SOURCES.items():
        posture = PROVIDERS[key]
        assert posture.tier is DataTier.PUBLIC and posture.may_host_derived, key
        assert source.licence in f"{posture.attribution} {posture.notes}", key
    for spec in site_nav.PAGES.values():
        footer = site_nav.footer_markup(spec, ALL_ROUTES)
        for key in spec.sources:
            assert site_nav.SOURCES[key].licence in footer
        assert "SIL Open Font License" in footer
        assert footer.count('href="/about"') == (0 if spec.key == "about" else 1)
    for _, path in site_nav.FONTS:
        assert (ROOT / "web" / path.removeprefix("/static/")).exists()


def test_the_chrome_colour_is_the_header_token():
    tokens = (ROOT / "web" / "tokens.css").read_text(encoding="utf-8")
    primitive = dict(re.findall(r"(--c-[\w-]+): (#[0-9a-f]{6});", tokens))
    headers = re.findall(r"--header-bg: var\((--c-[\w-]+)\);", tokens)
    assert [primitive[name] for name in headers] == [
        site_nav.THEME_COLOURS["light"], site_nav.THEME_COLOURS["dark"],
        site_nav.THEME_COLOURS["dark"]]


def test_a_page_without_its_placeholders_is_refused():
    spec = site_nav.PAGES["about"]
    whole = "".join(site_nav.PLACEHOLDERS)
    assert "site-header" in site_nav.render(whole, spec, ALL_ROUTES)
    for placeholder in site_nav.PLACEHOLDERS:
        with pytest.raises(ValueError, match="not once"):
            site_nav.render(whole.replace(placeholder, ""), spec, ALL_ROUTES)
        with pytest.raises(ValueError, match="not once"):
            site_nav.render(whole + placeholder, spec, ALL_ROUTES)
    with pytest.raises(ValueError, match="exactly once"):
        site_nav.render(whole, spec, ALL_ROUTES, slots={"sections": "x"})


# ---------------------------------------------------------------- both apps


def _shell_of(html: str) -> dict:
    return {
        "skip": html.count('<a class="skip-link" href="#main"'),
        "header": html.count('<header class="site-header"'),
        "nav": re.findall(r'<nav class="site-nav" aria-label="Main">(.*?)</nav>', html, re.S),
        "footer": html.count('<footer class="site-footer"'),
        "main": html.count('<main id="main"'),
    }


def _pages_served(client) -> list[str]:
    served = site_nav.served_paths(client.app)
    return sorted(spec.path for spec in site_nav.PAGES.values() if spec.path in served)


@pytest.mark.parametrize("app", ["hosted", "local"])
def test_every_page_is_served_inside_the_shell_with_links_the_app_serves(app, request):
    client = request.getfixturevalue(app)
    served = site_nav.served_paths(client.app)
    pages = _pages_served(client)
    assert set(pages) == ({"/match-centre", "/match-centre/leagues", "/match-centre/scouting",
                           "/lineup", "/about"} if app == "hosted"
                          else {spec.path for spec in site_nav.PAGES.values()})
    for path in [*pages, "/"]:
        reply = client.get(path)
        assert reply.status_code == 200 and reply.headers["content-type"].startswith("text/html")
        html = reply.text
        assert "<!--shell:" not in html and "<!--slot:" not in html, path
        parts = _shell_of(html)
        assert {k: v for k, v in parts.items() if k != "nav"} == {
            "skip": 1, "header": 1, "footer": 1, "main": 1}, path
        (nav,) = parts["nav"]
        links = NAV_LINK.findall(nav)
        assert [href for href, _, _ in links] == [
            next(h for h in item.hrefs if h in served) for item in site_nav.NAV
            if any(h in served for h in item.hrefs)]
        for href, _, _ in links:
            assert client.get(href).status_code == 200, href
        current = [key for _, key, mark in links if mark]
        assert len(current) == (0 if path == "/about" else 1), path
        # The new sheets load first, in layer order, before any sheet of the page.
        order = [html.index(f"/static/{name}") for name in ("tokens.css", "base.css",
                                                            "components.css")]
        assert order == sorted(order)
        first_old = min((m.start() for m in re.finditer(
            r'<link rel="stylesheet" href="/static/(?!tokens|base|components)|<style', html)),
            default=len(html))
        assert order[-1] < first_old, path
        assert scan_labels(shell.visible_text(html[:html.index("<main")])) == [], path
        assert scan_labels(shell.visible_text(html[html.rindex("</main>"):])) == [], path
    assert client.get("/static/tokens.css").status_code == 200
    assert client.get("/static/theme.js").status_code == 200
    assert client.get("/static/assets/favicon.svg").status_code == 200


def test_slash_is_matches_on_both_apps_and_old_links_keep_working(hosted, local):
    for client in (hosted, local):
        home = client.get("/")
        assert "<title>Matches · Galáctico</title>" in home.text
        assert 'data-nav="matches" aria-current="page"' in home.text
        # An old shared fixture link still opens the board, which reads its own query.
        assert "<title>Matches · Galáctico" in client.get("/?day=2026-09-01&match=x").text
        # Both moves are for good: permanent redirects that keep the method.
        demo = client.get("/match-centre/demo", follow_redirects=False)
        assert (demo.status_code, demo.headers["location"]) == (308, "/match-centre")
        for path in ("/match-centre", "/match-centre/leagues", "/match-centre/scouting",
                     "/lineup", "/about", "/match-centre?day=2026-09-01"):
            assert client.get(path).status_code == 200, path
    assert client.get("/static/matchroom-demo.html").status_code == 404
    # Player Lab moved to /player; an old link to / with a player or a view follows it there.
    moved = local.get("/?player=3359&view=compare", follow_redirects=False)
    assert moved.status_code == 308
    assert moved.headers["location"] == "/player?player=3359&view=compare"
    assert "<title>Player profiles · Players · Galáctico</title>" in local.get("/player").text
    for path in ("/match", "/xi", "/squad", "/transfer", "/match?id=2565907"):
        assert local.get(path).status_code == 200, path
    # The hosted app has no Player Lab: the same link opens Matches there, never a 404.
    stays = hosted.get("/?player=3359", follow_redirects=False)
    assert stays.status_code == 200 and "<title>Matches · Galáctico" in stays.text
    assert hosted.get("/player").status_code == 404


def test_about_the_numbers_lists_what_this_app_serves(hosted, local):
    sections = re.compile(r'<section class="page-section about-section" id="([\w-]+)"')
    answer = re.compile(r'<p class="page-answer">([^<]*)</p>')
    hosted_page = hosted.get("/about").text
    assert sections.findall(hosted_page) == ["sources"]
    # The hosted site serves no archive and no StatsBomb-derived analysis (R7).
    assert "StatsBomb" not in hosted_page and "Pappalardo" in hosted_page
    # It promises what it holds, and one section needs no list of contents.
    assert answer.findall(hosted_page) == ["Where every number comes from."]
    assert '<meta name="description" content="Where every number comes from.">' in hosted_page
    assert '<nav class="about-contents"' not in hosted_page
    local_page = local.get("/about").text
    assert sections.findall(local_page) == [
        "why-only-five", "evidence-classes", "verdicts", "not-measured", "sources"]
    assert answer.findall(local_page) == [
        "Why only five measures are shown, what kind of number each one is, which claims have "
        "been tested and how they stand, what this site does not measure and where every number "
        "comes from."]
    contents = re.search(r'<nav class="about-contents".*?</nav>', local_page, re.S).group(0)
    assert re.findall(r'href="#([\w-]+)"', contents) == sections.findall(local_page)
    # The sources table names every source the pages read; the one analysis formed from
    # another provider's data is named beside it, on the app that serves its page only.
    assert "formed from StatsBomb data" in local_page
    assert "A source that is not listed here is not used" not in local_page
    for page in (hosted_page, local_page):
        assert scan_labels(shell.visible_text(page)) == []
        assert page.count("<h1>") == 1
    # The archive sections are read where they are defined.
    for item in shell.NOT_MEASURED:
        assert item.reason in local_page
    for member in ("Observed", "Derived", "Estimated", "Predictive", "Optimized", "Heuristic",
                   "Experimental"):
        assert f"{member}</span>" in local_page
    assert local_page.count('data-verdict="RECORD_ONLY"') == 2
    assert 'href="/player"' in local_page


def _links(html: str) -> set[str]:
    return {href.split("#")[0] for href in re.findall(r'<a href="(/[^"?#]*)', html)}


@pytest.mark.parametrize("app", ["hosted", "local"])
def test_every_page_the_app_serves_is_reached_by_its_links_from_the_front_door(app, request):
    """A crawl of the served pages' own links, from ``/``: none is an island. Match reports and
    the XI check (the archive pages of Matches and Lineup) were reachable only from each other
    before the sub-navigation."""
    client = request.getfixturevalue(app)
    served = site_nav.served_paths(client.app)
    pages = {spec.path for spec in site_nav.PAGES.values() if spec.path in served}
    seen, queue = set(), ["/"]
    while queue:
        path = queue.pop()
        if path in seen or path not in served:
            continue
        seen.add(path)
        queue += sorted(_links(client.get(path).text) - seen)
    assert pages <= seen, sorted(pages - seen)
    # And each is at most two links from any other: its destination, then its row.
    for spec in site_nav.PAGES.values():
        if spec.path not in served or spec.nav is None:
            continue
        html = client.get(spec.path).text
        hop = _links(html)
        for other in pages - {spec.path}:
            if other in hop:
                continue
            assert any(other in _links(client.get(via).text) for via in hop if via in pages), (
                spec.path, other)


def test_about_says_so_when_the_archive_is_missing(monkeypatch, local):
    from fastapi import HTTPException

    from galactico.api import about, player_lab

    def missing():
        raise HTTPException(503, "profile artifacts not built")

    monkeypatch.setattr(player_lab.app.state, "about_sections",
                        about.sections(missing, note_base="https://example.org/"))
    page = local.get("/about").text
    assert about.UNAVAILABLE in page and "profile artifacts" not in page
    assert scan_labels(shell.visible_text(page)) == []
