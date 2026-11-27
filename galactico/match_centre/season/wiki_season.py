"""Real Madrid's season article on English Wikipedia, read into the season model.

One article holds most of what the free sources say about Madrid's season: the squad list
(transcluded from the club's article), appearances and goals per competition
(``{{Efs player2}}``), cards (``{{Fb disc player 3}}``), clean sheets (a ranked wikitable), every
competitive match with its scorers and minutes (``{{footballbox collapsible}}``), the transfers
and the stamps the editors put on the tables (``{{Fb cs footer|u=…}}``, ``{{Updated|…}}``).

**How it is read (B13).** Through the MediaWiki API only, with ``studio.AGENT`` and
``maxlag=5``: one ``action=parse&prop=text|wikitext|revid`` request, whose wikitext gives the
templates and whose HTML gives the transcluded squad list, and one ``prop=revisions`` request
for the time of the revision it parsed. Where ``api.php`` turns the request away, the article's
wikitext is read through ``index.php?action=raw`` instead, as ``Studio.positions`` falls back;
the squad list (HTML only) is then missing, and the facts say so.

**How the tables are joined (REC 1.4.3).** By the player's article link, never by shirt
number: an editor once wrote one defender's number in another's row of the disciplinary table.
A link is compared as MediaWiki compares titles: underscores are spaces, the first letter's
case is set aside, a ``#section`` is dropped.

**Missing stays missing (R8).** A blank cell, a cell that is not a count, a table that is not
there: each is ``None``, never 0, and a cell or a row that could not be read is a named
``ParseFailure``. Nothing is inferred from a table's silence: a player the disciplinary table
does not list has ``None`` cards, not 0 (the table lists only players with a card, but it does
not say so).

**Orders (R1).** The squad is in the squad list's declared order (by position, then shirt
number); season lines follow the squad, then players the list no longer names in the statistics
table's order, each in the article's competition order; matches by kick-off; goals by minute,
then added time, then as the box lists them (the home side's list first); transfers in the
tables' order (In, Out, Contract renewals).

Non-claim: the counts are what Wikipedia's editors entered (the statistics templates cite
FBref); nothing here checks them against another source. The catalogue (D3-A) does that.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from urllib.parse import unquote

import httpx

from ...providers import assert_may_host
from ..feed import FeedCache, FeedError
from ..kickoff import from_utc, utc_text
from ..openfootball import season_start
from ..studio import AGENT, API, MAXLAG, RAW, parse_roster, revision_time, stamp_params
from .competitions import BY_SLUG, season_label
from .keys import MADRID_FD_ID, MADRID_KEY, fold, match_key, plate, slugify
from .model import (
    GoalEvent,
    Match,
    PersonRef,
    SeasonLine,
    Side,
    SourceRef,
    SquadEntry,
    TeamRef,
    Transfer,
)

__all__ = [
    "PROVIDER", "LICENCE", "CREDIT", "COMPETITION_NAMES", "Template", "templates",
    "links", "plain", "title_key", "parse_day", "sections", "wikitables", "table_rows",
    "Column", "StatsRow", "Stats", "ParseFailure", "Stamps", "ArticleRef", "Box",
    "MadridSeasonFacts", "efs_columns", "efs_rows", "statistics", "discipline", "ranked",
    "clean_sheets", "boxes", "transfers", "stamps", "squad_entries", "season_lines",
    "read_article", "article_for", "MadridSeason",
]

PROVIDER = "wikipedia"
CREDIT = "Wikipedia contributors"
LICENCE = "https://creativecommons.org/licenses/by-sa/4.0/"

COMPETITION_NAMES: dict[str, str] = {
    "la liga": "la-liga",
    "copa del rey": "copa-del-rey", "cdr": "copa-del-rey",
    "uefa champions league": "champions-league", "champions league": "champions-league",
    "ucl": "champions-league",
    "supercopa de espana": "supercopa", "supercopa": "supercopa",
}
"""The article's names for Madrid's competitions (folded), and the slug of each. A column or a
section with any other name is not read."""


# ------------------------------------------------------------------ wikitext


@dataclass(frozen=True)
class Template:
    """One ``{{…}}`` call: its name as written, its named and its positional arguments."""

    name: str
    named: dict[str, str]
    positional: tuple[str, ...]
    start: int
    end: int


def _end_of(text: str, start: int, opening: str, closing: str) -> int:
    """The index just past the bracket that closes the one opened at ``start``; -1 if none."""
    depth, i = 0, start
    while i < len(text):
        if text.startswith(opening, i):
            depth += 1
            i += len(opening)
        elif text.startswith(closing, i):
            depth -= 1
            i += len(closing)
            if depth == 0:
                return i
        else:
            i += 1
    return -1


def _split(body: str, separator: str = "|") -> list[str]:
    """``body`` split on ``separator`` outside ``{{…}}`` and ``[[…]]``."""
    parts, depth, square, i, start = [], 0, 0, 0, 0
    while i < len(body):
        two = body[i:i + 2]
        if two == "{{":
            depth += 1
            i += 2
        elif two == "}}" and depth:
            depth -= 1
            i += 2
        elif two == "[[":
            square += 1
            i += 2
        elif two == "]]" and square:
            square -= 1
            i += 2
        elif not depth and not square and body.startswith(separator, i):
            parts.append(body[start:i])
            i += len(separator)
            start = i
        else:
            i += 1
    parts.append(body[start:])
    return parts


def _name_key(name: str) -> str:
    return re.sub(r"[\s_]+", " ", name).strip().casefold()


def templates(text: str, *names: str) -> list[Template]:
    """The top-level templates of ``text`` whose name is one of ``names`` (case and
    underscores set aside), in the order they occur; every top-level template without
    ``names``."""
    wanted = {_name_key(n) for n in names}
    found, i = [], 0
    while (i := text.find("{{", i)) != -1:
        end = _end_of(text, i, "{{", "}}")
        if end == -1:
            break
        parts = _split(text[i + 2:end - 2])
        name = parts[0].strip()
        if not wanted or _name_key(name) in wanted:
            named, positional = {}, []
            for part in parts[1:]:
                key, sign, value = part.partition("=")
                if sign and re.fullmatch(r"\s*[\w\- ]+\s*", key) and "[" not in key:
                    named[key.strip()] = value.strip()
                else:
                    positional.append(part.strip())
            found.append(Template(name, named, tuple(positional), i, end))
        i = end
    return found


_LINK = re.compile(r"\[\[([^\[\]|]*)(?:\|([^\[\]]*))?\]\]")
_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.S)
_TAG = re.compile(r"<[^>]+>")
_BOLD = re.compile(r"'{2,}")


def links(text: str) -> list[tuple[str, str]]:
    """Every ``[[title|text]]`` in ``text``: the title and the text it shows."""
    return [(m[1].strip(), (m[2] if m[2] is not None else m[1]).strip())
            for m in _LINK.finditer(text) if m[1].strip()]


def _drop_templates(text: str) -> str:
    out, i = [], 0
    while (j := text.find("{{", i)) != -1:
        end = _end_of(text, j, "{{", "}}")
        if end == -1:
            break
        out.append(text[i:j])
        i = end
    out.append(text[i:])
    return "".join(out)


def plain(text: str) -> str:
    """What ``text`` shows as words: links as the text they show, without references,
    templates (flags among them), tags or bold and italic marks, spaces collapsed."""
    text = _REF.sub(" ", text)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = _LINK.sub(lambda m: m[2] if m[2] is not None else m[1], text)
    text = _drop_templates(text)
    text = _BOLD.sub("", _TAG.sub(" ", text))
    return re.sub(r"\s+", " ", text).strip()


def title_key(title: str) -> str:
    """A title as MediaWiki compares titles: an HTML link's underscores and percent-escapes
    read as the title they encode, a ``#section`` dropped, the first letter upper case."""
    text = re.sub(r"[\s_]+", " ", unquote(title).split("#", 1)[0]).strip()
    return text[:1].upper() + text[1:]


