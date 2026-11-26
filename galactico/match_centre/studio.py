"""Lineup: the current squad, the XI the server proposes by a declared key, the next match,
and dated archive samples of pitch events.

Claim. The proposed XI is chosen by one declared key and nothing else: in each position the
Wikipedia season article lists (goalkeeper, defender, midfielder, forward), the players with
the most appearances this season, a tie going to the lower shirt number. Within a position each
player stands on the side his Wikipedia article's position names (a left-back on the left, a
centre-back in the middle); where the article names no side, by shirt number, left to right.
A tie at the cut is named on the board. Every
sentence the page shows about a lineup is composed here (R10), from the squad list and the
lineup on the board; every number in one is a count the data gives (R8).

Non-claim. An appearance count is a count, not a judgement of a player (R1): the key says who
has played most this season, nothing about who would do well. The side comes from the first
position the player's article lists, read as written ("Left-back", "Centre-back"); it says
nothing about the role he takes in a match. When the articles can't be read, every place inside
a position follows the shirt number, and the key says so.

A lineup travels in its link: the formation and the eleven shirt numbers in the formation's
slot order (``share_query``), with the season they belong to. ``parse_share`` reads one back
and refuses a link that does not match the current squad.

The activity maps are archive samples: for each of a few current players, his last recorded
match in the public 2017/18 Wyscout data (Pappalardo et al.), labelled with the match, the
competition and the date that data gives. The drawn role area beside them is a drawing of the
formation's slot, not a measurement, and says so.

The hosted app ships this module and cannot import the copy guard (``galactico.domain``); the
tests run every sentence shape through ``scan_labels``.
"""

from __future__ import annotations

import asyncio
import re
from datetime import date
from itertools import permutations
from typing import NamedTuple
from urllib.parse import unquote, urlencode, urlsplit

import httpx
from bs4 import BeautifulSoup, Tag

from ..providers import assert_may_host
from . import goal_scout
from .answers import MADRID
from .feed import FeedCache, FeedError
from .freshness import day_label
from .openfootball import CREDITS, season_start
from .openligadb import EUROPE


class Sample(NamedTuple):
    """A curated link from a current player's article to one identified Wyscout match."""

    match_id: int
    player: int
    match: str
    competition: str
    day: str


# Each is the player's last recorded match in the public 2017/18 data (a start or a
# substitute's entry), with the match, the competition and the date as that data gives them;
# a test checks all three, and that it is his last, against the local corpus where it exists.
# Event locations and season totals are read from their sources at runtime.
SAMPLES = {
    "Kylian_Mbappé": Sample(2058017, 353833, "France v Croatia", "World Cup", "2018-07-15"),
    "Thibaut_Courtois": Sample(2058016, 3429, "Belgium v England", "World Cup", "2018-07-14"),
    "Federico_Valverde": Sample(2565911, 364005, "Deportivo La Coruña v Villarreal",
                                "La Liga", "2018-05-12"),
    "Trent_Alexander-Arnold": Sample(2057994, 346101, "England v Belgium", "World Cup",
                                     "2018-06-28"),
    "Antonio_Rüdiger": Sample(2057986, 14748, "Germany v Sweden", "World Cup", "2018-06-23"),
    "Bernardo_Silva": Sample(2058002, 265673, "Uruguay v Portugal", "World Cup", "2018-06-30"),
    "Ferland_Mendy": Sample(2501058, 276979, "Olympique Lyonnais v Nice", "Ligue 1",
                            "2018-05-19"),
}
MIRROR = ("https://raw.githubusercontent.com/koenvo/wyscout-soccer-match-event-dataset/"
          "ebc4c54c1093c420a81ce442c69e4186fab33bb4/processed-v2/files")
AGENT = {"User-Agent": "Galactico/1.0 (https://github.com/zoniin/GALACTICO)"}
ACTIONS = {1: "Duel", 3: "Set piece", 7: "Ball action", 8: "Pass", 9: "Save", 10: "Shot"}

