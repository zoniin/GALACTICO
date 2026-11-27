"""Lineup: the squad, the XI the server proposes by a declared key, the next match and the
archive samples each keep their own source, scope and date.

The proposed XI is chosen by one visible key (most appearances this season in each position,
ties to the lower shirt number, places inside a position by shirt number), never by merit (R1),
and every sentence about a lineup is the server's (R10). The hosted app cannot import the copy
guard, so every sentence shape is run through ``scan_labels`` here (R3). Every number in a
sentence is a count the data gives (R8).

Re-pinned under ADR-0034 (Answer-first pages): a roster row carries its short name and the
squad comes in the declared order; ``/api/studio/squad`` serves the formations and the proposed
XI of each; an archive sample carries its competition and its label, its match named as the
public data names it; the hard-coded editorial XI is gone. The proposal's sentence says how the
XI was picked and leaves the eleven names to the pitch (and to a screen-reader list,
``proposal_names``); within a position a player stands where his Wikipedia article's first
position puts him (side, and for midfielders attacking or defensive), else by shirt number.

Re-pinned under B13 (the season data layer, D2-B): the squad list is read through the MediaWiki
API (``action=parse``, and the parsed revision's time for the day it was last edited), never the
rendered page; on a stubbed article, ``/api/studio/*`` and ``/lineup`` answer with the same bytes
the rendered page's read gave.
"""

import asyncio
import glob
import json
import re
from datetime import date
from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from galactico.domain.labels import scan_labels
from galactico.match_centre import goal_scout
from galactico.match_centre.feed import FeedError
from galactico.match_centre.openfootball import OpenFootball
from galactico.match_centre.public import create_centre
from galactico.match_centre.studio import (
    ANALYST_TOOLS,
    FORMATIONS,
    GROUPS,
    SAMPLES,
    Studio,
    depth_of,
    first_position,
    key_line,
    lineup_answer,
    long_day,
    next_card,
    opponent_goals_link,
    parse_positions,
    parse_roster,
    parse_share,
    proposal_answer,
    proposal_names,
    propose,
    revised_on,
    rule_line,
    scorers,
    share_query,
    short_name,
    side_of,
)


@pytest.fixture(autouse=True)
def no_squad_names(monkeypatch):
    # The squad list (Wikipedia) writes Real Madrid's scorers on the pages (names.py); no test
    # reaches it unless it says so.
    from galactico.match_centre.studio import Studio

    async def names(self, day):
        return []

    monkeypatch.setattr(Studio, "squad_names", names)

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
PAPPALARDO = ROOT / "data" / "public" / "pappalardo"
SEASON = "2026/27"


def squad_html():
    def table(headers, body):
        head = "".join(f"<th>{h}</th>" for h in headers)
        return f'<table class="wikitable"><tr>{head}</tr>{body}</table>'

    def player_row(slug, number, *values, group="MF"):
        # Deliberately use the same display name and a different shirt in the totals table.
        player = f'<a href="./{slug}" title="{slug}">Player</a>'
        cells = [number, group, "ESP", player, *values]
        return "<tr>" + "".join(f"<td>{v}</td>" for v in cells) + "</tr>"

    roster = table(["No.", "Pos.", "Nation", "Player"],
                   "".join(player_row(f"Test_{n}", n, group="FW" if n == 9 else "MF")
                           for n in range(11, 0, -1)))
    stats = table(["No.", "Pos.", "Nat.", "Player", "Total", "League"],
                  "<tr><th>Apps</th><th>Goals</th></tr>"
                  + player_row("Departed", 1, 10, 4)
                  + player_row("Test_1", 22, 7, 0)
                  + player_row("Test_3", 2, "–", 3))
    return stats + roster


def squad(spec: str) -> list[dict]:
    """A squad from "GK:1:17 DF:4:14 ...": group, shirt number, appearances ("-" for none)."""
    players = []
    for item in spec.split():
        group, number, apps = item.split(":")
        name = f"Player Name{number}"
        players.append({"id": f"P{number}", "name": name, "short": short_name(name),
                        "number": int(number), "group": group, "nation": "ESP",
                        "archive": False, "apps": None if apps == "-" else int(apps),
                        "goals": None})
    return players


# A squad shaped like Real Madrid's on 26 November 2026: ties at 18 among the forwards and at
# 15 among the midfielders, three players with no appearance, one with none listed.
CLUB = squad("GK:1:17 GK:13:1 DF:2:0 DF:3:3 DF:4:14 DF:12:9 DF:16:15 DF:17:18 DF:18:10 "
             "DF:22:8 DF:23:0 DF:24:11 MF:5:18 MF:6:15 MF:8:17 MF:14:11 MF:15:16 MF:20:15 "
             "MF:27:1 FW:7:14 FW:9:8 FW:10:18 FW:11:- FW:19:12 FW:21:10 FW:25:18")
BY_ID = {p["id"]: p for p in CLUB}


def numbers(xi):
    return [BY_ID[pid]["number"] for pid in xi]