def _undisambiguated(title: str) -> str:
    """"Carlos Puntá (footballer, born 2006)" is "Carlos Puntá"."""
    return re.sub(r"\s*\([^()]*\)\s*$", "", title).strip() or title


_MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august",
           "september", "october", "november", "december")


def parse_day(text: str | None) -> str | None:
    """An ISO day from "24 November 2026", "November 24, 2026" or "2026-11-24"; ``None``
    for anything else, a ``{{…}}`` date template's numbers included where they are y|m|d."""
    if not text:
        return None
    for template in templates(text):
        numbers = [p for p in template.positional if re.fullmatch(r"\d{1,4}", p)]
        if len(numbers) >= 3 and len(numbers[0]) == 4:
            try:
                return date(int(numbers[0]), int(numbers[1]), int(numbers[2])).isoformat()
            except ValueError:
                return None
    words = plain(text).replace(",", " ").split()
    try:
        if len(words) == 1 and re.fullmatch(r"\d{4}-\d\d-\d\d", words[0]):
            return date.fromisoformat(words[0]).isoformat()
        if len(words) >= 3 and words[1].casefold() in _MONTHS:
            return date(int(words[2]), _MONTHS.index(words[1].casefold()) + 1,
                        int(words[0])).isoformat()
        if len(words) >= 3 and words[0].casefold() in _MONTHS:
            return date(int(words[2]), _MONTHS.index(words[0].casefold()) + 1,
                        int(words[1])).isoformat()
    except ValueError:
        return None
    return None


_HEADING = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$", re.M)


def sections(text: str) -> list[tuple[int, str, int, int]]:
    """Each heading's (level, title, start of its body, end of its body): the body runs to
    the next heading of the same or a higher level."""
    heads = [(len(m[1]), plain(m[2]), m.start(), m.end()) for m in _HEADING.finditer(text)]
    found = []
    for n, (level, title, _, body) in enumerate(heads):
        end = next((start for lvl, _, start, _ in heads[n + 1:] if lvl <= level), len(text))
        found.append((level, title, body, end))
    return found


def _section(text: str, *path: str) -> str | None:
    """The body of the section reached by heading ``path`` (each one inside the last)."""
    lo, hi, level = 0, len(text), 1
    for wanted in path:
        for lvl, title, start, end in sections(text):
            if lo <= start < hi and lvl > level and fold(title) == fold(wanted):
                lo, hi, level = start, end, lvl
                break
        else:
            return None
    return text[lo:hi]


def wikitables(text: str) -> list[str]:
    """The top-level ``{| … |}`` tables of ``text``."""
    found, i = [], 0
    while (i := text.find("{|", i)) != -1:
        end = _end_of(text, i, "{|", "|}")
        if end == -1:
            break
        found.append(text[i:end])
        i = end
    return found


@dataclass(frozen=True)
class Cell:
    header: bool
    rowspan: int
    text: str


def _cell(raw: str, header: bool) -> Cell:
    parts = _split(raw)
    attrs, text = ("", raw) if len(parts) == 1 else (parts[0], "|".join(parts[1:]))
    span = re.search(r"rowspan\s*=\s*\"?(\d+)", attrs)
    return Cell(header, int(span[1]) if span else 1, text.strip())


