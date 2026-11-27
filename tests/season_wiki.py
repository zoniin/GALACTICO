"""Synthetic Wikipedia and Wikidata replies for the season data layer, built in code.

R7: these are builders, never recordings. They write the templates and tables of a club's
season article the way its editors write them, and the MediaWiki and Wikidata API replies the
data layer reads them through (B13: ``action=parse``, revision queries, ``pageprops``,
``wbgetentities``). Every player, club, date and number is invented; the squad is
``season_v4.SQUAD``, so a test can join the two sources' invented players.

The article's own conventions are kept, because the parsers must survive them:

- ``{{Efs player2|no=|pos=|nat=|name=|a1|g1|a2|g2|a3|g3|a4|g4}}`` under ``{{Efs start}}``, with
  the stamp ``{{Fb cs footer|u=<day>}}``;
- ``{{Fb disc player 3|p=|nb=|n=|pos=|yc1=|syc1=|rc1=|…|rc4=}}``, whose shirt number ``n`` may be
  wrong (REC 1.4.3: join by the article link, never by the number);
- the Goals and the Clean sheets tables, which share one header, tied rows under ``rowspan``;
- ``{{footballbox collapsible}}`` with ``{{goal|min}}``, ``{{goal|min|pen.}}``,
  ``{{goal|min|o.g.}}``, ``90+2`` and several goals in one template (``{{goal|37||63|pen.}}``),
  and the kick-off as ``{{UTZ|21:30|2}}``;
- the transfer tables, with dates and types under ``rowspan`` and the editors' ``||`` row starts;
- ``{{Updated|<day>}}``.

Malformed rows are a parameter, not a separate builder: pass a string where a count goes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from urllib.parse import quote

from season_v4 import SQUAD, Player

__all__ = [
    "TITLE", "PAGEID", "COMPETITIONS", "CENTIMETRE", "METRE", "long_day", "link", "player_link",
    "updated", "efs_start", "efs_player2", "cs_footer", "squad_statistics", "ranked_table",
    "disc_header", "disc_player", "disc_footer", "goal", "scorer", "footballbox",
    "Move", "transfers_in", "transfers_out", "renewals", "article", "squad_html",
    "parse_reply", "revision_stamp", "revision_list", "revision_contents", "snapshot",
    "infobox", "articles_reply", "pageprops_reply", "height", "birthplace",
    "entities_claims", "entities_labels", "RATE_LIMITED", "maxlag_reply", "Box",
    "SAMPLE_BOXES", "sample_article",
]

TITLE = "2026–27 Real Madrid CF season"
PAGEID = 99000001
COMPETITIONS = ("La Liga", "Copa del Rey", "Champions League", "Supercopa de España")
"""The statistics templates' four competitions, in their column order."""
CENTIMETRE = "http://www.wikidata.org/entity/Q174728"
METRE = "http://www.wikidata.org/entity/Q11573"
_STATS = "https://stats.example.invalid/season"
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December")


def long_day(day: date | str) -> str:
    """"24 November 2026": how the article writes a day."""
    when = day if isinstance(day, date) else date.fromisoformat(day)
    return f"{when.day} {_MONTHS[when.month - 1]} {when.year}"


def link(title: str, text: str | None = None) -> str:
    """A wikilink. ``title`` may use underscores, as an HTML link does; the wikitext writes
    spaces."""
    target = title.replace("_", " ")
    return f"[[{target}]]" if text in (None, target) else f"[[{target}|{text}]]"


def player_link(player: Player, text: str | None = None) -> str:
    return link(player.wp_title, text if text is not None else player.wp_name)


def updated(day: date | str) -> str:
    return f"{{{{Updated|{long_day(day)}}}}}"


# ------------------------------------------------------------------ squad statistics


def efs_start() -> str:
    return ("{{Efs start|[[2026–27 La Liga|La Liga]]|[[2026–27 Copa del Rey|Copa del Rey]]"
            "|[[2026–27 UEFA Champions League|Champions League]]"
            "|[[2027 Supercopa de España|Supercopa de España]]}}")


def efs_player2(player: Player, counts: Sequence[tuple[int | str, int | str]], *,
                shirt: int | str | None = None) -> str:
    """One row: appearances and goals in each of the four competitions, in order. A string in
    place of a number writes a malformed row."""
    if len(counts) != 4:
        raise ValueError("four competitions, four (appearances, goals) pairs")
    number = player.shirt if shirt is None else shirt
    cells = "|".join(f"{a}|{g}" for a, g in counts)
    return (f"{{{{Efs player2|no={number!s:<2}|pos={player.group}|nat={player.nation}"
            f"|name={player_link(player)} |{cells}}}}}")


