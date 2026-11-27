"""A player's Wikipedia infobox: his listed positions in order, his date of birth, and his
club and international appearances as the infobox lists them (probe-gated).

``studio.first_position`` reads the first position an infobox lists; this reads every one,
in the order listed, with the same reading of each ("[[Defender (association football)#
Centre-back|centre-back]]" is "Centre-back"), so ``positions(text)[0]`` is
``first_position(text)`` where that reads a position (it reads one line, so a list template
written over several lines gives it the template's first line; this reads the list). It also
reads ``birth_date``, each ``clubs``/``caps``/``goals`` row
and each ``nationalteam``/``nationalcaps``/``nationalgoals`` row, and the ``club-update`` and
``nationalteam-update`` stamps those counts run to.

**Gated (B14).** The caps are read here and served by nobody until D4-B's coverage probe passes
("Caps and league games", P-D12). Where it fails, the criterion is withdrawn with one served
line, never shown half-filled.

**How it is read.** The batched request ``Studio.positions`` already makes: one
``prop=revisions&rvprop=content`` for at most 50 titles, with the reply's normalisations and
redirects followed back to the title asked for; where ``api.php`` turns it away, each
article's ``index.php?action=raw``, four at a time. Kept a day.

**Missing stays missing (R8).** A blank caps field is ``None``, a field that is not a count is
``None`` (never 0), and a stamp that is not a date is ``None``.

Non-claim: caps are what the article's editors entered, as of the stamp beside them; a club's
"caps" in an infobox are league appearances only, by the infobox's own convention.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from ...providers import assert_may_host
from ..feed import FeedCache, FeedError
from ..studio import AGENT, API, MAXLAG, RAW, first_position
from .wiki_season import PROVIDER, gather_limited, parse_day, plain, templates, title_key

__all__ = ["Spell", "Infobox", "positions", "birth_date", "parse_infobox", "articles",
           "Infoboxes"]

_INFOBOX = ("Infobox football biography", "Infobox football biography 2", "Infobox footballer")
_LISTS = ("hlist", "flatlist", "plainlist", "ubl", "unbulleted list", "flat list")
_SPLIT = re.compile(r",|/|;|\band\b|\bor\b|<br\s*/?>|\n\s*\*", re.I)


@dataclass(frozen=True)
class Spell:
    """One row of the infobox's career: years, team, appearances and goals as listed."""

    years: str | None
    team: str | None
    caps: int | None
    goals: int | None
    loan: bool


@dataclass(frozen=True)
class Infobox:
    title: str
    positions: tuple[str, ...]          # as listed, in order
    born: str | None                    # ISO date
    clubs: tuple[Spell, ...]            # senior clubs, in the infobox's order
    national: tuple[Spell, ...]
    club_update: str | None             # ISO day the club counts run to
    nationalteam_update: str | None


def _box(wikitext: str):
    found = templates(wikitext, *_INFOBOX)
    return found[0] if found else None


def _cap(word: str) -> str:
    return word[:1].upper() + word[1:]


def _list_items(value: str) -> list[str]:
    """``{{hlist|a|b}}``, ``{{plainlist|* a * b}}`` and the like, unwrapped to their items;
    a plain value is split on commas, slashes, semicolons, "and", "or" and line breaks."""
    items: list[str] = []
    rest = value
    for template in templates(value, *_LISTS):
        for arg in template.positional:
            items += _SPLIT.split(arg)
        rest = rest.replace(value[template.start:template.end], " ")
    items += _SPLIT.split(rest)
    return items


def positions(wikitext: str) -> tuple[str, ...]:
    """Every position the infobox lists, in order, each read as ``first_position`` reads
    the first ("Left-back"); duplicates once. Empty where there is no position field."""
    box = _box(wikitext)
    value = None
    if box is not None:
        value = box.named.get("position") or box.named.get("positions")
    if value is None:
        first = first_position(wikitext)
        return (first,) if first else ()
    value = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", " ", value, flags=re.S)
    found = []
    for item in _list_items(value):
        text = plain(item).strip(" .\t*")
        if text:
            found.append(_cap(text))
    return tuple(dict.fromkeys(found))


def birth_date(wikitext: str) -> str | None:
    """The ``birth_date`` field as an ISO date: ``{{birth date and age|1996|3|14}}`` (with
    ``df=y`` or not), or a date written out; else ``None``."""
    box = _box(wikitext)
    return parse_day(box.named.get("birth_date")) if box is not None else None