def table_rows(table: str) -> list[list[Cell]]:
    """A wikitable's rows as cells, ``||`` and ``!!`` split, attributes read off: the
    editors' line that starts ``||`` is a row like any other."""
    rows: list[list[Cell]] = []
    current: list[Cell] | None = None
    for line in table.splitlines()[1:]:
        stripped = line.strip()
        if stripped.startswith("|}"):
            break
        if stripped.startswith("|-"):
            current = None
            continue
        if stripped.startswith("|+"):
            continue
        if stripped.startswith(("!", "|")):
            if current is None:
                current = []
                rows.append(current)
            header = stripped.startswith("!")
            body = stripped[1:]
            if not header and body.startswith("|"):
                body = body[1:]
            pieces = _split(body, "||")
            if header:
                pieces = [p for piece in pieces for p in _split(piece, "!!")]
            current.extend(_cell(p, header) for p in pieces)
        elif current:
            last = current[-1]
            current[-1] = Cell(last.header, last.rowspan, f"{last.text}\n{stripped}".strip())
    return [row for row in rows if row]


def _grid(rows: Sequence[Sequence[Cell]], width: int) -> list[list[str]]:
    """Rows of ``width`` cells, a ``rowspan`` cell repeated down its rows."""
    carried: dict[int, tuple[int, str]] = {}
    out = []
    for row in rows:
        cells = iter(row)
        filled = []
        for column in range(width):
            if column in carried:
                left, text = carried[column]
                filled.append(text)
                if left <= 1:
                    del carried[column]
                else:
                    carried[column] = (left - 1, text)
                continue
            cell = next(cells, None)
            if cell is None:
                filled.append("")
                continue
            filled.append(cell.text)
            if cell.rowspan > 1:
                carried[column] = (cell.rowspan - 1, cell.text)
        out.append(filled)
    return out


def _count(text: str) -> tuple[int | None, bool]:
    """A cell's count and whether the cell was read: a blank is ``(None, True)``; a cell that
    is not a whole number is ``(None, False)``; never 0 for either."""
    value = plain(text)
    if value in ("", "–", "—", "-"):
        return None, True
    return (int(value), True) if re.fullmatch(r"\d{1,4}", value) else (None, False)


def _competition(name: str) -> str | None:
    text = plain(name)
    abbr = re.search(r"<abbr[^>]*title=\"([^\"]+)\"", name)
    for candidate in ([abbr[1]] if abbr else []) + [text]:
        if (slug := COMPETITION_NAMES.get(fold(candidate))) is not None:
            return slug
    return None


# ------------------------------------------------------------------ the facts


@dataclass(frozen=True)
class ParseFailure:
    """A table, row or box the parser could not read, named so a page can say so."""

    table: str          # "statistics", "discipline", "clean_sheets", "boxes", "transfers", …
    item: str | None    # the player, match or row it concerns, as the article writes it
    line: str           # the server's sentence


@dataclass(frozen=True)
class Stamps:
    """The dates the editors put on the tables, and the revision they were read from."""

    statistics: str | None      # {{Fb cs footer|u=…}}: the day the counts run to
    discipline: str | None      # {{Fb disc footer 3|u=…}}
    updated: tuple[str, ...]    # each {{Updated|…}} in the article's order
    revision: int | None
    revised: str | None         # the revision's timestamp (ISO UTC)


@dataclass(frozen=True)
class ArticleRef:
    """A player's article, by the link the squad list or a table gives."""

    person: PersonRef
    title: str


@dataclass(frozen=True)
class MadridSeasonFacts:
    title: str
    season: str                          # "2026/27"
    squad: tuple[SquadEntry, ...]        # the squad list, in its declared order
    articles: tuple[ArticleRef, ...]     # each person's article title (squad, then others)
    lines: tuple[SeasonLine, ...]
    matches: tuple[Match, ...]           # Madrid's competitive matches, by kick-off
    goals: tuple[GoalEvent, ...]
    transfers: tuple[Transfer, ...]
    stamps: Stamps
    failures: tuple[ParseFailure, ...]
    sources: tuple[SourceRef, ...]
    warning: str | None                  # a failed refresh: these facts are the last read


@dataclass(frozen=True)
class Column:
    competition: str                     # a slug
    name: str                            # as the article heads it


@dataclass(frozen=True)
class StatsRow:
    title: str                           # the article link, ``title_key``-normalised
    name: str                            # as the row shows him
    counts: dict[str, int | None]        # competition slug -> count (None: blank or unread)


@dataclass(frozen=True)
class Stats:
    columns: tuple[Column, ...]
    rows: tuple[StatsRow, ...]
    failures: tuple[ParseFailure, ...]


def _who(text: str) -> tuple[str, str] | None:
    found = links(text)
    if not found:
        return None
    title, shown = found[0]
    return title_key(title), plain(shown) or title_key(title)


def _efs_slots(wikitext: str) -> list[str | None] | None:
    """Each ``{{Efs start}}`` column's competition slug, in order, ``None`` for a competition
    not read; ``None`` where the article has no ``{{Efs start}}``."""
    for template in templates(wikitext, "Efs start"):
        return [_competition(arg) for arg in template.positional]
    return None


def efs_columns(wikitext: str) -> tuple[Column, ...]:
    """The statistics table's competitions in column order, from ``{{Efs start}}``."""
    for template in templates(wikitext, "Efs start"):
        return tuple(Column(slug, plain(arg)) for arg in template.positional
                     if (slug := _competition(arg)) is not None)
    return ()


def efs_rows(wikitext: str) -> Stats:
    """Appearances and goals per competition from every ``{{Efs player2}}`` row: counts keyed
    ``apps:<slug>`` and ``goals:<slug>``. Each competition is read from its own column of
    ``{{Efs start}}``, so a column of another competition moves nothing."""
    slots, columns = _efs_slots(wikitext), efs_columns(wikitext)
    rows, failures = [], []
    if not slots or not columns:
        return Stats((), (), (ParseFailure("statistics", None, _UNREAD["statistics"]),))
    for template in templates(wikitext, "Efs player2"):
        who = _who(template.named.get("name", ""))
        if who is None:
            failures.append(ParseFailure("statistics", plain(template.named.get("name", ""))
                                         or None, "A squad statistics row names no article; "
                                         "it is left out."))
            continue
        title, name = who
        values = list(template.positional)
        counts: dict[str, int | None] = {}
        whole = len(values) == 2 * len(slots)
        read = whole
        for n, slug in enumerate(slots):
            if slug is None:
                continue
            for kind, offset in (("apps", 0), ("goals", 1)):
                count, ok = _count(values[2 * n + offset]) if whole else (None, False)
                counts[f"{kind}:{slug}"] = count
                read = read and ok
        if not read:
            failures.append(ParseFailure(
                "statistics", name, f"Wikipedia’s squad statistics row for {name} couldn’t "
                "be read in full; the counts it couldn’t read are left blank."))
        rows.append(StatsRow(title, name, counts))
    return Stats(columns, tuple(rows), tuple(failures))