def cs_footer(day: date | str) -> str:
    """The statistics table's stamp: the day its counts run to."""
    return f"{{{{Fb cs footer|u={long_day(day)}|s=[{_STATS} Statistics]|date=August 2026}}}}"


def squad_statistics(rows: Sequence[str], day: date | str) -> str:
    """The Squad statistics section: start, rows (``efs_player2``), stamp."""
    return "\n".join(["===Squad statistics===", efs_start(), *rows, cs_footer(day)])


def ranked_table(rows: Sequence[tuple[Player, Sequence[int | str]]], *,
                 own_goals: Sequence[int] | None = None) -> str:
    """The Goals or the Clean sheets table: one row per player with four competition counts,
    ranked by the total, tied players under one ``rowspan`` rank and total (as editors write
    them). ``own_goals`` adds the Goals table's own-goal row."""
    lines = ['{| class="wikitable" style="text-align:center;"', "|-", "!Rank", "!Player",
             "!width=14.5%|La Liga", '!width=14.5%|<abbr title="Copa del Rey">CdR</abbr>',
             '!width=14.5%|<abbr title="UEFA Champions League">UCL</abbr>', "!Supercopa",
             "!Total"]

    def total(counts: Sequence[int | str]) -> int | str:
        return sum(counts) if all(isinstance(c, int) for c in counts) else "?"

    groups: list[list[tuple[Player, Sequence[int | str]]]] = []
    for row in rows:
        if groups and total(groups[-1][0][1]) == total(row[1]):
            groups[-1].append(row)
        else:
            groups.append([row])
    position = 1
    for group in groups:
        for n, (player, counts) in enumerate(group):
            lines.append("|-")
            cells = "||".join(str(c) for c in counts)
            person = f"{{{{flagicon|{player.nation}}}}} {player_link(player)}"
            if n == 0:
                span = f"rowspan={len(group)}|" if len(group) > 1 else ""
                lines.append(f"|{span}{position}")
                lines.append(f"|align=left|{person}||{cells}||{span}'''{total(counts)}'''")
            else:
                lines.append(f"|align=left|{person}||{cells}")
        position += len(group)
    if own_goals is not None:
        lines += ["|-", "|align=center colspan=2|''Own goals''||"
                  + "||".join(str(c) for c in own_goals) + f"||'''{sum(own_goals)}'''"]
    lines += ["|}", f"{{{{small|Source: [{_STATS} Statistics]}}}}"]
    return "\n".join(lines)


def disc_header() -> str:
    return ('{{fb disc header 3|c1=La Liga|c2=<abbr title="Copa del Rey">CdR</abbr>'
            '|c3=<abbr title="UEFA Champions League">UCL</abbr>|c4=Supercopa}}')


def disc_player(player: Player, cards: Sequence[tuple[int | str, int | str, int | str]], *,
                shirt: int | None = None) -> str:
    """One disciplinary row: (yellow, second yellow, red) in each competition. ``shirt``
    writes another player's number in ``n``, as an editor once did."""
    if len(cards) != 4:
        raise ValueError("four competitions, four (yellow, second yellow, red) triples")
    number = player.shirt if shirt is None else shirt
    cells = "".join(f"|yc{i}={y} |syc{i}={s} |rc{i}={r} "
                    for i, (y, s, r) in enumerate(cards, start=1))
    return (f"{{{{Fb disc player 3|p={player_link(player):<24}|nb={player.nation}"
            f"|n={number!s:<2}|pos={player.group}{cells.rstrip()}}}}}")


def disc_footer(day: date | str) -> str:
    return f"{{{{Fb disc footer 3|s=[{_STATS} Statistics]|u={long_day(day)}|date=August 2026}}}}"


# ------------------------------------------------------------------ match boxes


def goal(*events: tuple[int | str, str | None]) -> str:
    """``{{goal|…}}`` for one scorer's goals: (minute, note) pairs, a minute such as 90 or
    "90+2", a note "pen.", "o.g." or ``None``. Two goals, the second a penalty, are
    ``{{goal|37||63|pen.}}``."""
    parts: list[str] = []
    for minute, note in events:
        parts += [str(minute), note or ""]
    while parts and parts[-1] == "":
        parts.pop()
    return "{{goal|" + "|".join(parts) + "}}"