def _number(text: str | None) -> int | None:
    value = plain(re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", text or "", flags=re.S))
    value = value.strip("() ")
    return int(value) if re.fullmatch(r"\d{1,4}", value) else None


def _spells(named: dict[str, str], years: str, team: str, caps: str, goals: str) -> list[Spell]:
    numbers = sorted({int(m[1]) for key in named
                      if (m := re.fullmatch(rf"(?:{years}|{team})(\d+)", key))})
    found = []
    for n in numbers:
        raw_team = named.get(f"{team}{n}", "")
        found.append(Spell(years=plain(named.get(f"{years}{n}", "")) or None,
                           team=plain(raw_team.replace("→", " ")) or None,
                           caps=_number(named.get(f"{caps}{n}")),
                           goals=_number(named.get(f"{goals}{n}")),
                           loan="loan" in raw_team.casefold() or "→" in raw_team))
    return found


def parse_infobox(title: str, wikitext: str) -> Infobox | None:
    """The infobox of ``title``'s article; ``None`` where it has none."""
    box = _box(wikitext)
    if box is None:
        return None
    named = box.named
    return Infobox(
        title=title_key(title), positions=positions(wikitext), born=birth_date(wikitext),
        clubs=tuple(_spells(named, "years", "clubs", "caps", "goals")),
        national=tuple(_spells(named, "nationalyears", "nationalteam", "nationalcaps",
                               "nationalgoals")),
        club_update=parse_day(named.get("club-update")),
        nationalteam_update=parse_day(named.get("nationalteam-update")))


def articles(payload: object) -> dict[str, str]:
    """The batched ``prop=revisions&rvprop=content`` reply's articles: each requested title
    and its wikitext, following the reply's normalisations and redirects back to the title
    asked for (``studio.parse_positions``' rule). A missing article is left out."""
    query = payload.get("query") if isinstance(payload, dict) else None
    if not isinstance(query, dict):
        raise FeedError("The players’ articles couldn’t be read.")
    back: dict[str, str] = {}
    for step in (query.get("normalized") or []) + (query.get("redirects") or []):
        if isinstance(step, dict) and isinstance(step.get("to"), str):
            back[step["to"]] = back.get(str(step.get("from")), str(step.get("from")))
    found = {}
    for page in query.get("pages") or []:
        if not isinstance(page, dict) or not isinstance(page.get("title"), str):
            continue
        revisions = page.get("revisions") or [{}]
        content = ((revisions[0].get("slots") or {}).get("main") or {}).get("content")
        if isinstance(content, str):
            found[back.get(page["title"], page["title"])] = content
    return found


class Infoboxes:
    """Players' infoboxes, by article title, read in batches of 50 and kept a day."""

    TTL = 24 * 3600

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.cache = FeedCache(32)
        self._transport = transport

    async def read(self, titles: list[str]) -> dict[str, Infobox]:
        """Each title's infobox, keyed by the title as given (``title_key``-normalised).
        Empty where no article can be read."""
        assert_may_host(PROVIDER)
        asked = sorted({title_key(t) for t in titles if t})
        found: dict[str, Infobox] = {}
        for start in range(0, len(asked), 50):
            batch = asked[start:start + 50]
            try:
                snap = await self.cache.get("infobox/" + "|".join(batch), self.TTL,
                                            lambda batch=batch: self._fetch(batch))
            except FeedError:
                continue
            for row in snap.rows:
                if (box := parse_infobox(row["title"], row["text"])) is not None:
                    found[row["title"]] = box
        return found

    async def _fetch(self, titles: list[str]) -> list[dict]:
        params = {"action": "query", "prop": "revisions", "rvprop": "content",
                  "rvslots": "main", "format": "json", "formatversion": "2",
                  "redirects": "1", "titles": "|".join(titles), "maxlag": MAXLAG}
        async with httpx.AsyncClient(headers=AGENT, timeout=12, follow_redirects=True,
                                     transport=self._transport) as client:
            try:
                response = await client.get(API, params=params)
                response.raise_for_status()
                texts = articles(response.json())
            except (httpx.HTTPError, ValueError, FeedError):
                async def one(title: str) -> tuple[str, str | None]:
                    try:
                        reply = await client.get(RAW, params={"title": title, "action": "raw"})
                        reply.raise_for_status()
                    except httpx.HTTPError:
                        return title, None
                    return title, reply.text

                texts = {title: text for title, text in
                         await gather_limited([one(t) for t in titles]) if text is not None}
        if not texts:
            raise FeedError("The players’ articles couldn’t be read.")
        return [{"title": title_key(title), "text": text} for title, text in texts.items()]