def statistics(wikitext: str) -> Stats:
    """The squad statistics (``efs_rows``)."""
    return efs_rows(wikitext)


def discipline(wikitext: str) -> Stats:
    """Cards per competition from ``{{Fb disc player 3}}``, its columns from
    ``{{fb disc header 3}}``: counts keyed ``yellow:<slug>``, ``second_yellow:<slug>`` and
    ``red:<slug>``. Joined by the ``p`` link; ``n`` (the shirt number) is never read."""
    headers = templates(wikitext, "Fb disc header 3")
    numbered = sorted(((int(k[1:]), v) for k, v in (headers[0].named if headers else {}).items()
                       if re.fullmatch(r"c\d", k)))
    slots = [(n, Column(slug, plain(value))) for n, value in numbered
             if (slug := _competition(value)) is not None]
    columns = tuple(column for _, column in slots)
    rows_ = templates(wikitext, "Fb disc player 3")
    if not rows_:
        return Stats(columns, (), ())
    if not columns:
        return Stats((), (), (ParseFailure("discipline", None, _UNREAD["discipline"]),))
    rows, failures = [], []
    for template in rows_:
        who = _who(template.named.get("p", ""))
        if who is None:
            failures.append(ParseFailure("discipline", None, "A disciplinary row names no "
                                         "article; it is left out."))
            continue
        title, name = who
        counts: dict[str, int | None] = {}
        read = True
        for n, column in slots:   # each competition from its own cN, whatever lies between
            for kind, key in (("yellow", "yc"), ("second_yellow", "syc"), ("red", "rc")):
                raw = template.named.get(f"{key}{n}")
                count, ok = _count(raw) if raw is not None else (None, False)
                counts[f"{kind}:{column.competition}"] = count
                read = read and ok
        if not read:
            failures.append(ParseFailure(
                "discipline", name, f"Wikipedia’s disciplinary row for {name} couldn’t be read "
                "in full; the cards it couldn’t read are left blank."))
        rows.append(StatsRow(title, name, counts))
    return Stats(columns, tuple(rows), tuple(failures))


def ranked(table: str, kind: str, label: str) -> tuple[Stats, dict[str, int | None]]:
    """A Goals or a Clean sheets table: each player's count per competition column (keyed
    ``<kind>:<slug>``), and the own-goal row's counts where it has one. The rank and the
    total columns are not read (the counts are)."""
    rows = table_rows(table)
    if not rows:
        return Stats((), (), (ParseFailure(label, None, _UNREAD[label]),)), {}
    head = [c.text for c in rows[0] if c.header]
    player = next((i for i, text in enumerate(head) if fold(plain(text)) == "player"), None)
    slots = [(i - player, Column(slug, plain(text))) for i, text in enumerate(head)
             if player is not None and i > player and (slug := _competition(text)) is not None]
    columns = tuple(column for _, column in slots)
    if not columns:
        return Stats((), (), (ParseFailure(label, None, _UNREAD[label]),)), {}
    found, failures, own = [], [], {}
    for row in rows[1:]:
        if all(c.header for c in row):
            continue
        texts = [c.text for c in row if not c.header]
        at = next((i for i, t in enumerate(texts) if links(t)), None)
        if at is None:
            own_at = next((i for i, t in enumerate(texts)
                           if "own goal" in plain(t).casefold()), None)
            if own_at is not None:
                own = {c.competition: (_count(texts[own_at + offset])[0]
                                       if own_at + offset < len(texts) else None)
                       for offset, c in slots}
            continue
        title, name = _who(texts[at]) or ("", "")
        counts, read = {}, True
        for offset, column in slots:
            count, ok = (_count(texts[at + offset]) if at + offset < len(texts)
                         else (None, False))
            counts[f"{kind}:{column.competition}"] = count
            read = read and ok
        if not read:
            failures.append(ParseFailure(label, name, f"Wikipedia’s {_WORDS[label]} row for "
                                         f"{name} couldn’t be read in full; the counts it "
                                         "couldn’t read are left blank."))
        found.append(StatsRow(title, name, counts))
    return Stats(columns, tuple(found), tuple(failures)), own


def clean_sheets(wikitext: str) -> Stats:
    """Clean sheets per goalkeeper per competition, from the Clean sheets section's table."""
    body = _section(wikitext, "Statistics", "Clean sheets")
    tables = wikitables(body) if body is not None else []
    if not tables:
        return Stats((), (), ())
    return ranked(tables[0], "clean_sheets", "clean_sheets")[0]


_WORDS = {"statistics": "squad statistics", "discipline": "disciplinary",
          "clean_sheets": "clean sheets", "goals": "goals"}
_UNREAD = {
    "statistics": "Wikipedia’s squad statistics table couldn’t be read; appearances and goals "
                  "are left blank.",
    "discipline": "Wikipedia’s disciplinary table couldn’t be read; cards are left blank.",
    "clean_sheets": "Wikipedia’s clean sheets table couldn’t be read; clean sheets are left "
                    "blank.",
    "goals": "Wikipedia’s goals table couldn’t be read.",
    "squad": "The squad list couldn’t be read just now; the squad is left out.",
}


# ------------------------------------------------------------------ match boxes


@dataclass(frozen=True)
class Box:
    """One footballbox read: the match and its goals."""

    match: Match
    goals: tuple[GoalEvent, ...]


