"""Wikidata (CC0): each Real Madrid player's height and place of birth, by his article's QID.

**The join (DC 2.2).** English Wikipedia article title, as the squad list links it, to its
item through ``pageprops.wikibase_item`` (at most 50 titles a request, normalisations and
redirects followed back to the title asked for), then ``wbgetentities`` for the items' claims
(at most 50 a request), then the English labels of the places named. Never a label search,
never "current members of the club" (those statements are stale), and never ``P18``: images
are Commons files under their own licences, and the site shows none.

**Height (P2048).** Normalised to whole centimetres: an amount in centimetres as it is, in
metres times 100, each rounded half up. Any other unit is not converted, and stays ``None``.

**Place of birth (P19).** The declared rule: the statement of preferred rank, else the first
statement of normal rank (a deprecated one never), and that item's English label. A place with
no English label stays ``None``.

**Missing stays missing (R8).** An article with no item, an item with no statement, a
statement of "no value" or "unknown value": each is ``None``.

Non-claim: Wikidata's values are community-entered; nothing here checks them against another
source. Wikidata is credited as a courtesy (CC0 asks for none).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import httpx

from ...providers import assert_may_host
from ..feed import FeedCache, FeedError
from ..studio import AGENT, API, MAXLAG
from .model import SourceRef
from .wiki_season import title_key

__all__ = ["PROVIDER", "ENTITIES", "CENTIMETRE", "METRE", "HEIGHT", "BIRTHPLACE",
           "WikidataPerson", "qids", "claims", "height_cm", "place", "labels", "Wikidata"]

PROVIDER = "wikidata"
ENTITIES = "https://www.wikidata.org/w/api.php"
CENTIMETRE = "http://www.wikidata.org/entity/Q174728"
METRE = "http://www.wikidata.org/entity/Q11573"
HEIGHT, BIRTHPLACE = "P2048", "P19"
READ = (HEIGHT, BIRTHPLACE)
"""The only properties read."""


@dataclass(frozen=True)
class WikidataPerson:
    title: str
    qid: str | None
    height_cm: int | None
    birthplace: str | None
    sources: tuple[SourceRef, ...]


def qids(payload: object) -> dict[str, str | None]:
    """A ``prop=pageprops&ppprop=wikibase_item`` reply: each title asked for (followed back
    through normalisations and redirects) and its item, ``None`` where it has none. A
    missing article is left out."""
    query = payload.get("query") if isinstance(payload, dict) else None
    if not isinstance(query, dict):
        raise FeedError("Wikipedia’s article items couldn’t be read.")
    back: dict[str, str] = {}
    for step in (query.get("normalized") or []) + (query.get("redirects") or []):
        if isinstance(step, dict) and isinstance(step.get("to"), str):
            back[step["to"]] = back.get(str(step.get("from")), str(step.get("from")))
    found: dict[str, str | None] = {}
    for page in query.get("pages") or []:
        if not isinstance(page, dict) or not isinstance(page.get("title"), str):
            continue
        if page.get("missing") is not None and page.get("missing") is not False:
            continue
        item = (page.get("pageprops") or {}).get("wikibase_item")
        valid = isinstance(item, str) and item[:1] == "Q" and item[1:].isdigit()
        found[title_key(back.get(page["title"], page["title"]))] = item if valid else None
    return found


def claims(payload: object) -> dict[str, dict[str, list[dict]]]:
    """A ``wbgetentities&props=claims`` reply: each item's statements of the properties read
    (``READ``) and of no other. A missing item has none."""
    entities = payload.get("entities") if isinstance(payload, dict) else None
    if not isinstance(entities, dict):
        raise FeedError("Wikidata couldn’t be read.")
    found = {}
    for qid, entity in entities.items():
        if not isinstance(entity, dict) or "missing" in entity:
            found[qid] = {}
            continue
        held = entity.get("claims") or {}
        found[qid] = {prop: [s for s in held.get(prop) or [] if isinstance(s, dict)]
                      for prop in READ}
    return found


def _chosen(statements: list[dict]) -> dict | None:
    """The declared statement: preferred rank, else the first of normal rank."""
    for rank in ("preferred", "normal"):
        for statement in statements:
            if statement.get("rank", "normal") == rank:
                return statement
    return None


def _value(statement: dict | None) -> object:
    snak = (statement or {}).get("mainsnak") or {}
    if snak.get("snaktype") != "value":
        return None
    return (snak.get("datavalue") or {}).get("value")


def height_cm(statements: list[dict]) -> int | None:
    """P2048 in whole centimetres (a metre amount times 100), rounded half up; ``None`` for
    another unit, no value or an amount that is not a number."""
    value = _value(_chosen(statements))
    if not isinstance(value, dict):
        return None
    try:
        amount = Decimal(str(value.get("amount", "")))
    except InvalidOperation:
        return None
    unit = value.get("unit")
    if unit == METRE:
        amount *= 100
    elif unit != CENTIMETRE:
        return None
    whole = int(amount.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return whole if 0 < whole < 300 else None


def place(statements: list[dict]) -> str | None:
    """The QID of the declared P19 statement's place, or ``None``."""
    value = _value(_chosen(statements))
    qid = value.get("id") if isinstance(value, dict) else None
    return qid if isinstance(qid, str) and qid[:1] == "Q" and qid[1:].isdigit() else None