def scorer(who: Player | tuple[str, str], *events: tuple[int | str, str | None]) -> str:
    """A scorer's line of a box: his link (shown by surname, as editors write it) and goals.
    ``who`` is a squad player or (article title, shown name) for anyone else."""
    title, text = ((who.wp_title, who.wp_name.split()[-1]) if isinstance(who, Player)
                   else who)
    return f"{link(title, text)} {goal(*events)}"


def _goals(lines: Sequence[str]) -> str:
    if not lines:
        return ""
    if len(lines) == 1:
        return f" {lines[0]}"
    return "\n" + "\n".join(f"*{line}" for line in lines)


def footballbox(*, round: str, day: date | str, time: str | None, team1: str, team2: str,
                score: str | None = None, goals1: Sequence[str] = (),
                goals2: Sequence[str] = (), stadium: str | None = None,
                location: str | None = None, attendance: int | str | None = None,
                referee: str | None = None, result: str | None = None,
                report: str | None = None) -> str:
    """One ``{{footballbox collapsible}}``. ``time`` is local "21:30", written with the UTC
    offset as ``{{UTZ|21:30|2}}`` (the offset of Europe/Madrid on ``day``). ``score`` is
    "2–3" (an en dash), empty before the match. ``attendance`` an int is written with a
    thousands comma."""
    when = day if isinstance(day, date) else date.fromisoformat(day)
    offset = 2 if _summer(when) else 1
    crowd = f"{attendance:,}" if isinstance(attendance, int) else (attendance or "")
    fields = [
        ("round", round), ("date", long_day(when)),
        ("time", f"{{{{UTZ|{time}|{offset}}}}}" if time else ""),
        ("team1", team1), ("score", score or ""), ("report", report or ""), ("team2", team2),
        ("goals1", None), ("goals2", None), ("stadium", stadium or ""),
        ("location", location or ""), ("attendance", crowd), ("referee", referee or ""),
        ("result", result or ""),
    ]
    lines = ["{{footballbox collapsible"]
    for name, value in fields:
        if name in ("goals1", "goals2"):
            lines.append(f"|{name:<11}={_goals(goals1 if name == 'goals1' else goals2)}")
        else:
            lines.append(f"|{name:<11}= {value}".rstrip())
    lines.append("}}")
    return "\n".join(lines)


def _summer(day: date) -> bool:
    """Central European Summer Time: from the last Sunday of March to the last Sunday of
    October (the change days counted as summer; no box kicks off at 01:00)."""
    def last_sunday(month: int) -> date:
        end = date(day.year, month, 31)
        return date.fromordinal(end.toordinal() - (end.weekday() + 1) % 7)
    return last_sunday(3) <= day < last_sunday(10)


# ------------------------------------------------------------------ transfers


@dataclass(frozen=True)
class Move:
    day: str                       # ISO
    pos: str
    player: tuple[str, str] | Player  # (article title, name) or a squad player
    club: tuple[str, str] | None   # (article title, name); None for a renewal
    kind: str                      # "Transfer", "Free transfer", "End of loan", ...
    nation: str = "ESP"


def _who(move: Move) -> str:
    if isinstance(move.player, Player):
        return f"{{{{flagicon|{move.player.nation}}}}} {player_link(move.player)}"
    return f"{{{{flagicon|{move.nation}}}}} {link(*move.player)}"


def _ref(n: int) -> str:
    return (f'align="center" | <ref>{{{{cite press release|title=Announcement {n}'
            f'|url=https://club.example.invalid/news/{n}|publisher=Test Club}}}}</ref>')


