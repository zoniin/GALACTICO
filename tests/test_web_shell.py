"""Every lab page carries the one navigation block the server defines.

Five pages ship. Four draw ``shell.nav_markup`` byte for byte, so a destination cannot be
added to one page and forgotten on another; Player Lab keeps its own header and must link
to the other four.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from galactico.api import shell

WEB = Path(__file__).resolve().parents[1] / "web"
NAV = re.compile(r'<nav aria-label="Laboratories".*?</nav>', re.S)
PAGES = {"match": "match.html", "xi": "xi.html", "squad": "squad.html", "transfer": "transfer.html"}


def test_every_destination_but_player_lab_is_a_page_checked_here():
    assert {d.dest for d in shell.DESTINATIONS} - {"player"} == set(PAGES)


@pytest.mark.parametrize("dest", sorted(PAGES))
def test_a_lab_page_carries_the_shared_nav_with_its_own_page_marked(dest):
    html = (WEB / PAGES[dest]).read_text(encoding="utf-8")
    assert NAV.findall(html) == [shell.nav_markup(dest)]
    # The sheet that lays five links out; without it the 390 px header overflows.
    assert '<link rel="stylesheet" href="/static/labs-shared.css">' in html


def test_player_lab_links_to_every_other_destination():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for destination in shell.DESTINATIONS:
        if destination.dest != "player":
            assert f'<a href="{destination.href}"' in html, destination.dest