def test_roster_joins_current_members_by_link_and_keeps_unknown_totals():
    found = parse_roster(squad_html())
    players = {p["id"]: p for p in found}
    assert len(players) == 11 and "Departed" not in players
    assert players["Test_1"] == dict(id="Test_1", number=1, name="Player", short="Player",
                                     nation="ESP", group="MF", archive=False, apps=7, goals=0)
    assert players["Test_2"]["goals"] is None
    assert players["Test_3"]["apps"] is None and players["Test_3"]["goals"] == 3
    # The declared order: by position from the back, then shirt number.
    assert [(p["group"], p["number"]) for p in found] == (
        [("MF", n) for n in (1, 2, 3, 4, 5, 6, 7, 8, 10, 11)] + [("FW", 9)])
    with pytest.raises(FeedError):
        parse_roster("<html></html>")


def test_the_proposed_xi_takes_the_most_appearances_in_each_position():
    xi, ties = propose(CLUB, "4-3-3")
    slots = FORMATIONS["4-3-3"]
    chosen = {g: sorted(BY_ID[pid]["number"] for pid, s in zip(xi, slots, strict=True)
                        if s["group"] == g) for g in GROUPS}
    assert chosen == {"GK": [1], "DF": [4, 16, 17, 24], "MF": [5, 8, 15], "FW": [7, 10, 25]}
    # Within a position, left to right by shirt number: LB 4, LCB 16, RCB 17, RB 24.
    assert numbers(xi) == [7, 10, 25, 5, 8, 15, 4, 16, 17, 24, 1]
    assert ties is None
    assert proposal_answer(BY_ID, "4-3-3", xi, SEASON) == (
        "The proposed 4-3-3 picks the players with the most 2026/27 appearances in each "
        "position.")
    assert proposal_names(BY_ID, "4-3-3", xi) == (
        "Name1; Name4, Name16, Name17, Name24; Name5, Name8, Name15; Name7, Name10, Name25.")


def test_the_squad_scorers_are_listed_by_goals_then_name_and_counted_from_the_list():
    goals = [dict(p, goals=g) for p, g in zip(CLUB, (0, 0, 2, None) + (0,) * 5 + (5, 0, 2)
                                              + (0,) * 14, strict=True)]
    found = scorers(goals, SEASON)
    # Only players credited with a goal; a blank count is not a zero and is left out.
    assert [(r["name"], r["goals"]) for r in found["rows"]] == [
        ("Player Name22", 5), ("Player Name2", 2), ("Player Name24", 2)]
    assert found["order"] == "By goals, then name."
    assert found["answer"] == ("Player Name22 has the most 2026/27 goals in the squad, all "
                               "competitions: 5 in 8 appearances. 2 other players have scored.")
    # Every number is the list's: the season, the goals, the appearances, the other scorers.
    numbers_ = re.findall(r"\d+", found["answer"].replace("Player Name22", ""))
    assert set(numbers_) <= {"2026", "27", "5", "8", "2"}
    assert scorers(CLUB, SEASON)["rows"] == []


def test_a_player_stands_where_his_wikipedia_position_puts_him():
    # The article's first position, read as written; a side or a depth only where it says one.
    wikitext = ("{{Infobox football biography\n| name = X\n| position = [[Full-back (association "
                "football)|Left-back]], [[Defender (association football)#Centre-back|centre-back]]"
                "<ref>x</ref>\n| years1 = 2020\n}}")
    assert first_position(wikitext) == "Left-back"
    assert [side_of(p) for p in ("Left-back", "Right winger", "Centre-back", "Attacking "
                                 "midfielder", "Winger", "Forward", None)] == [
        "L", "R", "C", "C", None, None, None]
    assert [depth_of(p) for p in ("Attacking midfielder", "Defensive midfielder",
                                  "Centre-back")] == [0, 2, None]
    reply = {"query": {"normalized": [{"from": "Name_4", "to": "Name 4"}],
                       "pages": [{"title": "Name 4", "revisions": [{"slots": {"main": {
                           "content": "| position = [[Defender#Centre-back|Centre-back]]"}}}]}]}}
    assert parse_positions(reply) == {"Name_4": "Centre-back"}
    with pytest.raises(FeedError):
        parse_positions({"error": "x"})
    # The back four by shirt number would be 4, 16, 17, 24 from the left; the articles put the
    # left-back (24) on the left and the right-back (4) on the right.
    sides = {4: ("R", None), 16: ("C", None), 17: ("C", None), 24: ("L", None),
             5: ("C", 2), 15: ("C", 0)}
    players = [dict(p, side=sides.get(p["number"], (None, None))[0],
                    depth=sides.get(p["number"], (None, None))[1]) for p in CLUB]
    by_id = {p["id"]: p for p in players}
    xi, _ = propose(players, "4-3-3")
    roles = [slot["role"] for slot in FORMATIONS["4-3-3"]]
    placed = {role: by_id[pid]["number"] for role, pid in zip(roles, xi, strict=True)}
    assert [placed[r] for r in ("LB", "LCB", "RCB", "RB")] == [24, 16, 17, 4]
    # The defensive midfielder (5) takes the deepest place, the attacking one (15) a forward
    # one; the one the article gives neither (8) takes what is left, by shirt number.
    assert (placed["DM"], placed["LCM"], placed["RCM"]) == (5, 8, 15)
    assert "Wikipedia position" in key_line(SEASON) and "by shirt number" in key_line(SEASON)
    assert key_line(SEASON, False).endswith("left to right by shirt number")
    assert revised_on('<li id="footer-info-lastmod"> This page was last edited on 25 November '
                      '2026, at 10:12</li>') == "2026-11-25"
    assert revised_on("<html></html>") is None


