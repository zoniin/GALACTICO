"""Wikidata: height and place of birth, joined by the QID of the player's article only.

Each test targets one way the Wikidata facts could mislead or leak:

- a height in metres served as centimetres, a rounding other than half up, another unit
  converted by a guess, or a "no value" served as a number (R8);
- a place of birth chosen by anything but the declared rank rule, a deprecated statement
  used, or a missing English label filled in;
- a join by label or by club membership instead of by the article's QID, an image (P18) read,
  a request without the agent or ``maxlag``, a batch over fifty, or a second request for what
  is kept a week.

Every reply here is built by ``season_wiki`` (invented players and places, R7).
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
import season_wiki as wiki

from galactico.domain.labels import scan_labels
from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.match_centre.feed import FeedError
from galactico.match_centre.season import wikidata as wd
from galactico.match_centre.season.model import to_json
from galactico.match_centre.studio import AGENT


@pytest.mark.parametrize("amount, unit, cm", [
    ("+183", wiki.CENTIMETRE, 183), ("+1.91", wiki.METRE, 191), ("+1.835", wiki.METRE, 184),
    ("+1.825", wiki.METRE, 183), ("+182.5", wiki.CENTIMETRE, 183),
    ("+6", "http://www.wikidata.org/entity/Q3710", None),
    ("not a number", wiki.CENTIMETRE, None),
])
def test_height_is_whole_centimetres_rounded_half_up(amount, unit, cm):
    assert wd.height_cm([wiki.height(amount, unit)]) == cm


def test_the_declared_statement_preferred_else_the_first_normal_never_deprecated():
    assert wd.height_cm([wiki.height("+180"), wiki.height("+185", rank="preferred")]) == 185
    assert wd.height_cm([wiki.height("+170", rank="deprecated"), wiki.height("+181"),
                         wiki.height("+182")]) == 181
    assert wd.height_cm([wiki.height("+170", rank="deprecated")]) is None
    assert wd.height_cm([]) is None
    novalue = {"mainsnak": {"snaktype": "novalue", "property": "P2048"}, "rank": "normal"}
    assert wd.height_cm([novalue]) is None
    assert wd.place([wiki.birthplace("Q900001"), wiki.birthplace("Q900002",
                                                                rank="preferred")]) == "Q900002"
    assert wd.place([wiki.birthplace("Q900001"), wiki.birthplace("Q900002")]) == "Q900001"
    assert wd.place([{"mainsnak": {"snaktype": "somevalue"}, "rank": "normal"}]) is None


def test_qids_follow_normalisations_and_leave_out_missing_articles():
    reply = wiki.pageprops_reply({"Kai Delantero": "Q900101", "Test Lateral": None,
                                  "Missing Player": "Q1"},
                                 normalized=[("Kai_Delantero", "Kai Delantero")])
    # Keyed by the title asked for, read as MediaWiki reads titles.
    assert wd.qids(reply) == {"Kai Delantero": "Q900101", "Test Lateral": None}
    with pytest.raises(FeedError):
        wd.qids({"error": {"code": "maxlag"}})


class Upstream:
    def __init__(self, items, claims, labels, *, status=200):
        self.items, self.claims, self.labels, self.status = items, claims, labels, status
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status != 200:
            return httpx.Response(self.status, text=wiki.RATE_LIMITED)
        params = request.url.params
        if request.url.host == "en.wikipedia.org":
            titles = params["titles"].split("|")
            return httpx.Response(200, json=wiki.pageprops_reply(
                {t: self.items.get(t) for t in titles}))
        ids = params["ids"].split("|")
        if params["props"] == "claims":
            return httpx.Response(200, json=wiki.entities_claims(
                {q: self.claims.get(q) for q in ids}))
        return httpx.Response(200, json=wiki.entities_labels(
            {q: self.labels.get(q) for q in ids}))


ITEMS = {"Kai Delantero": "Q900101", "Test Lateral": "Q900102", "Ferrito": None,
         "Nico Enlace": "Q900104"}
CLAIMS = {
    "Q900101": {"P2048": [wiki.height("+1.88", wiki.METRE)],
                "P19": [wiki.birthplace("Q900201")],
                "P18": [{"mainsnak": {"snaktype": "value", "property": "P18",
                                      "datavalue": {"value": "Invented.jpg"}}}]},
    "Q900102": {"P2048": [wiki.height("+176")], "P19": [wiki.birthplace("Q900202")]},
    "Q900104": None,
}
LABELS = {"Q900201": "Villa Inventada", "Q900202": None}


def test_people_join_by_qid_alone_and_never_read_an_image():
    upstream = Upstream(ITEMS, CLAIMS, LABELS)
    found = asyncio.run(wd.Wikidata(transport=httpx.MockTransport(upstream)).people(
        ["Kai_Delantero", "Test Lateral", "Ferrito", "Nico Enlace"]))
    assert {t: (p.qid, p.height_cm, p.birthplace) for t, p in found.items()} == {
        "Kai Delantero": ("Q900101", 188, "Villa Inventada"),
        "Test Lateral": ("Q900102", 176, None),           # the place has no English label
        "Ferrito": (None, None, None),                    # no item: missing, not filled
        "Nico Enlace": ("Q900104", None, None)}           # a missing item
    assert found["Kai Delantero"].sources[0].url == "https://www.wikidata.org/wiki/Q900101"
    assert found["Ferrito"].sources == ()
    actions = [r.url.params["action"] for r in upstream.requests]
    assert actions == ["query", "wbgetentities", "wbgetentities"]
    assert [r.url.params.get("props") for r in upstream.requests] == [
        None, "claims", "labels"]
    assert upstream.requests[1].url.params["ids"] == "Q900101|Q900102|Q900104"
    assert upstream.requests[2].url.params["ids"] == "Q900201|Q900202"
    for request in upstream.requests:
        assert request.headers["user-agent"] == AGENT["User-Agent"]
        assert request.url.params["maxlag"] == "5"
        assert "search" not in str(request.url) and "P18" not in str(request.url)
        assert "Q8682" not in str(request.url)  # never "members of the club"
    assert "P18" not in str(wd.claims(wiki.entities_claims(CLAIMS)))
    data = to_json(list(found.values()))
    assert banned_key_paths(data, parts=BANNED_KEY_PARTS) == []
    assert scan_labels(data, keys=False) == []


def test_people_are_kept_a_week_and_asked_for_fifty_at_a_time():
    items = {f"Player {n}": f"Q{900300 + n}" for n in range(60)}
    claims = {q: {"P2048": [wiki.height("+180")]} for q in items.values()}
    upstream = Upstream(items, claims, {})
    service = wd.Wikidata(transport=httpx.MockTransport(upstream))
    found = asyncio.run(service.people(list(items)))
    assert len(found) == 60 and {p.height_cm for p in found.values()} == {180}
    pages = [r for r in upstream.requests if r.url.host == "en.wikipedia.org"]
    assert [len(r.url.params["titles"].split("|")) for r in pages] == [50, 10]
    assert all(len(r.url.params["ids"].split("|")) <= 50 for r in upstream.requests
               if r.url.host == "www.wikidata.org")
    count = len(upstream.requests)
    asyncio.run(service.people(list(items)))
    assert len(upstream.requests) == count


def test_an_unreadable_batch_leaves_its_facts_missing(monkeypatch):
    asked = []
    monkeypatch.setattr(wd, "assert_may_host", lambda provider: asked.append(provider))
    upstream = Upstream(ITEMS, CLAIMS, LABELS, status=429)
    assert asyncio.run(wd.Wikidata(transport=httpx.MockTransport(upstream)).people(
        ["Kai Delantero"])) == {}
    assert asked == ["wikidata"]
    def maxlag(request):
        return httpx.Response(200, json=wiki.maxlag_reply())

    assert asyncio.run(wd.Wikidata(transport=httpx.MockTransport(maxlag)).people(
        ["Kai Delantero"])) == {}