def _moves_table(moves: Sequence[Move], club_header: str, *, lead: str) -> str:
    """A transfers table with the editors' ``rowspan`` for a run of one day and of one type.
    A row under a spanned cell starts with ``lead`` (``"||"`` or ``"|"``): both occur."""
    lines = ['{| class="wikitable"', "|-", "!Date", "!{{Abbr|Pos.|Position}}", "!Player",
             f"!{club_header}", "!Type", "!{{abbr|Ref.|Reference}}"]
    day_left = kind_left = 0
    for n, move in enumerate(moves):
        cells: list[str] = []
        dated = day_left == 0
        if dated:
            run = 1
            while n + run < len(moves) and moves[n + run].day == move.day:
                run += 1
            day_left = run
            span = f"rowspan={run} | " if run > 1 else ""
            cells.append(f"{span}{long_day(move.day)}")
        cells += [move.pos, _who(move), link(*move.club) if move.club else ""]
        if kind_left == 0:
            run = 1
            while n + run < len(moves) and moves[n + run].kind == move.kind:
                run += 1
            kind_left = run
            span = f"rowspan={run} | " if run > 1 else ""
            cells.append(f"{span}{move.kind}")
        cells.append(_ref(n + 1))
        lines += ["|-", f"{'|' if dated else lead} " + " || ".join(cells)]
        day_left -= 1
        kind_left -= 1
    lines.append("|}")
    return "\n".join(lines)


def transfers_in(moves: Sequence[Move]) -> str:
    return "===In===\n" + _moves_table(moves, "From", lead="||")


def transfers_out(moves: Sequence[Move]) -> str:
    return "===Out===\n" + _moves_table(moves, "To", lead="|")


def renewals(rows: Sequence[tuple[str, Player, str, str]]) -> str:
    """Contract renewals: (ISO day, player, contract length, contract ends)."""
    lines = ["===Contract renewals===", '{| class="wikitable"', "|-", "!Date",
             "!{{Abbr|Pos.|Position}}", "!Player", "!Contract length", "!Contract ends",
             "!{{abbr|Ref.|Reference}}"]
    for n, (day, player, length, ends) in enumerate(rows, start=1):
        lines += ["|-", f"| {long_day(day)} || {player.group} || "
                  f"{{{{flagicon|{player.nation}}}}} {player_link(player)} || {length} || "
                  f"{ends} || {_ref(100 + n)}"]
    lines.append("|}")
    return "\n".join(lines)


# ------------------------------------------------------------------ the article


def article(*, transfers: Sequence[str] = (), league: Sequence[str] = (),
            cup: Sequence[str] = (), supercup: Sequence[str] = (),
            europe: Sequence[str] = (), statistics: str = "", goals: str = "",
            clean_sheets: str = "", discipline: Sequence[str] = (),
            day: date | str = "2026-11-24") -> str:
    """A season article's wikitext, its sections in the article's order. Each argument is the
    output of the builders above; an empty one leaves its section empty."""
    stamp = updated(day)
    parts = [
        "{{Infobox football club season\n|club = [[Real Madrid CF|Real Madrid]]\n"
        "|season = [[2026–27 La Liga|2026–27]]\n}}",
        "The '''2026–27 season''' is an invented season written for tests.",
        "==Players==", "{{:Real Madrid CF}}",
        "==Transfers==", *transfers,
        "==Competitions==", "===La Liga===", "====Matches====", *league,
        "===Copa del Rey===", *cup,
        "===Supercopa de España===", *supercup,
        "===UEFA Champions League===", "====League phase====", *europe,
        "==Statistics==", statistics,
        "===Goals===", stamp, goals,
        "===Clean sheets===", stamp, clean_sheets,
        "===Disciplinary record===", *discipline,
        "==References==", "{{Reflist}}",
    ]
    return "\n".join(part for part in parts if part != "") + "\n"


def squad_html(players: Sequence[Player] = SQUAD) -> str:
    """The transcluded squad list as ``action=parse`` renders it: one ``wikitable`` whose
    header is No., Pos., Nation, Player, each player linked to his article. A player without
    a shirt or a group (not on the list) is left out, as the list leaves him out. A link's
    path is percent-encoded, as the parser writes it. No flag and no image."""
    head = "".join(f"<th>{h}</th>" for h in ("No.", "Pos.", "Nation", "Player"))
    rows = "".join(
        f'<tr><td>{p.shirt}</td><td>{p.group}</td><td>{p.nation}</td>'
        f'<td><a href="/wiki/{quote(p.wp_title, safe="(),_")}" '
        f'title="{p.wp_title.replace("_", " ")}">{p.wp_name}</a></td></tr>'
        for p in players if p.shirt is not None and p.group is not None and p.wp_title)
    return (f'<div class="mw-content-ltr mw-parser-output" lang="en" dir="ltr">'
            f'<h2 id="Players">Players</h2><table class="wikitable"><tbody><tr>{head}</tr>'
            f"{rows}</tbody></table></div>")


# ------------------------------------------------------------------ MediaWiki replies