def test_a_tie_at_the_cut_goes_to_the_lower_shirt_number_and_is_named():
    xi, ties = propose(CLUB, "4-4-2")
    assert sorted(numbers(xi)) == [1, 4, 5, 6, 8, 10, 15, 16, 17, 24, 25]
    assert ties == ("Name6 and Name20 have 15 appearances each; Name6 starts on the lower "
                    "shirt number.")
    xi, ties = propose(CLUB, "4-2-3-1")
    assert 10 in numbers(xi) and 25 not in numbers(xi)
    assert ties == ("Name10 and Name25 have 18 appearances each; Name10 starts on the lower "
                    "shirt number.")


def test_no_count_listed_comes_after_every_count_and_a_short_position_borrows_by_the_key():
    players = squad("GK:1:- GK:13:0 DF:2:5 DF:3:4 DF:4:3 MF:5:9 MF:6:8 MF:7:7 MF:8:6 MF:10:1 "
                    "FW:9:2 FW:11:- FW:19:- FW:21:0")
    xi, _ = propose(players, "4-3-3")
    by_id = {p["id"]: p for p in players}
    # No count listed comes after a count of none: the keeper with 0 starts, and the forward
    # with 0 starts ahead of two with none listed (11 before 19 on the shirt number). Three
    # defenders for four places: the next player by the key, #8 (6 appearances), takes the
    # fourth, and stands rightmost as the highest number of the back four.
    assert sorted(by_id[pid]["number"] for pid in xi) == [2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 21]
    roles = [s["role"] for s in FORMATIONS["4-3-3"]]
    assert by_id[xi[roles.index("GK")]]["number"] == 13
    assert [by_id[xi[roles.index(r)]]["number"] for r in ("LB", "LCB", "RCB", "RB")] == [2, 3, 4, 8]


def test_the_sentence_follows_the_board_against_the_proposal():
    proposed, _ = propose(CLUB, "4-3-3")
    moved = list(proposed)
    moved[0], moved[2] = moved[2], moved[0]
    assert lineup_answer(BY_ID, "4-3-3", moved, proposed, SEASON) == (
        "This 4-3-3 starts the proposed eleven, the most 2026/27 appearances in each position, "
        "with 2 of them in other places: Name25 plays LW and Name7 RW.")
    swapped = list(proposed)
    swapped[5] = "P6"  # Name6 for Name15
    assert lineup_answer(BY_ID, "4-3-3", swapped, proposed, SEASON) == (
        "This 4-3-3 keeps 10 of the 11 proposed starters; Name6 starts in place of Name15.")
    two = list(swapped)
    two[6] = "P18"  # Name18 for Name4
    assert lineup_answer(BY_ID, "4-3-3", two, proposed, SEASON) == (
        "This 4-3-3 keeps 9 of the 11 proposed starters; Name6 and Name18 start in place of "
        "Name15 and Name4.")
    # A substitution and a swap: the sentence names the move as well (H21).
    both = list(swapped)
    both[0], both[1] = both[1], both[0]
    assert lineup_answer(BY_ID, "4-3-3", both, proposed, SEASON) == (
        "This 4-3-3 keeps 10 of the 11 proposed starters; Name6 starts in place of Name15; "
        f"{BY_ID[proposed[1]]['short']} plays LW and {BY_ID[proposed[0]]['short']} ST.")
    assert scan_labels([lineup_answer(BY_ID, "4-3-3", both, proposed, SEASON)]) == []
    others = ["P13", "P2", "P3", "P12", "P18", "P22", "P23", "P14", "P20", "P27", "P9"]
    assert lineup_answer(BY_ID, "4-3-3", others, proposed, SEASON) == (
        "This 4-3-3 shares none of the 11 proposed starters, the most 2026/27 appearances in "
        "each position.")
    assert lineup_answer(BY_ID, "4-3-3", proposed, proposed, SEASON) == proposal_answer(
        BY_ID, "4-3-3", proposed, SEASON)


