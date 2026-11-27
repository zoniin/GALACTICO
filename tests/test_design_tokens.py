"""The design system's sheets: colour lives in tokens.css, and every pair a page draws is legible.

Corpus-free. tokens.css holds every colour literal; every other sheet of the site, the sheets
written before the system included, and every page's own <style> read roles. Every role has a
light and a dark value, and each text, control border and focus pair clears WCAG 2 contrast on
the surfaces it appears on (4.5:1 for text, 3:1 for a control's border, the focus ring, the pitch
lines and the chart marks). Gold is the selected subject's and nothing else's, focus is never
gold, and no text is set under 12 px.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
TOKENS = (WEB / "tokens.css").read_text(encoding="utf-8")
SHEETS = {name: re.sub(r"/\*.*?\*/", "", (WEB / name).read_text(encoding="utf-8"), flags=re.S)
          for name in ("base.css", "components.css")}


def _files(web: Path, pattern: str) -> list[Path]:
    """Every file under ``web`` matching ``pattern``, subfolders included (``web/season/``, the
    season pages' folder): a guard that globbed only the top would let a page escape it.
    Re-pinned in wave D4 (PLAN 4, D4-A): the globs were ``web/*``."""
    return sorted(path for path in web.rglob(pattern) if path.is_file())


def _name(web: Path, path: Path) -> str:
    # Keyed by the path under web/, so web/season/matches.css never overwrites web/matches.css.
    return path.relative_to(web).as_posix()


def every_sheet(web: Path) -> dict[str, str]:
    """Every sheet but tokens.css, and every page's own <style>, comments removed."""
    return {
        **{_name(web, path): re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"),
                                    flags=re.S)
           for path in _files(web, "*.css") if path != web / "tokens.css"},
        **{_name(web, path): re.sub(r"/\*.*?\*/", "", " ".join(re.findall(
            r"<style>(.*?)</style>", path.read_text(encoding="utf-8"), flags=re.S)), flags=re.S)
           for path in _files(web, "*.html")},
    }


# Every other sheet and every page's own <style>: the pages written before the system read the
# same roles (labs.css re-points the labs' names at them), so a theme is one block of tokens.css.
EVERY_SHEET = every_sheet(WEB)
COLOUR_WORDS = {"red", "green", "gold", "orange", "lime", "white", "black", "yellow", "blue",
                "purple", "violet", "navy"}
GOLD = "#c9a227"  # rgb(201, 162, 39): the selected subject, pinned by the e2e gold checks.


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_colour: str) -> float:
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


PRIMITIVES = dict(re.findall(r"(--c-[\w-]+): (#[0-9a-f]{6});", TOKENS))


def _block(start: str) -> dict[str, str]:
    body = TOKENS[TOKENS.index(start) + len(start):]
    body = body[:body.index("}")]
    roles = {}
    for name, value in re.findall(r"(--[\w-]+): ([^;]+);", body):
        ref = re.fullmatch(r"var\((--c-[\w-]+)\)", value.strip())
        roles[name] = PRIMITIVES[ref.group(1)] if ref else value.strip()
    return roles


LIGHT = _block(":root,\n  [data-shell] {\n    color-scheme: light;")
DARK = _block(":root:not([data-theme=\"light\"]) [data-shell] {\n      color-scheme: dark;")
DARK_CHOSEN = _block(":root[data-theme=\"dark\"] [data-shell] {\n    color-scheme: dark;")
FIXED = _block(":root,\n  [data-shell] {\n    /* Pitch")
THEMES = {"light": {**LIGHT, **FIXED}, "dark": {**DARK, **FIXED}}