def parse_reply(wikitext: str, html: str, *, revid: int = 1000020, title: str = TITLE,
                pageid: int = PAGEID) -> dict:
    """``action=parse&prop=text|wikitext|revid&format=json&formatversion=2``."""
    return {"parse": {"title": title, "pageid": pageid, "revid": revid, "text": html,
                      "wikitext": wikitext}}


def revision_stamp(revid: int, timestamp: str, *, parentid: int | None = None,
                   title: str = TITLE, pageid: int = PAGEID) -> dict:
    """``prop=revisions&rvprop=timestamp|ids``: the latest revision's id and time."""
    return {"batchcomplete": True, "query": {"pages": [{
        "pageid": pageid, "ns": 0, "title": title,
        "revisions": [{"revid": revid, "parentid": parentid or revid - 1,
                       "timestamp": timestamp}]}]}}


def revision_list(revisions: Sequence[tuple[int, str]], *, title: str = TITLE,
                  pageid: int = PAGEID, more: str | None = None) -> dict:
    """``prop=revisions&rvprop=ids|timestamp|size|comment&rvlimit=``: newest first, as the API
    lists them. ``more`` is the ``rvcontinue`` of a list with further pages."""
    ordered = sorted(revisions, key=lambda r: r[0], reverse=True)
    listed = [{"revid": revid, "parentid": ordered[n + 1][0] if n + 1 < len(ordered) else 0,
               "timestamp": stamp, "size": 50000 + n, "comment": "/* Statistics */"}
              for n, (revid, stamp) in enumerate(ordered)]
    reply: dict = {"query": {"pages": [{"pageid": pageid, "ns": 0, "title": title,
                                        "revisions": listed}]}}
    if more is not None:
        reply = {"continue": {"rvcontinue": more, "continue": "||"}, **reply}
    else:
        reply = {"batchcomplete": True, **reply}
    return reply


def revision_contents(revisions: Sequence[tuple[int, str, str]], *, title: str = TITLE,
                      pageid: int = PAGEID) -> dict:
    """``prop=revisions&revids=…&rvprop=ids|timestamp|content&rvslots=main``: (revid,
    timestamp, wikitext) each, oldest first as the API returns them for ``revids``."""
    listed = [{"revid": revid, "parentid": revid - 1, "timestamp": stamp,
               "slots": {"main": {"contentmodel": "wikitext", "contentformat": "text/x-wiki",
                                  "content": content}}}
              for revid, stamp, content in sorted(revisions)]
    return {"batchcomplete": True, "query": {"pages": [{"pageid": pageid, "ns": 0,
                                                        "title": title,
                                                        "revisions": listed}]}}


def snapshot(rows: Sequence[str], day: date | str) -> str:
    """A revision's content cut to what the revision rules read: the statistics section with
    its stamp, inside an article."""
    return article(statistics=squad_statistics(rows, day), day=day)


RATE_LIMITED = ("You are making too many requests to the API.\n"
                "Please slow down and try again later.\n")
"""The plain-text body MediaWiki sends with a 429 (the API turns a client away)."""


def maxlag_reply(lag: int = 6) -> dict:
    """The reply to a request whose ``maxlag`` the servers exceed (sent with Retry-After)."""
    return {"error": {"code": "maxlag", "info": f"Waiting for a database server: {lag} "
                      "seconds lagged.", "host": "db.example.invalid", "lag": lag,
                      "type": "db"}}


# ------------------------------------------------------------------ players' articles