def test_a_link_carries_the_lineup_and_refuses_one_the_squad_cannot_hold():
    xi, _ = propose(CLUB, "3-5-2")
    query = share_query(CLUB, "3-5-2", xi, SEASON)
    assert query == "formation=3-5-2&xi=10-25-5-6-8-15-20-4-16-17-1&season=2026-27"
    assert parse_share(CLUB, "3-5-2", "10-25-5-6-8-15-20-4-16-17-1", "2026-27", SEASON) == xi
    assert parse_share(CLUB, "3-5-2", "10-25-5-6-8-15-20-4-16-17-1", None, SEASON) == xi
    for formation, numbers_, season, said in (
        ("5-4-1", "1-2-3-4-5-6-7-8-9-10-11", None, "formation the board doesn’t have"),
        ("4-3-3", "1-2-3", None, "doesn’t hold 11 shirt numbers"),
        ("4-3-3", "1-2-3-4-5-6-7-8-9-10-99", None, "doesn’t match the 2026/27 squad"),
        ("4-3-3", "1-2-3-4-5-6-7-8-9-10-10", None, "names a player twice"),
        ("4-3-3", "1-2-3-4-5-6-7-8-9-10-11", "2025-26", "from another season, not 2026/27"),
    ):
        with pytest.raises(ValueError, match=said):
            parse_share(CLUB, formation, numbers_, season, SEASON)
    # A link with no formation is of the default one, so the real problem is the one said
    # (H20); a formation alone opens its proposed XI (FN-1).
    with pytest.raises(ValueError, match="doesn’t hold 11 shirt numbers"):
        parse_share(CLUB, "", "garbage", None, SEASON)
    assert parse_share(CLUB, "4-4-2", "", None, SEASON) == propose(CLUB, "4-4-2")[0]
    assert parse_share(CLUB, "", "", None, SEASON) == propose(CLUB, "4-3-3")[0]


def test_the_next_match_card_comes_from_the_schedule_and_invents_nothing():
    fixture = {"id": "es.1-2026-f27c047388ef136d", "code": "es.1", "competition": "La Liga",
               "home": "Real Madrid CF", "away": "Deportivo Alavés", "day": "2026-11-29",
               "kickoff": None, "round": "Matchday 14", "score": None}
    card = next_card(fixture, date(2026, 11, 26))
    assert card["fixture"] == {
        "opponent": "Deportivo Alavés", "venue": "Home", "when": "Sun 29 Nov",
        "kickoff": None, "kickoff_utc": None,
        "competition": "La Liga · Matchday 14", "code": "es.1", "day": "2026-11-29",
        "links": {"form": "/match-centre?day=2026-11-29&match=es.1-2026-f27c047388ef136d",
                  "table": "/match-centre/leagues?league=es.1&highlight=Real+Madrid+CF",
                  "goals": None}}
    assert card["credit"]["name"] == "OpenFootball"
    away = dict(fixture, code="ucl", competition="Champions League", home="PSV Eindhoven",
                away="Real Madrid", kickoff="21:00", kickoff_utc="2026-11-29T20:00:00Z",
                round=None)
    card = next_card(away, date(2026, 11, 26))
    # Re-pinned (D2): the day is the server's words; the kick-off travels as an instant the page
    # shows in the reader's time zone (was "Sun 29 Nov · 21:00", the source's local time).
    assert (card["fixture"]["venue"], card["fixture"]["when"], card["fixture"]["competition"],
            card["credit"]["name"]) == ("Away", "Sun 29 Nov", "Champions League", "OpenLigaDB")
    assert (card["fixture"]["kickoff"], card["fixture"]["kickoff_utc"]) == (
        "21:00", "2026-11-29T20:00:00Z")
    assert next_card(None, date(2026, 11, 26)) == {
        "fixture": None, "empty": "No further Real Madrid fixture is listed this season."}


def test_the_goal_explorer_is_linked_only_where_it_covers_the_opponent(monkeypatch):
    class Goals:
        def __init__(self, clubs=None, error=None):
            self.clubs, self.error, self.asked = clubs, error, []

        async def report(self, league, club, today):
            self.asked.append(league)
            if self.error:
                raise self.error
            return {"clubs": self.clubs}

    today = date(2026, 11, 26)
    monkeypatch.setattr(goal_scout, "LEAGUES", {"en": ("pl", "Premier League", 1)})
    found = Goals({7: "Arsenal FC", 8: "Chelsea FC"})
    assert asyncio.run(opponent_goals_link(found, "en.1", "Chelsea FC", today)) == (
        "/match-centre/scouting?goalsLeague=en&goalsClub=8#goals")
    # A competition the explorer does not cover is never asked for.
    assert asyncio.run(opponent_goals_link(found, "es.1", "Deportivo Alavés", today)) is None
    assert found.asked == ["en"]
    assert asyncio.run(opponent_goals_link(found, "en.1", "Fulham FC", today)) is None
    failing = Goals(error=FeedError("OpenLigaDB is unavailable."))
    assert asyncio.run(opponent_goals_link(failing, "en.1", "Chelsea FC", today)) is None