_BOXES = ("footballbox collapsible", "football box collapsible", "footballbox",
          "football box")
_SCORE = re.compile(r"^\s*(\d{1,2})\s*[–—\-−]\s*(\d{1,2})")
_MINUTE = re.compile(r"^(\d{1,3})(?:\s*\+\s*(\d{1,2}))?'?$")
_MADRID = {"real madrid", "real madrid cf", "real madrid c.f."}

MADRID_REF = TeamRef(key=MADRID_KEY, fd_id=MADRID_FD_ID, name="Real Madrid",
                     short="Real Madrid", plate="RMA")
"""The article's own club, which its boxes write as plain "Real Madrid"."""


def _team(text: str) -> TeamRef | None:
    found = links(text)
    shown = plain(text)
    if not shown:
        return None
    if fold(shown) in _MADRID or (found and fold(_undisambiguated(found[0][0])) in _MADRID):
        return MADRID_REF
    name = _undisambiguated(title_key(found[0][0])) if found else shown
    short = plain(found[0][1]) if found else shown
    try:
        return TeamRef(key=slugify(short) or slugify(name), fd_id=None, name=name,
                       short=short, plate=plate(short))
    except ValueError:
        return None


def _kickoff(day: str, time: str) -> str | None:
    """The UTC instant of ``{{UTZ|21:30|2}}`` on ``day``: the local time less the offset the
    template states. A time without its offset has no instant."""
    for template in templates(time, "UTZ"):
        if len(template.positional) >= 2:
            clock = re.fullmatch(r"(\d{1,2})[:.](\d\d)", template.positional[0].strip())
            offset = re.fullmatch(r"([+\-−]?)(\d{1,2})(?:[:.](\d\d))?",
                                  template.positional[1].strip())
            if clock and offset and int(clock[1]) < 24 and int(clock[2]) < 60:
                sign = -1 if offset[1] in ("-", "−") else 1
                local = datetime.fromisoformat(day).replace(
                    hour=int(clock[1]), minute=int(clock[2]), tzinfo=UTC)
                shift = timedelta(hours=int(offset[2]), minutes=int(offset[3] or 0))
                return utc_text(local - sign * shift)
    return None


def _goal_events(text: str, side: Literal["home", "away"], key: str,
                 squad: dict[str, PersonRef], source: SourceRef, order: int,
                 failures: list[ParseFailure], label: str) -> list[tuple[tuple, GoalEvent]]:
    """Each ``{{goal|…}}`` in a box's goals field, with the scorer whose link precedes it."""
    events = []
    last: tuple[str, str] | None = None
    i = 0
    tokens = sorted([(m.start(), "link", m) for m in _LINK.finditer(text)]
                    + [(t.start, "goal", t) for t in templates(text, "goal")],
                    key=lambda item: item[0])
    for _, what, item in tokens:
        if what == "link":
            last = (title_key(item[1]), plain(item[2] if item[2] is not None else item[1]))
            continue
        if last is None:
            failures.append(ParseFailure("boxes", label, f"A goal in {label} names no scorer; "
                                         "it is left out."))
            continue
        title, shown = last
        args = list(item.positional)
        pairs = [(args[n], args[n + 1] if n + 1 < len(args) else "")
                 for n in range(0, len(args), 2)]
        for minute_text, note in pairs:
            minute_text = plain(minute_text)
            found = _MINUTE.fullmatch(minute_text)
            if minute_text and found is None:
                failures.append(ParseFailure("boxes", label, f"A goal minute in {label} "
                                             "couldn’t be read; that goal has no minute."))
            minute = int(found[1]) if found else None
            added = int(found[2]) if found and found[2] else None
            note_text = fold(plain(note))
            person = squad.get(title)
            events.append(((minute is None, minute or 0, added or 0, order, i), GoalEvent(
                match=key, side=side, minute=minute, added=added,
                scorer=person.name if person else _undisambiguated(title) or shown,
                scorer_key=person.key if person else None,
                penalty=note_text.startswith("pen"),
                own_goal=note_text in ("o.g.", "og", "o.g", "own goal"),
                running=None, sources=(source,))))
            i += 1
    return events


def _stage(round_text: str, heading: str | None) -> tuple[str | None, int | None]:
    """A box's stage and matchday: a round that is a number is the matchday, in the stage the
    section's own heading names ("League phase"); "League phase Matchday 1" is both; any
    other round ("First round", "Semi-finals") is the stage."""
    if re.fullmatch(r"\d{1,2}", round_text):
        return heading, int(round_text)
    found = re.fullmatch(r"(?i)(.*?)\s*matchday\s*(\d{1,2})", round_text)
    if found:
        return found[1].strip() or heading, int(found[2])
    return round_text or heading, None


