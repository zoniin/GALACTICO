"""A player's infobox: every listed position in order, his date of birth, his caps (gated).

Each test targets one way the infobox facts could mislead:

- positions out of the order listed, or a first position other than the one the Lineup
  already reads (``studio.first_position``);
- a blank or unreadable caps field served as 0 (R8), a loan not marked, a stamp misread;
- a batched reply's normalised or redirected title not followed back to the one asked for;
- a request without the agent or ``maxlag``, a rate-limited batch that is not retried article
  by article, or a second request for what is kept a day.

Every article here is built by ``season_wiki.infobox`` (invented players, R7).
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
import season_wiki as wiki

from galactico.domain.labels import scan_labels
from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.match_centre.season import infobox as ib
from galactico.match_centre.season.model import to_json
from galactico.match_centre.studio import AGENT, first_position

BACK = ("[[Defender (association football)#Full-back|Left-back]], "
        "[[Defender (association football)#Centre-back|centre-back]]")


def article(position=BACK, **kwargs) -> str:
    return wiki.infobox(name="Test Lateral", position=position, born=(1999, 1, 21), **kwargs)


@pytest.mark.parametrize("position, listed", [
    (BACK, ("Left-back", "Centre-back")),
    ("[[Winger (association football)|Winger]] / [[Forward (association football)|forward]]",
     ("Winger", "Forward")),
    ("[[Midfielder#Defensive|Defensive midfielder]]<ref>{{cite web|title=x}}</ref> or "
     "[[Midfielder#Central|central midfielder]]", ("Defensive midfielder", "Central midfielder")),
    ("{{hlist|[[Centre-back]]|[[Right-back]]}}", ("Centre-back", "Right-back")),
    ("{{plainlist|\n* [[Striker]]\n* [[Winger]]\n}}", ("Striker", "Winger")),
    ("[[Goalkeeper (association football)|Goalkeeper]]", ("Goalkeeper",)),
])
def test_every_listed_position_in_order_the_first_as_the_lineup_reads_it(position, listed):
    text = article(position)
    assert ib.positions(text) == listed
    first = first_position(text)
    if "{{hlist" not in position and "{{plainlist" not in position:
        assert ib.positions(text)[0] == first
    else:
        # The Lineup's reader takes one line and drops templates: a list template gives it
        # nothing, or over several lines the template's opening, which is no position. This
        # reads the list.
        assert first in (None, "{{plainlist|")


def test_no_position_field_is_no_position():
    assert ib.positions(wiki.infobox(name="X", position=None, born=None)) == ()
    assert ib.positions("no infobox at all") == ()


def test_birth_date_caps_and_stamps_are_read_as_listed_and_missing_stays_missing():
    text = article(clubs=[("2016–2018", "[[Ribera UD|Ribera]]", 41, 2),
                          ("2018–", "[[Real Madrid CF|Real Madrid]]", 120, "?"),
                          ("2019–2020", "→ [[Norte CF|Norte]] (loan)", None, None)],
                   national=[("2019–", "[[Testland national football team|Testland]]", 33, 1)],
                   club_update="24 November 2026", nationalteam_update="18 November 2026")
    box = ib.parse_infobox("Test_Lateral", text)
    assert box.title == "Test Lateral" and box.born == "1999-01-21"
    assert box.positions == ("Left-back", "Centre-back")
    assert [(s.years, s.team, s.caps, s.goals, s.loan) for s in box.clubs] == [
        ("2016–2018", "Ribera", 41, 2, False),
        ("2018–", "Real Madrid", 120, None, False),    # "?" is not a count
        ("2019–2020", "Norte (loan)", None, None, True)]  # blank caps stay blank
    assert [(s.team, s.caps, s.goals) for s in box.national] == [("Testland", 33, 1)]
    assert (box.club_update, box.nationalteam_update) == ("2026-11-24", "2026-11-18")
    bare = ib.parse_infobox("X", wiki.infobox(name="X", position=None, born=None))
    assert (bare.born, bare.clubs, bare.national, bare.club_update) == (None, (), (), None)
    assert ib.parse_infobox("X", "no infobox") is None
    assert ib.birth_date("{{Infobox football biography\n| birth_date = 14 March 1996\n}}") == (
        "1996-03-14")
    data = to_json(box)
    assert banned_key_paths(data, parts=BANNED_KEY_PARTS) == []
    assert scan_labels(data, keys=False) == []


class Upstream:
    def __init__(self, texts: dict[str, str | None], *, status: int = 200, **reply):
        self.texts, self.status, self.reply = texts, status, reply
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/w/index.php":
            text = self.texts.get(request.url.params["title"])
            return httpx.Response(200, text=text) if text else httpx.Response(404)
        if self.status != 200:
            return httpx.Response(self.status, text=wiki.RATE_LIMITED)
        titles = request.url.params["titles"].split("|")
        normalized = dict(self.reply.get("normalized", ()))
        redirects = dict(self.reply.get("redirects", ()))
        pages = {}
        for title in titles:
            shown = redirects.get(normalized.get(title, title), normalized.get(title, title))
            pages[shown] = self.texts.get(title)
        return httpx.Response(200, json=wiki.articles_reply(
            pages, normalized=[(a, b) for a, b in normalized.items() if a in titles],
            redirects=[(a, b) for a, b in redirects.items()]))


def test_one_batched_request_followed_back_to_the_titles_asked_and_kept_a_day():
    texts = {"Test Lateral": article(), "Kai Delantero": article("[[Striker]]"),
             "Missing Player": None}
    upstream = Upstream(texts, redirects=[("Kai Delantero", "Kai Delantero (footballer)")])
    boxes = ib.Infoboxes(transport=httpx.MockTransport(upstream))
    found = asyncio.run(boxes.read(["Test_Lateral", "Kai Delantero", "Missing Player"]))
    assert set(found) == {"Test Lateral", "Kai Delantero"}
    assert found["Kai Delantero"].positions == ("Striker",)
    (request,) = upstream.requests
    assert dict(request.url.params) == {
        "action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
        "format": "json", "formatversion": "2", "redirects": "1",
        "titles": "Kai Delantero|Missing Player|Test Lateral", "maxlag": "5"}
    assert request.headers["user-agent"] == AGENT["User-Agent"]
    asyncio.run(boxes.read(["Kai Delantero", "Test Lateral", "Missing Player"]))
    assert len(upstream.requests) == 1


def test_a_rate_limited_batch_is_read_article_by_article():
    texts = {"Test Lateral": article(), "Kai Delantero": article("[[Striker]]")}
    upstream = Upstream(texts, status=429)
    found = asyncio.run(ib.Infoboxes(transport=httpx.MockTransport(upstream)).read(
        ["Test Lateral", "Kai Delantero"]))
    assert set(found) == {"Test Lateral", "Kai Delantero"}
    raw = [r for r in upstream.requests if r.url.path == "/w/index.php"]
    assert sorted(r.url.params["title"] for r in raw) == ["Kai Delantero", "Test Lateral"]
    assert all(r.url.params["action"] == "raw" for r in raw)
    assert all(r.headers["user-agent"] == AGENT["User-Agent"] for r in upstream.requests)


def test_no_readable_article_is_an_empty_answer_and_batches_hold_fifty():
    upstream = Upstream({}, status=503)
    assert asyncio.run(ib.Infoboxes(transport=httpx.MockTransport(upstream)).read(["A"])) == {}
    texts = {f"Player {n}": article() for n in range(60)}
    upstream = Upstream(texts)
    found = asyncio.run(ib.Infoboxes(transport=httpx.MockTransport(upstream)).read(list(texts)))
    assert len(found) == 60
    assert [len(r.url.params["titles"].split("|")) for r in upstream.requests] == [50, 10]


def test_the_hosted_guard_runs_before_any_request(monkeypatch):
    asked = []
    monkeypatch.setattr(ib, "assert_may_host", lambda provider: asked.append(provider))
    upstream = Upstream({"Test Lateral": article()})
    asyncio.run(ib.Infoboxes(transport=httpx.MockTransport(upstream)).read(["Test Lateral"]))
    assert asked == ["wikipedia"]
    assert "crests.football-data.org" not in json.dumps([r.url.params.get("titles")
                                                         for r in upstream.requests])