def test_every_sentence_the_lineup_serves_passes_the_copy_guard():
    served = [key_line(SEASON), rule_line(SEASON), key_line(SEASON, False),
              rule_line(SEASON, False)]
    # The squad's scorers (the Players page's first card): every sentence shape.
    goals = [dict(p, goals=g) for p, g in zip(CLUB, (19, 7, 4, 4, 1) + (0,) * 21, strict=True)]
    served += [scorers(goals, SEASON)["answer"], scorers(CLUB, SEASON)["answer"],
               scorers([dict(p, goals=3) for p in CLUB[:2]], SEASON)["answer"],
               scorers([dict(p, goals=3) for p in CLUB[:5]], SEASON)["answer"],
               scorers(goals, SEASON)["order"]]
    for formation in FORMATIONS:
        xi, ties = propose(CLUB, formation)
        served += [proposal_answer(BY_ID, formation, xi, SEASON), ties or ""]
        served += [slot["zone"] for slot in FORMATIONS[formation]]
    proposed, _ = propose(CLUB, "4-3-3")
    swapped = [*proposed[:5], "P6", *proposed[6:]]
    moved = [proposed[2], proposed[1], proposed[0], *proposed[3:]]
    others = ["P13", "P2", "P3", "P12", "P18", "P22", "P23", "P14", "P20", "P27", "P9"]
    served += [lineup_answer(BY_ID, "4-3-3", xi, proposed, SEASON)
               for xi in (swapped, moved, others)]
    served += [f"Archive sample: {s.match}, {s.competition}, {long_day(s.day)} (his last "
               "recorded match in the public 2017/18 data)" for s in SAMPLES.values()]
    for bad in ("5-4-1", "4-3-3"):
        with pytest.raises(ValueError) as caught:
            parse_share(CLUB, bad, "1-2-3-4-5-6-7-8-9-10-99", None, SEASON)
        served.append(str(caught.value))
    card = next_card({"id": "x", "code": "es.1", "competition": "La Liga", "home": "Real Madrid CF",
                      "away": "Deportivo Alavés", "day": "2026-11-29", "kickoff": "21:00",
                      "round": "Matchday 14"}, date(2026, 11, 26))
    served += [card["fixture"]["when"], card["fixture"]["competition"], card["fixture"]["venue"],
               next_card(None, date(2026, 11, 26))["empty"]]
    assert scan_labels(served) == []


def test_the_page_is_answer_first_and_its_own_text_passes_the_copy_guard():
    html = (WEB / "studio.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")
    # One h1 naming the object, the server's sentence under it, then the board.
    assert [h.get_text(strip=True) for h in soup.find_all("h1")] == ["Lineup"]
    header = main.find("header", class_="page-header")
    assert header.find("p", id="answer", class_="page-answer") is not None
    assert main.find(id="field") is not None
    order = [main.find(id=i).sourceline for i in ("answer", "field", "bench-list", "next")]
    assert order == sorted(order)
    # The 2017/18 archive map and the notes are closed by default, the notes last (ADR-0034,
    # G3-4: an archive sample does not take a 2026/27 page's prime space). Re-pinned (H28): the
    # analyst's import is not in the page file; the server fills its slot on a local install
    # only, closed, before the notes.
    details = main.find_all("details")
    assert [d.find("summary").get_text(" ", strip=True) for d in details] == [
        "Archive: where he played in 2017/18", "About these numbers"]
    assert all(not d.has_attr("open") for d in details)
    assert details[0].find("canvas", id="map") is not None
    assert html.count("<!--slot:tools-->") == 1
    assert html.index("<!--slot:tools-->") < html.index('class="ui-disclosure ln-about"')
    tools = BeautifulSoup(ANALYST_TOOLS, "html.parser").find("details")
    assert tools.find("summary").get_text(" ", strip=True) == "Analyst tools Import match events"
    assert not tools.has_attr("open") and tools.find("input", id="file") is not None
    with TestClient(create_centre("Test")) as client:
        hosted = client.get("/lineup").text
    assert "Analyst tools" not in hosted and 'id="file"' not in hosted
    from galactico.api.player_lab import app as local_app
    with TestClient(local_app) as client:
        local = client.get("/lineup").text
    assert local.count("Analyst tools") == 1 and 'id="file"' in local
    # The page's own sheet is in the page layer; the old sheets are not loaded.
    sheets = [link["href"] for link in soup.find_all("link", rel="stylesheet")]
    assert sheets == ["/static/lineup.css"]
    sheet = re.sub(r"/\*.*?\*/", "", (WEB / "lineup.css").read_text(encoding="utf-8"), flags=re.S)
    assert sheet.strip().startswith("@layer page {") and "--selected" not in sheet
    for hidden in soup.select(".sr-only"):
        hidden.decompose()
    text = " ".join(main.get_text(" ", strip=True).split())
    assert scan_labels(text) == []


def test_the_script_renders_the_server_and_never_ranks_or_sorts():
    script = (WEB / "studio.js").read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", script, flags=re.S)
    # The order of the squad and the bench is the server's; the XI is the server's proposal.
    assert ".sort(" not in code and "localeCompare" not in code
    assert "data.proposals[" in code and "/api/studio/lineup?" in code
    assert "La Liga goal log" not in script and "goal-scout/es" not in script
    # A link restores the lineup it carries; a change rewrites the address at once.
    assert "history.replaceState" in code and "navigator.clipboard.writeText" in code


def roster_stub(players):
    async def roster(self, day):
        return {"players": players, "season": "2026–27", "checked": "2026-11-26T12:00:00+00:00",
                "warning": None, "source": "https://en.wikipedia.org/", "credit": "Wikipedia",
                "licence": "https://creativecommons.org/licenses/by-sa/4.0/"}
    return roster