def _box(template: Template, competition: str, stage_heading: str | None, season: str,
         today: date, squad: dict[str, PersonRef], source: SourceRef,
         failures: list[ParseFailure]) -> Box | None:
    field = template.named
    day = parse_day(field.get("date"))
    home, away = _team(field.get("team1", "")), _team(field.get("team2", ""))
    label = f"{plain(field.get('team1', ''))} v {plain(field.get('team2', ''))}".strip()
    if day is None or home is None or away is None:
        failures.append(ParseFailure("boxes", label or None, "A match box couldn’t be read; "
                                     "it is left out."))
        return None
    kickoff = _kickoff(day, field.get("time", ""))
    madrid_day = from_utc(datetime.fromisoformat(kickoff.replace("Z", "+00:00")),
                          "CET").date().isoformat() if kickoff else day
    key = match_key(None, home.short, away.short, madrid_day)
    score_text = plain(field.get("score", ""))
    score = _SCORE.match(score_text)
    ahead = date.fromisoformat(madrid_day) > today
    if ahead and (score or plain(field.get("goals1", "")) or plain(field.get("goals2", ""))):
        failures.append(ParseFailure("boxes", label, f"The box for {label} on {day} carries a "
                                     "result before its day; the result and goals are left "
                                     "out."))
        score = None
    elif score_text and score is None and not re.fullmatch(
            r"(?i)v|vs\.?|p–p|postponed|cancelled|abandoned", score_text):
        failures.append(ParseFailure("boxes", label, f"The result of {label} couldn’t be read; "
                                     "it is left out."))
    result = Side(int(score[1]), int(score[2])) if score else Side(None, None)
    duration = winner = None
    if score:
        rest = fold(score_text[score.end():])
        shootout = (_SCORE.match(plain(field.get("penaltyscore", "")))
                    or re.search(r"\((\d{1,2})\s*[–—\-−]\s*(\d{1,2})\s*p", rest))
        duration = ("PENALTY_SHOOTOUT" if shootout
                    else "EXTRA_TIME" if "a.e.t" in rest or "aet" in rest else "REGULAR")
        decided = ((int(shootout[1]), int(shootout[2])) if shootout
                   else (result.home, result.away))
        winner = ("HOME_TEAM" if decided[0] > decided[1]
                  else "AWAY_TEAM" if decided[0] < decided[1] else "DRAW")
    stage, matchday = _stage(plain(field.get("round", "")), stage_heading)
    crowd = re.sub(r"[,\s.]", "", plain(field.get("attendance", "")))
    report = field.get("report", "").strip()
    match = Match(
        key=key, fd_id=None, legacy_keys=(), competition=competition, season=season,
        stage=stage, matchday=matchday, group=None,
        kickoff_utc=kickoff, kickoff_confirmed=kickoff is not None,
        status="FINISHED" if score else ("TIMED" if kickoff else "SCHEDULED"),
        home=home, away=away, result=result, half_time=Side(None, None),
        duration=duration, winner=winner, referee=plain(field.get("referee", "")) or None,
        ground=plain(field.get("stadium", "")) or None,
        attendance=int(crowd) if re.fullmatch(r"\d{1,6}", crowd) and int(crowd) > 0 else None,
        report_url=report if re.fullmatch(r"https?://\S+", report) else None,
        source_updated=None, sources=(source,))
    events = [] if ahead else (
        _goal_events(field.get("goals1", ""), "home", key, squad, source, 0, failures, label)
        + _goal_events(field.get("goals2", ""), "away", key, squad, source, 1, failures, label))
    ordered = [event for _, event in sorted(events, key=lambda item: item[0])]
    if score and ordered:
        ordered = _running(ordered, result)
    return Box(match, tuple(ordered))


def _running(events: list[GoalEvent], result: Side) -> list[GoalEvent]:
    """The running result after each goal, only where the order is certain: every goal has
    a minute, no two goals of different sides share one, and the goals add up to the
    result. Otherwise ``running`` stays ``None``."""
    stamps = [(e.minute, e.added or 0, e.side) for e in events]
    tied = any(a[:2] == b[:2] and a[2] != b[2] for a in stamps for b in stamps)
    counts = (sum(e.side == "home" for e in events), sum(e.side == "away" for e in events))
    if any(e.minute is None for e in events) or tied or counts != (result.home, result.away):
        return events
    home = away = 0
    out = []
    for event in events:
        home += event.side == "home"
        away += event.side == "away"
        out.append(replace(event, running=Side(home, away)))
    return out


def boxes(wikitext: str, *, season: str, today: date, squad: dict[str, PersonRef],
          source: SourceRef) -> tuple[list[Box], list[ParseFailure]]:
    """Every footballbox in the Competitions section, with the competition its section names;
    boxes elsewhere (pre-season friendlies) are not read. In kick-off order (a box with no
    kick-off by its day), then as the article lists them."""
    failures: list[ParseFailure] = []
    heads = sections(wikitext)
    competitions = next(((start, end) for level, title, start, end in heads
                         if level == 2 and fold(title) == "competitions"), None)
    if competitions is None:
        return [], [ParseFailure("boxes", None, "The article’s Competitions section couldn’t be "
                                 "found; no match is read from it.")]
    found = []
    for n, template in enumerate(templates(wikitext, *_BOXES)):
        if not competitions[0] <= template.start < competitions[1]:
            continue
        around = [(level, title) for level, title, start, end in heads
                  if start <= template.start < end and level >= 3]
        section = next((title for level, title in around if level == 3), None)
        slug = COMPETITION_NAMES.get(fold(section or ""))
        if slug is None:
            continue
        inner = next((title for level, title in around if level == 4
                      and fold(title) not in ("matches", "fixtures")), None)
        box = _box(template, slug, inner, season, today, squad, source, failures)
        if box is not None:
            found.append((box.match.kickoff_utc or box.match.key[-10:] + "T99", n, box))
    return [box for *_, box in sorted(found, key=lambda item: item[:2])], failures


# ------------------------------------------------------------------ transfers


_TABLES: tuple[tuple[str, Literal["in", "out", "renewal"]], ...] = (
    ("In", "in"), ("Out", "out"), ("Contract renewals", "renewal"))


def _heading(text: str) -> str:
    """A header cell's word: "Date", or "Pos." for ``{{Abbr|Pos.|Position}}``, folded and
    without its full stop."""
    shown = plain(text)
    if not shown:
        found = templates(text)
        shown = plain(found[0].positional[0]) if found and found[0].positional else ""
    return fold(shown).rstrip(".")


