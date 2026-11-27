"""Hosting hygiene (PLAN D4-A, PLATFORM 3.6 and 5.4): how long a browser and the CDN may keep
each file under ``/static`` and each page, the content-versioned addresses the pages load the
files at, and the shell's work done once rather than on every request.

Corpus-free. Each test targets one way the hosted app could spend its capped invocations or
show a reader a stale file:

- a sheet, script or font served with no lifetime (every page view invokes the function);
- a file kept for a year at an address that does not change when the file does;
- a versioned address a page writes that ``/static`` does not answer as such;
- a page, or the designed "not here" page, served with no lifetime, or a reply that must not
  be kept (an API, a cookie, a route's own header) given one;
- a file under ``web/season/`` refused, or a page template under it served;
- a page file read, or the app's routes matched, on every request;
- an entity page's title, credits or canonical address not the ones the route hands over.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from galactico import site_nav
from galactico.match_centre import assets
from galactico.match_centre.assets import (
    HOSTED,
    MISSING_PAGE,
    PAGE,
    UNVERSIONED,
    VERSIONED,
    Assets,
    PageCache,
    allowed,
)
from galactico.match_centre.public import create_centre

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
HOSTED_PAGES = ("/", "/match-centre", "/match-centre/leagues", "/match-centre/scouting",
                "/lineup", "/about")
VERSIONED_URL = re.compile(r'(?:href|src)="(/static/[^"?#]+)\?v=([0-9a-f]{8})"')


def sha8(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def lifetime(reply) -> dict[str, str | None]:
    return {name: reply.headers.get(name) for name in ("Cache-Control",
                                                       "Vercel-CDN-Cache-Control")}


@pytest.fixture(scope="module")
def hosted():
    # The hosted app as it ships: create_centre installs the page lifetimes (no private feed).
    app = create_centre("Hosted")
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def local():
    from galactico.api.player_lab import app

    with TestClient(app) as client:
        yield client


# ------------------------------------------------------------------ /static


def test_a_file_at_its_version_is_kept_a_year_and_at_its_plain_address_ten_minutes(hosted):
    current = sha8(WEB / "tokens.css")
    assert lifetime(hosted.get(f"/static/tokens.css?v={current}")) == dict(VERSIONED)
    assert VERSIONED["Cache-Control"] == "public, max-age=31536000, immutable"
    assert VERSIONED["Vercel-CDN-Cache-Control"].startswith("s-maxage=31536000")
    for plain in ("/static/tokens.css", "/static/assets/type/dm-sans.woff2",
                  "/static/tokens.css?v=00000000", f"/static/base.css?v={current}"):
        # The plain address, a font its sheet loads, a stale version, another file's version.
        reply = hosted.get(plain)
        assert reply.status_code == 200 and lifetime(reply) == dict(UNVERSIONED), plain
    assert UNVERSIONED == {"Cache-Control": "public, max-age=600",
                           "Vercel-CDN-Cache-Control": "s-maxage=86400, stale-if-error=86400"}


def test_a_revalidation_and_a_head_carry_the_lifetime_and_a_missing_file_none(hosted):
    first = hosted.get("/static/site.js")
    again = hosted.get("/static/site.js", headers={"if-none-match": first.headers["etag"]})
    assert again.status_code == 304 and lifetime(again) == dict(UNVERSIONED)
    head = hosted.head(f"/static/site.js?v={sha8(WEB / 'site.js')}")
    assert head.status_code == 200 and lifetime(head) == dict(VERSIONED)
    for gone in ("/static/nope.css", "/static/match.html", "/static/index.html"):
        reply = hosted.get(gone)
        assert reply.status_code == 404 and lifetime(reply) == {
            "Cache-Control": None, "Vercel-CDN-Cache-Control": None}, gone


def test_the_local_app_keeps_the_same_lifetimes(local):
    version = sha8(WEB / "labs.css")
    assert lifetime(local.get(f"/static/labs.css?v={version}")) == dict(VERSIONED)
    assert lifetime(local.get("/static/labs.css")) == dict(UNVERSIONED)


def test_every_versioned_address_a_page_writes_is_answered_as_one(hosted):
    found: dict[str, str] = {}
    for path in HOSTED_PAGES:
        page = hosted.get(path).text
        found |= dict(VERSIONED_URL.findall(page))
        head = page[:page.index("</head>")]
        # The shell's sheets, scripts and icon are versioned; the type is preloaded at the
        # plain address base.css loads it from, so it is fetched once.
        for name in (*site_nav.SHELL_SHEETS, *site_nav.SHELL_SCRIPTS, "assets/favicon.svg"):
            assert f'/static/{name}?v=' in head, (path, name)
        for font in site_nav.PRELOADED_FONTS:
            assert f'href="/static/assets/type/{font}" as="font"' in head
            assert f'url("/static/assets/type/{font}")' in (WEB / "base.css").read_text()
    assert set(found) >= {f"/static/{name}" for name in site_nav.SHELL_SHEETS}
    for url, version in found.items():
        assert version == sha8(WEB / url.removeprefix("/static/")), url
        reply = hosted.get(f"{url}?v={version}")
        assert reply.status_code == 200 and lifetime(reply) == dict(VERSIONED), url


def test_a_version_changes_exactly_when_the_file_does(tmp_path):
    sheet = tmp_path / "x.css"
    sheet.write_text("a{}", encoding="utf-8")
    first = site_nav.asset_version(sheet)
    assert first == sha8(sheet)
    sheet.write_text("a{}", encoding="utf-8")
    assert site_nav.asset_version(sheet) == first, "the same bytes keep their address"
    stamp = sheet.stat()
    sheet.write_text("b{}", encoding="utf-8")
    # A file's time can be coarser than two writes apart: the edit is dated a second later.
    os.utime(sheet, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 10**9))
    assert site_nav.asset_version(sheet) not in (None, first)
    assert site_nav.asset_version(tmp_path / "gone.css") is None
    assert site_nav.asset_url("x.css", web=tmp_path) == f"/static/x.css?v={sha8(sheet)}"
    for bad in ("../tokens.css", "/etc/passwd", "a//b.css", "gone.css", "a b.css"):
        with pytest.raises(ValueError):
            site_nav.asset_url(bad, web=tmp_path)


def test_the_season_folder_is_served_whole_and_never_a_page_template(tmp_path):
    (tmp_path / "season" / "parts").mkdir(parents=True)
    for name in ("season/kit.js", "season/parts/team.css", "season/team.html", "other.css"):
        (tmp_path / name).write_text("/* x */", encoding="utf-8")
    assert "season/" in HOSTED
    app = FastAPI()
    app.mount("/static", Assets(directory=str(tmp_path), allow=HOSTED), name="static")
    with TestClient(app) as client:
        for name in ("season/kit.js", "season/parts/team.css"):
            reply = client.get(f"/static/{name}")
            assert reply.status_code == 200 and lifetime(reply) == dict(UNVERSIONED), name
        for name in ("season/team.html", "season/TEAM.HTML", "other.css",
                     "season/../other.css", "season"):
            assert client.get(f"/static/{name}").status_code == 404, name
    assert allowed("season/a/b.js", HOSTED) and not allowed("seasons/a.js", HOSTED)
    assert not allowed("season", HOSTED) and allowed("tokens.css", HOSTED)


# ------------------------------------------------------------------ the pages


def test_the_page_lifetimes_are_installed_only_where_no_private_feed_is_mounted():
    from galactico.match_centre.local import create_app

    def lifetimes(app):
        return [m for m in app.user_middleware if m.cls is PageCache]

    assert len(lifetimes(create_centre("Hosted"))) == 1
    assert lifetimes(create_centre("Private", private=object())) == []
    # The private centre without a key is the public one behind loopback: its no-store
    # middleware is outermost, so a reader's browser keeps nothing it serves.
    with TestClient(create_app(None), base_url="http://127.0.0.1",
                    client=("127.0.0.1", 50000)) as client:
        reply = client.get("/about")
        assert reply.status_code == 200 and reply.headers["cache-control"] == "no-store"


def test_every_page_and_the_designed_404_carry_a_lifetime(hosted):
    for path in HOSTED_PAGES:
        reply = hosted.get(path)
        assert reply.status_code == 200 and lifetime(reply) == dict(PAGE), path
    assert PAGE == {"Cache-Control": "max-age=0", "Vercel-CDN-Cache-Control":
                    "s-maxage=600, stale-while-revalidate=3600, stale-if-error=86400"}
    missing = hosted.get("/nope", headers={"accept": "text/html"})
    assert missing.status_code == 404 and lifetime(missing) == dict(MISSING_PAGE)
    assert MISSING_PAGE == {"Cache-Control": "max-age=60",
                            "Vercel-CDN-Cache-Control": "s-maxage=300, stale-if-error=86400"}
    # An API reply keeps its own header (or none): never the page's.
    data = hosted.get("/api/match-centre")
    assert data.headers["vercel-cdn-cache-control"] != PAGE["Vercel-CDN-Cache-Control"]
    assert lifetime(hosted.get("/api/nope", headers={"accept": "text/html"})) == {
        "Cache-Control": None, "Vercel-CDN-Cache-Control": None}


def test_a_page_that_says_otherwise_or_sets_a_cookie_keeps_its_own_headers():
    app = FastAPI()

    @app.get("/own", response_class=HTMLResponse)
    def own():
        return HTMLResponse("<p>x</p>", headers={"Cache-Control": "no-store"})

    @app.get("/cdn", response_class=HTMLResponse)
    def cdn():
        return HTMLResponse("<p>x</p>", headers={"Vercel-CDN-Cache-Control": "s-maxage=20"})

    @app.get("/cookie", response_class=HTMLResponse)
    def cookie():
        reply = HTMLResponse("<p>x</p>")
        reply.set_cookie("a", "b")
        return reply

    @app.get("/text")
    def text():
        return {"a": 1}

    @app.post("/form", response_class=HTMLResponse)
    def form():
        return "<p>x</p>"

    @app.get("/broken", response_class=HTMLResponse)
    def broken():
        return HTMLResponse("<p>x</p>", status_code=503)

    app.add_middleware(PageCache)
    with TestClient(app) as client:
        assert lifetime(client.get("/own")) == {"Cache-Control": "no-store",
                                                "Vercel-CDN-Cache-Control": None}
        assert lifetime(client.get("/cdn"))["Vercel-CDN-Cache-Control"] == "s-maxage=20"
        assert lifetime(client.get("/cdn"))["Cache-Control"] is None
        for reply in (client.get("/cookie"), client.get("/text"), client.post("/form"),
                      client.get("/broken")):
            assert lifetime(reply) == {"Cache-Control": None,
                                       "Vercel-CDN-Cache-Control": None}, reply.url


# ------------------------------------------------------------------ done once


def test_a_page_file_is_read_once_per_content_and_its_assets_filled_each_time(tmp_path):
    template = tmp_path / "t.html"
    template.write_text("<link href=\"<!--asset:tokens.css-->\">AAAA", encoding="utf-8")
    first = site_nav._template(template)
    assert first == f'<link href="{site_nav.asset_url("tokens.css")}">AAAA'
    stamp = template.stat()
    template.write_text("<link href=\"<!--asset:tokens.css-->\">BBBB", encoding="utf-8")
    os.utime(template, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert site_nav._template(template) == first, "the same size and time: not read again"
    os.utime(template, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 10**9))
    assert site_nav._template(template).endswith("BBBB")
    template.write_text("<!--asset:gone.css-->", encoding="utf-8")
    with pytest.raises(ValueError):
        site_nav._template(template)


def test_the_served_paths_are_worked_out_once_per_set_of_routes():
    app = create_centre("Hosted")
    first = site_nav.served_paths(app)
    assert site_nav.served_paths(app) is first
    assert "/xi" not in first

    @app.get("/xi")
    def xi():
        return "x"

    again = site_nav.served_paths(app)
    assert again is not first and again == first | {"/xi"}
    assert site_nav.served_paths(SimpleNamespace(routes=())) == frozenset()


# ------------------------------------------------------------------ an entity page's head


def _request(app) -> SimpleNamespace:
    return SimpleNamespace(app=app, url="http://testserver/competitions/la-liga?tab=table",
                           base_url="http://testserver/")


def test_an_entity_page_names_its_view_credits_its_sources_and_writes_its_canonical():
    assert all(spec.pattern is None for spec in site_nav.PAGES.values())
    app = create_centre("Hosted")
    html = site_nav.page(_request(app), "table", name="La Liga",
                         sources=["football_data_org", "football_data_org"],
                         canonical="/competitions/la-liga")
    assert "<title>La Liga · Table · Galáctico</title>" in html
    assert '<meta property="og:title" content="La Liga · Table · Galáctico">' in html
    assert ('<link rel="canonical" href="http://testserver/competitions/la-liga">' in html)
    assert '<meta property="og:url" content="http://testserver/competitions/la-liga">' in html
    footer = html[html.index('<footer class="site-footer"'):]
    assert footer.count("football-data.org terms") == 1
    assert "OpenFootball" not in footer and "OpenLigaDB" not in footer
    # The page's own credits stand where the route names none; an empty list credits none.
    plain = site_nav.page(_request(app), "table")
    assert "<title>Table · Galáctico</title>" in plain and 'rel="canonical"' not in plain
    assert "OpenFootball" in plain[plain.index('<footer class="site-footer"'):]
    bare = site_nav.page(_request(app), "table", sources=())
    assert "<p>Data:" not in bare
    with pytest.raises(ValueError, match="unknown sources"):
        site_nav.page(_request(app), "table", sources=["statsbomb"])
    full = site_nav.page(_request(app), "table", canonical="https://example.test/x")
    assert '<link rel="canonical" href="https://example.test/x">' in full


def test_the_shared_head_without_versions_is_the_plain_one():
    # head_markup's default stays the plain addresses (the pinned shell tests read them);
    # every served page asks for the versioned ones.
    head = site_nav.head_markup(site_nav.PAGES["about"])
    assert '<link rel="stylesheet" href="/static/tokens.css">' in head and "?v=" not in head
    versioned = site_nav.head_markup(site_nav.PAGES["about"], versioned=True)
    assert versioned.count("?v=") == len(site_nav.SHELL_SHEETS) + len(
        site_nav.SHELL_SCRIPTS) + 1
    assert assets.STALE_IF_ERROR == "stale-if-error=86400"