def test_studio_routes_serve_the_proposal_the_link_and_the_next_match(monkeypatch):
    monkeypatch.setattr(Studio, "roster", roster_stub(CLUB))

    async def summary(self, today):
        return {"next": {"id": "es.1-2026-f27c047388ef136d", "code": "es.1",
                         "competition": "La Liga", "home": "Real Madrid CF",
                         "away": "Deportivo Alavés", "day": "2026-11-29", "kickoff": "21:00",
                         "round": "Matchday 14"}, "unavailable": None, "warnings": []}

    monkeypatch.setattr(OpenFootball, "summary", summary)
    monkeypatch.setattr(goal_scout, "LEAGUES", {"de": ("bl1", "Bundesliga", 40)})
    with TestClient(create_centre("Test")) as client:
        reply = client.get("/api/studio/squad")
        assert reply.status_code == 200
        assert reply.headers["vercel-cdn-cache-control"] == (
            "s-maxage=3600, stale-while-revalidate=3600, stale-if-error=86400")
        data = reply.json()
        assert data["default"] == "4-3-3" and list(data["formations"]) == list(FORMATIONS)
        # The stub's roster has no Wikipedia positions: the key says shirt number throughout.
        assert data["key"] == key_line(SEASON, False) and data["season_label"] == SEASON
        assert data["proposals"]["4-3-3"]["names"].startswith("Name1; Name4, Name16")
        assert numbers(data["proposals"]["4-3-3"]["xi"]) == [7, 10, 25, 5, 8, 15, 4, 16, 17,
                                                             24, 1]
        assert data["proposals"]["4-4-2"]["ties"].startswith("Name6 and Name20")
        shared = client.get("/api/studio/lineup", params={
            "formation": "4-3-3", "xi": "7-10-25-5-8-6-4-16-17-24-1", "season": "2026-27"})
        assert shared.status_code == 200
        assert shared.json()["answer"] == (
            "This 4-3-3 keeps 10 of the 11 proposed starters; Name6 starts in place of Name15.")
        assert shared.json()["proposed"] is False
        refused = client.get("/api/studio/lineup", params={
            "formation": "4-3-3", "xi": "7-10-25-5-8-6-4-16-17-24-99"})
        assert refused.status_code == 422
        assert refused.json()["detail"] == "This link’s lineup doesn’t match the 2026/27 squad."
        card = client.get("/api/studio/next").json()
        assert card["fixture"]["opponent"] == "Deportivo Alavés"
        assert card["fixture"]["when"] == "Sun 29 Nov"
        assert card["fixture"]["kickoff"] == "21:00"
        assert card["fixture"]["links"]["goals"] is None