GROUPS = ("GK", "DF", "MF", "FW")
"""The positions of the Wikipedia squad list, from the back."""
LINES = {"GK": "in goal", "DF": "in defence", "MF": "in midfield", "FW": "up front"}


def _slot(role: str, group: str, x: int, y: int) -> dict:
    return {"role": role, "group": group, "x": x, "y": y,
            "zone": f"Drawn area for the {role} role, not measured"}


_BACK_FOUR = (_slot("LB", "DF", 13, 68), _slot("LCB", "DF", 37, 71),
              _slot("RCB", "DF", 63, 71), _slot("RB", "DF", 87, 68))
_KEEPER = _slot("GK", "GK", 50, 88)
FORMATIONS: dict[str, tuple[dict, ...]] = {
    "4-3-3": (_slot("LW", "FW", 20, 19), _slot("ST", "FW", 50, 13), _slot("RW", "FW", 80, 19),
              _slot("LCM", "MF", 24, 42), _slot("DM", "MF", 50, 50), _slot("RCM", "MF", 76, 42),
              *_BACK_FOUR, _KEEPER),
    "4-2-3-1": (_slot("ST", "FW", 50, 12), _slot("LAM", "MF", 17, 31),
                _slot("AM", "MF", 50, 34), _slot("RAM", "MF", 83, 31),
                _slot("LDM", "MF", 33, 52), _slot("RDM", "MF", 67, 52), *_BACK_FOUR, _KEEPER),
    "4-4-2": (_slot("LS", "FW", 36, 16), _slot("RS", "FW", 64, 16), _slot("LM", "MF", 13, 42),
              _slot("LCM", "MF", 37, 47), _slot("RCM", "MF", 63, 47), _slot("RM", "MF", 87, 42),
              *_BACK_FOUR, _KEEPER),
    "3-5-2": (_slot("LS", "FW", 36, 15), _slot("RS", "FW", 64, 15), _slot("LWB", "MF", 12, 43),
              _slot("LCM", "MF", 32, 39), _slot("DM", "MF", 50, 54), _slot("RCM", "MF", 68, 39),
              _slot("RWB", "MF", 88, 43), _slot("LCB", "DF", 25, 71), _slot("CB", "DF", 50, 73),
              _slot("RCB", "DF", 75, 71), _KEEPER),
}
"""Each formation's eleven slots: the board's coordinates (the opponent's goal at the top), the
position of the squad list a slot takes its player from, and the caption of its drawn area."""
DEFAULT_FORMATION = "4-3-3"
ORDER = "By position, then shirt number."
"""The declared order of the squad list and of the substitutes."""

API = "https://en.wikipedia.org/w/api.php"
RAW = "https://en.wikipedia.org/w/index.php"
SIDES = ("L", "C", "R")
_CENTRAL = ("centre-back", "center-back", "central", "centre", "center", "defensive midfield",
            "attacking midfield", "striker", "sweeper", "playmaker")
_LINK = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]")
_NOISE = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>|\{\{[^{}]*\}\}|<[^>]+>|'{2,}")
_POSITION = re.compile(r"^\s*\|\s*positions?\s*=\s*(.+)$", re.MULTILINE)


def first_position(wikitext: str) -> str | None:
    """The first position an article's infobox lists, as written ("Left-back"), or ``None``."""
    found = _POSITION.search(wikitext)
    if found is None:
        return None
    text = _NOISE.sub(" ", _LINK.sub(r"\1", found[1]))
    first = re.split(r",|/|;|\band\b|\bor\b", text)[0].strip(" .\t")
    return first[:1].upper() + first[1:] if first else None


def side_of(position: str | None) -> str | None:
    """"L", "C" or "R" for a position its words place on a side; ``None`` where they don't
    ("Winger", "Forward", "Full-back")."""
    if not position:
        return None
    text = position.casefold()
    if text.startswith("left"):
        return "L"
    if text.startswith("right"):
        return "R"
    return "C" if any(word in text for word in _CENTRAL) else None