def transfers(wikitext: str, source: SourceRef) -> tuple[list[Transfer], list[ParseFailure]]:
    """The In, Out and Contract renewals tables, rowspans carried down, in the tables' order.
    A renewal keeps its day and player only: contract terms are out of scope."""
    found: list[Transfer] = []
    failures: list[ParseFailure] = []
    for heading, direction in _TABLES:
        body = _section(wikitext, "Transfers", heading)
        tables = wikitables(body) if body is not None else []
        if not tables:
            continue
        rows = table_rows(tables[0])
        head = [_heading(c.text) for c in rows[0]] if rows and all(
            c.header for c in rows[0]) else []
        if "date" not in head or "player" not in head:
            failures.append(ParseFailure("transfers", heading, f"The {heading} transfers table "
                                         "couldn’t be read; it is left out."))
            continue
        column = {name: n for n, name in enumerate(head)}
        club = column.get("from" if direction == "in" else "to")
        for cells in _grid(rows[1:], len(head)):
            day = parse_day(cells[column["date"]])
            who = links(cells[column["player"]])
            kind = plain(cells[column["type"]]) if "type" in column else ""
            if day is None or not who or (direction != "renewal" and not kind):
                failures.append(ParseFailure(
                    "transfers", plain(who[0][1]) if who else None,
                    f"A row of the {heading} transfers table couldn’t be read; it is left out."))
                continue
            found.append(Transfer(
                day=day, person=plain(who[0][1]), direction=direction,
                club=(plain(cells[club]) or None) if club is not None else None,
                kind=kind if direction != "renewal" else "Contract renewal",
                sources=(source,)))
    return found, failures


# ------------------------------------------------------------------ stamps and the squad


def stamps(wikitext: str, revision: int | None, revised: str | None) -> Stamps:
    cs = templates(wikitext, "Fb cs footer")
    disc = templates(wikitext, "Fb disc footer 3")
    return Stamps(
        statistics=parse_day(cs[0].named.get("u")) if cs else None,
        discipline=parse_day(disc[0].named.get("u")) if disc else None,
        updated=tuple(day for t in templates(wikitext, "Updated")
                      if (day := parse_day(next(iter(t.positional), ""))) is not None),
        revision=revision, revised=revised)


def person_key(title: str) -> str:
    """A Wikipedia person's key: the slug of his article's title (PersonRef, PLAN 3.2)."""
    return slugify(title_key(title))


def squad_entries(html: str | None) -> tuple[list[SquadEntry], dict[str, PersonRef],
                                             list[ParseFailure]]:
    """The squad list (``studio.parse_roster``, the same parser and the same order the
    Lineup reads), as squad entries; and each listed player's reference by article title.
    ``nationality`` is the list's own three-letter code ("ESP"), as it writes it."""
    if html is None:
        return [], {}, [ParseFailure("squad", None, _UNREAD["squad"])]
    try:
        players = parse_roster(html)
    except FeedError:
        return [], {}, [ParseFailure("squad", None, _UNREAD["squad"])]
    entries, refs = [], {}
    for player in players:
        title = title_key(player["id"])
        ref = PersonRef(key=person_key(title), name=player["name"])
        refs[title] = ref
        entries.append(SquadEntry(person=ref, group=player["group"], shirt=player["number"],
                                  born=None, nationality=player["nation"] or None))
    return entries, refs, []


def season_lines(stats: Stats, cards: Stats, sheets: Stats, refs: dict[str, PersonRef],
                 source: SourceRef) -> tuple[list[SeasonLine], list[ArticleRef]]:
    """One line per player per competition of the statistics table, joined by article link
    with the disciplinary and clean sheets tables: the squad list's players in its order,
    then the tables' other players as the statistics table lists them; and each player's
    article, in the same order (the squad list's players all, with a line or not)."""
    by_title: dict[str, dict[str, int | None]] = {}
    for table in (stats, cards, sheets):
        for row in table.rows:
            by_title.setdefault(row.title, {}).update(row.counts)
    names = {row.title: row.name for table in (sheets, cards, stats) for row in table.rows}
    others = list(dict.fromkeys(row.title for table in (stats, cards, sheets)
                                for row in table.rows if row.title not in refs))
    people = [(title, ref) for title, ref in refs.items()]
    people += [(title, PersonRef(key=person_key(title), name=names[title])) for title in others]
    columns = [c.competition for c in stats.columns] or [c.competition for c in cards.columns]
    lines = []
    for title, ref in people:
        counts = by_title.get(title)
        if counts is None:
            continue
        for slug in columns:
            lines.append(SeasonLine(
                person=ref, competition=slug, appearances=counts.get(f"apps:{slug}"),
                goals=counts.get(f"goals:{slug}"), yellow=counts.get(f"yellow:{slug}"),
                second_yellow=counts.get(f"second_yellow:{slug}"),
                red=counts.get(f"red:{slug}"), clean_sheets=counts.get(f"clean_sheets:{slug}"),
                sources=(source,)))
    return lines, [ArticleRef(ref, title) for title, ref in people]


def article_for(day: date) -> tuple[str, str, str]:
    """``day``'s season: its label ("2026/27"), its article title and URL (the Lineup's)."""
    year = season_start(day)
    title = f"{year}–{(year + 1) % 100:02} Real Madrid CF season"
    return (season_label(BY_SLUG["la-liga"], year), title,
            "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"))


def read_article(wikitext: str, html: str | None, *, day: date, checked: str,
                 revision: int | None, revised: str | None) -> MadridSeasonFacts:
    """The facts of one revision of the season article (pure: no request)."""
    season, title, url = article_for(day)
    source = SourceRef(provider=PROVIDER, checked=checked, revised=revised, revision=revision,
                       url=url)
    squad, refs, failures = squad_entries(html)
    stats, cards, sheets = statistics(wikitext), discipline(wikitext), clean_sheets(wikitext)
    failures += [*stats.failures, *cards.failures, *sheets.failures]
    known = dict(refs)
    for row in stats.rows:
        known.setdefault(row.title, PersonRef(key=person_key(row.title), name=row.name))
    lines, articles = season_lines(stats, cards, sheets, refs, source)
    found, box_failures = boxes(wikitext, season=season, today=day, squad=known, source=source)
    moves, move_failures = transfers(wikitext, source)
    return MadridSeasonFacts(
        title=title, season=season, squad=tuple(squad), articles=tuple(articles),
        lines=tuple(lines), matches=tuple(b.match for b in found),
        goals=tuple(g for b in found for g in b.goals), transfers=tuple(moves),
        stamps=stamps(wikitext, revision, revised),
        failures=tuple(failures + box_failures + move_failures), sources=(source,),
        warning=None)


