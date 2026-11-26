"""Every HTML page carries the one site shell, and every sheet sits in its cascade layer.

A page file holds three placeholders and no hand-written header or navigation; the app that
serves it fills them (``galactico.site_nav``). So a destination cannot be added to one page
and forgotten on another, and a page cannot link to a route its app does not serve.

The cascade: tokens, base, legacy, components, page. A sheet written before the design system
is wrapped in ``@layer legacy``, so it keeps its page's look and never restyles the shell.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from galactico import site_nav

WEB = Path(__file__).resolve().parents[1] / "web"
LAYER_ORDER = "@layer tokens, base, legacy, components, page;"
LEGACY_SHEETS = ("labs.css", "labs-shared.css", "planning.css", "xi-extensions.css",
                 "match-centre.css", "studio-shell.css", "studio.css",
                 "goal-scout.css")
NEW_SHEETS = ("tokens.css", "base.css", "components.css")


def test_every_html_file_is_a_page_of_the_shell():
    # The invented-figures demo is gone (R8), and no page is served outside the shell.
    assert {path.name for path in WEB.glob("*.html")} == {
        spec.file for spec in site_nav.PAGES.values()}
    assert not (WEB / "matchroom-demo.html").exists()


@pytest.mark.parametrize("key", sorted(site_nav.PAGES))
def test_a_page_file_holds_the_placeholders_and_no_chrome_of_its_own(key):
    html = (WEB / site_nav.PAGES[key].file).read_text(encoding="utf-8")
    for placeholder in site_nav.PLACEHOLDERS:
        assert html.count(placeholder) == 1, placeholder
    # The head placeholder comes before any sheet, so the layer order is declared first.
    head = html.index(site_nav.PLACEHOLDERS[0])
    for sheet in re.finditer(r'<link rel="stylesheet"|<style', html):
        assert head < sheet.start()
    # The header placeholder opens the body; the footer follows the one main.
    assert html.index(site_nav.PLACEHOLDERS[1]) < html.index('<main id="main"')
    assert html.count("<main") == 1 and html.count('<main id="main"') == 1
    assert html.index("</main>") < html.index(site_nav.PLACEHOLDERS[2])
    # No copy of the old chrome: the lab nav, the workspace nav, the masthead, the wordmark.
    for gone in ('aria-label="Laboratories"', 'aria-label="Workspaces"', 'class="mast"',
                 'class="brand"', 'name="theme-color"', "match-centre/demo", "Scouting demo"):
        assert gone not in html, gone
    # One title pattern, which the shell writes (site_nav.title): the page's head holds none.
    assert "<title>" not in html[:html.index("</head>")]


@pytest.mark.parametrize("name", LEGACY_SHEETS)
def test_an_old_sheet_sits_in_the_legacy_layer(name):
    sheet = re.sub(r"/\*.*?\*/", "", (WEB / name).read_text(encoding="utf-8"), flags=re.S)
    assert sheet.strip().startswith("@layer legacy{") and sheet.strip().endswith("}"), name
    # No rule outside the layer: one opening block, closed at the very end.
    depth, closed_at = 0, None
    for position, char in enumerate(sheet.strip()):
        depth += {"{": 1, "}": -1}.get(char, 0)
        if depth == 0 and char == "}":
            closed_at = position
            break
    assert closed_at == len(sheet.strip()) - 1, name


@pytest.mark.parametrize("key", sorted(site_nav.PAGES))
def test_an_inline_style_of_a_page_sits_in_a_layer(key):
    html = (WEB / site_nav.PAGES[key].file).read_text(encoding="utf-8")
    for block in re.findall(r"<style>(.*?)</style>", html, flags=re.S):
        body = re.sub(r"/\*.*?\*/", "", block, flags=re.S).strip()
        assert re.match(r"@layer (legacy|page)\s*\{", body), key


def test_each_new_sheet_declares_the_layer_order_first():
    for name in NEW_SHEETS:
        sheet = re.sub(r"/\*.*?\*/", "", (WEB / name).read_text(encoding="utf-8"), flags=re.S)
        assert sheet.strip().startswith(LAYER_ORDER), name


def test_the_old_sheets_draw_no_header_and_no_navigation():
    # The shell's header is a <header>; an old element rule for header or nav would reach it.
    for name in LEGACY_SHEETS:
        sheet = re.sub(r"/\*.*?\*/", "", (WEB / name).read_text(encoding="utf-8"), flags=re.S)
        for selector in re.findall(r"([^{};]+)\{", sheet):
            for part in selector.split(","):
                part = part.strip()
                assert not re.match(r"(header|\.mast|\.brand|\.lab-tag)\b", part), (name, part)
                assert not re.match(r"(header\s+)?nav(\[data-nav)", part), (name, part)


def test_the_kit_and_the_shell_scripts_declare_no_global():
    theme = (WEB / "theme.js").read_text(encoding="utf-8")
    assert theme.lstrip().startswith("/*") and "(function () {" in theme
    assert "localStorage" in theme and "galactico-theme" in theme