def depth_of(position: str | None) -> int | None:
    """0 for a position its words put further forward ("Attacking midfielder"), 2 for one
    they put deeper ("Defensive midfielder"), ``None`` otherwise."""
    text = (position or "").casefold()
    if "attacking" in text:
        return 0
    return 2 if "defensive" in text or "holding" in text else None


def parse_positions(payload: object) -> dict[str, str]:
    """The MediaWiki reply's articles: each requested title and the first position its infobox
    lists, following the reply's normalisations and redirects back to the title asked for."""
    query = payload.get("query") if isinstance(payload, dict) else None
    if not isinstance(query, dict):
        raise FeedError("The players' articles couldn't be read.")
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
        if isinstance(content, str) and (position := first_position(content)):
            found[back.get(page["title"], page["title"])] = position
    return found


_LASTMOD = re.compile(r"last edited on (\d{1,2}) (\w+) (\d{4})")
_MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August",
                "September", "October", "November", "December")


def revised_on(html: str) -> str | None:
    """The day the article was last edited, from its footer, as an ISO date; else ``None``."""
    found = _LASTMOD.search(html)
    if found is None or found[2] not in _MONTH_NAMES:
        return None
    return date(int(found[3]), _MONTH_NAMES.index(found[2]) + 1, int(found[1])).isoformat()


DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def long_day(iso: str) -> str:
    """"Sun 15 Jul 2018": the site's one way of writing a date, with its year."""
    value = date.fromisoformat(iso)
    return f"{DAYS[value.weekday()]} {value.day} {MONTHS[value.month - 1]} {value.year}"


def season_label(day: date) -> str:
    """"2026/27": the season chip's form."""
    year = season_start(day)
    return f"{year}/{(year + 1) % 100:02}"


def short_name(name: str) -> str:
    """The name a nameplate shows: the surname, or the whole of a two-part name the second
    part of which is not a surname (Vinícius Júnior)."""
    parts = name.split()
    if len(parts) == 2 and parts[1] in {"Júnior", "Junior", "Silva"}:
        return name
    return parts[-1] if parts else name


def _player(cell: Tag) -> tuple[str, str] | None:
    link = cell.select_one('a[title][href]')
    if link is None:
        return None
    path = unquote(urlsplit(str(link["href"])).path)
    slug = path.removeprefix("/wiki/").removeprefix("./")
    name = link.get_text(" ", strip=True)
    if not slug or not name or "/" in slug or ":" in slug:
        return None
    return slug, name