def test_every_colour_literal_is_in_tokens_and_every_role_has_both_themes():
    # Re-pinned under ADR-0034: the current-season pages' sheets are matches.css, goals.css
    # and lineup.css (the old match-centre.css and studio.css are deleted).
    assert {"labs.css", "matches.css", "goals.css", "lineup.css", "index.html",
            "squad.html"} <= set(EVERY_SHEET)
    for name, sheet in EVERY_SHEET.items():
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|oklch\(", sheet), name
        words = set(re.findall(r":\s*([a-z]+)\b", sheet))
        assert not words & COLOUR_WORDS, name
    # A role a sheet reads is one tokens.css defines, or one an old sheet re-points.
    defined = set(re.findall(r"(--[\w-]+):", TOKENS))
    for sheet in EVERY_SHEET.values():
        defined |= set(re.findall(r"(--[\w-]+):", sheet))
    for name, sheet in EVERY_SHEET.items():
        assert set(re.findall(r"var\((--[\w-]+)", sheet)) <= defined, name
    assert set(LIGHT) == set(DARK) and len(LIGHT) > 30
    assert DARK == DARK_CHOSEN  # the system's dark and the reader's dark are one theme
    roles = {"--bg", "--surface-1", "--surface-2", "--surface-3", "--text", "--text-muted",
             "--text-subtle", "--border", "--border-control", "--accent", "--on-accent",
             "--focus-inner", "--focus-outer", "--selected", "--live", "--danger", "--warning"}
    assert roles <= set(LIGHT)
    assert {"--pitch-grass", "--pitch-line", "--chart-1", "--chart-8", "--seq-1", "--seq-7",
            "--diverging-mid"} <= set(FIXED)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_controls_and_focus_clear_contrast_on_every_surface(theme):
    t = THEMES[theme]
    surfaces = ("--bg", "--surface-1", "--surface-2", "--surface-3")
    for surface in surfaces:
        for ink in ("--text", "--text-muted", "--text-subtle", "--link", "--accent",
                    "--accent-strong", "--live", "--danger", "--warning"):
            assert contrast(t[ink], t[surface]) >= 4.5, (theme, ink, surface)
        assert contrast(t["--border-control"], t[surface]) >= 3, (theme, surface)
    for soft, ink in (("--live-soft", "--live"), ("--danger-soft", "--danger"),
                      ("--warning-soft", "--warning"), ("--accent-soft", "--text"),
                      ("--info-soft", "--text")):
        assert contrast(t[ink], t[soft]) >= 4.5, (theme, ink, soft)
    assert contrast(t["--on-accent"], t["--accent"]) >= 4.5
    for ink in ("--header-text", "--header-muted"):
        assert contrast(t[ink], t["--header-bg"]) >= 4.5, (theme, ink)
    assert contrast(t["--brand-mark"], t["--header-bg"]) >= 3
    if theme == "dark":
        # The dark header is a surface of its own, not the page's colour, and its edge is a
        # control-strength line: the two stay apart without the line being the only cue.
        assert t["--header-bg"] != t["--bg"]
        assert contrast(t["--header-line"], t["--bg"]) >= 3
    # The two-tone ring: one of its two colours clears 3:1 on every surface it can sit on.
    for surface in (*(t[s] for s in surfaces), t["--header-bg"], t["--accent"],
                    t["--pitch-grass"], t["--chart-bg"], t["--selected"]):
        assert max(contrast(t["--focus-inner"], surface),
                   contrast(t["--focus-outer"], surface)) >= 3, (theme, surface)


def test_gold_is_the_selected_subject_a_fill_with_an_edge_and_never_focus():
    for theme in THEMES.values():
        assert theme["--selected"] == GOLD
        assert GOLD not in (theme["--focus-inner"], theme["--focus-outer"], theme["--accent"])
        assert contrast(theme["--on-selected"], GOLD) >= 4.5
        # On a light surface gold alone is under 3:1: it is drawn with its edge.
        assert contrast(theme["--selected-edge"], theme["--surface-1"]) >= 3
    assert contrast(GOLD, THEMES["light"]["--surface-1"]) < 3
    for name, sheet in SHEETS.items():
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", sheet):
            if "var(--selected)" in body:
                assert "selected" in selectors, (name, selectors.strip())


def test_pitch_and_chart_surfaces_are_dark_and_their_marks_are_legible():
    t = FIXED
    assert _luminance(t["--pitch-grass"]) < 0.1 and _luminance(t["--chart-bg"]) < 0.05
    assert contrast(t["--pitch-line"], t["--pitch-grass"]) >= 3
    assert contrast(t["--pitch-text"], t["--pitch-grass"]) >= 4.5
    assert contrast(t["--chart-text"], t["--chart-bg"]) >= 4.5
    assert contrast(t["--chart-text-muted"], t["--chart-bg"]) >= 4.5
    assert contrast(t["--chart-axis"], t["--chart-bg"]) >= 3
    for slot in range(1, 9):
        assert contrast(t[f"--chart-{slot}"], t["--chart-bg"]) >= 3, slot
    # Two teams in one drawing: each legible on the grass and on the chart, and neither gold.
    for team in ("--chart-team-1", "--chart-team-2"):
        assert contrast(t[team], t["--pitch-grass"]) >= 3, team
        assert contrast(t[team], t["--chart-bg"]) >= 3, team
        assert t[team] != GOLD
    # The studio's board: its text and its lime mark on the board's own surfaces.
    for surface in ("--pitch-card", "--pitch-bar", "--pitch-field-1", "--pitch-field-2"):
        assert contrast(t["--pitch-text"], t[surface]) >= 4.5, surface
        assert contrast(t["--pitch-text-muted"], t[surface]) >= 4.5, surface
    assert contrast(t["--on-pitch-mark"], t["--pitch-mark"]) >= 4.5
    for surface in ("--hero-from", "--hero-mid"):
        assert contrast(t["--on-hero"], t[surface]) >= 4.5, surface
    # A control on the board (the formation select, the swap button) is bounded by its border:
    # 3:1 on the bar and the card it sits on, and on its own fill.
    for surface in ("--pitch-bar", "--pitch-card", "--pitch-control"):
        assert contrast(t["--pitch-control-border"], t[surface]) >= 3, surface
    # The focus ring on the board, the field and the player card, in both themes.
    for theme in THEMES.values():
        for surface in ("--pitch-field-1", "--pitch-field-2", "--pitch-card", "--pitch-bar",
                        "--hero-mid", "--hero-from"):
            assert max(contrast(theme["--focus-inner"], t[surface]),
                       contrast(theme["--focus-outer"], t[surface])) >= 3, surface
    ramp = [_luminance(t[f"--seq-{step}"]) for step in range(1, 8)]
    assert ramp == sorted(ramp)  # one hue, dark (near zero) to light


def test_no_text_under_12px():
    sizes = dict(re.findall(r"(--text-(?:xs|sm|md|lg|xl|2xl|3xl)): ([^;]+);", TOKENS))
    # The smallest step has a floor in px: an older page sets its root to 15 px, where 0.75rem
    # alone would be 11.25 px.
    assert sizes["--text-xs"] == "max(0.75rem, 12px)"
    for name, value in sizes.items():
        floor = re.search(r"(\d+)px", value)
        assert floor and int(floor.group(1)) >= 12, name
    for name, sheet in EVERY_SHEET.items():
        for value in re.findall(r"font(?:-size)?:\s*([^;}]+)[;}]", sheet):
            for px in re.findall(r"(?<![\w.-])(\d+(?:\.\d+)?)px", value.split("/")[0]):
                assert float(px) >= 12, (name, value)
            for rem in re.findall(r"(?<![\w.-])(\d*\.?\d+)rem", value.split("/")[0]):
                assert float(rem) >= 0.75, (name, value)


def test_components_use_their_own_names_and_honour_reduced_motion_and_forced_colours():
    # Old pages already use .badge, .card, .tabs, .field and .eyebrow for other things, and
    # this layer sits above theirs: a component never takes one of those names.
    own = re.compile(r"(\.(site|ui|page)-[\w-]+|\.skip-link|\.wordmark[\w-]*|\.season-chip|"
                     r"\.theme-toggle[\w-]*|\[data-shell\])")
    sheet = SHEETS["components.css"]
    body = re.sub(r"@keyframes[^{]+\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", sheet)
    for selectors in re.findall(r"([^{};]+)\{", body):
        for selector in selectors.split(","):
            selector = selector.strip()
            if not selector or selector.startswith("@"):
                continue
            assert own.match(selector), selector
    assert "prefers-reduced-motion: reduce" in SHEETS["base.css"]
    assert "forced-colors: active" in SHEETS["base.css"]
    assert "forced-colors: active" in sheet


# ------------------------------------------------------------------ scripts and page markup

# Every script of the site: the files, and each page's inline <script>. A drawing a script
# writes (inline SVG, a canvas) is held to the same rules as a sheet.
def every_script(web: Path) -> dict[str, str]:
    """Every script file under ``web``, and each page's inline <script>."""
    return {
        **{_name(web, path): path.read_text(encoding="utf-8") for path in _files(web, "*.js")},
        **{f"{_name(web, path)} <script>": " ".join(re.findall(
            r"<script>(.*?)</script>", path.read_text(encoding="utf-8"), flags=re.S))
           for path in _files(web, "*.html")},
    }


SCRIPTS = every_script(WEB)
# A pitch or a chart is dark in both themes: gold on it clears 3:1 and needs no edge.
DARK_SURFACE = re.compile(r'class="pitch|class=\\"pitch|\.pitch\b|\.depth\b|\.flow\b')


def test_no_script_draws_a_colour_literal_or_type_under_12px():
    assert {"site.js", "studio-map.js", "index.html <script>", "match.html <script>"} <= set(
        SCRIPTS)
    for name, script in SCRIPTS.items():
        code = re.sub(r"/\*.*?\*/|(?<![:'\"])//[^\n]*", "", script, flags=re.S)
        # Colours come from tokens.css, read at draw time (getComputedStyle) or as var(--role).
        assert not re.search(r"['\"`]#[0-9a-fA-F]{3,8}['\"`]|rgba?\(|hsla?\(", code), name
        assert not re.search(r"(?:fillStyle|strokeStyle)\s*=\s*['\"`][a-z]+['\"`]", code), name
        # A canvas sets its type in px: never under 12, never monospace for a label.
        for font in re.findall(r"\.font\s*=\s*([^;\n]+)", code):
            sizes = [float(px) for px in re.findall(r"(\d+(?:\.\d+)?)px", font)]
            assert sizes and min(sizes) >= 12 and "monospace" not in font, (name, font)
        # An inline style a script writes is held to the sheets' floor.
        for value in re.findall(r"font-size:\s*([\d.]+)(px|rem)", code):
            size = float(value[0]) * (16 if value[1] == "rem" else 1)
            assert size >= 12, (name, value)


def test_svg_text_in_a_drawing_is_kept_at_12px_on_screen_by_the_site_script():
    # A label set in a drawing's own units (font-size="2" on a pitch 100 units wide) scales
    # with the drawing; web/site.js, which every page loads, raises it to 12 px on screen.
    # The e2e gate (e2e/match-centre.spec.js) measures it at 390 and 1440 px.
    site = SCRIPTS["site.js"]
    assert "var MIN = 12;" in site and "querySelectorAll('svg text')" in site
    assert "MutationObserver" in site and "'resize'" in site
    drawn = [name for name, script in SCRIPTS.items() if re.search(r"<text\b", script)]
    # Re-pinned under ADR-0034: the XI page labels its pitch in HTML now (sheet-sized, 12 px
    # floor), so its script draws no SVG text.
    assert {"planning.js", "match.html <script>", "squad.html <script>"} <= set(drawn)


def test_gold_in_a_page_or_a_script_is_a_fill_with_its_edge_or_sits_on_a_dark_drawing():
    # Every rule of a page's <style> or an older sheet that paints gold either gives it its
    # dark edge, or is a rule of a pitch or a chart (dark in both themes).
    for name, sheet in EVERY_SHEET.items():
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", sheet):
            for prop, value in re.findall(r"([\w-]+)\s*:\s*([^;]+)", body):
                if prop.startswith("--") or not re.search(r"var\(--(gold|selected)\)", value):
                    continue
                edged = re.search(r"var\(--(selected-edge|text)\)", body)
                assert edged or DARK_SURFACE.search(selectors), (name, selectors.strip())
    # A script that writes gold into markup writes it on a pitch, or with the edge.
    for name, script in SCRIPTS.items():
        for line in script.splitlines():
            if re.search(r"var\(--(gold|selected)\)", line):
                assert "--selected-edge" in line or DARK_SURFACE.search(line), (name, line[:120])
    # Player Lab's marks of the selected player: gold with an edge, never faded.
    page = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'opacity=".75"' not in page and 'stroke="var(--gold)"' not in page


def test_the_archive_missing_state_is_one_sentence_everywhere():
    sentence = "The 2017/18 archive isn't installed on this server."
    assert f'var ARCHIVE_MISSING = "{sentence}";' in SCRIPTS["site.js"]
    assert f'const ARCHIVE_MISSING = "{sentence}";' in SCRIPTS["labs-shared.js"]
    from galactico.api import about
    assert about.UNAVAILABLE.startswith(sentence[:-1])
    # No page tells a reader to run a command.
    for path in _files(WEB, "*.html"):
        text = path.read_text(encoding="utf-8")
        for words in ("Run the Pappalardo", "API_FOOTBALL_KEY", "python -m", ".env"):
            assert words not in text, (path.name, words)
    for name in ("labs-shared.js", "site.js"):
        assert "Run the Pappalardo" not in SCRIPTS[name]


def test_the_guards_read_the_season_pages_folder_under_its_own_names(tmp_path):
    # D4-A: a sheet, a page and a script under web/season/ (the season pages' folder) reach
    # every guard of this file, each under its path, beside a top-level file of the same name.
    (tmp_path / "season").mkdir()
    files = {"tokens.css": ":root{}", "matches.css": "a{color:var(--text)}",
             "season/matches.css": "b{color:#123456}", "kit.js": "var a = 1;",
             "season/kit.js": "const c = '#abcdef';",
             "season/team.html": "<style>@layer page{i{color:red}}</style><script>x()</script>"}
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    sheets = every_sheet(tmp_path)
    assert set(sheets) == {"matches.css", "season/matches.css", "season/team.html"}
    assert "#123456" in sheets["season/matches.css"] and "red" in sheets["season/team.html"]
    scripts = every_script(tmp_path)
    assert set(scripts) == {"kit.js", "season/kit.js", "season/team.html <script>"}
    assert "#abcdef" in scripts["season/kit.js"]