# ------------------------------------------------------------------ the service


class MadridSeason:
    """The season article's facts, read through the MediaWiki API and kept six hours.

    ``facts(day)`` makes, when its six hours have run out, one ``action=parse`` request and
    one revision-time request; ``check(day)`` makes one ``rvprop=ids`` request and, when the
    article has a revision newer than the one the kept facts were read from, has the next
    ``facts`` read it (the catalogue calls it every 30 minutes while a Madrid match finished
    in the last 24 hours, PLAN 3.4). A failed read serves the last facts read, with a
    warning.
    """

    TTL = 6 * 3600

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None,
                 clock=lambda: datetime.now(UTC)) -> None:
        self.cache = FeedCache(8)
        self._transport = transport
        self._clock = clock
        self._read: dict[int, int | None] = {}        # season -> revision the facts read
        self._generation: dict[int, int] = {}
        self._last: dict[int, MadridSeasonFacts] = {}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=AGENT, timeout=12, transport=self._transport)

    async def _fetch(self, day: date, title: str) -> MadridSeasonFacts:
        async with self._client() as client:
            html = revid = None
            try:
                response = await client.get(API, params=_parse_params(title))
                response.raise_for_status()
                wikitext, html, revid = _parsed(response.json())
            except (httpx.HTTPError, ValueError, FeedError):
                # api.php turned the request away: the wikitext alone, as positions() does.
                response = await client.get(RAW, params={"title": title, "action": "raw"})
                response.raise_for_status()
                wikitext = response.text
            revised = None
            if revid is not None:
                try:
                    stamp = await client.get(API, params=stamp_params(revid))
                    stamp.raise_for_status()
                    revised = revision_time(stamp.json(), revid)
                except (httpx.HTTPError, ValueError):
                    revised = None
        if not templates(wikitext, "Efs start") and not templates(wikitext, *_BOXES):
            raise FeedError("Wikipedia’s season article couldn’t be read.")
        checked = self._clock().astimezone(UTC).isoformat()
        return read_article(wikitext, html, day=day, checked=checked, revision=revid,
                            revised=revised)

    async def facts(self, day: date) -> MadridSeasonFacts:
        """The facts of ``day``'s season article. ``day`` picks the season and is the reading
        day a box's result may not be dated after; it is not an "as of" filter. Facts before
        a date (R9) are the derivations' (``derive.py``, the builder), which take ``before``."""
        assert_may_host(PROVIDER)
        _, title, _ = article_for(day)
        year = season_start(day)

        async def fetch() -> list:
            facts = await self._fetch(day, title)
            self._read[year] = facts.stamps.revision
            self._last[year] = facts
            return [facts]

        key = f"madrid/{year}/{self._generation.get(year, 0)}"
        try:
            snap = await self.cache.get(key, self.TTL, fetch)
        except FeedError as error:
            if year in self._last:
                return replace(self._last[year], warning=str(error))
            raise
        return replace(snap.rows[0], warning=snap.warning)

    async def check(self, day: date) -> int | None:
        """The article's newest revision id, or ``None`` where it cannot be read. When it is
        not the revision the kept facts were read from, the next ``facts`` reads it."""
        assert_may_host(PROVIDER)
        _, title, _ = article_for(day)
        year = season_start(day)
        query = {"action": "query", "prop": "revisions", "titles": title, "rvprop": "ids",
                 "rvlimit": "1", "redirects": "1", "format": "json", "formatversion": "2",
                 "maxlag": MAXLAG}
        try:
            async with self._client() as client:
                response = await client.get(API, params=query)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return None
        revid = _newest(payload)
        if revid is not None and year in self._read and self._read[year] != revid:
            self._generation[year] = self._generation.get(year, 0) + 1
            self._read.pop(year)
        return revid


def _newest(payload: object) -> int | None:
    query = payload.get("query") if isinstance(payload, dict) else None
    pages = query.get("pages") if isinstance(query, dict) else None
    for page in pages if isinstance(pages, list) else []:
        for revision in (page.get("revisions") or []) if isinstance(page, dict) else []:
            revid = revision.get("revid") if isinstance(revision, dict) else None
            if isinstance(revid, int) and not isinstance(revid, bool):
                return revid
    return None


def _parse_params(title: str) -> dict[str, str]:
    return {"action": "parse", "page": title, "prop": "text|wikitext|revid", "redirects": "1",
            "format": "json", "formatversion": "2", "maxlag": MAXLAG}


def _parsed(payload: object) -> tuple[str, str | None, int | None]:
    parsed = payload.get("parse") if isinstance(payload, dict) else None
    if not isinstance(parsed, dict):
        raise FeedError("Wikipedia’s season article couldn’t be read.")
    wikitext, text = parsed.get("wikitext"), parsed.get("text")
    if isinstance(wikitext, dict):
        wikitext = wikitext.get("*")
    if isinstance(text, dict):
        text = text.get("*")
    if not isinstance(wikitext, str) or not wikitext:
        raise FeedError("Wikipedia’s season article couldn’t be read.")
    revid = parsed.get("revid")
    return (wikitext, text if isinstance(text, str) and text else None,
            revid if isinstance(revid, int) and not isinstance(revid, bool) else None)


async def gather_limited(jobs: Iterable, limit: int = 4) -> list:
    """Run ``jobs`` (coroutines) at most ``limit`` at a time, in order (the raw fallbacks)."""
    gate = asyncio.Semaphore(limit)

    async def gated(job):
        async with gate:
            return await job

    return list(await asyncio.gather(*map(gated, jobs)))