def parse_roster(html: str) -> list[dict]:
    """The current squad, in the declared order (``ORDER``), each with this season's
    appearances and goals in all competitions where the article lists them, else ``None``."""
    soup = BeautifulSoup(html, "html.parser")
    players: dict[str, dict] = {}
    totals = {}
    for table in soup.select("table.wikitable"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [c.get_text(" ", strip=True).strip(".").lower()
                   for c in rows[0].find_all("th", recursive=False)]
        roster = headers == ["no", "pos", "nation", "player"]
        stats = (headers[:5] == ["no", "pos", "nat", "player", "total"] and len(rows) > 1
                 and [c.get_text(strip=True) for c in rows[1].find_all("th")][:2]
                 == ["Apps", "Goals"])
        if not roster and not stats:
            continue
        for row in rows[1:]:
            cells = row.find_all("td", recursive=False)
            if len(cells) < 4 or not (identity := _player(cells[3])):
                continue
            slug, name = identity
            if stats and len(cells) >= 6:
                values = [c.get_text(strip=True) for c in cells[4:6]]
                totals[slug] = [int(v) if re.fullmatch(r"[0-9]+", v) else None for v in values]
            if roster:
                number = cells[0].get_text(strip=True)
                group = cells[1].get_text(strip=True)
                if group in GROUPS and number.isdecimal():
                    players[slug] = {"id": slug, "name": name, "short": short_name(name),
                                     "number": int(number), "group": group,
                                     "nation": cells[2].get_text(strip=True),
                                     "archive": slug in SAMPLES}
    if len(players) < 11:
        raise FeedError("The current squad list is unavailable.")
    for slug, player in players.items():
        player["apps"], player["goals"] = totals.get(slug, [None, None])
    return sorted(players.values(), key=lambda p: (GROUPS.index(p["group"]), p["number"]))


# ------------------------------------------------------------------ the proposed XI


def _most_appearances(player: dict) -> tuple:
    # Most appearances first; a player whose count the article leaves blank after every count;
    # then the lower shirt number. The name only makes the order total.
    apps = player["apps"]
    return (apps is None, -(apps or 0), player["number"], player["name"])


def _listing(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def key_line(season: str, sides: bool = True) -> str:
    """The key, as the board states it."""
    where = ("where his Wikipedia position puts him, else by shirt number" if sides
             else "left to right by shirt number")
    return f"Picked by most {season} appearances in each position; within a position, {where}"


def rule_line(season: str, sides: bool = True) -> str:
    """The whole rule, as "About these numbers" states it."""
    where = ("each player stands where the first position in his Wikipedia article puts him "
             "(a left-back on the left, a centre-back in the middle, an attacking midfielder "
             "in the more advanced places); where it says neither, the players stand left to "
             "right by shirt number" if sides else
             "the players stand left to right by shirt number: the players' articles couldn't "
             "be read just now, so no side is known")
    return (f"The proposed XI takes, in each position of the Wikipedia squad list (goalkeeper, "
            f"defender, midfielder, forward), the players with the most {season} appearances "
            f"in all competitions; a tie goes to the lower shirt number. Within a position "
            f"{where}.")


def _slot_side(slot: dict) -> int:
    return 0 if slot["x"] < 35 else 2 if slot["x"] > 65 else 1


def _place(slots: list[dict], group: list[dict]) -> list[dict]:
    """``group``'s players in the order of ``slots`` (left to right): each on the side his
    position names and, for an attacking or a defensive midfielder, in the more advanced or the
    deeper places of the line, as near as the slots allow; the rest, and every tie, by shirt
    number."""
    players = sorted(group, key=lambda p: p["number"])
    ys = [slot["y"] for slot in slots]
    depth = [None if min(ys) == max(ys) else 0 if y == min(ys) else 2 if y == max(ys) else 1
             for y in ys]
    best: tuple | None = None
    for order in permutations(players):
        cost = 0
        for p, slot, deep in zip(order, slots, depth, strict=False):
            if p.get("side") in SIDES:
                cost += abs(SIDES.index(p["side"]) - _slot_side(slot))
            if p.get("depth") is not None and deep is not None:
                cost += abs(p["depth"] - deep)
        rank = (cost, [p["number"] for p in order])
        if best is None or rank < best[0]:
            best = (rank, list(order))
    return best[1] if best else []


def propose(players: list[dict], formation: str) -> tuple[list[str], str | None]:
    """The proposed XI for ``formation`` (player ids in its slot order) and a line naming a tie
    at the cut, if there is one.

    A position with fewer players than its slots takes the next players by the same key from
    the rest of the squad.
    """
    slots = FORMATIONS[formation]
    picked: dict[str, list[dict]] = {}
    ties: list[str] = []
    for group in GROUPS:
        need = sum(1 for slot in slots if slot["group"] == group)
        pool = sorted((p for p in players if p["group"] == group), key=_most_appearances)
        picked[group] = pool[:need]
        if 0 < need < len(pool) and pool[need - 1]["apps"] is not None and (
                pool[need]["apps"] == pool[need - 1]["apps"]):
            level = pool[need - 1]["apps"]
            names = [p["short"] for p in pool if p["apps"] == level]
            starts = [p["short"] for p in pool[:need] if p["apps"] == level]
            ties.append(f"{_listing(names)} have {level} appearances each; "
                        f"{_listing(starts)} {'starts' if len(starts) == 1 else 'start'} "
                        "on the lower shirt number.")
    chosen = {p["id"] for group in picked.values() for p in group}
    rest = sorted((p for p in players if p["id"] not in chosen), key=_most_appearances)
    for group in GROUPS:
        need = sum(1 for slot in slots if slot["group"] == group)
        while len(picked[group]) < need and rest:
            picked[group].append(rest.pop(0))
    xi: list[str] = [""] * len(slots)
    for group in GROUPS:
        places = sorted((i for i, slot in enumerate(slots) if slot["group"] == group),
                        key=lambda i: (slots[i]["x"], slots[i]["y"]))
        placed = _place([slots[i] for i in places], picked[group])
        for index, player in zip(places, placed, strict=False):
            xi[index] = player["id"]
    if "" in xi:
        raise FeedError("The current squad list is too short for a lineup.")
    return xi, " ".join(ties) or None


def _lines(by_id: dict[str, dict], formation: str, xi: list[str]) -> str:
    # The eleven by position, from the back, left to right as the board shows them:
    # "Courtois; Huijsen, Konaté, Cucurella, Dumfries; ...".
    slots = FORMATIONS[formation]
    parts = []
    for group in GROUPS:
        places = sorted((i for i, slot in enumerate(slots) if slot["group"] == group),
                        key=lambda i: (slots[i]["x"], slots[i]["y"]))
        if places:
            parts.append(", ".join(by_id[xi[i]]["short"] for i in places))
    return "; ".join(parts)


def proposal_answer(by_id: dict[str, dict], formation: str, xi: list[str],
                    season: str) -> str:
    """The page's sentence for a proposed XI. The pitch shows the eleven; the sentence says how
    they were picked (``proposal_names`` lists them for a screen reader)."""
    return (f"The proposed {formation} picks the players with the most {season} appearances "
            "in each position.")


def proposal_names(by_id: dict[str, dict], formation: str, xi: list[str]) -> str:
    """The proposed eleven by position, from the back: "Courtois; Huijsen, Konaté, ..."."""
    return _lines(by_id, formation, xi) + "."


def lineup_answer(by_id: dict[str, dict], formation: str, xi: list[str], proposed: list[str],
                  season: str) -> str:
    """The page's sentence for the lineup on the board, set against the proposed XI of the
    same formation."""
    if xi == proposed:
        return proposal_answer(by_id, formation, xi, season)
    kept = [pid for pid in xi if pid in proposed]
    if len(kept) == len(proposed):
        moved = sum(1 for a, b in zip(xi, proposed, strict=True) if a != b)
        places = "another place" if moved == 1 else "other places"
        return (f"This {formation} starts the proposed eleven, the most {season} appearances "
                f"in each position, with {moved} of them in {places}.")
    ins = [by_id[pid]["short"] for pid in xi if pid not in proposed]
    outs = [by_id[pid]["short"] for pid in proposed if pid not in xi]
    if not kept:
        return (f"This {formation} shares none of the {len(proposed)} proposed starters, the "
                f"most {season} appearances in each position.")
    verb = "starts" if len(ins) == 1 else "start"
    return (f"This {formation} keeps {len(kept)} of the {len(proposed)} proposed starters; "
            f"{_listing(ins)} {verb} in place of {_listing(outs)}.")


def share_query(players: list[dict], formation: str, xi: list[str], season: str) -> str:
    """A lineup's link query: its formation, its shirt numbers in slot order, its season."""
    numbers = {p["id"]: p["number"] for p in players}
    return urlencode({"formation": formation, "xi": "-".join(str(numbers[pid]) for pid in xi),
                      "season": season.replace("/", "-")})


def parse_share(players: list[dict], formation: str, xi: str, season: str | None,
                current: str) -> list[str]:
    """The player ids of a shared lineup, in slot order, or ``ValueError`` with a sentence a
    reader can act on."""
    if formation not in FORMATIONS:
        raise ValueError("This link names a formation the board doesn't have.")
    if season is not None and season.replace("-", "/") != current:
        raise ValueError(f"This link holds a lineup from another season, not {current}.")
    slots = len(FORMATIONS[formation])
    if not re.fullmatch(rf"[0-9]{{1,2}}(-[0-9]{{1,2}}){{{slots - 1}}}", xi):
        raise ValueError(f"This link doesn't hold {slots} shirt numbers.")
    by_number: dict[int, list[str]] = {}
    for p in players:
        by_number.setdefault(p["number"], []).append(p["id"])
    ids = []
    for number in (int(n) for n in xi.split("-")):
        found = by_number.get(number, [])
        if len(found) != 1:
            raise ValueError(f"This link's lineup doesn't match the {current} squad.")
        ids.append(found[0])
    if len(set(ids)) != len(ids):
        raise ValueError("This link names a player twice.")
    return ids


# ------------------------------------------------------------------ the next match


GOAL_LEAGUE = {"es.1": "es", "en.1": "en", "de.1": "de", "it.1": "it", "fr.1": "fr",
               "ucl": "ucl"}
"""A competition's key in the goal explorer (``goal_scout.LEAGUES``), where it has one."""


def next_card(fixture: dict | None, today: date) -> dict:
    """Madrid's next fixture as the Next match card shows it, from the Matches page's own
    schedule (OpenFootball; OpenLigaDB for the Champions League). Nothing here is invented: a
    missing round or kick-off time is left out."""
    if fixture is None:
        return {"fixture": None, "empty": "No further Real Madrid fixture is listed this season."}
    home = fixture["home"] in MADRID
    madrid, opponent = ((fixture["home"], fixture["away"]) if home
                        else (fixture["away"], fixture["home"]))
    kickoff = fixture.get("kickoff")
    competition = fixture["competition"]
    if fixture.get("round"):
        competition += f" · {fixture['round']}"
    code = fixture["code"]
    return {
        "fixture": {
            "opponent": opponent, "venue": "Home" if home else "Away",
            "when": day_label(fixture["day"], today) + (f" · {kickoff}" if kickoff else ""),
            "competition": competition, "code": code, "day": fixture["day"],
            "links": {
                "form": "/match-centre?" + urlencode({"day": fixture["day"],
                                                      "match": fixture["id"]}),
                "table": "/match-centre/leagues?" + urlencode({"league": code,
                                                               "highlight": madrid}),
                "goals": None,
            },
        },
        "credit": CREDITS["openligadb" if code in EUROPE else "openfootball"],
    }


async def opponent_goals_link(goals: goal_scout.GoalScout, code: str, opponent: str,
                              today: date) -> str | None:
    """The goal explorer opened on ``opponent``, where the explorer covers his league and the
    feed names a club of that exact name; else ``None``."""
    league = GOAL_LEAGUE.get(code)
    if league not in goal_scout.LEAGUES:
        return None
    try:
        report = await goals.report(league, None, today)
    except FeedError:
        return None
    clubs = (report or {}).get("clubs") or {}
    club = next((cid for cid, name in clubs.items()
                 if str(name).casefold() == opponent.casefold()), None)
    if club is None:
        return None
    return ("/match-centre/scouting?" + urlencode({"goalsLeague": league, "goalsClub": club})
            + "#goals")


# ------------------------------------------------------------------ the service


SCORERS_ORDER = "By goals, then name."


def scorers(players: list[dict], season: str) -> dict:
    """The squad's scorers this season in all competitions, by the declared key (goals, then
    name), and the sentence that opens the list. Only players the article credits with a goal
    are listed; a blank count is not a zero and is left out."""
    rows = sorted((p for p in players if p.get("goals")),
                  key=lambda p: (-p["goals"], p["name"].casefold()))
    listed = [{"id": p["id"], "name": p["name"], "group": p["group"], "number": p["number"],
               "apps": p["apps"], "goals": p["goals"]} for p in rows]
    if not rows:
        return {"rows": [], "order": SCORERS_ORDER,
                "answer": f"The squad list credits no {season} goal to a player yet."}
    most = rows[0]["goals"]
    leaders = [p for p in rows if p["goals"] == most]
    if len(leaders) == 1:
        lead = leaders[0]
        apps = (f" in {lead['apps']} {'appearance' if lead['apps'] == 1 else 'appearances'}"
                if lead["apps"] else "")
        answer = (f"{lead['name']} has the most {season} goals in the squad, all "
                  f"competitions: {most}{apps}.")
    elif len(leaders) <= 3:
        answer = (f"{_listing([p['name'] for p in leaders])} have the most {season} goals in "
                  f"the squad, all competitions: {most} each.")
    else:
        answer = (f"{len(leaders)} players share the most {season} goals in the squad, all "
                  f"competitions: {most} each.")
    others = len(rows) - 1
    answer += (f" {others} other {'player has' if others == 1 else 'players have'} scored."
               if others else "")
    return {"rows": listed, "order": SCORERS_ORDER, "answer": answer}


class Studio:
    def __init__(self) -> None:
        self.cache = FeedCache(16)
        self._revised: dict[int, str | None] = {}

    async def positions(self, slugs: list[str]) -> dict[str, str]:
        """Each player's first position as his Wikipedia article's infobox lists it, by slug,
        kept for a day. One batched API request; where the API turns the request away, each
        article's source, a few at a time. Empty when no article can be read."""
        titles = sorted({slug.replace("_", " ") for slug in slugs})[:50]

        async def one(client: httpx.AsyncClient, title: str) -> tuple[str, str | None]:
            try:
                response = await client.get(RAW, params={"title": title, "action": "raw"})
                response.raise_for_status()
            except httpx.HTTPError:
                return title, None
            return title, first_position(response.text)

        async def fetch() -> list:
            params = {"action": "query", "prop": "revisions", "rvprop": "content",
                      "rvslots": "main", "format": "json", "formatversion": "2",
                      "redirects": "1", "titles": "|".join(titles)}
            async with httpx.AsyncClient(headers=AGENT, timeout=12,
                                         follow_redirects=True) as client:
                try:
                    response = await client.get(API, params=params)
                    response.raise_for_status()
                    found = parse_positions(response.json())
                except (httpx.HTTPError, ValueError, FeedError):
                    found = {}
                    gate = asyncio.Semaphore(4)

                    async def gated(title: str) -> tuple[str, str | None]:
                        async with gate:
                            return await one(client, title)

                    for title, position in await asyncio.gather(*map(gated, titles)):
                        if position:
                            found[title] = position
            if not found:
                raise FeedError("The players' articles couldn't be read.")
            return [{"title": title, "position": position} for title, position in found.items()]

        try:
            snap = await self.cache.get("positions/" + "|".join(titles), 24*3600, fetch)
        except FeedError:
            return {}
        return {row["title"].replace(" ", "_"): row["position"] for row in snap.rows}

    async def roster(self, day: date) -> dict:
        year = season_start(day)
        season = f"{year}–{(year+1)%100:02}"
        url = f"https://en.wikipedia.org/wiki/{season}_Real_Madrid_CF_season"
        assert_may_host("wikipedia")

        async def fetch() -> list:
            async with httpx.AsyncClient(headers=AGENT, timeout=12) as client:
                response = await client.get(url)
            response.raise_for_status()
            players = parse_roster(response.text)
            self._revised[year] = revised_on(response.text)
            return players

        snap = await self.cache.get(f"roster/{year}", 6*3600, fetch)
        # A side matters only where it places a player the proposals start.
        starters = {pid for formation in FORMATIONS for pid in propose(snap.rows, formation)[0]}
        found = await self.positions([p["id"] for p in snap.rows
                                      if p["id"] in starters and p["group"] != "GK"])
        players = [{**p, "position": found.get(p["id"]), "side": side_of(found.get(p["id"])),
                    "depth": depth_of(found.get(p["id"]))} for p in snap.rows]
        revised = self._revised.get(year)
        return {"players": players, "season": season, "checked": snap.checked,
                "warning": snap.warning, "source": url, "credit": "Wikipedia contributors",
                "licence": "https://creativecommons.org/licenses/by-sa/4.0/",
                "sides": bool(found), "revised": revised,
                "revised_label": long_day(revised) if revised else None}

    async def lineup(self, day: date) -> dict:
        """The squad, the formations, and the proposed XI of each formation with its
        sentence."""
        roster = await self.roster(day)
        players, label = roster["players"], season_label(day)
        by_id = {p["id"]: p for p in players}
        proposals = {}
        for formation in FORMATIONS:
            xi, ties = propose(players, formation)
            proposals[formation] = {"xi": xi, "ties": ties,
                                    "answer": proposal_answer(by_id, formation, xi, label),
                                    "names": proposal_names(by_id, formation, xi)}
        sides = roster.get("sides", False)
        return {**roster, "season_label": label, "order": ORDER, "key": key_line(label, sides),
                "rule": rule_line(label, sides), "formations": FORMATIONS,
                "default": DEFAULT_FORMATION, "proposals": proposals}

    async def scorers(self, day: date) -> dict:
        """The squad's scorers this season, all competitions, with the sentence and credit."""
        roster = await self.roster(day)
        return {**scorers(roster["players"], season_label(day)),
                **{key: roster[key] for key in ("source", "credit", "licence", "checked",
                                                "warning", "revised", "revised_label")},
                "season_label": season_label(day)}

    async def compare(self, day: date, formation: str, xi: str, season: str | None) -> dict:
        """A lineup from a link or from the board: its ids and its sentence."""
        roster = await self.roster(day)
        players, label = roster["players"], season_label(day)
        ids = parse_share(players, formation, xi, season, label)
        proposed, _ = propose(players, formation)
        by_id = {p["id"]: p for p in players}
        return {"formation": formation, "xi": ids, "proposed": ids == proposed,
                "answer": lineup_answer(by_id, formation, ids, proposed, label),
                "warning": roster["warning"]}

    async def activity(self, slug: str) -> dict | None:
        if slug not in SAMPLES:
            return None
        sample = SAMPLES[slug]
        assert_may_host("pappalardo")

        async def fetch() -> list:
            async with httpx.AsyncClient(headers=AGENT, timeout=12) as client:
                response = await client.get(f"{MIRROR}/{sample.match_id}.json")
            response.raise_for_status()
            payload = response.json()
            events = payload.get("events") if isinstance(payload, dict) else None
            if not isinstance(events, list):
                raise FeedError("The spatial sample could not be read.")
            points = []
            for e in events:
                if not isinstance(e, dict) or e.get("playerId") != sample.player:
                    continue
                kind = e.get("eventId")
                if not isinstance(kind, int) or kind not in ACTIONS:
                    continue
                positions = e.get("positions")
                if not isinstance(positions, list) or not positions:
                    continue
                if not isinstance(positions[0], dict):
                    continue
                pos = positions[0]
                x, y = pos.get("x"), pos.get("y")
                if isinstance(x, bool) or isinstance(y, bool):
                    continue
                if (isinstance(x, (int, float)) and isinstance(y, (int, float))
                        and 0 <= x <= 100 and 0 <= y <= 100 and (x, y) not in {(0, 0), (100, 100)}):
                    points.append({"x": x, "y": y, "type": ACTIONS[kind]})
            if not points:
                raise FeedError("No located actions are available for this player in this sample.")
            return points

        snap = await self.cache.get(f"activity/{slug}", 24*3600, fetch)
        return {"player": slug, "match": sample.match, "competition": sample.competition,
                "date": sample.day,
                "label": (f"Archive sample: {sample.match}, {sample.competition}, "
                          f"{long_day(sample.day)} (his last recorded match in the public "
                          "2017/18 data)"),
                "points": snap.rows, "warning": snap.warning,
                "credit": "Pappalardo et al. / Wyscout",
                "source": "https://doi.org/10.6084/m9.figshare.7770599.v1",
                "licence": "https://creativecommons.org/licenses/by/4.0/"}