def labels(payload: object) -> dict[str, str | None]:
    """A ``wbgetentities&props=labels&languages=en`` reply: each item's English label."""
    entities = payload.get("entities") if isinstance(payload, dict) else None
    if not isinstance(entities, dict):
        raise FeedError("Wikidata couldn’t be read.")
    found = {}
    for qid, entity in entities.items():
        label = (((entity or {}).get("labels") or {}).get("en") or {}).get("value") \
            if isinstance(entity, dict) else None
        found[qid] = label if isinstance(label, str) and label.strip() else None
    return found


class Wikidata:
    """Height and place of birth by English Wikipedia title, kept seven days."""

    TTL = 7 * 24 * 3600
    BATCH = 50

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None,
                 clock=lambda: datetime.now(UTC)) -> None:
        self.cache = FeedCache(32)
        self._transport = transport
        self._clock = clock

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=AGENT, timeout=12, transport=self._transport)

    async def _get(self, client: httpx.AsyncClient, url: str, params: dict) -> object:
        response = await client.get(url, params={**params, "format": "json",
                                                 "maxlag": MAXLAG})
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and "error" in payload:
            raise FeedError("Wikidata couldn’t be read just now.")
        return payload

    async def people(self, titles: list[str]) -> dict[str, WikidataPerson]:
        """Each title's QID, height and place of birth. A batch that cannot be read is left
        out (its players' facts stay missing), never filled."""
        assert_may_host(PROVIDER)
        asked = sorted({title_key(t) for t in titles if t})
        found: dict[str, WikidataPerson] = {}
        for start in range(0, len(asked), self.BATCH):
            batch = asked[start:start + self.BATCH]
            try:
                snap = await self.cache.get("people/" + "|".join(batch), self.TTL,
                                            lambda batch=batch: self._fetch(batch))
            except FeedError:
                continue
            for row in snap.rows:
                found[row["title"]] = WikidataPerson(
                    title=row["title"], qid=row["qid"], height_cm=row["height_cm"],
                    birthplace=row["birthplace"],
                    sources=(SourceRef(provider=PROVIDER, checked=snap.checked, revised=None,
                                       revision=None,
                                       url=f"https://www.wikidata.org/wiki/{row['qid']}"),)
                    if row["qid"] else ())
        return found

    async def _fetch(self, titles: list[str]) -> list[dict]:
        async with self._client() as client:
            items = qids(await self._get(client, API, {
                "action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
                "redirects": "1", "formatversion": "2", "titles": "|".join(titles)}))
            ids = sorted({q for q in items.values() if q})
            statements = claims(await self._get(client, ENTITIES, {
                "action": "wbgetentities", "ids": "|".join(ids), "props": "claims"})) \
                if ids else {}
            places = {q: place(statements.get(q, {}).get(BIRTHPLACE, [])) for q in ids}
            wanted = sorted({p for p in places.values() if p})
            named = labels(await self._get(client, ENTITIES, {
                "action": "wbgetentities", "ids": "|".join(wanted), "props": "labels",
                "languages": "en"})) if wanted else {}
        rows = []
        for title in titles:
            if title not in items:
                continue
            qid = items[title]
            held = statements.get(qid, {}) if qid else {}
            where = places.get(qid) if qid else None
            rows.append({"title": title, "qid": qid,
                         "height_cm": height_cm(held.get(HEIGHT, [])),
                         "birthplace": named.get(where) if where else None})
        return rows