def infobox(*, name: str, position: str | None, born: tuple[int, int, int] | None,
            clubs: Sequence[tuple[str, str, int | str | None, int | str | None]] = (),
            national: Sequence[tuple[str, str, int | str | None, int | str | None]] = (),
            club_update: str | None = None, nationalteam_update: str | None = None,
            birth_place: str | None = None) -> str:
    """A player's ``{{Infobox football biography}}``. ``position`` as the editors write it,
    links and all ("[[Winger (association football)|Winger]], [[Forward]]"). ``clubs`` and
    ``national`` are (years, team link, caps, goals) in order; a caps value ``None`` is a
    blank field. No image: the site uses none."""
    lines = ["{{Infobox football biography", f"| name = {name}"]
    if born is not None:
        lines.append(f"| birth_date = {{{{birth date and age|{born[0]}|{born[1]}|{born[2]}"
                     "|df=y}}")
    if birth_place is not None:
        lines.append(f"| birth_place = {birth_place}")
    if position is not None:
        lines.append(f"| position = {position}")
    lines.append("| currentclub = [[Real Madrid CF|Real Madrid]]")
    for n, (years, club, caps, goals_) in enumerate(clubs, start=1):
        lines.append(f"| years{n} = {years} | clubs{n} = {club} | caps{n} = "
                     f"{'' if caps is None else caps} | goals{n} = "
                     f"{'' if goals_ is None else goals_}")
    for n, (years, team, caps, goals_) in enumerate(national, start=1):
        lines.append(f"| nationalyears{n} = {years} | nationalteam{n} = {team}"
                     f" | nationalcaps{n} = {'' if caps is None else caps}"
                     f" | nationalgoals{n} = {'' if goals_ is None else goals_}")
    if club_update is not None:
        lines.append(f"| club-update = {club_update}")
    if nationalteam_update is not None:
        lines.append(f"| nationalteam-update = {nationalteam_update}")
    lines.append("}}")
    return "\n".join(lines) + "\n'''" + name + "''' is an invented footballer.\n"


def articles_reply(articles: Mapping[str, str | None], *,
                   normalized: Sequence[tuple[str, str]] = (),
                   redirects: Sequence[tuple[str, str]] = ()) -> dict:
    """The batched ``prop=revisions&rvprop=content&rvslots=main&redirects=1`` reply
    ``Studio.positions`` reads. ``None`` content is a missing article."""
    pages = []
    for n, (title, content) in enumerate(articles.items(), start=1):
        if content is None:
            pages.append({"ns": 0, "title": title, "missing": True})
            continue
        pages.append({"pageid": PAGEID + n, "ns": 0, "title": title, "revisions": [
            {"slots": {"main": {"contentmodel": "wikitext", "contentformat": "text/x-wiki",
                                "content": content}}}]})
    query: dict = {}
    if normalized:
        query["normalized"] = [{"fromencoded": False, "from": a, "to": b} for a, b in normalized]
    if redirects:
        query["redirects"] = [{"from": a, "to": b} for a, b in redirects]
    query["pages"] = pages
    return {"batchcomplete": True, "query": query}


# ------------------------------------------------------------------ Wikidata


def pageprops_reply(items: Mapping[str, str | None], *,
                    normalized: Sequence[tuple[str, str]] = ()) -> dict:
    """``prop=pageprops&ppprop=wikibase_item``: each title's QID; ``None`` is an article with
    no item, and a title starting "Missing" is a missing article."""
    pages = []
    for n, (title, qid) in enumerate(items.items(), start=1):
        if title.startswith("Missing"):
            pages.append({"ns": 0, "title": title, "missing": True})
        elif qid is None:
            pages.append({"pageid": PAGEID + 100 + n, "ns": 0, "title": title})
        else:
            pages.append({"pageid": PAGEID + 100 + n, "ns": 0, "title": title,
                          "pageprops": {"wikibase_item": qid}})
    query: dict = {}
    if normalized:
        query["normalized"] = [{"fromencoded": False, "from": a, "to": b} for a, b in normalized]
    query["pages"] = pages
    return {"batchcomplete": True, "query": query}


def height(amount: str, unit: str = CENTIMETRE, *, rank: str = "normal") -> dict:
    """A P2048 statement: ``amount`` as Wikidata writes it ("+183", "+1.91")."""
    return {"mainsnak": {"snaktype": "value", "property": "P2048", "datatype": "quantity",
                         "datavalue": {"value": {"amount": amount, "unit": unit},
                                       "type": "quantity"}},
            "type": "statement", "rank": rank}


def birthplace(qid: str, *, rank: str = "normal") -> dict:
    """A P19 statement naming the item ``qid``."""
    return {"mainsnak": {"snaktype": "value", "property": "P19", "datatype": "wikibase-item",
                         "datavalue": {"value": {"entity-type": "item",
                                                 "numeric-id": int(qid[1:]), "id": qid},
                                       "type": "wikibase-entityid"}},
            "type": "statement", "rank": rank}


def entities_claims(entities: Mapping[str, Mapping[str, Sequence[dict]] | None]) -> dict:
    """``wbgetentities&props=claims``: each QID's statements by property; ``None`` is a
    missing item."""
    found: dict = {}
    for qid, claims in entities.items():
        if claims is None:
            found[qid] = {"id": qid, "missing": ""}
        else:
            found[qid] = {"type": "item", "id": qid,
                          "claims": {prop: list(st) for prop, st in claims.items()}}
    return {"entities": found, "success": 1}