def test_studio_routes_preserve_fixture_links_and_separate_missing_data(monkeypatch):
    async def unavailable(self, url, **kwargs):
        return httpx.Response(503, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", unavailable)
    with TestClient(create_centre("Test")) as client:
        # "/" is Matches on every app; the studio is /lineup. Old fixture links on "/" still
        # open the board.
        assert "<title>Lineup · Galáctico</title>" in client.get("/lineup").text
        for url in ("/", "/?day=2026-09-01"):
            assert "<title>Matches · Galáctico</title>" in client.get(url).text
        assert client.get("/api/studio/squad").status_code == 503
        assert client.get("/api/studio/lineup", params={
            "formation": "4-3-3", "xi": "1-2-3-4-5-6-7-8-9-10-11"}).status_code == 503
        assert client.get("/api/studio/next").status_code == 503
        assert client.get("/api/studio/activity/Unknown").status_code == 404
        assert client.get("/api/studio/activity/Kylian_Mbappé").status_code == 503


def test_event_map_uses_valid_action_starts_for_the_selected_player(monkeypatch):
    slug = "Kylian_Mbappé"
    sample = SAMPLES[slug]
    person = sample.player

    def event(who=person, kind=8, *locations):
        return dict(playerId=who, eventId=kind,
                    positions=[dict(x=x, y=y) for x, y in locations])

    events = [event(person, 8, (10, 20), (80, 90)), event(person, 10, (0, 35)),
              event(person, 8, (0, 0)), event(person, 8, (100, 100)),
              event(person, 8, (-3, 5)), event(person, 8, ("6", 4)),
              event(-1, 8, (11, 12)), event(person, 2, (11, 12)), event(), None]

    async def get(self, url):
        return httpx.Response(200, json={"events": events}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    found = asyncio.run(Studio().activity(slug))
    assert found["match"] == sample.match and found["date"] == sample.day
    assert found["label"] == ("Archive sample: France v Croatia, World Cup, Sun 15 Jul 2018 "
                              "(his last recorded match in the public 2017/18 data)")
    assert found["points"] == [dict(x=10, y=20, type="Pass"), dict(x=0, y=35, type="Shot")]


@pytest.mark.parametrize("payload", [[], {"events": []}])
def test_unusable_event_files_return_a_feed_error(monkeypatch, payload):
    async def get(self, url):
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    with pytest.raises(FeedError):
        asyncio.run(Studio().activity("Kylian_Mbappé"))


COMPETITION = {"World Cup": "World Cup", "Spanish first division": "La Liga",
               "French first division": "Ligue 1"}


@pytest.mark.slow
def test_each_archive_label_is_what_the_public_data_says():
    """The match, the competition and the date of each sample, and that it is the player's last
    recorded match (a start or a substitute's entry), read from the local corpus."""
    if not (PAPPALARDO / "competitions.json").exists():
        pytest.skip("public historical corpus not downloaded")
    competitions = {c["wyId"]: c["name"] for c in json.loads(
        (PAPPALARDO / "competitions.json").read_text(encoding="utf-8"))}
    matches, played = {}, {s.player: [] for s in SAMPLES.values()}
    for path in glob.glob(str(PAPPALARDO / "matches_*.json")):
        for match in json.loads(Path(path).read_text(encoding="utf-8")):
            matches[match["wyId"]] = match
            for team in match["teamsData"].values():
                formation = team.get("formation") or {}
                on = {row["playerId"] for row in formation.get("lineup") or []}
                on |= {row["playerIn"] for row in formation.get("substitutions") or []
                       if isinstance(row, dict)}
                for person in played:
                    if person in on:
                        played[person].append((match["dateutc"], match["wyId"]))
    for slug, sample in SAMPLES.items():
        match = matches[sample.match_id]
        # The files keep some labels escaped twice ("Deportivo La Coru\\u00f1a").
        label = json.loads('"' + match["label"].replace('"', '\\"') + '"')
        teams = label.split(",")[0].split(" - ")
        assert sample.match == " v ".join(teams), slug
        assert sample.competition == COMPETITION[competitions[match["competitionId"]]], slug
        assert match["dateutc"].startswith(sample.day), slug
        assert max(played[sample.player])[1] == sample.match_id, slug


def test_every_slot_is_named_in_words_and_the_archive_sample_counts_in_football_terms():
    # D9: "LCM" reads "Left central midfield" wherever a slot is named in words; H28: the
    # archive sample's counts are the server's, in football words.
    from galactico.match_centre.studio import ROLE_NAMES, activity_filters
    for formation, slots in FORMATIONS.items():
        for slot in slots:
            assert slot["name"] == ROLE_NAMES[slot["role"]], (formation, slot["role"])
            assert slot["zone"] == f"Drawn area for the {slot['name'].lower()} role, not measured"
    assert ROLE_NAMES["LCM"] == "Left central midfield"
    assert ROLE_NAMES["RCM"] == "Right central midfield"
    assert scan_labels(list(ROLE_NAMES.values())) == []
    points = [{"x": 1, "y": 1, "type": kind} for kind in ("Pass", "Pass", "Duel", "Ball action")]
    assert activity_filters(points) == [
        {"type": "All actions", "label": "All actions",
         "count": "4 actions in his last 2017/18 match"},
        {"type": "Pass", "label": "Passes", "count": "2 passes in his last 2017/18 match"},
        {"type": "Duel", "label": "Duels", "count": "1 duel in his last 2017/18 match"},
        {"type": "Ball action", "label": "Touches",
         "count": "1 touch in his last 2017/18 match"}]
    assert scan_labels([f["count"] for f in activity_filters(points)]) == []
    # The 3-5-2's wing-backs stand wider and deeper than its central midfielders (H7).
    by = {s["role"]: s for s in FORMATIONS["3-5-2"]}
    assert by["LWB"]["x"] < 12 and by["RWB"]["x"] > 88
    assert by["LWB"]["y"] - by["LCM"]["y"] >= 12 and by["RWB"]["y"] - by["RCM"]["y"] >= 12


# ------------------------------------------------------------------ B13: the MediaWiki read


def _stub_article():
    """The squad list and a statistics table as the parser renders them (invented players),
    and each player's infobox for the positions request."""
    from urllib.parse import quote

    import season_wiki as wiki
    from season_v4 import SQUAD

    head = "".join(f"<th>{h}</th>" for h in ("No.", "Pos.", "Nat.", "Player", "Total",
                                             "La Liga"))
    rows = "".join(
        f'<tr><td>{p.shirt}</td><td>{p.group}</td><td>{p.nation}</td><td><a href="/wiki/'
        f'{quote(p.wp_title, safe="(),_")}" title="{p.wp_title.replace("_", " ")}">{p.wp_name}'
        f"</a></td><td>{(p.shirt * 7) % 19}</td><td>{p.shirt % 4}</td></tr>"
        for p in SQUAD if p.group)
    body = wiki.squad_html() + (f'<table class="wikitable"><tbody><tr>{head}</tr><tr><th>Apps'
                                f"</th><th>Goals</th><th>Apps</th><th>Goals</th></tr>{rows}"
                                "</tbody></table>")
    boxes = {p.wp_title.replace("_", " "): wiki.infobox(
        name=p.wp_name, position="[[Defender#Full-back|Left-back]]" if p.group == "DF"
        else "[[Midfielder]]", born=(2000, 1, 1)) for p in SQUAD if p.wp_title}
    return wiki, body, boxes


def _upstream(monkeypatch, *, parse=None, stamp=None):
    """Every Wikipedia request the Lineup makes, stubbed and recorded."""
    wiki, body, boxes = _stub_article()
    footer = ('<li id="footer-info-lastmod"> This page was last edited on 25 November 2026, '
              "at 22:52</li>")
    asked = []

    async def get(self, url, params=None, **kwargs):
        request = httpx.Request("GET", url, params=params)
        asked.append((request, dict(self.headers)))
        if url.endswith("/w/api.php") and params.get("action") == "parse":
            reply = parse or wiki.parse_reply("", body)
            return httpx.Response(200, json=reply, request=request)
        if url.endswith("/w/api.php") and params.get("rvprop") == "timestamp|ids":
            reply = stamp or wiki.revision_stamp(1000020, "2026-11-25T22:52:44Z")
            return httpx.Response(200, json=reply, request=request)
        if url.endswith("/w/api.php"):
            titles = params["titles"].split("|")
            return httpx.Response(200, json=wiki.articles_reply(
                {t: boxes.get(t) for t in titles}), request=request)
        if "/wiki/" in url:
            return httpx.Response(200, text=body + footer, request=request)
        return httpx.Response(404, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    return asked


@pytest.fixture
def fixed_clock(monkeypatch):
    from datetime import UTC
    from datetime import datetime as real

    from galactico.match_centre import feed

    class Fixed(real):
        @classmethod
        def now(cls, tz=None):
            return real(2026, 11, 26, 12, tzinfo=UTC)

    monkeypatch.setattr(feed, "datetime", Fixed)


PINNED = ("/api/studio/squad", "/api/studio/scorers", "/lineup",
          "/api/studio/lineup?formation=4-3-3&xi=9-7-11-6-8-10-2-3-4-5-1&season=2026-27",
          "/lineup?formation=4-3-3&xi=9-7-11-6-8-10-2-3-4-5-1")


def _replies():
    with TestClient(create_centre("Test")) as client:
        return {path: (reply.status_code, sorted((k, v) for k, v in reply.headers.items()
                                                  if k not in ("date", "content-length")),
                       reply.content)
                for path in PINNED for reply in [client.get(path)]}


def test_the_squad_list_reads_through_mediawiki_and_every_reply_keeps_its_bytes(
        monkeypatch, fixed_clock):
    """R13: the rendered page's read (kept here as it was) and the MediaWiki read give the
    same bytes on one stubbed article, for every Lineup reply that reads the squad list."""
    from galactico.match_centre import studio as studio_module

    asked = _upstream(monkeypatch)
    new = _replies()
    assert not [r for r, _ in asked if "/wiki/" in r.url.path]
    parse = next(r for r, _ in asked if r.url.params.get("action") == "parse")
    assert parse.url.host == "en.wikipedia.org" and parse.url.path == "/w/api.php"
    assert dict(parse.url.params) == {
        "action": "parse", "page": "2026–27 Real Madrid CF season", "prop": "text|revid",
        "redirects": "1", "format": "json", "formatversion": "2", "maxlag": "5"}
    stamp = next(r for r, _ in asked if r.url.params.get("rvprop") == "timestamp|ids")
    assert stamp.url.params["revids"] == "1000020" and stamp.url.params["maxlag"] == "5"
    assert all(headers["user-agent"] == studio_module.AGENT["User-Agent"]
               for _, headers in asked)
    # B13: every API request, the infobox batch included, carries maxlag.
    api = [r for r, _ in asked if r.url.path == "/w/api.php"]
    assert any("titles" in r.url.params for r in api)
    assert all(r.url.params.get("maxlag") == "5" for r in api)

    async def rendered_page(self, day):
        # The read before B13: the rendered page, and its footer's last-edited day.
        year, _, url = self._article(day)

        async def fetch():
            async with httpx.AsyncClient(headers=studio_module.AGENT, timeout=12) as client:
                response = await client.get(url)
            response.raise_for_status()
            players = parse_roster(response.text)
            self._revised[year] = revised_on(response.text)
            return players

        return await self.cache.get(f"roster/{year}", 6 * 3600, fetch)

    monkeypatch.setattr(Studio, "squad", rendered_page)
    old = _replies()
    assert [r.url.path for r, _ in asked].count("/wiki/2026–27_Real_Madrid_CF_season") == 1
    assert old == new
    assert json.loads(new["/api/studio/squad"][2])["revised"] == "2026-11-25"
    assert all(status == 200 for status, _, _ in new.values())


def test_an_unreadable_parse_is_the_squad_list_unavailable_and_a_missing_time_no_date(
        monkeypatch, fixed_clock):
    import season_wiki as wiki

    _upstream(monkeypatch, parse=wiki.maxlag_reply())
    with TestClient(create_centre("Test")) as client:
        reply = client.get("/api/studio/squad")
    assert reply.status_code == 503
    assert reply.json()["detail"] == "The current squad list is unavailable."
    _upstream(monkeypatch, stamp={"batchcomplete": True, "query": {"pages": []}})
    with TestClient(create_centre("Test")) as client:
        data = client.get("/api/studio/squad").json()
    assert data["revised"] is None and data["revised_label"] is None and data["players"]