def entities_labels(labels: Mapping[str, str | None]) -> dict:
    """``wbgetentities&props=labels&languages=en``: each QID's English label; ``None`` is an
    item with no English label."""
    return {"entities": {qid: {"type": "item", "id": qid, "labels": (
        {} if label is None else {"en": {"language": "en", "value": label}})}
        for qid, label in labels.items()}, "success": 1}


# ------------------------------------------------------------------ a sample season


@dataclass(frozen=True)
class Box:
    """A sample match box and what it says, so a test can compare a parse with its source."""

    competition: str     # one of COMPETITIONS
    day: str
    text: str


def _by(name: str) -> Player:
    return next(p for p in SQUAD if p.name == name)


_ROMA_ONE = ("Test_Roma_Uno", "Uno")
_ROMA_TWO = ("Test_Roma_Dos", "Dos")
_A_ONE = ("A_FC_Striker", "Striker")


def _sample_boxes() -> tuple[Box, ...]:
    kai, ala, punta = _by("Kai Delantero"), _by("Vinicio Ala"), _by("Carlos Punta")
    nico, hugo = _by("Nico Enlace"), _by("Hugo Central")
    return (
        Box("La Liga", "2026-08-22", footballbox(
            round="1", day="2026-08-22", time="21:00", team1="Real Madrid",
            team2="[[A FC]]", score="3–1",
            goals1=[scorer(kai, (12, "pen."), (55, None)), scorer(ala, ("90+2", None))],
            goals2=[scorer(_A_ONE, (70, None))], stadium="[[Estadio Invento]]",
            location="[[Madrid]]", attendance=70123, referee="[[Iván Silbato]]", result="W",
            report="https://league.example.invalid/match/100001")),
        Box("La Liga", "2026-08-29", footballbox(
            round="2", day="2026-08-29", time="21:30", team1="[[Ribera UD|Ribera]]",
            team2="Real Madrid", score="1–2", goals1=[scorer(hugo, (30, "o.g."))],
            goals2=[scorer(kai, (40, None)), scorer(punta, ("90+2", None))],
            stadium="[[Campo de Ribera]]", location="[[Ribera]]", attendance="",
            referee="[[Iván Silbato]]", result="W")),
        Box("Champions League", "2026-09-16", footballbox(
            round="League phase<br>Matchday 1", day="2026-09-16", time="21:00",
            team1="{{fbaicon|ESP}} Real Madrid", team2="{{fbaicon|ITA}} [[Test Roma]]",
            score="2–0", goals1=[scorer(kai, (8, None)), scorer(nico, (77, None))],
            stadium="[[Estadio Invento]]", location="[[Madrid]]", attendance=69000,
            result="W")),
        Box("Copa del Rey", "2026-10-28", footballbox(
            round="First round", day="2026-10-28", time="19:00",
            team1="[[Atlético Prueba]]", team2="Real Madrid", score="0–4",
            goals2=[scorer(kai, (5, None), (37, None), (63, "pen.")),
                    scorer(("Atletico_Prueba_Defensa", "Defensa"), (81, "o.g."))],
            stadium="Campo Municipal de Prueba", location="Prueba", attendance=4000,
            result="W")),
        Box("Champions League", "2026-11-24", footballbox(
            round="League phase<br>Matchday 2", day="2026-11-24", time="21:00",
            team1="{{fbaicon|ITA}} [[Test Roma]]", team2="{{fbaicon|ESP}} Real Madrid",
            score="1–3", goals1=[scorer(_ROMA_ONE, (20, None))],
            goals2=[scorer(kai, (25, None)), scorer(nico, (51, None)),
                    scorer(_ROMA_TWO, (88, "o.g."))],
            stadium="[[Stadio di Prova]]", location="[[Roma]]", attendance=60500,
            referee="[[Lars Pfeife]]", result="W")),
        Box("La Liga", "2026-11-28", footballbox(
            round="4", day="2026-11-28", time="21:00", team1="Real Madrid",
            team2="[[Norte CF|Norte]]", stadium="[[Estadio Invento]]",
            location="[[Madrid]]")),
        Box("Supercopa de España", "2027-01-08", footballbox(
            round="Semi-final", day="2027-01-08", time="20:00", team1="Real Madrid",
            team2="[[Norte CF|Norte]]", stadium="[[Estadio Neutral]]",
            location="[[Testland]]")),
    )


SAMPLE_BOXES: tuple[Box, ...] = _sample_boxes()


def sample_article() -> str:
    """A whole invented season article: transfers, every box of ``SAMPLE_BOXES``, the
    statistics, goals, clean sheets and disciplinary tables, consistent with each other and
    with ``season_v4.sample_world``'s Madrid results."""
    kai, ala, punta, nico = (_by("Kai Delantero"), _by("Vinicio Ala"), _by("Carlos Punta"),
                             _by("Nico Enlace"))
    keeper, second = _by("Inaki Portero"), _by("Bruno Guante")
    listed = [p for p in SQUAD if p.group is not None]
    goals_by = {kai.fd_id: (3, 3, 2, 0), ala.fd_id: (1, 0, 0, 0), punta.fd_id: (1, 0, 0, 0),
                nico.fd_id: (0, 0, 2, 0)}
    # Thirteen players appear in each match; the first-choice keeper sits out the cup tie and
    # the second plays it, so every match has 13 appearances.
    regulars = {"Inaki Portero", "Dario Lateral", "Hugo Central", "Tomas Muro", "Leon Zaga",
                "Rui Banda", "Pablo Medio", "Santi Pivote", "Nico Enlace", "Oscar Volante",
                "Vinicio Ala", "Kai Delantero", "Carlos Punta"}
    rows = []
    for p in listed:
        apps = (2, 1, 2, 0) if p.name in regulars else (0, 0, 0, 0)
        if p is keeper:
            apps = (2, 0, 2, 0)
        if p is second:
            apps = (0, 1, 0, 0)
        g = goals_by.get(p.fd_id, (0, 0, 0, 0))
        rows.append(efs_player2(p, list(zip(apps, g, strict=True))))
    scorers_rows = [(kai, (3, 3, 2, 0)), (nico, (0, 0, 2, 0)), (ala, (1, 0, 0, 0)),
                    (punta, (1, 0, 0, 0))]
    discipline = [
        disc_header(),
        disc_player(_by("Leon Zaga"), [(1, 0, 1), (0, 0, 0), (1, 0, 0), (0, 0, 0)]),
        disc_player(_by("Santi Pivote"), [(2, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)],
                    shirt=_by("Nico Enlace").shirt),
        disc_footer("2026-11-24"),
    ]
    moves_in = [
        Move("2026-07-01", "DF", _by("Rui Banda"), ("Test_Porto_FC", "Test Porto"),
             "Transfer"),
        Move("2026-07-01", "MF", _by("Joan Interior"), ("Ribera_UD", "Ribera"),
             "Free transfer"),
        Move("2026-07-01", "FW", _by("Carlos Punta"), ("Norte_CF", "Norte"), "End of loan"),
        Move("2026-08-06", "MF", _by("Kemal Olcu"), ("Nord_Kickers_1904", "Nord Kickers"),
             "Transfer"),
    ]
    moves_out = [
        Move("2026-06-26", "MF", ("Antiguo_Medio", "Antiguo Medio"), ("A_FC", "A FC"),
             "Mutual agreement"),
        Move("2026-07-01", "DF", ("Viejo_Muro", "Viejo Muro"), ("Test_City_FC", "Test City"),
             "End of contract"),
        Move("2026-07-01", "DF", ("Otro_Lateral", "Otro Lateral"), ("Norte_CF", "Norte"),
             "End of contract"),
    ]
    boxes = {name: [b.text for b in SAMPLE_BOXES if b.competition == name]
             for name in COMPETITIONS}
    return article(
        transfers=[transfers_in(moves_in), transfers_out(moves_out),
                   renewals([("2026-09-01", _by("Santi Pivote"), "2 years", "2029")])],
        league=boxes["La Liga"], cup=boxes["Copa del Rey"],
        supercup=boxes["Supercopa de España"], europe=boxes["Champions League"],
        statistics=squad_statistics(rows, "2026-11-24"),
        goals=ranked_table(scorers_rows, own_goals=(0, 1, 1, 0)),
        clean_sheets=ranked_table([(keeper, (0, 0, 1, 0)), (second, (0, 1, 0, 0))]),
        discipline=discipline, day="2026-11-24")
